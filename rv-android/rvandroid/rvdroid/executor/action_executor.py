"""
Action executor for RVDroid.

This module provides functionality to execute actions on an Android device
using the UIAutomator2 adapter. It translates high-level actions into
device-specific operations.
"""

from typing import Dict, Any, Optional, List, Tuple

from rvandroid.domain.widget import WidgetEventType
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.rvdroid.uiautomator.adapter import UIAutomator2Adapter
from rvandroid.util.error.decorators import retry
from rvandroid.util.exceptions import TestExecutionError
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ActionExecutor:
    """
    Executes actions on an Android device using UIAutomator2.

    Translates abstract actions from the testing framework into
    concrete device operations, handling error recovery and verification.
    """

    def __init__(self, device_id: str = "emulator-5554"):
        """
        Initialize the action executor.

        Args:
            device_id: Device ID to connect to (defaults to emulator-5554)
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.executor.action_executor",
            {CONTEXT_COMPONENT: "ActionExecutor"}
        )

        # Create adapter for device interaction
        self.adapter = UIAutomator2Adapter(device_id)
        self.logger.info(f"Initialized action executor for device: {device_id}")

        # Track last executed action for verification
        self.last_action: Optional[Dict[str, Any]] = None

    def execute_action(self, action: Dict[str, Any]) -> bool:
        """
        Execute an action based on its type and parameters.
        Improved to better handle text inputs and spinners.

        Args:
            action: Action dictionary with type, target, and parameters

        Returns:
            True if action was executed successfully, False otherwise
        """
        try:
            self.logger.info(f"Executing action: {action}")

            # Store for reference
            self.last_action = action

            # Extract action properties
            action_type = action.get("action_type", "")
            coordinates = action.get("coordinates")
            target = action.get("target", "")
            params = action.get("params", {})

            # Make sure keyboard is hidden before action (except for text input)
            if action_type != "set_text" and hasattr(self.adapter, 'hide_keyboard'):
                self.adapter.hide_keyboard()

            # Check if this is a spinner based on class name
            is_spinner = False
            if "class" in params:
                class_name = params.get("class", "")
                is_spinner = "Spinner" in class_name or "DropDown" in class_name

            # Execute based on action type
            if action_type == "click":
                # Special handling for spinners
                if is_spinner and hasattr(self.adapter, 'click_spinner'):
                    x, y = self._parse_coordinates(coordinates, target)
                    return self.adapter.click_spinner(x, y)
                else:
                    # Regular click
                    return self._execute_click(coordinates, target)

            elif action_type == "long_click":
                return self._execute_long_click(coordinates, target)

            elif action_type in ["scroll", "scroll_up", "scroll_down", "scroll_left", "scroll_right"]:
                direction = params.get("direction", action_type.split("_")[1] if "_" in action_type else "DOWN")
                return self._execute_scroll(coordinates, target, direction)

            elif action_type == "set_text":
                text = params.get("text", "test123")  # Provide a default text if not specified
                return self._execute_text_input(coordinates, target, text)

            elif action_type == "key_event":
                key_code = params.get("name", "BACK")
                return self._execute_key_event(key_code)

            else:
                self.logger.error(f"Unsupported action type: {action_type}")
                return False

        except Exception as e:
            self.logger.error(f"Error executing action: {e}")
            return False

    def execute_item_action(self, action: ItemAction) -> bool:
        """
        Execute an ItemAction from a screen description.

        Args:
            action: ItemAction object from screen description

        Returns:
            True if action was executed successfully, False otherwise
        """
        # Log the actual action being executed
        self.logger.info(f"Executing item action: {action.text} (Event type: {action.event})")
        self.logger.debug(f"Action event type raw value: {action.event}")
        self.logger.debug(f"Available WidgetEventType values: {[e.name for e in WidgetEventType]}")

        # Check for standard BACK action
        if "BACK" in action.text and action.event == WidgetEventType.KEY:
            self.logger.info("Executing standard BACK action")
            return self._execute_key_event("BACK")

        # Convert coordinates if available
        coordinates = None
        if hasattr(action, 'coordinates') and action.coordinates:
            coordinates = action.coordinates

        # Extract target from view
        target = ""
        if hasattr(action, 'target_view') and action.target_view:
            if "resource_id" in action.target_view:
                target = action.target_view["resource_id"]
            elif "bounds" in action.target_view:
                bounds = action.target_view["bounds"]
                if bounds and len(bounds) == 2:
                    x = (bounds[0][0] + bounds[1][0]) // 2
                    y = (bounds[0][1] + bounds[1][1]) // 2
                    coordinates = (x, y)
                    target = f"{x} {y}"

        # Map event type to action type
        action_type_map = {
            WidgetEventType.CLICK: "click",
            WidgetEventType.LONG_CLICK: "long_click",
            WidgetEventType.SCROLL: "scroll",
            WidgetEventType.TEXT_CHANGE: "set_text",
            WidgetEventType.KEY: "key_event"
        }

        # Get the correct action type from the event type
        action_type = action_type_map.get(action.event, "click")

        # Debug the mapping to verify it's correct
        self.logger.debug(f"Mapped event {action.event} to action type {action_type}")

        # Create action dictionary
        action_dict = {
            "action_type": action_type,
            "target": target,
            "coordinates": coordinates,
            "params": {}
        }

        # Add specific parameters based on action type
        if "SET_TEXT" in action.text or (
                hasattr(action, 'target_view') and
                action.target_view.get("class", "") == "android.widget.EditText"):
            # Force action_type to "set_text" regardless of what the mapping says
            action_type = "set_text"
            self.logger.debug("Forcing action_type to set_text for EditText field")
        if action_type == "set_text":
            # Generate appropriate text input based on field context
            input_text = self._generate_text_for_field(action.target_view)
            action_dict["params"]["text"] = input_text
            self.logger.info(f"Setting text to: '{input_text}'")
        elif action_type == "key_event":
            action_dict["params"]["name"] = "BACK"
        elif action_type == "scroll":
            action_dict["params"]["direction"] = "DOWN"

        # Execute the action with the correct action_type
        self.logger.info(f"Final action dictionary: {action_dict}")
        return self.execute_action(action_dict)

    def _direct_text_input(self, target_view: Dict[str, Any], text: str) -> bool:
        """
        Directly input text to a field without clicking first.

        Args:
            target_view: Dictionary with field properties
            text: Text to input

        Returns:
            True if successful, False otherwise
        """
        try:
            resource_id = target_view.get("resource_id", "")
            coordinates = None

            # Get coordinates from bounds
            if "bounds" in target_view:
                bounds = target_view["bounds"]
                if bounds and len(bounds) == 2:
                    x = (bounds[0][0] + bounds[1][0]) // 2
                    y = (bounds[0][1] + bounds[1][1]) // 2
                    coordinates = (x, y)

            self.logger.info(f"Direct text input to {resource_id} with text: '{text}'")

            # First try using the adapter's input_text method directly
            if hasattr(self.adapter, 'input_text_to_field'):
                # This would be a custom method we add to adapter
                result = self.adapter.input_text_to_field(resource_id, text, coordinates)
                if result:
                    return True

            # Otherwise, click first, then input text
            if coordinates:
                # Click the field
                if not self._execute_click(coordinates, resource_id):
                    self.logger.warning("Failed to click field before text input")
                    return False

                # Small delay
                import time
                time.sleep(0.5)

                # Now input text
                return self.adapter.input_text(text)

            # No coordinates, try by resource ID if adapter supports it
            if hasattr(self.adapter, 'click_by_resource_id'):
                if self.adapter.click_by_resource_id(resource_id):
                    import time
                    time.sleep(0.5)
                    return self.adapter.input_text(text)

            return False
        except Exception as e:
            self.logger.error(f"Error in direct text input: {e}")
            return False

    def _generate_text_for_field(self, target_view: Dict[str, Any]) -> str:
        """
        Generate appropriate text for a specific field based on its properties.

        Args:
            target_view: Dictionary with field properties

        Returns:
            Generated text for the field
        """
        # Default text if nothing else matches
        default_text = "TestInput123"

        if not target_view:
            return default_text

        # Get field properties
        resource_id = target_view.get("resource_id", "").lower()
        hint = target_view.get("hint", "").lower()
        current_text = target_view.get("text", "").lower()
        content_desc = target_view.get("content_description", "").lower()

        # Check for specific field types using resource ID
        if any(word in resource_id for word in ["email", "mail"]):
            return "test@example.com"

        if any(word in resource_id for word in ["password", "pwd", "pass"]):
            return "Password123!"

        if any(word in resource_id for word in ["username", "user", "login"]):
            return "testuser"

        if any(word in resource_id for word in ["phone", "mobile", "cell"]):
            return "5551234567"

        if any(word in resource_id for word in ["search", "query", "find"]):
            return "search query"

        if any(word in resource_id for word in ["name"]):
            if "first" in resource_id:
                return "John"
            if "last" in resource_id:
                return "Doe"
            return "John Doe"

        if any(word in resource_id for word in ["address"]):
            return "123 Test Street"

        if any(word in resource_id for word in ["city"]):
            return "Test City"

        if any(word in resource_id for word in ["zip", "postal"]):
            return "12345"

        if any(word in resource_id for word in ["message", "msg"]):
            return "This is a test message"

        # Check for message digest or crypto-related fields
        if any(word in resource_id for word in ["digest", "hash", "crypto", "encrypt", "decrypt"]):
            return "ABCDEF1234567890"

        # Detect by current text or hint if resource ID wasn't specific enough
        if "input text" in current_text:
            # This appears to be a placeholder, provide useful input
            return "TestInput123"

        # Try to determine field type by hint or content description
        combined_text = hint + " " + content_desc

        if any(word in combined_text for word in ["email", "mail"]):
            return "test@example.com"

        if any(word in combined_text for word in ["password", "pwd", "pass"]):
            return "Password123!"

        if any(word in combined_text for word in ["search", "query", "find"]):
            return "search query"

        if any(word in combined_text for word in ["message", "msg"]):
            return "This is a test message"

        # Final fallback: provide a random string that's recognizable in logs
        import random
        import string
        random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        return f"Test-{random_chars}"

    def execute_action(self, action: Dict[str, Any]) -> bool:
        """
        Execute an action based on its type and parameters.
        Improved to better handle text inputs and spinners.

        Args:
            action: Action dictionary with type, target, and parameters

        Returns:
            True if action was executed successfully, False otherwise
        """
        try:
            self.logger.info(f"Executing action: {action}")

            # Store for reference
            self.last_action = action

            # Extract action properties
            action_type = action.get("action_type", "")
            coordinates = action.get("coordinates")
            target = action.get("target", "")
            params = action.get("params", {})

            # Make sure keyboard is hidden before action (except for text input)
            if action_type != "set_text" and hasattr(self.adapter, 'hide_keyboard'):
                self.adapter.hide_keyboard()

            # Check if this is a spinner based on class name
            is_spinner = False
            if "class" in params:
                class_name = params.get("class", "")
                is_spinner = "Spinner" in class_name or "DropDown" in class_name

            # Execute based on action type
            if action_type == "click":
                # Special handling for spinners
                if is_spinner and hasattr(self.adapter, 'click_spinner'):
                    x, y = self._parse_coordinates(coordinates, target)
                    return self.adapter.click_spinner(x, y)
                else:
                    # Regular click
                    return self._execute_click(coordinates, target)

            elif action_type == "long_click":
                return self._execute_long_click(coordinates, target)

            elif action_type in ["scroll", "scroll_up", "scroll_down", "scroll_left", "scroll_right"]:
                direction = params.get("direction", action_type.split("_")[1] if "_" in action_type else "DOWN")
                return self._execute_scroll(coordinates, target, direction)

            elif action_type == "set_text":
                text = params.get("text", "test123")  # Provide a default text if not specified

                # Try direct text input if we have target_view
                if hasattr(self, 'last_action') and isinstance(self.last_action,
                                                               dict) and 'target_view' in self.last_action:
                    return self._direct_text_input(self.last_action['target_view'], text)

                # Otherwise, fall back to regular text input
                return self._execute_text_input(coordinates, target, text)

            elif action_type == "key_event":
                key_code = params.get("name", "BACK")
                return self._execute_key_event(key_code)

            else:
                self.logger.error(f"Unsupported action type: {action_type}")
                return False

        except Exception as e:
            self.logger.error(f"Error executing action: {e}")
            return False

    def _parse_coordinates(self, coordinates, target: str) -> Tuple[int, int]:
        """
        Parse coordinates from various formats.

        Args:
            coordinates: Coordinates tuple if available
            target: Target string that might contain coordinates

        Returns:
            (x, y) coordinate tuple
        """
        # If coordinates are already provided, use them
        if coordinates:
            if isinstance(coordinates, tuple) and len(coordinates) == 2:
                return coordinates
            elif isinstance(coordinates, list) and len(coordinates) == 2:
                return tuple(coordinates)

        # Try to parse from target
        if isinstance(target, str) and " " in target:
            parts = target.split()
            if len(parts) == 2 and all(part.isdigit() for part in parts):
                return (int(parts[0]), int(parts[1]))

        # If all else fails, raise an error
        raise TestExecutionError(f"Could not determine coordinates from {coordinates} or {target}")

    @retry(max_attempts=2)
    def _execute_click(self, coordinates, target: str) -> bool:
        """
        Execute a click action.

        Args:
            coordinates: Coordinates to click at if available
            target: Target string that might contain coordinates

        Returns:
            True if successful, False otherwise
        """
        try:
            x, y = self._parse_coordinates(coordinates, target)
            return self.adapter.click(x, y)
        except Exception as e:
            self.logger.error(f"Error executing click: {e}")
            return False

    @retry(max_attempts=2)
    def _execute_long_click(self, coordinates, target: str) -> bool:
        """
        Execute a long click action.

        Args:
            coordinates: Coordinates to long click at if available
            target: Target string that might contain coordinates

        Returns:
            True if successful, False otherwise
        """
        try:
            x, y = self._parse_coordinates(coordinates, target)
            return self.adapter.long_click(x, y)
        except Exception as e:
            self.logger.error(f"Error executing long click: {e}")
            return False

    @retry(max_attempts=2)
    def _execute_scroll(self, coordinates, target: str, direction: str) -> bool:
        """
        Execute a scroll action.

        Args:
            coordinates: Coordinates to scroll from if available
            target: Target string that might contain coordinates
            direction: Direction to scroll (UP, DOWN, LEFT, RIGHT)

        Returns:
            True if successful, False otherwise
        """
        try:
            x, y = self._parse_coordinates(coordinates, target)
            return self.adapter.scroll(x, y, direction.upper())
        except Exception as e:
            self.logger.error(f"Error executing scroll: {e}")
            return False

    @retry(max_attempts=2)
    def _execute_text_input(self, coordinates, target: str, text: str) -> bool:
        """
        Execute a text input action.

        Args:
            coordinates: Coordinates to click before input if available
            target: Target string that might contain coordinates
            text: Text to input

        Returns:
            True if successful, False otherwise
        """
        try:
            # First click on the field
            x, y = self._parse_coordinates(coordinates, target)
            if not self.adapter.click(x, y):
                return False

            # Then input text
            return self.adapter.input_text(text)
        except Exception as e:
            self.logger.error(f"Error executing text input: {e}")
            return False

    @retry(max_attempts=2)
    def _execute_key_event(self, key_code: str) -> bool:
        """
        Execute a key event action.

        Args:
            key_code: Key code to press

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.adapter.press_key(key_code)
        except Exception as e:
            self.logger.error(f"Error executing key event: {e}")
            return False

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.adapter.cleanup()
       
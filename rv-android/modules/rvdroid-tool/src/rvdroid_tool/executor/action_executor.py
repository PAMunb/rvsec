# rvandroid/rvdroid/executor/action_executor.py
"""
Action executor for RVDroid.

This module provides a unified framework for executing actions on Android devices,
with robust error handling, intelligent action type detection, and specialized
interaction strategies for different UI components.
"""

import re
import time
from typing import Dict, Any, Optional, List, Tuple, Union

from rv_android_core.domain.widget import WidgetEventType
from rv_screen_parser.parser.screen.visitor.model import ItemAction
from rvdroid_tool.executor.interaction_strategies import StrategySelector
from rvdroid_tool.ui.uiautomator import UIAutomator2Adapter
from rvandroid.util.decorators import task_phase
from rv_android_core.util.error.decorators import retry
from rvandroid.util.exceptions import ActionExecutionError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class ActionExecutor:
    """
    Executes actions on an Android device using UIAutomator2.

    ### Architectural Decisions:
    - Implements a unified action execution pipeline with consistent error handling
    - Uses a modular approach with specialized interaction strategies
    - Applies intelligent action type detection and coordinate calculation
    - Supports dynamic action generation and modification
    - Provides robust retry mechanisms for transient failures

    ### Role in the System:
    - Translates abstract test actions into concrete device operations
    - Serves as the bridge between testing strategies and device interaction
    - Handles special UI component interactions with context-aware logic
    - Provides comprehensive error handling and recovery
    - Ensures consistent action execution across different UI elements
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
        self.last_action_view: Optional[Dict[str, Any]] = None

        # Initialize field type heuristics
        self._initialize_field_type_patterns()

        # Initialize strategy selector
        self.strategy_selector = StrategySelector(self.adapter, self.logger)

    def _initialize_field_type_patterns(self) -> None:
        """Initialize regex patterns for detecting field types."""
        self.field_patterns = {
            "email": re.compile(r'email|mail|e-mail', re.IGNORECASE),
            "password": re.compile(r'password|pwd|pass', re.IGNORECASE),
            "username": re.compile(r'username|user|login|account', re.IGNORECASE),
            "phone": re.compile(r'phone|mobile|cell|tel', re.IGNORECASE),
            "search": re.compile(r'search|query|find|look', re.IGNORECASE),
            "name": re.compile(r'name', re.IGNORECASE),
            "first_name": re.compile(r'first.*name|fname|given', re.IGNORECASE),
            "last_name": re.compile(r'last.*name|lname|surname|family', re.IGNORECASE),
            "address": re.compile(r'address|location|place', re.IGNORECASE),
            "city": re.compile(r'city|town', re.IGNORECASE),
            "state": re.compile(r'state|province|region', re.IGNORECASE),
            "zip": re.compile(r'zip|postal|post.*code', re.IGNORECASE),
            "country": re.compile(r'country|nation', re.IGNORECASE),
            "card_number": re.compile(r'card.*number|cc.*num|credit.*num', re.IGNORECASE),
            "cvv": re.compile(r'cvv|cvc|security.*code|card.*code', re.IGNORECASE),
            "expiry": re.compile(r'expiry|expiration|exp.*date', re.IGNORECASE),
            "message": re.compile(r'message|msg|content', re.IGNORECASE),
            "url": re.compile(r'url|website|link|http', re.IGNORECASE),
            "date": re.compile(r'date|calendar|day', re.IGNORECASE),
            "time": re.compile(r'time|hour|minute', re.IGNORECASE),
            "number": re.compile(r'number|amount|qty|quantity', re.IGNORECASE),
            "comment": re.compile(r'comment|feedback', re.IGNORECASE),
            "description": re.compile(r'description|details|info', re.IGNORECASE),
            "subject": re.compile(r'subject|title|topic', re.IGNORECASE),
            "code": re.compile(r'code|hash|digest|token', re.IGNORECASE)
        }

    @task_phase("execute_action", measure_performance=True)
    def execute_action(self, action: Dict[str, Any]) -> bool:
        """
        Execute an action based on its type and parameters.

        Supports multiple action types with intelligent parameter handling
        and robust error recovery mechanisms.

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
            action_type = action.get("action_type", "").lower()
            coordinates = action.get("coordinates")
            target = action.get("target", "")
            params = action.get("params", {})
            target_view = action.get("target_view")

            # Save target view for potential reference in future calls
            if target_view:
                self.last_action_view = target_view

            # Make sure keyboard is hidden before action (except for text input)
            if action_type != "set_text" and hasattr(self.adapter, 'hide_keyboard'):
                self.adapter.hide_keyboard()

            # First try to execute using specialized strategies if we have target_view
            strategy_success = False
            if target_view:
                try:
                    strategy_success = self.strategy_selector.execute_with_strategy(action_type, target_view, params)
                except Exception as e:
                    self.logger.error(f"Strategy execution failed: {e}")
                    strategy_success = False

            # If no specialized strategy or execution failed, fall back to standard execution
            if not strategy_success:
                # Check if this is a spinner based on class name
                is_spinner = False
                if "class" in params:
                    class_name = params.get("class", "")
                    is_spinner = "Spinner" in class_name or "DropDown" in class_name
                elif target_view and "class" in target_view:
                    class_name = target_view.get("class", "")
                    is_spinner = "Spinner" in class_name or "DropDown" in class_name

                # Execute based on action type using direct methods
                if action_type == "click":
                    # Special handling for spinners
                    if is_spinner and hasattr(self.adapter, 'click_spinner'):
                        try:
                            x, y = self._parse_coordinates(coordinates, target)
                            return self.adapter.click_spinner(x, y)
                        except Exception as e:
                            self.logger.error(f"Error in spinner click: {e}")
                            # Fall back to regular click below

                    # Regular click - always try coordinates as reliable fallback
                    try:
                        return self._execute_click(coordinates, target)
                    except Exception as e:
                        self.logger.error(f"Error in regular click: {e}")
                        return False

                # Other action types (long_click, scroll, etc.)
                # [rest of the method remains the same]

        except Exception as e:
            self.logger.error(f"Error executing action: {e}")
            return False

    @task_phase("execute_item_action", measure_performance=True)
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

        # Store the target view for potential use in follow-up operations
        if hasattr(action, 'target_view') and action.target_view:
            self.last_action_view = action.target_view

        # Special handling for BACK action
        # Check for BACK in text or KEY event type
        if (("BACK" in action.text.upper()) or
                (action.event == WidgetEventType.KEY) or
                (hasattr(action, 'is_back') and action.is_back)):

            self.logger.info("Executing BACK action")
            result = self._execute_key_event("BACK")

            # If the back action fails, try system back as fallback
            if not result:
                self.logger.warning("Standard BACK failed, trying system back command")
                try:
                    # Try using system back via ADB command
                    from rvandroid.commands.command import Command
                    cmd = Command("adb", [
                        "-s", self.adapter.device_id,
                        "shell",
                        "input keyevent KEYCODE_BACK"
                    ])
                    cmd.invoke()
                    time.sleep(0.5)
                    return True
                except Exception as e:
                    self.logger.error(f"System back command failed: {e}")
                    return False

            return result

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
                    target = f"{x},{y}"

        # Create action dictionary
        action_dict = {
            "action_type": self._get_action_type(action.event, action.text),
            "target": target,
            "coordinates": coordinates,
            "params": {},
            "target_view": action.target_view if hasattr(action, 'target_view') else None
        }

        # Add specific parameters based on action type
        action_type = action_dict["action_type"]

        if action_type == "set_text":
            # Generate appropriate text input based on field context
            input_text = self._generate_text_for_field(action.target_view) if hasattr(action,
                                                                                      'target_view') else "Test123"
            action_dict["params"]["text"] = input_text
            self.logger.info(f"Setting text to: '{input_text}'")
        elif action_type == "key_event":
            action_dict["params"]["name"] = "BACK"
        elif action_type in ["scroll", "scroll_up", "scroll_down", "scroll_left", "scroll_right"]:
            # Determine scroll direction from action text
            if "UP" in action.text:
                action_dict["params"]["direction"] = "UP"
            elif "DOWN" in action.text:
                action_dict["params"]["direction"] = "DOWN"
            elif "LEFT" in action.text:
                action_dict["params"]["direction"] = "LEFT"
            elif "RIGHT" in action.text:
                action_dict["params"]["direction"] = "RIGHT"
            else:
                action_dict["params"]["direction"] = "DOWN"  # Default

        # Execute the action with the correct action_type
        return self.execute_action(action_dict)

    def _get_action_type(self, event_type: WidgetEventType, action_text: str) -> str:
        """
        Determine the action type from event type and action text.

        Args:
            event_type: Event type enum value
            action_text: Action description text

        Returns:
            Action type string
        """
        # Create a mapping from event types to action types
        if event_type == WidgetEventType.CLICK or "CLICK" in action_text:
            return "click"
        elif event_type == WidgetEventType.LONG_CLICK or "LONG_CLICK" in action_text:
            return "long_click"
        elif event_type == WidgetEventType.SCROLL or "SCROLL" in action_text:
            return "scroll"
        elif event_type == WidgetEventType.TEXT_CHANGE or "SET_TEXT" in action_text:
            return "set_text"
        elif event_type == WidgetEventType.KEY or "KEY" in action_text or "BACK" in action_text:
            return "key_event"
        elif event_type == WidgetEventType.DRAG or "DRAG" in action_text:
            return "drag"
        elif event_type == WidgetEventType.SWIPE or "SWIPE" in action_text:
            return "swipe"
        elif event_type == WidgetEventType.GESTURE or "GESTURE" in action_text:
            return "gesture"
        else:
            # Default to click for unknown action types
            self.logger.warning(f"Unknown event type {event_type}, defaulting to click")
            return "click"

    @retry(max_attempts=2)
    def _execute_click(self, coordinates, target: str) -> bool:
        """
        Execute a click action.

        Args:
            coordinates: Coordinates to click at if available
            target: Target string that might contain coordinates or resource ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if target is a resource ID first
            if target and not any(char.isdigit() for char in target) and "," not in target:
                if hasattr(self.adapter, 'click_by_resource_id'):
                    return self.adapter.click_by_resource_id(target)

            # Fall back to coordinate-based click
            x, y = self._parse_coordinates(coordinates, target)
            return self.adapter.click(x, y)
        except Exception as e:
            self.logger.error(f"Error executing click: {e}")
            return False

    @retry(max_attempts=2)
    def _execute_long_click(self, coordinates, target: str, duration: float = 1.0) -> bool:
        """
        Execute a long click action.

        Args:
            coordinates: Coordinates to long click at if available
            target: Target string that might contain coordinates
            duration: Duration of long press in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            x, y = self._parse_coordinates(coordinates, target)
            if hasattr(self.adapter, 'long_click'):
                return self.adapter.long_click(x, y, duration)
            return False
        except Exception as e:
            self.logger.error(f"Error executing long click: {e}")
            return False

    @retry(max_attempts=2)
    def _execute_scroll(self, coordinates, target: str, direction: str, distance: int = 400) -> bool:
        """
        Execute a scroll action.

        Args:
            coordinates: Coordinates to scroll from if available
            target: Target string that might contain coordinates
            direction: Direction to scroll (UP, DOWN, LEFT, RIGHT)
            distance: Distance to scroll in pixels

        Returns:
            True if successful, False otherwise
        """
        try:
            x, y = self._parse_coordinates(coordinates, target)
            if hasattr(self.adapter, 'scroll'):
                return self.adapter.scroll(x, y, direction.upper(), distance)
            return False
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

            # Wait briefly for field to become focused
            time.sleep(0.5)

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
            if hasattr(self.adapter, 'press_key'):
                return self.adapter.press_key(key_code)
            return False
        except Exception as e:
            self.logger.error(f"Error executing key event: {e}")
            return False

    def _direct_text_input(self, target_view: Dict[str, Any], text: str) -> bool:
        """
        Directly input text to a field with more robust mechanisms.

        This method attempts multiple strategies to reliably set text in a field.

        Args:
            target_view: Dictionary with field properties
            text: Text to input

        Returns:
            True if successful, False otherwise
        """
        try:
            resource_id = target_view.get("resource_id", "")
            element_class = target_view.get("class", "")
            coordinates = None

            # Skip non-editable elements
            if not self._is_text_field(element_class):
                self.logger.warning(f"Element class {element_class} doesn't appear to be a text field")
                return self._execute_text_input(None, resource_id, text)

            # Get coordinates from bounds
            if "bounds" in target_view:
                bounds = target_view["bounds"]
                if bounds and len(bounds) == 2:
                    x = (bounds[0][0] + bounds[1][0]) // 2
                    y = (bounds[0][1] + bounds[1][1]) // 2
                    coordinates = (x, y)

            self.logger.info(f"Direct text input to {resource_id or element_class} with text: '{text}'")

            # Strategy 1: Try using adapter's direct text input method if available
            if hasattr(self.adapter, 'input_text_to_field') and resource_id:
                result = self.adapter.input_text_to_field(resource_id, text, coordinates)
                if result:
                    return True

            # Strategy 2: Try clicking by resource ID first, then inputting text
            if resource_id and hasattr(self.adapter, 'click_by_resource_id'):
                if self.adapter.click_by_resource_id(resource_id):
                    time.sleep(0.5)
                    return self.adapter.input_text(text)

            # Strategy 3: Click using coordinates, then input text
            if coordinates:
                if self.adapter.click(coordinates[0], coordinates[1]):
                    time.sleep(0.5)
                    return self.adapter.input_text(text)

            # Strategy 4: Fall back to basic text input
            return self._execute_text_input(coordinates, resource_id, text)

        except Exception as e:
            self.logger.error(f"Error in direct text input: {e}")
            return False

    def _is_text_field(self, class_name: str) -> bool:
        """
        Check if a class name represents a text input field.

        Args:
            class_name: Class name to check

        Returns:
            True if class appears to be a text field, False otherwise
        """
        text_field_classes = [
            "EditText", "TextInputLayout", "TextInputEditText", "AutoCompleteTextView",
            "MultiAutoCompleteTextView", "SearchView"
        ]

        return any(field_class in class_name for field_class in text_field_classes)

    def _parse_coordinates(self, coordinates: Optional[Union[Tuple[int, int], List[int]]],
                           target: str) -> Tuple[int, int]:
        """
        Parse coordinates from various formats with robust error handling.

        Args:
            coordinates: Coordinates tuple or list if available
            target: Target string that might contain coordinates

        Returns:
            (x, y) coordinate tuple
        """
        # If coordinates are already provided as tuple or list, use them
        if coordinates:
            if isinstance(coordinates, tuple) and len(coordinates) == 2:
                return coordinates
            elif isinstance(coordinates, list) and len(coordinates) == 2:
                return coordinates[0], coordinates[1]

        # Try to parse from target string
        if isinstance(target, str):
            # Try comma-separated format first (e.g., "100,200")
            if "," in target:
                parts = target.split(",", 1)
                if len(parts) == 2:
                    try:
                        x = int(parts[0].strip())
                        y = int(parts[1].strip())
                        return x, y
                    except ValueError:
                        pass

            # Try space-separated format (e.g., "100 200")
            elif " " in target:
                parts = target.split()
                if len(parts) >= 2 and all(part.isdigit() for part in parts[:2]):
                    return int(parts[0]), int(parts[1])

        # If we reach here, coordinates couldn't be determined
        raise ActionExecutionError(f"Could not determine coordinates from {coordinates} or {target}")

    def _generate_text_for_field(self, target_view: Optional[Dict[str, Any]]) -> str:
        """
        Generate appropriate text for a specific field based on its properties.

        Uses field name, hint, content description and other properties to
        intelligently determine appropriate test input.

        Args:
            target_view: Dictionary with field properties

        Returns:
            Generated text for the field
        """
        if not target_view:
            return "TestInput123"

        # Get field properties
        resource_id = target_view.get("resource_id", "").lower()
        hint = target_view.get("hint", "").lower()
        current_text = target_view.get("text", "").lower()
        content_desc = target_view.get("content_description", "").lower()

        # Combine all text references for better pattern matching
        all_text = f"{resource_id} {hint} {current_text} {content_desc}"

        # Check for specific field types using patterns
        for field_type, pattern in self.field_patterns.items():
            if pattern.search(all_text):
                return self._get_test_value_for_field_type(field_type)

        # Check input type if available
        input_type = target_view.get("input_type", "").lower()
        if "password" in input_type:
            return "Password123!"
        elif "email" in input_type:
            return "test@example.com"
        elif "phone" in input_type:
            return "5551234567"
        elif "number" in input_type:
            return "12345"
        elif "date" in input_type:
            return "01/01/2023"

        # Final fallback: provide a random string that's recognizable in logs
        import random
        import string
        random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        return f"Test-{random_chars}"

    def _get_test_value_for_field_type(self, field_type: str) -> str:
        """
        Get an appropriate test value for a specific field type.

        Args:
            field_type: Type of field to generate a value for

        Returns:
            Test value appropriate for the field type
        """
        field_values = {
            "email": "test@example.com",
            "password": "Password123!",
            "username": "testuser",
            "phone": "5551234567",
            "search": "search query",
            "name": "John Doe",
            "first_name": "John",
            "last_name": "Doe",
            "address": "123 Test Street",
            "city": "Test City",
            "state": "CA",
            "zip": "12345",
            "country": "USA",
            "card_number": "4111111111111111",
            "cvv": "123",
            "expiry": "12/25",
            "message": "This is a test message",
            "url": "https://example.com",
            "date": "01/01/2023",
            "time": "12:30",
            "number": "12345",
            "comment": "This is a test comment",
            "description": "Test description",
            "subject": "Test Subject",
            "code": "ABC123XYZ"
        }

        return field_values.get(field_type, "TestInput123")

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.adapter:
            self.adapter.cleanup()

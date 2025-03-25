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

            # Execute based on action type
            if action_type == "click":
                return self._execute_click(coordinates, target)

            elif action_type == "long_click":
                return self._execute_long_click(coordinates, target)

            elif action_type in ["scroll", "scroll_up", "scroll_down", "scroll_left", "scroll_right"]:
                direction = params.get("direction", action_type.split("_")[1] if "_" in action_type else "DOWN")
                return self._execute_scroll(coordinates, target, direction)

            elif action_type == "set_text":
                text = params.get("text", "")
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

        action_type = action_type_map.get(action.event, "click")

        # Create action dictionary
        action_dict = {
            "action_type": action_type,
            "target": target,
            "coordinates": coordinates,
            "params": {}
        }

        # Add specific parameters based on action type
        if action_type == "set_text":
            action_dict["params"]["text"] = "test input"
        elif action_type == "key_event":
            action_dict["params"]["name"] = "BACK"
        elif action_type == "scroll":
            action_dict["params"]["direction"] = "DOWN"

        return self.execute_action(action_dict)

    def execute_actions_from_screen(self, screen: ScreenDescription) -> List[Tuple[ItemAction, bool]]:
        """
        Execute a series of actions from a screen description.

        Args:
            screen: Screen description with UI elements and actions

        Returns:
            List of tuples containing (action, success_status)
        """
        results = []

        for item in screen.items:
            for action in item.actions:
                success = self.execute_item_action(action)
                results.append((action, success))

                # Get updated UI state after each action
                try:
                    self.adapter.get_ui_state(force_refresh=True)
                except:
                    pass

                # Small delay between actions
                import time
                time.sleep(1)

        return results

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
       
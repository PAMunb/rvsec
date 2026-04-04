"""
Action executor for UIAutomator framework.

This module provides action execution capabilities using UIAutomator,
translating GeneratedAction objects into device interactions.
"""


from rv_android_core.domain.widget import WidgetEventType
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

from ..adapter.base import UIAdapter


class UIAutomatorActionExecutor:
    """
    Executes test actions using UIAutomator framework.

    ### Architectural Decisions:
    - Translates GeneratedAction objects to UIAutomator commands
    - Handles all WidgetEventType actions consistently
    - Supports custom coordinate-based actions from vision strategy
    - Implements action delays for UI stabilization

    ### Role in the System:
    - Bridge between LLM-generated actions and device execution
    - Provides reliable action execution with error recovery
    - Handles both standard UI actions and coordinate-based actions
    - Ensures consistent execution across different action types
    """

    def __init__(self):
        """Initialize action executor with logging."""
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_uiautomator.executor", {CONTEXT_COMPONENT: "UIAutomatorActionExecutor"}
        )

        self.logger.debug("UIAutomatorActionExecutor initialized")

    @ErrorHandler.handle_errors(
        component="UIAutomatorActionExecutor", phase="action_execution"
    )
    def execute(self, action, ui_adapter: UIAdapter) -> bool:
        """
        Execute action on device through UIAutomator.

        Args:
            action: Generated action to execute (GeneratedAction object)
            ui_adapter: UIAutomator adapter instance

        Returns:
            True if execution successful, False otherwise
        """
        if not action or not ui_adapter:
            self.logger.warning("Invalid action or adapter provided")
            return False

        try:
            action_type = action.action_type.lower()
            self.logger.info(f"Executing action: {action.text} ({action_type})")

            # Standard UI element actions
            if action_type == WidgetEventType.CLICK.name.lower():
                return self._execute_click(action, ui_adapter)

            elif action_type == WidgetEventType.TEXT_CHANGE.name.lower():
                return self._execute_text_change(action, ui_adapter)

            elif action_type == WidgetEventType.LONG_CLICK.name.lower():
                return self._execute_long_click(action, ui_adapter)

            elif action_type == WidgetEventType.SCROLL.name.lower():
                return self._execute_scroll(action, ui_adapter)

            # System actions
            elif action_type == WidgetEventType.BACK.name.lower():
                return ui_adapter.press_back()

            # Custom coordinate actions (from vision strategy)
            elif hasattr(action, "is_custom") and action.is_custom:
                self.logger.info(
                    f"Executing custom coordinate action at {action.coordinates}"
                )
                return ui_adapter.click(action.coordinates[0], action.coordinates[1])

            else:
                self.logger.warning(f"Unsupported action type: {action_type}")
                return False

        except Exception as e:
            self.logger.error(f"Action execution failed: {e}")
            return False

    def _execute_click(self, action, ui_adapter: UIAdapter) -> bool:
        """Execute click action at specified coordinates."""
        try:
            if not hasattr(action, "coordinates") or not action.coordinates:
                self.logger.error("Click action missing coordinates")
                return False

            x, y = action.coordinates[0], action.coordinates[1]
            success = ui_adapter.click(x, y)

            if success:
                self.logger.debug(f"Click executed at ({x}, {y})")
            else:
                self.logger.warning(f"Click failed at ({x}, {y})")

            return success

        except Exception as e:
            self.logger.error(f"Click execution error: {e}")
            return False

    def _execute_text_change(self, action, ui_adapter: UIAdapter) -> bool:
        """Execute text input action."""
        try:
            # First click on the field if coordinates are available
            if hasattr(action, "coordinates") and action.coordinates:
                x, y = action.coordinates[0], action.coordinates[1]
                if not ui_adapter.click(x, y):
                    self.logger.warning(f"Failed to click on text field at ({x}, {y})")
                    return False

            # Get text from action parameters
            text = ""
            if hasattr(action, "params") and action.params and "text" in action.params:
                text = action.params["text"]
            elif hasattr(action, "text_value") and action.text_value:
                text = action.text_value
            else:
                self.logger.error("Text change action missing text content")
                return False

            # Input the text
            success = ui_adapter.input_text(text)

            if success:
                self.logger.debug(f"Text input executed: '{text}'")
            else:
                self.logger.warning(f"Text input failed: '{text}'")

            return success

        except Exception as e:
            self.logger.error(f"Text change execution error: {e}")
            return False

    def _execute_long_click(self, action, ui_adapter: UIAdapter) -> bool:
        """Execute long click action."""
        try:
            if not hasattr(action, "coordinates") or not action.coordinates:
                self.logger.error("Long click action missing coordinates")
                return False

            x, y = action.coordinates[0], action.coordinates[1]

            # Get duration from parameters or use default
            duration = 1.0
            if (
                hasattr(action, "params")
                and action.params
                and "duration" in action.params
            ):
                duration = float(action.params["duration"])

            success = ui_adapter.long_click(x, y, duration)

            if success:
                self.logger.debug(f"Long click executed at ({x}, {y}) for {duration}s")
            else:
                self.logger.warning(f"Long click failed at ({x}, {y})")

            return success

        except Exception as e:
            self.logger.error(f"Long click execution error: {e}")
            return False

    def _execute_scroll(self, action, ui_adapter: UIAdapter) -> bool:
        """Execute scroll action."""
        try:
            if not hasattr(action, "coordinates") or not action.coordinates:
                self.logger.error("Scroll action missing coordinates")
                return False

            x, y = action.coordinates[0], action.coordinates[1]

            # Get scroll direction and distance from parameters
            direction = "down"
            distance = 300

            if hasattr(action, "params") and action.params:
                direction = action.params.get("direction", "down")
                distance = action.params.get("distance", 300)

            # Calculate end coordinates based on direction
            if direction == "down":
                x2, y2 = x, y + distance
            elif direction == "up":
                x2, y2 = x, y - distance
            elif direction == "left":
                x2, y2 = x - distance, y
            elif direction == "right":
                x2, y2 = x + distance, y
            else:
                self.logger.error(f"Unknown scroll direction: {direction}")
                return False

            success = ui_adapter.swipe(x, y, x2, y2, 0.5)

            if success:
                self.logger.debug(f"Scroll executed from ({x}, {y}) to ({x2}, {y2})")
            else:
                self.logger.warning(
                    f"Scroll failed from ({x}, {y}) direction {direction}"
                )

            return success

        except Exception as e:
            self.logger.error(f"Scroll execution error: {e}")
            return False

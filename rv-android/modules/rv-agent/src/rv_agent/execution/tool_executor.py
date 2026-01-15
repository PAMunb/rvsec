"""
Tool execution for RVAgent actions.

Executes unified-format actions on Android devices via DeviceInterface.
"""

import logging
from typing import Dict, Any, Optional

from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.domain.exceptions import DeviceError
from rv_agent.services.vision_service import ImageHandler


class ToolExecutor:
    """
    Executes actions on Android device via DeviceInterface.

    Receives actions in unified format (from ActionNormalizer) and delegates
    execution to the appropriate DeviceInterface method.

    ### Architectural Decisions:
    - Expects unified action format with device-space coordinates
    - Delegates all device interaction to DeviceInterface
    - Raises DeviceError on execution failures
    - Stateless execution with no action history

    ### Role in the System:
    - Bridges action decisions to device execution
    - Provides consistent action execution interface
    - Maps action types to DeviceInterface methods
    - Reports execution results to caller

    ### Action Format:
    - action_type: CLICK, SET_TEXT, BACK, SCROLL, etc.
    - x, y: Coordinates in device space (already converted)
    - text: For SET_TEXT actions
    - source: "llm" or "algorithm" (for metrics)
    """

    def __init__(
        self,
        device: DeviceInterface,
        image_handler: Optional[ImageHandler] = None
    ):
        """
        Initialize tool executor.

        Args:
            device: Device interface for action execution
            image_handler: Optional image handler for screenshots
        """
        self.device = device
        self.image_handler = image_handler
        self.logger = logging.getLogger(__name__)

        self.logger.info("ToolExecutor initialized")

    def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute action on device.

        Actions must be in unified format (from ActionNormalizer):
        {"action_type": "CLICK", "x": 540, "y": 383, "source": "llm"|"algorithm"}

        Coordinates are expected to already be in device space.

        Args:
            action: Action dictionary in unified format

        Returns:
            Result dictionary with:
            - success: Whether action executed successfully
            - action_executed: Copy of executed action
            - error: Error message if failed
        """
        action_type = action.get("action_type", "UNKNOWN")

        self.logger.info(f"Executing action: {action_type} (source={action.get('source', 'unknown')})")

        try:
            if action_type == "CLICK":
                result = self._execute_click(action)
            elif action_type == "LONG_CLICK":
                result = self._execute_long_click(action)
            elif action_type == "SET_TEXT":
                result = self._execute_type_text(action)
            elif action_type == "SWIPE":
                result = self._execute_swipe(action)
            elif action_type == "SCROLL":
                result = self._execute_scroll(action)
            elif action_type in ("SCROLL_UP", "SCROLL_DOWN", "SCROLL_LEFT", "SCROLL_RIGHT"):
                result = self._execute_directional_scroll(action_type)
            elif action_type == "BACK":
                result = self._execute_back()
            elif action_type == "SYSTEM_BACK":
                result = self._execute_back()
            elif action_type == "HOME":
                result = self._execute_home()
            elif action_type == "PRESS_ENTER":
                result = self._execute_press_enter()
            elif action_type == "RESTART_APP":
                result = self._execute_restart(action)
            else:
                self.logger.warning(f"Unknown action type: {action_type}")
                result = {
                    "success": False,
                    "error": f"Unknown action type: {action_type}"
                }

            result["action_executed"] = action
            return result

        except DeviceError:
            raise
        except Exception as e:
            self.logger.error(f"Action execution failed: {e}", exc_info=True)
            raise DeviceError(f"Action execution failed: {e}") from e

    def _execute_click(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute click action."""
        x = action.get("x", 0)
        y = action.get("y", 0)

        self.device.click(x, y)
        self.logger.debug(f"Clicked at ({x}, {y})")

        return {"success": True}

    def _execute_long_click(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute long click action."""
        x = action.get("x", 0)
        y = action.get("y", 0)

        self.device.long_click(x, y)
        self.logger.debug(f"Long clicked at ({x}, {y})")

        return {"success": True}

    def _execute_type_text(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute type text action."""
        x = action.get("x", 0)
        y = action.get("y", 0)
        text = action.get("text", "")

        if not text:
            self.logger.warning("SET_TEXT action with no text")
            return {
                "success": False,
                "error": "No text provided for SET_TEXT"
            }

        self.device.click(x, y)
        self.device.input_text(text)
        self.logger.debug(f"Typed '{text}' at ({x}, {y})")

        return {"success": True}

    def _execute_scroll(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute scroll action with specific coordinates or direction."""
        # Try to use specific swipe coordinates if available
        swipe_start = action.get("swipe_start")
        swipe_end = action.get("swipe_end")

        if swipe_start and swipe_end:
            start_x, start_y = swipe_start
            end_x, end_y = swipe_end
            self.device.swipe(start_x, start_y, end_x, end_y)
            self.logger.debug(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")
        else:
            # Fallback to direction-based scroll
            direction = action.get("direction", "down")
            self.device.scroll(direction, "medium")
            self.logger.debug(f"Scrolled {direction}")

        return {"success": True}

    def _execute_swipe(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute swipe action."""
        direction = action.get("direction", "up")
        distance = action.get("distance", "medium")

        self.device.scroll(direction, distance)
        self.logger.debug(f"Swiped {direction} ({distance})")

        return {"success": True}

    def _execute_directional_scroll(self, action_type: str) -> Dict[str, Any]:
        """Execute directional scroll action."""
        direction_map = {
            "SCROLL_UP": "up",
            "SCROLL_DOWN": "down",
            "SCROLL_LEFT": "left",
            "SCROLL_RIGHT": "right"
        }

        direction = direction_map.get(action_type, "down")
        self.device.scroll(direction, "medium")
        self.logger.debug(f"Scrolled {direction}")

        return {"success": True}

    def _execute_back(self) -> Dict[str, Any]:
        """Execute back action."""
        self.device.back()
        self.logger.debug("Pressed BACK")

        return {"success": True}

    def _execute_home(self) -> Dict[str, Any]:
        """Execute home action."""
        self.device.home()
        self.logger.debug("Pressed HOME")

        return {"success": True}

    def _execute_press_enter(self) -> Dict[str, Any]:
        """Execute ENTER key press action."""
        self.device.press_keycode(66)
        self.logger.debug("Pressed ENTER key")

        return {"success": True}

    def _execute_restart(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute app restart action."""
        package = action.get("package_name")

        if not package:
            self.logger.warning("RESTART_APP action with no package name")
            return {
                "success": False,
                "error": "No package name provided for RESTART_APP"
            }

        self.device.stop_app(package)
        self.device.start_app(package)
        self.logger.debug(f"Restarted app: {package}")

        return {"success": True}

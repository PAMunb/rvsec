"""
Tool execution for RVAgent actions.

Executes unified-format actions on Android devices via DeviceInterface.
"""

import logging
from typing import Any, Dict, Optional

from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.domain.exceptions import DeviceError
from rv_agent.services.vision_service import ImageHandler


class ToolExecutor:
    """
    Execute actions on Android device via DeviceInterface.

    Receive actions in unified format (from ActionNormalizer) and delegate
    execution to the appropriate DeviceInterface method. Each action dict
    contains action_type, device-space coordinates (x, y), optional text,
    and a source tag ("llm" or "algorithm") for metrics tracking.

    ### Architectural Decisions:
    - Expects unified action format with device-space coordinates
      (already converted from Qwen3-VL [0, 1000) by ActionNormalizer)
    - Delegates all device interaction to DeviceInterface
    - Wraps non-DeviceError exceptions into DeviceError for uniform
      error handling upstream
    - Stateless execution with no action history

    ### Role in the System:
    - Bridges action decisions (from algorithm_node or llm_node) to
      device execution via DeviceInterface
    - Maps action_type strings to specific DeviceInterface methods
    - Returns success/failure result dicts consumed by execute_node
    """

    def __init__(
        self, device: DeviceInterface, image_handler: Optional[ImageHandler] = None
    ):
        """Initialize tool executor.

        Args:
            device: Device interface for action execution.
            image_handler: Optional image handler for screenshots.

        State:
            self.device: DeviceInterface used for all device operations.
            self.image_handler: Optional ImageHandler, currently unused
                by execute_action but available for screenshot capture.
        """
        self.device = device
        self.image_handler = image_handler
        self.logger = logging.getLogger(__name__)

        self.logger.info("ToolExecutor initialized")

    def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action on device.

        Actions must be in unified format (from ActionNormalizer):
        {"action_type": "CLICK", "x": 540, "y": 383, "source": "llm"|"algorithm"}

        Coordinates are expected to already be in device space.

        Args:
            action: Action dictionary in unified format.

        Returns:
            Dictionary with keys:
            - "success" (bool): Whether action executed successfully.
            - "action_executed" (dict): Copy of the executed action dict.
            - "error" (str): Error message, present only on failure.

        Raises:
            DeviceError: When the underlying device operation fails or
                when an unexpected exception occurs during execution.
        """
        action_type = action.get("action_type", "UNKNOWN")

        self.logger.info(
            f"Executing action: {action_type} (source={action.get('source', 'unknown')})"
        )

        try:
            if action_type == "CLICK":
                result = self._execute_click(action)
            elif action_type == "LONG_CLICK":
                result = self._execute_long_click(action)
            elif action_type == "SET_TEXT":
                result = self._execute_type_text(action)
            elif action_type == "SWIPE":
                result = self._execute_swipe(action)
            elif action_type == "DRAG":
                result = self._execute_drag(action)
            elif action_type == "SCROLL":
                result = self._execute_scroll(action)
            elif action_type in (
                "SCROLL_UP",
                "SCROLL_DOWN",
                "SCROLL_LEFT",
                "SCROLL_RIGHT",
            ):
                result = self._execute_directional_scroll(action_type)
            elif action_type == "BACK":
                result = self._execute_back()
            elif action_type == "SYSTEM_BACK":
                result = self._execute_back()
            elif action_type == "KEY_EVENT":
                # KEY_EVENT is how BACK actions come through via WidgetEventType mapping
                result = self._execute_back()
            elif action_type == "HOME":
                result = self._execute_home()
            elif action_type == "PRESS_ENTER":
                result = self._execute_press_enter()
            elif action_type in ("RESTART_APP", "RESTART"):
                result = self._execute_restart(action)
            else:
                self.logger.warning(f"Unknown action type: {action_type}")
                result = {
                    "success": False,
                    "error": f"Unknown action type: {action_type}",
                }

            result["action_executed"] = action
            return result

        except DeviceError:
            raise
        except Exception as e:
            self.logger.error(f"Action execution failed: {e}", exc_info=True)
            raise DeviceError(f"Action execution failed: {e}") from e

    def _execute_click(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute click action. Propagates device return value."""
        x = action.get("x", 0)
        y = action.get("y", 0)

        success = self.device.click(x, y)
        self.logger.debug(f"Clicked at ({x}, {y}), success={success}")

        # DeviceInterface methods return None when the backend does not
        # report success/failure (e.g., UIAutomator2 click). Treat None
        # as success to avoid false negatives. This pattern is used by
        # all _execute_* methods.
        return {"success": bool(success) if success is not None else True}

    def _execute_long_click(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute long click action. Propagates device return value."""
        x = action.get("x", 0)
        y = action.get("y", 0)

        success = self.device.long_click(x, y)
        self.logger.debug(f"Long clicked at ({x}, {y}), success={success}")

        return {"success": bool(success) if success is not None else True}

    def _execute_type_text(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute type text action with click-clear-type sequence.

        Args:
            action: Action dict with "x", "y" coordinates and "text" value.

        Returns:
            Dictionary with "success" bool. Fails if text is empty or
            if the click on the target field fails.
        """
        x = action.get("x", 0)
        y = action.get("y", 0)
        text = action.get("text", "")

        if not text:
            self.logger.warning("SET_TEXT action with no text")
            return {"success": False, "error": "No text provided for SET_TEXT"}

        click_ok = self.device.click(x, y)
        self.device.clear_text()
        input_ok = self.device.input_text(text)
        self.logger.debug(f"Typed '{text}' at ({x}, {y})")

        # Success requires at least the click to work; input_text may return None
        success = bool(click_ok) if click_ok is not None else True
        if input_ok is not None:
            success = success and bool(input_ok)

        return {"success": success}

    def _execute_scroll(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute scroll action using swipe coordinates or direction fallback.

        Args:
            action: Action dict. If "swipe_start" and "swipe_end" tuples
                are present, uses precise coordinate-based swipe. Otherwise
                falls back to direction-based scroll ("direction" key,
                defaults to "down").

        Returns:
            Dictionary with "success" bool.
        """
        # Try to use specific swipe coordinates if available
        swipe_start = action.get("swipe_start")
        swipe_end = action.get("swipe_end")

        if swipe_start and swipe_end:
            start_x, start_y = swipe_start
            end_x, end_y = swipe_end
            success = self.device.swipe(start_x, start_y, end_x, end_y)
            self.logger.debug(
                f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})"
            )
        else:
            # Fallback to direction-based scroll
            direction = action.get("direction", "down")
            success = self.device.scroll(direction, "medium")
            self.logger.debug(f"Scrolled {direction}")

        return {"success": bool(success) if success is not None else True}

    def _execute_swipe(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute swipe action (direction-based). Propagates device return value."""
        direction = action.get("direction", "up")
        distance = action.get("distance", "medium")

        success = self.device.scroll(direction, distance)
        self.logger.debug(f"Swiped {direction} ({distance})")

        return {"success": bool(success) if success is not None else True}

    def _execute_drag(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute drag action between two coordinate pairs.

        Used for SeekBar, sliders, and similar drag-target widgets.

        Args:
            action: Action dict requiring "swipe_start" and "swipe_end"
                coordinate tuples. Returns failure if either is missing.

        Returns:
            Dictionary with "success" bool, or "error" if coordinates
            are missing.
        """
        swipe_start = action.get("swipe_start")
        swipe_end = action.get("swipe_end")

        if not swipe_start or not swipe_end:
            self.logger.warning(
                "DRAG action missing swipe_start or swipe_end coordinates"
            )
            return {
                "success": False,
                "error": "DRAG requires swipe_start and swipe_end coordinates",
            }

        start_x, start_y = swipe_start
        end_x, end_y = swipe_end

        success = self.device.swipe(start_x, start_y, end_x, end_y)
        self.logger.debug(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")

        return {"success": bool(success) if success is not None else True}

    def _execute_directional_scroll(self, action_type: str) -> Dict[str, Any]:
        """Execute directional scroll from action_type name.

        Args:
            action_type: One of SCROLL_UP, SCROLL_DOWN, SCROLL_LEFT,
                SCROLL_RIGHT. Defaults to "down" if unrecognized.

        Returns:
            Dictionary with "success" bool.
        """
        direction_map = {
            "SCROLL_UP": "up",
            "SCROLL_DOWN": "down",
            "SCROLL_LEFT": "left",
            "SCROLL_RIGHT": "right",
        }

        direction = direction_map.get(action_type, "down")
        success = self.device.scroll(direction, "medium")
        self.logger.debug(f"Scrolled {direction}")

        return {"success": bool(success) if success is not None else True}

    def _execute_back(self) -> Dict[str, Any]:
        """Execute back action. Propagates device return value."""
        success = self.device.back()
        self.logger.debug("Pressed BACK")

        return {"success": bool(success) if success is not None else True}

    def _execute_home(self) -> Dict[str, Any]:
        """Execute home action. Propagates device return value."""
        success = self.device.home()
        self.logger.debug("Pressed HOME")

        return {"success": bool(success) if success is not None else True}

    def _execute_press_enter(self) -> Dict[str, Any]:
        """Execute ENTER key press action. Propagates device return value."""
        success = self.device.press_keycode(66)
        self.logger.debug("Pressed ENTER key")

        return {"success": bool(success) if success is not None else True}

    def _execute_restart(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute app restart by stopping and re-launching the package.

        Falls back to device config package_name when the action dict
        does not include package_name explicitly.

        Args:
            action: Action dict with optional "package_name". If missing,
                falls back to device.config.package_name.

        Returns:
            Dictionary with "success" bool. Fails if no package name
            can be resolved from either source.
        """
        package = action.get("package_name")

        if not package:
            # Fallback to device config — prevents silent failure when
            # package_name is missing from the action dict
            device_config = getattr(self.device, "config", None)
            if device_config:
                package = getattr(device_config, "package_name", None)

        if not package:
            self.logger.warning(
                "RESTART_APP action with no package name and no fallback"
            )
            return {
                "success": False,
                "error": "No package name provided for RESTART_APP",
            }

        stop_ok = self.device.stop_app(package)
        start_ok = self.device.start_app(package)
        self.logger.debug(f"Restarted app: {package}")

        # Success requires start to work; stop may return None on some backends
        success = bool(start_ok) if start_ok is not None else True

        return {"success": success}

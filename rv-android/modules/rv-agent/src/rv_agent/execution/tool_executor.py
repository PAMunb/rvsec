"""
Tool execution management for agent actions.

Executes actions on Android device via DeviceInterface with proper
error handling and result reporting.
"""

import logging
from typing import Dict, Any, Optional

from rv_agent.core.device_interface import DeviceInterface
from rv_agent.vision.image_handler import ImageHandler


class ToolExecutor:
    """
    Executes actions on Android device.

    ### Architectural Decisions:
    - Delegates to DeviceInterface for actual execution
    - Provides unified interface for all action types
    - Handles coordinate conversion from optimized to device space
    - Implements error handling with detailed reporting
    - Captures screenshots after actions when needed

    ### Role in the System:
    - Executes LLM-generated and algorithmic actions
    - Bridges agent decisions to device operations
    - Provides execution results for state updates
    - Manages action timing and error recovery

    ### Integration Points:
    - Used by RVAgent execute_tools node
    - Calls DeviceInterface for actual execution
    - Uses ImageHandler for screenshot management
    - Reports results to agent state
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

        # Get device screen size and calculate coordinate conversion factors
        self.device_size = self._get_device_size()

        # Get optimized image size from image handler or use default
        if image_handler:
            self.optimized_size = image_handler.target_size
        else:
            self.optimized_size = (704, 1248)  # Default for Qwen3-VL

        # Calculate scale factors for coordinate conversion
        self.scale_x = self.device_size[0] / self.optimized_size[0]
        self.scale_y = self.device_size[1] / self.optimized_size[1]

        self.logger.info(
            f"ToolExecutor initialized: device={self.device_size}, "
            f"optimized={self.optimized_size}, scale=({self.scale_x:.3f}, {self.scale_y:.3f})"
        )

    # Tool name mapping (LLM format → internal format)
    TOOL_NAME_TO_ACTION_TYPE = {
        "android_click": "CLICK",
        "android_type_text": "TYPE_TEXT",
        "android_long_click": "LONG_CLICK",
        "android_swipe": "SWIPE",
        "android_scroll": "SCROLL",
        "android_back": "BACK",
        "android_home": "HOME",
        "android_press_enter": "PRESS_ENTER",
        "android_restart": "RESTART_APP"
    }

    def _get_device_size(self) -> tuple:
        """
        Get device screen size from UIAutomator2.

        Returns:
            Tuple of (width, height) in pixels
        """
        try:
            info = self.device.d.info
            size = (info['displayWidth'], info['displayHeight'])
            self.logger.debug(f"Device size: {size}")
            return size
        except Exception as e:
            self.logger.warning(f"Could not get device size, using default 1080x1920: {e}")
            return (1080, 1920)

    def _convert_to_device(self, x: int, y: int) -> tuple:
        """
        Convert coordinates from optimized image space to device space.

        LLM sees optimized screenshots (e.g., 704x1248) but device operates
        in real resolution (e.g., 1080x1920). This method scales coordinates
        appropriately.

        Args:
            x: X coordinate in optimized space
            y: Y coordinate in optimized space

        Returns:
            Tuple of (x, y) in device space
        """
        device_x = int(x * self.scale_x)
        device_y = int(y * self.scale_y)
        return (device_x, device_y)

    def execute_action(
        self,
        action: Dict[str, Any],
        convert_coordinates: bool = True
    ) -> Dict[str, Any]:
        """
        Execute action on device.

        Supports both formats:
        - Algorithm format: {"action_type": "CLICK", "x": 100, "y": 200}
        - LLM format: {"tool_name": "android_click", "tool_args": {"x": 100, "y": 200}}

        Args:
            action: Action dictionary with type and parameters
            convert_coordinates: Whether to convert from optimized to device space

        Returns:
            Result dictionary with:
            - success: Whether action executed successfully
            - action_executed: Copy of executed action
            - error: Error message if failed
        """
        # Normalize LLM format to internal format
        normalized_action = self._normalize_action(action)
        action_type = normalized_action.get("action_type", "UNKNOWN")

        self.logger.info(f"Executing action: {action_type}")

        try:
            if action_type == "CLICK":
                result = self._execute_click(normalized_action, convert_coordinates)
            elif action_type == "LONG_CLICK":
                result = self._execute_long_click(normalized_action, convert_coordinates)
            elif action_type in ("TYPE_TEXT", "SET_TEXT"):
                # SET_TEXT and TYPE_TEXT are synonyms
                result = self._execute_type_text(normalized_action, convert_coordinates)
            elif action_type == "SWIPE":
                result = self._execute_swipe(normalized_action)
            elif action_type == "SCROLL":
                result = self._execute_scroll(normalized_action)
            elif action_type in ("SCROLL_UP", "SCROLL_DOWN", "SCROLL_LEFT", "SCROLL_RIGHT"):
                # Algorithm-specific scroll actions
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
                result = self._execute_restart(normalized_action)
            else:
                self.logger.warning(f"Unknown action type: {action_type}")
                result = {
                    "success": False,
                    "error": f"Unknown action type: {action_type}"
                }

            result["action_executed"] = normalized_action
            return result

        except Exception as e:
            self.logger.error(f"Action execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "action_executed": normalized_action,
                "error": str(e)
            }

    def _normalize_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize action from LLM format to internal format.

        LLM format: {"tool_name": "android_click", "tool_args": {"x": 100, "y": 200}}
        Internal format: {"action_type": "CLICK", "x": 100, "y": 200}

        Args:
            action: Action in either format

        Returns:
            Action in internal format
        """
        # Already in internal format
        if "action_type" in action:
            return action

        # Convert from LLM format
        tool_name = action.get("tool_name", "")
        tool_args = action.get("tool_args", {})

        # Map tool name to action type
        action_type = self.TOOL_NAME_TO_ACTION_TYPE.get(tool_name, "UNKNOWN")

        # Build normalized action
        normalized = {
            "action_type": action_type,
            **tool_args  # Flatten tool_args into action
        }

        self.logger.debug(f"Normalized LLM action: {tool_name} → {action_type}")

        return normalized

    def _execute_click(
        self,
        action: Dict[str, Any],
        convert: bool
    ) -> Dict[str, Any]:
        """Execute click action."""
        x = action.get("x", 0)
        y = action.get("y", 0)

        # Convert coordinates if from LLM (optimized space → device space)
        if convert:
            original_x, original_y = x, y
            x, y = self._convert_to_device(original_x, original_y)
            self.logger.info(
                f"🔄 Coordinate conversion: ({original_x}, {original_y}) OPTIMIZED "
                f"→ ({x}, {y}) DEVICE"
            )

            # Update action with device coordinates for memory recording
            action["x"] = x
            action["y"] = y
        else:
            self.logger.debug(f"Using coordinates as-is (algorithm path): ({x}, {y})")

        self.device.click(x, y)

        self.logger.debug(f"Clicked at ({x}, {y})")

        return {"success": True}

    def _execute_type_text(
        self,
        action: Dict[str, Any],
        convert: bool
    ) -> Dict[str, Any]:
        """Execute type text action."""
        x = action.get("x", 0)
        y = action.get("y", 0)
        text = action.get("text", "")

        if not text:
            self.logger.warning("TYPE_TEXT action with no text")
            return {
                "success": False,
                "error": "No text provided for TYPE_TEXT"
            }

        # Convert coordinates if from LLM (optimized space → device space)
        if convert:
            original_x, original_y = x, y
            x, y = self._convert_to_device(original_x, original_y)
            self.logger.info(
                f"🔄 Coordinate conversion: ({original_x}, {original_y}) OPTIMIZED "
                f"→ ({x}, {y}) DEVICE"
            )

            # Update action with device coordinates for memory recording
            action["x"] = x
            action["y"] = y
        else:
            self.logger.debug(f"Using coordinates as-is (algorithm path): ({x}, {y})")

        # Click on field first
        self.device.click(x, y)

        # Type text
        self.device.input_text(text)

        self.logger.debug(f"Typed '{text}' at ({x}, {y})")

        return {"success": True}

    def _execute_scroll(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute scroll action."""
        direction = action.get("direction", "down")

        self.device.scroll(direction, "medium")

        self.logger.debug(f"Scrolled {direction}")

        return {"success": True}

    def _execute_back(self) -> Dict[str, Any]:
        """Execute back action."""
        self.device.back()

        self.logger.debug("Pressed BACK")

        return {"success": True}

    def _execute_long_click(
        self,
        action: Dict[str, Any],
        convert: bool
    ) -> Dict[str, Any]:
        """Execute long click action."""
        x = action.get("x", 0)
        y = action.get("y", 0)

        # Convert coordinates if from LLM (optimized space → device space)
        if convert:
            original_x, original_y = x, y
            x, y = self._convert_to_device(original_x, original_y)
            self.logger.info(
                f"🔄 Coordinate conversion: ({original_x}, {original_y}) OPTIMIZED "
                f"→ ({x}, {y}) DEVICE"
            )

            # Update action with device coordinates for memory recording
            action["x"] = x
            action["y"] = y
        else:
            self.logger.debug(f"Using coordinates as-is (algorithm path): ({x}, {y})")

        self.device.long_click(x, y)

        self.logger.debug(f"Long clicked at ({x}, {y})")

        return {"success": True}

    def _execute_swipe(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute swipe action (from LLM tools)."""
        direction = action.get("direction", "up")
        distance = action.get("distance", "medium")

        self.device.swipe(direction, distance)

        self.logger.debug(f"Swiped {direction} ({distance})")

        return {"success": True}

    def _execute_directional_scroll(self, action_type: str) -> Dict[str, Any]:
        """Execute directional scroll action (from algorithm)."""
        # Map algorithm scroll types to device swipe direction
        direction_map = {
            "SCROLL_UP": "up",
            "SCROLL_DOWN": "down",
            "SCROLL_LEFT": "left",
            "SCROLL_RIGHT": "right"
        }

        direction = direction_map.get(action_type, "down")
        self.device.swipe(direction, "medium")

        self.logger.debug(f"Scrolled {direction}")

        return {"success": True}

    def _execute_home(self) -> Dict[str, Any]:
        """Execute home action."""
        self.device.home()

        self.logger.debug("Pressed HOME")

        return {"success": True}

    def _execute_press_enter(self) -> Dict[str, Any]:
        """Execute ENTER key press action."""
        # Press ENTER key (keycode 66 in Android)
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

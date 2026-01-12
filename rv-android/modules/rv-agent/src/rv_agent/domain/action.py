"""
Unified action format and normalization for RVAgent.

Converts actions from different sources (LLM, algorithm) to a single format.
Handles coordinate conversion from Qwen3-VL [0, 1000) normalized space to device pixels.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
import logging

from rv_agent.llm.tools.tool_call_parser import denormalize_qwen_coords

logger = logging.getLogger(__name__)

# Tool name to action type mapping
TOOL_TO_ACTION = {
    "android_click": "CLICK",
    "android_type_text": "SET_TEXT",
    "android_long_click": "LONG_CLICK",
    "android_swipe": "SWIPE",
    "android_scroll": "SCROLL",
    "android_back": "BACK",
    "android_home": "HOME",
    "android_press_enter": "PRESS_ENTER",
    "android_restart": "RESTART_APP"
}


@dataclass
class ActionNormalizer:
    """
    Normalizes actions from LLM or algorithm to unified format.

    Converts LLM tool calls to internal action format and handles
    coordinate conversion from Qwen3-VL [0, 1000) normalized space
    to device pixel coordinates.

    Qwen3-VL returns coordinates in a normalized [0, 1000) range,
    independent of input image resolution. This class converts those
    coordinates to actual device pixels.

    Reference: https://github.com/QwenLM/Qwen3-VL/issues/1486

    Unified Action Format:
    - action_type: CLICK, SET_TEXT, BACK, SCROLL, etc.
    - x, y: Device-space pixel coordinates
    - text: For SET_TEXT actions
    - source: "llm" or "algorithm"
    - original_coords: Raw LLM coordinates before conversion (for debugging)
    """

    device_width: int = 1080
    device_height: int = 1920

    def from_llm(self, llm_action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize LLM action to unified format with coordinate conversion.

        Converts Qwen3-VL [0, 1000) normalized coordinates to device pixels.

        Args:
            llm_action: Raw LLM action with tool_name and tool_args

        Returns:
            Normalized action dict or None if invalid
        """
        if not llm_action:
            return None

        tool_name = llm_action.get("tool_name", "")
        tool_args = llm_action.get("tool_args", {})

        action_type = TOOL_TO_ACTION.get(tool_name)
        if not action_type:
            logger.warning(f"Unknown tool name: {tool_name}")
            return None

        # Get raw coordinates from LLM (in [0, 1000) normalized space)
        x_raw = tool_args.get("x", 0)
        y_raw = tool_args.get("y", 0)

        # Convert from [0, 1000) normalized to device pixels
        x_dev, y_dev = denormalize_qwen_coords(
            x_raw, y_raw,
            image_width=self.device_width,
            image_height=self.device_height
        )

        logger.debug(
            f"Coordinate conversion: ({x_raw}, {y_raw}) [0,1000) -> ({x_dev}, {y_dev}) pixels"
        )

        # [DEBUG_NAVBAR] Check if coordinates are in navigation bar area
        navbar_threshold_norm = 950  # ~95% of screen height in [0,1000) space
        navbar_threshold_px = int(self.device_height * 0.95)
        is_navbar_area = y_raw > navbar_threshold_norm or y_dev > navbar_threshold_px

        logger.info(
            f"[DEBUG_NAVBAR] LLM coords: raw=({x_raw}, {y_raw}) -> pixels=({x_dev}, {y_dev}) "
            f"| device={self.device_width}x{self.device_height} "
            f"| NAVBAR={'YES' if is_navbar_area else 'no'}"
        )

        return {
            "action_type": action_type,
            "x": x_dev,
            "y": y_dev,
            "text": tool_args.get("text", ""),
            "direction": tool_args.get("direction", ""),
            "source": "llm",
            "original_coords": (x_raw, y_raw),
        }

    def from_algorithm(self, algo_action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Add source field to algorithm actions.

        Algorithm actions already use device pixel coordinates,
        so no conversion is needed.

        Args:
            algo_action: Algorithm action dict with device coordinates

        Returns:
            Action with source field added or None if invalid
        """
        if not algo_action or not algo_action.get("action_type"):
            return None

        return {
            **algo_action,
            "source": "algorithm",
        }

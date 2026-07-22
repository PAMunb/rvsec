"""
Unified action format and normalization for RVAgent.

Converts actions from different sources (LLM, algorithm) to a single format.
Handles coordinate conversion from Qwen3-VL [0, 1000) normalized space to device pixels.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from rv_agent.llm.tools.tool_call_parser import denormalize_qwen_coords

logger = logging.getLogger(__name__)

# Tool name to action type mapping
TOOL_TO_ACTION = {
    "android_click": "CLICK",
    "android_type_text": "SET_TEXT",
    "android_long_click": "LONG_CLICK",
    "android_swipe": "SWIPE",
    "android_drag": "DRAG",
    "android_scroll": "SCROLL",
    "android_back": "BACK",
    "android_home": "HOME",
    "android_press_enter": "PRESS_ENTER",
    "android_restart": "RESTART_APP",
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

        # Handle DRAG action separately (has start/end coordinates)
        if action_type == "DRAG":
            return self._normalize_drag_action(tool_args)

        # Get raw coordinates from LLM (in [0, 1000) normalized space)
        x_raw = tool_args.get("x", 0)
        y_raw = tool_args.get("y", 0)

        # Ensure coordinates are numeric (LLM may return strings)
        if isinstance(x_raw, str):
            try:
                x_raw = float(x_raw)
            except (ValueError, TypeError):
                x_raw = 0
        if isinstance(y_raw, str):
            try:
                y_raw = float(y_raw)
            except (ValueError, TypeError):
                y_raw = 0

        # Convert from [0, 1000) normalized to device pixels
        x_dev, y_dev = denormalize_qwen_coords(
            x_raw, y_raw, image_width=self.device_width, image_height=self.device_height
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

    def _normalize_drag_action(self, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize DRAG action with start/end coordinates.

        Args:
            tool_args: Tool arguments with start_x, start_y, end_x, end_y

        Returns:
            Normalized DRAG action with swipe_start and swipe_end
        """
        # Get raw coordinates
        start_x_raw = tool_args.get("start_x", 0)
        start_y_raw = tool_args.get("start_y", 0)
        end_x_raw = tool_args.get("end_x", 0)
        end_y_raw = tool_args.get("end_y", 0)

        # Convert from [0, 1000) normalized to device pixels
        start_x, start_y = denormalize_qwen_coords(
            start_x_raw,
            start_y_raw,
            image_width=self.device_width,
            image_height=self.device_height,
        )
        end_x, end_y = denormalize_qwen_coords(
            end_x_raw,
            end_y_raw,
            image_width=self.device_width,
            image_height=self.device_height,
        )

        logger.info(
            f"[DRAG] Normalized: ({start_x_raw},{start_y_raw})->({end_x_raw},{end_y_raw}) "
            f"to pixels ({start_x},{start_y})->({end_x},{end_y})"
        )

        return {
            "action_type": "DRAG",
            "x": start_x,  # Use start as primary coordinate
            "y": start_y,
            "swipe_start": (start_x, start_y),
            "swipe_end": (end_x, end_y),
            "source": "llm",
            "original_coords": (start_x_raw, start_y_raw),
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

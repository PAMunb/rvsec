"""
Unified action format and normalization for RVAgent.

Converts actions from different sources (LLM, algorithm) to a single format.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
import logging

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
    coordinate conversion from optimized screenshot space to device space.

    ### Architectural Decisions:
    - Normalizes at source (LLM node, algorithm node)
    - Converts coordinates from optimized (704x1248) to device (1080x1920)
    - Preserves original coordinates for debugging
    - Adds source field for metrics tracking

    ### Role in the System:
    - Provides single action format for validation and execution
    - Eliminates format checking in downstream components
    - Centralizes coordinate conversion logic
    - Enables consistent loop detection

    ### Unified Action Format:
    - action_type: CLICK, SET_TEXT, BACK, SCROLL, etc.
    - x, y: Device-space coordinates
    - text: For SET_TEXT actions
    - source: "llm" or "algorithm"
    - original_coords: LLM coordinates before conversion (debug)
    """

    device_size: Tuple[int, int] = (1080, 1920)
    optimized_size: Tuple[int, int] = (704, 1248)

    @property
    def scale_x(self) -> float:
        """Scale factor for X coordinate conversion."""
        return self.device_size[0] / self.optimized_size[0]

    @property
    def scale_y(self) -> float:
        """Scale factor for Y coordinate conversion."""
        return self.device_size[1] / self.optimized_size[1]

    def from_llm(self, llm_action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize LLM action to unified format with coordinate conversion.

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

        # Convert coordinates from optimized to device space
        x_opt = tool_args.get("x", 0)
        y_opt = tool_args.get("y", 0)
        x_dev = int(x_opt * self.scale_x)
        y_dev = int(y_opt * self.scale_y)

        logger.debug(
            f"Coordinate conversion: ({x_opt}, {y_opt}) -> ({x_dev}, {y_dev})"
        )

        return {
            "action_type": action_type,
            "x": x_dev,
            "y": y_dev,
            "text": tool_args.get("text", ""),
            "direction": tool_args.get("direction", ""),
            "source": "llm",
            "original_coords": (x_opt, y_opt),
        }

    def from_algorithm(self, algo_action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Add source field to algorithm actions.

        Args:
            algo_action: Algorithm action dict

        Returns:
            Action with source field added or None if invalid
        """
        if not algo_action or not algo_action.get("action_type"):
            return None

        return {
            **algo_action,
            "source": "algorithm",
        }

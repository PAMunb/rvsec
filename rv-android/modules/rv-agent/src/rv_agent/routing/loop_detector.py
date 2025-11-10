"""
Loop detection for repetitive action sequences.

Detects when agent is repeating the same actions consecutively,
which indicates potential loops that should trigger fallback.
"""

import logging
from typing import List, Dict, Any

from rv_agent.config.agent_config import RVAgentConfig


class LoopDetector:
    """
    Detects repetitive action loops during exploration.

    ### Architectural Decisions:
    - Tracks recent action window for pattern detection
    - Uses action type and coordinate-based similarity
    - Configurable thresholds per action type
    - Supports coordinate tolerance for click actions
    - Provides clear loop detection signals

    ### Role in the System:
    - Identifies when agent is stuck in loops
    - Triggers fallback to algorithmic exploration
    - Prevents infinite repetitive behaviors
    - Maintains action history window

    ### Integration Points:
    - Used by RoutingManager for validation
    - Receives action history from agent memory
    - Provides loop detection signals to routing logic
    - Configurable via RVAgentConfig thresholds
    """

    COORDINATE_TOLERANCE = 20  # pixels

    def __init__(self, config: RVAgentConfig):
        """
        Initialize loop detector.

        Args:
            config: Agent configuration with loop thresholds
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    def detect_loop(
        self,
        recent_actions: List[Dict[str, Any]],
        current_action: Dict[str, Any]
    ) -> tuple[bool, int, int]:
        """
        Detect if current action would create a loop.

        Args:
            recent_actions: Recent action history window
            current_action: Current action to check

        Returns:
            Tuple of (is_loop, consecutive_count, threshold)
        """
        action_type = current_action.get("action_type", "UNKNOWN")

        # Count consecutive similar actions
        consecutive_count = self._count_consecutive_actions(
            recent_actions,
            current_action
        )

        # Get threshold for this action type
        threshold = self.config.get_loop_threshold(action_type)

        # Detect loop
        is_loop = consecutive_count >= threshold

        if is_loop:
            self.logger.warning(
                f"Loop detected: {action_type} repeated {consecutive_count}x "
                f"(threshold={threshold})"
            )
        else:
            self.logger.debug(
                f"Loop check: {action_type} count={consecutive_count} "
                f"(threshold={threshold})"
            )

        return is_loop, consecutive_count, threshold

    def _count_consecutive_actions(
        self,
        recent: List[Dict[str, Any]],
        current: Dict[str, Any]
    ) -> int:
        """
        Count consecutive occurrences of action in recent history.

        Iterates backwards through recent actions, counting matches
        until a different action is found.

        Args:
            recent: List of recent actions
            current: Current action to check

        Returns:
            Number of consecutive repetitions
        """
        count = 0
        for action in reversed(recent):
            if self._actions_are_similar(action, current):
                count += 1
            else:
                break
        return count

    def _actions_are_similar(
        self,
        a1: Dict[str, Any],
        a2: Dict[str, Any]
    ) -> bool:
        """
        Check if two actions are similar for loop detection.

        Comparison rules:
        - Different types → not similar
        - TYPE_TEXT: compare text content
        - CLICK: compare coordinates (tolerance-based)
        - Others: type match is sufficient

        Args:
            a1: First action
            a2: Second action

        Returns:
            True if actions are similar
        """
        type1 = a1.get("action_type")
        type2 = a2.get("action_type")

        if type1 != type2:
            return False

        # TYPE_TEXT: compare text
        if type1 == "TYPE_TEXT":
            return a1.get("text") == a2.get("text")

        # CLICK: compare coordinates with tolerance
        if type1 == "CLICK":
            x1, y1 = a1.get("x", 0), a1.get("y", 0)
            x2, y2 = a2.get("x", 0), a2.get("y", 0)
            return (
                abs(x1 - x2) < self.COORDINATE_TOLERANCE and
                abs(y1 - y2) < self.COORDINATE_TOLERANCE
            )

        # Others: type match sufficient
        return True

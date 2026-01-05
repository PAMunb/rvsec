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
    SPATIAL_LOOP_RADIUS = 50  # pixels for spatial loop detection
    SPATIAL_LOOP_WINDOW = 3  # number of recent CLICK actions to check

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
        - SET_TEXT: compare text content
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

        # SET_TEXT: compare text
        if type1 == "SET_TEXT":
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

    def detect_spatial_loop(
        self,
        recent_actions: List[Dict[str, Any]]
    ) -> bool:
        """
        Detect if recent CLICK actions are clustered in a small spatial area.

        This detects when the agent is clicking repeatedly in the same region,
        which often indicates the agent is stuck trying the same element multiple
        times without making progress.

        Args:
            recent_actions: Recent action history window

        Returns:
            True if spatial loop detected (last 3 CLICKs within 50px radius)
        """
        # Filter only CLICK actions from recent history
        recent_clicks = [
            action for action in recent_actions
            if action.get("action_type") == "CLICK"
        ]

        # Need at least SPATIAL_LOOP_WINDOW CLICKs to detect pattern
        if len(recent_clicks) < self.SPATIAL_LOOP_WINDOW:
            return False

        # Get last N CLICKs
        last_clicks = recent_clicks[-self.SPATIAL_LOOP_WINDOW:]

        # Extract coordinates
        coordinates = [
            (action.get("x", 0), action.get("y", 0))
            for action in last_clicks
        ]

        # Check if all coordinates are within radius of first coordinate
        x0, y0 = coordinates[0]
        for x, y in coordinates[1:]:
            distance = ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5
            if distance > self.SPATIAL_LOOP_RADIUS:
                return False

        # All clicks within radius - spatial loop detected
        self.logger.warning(
            f"🔄 Spatial loop detected: {self.SPATIAL_LOOP_WINDOW} CLICKs "
            f"within {self.SPATIAL_LOOP_RADIUS}px radius at ~({x0}, {y0})"
        )
        return True

"""
Successor Tracker - Tracks which actions lead to which successor states.

Solves the "combobox problem":
- Clicking a dropdown opens a new state with multiple items
- If not all items are explored, the dropdown action should be re-enabled
- This tracker monitors successor state exploration and re-enables parent actions

Also tracks BACK transitions for Backtrack BFS algorithm.
"""

import logging
from collections import deque
from typing import Dict, Tuple, Set, Optional, List, TYPE_CHECKING

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph

if TYPE_CHECKING:
    from rv_agent.config.agent_config import RVAgentConfig


logger = logging.getLogger(__name__)


class SuccessorTracker:
    """
    Tracks action → successor state mappings and successor exploration status.

    Key Concept:
    An action is only "complete" if its successor state is fully explored.
    This prevents premature backtracking when transitional states (like dropdowns)
    haven't been fully explored.

    Example:
        State A: Click "Settings Dropdown" → State B (dropdown menu)
        State B: Has items ["Option 1", "Option 2", "Option 3"]

        If only "Option 1" tested:
        - State B coverage = 33% (1/3 actions)
        - "Settings Dropdown" action should be RE-ENABLED in State A
        - Allows revisiting dropdown to test remaining options

    Re-enablement Limits:
        To prevent infinite re-enablement cycles, each action can only be
        re-enabled a limited number of times (max_re_enables), and only when
        successor coverage is below the threshold (coverage_threshold).
    """

    # Default values (used when config not provided)
    DEFAULT_MAX_RE_ENABLES = 6
    # UI coverage threshold: ratio of executed_actions / total_actions per screen
    # This is internal UI exploration coverage, not method coverage from instrumentation
    DEFAULT_UI_COVERAGE_THRESHOLD = 0.9

    def __init__(
        self,
        graph: DynamicStateGraph,
        config: Optional["RVAgentConfig"] = None
    ):
        """
        Initialize successor tracker.

        Args:
            graph: DynamicStateGraph to query state coverage
            config: Optional RVAgentConfig with calibration parameters
        """
        self.graph = graph

        # Configurable parameters
        if config:
            self.max_re_enables = config.max_re_enables
            # UI coverage threshold (executed_actions / total_actions per screen)
            self.ui_coverage_threshold = config.ui_coverage_threshold
        else:
            self.max_re_enables = self.DEFAULT_MAX_RE_ENABLES
            self.ui_coverage_threshold = self.DEFAULT_UI_COVERAGE_THRESHOLD

        # Maps: (from_hash, action_signature) → successor_hash
        self.successors: Dict[Tuple[str, Tuple], str] = {}

        # Cache of successor coverage (updated on demand)
        self.coverage_cache: Dict[str, float] = {}

        # Tracks how many times each action has been re-enabled
        # Key: (state_hash, action_signature), Value: count
        self.re_enable_counts: Dict[Tuple[str, Tuple], int] = {}

        # Maps: state_hash → set of states reachable via BACK action
        # Used for Backtrack BFS to find unsaturated ancestors
        self.back_successors: Dict[str, Set[str]] = {}

        logger.info(
            f"SuccessorTracker initialized: max_re_enables={self.max_re_enables}, "
            f"coverage_threshold={self.ui_coverage_threshold}"
        )

    def record_successor(
        self,
        from_hash: str,
        action_signature: Tuple,
        to_hash: str
    ):
        """
        Record that action_signature from from_hash leads to to_hash.

        Args:
            from_hash: Source state hash
            action_signature: Action signature (coords, action_type)
            to_hash: Destination state hash
        """
        key = (from_hash, action_signature)

        # Only record if new or different successor
        if key not in self.successors or self.successors[key] != to_hash:
            self.successors[key] = to_hash
            logger.debug(
                f"Recorded successor: {from_hash[:8]}...{action_signature} → {to_hash[:8]}"
            )

            # Invalidate coverage cache for this successor
            if to_hash in self.coverage_cache:
                del self.coverage_cache[to_hash]

    def get_successor_coverage(self, state_hash: str) -> float:
        """
        Get exploration coverage of a successor state.

        Args:
            state_hash: State to check

        Returns:
            Coverage percentage (0.0 to 1.0), or 1.0 if state not found
        """
        # Check cache first
        if state_hash in self.coverage_cache:
            return self.coverage_cache[state_hash]

        # Query graph for state
        node = self.graph.states.get(state_hash)
        if not node:
            # Unknown state - assume fully explored to avoid infinite loops
            return 1.0

        # Calculate coverage: executed_actions / total_actions
        if node.total_actions == 0:
            coverage = 1.0  # No actions = fully explored
        else:
            coverage = len(node.executed_actions) / node.total_actions

        # Cache result
        self.coverage_cache[state_hash] = coverage

        return coverage

    def has_incomplete_successors(self, state_hash: str) -> bool:
        """
        Check if any actions from state_hash lead to incompletely explored states.

        Only considers successors with coverage below coverage_threshold as incomplete.

        Args:
            state_hash: State to check

        Returns:
            True if at least one action has an incomplete successor
        """
        node = self.graph.states.get(state_hash)
        if not node:
            return False

        # Check each executed action
        for action_sig in node.executed_actions:
            key = (state_hash, action_sig)

            if key in self.successors:
                successor_hash = self.successors[key]
                coverage = self.get_successor_coverage(successor_hash)

                if coverage < self.ui_coverage_threshold:
                    logger.debug(
                        f"Found incomplete successor: {successor_hash[:8]} "
                        f"(coverage: {coverage:.1%})"
                    )
                    return True

        return False

    def get_incomplete_successors(self, state_hash: str) -> Set[Tuple]:
        """
        Get action signatures that lead to incomplete successor states.

        Only considers successors with coverage below coverage_threshold as incomplete.

        Args:
            state_hash: State to check

        Returns:
            Set of action signatures with incomplete successors
        """
        incomplete = set()

        node = self.graph.states.get(state_hash)
        if not node:
            return incomplete

        for action_sig in node.executed_actions:
            key = (state_hash, action_sig)

            if key in self.successors:
                successor_hash = self.successors[key]
                coverage = self.get_successor_coverage(successor_hash)

                if coverage < self.ui_coverage_threshold:
                    incomplete.add(action_sig)

        return incomplete

    def update_action_availability(self, state_hash: str) -> int:
        """
        Re-enable actions if their successors are incompletely explored.

        This is the KEY METHOD that solves the combobox problem:
        - Checks all executed actions
        - If an action's successor is incomplete, removes it from executed set
        - Allows the action to be re-selected for further exploration

        Re-enablement is limited to prevent infinite cycles:
        - Each action can only be re-enabled max_re_enables times
        - Only re-enables if UI coverage is below ui_coverage_threshold

        Args:
            state_hash: State to update

        Returns:
            Number of actions re-enabled
        """
        node = self.graph.states.get(state_hash)
        if not node:
            return 0

        re_enabled = 0

        # Check each executed action
        for action_sig in list(node.executed_actions):
            key = (state_hash, action_sig)

            if key not in self.successors:
                continue

            successor_hash = self.successors[key]
            ui_coverage = self.get_successor_coverage(successor_hash)

            # Check re-enable limits and UI coverage threshold
            current_count = self.re_enable_counts.get(key, 0)

            if current_count < self.max_re_enables and ui_coverage < self.ui_coverage_threshold:
                node.executed_actions.discard(action_sig)
                self.re_enable_counts[key] = current_count + 1
                re_enabled += 1
                logger.info(
                    f"Re-enabled action {action_sig} (count={current_count + 1}/{self.max_re_enables}) "
                    f"- successor {successor_hash[:8]} ui_coverage: {ui_coverage:.1%}"
                )

        if re_enabled > 0:
            logger.info(f"Re-enabled {re_enabled} actions in state {state_hash[:8]}")

        return re_enabled

    def get_statistics(self) -> Dict[str, int]:
        """
        Get tracker statistics.

        Returns:
            Dictionary with tracking statistics
        """
        total_tracked = len(self.successors)

        # Count successors below ui_coverage_threshold (same as re-enablement)
        incomplete_count = 0
        for (from_hash, action_sig), to_hash in self.successors.items():
            if self.get_successor_coverage(to_hash) < self.ui_coverage_threshold:
                incomplete_count += 1

        # Sum total re-enablements
        total_re_enables = sum(self.re_enable_counts.values())

        return {
            "total_successors_tracked": total_tracked,
            "incomplete_successors": incomplete_count,
            "complete_successors": total_tracked - incomplete_count,
            "successor_re_enables": total_re_enables,
            "actions_at_max_re_enables": sum(
                1 for count in self.re_enable_counts.values()
                if count >= self.max_re_enables
            ),
            "back_transitions_tracked": sum(len(s) for s in self.back_successors.values()),
        }

    def record_back_transition(self, from_hash: str, to_hash: str) -> None:
        """
        Record a BACK transition from from_hash to to_hash.

        Used by Backtrack BFS to navigate to unsaturated ancestor states.

        Args:
            from_hash: State where BACK was executed
            to_hash: State reached after BACK
        """
        if from_hash not in self.back_successors:
            self.back_successors[from_hash] = set()

        if to_hash not in self.back_successors[from_hash]:
            self.back_successors[from_hash].add(to_hash)
            logger.debug(f"Recorded BACK transition: {from_hash[:8]} → {to_hash[:8]}")

    def get_back_successors(self, state_hash: str) -> List[str]:
        """
        Get states reachable via BACK from the given state.

        Args:
            state_hash: State to check

        Returns:
            List of state hashes reachable via BACK
        """
        return list(self.back_successors.get(state_hash, set()))

    def find_nearest_unsaturated(self, current_state: str) -> Optional[str]:
        """
        BFS to find the nearest unsaturated ancestor state.

        An unsaturated state has actions that haven't been executed at least twice.
        This implements the Backtrack BFS algorithm from APE.

        Args:
            current_state: Current state hash to start search from

        Returns:
            Hash of nearest unsaturated state, or None if all saturated
        """
        visited = {current_state}
        queue = deque([current_state])

        while queue:
            state_hash = queue.popleft()

            for back_target in self.back_successors.get(state_hash, []):
                if back_target in visited:
                    continue

                visited.add(back_target)

                if not self._is_saturated(back_target):
                    logger.info(
                        f"Backtrack BFS: Found unsaturated state {back_target[:8]} "
                        f"(distance: {len(visited) - 1} BACK actions)"
                    )
                    return back_target

                queue.append(back_target)

        logger.info("Backtrack BFS: All reachable states are saturated")
        return None

    def _is_saturated(self, state_hash: str) -> bool:
        """
        Check if a state is saturated (all actions executed at least twice).

        Args:
            state_hash: State to check

        Returns:
            True if saturated, False otherwise
        """
        node = self.graph.states.get(state_hash)
        if not node:
            return True  # Unknown state considered saturated

        if node.total_actions == 0:
            return True  # No actions = saturated

        # Use ScreenNode's saturation rate method
        return node.get_saturation_rate(threshold=2) >= 1.0

    def has_unsaturated_actions(self, state_hash: str) -> bool:
        """
        Check if a state has any unsaturated actions.

        Args:
            state_hash: State to check

        Returns:
            True if state has actions executed less than twice
        """
        node = self.graph.states.get(state_hash)
        if not node:
            return False

        return node.get_saturation_rate(threshold=2) < 1.0

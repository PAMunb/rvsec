"""
Successor Tracker - Tracks which actions lead to which successor states.

Solves the "combobox problem":
- Clicking a dropdown opens a new state with multiple items
- If not all items are explored, the dropdown action should be re-enabled
- This tracker monitors successor state exploration and re-enables parent actions
"""

import logging
from typing import Dict, Tuple, Set, Optional

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph


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
    """

    def __init__(self, graph: DynamicStateGraph):
        """
        Initialize successor tracker.

        Args:
            graph: DynamicStateGraph to query state coverage
        """
        self.graph = graph

        # Maps: (from_hash, action_signature) → successor_hash
        self.successors: Dict[Tuple[str, Tuple], str] = {}

        # Cache of successor coverage (updated on demand)
        self.coverage_cache: Dict[str, float] = {}

        logger.info("SuccessorTracker initialized")

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

                if coverage < 1.0:
                    logger.debug(
                        f"Found incomplete successor: {successor_hash[:8]} "
                        f"(coverage: {coverage:.1%})"
                    )
                    return True

        return False

    def get_incomplete_successors(self, state_hash: str) -> Set[Tuple]:
        """
        Get action signatures that lead to incomplete successor states.

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

                if coverage < 1.0:
                    incomplete.add(action_sig)

        return incomplete

    def update_action_availability(self, state_hash: str) -> int:
        """
        Re-enable actions if their successors are incompletely explored.

        This is the KEY METHOD that solves the combobox problem:
        - Checks all executed actions
        - If an action's successor is incomplete, removes it from executed set
        - Allows the action to be re-selected for further exploration

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

            if key in self.successors:
                successor_hash = self.successors[key]
                coverage = self.get_successor_coverage(successor_hash)

                # If successor incomplete, re-enable the action
                if coverage < 1.0:
                    node.executed_actions.discard(action_sig)
                    re_enabled += 1
                    logger.info(
                        f"Re-enabled action {action_sig} - successor {successor_hash[:8]} "
                        f"coverage: {coverage:.1%}"
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

        incomplete_count = 0
        for (from_hash, action_sig), to_hash in self.successors.items():
            if self.get_successor_coverage(to_hash) < 1.0:
                incomplete_count += 1

        return {
            "total_successors_tracked": total_tracked,
            "incomplete_successors": incomplete_count,
            "complete_successors": total_tracked - incomplete_count
        }

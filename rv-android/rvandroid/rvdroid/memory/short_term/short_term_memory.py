# rvandroid/rvdroid/memory/short_term/short_term_memory.py

"""
Short-term memory module for RVDroid.

This module provides a short-term memory implementation that stores
recent actions, states, and transitions for quick lookups and pattern detection.
"""

import time
from collections import deque
from typing import Dict, Any, List, Optional, Deque, Tuple

from rvandroid.rvdroid.memory.action.memory_action import MemoryAction
from rvandroid.rvdroid.memory.state.memory_state import MemoryState
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ShortTermMemory:
    """
    Maintains a short-term memory of recent actions and states.

    ### Architectural Decisions:
    - Implements an efficient circular buffer for fixed-capacity memory management
    - Optimizes for rapid access to recent events and quick pattern detection
    - Uses lightweight representations of actions and states to minimize memory usage
    - Maintains temporal ordering of events for sequence-based analysis
    - Provides efficient cycle and pattern detection with minimal computational overhead

    ### Role in the System:
    - Provides immediate context for decision making
    - Enables detection of short-term patterns and cycles
    - Supports quick lookups for recent activities
    - Serves as a bridge between immediate perception and long-term memory
    """

    def __init__(self, capacity: int = 50):
        """
        Initialize short-term memory.

        Args:
            capacity: Maximum number of states/actions to remember
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.memory.short_term",
            {CONTEXT_COMPONENT: "ShortTermMemory"}
        )

        # Initialize memory structures
        self.capacity = capacity
        self.states: Dict[str, MemoryState] = {}  # fingerprint -> MemoryState
        self.actions: Dict[int, MemoryAction] = {}  # action_id -> MemoryAction

        # Time-ordered history (most recent at end)
        self.state_history: Deque[str] = deque(maxlen=capacity)  # fingerprints
        self.action_history: Deque[int] = deque(maxlen=capacity)  # action_ids
        self.transition_history: Deque[Dict[str, Any]] = deque(maxlen=capacity)

        # Current state tracking
        self.current_state_fingerprint: Optional[str] = None

        self.logger.info(f"Initialized short-term memory with capacity {capacity}")

    def record_state(self, state: MemoryState) -> None:
        """
        Record a state in short-term memory.

        Args:
            state: State to record
        """
        fingerprint = state.fingerprint

        # Check if state exists
        if fingerprint in self.states:
            # Update existing state
            self.states[fingerprint].record_visit()
        else:
            # Add new state
            self.states[fingerprint] = state

        # Update history
        self.state_history.append(fingerprint)

        # Update current state
        self.current_state_fingerprint = fingerprint

        self.logger.debug(f"Recorded state: {fingerprint}")

        # Clean up old states if needed
        self._cleanup_states()

    def record_action(self, action: MemoryAction, success: bool = True) -> None:
        """
        Record an action in short-term memory.

        Args:
            action: Action to record
            success: Whether the action was successful
        """
        action_id = action.id

        # Add action to memory
        self.actions[action_id] = action

        # Update history
        self.action_history.append(action_id)

        self.logger.debug(f"Recorded action: {action_id}")

        # Clean up old actions if needed
        self._cleanup_actions()

    def record_transition(self, from_state: str, to_state: str,
                          action: MemoryAction, success: bool = True) -> None:
        """
        Record a state transition in short-term memory.

        Args:
            from_state: Source state fingerprint
            to_state: Destination state fingerprint
            action: Action that caused the transition
            success: Whether the transition was successful
        """
        # Create memory entry
        transition = {
            "from_state": from_state,
            "to_state": to_state,
            "action_id": action.id,
            "timestamp": time.time(),
            "success": success
        }

        # Add to transition history
        self.transition_history.append(transition)

        # Update action with transition
        if action.id in self.actions:
            self.actions[action.id].record_execution(from_state, to_state, success)

        # Update state transition records
        if from_state in self.states:
            self.states[from_state].record_transition(action.id, to_state)

        if to_state in self.states:
            self.states[to_state].record_incoming_transition(action.id, from_state)

        self.logger.debug(f"Recorded transition: {from_state} -> {to_state} via {action.id}")

    def get_current_state(self) -> Optional[MemoryState]:
        """
        Get the current state.

        Returns:
            Current state or None if no states recorded
        """
        if self.current_state_fingerprint:
            return self.states.get(self.current_state_fingerprint)
        return None

    def get_recent_states(self, count: int = 5) -> List[MemoryState]:
        """
        Get the most recent states.

        Args:
            count: Number of states to retrieve

        Returns:
            List of recent states
        """
        recent_fingerprints = list(self.state_history)[-count:]
        return [self.states[fp] for fp in recent_fingerprints if fp in self.states]

    def get_recent_actions(self, count: int = 5) -> List[MemoryAction]:
        """
        Get the most recent actions.

        Args:
            count: Number of actions to retrieve

        Returns:
            List of recent actions
        """
        recent_action_ids = list(self.action_history)[-count:]
        return [self.actions[aid] for aid in recent_action_ids if aid in self.actions]

    def detect_cycles(self) -> Tuple[bool, Optional[List[str]]]:
        """
        Detect cycles in recent state transitions.

        Returns:
            Tuple of (cycle_detected, cycle_states)
        """
        # Minimum and maximum cycle length
        min_cycle_length = 2
        max_cycle_length = 5

        # Get recent state fingerprints
        recent_states = list(self.state_history)

        # Need at least 2*min_cycle_length states to detect a cycle
        if len(recent_states) < 2 * min_cycle_length:
            return False, None

        # Check for cycles of different lengths
        for cycle_length in range(min_cycle_length, min(max_cycle_length + 1, len(recent_states) // 2 + 1)):
            # Get the most recent states of this cycle length
            recent_cycle = recent_states[-cycle_length:]

            # Check if this pattern repeats in the previous states
            previous_states = recent_states[-(cycle_length * 2):-cycle_length]

            if recent_cycle == previous_states:
                self.logger.info(f"Detected cycle of length {cycle_length}: {recent_cycle}")
                return True, recent_cycle

        return False, None

    def detect_repetitive_actions(self, threshold: int = 3) -> List[int]:
        """
        Detect repetitive actions that don't lead to state changes.

        Args:
            threshold: Minimum number of repetitions to detect

        Returns:
            List of action IDs that are being repeated
        """
        # Count consecutive actions
        action_counts: Dict[int, int] = {}
        last_state = None
        repetitive_actions = []

        # Get recent states and actions
        recent_states = list(self.state_history)
        recent_actions = list(self.action_history)

        # Process events in pairs (state, action)
        for i in range(min(len(recent_states), len(recent_actions))):
            state_fp = recent_states[i]
            action_id = recent_actions[i]

            # If state changed, reset action counts
            if last_state != state_fp:
                last_state = state_fp
                action_counts = {}

            # Count actions in the same state
            action_counts[action_id] = action_counts.get(action_id, 0) + 1

            # Check if this action is repetitive
            if action_counts[action_id] >= threshold:
                repetitive_actions.append(action_id)

        return repetitive_actions

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the short-term memory.

        Returns:
            Dictionary with memory statistics
        """
        # Find most visited state
        most_visited_state = None
        most_visited_count = 0

        for fingerprint, state in self.states.items():
            if state.visit_count > most_visited_count:
                most_visited_count = state.visit_count
                most_visited_state = fingerprint

        return {
            "capacity": self.capacity,
            "state_count": len(self.states),
            "action_count": len(self.actions),
            "transition_count": len(self.transition_history),
            "unique_states": len(self.states),
            "most_visited_state": most_visited_state,
            "most_visited_count": most_visited_count
        }

    def _cleanup_states(self) -> None:
        """Clean up old states if needed."""
        # Only keep states that are in the history
        if len(self.states) > self.capacity * 2:
            active_fingerprints = set(self.state_history)
            inactive_fingerprints = set(self.states.keys()) - active_fingerprints

            # Remove oldest inactive states
            for fingerprint in list(inactive_fingerprints)[:len(inactive_fingerprints) - self.capacity]:
                if fingerprint in self.states:
                    del self.states[fingerprint]

    def _cleanup_actions(self) -> None:
        """Clean up old actions if needed."""
        # Only keep actions that are in the history
        if len(self.actions) > self.capacity * 2:
            active_action_ids = set(self.action_history)
            inactive_action_ids = set(self.actions.keys()) - active_action_ids

            # Remove oldest inactive actions
            for action_id in list(inactive_action_ids)[:len(inactive_action_ids) - self.capacity]:
                if action_id in self.actions:
                    del self.actions[action_id]

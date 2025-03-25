"""
Short-term memory system for RVDroid.

This module provides a short-term memory implementation that stores
recent actions, states, and transitions for quick lookups and pattern detection.
"""

import time
from collections import deque
from typing import Dict, Any, List, Optional, Deque, Tuple

from rvandroid.parser.screen.visitor.base_visitor import ItemAction
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ShortTermMemory:
    """
    Maintains a short-term memory of recent actions and states.

    Provides efficient storage and retrieval of recent events, with
    cycle detection and pattern recognition capabilities.
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
        self.state_history: Deque[Dict[str, Any]] = deque(maxlen=capacity)
        self.action_history: Deque[Dict[str, Any]] = deque(maxlen=capacity)
        self.transition_history: Deque[Dict[str, Any]] = deque(maxlen=capacity)

        # Track recent states for cycle detection
        self.recent_state_fingerprints: List[str] = []
        self.state_visit_counts: Dict[str, int] = {}

        self.logger.info(f"Initialized short-term memory with capacity {capacity}")

    def record_state(self, state_data: Dict[str, Any]) -> None:
        """
        Record a state in short-term memory.

        Args:
            state_data: State data dictionary
        """
        # Extract key information
        fingerprint = state_data.get("fingerprint", "unknown")
        timestamp = time.time()

        # Create memory entry
        memory_entry = {
            "fingerprint": fingerprint,
            "timestamp": timestamp,
            "activity": state_data.get("activity", "unknown"),
            "screen_type": state_data.get("screen_type", "unknown"),
            "interactive_elements_count": state_data.get("interactive_elements_count", 0)
        }

        # Add to state history
        self.state_history.append(memory_entry)

        # Update state visit tracking
        self.state_visit_counts[fingerprint] = self.state_visit_counts.get(fingerprint, 0) + 1

        # Update recent states for cycle detection (keep last 10)
        self.recent_state_fingerprints.append(fingerprint)
        if len(self.recent_state_fingerprints) > 10:
            self.recent_state_fingerprints.pop(0)

    def record_action(self, action: ItemAction, success: bool = True) -> None:
        """
        Record an action in short-term memory.

        Args:
            action: Action that was executed
            success: Whether the action was successful
        """
        # Create memory entry
        memory_entry = {
            "action_id": action.id,
            "action_text": action.text,
            "timestamp": time.time(),
            "success": success,
            "reaches_mop": action.reaches_mop,
            "directly_reaches_mop": action.directly_reaches_mop
        }

        # Add to action history
        self.action_history.append(memory_entry)

    def record_transition(self, from_state: str, to_state: str, action: ItemAction, success: bool = True) -> None:
        """
        Record a state transition in short-term memory.

        Args:
            from_state: Source state fingerprint
            to_state: Destination state fingerprint
            action: Action that caused the transition
            success: Whether the transition was successful
        """
        # Create memory entry
        memory_entry = {
            "from_state": from_state,
            "to_state": to_state,
            "action_id": action.id,
            "action_text": action.text,
            "timestamp": time.time(),
            "success": success
        }

        # Add to transition history
        self.transition_history.append(memory_entry)

    def get_recent_states(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent states.

        Args:
            count: Number of states to retrieve

        Returns:
            List of recent state entries
        """
        return list(self.state_history)[-count:]

    def get_recent_actions(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent actions.

        Args:
            count: Number of actions to retrieve

        Returns:
            List of recent action entries
        """
        return list(self.action_history)[-count:]

    def get_state_transitions(self, state_fingerprint: str) -> List[Dict[str, Any]]:
        """
        Get transitions from a specific state.

        Args:
            state_fingerprint: State fingerprint to get transitions for

        Returns:
            List of transition entries
        """
        return [t for t in self.transition_history if t["from_state"] == state_fingerprint]

    def get_action_history_in_state(self, state_fingerprint: str) -> List[Dict[str, Any]]:
        """
        Get history of actions performed in a specific state.

        Args:
            state_fingerprint: State fingerprint to get actions for

        Returns:
            List of action entries
        """
        # Find state visits in history
        state_visits = [i for i, s in enumerate(self.state_history) if s["fingerprint"] == state_fingerprint]

        if not state_visits:
            return []

        # Find actions that occurred during state visits
        actions = []
        for i, action in enumerate(self.action_history):
            # Find corresponding state visit for this action
            action_time = action["timestamp"]
            for visit_idx in state_visits:
                if visit_idx < len(self.state_history) - 1:
                    # Check if action time is between this state and the next
                    state_time = self.state_history[visit_idx]["timestamp"]
                    next_state_time = self.state_history[visit_idx + 1]["timestamp"]

                    if state_time <= action_time < next_state_time:
                        actions.append(action)
                        break
                else:
                    # Last state visit, check if action came after
                    state_time = self.state_history[visit_idx]["timestamp"]
                    if action_time >= state_time:
                        actions.append(action)

        return actions

    def detect_cycles(self) -> Tuple[bool, Optional[List[str]]]:
        """
        Detect cycles in recent state transitions.

        Returns:
            Tuple of (cycle_detected, cycle_states)
        """
        # Minimum cycle length
        min_cycle_length = 2
        max_cycle_length = 5

        recent_states = self.recent_state_fingerprints

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

        # Process events in chronological order
        events = []

        # Add state events
        for i, state in enumerate(self.state_history):
            events.append(("state", i, state["timestamp"], state))

        # Add action events
        for i, action in enumerate(self.action_history):
            events.append(("action", i, action["timestamp"], action))

        # Sort by timestamp
        events.sort(key=lambda x: x[2])

        # Process events in order
        for event_type, idx, timestamp, event in events:
            if event_type == "state":
                # State change resets action counts
                last_state = event["fingerprint"]
                action_counts = {}

            elif event_type == "action":
                # Count consecutive actions in the same state
                action_id = event["action_id"]

                if last_state:
                    action_counts[action_id] = action_counts.get(action_id, 0) + 1

                    # Check if this action is repetitive
                    if action_counts[action_id] >= threshold:
                        repetitive_actions.append(action_id)

        return repetitive_actions

    def get_successful_actions_in_state(self, state_fingerprint: str) -> List[int]:
        """
        Get actions that were successful in a specific state.

        Args:
            state_fingerprint: State fingerprint

        Returns:
            List of successful action IDs
        """
        successful_actions = []

        # Find transitions from this state
        for transition in self.transition_history:
            if transition["from_state"] == state_fingerprint and transition["success"]:
                successful_actions.append(transition["action_id"])

        return successful_actions

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the short-term memory.

        Returns:
            Dictionary with memory statistics
        """
        return {
            "capacity": self.capacity,
            "state_count": len(self.state_history),
            "action_count": len(self.action_history),
            "transition_count": len(self.transition_history),
            "unique_states": len(self.state_visit_counts),
            "most_visited_state": max(self.state_visit_counts.items(), key=lambda x: x[1])[
                0] if self.state_visit_counts else None,
            "most_visited_count": max(self.state_visit_counts.values()) if self.state_visit_counts else 0
        }
   
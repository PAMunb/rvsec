# rvandroid/rvdroid/memory/long_term/long_term_memory.py

"""
Long-term memory module for RVDroid.

This module provides a memory system that maintains knowledge about application
behavior during a test execution session, enabling the tool to build on
exploration discoveries and guide testing.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional, Tuple, Set

from rvandroid.domain.dynamic_wtg import DynamicTransitionGraph
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.rvdroid.memory.action.memory_action import MemoryAction
from rvandroid.rvdroid.memory.state.memory_state import MemoryState
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class LongTermMemory:
    """
    Maintains knowledge about application behavior across a single test execution session.

    Unlike its name suggests, this is not a persistent memory system, but rather a
    comprehensive memory that lives only during the execution of a task (which may be several
    hours long). It integrates with window transition graphs to guide testing behavior.

    ### Architectural Decisions:
    - Stores and organizes testing information in-memory for the duration of a test session
    - Integrates with static and dynamic window transition graphs
    - Provides efficient access patterns to guide action generation and selection
    - Maintains a comprehensive model of application states and transitions

    ### Role in the System:
    - Provides long-running execution context for a single task
    - Guides action selection and prioritization
    - Helps identify unexplored areas of the application
    - Supports strategic testing decisions based on historical execution
    """

    def __init__(self, app_package: str, static_data: Optional[StaticAnalysisData] = None,
                 static_wtg=None, dynamic_wtg=None):
        """
        Initialize long-term memory.

        Args:
            app_package: Package name of the application
            static_data: Optional static analysis data
            static_wtg: Static window transition graph
            dynamic_wtg: Dynamic window transition graph
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.memory.long_term",
            {CONTEXT_COMPONENT: "LongTermMemory"}
        )

        # Initialize parameters
        self.app_package = app_package
        self.static_data = static_data
        self.static_wtg = static_wtg
        self.dynamic_wtg = dynamic_wtg

        # Initialize memory structures
        self.states: Dict[str, MemoryState] = {}  # fingerprint -> MemoryState
        self.actions: Dict[int, MemoryAction] = {}  # action_id -> MemoryAction

        # Activity tracking
        self.activities: Dict[str, Dict[str, Any]] = {}  # activity_name -> info

        # Security operations tracking
        self.security_operations: Dict[int, Dict[str, Any]] = {}  # action_id -> info

        # Prioritized state tracking
        self.unexplored_states: Set[str] = set()  # States with unexplored actions
        self.security_states: Set[str] = set()  # States with security operations
        self.error_states: Set[str] = set()  # States with error conditions

        # Transition tracking for navigation
        self.transition_graph = dynamic_wtg if dynamic_wtg else DynamicTransitionGraph()

        # Statistics
        self.session_stats: Dict[str, Any] = {
            "start_time": time.time(),
            "states_visited": 0,
            "activities_visited": 0,
            "actions_executed": 0,
            "security_operations_executed": 0,
            "new_states_discovered": 0,
            "errors_detected": 0
        }

        self.logger.info(f"Initialized long-term memory for {app_package}")

    def record_state(self, state: MemoryState, is_new: bool = False) -> None:
        """
        Record information about an application state.

        Args:
            state: State to record
            is_new: Whether this is a newly discovered state
        """
        fingerprint = state.fingerprint
        activity = state.activity

        # Update statistics
        self.session_stats["states_visited"] += 1
        if is_new:
            self.session_stats["new_states_discovered"] += 1
            self.unexplored_states.add(fingerprint)

        # Record activity visit
        if activity not in self.activities:
            self.activities[activity] = {
                "visit_count": 0,
                "first_seen": time.time(),
                "last_seen": time.time(),
                "states": set()
            }
            self.session_stats["activities_visited"] += 1

        # Update activity knowledge
        activity_info = self.activities[activity]
        activity_info["visit_count"] += 1
        activity_info["last_seen"] = time.time()
        activity_info["states"].add(fingerprint)

        # Record state
        if fingerprint in self.states:
            # Update existing state
            self.states[fingerprint].record_visit()
        else:
            # Add new state
            self.states[fingerprint] = state

        # Record in transition graph if needed
        if hasattr(self.transition_graph, 'record_visit'):
            try:
                self.transition_graph.record_visit(activity)
            except Exception as e:
                self.logger.error(f"Error recording visit to transition graph: {e}")

    def record_action(self, action: MemoryAction, state_fingerprint: str, success: bool) -> None:
        """
        Record information about an executed action.

        Args:
            action: Action that was executed
            state_fingerprint: State fingerprint where action was executed
            success: Whether the action was successful
        """
        # Update statistics
        self.session_stats["actions_executed"] += 1

        # Track security operations
        if action.reaches_mop:
            self.session_stats["security_operations_executed"] += 1
            self.security_states.add(state_fingerprint)

            # Record security operation details
            self.security_operations[action.id] = {
                "timestamp": time.time(),
                "state": state_fingerprint,
                "success": success,
                "directly_reaches_mop": action.directly_reaches_mop
            }

        # Store or update action
        if action.id in self.actions:
            # Action exists, just update execution info
            existing_action = self.actions[action.id]
            # Update record will happen in transition record
        else:
            # New action
            self.actions[action.id] = action

        # Update state knowledge
        if state_fingerprint in self.states:
            state = self.states[state_fingerprint]
            state.record_action(action.id, success)

            # If all actions in this state have been executed,
            # remove from unexplored states
            if state_fingerprint in self.unexplored_states:
                # Check if there are unexplored actions
                # This is a simple check - in practice we would need
                # a more sophisticated way to determine "all actions"
                if len(state.all_actions) > 0:
                    has_unexplored = False  # Assume all explored until proven otherwise
                    for item_action_id in state.all_actions:
                        if item_action_id not in state.successful_actions and item_action_id not in state.failed_actions:
                            has_unexplored = True
                            break

                    if not has_unexplored:
                        self.unexplored_states.remove(state_fingerprint)

    def record_transition(self, from_state: str, to_state: str, action: MemoryAction, success: bool) -> None:
        """
        Record a state transition.

        Args:
            from_state: Source state fingerprint
            to_state: Destination state fingerprint
            action: Action that caused the transition
            success: Whether the transition was successful
        """
        try:
            # Skip recording if either state is unknown
            if from_state == "unknown" or to_state == "unknown":
                return

            # Get activity names
            from_activity = self.states.get(from_state, MemoryState(from_state, "unknown")).activity
            to_activity = self.states.get(to_state, MemoryState(to_state, "unknown")).activity

            # Update state transition records
            if from_state in self.states:
                self.states[from_state].record_transition(action.id, to_state)

            if to_state in self.states:
                self.states[to_state].record_incoming_transition(action.id, from_state)

            # Record in transition graph
            if hasattr(self.transition_graph, 'record_transition'):
                self.transition_graph.record_transition(
                    from_activity,
                    to_activity,
                    str(action.id),
                    action.type
                )

            # Update action with transition info
            if action.id in self.actions:
                action.record_execution(from_state, to_state, success)

        except Exception as e:
            self.logger.error(f"Error recording transition: {e}", exc_info=True)

    def save(self, file_path: str) -> bool:
        """
        Save memory to disk.

        Args:
            file_path: Path to save the memory

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create serializable data
            memory_data = {
                "app_package": self.app_package,
                "last_updated": time.time(),
                "session_stats": self.session_stats,
                "states": {fp: state.to_dict() for fp, state in self.states.items()},
                "actions": {str(aid): action.to_dict() for aid, action in self.actions.items()},
                "activities": self._serialize_activities(),
                "security_operations": self.security_operations,
                "unexplored_states": list(self.unexplored_states),
                "security_states": list(self.security_states),
                "error_states": list(self.error_states)
            }

            # Add transition graph if available
            if hasattr(self.transition_graph, 'to_dict'):
                memory_data["transition_graph"] = self.transition_graph.to_dict()

            # Write to file
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(memory_data, f, indent=2)

            self.logger.info(f"Saved memory to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving memory: {e}")
            return False

    def load(self, file_path: str) -> bool:
        """
        Load memory from disk.

        Args:
            file_path: Path to load the memory from

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(file_path):
            self.logger.info(f"No existing memory file found at {file_path}")
            return False

        try:
            # Read from file
            with open(file_path, 'r') as f:
                memory_data = json.load(f)

            # Check application package
            if memory_data.get("app_package") != self.app_package:
                self.logger.warning(f"Memory file is for a different app: {memory_data.get('app_package')}")
                return False

            # Load states
            for fingerprint, state_data in memory_data.get("states", {}).items():
                self.states[fingerprint] = MemoryState.from_dict(state_data)

            # Load actions
            for action_id_str, action_data in memory_data.get("actions", {}).items():
                self.actions[int(action_id_str)] = MemoryAction.from_dict(action_data)

            # Load activities
            activities_data = memory_data.get("activities", {})
            self._deserialize_activities(activities_data)

            # Load special state sets
            self.unexplored_states = set(memory_data.get("unexplored_states", []))
            self.security_states = set(memory_data.get("security_states", []))
            self.error_states = set(memory_data.get("error_states", []))

            # Load security operations
            self.security_operations = memory_data.get("security_operations", {})

            # Load transition graph if available
            if "transition_graph" in memory_data and hasattr(self.transition_graph, 'from_dict'):
                graph_data = memory_data["transition_graph"]
                self.transition_graph = DynamicTransitionGraph.from_dict(graph_data)

            # Load session stats
            self.session_stats = memory_data.get("session_stats", self.session_stats)

            self.logger.info(f"Loaded memory from {file_path} with {len(self.states)} states")
            return True

        except Exception as e:
            self.logger.error(f"Error loading memory: {e}")
            return False

    def get_successful_actions_for_state(self, state_fingerprint: str) -> List[int]:
        """
        Get actions that have been successful in a specific state.

        Args:
            state_fingerprint: State fingerprint

        Returns:
            List of successful action IDs
        """
        if state_fingerprint not in self.states:
            return []

        return list(self.states[state_fingerprint].successful_actions)

    def get_security_actions(self) -> List[Tuple[str, int]]:
        """
        Get state-action pairs that trigger security operations.

        Returns:
            List of (state_fingerprint, action_id) tuples
        """
        result = []

        for action_id, info in self.security_operations.items():
            state_fingerprint = info.get("state", "unknown")
            result.append((state_fingerprint, int(action_id)))

        return result

    def get_action_success_rate(self, action_id: int) -> float:
        """
        Get the success rate for an action across all states.

        Args:
            action_id: Action ID

        Returns:
            Success rate (0.0 to 1.0)
        """
        if action_id not in self.actions:
            return 0.0

        return self.actions[action_id].get_success_rate()

    def get_action_success_rate_in_state(self, action_id: int, state_fingerprint: str) -> float:
        """
        Get the success rate for an action in a specific state.

        Args:
            action_id: Action ID
            state_fingerprint: State fingerprint

        Returns:
            Success rate (0.0 to 1.0) or 0.0 if unknown
        """
        if action_id not in self.actions:
            return 0.0

        return self.actions[action_id].get_success_rate(state_fingerprint)

    def suggest_next_actions(self, current_state: str, count: int = 3) -> List[int]:
        """
        Suggest next actions based on historical data.

        Args:
            current_state: Current state fingerprint
            count: Maximum number of actions to suggest

        Returns:
            List of suggested action IDs
        """
        if current_state not in self.states:
            return []

        # Get successful actions for this state
        current_state_obj = self.states[current_state]
        successful_actions = list(current_state_obj.successful_actions)

        # If we have enough actions, return them
        if len(successful_actions) >= count:
            return successful_actions[:count]

        # Otherwise, add actions that were successful in similar states
        current_activity = current_state_obj.activity

        # Find other states in the same activity
        similar_states = [
            fingerprint for fingerprint, state in self.states.items()
            if state.activity == current_activity and fingerprint != current_state
        ]

        # Collect successful actions from similar states
        for state_fingerprint in similar_states:
            if state_fingerprint in self.states:
                state = self.states[state_fingerprint]
                actions = state.successful_actions
                for action_id in actions:
                    if action_id not in successful_actions:
                        successful_actions.append(action_id)
                        if len(successful_actions) >= count:
                            break

            if len(successful_actions) >= count:
                break

        return successful_actions[:count]

    def get_next_activities_to_explore(self, current_activity: str, count: int = 3) -> List[str]:
        """
        Get activities to explore next based on transition graph.

        Args:
            current_activity: Current activity name
            count: Maximum number of activities to suggest

        Returns:
            List of activity names
        """
        try:
            # Get least visited neighbors from transition graph
            neighbor_activities = []

            # Check if we can access transition graph neighbors
            if hasattr(self.transition_graph, 'graph') and hasattr(self.transition_graph.graph, 'neighbors'):
                neighbors = list(self.transition_graph.graph.neighbors(current_activity))

                if not neighbors:
                    # No known transitions, return least visited activities
                    least_visited = sorted(
                        [(a, info["visit_count"]) for a, info in self.activities.items()],
                        key=lambda x: x[1]
                    )
                    neighbor_activities = [a for a, _ in least_visited[:count]]
                else:
                    # Get visit counts for neighbors
                    neighbor_visits = []
                    for neighbor in neighbors:
                        visit_count = self.activities.get(neighbor, {}).get("visit_count", 0)
                        neighbor_visits.append((neighbor, visit_count))

                    # Sort by visit count (ascending)
                    neighbor_visits.sort(key=lambda x: x[1])

                    # Get activity names
                    neighbor_activities = [a for a, _ in neighbor_visits[:count]]

            return neighbor_activities
        except Exception as e:
            self.logger.error(f"Error getting next activities to explore: {e}")
            return []

    def mark_error_state(self, state_fingerprint: str) -> None:
        """
        Mark a state as having an error condition.

        Args:
            state_fingerprint: State fingerprint to mark
        """
        self.error_states.add(state_fingerprint)
        self.session_stats["errors_detected"] += 1

    def get_prioritized_states(self, count: int = 5) -> List[str]:
        """
        Get prioritized states for exploration.

        Args:
            count: Maximum number of states to return

        Returns:
            List of state fingerprints in priority order
        """
        prioritized = []

        # First priority: unexplored states with security operations
        security_unexplored = self.security_states.intersection(self.unexplored_states)
        prioritized.extend(list(security_unexplored)[:count])

        # Second priority: other unexplored states
        if len(prioritized) < count:
            remaining = count - len(prioritized)
            other_unexplored = self.unexplored_states - security_unexplored
            prioritized.extend(list(other_unexplored)[:remaining])

        # Third priority: states with outgoing transitions to unexplored states
        if len(prioritized) < count:
            remaining = count - len(prioritized)
            transition_states = self._get_states_with_transitions_to_unexplored(remaining)
            prioritized.extend([s for s in transition_states if s not in prioritized][:remaining])

        # Fourth priority: states with security operations
        if len(prioritized) < count:
            remaining = count - len(prioritized)
            other_security = self.security_states - set(prioritized)
            prioritized.extend(list(other_security)[:remaining])

        return prioritized[:count]

    def get_state_by_fingerprint(self, fingerprint: str) -> Optional[MemoryState]:
        """
        Get a state by its fingerprint.

        Args:
            fingerprint: State fingerprint

        Returns:
            Memory state or None if not found
        """
        return self.states.get(fingerprint)

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the long-term memory.

        Returns:
            Dictionary with memory statistics
        """
        try:
            # Calculate additional metrics
            security_ratio = 0
            if self.session_stats["actions_executed"] > 0:
                security_ratio = (self.session_stats["security_operations_executed"] /
                                  self.session_stats["actions_executed"])

            transitions_count = 0
            if hasattr(self.transition_graph, 'transitions'):
                transitions_count = len(self.transition_graph.transitions)

            stats = {
                "states_count": len(self.states),
                "activities_count": len(self.activities),
                "actions_count": len(self.actions),
                "security_operations_count": len(self.security_operations),
                "unexplored_states_count": len(self.unexplored_states),
                "security_states_count": len(self.security_states),
                "error_states_count": len(self.error_states),
                "transitions_count": transitions_count,
                "session_duration": time.time() - self.session_stats["start_time"],
                "security_ratio": security_ratio,
                "session_stats": self.session_stats
            }

            return stats

        except Exception as e:
            self.logger.error(f"Error getting memory stats: {e}")
            return {
                "error": f"Failed to get memory stats: {str(e)}"
            }

    def _serialize_activities(self) -> Dict[str, Any]:
        """
        Serialize activities for JSON storage.

        Returns:
            Dictionary representation of activities
        """
        result = {}

        for activity, info in self.activities.items():
            result[activity] = {
                "visit_count": info["visit_count"],
                "first_seen": info["first_seen"],
                "last_seen": info["last_seen"],
                "states": list(info["states"])
            }

        return result

    def _deserialize_activities(self, activities_data: Dict[str, Any]) -> None:
        """
        Deserialize activities from JSON.

        Args:
            activities_data: Dictionary representation of activities
        """
        for activity, info in activities_data.items():
            self.activities[activity] = {
                "visit_count": info["visit_count"],
                "first_seen": info["first_seen"],
                "last_seen": info["last_seen"],
                "states": set(info["states"])
            }

    def _get_states_with_transitions_to_unexplored(self, count: int) -> List[str]:
        """
        Get states that have transitions to unexplored states.

        Args:
            count: Maximum number of states to return

        Returns:
            List of state fingerprints
        """
        transition_states = []

        for fingerprint, state in self.states.items():
            # Skip if already in unexplored
            if fingerprint in self.unexplored_states:
                continue

            # Check if this state has transitions to unexplored states
            for target in state.outgoing_transitions:
                if target in self.unexplored_states:
                    transition_states.append(fingerprint)
                    break

            if len(transition_states) >= count:
                break

        return transition_states

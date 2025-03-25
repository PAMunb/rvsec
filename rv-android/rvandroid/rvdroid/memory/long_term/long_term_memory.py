"""
Long-term memory system for RVDroid.

This module provides a persistent memory system that maintains knowledge
about application behavior across testing sessions, enabling the tool
to build on previous explorations.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional, Tuple

from rvandroid.domain.dynamic_wtg import DynamicTransitionGraph
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ItemAction
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class LongTermMemory:
    """
    Maintains knowledge about application behavior across a single test execution session.

    Unlike its name suggests, this is not a persistent memory system, but rather a
    comprehensive memory that lives only during the execution of a task (which may be several
    hours long). It integrates with window transition graphs to guide testing behavior.

    ### Architectural Decisions:
    - Stores and organizes testing information in-memory without writing to disk
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
        self.state_knowledge: Dict[str, Dict[str, Any]] = {}
        self.activity_knowledge: Dict[str, Dict[str, Any]] = {}
        self.action_knowledge: Dict[int, Dict[str, Any]] = {}
        self.security_operations: Dict[str, List[Dict[str, Any]]] = {}

        # Statistics
        self.session_stats: Dict[str, Any] = {
            "start_time": time.time(),
            "states_visited": 0,
            "activities_visited": 0,
            "actions_executed": 0,
            "security_operations_executed": 0,
            "new_states_discovered": 0
        }

        self.logger.info(f"Initialized long-term memory for {app_package}")

    def record_state(self, state_data: Dict[str, Any], is_new: bool = False) -> None:
        """
        Record information about an application state.

        Args:
            state_data: State data dictionary
            is_new: Whether this is a newly discovered state
        """
        # Extract key information
        fingerprint = state_data.get("fingerprint", "unknown")
        activity = state_data.get("activity", "unknown")
        timestamp = time.time()

        # Update statistics
        self.session_stats["states_visited"] += 1
        if is_new:
            self.session_stats["new_states_discovered"] += 1

        # Record activity visit
        if activity not in self.activity_knowledge:
            self.activity_knowledge[activity] = {
                "visit_count": 0,
                "first_seen": timestamp,
                "last_seen": timestamp,
                "states": set()
            }
            self.session_stats["activities_visited"] += 1

        # Update activity knowledge
        activity_info = self.activity_knowledge[activity]
        activity_info["visit_count"] += 1
        activity_info["last_seen"] = timestamp
        activity_info["states"].add(fingerprint)

        # Record state knowledge
        if fingerprint not in self.state_knowledge:
            self.state_knowledge[fingerprint] = {
                "activity": activity,
                "visit_count": 0,
                "first_seen": timestamp,
                "last_seen": timestamp,
                "interactive_elements": state_data.get("interactive_elements_count", 0),
                "successful_actions": set(),
                "failed_actions": set()
            }

        # Update state knowledge
        state_info = self.state_knowledge[fingerprint]
        state_info["visit_count"] += 1
        state_info["last_seen"] = timestamp

        # Record in transition graph
        self.transition_graph.record_visit(activity)

    def record_action(self, action: ItemAction, state_fingerprint: str, success: bool) -> None:
        """
        Record information about an executed action.

        Args:
            action: Action that was executed
            state_fingerprint: State fingerprint where action was executed
            success: Whether the action was successful
        """
        # Update statistics
        self.session_stats["actions_executed"] += 1
        if action.reaches_mop:
            self.session_stats["security_operations_executed"] += 1

        # Update action knowledge
        if action.id not in self.action_knowledge:
            self.action_knowledge[action.id] = {
                "execution_count": 0,
                "success_count": 0,
                "states": set(),
                "reaches_mop": action.reaches_mop,
                "directly_reaches_mop": action.directly_reaches_mop
            }

        # Update action stats
        action_info = self.action_knowledge[action.id]
        action_info["execution_count"] += 1
        if success:
            action_info["success_count"] += 1
        action_info["states"].add(state_fingerprint)

        # Update state knowledge
        if state_fingerprint in self.state_knowledge:
            state_info = self.state_knowledge[state_fingerprint]
            if success:
                state_info["successful_actions"].add(action.id)
            else:
                state_info["failed_actions"].add(action.id)

        # Record security operations
        if action.reaches_mop:
            operation_key = f"{state_fingerprint}_{action.id}"
            if operation_key not in self.security_operations:
                self.security_operations[operation_key] = []

            self.security_operations[operation_key].append({
                "timestamp": time.time(),
                "success": success,
                "state": state_fingerprint,
                "action_id": action.id,
                "directly_reaches_mop": action.directly_reaches_mop
            })

    def record_transition(self, from_state: str, to_state: str, action: ItemAction, success: bool) -> None:
        """
        Record a state transition.

        Args:
            from_state: Source state fingerprint
            to_state: Destination state fingerprint
            action: Action that caused the transition
            success: Whether the transition was successful
        """
        # Skip recording if either state is unknown
        if from_state == "unknown" or to_state == "unknown":
            return

        # Get activity names
        from_activity = self.state_knowledge.get(from_state, {}).get("activity", "unknown")
        to_activity = self.state_knowledge.get(to_state, {}).get("activity", "unknown")

        # Record in transition graph
        self.transition_graph.record_transition(
            from_activity,
            to_activity,
            str(action.id),
            self._get_action_type(action.text)
        )

    def save(self) -> bool:
        """
        Save memory to disk.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert sets to lists for JSON serialization
            serializable_state_knowledge = {}
            for fingerprint, info in self.state_knowledge.items():
                serializable_info = info.copy()
                serializable_info["successful_actions"] = list(info["successful_actions"])
                serializable_info["failed_actions"] = list(info["failed_actions"])
                serializable_state_knowledge[fingerprint] = serializable_info

            serializable_activity_knowledge = {}
            for activity, info in self.activity_knowledge.items():
                serializable_info = info.copy()
                serializable_info["states"] = list(info["states"])
                serializable_activity_knowledge[activity] = serializable_info

            serializable_action_knowledge = {}
            for action_id, info in self.action_knowledge.items():
                serializable_info = info.copy()
                serializable_info["states"] = list(info["states"])
                serializable_action_knowledge[str(action_id)] = serializable_info

            # Prepare data structure for serialization
            memory_data = {
                "app_package": self.app_package,
                "last_updated": time.time(),
                "session_stats": self.session_stats,
                "state_knowledge": serializable_state_knowledge,
                "activity_knowledge": serializable_activity_knowledge,
                "action_knowledge": serializable_action_knowledge,
                "security_operations": self.security_operations,
                "transition_graph": self.transition_graph.to_dict()
            }

            # Write to file
            with open(self.memory_file, 'w') as f:
                json.dump(memory_data, f, indent=2)

            self.logger.info(f"Saved memory to {self.memory_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving memory: {e}")
            return False

    def _load_memory(self) -> bool:
        """
        Load memory from disk.

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(self.memory_file):
            self.logger.info(f"No existing memory file found at {self.memory_file}")
            return False

        try:
            with open(self.memory_file, 'r') as f:
                memory_data = json.load(f)

            # Check if this memory is for the correct app
            if memory_data.get("app_package") != self.app_package:
                self.logger.warning(f"Memory file is for a different app: {memory_data.get('app_package')}")
                return False

            # Load state knowledge
            for fingerprint, info in memory_data.get("state_knowledge", {}).items():
                self.state_knowledge[fingerprint] = {
                    "activity": info.get("activity", "unknown"),
                    "visit_count": info.get("visit_count", 0),
                    "first_seen": info.get("first_seen", 0),
                    "last_seen": info.get("last_seen", 0),
                    "interactive_elements": info.get("interactive_elements", 0),
                    "successful_actions": set(info.get("successful_actions", [])),
                    "failed_actions": set(info.get("failed_actions", []))
                }

            # Load activity knowledge
            for activity, info in memory_data.get("activity_knowledge", {}).items():
                self.activity_knowledge[activity] = {
                    "visit_count": info.get("visit_count", 0),
                    "first_seen": info.get("first_seen", 0),
                    "last_seen": info.get("last_seen", 0),
                    "states": set(info.get("states", []))
                }

            # Load action knowledge
            for action_id_str, info in memory_data.get("action_knowledge", {}).items():
                action_id = int(action_id_str)
                self.action_knowledge[action_id] = {
                    "execution_count": info.get("execution_count", 0),
                    "success_count": info.get("success_count", 0),
                    "states": set(info.get("states", [])),
                    "reaches_mop": info.get("reaches_mop", False),
                    "directly_reaches_mop": info.get("directly_reaches_mop", False)
                }

            # Load security operations
            self.security_operations = memory_data.get("security_operations", {})

            # Load transition graph
            if "transition_graph" in memory_data:
                graph_data = memory_data["transition_graph"]
                self.transition_graph = DynamicTransitionGraph.from_dict(graph_data)

            self.logger.info(f"Loaded memory from {self.memory_file} with {len(self.state_knowledge)} states")
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
        if state_fingerprint not in self.state_knowledge:
            return []

        return list(self.state_knowledge[state_fingerprint]["successful_actions"])

    def get_security_actions(self) -> List[Tuple[str, int]]:
        """
        Get state-action pairs that trigger security operations.

        Returns:
            List of (state_fingerprint, action_id) tuples
        """
        security_actions = []

        for action_id, info in self.action_knowledge.items():
            if info["reaches_mop"]:
                for state in info["states"]:
                    security_actions.append((state, action_id))

        return security_actions

    def get_action_success_rate(self, action_id: int) -> float:
        """
        Get the success rate for an action across all states.

        Args:
            action_id: Action ID

        Returns:
            Success rate (0.0 to 1.0)
        """
        if action_id not in self.action_knowledge:
            return 0.0

        info = self.action_knowledge[action_id]
        if info["execution_count"] == 0:
            return 0.0

        return info["success_count"] / info["execution_count"]

    def get_action_success_rate_in_state(self, action_id: int, state_fingerprint: str) -> float:
        """
        Get the success rate for an action in a specific state.

        Args:
            action_id: Action ID
            state_fingerprint: State fingerprint

        Returns:
            Success rate (0.0 to 1.0) or 0.0 if unknown
        """
        if state_fingerprint not in self.state_knowledge:
            return 0.0

        state_info = self.state_knowledge[state_fingerprint]
        successful = action_id in state_info["successful_actions"]
        failed = action_id in state_info["failed_actions"]

        if not successful and not failed:
            return 0.0

        success_count = 1 if successful else 0
        total_count = 1 if successful else 0 + 1 if failed else 0

        return success_count / total_count

    def suggest_next_actions(self, current_state: str, count: int = 3) -> List[int]:
        """
        Suggest next actions based on historical data.

        Args:
            current_state: Current state fingerprint
            count: Maximum number of actions to suggest

        Returns:
            List of suggested action IDs
        """
        if current_state not in self.state_knowledge:
            return []

        # Get successful actions for this state
        successful_actions = list(self.state_knowledge[current_state]["successful_actions"])

        # If we have enough actions, return them
        if len(successful_actions) >= count:
            return successful_actions[:count]

        # Otherwise, add actions that were successful in similar states
        current_activity = self.state_knowledge[current_state]["activity"]

        # Find other states in the same activity
        similar_states = [
            state for state, info in self.state_knowledge.items()
            if info["activity"] == current_activity and state != current_state
        ]

        # Collect successful actions from similar states
        for state in similar_states:
            actions = self.state_knowledge[state]["successful_actions"]
            for action in actions:
                if action not in successful_actions:
                    successful_actions.append(action)
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
        # Get least visited neighbors from transition graph
        neighbor_activities = []

        # Get neighbors from graph
        neighbors = list(self.transition_graph.graph.neighbors(current_activity))

        if not neighbors:
            # No known transitions, return least visited activities
            least_visited = sorted(
                [(a, info["visit_count"]) for a, info in self.activity_knowledge.items()],
                key=lambda x: x[1]
            )
            neighbor_activities = [a for a, _ in least_visited[:count]]
        else:
            # Get visit counts for neighbors
            neighbor_visits = []
            for neighbor in neighbors:
                visit_count = self.activity_knowledge.get(neighbor, {}).get("visit_count", 0)
                neighbor_visits.append((neighbor, visit_count))

            # Sort by visit count (ascending)
            neighbor_visits.sort(key=lambda x: x[1])

            # Get activity names
            neighbor_activities = [a for a, _ in neighbor_visits[:count]]

        return neighbor_activities

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the long-term memory.

        Returns:
            Dictionary with memory statistics
        """
        return {
            "states_count": len(self.state_knowledge),
            "activities_count": len(self.activity_knowledge),
            "actions_count": len(self.action_knowledge),
            "security_operations_count": len(self.security_operations),
            "transitions_count": sum(1 for _ in self.transition_graph.transitions),
            "session_stats": self.session_stats
        }

    def _get_action_type(self, action_text: str) -> str:
        """
        Extract action type from action text.

        Args:
            action_text: Text description of the action

        Returns:
            Action type string
        """
        if "CLICK" in action_text:
            return "click"
        elif "LONG_CLICK" in action_text:
            return "long_click"
        elif "SCROLL" in action_text:
            return "scroll"
        elif "SET_TEXT" in action_text:
            return "text_input"
        elif "BACK" in action_text:
            return "back"
        else:
            return "other"

# rvandroid/core/memory/long_term_memory.py
"""
Long-term memory system shared between RV-Android tools.

This module provides a memory system that persists across multiple interactions
with the application, tracking state transitions, action success rates, and
exploration patterns.
"""

import time
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rvsmart_tool.llm.service.action_generator import GeneratedAction


class MemoryState:
    """
    Represents an application state in memory.
    
    Stores state information, transition history, and action results.
    """

    def __init__(self, fingerprint: str, activity: str):
        """
        Initialize a memory state.
        
        Args:
            fingerprint: Unique identifier for the state
            activity: Activity name
        """
        self.fingerprint = fingerprint
        self.activity = activity
        self.visit_count = 0
        self.first_visit = time.time()
        self.last_visit = time.time()
        self.successful_actions = set()  # deprecated
        self.failed_actions = set()  # deprecated
        self.all_actions = set()
        self.outgoing_transitions = {}
        self.incoming_transitions = {}
        self.interactive_elements_count = 0
        self.screenshot_path = None  # deprecated

    def record_visit(self):
        """Record a visit to this state."""
        self.visit_count += 1
        self.last_visit = time.time()

    def record_action(self, action_id: int, success: bool):
        """
        Record an action executed in this state.
        
        Args:
            action_id: Action identifier
            success: Whether the action was successful
        """
        self.all_actions.add(action_id)
        if success:
            self.successful_actions.add(action_id)
        else:
            self.failed_actions.add(action_id)

    def set_screenshot(self, path: Optional[str]):
        """
        Set the screenshot path for this state.

        Args:
            path: Path to screenshot file
        """
        if path:
            self.screenshot_path = path

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary representation
        """
        return {
            "fingerprint": self.fingerprint,
            "activity": self.activity,
            "visit_count": self.visit_count,
            "first_visit": self.first_visit,
            "last_visit": self.last_visit,
            "successful_actions": list(self.successful_actions),
            "failed_actions": list(self.failed_actions),
            "all_actions": list(self.all_actions),
            "outgoing_transitions": self.outgoing_transitions,
            "incoming_transitions": self.incoming_transitions,
            "interactive_elements_count": self.interactive_elements_count,
            "screenshot_path": self.screenshot_path
        }

class MemoryAction:
    """
    Represents an action in memory.
    
    Tracks execution history, success rate, and transitions caused by this action.
    """

    def __init__(self, action_id: int, text: str, action_type: str):
        """
        Initialize a memory action.
        
        Args:
            action_id: Unique identifier for the action
            text: Text description of the action
            action_type: Type of action (e.g., click, long_click)
        """
        self.id = action_id
        self.text = text
        self.type = action_type
        self.execution_count = 0
        self.success_count = 0  # TODO deprecated
        self.failure_count = 0  # TODO deprecated
        self.state_transitions = defaultdict(list)  # TODO entender
        self.element_properties = {}  # TODO entender
        self.reaches_mop = False
        self.directly_reaches_mop = False

    def record_execution(self, success: bool):
        """
        Record an execution of this action.
        
        Args:
            success: Whether the execution was successful
        """
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

    def record_transition(self, from_state: str, to_state: str):
        """
        Record a state transition caused by this action.
        
        Args:
            from_state: Source state fingerprint
            to_state: Destination state fingerprint
        """
        if to_state not in self.state_transitions[from_state]:
            self.state_transitions[from_state].append(to_state)

    def get_success_rate(self) -> float:
        """
        Get the success rate of this action.
        
        Returns:
            Success rate between 0.0 and 1.0
        """
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "text": self.text,
            "type": self.type,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "state_transitions": dict(self.state_transitions),
            "element_properties": self.element_properties,
            "reaches_mop": self.reaches_mop,
            "directly_reaches_mop": self.directly_reaches_mop
        }

    @classmethod
    def from_action(cls, action: GeneratedAction) -> 'MemoryAction':
        """
        Create from an ItemAction.
        
        Args:
            action: ItemAction instance
            
        Returns:
            MemoryAction instance
        """
        memory_action = cls(action.id, action.text, action.action_type)
        memory_action.reaches_mop = action.reaches_mop
        memory_action.directly_reaches_mop = action.directly_reaches_mop

        # Extract element properties if available
        if hasattr(action, 'target_view') and action.target_view:
            memory_action.element_properties = {
                "class": action.target_view.get("class", ""),
                "text": action.target_view.get("text", ""),
                "content_description": action.target_view.get("content_description", ""),
                "resource_id": action.target_view.get("resource_id", ""),
                "clickable": action.target_view.get("clickable", False),
                "enabled": action.target_view.get("enabled", False)
            }

        return memory_action


class LongTermMemory:
    """
    Long-term memory system for RV-Android.
    
    ### Architectural Decisions:
    - Implements a persistent memory system that outlasts individual test sessions
    - Provides comprehensive tracking of states, actions, and transitions
    - Supports both in-memory and serialized storage
    - Maintains statistics for exploration analysis and guidance
    - Integrates static analysis data for enhanced context
    
    ### Role in the System:
    - Serves as the primary long-term memory component for all tools
    - Enables history-aware testing and exploration
    - Facilitates pattern detection and optimization
    - Provides comprehensive application behavior tracking
    - Supports intelligent exploration through memory-based guidance
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the long-term memory system.
        
        Args:
            static_data: Optional static analysis data
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvsmart_tool.core.memory.long_term_memory",
            {CONTEXT_COMPONENT: "LongTermMemory"}
        )

        # Initialize core parameters
        self.static_data = static_data
        self.creation_time = time.time()

        # Initialize data structures
        self.states: Dict[str, MemoryState] = {}  # Fingerprint -> MemoryState
        self.actions = {}  # Action ID -> MemoryAction  # TODO deprecated
        self.activities = {}  # Activity name -> Activity info
        self.transitions = []  # List of transitions

        # Statistics
        self.total_states = 0
        self.total_activities = 0
        self.total_actions = 0
        self.total_transitions = 0
        self.successful_actions = 0  # TODO deprecated
        self.failed_actions = 0  # TODO deprecated

        self.logger.info(f"Initialized long-term memory")

    def record_state(self, state: MemoryState) -> None:
        """
        Record or update a state in memory.
        
        Args:
            state: State to record
        """
        # Check if this is a new state
        is_new_state = state.fingerprint not in self.states

        # Update statistics for new states
        if is_new_state:
            self.total_states += 1

            # Update activity statistics
            activity = state.activity
            if activity not in self.activities:
                self.activities[activity] = {
                    "first_seen": time.time(),
                    "visit_count": 0,
                    "states": []
                }
                self.total_activities += 1

            # Add state to activity
            if state.fingerprint not in self.activities[activity]["states"]:
                self.activities[activity]["states"].append(state.fingerprint)

        # Update or add state
        if is_new_state:
            self.states[state.fingerprint] = state
        else:
            # Update existing state
            existing_state: MemoryState = self.states[state.fingerprint]
            existing_state.record_visit()

            # Update screenshot if available
            if state.screenshot_path:
                existing_state.set_screenshot(state.screenshot_path)

            # Update interactive elements count if available
            if state.interactive_elements_count > 0:
                existing_state.interactive_elements_count = state.interactive_elements_count

        # Update activity visit count
        if state.activity in self.activities:
            self.activities[state.activity]["visit_count"] += 1
            self.activities[state.activity]["last_seen"] = time.time()

    # TODO rever, pois o ID da action eh unico apenas na tela atual
    def record_action(self, action: MemoryAction, state_fingerprint: str, success: bool) -> None:
        """
        Record an action execution.
        
        Args:
            action: Action that was executed
            state_fingerprint: State in which the action was executed
            success: Whether the execution was successful
        """
        # Update action statistics
        if success:
            self.successful_actions += 1
        else:
            self.failed_actions += 1

        # Update or add action
        if action.id in self.actions:
            self.actions[action.id].record_execution(success)
        else:
            action.record_execution(success)
            self.actions[action.id] = action
            self.total_actions += 1

        # Update state with action
        if state_fingerprint in self.states:
            self.states[state_fingerprint].record_action(action.id, success)

    # TODO: rever apenas uma acao???
    # TODO deprecated ??
    def record_transition(self, from_state: str, to_state: str, action: MemoryAction, success: bool) -> None:
        """
        Record a state transition.
        
        Args:
            from_state: Source state fingerprint
            to_state: Destination state fingerprint
            action: Action that caused the transition
            success: Whether the transition was successful
        """
        self.logger.info(f"Recording transition from {from_state} to {to_state} with action {action}")
        # Only record successful transitions
        if not success:
            return

        # Record transition in action
        if action.id in self.actions:
            self.actions[action.id].record_transition(from_state, to_state)

        # Record transition in states
        if from_state in self.states:
            if to_state not in self.states[from_state].outgoing_transitions:
                self.states[from_state].outgoing_transitions[to_state] = []
            self.states[from_state].outgoing_transitions[to_state].append({
                "action_id": action.id,
                "timestamp": time.time()
            })

        if to_state in self.states:
            if from_state not in self.states[to_state].incoming_transitions:
                self.states[to_state].incoming_transitions[from_state] = []
            self.states[to_state].incoming_transitions[from_state].append({
                "action_id": action.id,
                "timestamp": time.time()
            })

        # Record in transitions list
        self.transitions.append({
            "from_state": from_state,
            "to_state": to_state,
            "action_id": action.id,
            "timestamp": time.time()
        })
        self.logger.info(f"Transition added from:{from_state} to:{to_state} with action={action.to_dict()}")

        self.total_transitions += 1

    def get_state_by_fingerprint(self, fingerprint: str) -> Optional[MemoryState]:
        """
        Get a state by its fingerprint.
        
        Args:
            fingerprint: State fingerprint
            
        Returns:
            MemoryState or None if not found
        """
        return self.states.get(fingerprint)

    def get_action_by_id(self, action_id: int) -> Optional[MemoryAction]:
        """
        Get an action by its ID.
        
        Args:
            action_id: Action ID
            
        Returns:
            MemoryAction or None if not found
        """
        return self.actions.get(action_id)

    def get_least_visited_activities(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get the least visited activities.
        
        Args:
            count: Number of activities to return
            
        Returns:
            List of activity info dictionaries
        """
        if not self.activities:
            return []

        # Sort activities by visit count
        sorted_activities = sorted(
            [(name, info) for name, info in self.activities.items()],
            key=lambda x: x[1]["visit_count"]
        )

        # Return the least visited
        return [
            {
                "name": name,
                "visit_count": info["visit_count"],
                "first_seen": info["first_seen"],
                "last_seen": info.get("last_seen", info["first_seen"]),
                "state_count": len(info["states"])
            }
            for name, info in sorted_activities[:count]
        ]

    def get_actions_for_coverage(self, target_activity: str) -> List[Tuple[int, float]]:
        """
        Find actions that might lead to the target activity.
        
        Args:
            target_activity: Activity to reach
            
        Returns:
            List of (action_id, confidence) tuples
        """
        candidate_actions = []

        # Find states in the target activity
        target_states = []
        for fingerprint, state in self.states.items():
            if state.activity == target_activity:
                target_states.append(fingerprint)

        if not target_states:
            return []

        # Find actions that have transitions to these states
        for action_id, action in self.actions.items():
            highest_confidence = 0.0

            for from_state, to_states in action.state_transitions.items():
                # Calculate confidence based on transition frequency
                for to_state in to_states:
                    if to_state in target_states:
                        # Count how many times this transition happened
                        transition_count = 0
                        for transition in self.transitions:
                            if (transition["from_state"] == from_state and
                                    transition["to_state"] == to_state and
                                    transition["action_id"] == action_id):
                                transition_count += 1

                        # Calculate confidence
                        confidence = min(1.0, transition_count / 5.0)  # Max confidence after 5 transitions
                        highest_confidence = max(highest_confidence, confidence)

            if highest_confidence > 0:
                candidate_actions.append((action_id, highest_confidence))

        # Sort by confidence
        return sorted(candidate_actions, key=lambda x: x[1], reverse=True)

    def suggest_next_activity(self) -> Optional[str]:
        """
        Suggest the next activity to explore based on visit count.
        
        Returns:
            Activity name or None if no activities
        """
        # Get least visited activities
        least_visited = self.get_least_visited_activities(1)

        if not least_visited:
            return None

        return least_visited[0]["name"]

    def get_activity_visit_count(self, activity: str) -> int:
        """
        Get the number of times an activity has been visited.
        
        Args:
            activity: Activity name
            
        Returns:
            Visit count for the activity
        """
        if activity in self.activities:
            return self.activities[activity]["visit_count"]
        return 0

    def get_activity_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about all visited activities.
        
        Returns:
            Dictionary with activity statistics
        """
        statistics = {
            "total_activities": self.total_activities,
            "activities": []
        }

        # Sort activities by visit count (most visited first)
        sorted_activities = sorted(
            [(name, info) for name, info in self.activities.items()],
            key=lambda x: x[1]["visit_count"],
            reverse=True
        )

        # Collect statistics for each activity
        for name, info in sorted_activities:
            activity_stats = {
                "name": name,
                "visit_count": info["visit_count"],
                "states_count": len(info["states"]),
                "first_seen": info["first_seen"],
                "last_seen": info.get("last_seen", info["first_seen"])
            }
            statistics["activities"].append(activity_stats)

        return statistics

    def get_visited_activities(self) -> List[str]:
        """
        Get a list of visited activities in chronological order.
        
        Returns:
            List of activity names in order of first visit
        """
        if not self.activities:
            return []

        # Sort activities by first_seen timestamp
        sorted_activities = sorted(
            [(name, info) for name, info in self.activities.items()],
            key=lambda x: x[1]["first_seen"]
        )

        # Extract just the activity names
        return [name for name, _ in sorted_activities]

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        return {
            "total_states": self.total_states,
            "total_activities": self.total_activities,
            "total_actions": self.total_actions,
            "total_transitions": self.total_transitions,
            "creation_time": self.creation_time,
            "runtime": time.time() - self.creation_time
        }

# rvandroid/rvdroid/memory/state/memory_state.py

"""
Memory state module for RVDroid.

This module provides a unified representation of application states in memory,
supporting both short-term and long-term memory systems.
"""

import time
from typing import Dict, Any, Set

from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class MemoryState:
    """
    Represents an application state in memory.

    ### Architectural Decisions:
    - Implements a comprehensive state model with hierarchical properties
    - Separates stable identity (fingerprint) from state properties
    - Supports tracking of state visits, transitions, and executed actions
    - Enables efficient memory management through selective property storage

    ### Role in the System:
    - Provides a uniform state representation across memory systems
    - Enables efficient tracking of state properties and metrics
    - Supports analysis of state characteristics and transitions
    - Facilitates memory optimization through selective property storage
    """

    def __init__(self, fingerprint: str, activity: str,
                 visit_timestamp: float = None):
        """
        Initialize a memory state.

        Args:
            fingerprint: State fingerprint
            activity: Activity name
            visit_timestamp: Timestamp of first visit
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.memory.memory_state",
            {CONTEXT_COMPONENT: "MemoryState"}
        )

        # Core identity
        self.fingerprint = fingerprint
        self.activity = activity

        # Visit tracking
        self.first_visit = visit_timestamp or time.time()
        self.last_visit = self.first_visit
        self.visit_count = 1

        # Action tracking
        self.successful_actions: Set[int] = set()
        self.failed_actions: Set[int] = set()
        self.all_actions: Set[int] = set()

        # State properties
        self.properties: Dict[str, Any] = {}

        # UI elements count
        self.interactive_elements_count = 0

        # Transitions
        self.outgoing_transitions: Dict[str, Set[int]] = {}  # target_state -> action_ids
        self.incoming_transitions: Dict[str, Set[int]] = {}  # source_state -> action_ids

        # Monitored operations (formerly security operations)
        self.monitored_operations: Set[int] = set()

        # Screenshot path (if available)
        self.screenshot_path = None

        self.logger.debug(f"Created memory state with fingerprint {fingerprint}")

    def record_visit(self) -> None:
        """Record a visit to this state."""
        self.visit_count += 1
        self.last_visit = time.time()

    def record_action(self, action_id: int, success: bool) -> None:
        """
        Record an action executed in this state.

        Args:
            action_id: ID of the executed action
            success: Whether the action was successful
        """
        self.all_actions.add(action_id)

        if success:
            self.successful_actions.add(action_id)
        else:
            self.failed_actions.add(action_id)

    def record_transition(self, action_id: int, target_state: str) -> None:
        """
        Record a transition to another state.

        Args:
            action_id: ID of the action that caused the transition
            target_state: Fingerprint of the target state
        """
        if target_state not in self.outgoing_transitions:
            self.outgoing_transitions[target_state] = set()

        self.outgoing_transitions[target_state].add(action_id)

    def record_incoming_transition(self, action_id: int, source_state: str) -> None:
        """
        Record an incoming transition from another state.

        Args:
            action_id: ID of the action that caused the transition
            source_state: Fingerprint of the source state
        """
        if source_state not in self.incoming_transitions:
            self.incoming_transitions[source_state] = set()

        self.incoming_transitions[source_state].add(action_id)

    def set_screenshot(self, path: str) -> None:
        """
        Set the screenshot path for this state.

        Args:
            path: Path to screenshot
        """
        self.screenshot_path = path

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary representation.

        Returns:
            Dictionary representation
        """
        return {
            "fingerprint": self.fingerprint,
            "activity": self.activity,
            "first_visit": self.first_visit,
            "last_visit": self.last_visit,
            "visit_count": self.visit_count,
            "successful_actions": list(self.successful_actions),
            "failed_actions": list(self.failed_actions),
            "interactive_elements_count": self.interactive_elements_count,
            "outgoing_transitions": {
                target: list(actions)
                for target, actions in self.outgoing_transitions.items()
            },
            "incoming_transitions": {
                source: list(actions)
                for source, actions in self.incoming_transitions.items()
            },
            "monitored_operations": list(self.monitored_operations),
            "screenshot_path": self.screenshot_path,
            "properties": self.properties
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryState':
        """
        Create a memory state from dictionary representation.

        Args:
            data: Dictionary representation

        Returns:
            Memory state instance
        """
        state = cls(
            fingerprint=data["fingerprint"],
            activity=data["activity"],
            visit_timestamp=data["first_visit"]
        )

        state.last_visit = data["last_visit"]
        state.visit_count = data["visit_count"]
        state.successful_actions = set(data["successful_actions"])
        state.failed_actions = set(data["failed_actions"])
        state.interactive_elements_count = data["interactive_elements_count"]

        # Convert transitions back to sets
        for target, actions in data["outgoing_transitions"].items():
            state.outgoing_transitions[target] = set(actions)

        for source, actions in data["incoming_transitions"].items():
            state.incoming_transitions[source] = set(actions)

        # Handle both new and old format for backward compatibility
        if "monitored_operations" in data:
            state.monitored_operations = set(data["monitored_operations"])
        elif "security_operations" in data:
            state.monitored_operations = set(data["security_operations"])
        
        state.screenshot_path = data["screenshot_path"]
        state.properties = data["properties"]

        return state
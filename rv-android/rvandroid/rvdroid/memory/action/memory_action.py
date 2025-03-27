# rvandroid/rvdroid/memory/action/memory_action.py

"""
Memory action module for RVDroid.

This module provides a representation of actions in memory systems,
supporting both short-term and long-term tracking of action execution.
"""

import time
from typing import Dict, Any, Optional

from rvandroid.parser.screen.visitor.base_visitor import ItemAction
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class MemoryAction:
    """
    Represents an action in memory.

    ### Architectural Decisions:
    - Implements a lightweight action model focused on essential execution metrics
    - Maintains clear separation between action identity and execution history
    - Tracks state transitions and success rates with minimal overhead
    - Provides efficient comparison and persistence mechanisms
    - Supports intelligent categorization of actions based on properties

    ### Role in the System:
    - Provides a unified action representation across memory systems
    - Enables efficient tracking of action execution and outcomes
    - Supports analysis of action effectiveness and security implications
    - Facilitates prediction of action outcomes in similar states
    """

    def __init__(self, action_id: int, action_text: str, action_type: str):
        """
        Initialize a memory action.

        Args:
            action_id: Unique action ID
            action_text: Action description text
            action_type: Type of action (click, long_click, etc.)
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.memory.memory_action",
            {CONTEXT_COMPONENT: "MemoryAction"}
        )

        # Core identity
        self.id = action_id
        self.text = action_text
        self.type = action_type

        # Execution tracking
        self.execution_count = 0
        self.success_count = 0
        self.first_execution = None
        self.last_execution = None

        # State transitions
        self.state_transitions: Dict[str, Dict[str, int]] = {}  # from_state -> {to_state -> count}

        # Security properties
        self.reaches_mop = False
        self.directly_reaches_mop = False

        # Element properties (extracted from original action)
        self.element_properties: Dict[str, Any] = {}

        self.logger.debug(f"Created memory action with ID {action_id}")

    def record_execution(self, from_state: str, to_state: str, success: bool) -> None:
        """
        Record execution of this action.

        Args:
            from_state: Source state fingerprint
            to_state: Target state fingerprint
            success: Whether the execution was successful
        """
        # Update execution counts
        self.execution_count += 1
        if success:
            self.success_count += 1

        # Update timestamps
        now = time.time()
        if not self.first_execution:
            self.first_execution = now
        self.last_execution = now

        # Update state transitions
        if from_state not in self.state_transitions:
            self.state_transitions[from_state] = {}

        if to_state in self.state_transitions[from_state]:
            self.state_transitions[from_state][to_state] += 1
        else:
            self.state_transitions[from_state][to_state] = 1

    def get_success_rate(self, state: Optional[str] = None) -> float:
        """
        Get success rate of this action, optionally for a specific state.

        Args:
            state: Optional state fingerprint to get success rate for

        Returns:
            Success rate (0.0 to 1.0)
        """
        if state is not None:
            # Calculate success rate for specific state
            if state in self.state_transitions:
                transitions = self.state_transitions[state]
                total = sum(transitions.values())
                if total > 0:
                    # Count transitions to non-identical states as success
                    success = sum(count for target, count in transitions.items() if target != state)
                    return success / total
            return 0.0

        # Calculate overall success rate
        if self.execution_count > 0:
            return self.success_count / self.execution_count
        return 0.0

    def set_security_properties(self, reaches_mop: bool, directly_reaches_mop: bool) -> None:
        """
        Set security properties of this action.

        Args:
            reaches_mop: Whether this action reaches a MOP method
            directly_reaches_mop: Whether this action directly reaches a MOP method
        """
        self.reaches_mop = reaches_mop
        self.directly_reaches_mop = directly_reaches_mop

    def extract_properties_from_item_action(self, action: ItemAction) -> None:
        """
        Extract properties from an ItemAction.

        Args:
            action: Source ItemAction
        """
        if hasattr(action, 'target_view') and action.target_view:
            view = action.target_view
            self.element_properties = {
                "class": view.get("class", ""),
                "resource_id": view.get("resource_id", ""),
                "text": view.get("text", ""),
                "content_desc": view.get("content_description", ""),
                "clickable": view.get("clickable", False),
                "long_clickable": view.get("long_clickable", False),
                "checkable": view.get("checkable", False),
                "checked": view.get("checked", False),
                "scrollable": view.get("scrollable", False),
                "password": view.get("password", False)
            }

    def is_similar_to(self, other: 'MemoryAction') -> bool:
        """
        Check if this action is similar to another action.

        Args:
            other: Other action to compare with

        Returns:
            True if similar, False otherwise
        """
        # Same action type is required
        if self.type != other.type:
            return False

        # Check element properties for similarity
        if self.element_properties and other.element_properties:
            # Same class is strong indicator
            if (self.element_properties.get("class") == other.element_properties.get("class") and
                    self.element_properties.get("class")):
                return True

            # Same resource ID is strong indicator
            if (self.element_properties.get("resource_id") == other.element_properties.get("resource_id") and
                    self.element_properties.get("resource_id")):
                return True

            # Same text is moderate indicator if non-empty
            if (self.element_properties.get("text") == other.element_properties.get("text") and
                    self.element_properties.get("text")):
                return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert action to dictionary representation.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "text": self.text,
            "type": self.type,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "first_execution": self.first_execution,
            "last_execution": self.last_execution,
            "state_transitions": self.state_transitions,
            "reaches_mop": self.reaches_mop,
            "directly_reaches_mop": self.directly_reaches_mop,
            "element_properties": self.element_properties
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryAction':
        """
        Create a memory action from dictionary representation.

        Args:
            data: Dictionary representation

        Returns:
            Memory action instance
        """
        action = cls(
            action_id=data["id"],
            action_text=data["text"],
            action_type=data["type"]
        )

        action.execution_count = data["execution_count"]
        action.success_count = data["success_count"]
        action.first_execution = data["first_execution"]
        action.last_execution = data["last_execution"]
        action.state_transitions = data["state_transitions"]
        action.reaches_mop = data["reaches_mop"]
        action.directly_reaches_mop = data["directly_reaches_mop"]
        action.element_properties = data["element_properties"]

        return action

    @classmethod
    def from_item_action(cls, action: ItemAction) -> 'MemoryAction':
        """
        Create a memory action from an ItemAction.

        Args:
            action: Source ItemAction

        Returns:
            Memory action instance
        """
        # Extract action type from text
        action_type = cls._get_action_type_from_text(action.text)

        # Create memory action
        memory_action = cls(
            action_id=action.id,
            action_text=action.text,
            action_type=action_type
        )

        # Extract security properties
        memory_action.set_security_properties(
            reaches_mop=getattr(action, 'reaches_mop', False),
            directly_reaches_mop=getattr(action, 'directly_reaches_mop', False)
        )

        # Extract element properties
        memory_action.extract_properties_from_item_action(action)

        return memory_action

    @staticmethod
    def _get_action_type_from_text(action_text: str) -> str:
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

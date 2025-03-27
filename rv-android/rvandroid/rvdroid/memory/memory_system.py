# rvandroid/rvdroid/memory/memory_system.py

"""
Memory system module for RVDroid.

This module provides a centralized memory system that integrates all memory components,
offering a unified interface for state tracking, action recording, and pattern detection.
"""

from typing import Dict, Any, List, Optional

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.rvdroid.memory.action.memory_action import MemoryAction
from rvandroid.rvdroid.memory.exploration.exploration_optimizer import ExplorationOptimizer
from rvandroid.rvdroid.memory.long_term.long_term_memory import LongTermMemory
from rvandroid.rvdroid.memory.patterns.pattern_recognition import PatternRecognition
from rvandroid.rvdroid.memory.short_term.short_term_memory import ShortTermMemory
from rvandroid.rvdroid.memory.state.memory_state import MemoryState
from rvandroid.rvdroid.memory.state.state_fingerprinter import StateFingerprinter
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class MemorySystem:
    """
    Integrated memory system for RVDroid.

    ### Architectural Decisions:
    - Implements a centralized system that integrates all memory components
    - Provides a unified interface for state tracking and action recording
    - Uses a modular architecture with clear separation of responsibilities
    - Efficiently coordinates information flow between memory components
    - Supports flexible exploration optimization based on comprehensive memory

    ### Role in the System:
    - Serves as the central memory management facility
    - Coordinates information flow between memory components
    - Provides consistent access to application state history
    - Enables sophisticated pattern detection and exploration optimization
    - Guides testing strategies through memory-based insights
    """

    def __init__(self, app_package: str, static_data: Optional[StaticAnalysisData] = None,
                 short_term_capacity: int = 50):
        """
        Initialize the memory system.

        Args:
            app_package: Application package name
            static_data: Optional static analysis data
            short_term_capacity: Capacity of short-term memory
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.memory.memory_system",
            {CONTEXT_COMPONENT: "MemorySystem"}
        )

        # Initialize core parameters
        self.app_package = app_package
        self.static_data = static_data

        # Initialize state fingerprinter
        self.fingerprinter = StateFingerprinter()

        # Initialize memory components
        self.short_term_memory = ShortTermMemory(capacity=short_term_capacity)
        self.long_term_memory = LongTermMemory(app_package, static_data)

        # Initialize pattern recognition and exploration optimizer
        self.pattern_recognition = PatternRecognition(self.short_term_memory, self.long_term_memory)
        self.exploration_optimizer = ExplorationOptimizer(
            self.short_term_memory,
            self.long_term_memory,
            self.pattern_recognition
        )

        # Last state and action tracking for transitions
        self.last_state_fingerprint = None
        self.last_action = None

        self.logger.info(f"Initialized memory system for {app_package}")

    def process_state(self, screen: ScreenDescription,
                      state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an application state.

        Args:
            screen: Parsed screen description
            state_data: Raw state data

        Returns:
            Processed state information including fingerprint and analysis
        """
        # Generate state fingerprint
        fingerprint = self.fingerprinter.generate_fingerprint(screen, state_data)

        # Determine if this is a new state
        is_new_state = fingerprint != self.last_state_fingerprint

        # Update the state data with fingerprint
        state_data["fingerprint"] = fingerprint

        # Create memory state object
        memory_state = MemoryState(
            fingerprint=fingerprint,
            activity=state_data.get("activity", "unknown")
        )

        # Set additional properties
        memory_state.interactive_elements_count = len(screen.items)
        memory_state.set_screenshot(state_data.get("screenshot_path"))

        # Record state in memory systems
        self.short_term_memory.record_state(memory_state)
        self.long_term_memory.record_state(memory_state, is_new_state)

        # Record transition if this is a new state and we have a previous action
        if is_new_state and self.last_state_fingerprint and self.last_action:
            self._record_transition(self.last_state_fingerprint, fingerprint, self.last_action)

        # Update last state tracking
        self.last_state_fingerprint = fingerprint

        # Create result
        result = {
            "fingerprint": fingerprint,
            "is_new_state": is_new_state,
            "memory_state": memory_state
        }

        # Scan for patterns if this is a good opportunity
        if is_new_state and len(self.short_term_memory.state_history) > 10:
            result["patterns"] = self._analyze_patterns()

        return result

    def process_action(self, action: ItemAction, success: bool) -> Dict[str, Any]:
        """
        Process an executed action.

        Args:
            action: Action that was executed
            success: Whether the action was successful

        Returns:
            Processed action information
        """
        # Create memory action
        memory_action = MemoryAction.from_item_action(action)

        # Record in memory systems
        self.short_term_memory.record_action(memory_action, success)

        if self.last_state_fingerprint:
            self.long_term_memory.record_action(memory_action, self.last_state_fingerprint, success)

        # Record for exploration optimizer
        self.exploration_optimizer.record_action_result(action, {"success": success})

        # Update last action tracking
        self.last_action = memory_action

        # Create result
        result = {
            "action_id": action.id,
            "success": success,
            "memory_action": memory_action
        }

        return result

    def optimize_actions(self, screen: ScreenDescription,
                         state_data: Dict[str, Any],
                         available_actions: List[ItemAction]) -> List[ItemAction]:
        """
        Optimize the order of actions based on exploration strategy.

        Args:
            screen: Parsed screen description
            state_data: State data dictionary
            available_actions: List of available actions

        Returns:
            Re-prioritized list of actions
        """
        return self.exploration_optimizer.optimize_action_selection(
            screen, state_data, available_actions
        )

    def get_state_info(self, fingerprint: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get information about a state.

        Args:
            fingerprint: State fingerprint or None for current state

        Returns:
            State information or None if not found
        """
        # Use last state fingerprint if none provided
        if fingerprint is None:
            fingerprint = self.last_state_fingerprint

        if not fingerprint:
            return None

        # Try to get state from short-term memory first
        state = None
        for s in self.short_term_memory.states.values():
            if s.fingerprint == fingerprint:
                state = s
                break

        # If not found, try long-term memory
        if not state and self.long_term_memory:
            state = self.long_term_memory.get_state_by_fingerprint(fingerprint)

        if not state:
            return None

        # Create result
        result = {
            "fingerprint": state.fingerprint,
            "activity": state.activity,
            "visit_count": state.visit_count,
            "first_visit": state.first_visit,
            "last_visit": state.last_visit,
            "action_count": len(state.all_actions),
            "successful_actions": list(state.successful_actions),
            "failed_actions": list(state.failed_actions),
            "outgoing_transitions": state.outgoing_transitions,
            "incoming_transitions": state.incoming_transitions,
            "screenshot_path": state.screenshot_path
        }

        return result

    def get_action_info(self, action_id: int) -> Optional[Dict[str, Any]]:
        """
        Get information about an action.

        Args:
            action_id: Action ID

        Returns:
            Action information or None if not found
        """
        # Try to get action from short-term memory first
        action = None
        if action_id in self.short_term_memory.actions:
            action = self.short_term_memory.actions[action_id]

        # If not found, try long-term memory
        if not action and self.long_term_memory and action_id in self.long_term_memory.actions:
            action = self.long_term_memory.actions[action_id]

        if not action:
            return None

        # Create result
        result = {
            "id": action.id,
            "text": action.text,
            "type": action.type,
            "execution_count": action.execution_count,
            "success_count": action.success_count,
            "success_rate": action.get_success_rate(),
            "reaches_mop": action.reaches_mop,
            "directly_reaches_mop": action.directly_reaches_mop,
            "element_properties": action.element_properties
        }

        return result

    def get_patterns(self) -> Dict[str, Any]:
        """
        Get detected patterns.

        Returns:
            Dictionary with detected patterns
        """
        return {
            "action_patterns": self.pattern_recognition.detect_common_action_sequences(),
            "form_patterns": self.pattern_recognition.detect_form_filling_patterns(),
            "cycles": self.pattern_recognition.detect_cycles()
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics.

        Returns:
            Dictionary with memory statistics
        """
        return {
            "short_term": self.short_term_memory.get_memory_stats(),
            "long_term": self.long_term_memory.get_memory_stats(),
            "patterns": self.pattern_recognition.get_pattern_stats()
        }

    def _record_transition(self, from_state: str, to_state: str, action: MemoryAction) -> None:
        """
        Record a state transition in memory systems.

        Args:
            from_state: Source state fingerprint
            to_state: Destination state fingerprint
            action: Action that caused the transition
        """
        # Record in short-term memory
        self.short_term_memory.record_transition(from_state, to_state, action, True)

        # Record in long-term memory
        self.long_term_memory.record_transition(from_state, to_state, action, True)

    def _analyze_patterns(self) -> Dict[str, Any]:
        """
        Analyze patterns in short-term memory.

        Returns:
            Dictionary with pattern analysis results
        """
        action_patterns = self.pattern_recognition.analyze_action_sequences()
        state_patterns = self.pattern_recognition.analyze_state_transitions()

        return {
            "action_patterns": [p.to_dict() for p in action_patterns],
            "state_patterns": [p.to_dict() for p in state_patterns],
            "action_pattern_count": len(action_patterns),
            "state_pattern_count": len(state_patterns)
        }

    def save_memory(self, file_path: str) -> bool:
        """
        Save long-term memory to disk.

        Args:
            file_path: Path to save the memory

        Returns:
            True if successful, False otherwise
        """
        return self.long_term_memory.save(file_path)

    def load_memory(self, file_path: str) -> bool:
        """
        Load long-term memory from disk.

        Args:
            file_path: Path to load the memory from

        Returns:
            True if successful, False otherwise
        """
        return self.long_term_memory.load(file_path)

    def get_recent_states(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent states.

        Args:
            count: Number of states to retrieve

        Returns:
            List of recent states in dictionary format
        """
        memory_states = self.short_term_memory.get_recent_states(count)

        # Convert to dictionary format for use by other systems
        return [
            {
                "fingerprint": state.fingerprint,
                "activity": state.activity,
                "timestamp": state.last_visit,
                "visit_count": state.visit_count,
                "interactive_elements_count": state.interactive_elements_count
            }
            for state in memory_states
        ]

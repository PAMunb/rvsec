# rvandroid/core/memory/short_term_memory.py
"""
Short-term memory system for tracking recent interactions within the current screen.

This module provides a memory system that retains information about recent
interactions with the current screen, including executed actions and their results.
The memory is cleared when navigating to a different screen.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.llm.constants import StateEntry
from rvandroid_tool.llm.service.action_generator import GeneratedAction


class Iteration:
    """
    Represents a single iteration of interaction with the current screen.
    Represents a call to LLM and the generated actions.

    ### Architectural Decisions:
    - Stores complete ItemAction instances to maintain full context
    - Tracks timestamps for ordering and age-based filtering
    - Maintains hash references to allow correlation with state data

    ### Role in the System:
    - Provides atomic unit of historical interaction data
    - Enables tracking of recently executed actions
    - Supports detailed history formatting for prompt templates
    """

    def __init__(self, state_hash: str, activity: str):
        """
        Initialize an iteration.

        Args:
            state_hash: Hash of the screen state
            activity: Current activity name
        """
        self.state_hash = state_hash
        self.activity = activity
        self.timestamp = datetime.now()
        self.actions: List[GeneratedAction] = []

    def add_action(self, action: GeneratedAction) -> None:
        """
        Add an action to this iteration.

        Args:
            action: The executed action
        """
        self.actions.append(action)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary representation
        """
        return {
            "state_hash": self.state_hash,
            "activity": self.activity,
            "timestamp": self.timestamp.isoformat(),
            "actions": [{"id": action.id, "text": action.text} for action in self.actions]
        }

    # TODO deprecated ... nao deve ficar aqui ... acho q no state bota o objeto de memoria e no fragment ele escreve do jeito q quiser
    def format_for_template(self) -> str:
        """
        Format iteration information for a template.

        Returns:
            Formatted string representation
        """
        action_texts = [f"{action.text}" for action in self.actions]

        # Format with timestamp and actions
        return f"[{self.timestamp.strftime('%H:%M:%S')}] Executed: {', '.join(action_texts)}"


class ShortTermMemory:
    """
    Manages short-term memory of interactions (LLM calls and generated actions) for the current screen.

    ### Architectural Decisions:
    - Maintains a screen-specific history of recent interactions
    - Implements an activity-based reset mechanism
    - Organizes iterations in chronological order for template usage
    - Limits history size to prevent context overload

    ### Role in the System:
    - Provides recent history for enhanced LLM context
    - Enables learning from recently executed actions
    - Facilitates improved action selection through pattern recognition
    - Delivers formatted history data for prompt templates
    """

    def __init__(self, max_iterations: int = 10):
        """
        Initialize the short-term memory.

        Args:
            max_iterations: Maximum number of iterations to keep in memory
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvandroid_tool.core.memory.short_term_memory",
            {CONTEXT_COMPONENT: "ShortTermMemory"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

        # Initialize memory
        self.current_activity: Optional[str] = None
        self.iterations: List[Iteration] = []
        self.max_iterations = max_iterations

        self.logger.info(f"Initialized short-term memory with max_iterations={max_iterations}")

    def record_iteration(self, state: Dict[str, Any], actions: List[GeneratedAction]) -> None:
        """
        Record a new iteration.

        Args:
            state: Current application state
            actions: List of executed actions
            result_message: Optional result/feedback message
        """
        try:
            # Get current activity and state hash
            activity = state.get(StateEntry.ACTIVITY, "unknown")

            # Use appropriate state hash - prefer content+structure hash if available
            state_hash = state.get(StateEntry.HASH_SCREEN, "unknown")

            # Check if activity has changed
            if activity != self.current_activity:
                self.logger.info(f"Activity changed from {self.current_activity} to {activity}, clearing memory")
                self.clear()
                self.current_activity = activity

            # Create new iteration
            iteration = Iteration(state_hash, activity)

            # Add actions
            for action in actions:
                iteration.add_action(action)

            # Add to iterations list
            self.iterations.insert(0, iteration)  # Add at the beginning (most recent first)

            # Prune if necessary
            if len(self.iterations) > self.max_iterations:
                self.iterations = self.iterations[:self.max_iterations]

            self.logger.info(f"Recorded iteration with {len(actions)} actions, memory size: {len(self.iterations)}")
            self.logger.info(f"Recent iterations: {self.iterations}")

        except Exception as e:
            self.logger.error(f"Error recording iteration: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ShortTermMemory",
                    "function": "record_iteration",
                    "activity": state.get(StateEntry.ACTIVITY, "unknown")
                }
            )

    def get_recent_iterations(self, count: int = 5) -> List[Iteration]:
        """
        Get the most recent iterations.

        Args:
            count: Number of iterations to return (default: 5)

        Returns:
            List of recent iterations (most recent first)
        """
        return self.iterations[:min(count, len(self.iterations))]

    def clear(self) -> None:
        """Clear the memory."""
        self.iterations = []
        self.logger.debug("Short-term memory cleared")

    def format_for_template(self, count: int = 5) -> str:
        """
        Format memory for template inclusion.

        Args:
            count: Number of iterations to include (default: 5)

        Returns:
            Formatted string representation
        """
        if not self.iterations:
            return "No recent actions on this screen."

        recent = self.get_recent_iterations(count)

        # Format header based on number of iterations
        if len(recent) == 1:
            header = "Recent action on this screen:"
        else:
            header = f"Recent actions on this screen (last {len(recent)}):"

        # Format each iteration
        formatted_iterations = [iteration.format_for_template() for iteration in recent]

        # Combine into a single string
        return header + "\n" + "\n".join(formatted_iterations)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary representation
        """
        return {
            "current_activity": self.current_activity,
            "iterations": [iteration.to_dict() for iteration in self.iterations]
        }

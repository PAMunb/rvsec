# rvandroid/llm/prompt/information/fragments/history_fragment.py
"""Testing history information fragment for the prompt system.

This module defines a specialized fragment for extracting and formatting testing
history information for use in prompt generation.
"""

from typing import Any, Dict, List, Optional

from rvandroid.llm.constants import FragmentType
from rvandroid.llm.prompt.information.base_fragment import InformationFragment
from rvandroid.util.error.error_handler import ErrorHandler


class HistoryFragment(InformationFragment):
    """Fragment for extracting and formatting testing history information.

    This fragment processes information about previously executed testing
    actions, their results, and discovered features to provide context for
    future action generation.

    ### Architectural Decisions:
    - Leverages both short-term and long-term memory systems
    - Formats historical data for readability and template integration
    - Prioritizes recent interactions for immediate context
    - Includes insights from long-term trends for exploration guidance

    ### Role in the System:
    - Provides historical context to improve LLM decision making
    - Enables learning from previous interactions and their outcomes
    - Helps avoid repetitive actions and explore new paths
    - Delivers targeted insights for the current screen context
    """

    def __init__(self, name: str = FragmentType.HISTORY, priority: int = 100):
        """Initialize the testing history fragment.

        Args:
            name: The name of the fragment (default: FragmentType.HISTORY).
            priority: The priority of the fragment (default: 100).
        """
        super().__init__(name, priority)
        self.error_handler = ErrorHandler.get_instance()
        self.max_history_entries = 5  # Limit history to last N entries

    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate testing history information from the state and context.

        Args:
            state: The current application state.
            context: Additional context information.

        Returns:
            A dictionary containing testing history information.
        """
        history = {}

        try:
            # Get action history from state (populated by MemoryManager)
            if "action_history" in state:
                # If action_history is a string, use it directly (formatted by MemoryManager)
                if isinstance(state["action_history"], str):
                    history["summary"] = state["action_history"]
                else:
                    # If it's still a list, format it
                    history["summary"] = self._format_action_history(state["action_history"])

            # Get memory insights if available
            if "memory_insights" in state:
                history["insights"] = state["memory_insights"]

            if not history:
                self.logger.debug("No testing history found")
                return {}

            return history

        except Exception as e:
            self.logger.error(f"Error generating history information: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"HistoryFragment",
                    "function": "generate"
                }
            )
            return {}

    def _format_action_history(self, actions: List[Dict[str, Any]]) -> str:
        """Format action history for display in the prompt.

        Args:
            actions: List of historical actions with results.

        Returns:
            Formatted action history.
        """
        # Limit to the last N entries to prevent context bloat
        actions = actions[-self.max_history_entries:] if len(actions) > self.max_history_entries else actions

        if not actions:
            return "No previous testing actions recorded."

        formatted_parts = [f"Recent testing history ({len(actions)} actions):"]

        # Add recent action descriptions
        for i, action in enumerate(actions):
            # Handle different action formats
            if isinstance(action, str):
                # Already formatted string
                formatted_parts.append(f"  {i + 1}. {action}")
            elif isinstance(action, dict):
                # Dictionary format with details
                action_type = action.get("action_type", "unknown")
                target = action.get("target", "")
                result = "succeeded" if action.get("success", False) else "failed"
                formatted_parts.append(f"  {i + 1}. {action_type} on {target} {result}")

        return "\n".join(formatted_parts)

    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if testing history information should be included.

        Args:
            state: The current application state.
            context: Additional context information.

        Returns:
            True if testing history information should be included, False otherwise.
        """
        # Include if action history is available in state
        if "action_history" in state or "memory_insights" in state:
            return True

        # Or if testing history is available in context
        if context and "testing_history" in context:
            return True

        return False

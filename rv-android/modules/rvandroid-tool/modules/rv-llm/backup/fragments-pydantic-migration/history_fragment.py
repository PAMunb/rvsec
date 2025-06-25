# rvandroid/llm/prompt/information/fragments/history_fragment.py
"""Testing history information fragment for the prompt system.

This module defines a specialized fragment for extracting and formatting testing
history information for use in prompt generation.
"""

from typing import Any, Dict, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_llm.llm.constants import FragmentType, StateEntry
from rv_llm.llm.prompt.information.base_fragment import InformationFragment


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
            if StateEntry.ACTION_HISTORY in state:
                # If action_history is a string, use it directly (formatted by MemoryManager)
                if isinstance(state[StateEntry.ACTION_HISTORY], str):
                    history["summary"] = state[StateEntry.ACTION_HISTORY]
                else:
                    # If it's still a list, format it
                    history["summary"] = self._format_action_history(state[StateEntry.ACTION_HISTORY])

            # Get memory insights if available
            if StateEntry.MEMORY_INSIGHTS in state:
                history["insights"] = state[StateEntry.MEMORY_INSIGHTS]

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

    def _format_action_history(self, actions) -> str:
        """Format action history for display in the prompt.

        Args:
            actions: List of historical actions with results (list of dicts or objects)

        Returns:
            Formatted action history.
        """
        # Limit to the last N entries to prevent context bloat
        if isinstance(actions, list):
            actions = actions[-self.max_history_entries:] if len(actions) > self.max_history_entries else actions
        else:
            # Already formatted string
            return actions

        if not actions:
            return "No previous testing actions recorded."

        formatted_parts = [f"Recent testing history ({len(actions)} actions):"]

        # Add recent action descriptions
        for i, action in enumerate(actions):
            # Handle different action formats
            if isinstance(action, str):
                # Already formatted string
                formatted_parts.append(f"  {i + 1}. {action}")
            elif hasattr(action, 'text') and hasattr(action, 'action_type'):
                # It's an Iteration or GeneratedAction object
                action_type = action.action_type
                target = getattr(action, 'target', '')
                text = action.text
                formatted_parts.append(f"  {i + 1}. {action_type} - {text}")
            elif isinstance(action, dict):
                # Dictionary format with details
                action_type = action.get("action_type", "unknown")
                target = action.get("target", "")
                text = action.get("text", "")
                result = "succeeded" if action.get("success", False) else "failed"
                formatted_parts.append(f"  {i + 1}. {action_type} - {text}")

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
        if StateEntry.ACTION_HISTORY in state or StateEntry.MEMORY_INSIGHTS in state:
            return True

        # Or if testing history is available in context
        if context and "testing_history" in context:
            return True

        return False

"""Testing history information fragment for the prompt system.

This module defines a specialized fragment for extracting and formatting testing
history information for use in prompt generation.
"""

from typing import Any, Dict, List, Optional

from rvandroid.llm.constants import FragmentType
from rvandroid.llm.prompt.information.base_fragment import InformationFragment


class HistoryFragment(InformationFragment):
    """Fragment for extracting and formatting testing history information.
    
    This fragment processes information about previously executed testing
    actions, their results, and discovered features to provide context for
    future action generation.
    """
    
    def __init__(self, name: str = FragmentType.HISTORY, priority: int = 100):
        """Initialize the testing history fragment.
        
        Args:
            name: The name of the fragment (default: FragmentType.HISTORY).
            priority: The priority of the fragment (default: 100).
        """
        super().__init__(name, priority)
        self.max_history_entries = 10  # Limit history to last N entries
    
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate testing history information from the state and context.
        
        Args:
            state: The current application state.
            context: Additional context information.
            
        Returns:
            A dictionary containing testing history information.
        """
        history = {}
        
        # First, check if history is available in context (preferred)
        if context and "testing_history" in context:
            raw_history = context["testing_history"]
            if isinstance(raw_history, list):
                history["actions"] = self._format_action_history(raw_history)
                history["summary"] = self._generate_summary(raw_history)
            elif isinstance(raw_history, str):
                # If history is provided as a string, use it directly
                history["summary"] = raw_history
            else:
                self.logger.warning("Testing history in unexpected format")
        
        # Then, check if state contains any history information
        elif state and "testing_history" in state:
            raw_history = state["testing_history"]
            if isinstance(raw_history, list):
                history["actions"] = self._format_action_history(raw_history)
                history["summary"] = self._generate_summary(raw_history)
            elif isinstance(raw_history, str):
                history["summary"] = raw_history
            else:
                self.logger.warning("Testing history in unexpected format")
        
        # Also include visited activities if available
        if state and "visited_activities" in state:
            history["visited_activities"] = state["visited_activities"]
        
        if not history:
            self.logger.debug("No testing history found")
            return {}
        
        return history
    
    def _format_action_history(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format action history for display in the prompt.
        
        Args:
            actions: List of historical actions with results.
            
        Returns:
            Formatted action history.
        """
        # Limit to the last N entries to prevent context bloat
        actions = actions[-self.max_history_entries:] if len(actions) > self.max_history_entries else actions
        
        formatted_actions = []
        for action in actions:
            # Extract relevant information, omitting unnecessary details
            formatted_action = {
                "action_type": action.get("action_type", "unknown"),
                "target": action.get("target", ""),
                "result": action.get("result", "unknown"),
                "success": action.get("success", False)
            }
            
            # Include interesting attributes that might vary by action type
            for key in ["input_value", "app_response", "discovered_elements"]:
                if key in action and action[key]:
                    formatted_action[key] = action[key]
            
            formatted_actions.append(formatted_action)
        
        return formatted_actions
    
    def _generate_summary(self, actions: List[Dict[str, Any]]) -> str:
        """Generate a human-readable summary of testing history.
        
        Args:
            actions: List of historical actions with results.
            
        Returns:
            A human-readable summary string.
        """
        if not actions:
            return "No previous testing actions recorded."
        
        # Limit to last N entries
        actions = actions[-self.max_history_entries:] if len(actions) > self.max_history_entries else actions
        
        # Count successful and failed actions
        success_count = sum(1 for action in actions if action.get("success", False))
        failure_count = len(actions) - success_count
        
        # Group actions by type
        action_types = {}
        for action in actions:
            action_type = action.get("action_type", "unknown")
            if action_type not in action_types:
                action_types[action_type] = 0
            action_types[action_type] += 1
        
        # Generate summary
        summary_parts = [
            f"Recent testing history ({len(actions)} actions, {success_count} successful, {failure_count} failed):"
        ]
        
        # Add action type breakdown
        action_type_summary = ", ".join(f"{count} {action_type}" for action_type, count in action_types.items())
        summary_parts.append(f"Action types: {action_type_summary}")
        
        # Add recent action descriptions
        summary_parts.append("Recent actions:")
        for i, action in enumerate(actions[-5:]):  # Show only the 5 most recent
            action_type = action.get("action_type", "unknown")
            target = action.get("target", "")
            result = "succeeded" if action.get("success", False) else "failed"
            summary_parts.append(f"  {i+1}. {action_type} on {target} {result}")
        
        return "\n".join(summary_parts)
    
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if testing history information should be included.
        
        Args:
            state: The current application state.
            context: Additional context information.
            
        Returns:
            True if testing history information should be included, False otherwise.
        """
        # Include if testing history is available in either state or context
        has_context_history = context is not None and "testing_history" in context
        has_state_history = state is not None and "testing_history" in state
        
        return has_context_history or has_state_history
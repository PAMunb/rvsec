"""
TransitionGuidanceFragment Module

This module provides a fragment that formats transition guidance information for LLM prompts.
The fragment extracts and formats transition data from the state to provide context about
navigation paths, transition history, and exploration guidance.

The fragment is responsible for:
1. Extracting transition guidance data from the state
2. Formatting the guidance data as a readable text for LLM consumption
3. Providing context about visited activities, unexplored actions, and suggested targets

Author: Claude
Date: 2025-05-04
"""

from typing import Dict, Any, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.llm.constants import StateEntry
from rv_android_core.llm.prompt.information.base_fragment import InformationFragment


class TransitionGuidanceFragment(InformationFragment):
    """
    Fragment for formatting transition guidance data for LLM templates.
    
    This fragment is responsible for extracting and formatting transition guidance
    information from the state. It provides context about navigation paths, transition 
    history, and exploration suggestions to help the LLM make informed decisions
    about navigation actions.
    
    Attributes:
        logger: Logger instance for this class
        error_handler: Error handler for managing exceptions
    """

    def __init__(self, name: str = "transition_guidance", priority: int = 200):
        """
        Initialize the transition guidance fragment.
        
        Args:
            name: The name of the fragment
            priority: The priority of the fragment (higher values are displayed first)
        """
        super().__init__(name, priority)
        self.logger = LoggingManager.get_instance().get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler.get_instance()

    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate transition guidance formatted text from state information.
        
        This method extracts transition guidance information from the state and formats
        it into a human-readable text suitable for inclusion in LLM prompts.
        
        Args:
            state: The current state dictionary containing transition guidance information
            context: Optional additional context information
            
        Returns:
            Formatted transition guidance text for inclusion in prompts
        """
        try:
            # Get transition guidance information from state
            guidance = state.get(StateEntry.TRANSITION_GUIDANCE, {})
            if not guidance:
                self.logger.warning("No transition guidance information found in state")
                return ""

            # Begin formatted output
            formatted_guidance = "## Transition Guidance\n\n"

            # Add current activity and visit information
            current_activity = guidance.get("current_activity", "unknown")
            visit_count = guidance.get("visit_count", 0)
            formatted_guidance += f"Current activity: {current_activity} (visited {visit_count} times)\n\n"

            # Add navigation path if available
            if "navigation_path" in guidance:
                formatted_guidance += "### Navigation Path\n"
                path = guidance["navigation_path"]
                if path:
                    formatted_guidance += " → ".join(path[-5:])  # Show last 5 activities for brevity
                    if len(path) > 5:
                        formatted_guidance += f" (showing last 5 of {len(path)} activities)"
                    formatted_guidance += "\n\n"
                else:
                    formatted_guidance += "No navigation history yet.\n\n"

            # Add unexplored actions information
            unexplored_actions = guidance.get("unexplored_actions", [])
            if unexplored_actions:
                formatted_guidance += "### Unexplored Actions\n"
                formatted_guidance += f"There are {len(unexplored_actions)} unexplored actions on this screen: "
                formatted_guidance += ", ".join([f"Action {action_id}" for action_id in unexplored_actions])
                formatted_guidance += "\n\n"

            # Add transition suggestions
            suggested_targets = guidance.get("suggested_targets", [])
            if suggested_targets:
                formatted_guidance += "### Suggested Activities to Explore\n"
                for target in suggested_targets[:3]:  # Limit to top 3 for brevity
                    name = target.get("name", "unknown")
                    visits = target.get("visits", 0)
                    action_ids = target.get("action_ids", [])

                    action_text = ", ".join([f"Action {action_id}" for action_id in action_ids])
                    formatted_guidance += f"- {name} (visited {visits} times) via {action_text}\n"
                formatted_guidance += "\n"

            # Add static transition information
            static_transitions = guidance.get("static_transitions", [])
            if static_transitions:
                formatted_guidance += "### Potential Transitions (Static Analysis)\n"
                for transition in static_transitions[:5]:  # Limit to 5 for brevity
                    target = transition.get("target", "unknown")
                    action_id = transition.get("action_id", "?")
                    visited = "✓" if transition.get("visited", False) else "✗"

                    formatted_guidance += f"- {target} via Action {action_id} [Visited: {visited}]\n"

                if len(static_transitions) > 5:
                    formatted_guidance += f"(+ {len(static_transitions) - 5} more transitions)\n"
                formatted_guidance += "\n"

            # Return formatted guidance
            return formatted_guidance.strip()
        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TransitionGuidanceFragment",
                    "method": "generate"
                }
            )
            return "Error generating transition guidance"

    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine whether transition guidance should be included in the prompt.
        
        This method checks if there is transition guidance information available in the state
        and if it should be included in the current prompt.
        
        Args:
            state: The current state dictionary
            context: Optional additional context information
            
        Returns:
            True if transition guidance should be included, False otherwise
        """
        try:
            # Only include if there is transition guidance in the state
            has_guidance = StateEntry.TRANSITION_GUIDANCE in state

            # Log decision
            if not has_guidance:
                self.logger.debug("Transition guidance not included: not available in state")

            return has_guidance
        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TransitionGuidanceFragment",
                    "method": "should_include"
                }
            )
            return False

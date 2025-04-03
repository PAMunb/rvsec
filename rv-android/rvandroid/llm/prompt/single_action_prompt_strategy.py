# rvandroid/llm/prompt/single_action_prompt_strategy.py
"""
Single Action Prompt Strategy Implementation

Specializes the base prompt strategy to generate prompts focused on selecting
a single, most appropriate action at each step. Uses explicit guidance and
enhanced context to help the model make optimal decisions within the single-action
constraint.
"""

from typing import Dict, Optional, Any, Union

from rvandroid.llm.prompt.base_prompt_strategy import BasePromptStrategy
from rvandroid.llm.prompt.prompt_template import PromptLibrary
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType


class SingleActionPromptStrategy(BasePromptStrategy):
    """
    A specialized prompt strategy that focuses on generating exactly one action at a time.
    
    ### Architectural Decisions:
    - Extends the BasePromptStrategy for common functionality
    - Specializes prompts for single action selection
    - Provides enhanced contextual guidance for sequential action planning
    - Uses template system with single-action-specific parameters
    - Optimizes for depth-first exploration in form testing

    ### Role in the System:
    - Enables predictable, single-step test execution
    - Supports detailed reasoning about each chosen action
    - Facilitates careful workflow testing with explicit guidance
    - Provides clearer action history tracking
    - Ensures consistent, controllable UI interaction
    """

    def __init__(self, 
                 static_data: Optional[StaticAnalysisData] = None, 
                 parser: Union[ParserType, AbstractScreenParser, None] = None,
                 detailed_static_analysis: bool = False,
                 include_screenshots: bool = False):
        """
        Initialize the single action prompt strategy.

        Args:
            static_data: Static analysis data (optional)
            parser: Parser type or instance for screen parsing
            detailed_static_analysis: Whether to include detailed static analysis
            include_screenshots: Whether to include screenshot analysis
        """
        super().__init__(static_data, parser, detailed_static_analysis, include_screenshots)
        self.logger.info("Using SingleActionPromptStrategy for action generation")

    def generate_system_prompt(self) -> str:
        """
        Generate a system prompt specialized for single action selection.
        Emphasizes that EXACTLY ONE action should be selected.

        Returns:
            System prompt string
        """
        # Use deep exploration goal for single actions
        exploration_goal = ("Systematically exploring ALL parts of the application "
                           "with a focus on depth-first testing of complete workflows")
        
        # Use single action format
        response_format = PromptLibrary.single_action_format()
        
        # Add single-action-specific guidelines
        additional_guidelines = """
REMEMBER: You MUST suggest only ONE action - the single most important next action to take.

CRITICAL: In each step, carefully consider which UI element needs attention next based on logical workflow sequence."""
        
        # Render template with parameters
        return self.system_template.render({
            "exploration_goal": exploration_goal,
            "response_format": response_format,
            "additional_guidelines": additional_guidelines
        })

    def _generate_summary(self, activity: str, screen_description, state: Dict[str, Any]) -> str:
        """
        Generate a summary section specialized for single action selection.

        Args:
            activity: Current activity name
            screen_description: Parsed screen description
            state: Current application state

        Returns:
            Generated summary string
        """
        # Get basic summary from parent class
        summary = super()._generate_summary(activity, screen_description, state)
        
        # Add single-action-specific guidance
        summary += "\n\nIMPORTANT: Based on the context, SELECT EXACTLY ONE ACTION from the available options that would be the most effective next step in testing."
        
        # Check if this is a form with multiple inputs
        form_elements = [item for item in screen_description.items
                         if any(t in item.base_description.lower()
                               for t in ["text field", "spinner", "checkbox"])]
        
        if len(form_elements) > 1:
            summary += " Remember to follow a logical sequence when filling forms - handle one input at a time in a natural order."
        
        # Check for repetitive actions and suggest back navigation if needed
        action_history = state.get("action_history", [])
        if len(action_history) >= 3:
            # Check last few actions for repetition
            recent_actions = action_history[-3:]
            
            # Simple repetition check - are all recent actions identical?
            if len(set(recent_actions)) == 1:
                # Find back button action ID
                back_action_id = None
                for item in screen_description.items:
                    if "System back button" in item.base_description or "BACK" in item.base_description:
                        for action in item.actions:
                            if "BACK" in action.text:
                                back_action_id = action.id
                                break
                            
                if back_action_id:
                    summary += f" You have repeated the same action multiple times - consider using the BACK button (action_id: \"{back_action_id}\") to explore other parts of the application."
                else:
                    summary += " You have repeated the same action multiple times - consider navigating to a different part of the application."
        
        return summary
    
    def _add_transition_guidance(self, guidance: Dict[str, Any]) -> str:
        """
        Add transition guidance information to the prompt.

        Args:
            guidance: Transition guidance dictionary

        Returns:
            Formatted transition guidance string
        """
        output = "Screen Transition Analysis:\n"

        # Add current activity visit information
        output += f"- Current activity has been visited {guidance['visit_count']} time(s)\n"

        # Add information about visited activities
        visited_activities = guidance.get('visited_activities', [])
        if visited_activities:
            output += f"- Total of {len(visited_activities)} activities visited during testing\n"

        # Add information about least visited activities
        least_visited = guidance.get('least_visited_activities', [])
        if least_visited:
            output += "- Least visited activities:\n"
            for activity in least_visited[:3]:  # Top 3
                output += f"  * {activity['name']} ({activity['visits']} visit(s))\n"

        # Add information about suggested targets
        suggested_targets = guidance.get('suggested_targets', [])
        if suggested_targets:
            output += "- Suggested target activities for exploration:\n"
            for target in suggested_targets:
                output += f"  * {target['name']} ({target['visits']} visit(s))\n"

        # Add unexplored elements information
        unexplored_elements = guidance.get('unexplored_elements', [])
        if unexplored_elements:
            remaining = len(unexplored_elements)
            output += f"- {remaining} UI elements on this screen have not yet been tested\n"

        return output + "\n"

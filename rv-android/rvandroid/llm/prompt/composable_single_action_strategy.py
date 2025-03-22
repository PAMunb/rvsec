# rvandroid/llm/prompt/composable_single_action_strategy.py
"""
Implementation of a single action prompt strategy using the composable approach.
This strategy is designed to work with models that need to select a single action.
"""
import logging
from typing import Dict, Any, Optional, Union

from rvandroid.llm.prompt.composable_prompt_strategy import ComposablePromptStrategy
from rvandroid.llm.prompt.prompt_template import PromptTemplate, PromptLibrary
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType


class ComposableSingleActionStrategy(ComposablePromptStrategy):
    """
    A composable strategy specialized for selecting a single action at a time.
    Provides detailed context and instructions for the LLM to make the best choice.
    """

    def __init__(self,
                 static_data: Optional[StaticAnalysisData] = None,
                 parser: Union[ParserType, AbstractScreenParser, None] = None):
        """
        Initialize the single action strategy.

        Args:
            static_data: Static analysis data (optional)
            parser: Parser type or instance
        """
        super().__init__(static_data, parser, single_action_mode=True)

        self.logger = logging.getLogger(__name__)
        # Override templates with single-action specific ones
        self.system_template = self._create_single_action_system_template()
        self.user_template = self._create_single_action_user_template()

    def _create_single_action_system_template(self) -> PromptTemplate:
        """
        Create a system template specialized for single action mode.

        Returns:
            PromptTemplate for system prompt
        """
        template = """You are an Android UI testing expert. Your task is to analyze the current app state and suggest the SINGLE MOST EFFECTIVE NEXT ACTION to take based on the testing context and history.

Focus on:
1. Systematically exploring ALL parts of the application, not just the current screen
2. Maximizing code coverage by targeting untested UI elements
3. Prioritizing testing of methods of interest that directly or indirectly affect operations defined in formal specifications
4. Testing complete workflows from start to finish

IMPORTANT: You will be provided with a list of possible actions, each with a unique action_id. Your job is to select EXACTLY ONE action that would be most appropriate as the next step in the testing sequence.

YOUR RESPONSE MUST CONTAIN EXACTLY ONE ACTION. DO NOT SUGGEST MULTIPLE ACTIONS OR A SEQUENCE OF ACTIONS.

Your response MUST follow this schema - a JSON array with EXACTLY ONE object inside:
[
  {
    "action_id": "5",  
    "params": {},  
    "explanation": "Detailed explanation of why this action was chosen as the next step"
  }
]

{additional_guidelines}

REMEMBER: You MUST suggest only ONE action - the single most important next action to take.

DO NOT include any additional text outside of the JSON array. Your response must be valid JSON that can be parsed directly with EXACTLY ONE action."""

        return PromptTemplate(
            template,
            required_variables=["additional_guidelines"]
        )

    def _create_single_action_user_template(self) -> PromptTemplate:
        """
        Create a user template specialized for single action mode.

        Returns:
            PromptTemplate for user prompt
        """
        template = """Current Activity: {activity}

{static_context}

{transition_guidance}

Current UI Elements and Available Actions:
{ui_elements}

{action_history}

{workflow_guidance}

{critical_instruction}"""

        return PromptTemplate(
            template,
            required_variables=["activity", "ui_elements", "critical_instruction"]
        )

    def generate_system_prompt(self) -> str:
        """
        Generate a system prompt for single action mode.

        Returns:
            System prompt string
        """
        additional_guidelines = "\n\n".join([
            PromptLibrary.dropdown_guidelines(),
            PromptLibrary.form_guidelines(),

            """EXPLORATION GUIDELINES:
1. After testing the same workflow 3 times, use the BACK button to explore other parts of the app
2. Avoid repeatedly clicking the same button more than 3 times
3. When stuck in a loop, prioritize navigating to different screens
4. Try different input values each time you fill a form
5. Balance depth (completing workflows) with breadth (exploring all screens)"""
        ])

        return self.system_template.render({
            "additional_guidelines": additional_guidelines
        })

    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """
        Generate a user prompt for single action mode.

        Args:
            state: Current application state

        Returns:
            User prompt string
        """
        try:
            # Parse the state
            screen_description = self.parser.parse(state, self.static_data)
            activity = self.parser.get_activity_name(state)

            # Generate static context
            static_context = self._add_static_analysis_context(activity)

            # Format UI elements
            ui_elements_text = self._format_ui_elements(screen_description, state)

            # Format action history
            action_history_text = self._format_action_history(state)

            # Generate transition guidance
            transition_guidance = self._format_transition_guidance(state.get("transition_guidance", {}))

            # Generate workflow guidance
            workflow_guidance = self._add_workflow_guidance(screen_description, state.get("action_history", []))

            # Critical instruction
            critical_instruction = """⚠️ CRITICAL INSTRUCTION: You MUST return EXACTLY ONE action. Do not suggest multiple actions, even if you think more than one action would be useful. Your response should be a JSON array containing EXACTLY ONE object with 'action_id', 'params', and 'explanation' fields.

TASK: Based on the current state and action history, determine the SINGLE MOST EFFECTIVE ACTION to test this screen."""

            # Render the template
            return self.user_template.render({
                "activity": activity,
                "static_context": static_context,
                "transition_guidance": transition_guidance,
                "ui_elements": ui_elements_text,
                "action_history": action_history_text,
                "workflow_guidance": workflow_guidance,
                "critical_instruction": critical_instruction
            })

        except Exception as e:
            self.logger.error(f"Error generating user prompt: {e}", exc_info=True)
            return self._generate_fallback_prompt()

    def _format_transition_guidance(self, guidance: Dict[str, Any]) -> str:
        """
        Format transition guidance information.

        Args:
            guidance: Transition guidance dictionary

        Returns:
            Formatted transition guidance string
        """
        if not guidance:
            return ""

        output = ["Screen Transition Analysis:"]

        # Add current activity visit information
        if "visit_count" in guidance:
            output.append(f"- Current activity has been visited {guidance['visit_count']} time(s)")

        # Add information about visited activities
        visited_activities = guidance.get('visited_activities', [])
        if visited_activities:
            output.append(f"- Total of {len(visited_activities)} activities visited during testing")

        # Add information about least visited activities
        least_visited = guidance.get('least_visited_activities', [])
        if least_visited:
            output.append("- Least visited activities:")
            for activity in least_visited[:3]:  # Top 3
                output.append(f"  * {activity['name']} ({activity['visits']} visit(s))")

        # Add information about suggested targets
        suggested_targets = guidance.get('suggested_targets', [])
        if suggested_targets:
            output.append("- Suggested target activities for exploration:")
            for target in suggested_targets:
                output.append(f"  * {target['name']} ({target['visits']} visit(s))")

        # Add unexplored elements information
        unexplored_elements = guidance.get('unexplored_elements', [])
        if unexplored_elements:
            remaining = len(unexplored_elements)
            output.append(f"- {remaining} UI elements on this screen have not yet been tested")

        return "\n".join(output)

# rvandroid/llm/prompt_strategy_basic.py
import logging
from typing import Dict, Any, Optional

from rvandroid.llm.prompt.prompt_strategy import PromptStrategy
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.parser_factory import ParserType


class BasicPromptStrategy(PromptStrategy):
    """
    Basic prompt generation strategy.
    Creates straightforward prompts based on the current screen state.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, parser_type: ParserType = ParserType.DROIDBOT):
        """
        Initialize the basic prompt strategy.

        Args:
            static_data: Static analysis data (optional)
            parser_type: Type of parser to use
        """
        super().__init__(static_data, parser_type)
        self.logger = logging.getLogger(__name__)

    def generate_system_prompt(self) -> str:
        """
        Generate a basic system prompt.

        Returns:
            System prompt string
        """
        return """You are an Android UI testing expert. Your task is to analyze the current app state and suggest the most effective testing actions.

Focus on:
1. Maximizing code coverage by targeting untested UI elements
2. Exercising important methods that directly or indirectly affect operations of interest, defined in formal specifications
3. Systematically exploring application states
4. Testing complex UI interactions and edge cases

For each action, provide:
- Action type (click, long_click, scroll, set_text, key_event)
- Target widget identifier or coordinates
- Parameters where needed (text input, scroll direction, etc.)
- Brief explanation of why you chose this action

Format your response as a valid JSON array of actions following this schema:
[
  {
    "action_type": "click",
    "target": "widget_id_or_index",
    "params": {},
    "explanation": "Brief explanation"
  },
  ...
]

Maintain awareness of the application state after each action. When suggesting a sequence of actions, ensure they build logically upon each other.

Before responding, carefully analyze the context to avoid suggesting conflicting actions. For example: when a screen has only 2 clickable buttons (each leading to a different activity), select only one button based on the current context and action history. On subsequent executions of the same screen, reference the previous selections to determine which alternative button to choose.

DO NOT include any additional text outside of the JSON array. Your response must be valid JSON that can be parsed directly."""

    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """
        Generate a basic user prompt from the current application state.

        Args:
            state: Current state dictionary

        Returns:
            User prompt string
        """
        # Parse the state to get a structured representation
        screen_description = self.parser.parse(state, self.static_data)

        # Extract activity name
        activity = self.parser.get_activity_name(state)

        # Begin building the prompt
        prompt = f"Current Activity: {activity}\n\n"

        # Add static analysis context if available
        prompt += self._add_static_analysis_context(activity)

        # Add UI state information
        prompt += "Current UI Elements:\n"
        for item in screen_description.items:
            # Add the item description
            prompt += f"- {item.description}\n"

        # Add action history if available
        if "action_history" in state:
            prompt += "\nRecent Actions:\n"
            history = state.get("action_history", [])
            recent_actions = history[-5:] if len(history) > 5 else history
            for action in recent_actions:
                prompt += f"- {action}\n"

        # Add instructions for the LLM
        prompt += "\nSuggest test actions that would be most effective for testing this screen, formatted as JSON according to the specified schema."

        return prompt

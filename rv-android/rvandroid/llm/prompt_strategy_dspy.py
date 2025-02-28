# rvandroid/llm/prompt_strategy_dspy.py
from typing import Dict, Any, Optional
import logging

from rvandroid.llm.prompt_strategy import PromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.parser_factory import ParserType


class DSPyPromptStrategy(PromptStrategy):
    """
    Specialized prompt strategy for DSPy models.
    Uses a more structured approach suitable for DSPy's programming model.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, parser_type: ParserType = ParserType.DROIDBOT):
        """
        Initialize the DSPy prompt strategy.

        Args:
            static_data: Static analysis data (optional)
            parser_type: Type of parser to use
        """
        super().__init__(static_data, parser_type)
        self.logger = logging.getLogger(__name__)

    def generate_system_prompt(self) -> str:
        """
        Generate system prompt optimized for DSPy models.

        Returns:
            System prompt string
        """
        return """You are an Android UI testing AI assistant. Your role is to analyze application states and generate optimal testing actions.

Your output must follow this JSON format exactly:
[{"action_type": "...", "target": "...", "params": {...}, "explanation": "..."}]

Valid action types: click, long_click, scroll, set_text, key_event

Focus on these testing objectives:
- Find security vulnerabilities by targeting critical operations
- Maximize test coverage across the application
- Exercise complex UI paths and edge cases
- Ensure all UI elements are properly tested

Your response must be a valid JSON array that follows the specified format exactly. Do not include any text outside of the JSON array."""

    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """
        Generate user prompt for DSPy with additional structure.

        Args:
            state: Current state dictionary

        Returns:
            User prompt string
        """
        # Parse the state
        screen_description = self.parser.parse(state, self.static_data)
        activity = self.parser.get_activity_name(state)

        # Structure the prompt with clear sections
        sections = []

        # Section 1: Activity information
        sections.append(f"ACTIVITY: {activity}")

        # Section 2: Static analysis
        static_section = ["STATIC ANALYSIS:"]
        static_section.append(self._add_static_analysis_context(activity).strip())
        sections.append("\n".join(static_section))

        # Section 3: UI elements
        ui_section = ["UI ELEMENTS:"]
        for item in screen_description.items:
            element_info = [f"ELEMENT: {item.base_description}"]

            # Add actions
            if item.actions:
                action_info = []
                for action in item.actions:
                    security_tag = ""
                    if action.directly_reaches_mop:
                        security_tag = "[CRITICAL]"
                    elif action.reaches_mop:
                        security_tag = "[IMPORTANT]"
                    action_info.append(f"- {action.text} {security_tag}")

                if action_info:
                    element_info.append("ACTIONS:\n" + "\n".join(action_info))

            ui_section.append("\n".join(element_info))

        sections.append("\n\n".join(ui_section))

        # Section 4: Action history
        if "action_history" in state:
            history_section = ["RECENT ACTIONS:"]
            history = state.get("action_history", [])
            recent_actions = history[-5:] if len(history) > 5 else history
            for action in recent_actions:
                history_section.append(f"- {action}")
            sections.append("\n".join(history_section))

        # Section 5: Task instruction
        sections.append(
            "TASK: Generate 3-5 test actions in JSON format. Focus on security-critical operations and unexplored UI elements.")

        return "\n\n".join(sections)

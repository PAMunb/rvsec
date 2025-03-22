# rvandroid/llm/prompt/prompt_strategy_frontier.py
from typing import Dict, Any, Optional

from rvandroid.llm.prompt.base_prompt_strategy import BasePromptStrategy
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.parser_factory import ParserType


class FrontierPromptStrategy(BasePromptStrategy):
    """
    Prompt strategy for frontier models like Claude, GPT, Gemini, etc.
    These models typically have better understanding of complex instructions
    and can handle more nuanced prompts.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, parser_type: ParserType = ParserType.DROIDBOT):
        """
        Initialize the frontier prompt strategy.

        Args:
            static_data: Static analysis data (optional)
            parser_type: Type of parser to use
        """
        super().__init__(static_data, parser_type)
        self.logger.info("Using FrontierPromptStrategy for action generation")

    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """
        Generate user prompt with detailed context for frontier models.

        Args:
            state: Current state dictionary

        Returns:
            User prompt string
        """
        # Parse the state
        screen_description = self.parser.parse(state, self.static_data)
        activity = self.parser.get_activity_name(state)

        # Build a comprehensive prompt with clear sections
        sections = []

        # Current activity
        sections.append(f"# Current Activity: {activity}")

        # Static analysis
        sections.append("# Static Analysis")
        sections.append(self._add_static_analysis_context(activity))

        # UI Elements with rich information
        sections.append("# UI Elements")
        for item in screen_description.items:
            view = item.view

            # Extract common properties if available
            widget_id = "unknown"
            if "resource_id" in view:
                resource_id = view.get("resource_id", "")
                if resource_id and "/" in resource_id:
                    widget_id = resource_id.split("/")[-1]

            widget_class = "unknown"
            if "class" in view:
                class_name = view.get("class", "")
                if class_name and "." in class_name:
                    widget_class = class_name.split(".")[-1]

            widget_text = view.get("text", "")
            widget_bounds = view.get("bounds", [[0, 0], [0, 0]])
            widget_clickable = view.get("clickable", False)
            widget_enabled = view.get("enabled", True)

            # Build detailed element description
            element_info = [
                f"## Element: {widget_class} (ID: {widget_id})",
                f"- Description: {item.base_description}",
                f"- Bounds: {widget_bounds}",
                f"- Properties: {'Clickable' if widget_clickable else 'Not clickable'}, {'Enabled' if widget_enabled else 'Disabled'}"
            ]

            if widget_text:
                element_info.append(f"- Text: \"{widget_text}\"")

            # Add actions with annotations
            if item.actions:
                action_info = ["- Available actions:"]
                for action in item.actions:
                    importance_tag = ""
                    if action.directly_reaches_mop:
                        importance_tag = " [CRITICAL: Directly reaches operation of interest]"
                    elif action.reaches_mop:
                        importance_tag = " [IMPORTANT: Can reach operation of interest]"
                    action_info.append(f"  * {action.text}{importance_tag}")
                element_info.append("\n".join(action_info))

            # Add static info
            static_info = self._get_widget_static_info(activity, widget_id)
            if static_info:
                element_info.append(f"- Static analysis: {static_info}")

            sections.append("\n".join(element_info))

        # Action history with context
        if "action_history" in state and state["action_history"]:
            sections.append("# Recent Actions")
            history = state.get("action_history", [])
            recent_actions = history[-5:] if len(history) > 5 else history
            for i, action in enumerate(recent_actions):
                sections.append(f"{i + 1}. {action}")

        # Testing objective reminder
        sections.append("# Task")
        sections.append(
            "Based on the above information, provide 3-5 test actions that would be most effective "
            "for testing this screen. Focus on exercising code paths that call operations of interest and testing "
            "unexplored functionality. Return your response as a valid JSON array with the following structure for each action:\n"
            "[\n"
            "  {\n"
            "    \"action_id\": \"5\",\n"
            "    \"params\": {},\n"
            "    \"explanation\": \"Detailed explanation of why this action was chosen\"\n"
            "  },\n"
            "  ...\n"
            "]\n"
            "Make sure to include the action_id as specified in the UI elements section."
        )

        return "\n\n".join(sections)
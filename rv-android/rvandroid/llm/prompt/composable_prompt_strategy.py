# rvandroid/llm/prompt/composable_prompt_strategy.py
"""
Refactored version of the prompt strategy using a composition-based approach.
This approach allows for more flexible prompt generation and easier reuse of components.
"""

from typing import Dict, Any, Optional, Union

from rvandroid.llm.prompt.prompt_strategy import PromptStrategy
from rvandroid.llm.prompt.prompt_template import PromptLibrary
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType


class ComposablePromptStrategy(PromptStrategy):
    """
    A flexible prompt strategy that uses composition of template components.
    This strategy provides better reuse capabilities and easier customization.
    """

    def __init__(self,
                 static_data: Optional[StaticAnalysisData] = None,
                 parser: Union[ParserType, AbstractScreenParser, None] = None,
                 single_action_mode: bool = False):
        """
        Initialize the composable prompt strategy.

        Args:
            static_data: Static analysis data (optional)
            parser: Parser type or instance
            single_action_mode: Whether to generate prompts for single action mode
        """
        super().__init__(static_data, parser)
        self.system_template = PromptLibrary.system_base_template()
        self.user_template = PromptLibrary.user_base_template()
        self.single_action_mode = single_action_mode

        # Configure system template based on mode
        if single_action_mode:
            self.response_format = PromptLibrary.single_action_format()
            self.exploration_goal = ("Systematically exploring ALL parts of the application "
                                     "with a focus on depth-first testing of complete workflows")
        else:
            self.response_format = PromptLibrary.multi_action_format()
            self.exploration_goal = ("Systematically exploring all application states in a logical sequence "
                                     "with a balanced approach to breadth and depth")

    def generate_system_prompt(self) -> str:
        """
        Generate a system prompt using the template approach.

        Returns:
            System prompt string
        """
        additional_guidelines = "\n\n".join([
            PromptLibrary.dropdown_guidelines(),
            PromptLibrary.form_guidelines(),
            "REVIEW the action history carefully to understand what has already been tested and choose the most logical next action."
        ])

        return self.system_template.render({
            "exploration_goal": self.exploration_goal,
            "response_format": self.response_format,
            "additional_guidelines": additional_guidelines
        })

    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """
        Generate a user prompt using the template approach.

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

            # Generate summary
            summary_text = self._generate_summary(activity, state, screen_description)

            # Render the template
            return self.user_template.render({
                "activity": activity,
                "static_context": static_context,
                "ui_elements": ui_elements_text,
                "action_history": action_history_text,
                "summary": summary_text
            })

        except Exception as e:
            self.logger.error(f"Error generating user prompt: {e}", exc_info=True)
            return self._generate_fallback_prompt()

    def _format_ui_elements(self, screen_description, state: Dict[str, Any]) -> str:
        """
        Format UI elements for the prompt.

        Args:
            screen_description: Screen description object
            state: Current application state

        Returns:
            Formatted UI elements string
        """
        ui_elements_text = []

        if not screen_description.items:
            return "No UI elements detected in the current state. This might be a loading screen or an error state."

        for item in screen_description.items:
            view = item.view
            widget_id = view.get("resource_id", "").split("/")[-1] if view.get("resource_id") else "unknown"

            # Add the item description
            ui_elements_text.append(f"- {item.base_description}")

            # Add actions with their IDs
            if item.actions:
                ui_elements_text.append("  Available actions:")
                for action in item.actions:
                    # Add importance indicators
                    importance_tag = ""
                    if action.directly_reaches_mop:
                        importance_tag = " [CRITICAL: Directly reaches operation of interest]"
                    elif action.reaches_mop:
                        importance_tag = " [IMPORTANT: Can reach operation of interest]"

                    # Add the action
                    ui_elements_text.append(f"  - {action.text} (action_id: \"{action.id}\"){importance_tag}")

                    # Add usage history if available
                    if "action_specific_history" in state:
                        history = state["action_specific_history"].get(str(action.id), [])
                        if history:
                            ui_elements_text.append(f"    Used {len(history)} time(s) previously")

            # Add input type for text fields
            has_text_action = any(a.text.startswith("SET_TEXT") for a in item.actions)
            if has_text_action:
                hint = view.get("hint", "") or view.get("content_description", "") or view.get("text", "")
                if hint:
                    ui_elements_text.append(f"  Input hint: {hint}")

                input_type = self._infer_input_type(view, widget_id)
                if input_type:
                    ui_elements_text.append(f"  Input type appears to be: {input_type}")

        return "\n".join(ui_elements_text)

    def _format_action_history(self, state: Dict[str, Any]) -> str:
        """
        Format action history for the prompt.

        Args:
            state: Current application state

        Returns:
            Formatted action history string
        """
        if "action_history" not in state or not state["action_history"]:
            return ""

        history = state.get("action_history", [])
        recent_actions = history[-10:] if len(history) > 10 else history

        history_text = ["Recent Actions:"]
        for action in recent_actions:
            history_text.append(f"- {action}")

        return "\n".join(history_text)

    def _generate_summary(self, activity: str, state: Dict[str, Any], screen_description) -> str:
        """
        Generate a summary for the prompt.

        Args:
            activity: Current activity name
            state: Current application state
            screen_description: Screen description object

        Returns:
            Summary string
        """
        summary = f"SUMMARY: You are testing the {activity} screen."

        # Add specific instructions based on UI element types
        form_elements = [item for item in screen_description.items
                         if any(t in item.base_description.lower()
                                for t in ["text field", "spinner", "checkbox"])]

        buttons = [item for item in screen_description.items
                   if "button" in item.base_description.lower()]

        if form_elements and buttons:
            summary += " This screen appears to contain a form with input fields and buttons."

            # Check if this appears to be a login form
            login_related = any(("login" in item.base_description.lower() or
                                 "username" in item.base_description.lower() or
                                 "password" in item.base_description.lower())
                                for item in form_elements)

            if login_related:
                summary += " This appears to be a login form."

        # Add mode-specific instructions
        if self.single_action_mode:
            summary += " Select ONE action from the available options above that would be the most logical next step in testing this screen."
        else:
            summary += " Select 3-5 actions from the available options above that would be most effective for testing this screen."

        return summary

    def _generate_fallback_prompt(self) -> str:
        """
        Generate a fallback prompt when normal generation fails.

        Returns:
            Fallback prompt string
        """
        return ("Error occurred while analyzing the current screen. Please suggest basic testing actions.\n"
                "Return your response as a JSON array with action_id values that might be on the screen.\n"
                "Example: [{\"action_id\": \"1\", \"params\": {}, \"explanation\": \"Basic test action\"}]")
   
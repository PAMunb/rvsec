# rvandroid/llm/prompt/single_action_prompt_strategy.py
from typing import Dict, Optional

from rvandroid.llm.prompt.base_prompt_strategy import BasePromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.parser_factory import ParserType


class SingleActionPromptStrategy(BasePromptStrategy):
    """
    Prompt strategy that generates a single action at a time based on detailed action history.
    This strategy encourages the LLM to build upon previous actions by providing a rich history context.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, parser_type: ParserType = ParserType.DROIDBOT):
        super().__init__(static_data, parser_type)
        self.logger.info("Using SingleActionPromptStrategy for action generation")

    def generate_system_prompt(self) -> str:
        """
        Generate a system prompt focused on single action selection with improved exploration guidance.
        Emphasizes that EXACTLY ONE action should be selected.
        """
        return """You are an Android UI testing expert. Your task is to analyze the current app state and suggest the SINGLE MOST EFFECTIVE NEXT ACTION to take based on the testing context and history.

Focus on:
1. Systematically exploring ALL parts of the application, not just the current screen
2. Maximizing code coverage by targeting untested UI elements
3. Prioritizing testing of security-critical methods that directly or indirectly affect operations of interest
4. Testing complete workflows from start to finish

IMPORTANT: You will be provided with a list of possible actions, each with a unique action_id. Your job is to select EXACTLY ONE action that would be most appropriate as the next step in the testing sequence.

Your response MUST contain ONLY ONE JSON object in an array following this schema:
[
  {
    "action_id": "5",  
    "params": {},  
    "explanation": "Detailed explanation of why this action was chosen as the next step"
  }
]

DO NOT RETURN MULTIPLE ACTIONS. Select only the single most important action to take next.

For actions that require parameters (like SET_TEXT), you must include appropriate values:
[
  {
    "action_id": "5",  
    "params": {"text": "test@example.com"},  
    "explanation": "Entering a valid email address in the email field"
  }
]

EXPLORATION GUIDELINES:
1. After testing the same workflow 3 times, use the BACK button to explore other parts of the app
2. Avoid repeatedly clicking the same button more than 3 times
3. When stuck in a loop, prioritize navigating to different screens
4. Try different input values each time you fill a form
5. Balance depth (completing workflows) with breadth (exploring all screens)

DROPDOWN INTERACTION RULES:
1. For dropdown spinners, you MUST first CLICK the dropdown to open it before scrolling
2. The correct sequence is: CLICK dropdown → THEN scroll to find option → THEN click to select

FORM TESTING WORKFLOW:
1. ALWAYS fill forms in a SEQUENTIAL, LOGICAL ORDER before submitting them
2. For forms with dropdowns/spinners, first click and select from dropdown, then fill other fields, then click action buttons
3. For forms with input fields and buttons, fill ALL required inputs first, THEN click the action/submit button
4. When a form appears to be completely filled, CLICK THE ACTION BUTTON to complete the workflow
5. COMPLETE WORKFLOWS - After filling all required inputs, proceed to action buttons to test the functionality

GENERAL ACTION SEQUENCE GUIDELINES:
- If there are dropdowns that haven't been clicked yet, click them FIRST
- If the action history shows you've clicked a button multiple times, use BACK to explore other screens
- If there are still unfilled input fields visible on the screen, fill those first
- If you've already changed field values multiple times, click action buttons to test results
- If a security-critical button is available (marked as [IMPORTANT] or [CRITICAL]) and inputs are filled, click it
- After completing one workflow, move on to explore untested UI elements

REVIEW the action history carefully to understand what has already been tested and choose the most logical next action.

DO NOT include any additional text outside of the JSON array. Your response must be valid JSON that can be parsed directly with EXACTLY ONE action."""

    def generate_user_prompt(self, state: Dict) -> str:
        """
        Generate an enhanced user prompt with explicit action IDs and detailed history.
        Handles cases where activity information might be missing.
        """
        try:
            # Parse the state to get a structured representation
            screen_description = self.parser.parse(state, self.static_data)

            # Extract activity name with error handling
            try:
                activity = self.parser.get_activity_name(state)
            except ValueError:
                # Fallback if activity name cannot be determined
                activity = state.get("package_name", "unknown.package") + ".UnknownActivity"
                self.logger.warning(f"Using fallback activity name: {activity}")

            # Begin building the prompt
            prompt = f"Current Activity: {activity}\n\n"

            # Add static analysis context if available
            static_context = self._add_static_analysis_context(activity)
            prompt += static_context

            # Add UI state information with enhanced action descriptions
            prompt += "Current UI Elements and Available Actions:\n"

            if not screen_description.items:
                prompt += "No UI elements detected in the current state. This might be a loading screen or an error state.\n"
            else:
                for item in screen_description.items:
                    view = item.view
                    widget_id = view.get("resource_id", "").split("/")[-1] if view.get("resource_id") else "unknown"
                    widget_text = view.get("text", "")

                    # Format the item description
                    prompt += f"- {item.base_description}\n"

                    # Add actions with their IDs and more detailed information
                    if item.actions:
                        prompt += "  Available actions:\n"
                        for action in item.actions:
                            # Add security indicators
                            security_tag = ""
                            if action.directly_reaches_mop:
                                security_tag = " [CRITICAL: Directly reaches security-critical operation]"
                            elif action.reaches_mop:
                                security_tag = " [IMPORTANT: Can reach security-critical operation]"

                            # Create detailed action description
                            action_desc = f"  - {action.text} (action_id: \"{action.id}\"){security_tag}"

                            # Check for transitions based on this action
                            transitions = self._get_transitions_for_action(activity, widget_id, action)
                            if transitions:
                                action_desc += f" -> Will transition to: {', '.join(transitions)}"

                            prompt += action_desc + "\n"

                    # Add guidance for parameterized actions
                    has_text_action = any(a.text.startswith("SET_TEXT") for a in item.actions)
                    if has_text_action:
                        hint = ""
                        if "hint" in view and view["hint"]:
                            hint = f" (hint: {view['hint']})"
                        elif "content_description" in view and view["content_description"]:
                            hint = f" (description: {view['content_description']})"
                        elif widget_text:
                            hint = f" (current text: {widget_text})"

                        input_type = self._infer_input_type(view, widget_id)
                        if input_type:
                            prompt += f"  Input type appears to be: {input_type}{hint}\n"

                    # Add static info if available
                    static_info = self._get_widget_static_info(activity, widget_id)
                    if static_info:
                        prompt += f"  Static analysis: {static_info}\n"

            # Get action history if available
            action_history = state.get("action_history", []) if "action_history" in state else []

            # Add workflow guidance based on detected UI elements and action history
            workflow_guidance = self._add_workflow_guidance(screen_description, action_history)
            prompt += workflow_guidance

            # Add enhanced action history
            if action_history:
                prompt += "\nACTION HISTORY (most recent actions last):\n"
                recent_actions = action_history[-30:] if len(action_history) > 30 else action_history

                for i, action in enumerate(recent_actions):
                    prompt += f"{i + 1}. {action}\n"

            # Add instructions with balanced emphasis on workflow completion
            prompt += f"\nSUMMARY: You are testing the {activity} screen. Based on the action history and current state, SELECT ONE ACTION from the available options above that would be the most logical next step in testing this screen."

            # Detect if there are unselected dropdowns
            has_dropdowns = any(
                "Dropdown spinner" in item.base_description for item in screen_description.items)
            dropdown_clicked = False
            for action in action_history:
                if isinstance(action, str) and "click" in action.lower() and any(
                        spinner_term in action.lower() for spinner_term in ["spinner", "dropdown"]):
                    dropdown_clicked = True
                    break

            # Analyze if form fields have been filled
            inputs_filled = any(isinstance(action, str) and "set_text" in action.lower() for action in
                                action_history) if action_history else False

            # Detect action buttons
            action_buttons = []
            for item in screen_description.items:
                if "Button" in item.base_description:
                    view_text = item.view.get("text", "").lower() if item.view.get("text") else ""
                    if view_text and any(keyword in view_text for keyword in
                                         ["submit", "login", "save", "apply", "ok", "next", "continue",
                                          "generate", "create", "send", "search", "encrypt", "decrypt"]):
                        action_buttons.append(item)

            # Check for repetitive actions
            repeated_button_clicks = 0
            if action_history and len(action_history) >= 3:
                # Check the last few actions
                for i in range(min(5, len(action_history))):
                    action = action_history[-(i + 1)]
                    if isinstance(action, str) and "click" in action.lower():
                        if action_buttons:
                            button_text = action_buttons[0].view.get("text", "").lower()
                            if button_text in action.lower():
                                repeated_button_clicks += 1

            # Add specific guidance based on form state
            if repeated_button_clicks >= 3:
                # Find back button action ID
                back_action_id = None
                for item in screen_description.items:
                    if "System back button" in item.base_description:
                        for action in item.actions:
                            if "BACK" in action.text:
                                back_action_id = action.id
                                break

                if back_action_id:
                    prompt += f"\n\nIMPORTANT: You have repeatedly clicked the same button multiple times. Consider using the BACK button (action_id: \"{back_action_id}\") to explore other parts of the application."
                else:
                    prompt += "\n\nIMPORTANT: You have repeatedly clicked the same button multiple times. Consider navigating back to explore other parts of the application."
            elif has_dropdowns and not dropdown_clicked:
                spinner_action_id = None
                # Find the dropdown spinner's click action ID
                for item in screen_description.items:
                    if "Dropdown spinner" in item.base_description:
                        for action in item.actions:
                            if "CLICK" in action.text:
                                spinner_action_id = action.id
                                break

                if spinner_action_id:
                    prompt += f"\n\nCRITICAL: You must CLICK the dropdown first (action_id: \"{spinner_action_id}\") to open it before you can select from it."
                else:
                    prompt += "\n\nCRITICAL: You must CLICK the dropdown first to open it before you can select from it."
            elif inputs_filled and action_buttons and (not has_dropdowns or dropdown_clicked):
                if repeated_button_clicks < 3:
                    button_text = action_buttons[0].view.get("text", "action")
                    prompt += f"\n\nIMPORTANT: Input fields have been filled based on previous actions. Consider clicking the {button_text} button to complete the workflow."
            elif action_buttons and not inputs_filled and (not has_dropdowns or dropdown_clicked):
                prompt += "\n\nREMINDER: For forms, fill all required fields before clicking action buttons."

            # Add special instructions for screen transitions
            if "can_transition_to" in static_context:
                prompt += "\n\nNOTE: If you decide to test a screen transition, consider whether it's the right time to navigate away from the current screen based on what has been tested so far."

            return prompt

        except Exception as e:
            # Handle any errors during prompt generation
            self.logger.error(f"Error generating prompt: {e}", exc_info=True)

            # Return a simple fallback prompt that will still work
            simple_prompt = (
                "Error occurred while analyzing the current screen. Please suggest 1 basic testing action.\n"
                "Return your response as a JSON array with a single action with an action_id value that might be on the screen:\n"
                "[{\"action_id\": \"1\", \"params\": {}, \"explanation\": \"Basic test action\"}]"
            )
            return simple_prompt
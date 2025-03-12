# rvandroid/llm/prompt/dspy_single_action_prompt_strategy.py
from typing import Dict, Any, Optional, List

import dspy

from rvandroid.llm.prompt.base_prompt_strategy import BasePromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.parser_factory import ParserType


class DSPySingleActionPromptStrategy(BasePromptStrategy):
    """
    A prompt strategy that combines DSPy's capabilities with the single action approach.
    This strategy encourages the LLM to select exactly one action at a time,
    building upon previous actions using rich history context and DSPy's structured approach.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, parser_type: ParserType = ParserType.DROIDBOT):
        super().__init__(static_data, parser_type)
        self._signature = None
        self._action_schema = None
        self.logger.info("Using DSPySingleActionPromptStrategy for action generation")

    def generate_system_prompt(self) -> str:
        """
        Generate a system prompt focused on single action selection using DSPy's approach.
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

DO NOT include any additional text outside of the JSON array. Your response must be valid JSON that can be parsed directly with EXACTLY ONE action."""

    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """
        Generate an enhanced user prompt with structured DSPy approach but focused on single action selection.
        """
        try:
            # Parse the state
            screen_description = self.parser.parse(state, self.static_data)

            # Extract activity name with error handling
            try:
                activity = self.parser.get_activity_name(state)
            except ValueError:
                activity = state.get("package_name", "unknown.package") + ".UnknownActivity"
                self.logger.warning(f"Using fallback activity name: {activity}")

            # Structure the prompt with clear sections
            sections = []

            # Section 1: Activity information with clear header
            sections.append(f"## CURRENT ACTIVITY: {activity}")

            # Section 2: Static analysis with enhanced formatting
            static_section = [f"## STATIC ANALYSIS FOR {activity}:"]
            static_context = self._add_static_analysis_context(activity).strip()
            static_section.append(static_context)
            sections.append("\n".join(static_section))

            # Section 3: UI elements with detailed descriptions
            ui_section = ["## AVAILABLE UI ELEMENTS AND ACTIONS:"]

            if not screen_description.items:
                ui_section.append(
                    "No UI elements detected on the current screen. This might be a loading screen or an error state.")
            else:
                # Group elements by type for better organization
                buttons = []
                text_fields = []
                dropdowns = []
                checkboxes = []
                other_elements = []

                for item in screen_description.items:
                    desc = item.base_description.lower()
                    if "button" in desc:
                        buttons.append(item)
                    elif "text field" in desc or "edittext" in desc:
                        text_fields.append(item)
                    elif "dropdown" in desc or "spinner" in desc:
                        dropdowns.append(item)
                    elif "checkbox" in desc or "toggle" in desc or "switch" in desc:
                        checkboxes.append(item)
                    else:
                        other_elements.append(item)

                # Add form elements first (better for form filling workflows)
                all_groups = []
                if text_fields:
                    all_groups.append(("TEXT FIELDS", text_fields))
                if dropdowns:
                    all_groups.append(("DROPDOWNS", dropdowns))
                if checkboxes:
                    all_groups.append(("CHECKBOXES & TOGGLES", checkboxes))
                if buttons:
                    all_groups.append(("BUTTONS", buttons))
                if other_elements:
                    all_groups.append(("OTHER ELEMENTS", other_elements))

                # Build detailed UI description by groups
                for group_name, items in all_groups:
                    ui_section.append(f"### {group_name}:")

                    for item in items:
                        view = item.view
                        widget_id = view.get("resource_id", "").split("/")[-1] if view.get("resource_id") else "unknown"
                        widget_text = view.get("text", "")
                        content_desc = view.get("content_description", "")

                        # Build a rich description of the element
                        element_desc = [f"- **{item.base_description}**"]

                        # Add important attributes
                        attributes = []
                        if widget_text:
                            attributes.append(f"Text: \"{widget_text}\"")
                        if content_desc:
                            attributes.append(f"Description: \"{content_desc}\"")
                        if view.get("resource_id"):
                            attributes.append(f"ID: {view.get('resource_id')}")

                        if attributes:
                            element_desc.append("  " + ", ".join(attributes))

                        # Add actions with detailed information
                        if item.actions:
                            element_desc.append("  **Available actions:**")
                            for action in item.actions:
                                security_tag = ""
                                if action.directly_reaches_mop:
                                    security_tag = "🔴 [CRITICAL SECURITY OPERATION]"
                                elif action.reaches_mop:
                                    security_tag = "🟠 [SECURITY SENSITIVE]"

                                action_desc = f"    - `{action.text}` (action_id: \"{action.id}\") {security_tag}"
                                element_desc.append(action_desc)

                                # If it's a text field, suggest appropriate input
                                if "SET_TEXT" in action.text:
                                    input_type = self._infer_input_type(view, widget_id)
                                    if input_type:
                                        element_desc.append(f"      (Expects {input_type} input)")

                        ui_section.append("\n".join(element_desc))

            sections.append("\n".join(ui_section))

            # Section 4: Action history with better formatting
            if "action_history" in state and state["action_history"]:
                history_section = ["## RECENT TESTING ACTIONS:"]
                history = state.get("action_history", [])
                recent_actions = history[-15:] if len(history) > 15 else history

                for i, action in enumerate(recent_actions):
                    history_section.append(f"{len(recent_actions) - i}. {action}")

                sections.append("\n".join(history_section))

            # Section 5: Workflow guidance based on UI analysis
            workflow_section = ["## WORKFLOW GUIDANCE:"]

            # Add workflow guidance based on detected UI elements and action history
            workflow_guidance = self._add_workflow_guidance(screen_description, state.get("action_history", []))
            workflow_section.append(workflow_guidance)
            sections.append("\n".join(workflow_section))

            # Section 6: Single action task reminder
            sections.append("""## TESTING TASK:
Based on the current state and action history, determine the SINGLE MOST EFFECTIVE ACTION to test this screen.
Return EXACTLY ONE action in valid JSON format. Remember to include the action_id.

Your response should be a JSON array with ONLY ONE object like this:
[{"action_id": "X", "params": {}, "explanation": "Detailed explanation of why this is the best next action"}]

Prioritize actions that:
1. Continue logical workflows
2. Explore untested elements
3. Test security-critical operations
4. Maximize testing coverage""")

            # Join all sections with double newlines for clarity
            return "\n\n".join(sections)

        except Exception as e:
            # Handle any errors during prompt generation
            self.logger.error(f"Error generating prompt: {e}", exc_info=True)

            # Return a simple fallback prompt
            simple_prompt = """## ERROR ANALYZING SCREEN
Could not fully analyze the current screen. Please suggest 1 basic testing action.
Focus on exploring visible elements.

## TESTING TASK:
Suggest exactly ONE testing action in valid JSON format with an action_id.
"""
            return simple_prompt

    def _get_action_schema(self):
        """
        Get the DSPy signature for single action generation.

        Returns:
            DSPy Signature for action generation
        """
        if self._signature is None:
            # Define a schema for Android testing actions - single action variant
            action_schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action_id": {
                            "type": "string"
                        },
                        "params": {
                            "type": "object"
                        },
                        "explanation": {
                            "type": "string"
                        }
                    },
                    "required": ["action_id", "params", "explanation"]
                },
                "maxItems": 1
            }

            # Create a DSPy signature for structured output
            self._signature = dspy.Signature(
                inputs=[
                    dspy.InputField("activity", description="Current Android activity"),
                    dspy.InputField("ui_elements", description="Available UI elements and actions"),
                    dspy.InputField("action_history", description="Previous testing actions")
                ],
                outputs=[
                    dspy.OutputField("actions", description="JSON array with a single action with action_id field", schema=action_schema)
                ]
            )

        return self._signature

    def _get_dspy_modules(self):
        """
        Create DSPy module for single action prediction.

        Returns:
            Dictionary with DSPy module
        """
        # Define module for single action prediction with action_id
        class SingleActionPredictor(dspy.Module):
            def __init__(self):
                super().__init__()
                self.predict = dspy.ChainOfThought("single_action_signature")

            def forward(self, activity, ui_elements, action_history):
                return self.predict(
                    activity=activity,
                    ui_elements=ui_elements,
                    action_history=action_history
                )

        return {
            "single_action": SingleActionPredictor()
        }
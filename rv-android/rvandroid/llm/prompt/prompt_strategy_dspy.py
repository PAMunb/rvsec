# rvandroid/llm/prompt/prompt_strategy_dspy.py
import logging
from typing import Dict, Any, Optional, List

import dspy
from dspy import Signature, InputField, OutputField

from rvandroid.llm.prompt.prompt_strategy import PromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.parser_factory import ParserType


class DSPyPromptStrategy(PromptStrategy):
    """
    Specialized prompt strategy for DSPy models.
    Takes advantage of DSPy's programmatic approach to prompt engineering.
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
        self._signature = None
        self._action_schema = None

    def generate_system_prompt(self) -> str:
        """
        Generate system prompt optimized for DSPy models.

        Returns:
            System prompt string
        """
        return """You are an Android UI testing expert. Your task is to analyze the current app state and suggest the MOST EFFECTIVE NEXT ACTIONS to take for testing the application thoroughly.

Focus on:
1. Systematically exploring all parts of the application
2. Maximizing code coverage by targeting untested UI elements
3. Prioritizing testing of security-critical methods
4. Testing complete workflows from beginning to end

You will receive information about:
- The current activity screen
- UI elements and their available actions
- Static analysis information about security-critical operations
- Action history showing what has already been tested

Your response must be a valid JSON array of actions with this structure:
[
  {
    "action_type": "click", 
    "target": "resource_id or coordinates", 
    "params": {}, 
    "explanation": "Why this action was chosen"
  }
]

Valid action types:
- click: Tap on a UI element
- long_click: Long press on a UI element
- scroll_up/scroll_down/scroll_left/scroll_right: Scroll in a direction
- set_text: Enter text into a field (include "text" in params)
- key_event: Use system keys like BACK, HOME (include "name" in params)

FORM FILLING GUIDELINES:
- Fill forms in a logical sequence (inputs first, then submit)
- Use appropriate values for different field types
- Interact with dropdowns by clicking first, then scrolling
- Test edge cases with invalid inputs

WORKFLOW TESTING GUIDELINES:
- Complete one interaction sequence before starting another
- Prioritize unexplored elements over previously tested ones
- Use BACK to navigate when workflows are complete
- Test security-critical elements thoroughly

Your response must be valid JSON without any additional text."""

    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """
        Generate structured user prompt for DSPy with clear sections.

        Args:
            state: Current state dictionary

        Returns:
            User prompt string
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

                                action_desc = f"    - `{action.text}` {security_tag}"
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

            # Detect forms and other patterns
            has_text_fields = any("text field" in item.base_description.lower() for item in screen_description.items)
            has_dropdowns = any(
                "dropdown" in item.base_description.lower() or "spinner" in item.base_description.lower() for item in
                screen_description.items)
            has_buttons = any("button" in item.base_description.lower() for item in screen_description.items)

            # Provide workflow-specific guidance
            if has_text_fields and has_buttons:
                workflow_section.append(
                    "- This screen appears to have a form. Fill all text fields before clicking action buttons.")
                workflow_section.append("- Use contextually appropriate test data for each field.")

            if has_dropdowns:
                workflow_section.append(
                    "- IMPORTANT: For dropdowns, you must CLICK the dropdown first to open it, then use scroll actions.")

            # Check action history for patterns
            action_history = state.get("action_history", [])
            if action_history:
                # Detect if we've been clicking the same button repeatedly
                button_clicks = [a for a in action_history[-5:] if isinstance(a, str) and "CLICK" in a]
                if len(button_clicks) >= 3 and all(b == button_clicks[0] for b in button_clicks):
                    workflow_section.append(
                        "- You appear to be repeatedly clicking the same element. Consider using BACK or trying different inputs.")

                # Detect if we've filled text fields but not submitted
                filled_fields = any(isinstance(a, str) and "FILLED" in a for a in action_history[-5:])
                if filled_fields and not any(isinstance(a, str) and "SUBMITTED" in a for a in action_history[-3:]):
                    workflow_section.append(
                        "- Text fields have been filled. Consider clicking a submission/action button to complete the workflow.")

            sections.append("\n".join(workflow_section))

            # Section 6: Testing task with specific instructions
            sections.append("""## TESTING TASK:
Based on the current state and action history, determine the most effective actions to test this screen.
Return EXACTLY 3 actions in valid JSON format.
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
Could not fully analyze the current screen. Please suggest 1-2 basic testing actions.
Focus on exploring visible elements and using BACK if needed.

## TESTING TASK:
Suggest basic testing actions in valid JSON format.
"""
            return simple_prompt

    def _get_action_schema(self):
        """
        Get the DSPy signature for action generation.

        Returns:
            DSPy Signature for action generation
        """
        if self._signature is None:
            # Define a schema for Android testing actions
            action_schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action_type": {
                            "type": "string",
                            "enum": ["click", "long_click", "scroll_up", "scroll_down", "scroll_left", "scroll_right",
                                     "set_text", "key_event"]
                        },
                        "target": {
                            "type": "string"
                        },
                        "params": {
                            "type": "object"
                        },
                        "explanation": {
                            "type": "string"
                        }
                    },
                    "required": ["action_type", "target", "params", "explanation"]
                }
            }

            # Create a DSPy signature for structured output
            self._signature = Signature(
                inputs=[
                    InputField("activity", description="Current Android activity"),
                    InputField("ui_elements", description="Available UI elements and actions"),
                    InputField("action_history", description="Previous testing actions")
                ],
                outputs=[
                    OutputField("actions", description="JSON array of testing actions", schema=action_schema)
                ]
            )

        return self._signature

    # Métodos adicionais para a classe DSPyPromptStrategy

    def define_dspy_signatures(self):
        """
        Define DSPy signatures para diferentes tipos de tarefas de teste.
        Retorna um dicionário de assinaturas que podem ser usadas com base no contexto.
        """
        # Definir signature para previsão baseada em action_id
        action_id_signature = dspy.Signature(
            inputs=[
                dspy.InputField("activity", description="Current Android activity"),
                dspy.InputField("ui_elements", description="Available UI elements and actions"),
                dspy.InputField("action_history", description="Previous testing actions")
            ],
            outputs=[
                dspy.OutputField("actions", description="JSON array of actions with action_id field")
            ]
        )

        # Definir signature para previsão baseada em coordenadas
        coordinate_signature = dspy.Signature(
            inputs=[
                dspy.InputField("activity", description="Current Android activity"),
                dspy.InputField("ui_elements", description="Available UI elements and actions"),
                dspy.InputField("action_history", description="Previous testing actions")
            ],
            outputs=[
                dspy.OutputField("actions", description="JSON array of actions with coordinates")
            ]
        )

        # Definir signature para previsão de uma única ação
        single_action_signature = dspy.Signature(
            inputs=[
                dspy.InputField("activity", description="Current Android activity"),
                dspy.InputField("ui_elements", description="Available UI elements and actions"),
                dspy.InputField("action_history", description="Previous testing actions")
            ],
            outputs=[
                dspy.OutputField("action", description="Single JSON action object")
            ]
        )

        return {
            "action_id": action_id_signature,
            "coordinate": coordinate_signature,
            "single_action": single_action_signature
        }

    def analyze_screen_context(self, screen_description) -> Dict[str, Any]:
        """
        Analisa o contexto da tela para determinar a melhor estratégia de prompt.

        Args:
            screen_description: Descrição da tela atual

        Returns:
            Dicionário com análise do contexto
        """
        context = {
            "is_form": False,
            "has_text_fields": False,
            "has_buttons": False,
            "has_dropdowns": False,
            "has_security_actions": False,
            "form_elements_count": 0,
            "interactive_elements_count": 0
        }

        # Analisa os elementos da tela
        for item in screen_description.items:
            desc = item.base_description.lower()

            # Conta elementos interativos
            if item.actions:
                context["interactive_elements_count"] += 1

                # Verifica ações relacionadas à segurança
                for action in item.actions:
                    if action.reaches_mop or action.directly_reaches_mop:
                        context["has_security_actions"] = True

            # Detecta elementos de formulário
            if "text field" in desc or "edittext" in desc:
                context["has_text_fields"] = True
                context["form_elements_count"] += 1
            elif "button" in desc:
                context["has_buttons"] = True
                if "submit" in desc or "login" in desc or "next" in desc:
                    context["form_elements_count"] += 1
            elif "dropdown" in desc or "spinner" in desc:
                context["has_dropdowns"] = True
                context["form_elements_count"] += 1
            elif "checkbox" in desc or "radio" in desc:
                context["form_elements_count"] += 1

        # Determina se é um formulário
        context["is_form"] = (context["has_text_fields"] and context["has_buttons"]) or context[
            "form_elements_count"] >= 2

        return context

    def _get_dspy_modules(self):
        """
        Cria módulos DSPy específicos para diferentes cenários de teste.

        Returns:
            Dicionário com diferentes módulos DSPy
        """

        # Define módulo para previsão de ações baseadas em action_id
        class ActionIDPredictor(dspy.Module):
            def __init__(self):
                super().__init__()
                self.predict = dspy.ChainOfThought("action_id_signature")

            def forward(self, activity, ui_elements, action_history):
                return self.predict(
                    activity=activity,
                    ui_elements=ui_elements,
                    action_history=action_history
                )

        # Define módulo para previsão de ações baseadas em coordenadas
        class CoordinateActionPredictor(dspy.Module):
            def __init__(self):
                super().__init__()
                self.predict = dspy.ChainOfThought("coordinate_signature")

            def forward(self, activity, ui_elements, action_history):
                return self.predict(
                    activity=activity,
                    ui_elements=ui_elements,
                    action_history=action_history
                )

        # Define módulo para previsão de uma única ação
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
            "action_id": ActionIDPredictor(),
            "coordinate": CoordinateActionPredictor(),
            "single_action": SingleActionPredictor()
        }
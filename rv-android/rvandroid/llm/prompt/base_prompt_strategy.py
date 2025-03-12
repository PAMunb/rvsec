# rvandroid/llm/prompt/base_prompt_strategy.py
import logging
from typing import Dict, List, Any, Optional

from rvandroid.llm.prompt.prompt_strategy import PromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.parser_factory import ParserType


class BasePromptStrategy(PromptStrategy):
    """
    Base class for all prompt strategies that implements common functionality.
    Contains shared system prompts, utility methods, and basic structure.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, parser_type: ParserType = ParserType.DROIDBOT):
        super().__init__(static_data, parser_type)
        self.logger = logging.getLogger(__name__)

    def generate_system_prompt(self) -> str:
        """
        Generate a standardized system prompt to be used across different LLM providers.
        This base implementation provides a comprehensive system prompt that works well
        with most models.

        Returns:
            System prompt string
        """
        return """You are an Android UI testing expert. Your task is to analyze the current app state and suggest the MOST EFFECTIVE NEXT ACTIONS to take for testing the application thoroughly.

Focus on:
1. Systematically exploring ALL parts of the application, not just the current screen
2. Maximizing code coverage by targeting untested UI elements
3. Prioritizing the examination of methods of interest that interact with points defined in formal specifications, enabling verdict emissions during monitored execution
4. Testing complete workflows from start to finish

Your response must be a valid JSON array of actions with this structure:
[
  {
    "action_id": "5",  
    "params": {},  
    "explanation": "Detailed explanation of why this action was chosen as the next step"
  }
]

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

REVIEW the action history carefully to understand what has already been tested and choose the most logical next action.

DO NOT include any additional text outside of the JSON array. Your response must be valid JSON that can be parsed directly."""

    def _add_workflow_guidance(self, screen_description, action_history=None) -> str:
        """
        Add generic workflow guidance based on detected UI elements and action history.
        Encourages exploration after repeated actions.

        Args:
            screen_description: The parsed screen description
            action_history: List of previous actions

        Returns:
            String containing workflow guidance
        """
        guidance = "WORKFLOW GUIDANCE:\n"

        # Detect form patterns
        input_fields = []
        dropdowns = []
        buttons = []
        submit_buttons = []

        for item in screen_description.items:
            if "Editable text field" in item.base_description:
                input_fields.append(item)
            elif "Dropdown spinner" in item.base_description or "Spinner" in item.base_description:
                dropdowns.append(item)
            elif "Button" in item.base_description:
                buttons.append(item)
                # Check if this might be a submit/action button
                view_text = item.view.get("text", "").lower() if item.view.get("text") else ""
                if view_text and any(keyword in view_text for keyword in
                                     ["submit", "login", "save", "apply", "ok", "next", "continue",
                                      "generate", "create", "send", "search", "encrypt", "decrypt"]):
                    submit_buttons.append(item)

        # Analyze action history to determine form state and detect repetition
        inputs_filled = False
        dropdown_clicked = False
        repeated_submit_count = 0
        back_needed = False

        if action_history:
            # Check if input fields have been filled
            set_text_count = sum(
                1 for action in action_history if isinstance(action, str) and "set_text" in action.lower())
            if set_text_count > 0:
                inputs_filled = True

            # Check if dropdowns have been clicked
            for action in action_history:
                if isinstance(action, str) and "click" in action.lower() and any(
                        spinner_term in action.lower() for spinner_term in ["spinner", "dropdown"]):
                    dropdown_clicked = True
                    break

            # Check for repeated submit button clicks
            if submit_buttons:
                submit_button_text = submit_buttons[0].view.get("text", "").lower()
                submit_count = 0

                # Count consecutive identical button clicks at the end of history
                for action in reversed(action_history):
                    if isinstance(action, str) and "click" in action.lower() and submit_button_text in action.lower():
                        submit_count += 1
                    else:
                        break

                repeated_submit_count = submit_count

                # If same button clicked multiple times, suggest exploring other areas
                if repeated_submit_count >= 3:
                    back_needed = True

        # Generate appropriate guidance based on detected elements and history
        if back_needed:
            guidance += "- EXPLORATION NEEDED: You have tested the current workflow multiple times.\n"
            guidance += "- Consider using the BACK button to navigate to previous screens and explore other functionality.\n"
            guidance += "- Alternatively, try different input values or select different options from dropdowns.\n"
        elif dropdowns and not dropdown_clicked:
            guidance += "- This screen contains dropdown menu(s).\n"
            guidance += "- CRITICAL: You must CLICK the dropdown first to open it, THEN scroll to find option.\n"
            guidance += "- Proper sequence: 1) Click the dropdown to open it → 2) Scroll to find option → 3) Click to select option → 4) Fill other inputs → 5) Click action button.\n"
        elif dropdowns and dropdown_clicked:
            # Dropdown has been clicked, now guide to select an option
            guidance += "- Dropdown has been clicked. Now scroll to find the desired option and click to select it.\n"
            guidance += "- After selecting from the dropdown, proceed to fill any input fields before clicking action buttons.\n"

        if submit_buttons and (input_fields or dropdowns):
            guidance += "- This screen contains a form with input fields and action buttons.\n"

            if dropdowns and not dropdown_clicked:
                guidance += "- FORM STATUS: Dropdown selection is needed first.\n"
                guidance += "- NEXT STEP: Click the dropdown spinner to open it before you can select an option.\n"
            elif inputs_filled and (not dropdowns or dropdown_clicked):
                if repeated_submit_count >= 3:
                    guidance += "- FORM STATUS: Form workflow has been tested multiple times.\n"
                    guidance += "- NEXT STEP: Consider using BACK to explore other parts of the application.\n"
                else:
                    guidance += "- FORM STATUS: Form appears to be completely filled based on action history.\n"
                    button_text = submit_buttons[0].view.get('text', 'ACTION')
                    guidance += f"- NEXT STEP: Consider clicking the {button_text} button to complete the workflow.\n"
            elif input_fields and not inputs_filled and (not dropdowns or dropdown_clicked):
                guidance += "- NEXT STEP: Fill the input fields before clicking action buttons.\n"
        elif input_fields and not submit_buttons:
            guidance += "- This screen contains input fields. Fill these with appropriate test data.\n"
        elif buttons and not input_fields and not dropdowns:
            guidance += "- This screen contains multiple buttons. Test them systematically to explore application functionality.\n"

        # If no specific patterns detected, provide general guidance
        if guidance == "WORKFLOW GUIDANCE:\n":
            guidance += "- Explore UI elements systematically from top to bottom.\n"
            guidance += "- Complete one interaction sequence before moving to another.\n"

        return guidance + "\n"

    def _get_transitions_for_action(self, activity: str, widget_id: str, action) -> List[str]:
        """
        Find possible screen transitions for a given action.

        Args:
            activity: Current activity name
            widget_id: Widget identifier
            action: ItemAction being checked

        Returns:
            List of target activity names this action might transition to
        """
        transitions = []

        if not self.static_data or not self.static_data.wtg:
            return transitions

        # Get activity class
        activity_class = None
        if self.static_data.classes:
            activity_class = self.static_data.classes.get_clazz(activity)

        if not activity_class:
            return transitions

        # Find edges from current activity
        for edge in self.static_data.wtg.graph.edges(data=True):
            if edge[0].name == activity_class.name:
                target_activity = edge[1].name
                events = edge[2].get('events', [])

                # Check if any event matches our widget and action type
                for event in events:
                    if (event.widget_id == widget_id or not widget_id) and \
                            event.event_type == action.event:
                        transitions.append(target_activity)
                        break

        return transitions

    def _infer_input_type(self, view: Dict, widget_id: str) -> str:
        """
        Infer the input type for a text field based on properties and static analysis.

        Args:
            view: View data dictionary
            widget_id: Widget identifier

        Returns:
            Inferred input type as string
        """
        # Try to find widget in static data
        widget = None
        if self.static_data and self.static_data.windows:
            activity = self.parser.get_activity_name({})  # Get current activity
            window = self.static_data.windows.get_window(activity)
            if window:
                widget = window.get_widget_by_name(widget_id)

        # Use widget input_type if available
        if widget and hasattr(widget, 'input_type') and widget.input_type:
            return widget.input_type

        # Otherwise infer from view properties
        input_type = view.get("input_type", 0)
        hint = view.get("hint", "")
        text = view.get("text", "")
        resource_id = view.get("resource_id", "")

        # Check common patterns in properties
        lower_id = resource_id.lower() if resource_id else ""
        lower_hint = hint.lower() if hint else ""
        lower_text = text.lower() if text else ""

        if "password" in lower_id or "password" in lower_hint or view.get("is_password", False):
            return "password"
        elif "email" in lower_id or "email" in lower_hint or "email" in lower_text:
            return "email address"
        elif "phone" in lower_id or "phone" in lower_hint:
            return "phone number"
        elif "search" in lower_id or "search" in lower_hint:
            return "search query"
        elif "username" in lower_id or "username" in lower_hint or "user" in lower_id:
            return "username"
        elif "url" in lower_id or "website" in lower_hint:
            return "URL"

        # Default
        return "text"

    def _add_static_analysis_context(self, activity: str) -> str:
        """
        Enhanced static analysis context that includes clearer transition information.

        Args:
            activity: Current activity name

        Returns:
            String containing static analysis context
        """
        context = "Static Analysis Context:\n"

        # Get information about the activity class
        activity_class = None
        if self.static_data and self.static_data.classes:
            activity_class = self.static_data.classes.get_clazz(activity)

        if not activity_class:
            return context + "No static analysis data available for this activity.\n\n"

        # Count methods with different properties
        reachable_methods = [m for m in activity_class.methods if m.reachable]
        critical_methods = [m for m in activity_class.methods if m.reaches_mop]
        direct_critical_methods = [m for m in activity_class.methods if m.directly_reaches_mop]

        # Add method statistics
        context += f"- Activity contains {len(reachable_methods)} reachable methods\n"
        context += f"- {len(critical_methods)} methods can reach operations of interest\n"
        context += f"- {len(direct_critical_methods)} methods directly call operations of interest\n"

        # Add enhanced window transition information with actions
        if self.static_data and self.static_data.wtg:
            edges = [edge for edge in self.static_data.wtg.graph.edges(data=True)
                     if edge[0].name == activity_class.name]

            if edges:
                # Format transitions with related actions
                context += f"- Can transition to {len(edges)} other activities/screens:\n"
                for edge in edges:
                    to_activity = edge[1].name
                    events = edge[2].get('events', [])

                    # Find corresponding actions if possible
                    for event in events:
                        widget_id = event.widget_id
                        event_type = event.event_type

                        # Find matching action IDs from the current state
                        context += f"  - Can transition to {to_activity}"
                        if widget_id:
                            context += f" via widget ID: {widget_id}"
                        if event_type:
                            context += f" using {event_type.name}"
                        context += "\n"

        return context + "\n"

    def _get_widget_static_info(self, activity: str, widget_id: str) -> str:
        """
        Get static analysis information for a specific widget.

        Args:
            activity: Activity name
            widget_id: Widget identifier

        Returns:
            String containing widget static analysis information
        """
        if not self.static_data or not self.static_data.windows:
            return ""

        window = self.static_data.windows.get_window(activity)
        if not window:
            return ""

        widget = window.get_widget_by_name(widget_id)
        if not widget:
            return ""

        # Gather information about widget events
        event_info = []
        for event in widget.events:
            if event.signature in self.static_data.classes.methods:
                method = self.static_data.classes.methods[event.signature]
                event_desc = f"{event.type.name}"
                if method.directly_reaches_mop:
                    event_desc += " (directly reaches operations of interest)"
                elif method.reaches_mop:
                    event_desc += " (can reach operations of interest)"
                event_info.append(event_desc)

        if not event_info:
            return ""

        return "Registered events: " + ", ".join(event_info)
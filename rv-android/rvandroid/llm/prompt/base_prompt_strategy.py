# rvandroid/llm/prompt/base_prompt_strategy.py
"""
Base Prompt Strategy Implementation

Provides a robust foundation for all prompt strategy implementations.
This class implements shared functionality like workflow guidance,
input type inference, and action analysis to reduce code duplication.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple

from rvandroid.llm.prompt.prompt_strategy import PromptStrategy
from rvandroid.llm.prompt.prompt_template import PromptTemplate, PromptLibrary
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription


class BasePromptStrategy(PromptStrategy):
    """
    Base class for all prompt strategies implementing shared functionality.
    
    ### Architectural Decisions:
    - Implements common prompt generation patterns and utilities
    - Provides reusable workflow analysis and guidance functions
    - Integrates with template system for consistent prompt generation
    - Supports different complexity levels of static analysis integration
    - Maintains backward compatibility with existing prompt consumers

    ### Role in the System:
    - Serves as the foundation for all prompt strategy implementations
    - Reduces code duplication across different strategy variants
    - Ensures consistent handling of static analysis and workflow data
    - Facilitates template-based prompt generation
    - Provides flexible extension points for specialized strategies
    """

    def __init__(self, 
                 static_data: Optional[StaticAnalysisData] = None, 
                 parser: Union[ParserType, AbstractScreenParser, None] = None,
                 detailed_static_analysis: bool = False,
                 include_screenshots: bool = False):
        """
        Initialize the base prompt strategy.

        Args:
            static_data: Static analysis data (optional)
            parser: Parser type or instance for screen parsing
            detailed_static_analysis: Whether to include detailed static analysis
            include_screenshots: Whether to include screenshot analysis
        """
        super().__init__(static_data, parser)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Configuration flags
        self.detailed_static_analysis = detailed_static_analysis
        self.include_screenshots = include_screenshots
        
        # Initialize template system
        self.system_template = PromptLibrary.get_template("system_base")
        self.user_template = PromptLibrary.get_template("user_base")
        
        if not self.system_template or not self.user_template:
            # Fall back to creating new templates
            self.system_template = PromptLibrary.system_base_template()
            self.user_template = PromptLibrary.user_base_template()
            
        # Track the last processed screen description
        self._last_screen_description = None

    def generate_system_prompt(self) -> str:
        """
        Generate a standardized system prompt using the template system.
        This implementation provides a comprehensive system prompt that works well
        with most models.

        Returns:
            System prompt string
        """
        # Default to balanced exploration
        exploration_goal = ("Systematically exploring ALL parts of the application, "
                           "balancing breadth and depth to maximize coverage")
        
        # Default to multi-action format
        response_format = PromptLibrary.multi_action_format()
        
        # No additional guidelines by default
        additional_guidelines = ""
        
        # Render template with parameters
        return self.system_template.render({
            "exploration_goal": exploration_goal,
            "response_format": response_format,
            "additional_guidelines": additional_guidelines
        })

    def process_screen(self, state: Dict[str, Any]) -> Optional[ScreenDescription]:
        """
        Process the screen state to get a structured representation.
        This is called before generating prompts to extract and analyze the screen.
        
        Args:
            state: Current application state dictionary
            
        Returns:
            ScreenDescription object or None if parsing fails
        """
        try:
            # Parse the screen to get a structured representation
            screen_description = self.parser.parse(state, self.static_data)
            
            # Store the screen description for later use
            self._last_screen_description = screen_description
            
            return screen_description
            
        except Exception as e:
            self.logger.error(f"Error processing screen: {e}", exc_info=True)
            return None

    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """
        Generate a user prompt based on current application state.
        Uses template system to create a consistent, structured prompt.

        Args:
            state: Current application state dictionary

        Returns:
            Formatted user prompt string
        """
        try:
            # Use screen description if already processed, otherwise parse now
            if "screen_description" in state and isinstance(state["screen_description"], ScreenDescription):
                screen_description = state["screen_description"]
            elif self._last_screen_description:
                screen_description = self._last_screen_description
            else:
                # Try to parse as a fallback
                screen_description = self.process_screen(state)
                if not screen_description:
                    raise ValueError("Failed to obtain screen description")
            
            # Get activity name with error handling
            try:
                activity = self.parser.get_activity_name(state)
            except (ValueError, AttributeError):
                activity = state.get("package_name", "unknown.package") + ".UnknownActivity"
                self.logger.warning(f"Using fallback activity name: {activity}")
            
            # Format UI elements for the prompt
            ui_elements = self._format_ui_elements(screen_description, state)
            
            # Get static analysis context
            if self.detailed_static_analysis:
                static_context = self._get_detailed_static_analysis_context(activity)
            else:
                static_context = self._add_static_analysis_context(activity)
                
            # Format action history if available
            action_history = self._format_action_history(state)
            
            # Generate the summary section
            summary = self._generate_summary(activity, screen_description, state)
            
            # Add screenshot analysis if enabled
            if self.include_screenshots:
                screenshot_analysis = self._get_screenshot_analysis(state)
                if screenshot_analysis:
                    static_context += screenshot_analysis
                    
            # Add transition guidance if available
            transition_guidance = state.get("transition_guidance")
            if transition_guidance:
                nav_guidance = self._get_transition_guidance(state)
                if nav_guidance:
                    static_context += nav_guidance
            
            # Add workflow guidance based on UI elements and history
            workflow = self._add_workflow_guidance(screen_description, state.get("action_history", []))
            if workflow:
                summary += "\n\n" + workflow
                
            # Render the template with all components
            return self.user_template.render({
                "activity": activity,
                "static_context": static_context,
                "ui_elements": ui_elements,
                "action_history": action_history,
                "summary": summary
            })
            
        except Exception as e:
            self.logger.error(f"Error generating user prompt: {e}", exc_info=True)
            
            # Provide a simple fallback prompt
            return (f"Current Activity: {state.get('activity', 'Unknown')}\n\n"
                   f"Analyze the current screen and suggest appropriate testing actions.")

    def _format_ui_elements(self, screen_description: ScreenDescription, state: Dict[str, Any]) -> str:
        """
        Format UI elements for prompt display.

        Args:
            screen_description: Parsed screen description
            state: Current application state

        Returns:
            Formatted UI elements string
        """
        if not screen_description.items:
            return "No UI elements detected in the current state."
            
        lines = []
        activity = state.get("activity", "")
        
        for item in screen_description.items:
            view = item.view
            widget_id = view.get("resource_id", "").split("/")[-1] if view.get("resource_id") else "unknown"
            
            # Format the item description
            lines.append(f"- {item.base_description}")
            
            # Add actions with their IDs
            if item.actions:
                lines.append("  Available actions:")
                for action in item.actions:
                    # Add indicators for operations of interest
                    importance_tag = ""
                    if action.directly_reaches_mop:
                        importance_tag = " [CRITICAL: Directly reaches operation of interest]"
                    elif action.reaches_mop:
                        importance_tag = " [IMPORTANT: Can reach operation of interest]"
                    
                    # Add usage history
                    history_tag = ""
                    if "action_specific_history" in state:
                        action_specific_history = state["action_specific_history"].get(str(action.id), [])
                        if action_specific_history:
                            count = len(action_specific_history)
                            history_tag = f" [Used {count} times]"
                    
                    # Create detailed action description
                    action_desc = f"  - {action.text} (action_id: \"{action.id}\"){importance_tag}{history_tag}"
                    
                    # Check for transitions
                    transitions = self._get_transitions_for_action(activity, widget_id, action)
                    if transitions:
                        action_desc += f" -> Will transition to: {', '.join(transitions)}"
                    
                    lines.append(action_desc)
                    
                    # Add most recent usage if available
                    if "action_specific_history" in state:
                        action_specific_history = state["action_specific_history"].get(str(action.id), [])
                        if action_specific_history and len(action_specific_history) > 0:
                            last_usage = action_specific_history[-1]
                            lines.append(f"    Last usage: {last_usage}")
                
                # Add guidance for parameterized actions
                has_text_action = any(a.text.startswith("SET_TEXT") for a in item.actions)
                if has_text_action:
                    # Get input hints or description
                    hint = ""
                    if "hint" in view and view["hint"]:
                        hint = f" (hint: {view['hint']})"
                    elif "content_description" in view and view["content_description"]:
                        hint = f" (description: {view['content_description']})"
                    elif "text" in view and view["text"]:
                        hint = f" (current text: {view['text']})"
                    
                    # Infer input type
                    input_type = self._infer_input_type(view, widget_id)
                    if input_type:
                        lines.append(f"  Input type appears to be: {input_type}{hint}")
                
                # Add static analysis info if available
                static_info = self._get_widget_static_info(activity, widget_id)
                if static_info:
                    lines.append(f"  Static analysis: {static_info}")
        
        return "\n".join(lines)

    def _format_action_history(self, state: Dict[str, Any]) -> str:
        """
        Format action history for display in the prompt.

        Args:
            state: Current application state

        Returns:
            Formatted action history string
        """
        if "action_history" not in state or not state["action_history"]:
            return ""
            
        action_history = state["action_history"]
        
        # Limit history to most recent actions
        max_actions = 15
        recent_actions = action_history[-max_actions:] if len(action_history) > max_actions else action_history
        
        # Create formatted history string
        history_text = ["ACTION HISTORY (most recent actions last):"]
        for i, action in enumerate(recent_actions):
            history_text.append(f"{i + 1}. {action}")
            
        return "\n".join(history_text)

    def _generate_summary(self, activity: str, screen_description: ScreenDescription, 
                         state: Dict[str, Any]) -> str:
        """
        Generate a summary section for the prompt.

        Args:
            activity: Current activity name
            screen_description: Parsed screen description
            state: Current application state

        Returns:
            Generated summary string
        """
        summary = f"SUMMARY: You are testing the {activity} screen."
        
        # Detect form patterns
        form_elements = [item for item in screen_description.items
                         if any(t in item.base_description.lower()
                                for t in ["text field", "spinner", "checkbox"])]
        
        buttons = [item for item in screen_description.items
                   if "button" in item.base_description.lower()]
        
        # Identify screen type
        if form_elements and buttons:
            summary += " This screen appears to contain a form with input fields and buttons."
            
            # Check if this appears to be a login form
            login_related = any(("login" in item.base_description.lower() or
                               "username" in item.base_description.lower() or
                               "password" in item.base_description.lower())
                              for item in form_elements)
            
            if login_related:
                summary += " This appears to be a login form."
                
        elif buttons and len(buttons) > 3:
            summary += " This screen contains multiple buttons/controls that should be systematically tested."
            
        elif "menu" in activity.lower() or len(screen_description.items) > 5:
            summary += " This appears to be a menu or list screen with multiple options."
        
        # Add testing instructions
        summary += " Based on the state analysis and action history, suggest the most appropriate testing actions."
        
        return summary

    def _add_workflow_guidance(self, screen_description: ScreenDescription, action_history: List[Any]) -> str:
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
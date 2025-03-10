import logging
from typing import Dict, List, Optional

from rvandroid.llm.prompt.prompt_strategy import PromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.parser_factory import ParserType


class BasicPromptStrategy001(PromptStrategy):
    """
    Enhanced prompt strategy for Android UI testing with action ID references.
    Generates prompts that instruct LLMs to use action IDs for more precise action selection.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, parser_type: ParserType = ParserType.DROIDBOT):
        super().__init__(static_data, parser_type)
        self.logger = logging.getLogger(__name__)

    def generate_system_prompt(self) -> str:
        """
        Generate an enhanced system prompt with the new action_id based format.
        """
        return """You are an Android UI testing expert. Your task is to systematically analyze the current app state and suggest the most effective testing actions to maximize coverage and find potential issues.

Focus on:
1. Maximizing code coverage by targeting untested UI elements
2. Prioritizing testing of security-critical methods that directly or indirectly affect operations of interest
3. Systematically exploring all application states in a logical sequence
4. Testing complex UI interactions and edge cases

IMPORTANT: You will be provided with a list of possible actions, each with a unique action_id. Your job is to select which actions to perform and in what ORDER. The order is CRITICAL as you are systematically testing an Android screen, not randomly triggering events.

Format your response as a valid JSON array of actions following this schema:
[
  {
    "action_id": "5",  
    "params": {},  
    "explanation": "Detailed explanation of why this action was chosen"
  },
  ...
]

For actions that require parameters (like SET_TEXT), you must include appropriate values:
[
  {
    "action_id": "5",  
    "params": {"text": "test@example.com"},  
    "explanation": "Entering a valid email address in the email field"
  }
]

GUIDELINES FOR ACTION SELECTION:
1. ORDERING MATTERS - arrange actions in a logical testing sequence (e.g., fill a form before submitting it)
2. If an action leads to a screen transition, it should typically be the last action in your sequence
3. For text inputs, generate contextually appropriate values based on the field type (email, password, etc.)
4. Prioritize actions that trigger security-critical code paths (marked as [CRITICAL] or [IMPORTANT])
5. Choose 3-5 most effective actions for thorough testing
6. Ensure your suggested actions form a coherent testing strategy
7. For login forms: first fill username, then password, THEN click login button
8. For registration forms: fill ALL fields in a logical order before submission
9. If a screen has a primary action (OK, NEXT, CONTINUE), it should be the LAST action
10. Prioritize actions that trigger security-critical code paths (marked as [CRITICAL] or [IMPORTANT])
11. For dropdowns/spinners: click to open them first, then select an option
12. For checkboxes in a form: handle them BEFORE clicking submit buttons

IMPORTANT RULES:
1. SEQUENCE MATTERS - actions must be in a logical order (e.g., fill all form fields BEFORE submitting)
2. FORM FILLING - when you see a form, ALWAYS fill out all required fields before clicking submit/next buttons
3. NEVER include a BACK action unless absolutely necessary (only when no other actions are possible)
4. Prioritize exploring new functionality over revisiting previous screens
5. For text inputs, provide appropriate values based on the field type (emails, passwords, etc.)
6. Choose 3-5 most effective actions for thorough testing

You will be provided with a list of possible actions, each with a unique action_id. Your job is to select which actions to perform and in what ORDER. The order is CRITICAL.

DO NOT include any additional text outside of the JSON array. Your response must be valid JSON that can be parsed directly."""

    def generate_user_prompt(self, state: Dict) -> str:
        """
        Generate an enhanced user prompt with explicit action IDs and clearer transition information.
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

            # Add action history if available
            if "action_history" in state:
                prompt += "\nRecent Actions:\n"
                history = state.get("action_history", [])
                recent_actions = history[-20:] if len(history) > 20 else history
                for action in recent_actions:
                    prompt += f"- {action}\n"

            # Add instructions for the LLM
            prompt += f"\nSUMMARY: You are testing the {activity} screen. Select 3-5 actions from the available options above that would be most effective for testing this screen. Remember to return your answer as a JSON array using the action_id values provided. The order of actions is critical - arrange them in a logical testing sequence."

            # Add special instructions for screen transitions
            if "can_transition_to" in static_context:
                prompt += "\n\nNOTE: If you decide to test a screen transition, it should typically be your last action since it will navigate away from the current screen."

            return prompt

        except Exception as e:
            # Handle any errors during prompt generation
            self.logger.error(f"Error generating prompt: {e}", exc_info=True)

            # Return a simple fallback prompt that will still work
            simple_prompt = (
                "Error occurred while analyzing the current screen. Please suggest 1-2 basic testing actions.\n"
                "Return your response as a JSON array of actions with action_id values that might be on the screen:\n"
                "[{\"action_id\": \"1\", \"params\": {}, \"explanation\": \"Basic test action\"}]"
            )
            return simple_prompt

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
        context += f"- {len(critical_methods)} methods can reach security-critical operations\n"
        context += f"- {len(direct_critical_methods)} methods directly call security-critical operations\n"

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
                    action_ids = []  # TODO ........
                    for event in events:
                        widget_id = event.widget_id
                        event_type = event.event_type

                        # Find matching action IDs from the current state
                        # This is a simplified approach - in practice, you may need to look up actions
                        # based on widget ID and event type
                        context += f"  - Can transition to {to_activity}"
                        if widget_id:
                            context += f" via widget ID: {widget_id}"
                        if event_type:
                            context += f" using {event_type.name}"
                        context += "\n"

        return context + "\n"

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

# rvandroid/mcp/strategies/composable_strategy.py
"""Composable strategy implementation using MCP."""

from typing import Dict, Any, List, Optional, Callable

from rvandroid.static.data.static_data import StaticAnalysisData

from rvandroid.mcp.mcp_data_structures import MCPMessage, MCPRole, MCPTextContent
from rvandroid.mcp.strategies.base_strategy import BasePromptStrategy
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser


class ComposablePromptStrategy(BasePromptStrategy):
    """Strategy using composable components for flexibility."""

    def __init__(self,
                 static_data: Optional[StaticAnalysisData] = None,
                 parser: Optional[AbstractScreenParser] = None,
                 **kwargs):
        """Initialize with component-based structure."""
        super().__init__(static_data, parser, **kwargs)

        # Initialize component registry
        self.components: Dict[str, Callable[[Dict[str, Any]], str]] = {
            "header": self._generate_header,
            "state_description": self._generate_state_description,
            "static_analysis": self._generate_static_analysis,
            "action_history": self._generate_action_history,
            "guidance": self._generate_guidance,
            "workflow_hints": self._generate_workflow_hints,
            "action_prioritization": self._generate_action_prioritization
        }

        # Default component order
        self.component_order = [
            "header",
            "state_description",
            "static_analysis",
            "action_history",
            "guidance",
            "workflow_hints",
            "action_prioritization"
        ]

        # Process kwargs for component customization
        if "component_order" in kwargs:
            self.component_order = kwargs["component_order"]

        self.response_format_name = "single_action_format"

    def generate_user_prompt(self, state: Dict[str, Any]) -> List[MCPMessage]:
        """Generate a user prompt using the component composition approach."""
        try:
            # Process the screen first to have a consistent representation
            screen_description = self.process_screen(state)
            state["screen_description"] = screen_description

            # Generate each component in the specified order
            sections = []
            for component_name in self.component_order:
                if component_name in self.components:
                    component_func = self.components[component_name]
                    component_content = component_func(state)
                    if component_content:
                        sections.append(component_content)

            # Join all sections with double newlines
            content = "\n\n".join(sections)

            return [MCPMessage(
                role=MCPRole.USER,
                content=[MCPTextContent(text=content)]
            )]

        except Exception as e:
            self.logger.error(f"Error generating composable prompt: {e}", exc_info=True)
            # Return basic message as fallback
            return [MCPMessage(
                role=MCPRole.USER,
                content=[MCPTextContent(text="Please suggest a testing action for this Android application.")]
            )]

    def _generate_header(self, state: Dict[str, Any]) -> str:
        """Generate the header component."""
        return "I need your help testing an Android application. Please analyze the current state and suggest the most effective testing action."

    def _generate_state_description(self, state: Dict[str, Any]) -> str:
        """Generate the state description component."""
        screen_description = state.get("screen_description")
        if not screen_description:
            return "Current UI State: [Unable to parse UI state]"

        activity = self.parser.get_activity_name(state)
        ui_elements = self._format_ui_elements(screen_description, state)

        return f"Current Activity: {activity}\n\nUI Elements and Available Actions:\n{ui_elements}"

    def _generate_static_analysis(self, state: Dict[str, Any]) -> Optional[str]:
        """Generate the static analysis component."""
        if not self.static_data:
            return None

        activity = self.parser.get_activity_name(state)

        # Get window from static analysis
        window = None
        if self.static_data.windows:
            window = self.static_data.windows.get_window(activity)

        if not window:
            return None

        # Gather relevant methods
        mop_methods = []
        for event in window.events:
            if event.reaches_mop or event.directly_reaches_mop:
                method_desc = f"- {event.method}"
                if event.directly_reaches_mop:
                    method_desc += " (directly reaches monitored operation)"
                elif event.reaches_mop:
                    method_desc += " (indirectly reaches monitored operation)"
                mop_methods.append(method_desc)

        if not mop_methods:
            return None

        return f"STATIC ANALYSIS: The following methods in this screen may trigger monitored operations:\n" + "\n".join(
            mop_methods)

    def _generate_action_history(self, state: Dict[str, Any]) -> Optional[str]:
        """Generate the action history component."""
        if "action_history" not in state or not state["action_history"]:
            return None

        history = state["action_history"]
        recent_actions = history[-10:] if len(history) > 10 else history

        history_section = ["RECENT ACTIONS:"]
        for i, action in enumerate(recent_actions):
            history_section.append(f"{i + 1}. {action}")

        return "\n".join(history_section)

    def _generate_guidance(self, state: Dict[str, Any]) -> Optional[str]:
        """Generate the guidance component."""
        screen_description = state.get("screen_description")
        if not screen_description:
            return None

        # Check for specific UI patterns
        pattern_detected = False
        guidance = ["TESTING GUIDANCE:"]

        # Check for form pattern
        form_elements = [item for item in screen_description.items
                         if hasattr(item, "element_type") and
                         item.element_type in ["EditText", "CheckBox", "Spinner", "RadioButton"]]

        if form_elements:
            pattern_detected = True
            form_fragment = self.library.get_fragment("form_guidelines")
            if form_fragment:
                guidance.append(form_fragment.render({}))

        # Check for list pattern
        list_elements = [item for item in screen_description.items
                         if hasattr(item, "element_type") and
                         item.element_type in ["ListView", "RecyclerView", "ScrollView"]]

        if list_elements:
            pattern_detected = True
            list_fragment = self.library.get_fragment("list_guidelines")
            if list_fragment:
                guidance.append(list_fragment.render({}))

        # Check for navigation pattern
        nav_elements = [item for item in screen_description.items
                        if hasattr(item, "element_type") and
                        item.element_type in ["DrawerLayout", "NavigationView", "TabLayout", "BottomNavigationView"]]

        if nav_elements:
            pattern_detected = True
            nav_fragment = self.library.get_fragment("navigation_guidelines")
            if nav_fragment:
                guidance.append(nav_fragment.render({}))

        if not pattern_detected:
            # General guidance
            guidance.append(
                "1. Focus on unexplored UI elements\n2. Prioritize elements that reach monitored operations\n3. Look for input validation and error handling\n4. Explore navigation paths")

        return "\n\n".join(guidance)

    def _generate_workflow_hints(self, state: Dict[str, Any]) -> Optional[str]:
        """Generate workflow hints component."""
        history = state.get("action_history", [])
        if len(history) < 3:
            return None

        # Simple workflow detection
        if any("login" in action.lower() for action in history[-5:]):
            return "WORKFLOW HINT: You appear to be in a login workflow. Consider testing with both valid and invalid credentials, checking error messages, and testing password recovery flows."

        if any("search" in action.lower() for action in history[-5:]):
            return "WORKFLOW HINT: You appear to be in a search workflow. Consider testing with various search terms, empty searches, and very long search queries."

        if any("form" in action.lower() for action in history[-5:]) or any(
                "field" in action.lower() for action in history[-5:]):
            return "WORKFLOW HINT: You appear to be filling a form. Ensure all required fields are completed before submission, and test with both valid and invalid inputs."

        return None

    def _generate_action_prioritization(self, state: Dict[str, Any]) -> str:
        """Generate action prioritization component."""
        return ("ACTION PRIORITIZATION:\n"
                "1. Actions that directly reach monitored operations [CRITICAL]\n"
                "2. Actions that indirectly reach monitored operations [IMPORTANT]\n"
                "3. Unexplored UI elements and paths\n"
                "4. Elements required to complete the current workflow\n"
                "5. Error handling and edge cases")
   
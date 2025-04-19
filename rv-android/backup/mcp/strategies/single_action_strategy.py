# rvandroid/mcp/strategies/single_action_strategy.py
"""Single action strategy implementation using MCP."""

from typing import Dict, Any, Optional

from rvandroid.static.data.static_data import StaticAnalysisData

from rvandroid.mcp.mcp_data_structures import MCPMessage
from rvandroid.mcp.strategies.base_strategy import BasePromptStrategy
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser


class SingleActionPromptStrategy(BasePromptStrategy):
    """Strategy specialized for generating exactly one action."""

    def __init__(self,
                 static_data: Optional[StaticAnalysisData] = None,
                 parser: Optional[AbstractScreenParser] = None,
                 **kwargs):
        """Initialize single action prompt strategy."""
        super().__init__(static_data, parser, **kwargs)

        # Set single action specific defaults
        self.exploration_goal = "Systematically exploring ALL parts of the application, ensuring exactly ONE action is recommended"
        self.response_format_name = "single_action_format"
        self.additional_guidelines = ("IMPORTANT: You MUST respond with EXACTLY ONE action. "
                                      "The action should be the most valuable next step for testing. "
                                      "Consider coverage, unexplored areas, and monitored operations.")

    def _generate_summary(self, activity: str, screen_description: Any, state: Dict[str, Any]) -> Optional[str]:
        """Generate summary with focused single action guidance."""
        action_history = state.get("action_history", [])

        # Check for form pattern
        form_elements = [item for item in screen_description.items
                         if hasattr(item, "element_type") and
                         item.element_type in ["EditText", "CheckBox", "Spinner", "RadioButton"]]

        if form_elements:
            return ("This screen appears to contain a form. Consider filling required fields "
                    "before submitting. Test with both valid and invalid inputs.")

        # Check for list pattern
        list_elements = [item for item in screen_description.items
                         if hasattr(item, "element_type") and
                         item.element_type in ["ListView", "RecyclerView", "ScrollView"]]

        if list_elements:
            return ("This screen appears to contain a list or scrollable content. "
                    "Consider scrolling to view more items or selecting list items to test selection behavior.")

        # Check for navigation pattern
        nav_elements = [item for item in screen_description.items
                        if hasattr(item, "element_type") and
                        item.element_type in ["DrawerLayout", "NavigationView", "TabLayout", "BottomNavigationView"]]

        if nav_elements:
            return ("This screen appears to contain navigation elements. "
                    "Consider exploring different navigation options to maximize application coverage.")

        return None

    def process_response(self, response: MCPMessage, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process model response to extract a single action."""
        result = super().process_response(response, state)

        # Ensure we have exactly one action
        if "error" not in result:
            if "action" in result:
                # Single action format - good
                return result
            elif "actions" in result and isinstance(result["actions"], list) and result["actions"]:
                # Multiple actions - take first one
                self.logger.warning("Multiple actions returned, using only the first one")
                return {"action": result["actions"][0]}
            else:
                return {"error": "No valid action found in response"}

        return result
   
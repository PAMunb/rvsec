# rvandroid/mcp/strategies/flow_based_batch_strategy.py
"""Flow-based batch action strategy implementation using MCP."""

from typing import Dict, Any, List, Optional

from rvandroid.static.data.static_data import StaticAnalysisData

from rvandroid.mcp.mcp_data_structures import MCPMessage
from rvandroid.mcp.strategies.base_strategy import BasePromptStrategy
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser


class FlowBasedBatchActionStrategy(BasePromptStrategy):
    """Strategy for generating batches of related actions."""

    def __init__(self,
                 static_data: Optional[StaticAnalysisData] = None,
                 parser: Optional[AbstractScreenParser] = None,
                 **kwargs):
        """Initialize batch action strategy."""
        super().__init__(static_data, parser, **kwargs)

        # Set batch action specific defaults
        self.exploration_goal = ("Analyzing UI patterns and generating logical sequences "
                                 "of related actions for complete workflow testing")
        self.response_format_name = "batch_action_format"
        self.additional_guidelines = (
            "IMPORTANT: Analyze the UI to identify patterns like forms, lists, tabs, "
            "navigation elements, and dialogs. Then generate a LOGICAL SEQUENCE of "
            "actions that test complete workflows within the identified pattern.\n\n"
            "FOR EACH PATTERN:\n"
            "1. Begin with a clear pattern identification\n"
            "2. List 2-5 related actions that form a cohesive testing sequence\n"
            "3. Explain the testing objective for this sequence"
        )

        # Pattern detection configuration
        self.detect_forms = kwargs.get("detect_forms", True)
        self.detect_lists = kwargs.get("detect_lists", True)
        self.detect_tabs = kwargs.get("detect_tabs", True)
        self.detect_navigation = kwargs.get("detect_navigation", True)
        self.detect_dialogs = kwargs.get("detect_dialogs", True)

    def _generate_summary(self, activity: str, screen_description: Any, state: Dict[str, Any]) -> str:
        """Generate summary with pattern-specific guidance."""
        patterns = self._detect_patterns(screen_description)

        if not patterns:
            return "No specific UI patterns detected. Consider general exploration actions."

        summary_parts = ["UI PATTERNS DETECTED:"]

        for pattern, confidence in patterns:
            if pattern == "form":
                summary_parts.append(f"- FORM PATTERN detected (confidence: {confidence:.0%})")
                form_fragment = self.library.get_fragment("form_guidelines")
                if form_fragment:
                    summary_parts.append(form_fragment.render({}))

            elif pattern == "list":
                summary_parts.append(f"- LIST PATTERN detected (confidence: {confidence:.0%})")
                list_fragment = self.library.get_fragment("list_guidelines")
                if list_fragment:
                    summary_parts.append(list_fragment.render({}))

            elif pattern == "tabs":
                summary_parts.append(f"- TAB PATTERN detected (confidence: {confidence:.0%})")
                tabs_fragment = self.library.get_fragment("tabs_guidelines")
                if tabs_fragment:
                    summary_parts.append(tabs_fragment.render({}))

            elif pattern == "navigation":
                summary_parts.append(f"- NAVIGATION PATTERN detected (confidence: {confidence:.0%})")
                navigation_fragment = self.library.get_fragment("navigation_guidelines")
                if navigation_fragment:
                    summary_parts.append(navigation_fragment.render({}))

            elif pattern == "dialog":
                summary_parts.append(f"- DIALOG PATTERN detected (confidence: {confidence:.0%})")
                dialog_fragment = self.library.get_fragment("dialog_guidelines")
                if dialog_fragment:
                    summary_parts.append(dialog_fragment.render({}))

        return "\n\n".join(summary_parts)

    def _detect_patterns(self, screen_description: Any) -> List[tuple]:
        """Detect UI patterns in the screen description."""
        patterns = []

        # Check for form pattern
        if self.detect_forms:
            form_score = self._calculate_form_score(screen_description)
            if form_score > 0.5:
                patterns.append(("form", form_score))

        # Check for list pattern
        if self.detect_lists:
            list_score = self._calculate_list_score(screen_description)
            if list_score > 0.5:
                patterns.append(("list", list_score))

        # Check for tab pattern
        if self.detect_tabs:
            tab_score = self._calculate_tab_score(screen_description)
            if tab_score > 0.5:
                patterns.append(("tabs", tab_score))

        # Check for navigation pattern
        if self.detect_navigation:
            navigation_score = self._calculate_navigation_score(screen_description)
            if navigation_score > 0.5:
                patterns.append(("navigation", navigation_score))

        # Check for dialog pattern
        if self.detect_dialogs:
            dialog_score = self._calculate_dialog_score(screen_description)
            if dialog_score > 0.5:
                patterns.append(("dialog", dialog_score))

        # Sort by confidence score
        patterns.sort(key=lambda x: x[1], reverse=True)

        return patterns

    def _calculate_form_score(self, screen_description: Any) -> float:
        """Calculate form pattern confidence score."""
        # Count form elements
        input_elements = 0
        has_submit_button = False
        total_elements = len(screen_description.items)

        if total_elements == 0:
            return 0.0

        for item in screen_description.items:
            element_type = getattr(item, "element_type", "")

            # Count input elements
            if element_type in ["EditText", "CheckBox", "RadioButton", "Spinner", "Switch"]:
                input_elements += 1

            # Check for submit button
            if element_type == "Button":
                text = getattr(item, "text", "").lower()
                content_desc = getattr(item, "content_desc", "").lower()
                resource_id = getattr(item, "resource_id", "").lower()

                if any(submit_term in text or submit_term in content_desc or submit_term in resource_id
                       for submit_term in ["submit", "login", "register", "sign", "save", "done", "ok", "confirm"]):
                    has_submit_button = True

        # Calculate score
        if input_elements == 0:
            return 0.0

        input_ratio = min(input_elements / total_elements, 1.0)

        # Weighted scoring
        score = (0.7 * input_ratio) + (0.3 * has_submit_button)

        return score

    def _calculate_list_score(self, screen_description: Any) -> float:
        """Calculate list pattern confidence score."""
        # Look for list indicators
        list_elements = 0
        has_scrollable = False
        repeated_patterns = 0
        total_elements = len(screen_description.items)

        if total_elements == 0:
            return 0.0

        for item in screen_description.items:
            element_type = getattr(item, "element_type", "")

            # Direct list types
            if element_type in ["ListView", "RecyclerView", "GridView"]:
                list_elements += 1

            # Scrollable indicators
            if element_type == "ScrollView" or getattr(item, "scrollable", False):
                has_scrollable = True

            # Check for repeated element patterns
            # TODO: Implement pattern detection logic

        # Calculate score
        if list_elements == 0 and not has_scrollable:
            return 0.0

        # Weighted scoring
        score = (0.7 * min(list_elements, 1.0)) + (0.3 * has_scrollable)

        return score

    def _calculate_tab_score(self, screen_description: Any) -> float:
        """Calculate tab pattern confidence score."""
        # Look for tab indicators
        tab_elements = 0
        total_elements = len(screen_description.items)

        if total_elements == 0:
            return 0.0

        for item in screen_description.items:
            element_type = getattr(item, "element_type", "")
            resource_id = getattr(item, "resource_id", "").lower()

            # Direct tab types
            if element_type in ["TabLayout", "TabWidget", "ViewPager"]:
                tab_elements += 1

            # Check resource IDs for tab hints
            if any(tab_term in resource_id for tab_term in ["tab", "viewpager", "pager"]):
                tab_elements += 0.5

        # Calculate score
        if tab_elements == 0:
            return 0.0

        score = min(tab_elements, 2.0) / 2.0

        return score

    def _calculate_navigation_score(self, screen_description: Any) -> float:
        """Calculate navigation pattern confidence score."""
        # Look for navigation indicators
        nav_elements = 0
        total_elements = len(screen_description.items)

        if total_elements == 0:
            return 0.0

        for item in screen_description.items:
            element_type = getattr(item, "element_type", "")
            resource_id = getattr(item, "resource_id", "").lower()

            # Direct navigation types
            if element_type in ["DrawerLayout", "NavigationView", "BottomNavigationView", "Toolbar"]:
                nav_elements += 1

            # Check resource IDs for navigation hints
            if any(nav_term in resource_id for nav_term in ["nav", "drawer", "menu", "toolbar", "action_bar"]):
                nav_elements += 0.5

        # Calculate score
        if nav_elements == 0:
            return 0.0

        score = min(nav_elements, 2.0) / 2.0

        return score

    def _calculate_dialog_score(self, screen_description: Any) -> float:
        """Calculate dialog pattern confidence score."""
        # Look for dialog indicators
        dialog_elements = 0
        has_title = False
        has_buttons = False
        total_elements = len(screen_description.items)

        if total_elements == 0:
            return 0.0

        for item in screen_description.items:
            element_type = getattr(item, "element_type", "")
            resource_id = getattr(item, "resource_id", "").lower()

            # Direct dialog types
            if element_type in ["AlertDialog", "Dialog"]:
                dialog_elements += 1

            # Check for title
            if "title" in resource_id:
                has_title = True

            # Check for dialog buttons
            if element_type == "Button" and any(
                    button_term in resource_id for button_term in ["button", "positive", "negative", "neutral"]):
                has_buttons = True

        # Calculate score
        if dialog_elements == 0 and not (has_title and has_buttons):
            return 0.0

        # Weighted scoring
        score = (0.5 * min(dialog_elements, 1.0)) + (0.25 * has_title) + (0.25 * has_buttons)

        return score

    def process_response(self, response: MCPMessage, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process model response to extract batch actions."""
        result = super().process_response(response, state)

        # Check for batch action format
        if "error" not in result:
            if "actions" in result and isinstance(result["actions"], list):
                # Good format - add validation
                return self._validate_batch_actions(result)
            elif "action" in result:
                # Single action format - convert to batch
                self.logger.warning("Single action returned, converting to batch format")
                return {
                    "actions": [result["action"]],
                    "pattern": result.get("pattern", "general"),
                    "objective": result.get("objective", "General testing")
                }
            else:
                return {"error": "No valid actions found in response"}

        return result

    def _validate_batch_actions(self, batch: Dict[str, Any]) -> Dict[str, Any]:
        """Validate batch actions for consistency."""
        # Ensure actions list exists and is not empty
        if not batch.get("actions") or not isinstance(batch["actions"], list):
            self.logger.warning("No actions found in batch")
            return {"error": "No actions found in batch"}

        actions = batch["actions"]

        # Ensure each action has a type
        for i, action in enumerate(actions):
            if not action.get("type"):
                self.logger.warning(f"Action {i} is missing a type")
                return {"error": f"Action {i} is missing a type"}

        # Ensure text actions have text
        for i, action in enumerate(actions):
            if action.get("type") == "text" and not action.get("text"):
                self.logger.warning(f"Text action {i} is missing text")
                return {"error": f"Text action {i} is missing text"}

        # Ensure actions have element_id except for special actions
        for i, action in enumerate(actions):
            if action.get("type") not in ["back", "menu", "home"] and not action.get("element_id"):
                self.logger.warning(f"Action {i} is missing element_id")
                return {"error": f"Action {i} is missing element_id"}

        # Ensure pattern and objective exist
        if not batch.get("pattern"):
            batch["pattern"] = "general"

        if not batch.get("objective"):
            batch["objective"] = "General testing"

        return batch
   
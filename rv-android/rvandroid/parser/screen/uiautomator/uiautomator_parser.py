# rvandroid/parser/uiautomator/uiautomator_parser.py
import logging
from typing import Dict, Any, Optional

from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, Node
from rvandroid.parser.screen.visitor.text_visitor import EnhancedTextVisitor


class UIAutomator2Parser(AbstractScreenParser):
    """
    Parser for UIAutomator2 state data.
    Converts UIAutomator2 XML/JSON data into a ScreenDescription.
    """

    def __init__(self):
        """Initialize the UIAutomator2 parser."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def parse(self, state_data: Dict[str, Any], static_data: Optional[StaticAnalysisData] = None) -> ScreenDescription:
        """
        Parse UIAutomator2 state data into a ScreenDescription.

        Args:
            state_data: Dictionary containing UIAutomator2 state
            static_data: Static analysis data for the application (optional)

        Returns:
            ScreenDescription object

        Raises:
            ValueError: If state data is invalid or cannot be parsed
        """
        # Validate state data
        if not self.validate_state_data(state_data):
            raise ValueError("Invalid UIAutomator2 state data: missing required fields")

        self.logger.info("Parsing UIAutomator2 state data")

        # Extract activity name
        activity_name = self.get_activity_name(state_data)

        # Create tree from hierarchy
        ui_hierarchy = state_data.get("hierarchy", {})
        if not ui_hierarchy:
            self.logger.error("No hierarchy data found in UIAutomator2 state")
            return ScreenDescription(activity_name, [])

        # Convert UIAutomatorNode to standard Node
        root_node = self._convert_to_node_tree(ui_hierarchy)

        if not root_node:
            self.logger.error("Failed to create UI tree from UIAutomator2 data")
            return ScreenDescription(activity_name, [])

        # Create visitor and traverse tree
        visitor = EnhancedTextVisitor(static_data, activity_name)
        root_node.accept(visitor)

        # Get and return screen description
        description = visitor.get_screen_description()
        self.logger.info(f"Parsed {len(description.items)} UI elements from UIAutomator2 state")

        return description

    def get_activity_name(self, state_data: Dict[str, Any]) -> str:
        """
        Extract activity name from UIAutomator2 state data.

        Args:
            state_data: Dictionary containing UIAutomator2 state

        Returns:
            Activity name

        Raises:
            ValueError: If activity name is not found
        """
        # UIAutomator2 stores the current activity differently than DroidBot
        activity = state_data.get("currentActivityName", state_data.get("activity", ""))
        if not activity:
            raise ValueError("No activity name found in UIAutomator2 state data")

        # Clean up activity name (remove package if present)
        if "/" in activity:
            activity = activity.split("/")[-1]

        return activity

    def validate_state_data(self, state_data: Dict[str, Any]) -> bool:
        """
        Validate UIAutomator2 state data.

        Args:
            state_data: Dictionary containing UIAutomator2 state

        Returns:
            True if valid, False otherwise
        """
        # Either currentActivityName or activity must be present
        has_activity = "currentActivityName" in state_data or "activity" in state_data
        has_hierarchy = "hierarchy" in state_data

        return has_activity and has_hierarchy

    def _convert_to_node_tree(self, data: Dict[str, Any]) -> Optional[Node]:
        """
        Convert UIAutomator2 hierarchy data to standard Node tree.

        Args:
            data: UIAutomator2 hierarchy data

        Returns:
            Root Node or None if invalid data
        """

        def map_properties(ui_node_data: Dict[str, Any]) -> Dict[str, Any]:
            """Map UIAutomator property names to standard names."""
            property_mapping = {
                "className": "class",
                "resourceId": "resource_id",
                "contentDescription": "content_description",
                "longClickable": "long_clickable",
                "packageName": "package",
                "password": "is_password"
            }

            # Create new dict with mapped property names
            node_data = {}
            for key, value in ui_node_data.items():
                new_key = property_mapping.get(key, key)
                node_data[new_key] = value

            # Convert bounds to standard format
            if "bounds" in node_data:
                bounds = node_data["bounds"]
                if isinstance(bounds, dict) and all(k in bounds for k in ["left", "top", "right", "bottom"]):
                    node_data["bounds"] = [
                        [bounds["left"], bounds["top"]],
                        [bounds["right"], bounds["bottom"]]
                    ]

            return node_data

        def create_node(node_data: Dict[str, Any], parent: Optional[Node] = None) -> Optional[Node]:
            """Create Node from UIAutomator data."""
            if not isinstance(node_data, dict):
                return None

            # Map properties to standard format
            mapped_data = map_properties(node_data)

            # Extract children
            children_data = node_data.pop("children", [])
            mapped_data.pop("children", None)  # Remove children from mapped data

            # Create node
            node = Node(mapped_data, [], parent)

            # Process children
            for child_data in children_data:
                child = create_node(child_data, node)
                if child:
                    node.children.append(child)

            return node

        return create_node(data)

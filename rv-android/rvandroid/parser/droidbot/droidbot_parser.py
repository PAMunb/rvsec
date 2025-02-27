import logging
from typing import Dict, Any

from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.abstract_parser import AbstractStateParser
from rvandroid.parser.visitor.base_visitor import ScreenDescription, Node
from rvandroid.parser.visitor.text_visitor import EnhancedTextVisitor


class DroidBotParser(AbstractStateParser):
    """
    Parser for DroidBot state data.
    Converts DroidBot state data into a ScreenDescription.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse(self, state_data: Dict[str, Any], static_data: StaticAnalysisData) -> ScreenDescription:
        """
        Parse DroidBot state data into a ScreenDescription.

        Args:
            state_data: Dictionary containing DroidBot state
            static_data: Static analysis data for the application

        Returns:
            ScreenDescription object
        """
        self.logger.info(f"Parsing DroidBot state for activity: {self.get_activity_name(state_data)}")

        # Clean up activity name
        activity = self.get_activity_name(state_data)

        # Update stack info if available
        if "stack" in state_data:
            stack = state_data.get("stack", [])
            new_stack = [name.replace("/", "") for name in stack]
            state_data["stack"] = new_stack

        # Create UI hierarchy tree
        if "view_tree" not in state_data:
            self.logger.error("No view_tree found in DroidBot state")
            return ScreenDescription(activity, [])

        tree = self._create_tree_from_json(state_data["view_tree"])
        if not tree:
            self.logger.error("Failed to create UI tree from view_tree data")
            return ScreenDescription(activity, [])

        # Create visitor and traverse tree
        visitor = EnhancedTextVisitor(static_data, activity)
        tree.accept(visitor)

        # Get and return screen description
        description = visitor.get_screen_description()
        self.logger.info(f"Parsed {len(description.items)} UI elements from DroidBot state")

        return description

    def get_activity_name(self, state_data: Dict[str, Any]) -> str:
        """
        Extract activity name from DroidBot state data.

        Args:
            state_data: Dictionary containing DroidBot state

        Returns:
            Activity name
        """
        activity = state_data.get("activity", "")

        # Clean up activity name
        activity = activity.replace("/", "")

        return activity

    def _create_tree_from_json(self, json_data: dict) -> Node:
        """
        Create a Node tree from JSON representation of an Android UI hierarchy.

        Args:
            json_data: JSON dictionary containing UI hierarchy data

        Returns:
            Root Node of the UI hierarchy tree
        """
        self.logger.debug("Creating UI tree from DroidBot JSON data")

        def create_node(data, parent=None):
            """Recursive function to create nodes from JSON data"""
            if not isinstance(data, dict):
                self.logger.warning(f"Invalid node data format: {data}")
                return None

            children = []
            if "children" in data and isinstance(data["children"], list):
                for child_data in data["children"]:
                    child_node = create_node(child_data, parent)
                    if child_node:
                        children.append(child_node)

            node = Node(data, children)
            node.parent = parent
            return node

        return create_node(json_data)

# rvandroid/parser/uiautomator/uiautomator_parser.py
import logging
from typing import Dict, Any, List

from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.abstract_parser import AbstractStateParser
from rvandroid.parser.droidbot.screen_visitor import ScreenDescription
from rvandroid.parser.uiautomator.uiautomator_node import UIAutomatorNode
from rvandroid.parser.visitor.text_visitor import EnhancedTextVisitor


class UIAutomator2Parser(AbstractStateParser):
    """
    Parser for UIAutomator2 state data.
    Converts UIAutomator2 XML/JSON data into a ScreenDescription.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse(self, state_data: Dict[str, Any], static_data: StaticAnalysisData) -> ScreenDescription:
        """
        Parse UIAutomator2 state data into a ScreenDescription.

        Args:
            state_data: Dictionary containing UIAutomator2 state
            static_data: Static analysis data for the application

        Returns:
            ScreenDescription object
        """
        self.logger.info("Parsing UIAutomator2 state data")

        # Extract activity name
        activity_name = self.get_activity_name(state_data)

        # Create tree from hierarchy
        ui_hierarchy = state_data.get("hierarchy", {})
        root_node = self._create_tree_from_data(ui_hierarchy)

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
        """
        # UIAutomator2 stores the current activity differently than DroidBot
        activity = state_data.get("currentActivityName", state_data.get("activity", ""))

        # Clean up activity name (remove package if present)
        if "/" in activity:
            activity = activity.split("/")[-1]

        return activity

    def _create_tree_from_data(self, data: Dict) -> UIAutomatorNode:
        """
        Create a UIAutomatorNode tree from UIAutomator2 data.

        Args:
            data: Dictionary containing UI hierarchy data

        Returns:
            Root UIAutomatorNode
        """

        def create_node(node_data, parent=None):
            if not isinstance(node_data, dict):
                return None

            children_data = node_data.pop("children", [])
            node = UIAutomatorNode(node_data, [], parent)

            for child_data in children_data:
                child = create_node(child_data, node)
                if child:
                    node.children.append(child)

            return node

        return create_node(data)
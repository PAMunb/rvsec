import logging as logging_api
from typing import List, Dict, Optional

from rvandroid.model.static import StaticAnalysisData
from rvandroid.model.widget import Widget, WidgetEventType
from rvandroid.parser.visitor.base_visitor import ScreenDescription, Node, Counter, ScreenItem, ItemAction

# from droidbot.input_event import *

# DEPRECATED:

"""
This module contains the implementation of a visitor pattern to parse Android UI elements and their associated actions.

The `ScreenVisitor` class is responsible for visiting each node in the UI hierarchy, collecting information about clickable,
scrollable, checkable, long-clickable, editable, and actionable views. It generates descriptions of these views
and their corresponding actions, which are stored in a `ScreenDescription` object.

The `Node` class represents an individual view in the UI hierarchy and provides methods to accept a visitor for traversal.
It also includes helper methods to safely retrieve dictionary values with default fallbacks.
"""


class ScreenVisitor:
    """Base visitor class for traversing UI hierarchy and collecting view information"""

    def __init__(self, static_info: StaticAnalysisData, activity: str):
        self.logging = logging_api.getLogger(__name__)
        self.static_info = static_info
        self.activity = activity
        self.window = static_info.windows.get_window(activity)
        self.counter = Counter()
        self.items: List[ScreenItem] = []
        self.window_info: Dict = {
            "total_widgets": 0,
            "matched_widgets": 0,
            "interactive_elements": 0
        }

    def find_matching_widget(self, node: Node) -> Optional[Widget]:
        """Enhanced to use multiple strategies to find matching widgets"""
        self.logging.debug(f"Finding matching widget for node: {node.data}")

        # Try by resource ID
        if node.resource_id:
            parts = node.resource_id.split("/")
            resource_id = parts[-1] if len(parts) > 1 else parts[0]

            self.logging.debug(f"Looking for widget by resource ID: {resource_id}")
            if self.window is not None:
                widget = self.window.get_widget_by_name(resource_id)
                if widget:
                    self.window_info["matched_widgets"] += 1
                    self.logging.debug(f"Widget found by ID: {widget}")
                    return widget

        # Try by text content if no widget found by ID
        if node.view_text and self.window:
            self.logging.debug(f"Looking for widget by text: {node.view_text}")
            for widget_id, widget in self.window.widgets.items():
                if widget.text == node.view_text:
                    self.window_info["matched_widgets"] += 1
                    self.logging.debug(f"Widget found by text: {widget}")
                    return widget

        # Could add more matching strategies here

        return None

    @staticmethod
    def get_possible_actions(node: Node, counter: Counter) -> List[ItemAction]:
        """Enhanced to provide more context-specific actions"""
        actions = []

        # Handle click actions
        if node.clickable:
            actions.append(ItemAction(
                counter.inc(),
                f"CLICK ({counter.get()})" + (f" on '{node.view_text}'" if node.view_text else ""),
                WidgetEventType.CLICK, False, False
            ))

        # Handle long click actions    
        if node.long_clickable:
            actions.append(ItemAction(
                counter.inc(),
                f"LONG_CLICK ({counter.get()})" + (f" on '{node.view_text}'" if node.view_text else ""),
                WidgetEventType.LONG_CLICK, False, False
            ))

        # Handle check/uncheck actions with more context
        if node.checkable:
            if node.checked:
                actions.append(ItemAction(
                    counter.inc(),
                    f"UNCHECK ({counter.get()})" + (f" '{node.view_text}'" if node.view_text else ""),
                    WidgetEventType.CLICK, False, False
                ))
            else:
                actions.append(ItemAction(
                    counter.inc(),
                    f"CHECK ({counter.get()})" + (f" '{node.view_text}'" if node.view_text else ""),
                    WidgetEventType.CLICK, False, False
                ))

        # Handle scroll actions with better description
        if node.scrollable:
            for direction in ["UP", "DOWN", "LEFT", "RIGHT"]:
                actions.append(ItemAction(
                    counter.inc(),
                    f"SCROLL {direction} {counter.get()}" +
                    (f" on '{node.view_class.split('.')[-1]}'" if node.view_class else ""),
                    WidgetEventType.SCROLL, False, False
                ))

        # Handle text input actions with better hints
        if node.editable:
            hint = ""
            if node.view_text:
                hint = f" [current: '{node.view_text}']"
            elif node.content_description:
                hint = f" [hint: '{node.content_description}']"

            actions.append(ItemAction(
                counter.inc(),
                f"SET_TEXT ({counter.get()}) {hint}",
                WidgetEventType.TEXT_CHANGE, False, False
            ))

        return actions

    def get_screen_description(self) -> ScreenDescription:
        """Returns the complete screen description based on visited items"""
        return ScreenDescription("", self.items)

    # Define visit methods for different types of nodes
    def visit_node(self, node: Node) -> None:
        pass

    def visit_leaf_node(self, leaf_node: Node) -> None:
        pass

    def visit_button(self, node: Node) -> None:
        pass

    def visit_edit_text(self, node: Node) -> None:
        pass

    def visit_text_view(self, node: Node) -> None:
        pass

    def visit_checkbox(self, node: Node) -> None:
        pass

    def visit_checked_text(self, node: Node) -> None:
        pass

    def visit_image_button(self, node: Node) -> None:
        pass

    def visit_image(self, node: Node) -> None:
        pass

    def visit_spinner(self, node: Node) -> None:
        pass

    def visit_toggle_button(self, node: Node) -> None:
        pass

    def visit_switch(self, node: Node) -> None:
        pass

    def visit_radio_button(self, node: Node) -> None:
        pass

    def visit_slider(self, node: Node) -> None:
        pass

    def visit_radio_group(self, node: Node) -> None:
        pass

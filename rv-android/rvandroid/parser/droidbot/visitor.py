from dataclasses import dataclass
from typing import List, Dict, Optional

from droidbot.input_event import *

"""
This module contains the implementation of a visitor pattern to parse Android UI elements and their associated actions.

The `Visitor` class is responsible for visiting each node in the UI hierarchy, collecting information about clickable,
scrollable, checkable, long-clickable, editable, and actionable views. It generates descriptions of these views
and their corresponding actions, which are stored in a `ScreenDescription` object.

The `Node` class represents an individual view in the UI hierarchy and provides methods to accept a visitor for traversal.
It also includes helper methods to safely retrieve dictionary values with default fallbacks.
"""


@dataclass
class ItemAction:
    """Represents an action that can be performed on a UI element"""
    id: int
    text: str
    event: InputEvent


@dataclass
class ScreenItem:
    """Represents a UI element on the screen with its description and possible actions"""
    view: dict
    base_description: str
    actions: List[ItemAction]

    @property
    def description(self) -> str:
        """Generates a human-readable description of the item and its actions"""
        actions_desc = f". Actions: {', '.join([a.text for a in self.actions])}" if self.actions else "."
        return f"{self.base_description}{actions_desc}"

    def __str__(self) -> str:
        return self.description


class ScreenDescription:
    """Represents the complete description of a screen including all UI elements and their actions"""

    def __init__(self, activity: str, items: List[ScreenItem]):
        self.activity = activity
        self.items = items
        self.events_by_id: Dict[int, InputEvent] = {
            action.id: action.event
            for item in items
            for action in item.actions
        }

    @property
    def description(self) -> str:
        """Generates a complete description of the screen and its elements"""
        view_descs = [f" - {item.description}" for item in self.items]
        state_desc = (
            "The current screen has the following UI views and corresponding actions, "
            "with action id in parentheses:\n "
        )
        return state_desc + "\n ".join(view_descs)

    def __str__(self) -> str:
        return self.description


class Counter:
    """Simple counter implementation for generating unique action IDs"""

    def __init__(self):
        self.value: int = 0

    def inc(self) -> int:
        """Increments counter and returns new value"""
        self.value += 1
        return self.value


class Node:
    """Represents a node in the UI hierarchy tree with its properties and children"""

    def __init__(self, view: dict, children: Optional[List['Node']] = None):
        self.data = view
        print("view:", view)
        self.children = children or []

        # Extract view properties
        self.clickable = self._get_property("clickable", False)
        self.scrollable = self._get_property("scrollable", False)
        self.checkable = self._get_property("checkable", False)
        self.long_clickable = self._get_property("long_clickable", False)
        self.editable = self._get_property("editable", False)
        self.checked = self._get_property("checked", False)
        self.selected = self._get_property("selected", False)

        # View identifiers
        self.content_description = self._get_property("content_description", "")
        self.view_text = self._get_property("text", "")
        self.view_class = self._get_property("class", "")
        self.resource_id = self._get_property("resource_id", "")

        # Derived properties
        self.actionable = (self.clickable or self.scrollable or self.checkable or
                           self.long_clickable or self.editable)

    def _get_property(self, key: str, default: any) -> any:
        """Safely retrieves a property from the view dictionary"""
        return self.data.get(key, default)

    def accept(self, visitor: 'Visitor') -> None:
        """Implements the visitor pattern for traversing the UI hierarchy"""
        if not self.children:
            self._handle_leaf_node(visitor)
        else:
            self._handle_container_node(visitor)

    def _handle_leaf_node(self, visitor: 'Visitor') -> None:
        """Handles visitation for leaf nodes based on their widget type"""
        widget_handlers = {
            "android.widget.Button": visitor.visit_button,
            "android.widget.EditText": visitor.visit_edit_text,
            "android.widget.TextView": visitor.visit_text_view,
            "android.widget.CheckBox": visitor.visit_checkbox,
            "android.widget.CheckedTextView": visitor.visit_checked_text,
            "android.widget.ImageButton": visitor.visit_image_button,
            "android.widget.ImageView": visitor.visit_image,
            "android.widget.ToggleButton": visitor.visit_toggle_button,
            "android.widget.Switch": visitor.visit_switch,
            "android.widget.RadioButton": visitor.visit_radio_button
        }
        handler = widget_handlers.get(self.view_class, visitor.visit_leaf_node)
        handler(self)


    def _handle_container_node(self, visitor: 'Visitor') -> None:
        """Handles visitation for container nodes"""
        if self.view_class == "android.widget.Spinner":
            visitor.visit_spinner(self)
        elif self.view_class == "android.widget.RadioGroup":
            visitor.visit_radio_group(self)
        else:
            visitor.visit_node(self)
            for child in self.children:
                child.accept(visitor)


class Visitor:
    """Base visitor class for traversing UI hierarchy and collecting view information"""

    def __init__(self):
        self.counter = Counter()
        self.items: List[ScreenItem] = []

    @staticmethod
    def get_possible_actions(node: Node, counter: Counter) -> List[ItemAction]:
        """Determines all possible actions for a given node"""
        actions = []

        # Handle click actions
        if node.clickable:
            actions.append(ItemAction(
                counter.inc(),
                "click ({})",
                TouchEvent(view=node.data)
            ))

        # Handle long click actions    
        if node.long_clickable:
            actions.append(ItemAction(
                counter.inc(),
                "long click ({})",
                LongTouchEvent(view=node.data)
            ))

        # Handle check/uncheck actions
        if node.checkable:
            actions.append(ItemAction(
                counter.inc(),
                "check ({})",
                TouchEvent(view=node.data)
            ))
        if node.checked:
            actions.append(ItemAction(
                counter.inc(),
                "uncheck ({})",
                TouchEvent(view=node.data)
            ))

        # Handle scroll actions
        if node.scrollable:
            for direction in ["UP", "DOWN", "LEFT", "RIGHT"]:
                actions.append(ItemAction(
                    counter.inc(),
                    f"scroll {direction} ({{}})",
                    ScrollEvent(view=node.data, direction=direction)
                ))

        # Handle text input actions
        if node.editable:
            actions.append(ItemAction(
                counter.inc(),
                "set text ({})",
                SetTextEvent(view=node.data, text="")
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

    def visit_radio_group(self, node: Node) -> None:
        pass

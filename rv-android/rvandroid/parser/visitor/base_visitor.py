import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
from typing import Set

from rvandroid.model.static import StaticAnalysisData
from rvandroid.model.widget import Widget, WidgetEventType


@dataclass
class ItemAction:
    """Represents an action that can be performed on a UI element"""
    id: int
    text: str
    event: WidgetEventType
    reaches_mop: bool
    directly_reaches_mop: bool


@dataclass
class ScreenItem:
    """Represents a UI element on the screen with its description and possible actions"""
    view: dict  # TODO estruturar direito ou identificar o conteudo do dict
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
        self.events_by_id: Dict[int, ItemAction] = {
            action.id: action
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

    def get(self):
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
        self.is_password = self._get_property("is_password", False)
        self.enabled = self._get_property("enabled", False)
        self.focused = self._get_property("focused", False)

        # View identifiers
        self.content_description = self._get_property("content_description", "")
        self.view_text = self._get_property("text", "")
        self.view_class = self._get_property("class", "")
        self.package = self._get_property("package", "")
        self.resource_id = self._get_property("resource_id", "")

        # Derived properties
        self.actionable = (self.clickable or self.scrollable or self.checkable or
                           self.long_clickable or self.editable)

    def _get_property(self, key: str, default: any) -> any:
        """Safely retrieves a property from the view dictionary"""
        return self.data.get(key, default)

    def accept(self, visitor: 'ScreenVisitor') -> None:
        """Implements the visitor pattern for traversing the UI hierarchy"""
        if not self.children:
            self._handle_leaf_node(visitor)
        else:
            self._handle_container_node(visitor)

    def _handle_leaf_node(self, visitor: 'ScreenVisitor') -> None:
        """Handles visitation for leaf nodes based on their widget type"""
        print("Leaf node:", self.view_class)
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

    def _handle_container_node(self, visitor: 'ScreenVisitor') -> None:
        """Handles visitation for container nodes"""
        if self.view_class == "android.widget.Spinner":
            visitor.visit_spinner(self)
        elif self.view_class == "android.widget.RadioGroup":
            visitor.visit_radio_group(self)
        else:
            visitor.visit_node(self)
            for child in self.children:
                child.accept(visitor)


class BaseScreenVisitor:

    def __init__(self, static_info: StaticAnalysisData, activity: str):
        self.logging = logging.getLogger(__name__)
        self.static_info = static_info
        self.activity = activity
        self.window = static_info.windows.get_window(activity) if static_info and static_info.windows else None
        self.counter = Counter()
        self.items: List[ScreenItem] = []
        self.visited_nodes: Set[str] = set()  # Track visited nodes to avoid duplicates
        self.window_info: Dict = {
            "total_widgets": 0,
            "matched_widgets": 0,
            "interactive_elements": 0
        }

    def get_screen_description(self) -> ScreenDescription:
        """
        Create and return a complete screen description with a BACK action added.

        Returns:
            ScreenDescription object containing all parsed items
        """
        # Add a default BACK action to the screen description
        back_action = ItemAction(
            self.counter.inc(),
            f"BACK ({self.counter.get()})",
            WidgetEventType.KEY,
            False,
            False
        )

        # Create a back button item
        back_item = ScreenItem(
            {"special": "back_button"},  # dummy data
            "System back button",
            [back_action]
        )

        self.items.append(back_item)
        self.logging.info(f"Generated screen description with {len(self.items)} items")

        return ScreenDescription(self.activity, self.items)

    def find_matching_widget(self, node_data: Dict) -> Optional[Widget]:
        """
        Find a matching widget in the static data based on various strategies.

        Args:
            node_data: Node data dictionary

        Returns:
            Widget if found, None otherwise
        """
        resource_id = node_data.get("resource_id", "")
        if not resource_id or not self.window:
            return None

        # Try by resource ID
        parts = resource_id.split("/")
        widget_id = parts[-1] if len(parts) > 1 else parts[0]

        self.logging.debug(f"Looking for widget by resource ID: {widget_id}")
        widget = self.window.get_widget_by_name(widget_id)
        if widget:
            self.window_info["matched_widgets"] += 1
            return widget

        # Try by text content
        text = node_data.get("text", "")
        if text:
            self.logging.debug(f"Looking for widget by text: {text}")
            for widget_id, widget in self.window.widgets.items():
                if widget.text == text:
                    self.window_info["matched_widgets"] += 1
                    return widget

        return None

    def is_parent_clickable(self, node: Node) -> bool:
        """
        Check if any parent of this node is clickable.

        Args:
            node: Current node

        Returns:
            True if a parent is clickable, False otherwise
        """
        parent = node.parent if hasattr(node, 'parent') else None
        while parent:
            if parent.clickable:
                return True
            parent = parent.parent if hasattr(parent, 'parent') else None
        return False

    def _check_method_reaches_mop(self, signature: str) -> bool:
        """
        Check if a method reaches MOP (Method of Protection).

        Args:
            signature: Method signature to check

        Returns:
            True if method reaches MOP, False otherwise
        """
        if self.static_info and self.static_info.classes:
            method = self.static_info.classes.methods.get(signature)
            if method:
                return method.reaches_mop
        return False

    def _check_method_directly_reaches_mop(self, signature: str) -> bool:
        """
        Check if a method directly reaches MOP.

        Args:
            signature: Method signature to check

        Returns:
            True if method directly reaches MOP, False otherwise
        """
        if self.static_info and self.static_info.classes:
            method = self.static_info.classes.methods.get(signature)
            if method:
                return method.directly_reaches_mop
        return False

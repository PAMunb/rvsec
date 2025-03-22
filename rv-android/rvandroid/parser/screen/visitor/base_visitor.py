# rvandroid/parser/screen/visitor/base_visitor.py
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Any

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.domain.widget import WidgetEventType, Widget


@dataclass
class ItemAction:
    """Represents an action that can be performed on a UI element."""
    id: int
    text: str
    event: WidgetEventType
    reaches_mop: bool = False
    directly_reaches_mop: bool = False
    target_view: Dict[str, Any] = field(default_factory=dict)
    coordinates: Optional[tuple] = None

    @property
    def action_type(self) -> str:
        """Extract the action type from the text description."""
        if self.text.startswith("CLICK"):
            return "click"
        elif self.text.startswith("LONG_CLICK"):
            return "long_click"
        elif self.text.startswith("SCROLL"):
            # Extract direction if present
            if "UP" in self.text:
                return "scroll_up"
            elif "DOWN" in self.text:
                return "scroll_down"
            elif "LEFT" in self.text:
                return "scroll_left"
            elif "RIGHT" in self.text:
                return "scroll_right"
            return "scroll"
        elif self.text.startswith("SET_TEXT"):
            return "set_text"
        elif self.text.startswith("CHECK") or self.text.startswith("UNCHECK"):
            return "click"  # Checkbox actions are clicks
        elif self.text.startswith("BACK"):
            return "key_event"
        return "unknown"

    def to_droidbot_action(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Convert this action to a format suitable for droidbot.

        Args:
            params: Optional parameters passed from LLM

        Returns:
            Action dictionary for droidbot
        """
        # Get both target identifier and coordinates
        target = self._get_target()
        coords = self._get_coordinates()

        action_dict = {
            "action_type": self.action_type,
            "target": target,
            "coordinates": coords,
            "params": params or {}
        }

        # Handle special cases
        if self.action_type == "key_event":
            action_dict["params"]["name"] = "BACK"

        return action_dict

    def _get_target(self) -> str:
        """Get target identifier from the associated view."""
        if not self.target_view:
            return ""

        # Try resource_id first
        if "resource_id" in self.target_view:
            return self.target_view["resource_id"]

        # Fall back to coordinates if bounds are available
        if "bounds" in self.target_view:
            bounds = self.target_view["bounds"]
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                return f"{x} {y}"

        # Use stored coordinates if available
        if self.coordinates:
            x, y = self.coordinates
            return f"{x} {y}"

        return ""

    def _get_coordinates(self) -> Optional[tuple]:
        """
        Get the coordinates for this action. Will use stored coordinates first,
        then try to extract from bounds.

        Returns:
            Tuple of (x, y) coordinates or None if not available
        """
        # Use stored coordinates if available
        if self.coordinates:
            return self.coordinates

        # Extract from bounds if available
        if self.target_view and "bounds" in self.target_view:
            bounds = self.target_view["bounds"]
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                return (x, y)

        return None


@dataclass
class ScreenItem:
    """Represents a UI element on the screen with its description and possible actions."""
    view: Dict[str, Any]  # Raw view data
    base_description: str
    actions: List[ItemAction] = field(default_factory=list)

    @property
    def description(self) -> str:
        """Generates a human-readable description of the item and its actions."""
        actions_desc = f". Actions: {', '.join([a.text for a in self.actions])}" if self.actions else "."
        return f"{self.base_description}{actions_desc}"

    def __str__(self) -> str:
        return self.description


class ScreenDescription:
    """Represents the complete description of a screen including all UI elements and their actions."""

    def __init__(self, activity: str, items: List[ScreenItem]):
        """
        Initialize screen description.

        Args:
            activity: Current activity name
            items: List of UI elements with actions
        """
        self.activity = activity
        self.items = items
        self.events_by_id: Dict[int, ItemAction] = {
            action.id: action
            for item in items
            for action in item.actions
        }

    @property
    def description(self) -> str:
        """Generates a complete description of the screen and its elements."""
        view_descs = [f" - {item.description}" for item in self.items]
        state_desc = (
            "The current screen has the following UI views and corresponding actions, "
            "with action id in parentheses:\n "
        )
        return state_desc + "\n ".join(view_descs)

    def __str__(self) -> str:
        return self.description


class Counter:
    """Simple counter implementation for generating unique action IDs."""

    def __init__(self, start_value: int = 0):
        """
        Initialize counter.

        Args:
            start_value: Initial counter value
        """
        self.value: int = start_value

    def inc(self) -> int:
        """
        Increments counter and returns new value.

        Returns:
            New counter value
        """
        self.value += 1
        return self.value

    def get(self) -> int:
        """
        Gets current counter value without incrementing.

        Returns:
            Current counter value
        """
        return self.value


class UiElementType(Enum):
    """Enumeration of UI element types for more generic processing."""
    CONTAINER = "container"
    BUTTON = "button"
    TEXT_FIELD = "text_field"
    TEXT_VIEW = "text_view"
    CHECKBOX = "checkbox"
    TOGGLE = "toggle"
    RADIO_BUTTON = "radio_button"
    SPINNER = "spinner"
    SLIDER = "slider"
    IMAGE = "image"
    UNKNOWN = "unknown"

    @staticmethod
    def from_class_name(class_name: str) -> 'UiElementType':
        """Maps Android class names to element types."""
        mapping = {
            "android.widget.Button": UiElementType.BUTTON,
            "android.widget.ImageButton": UiElementType.BUTTON,
            "android.widget.EditText": UiElementType.TEXT_FIELD,
            "android.widget.TextView": UiElementType.TEXT_VIEW,
            "android.widget.CheckBox": UiElementType.CHECKBOX,
            "android.widget.CheckedTextView": UiElementType.CHECKBOX,
            "android.widget.ToggleButton": UiElementType.TOGGLE,
            "android.widget.Switch": UiElementType.TOGGLE,
            "android.widget.RadioButton": UiElementType.RADIO_BUTTON,
            "android.widget.Spinner": UiElementType.SPINNER,
            "android.widget.SeekBar": UiElementType.SLIDER,
            "android.widget.ImageView": UiElementType.IMAGE,
        }
        return mapping.get(class_name, UiElementType.UNKNOWN)


class Node:
    """
    Represents a node in the UI hierarchy tree with its properties and children.
    Enhanced implementation with better type safety and property access.
    """

    def __init__(
            self,
            view: Dict[str, Any],
            children: Optional[List['Node']] = None,
            parent: Optional['Node'] = None
    ):
        """
        Initialize a Node.

        Args:
            view: Dictionary of view properties
            children: List of child nodes (optional)
            parent: Parent node (optional)
        """
        self.data = view
        self.children = children or []
        self.parent = parent

        # Extract common view properties
        self.clickable = self._get_property("clickable", False)
        self.scrollable = self._get_property("scrollable", False)
        self.checkable = self._get_property("checkable", False)
        self.long_clickable = self._get_property("long_clickable", False)
        self.editable = self._get_property("editable", False)
        self.checked = self._get_property("checked", False)
        self.selected = self._get_property("selected", False)
        self.is_password = self._get_property("is_password", False)
        self.enabled = self._get_property("enabled", True)
        self.focused = self._get_property("focused", False)

        # View identifiers
        self.content_description = self._get_property("content_description", "")
        self.view_text = self._get_property("text", "")
        self.view_class = self._get_property("class", "")
        self.package = self._get_property("package", "")
        self.resource_id = self._get_property("resource_id", "")
        self.hint = self._get_property("hint", "")

        # Bounds are represented as [[left, top], [right, bottom]]
        self.bounds = self._get_property("bounds", [[0, 0], [0, 0]])

        # Progress values for sliders/seekbars
        self.progress = self._get_property("progress", 0)
        self.max = self._get_property("max", 100)

        # Derived properties
        self.actionable = (self.clickable or self.scrollable or self.checkable or
                           self.long_clickable or self.editable)

        # Element type
        self.element_type = UiElementType.from_class_name(self.view_class)

    def _get_property(self, key: str, default: Any) -> Any:
        """
        Safely retrieves a property from the view dictionary.

        Args:
            key: Property key
            default: Default value if key doesn't exist

        Returns:
            Property value or default
        """
        return self.data.get(key, default)

    def accept(self, visitor: 'BaseScreenVisitor') -> None:
        """
        Implements the visitor pattern for traversing the UI hierarchy.

        Args:
            visitor: Visitor implementation
        """
        visitor.visit(self)
        for child in self.children:
            child.accept(visitor)

    def find_children_by_class(self, class_name: str) -> List['Node']:
        """
        Find all child nodes with a specific class name.

        Args:
            class_name: Class name to search for

        Returns:
            List of matching nodes
        """
        result = []

        for child in self.children:
            if child.view_class == class_name:
                result.append(child)
            # Recursively search in child's children
            result.extend(child.find_children_by_class(class_name))

        return result

    def get_center_coordinates(self) -> tuple:
        """
        Get the center coordinates of this node's bounding box.

        Returns:
            Tuple of (x, y) coordinates
        """
        if not isinstance(self.bounds, list) or len(self.bounds) != 2:
            return (0, 0)

        try:
            x1, y1 = self.bounds[0]
            x2, y2 = self.bounds[1]
            return ((x1 + x2) // 2, (y1 + y2) // 2)
        except (TypeError, IndexError):
            return (0, 0)

    def get_unique_id(self) -> str:
        """
        Generate a unique identifier for this node based on its properties.

        Returns:
            String identifier
        """
        bounds_str = str(self.bounds) if hasattr(self, 'bounds') else ''
        return f"{self.view_class}_{self.resource_id}_{bounds_str}"

    def __str__(self) -> str:
        """String representation of the node."""
        return f"{self.view_class} - {self.resource_id or self.view_text or 'unnamed'}"


class ElementHandler:
    """Handler for a specific type of UI element."""

    def __init__(self, element_type: UiElementType):
        self.element_type = element_type

    def can_handle(self, node: Node) -> bool:
        """Check if this handler can process the given node."""
        return node.element_type == self.element_type

    def handle(self, node: Node, visitor: 'BaseScreenVisitor') -> Optional[ScreenItem]:
        """Process a node and generate a ScreenItem."""
        return None


class BaseScreenVisitor(ABC):
    """
    Simplified abstract base visitor implementation for processing Android UI elements.
    Uses a more generic approach with registered handlers for different element types.
    """

    def __init__(self, static_info: Optional[StaticAnalysisData], activity: str):
        """
        Initialize the visitor.

        Args:
            static_info: Static analysis data (optional)
            activity: Current activity name
        """
        self.logger = logging.getLogger(__name__)
        self.static_info = static_info
        self.activity = activity
        self.window = None

        # Initialize window info if static info is available
        if static_info and static_info.windows:
            self.window = static_info.windows.get_window(activity)

        self.counter = Counter()
        self.items: List[ScreenItem] = []
        self.visited_nodes: Set[str] = set()  # Track visited nodes to avoid duplicates
        self.window_info: Dict = {
            "total_widgets": 0,
            "matched_widgets": 0,
            "interactive_elements": 0
        }

        # Initialize element handlers
        self.handlers: Dict[UiElementType, ElementHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default element handlers."""
        pass

    def register_handler(self, handler: ElementHandler) -> None:
        """Register a custom element handler."""
        self.handlers[handler.element_type] = handler

    @abstractmethod
    def get_screen_description(self) -> ScreenDescription:
        """
        Create and return a complete screen description.

        Returns:
            ScreenDescription object containing all parsed items
        """
        pass

    def visit(self, node: Node) -> None:
        """
        Visit a node in the UI hierarchy - simplified generic method.
        Finds the appropriate handler for the node type and processes it.

        Args:
            node: Node to process
        """
        # Skip already visited nodes
        node_id = node.get_unique_id()
        if node_id in self.visited_nodes:
            return

        # Find handler for this element type
        handler = self.handlers.get(node.element_type)

        # Use generic processing if no specific handler
        if handler and handler.can_handle(node):
            item = handler.handle(node, self)
            if item:
                self.items.append(item)
                self.visited_nodes.add(node_id)
                self.window_info["interactive_elements"] += 1
        elif node.actionable:
            # Generic handling for actionable elements
            self._process_actionable_node(node)

    def _process_actionable_node(self, node: Node) -> None:
        """Process a generic actionable node."""
        actions = self.get_possible_actions(node, self.counter)
        if actions:
            description = f"{node.element_type.value.capitalize()} {node.view_class}"
            item = ScreenItem(node.data, description, actions)
            self.items.append(item)
            self.visited_nodes.add(node.get_unique_id())
            self.window_info["interactive_elements"] += 1

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

        self.logger.debug(f"Looking for widget by resource ID: {widget_id}")
        widget = self.window.get_widget_by_name(widget_id)
        if widget:
            self.window_info["matched_widgets"] += 1
            return widget

        # Try by text content
        text = node_data.get("text", "")
        if text:
            self.logger.debug(f"Looking for widget by text: {text}")
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
        parent = node.parent
        while parent:
            if parent.clickable:
                return True
            parent = parent.parent
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

    def get_possible_actions(self, node: Node, counter: Counter, inherit_click: bool = False,
                             prioritize_check: bool = False) -> List[ItemAction]:
        """
        Get possible actions for a node.

        Args:
            node: The node to get actions for
            counter: Counter for generating unique IDs
            inherit_click: Whether to add click action from parent
            prioritize_check: Whether to prioritize check/uncheck over click

        Returns:
            List of possible actions
        """
        actions = []
        node_data = node.data
        coordinates = node.get_center_coordinates()

        # Handle check/uncheck actions with priority if needed
        if prioritize_check and node.checkable:
            if node.checked:
                action = ItemAction(
                    id=counter.inc(),
                    text=f"UNCHECK ({counter.get()})",
                    event=WidgetEventType.CLICK,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view=node_data,
                    coordinates=coordinates
                )
                # Update security information
                self._update_action_security_info(action, node)
                actions.append(action)
            else:
                action = ItemAction(
                    id=counter.inc(),
                    text=f"CHECK ({counter.get()})",
                    event=WidgetEventType.CLICK,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view=node_data,
                    coordinates=coordinates
                )
                # Update security information
                self._update_action_security_info(action, node)
                actions.append(action)
            return actions

        # Handle click actions
        if node.clickable or inherit_click:
            actions.append(ItemAction(
                id=counter.inc(),
                text=f"CLICK ({counter.get()})",
                event=WidgetEventType.CLICK,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view=node_data,
                coordinates=coordinates
            ))

        # Handle long click actions
        if node.long_clickable:
            actions.append(ItemAction(
                id=counter.inc(),
                text=f"LONG_CLICK ({counter.get()})",
                event=WidgetEventType.LONG_CLICK,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view=node_data,
                coordinates=coordinates
            ))

        # Handle scroll actions
        if node.scrollable:
            for direction in ["UP", "DOWN", "LEFT", "RIGHT"]:
                actions.append(ItemAction(
                    id=counter.inc(),
                    text=f"SCROLL {direction} ({counter.get()})",
                    event=WidgetEventType.SCROLL,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view=node_data,
                    coordinates=coordinates
                ))

        # Handle text input actions
        if node.editable:
            actions.append(ItemAction(
                id=counter.inc(),
                text=f"SET_TEXT ({counter.get()})",
                event=WidgetEventType.TEXT_CHANGE,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view=node_data,
                coordinates=coordinates
            ))

        # Update security info for all actions
        for action in actions:
            self._update_action_security_info(action, node)

        return actions

    def _update_action_security_info(self, action: ItemAction, node: Node) -> None:
        """
        Update an action with security information from static analysis.

        Args:
            action: The action to update
            node: The node associated with the action
        """
        widget = self.find_matching_widget(node.data)
        if not widget:
            return

        # Find matching event type
        for event in widget.events:
            if event.type == action.event:
                # Check if method reaches or directly reaches MOP
                action.reaches_mop = self._check_method_reaches_mop(event.signature)
                action.directly_reaches_mop = self._check_method_directly_reaches_mop(event.signature)
                if action.reaches_mop or action.directly_reaches_mop:
                    self.logger.debug(
                        f"Action {action.id} security info updated: reaches_mop={action.reaches_mop}, directly_reaches_mop={action.directly_reaches_mop}")
                return

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Any


class ViewProperty(Enum):
    """Enumeration of common view properties for consistency."""
    CLICKABLE = "clickable"
    SCROLLABLE = "scrollable"
    CHECKABLE = "checkable"
    LONG_CLICKABLE = "long_clickable"
    EDITABLE = "editable"
    CHECKED = "checked"
    SELECTED = "selected"
    FOCUSED = "focused"
    PASSWORD = "is_password"
    ENABLED = "enabled"

    TEXT = "text"
    CONTENT_DESCRIPTION = "content_description"
    CLASS = "class"
    PACKAGE = "package"
    RESOURCE_ID = "resource_id"
    BOUNDS = "bounds"

    PROGRESS = "progress"
    MAX = "max"


@dataclass
class ItemAction:
    """Represents an action that can be performed on a UI element."""
    id: int
    text: str
    event: 'WidgetEventType'  # Forward reference
    reaches_mop: bool = False
    directly_reaches_mop: bool = False

    # Additional properties to support droidbot action creation
    target_view: Dict[str, Any] = field(default_factory=dict)

    # Store the coordinates explicitly
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
        elif self.text.startswith("CHECK"):
            return "click"  # Checkbox check is actually a click
        elif self.text.startswith("UNCHECK"):
            return "click"  # Checkbox uncheck is also a click
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
            "coordinates": coords,  # Add coordinates explicitly
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


from rvandroid.model.widget import WidgetEventType, Widget
from rvandroid.model.static import StaticAnalysisData


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
        self.clickable = self._get_property(ViewProperty.CLICKABLE.value, False)
        self.scrollable = self._get_property(ViewProperty.SCROLLABLE.value, False)
        self.checkable = self._get_property(ViewProperty.CHECKABLE.value, False)
        self.long_clickable = self._get_property(ViewProperty.LONG_CLICKABLE.value, False)
        self.editable = self._get_property(ViewProperty.EDITABLE.value, False)
        self.checked = self._get_property(ViewProperty.CHECKED.value, False)
        self.selected = self._get_property(ViewProperty.SELECTED.value, False)
        self.is_password = self._get_property(ViewProperty.PASSWORD.value, False)
        self.enabled = self._get_property(ViewProperty.ENABLED.value, True)
        self.focused = self._get_property(ViewProperty.FOCUSED.value, False)

        # View identifiers
        self.content_description = self._get_property(ViewProperty.CONTENT_DESCRIPTION.value, "")
        self.view_text = self._get_property(ViewProperty.TEXT.value, "")
        self.view_class = self._get_property(ViewProperty.CLASS.value, "")
        self.package = self._get_property(ViewProperty.PACKAGE.value, "")
        self.resource_id = self._get_property(ViewProperty.RESOURCE_ID.value, "")

        # Bounds are represented as [[left, top], [right, bottom]]
        self.bounds = self._get_property(ViewProperty.BOUNDS.value, [[0, 0], [0, 0]])

        # Progress values for sliders/seekbars
        self.progress = self._get_property(ViewProperty.PROGRESS.value, 0)
        self.max = self._get_property(ViewProperty.MAX.value, 100)

        # Derived properties
        self.actionable = (self.clickable or self.scrollable or self.checkable or
                           self.long_clickable or self.editable)

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
        if not self.children:
            self._handle_leaf_node(visitor)
        else:
            self._handle_container_node(visitor)

    def _handle_leaf_node(self, visitor: 'BaseScreenVisitor') -> None:
        """
        Handles visitation for leaf nodes based on their widget type.

        Args:
            visitor: Visitor implementation
        """
        # Map of widget classes to visitor methods
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
            "android.widget.RadioButton": visitor.visit_radio_button,
            "android.widget.SeekBar": visitor.visit_slider
        }

        # Call specific handler if available, otherwise use generic handler
        handler = widget_handlers.get(self.view_class, visitor.visit_leaf_node)
        handler(self)

    def _handle_container_node(self, visitor: 'BaseScreenVisitor') -> None:
        """
        Handles visitation for container nodes.

        Args:
            visitor: Visitor implementation
        """
        if self.view_class == "android.widget.Spinner":
            visitor.visit_spinner(self)
        elif self.view_class == "android.widget.RadioGroup":
            visitor.visit_radio_group(self)
        else:
            # Generic container handling
            visitor.visit_node(self)
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


class BaseScreenVisitor:
    """
    Base visitor implementation for processing Android UI elements.
    Implements the visitor pattern to traverse the UI hierarchy and create descriptions.
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
        self.logger.info(f"Generated screen description with {len(self.items)} items")

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

    # Default implementations for visit methods that should be overridden by subclasses

    def visit_node(self, node: Node) -> None:
        """Default implementation for visiting a container node."""
        pass

    def visit_leaf_node(self, node: Node) -> None:
        """Default implementation for visiting a leaf node."""
        pass

    def visit_button(self, node: Node) -> None:
        """Default implementation for visiting a button."""
        self.visit_leaf_node(node)

    def visit_edit_text(self, node: Node) -> None:
        """Default implementation for visiting an edit text field."""
        self.visit_leaf_node(node)

    def visit_text_view(self, node: Node) -> None:
        """Default implementation for visiting a text view."""
        self.visit_leaf_node(node)

    def visit_checkbox(self, node: Node) -> None:
        """Default implementation for visiting a checkbox."""
        self.visit_leaf_node(node)

    def visit_checked_text(self, node: Node) -> None:
        """Default implementation for visiting a checked text view."""
        self.visit_leaf_node(node)

    def visit_image_button(self, node: Node) -> None:
        """Default implementation for visiting an image button."""
        self.visit_leaf_node(node)

    def visit_image(self, node: Node) -> None:
        """Default implementation for visiting an image."""
        self.visit_leaf_node(node)

    def visit_toggle_button(self, node: Node) -> None:
        """Default implementation for visiting a toggle button."""
        self.visit_leaf_node(node)

    def visit_switch(self, node: Node) -> None:
        """Default implementation for visiting a switch."""
        self.visit_leaf_node(node)

    def visit_radio_button(self, node: Node) -> None:
        """Default implementation for visiting a radio button."""
        self.visit_leaf_node(node)

    def visit_spinner(self, node: Node) -> None:
        """Default implementation for visiting a spinner."""
        self.visit_node(node)

    def visit_radio_group(self, node: Node) -> None:
        """Default implementation for visiting a radio group."""
        self.visit_node(node)

    def visit_slider(self, node: Node) -> None:
        """Default implementation for visiting a slider."""
        self.visit_leaf_node(node)

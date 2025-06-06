from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List

from rv_android_core.domain.widget import WidgetEventType


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
                return x, y

        return None


@dataclass
class ScreenItem:
    """Represents a UI element on the screen with its description and possible actions."""
    view: Dict[str, Any]  # Raw view data
    base_description: str
    actions: List[ItemAction] = field(default_factory=list)
    complement: Dict[str, Any] = field(default_factory=dict)

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

        # Add a standard BACK action if needed
        self._add_standard_back_action()

        # Update the events dictionary
        self.events_by_id: Dict[int, ItemAction] = {
            action.id: action
            for item in items
            for action in item.actions
        }

    def _add_standard_back_action(self):
        """
        Add a standard BACK action to the screen if one doesn't already exist.
        This ensures there's always a way to navigate back regardless of the UI state.
        """
        # Find the maximum action ID to ensure uniqueness
        max_id = 0
        for item in self.items:
            for action in item.actions:
                max_id = max(max_id, action.id)

        # Check if there's already a BACK action
        has_back_action = False
        for item in self.items:
            for action in item.actions:
                if "BACK" in action.text:
                    has_back_action = True
                    break
            if has_back_action:
                break

        # If no BACK action exists, create one
        if not has_back_action:
            # Create a virtual view for the back action
            back_view = {
                "content_description": "Back",
                "class": "BackAction",
                "resource_id": "standard_back_action"
            }

            # Create action for the back button
            back_action = ItemAction(
                id=max_id + 1,
                text=f"BACK ({max_id + 1})",
                event=WidgetEventType.KEY,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view=back_view,
                coordinates=None
            )

            # Create item for the back action
            back_item = ScreenItem(
                view=back_view,
                base_description="Standard back action",
                actions=[back_action]
            )

            # Add to items list
            self.items.append(back_item)

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

    # def accept(self, visitor: 'AbstractScreenVisitor') -> None:
    #     """
    #     Implements the visitor pattern for traversing the UI hierarchy.
    #
    #     Args:
    #         visitor: Visitor implementation
    #     """
    #     visitor.visit(self)
    #     for child in self.children:
    #         child.accept(visitor)
    def accept(self, visitor):
        """
        Implements the visitor pattern for traversing the UI hierarchy.

        Args:
            visitor: Visitor implementation
        """
        if not self.children:
            self._handle_leaf_node(visitor)
        else:
            self._handle_container_node(visitor)

    def _handle_leaf_node(self, visitor):
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
        if handler:
            handler(self)
        else:
            visitor.visit_leaf_node(self)

    def _handle_container_node(self, visitor):
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
            return 0, 0

        try:
            x1, y1 = self.bounds[0]
            x2, y2 = self.bounds[1]
            return (x1 + x2) // 2, (y1 + y2) // 2
        except (TypeError, IndexError):
            return 0, 0

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

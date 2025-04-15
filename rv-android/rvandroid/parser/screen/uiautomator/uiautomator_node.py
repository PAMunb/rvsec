# rvandroid/parser/uiautomator/uiautomator_node.py
from typing import List, Dict, Optional, Any

from rvandroid.parser.screen.visitor.base_visitor import ViewProperty


class UIAutomatorNode:
    """
    Represents a node in the UI hierarchy from UIAutomator2.
    Provides similar interface to the standard Node class.
    """

    def __init__(self, data: Dict[str, Any], children: Optional[List['UIAutomatorNode']] = None,
                 parent: Optional['UIAutomatorNode'] = None):
        """
        Initialize a UIAutomatorNode.

        Args:
            data: Dictionary containing node properties
            children: List of child nodes (optional)
            parent: Parent node (optional)
        """
        self.data = data
        self.children = children or []
        self.parent = parent

        # Extract common properties
        self.clickable = self._get_property("clickable", False)
        self.scrollable = self._get_property("scrollable", False)
        self.checkable = self._get_property("checkable", False)
        self.long_clickable = self._get_property("longClickable", False)
        self.editable = self._get_property("editable", False)
        self.checked = self._get_property("checked", False)
        self.selected = self._get_property("selected", False)
        self.focused = self._get_property("focused", False)

        # Extract view identifiers
        self.content_description = self._get_property("contentDescription", "")
        self.view_text = self._get_property("text", "")
        self.view_class = self._get_property("className", "")
        self.package = self._get_property("packageName", "")
        self.resource_id = self._get_property("resourceId", "")

        # Progress values for sliders
        self.progress = self._get_property("progress", 0)
        self.max = self._get_property("max", 100)

        # Bounds (convert to standard format)
        bounds = self._get_property("bounds", {"left": 0, "top": 0, "right": 0, "bottom": 0})
        self.bounds = [[bounds["left"], bounds["top"]], [bounds["right"], bounds["bottom"]]]

        # Password field
        self.is_password = self._get_property("password", False)

        # Derived properties
        self.actionable = (self.clickable or self.scrollable or self.checkable or
                           self.long_clickable or self.editable)

    def _get_property(self, key: str, default: Any) -> Any:
        """Safely retrieves a property from the view dictionary"""
        return self.data.get(key, default)

    def get_standard_property_map(self) -> Dict[str, Any]:
        # TODO: esta em uso?
        """
        Get properties mapped to standard format used by Node class.

        Returns:
            Dictionary with standardized property names
        """
        # Map UIAutomator property names to standard names
        property_mapping = {
            "className": ViewProperty.CLASS.value,
            "resourceId": ViewProperty.RESOURCE_ID.value,
            "contentDescription": ViewProperty.CONTENT_DESCRIPTION.value,
            "text": ViewProperty.TEXT.value,
            "packageName": ViewProperty.PACKAGE.value,
            "bounds": ViewProperty.BOUNDS.value,
            "clickable": ViewProperty.CLICKABLE.value,
            "scrollable": ViewProperty.SCROLLABLE.value,
            "longClickable": ViewProperty.LONG_CLICKABLE.value,
            "checkable": ViewProperty.CHECKABLE.value,
            "password": ViewProperty.PASSWORD.value,
            "enabled": ViewProperty.ENABLED.value,
            "focused": ViewProperty.FOCUSED.value,
            "selected": ViewProperty.SELECTED.value,
            "checked": ViewProperty.CHECKED.value,
            "progress": ViewProperty.PROGRESS.value,
            "max": ViewProperty.MAX.value
        }

        # Create standard property dictionary
        standard_props = {}
        for uia_prop, std_prop in property_mapping.items():
            if uia_prop in self.data:
                standard_props[std_prop] = self.data[uia_prop]

        # Convert bounds to standard format
        if "bounds" in self.data:
            bounds = self.data["bounds"]
            if isinstance(bounds, dict) and all(k in bounds for k in ["left", "top", "right", "bottom"]):
                standard_props[ViewProperty.BOUNDS.value] = [
                    [bounds["left"], bounds["top"]],
                    [bounds["right"], bounds["bottom"]]
                ]

        return standard_props

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
        handler(self)

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

    def find_children_by_class(self, class_name: str) -> List['UIAutomatorNode']:
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

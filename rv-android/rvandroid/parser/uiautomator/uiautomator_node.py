# rvandroid/parser/uiautomator/uiautomator_node.py
from typing import List, Dict, Optional


class UIAutomatorNode:
    """
    Represents a node in the UI hierarchy from UIAutomator2.
    Provides similar interface to the DroidBot Node class.
    """

    def __init__(self, data: Dict, children: Optional[List['UIAutomatorNode']] = None, parent=None):
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

        # Progress for sliders
        self.progress = self._get_property("progress", 0)
        self.max = self._get_property("max", 100)

        # Bounds
        bounds = self._get_property("bounds", {"left": 0, "top": 0, "right": 0, "bottom": 0})
        self.bounds = [[bounds["left"], bounds["top"]], [bounds["right"], bounds["bottom"]]]

        # Password field
        self.is_password = self._get_property("password", False)

        # Derived properties
        self.actionable = (self.clickable or self.scrollable or self.checkable or
                           self.long_clickable or self.editable)

    def _get_property(self, key: str, default: any) -> any:
        """Safely retrieves a property from the view dictionary"""
        return self.data.get(key, default)

    def accept(self, visitor):
        """Implements the visitor pattern for traversing the UI hierarchy"""
        if not self.children:
            self._handle_leaf_node(visitor)
        else:
            self._handle_container_node(visitor)

    def _handle_leaf_node(self, visitor):
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
            "android.widget.RadioButton": visitor.visit_radio_button,
            "android.widget.SeekBar": visitor.visit_slider
        }
        handler = widget_handlers.get(self.view_class, visitor.visit_leaf_node)
        handler(self)

    def _handle_container_node(self, visitor):
        """Handles visitation for container nodes"""
        if self.view_class == "android.widget.Spinner":
            visitor.visit_spinner(self)
        elif self.view_class == "android.widget.RadioGroup":
            visitor.visit_radio_group(self)
        else:
            visitor.visit_node(self)
            for child in self.children:
                child.accept(visitor)

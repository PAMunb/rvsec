# rvandroid/parser/screen/visitor/element_handlers.py
"""
Element handlers for different types of UI elements.
This module implements the element handler pattern for processing different UI element types.
"""

from typing import Optional

from rvandroid.domain.widget import WidgetEventType
from rvandroid.parser.screen.visitor.abstract_visitor import (
    ElementHandler, AbstractScreenVisitor
)
from rvandroid.parser.screen.visitor.model import ScreenItem, UiElementType, Node


class ButtonHandler(ElementHandler):
    """Handler for button elements."""

    def __init__(self):
        super().__init__(UiElementType.BUTTON)

    def handle(self, node: Node, visitor: AbstractScreenVisitor) -> Optional[ScreenItem]:
        """Process a button node."""
        actions = visitor.get_possible_actions(node, visitor.counter)
        if not actions:
            return None

        # Add button-specific description
        text = f"Button {self._with_text(node)}"
        item = ScreenItem(node.data, text, actions)
        return item

    def _with_text(self, node: Node) -> str:
        """Format text description for node."""
        return f"with text '{node.view_text}'" if node.view_text else "with no text"


class TextFieldHandler(ElementHandler):
    """Handler for text field elements."""

    def __init__(self):
        super().__init__(UiElementType.TEXT_FIELD)

    def handle(self, node: Node, visitor: AbstractScreenVisitor) -> Optional[ScreenItem]:
        """Process a text field node."""
        actions = visitor.get_possible_actions(node, visitor.counter)
        if not actions:
            return None

        # Determine field type
        field_type = "password field" if node.is_password else "text field"

        # Add field-specific description
        description = f"{field_type.capitalize()} {self._with_hint(node)}"
        item = ScreenItem(node.data, description, actions)
        return item

    def _with_hint(self, node: Node) -> str:
        """Format hint description for node."""
        if node.hint:
            return f"with hint '{node.hint}'"
        elif node.view_text:
            return f"with text '{node.view_text}'"
        return "with no hint"


class CheckboxHandler(ElementHandler):
    """Handler for checkbox elements."""

    def __init__(self):
        super().__init__(UiElementType.CHECKBOX)

    def handle(self, node: Node, visitor: AbstractScreenVisitor) -> Optional[ScreenItem]:
        """Process a checkbox node."""
        actions = visitor.get_possible_actions(node, visitor.counter, prioritize_check=True)
        if not actions:
            return None

        # Add checkbox-specific description
        state = "checked" if node.checked else "unchecked"
        description = f"Checkbox ({state}) {self._with_text(node)}"
        item = ScreenItem(node.data, description, actions)
        return item

    def _with_text(self, node: Node) -> str:
        """Format text description for node."""
        return f"with text '{node.view_text}'" if node.view_text else "with no text"


class SpinnerHandler(ElementHandler):
    """Handler for spinner/dropdown elements."""

    def __init__(self):
        super().__init__(UiElementType.SPINNER)

    def handle(self, node: Node, visitor: AbstractScreenVisitor) -> Optional[ScreenItem]:
        """Process a spinner node."""
        # For spinners, we need custom actions
        actions = []

        # Add click action
        if node.clickable:
            actions.append(visitor._create_action(
                visitor.counter,
                f"CLICK ({visitor.counter.get()})",
                WidgetEventType.CLICK,
                node.data,
                node.get_center_coordinates()
            ))

        # Add scroll actions for selection
        if node.scrollable:
            for direction in ["UP", "DOWN"]:
                actions.append(visitor._create_action(
                    visitor.counter,
                    f"SCROLL {direction} ({visitor.counter.get()})",
                    WidgetEventType.SCROLL,
                    node.data,
                    node.get_center_coordinates()
                ))

        if not actions:
            return None

        # Try to get options from static data
        widget = visitor.find_matching_widget(node.data)
        options_text = ""
        if widget and hasattr(widget, 'entries') and widget.entries:
            options = ", ".join(widget.entries[:3])
            if len(widget.entries) > 3:
                options += ", ..."
            options_text = f" with options: {options}"

        description = f"Dropdown spinner{options_text}"
        item = ScreenItem(node.data, description, actions)
        return item

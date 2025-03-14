# rvandroid/parser/screen/visitor/generic_visitor.py
"""
Generic visitor implementation for handling UI elements.
This module implements a generic visitor that uses element handlers.
"""

from typing import Optional, Dict, List

from rvandroid.model.static import StaticAnalysisData
from rvandroid.model.widget import WidgetEventType
from rvandroid.parser.screen.visitor.base_visitor import (
    BaseScreenVisitor, ScreenItem, ScreenDescription, Node,
    UiElementType, ElementHandler, ItemAction
)
from rvandroid.parser.screen.visitor.element_handlers import (
    ButtonHandler, TextFieldHandler, CheckboxHandler, SpinnerHandler
)


class GenericScreenVisitor(BaseScreenVisitor):
    """
    Generic visitor implementation that uses element handlers to process UI elements.
    This visitor provides a flexible and extensible way to handle different element types.
    """

    def __init__(self, static_info: Optional[StaticAnalysisData], activity: str):
        """Initialize visitor with static info and activity."""
        super().__init__(static_info, activity)
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register the default element handlers."""
        self.register_handler(ButtonHandler())
        self.register_handler(TextFieldHandler())
        self.register_handler(CheckboxHandler())
        self.register_handler(SpinnerHandler())
        # Additional handlers can be registered here or by client code

    def get_screen_description(self) -> ScreenDescription:
        """
        Create and return a screen description with a BACK action added.

        Returns:
            ScreenDescription with all parsed items
        """
        # Add a default BACK action
        back_action = self._create_action(
            self.counter,
            f"BACK ({self.counter.get()})",
            WidgetEventType.KEY,
            {"special": "back_button"},
            None
        )

        back_item = ScreenItem(
            {"special": "back_button"},
            "System back button",
            [back_action]
        )

        self.items.append(back_item)
        self.logger.info(f"Generated screen description with {len(self.items)} items")

        return ScreenDescription(self.activity, self.items)

    def _create_action(self, counter, text: str, event_type: WidgetEventType,
                       view_data: Dict, coordinates) -> ItemAction:
        """Create an action with proper ID and properties."""
        action = ItemAction(
            id=counter.inc(),
            text=text,
            event=event_type,
            reaches_mop=False,
            directly_reaches_mop=False,
            target_view=view_data,
            coordinates=coordinates
        )

        # Update security info if applicable
        if view_data and view_data != {"special": "back_button"}:
            node = Node(view_data)
            self._update_action_security_info(action, node)

        return action

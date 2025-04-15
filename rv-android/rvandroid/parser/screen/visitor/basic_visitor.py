# rvandroid/parser/screen/visitor/basic_visitor.py

from typing import List, Optional, Set

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.domain.widget import WidgetEventType
from rvandroid.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rvandroid.parser.screen.visitor.model import ItemAction, ScreenItem, ScreenDescription, Counter, Node


class BasicTextVisitor(AbstractScreenVisitor):
    """
    Basic visitor implementation for generating simplified text descriptions of Android UI elements.
    This visitor provides minimal descriptions focusing only on essential information,
    making it suitable for situations where concise output is preferred.
    """

    def __init__(self, static_info: Optional[StaticAnalysisData], activity: str):
        """
        Initialize the basic visitor.

        Args:
            static_info: Static analysis data (optional)
            activity: Current activity name
        """
        super().__init__(static_info, activity)
        self.processed_parents: Set[str] = set()  # Track processed parent nodes
        self.logger.debug(f"Initialized BasicTextVisitor for activity: {activity}")

    def get_screen_description(self) -> ScreenDescription:
        """
        Create and return a basic screen description with a BACK action added.

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
        self.logger.info(f"Generated basic screen description with {len(self.items)} items")

        return ScreenDescription(self.activity, self.items)

    def visit_node(self, node: Node) -> None:
        """
        Visit a container node in the UI hierarchy.
        Process only actionable containers.

        Args:
            node: The node to visit
        """
        # Only process actionable containers that haven't been processed yet
        node_id = node.get_unique_id()

        if node_id in self.processed_parents:
            return

        if node.actionable:
            actions = self.get_possible_actions(node, self.counter)
            if actions:
                item = ScreenItem(node.data, f"Container {node.view_class}", actions)
                self.items.append(item)
                self.window_info["interactive_elements"] += 1
                self.processed_parents.add(node_id)

    def visit_leaf_node(self, node: Node) -> None:
        """
        Visit a leaf node in the UI hierarchy that doesn't have a specific handler.

        Args:
            node: The leaf node to visit
        """
        node_id = node.get_unique_id()

        if node_id in self.processed_parents:
            return

        if node.actionable:
            actions = self.get_possible_actions(node, self.counter)
            item = ScreenItem(node.data, f"Element {node.view_class}", actions)
            self.items.append(item)
            self.window_info["interactive_elements"] += 1
            self.processed_parents.add(node_id)

    def visit_button(self, node: Node) -> None:
        """
        Visit a button element with minimal description.

        Args:
            node: The button node to visit
        """
        actions = self.get_possible_actions(node, self.counter)
        text = f"Button \"{node.view_text if node.view_text else ""}\""
        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_edit_text(self, node: Node) -> None:
        """
        Visit an editable text field with minimal description.

        Args:
            node: The edit text node to visit
        """
        actions = self.get_possible_actions(node, self.counter)

        description = "Password field" if node.is_password else "Text field"
        if node.content_description:
            description += f" ({node.content_description})"

        item = ScreenItem(node.data, description, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_text_view(self, node: Node) -> None:
        """
        Visit a text view element with minimal description.

        Args:
            node: The text view node to visit
        """
        # Only add if it has text content or is interactive
        is_actionable = node.clickable or node.long_clickable

        if node.view_text or is_actionable:
            actions = self.get_possible_actions(node, self.counter)
            text = node.view_text if node.view_text else "Text view"
            item = ScreenItem(node.data, text, actions)
            self.items.append(item)
            if actions:
                self.window_info["interactive_elements"] += 1

    def visit_checkbox(self, node: Node) -> None:
        """
        Visit a checkbox element with minimal description.

        Args:
            node: The checkbox node to visit
        """
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)
        state = "checked" if node.checked else "unchecked"
        item = ScreenItem(node.data, f"Checkbox ({state})", actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_checked_text(self, node: Node) -> None:
        """
        Visit a checked text view element with minimal description.

        Args:
            node: The checked text view node to visit
        """
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)
        state = "checked" if node.checked else "unchecked"
        item = ScreenItem(node.data, f"Checked text ({state})", actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_image_button(self, node: Node) -> None:
        """
        Visit an image button element with minimal description.

        Args:
            node: The image button node to visit
        """
        actions = self.get_possible_actions(node, self.counter)
        item = ScreenItem(node.data, "Image button", actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_image(self, node: Node) -> None:
        """
        Visit an image element with minimal description.

        Args:
            node: The image node to visit
        """
        # Only add if it is interactive or has a description
        is_actionable = node.clickable or node.long_clickable

        if is_actionable or node.content_description:
            actions = self.get_possible_actions(node, self.counter)
            description = f"Image: {node.content_description}" if node.content_description else "Image"
            item = ScreenItem(node.data, description, actions)
            self.items.append(item)
            if actions:
                self.window_info["interactive_elements"] += 1

    def visit_toggle_button(self, node: Node) -> None:
        """
        Visit a toggle button element with minimal description.

        Args:
            node: The toggle button node to visit
        """
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)
        state = "ON" if node.checked else "OFF"
        item = ScreenItem(node.data, f"Toggle button ({state})", actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_switch(self, node: Node) -> None:
        """
        Visit a switch element with minimal description.

        Args:
            node: The switch node to visit
        """
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)
        state = "ON" if node.checked else "OFF"
        item = ScreenItem(node.data, f"Switch ({state})", actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_radio_button(self, node: Node) -> None:
        """
        Visit a radio button element with minimal description.

        Args:
            node: The radio button node to visit
        """
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)
        state = "selected" if node.selected else "not selected"
        item = ScreenItem(node.data, f"Radio button ({state})", actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_spinner(self, node: Node) -> None:
        """
        Visit a spinner element with minimal description.

        Args:
            node: The spinner node to visit
        """
        # For spinners, we want click action and scroll actions
        actions = []

        # Add click action
        if node.clickable:
            actions.append(ItemAction(
                self.counter.inc(),
                f"CLICK ({self.counter.get()})",
                WidgetEventType.CLICK, False, False,
                target_view=node.data
            ))

        # Add scroll actions
        if node.scrollable:
            for direction in ["UP", "DOWN"]:
                actions.append(ItemAction(
                    self.counter.inc(),
                    f"SCROLL {direction} ({self.counter.get()})",
                    WidgetEventType.SCROLL, False, False,
                    target_view=node.data
                ))

        item = ScreenItem(node.data, "Dropdown", actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_radio_group(self, node: Node) -> None:
        """
        Visit a radio group element with minimal description.

        Args:
            node: The radio group node to visit
        """
        # Process the radio group if it's directly actionable
        if node.actionable:
            actions = self.get_possible_actions(node, self.counter)
            item = ScreenItem(node.data, "Radio group", actions)
            self.items.append(item)
            self.window_info["interactive_elements"] += 1

        # Process each child individually
        for child in node.children:
            child.accept(self)

    def visit_slider(self, node: Node) -> None:
        """
        Visit a slider element with minimal description.

        Args:
            node: The slider node to visit
        """
        actions = self.get_possible_actions(node, self.counter)
        progress = node.progress if hasattr(node, 'progress') else 0
        max_val = node.max if hasattr(node, 'max') else 100

        if max_val > 0:
            percentage = int(progress * 100 / max_val)
        else:
            percentage = 0

        item = ScreenItem(node.data, f"Slider ({percentage}%)", actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    # def get_possible_actions(self, node: Node, counter: Counter, inherit_click: bool = False,
    #                          prioritize_check: bool = False) -> List[ItemAction]:
    #     """
    #     Get possible actions for a node with minimal information.
    #
    #     Args:
    #         node: The node to get actions for
    #         counter: Counter for generating unique IDs
    #         inherit_click: Whether to add click action from parent
    #         prioritize_check: Whether to prioritize check/uncheck over click
    #
    #     Returns:
    #         List of possible actions
    #     """
    #     actions = []
    #     node_data = node.data
    #
    #     # Extract coordinates from node
    #     coordinates = node.get_center_coordinates()
    #
    #     # Handle check/uncheck actions with priority if needed
    #     if prioritize_check and node.checkable:
    #         action_text = "UNCHECK" if node.checked else "CHECK"
    #         actions.append(ItemAction(
    #             id=counter.inc(),
    #             text=f"{action_text} ({counter.get()})",
    #             event=WidgetEventType.CLICK,
    #             reaches_mop=False,
    #             directly_reaches_mop=False,
    #             target_view=node_data,
    #             coordinates=coordinates
    #         ))
    #         return actions
    #
    #     # Handle click actions
    #     if node.clickable or inherit_click:
    #         actions.append(ItemAction(
    #             id=counter.inc(),
    #             text=f"CLICK ({counter.get()})",
    #             event=WidgetEventType.CLICK,
    #             reaches_mop=False,
    #             directly_reaches_mop=False,
    #             target_view=node_data,
    #             coordinates=coordinates
    #         ))
    #
    #     # Handle long click actions
    #     if node.long_clickable:
    #         actions.append(ItemAction(
    #             id=counter.inc(),
    #             text=f"LONG_CLICK ({counter.get()})",
    #             event=WidgetEventType.LONG_CLICK,
    #             reaches_mop=False,
    #             directly_reaches_mop=False,
    #             target_view=node_data,
    #             coordinates=coordinates
    #         ))
    #
    #     # Handle scroll actions
    #     if node.scrollable:
    #         for direction in ["UP", "DOWN", "LEFT", "RIGHT"]:
    #             actions.append(ItemAction(
    #                 id=counter.inc(),
    #                 text=f"SCROLL {direction} ({counter.get()})",
    #                 event=WidgetEventType.SCROLL,
    #                 reaches_mop=False,
    #                 directly_reaches_mop=False,
    #                 target_view=node_data,
    #                 coordinates=coordinates
    #             ))
    #
    #     # Handle text input actions
    #     if node.editable:
    #         actions.append(ItemAction(
    #             id=counter.inc(),
    #             text=f"SET_TEXT ({counter.get()})",
    #             event=WidgetEventType.TEXT_CHANGE,
    #             reaches_mop=False,
    #             directly_reaches_mop=False,
    #             target_view=node_data,
    #             coordinates=coordinates
    #         ))
    #
    #     return actions

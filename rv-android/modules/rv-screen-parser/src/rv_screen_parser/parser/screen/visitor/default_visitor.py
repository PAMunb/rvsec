# rvandroid/parser/visitor/text_visitor.py
from typing import Optional, Set

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
from rv_android_core.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rv_android_core.parser.screen.visitor.model import ItemAction, ScreenItem, ScreenDescription, Node


class DefaultTextVisitor(AbstractScreenVisitor):

    def __init__(self, static_info: Optional[StaticAnalysisData], activity: str):
        """
        Initialize the visitor.

        Args:
            static_info: Static analysis data (optional)
            activity: Current activity name
        """
        super().__init__(static_info, activity)
        self.processed_parents: Set[str] = set()  # Track processed parent nodes
        self.logger.debug(f"Initialized EnhancedTextVisitor for activity: {activity}")

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

    def visit_node(self, node: Node) -> None:
        """
        Visit a container node in the UI hierarchy.
        Process container if it's actionable but children aren't.

        Args:
            node: The node to visit
        """
        self.logger.debug(f"Visiting node: {node.view_class}")

        # Generate a unique identifier for the node
        node_id = node.get_unique_id()

        # Skip if already processed
        if node_id in self.processed_parents:
            return

        # Check if this node is actionable but none of its children handle the action
        if node.actionable and node.children:
            # Process actionable parent only if children don't handle the actions
            child_handles_action = False
            for child in node.children:
                if child.actionable:
                    child_handles_action = True
                    break

            if not child_handles_action:
                # This container has actions that aren't handled by children
                actions = self.get_possible_actions(node, self.counter)
                if actions:
                    text = f"Container {node.view_class} {self._with_description(node)}{self._with_hint(node)}"
                    item = ScreenItem(node.data, text, actions)
                    self.items.append(item)
                    self.window_info["interactive_elements"] += 1
                    self.processed_parents.add(node_id)

    def visit_leaf_node(self, leaf_node: Node) -> None:
        """
        Visit a leaf node in the UI hierarchy that doesn't have a specific handler.

        Args:
            leaf_node: The leaf node to visit
        """
        self.logger.debug(f"Visiting leaf node: {leaf_node.view_class}")

        # Generate a unique ID for the node
        node_id = leaf_node.get_unique_id()

        # Check if this node or its parent is actionable
        is_actionable = leaf_node.actionable

        # If not actionable itself, check if it inherits actions from parent
        parent_clickable = False
        if not is_actionable:
            parent_clickable = self.is_parent_clickable(leaf_node)
            is_actionable = parent_clickable

        if is_actionable and node_id not in self.processed_parents:
            actions = self.get_possible_actions(leaf_node, self.counter, inherit_click=parent_clickable)
            text = f"Element {leaf_node.view_class} {self._with_text(leaf_node)}{self._has_focus(leaf_node)}{self._with_description(leaf_node)}{self._with_resource_id(leaf_node)}"
            item = ScreenItem(leaf_node.data, text, actions)
            self.items.append(item)
            self.window_info["interactive_elements"] += 1
            self.processed_parents.add(node_id)

    def visit_button(self, node: Node) -> None:
        """
        Visit a button element and generate its description.

        Args:
            node: The button node to visit
        """
        self.logger.debug(f"Visiting button: {node.resource_id}")

        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter)

        # Verificar se actions não é None antes de iterá-lo
        if actions is not None:
            # Update actions with additional information from static analysis if available
            if widget:
                for action in actions:
                    for event in widget.events:
                        if event.type == action.event:
                            # TODO rever
                            action.reaches_mop = self._check_method_reaches_mop(event.signature)
                            action.directly_reaches_mop = self._check_method_directly_reaches_mop(event.signature)
        else:
            # Se actions for None, inicializar como lista vazia
            actions = []

        text = self.__default_message(node, "Button ")
        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_edit_text(self, node: Node) -> None:
        """
        Visit an editable text field and generate its description.

        Args:
            node: The edit text node to visit
        """
        self.logger.debug(f"Visiting edit text: {node.resource_id}")
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter)

        # Add input type information if available
        input_type = ""
        if widget and hasattr(widget, 'input_type') and widget.input_type:
            input_type = f" for {widget.input_type}"

        text = f"Editable text field{input_type} {self._with_text(node)}{self._with_description(node)}{self._with_hint(node)}{self._has_focus(node)} {self._with_field(widget)}"

        if node.is_password:
            text = f"Password field {self._with_text(node)}{self._with_description(node)}{self._with_hint(node)}{self._has_focus(node)}"

        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_text_view(self, node: Node) -> None:
        """
        Visit a text view element and generate its description.

        Args:
            node: The text view node to visit
        """
        self.logger.debug(f"Visiting text view: {node.resource_id}")

        # Check if node is actionable itself
        is_actionable = node.clickable or node.long_clickable

        # If not actionable itself, check if it inherits click from parent
        parent_clickable = False
        if not is_actionable:
            parent_clickable = self.is_parent_clickable(node)
            is_actionable = parent_clickable

        actions = self.get_possible_actions(node, self.counter, inherit_click=parent_clickable)

        # Only add if it has text content or is interactive
        if node.view_text or actions:
            text = f"Text view {self._with_text(node)}{self._with_description(node)}{self._with_hint(node)}{self._has_focus(node)}"
            item = ScreenItem(node.data, text, actions)
            self.items.append(item)
            if actions:
                self.window_info["interactive_elements"] += 1

    def visit_checkbox(self, node: Node) -> None:
        """
        Visit a checkbox element and generate its description.

        Args:
            node: The checkbox node to visit
        """
        self.logger.debug(f"Visiting checkbox: {node.resource_id}")
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)

        checked = " that is checked" if node.checked else " that is unchecked"
        text = f"Checkbox{checked} {self._with_text(node)}{self._with_description(node)}{self._with_hint(node)}{self._has_focus(node)}"

        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_checked_text(self, node: Node) -> None:
        """
        Visit a checked text view element and generate its description.

        Args:
            node: The checked text view node to visit
        """
        self.logger.debug(f"Visiting checked text view: {node.resource_id}")
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)

        checked = " that is checked" if node.checked else " that is unchecked"
        text = f"Checkable text{checked} {self._with_text(node)}{self._with_description(node)}{self._with_hint(node)}{self._has_focus(node)}"

        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_image_button(self, node: Node) -> None:
        """
        Visit an image button element and generate its description.

        Args:
            node: The image button node to visit
        """
        self.logger.debug(f"Visiting image button: {node.resource_id}")
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter)

        text = f"Image button {self._with_text(node)}{self._with_description(node)}{self._with_hint(node)}"

        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_image(self, node: Node) -> None:
        """
        Visit an image element and generate its description.

        Args:
            node: The image node to visit
        """
        self.logger.debug(f"Visiting image: {node.resource_id}")

        # Check if node is actionable itself
        is_actionable = node.clickable or node.long_clickable

        # If not actionable itself, check if it inherits click from parent
        parent_clickable = False
        if not is_actionable:
            parent_clickable = self.is_parent_clickable(node)
            is_actionable = parent_clickable

        actions = self.get_possible_actions(node, self.counter, inherit_click=parent_clickable)

        # Only include interactive images or those with descriptions
        if actions or node.content_description:
            text = f"Image {self._with_text(node)}{self._with_description(node)}{self._with_hint(node)}"
            item = ScreenItem(node.data, text, actions)
            self.items.append(item)
            if actions:
                self.window_info["interactive_elements"] += 1

    def visit_toggle_button(self, node: Node) -> None:
        """
        Visit a toggle button element and generate its description.

        Args:
            node: The toggle button node to visit
        """
        self.logger.debug(f"Visiting toggle button: {node.resource_id}")
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)

        state = " that is ON" if node.checked else " that is OFF"
        text = f"Toggle button{state} {self._with_text(node)}{self._with_description(node)}{self._with_hint(node)}{self._has_focus(node)}"

        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_switch(self, node: Node) -> None:
        """
        Visit a switch element and generate its description.

        Args:
            node: The switch node to visit
        """
        self.logger.debug(f"Visiting switch: {node.resource_id}")
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)

        state = " that is ON" if node.checked else " that is OFF"
        text = f"Switch{state} {self._with_text(node)}{self._with_description(node)}{self._with_hint(node)}{self._has_focus(node)}"

        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_radio_button(self, node: Node) -> None:
        """
        Visit a radio button element and generate its description.

        Args:
            node: The radio button node to visit
        """
        self.logger.debug(f"Visiting radio button: {node.resource_id}")
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)

        selected = " that is selected" if node.selected else " that is not selected"
        text = f"Radio button{selected} {self._with_text(node)}{self._with_description(node)}{self._with_hint(node)}{self._has_focus(node)}"

        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_spinner(self, node: Node) -> None:
        """
        Visit a spinner element and generate its description.

        Args:
            node: The spinner node to visit
        """
        self.logger.debug(f"Visiting spinner: {node.resource_id}")
        widget = self.find_matching_widget(node.data)

        # For spinners, we want click action and a selective set of scroll actions
        # Usually spinners need vertical scrolling, not horizontal
        actions = []

        # Add click action
        if node.clickable:
            actions.append(ItemAction(
                self.counter.inc(),
                f"CLICK ({self.counter.get()})" + (f" on '{node.view_text}'" if node.view_text else ""),
                WidgetEventType.CLICK, False, False
            ))

        # Only add vertical scroll for spinners
        # if node.scrollable:
        #     for direction in ["UP", "DOWN"]:
        #         actions.append(ItemAction(
        #             self.counter.inc(),
        #             f"SCROLL {direction} ({self.counter.get()})",
        #             WidgetEventType.SCROLL, False, False
        #         ))

        selected_item_text = ""
        if hasattr(node, 'children') and node.children:
            first_child = node.children[0]
            selected_item_text = f" with selected item '{first_child.view_text}'"

        options = ""
        if widget and hasattr(widget, 'entries') and widget.entries:
            options_list = ", ".join(widget.entries[:5])
            if len(widget.entries) > 5:
                options_list += f", and {len(widget.entries) - 5} more options"
            options = f" with options: {options_list}"

        text = f"Dropdown spinner{selected_item_text}{options}{self._with_description(node)}{self._with_hint(node)}"

        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def visit_radio_group(self, node: Node) -> None:
        """
        Visit a radio group element and generate its description.
        Group radio buttons together.

        Args:
            node: The radio group node to visit
        """
        self.logger.debug(f"Visiting radio group: {node.resource_id}")

        # Process group itself if actionable
        if node.actionable:
            actions = self.get_possible_actions(node, self.counter)
            text = f"Radio button group {self._with_description(node)}{self._with_hint(node)}"
            item = ScreenItem(node.data, text, actions)
            self.items.append(item)

        # Collect all radio buttons in this group
        radio_buttons = node.find_children_by_class("android.widget.RadioButton")

        # If we found multiple radio buttons, create a single item for the group
        if len(radio_buttons) > 1:
            group_actions = []
            group_text = "Radio button group with options: "

            for i, rb in enumerate(radio_buttons):
                # Create a select action for each radio button
                action_text = f"SELECT ({self.counter.inc()}) '{rb.view_text}'" if rb.view_text else f"SELECT option {i + 1} ({self.counter.get()})"
                group_actions.append(ItemAction(
                    self.counter.get(),
                    action_text,
                    WidgetEventType.CLICK,
                    False,
                    False
                ))

                # Add the radio button's text to the group description
                if i > 0:
                    group_text += ", "
                group_text += f"'{rb.view_text}'" if rb.view_text else f"Option {i + 1}"

            group_item = ScreenItem(node.data, group_text, group_actions)
            self.items.append(group_item)
            self.window_info["interactive_elements"] += 1

            # Mark all radio buttons as processed
            for rb in radio_buttons:
                self.processed_parents.add(rb.get_unique_id())
        else:
            # If only one radio button, visit it normally
            for child in node.children:
                child.accept(self)

    def visit_slider(self, node: Node) -> None:
        """
        Visit a slider (SeekBar) element and generate its description.

        Args:
            node: The slider node to visit
        """
        self.logger.debug(f"Visiting slider: {node.resource_id}")

        actions = []

        # Create actions for different positions on the slider
        slider_positions = [0, 25, 50, 75, 100]
        for position in slider_positions:
            actions.append(ItemAction(
                self.counter.inc(),
                f"SET_SLIDER ({self.counter.get()}) to {position}%",
                WidgetEventType.SCROLL,
                False,
                False
            ))

        current_percent = int((node.progress / node.max) * 100) if node.max > 0 else 0
        text = f"Slider currently at {current_percent}% {self._with_text(node)}{self._with_description(node)}"

        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def __default_message(self, node: Node, prefix: str) -> str:
        """
        Generate a default message for a UI element.

        Args:
            node: The node to describe
            prefix: Prefix to add to the description

        Returns:
            Formatted description string
        """
        return f"{prefix}{self._with_text(node)}{self._with_description(node)}{self._with_hint(node)}{self._has_focus(node)}"

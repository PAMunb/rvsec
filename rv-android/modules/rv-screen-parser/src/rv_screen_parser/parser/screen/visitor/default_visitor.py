"""Default visitor producing standard screen descriptions with system actions.

Generates balanced descriptions that include element type, text content,
accessibility hints, focus state, and resource IDs. Automatically injects
SYSTEM_BACK and RESTART_APP actions on every screen for consistent navigation.
This is the standard visitor used in production exploration flows.
"""

from typing import Any, Dict, Optional, Set

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
from rv_screen_parser.constants import ActionType, SystemActionType
from rv_screen_parser.parser.screen.visitor.abstract_visitor import (
    AbstractScreenVisitor,
)
from rv_screen_parser.parser.screen.visitor.model import (
    ItemAction,
    Node,
    ScreenDescription,
    ScreenItem,
)


class DefaultTextVisitor(AbstractScreenVisitor):
    """Generate standard screen descriptions with automatic system action injection.

    ### Architectural Decisions:
    - Balances description detail with token efficiency -- includes element type,
      text, hints, focus state, and resource IDs without depth/bounds metadata.
    - Automatically injects SYSTEM_BACK and RESTART_APP actions via
      _ensure_standard_system_actions, so every screen provides consistent
      navigation capabilities regardless of its UI elements.
    - Uses processed_parents tracking to handle actionable containers whose
      children do not themselves handle the action (avoids missing interactions).

    ### Role in the System:
    - The standard production visitor, selected via VisitorType.DEFAULT.
    - Produces ScreenDescription objects consumed by rv-agent for LLM-driven
      action selection and by rv-platform for task execution.
    - Handles the full widget type spectrum: buttons, edit text, text views,
      checkboxes, switches, toggles, radio buttons/groups, spinners, sliders,
      and image buttons/images.

    ### Key Features:
    - System action injection: SYSTEM_BACK and RESTART_APP with virtual target views.
    - Parent clickability inheritance: leaf nodes inherit click from parent containers.
    - ALWAYS_CLICKABLE_TYPES support for inherently interactive elements.
    - Slider support via DRAG actions with calculated swipe coordinates.
    - Spinner support with forced click action (spinners may lack clickable attr).

    ### Integration Points:
    - Inherits action generation and MOP tracking from AbstractScreenVisitor.
    - VisitorFactory creates instances based on VisitorType enum.
    - SystemActionType and ActionType enums from constants.py classify virtual actions.
    """

    def __init__(self, static_info: Optional[StaticAnalysisData], activity: str):
        """Initialize the default visitor.

        Args:
            static_info: Static analysis data for MOP tracking and widget matching.
                When None, MOP annotations are skipped.
            activity: Fully qualified Android activity name for the current screen.

        State:
            processed_parents: Set of node IDs already processed to avoid duplicates.
        """
        super().__init__(static_info, activity)
        self.processed_parents: Set[str] = set()  # Track processed parent nodes
        self.logger.debug(f"Initialized DefaultTextVisitor for activity: {activity}")

    def get_screen_description(self) -> ScreenDescription:
        """Build a ScreenDescription with automatic system action injection.

        Injects SYSTEM_BACK and RESTART_APP actions (if not already present)
        before constructing the final ScreenDescription, ensuring every screen
        provides consistent navigation capabilities.

        Returns:
            ScreenDescription with all visited UI elements and system actions.
        """
        # Add standard system actions for consistent navigation
        self._ensure_standard_system_actions()

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

        # NOTE: Do NOT call should_exclude_system_button here!
        # Containers often span the full screen (bottom_y >= 1850), so filtering
        # them would exclude ALL their children. Only filter leaf nodes.

        # Generate a unique identifier for the node
        node_id = node.unique_identifier

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

        # Skip system navigation buttons (navbar, status bar)
        if self.should_exclude_system_button(leaf_node):
            self.logger.debug(f"Excluding system button: {leaf_node.view_class}")
            return

        # Generate a unique ID for the node
        node_id = leaf_node.unique_identifier

        # Check if this node or its parent is actionable (including inherently clickable types)
        is_actionable = leaf_node.actionable or self.is_always_clickable_type(leaf_node)

        # If not actionable itself, check if it inherits actions from parent
        parent_clickable = False
        if not is_actionable:
            parent_clickable = self.is_parent_clickable(leaf_node)
            is_actionable = parent_clickable

        if is_actionable and node_id not in self.processed_parents:
            actions = self.get_possible_actions(
                leaf_node, self.counter, inherit_click=parent_clickable
            )
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
                            action.reaches_target = self._check_method_reaches_target(
                                event.signature
                            )
                            action.directly_reaches_target = (
                                self._check_method_directly_reaches_target(
                                    event.signature
                                )
                            )
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
        if widget and hasattr(widget, "input_type") and widget.input_type:
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

        # Check if node is actionable itself (including inherently clickable types)
        is_actionable = (
            node.clickable or node.long_clickable or self.is_always_clickable_type(node)
        )

        # If not actionable itself, check if it inherits click from parent
        parent_clickable = False
        if not is_actionable:
            parent_clickable = self.is_parent_clickable(node)
            is_actionable = parent_clickable

        actions = self.get_possible_actions(
            node, self.counter, inherit_click=parent_clickable
        )

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
        self.find_matching_widget(node.data)
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
        self.find_matching_widget(node.data)
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

        # Check if node is actionable itself (including inherently clickable types)
        is_actionable = (
            node.clickable or node.long_clickable or self.is_always_clickable_type(node)
        )

        # If not actionable itself, check if it inherits click from parent
        parent_clickable = False
        if not is_actionable:
            parent_clickable = self.is_parent_clickable(node)
            is_actionable = parent_clickable

        actions = self.get_possible_actions(
            node, self.counter, inherit_click=parent_clickable
        )

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
        self.find_matching_widget(node.data)
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
        self.find_matching_widget(node.data)
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
        self.find_matching_widget(node.data)
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

        # For spinners, always generate click action to open dropdown
        # Spinners may not be marked as clickable in UIAutomator dump
        actions = []

        # Extract coordinates from node
        node_data = node.data
        coordinates = None
        if hasattr(node, "center_coordinates"):
            coordinates = node.center_coordinates
        elif "bounds" in node_data:
            bounds = node_data["bounds"]
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                coordinates = (x, y)

        # Add click action (always for spinners)
        actions.append(
            ItemAction(
                id=self.counter.increment(),
                text=f"CLICK ({self.counter.get_current()})"
                + (f" on '{node.view_text}'" if node.view_text else ""),
                event=WidgetEventType.CLICK,
                reaches_target=False,
                directly_reaches_target=False,
                target_view=node_data,
                coordinates=coordinates,
            )
        )

        # Only add vertical scroll for spinners
        # if node.scrollable:
        #     for direction in ["UP", "DOWN"]:
        #         actions.append(ItemAction(
        #             self.counter.increment(),
        #             f"SCROLL {direction} ({self.counter.get_current()})",
        #             WidgetEventType.SCROLL, False, False
        #         ))

        selected_item_text = ""
        if hasattr(node, "children") and node.children:
            first_child = node.children[0]
            selected_item_text = f" with selected item '{first_child.view_text}'"

        options = ""
        if widget and hasattr(widget, "entries") and widget.entries:
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
                # Calculate coordinates from radio button bounds
                bounds = rb.bounds if hasattr(rb, "bounds") else rb.data.get("bounds")
                coordinates = None
                if bounds and len(bounds) == 2:
                    x1, y1 = bounds[0]
                    x2, y2 = bounds[1]
                    coordinates = ((x1 + x2) // 2, (y1 + y2) // 2)

                # Create a select action for each radio button with coordinates
                action_text = (
                    f"SELECT ({self.counter.increment()}) '{rb.view_text}'"
                    if rb.view_text
                    else f"SELECT option {i + 1} ({self.counter.get_current()})"
                )
                target_view = dict(rb.data) if rb.data else {}

                group_actions.append(
                    ItemAction(
                        id=self.counter.get_current(),
                        text=action_text,
                        event=WidgetEventType.CLICK,
                        reaches_target=False,
                        directly_reaches_target=False,
                        target_view=target_view,
                        coordinates=coordinates,
                    )
                )

                # Add the radio button's text to the group description
                if i > 0:
                    group_text += ", "
                group_text += f"'{rb.view_text}'" if rb.view_text else f"Option {i + 1}"

            group_item = ScreenItem(node.data, group_text, group_actions)
            self.items.append(group_item)
            self.window_info["interactive_elements"] += 1

            # Mark all radio buttons as processed
            for rb in radio_buttons:
                self.processed_parents.add(rb.unique_identifier)
        else:
            # If only one radio button, visit it normally
            for child in node.children:
                child.accept(self)

    def visit_slider(self, node: Node) -> None:
        """Visit a slider (SeekBar) and generate DRAG actions for target positions.

        Create DRAG_SLIDER actions for 0%, 25%, 50%, 75%, and 100% positions,
        each with calculated swipe coordinates from the current center to the
        target. Falls back to CLICK if bounds are not available.

        Args:
            node: The slider node to visit.
        """
        self.logger.debug(f"Visiting slider: {node.resource_id}")

        actions = []

        # Get slider bounds for coordinate calculation
        bounds = node.bounds if hasattr(node, "bounds") else node.data.get("bounds")
        if bounds and len(bounds) == 2:
            x1, y1 = bounds[0]
            x2, y2 = bounds[1]
            center_y = (y1 + y2) // 2
            width = x2 - x1
            center_x = (x1 + x2) // 2

            # Create DRAG actions for different positions on the slider
            slider_positions = [0, 25, 50, 75, 100]
            for position in slider_positions:
                # Calculate target X coordinate based on position percentage
                target_x = x1 + int(width * (position / 100))

                # Create target_view with swipe coordinates
                target_view = dict(node.data) if node.data else {}
                target_view["swipe_start"] = (center_x, center_y)
                target_view["swipe_end"] = (target_x, center_y)

                actions.append(
                    ItemAction(
                        id=self.counter.increment(),
                        text=f"DRAG_SLIDER ({self.counter.get_current()}) to {position}%",
                        event=WidgetEventType.DRAG,
                        reaches_target=False,
                        directly_reaches_target=False,
                        target_view=target_view,
                        coordinates=(center_x, center_y),
                    )
                )
        else:
            # Fallback if bounds not available - use CLICK at slider center
            self.logger.warning("Slider bounds not available, using click fallback")
            actions.append(
                ItemAction(
                    id=self.counter.increment(),
                    text=f"CLICK ({self.counter.get_current()}) on slider",
                    event=WidgetEventType.CLICK,
                    reaches_target=False,
                    directly_reaches_target=False,
                    target_view=node.data,
                )
            )

        current_percent = (
            int((node.progress / node.max_progress) * 100)
            if node.max_progress > 0
            else 0
        )
        text = f"Slider currently at {current_percent}% {self._with_text(node)}{self._with_description(node)}"

        item = ScreenItem(node.data, text, actions)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1

    def _get_max_action_id(self) -> int:
        """Get maximum action ID from all actions in all items."""
        if not self.items:
            return 0
        return max(
            (action.id for item in self.items for action in item.actions), default=0
        )

    def _add_system_action(self, actions: list[ItemAction]):
        """Wrap system actions in a ScreenItem and append to items list."""
        system_item = ScreenItem(
            view=self._create_system_action_view(SystemActionType.BACK),
            base_description="System",
            actions=actions,
        )
        self.items.append(system_item)
        self.logger.debug(f"Adding system actions: {len(actions)}")

    def _ensure_standard_system_actions(self) -> None:
        """Inject SYSTEM_BACK and RESTART_APP actions if not already present.

        Creates virtual ScreenItems with system action markers so every screen
        provides consistent navigation capabilities. Uses null coordinates and
        incremental IDs that avoid conflicts with UI element actions.
        """
        max_action_id = self._get_max_action_id()
        actions = []

        # Inject SYSTEM_BACK action if not already present
        if not self._has_action_by_type(SystemActionType.BACK):
            back_action = ItemAction(
                id=max_action_id + 1,
                text=f"SYSTEM_BACK ({max_action_id + 1})",
                event=WidgetEventType.BACK,
                reaches_target=False,
                directly_reaches_target=False,
                target_view=self._create_system_action_view(SystemActionType.BACK),
                coordinates=None,  # System actions use null coordinates
            )
            actions.append(back_action)
            # self._add_system_action(back_action)
            max_action_id += 1  # Increment max_id after use

        # Inject RESTART action if not already present
        if not self._has_action_by_type(SystemActionType.RESTART):
            restart_action = ItemAction(
                id=max_action_id + 1,
                text=f"RESTART_APP ({max_action_id + 1})",
                event=WidgetEventType.RESTART,
                reaches_target=False,
                directly_reaches_target=False,
                target_view=self._create_system_action_view(SystemActionType.RESTART),
                coordinates=None,  # System actions use null coordinates
            )
            actions.append(restart_action)
            # self._add_system_action(restart_action)

        if len(actions) > 0:
            self._add_system_action(actions)

    def _create_system_action_view(
        self, action_type: SystemActionType
    ) -> Dict[str, Any]:
        """Create a virtual view dictionary representing a system-level action.

        Args:
            action_type: System action type (BACK, RESTART) from SystemActionType enum.

        Returns:
            Dictionary with system_action flag, action_type classification,
            and placeholder bounds/resource_id for pipeline compatibility.
        """
        return {
            "content_description": f"System {action_type.value} Action",
            "class": f"SystemAction_{action_type.name}",
            "resource_id": f"system_{action_type.name.lower()}_action",
            "bounds": [[0, 0], [0, 0]],  # Virtual bounds for system actions
            "action_type": ActionType.SYSTEM_ACTION,
            "system_action_type": action_type,
            "system_action": True,  # Compatibility flag for existing code
        }

    def _has_action_by_type(self, system_action_type: SystemActionType) -> bool:
        """
        Check if screen already contains specific system action type.

        Args:
            system_action_type: System action type to check

        Returns:
            True if action type already exists in screen actions
        """
        for item in self.items:
            for action in item.actions:
                if (
                    hasattr(action, "target_view")
                    and action.target_view
                    and action.target_view.get("system_action_type")
                    == system_action_type
                ):
                    return True
        return False

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

# rvandroid/parser/screen/visitor/new_enhanced_visitor.py
from typing import List, Optional, Set, Dict, Any
import logging

from rvandroid.model.static import StaticAnalysisData
from rvandroid.model.widget import WidgetEventType, WidgetEvent
from rvandroid.parser.screen.visitor.base_visitor import BaseScreenVisitor, ItemAction, ScreenItem, Node, Counter, \
    ScreenDescription


class NewEnhancedTextVisitor(BaseScreenVisitor):
    """
    Highly detailed visitor implementation for generating comprehensive text descriptions of Android UI elements.
    This visitor provides extensive details about UI elements, their properties, relationships, and accessibility information.
    It's designed for situations where maximum information is needed for thorough analysis.
    """

    def __init__(self, static_info: Optional[StaticAnalysisData], activity: str):
        """
        Initialize the visitor.

        Args:
            static_info: Static analysis data (optional)
            activity: Current activity name
        """
        super().__init__(static_info, activity)
        self.processed_parents: Set[str] = set()  # Track processed parent nodes
        self.node_depth_map: Dict[str, int] = {}  # Track depth of nodes in hierarchy
        self.screen_structure: Dict[str, Any] = {
            "activity": activity,
            "hierarchy_depth": 0,
            "element_count": 0,
            "actionable_count": 0,
            "form_elements": [],
            "navigation_elements": []
        }
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Initialized NewEnhancedTextVisitor for activity: {activity}")

    def get_screen_description(self) -> ScreenDescription:
        """
        Create a comprehensive screen description including element relationships
        and screen structure information.

        Returns:
            ScreenDescription object with detailed information
        """
        # Add screen structure overview as the first item
        structure_desc = (
            f"Screen Overview: Activity {self.activity} with "
            f"{self.screen_structure['element_count']} elements "
            f"({self.screen_structure['actionable_count']} actionable), "
            f"hierarchy depth: {self.screen_structure['hierarchy_depth']}, "
            f"form elements: {len(self.screen_structure['form_elements'])}"
        )

        # Add form detection
        if self.screen_structure['form_elements']:
            form_types = set(elem['type'] for elem in self.screen_structure['form_elements'])
            form_desc = f"Form detected with: {', '.join(form_types)}"
            structure_item = ScreenItem(
                {"special": "screen_structure"},
                f"{structure_desc}. {form_desc}",
                []
            )
        else:
            structure_item = ScreenItem(
                {"special": "screen_structure"},
                structure_desc,
                []
            )

        # Insert as the first item
        self.items.insert(0, structure_item)

        # Add a default BACK action to the screen description
        back_action = ItemAction(
            self.counter.inc(),
            f"BACK ({self.counter.get()})",
            WidgetEventType.KEY,
            False,
            False,
            target_view={"special": "back_button"}
        )

        # Create a back button item
        back_item = ScreenItem(
            {"special": "back_button"},
            "System back button",
            [back_action]
        )

        self.items.append(back_item)
        self.logger.info(f"Generated comprehensive screen description with {len(self.items)} items")

        return ScreenDescription(self.activity, self.items)

    def visit_node(self, node: Node) -> None:
        """
        Visit a container node in the UI hierarchy.
        Process container with extensive details and track hierarchy depth.

        Args:
            node: The node to visit
        """
        # Compute node depth and update max hierarchy depth
        node_depth = self._compute_node_depth(node)
        self.node_depth_map[node.get_unique_id()] = node_depth
        self.screen_structure["hierarchy_depth"] = max(self.screen_structure["hierarchy_depth"], node_depth)

        node_id = node.get_unique_id()
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
                    # Get container layout type
                    layout_type = self._infer_layout_type(node)

                    # Detailed container description with layout information and dimensions
                    bounds_info = self._format_bounds_info(node)
                    description = (
                        f"{layout_type} Container {node.view_class} "
                        f"{self._with_resource_id(node)}"
                        f"{self._with_description(node)}"
                        f"{bounds_info} at depth {node_depth}"
                    )

                    item = ScreenItem(node.data, description, actions)
                    self._add_security_info(item, node)
                    self.items.append(item)
                    self.window_info["interactive_elements"] += 1
                    self.processed_parents.add(node_id)
                    self.screen_structure["element_count"] += 1
                    self.screen_structure["actionable_count"] += 1

    def visit_leaf_node(self, node: Node) -> None:
        """
        Visit a leaf node in the UI hierarchy with detailed information.

        Args:
            node: The leaf node to visit
        """
        node_id = node.get_unique_id()
        if node_id in self.processed_parents:
            return

        # Calculate node depth if not already done
        if node_id not in self.node_depth_map:
            node_depth = self._compute_node_depth(node)
            self.node_depth_map[node_id] = node_depth
        else:
            node_depth = self.node_depth_map[node_id]

        # Check if this node or its parent is actionable
        is_actionable = node.actionable
        parent_clickable = False

        if not is_actionable:
            parent_clickable = self.is_parent_clickable(node)
            is_actionable = parent_clickable

        if is_actionable:
            actions = self.get_possible_actions(node, self.counter, inherit_click=parent_clickable)

            # Include accessibility information and detailed properties
            accessibility_info = self._format_accessibility_info(node)
            bounds_info = self._format_bounds_info(node)

            description = (
                f"Element {node.view_class} "
                f"{self._with_text(node)}"
                f"{self._has_focus(node)}"
                f"{self._with_description(node)}"
                f"{self._with_resource_id(node)}"
                f"{bounds_info} at depth {node_depth}"
                f"{accessibility_info}"
            )

            item = ScreenItem(node.data, description, actions)
            self._add_security_info(item, node)
            self.items.append(item)
            self.window_info["interactive_elements"] += 1
            self.processed_parents.add(node_id)
            self.screen_structure["element_count"] += 1
            self.screen_structure["actionable_count"] += 1

    def visit_button(self, node: Node) -> None:
        """
        Visit a button element with detailed information.

        Args:
            node: The button node to visit
        """
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter)
        node_depth = self._compute_node_depth(node)

        # Check if this appears to be a navigation or form submission button
        button_purpose = self._determine_button_purpose(node)
        bounds_info = self._format_bounds_info(node)

        text = (
            f"{button_purpose} Button "
            f"{self._with_text(node)}"
            f"{self._has_focus(node)}"
            f"{self._with_description(node)}"
            f"{self._with_resource_id(node)}"
            f"{bounds_info} at depth {node_depth}"
        )

        # If button is used for navigation, track it in screen structure
        if button_purpose == "Navigation":
            self.screen_structure["navigation_elements"].append(node.resource_id or node.view_text or "unnamed_button")

        item = ScreenItem(node.data, text, actions)
        self._add_security_info(item, node)
        self._add_widget_info(item, widget)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1
        self.screen_structure["element_count"] += 1
        self.screen_structure["actionable_count"] += 1

    def visit_edit_text(self, node: Node) -> None:
        """
        Visit an editable text field with detailed information.

        Args:
            node: The edit text node to visit
        """
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter)
        node_depth = self._compute_node_depth(node)

        # More detailed input type analysis
        input_type_info = self._analyze_input_type(node)
        bounds_info = self._format_bounds_info(node)
        validation_info = self._infer_validation_rules(node, widget)

        description = (
            f"Editable {input_type_info} field "
            f"{self._with_text(node)}"
            f"{self._has_focus(node)}"
            f"{self._with_description(node)}"
            f"{self._with_resource_id(node)}"
            f"{bounds_info} at depth {node_depth}"
            f"{validation_info}"
        )

        # Track form elements in screen structure
        self.screen_structure["form_elements"].append({
            "id": node.resource_id or "unnamed_input",
            "type": input_type_info,
            "required": "required" in validation_info.lower()
        })

        item = ScreenItem(node.data, description, actions)
        self._add_security_info(item, node)
        self._add_widget_info(item, widget)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1
        self.screen_structure["element_count"] += 1
        self.screen_structure["actionable_count"] += 1

    def visit_text_view(self, node: Node) -> None:
        """
        Visit a text view element with detailed information.

        Args:
            node: The text view node to visit
        """
        is_actionable = node.clickable or node.long_clickable
        parent_clickable = False

        if not is_actionable:
            parent_clickable = self.is_parent_clickable(node)
            is_actionable = parent_clickable

        actions = self.get_possible_actions(node, self.counter, inherit_click=parent_clickable)
        node_depth = self._compute_node_depth(node)

        # Analyze text content and purpose
        text_purpose = self._determine_text_purpose(node)
        bounds_info = self._format_bounds_info(node)

        # Only add if it has text content or is interactive
        if node.view_text or actions:
            description = (
                f"{text_purpose} Text view "
                f"{self._with_text(node)}"
                f"{self._with_description(node)}"
                f"{self._with_resource_id(node)}"
                f"{bounds_info} at depth {node_depth}"
            )

            item = ScreenItem(node.data, description, actions)
            self._add_security_info(item, node)
            self.items.append(item)
            if actions:
                self.window_info["interactive_elements"] += 1
                self.screen_structure["actionable_count"] += 1
            self.screen_structure["element_count"] += 1

    def visit_checkbox(self, node: Node) -> None:
        """
        Visit a checkbox element with detailed information.

        Args:
            node: The checkbox node to visit
        """
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)
        node_depth = self._compute_node_depth(node)

        # Determine if this checkbox is part of a form and its purpose
        checkbox_purpose = self._determine_checkbox_purpose(node)
        bounds_info = self._format_bounds_info(node)

        checked = " that is checked" if node.checked else " that is unchecked"
        description = (
            f"{checkbox_purpose} Checkbox{checked} "
            f"{self._with_text(node)}"
            f"{self._with_description(node)}"
            f"{self._has_focus(node)}"
            f"{self._with_resource_id(node)}"
            f"{bounds_info} at depth {node_depth}"
        )

        # Track form elements if applicable
        if checkbox_purpose == "Form":
            self.screen_structure["form_elements"].append({
                "id": node.resource_id or "unnamed_checkbox",
                "type": "checkbox",
                "checked": node.checked
            })

        item = ScreenItem(node.data, description, actions)
        self._add_security_info(item, node)
        self._add_widget_info(item, widget)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1
        self.screen_structure["element_count"] += 1
        self.screen_structure["actionable_count"] += 1

    def visit_checked_text(self, node: Node) -> None:
        """
        Visit a checked text view element with detailed information.

        Args:
            node: The checked text view node to visit
        """
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)
        node_depth = self._compute_node_depth(node)
        bounds_info = self._format_bounds_info(node)

        checked = " that is checked" if node.checked else " that is unchecked"
        description = (
            f"Checkable text{checked} "
            f"{self._with_text(node)}"
            f"{self._with_description(node)}"
            f"{self._has_focus(node)}"
            f"{self._with_resource_id(node)}"
            f"{bounds_info} at depth {node_depth}"
        )

        item = ScreenItem(node.data, description, actions)
        self._add_security_info(item, node)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1
        self.screen_structure["element_count"] += 1
        self.screen_structure["actionable_count"] += 1

    def visit_toggle_button(self, node: Node) -> None:
        """
        Visit a toggle button with detailed information.

        Args:
            node: The toggle button node to visit
        """
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)
        node_depth = self._compute_node_depth(node)
        bounds_info = self._format_bounds_info(node)

        # Analyze toggle purpose
        toggle_purpose = self._determine_toggle_purpose(node)

        state = " that is ON" if node.checked else " that is OFF"
        description = (
            f"{toggle_purpose} Toggle button{state} "
            f"{self._with_text(node)}"
            f"{self._with_description(node)}"
            f"{self._has_focus(node)}"
            f"{self._with_resource_id(node)}"
            f"{bounds_info} at depth {node_depth}"
        )

        # Track as form element if applicable
        if toggle_purpose == "Form":
            self.screen_structure["form_elements"].append({
                "id": node.resource_id or "unnamed_toggle",
                "type": "toggle",
                "state": "on" if node.checked else "off"
            })

        item = ScreenItem(node.data, description, actions)
        self._add_security_info(item, node)
        self._add_widget_info(item, widget)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1
        self.screen_structure["element_count"] += 1
        self.screen_structure["actionable_count"] += 1

    def visit_switch(self, node: Node) -> None:
        """
        Visit a switch element with detailed information.

        Args:
            node: The switch node to visit
        """
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)
        node_depth = self._compute_node_depth(node)
        bounds_info = self._format_bounds_info(node)

        # Analyze switch purpose
        switch_purpose = self._determine_switch_purpose(node)

        state = " that is ON" if node.checked else " that is OFF"
        description = (
            f"{switch_purpose} Switch{state} "
            f"{self._with_text(node)}"
            f"{self._with_description(node)}"
            f"{self._has_focus(node)}"
            f"{self._with_resource_id(node)}"
            f"{bounds_info} at depth {node_depth}"
        )

        # Track as form element or setting if applicable
        if switch_purpose in ["Form", "Setting"]:
            self.screen_structure["form_elements"].append({
                "id": node.resource_id or "unnamed_switch",
                "type": "switch",
                "purpose": switch_purpose.lower(),
                "state": "on" if node.checked else "off"
            })

        item = ScreenItem(node.data, description, actions)
        self._add_security_info(item, node)
        self._add_widget_info(item, widget)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1
        self.screen_structure["element_count"] += 1
        self.screen_structure["actionable_count"] += 1

    def visit_image_button(self, node: Node) -> None:
        """
        Visit an image button with detailed information.

        Args:
            node: The image button node to visit
        """
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter)
        node_depth = self._compute_node_depth(node)

        # Analyze purpose and position of image button
        button_purpose = self._determine_button_purpose(node)
        position = self._determine_position(node)
        bounds_info = self._format_bounds_info(node)

        description = (
            f"{button_purpose} {position} Image button "
            f"{self._with_text(node)}"
            f"{self._with_description(node)}"
            f"{self._with_resource_id(node)}"
            f"{bounds_info} at depth {node_depth}"
        )

        # Track as navigation element if applicable
        if button_purpose == "Navigation":
            self.screen_structure["navigation_elements"].append(
                node.resource_id or node.content_description or "unnamed_image_button")

        item = ScreenItem(node.data, description, actions)
        self._add_security_info(item, node)
        self._add_widget_info(item, widget)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1
        self.screen_structure["element_count"] += 1
        self.screen_structure["actionable_count"] += 1

    def visit_image(self, node: Node) -> None:
        """
        Visit an image element with detailed information.

        Args:
            node: The image node to visit
        """
        # Check if node is actionable itself
        is_actionable = node.clickable or node.long_clickable
        parent_clickable = False

        if not is_actionable:
            parent_clickable = self.is_parent_clickable(node)
            is_actionable = parent_clickable

        actions = self.get_possible_actions(node, self.counter, inherit_click=parent_clickable)
        node_depth = self._compute_node_depth(node)

        # Analyze image properties and position
        position = self._determine_position(node)
        image_purpose = self._determine_image_purpose(node)
        bounds_info = self._format_bounds_info(node)

        # Only include interactive images or those with descriptions
        if actions or node.content_description:
            description = (
                f"{image_purpose} {position} Image "
                f"{self._with_text(node)}"
                f"{self._with_description(node)}"
                f"{self._with_resource_id(node)}"
                f"{bounds_info} at depth {node_depth}"
            )

            item = ScreenItem(node.data, description, actions)
            self._add_security_info(item, node)
            self.items.append(item)
            if actions:
                self.window_info["interactive_elements"] += 1
                self.screen_structure["actionable_count"] += 1
            self.screen_structure["element_count"] += 1

    def visit_radio_button(self, node: Node) -> None:
        """
        Visit a radio button with detailed information.

        Args:
            node: The radio button node to visit
        """
        widget = self.find_matching_widget(node.data)
        actions = self.get_possible_actions(node, self.counter, prioritize_check=True)
        node_depth = self._compute_node_depth(node)
        bounds_info = self._format_bounds_info(node)

        selected = " that is selected" if node.selected else " that is not selected"
        description = (
            f"Radio button{selected} "
            f"{self._with_text(node)}"
            f"{self._with_description(node)}"
            f"{self._has_focus(node)}"
            f"{self._with_resource_id(node)}"
            f"{bounds_info} at depth {node_depth}"
        )

        # Track as form element
        self.screen_structure["form_elements"].append({
            "id": node.resource_id or "unnamed_radio",
            "type": "radio",
            "selected": node.selected
        })

        item = ScreenItem(node.data, description, actions)
        self._add_security_info(item, node)
        self._add_widget_info(item, widget)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1
        self.screen_structure["element_count"] += 1
        self.screen_structure["actionable_count"] += 1

    def visit_radio_group(self, node: Node) -> None:
        """
        Visit a radio group element with detailed information.

        Args:
            node: The radio group node to visit
        """
        node_depth = self._compute_node_depth(node)
        bounds_info = self._format_bounds_info(node)

        # Process group itself if actionable
        if node.actionable:
            actions = self.get_possible_actions(node, self.counter)
            description = (
                f"Radio button group "
                f"{self._with_description(node)}"
                f"{self._with_resource_id(node)}"
                f"{bounds_info} at depth {node_depth}"
            )
            item = ScreenItem(node.data, description, actions)
            self._add_security_info(item, node)
            self.items.append(item)
            self.screen_structure["element_count"] += 1
            self.screen_structure["actionable_count"] += 1

        # Collect all radio buttons in this group
        radio_buttons = node.find_children_by_class("android.widget.RadioButton")

        # If we found multiple radio buttons, create a single item for the group
        if len(radio_buttons) > 1:
            group_actions = []
            group_text = "Radio button group with options: "

            # Track option values for screen structure
            radio_options = []

            for i, rb in enumerate(radio_buttons):
                # Create a select action for each radio button
                rb_node_id = rb.get_unique_id()
                self.processed_parents.add(rb_node_id)

                action_text = f"SELECT ({self.counter.inc()}) '{rb.view_text}'" if rb.view_text else f"SELECT option {i + 1} ({self.counter.get()})"

                action = ItemAction(
                    self.counter.get(),
                    action_text,
                    WidgetEventType.CLICK,
                    False,
                    False,
                    target_view=rb.data
                )

                group_actions.append(action)

                # Add the radio button's text to the group description
                if i > 0:
                    group_text += ", "
                option_text = f"'{rb.view_text}'" if rb.view_text else f"Option {i + 1}"
                group_text += option_text

                # Track option
                radio_options.append({
                    "text": rb.view_text or f"Option {i + 1}",
                    "selected": rb.selected
                })

            # Track as form element
            self.screen_structure["form_elements"].append({
                "id": node.resource_id or "radio_group",
                "type": "radio_group",
                "options": radio_options
            })

            group_item = ScreenItem(node.data, f"{group_text}{bounds_info} at depth {node_depth}", group_actions)
            self._add_security_info(group_item, node)
            self.items.append(group_item)
            self.window_info["interactive_elements"] += 1
            self.screen_structure["element_count"] += 1
            self.screen_structure["actionable_count"] += 1
        else:
            # If only one radio button, visit it normally
            for child in node.children:
                child.accept(self)

    def visit_spinner(self, node: Node) -> None:
        """
        Visit a spinner element with detailed information.

        Args:
            node: The spinner node to visit
        """
        widget = self.find_matching_widget(node.data)
        node_depth = self._compute_node_depth(node)
        bounds_info = self._format_bounds_info(node)

        # For spinners, we want click action and a selective set of scroll actions
        actions = []

        # Add click action
        if node.clickable:
            actions.append(ItemAction(
                self.counter.inc(),
                f"CLICK ({self.counter.get()})" + (f" on '{node.view_text}'" if node.view_text else ""),
                WidgetEventType.CLICK, False, False,
                target_view=node.data
            ))

        # Add vertical scroll for spinners
        if node.scrollable:
            for direction in ["UP", "DOWN"]:
                actions.append(ItemAction(
                    self.counter.inc(),
                    f"SCROLL {direction} ({self.counter.get()})",
                    WidgetEventType.SCROLL, False, False,
                    target_view=node.data
                ))

        # Generate detailed options information
        options_info = ""
        if widget and hasattr(widget, 'entries') and widget.entries:
            options_list = ", ".join(widget.entries[:3])
            if len(widget.entries) > 3:
                options_list += f", and {len(widget.entries) - 3} more options"
            options_info = f" with options: {options_list}"

        description = (
            f"Dropdown spinner{options_info} "
            f"{self._with_text(node)}"
            f"{self._with_description(node)}"
            f"{self._with_resource_id(node)}"
            f"{bounds_info} at depth {node_depth}"
        )

        # Track as form element
        self.screen_structure["form_elements"].append({
            "id": node.resource_id or "unnamed_spinner",
            "type": "dropdown",
            "options_count": len(widget.entries) if widget and hasattr(widget, 'entries') else 0
        })

        item = ScreenItem(node.data, description, actions)
        self._add_security_info(item, node)
        self._add_widget_info(item, widget)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1
        self.screen_structure["element_count"] += 1
        self.screen_structure["actionable_count"] += 1

    def visit_slider(self, node: Node) -> None:
        """
        Visit a slider (SeekBar) element with detailed information.

        Args:
            node: The slider node to visit
        """
        widget = self.find_matching_widget(node.data)
        node_depth = self._compute_node_depth(node)
        bounds_info = self._format_bounds_info(node)

        actions = []

        # Create actions for different positions on the slider
        slider_positions = [0, 25, 50, 75, 100]
        for position in slider_positions:
            actions.append(ItemAction(
                self.counter.inc(),
                f"SET_SLIDER ({self.counter.get()}) to {position}%",
                WidgetEventType.SCROLL,
                False,
                False,
                target_view=node.data
            ))

        # Calculate current position as percentage
        current_percent = int((node.progress / node.max) * 100) if node.max > 0 else 0

        # Determine slider purpose
        slider_purpose = self._determine_slider_purpose(node)

        description = (
            f"{slider_purpose} Slider currently at {current_percent}% "
            f"{self._with_text(node)}"
            f"{self._with_description(node)}"
            f"{self._with_resource_id(node)}"
            f"{bounds_info} at depth {node_depth} "
            f"(range: 0-{node.max})"
        )

        # Track as form element
        self.screen_structure["form_elements"].append({
            "id": node.resource_id or "unnamed_slider",
            "type": "slider",
            "value": current_percent,
            "max": node.max
        })

        item = ScreenItem(node.data, description, actions)
        self._add_security_info(item, node)
        self._add_widget_info(item, widget)
        self.items.append(item)
        self.window_info["interactive_elements"] += 1
        self.screen_structure["element_count"] += 1
        self.screen_structure["actionable_count"] += 1

    def get_possible_actions(self, node: Node, counter: Counter, inherit_click: bool = False,
                             prioritize_check: bool = False) -> List[ItemAction]:
        """
        Get possible actions for a node with enhanced security awareness and detailed information.

        Args:
            node: The node to get actions for
            counter: Counter for generating unique IDs
            inherit_click: Whether to add click action from parent
            prioritize_check: Whether to prioritize check/uncheck over click

        Returns:
            List of possible actions with security information
        """
        actions = []

        # Store the node data for later use in the ItemAction
        node_data = node.data

        # Extract coordinates from node
        coordinates = None
        if hasattr(node, 'get_center_coordinates'):
            coordinates = node.get_center_coordinates()
        elif 'bounds' in node_data:
            bounds = node_data['bounds']
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                coordinates = (x, y)

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

        # Handle click actions
        elif (node.clickable or inherit_click) and not (prioritize_check and node.checkable):
            text_suffix = ""
            if node.view_text:
                text_suffix = f" on '{node.view_text[:30]}'{' (truncated)' if len(node.view_text) > 30 else ''}"

            action = ItemAction(
                id=counter.inc(),
                text=f"CLICK ({counter.get()}){text_suffix}",
                event=WidgetEventType.CLICK,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view=node_data,
                coordinates=coordinates
            )
            # Update security information
            self._update_action_security_info(action, node)
            actions.append(action)

        # Handle long click actions
        if node.long_clickable:
            text_suffix = ""
            if node.view_text:
                text_suffix = f" on '{node.view_text[:30]}'{' (truncated)' if len(node.view_text) > 30 else ''}"

            action = ItemAction(
                id=counter.inc(),
                text=f"LONG_CLICK ({counter.get()}){text_suffix}",
                event=WidgetEventType.LONG_CLICK,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view=node_data,
                coordinates=coordinates
            )
            # Update security information
            self._update_action_security_info(action, node)
            actions.append(action)

        # Handle check/uncheck actions with normal priority
        if not prioritize_check and node.checkable:
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

        # Handle scroll actions with better description
        if node.scrollable:
            # Infer scrollable directions based on the widget type and content
            directions = ["UP", "DOWN", "LEFT", "RIGHT"]

            # Filter directions for certain widget types
            if node.view_class in ["android.widget.ListView", "android.widget.ScrollView"]:
                directions = ["UP", "DOWN"]
            elif node.view_class in ["android.widget.HorizontalScrollView"]:
                directions = ["LEFT", "RIGHT"]

            for direction in directions:
                action = ItemAction(
                    id=counter.inc(),
                    text=f"SCROLL {direction} ({counter.get()})",
                    event=WidgetEventType.SCROLL,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view=node_data,
                    coordinates=coordinates
                )
                # Update security information
                self._update_action_security_info(action, node)
                actions.append(action)

        # Handle text input actions with better hints
        if node.editable:
            hint = ""
            input_type = self._analyze_input_type(node)

            if node.view_text:
                hint = f" [current: '{node.view_text[:20]}'{' (truncated)' if len(node.view_text) > 20 else ''}]"
            elif node.content_description:
                hint = f" [hint: '{node.content_description[:20]}'{' (truncated)' if len(node.content_description) > 20 else ''}]"
            elif input_type:
                hint = f" [{input_type}]"

            action = ItemAction(
                id=counter.inc(),
                text=f"SET_TEXT ({counter.get()}){hint}",
                event=WidgetEventType.TEXT_CHANGE,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view=node_data,
                coordinates=coordinates
            )
            # Update security information
            self._update_action_security_info(action, node)
            actions.append(action)

        return actions

    def get_screen_description(self) -> ScreenDescription:
        """
        Create a comprehensive screen description including element relationships
        and screen structure information.

        Returns:
            ScreenDescription object with detailed information
        """
        # Add screen structure overview as the first item
        structure_desc = (
            f"Screen Overview: Activity {self.activity} with "
            f"{self.screen_structure['element_count']} elements "
            f"({self.screen_structure['actionable_count']} actionable), "
            f"hierarchy depth: {self.screen_structure['hierarchy_depth']}, "
            f"form elements: {len(self.screen_structure['form_elements'])}"
        )

        # Add form detection
        if self.screen_structure['form_elements']:
            form_types = set(elem['type'] for elem in self.screen_structure['form_elements'])
            form_desc = f"Form detected with: {', '.join(form_types)}"
            structure_item = ScreenItem(
                {"special": "screen_structure"},
                f"{structure_desc}. {form_desc}",
                []
            )
        else:
            structure_item = ScreenItem(
                {"special": "screen_structure"},
                structure_desc,
                []
            )

        # Insert as the first item
        self.items.insert(0, structure_item)

        # Add a default BACK action to the screen description
        back_action = ItemAction(
            self.counter.inc(),
            f"BACK ({self.counter.get()})",
            WidgetEventType.KEY,
            False,
            False,
            target_view={"special": "back_button"}
        )

        # Create a back button item
        back_item = ScreenItem(
            {"special": "back_button"},
            "System back button",
            [back_action]
        )

        self.items.append(back_item)
        self.logger.info(f"Generated comprehensive screen description with {len(self.items)} items")

        return ScreenDescription(self.activity, self.items)

    def _compute_node_depth(self, node: Node) -> int:
        """
        Compute the depth of a node in the UI hierarchy.

        Args:
            node: The node to compute depth for

        Returns:
            Depth of the node (0 for root)
        """
        depth = 0
        parent = node.parent

        while parent is not None:
            depth += 1
            parent = parent.parent

        return depth

    def _update_action_security_info(self, action: ItemAction, node: Node) -> None:
        """
        Update an action with detailed security information from static analysis.

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

                # Add more detailed info to action text if it reaches MOP
                if action.directly_reaches_mop:
                    action.text += " [CRITICAL SECURITY OPERATION]"
                elif action.reaches_mop:
                    action.text += " [SECURITY SENSITIVE]"

                return

    def _add_security_info(self, item: ScreenItem, node: Node) -> None:
        """
        Add security information to the item description.

        Args:
            item: The screen item to update
            node: The node associated with the item
        """
        # Check if any actions have security implications
        has_critical = any(action.directly_reaches_mop for action in item.actions)
        has_sensitive = any(action.reaches_mop for action in item.actions)

        if has_critical:
            item.base_description += " [CRITICAL SECURITY ELEMENT]"
        elif has_sensitive:
            item.base_description += " [SECURITY SENSITIVE]"

    def _add_widget_info(self, item: ScreenItem, widget) -> None:
        """
        Add detailed widget information from static analysis.

        Args:
            item: The screen item to update
            widget: The widget from static analysis
        """
        if not widget:
            return

        # Add information about widget events
        event_info = []
        for event in widget.events:
            event_desc = f"{event.type.name}"
            if self._check_method_directly_reaches_mop(event.signature):
                event_desc += " (directly reaches critical operation)"
            elif self._check_method_reaches_mop(event.signature):
                event_desc += " (can reach critical operation)"
            event_info.append(event_desc)

        if event_info:
            item.base_description += f" [Events: {', '.join(event_info)}]"

    def _infer_layout_type(self, node: Node) -> str:
        """
        Infer the layout type of a container node.

        Args:
            node: The container node

        Returns:
            Layout type description
        """
        class_name = node.view_class.lower()

        if "linear" in class_name:
            orientation = "Vertical" if "vertical" in str(node.data) else "Horizontal"
            return f"{orientation} Linear"
        elif "relative" in class_name:
            return "Relative"
        elif "frame" in class_name:
            return "Frame"
        elif "constraint" in class_name:
            return "Constraint"
        elif "coordinator" in class_name:
            return "Coordinator"
        elif "grid" in class_name:
            return "Grid"
        elif "table" in class_name:
            return "Table"
        elif "drawer" in class_name:
            return "Drawer"
        elif "recycler" in class_name or "list" in class_name:
            return "List"
        elif "scroll" in class_name:
            orientation = "Vertical" if "vertical" in str(node.data) else "Horizontal"
            return f"{orientation} Scrollable"

        return "Generic"

    def _format_bounds_info(self, node: Node) -> str:
        """
        Format bounds information for display.

        Args:
            node: The node to get bounds for

        Returns:
            Formatted bounds information
        """
        if not hasattr(node, 'bounds') or not node.bounds:
            return ""

        try:
            bounds = node.bounds
            if len(bounds) == 2:
                x1, y1 = bounds[0]
                x2, y2 = bounds[1]
                width = x2 - x1
                height = y2 - y1
                position = self._determine_screen_position(x1, y1, x2, y2)
                return f" at {position} [{width}x{height}]"
        except (IndexError, TypeError):
            pass

        return ""

    def _format_accessibility_info(self, node: Node) -> str:
        """
        Format accessibility information.

        Args:
            node: The node to get accessibility info for

        Returns:
            Formatted accessibility information
        """
        info_parts = []

        if hasattr(node, 'content_description') and node.content_description:
            info_parts.append(f"a11y description: '{node.content_description}'")

        # Analyze accessibility issues
        if not node.content_description and node.clickable:
            info_parts.append("missing a11y description")

        if hasattr(node, 'enabled') and not node.enabled:
            info_parts.append("disabled")

        if not info_parts:
            return ""

        return f" [{', '.join(info_parts)}]"

    def _determine_position(self, node: Node) -> str:
        """
        Determine the screen position of a node.

        Args:
            node: The node to determine position for

        Returns:
            Position description (e.g., "Top Left", "Center", etc.)
        """
        if not hasattr(node, 'bounds') or not node.bounds:
            return ""

        try:
            bounds = node.bounds
            if len(bounds) == 2:
                x1, y1 = bounds[0]
                x2, y2 = bounds[1]
                return self._determine_screen_position(x1, y1, x2, y2)
        except (IndexError, TypeError):
            pass

        return ""

    def _determine_screen_position(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """
        Determine screen position based on coordinates.

        Args:
            x1: Left coordinate
            y1: Top coordinate
            x2: Right coordinate
            y2: Bottom coordinate

        Returns:
            Position description
        """
        # Assume screen is approximately 1080x1920 (can be adjusted based on device)
        screen_width = 1080
        screen_height = 1920

        # Calculate center point
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        # Determine horizontal position
        if center_x < screen_width * 0.33:
            h_pos = "Left"
        elif center_x > screen_width * 0.66:
            h_pos = "Right"
        else:
            h_pos = "Center"

        # Determine vertical position
        if center_y < screen_height * 0.33:
            v_pos = "Top"
        elif center_y > screen_height * 0.66:
            v_pos = "Bottom"
        else:
            v_pos = "Middle"

        return f"{v_pos} {h_pos}"

    def _analyze_input_type(self, node: Node) -> str:
        """
        Perform detailed analysis of input field type.

        Args:
            node: The input node to analyze

        Returns:
            Detailed input type description
        """
        # Check common properties for clues
        resource_id = node.resource_id.lower() if hasattr(node, 'resource_id') and node.resource_id else ""
        text = node.view_text.lower() if hasattr(node, 'view_text') and node.view_text else ""
        hint = node.hint.lower() if hasattr(node, 'hint') and node.hint else ""
        content_desc = node.content_description.lower() if hasattr(node,
                                                                   'content_description') and node.content_description else ""

        # Check the most specific types first
        if hasattr(node, 'is_password') and node.is_password:
            return "password"

        if "email" in resource_id or "email" in hint or "email" in content_desc:
            return "email address"

        if "phone" in resource_id or "phone" in hint or "mobile" in resource_id:
            return "phone number"

        if "username" in resource_id or "username" in hint or "user name" in hint:
            return "username"

        if "search" in resource_id or "search" in hint or "query" in resource_id:
            return "search query"

        if "url" in resource_id or "website" in hint or "http" in hint:
            return "URL"

        if "date" in resource_id or "date" in hint or "calendar" in resource_id:
            return "date"

        if "time" in resource_id or "time" in hint or "hours" in hint:
            return "time"

        if "zip" in resource_id or "postal" in resource_id or "zip" in hint:
            return "ZIP/postal code"

        if "address" in resource_id or "address" in hint:
            return "address"

        if "code" in resource_id or "otp" in resource_id or "verification" in resource_id:
            return "verification code"

        if "name" in resource_id or "name" in hint:
            if "first" in resource_id or "first" in hint:
                return "first name"
            if "last" in resource_id or "last" in hint:
                return "last name"
            return "name"

        # More generic types
        if "number" in resource_id or "numeric" in hint:
            return "numeric field"

        if "message" in resource_id or "comment" in resource_id or node.view_class == "android.widget.EditText" and node.view_text and len(
                node.view_text) > 50:
            return "multi-line text"

        # Default
        return "text field"

    def _determine_button_purpose(self, node: Node) -> str:
        """
        Determine the purpose of a button.

        Args:
            node: The button node

        Returns:
            Button purpose description
        """
        # Check common properties for clues
        resource_id = node.resource_id.lower() if hasattr(node, 'resource_id') and node.resource_id else ""
        text = node.view_text.lower() if hasattr(node, 'view_text') and node.view_text else ""
        content_desc = node.content_description.lower() if hasattr(node,
                                                                   'content_description') and node.content_description else ""

        # Navigation buttons
        if any(term in (text + resource_id + content_desc) for term in
               ["back", "prev", "previous", "return", "nav", "arrow"]):
            return "Navigation"

        # Action buttons
        if any(term in (text + resource_id + content_desc) for term in
               ["submit", "save", "done", "ok", "apply", "confirm", "accept"]):
            return "Action"

        # Confirmation buttons
        if any(term in (text + resource_id + content_desc) for term in
               ["yes", "confirm", "agree", "proceed"]):
            return "Confirmation"

        # Cancellation buttons
        if any(term in (text + resource_id + content_desc) for term in
               ["no", "cancel", "deny", "reject", "dismiss", "close"]):
            return "Cancellation"

        # Menu buttons
        if any(term in (text + resource_id + content_desc) for term in
               ["menu", "drawer", "hamburger", "options"]):
            return "Menu"

        # Default
        return "Standard"

    def _determine_text_purpose(self, node: Node) -> str:
        """
        Determine the purpose of a text element.

        Args:
            node: The text node

        Returns:
            Text purpose description
        """
        # Check common properties for clues
        resource_id = node.resource_id.lower() if hasattr(node, 'resource_id') and node.resource_id else ""
        text = node.view_text.lower() if hasattr(node, 'view_text') and node.view_text else ""

        # Title or heading (typically larger or bold text)
        if "title" in resource_id or "header" in resource_id:
            return "Title"

        # Label (typically describing a UI element)
        if "label" in resource_id:
            return "Label"

        # Error message
        if "error" in resource_id or "error" in text:
            return "Error"

        # Status text
        if "status" in resource_id:
            return "Status"

        # Description or info text
        if "desc" in resource_id or "info" in resource_id:
            return "Description"

        # Default - use heuristics based on content
        if text:
            if len(text) < 30 and text.upper() == text:  # All caps short text is likely a header
                return "Header"
            elif len(text) > 100:  # Long text is likely a paragraph
                return "Paragraph"

        # Generic label
        return "Generic"

    def _determine_checkbox_purpose(self, node: Node) -> str:
        """
        Determine the purpose of a checkbox.

        Args:
            node: The checkbox node

        Returns:
            Checkbox purpose description
        """
        # Check common properties for clues
        resource_id = node.resource_id.lower() if hasattr(node, 'resource_id') and node.resource_id else ""
        text = node.view_text.lower() if hasattr(node, 'view_text') and node.view_text else ""
        content_desc = node.content_description.lower() if hasattr(node,
                                                                   'content_description') and node.content_description else ""

        # Terms for agreement checkboxes
        agreement_terms = ["agree", "accept", "terms", "conditions", "policy", "policies", "consent"]
        if any(term in (text + resource_id + content_desc) for term in agreement_terms):
            return "Agreement"

        # Terms for preference or settings checkboxes
        preference_terms = ["preference", "option", "setting", "config", "enable", "disable", "turn on", "turn off"]
        if any(term in (text + resource_id + content_desc) for term in preference_terms):
            return "Preference"

        # Terms for form checkboxes
        form_terms = ["form", "select", "choose", "selection"]
        if any(term in (text + resource_id + content_desc) for term in form_terms):
            return "Form"

        # Default
        return "Form"  # Most checkboxes are part of forms

    def _determine_toggle_purpose(self, node: Node) -> str:
        """
        Determine the purpose of a toggle button.

        Args:
            node: The toggle button node

        Returns:
            Toggle purpose description
        """
        # Similar to checkbox purpose but with toggle-specific terms
        resource_id = node.resource_id.lower() if hasattr(node, 'resource_id') and node.resource_id else ""
        text = node.view_text.lower() if hasattr(node, 'view_text') and node.view_text else ""
        content_desc = node.content_description.lower() if hasattr(node,
                                                                   'content_description') and node.content_description else ""

        # Settings toggles
        settings_terms = ["setting", "preference", "enable", "disable", "mode"]
        if any(term in (text + resource_id + content_desc) for term in settings_terms):
            return "Setting"

        # Feature toggles
        feature_terms = ["feature", "function", "capability"]
        if any(term in (text + resource_id + content_desc) for term in feature_terms):
            return "Feature"

        # Form toggles
        form_terms = ["form", "option", "select"]
        if any(term in (text + resource_id + content_desc) for term in form_terms):
            return "Form"

        # Default
        return "State"  # Generic state toggle

    def _determine_switch_purpose(self, node: Node) -> str:
        """
        Determine the purpose of a switch.

        Args:
            node: The switch node

        Returns:
            Switch purpose description
        """
        # Similar to toggle purpose
        resource_id = node.resource_id.lower() if hasattr(node, 'resource_id') and node.resource_id else ""
        text = node.view_text.lower() if hasattr(node, 'view_text') and node.view_text else ""
        content_desc = node.content_description.lower() if hasattr(node,
                                                                   'content_description') and node.content_description else ""

        # Privacy settings
        privacy_terms = ["privacy", "data", "collection", "tracking", "analytics"]
        if any(term in (text + resource_id + content_desc) for term in privacy_terms):
            return "Privacy"

        # System settings
        system_terms = ["wifi", "bluetooth", "location", "gps", "notification", "sound", "vibrate", "airplane", "sync"]
        if any(term in (text + resource_id + content_desc) for term in system_terms):
            return "System"

        # General settings
        settings_terms = ["setting", "preference", "enable", "disable", "toggle", "turn on", "turn off"]
        if any(term in (text + resource_id + content_desc) for term in settings_terms):
            return "Setting"

        # Form switches
        form_terms = ["form", "option", "select", "choose"]
        if any(term in (text + resource_id + content_desc) for term in form_terms):
            return "Form"

        # Default
        return "Toggle"  # Generic toggle switch

    def _determine_image_purpose(self, node: Node) -> str:
        """
        Determine the purpose of an image.

        Args:
            node: The image node

        Returns:
            Image purpose description
        """
        resource_id = node.resource_id.lower() if hasattr(node, 'resource_id') and node.resource_id else ""
        content_desc = node.content_description.lower() if hasattr(node,
                                                                   'content_description') and node.content_description else ""

        # Icons
        icon_terms = ["icon", "ic_", "img_"]
        if any(term in resource_id for term in icon_terms):
            return "Icon"

        # Avatars/profile pictures
        avatar_terms = ["avatar", "profile", "picture", "photo", "user"]
        if any(term in (resource_id + content_desc) for term in avatar_terms):
            return "Avatar"

        # Banners
        banner_terms = ["banner", "header", "logo", "brand"]
        if any(term in (resource_id + content_desc) for term in banner_terms):
            return "Banner"

        # Illustrations
        illustration_terms = ["illustration", "graphic", "drawing"]
        if any(term in (resource_id + content_desc) for term in illustration_terms):
            return "Illustration"

        # Decorative or unknown
        return "Decorative"

    def _determine_slider_purpose(self, node: Node) -> str:
        """
        Determine the purpose of a slider.

        Args:
            node: The slider node

        Returns:
            Slider purpose description
        """
        resource_id = node.resource_id.lower() if hasattr(node, 'resource_id') and node.resource_id else ""
        content_desc = node.content_description.lower() if hasattr(node,
                                                                   'content_description') and node.content_description else ""

        # Media player sliders
        media_terms = ["media", "player", "video", "audio", "music", "volume", "progress", "seek", "timeline"]
        if any(term in (resource_id + content_desc) for term in media_terms):
            return "Media Control"

        # Value selection sliders
        value_terms = ["value", "rating", "score", "amount", "quantity", "level", "range"]
        if any(term in (resource_id + content_desc) for term in value_terms):
            return "Value Selection"

        # Settings sliders
        settings_terms = ["setting", "brightness", "opacity", "transparency", "size", "zoom", "scale"]
        if any(term in (resource_id + content_desc) for term in settings_terms):
            return "Setting"

        # Default
        return "Adjustment"  # Generic adjustment slider

    def _infer_validation_rules(self, node: Node, widget) -> str:
        """
        Infer validation rules for an input field.

        Args:
            node: The input node
            widget: Associated widget from static analysis

        Returns:
            Validation rule description
        """
        # Start with empty validation info
        validation_info = ""

        # Check if field appears to be required
        resource_id = node.resource_id.lower() if hasattr(node, 'resource_id') and node.resource_id else ""
        hint = node.hint.lower() if hasattr(node, 'hint') and node.hint else ""

        if "required" in resource_id or "required" in hint or "*" in hint:
            validation_info += " (required)"

        # Add input type specific validation expectations
        input_type = self._analyze_input_type(node)

        if input_type == "email address":
            validation_info += " [expects valid email format]"
        elif input_type == "password":
            validation_info += " [may have password requirements]"
        elif input_type == "phone number":
            validation_info += " [expects numeric format]"
        elif input_type == "URL":
            validation_info += " [expects valid URL format]"
        elif input_type == "numeric field":
            validation_info += " [expects numbers only]"

        return validation_info

    def _with_text(self, node: Node) -> str:
        """
        Format node text description with additional detail.

        Args:
            node: The node to describe

        Returns:
            Formatted text description
        """
        if not hasattr(node, 'view_text') or not node.view_text:
            return "with no text"

        text = node.view_text

        # Add truncation indicator for long text
        if len(text) > 50:
            return f"with text '{text[:50]}...' (truncated)"

        return f"with text '{text}'"

    def _has_focus(self, node: Node) -> str:
        """
        Format node focus description with additional context.

        Args:
            node: The node to describe

        Returns:
            Formatted focus description
        """
        if not hasattr(node, 'focused'):
            return ""

        return " that is currently focused" if node.focused else ""

    def _with_description(self, node: Node) -> str:
        """
        Format node content description with additional detail.

        Args:
            node: The node to describe

        Returns:
            Formatted content description
        """
        if not hasattr(node, 'content_description') or not node.content_description:
            return ""

        content_desc = node.content_description

        # Add truncation indicator for long descriptions
        if len(content_desc) > 50:
            return f" with description '{content_desc[:50]}...' (truncated)"

        return f" with description '{content_desc}'"

    def _with_resource_id(self, node: Node) -> str:
        """
        Format node resource ID with additional context.

        Args:
            node: The node to describe

        Returns:
            Formatted resource ID description
        """
        if not hasattr(node, 'resource_id') or not node.resource_id:
            return ""

        resource_id = node.resource_id

        # Extract just the ID part for clarity
        if "/" in resource_id:
            parts = resource_id.split("/")
            if len(parts) > 1:
                return f" (id: {parts[1]})"

        return f" (id: {resource_id})"
# rvandroid/parser/screen/visitor/generic_visitor.py

from typing import List, Optional, Set

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType  # Import the enum
from rv_android_core.parser.screen.visitor.model import ItemAction, ScreenItem, Node


# TODO deprecated
class GenericScreenVisitor:  # (AbstractScreenVisitor):
    """
    Generic implementation of screen visitor for processing UI hierarchies.

    ### Architectural Decisions:
    - Implements a robust visitor pattern for UI element traversal
    - Provides specialized handling for different UI element types
    - Filters system navigation elements to focus on app UI
    - Includes consistent action generation for all interactive elements
    - Supports security-sensitive operation detection

    ### Role in the System:
    - Processes UI elements to generate actionable screen descriptions
    - Enables interaction with all types of Android UI components
    - Provides standardized action generation across UI types
    - Filters system elements to improve testing efficiency
    """

    def __init__(self, static_data: Optional[StaticAnalysisData], activity: str):
        """
        Initialize the generic screen visitor.

        Args:
            static_data: Optional static analysis data
            activity: Current activity name
        """
        super().__init__(static_data, activity)

        # Track processed elements to avoid duplicates
        self.processed_elements: Set[str] = set()

        # Element action generators
        self.action_generators = {
            "android.widget.Button": self._create_button_actions,
            "android.widget.ImageButton": self._create_button_actions,
            "android.widget.EditText": self._create_text_field_actions,
            "android.widget.TextView": self._create_text_view_actions,
            "android.widget.CheckBox": self._create_checkbox_actions,
            "android.widget.RadioButton": self._create_radio_button_actions,
            "android.widget.Spinner": self._create_spinner_actions,
            "android.widget.ListView": self._create_list_view_actions,
            "android.widget.RecyclerView": self._create_recycler_view_actions,
        }

    def visit(self, node: Node) -> None:
        """
        Visit a node in the UI hierarchy.

        Args:
            node: Node to process
        """
        # Skip already visited nodes
        node_id = node.get_unique_id()
        if node_id in self.visited_nodes:
            return

        # Skip system navigation buttons
        if self.should_exclude_system_button(node):
            self.logger.debug(f"Excluding system navigation button: {node}")
            return

        # Process node based on its class
        class_name = node.view_class

        # Find the appropriate action generator
        action_generator = None
        for class_pattern, generator in self.action_generators.items():
            if class_pattern in class_name:
                action_generator = generator
                break

        # Use default generator if no specific one found
        if not action_generator and node.actionable:
            action_generator = self._create_default_actions

        # Generate actions and create item
        if action_generator:
            actions = action_generator(node)
            if actions:
                description = self._create_element_description(node)
                item = ScreenItem(node.data, description, actions)
                self.items.append(item)
                self.visited_nodes.add(node_id)
                self.window_info["interactive_elements"] += 1

    def _create_element_description(self, node: Node) -> str:
        """
        Create a human-readable description of an element.

        Args:
            node: UI node

        Returns:
            Element description string
        """
        element_type = node.view_class.split('.')[-1]

        # Use content description or text if available
        if node.content_description:
            return f"{element_type} with description '{node.content_description}'"
        elif node.view_text:
            return f"{element_type} with text '{node.view_text}'"
        elif node.resource_id:
            return f"{element_type} with ID '{node.resource_id}'"
        else:
            return f"{element_type} at {node.bounds}"

    def _create_default_actions(self, node: Node) -> List[ItemAction]:
        """
        Create default actions for an actionable element.

        Args:
            node: UI node

        Returns:
            List of possible actions
        """
        return self.get_possible_actions(node, self.counter)

    def _create_button_actions(self, node: Node) -> List[ItemAction]:
        """
        Create actions for a button element.

        Args:
            node: Button node

        Returns:
            List of button actions
        """
        actions = []

        # Add click action
        if node.clickable:
            action_id = self.counter.inc()
            actions.append(ItemAction(
                id=action_id,
                text=f"CLICK ({action_id})",
                event=WidgetEventType.CLICK,
                target_view=node.data,
                coordinates=node.get_center_coordinates()
            ))

        # Add long-click action
        if node.long_clickable:
            action_id = self.counter.inc()
            actions.append(ItemAction(
                id=action_id,
                text=f"LONG_CLICK ({action_id})",
                event=WidgetEventType.LONG_CLICK,
                target_view=node.data,
                coordinates=node.get_center_coordinates()
            ))

        # Update security information
        for action in actions:
            self._update_action_mop_related_info(action, node)

        return actions

    def _create_text_field_actions(self, node: Node) -> List[ItemAction]:
        """
        Create actions for a text field element.

        Args:
            node: Text field node

        Returns:
            List of text field actions
        """
        actions = []

        # Add text input action
        action_id = self.counter.inc()
        actions.append(ItemAction(
            id=action_id,
            text=f"SET_TEXT ({action_id})",
            event=WidgetEventType.TEXT_CHANGE,
            target_view=node.data,
            coordinates=node.get_center_coordinates()
        ))

        # Add click action
        if node.clickable:
            action_id = self.counter.inc()
            actions.append(ItemAction(
                id=action_id,
                text=f"CLICK ({action_id})",
                event=WidgetEventType.CLICK,
                target_view=node.data,
                coordinates=node.get_center_coordinates()
            ))

        # Update security information
        for action in actions:
            self._update_action_mop_related_info(action, node)

        return actions

    def _create_text_view_actions(self, node: Node) -> List[ItemAction]:
        """
        Create actions for a text view element.

        Args:
            node: Text view node

        Returns:
            List of text view actions
        """
        # Only create actions if the text view is clickable
        if node.clickable or node.long_clickable:
            return self._create_default_actions(node)
        return []

    def _create_checkbox_actions(self, node: Node) -> List[ItemAction]:
        """
        Create actions for a checkbox element.

        Args:
            node: Checkbox node

        Returns:
            List of checkbox actions
        """
        actions = []

        # Add check/uncheck action based on current state
        if node.checkable:
            action_id = self.counter.inc()
            if node.checked:
                actions.append(ItemAction(
                    id=action_id,
                    text=f"UNCHECK ({action_id})",
                    event=WidgetEventType.CLICK,
                    target_view=node.data,
                    coordinates=node.get_center_coordinates()
                ))
            else:
                actions.append(ItemAction(
                    id=action_id,
                    text=f"CHECK ({action_id})",
                    event=WidgetEventType.CLICK,
                    target_view=node.data,
                    coordinates=node.get_center_coordinates()
                ))

        # Update security information
        for action in actions:
            self._update_action_mop_related_info(action, node)

        return actions

    def _create_radio_button_actions(self, node: Node) -> List[ItemAction]:
        """
        Create actions for a radio button element.

        Args:
            node: Radio button node

        Returns:
            List of radio button actions
        """
        # Radio buttons only need click actions
        if node.clickable and not node.checked:
            action_id = self.counter.inc()
            action = ItemAction(
                id=action_id,
                text=f"SELECT ({action_id})",
                event=WidgetEventType.CLICK,
                target_view=node.data,
                coordinates=node.get_center_coordinates()
            )
            self._update_action_mop_related_info(action, node)
            return [action]
        return []

    def _create_spinner_actions(self, node: Node) -> List[ItemAction]:
        """
        Create actions for a spinner element.

        Args:
            node: Spinner node

        Returns:
            List of spinner actions
        """
        actions = []

        # Add spinner click action
        if node.clickable:
            action_id = self.counter.inc()
            actions.append(ItemAction(
                id=action_id,
                text=f"CLICK_SPINNER ({action_id})",
                event=WidgetEventType.CLICK,
                target_view=node.data,
                coordinates=node.get_center_coordinates()
            ))

        # Update security information
        for action in actions:
            self._update_action_mop_related_info(action, node)

        return actions

    def _create_list_view_actions(self, node: Node) -> List[ItemAction]:
        """
        Create actions for a list view element.

        Args:
            node: List view node

        Returns:
            List of list view actions
        """
        actions = []

        # Add scroll actions
        if node.scrollable:
            # Add scroll UP action
            action_id = self.counter.inc()
            actions.append(ItemAction(
                id=action_id,
                text=f"SCROLL UP ({action_id})",
                event=WidgetEventType.SCROLL,
                target_view=node.data,
                coordinates=node.get_center_coordinates()
            ))

            # Add scroll DOWN action
            action_id = self.counter.inc()
            actions.append(ItemAction(
                id=action_id,
                text=f"SCROLL DOWN ({action_id})",
                event=WidgetEventType.SCROLL,
                target_view=node.data,
                coordinates=node.get_center_coordinates()
            ))

        # Update security information
        for action in actions:
            self._update_action_mop_related_info(action, node)

        return actions

    def _create_recycler_view_actions(self, node: Node) -> List[ItemAction]:
        """
        Create actions for a recycler view element.

        Args:
            node: Recycler view node

        Returns:
            List of recycler view actions
        """
        # RecyclerView usually needs the same actions as ListView
        return self._create_list_view_actions(node)

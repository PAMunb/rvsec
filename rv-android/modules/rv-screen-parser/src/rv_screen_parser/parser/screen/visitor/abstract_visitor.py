# rvandroid/parser/screen/visitor/abstract_visitor.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Set

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType, Widget
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenItem, ScreenDescription, Counter, Node


class AbstractScreenVisitor(ABC):
    """
    Abstract base visitor implementation for processing Android UI elements.
    Uses a more generic approach with registered handlers for different element types.
    """

    def __init__(self, static_info: Optional[StaticAnalysisData], activity: str):
        """
        Initialize the visitor.

        Args:
            static_info: Static analysis data (optional)
            activity: Current activity name
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "parser.screen.visitor",
            {
                CONTEXT_COMPONENT: "AbstractScreenVisitor"
            }
        )
        self.static_info = static_info
        self.activity = activity
        self.window = None

        # System navigation bounds
        self.system_navigation_bounds = {}

        # Device info
        self.device_info = {}

        # Initialize window info if static info is available
        if static_info and static_info.windows:
            self.window = static_info.windows.get_window(activity)

        self.counter = Counter()
        self.items: List[ScreenItem] = []
        self.visited_nodes: Set[str] = set()  # Track visited nodes to avoid duplicates
        self.window_info: Dict = {
            "total_widgets": 0,
            "matched_widgets": 0,
            "interactive_elements": 0
        }

    def get_screen_description(self) -> ScreenDescription:
        """
        Create and return a complete screen description.

        Returns:
            ScreenDescription object containing all parsed items
        """
        # Create a screen description with items
        return ScreenDescription(self.activity, self.items)

    # deprecated
    def visit(self, node: Node) -> None:
        """
        Visit a node in the UI hierarchy - simplified generic method.
        Finds the appropriate handler for the node type and processes it.

        Args:
            node: Node to process
        """
        # Skip already visited nodes
        node_id = node.unique_identifier
        if node_id in self.visited_nodes:
            return

        # Skip system navigation buttons
        if self.should_exclude_system_button(node):
            self.logger.debug(f"Excluding system navigation button: {node}")
            return

        if not node.children:
            self.visit_node(node)
        else:
            self.visit_leaf_node(node)

    def find_matching_widget(self, node_data: Dict) -> Optional[Widget]:
        """
        Find a matching widget in the static data based on various strategies.

        Args:
            node_data: Node data dictionary

        Returns:
            Widget if found, None otherwise
        """
        resource_id = node_data.get("resource_id", "")
        if not resource_id or not self.window:
            return None

        # Try by resource ID
        parts = resource_id.split("/")
        widget_id = parts[-1] if len(parts) > 1 else parts[0]

        self.logger.debug(f"Looking for widget by resource ID: {widget_id}")
        widget = self.window.get_widget_by_name(widget_id)
        if widget:
            self.window_info["matched_widgets"] += 1
            return widget

        # Try by text content
        text = node_data.get("text", "")
        if text:
            self.logger.debug(f"Looking for widget by text: {text}")
            for widget_id, widget in self.window.widgets.items():
                if widget.text == text:
                    self.window_info["matched_widgets"] += 1
                    return widget

        return None

    def is_parent_clickable(self, node: Node) -> bool:
        """
        Check if any parent of this node is clickable.

        Args:
            node: Current node

        Returns:
            True if a parent is clickable, False otherwise
        """
        parent = node.parent
        while parent:
            if parent.clickable:
                return True
            parent = parent.parent
        return False

    def _check_method_reaches_mop(self, signature: str) -> bool:
        """
        Check if a method reaches MOP (Method of Protection).

        Args:
            signature: Method signature to check

        Returns:
            True if method reaches MOP, False otherwise
        """
        if self.static_info and self.static_info.classes:
            method = self.static_info.classes.methods.get(signature)
            if method:
                return method.reaches_mop
        return False

    def _check_method_directly_reaches_mop(self, signature: str) -> bool:
        """
        Check if a method directly reaches MOP.

        Args:
            signature: Method signature to check

        Returns:
            True if method directly reaches MOP, False otherwise
        """
        if self.static_info and self.static_info.classes:
            method = self.static_info.classes.methods.get(signature)
            if method:
                return method.directly_reaches_mop
        return False

    def should_exclude_system_button(self, node: Node) -> bool:
        """
        Determine if a node represents a system navigation button or keyboard key that should be excluded.

        Args:
            node: UI node to check

        Returns:
            True if the node should be excluded from testing
        """
        # Check for resource IDs related to navigation buttons
        resource_id = node.resource_id or ""

        # Common resource IDs for system navigation buttons
        system_button_ids = [
            "home", "recent", "recents", "back", "back_button",
            "navigation_bar", "nav_bar", "navbar_view",
            "com.android.systemui:id/home",
            "com.android.systemui:id/recent_apps",
            "com.android.systemui:id/back"
        ]

        # Check if resource ID contains any system button pattern
        if any(btn_id in resource_id.lower() for btn_id in system_button_ids):
            return True

        # Check for packages associated with system UI or keyboards
        package = node.package or ""
        keyboard_packages = [
            "com.android.inputmethod",
            "com.google.android.inputmethod",
            "android.inputmethodservice",
            "com.samsung.android.keyboardsettings",
            "com.android.systemui"
        ]

        if any(kbd_pkg in package.lower() for kbd_pkg in keyboard_packages):
            return True

        # Check for common keyboard class names
        class_name = node.view_class or ""
        keyboard_classes = [
            "Keyboard", "KeyboardView", "KeyboardViewCluster",
            "SoftKeyboard", "SoftKeyboardView", "KeyboardLayout",
            "KeyButton", "KeyboardButtonCluster"
        ]

        if any(kbd_cls.lower() in class_name.lower() for kbd_cls in keyboard_classes):
            return True

        # Check if the node is in the system navigation area based on bounds
        if hasattr(self, 'system_navigation_bounds') and self.system_navigation_bounds.get("present", False):
            bounds = node.bounds
            if bounds and len(bounds) == 2:
                # Check if the node is entirely in the navigation area
                bottom_y = bounds[1][1]  # Bottom Y coordinate
                top_y = bounds[0][1]  # Top Y coordinate

                nav_top = self.system_navigation_bounds.get("top", 0)
                if top_y >= nav_top:
                    return True

        # Check for keyboard pattern: small buttons in bottom half of screen
        if hasattr(self, 'device_info') and self.device_info:
            display_height = self.device_info.get("displayHeight", 0)
            if display_height > 0:
                bounds = node.bounds
                if bounds and len(bounds) == 2:
                    # Keyboard keys are typically small buttons in the bottom half of the screen
                    width = bounds[1][0] - bounds[0][0]
                    height = bounds[1][1] - bounds[0][1]
                    center_y = (bounds[0][1] + bounds[1][1]) / 2

                    # Check if it's a small button in the bottom half of the screen
                    if (width < 100 and height < 100 and
                            center_y > display_height * 0.5):

                        # Additional check for keyboard key: look for single character text
                        text = node.view_text or ""
                        if len(text) <= 2:  # Single character or special keys
                            return True

        # Check based on common descriptions for system buttons
        content_desc = (node.content_description or "").lower()
        if any(desc in content_desc for desc in ["home", "recent apps", "overview", "go back"]):
            return True

        # Check "soft buttons" identifier
        if "soft" in class_name.lower() and "button" in class_name.lower():
            return True

        return False

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
                    id=counter.increment(),
                    text=f"UNCHECK ({counter.get_current()})",
                    event=WidgetEventType.CLICK,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view=node_data,
                    coordinates=coordinates
                )
                # Update security information
                self._update_action_mop_related_info(action, node)
                actions.append(action)
            else:
                action = ItemAction(
                    id=counter.increment(),
                    text=f"CHECK ({counter.get_current()})",
                    event=WidgetEventType.CLICK,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view=node_data,
                    coordinates=coordinates
                )
                self._update_action_mop_related_info(action, node)
                actions.append(action)

        # Handle click actions
        elif (node.clickable or inherit_click) and not (prioritize_check and node.checkable):
            text_suffix = ""
            if node.view_text:
                text_suffix = f" on '{node.view_text[:30]}'{' (truncated)' if len(node.view_text) > 30 else ''}"

            action = ItemAction(
                id=counter.increment(),
                text=f"CLICK ({counter.get_current()})",
                # text=f"CLICK ({counter.get_current()}){text_suffix}",
                event=WidgetEventType.CLICK,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view=node_data,
                coordinates=coordinates
            )
            self._update_action_mop_related_info(action, node)
            actions.append(action)

        # Handle long click actions
        if node.long_clickable:
            if "EditText" not in node.view_class and "TextView" not in node.view_class:
                text_suffix = ""
                if node.view_text:
                    text_suffix = f" on '{node.view_text[:30]}'{' (truncated)' if len(node.view_text) > 30 else ''}"

                action = ItemAction(
                    id=counter.increment(),
                    text=f"LONG_CLICK ({counter.get_current()}){text_suffix}",
                    event=WidgetEventType.LONG_CLICK,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view=node_data,
                    coordinates=coordinates
                )
                self._update_action_mop_related_info(action, node)
                actions.append(action)

        # Handle check/uncheck actions with normal priority
        if not prioritize_check and node.checkable:
            if node.checked:
                action = ItemAction(
                    id=counter.increment(),
                    text=f"UNCHECK ({counter.get_current()})",
                    event=WidgetEventType.CLICK,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view=node_data,
                    coordinates=coordinates
                )
                self._update_action_mop_related_info(action, node)
                actions.append(action)
            else:
                action = ItemAction(
                    id=counter.increment(),
                    text=f"CHECK ({counter.get_current()})",
                    event=WidgetEventType.CLICK,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view=node_data,
                    coordinates=coordinates
                )
                self._update_action_mop_related_info(action, node)
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
                    id=counter.increment(),
                    text=f"SCROLL {direction} ({counter.get_current()})",
                    event=WidgetEventType.SCROLL,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view=node_data,
                    coordinates=coordinates
                )
                self._update_action_mop_related_info(action, node)
                actions.append(action)

        # Handle text input actions with better hints
        if node.editable:
            action = ItemAction(
                id=counter.increment(),
                text=f"SET_TEXT ({counter.get_current()})",
                event=WidgetEventType.TEXT_CHANGE,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view=node_data,
                coordinates=coordinates
            )
            self._update_action_mop_related_info(action, node)
            actions.append(action)

        return actions

    def _update_action_mop_related_info(self, action: ItemAction, node: Node) -> None:
        """
        Update an action with monitored operations information from static analysis.

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
                if action.reaches_mop or action.directly_reaches_mop:
                    self.logger.debug(
                        f"Action {action.id} security info updated: reaches_mop={action.reaches_mop}, directly_reaches_mop={action.directly_reaches_mop}")
                    if action.directly_reaches_mop:
                        action.text += " [DM]"
                    elif action.reaches_mop:
                        action.text += " [M]"
                return

    @abstractmethod
    def visit_node(self, node: Node) -> None:
        """
        Visit a container node in the UI hierarchy.
        Process container with extensive details and track hierarchy depth.

        Args:
            node: The node to visit
        """
        pass

    @abstractmethod
    def visit_leaf_node(self, node: Node) -> None:
        """
        Visit a leaf node in the UI hierarchy with detailed information.

        Args:
            node: The leaf node to visit
        """
        pass

    @abstractmethod
    def visit_button(self, node: Node) -> None:
        """
        Visit a button element and generate its description.

        Args:
            node: The button node to visit
        """
        pass

    @abstractmethod
    def visit_edit_text(self, node: Node) -> None:
        """
        Visit an editable text field with detailed information.

        Args:
            node: The edit text node to visit
        """
        pass

    @abstractmethod
    def visit_text_view(self, node: Node) -> None:
        """
        Visit a text view element with detailed information.

        Args:
            node: The text view node to visit
        """
        pass

    @abstractmethod
    def visit_checkbox(self, node: Node) -> None:
        """
        Visit a checkbox element with detailed information.

        Args:
            node: The checkbox node to visit
        """
        pass

    @abstractmethod
    def visit_checked_text(self, node: Node) -> None:
        """
        Visit a checked text view element with detailed information.

        Args:
            node: The checked text view node to visit
        """
        pass

    @abstractmethod
    def visit_toggle_button(self, node: Node) -> None:
        """
        Visit a toggle button with detailed information.

        Args:
            node: The toggle button node to visit
        """
        pass

    @abstractmethod
    def visit_switch(self, node: Node) -> None:
        """
        Visit a switch element with detailed information.

        Args:
            node: The switch node to visit
        """
        pass

    @abstractmethod
    def visit_image_button(self, node: Node) -> None:
        """
        Visit an image button with detailed information.

        Args:
            node: The image button node to visit
        """
        pass

    @abstractmethod
    def visit_image(self, node: Node) -> None:
        """
        Visit an image element with detailed information.

        Args:
            node: The image node to visit
        """
        pass

    @abstractmethod
    def visit_radio_button(self, node: Node) -> None:
        """
        Visit a radio button with detailed information.

        Args:
            node: The radio button node to visit
        """
        pass

    @abstractmethod
    def visit_radio_group(self, node: Node) -> None:
        """
        Visit a radio group element with detailed information.

        Args:
            node: The radio group node to visit
        """
        pass

    @abstractmethod
    def visit_spinner(self, node: Node) -> None:
        """
        Visit a spinner element with detailed information.

        Args:
            node: The spinner node to visit
        """
        pass

    @abstractmethod
    def visit_slider(self, node: Node) -> None:
        """
        Visit a slider (SeekBar) element with detailed information.

        Args:
            node: The slider node to visit
        """
        pass

    def _with_text(self, node: Node, max_length: int = 50) -> str:
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
        if len(text) > max_length:
            return f"with text '{text[:max_length]}...' (truncated)"

        return f"with text '{text}'"

    def _with_field(self, widget: Widget):
        if widget is None or not hasattr(widget, 'field') or not widget.field:
            return ""

        return "is assigned to a field"

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

    def _with_description(self, node: Node, max_length: int = 50) -> str:
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
        if len(content_desc) > max_length:
            return f" with description '{content_desc[:max_length]}...' (truncated)"

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

    def _with_hint(self, node: Node, max_length: int = 50) -> str:
        """
        Format node hint with additional detail.

        Args:
            node: The node to describe

        Returns:
            Formatted hint
        """
        if not hasattr(node, 'hint') or not node.hint:
            return ""

        hint = node.hint

        # Add truncation indicator for long descriptions
        if len(hint) > max_length:
            return f" with hint '{hint[:max_length]}...' (truncated)"

        return f" with hint '{hint}'"

"""Abstract base visitor for processing Android UI hierarchy elements.

Defines the visitor pattern contract for traversing Android UI trees parsed from
UIAutomator or DroidBot dumps. Concrete visitors produce different output formats
(basic, default, enhanced) while sharing common logic for action generation,
system button filtering, and MOP (Monitored Operations) tracking.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import Widget, WidgetEventType
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_screen_parser.parser.screen.visitor.model import (
    Counter,
    ItemAction,
    Node,
    ScreenDescription,
    ScreenItem,
)

# UIAutomator dumps often report clickable=false for elements that are in fact
# interactive (especially custom views and Material Design components). This set
# overrides the clickable attribute for known-interactive types, preventing the
# visitor from silently dropping valid actions. Entries include both simple class
# names and fully-qualified names because UIAutomator inconsistently reports either.
ALWAYS_CLICKABLE_TYPES = {
    # Standard Android Tabs
    "ActionBar$Tab",
    "Tab",
    "TabLayout",
    "TabView",
    # Navigation Components
    "NavigationBarView",
    "BottomNavigationItemView",
    "NavigationRailView",
    # Menu Items
    "ActionMenuItemView",
    "MenuItemView",
    "OverflowMenuButton",
    # Material Design Components
    "Chip",
    "com.google.android.material.chip.Chip",
    "com.google.android.material.tabs.TabItem",
    "com.google.android.material.tabs.TabLayout$TabView",
    "com.google.android.material.bottomnavigation.BottomNavigationItemView",
    "com.google.android.material.navigation.NavigationBarItemView",
    "com.google.android.material.floatingactionbutton.FloatingActionButton",
    # AndroidX Components
    "androidx.appcompat.widget.ActionMenuView",
    "androidx.appcompat.view.menu.ActionMenuItemView",
}


class AbstractScreenVisitor(ABC):
    """Abstract base visitor for processing Android UI hierarchy elements.

    ### Architectural Decisions:
    - Uses the visitor pattern to decouple UI tree traversal from description
      generation, allowing multiple output formats from the same tree structure.
    - Centralizes action generation logic (click, long-click, scroll, text input,
      check/uncheck, drag) so concrete visitors only handle description formatting.
    - Integrates with static analysis data to annotate actions with MOP reachability,
      enabling prioritized exploration of specification-relevant UI paths.

    ### Role in the System:
    - Base class for all screen visitors (BasicTextVisitor, DefaultTextVisitor,
      EnhancedTextVisitor) providing shared traversal and action logic.
    - Consumed by screen parsers (UIAutomator2Parser, DroidBotParser) which build
      the Node tree and dispatch it through the visitor.
    - Produces ScreenDescription objects consumed by rv-agent for action selection
      and by rv-platform for coverage tracking.

    ### Key Features:
    - System button and keyboard filtering to exclude non-app UI elements.
    - ALWAYS_CLICKABLE_TYPES set for elements that are interactive regardless of
      the clickable attribute in UIAutomator dumps (tabs, navigation items, chips).
    - Widget matching against static analysis data for MOP annotation.
    - Coordinate extraction for precise action targeting.

    ### Integration Points:
    - StaticAnalysisData: provides window/widget info for MOP tracking.
    - Node: the UI tree element that accepts this visitor.
    - ScreenDescription/ScreenItem/ItemAction: the output model consumed downstream.
    """

    def __init__(self, static_info: Optional[StaticAnalysisData], activity: str):
        """Initialize the visitor with static analysis context and activity name.

        Args:
            static_info: Static analysis data for MOP tracking and widget matching.
                When None, MOP annotations are skipped.
            activity: Fully qualified Android activity name for the current screen.

        State:
            counter: Sequential ID generator for action identifiers.
            items: Accumulated ScreenItem list built during traversal.
            visited_nodes: Set of node unique identifiers to prevent duplicate processing.
            window_info: Running statistics (total/matched widgets, interactive elements).
            window: Resolved GATOR window for the current activity, if available.
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_screen_parser.parser.screen.visitor",
            {CONTEXT_COMPONENT: "AbstractScreenVisitor"},
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
            "interactive_elements": 0,
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

        # Android resource IDs use "package:type/name" format (e.g.,
        # "com.example:id/btn_submit"). GATOR stores only the name part
        # ("btn_submit") in Widget.name, so we strip the prefix before matching.
        parts = resource_id.split("/")
        widget_name = parts[-1] if len(parts) > 1 else parts[0]

        widget = self.window.get_widget_by_name(widget_name)
        if widget:
            self.window_info["matched_widgets"] += 1
            return widget

        # Try by text content
        text = node_data.get("text", "")
        if text:
            for wid, widget in self.window.widgets.items():
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

    def is_always_clickable_type(self, node: Node) -> bool:
        """
        Check if the node's class type is inherently clickable.

        Some UI elements like ActionBar$Tab are clickable but may not have
        the clickable attribute set to true in UIAutomator dump.

        Args:
            node: Current node

        Returns:
            True if the node type is always clickable, False otherwise
        """
        if not node.view_class:
            return False

        # Check exact match
        class_name = node.view_class.split(".")[-1]  # Get simple class name
        if class_name in ALWAYS_CLICKABLE_TYPES:
            return True

        # Check partial match for nested classes (e.g., ActionBar$Tab)
        for clickable_type in ALWAYS_CLICKABLE_TYPES:
            if clickable_type in class_name:
                return True

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
        """Determine if a node represents a system navigation button or keyboard key.

        Filter out non-app UI elements that would produce meaningless actions during
        automated testing: system navigation bar buttons (home, back, recents),
        on-screen keyboard keys, and elements within the system navigation area.

        Uses multiple heuristics: resource ID patterns, package names, class names,
        bounds-based position checks, content descriptions, and small-button detection
        for keyboard keys.

        Args:
            node: UI node to check.

        Returns:
            True if the node should be excluded from the action space.
        """
        # Check for resource IDs related to navigation buttons
        resource_id = node.resource_id or ""

        # Common resource IDs for system navigation buttons
        system_button_ids = [
            "home",
            "recent",
            "recents",
            "back",
            "back_button",
            "navigation_bar",
            "nav_bar",
            "navbar_view",
            "com.android.systemui:id/home",
            "com.android.systemui:id/recent_apps",
            "com.android.systemui:id/back",
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
            "com.android.systemui",
        ]

        if any(kbd_pkg in package.lower() for kbd_pkg in keyboard_packages):
            return True

        # Check for common keyboard class names
        class_name = node.view_class or ""
        keyboard_classes = [
            "Keyboard",
            "KeyboardView",
            "KeyboardViewCluster",
            "SoftKeyboard",
            "SoftKeyboardView",
            "KeyboardLayout",
            "KeyButton",
            "KeyboardButtonCluster",
        ]

        if any(kbd_cls.lower() in class_name.lower() for kbd_cls in keyboard_classes):
            return True

        # Check if the node is in the system navigation area based on bounds
        if hasattr(
            self, "system_navigation_bounds"
        ) and self.system_navigation_bounds.get("present", False):
            bounds = node.bounds
            if bounds and len(bounds) == 2:
                # Check if the node is entirely in the navigation area
                bottom_y = bounds[1][1]  # Bottom Y coordinate
                top_y = bounds[0][1]  # Top Y coordinate

                nav_top = self.system_navigation_bounds.get("top", 0)
                if top_y >= nav_top:
                    return True

        # Heuristic for on-screen keyboard keys: small buttons (< 100x100 px) in
        # the bottom half of the screen with single-character text. This catches
        # custom keyboards that do not set a recognizable package or class name.
        if hasattr(self, "device_info") and self.device_info:
            display_height = self.device_info.get("displayHeight", 0)
            if display_height > 0:
                bounds = node.bounds
                if bounds and len(bounds) == 2:
                    # Keyboard keys are typically small buttons in the bottom half of the screen
                    width = bounds[1][0] - bounds[0][0]
                    height = bounds[1][1] - bounds[0][1]
                    center_y = (bounds[0][1] + bounds[1][1]) / 2

                    # Check if it's a small button in the bottom half of the screen
                    if width < 100 and height < 100 and center_y > display_height * 0.5:

                        # Additional check for keyboard key: look for single character text
                        text = node.view_text or ""
                        if len(text) <= 2:  # Single character or special keys
                            return True

        # Check based on common descriptions for system buttons
        content_desc = (node.content_description or "").lower()
        if any(
            desc in content_desc
            for desc in ["home", "recent apps", "overview", "go back"]
        ):
            return True

        # Check "soft buttons" identifier
        if "soft" in class_name.lower() and "button" in class_name.lower():
            return True

        return False

    def get_possible_actions(
        self,
        node: Node,
        counter: Counter,
        inherit_click: bool = False,
        prioritize_check: bool = False,
    ) -> List[ItemAction]:
        """Generate all possible actions for a UI node based on its properties.

        Inspects node attributes (clickable, long_clickable, checkable, scrollable,
        editable) and the ALWAYS_CLICKABLE_TYPES set to build a complete action list.
        Each action is annotated with MOP reachability from static analysis when
        available.

        Args:
            node: The UI node to generate actions for.
            counter: Counter for generating unique sequential action IDs.
            inherit_click: When True, add a click action even if the node itself
                is not clickable (used for leaf nodes whose parent is clickable).
            prioritize_check: When True, generate CHECK/UNCHECK actions instead of
                CLICK for checkable nodes (used for checkboxes, switches, toggles).

        Returns:
            List of ItemAction instances, each with coordinates, event type, and
            MOP annotations. Empty list if the node has no interactive properties.
        """
        actions = []

        # Store the node data for later use in the ItemAction
        node_data = node.data

        # Extract coordinates from node
        coordinates = None
        if hasattr(node, "center_coordinates"):
            coordinates = node.center_coordinates
        elif "bounds" in node_data:
            bounds = node_data["bounds"]
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                coordinates = (x, y)

        # When prioritize_check is True, checkable nodes get CHECK/UNCHECK instead
        # of CLICK. This prevents checkboxes and switches from being treated as
        # plain buttons, which would lose semantic information for the LLM agent.
        if prioritize_check and node.checkable:
            if node.checked:
                action = ItemAction(
                    id=counter.increment(),
                    text=f"UNCHECK ({counter.get_current()})",
                    event=WidgetEventType.CLICK,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view=node_data,
                    coordinates=coordinates,
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
                    coordinates=coordinates,
                )
                self._update_action_mop_related_info(action, node)
                actions.append(action)

        # Editable elements get TEXT_CHANGE (not CLICK) because clicking an EditText
        # just focuses it -- the meaningful action is typing. ALWAYS_CLICKABLE_TYPES
        # overrides clickable=false for known-interactive widgets (tabs, chips, FABs).
        elif (
            (node.clickable or inherit_click or self.is_always_clickable_type(node))
            and not (prioritize_check and node.checkable)
            and not node.editable
        ):
            text_suffix = ""
            if node.view_text:
                text_suffix = f" on '{node.view_text[:30]}'{' (truncated)' if len(node.view_text) > 30 else ''}"

            action = ItemAction(
                id=counter.increment(),
                text=f"CLICK ({counter.get_current()})",
                event=WidgetEventType.CLICK,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view=node_data,
                coordinates=coordinates,
            )
            self._update_action_mop_related_info(action, node)
            actions.append(action)

        # Long-click on EditText/TextView triggers text selection, not a meaningful
        # app action, so we exclude those to avoid polluting the action space.
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
                    coordinates=coordinates,
                )
                self._update_action_mop_related_info(action, node)
                actions.append(action)

        # Handle check/uncheck actions with normal priority
        if not prioritize_check and node.checkable:
            self.create_checked_action(actions, coordinates, counter, node, node_data)

        # Generate scroll actions. We restrict directions by widget type to avoid
        # producing impossible actions (e.g., horizontal scroll on a ListView).
        # Unknown scrollable types get all four directions as a safe default.
        if node.scrollable:
            directions = ["UP", "DOWN", "LEFT", "RIGHT"]

            if node.view_class in [
                "android.widget.ListView",
                "android.widget.ScrollView",
            ]:
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
                    coordinates=coordinates,
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
                coordinates=coordinates,
            )
            self._update_action_mop_related_info(action, node)
            actions.append(action)

        return actions

    def create_checked_action(self, actions, coordinates, counter, node, node_data):
        """Append a CHECK or UNCHECK action based on the node's checked state."""
        if node.checked:
            action = ItemAction(
                id=counter.increment(),
                text=f"UNCHECK ({counter.get_current()})",
                event=WidgetEventType.CLICK,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view=node_data,
                coordinates=coordinates,
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
                coordinates=coordinates,
            )
            self._update_action_mop_related_info(action, node)
            actions.append(action)

    def _update_action_mop_related_info(self, action: ItemAction, node: Node) -> None:
        """
        Update an action with monitored operations information from static analysis.

        Args:
            action: The action to update
            node: The node associated with the action
        """
        # Match the runtime UI node to a GATOR-analyzed widget via resource ID or text.
        # If matched, check whether the widget's event handler reaches a monitored
        # operation (MOP). This enables rv-agent to prioritize actions that trigger
        # specification-relevant code paths.
        widget = self.find_matching_widget(node.data)
        if not widget:
            return

        for event in widget.events:
            if event.type == action.event:
                # Check if method reaches or directly reaches MOP
                action.reaches_mop = self._check_method_reaches_mop(event.signature)
                action.directly_reaches_mop = self._check_method_directly_reaches_mop(
                    event.signature
                )
                action.widget_id = widget.id
                action.callback_signature = event.signature

                # Append MOP markers to the action text so the LLM can see them
                # in the screen description. [DM] = directly reaches a monitored
                # operation (one call away); [M] = transitively reaches one.
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

    @abstractmethod
    def visit_leaf_node(self, node: Node) -> None:
        """
        Visit a leaf node in the UI hierarchy with detailed information.

        Args:
            node: The leaf node to visit
        """

    @abstractmethod
    def visit_button(self, node: Node) -> None:
        """
        Visit a button element and generate its description.

        Args:
            node: The button node to visit
        """

    @abstractmethod
    def visit_edit_text(self, node: Node) -> None:
        """
        Visit an editable text field with detailed information.

        Args:
            node: The edit text node to visit
        """

    @abstractmethod
    def visit_text_view(self, node: Node) -> None:
        """
        Visit a text view element with detailed information.

        Args:
            node: The text view node to visit
        """

    @abstractmethod
    def visit_checkbox(self, node: Node) -> None:
        """
        Visit a checkbox element with detailed information.

        Args:
            node: The checkbox node to visit
        """

    @abstractmethod
    def visit_checked_text(self, node: Node) -> None:
        """
        Visit a checked text view element with detailed information.

        Args:
            node: The checked text view node to visit
        """

    @abstractmethod
    def visit_toggle_button(self, node: Node) -> None:
        """
        Visit a toggle button with detailed information.

        Args:
            node: The toggle button node to visit
        """

    @abstractmethod
    def visit_switch(self, node: Node) -> None:
        """
        Visit a switch element with detailed information.

        Args:
            node: The switch node to visit
        """

    @abstractmethod
    def visit_image_button(self, node: Node) -> None:
        """
        Visit an image button with detailed information.

        Args:
            node: The image button node to visit
        """

    @abstractmethod
    def visit_image(self, node: Node) -> None:
        """
        Visit an image element with detailed information.

        Args:
            node: The image node to visit
        """

    @abstractmethod
    def visit_radio_button(self, node: Node) -> None:
        """
        Visit a radio button with detailed information.

        Args:
            node: The radio button node to visit
        """

    @abstractmethod
    def visit_radio_group(self, node: Node) -> None:
        """
        Visit a radio group element with detailed information.

        Args:
            node: The radio group node to visit
        """

    @abstractmethod
    def visit_spinner(self, node: Node) -> None:
        """
        Visit a spinner element with detailed information.

        Args:
            node: The spinner node to visit
        """

    @abstractmethod
    def visit_slider(self, node: Node) -> None:
        """
        Visit a slider (SeekBar) element with detailed information.

        Args:
            node: The slider node to visit
        """

    def _with_text(self, node: Node, max_length: int = 50) -> str:
        """
        Format node text description with additional detail.

        Args:
            node: The node to describe

        Returns:
            Formatted text description
        """
        if not hasattr(node, "view_text") or not node.view_text:
            return "with no text"

        text = node.view_text

        # Add truncation indicator for long text
        if len(text) > max_length:
            return f"with text '{text[:max_length]}...' (truncated)"

        return f"with text '{text}'"

    def _with_field(self, widget: Widget):
        if widget is None or not hasattr(widget, "field") or not widget.field:
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
        if not hasattr(node, "focused"):
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
        if not hasattr(node, "content_description") or not node.content_description:
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
        if not hasattr(node, "resource_id") or not node.resource_id:
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
        if not hasattr(node, "hint") or not node.hint:
            return ""

        hint = node.hint

        # Add truncation indicator for long descriptions
        if len(hint) > max_length:
            return f" with hint '{hint[:max_length]}...' (truncated)"

        return f" with hint '{hint}'"

    def _with_position(self, node: Node) -> str:
        """
        Format node position coordinates for enhanced coordinate precision.

        ### Coordinate Precision Enhancement:
        Provides precise position information to improve LLM coordinate generation
        accuracy from 30% to 95-100% as specified in the refactoring plan.

        Args:
            node: The node to describe

        Returns:
            Formatted position string with coordinates
        """
        if not hasattr(node, "center_coordinates") or not node.center_coordinates:
            return ""

        x, y = node.center_coordinates
        return f" at position ({x}, {y})"

    def _with_bounds(self, node: Node) -> str:
        """
        Format node bounds information for coordinate validation.

        ### Bounds Information Strategy:
        Provides complete bounds information following the standardized format
        specified in the plan: [[x1,y1],[x2,y2]] for arrays.

        Args:
            node: The node to describe

        Returns:
            Formatted bounds string with coordinate arrays
        """
        if not hasattr(node, "bounds") or not node.bounds:
            return ""

        bounds = node.bounds
        if len(bounds) == 2:
            x1, y1 = bounds[0]
            x2, y2 = bounds[1]
            return f" - bounds[[{x1}, {y1}], [{x2}, {y2}]]"

        return ""

    def _with_complete_coordinates(self, node: Node) -> str:
        """
        Provide complete coordinate information combining position and bounds.

        ### Complete Coordinate Strategy:
        Implements the proposed format from the plan:
        "button 'OK' at position (540, 1306) - bounds[[200, 1270], [880, 1342]]"

        Args:
            node: The node to describe

        Returns:
            Complete coordinate description string
        """
        position_info = self._with_position(node)
        bounds_info = self._with_bounds(node)
        return position_info + bounds_info

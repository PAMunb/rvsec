from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import Widget, WidgetEventType
from rv_android_core.domain.window import Window, Windows
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_screen_parser.parser.screen.visitor.abstract_visitor import (
    AbstractScreenVisitor,
)
from rv_screen_parser.parser.screen.visitor.model import (
    ItemAction,
    Node,
    ScreenDescription,
    ScreenItem,
)


class MockScreenVisitor(AbstractScreenVisitor):
    """Mock implementation of AbstractScreenVisitor for testing"""

    def __init__(self, static_info, activity):
        """Override init to avoid the ScreenDescription default behavior"""
        super().__init__(static_info, activity)

    def get_screen_description(self) -> ScreenDescription:
        """Override to just return the items without adding a BACK action"""
        return ScreenDescription(self.activity, self.items)

    def visit_node(self, node: Node) -> None:
        """Mock implementation of visit_node"""

    def visit_leaf_node(self, node: Node) -> None:
        """Mock implementation of visit_leaf_node"""

    def visit_button(self, node: Node) -> None:
        """Mock implementation of visit_button"""

    def visit_edit_text(self, node: Node) -> None:
        """Mock implementation of visit_edit_text"""

    def visit_text_view(self, node: Node) -> None:
        """Mock implementation of visit_text_view"""

    def visit_checkbox(self, node: Node) -> None:
        """Mock implementation of visit_checkbox"""

    def visit_checked_text(self, node: Node) -> None:
        """Mock implementation of visit_checked_text"""

    def visit_toggle_button(self, node: Node) -> None:
        """Mock implementation of visit_toggle_button"""

    def visit_switch(self, node: Node) -> None:
        """Mock implementation of visit_switch"""

    def visit_image_button(self, node: Node) -> None:
        """Mock implementation of visit_image_button"""

    def visit_image(self, node: Node) -> None:
        """Mock implementation of visit_image"""

    def visit_radio_button(self, node: Node) -> None:
        """Mock implementation of visit_radio_button"""

    def visit_radio_group(self, node: Node) -> None:
        """Mock implementation of visit_radio_group"""

    def visit_spinner(self, node: Node) -> None:
        """Mock implementation of visit_spinner"""

    def visit_slider(self, node: Node) -> None:
        """Mock implementation of visit_slider"""


class TestAbstractScreenVisitor:
    """Test suite for AbstractScreenVisitor"""

    @pytest.fixture(autouse=True)
    def setup_logging(self):
        """Fixture to set up logging and suppress log messages during tests"""
        with patch(
            "rv_android_core.util.logging.manager.LoggingManager"
        ) as mock_logging_manager:
            mock_logger = MagicMock()
            mock_logging_manager.get_instance.return_value = mock_logging_manager
            mock_logging_manager.get_logger.return_value = mock_logger
            yield

    @pytest.fixture
    def static_data(self):
        """Fixture for static analysis data"""
        # Create mock classes
        mock_classes = MagicMock(spec=Classes)
        mock_classes.methods = {}

        # Create mock windows
        mock_windows = MagicMock(spec=Windows)

        # Create mock window transition graph
        mock_wtg = MagicMock(spec=WindowTransitionGraph)

        # Create mock StaticAnalysisData with the components
        mock_static_data = MagicMock(spec=StaticAnalysisData)
        mock_static_data.classes = mock_classes
        mock_static_data.windows = mock_windows
        mock_static_data.wtg = mock_wtg

        return mock_static_data

    @pytest.fixture
    def visitor(self, static_data):
        """Fixture for a concrete visitor instance"""
        # Create a mock activity
        activity = "com.example.TestActivity"

        # Setup mock window
        mock_window = None  # Initially window is None

        # Mock the get_window method to return None
        static_data.windows.get_window.return_value = None

        return MockScreenVisitor(static_data, activity)

    @pytest.fixture
    def node(self):
        """Fixture for a Node object"""
        # Create a mock node with basic properties
        data = {
            "class": "android.widget.Button",
            "resource_id": "test_button",
            "text": "Test Button",
            "content_description": "A test button",
            "clickable": True,
            "bounds": [[10, 10], [100, 50]],
            "enabled": True,
            "focused": False,
        }
        return Node(data)

    @pytest.fixture
    def parent_node(self):
        """Fixture for a parent Node object"""
        data = {
            "class": "android.widget.LinearLayout",
            "resource_id": "parent_layout",
            "clickable": True,
            "bounds": [[0, 0], [200, 100]],
        }
        return Node(data)

    def test_initialization(self, static_data):
        """Test visitor initialization"""
        activity = "com.example.TestActivity"

        # Mock the get_window method to return None
        static_data.windows.get_window.return_value = None

        visitor = MockScreenVisitor(static_data, activity)

        assert visitor.activity == activity
        assert visitor.static_info == static_data
        assert visitor.items == []
        assert visitor.counter.value == 0
        assert visitor.window_info["interactive_elements"] == 0
        assert visitor.window is None  # Window should be None until it's found

    def test_get_screen_description(self, visitor):
        """Test get_screen_description method"""
        # Add some test items
        item1 = ScreenItem({"id": "item1"}, "Item 1", [])
        item2 = ScreenItem({"id": "item2"}, "Item 2", [])
        visitor.items = [item1, item2]

        # The default implementation of get_screen_description returns a
        # ScreenDescription with just the items provided
        description = visitor.get_screen_description()

        assert isinstance(description, ScreenDescription)
        assert description.activity == visitor.activity
        # The base implementation should return exactly the items we provided
        assert len(description.items) == 2  # No back button is inserted anymore
        assert description.items[0] == item1
        assert description.items[1] == item2

    def test_find_matching_widget_no_window(self, visitor):
        """Test find_matching_widget method with no window"""
        node_data = {"resource_id": "test_id"}
        visitor.window = None

        result = visitor.find_matching_widget(node_data)

        assert result is None

    def test_find_matching_widget_by_id(self, visitor):
        """Test find_matching_widget method with matching resource ID"""
        # Setup mock window
        mock_window = MagicMock(spec=Window)
        mock_widget = MagicMock(spec=Widget)
        mock_window.get_widget_by_name.return_value = mock_widget
        visitor.window = mock_window

        node_data = {"resource_id": "com.example:id/test_button"}

        result = visitor.find_matching_widget(node_data)

        assert result == mock_widget
        mock_window.get_widget_by_name.assert_called_once_with("test_button")
        assert visitor.window_info["matched_widgets"] == 1

    def test_is_parent_clickable_true(self, node, parent_node):
        """Test is_parent_clickable method with clickable parent"""
        # Set up the parent-child relationship
        node.parent = parent_node
        parent_node.clickable = True

        visitor = MockScreenVisitor(None, "test_activity")

        result = visitor.is_parent_clickable(node)

        assert result is True

    def test_is_parent_clickable_false(self, node, parent_node):
        """Test is_parent_clickable method with non-clickable parent"""
        # Set up the parent-child relationship
        node.parent = parent_node
        parent_node.clickable = False

        visitor = MockScreenVisitor(None, "test_activity")

        result = visitor.is_parent_clickable(node)

        assert result is False

    def test_check_method_reaches_target(self, visitor, static_data):
        """Test _check_method_reaches_target method"""
        # Setup mock method in static analysis data
        mock_method = MagicMock()
        mock_method.reaches_target = True

        # Update the methods dict in the existing classes mock
        visitor.static_info.classes.methods = {"test.method.signature": mock_method}

        result = visitor._check_method_reaches_target("test.method.signature")

        assert result is True

    def test_check_method_directly_reaches_target(self, visitor, static_data):
        """Test _check_method_directly_reaches_target method"""
        # Setup mock method in static analysis data
        mock_method = MagicMock()
        mock_method.directly_reaches_target = True

        # Update the methods dict in the existing classes mock
        visitor.static_info.classes.methods = {"test.method.signature": mock_method}

        result = visitor._check_method_directly_reaches_target("test.method.signature")

        assert result is True

    def test_should_exclude_system_button(self, visitor):
        """Test should_exclude_system_button method"""
        # System button node
        system_button = Node(
            {
                "resource_id": "com.android.systemui:id/home",
                "class": "android.widget.Button",
                "package": "com.android.systemui",
            }
        )

        # Regular app button
        app_button = Node(
            {
                "resource_id": "com.example.app:id/my_button",
                "class": "android.widget.Button",
                "package": "com.example.app",
            }
        )

        assert visitor.should_exclude_system_button(system_button) is True
        assert visitor.should_exclude_system_button(app_button) is False

    def test_get_possible_actions(self, visitor, node):
        """Test get_possible_actions method"""
        # Mock the _update_action_mop_related_info method to avoid issues
        visitor._update_action_mop_related_info = MagicMock()

        # Test with a clickable node
        node.clickable = True
        node.long_clickable = True
        node.scrollable = False
        node.editable = False
        node.checkable = False

        actions = visitor.get_possible_actions(node, visitor.counter)

        assert len(actions) == 2
        assert actions[0].event == WidgetEventType.CLICK
        assert actions[1].event == WidgetEventType.LONG_CLICK

        # Test with a scrollable node
        node.clickable = False
        node.long_clickable = False
        node.scrollable = True
        node.editable = False

        actions = visitor.get_possible_actions(node, visitor.counter)

        assert len(actions) == 4  # UP, DOWN, LEFT, RIGHT scrolls
        assert all(action.event == WidgetEventType.SCROLL for action in actions)

        # Test with an editable node
        node.scrollable = False
        node.editable = True

        actions = visitor.get_possible_actions(node, visitor.counter)

        assert len(actions) == 1
        assert actions[0].event == WidgetEventType.TEXT_CHANGE

    def test_update_action_mop_related_info(self, visitor, node):
        """Test _update_action_mop_related_info method"""
        # Setup action
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)

        # Setup widget with event that reaches MOP
        mock_widget = MagicMock(spec=Widget)
        mock_widget.id = "test_widget_id"  # Set id as string
        mock_event = MagicMock()
        mock_event.type = WidgetEventType.CLICK
        mock_event.signature = "test.method.signature"
        mock_widget.events = [mock_event]

        # Mock finding the widget
        visitor.find_matching_widget = MagicMock(return_value=mock_widget)

        # Mock MOP checking methods
        visitor._check_method_reaches_target = MagicMock(return_value=True)
        visitor._check_method_directly_reaches_target = MagicMock(return_value=False)

        visitor._update_action_mop_related_info(action, node)

        assert action.reaches_target is True
        assert action.directly_reaches_target is False
        assert "[M]" in action.text

        # Test directly reaching MOP
        visitor._check_method_directly_reaches_target = MagicMock(return_value=True)

        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor._update_action_mop_related_info(action, node)

        assert action.reaches_target is True
        assert action.directly_reaches_target is True
        assert "[DM]" in action.text

    def test_formatting_methods(self, visitor):
        """Test formatting methods for node descriptions"""
        # Test _with_text
        node = Node({"text": "Test Text"})
        assert visitor._with_text(node) == "with text 'Test Text'"

        # Test long text truncation
        node = Node({"text": "x" * 60})
        assert "truncated" in visitor._with_text(node)

        # Test _has_focus
        node = Node({"focused": True})
        assert visitor._has_focus(node) == " that is currently focused"

        node = Node({"focused": False})
        assert visitor._has_focus(node) == ""

        # Test _with_description
        node = Node({"content_description": "Test Description"})
        assert visitor._with_description(node) == " with description 'Test Description'"

        # Test _with_resource_id
        node = Node({"resource_id": "com.example:id/test_id"})
        assert visitor._with_resource_id(node) == " (id: test_id)"

        node = Node({"resource_id": "simple_id"})
        assert visitor._with_resource_id(node) == " (id: simple_id)"

    # ------------------------------------------------------------------
    # get_screen_description (base implementation, line 141)
    # ------------------------------------------------------------------
    def test_base_get_screen_description_returns_items(self, visitor):
        """The base get_screen_description wraps activity + items unchanged.

        MockScreenVisitor overrides the method, so we call the base class
        implementation explicitly to exercise the un-overridden production path
        that concrete visitors inherit when they do not customize it.
        """
        item = ScreenItem({"id": "x"}, "Item X", [])
        visitor.items = [item]

        description = AbstractScreenVisitor.get_screen_description(visitor)

        assert isinstance(description, ScreenDescription)
        assert description.activity == visitor.activity
        assert description.items == [item]

    # ------------------------------------------------------------------
    # visit() deprecated dispatcher (lines 153-165)
    # ------------------------------------------------------------------
    def test_visit_skips_already_visited_node(self, visitor, node):
        """A node whose identifier is already recorded must not be re-dispatched.

        Basis-path coverage of the early-return guard that prevents duplicate
        processing of the same UI element within one traversal.
        """
        visitor.visit_node = MagicMock()
        visitor.visit_leaf_node = MagicMock()
        visitor.visited_nodes.add(node.unique_identifier)

        visitor.visit(node)

        visitor.visit_node.assert_not_called()
        visitor.visit_leaf_node.assert_not_called()

    def test_visit_skips_system_button(self, visitor):
        """A system navigation button must be filtered out before dispatch.

        Uses a real system resource ID so should_exclude_system_button returns
        True, verifying the second early-return branch of visit().
        """
        visitor.visit_node = MagicMock()
        visitor.visit_leaf_node = MagicMock()
        system_node = Node({"resource_id": "com.android.systemui:id/home"})

        visitor.visit(system_node)

        visitor.visit_node.assert_not_called()
        visitor.visit_leaf_node.assert_not_called()

    def test_visit_dispatches_childless_node_to_visit_node(self, visitor, node):
        """A node without children is dispatched to visit_node.

        Traces the ``if not node.children`` branch (line 162-163).
        """
        visitor.visit_node = MagicMock()
        visitor.visit_leaf_node = MagicMock()

        visitor.visit(node)

        visitor.visit_node.assert_called_once_with(node)
        visitor.visit_leaf_node.assert_not_called()

    def test_visit_dispatches_node_with_children_to_visit_leaf_node(
        self, visitor, node, parent_node
    ):
        """A node with children is dispatched to visit_leaf_node.

        Traces the ``else`` branch (line 164-165). Naming is inverted in the
        deprecated method, but this test documents its current behavior.
        """
        node.children = [parent_node]
        visitor.visit_node = MagicMock()
        visitor.visit_leaf_node = MagicMock()

        visitor.visit(node)

        visitor.visit_leaf_node.assert_called_once_with(node)
        visitor.visit_node.assert_not_called()

    # ------------------------------------------------------------------
    # find_matching_widget text-content fallback (lines 194-200)
    # ------------------------------------------------------------------
    def test_find_matching_widget_by_text(self, visitor):
        """When resource-ID lookup fails, matching falls back to text content.

        GATOR sometimes lacks the resource name but records the widget's text,
        so the visitor scans window widgets for a text match as a second strategy.
        """
        mock_window = MagicMock(spec=Window)
        mock_window.get_widget_by_name.return_value = None
        text_widget = MagicMock(spec=Widget)
        text_widget.text = "Submit"
        mock_window.widgets = {"w1": text_widget}
        visitor.window = mock_window

        result = visitor.find_matching_widget(
            {"resource_id": "com.x:id/unknown", "text": "Submit"}
        )

        assert result is text_widget
        assert visitor.window_info["matched_widgets"] == 1

    def test_find_matching_widget_text_no_match_returns_none(self, visitor):
        """No resource-ID and no text match yields None (line 200)."""
        mock_window = MagicMock(spec=Window)
        mock_window.get_widget_by_name.return_value = None
        other_widget = MagicMock(spec=Widget)
        other_widget.text = "Cancel"
        mock_window.widgets = {"w1": other_widget}
        visitor.window = mock_window

        result = visitor.find_matching_widget(
            {"resource_id": "com.x:id/unknown", "text": "Submit"}
        )

        assert result is None

    # ------------------------------------------------------------------
    # is_always_clickable_type (lines 233, 238, 243)
    # ------------------------------------------------------------------
    def test_is_always_clickable_type_no_view_class(self, visitor):
        """A node with an empty view_class is never inherently clickable (line 233)."""
        assert visitor.is_always_clickable_type(Node({})) is False

    def test_is_always_clickable_type_exact_match(self, visitor):
        """A simple class name present in the set matches exactly (line 238).

        The fully-qualified Material Chip resolves to simple name 'Chip', which
        is an exact member of ALWAYS_CLICKABLE_TYPES.
        """
        node = Node({"class": "com.google.android.material.chip.Chip"})
        assert visitor.is_always_clickable_type(node) is True

    def test_is_always_clickable_type_partial_match(self, visitor):
        """A class whose name merely contains a known type matches (line 243).

        'CustomTabWidget' is not an exact member, but 'Tab' is a substring,
        covering the partial-match fallback for vendor-nested classes.
        """
        node = Node({"class": "com.vendor.CustomTabWidget"})
        assert visitor.is_always_clickable_type(node) is True

    # ------------------------------------------------------------------
    # MOP reachability helpers: not-found paths (lines 261, 277)
    # ------------------------------------------------------------------
    def test_check_method_reaches_target_missing_returns_false(self, visitor):
        """An unknown signature reaches no monitored operation (line 261)."""
        visitor.static_info.classes.methods = {}
        assert visitor._check_method_reaches_target("does.not.exist") is False

    def test_check_method_directly_reaches_target_missing_returns_false(self, visitor):
        """An unknown signature directly reaches no monitored operation (line 277)."""
        visitor.static_info.classes.methods = {}
        assert (
            visitor._check_method_directly_reaches_target("does.not.exist") is False
        )

    # ------------------------------------------------------------------
    # should_exclude_system_button heuristics (329, 345, 351-359, 365-380, 388, 392)
    # ------------------------------------------------------------------
    def test_exclude_by_keyboard_package(self, visitor):
        """A node from an input-method package is a keyboard element (line 329)."""
        node = Node({"package": "com.android.inputmethod.latin"})
        assert visitor.should_exclude_system_button(node) is True

    def test_exclude_by_keyboard_class(self, visitor):
        """A node whose class name mentions a keyboard type is excluded (line 345)."""
        node = Node({"class": "com.vendor.SoftKeyboardView"})
        assert visitor.should_exclude_system_button(node) is True

    def test_exclude_by_navigation_bounds(self, visitor):
        """A node positioned inside the reported nav area is excluded (351-359).

        When system_navigation_bounds is present, any node whose top edge is at
        or below the nav-bar top is treated as part of the system navigation.
        """
        visitor.system_navigation_bounds = {"present": True, "top": 1000}
        node = Node({"bounds": [[0, 1100], [200, 1200]]})
        assert visitor.should_exclude_system_button(node) is True

    def test_exclude_by_keyboard_key_heuristic(self, visitor):
        """A tiny single-character button in the lower half is a keyboard key.

        Covers the size/position/text heuristic (365-380) that catches custom
        keyboards lacking a recognizable package or class.
        """
        visitor.device_info = {"displayHeight": 2000}
        node = Node({"bounds": [[10, 1500], [60, 1550]], "text": "A"})
        assert visitor.should_exclude_system_button(node) is True

    def test_exclude_by_content_description(self, visitor):
        """A 'go back' content description marks a system button (line 388)."""
        node = Node({"content_description": "Go back"})
        assert visitor.should_exclude_system_button(node) is True

    def test_exclude_by_soft_button_class(self, visitor):
        """A class naming both 'soft' and 'button' is a soft navigation button (392)."""
        node = Node({"class": "com.vendor.SoftNavButton"})
        assert visitor.should_exclude_system_button(node) is True

    # ------------------------------------------------------------------
    # get_possible_actions: bounds-based coordinate fallback (431-436)
    # ------------------------------------------------------------------
    def test_get_possible_actions_bounds_coordinate_fallback(self, visitor):
        """When a node lacks center_coordinates, coordinates come from bounds.

        Real Node objects always expose center_coordinates, so this uses a
        lightweight stub without that attribute to exercise the ``elif 'bounds'``
        fallback that computes the center from the raw bounds array.
        """
        visitor._update_action_mop_related_info = MagicMock()
        fake_node = SimpleNamespace(
            data={"bounds": [[10, 20], [30, 40]]},
            clickable=True,
            checkable=False,
            checked=False,
            editable=False,
            long_clickable=False,
            scrollable=False,
            view_class="android.widget.Button",
            view_text="",
        )

        actions = visitor.get_possible_actions(fake_node, visitor.counter)

        assert len(actions) == 1
        assert actions[0].coordinates == (20, 30)

    # ------------------------------------------------------------------
    # get_possible_actions: check/uncheck actions (442-466, 514, 561-584)
    # ------------------------------------------------------------------
    def test_get_possible_actions_prioritize_check_checked(self, visitor):
        """prioritize_check on a checked node yields an UNCHECK action (442-454)."""
        visitor._update_action_mop_related_info = MagicMock()
        node = Node(
            {"class": "android.widget.CheckBox", "checkable": True, "checked": True}
        )

        actions = visitor.get_possible_actions(
            node, visitor.counter, prioritize_check=True
        )

        assert len(actions) == 1
        assert actions[0].text.startswith("UNCHECK")

    def test_get_possible_actions_prioritize_check_unchecked(self, visitor):
        """prioritize_check on an unchecked node yields a CHECK action (455-466)."""
        visitor._update_action_mop_related_info = MagicMock()
        node = Node(
            {"class": "android.widget.CheckBox", "checkable": True, "checked": False}
        )

        actions = visitor.get_possible_actions(
            node, visitor.counter, prioritize_check=True
        )

        assert len(actions) == 1
        assert actions[0].text.startswith("CHECK")

    def test_get_possible_actions_normal_check_unchecked(self, visitor):
        """A checkable node at normal priority produces a CHECK action (514, 573-584)."""
        visitor._update_action_mop_related_info = MagicMock()
        node = Node(
            {"class": "android.widget.CheckBox", "checkable": True, "checked": False}
        )

        actions = visitor.get_possible_actions(node, visitor.counter)

        assert any(a.text.startswith("CHECK") for a in actions)

    def test_get_possible_actions_normal_check_checked(self, visitor):
        """A checked node at normal priority produces an UNCHECK action (561-572)."""
        visitor._update_action_mop_related_info = MagicMock()
        node = Node(
            {"class": "android.widget.CheckBox", "checkable": True, "checked": True}
        )

        actions = visitor.get_possible_actions(node, visitor.counter)

        assert any(a.text.startswith("UNCHECK") for a in actions)

    # ------------------------------------------------------------------
    # get_possible_actions: scroll direction restriction (526, 528)
    # ------------------------------------------------------------------
    def test_get_possible_actions_vertical_scroll_only(self, visitor):
        """ListView/ScrollView are restricted to vertical scrolling (line 526)."""
        visitor._update_action_mop_related_info = MagicMock()
        node = Node({"class": "android.widget.ListView", "scrollable": True})

        actions = visitor.get_possible_actions(node, visitor.counter)

        directions = {a.text.split()[1] for a in actions}
        assert directions == {"UP", "DOWN"}

    def test_get_possible_actions_horizontal_scroll_only(self, visitor):
        """HorizontalScrollView is restricted to horizontal scrolling (line 528)."""
        visitor._update_action_mop_related_info = MagicMock()
        node = Node(
            {"class": "android.widget.HorizontalScrollView", "scrollable": True}
        )

        actions = visitor.get_possible_actions(node, visitor.counter)

        directions = {a.text.split()[1] for a in actions}
        assert directions == {"LEFT", "RIGHT"}

    # ------------------------------------------------------------------
    # _update_action_mop_related_info: no matching widget (line 600)
    # ------------------------------------------------------------------
    def test_update_action_mop_no_matching_widget(self, visitor, node):
        """With no matching widget the action text is left unchanged (line 600)."""
        visitor.window = None
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)

        visitor._update_action_mop_related_info(action, node)

        assert action.text == "CLICK (1)"
        assert action.reaches_target is False

    # ------------------------------------------------------------------
    # Formatting helpers: empty / truncated / field branches
    # ------------------------------------------------------------------
    def test_with_text_no_text(self, visitor):
        """A node without text reports 'with no text' (line 770)."""
        assert visitor._with_text(Node({})) == "with no text"

    def test_with_field_none_widget(self, visitor):
        """A None widget yields an empty field description (line 781)."""
        assert visitor._with_field(None) == ""

    def test_with_field_assigned(self, visitor):
        """A widget carrying a field reports the assignment (line 784)."""
        widget = SimpleNamespace(field="mSecretKey")
        assert visitor._with_field(widget) == "is assigned to a field"

    def test_has_focus_missing_attribute(self, visitor):
        """A node object without a 'focused' attribute yields '' (line 797)."""
        assert visitor._has_focus(SimpleNamespace()) == ""

    def test_with_description_empty(self, visitor):
        """A node without a content description yields '' (line 812)."""
        assert visitor._with_description(Node({})) == ""

    def test_with_description_truncated(self, visitor):
        """A long content description is truncated with an indicator (line 818)."""
        result = visitor._with_description(Node({"content_description": "d" * 60}))
        assert "truncated" in result

    def test_with_resource_id_empty(self, visitor):
        """A node without a resource ID yields '' (line 833)."""
        assert visitor._with_resource_id(Node({})) == ""

    def test_with_hint_empty(self, visitor):
        """A node without a hint yields '' (line 855)."""
        assert visitor._with_hint(Node({})) == ""

    def test_with_hint_truncated(self, visitor):
        """A long hint is truncated with an indicator (line 862)."""
        assert "truncated" in visitor._with_hint(Node({"hint": "h" * 60}))

    def test_with_hint_short(self, visitor):
        """A short hint is returned verbatim (line 864)."""
        assert visitor._with_hint(Node({"hint": "email"})) == " with hint 'email'"

    # ------------------------------------------------------------------
    # Coordinate formatting helpers (880-884, 900-909, 925-927)
    # ------------------------------------------------------------------
    def test_with_position_missing_center(self, visitor):
        """A node without center_coordinates yields '' (line 881)."""
        assert visitor._with_position(SimpleNamespace()) == ""

    def test_with_position_from_bounds(self, visitor):
        """center_coordinates are formatted as a position string (883-884)."""
        node = Node({"bounds": [[10, 20], [30, 40]]})
        assert visitor._with_position(node) == " at position (20, 30)"

    def test_with_bounds_empty(self, visitor):
        """A node with empty bounds yields '' (line 900-901)."""
        assert visitor._with_bounds(Node({"bounds": []})) == ""

    def test_with_bounds_formatted(self, visitor):
        """Two-corner bounds are formatted as coordinate arrays (903-907)."""
        node = Node({"bounds": [[10, 20], [30, 40]]})
        assert visitor._with_bounds(node) == " - bounds[[10, 20], [30, 40]]"

    def test_with_bounds_malformed_length(self, visitor):
        """Bounds that are not exactly two corners yield '' (line 909)."""
        assert visitor._with_bounds(Node({"bounds": [[10, 20]]})) == ""

    def test_with_complete_coordinates(self, visitor):
        """Complete coordinates concatenate position and bounds (925-927)."""
        node = Node({"bounds": [[10, 20], [30, 40]]})
        result = visitor._with_complete_coordinates(node)
        assert result == " at position (20, 30) - bounds[[10, 20], [30, 40]]"

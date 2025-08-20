from unittest.mock import MagicMock, patch

import pytest

from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType, Widget
from rv_android_core.domain.window import Windows, Window
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_screen_parser.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenItem, ScreenDescription, Node


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
        pass

    def visit_leaf_node(self, node: Node) -> None:
        """Mock implementation of visit_leaf_node"""
        pass

    def visit_button(self, node: Node) -> None:
        """Mock implementation of visit_button"""
        pass

    def visit_edit_text(self, node: Node) -> None:
        """Mock implementation of visit_edit_text"""
        pass

    def visit_text_view(self, node: Node) -> None:
        """Mock implementation of visit_text_view"""
        pass

    def visit_checkbox(self, node: Node) -> None:
        """Mock implementation of visit_checkbox"""
        pass

    def visit_checked_text(self, node: Node) -> None:
        """Mock implementation of visit_checked_text"""
        pass

    def visit_toggle_button(self, node: Node) -> None:
        """Mock implementation of visit_toggle_button"""
        pass

    def visit_switch(self, node: Node) -> None:
        """Mock implementation of visit_switch"""
        pass

    def visit_image_button(self, node: Node) -> None:
        """Mock implementation of visit_image_button"""
        pass

    def visit_image(self, node: Node) -> None:
        """Mock implementation of visit_image"""
        pass

    def visit_radio_button(self, node: Node) -> None:
        """Mock implementation of visit_radio_button"""
        pass

    def visit_radio_group(self, node: Node) -> None:
        """Mock implementation of visit_radio_group"""
        pass

    def visit_spinner(self, node: Node) -> None:
        """Mock implementation of visit_spinner"""
        pass

    def visit_slider(self, node: Node) -> None:
        """Mock implementation of visit_slider"""
        pass


class TestAbstractScreenVisitor:
    """Test suite for AbstractScreenVisitor"""

    @pytest.fixture(autouse=True)
    def setup_logging(self):
        """Fixture to set up logging and suppress log messages during tests"""
        with patch('rv_android_core.util.logging.manager.LoggingManager') as mock_logging_manager:
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
            "focused": False
        }
        return Node(data)

    @pytest.fixture
    def parent_node(self):
        """Fixture for a parent Node object"""
        data = {
            "class": "android.widget.LinearLayout",
            "resource_id": "parent_layout",
            "clickable": True,
            "bounds": [[0, 0], [200, 100]]
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

    def test_check_method_reaches_mop(self, visitor, static_data):
        """Test _check_method_reaches_mop method"""
        # Setup mock method in static analysis data
        mock_method = MagicMock()
        mock_method.reaches_mop = True

        # Update the methods dict in the existing classes mock
        visitor.static_info.classes.methods = {"test.method.signature": mock_method}

        result = visitor._check_method_reaches_mop("test.method.signature")

        assert result is True

    def test_check_method_directly_reaches_mop(self, visitor, static_data):
        """Test _check_method_directly_reaches_mop method"""
        # Setup mock method in static analysis data
        mock_method = MagicMock()
        mock_method.directly_reaches_mop = True

        # Update the methods dict in the existing classes mock
        visitor.static_info.classes.methods = {"test.method.signature": mock_method}

        result = visitor._check_method_directly_reaches_mop("test.method.signature")

        assert result is True

    def test_should_exclude_system_button(self, visitor):
        """Test should_exclude_system_button method"""
        # System button node
        system_button = Node({
            "resource_id": "com.android.systemui:id/home",
            "class": "android.widget.Button",
            "package": "com.android.systemui"
        })

        # Regular app button
        app_button = Node({
            "resource_id": "com.example.app:id/my_button",
            "class": "android.widget.Button",
            "package": "com.example.app"
        })

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
        visitor._check_method_reaches_mop = MagicMock(return_value=True)
        visitor._check_method_directly_reaches_mop = MagicMock(return_value=False)

        visitor._update_action_mop_related_info(action, node)

        assert action.reaches_mop is True
        assert action.directly_reaches_mop is False
        assert "[M]" in action.text

        # Test directly reaching MOP
        visitor._check_method_directly_reaches_mop = MagicMock(return_value=True)

        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor._update_action_mop_related_info(action, node)

        assert action.reaches_mop is True
        assert action.directly_reaches_mop is True
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

from unittest.mock import MagicMock, patch

import pytest

from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType, Widget
from rv_android_core.domain.window import Windows, Window
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenItem, ScreenDescription, Node, Counter


class TestDefaultTextVisitor:
    """Test suite for the DefaultTextVisitor class."""

    @pytest.fixture(autouse=True)
    def setup_logging(self):
        """Fixture to set up logging and suppress log messages during tests"""
        with patch('rv_android_core.util.logging.manager.LoggingManager') as mock_logging_manager:
            mock_logger = MagicMock()
            mock_logging_manager.get_instance.return_value = mock_logging_manager
            mock_logging_manager.get_logger.return_value = mock_logger
            yield mock_logger

    @pytest.fixture
    def static_data(self):
        """Fixture for mock static analysis data."""
        # Create mock classes
        mock_classes = MagicMock(spec=Classes)
        mock_classes.methods = {}

        # Create mock windows
        mock_windows = MagicMock(spec=Windows)
        mock_windows.get_window.return_value = None

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
        """Fixture for a DefaultTextVisitor instance."""
        return DefaultTextVisitor(static_data, "com.example.TestActivity")

    @pytest.fixture
    def node(self):
        """Fixture for a basic Node object."""
        data = {
            "class": "android.widget.Button",
            "resource_id": "test_button",
            "text": "Test Button",
            "content_description": "A test button",
            "clickable": True,
            "bounds": [[10, 10], [100, 50]]
        }
        return Node(data)

    @pytest.fixture
    def parent_node(self):
        """Fixture for a parent Node object."""
        data = {
            "class": "android.widget.LinearLayout",
            "resource_id": "parent_layout",
            "clickable": True,
            "bounds": [[0, 0], [200, 100]]
        }
        parent = Node(data)
        return parent

    @pytest.fixture
    def child_node(self, parent_node):
        """Fixture for a child Node object."""
        data = {
            "class": "android.widget.TextView",
            "resource_id": "test_text",
            "text": "Child Text",
            "clickable": False
        }
        child = Node(data, parent=parent_node)
        parent_node.children = [child]
        return child

    def test_initialization(self, static_data):
        """Test visitor initialization."""
        activity = "com.example.TestActivity"
        visitor = DefaultTextVisitor(static_data, activity)

        assert visitor.activity == activity
        assert visitor.static_info == static_data
        assert visitor.items == []
        assert visitor.counter.value == 0
        assert visitor.window_info["interactive_elements"] == 0
        assert visitor.window is None
        assert visitor.processed_parents == set()

    def test_get_screen_description(self, visitor):
        """Test get_screen_description method."""
        # Add test items
        item1 = ScreenItem(view={"id": "item1"}, base_description="Item 1", actions=[])
        item2 = ScreenItem(view={"id": "item2"}, base_description="Item 2", actions=[])
        visitor.items = [item1, item2]

        description = visitor.get_screen_description()

        # The method should add a BACK action, making a total of 3 items
        assert isinstance(description, ScreenDescription)
        assert description.activity == visitor.activity
        assert len(description.items) == 3
        assert "System back button" in description.items[2].base_description
        assert description.items[2].actions[0].event == WidgetEventType.KEY

    def test_visit_node_not_actionable(self, visitor, node):
        """Test visit_node method with a non-actionable node."""
        node.actionable = False
        visitor.visit_node(node)

        # Should not add an item since the node isn't actionable
        assert len(visitor.items) == 0
        assert visitor.window_info["interactive_elements"] == 0

    def test_visit_node_actionable_no_children(self, visitor, node):
        """Test visit_node method with an actionable node without children."""
        node.actionable = True
        node.children = []

        # In DefaultTextVisitor, visit_node only adds items if node has children
        # and child_handles_action is False
        visitor.visit_node(node)

        # Should not add an item since the node doesn't have children
        assert len(visitor.items) == 0
        assert visitor.window_info["interactive_elements"] == 0

    def test_visit_node_with_actionable_children(self, visitor, parent_node, child_node):
        """Test visit_node with parent that has actionable children."""
        parent_node.actionable = True
        child_node.actionable = True

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(id=1, text="CLICK (1)", event=WidgetEventType.CLICK, reaches_mop=False, directly_reaches_mop=False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_node(parent_node)

        # Should not add an item since the child handles the action
        assert len(visitor.items) == 0
        assert visitor.window_info["interactive_elements"] == 0

    def test_visit_node_with_non_actionable_children(self, visitor, parent_node, child_node):
        """Test visit_node with parent that has non-actionable children."""
        parent_node.actionable = True
        child_node.actionable = False

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(id=1, text="CLICK (1)", event=WidgetEventType.CLICK, reaches_mop=False, directly_reaches_mop=False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_node(parent_node)

        # Should add an item since children don't handle actions
        assert len(visitor.items) == 1
        assert visitor.items[0].view == parent_node.data
        assert "Container" in visitor.items[0].base_description
        assert visitor.window_info["interactive_elements"] == 1
        assert parent_node.unique_identifier in visitor.processed_parents

    def test_visit_leaf_node_not_actionable(self, visitor, node):
        """Test visit_leaf_node with a non-actionable node."""
        node.actionable = False
        visitor.visit_leaf_node(node)

        # Should not add an item since the node isn't actionable
        assert len(visitor.items) == 0
        assert visitor.window_info["interactive_elements"] == 0

    def test_visit_leaf_node_actionable(self, visitor, node):
        """Test visit_leaf_node with an actionable node."""
        node.actionable = True

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(id=1, text="CLICK (1)", event=WidgetEventType.CLICK, reaches_mop=False, directly_reaches_mop=False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_leaf_node(node)

        # Should add an item for the actionable node
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert "Element" in visitor.items[0].base_description
        assert visitor.window_info["interactive_elements"] == 1
        assert node.unique_identifier in visitor.processed_parents

    def test_visit_leaf_node_with_inherit_click(self, visitor, child_node, parent_node):
        """Test visit_leaf_node with node inheriting click from parent."""
        child_node.actionable = False
        parent_node.clickable = True

        # Mock is_parent_clickable to return True
        visitor.is_parent_clickable = MagicMock(return_value=True)

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(id=1, text="CLICK (1)", event=WidgetEventType.CLICK, reaches_mop=False, directly_reaches_mop=False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_leaf_node(child_node)

        # Should add an item for the node that inherits clickability
        assert len(visitor.items) == 1
        assert visitor.items[0].view == child_node.data
        assert "Element" in visitor.items[0].base_description
        assert visitor.window_info["interactive_elements"] == 1
        assert child_node.unique_identifier in visitor.processed_parents

        # Verify get_possible_actions was called with inherit_click=True
        visitor.get_possible_actions.assert_called_once()
        args, kwargs = visitor.get_possible_actions.call_args
        assert kwargs.get('inherit_click', False) is True

    def test_find_matching_widget_by_resource_id(self, visitor):
        """Test find_matching_widget method with resource ID."""
        # Create a mock window and widget
        mock_window = MagicMock(spec=Window)
        mock_widget = MagicMock(spec=Widget)
        visitor.window = mock_window

        # Set up the window mock to return the widget by name
        mock_window.get_widget_by_name.return_value = mock_widget

        # Test finding a widget by resource ID
        node_data = {"resource_id": "com.example:id/test_widget"}
        result = visitor.find_matching_widget(node_data)

        assert result == mock_widget
        mock_window.get_widget_by_name.assert_called_with("test_widget")
        assert visitor.window_info["matched_widgets"] == 1

    def test_visit_button(self, visitor, node):
        """Test visit_button method."""
        # Mock get_possible_actions to return a list of actions
        action = ItemAction(id=1, text="CLICK (1)", event=WidgetEventType.CLICK, reaches_mop=False, directly_reaches_mop=False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        # Mock find_matching_widget to return None
        visitor.find_matching_widget = MagicMock(return_value=None)

        node.view_text = "Test Button"
        visitor.visit_button(node)

        # Should add an item for the button
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert "Button " in visitor.items[0].base_description
        assert "with text 'Test Button'" in visitor.items[0].base_description
        assert visitor.window_info["interactive_elements"] == 1

    def test_visit_edit_text(self, visitor, node):
        """Test visit_edit_text method."""
        # Mock get_possible_actions to return a list of actions
        action = ItemAction(id=1, text="SET_TEXT (1)", event=WidgetEventType.TEXT_CHANGE, reaches_mop=False, directly_reaches_mop=False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        # Mock find_matching_widget to return a widget with input_type
        mock_widget = MagicMock(spec=Widget)
        mock_widget.input_type = "email"
        visitor.find_matching_widget = MagicMock(return_value=mock_widget)

        node.view_text = "test@example.com"
        node.is_password = False
        visitor.visit_edit_text(node)

        # Should add an item for the edit text with input type info
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert "Editable text field for email" in visitor.items[0].base_description
        assert "with text 'test@example.com'" in visitor.items[0].base_description
        assert visitor.window_info["interactive_elements"] == 1

        # Test password field
        visitor.items = []
        node.is_password = True
        visitor.visit_edit_text(node)

        assert len(visitor.items) == 1
        assert "Password field" in visitor.items[0].base_description

    def test_visit_text_view(self, visitor, node):
        """Test visit_text_view method."""
        # Mock get_possible_actions to return a list of actions
        action = ItemAction(id=1, text="CLICK (1)", event=WidgetEventType.CLICK, reaches_mop=False, directly_reaches_mop=False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        node.view_text = "Text view content"
        node.clickable = True
        visitor.visit_text_view(node)

        # Should add an item for the text view
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert "Text view" in visitor.items[0].base_description
        assert "with text 'Text view content'" in visitor.items[0].base_description
        assert visitor.window_info["interactive_elements"] == 1

    def test_visit_checkbox(self, visitor, node):
        """Test visit_checkbox method."""
        # Mock get_possible_actions to return a list of actions
        action = ItemAction(id=1, text="CLICK (1)", event=WidgetEventType.CLICK, reaches_mop=False, directly_reaches_mop=False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        # Mock find_matching_widget to return None
        visitor.find_matching_widget = MagicMock(return_value=None)

        node.checked = True
        node.view_text = "Accept terms"
        visitor.visit_checkbox(node)

        # Should add an item for the checkbox
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert "Checkbox that is checked" in visitor.items[0].base_description
        assert "with text 'Accept terms'" in visitor.items[0].base_description
        assert visitor.window_info["interactive_elements"] == 1

    def test_with_text_formatting(self, visitor, node):
        """Test _with_text method formatting."""
        # Test with normal text
        node.view_text = "Normal text"
        result = visitor._with_text(node)
        assert result == "with text 'Normal text'"

        # Test with empty text
        node.view_text = ""
        result = visitor._with_text(node)
        assert result == "with no text"

        # Test with long text that should be truncated
        node.view_text = "x" * 100
        result = visitor._with_text(node)
        assert "truncated" in result
        assert len(result) < 100

    def test_has_focus_formatting(self, visitor, node):
        """Test _has_focus method formatting."""
        # Test with focused node
        node.focused = True
        result = visitor._has_focus(node)
        assert result == " that is currently focused"

        # Test with unfocused node
        node.focused = False
        result = visitor._has_focus(node)
        assert result == ""

    def test_with_description_formatting(self, visitor, node):
        """Test _with_description method formatting."""
        # Test with description
        node.content_description = "Button description"
        result = visitor._with_description(node)
        assert result == " with description 'Button description'"

        # Test with empty description
        node.content_description = ""
        result = visitor._with_description(node)
        assert result == ""

        # Test with long description that should be truncated
        node.content_description = "x" * 100
        result = visitor._with_description(node)
        assert "truncated" in result

    def test_with_resource_id_formatting(self, visitor, node):
        """Test _with_resource_id method formatting."""
        # Test with full resource ID
        node.resource_id = "com.example:id/test_button"
        result = visitor._with_resource_id(node)
        assert result == " (id: test_button)"

        # Test with simple resource ID
        node.resource_id = "test_button"
        result = visitor._with_resource_id(node)
        assert result == " (id: test_button)"

        # Test with empty resource ID
        node.resource_id = ""
        result = visitor._with_resource_id(node)
        assert result == ""

    def test_get_possible_actions(self, visitor, node):
        """Test get_possible_actions method."""
        # Set up counter
        counter = Counter()

        # Test with a clickable node
        node.clickable = True
        node.long_clickable = False
        node.scrollable = False
        node.editable = False
        node.checkable = False

        actions = visitor.get_possible_actions(node, counter)

        assert len(actions) == 1
        assert actions[0].event == WidgetEventType.CLICK
        assert "CLICK" in actions[0].text

        # Test with a checkable node with prioritize_check=True
        node.clickable = False
        node.checkable = True
        node.checked = False

        actions = visitor.get_possible_actions(node, counter, prioritize_check=True)

        assert len(actions) == 1
        assert actions[0].event == WidgetEventType.CLICK
        assert "CHECK" in actions[0].text

        # Test with a scrollable node
        node.clickable = False
        node.checkable = False
        node.scrollable = True

        actions = visitor.get_possible_actions(node, counter)

        assert len(actions) == 4  # UP, DOWN, LEFT, RIGHT
        assert all(action.event == WidgetEventType.SCROLL for action in actions)
        directions = ["UP", "DOWN", "LEFT", "RIGHT"]
        for action, direction in zip(actions, directions):
            assert direction in action.text

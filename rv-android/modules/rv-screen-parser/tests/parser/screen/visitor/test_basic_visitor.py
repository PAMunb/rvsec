from unittest.mock import MagicMock, patch

import pytest

from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_screen_parser.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenItem, ScreenDescription, Node


class TestBasicTextVisitor:
    """Test suite for the BasicTextVisitor class."""

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
        """Fixture for a BasicTextVisitor instance."""
        return BasicTextVisitor(static_data, "com.example.TestActivity")

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
        return Node(data)

    def test_initialization(self, static_data):
        """Test visitor initialization."""
        activity = "com.example.TestActivity"
        visitor = BasicTextVisitor(static_data, activity)

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
        item1 = ScreenItem({"id": "item1"}, "Item 1", [])
        item2 = ScreenItem({"id": "item2"}, "Item 2", [])
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

    def test_visit_node_actionable(self, visitor, node):
        """Test visit_node method with an actionable node."""
        node.actionable = True

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_node(node)

        # Should add an item for the actionable node
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description.startswith("Container")
        assert visitor.window_info["interactive_elements"] == 1
        assert node.get_unique_id() in visitor.processed_parents

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
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_leaf_node(node)

        # Should add an item for the actionable node
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description.startswith("Element")
        assert visitor.window_info["interactive_elements"] == 1
        assert node.get_unique_id() in visitor.processed_parents

    def test_visit_button(self, visitor, node):
        """Test visit_button method."""
        node.view_text = "Test Button"

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_button(node)

        # Should add an item for the button
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == 'Button "Test Button"'
        assert visitor.window_info["interactive_elements"] == 1

    def test_visit_edit_text(self, visitor, node):
        """Test visit_edit_text method."""
        node.is_password = False
        node.content_description = "Username field"

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "SET_TEXT (1)", WidgetEventType.TEXT_CHANGE, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_edit_text(node)

        # Should add an item for the edit text
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Text field (Username field)"
        assert visitor.window_info["interactive_elements"] == 1

        # Test password field
        visitor.items = []
        node.is_password = True
        visitor.visit_edit_text(node)

        assert len(visitor.items) == 1
        assert "Password field" in visitor.items[0].base_description

    def test_visit_text_view_not_actionable(self, visitor, node):
        """Test visit_text_view method with non-actionable, no-text node."""
        node.view_text = ""
        node.clickable = False
        node.long_clickable = False

        visitor.visit_text_view(node)

        # Should not add an item for a non-actionable text view with no text
        assert len(visitor.items) == 0

    def test_visit_text_view_with_text(self, visitor, node):
        """Test visit_text_view method with text."""
        node.view_text = "Some text content"
        node.clickable = False
        node.long_clickable = False

        visitor.visit_text_view(node)

        # Should add an item for text view with text
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Some text content"

    def test_visit_text_view_actionable(self, visitor, node):
        """Test visit_text_view method with actionable node."""
        node.view_text = ""
        node.clickable = True

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_text_view(node)

        # Should add an item for actionable text view
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Text view"
        assert visitor.window_info["interactive_elements"] == 1

    def test_visit_checkbox(self, visitor, node):
        """Test visit_checkbox method."""
        node.checked = True

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "UNCHECK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_checkbox(node)

        # Should add an item for the checkbox
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Checkbox (checked)"
        assert visitor.window_info["interactive_elements"] == 1

        # Test unchecked checkbox
        visitor.items = []
        node.checked = False
        visitor.visit_checkbox(node)

        assert len(visitor.items) == 1
        assert "Checkbox (unchecked)" in visitor.items[0].base_description

    def test_visit_checked_text(self, visitor, node):
        """Test visit_checked_text method."""
        node.checked = True

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "UNCHECK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_checked_text(node)

        # Should add an item for the checked text
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Checked text (checked)"
        assert visitor.window_info["interactive_elements"] == 1

        # Test unchecked text
        visitor.items = []
        node.checked = False
        visitor.visit_checked_text(node)

        assert len(visitor.items) == 1
        assert "Checked text (unchecked)" in visitor.items[0].base_description

    def test_visit_image_button(self, visitor, node):
        """Test visit_image_button method."""
        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_image_button(node)

        # Should add an item for the image button
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Image button"
        assert visitor.window_info["interactive_elements"] == 1

    def test_visit_image_not_actionable(self, visitor, node):
        """Test visit_image method with non-actionable, no-description node."""
        node.clickable = False
        node.long_clickable = False
        node.content_description = ""

        visitor.visit_image(node)

        # Should not add an item for a non-actionable image with no description
        assert len(visitor.items) == 0

    def test_visit_image_with_description(self, visitor, node):
        """Test visit_image method with description."""
        node.clickable = False
        node.long_clickable = False
        node.content_description = "Logo image"

        visitor.visit_image(node)

        # Should add an item for image with description
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Image: Logo image"

    def test_visit_image_actionable(self, visitor, node):
        """Test visit_image method with actionable node."""
        node.clickable = True
        node.content_description = ""

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_image(node)

        # Should add an item for actionable image
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Image"
        assert visitor.window_info["interactive_elements"] == 1

    def test_visit_toggle_button(self, visitor, node):
        """Test visit_toggle_button method."""
        node.checked = True

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_toggle_button(node)

        # Should add an item for the toggle button
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Toggle button (ON)"
        assert visitor.window_info["interactive_elements"] == 1

        # Test OFF toggle button
        visitor.items = []
        node.checked = False
        visitor.visit_toggle_button(node)

        assert len(visitor.items) == 1
        assert "Toggle button (OFF)" in visitor.items[0].base_description

    def test_visit_switch(self, visitor, node):
        """Test visit_switch method."""
        node.checked = True

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_switch(node)

        # Should add an item for the switch
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Switch (ON)"
        assert visitor.window_info["interactive_elements"] == 1

        # Test OFF switch
        visitor.items = []
        node.checked = False
        visitor.visit_switch(node)

        assert len(visitor.items) == 1
        assert "Switch (OFF)" in visitor.items[0].base_description

    def test_visit_radio_button(self, visitor, node):
        """Test visit_radio_button method."""
        node.selected = True

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_radio_button(node)

        # Should add an item for the radio button
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Radio button (selected)"
        assert visitor.window_info["interactive_elements"] == 1

        # Test not selected radio button
        visitor.items = []
        node.selected = False
        visitor.visit_radio_button(node)

        assert len(visitor.items) == 1
        assert "Radio button (not selected)" in visitor.items[0].base_description

    def test_visit_spinner(self, visitor, node):
        """Test visit_spinner method."""
        node.clickable = True
        node.scrollable = True

        visitor.visit_spinner(node)

        # Should add an item for the spinner
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert "Dropdown" in visitor.items[0].base_description
        assert visitor.window_info["interactive_elements"] == 1

        # Check actions
        actions = visitor.items[0].actions
        assert len(actions) == 1  # CLICK

        action_types = [action.event for action in actions]
        assert WidgetEventType.CLICK in action_types

    def test_visit_radio_group_simple(self, visitor, node):
        """Test visit_radio_group method with direct actionable."""
        node.actionable = True

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        # Mock accept to verify it's called for child nodes
        node.children = [MagicMock(), MagicMock()]

        visitor.visit_radio_group(node)

        # Should add an item for the actionable radio group
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Radio group"
        assert visitor.window_info["interactive_elements"] == 1

        # Verify accept was called for each child
        for child in node.children:
            child.accept.assert_called_once_with(visitor)

    def test_visit_slider(self, visitor, node):
        """Test visit_slider method."""
        node.progress = 50
        node.max = 100

        # Mock get_possible_actions to return a list of actions
        action = ItemAction(1, "CLICK (1)", WidgetEventType.CLICK, False, False)
        visitor.get_possible_actions = MagicMock(return_value=[action])

        visitor.visit_slider(node)

        # Should add an item for the slider
        assert len(visitor.items) == 1
        assert visitor.items[0].view == node.data
        assert visitor.items[0].base_description == "Slider (50%)"
        assert visitor.window_info["interactive_elements"] == 1

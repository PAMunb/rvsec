"""
Comprehensive tests for the DroidBot parser.

This module contains unit tests for the DroidBotParser class, which is responsible
for parsing DroidBot state data into a structured representation of Android UI elements.
"""

import json
import os
from unittest.mock import Mock, patch

import pytest

from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_android_core.util.exceptions import RVParsingError
from rv_screen_parser.parser.screen.droidbot.droidbot_parser import DroidBotParser
from rv_screen_parser.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rv_screen_parser.parser.screen.visitor.model import Node, ScreenDescription


@pytest.fixture
def parser():
    """Fixture that provides a basic DroidBotParser instance."""
    return DroidBotParser()


@pytest.fixture
def parser_with_basic_visitor():
    """Fixture that provides a DroidBotParser with BasicTextVisitor."""
    return DroidBotParser(BasicTextVisitor)


@pytest.fixture
def mock_visitor():
    """Fixture that provides a mock visitor."""
    mock = Mock()
    mock.get_screen_description.return_value = ScreenDescription("TestActivity", [])

    # Add additional required methods for the visitor
    mock.system_navigation_bounds = {}
    mock.device_info = {}

    return mock


@pytest.fixture
def sample_state_file():
    """Fixture that provides the path to a sample DroidBot state file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "fixtures", "001.state")


@pytest.fixture
def sample_state_data(sample_state_file):
    """Fixture that provides the content of the sample DroidBot state file."""
    with open(sample_state_file, 'r') as f:
        return json.load(f)


@pytest.fixture
def static_data():
    """Fixture that provides mock static analysis data."""
    classes = Classes()
    windows = Windows()
    wtg = WindowTransitionGraph()
    return StaticAnalysisData(classes, windows, wtg)


class TestDroidBotParserBasics:
    """Tests for the basic functionality of the DroidBotParser."""

    def test_init(self, parser):
        """Test that the parser initializes correctly."""
        assert parser.parser_name == "droidbot"
        assert parser.visitor_class is not None

    def test_get_activity_name(self, parser, sample_state_data):
        """Test extracting the activity name from state data."""
        activity = parser.get_activity_name(sample_state_data)
        assert activity == "br.unb.cic.cryptoapp.MainActivity"

    def test_get_activity_name_with_slash(self, parser):
        """Test extracting activity name with a slash."""
        state_data = {"activity": "com.example.app/.MainActivity"}
        activity = parser.get_activity_name(state_data)
        assert activity == "com.example.app.MainActivity"

    def test_get_activity_from_stack(self, parser):
        """Test extracting activity from stack when activity field is empty."""
        state_data = {
            "activity": "",
            "stack": ["com.example.app/.MainActivity"]
        }
        activity = parser.get_activity_name(state_data)
        assert activity == "com.example.app.MainActivity"

    def test_get_activity_from_windows(self, parser):
        """Test extracting activity from windows when activity and stack are empty."""
        state_data = {
            "activity": "",
            "stack": [],
            "windows": [
                {"focused": True, "activity": "com.example.app/.MainActivity"},
                {"focused": False, "activity": "com.example.app/.OtherActivity"}
            ]
        }
        activity = parser.get_activity_name(state_data)
        assert activity == "com.example.app.MainActivity"

    def test_activity_fallback(self, parser):
        """Test fallback to package name when no activity info is available."""
        state_data = {
            "package_name": "com.example.app"
        }
        activity = parser.get_activity_name(state_data)
        assert activity == "com.example.app.UnknownActivity"

    def test_validate_state_data_valid(self, parser, sample_state_data):
        """Test validation with valid state data."""
        assert parser.validate_state_data(sample_state_data) is True

    def test_validate_state_data_invalid(self, parser):
        """Test validation with invalid state data."""
        # Missing view_tree
        assert parser.validate_state_data({}) is False

    def test_create_node_tree(self, parser, sample_state_data):
        """Test creating a node tree from view_tree data."""
        root_node = parser.create_node_tree(sample_state_data)

        # Check the root node
        assert isinstance(root_node, Node)
        assert hasattr(root_node, 'view_class')
        assert "FrameLayout" in root_node.view_class

        # Check that we have children
        assert len(root_node.children) > 0

    def test_create_node_tree_missing_view_tree(self, parser):
        """Test handling of missing view_tree in state data."""
        result = parser.create_node_tree({})
        assert result is None

    def test_create_node_tree_invalid_view_tree(self, parser):
        """Test handling of invalid view_tree in state data."""
        result = parser.create_node_tree({"view_tree": "not a dict"})
        assert result is None


class TestDroidBotParserIntegration:
    """Integration tests for the DroidBotParser."""

    def test_parse_implementation(self, parser, sample_state_data, static_data, mock_visitor):
        """Test the _parse_implementation method."""
        with patch.object(DroidBotParser, 'create_visitor', return_value=mock_visitor):
            # Configure the mock_visitor
            mock_visitor.get_screen_description.return_value = ScreenDescription(
                "br.unb.cic.cryptoapp.MainActivity", []
            )

            result = parser._parse_implementation(
                sample_state_data,
                static_data,
                "br.unb.cic.cryptoapp.MainActivity"
            )

            assert isinstance(result, ScreenDescription)
            assert result.activity == "br.unb.cic.cryptoapp.MainActivity"

    def test_parse_screen(self, parser, sample_state_data, mock_visitor):
        """Test the parse_screen method."""
        with patch.object(DroidBotParser, 'create_visitor', return_value=mock_visitor):
            # Configure the mock_visitor
            mock_visitor.get_screen_description.return_value = ScreenDescription(
                "br.unb.cic.cryptoapp.MainActivity", []
            )

            result = parser.parse_screen(sample_state_data)

            assert isinstance(result, ScreenDescription)
            assert result.activity == "br.unb.cic.cryptoapp.MainActivity"

    def test_parse_screen_invalid_data(self, parser):
        """Test the parse_screen method with invalid data."""
        with pytest.raises(RVParsingError):
            parser.parse_screen({})  # Missing view_tree

    def test_basic_visitor_integration(self, parser_with_basic_visitor, sample_state_data):
        """Test DroidBotParser with BasicTextVisitor."""
        result = parser_with_basic_visitor.parse_screen(sample_state_data)

        assert isinstance(result, ScreenDescription)
        assert result.activity == "br.unb.cic.cryptoapp.MainActivity"

        # We should have some items captured by the visitor
        assert len(result.items) > 0

        # Check that buttons are captured
        button_items = [item for item in result.items if "Button" in item.base_description]
        assert len(button_items) >= 3  # At least 3 buttons from the sample

        # Check for action items
        assert sum(len(item.actions) for item in result.items) > 0


class TestDroidBotParserNodeProcessing:
    """Tests for the node processing functionality of the DroidBotParser."""

    def test_node_attributes(self, parser, sample_state_data):
        """Test that node attributes are correctly processed."""
        root_node = parser.create_node_tree(sample_state_data)

        # Find a button node to test
        def find_button_node(node):
            """Helper to find a button node."""
            if hasattr(node, 'view_class') and "Button" in node.view_class:
                return node
            for child in node.children:
                result = find_button_node(child)
                if result:
                    return result
            return None

        button_node = find_button_node(root_node)
        assert button_node is not None

        # Check button attributes
        assert hasattr(button_node, 'clickable')
        assert button_node.clickable is True
        assert hasattr(button_node, 'view_text')
        assert button_node.view_text in ["MESSAGE DIGEST", "CIPHER", "GENERATED"]

    def test_node_recursion(self, parser, sample_state_data):
        """Test that node recursion works correctly."""
        root_node = parser.create_node_tree(sample_state_data)

        # Verify parent-child relationships
        for child in root_node.children:
            assert child.parent is root_node

            # Check second level recursion if there are grandchildren
            for grandchild in child.children:
                assert grandchild.parent is child

    def test_node_coordinates(self, parser, sample_state_data):
        """Test that node coordinates are correctly processed."""
        root_node = parser.create_node_tree(sample_state_data)

        # Find a node with specific bounds to test
        def find_node_with_bounds(node, bounds):
            """Helper to find a node with specific bounds."""
            if hasattr(node, 'bounds') and node.bounds == bounds:
                return node
            for child in node.children:
                result = find_node_with_bounds(child, bounds)
                if result:
                    return result
            return None

        # Find message digest button by its bounds
        button_node = find_node_with_bounds(root_node, [[0, 210], [1080, 336]])
        assert button_node is not None

        # Check center coordinates
        center = button_node.get_center_coordinates()
        assert center == (540, 273)  # Center of the button
       
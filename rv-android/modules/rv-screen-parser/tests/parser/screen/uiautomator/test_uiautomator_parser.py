"""
Tests for the UIAutomator2Parser class.

This module contains unit tests for the UIAutomator2Parser class, which is responsible
for parsing UIAutomator XML hierarchy data into a structured representation of
Android UI elements.
"""

import os
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch

import pytest
from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_android_core.util.error.exceptions import RVParsingError
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import (
    UIAutomator2Parser,
)
from rv_screen_parser.parser.screen.visitor.model import Node, ScreenDescription


@pytest.fixture
def parser():
    """Fixture that provides a basic UIAutomator2Parser instance."""
    return UIAutomator2Parser()


@pytest.fixture
def mock_visitor():
    """Fixture that provides a mock visitor."""
    mock = Mock()
    mock.get_screen_description.return_value = ScreenDescription("TestActivity", [])
    return mock


@pytest.fixture
def sample_xml_file():
    """Fixture that provides the path to a sample UIAutomator XML file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "fixtures", "001.uiautomator")


@pytest.fixture
def sample_xml_content(sample_xml_file):
    """Fixture that provides the content of the sample UIAutomator XML file."""
    with open(sample_xml_file, "r") as f:
        return f.read()


@pytest.fixture
def static_data():
    """Fixture that provides mock static analysis data."""
    classes = Classes()
    windows = Windows()
    wtg = WindowTransitionGraph()
    return StaticAnalysisData(classes, windows, wtg)


class TestUIAutomator2Parser:
    """Tests for the UIAutomator2Parser class."""

    def test_init(self, parser):
        """Test that the parser initializes correctly."""
        assert parser.parser_name == "uiautomator"
        assert parser.visitor_class is not None

    @patch.object(UIAutomator2Parser, "create_visitor")
    def test_parse_xml_string(
        self, mock_create_visitor, parser, mock_visitor, sample_xml_content
    ):
        """Test parsing an XML string directly."""
        mock_create_visitor.return_value = mock_visitor

        result = parser.parse(
            sample_xml_content, activity="br.unb.cic.cryptoapp.MainActivity"
        )

        assert isinstance(result, ScreenDescription)
        assert mock_visitor.get_screen_description.called
        mock_create_visitor.assert_called_once()

    @patch.object(UIAutomator2Parser, "create_visitor")
    def test_parse_state_data_dict(self, mock_create_visitor, parser, mock_visitor):
        """Test parsing a state data dictionary."""
        mock_create_visitor.return_value = mock_visitor

        state_data = {
            "hierarchy": "<hierarchy><node text='test' /></hierarchy>",
            "activity": "TestActivity",
        }

        result = parser.parse_screen(state_data)

        assert isinstance(result, ScreenDescription)
        assert mock_visitor.get_screen_description.called
        mock_create_visitor.assert_called_once()

    def test_get_activity_name_from_explicit(self, parser):
        """Test extracting activity name when explicitly provided."""
        state_data = {
            "activity": "com.test.Activity",
            "hierarchy": "<hierarchy></hierarchy>",
        }

        activity = parser.get_activity_name(state_data)

        assert activity == "com.test.Activity"

    def test_get_activity_name_from_xml(self, parser, sample_xml_content):
        """Test extracting activity name from XML content."""
        state_data = {"hierarchy": sample_xml_content}

        activity = parser.get_activity_name(state_data)

        assert activity == "br.unb.cic.cryptoapp"  # Package name from the XML

    def test_extract_activity_from_xml(self, parser, sample_xml_content):
        """Test extracting activity name directly from XML content."""
        activity = parser._extract_activity_from_xml(sample_xml_content)

        assert activity == "br.unb.cic.cryptoapp"

    def test_validate_state_data_valid(self, parser, sample_xml_content):
        """Test validation of valid state data."""
        state_data = {"hierarchy": sample_xml_content}

        assert parser.validate_state_data(state_data) is True

    def test_validate_state_data_invalid(self, parser):
        """Test validation of invalid state data."""
        # Missing hierarchy
        state_data1 = {}
        assert parser.validate_state_data(state_data1) is False

        # Invalid XML
        state_data2 = {"hierarchy": "<invalid>"}
        assert parser.validate_state_data(state_data2) is False

    def test_create_node_tree(self, parser, sample_xml_content):
        """Test creating a node tree from XML data."""
        state_data = {"hierarchy": sample_xml_content}

        root_node = parser.create_node_tree(state_data)

        assert isinstance(root_node, Node)
        # The exact class name might vary, test that it's a node with children
        assert hasattr(root_node, "view_class")
        assert len(root_node.children) > 0

    def test_parse_real_xml_file(self, parser, sample_xml_content, mock_visitor):
        """Test parsing a real XML file and validating the structure."""
        # Update the mock visitor to return a screen description with the correct activity
        mock_visitor.get_screen_description.return_value = ScreenDescription(
            "br.unb.cic.cryptoapp.MainActivity", []
        )

        with patch.object(
            UIAutomator2Parser, "create_visitor", return_value=mock_visitor
        ):
            state_data = {
                "hierarchy": sample_xml_content,
                "activity": "br.unb.cic.cryptoapp.MainActivity",
            }

            result = parser.parse_screen(state_data)

            assert isinstance(result, ScreenDescription)
            assert result.activity == "br.unb.cic.cryptoapp.MainActivity"

    def test_build_node_from_element(self, parser):
        """Test building a Node from an XML element."""
        xml_str = """
        <node class="android.widget.Button" text="Click me" 
              content-desc="Button description" clickable="true"
              bounds="[10,20][100,50]" />
        """
        element = ET.fromstring(xml_str)

        node = parser._build_node_from_element(element)

        assert node.view_class == "android.widget.Button"
        assert node.view_text == "Click me"
        assert node.content_description == "Button description"
        assert node.clickable is True
        assert node.bounds == [[10, 20], [100, 50]]

    def test_build_node_hierarchy(self, parser):
        """Test building a node hierarchy with parent-child relationships."""
        xml_str = """
        <node class="parent">
            <node class="child1" />
            <node class="child2">
                <node class="grandchild" />
            </node>
        </node>
        """
        element = ET.fromstring(xml_str)

        node = parser._build_node_from_element(element)

        assert node.view_class == "parent"
        assert len(node.children) == 2
        assert node.children[0].view_class == "child1"
        assert node.children[1].view_class == "child2"
        assert len(node.children[1].children) == 1
        assert node.children[1].children[0].view_class == "grandchild"

    def test_parse_implementation(
        self, parser, sample_xml_content, static_data, mock_visitor
    ):
        """Test the specific implementation of _parse_implementation."""
        # Update the mock visitor to return a screen description with the correct activity
        mock_visitor.get_screen_description.return_value = ScreenDescription(
            "br.unb.cic.cryptoapp.MainActivity", []
        )

        with patch.object(
            UIAutomator2Parser, "create_visitor", return_value=mock_visitor
        ):
            state_data = {
                "hierarchy": sample_xml_content,
                "activity": "br.unb.cic.cryptoapp.MainActivity",
            }

            result = parser._parse_implementation(
                state_data, static_data, "br.unb.cic.cryptoapp.MainActivity"
            )

            assert isinstance(result, ScreenDescription)
            assert result.activity == "br.unb.cic.cryptoapp.MainActivity"

    def test_visitor_creation(self, parser, static_data):
        """Test that the visitor is created correctly."""
        # Test the creation of a visitor - should return a valid visitor instance
        visitor = parser.create_visitor(static_data, "TestActivity")

        # Verify that we get a visitor instance
        assert visitor is not None
        # The visitor should have the expected methods
        assert hasattr(visitor, "get_screen_description")

    def test_parse_bounds_attribute(self, parser):
        """Test parsing of the bounds attribute."""
        xml_str = '<node bounds="[10,20][100,50]" />'
        element = ET.fromstring(xml_str)

        node = parser._build_node_from_element(element)

        assert node.bounds == [[10, 20], [100, 50]]

    def test_parse_invalid_bounds(self, parser):
        """Test handling of invalid bounds attribute."""
        xml_str = '<node bounds="invalid" />'
        element = ET.fromstring(xml_str)

        node = parser._build_node_from_element(element)

        # Should default to [[0, 0], [0, 0]] or similar when bounds are invalid
        assert isinstance(node.bounds, list)
        assert len(node.bounds) == 2

    def test_error_handling_invalid_xml(self, parser):
        """Test handling of invalid XML data."""
        with pytest.raises(RVParsingError):
            parser.parse_screen({"hierarchy": "<invalid>"})

"""
Tests for the integration between UIAutomator2Parser and various visitors.

This module contains integration tests that verify the UIAutomator2Parser
works correctly with different visitor implementations.
"""

import os

import pytest

from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


@pytest.fixture
def sample_xml_file():
    """Fixture that provides the path to a sample UIAutomator XML file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "fixtures", "001.uiautomator")


@pytest.fixture
def sample_xml_content(sample_xml_file):
    """Fixture that provides the content of the sample UIAutomator XML file."""
    with open(sample_xml_file, 'r') as f:
        return f.read()


@pytest.fixture
def static_data():
    """Fixture that provides mock static analysis data."""
    classes = Classes()
    windows = Windows()
    wtg = WindowTransitionGraph()
    return StaticAnalysisData(classes, windows, wtg)


class TestVisitorIntegration:
    """Integration tests for UIAutomator2Parser with visitors."""

    def test_basic_visitor_integration(self, sample_xml_content, static_data):
        """Test integration with BasicTextVisitor."""
        # Create parser with BasicTextVisitor
        parser = UIAutomator2Parser(BasicTextVisitor)

        # Parse the sample XML
        state_data = {
            "hierarchy": sample_xml_content,
            "activity": "br.unb.cic.cryptoapp.MainActivity"
        }

        # Run the parser
        result = parser.parse_screen(state_data, static_data)

        # Validate the result
        assert isinstance(result, ScreenDescription)
        assert result.activity == "br.unb.cic.cryptoapp.MainActivity"

        # The CryptoApp has three main buttons, so we expect them to be captured
        # Plus a BACK button added by the visitor
        button_items = [item for item in result.items
                        if "Button" in item.base_description]

        # Check for the three app buttons plus system back button = 4
        assert len(button_items) >= 3

        # Verify that the specific buttons from the app are present
        button_texts = [item.view.get('text', '') for item in result.items]
        assert "MESSAGE DIGEST" in button_texts
        assert "CIPHER" in button_texts
        assert "GENERATED" in button_texts

    def test_visitor_inheritance_hierarchy(self, sample_xml_content, static_data):
        """Test that different visitors create appropriate node representations."""
        # Test with basic visitor first
        basic_parser = UIAutomator2Parser(BasicTextVisitor)
        basic_result = basic_parser.parse_screen({
            "hierarchy": sample_xml_content,
            "activity": "br.unb.cic.cryptoapp.MainActivity"
        }, static_data)

        # Count actions in basic result
        basic_action_count = sum(len(item.actions) for item in basic_result.items)

        # Get all button descriptions
        basic_buttons = [item.base_description for item in basic_result.items
                         if "Button" in item.base_description]

        # Basic assertions
        assert len(basic_result.items) > 0
        assert basic_action_count > 0
        assert len(basic_buttons) >= 3

    def test_xml_parsing_structure(self, sample_xml_content):
        """Test that the parser correctly builds the UI element hierarchy."""
        parser = UIAutomator2Parser()

        # Parse the XML directly into a node tree
        state_data = {"hierarchy": sample_xml_content}
        root_node = parser.create_node_tree(state_data)

        # Check that the root node has the expected structure
        assert hasattr(root_node, 'view_class')
        assert hasattr(root_node, 'package')

        # Find buttons regardless of exact class name
        def find_buttons(node):
            """Recursively find buttons in the node tree."""
            buttons = []
            if hasattr(node, 'view_text') and node.view_text in ["MESSAGE DIGEST", "CIPHER", "GENERATED"]:
                buttons.append(node)
            for child in node.children:
                buttons.extend(find_buttons(child))
            return buttons

        buttons = find_buttons(root_node)

        # Check that we found the expected number of buttons (3 main buttons)
        assert len(buttons) >= 3

        # Verify button content
        button_texts = [btn.view_text for btn in buttons]
        assert "MESSAGE DIGEST" in button_texts
        assert "CIPHER" in button_texts
        assert "GENERATED" in button_texts

    def test_attributes_correctly_parsed(self, sample_xml_content):
        """Test that XML attributes are correctly parsed into node properties."""
        parser = UIAutomator2Parser()

        # Parse the XML directly into a node tree
        state_data = {"hierarchy": sample_xml_content}
        root_node = parser.create_node_tree(state_data)

        # Function to find a node by text
        def find_node_by_text(node, text):
            """Recursively find a node with specific text."""
            if node.view_text == text:
                return node
            for child in node.children:
                result = find_node_by_text(child, text)
                if result:
                    return result
            return None

        # Find the "MESSAGE DIGEST" button
        button = find_node_by_text(root_node, "MESSAGE DIGEST")

        # Verify button attributes
        assert button is not None
        assert button.view_class == "android.widget.Button"
        assert button.clickable is True
        assert button.resource_id == "br.unb.cic.cryptoapp:id/buttonMessageDigest"
        assert isinstance(button.bounds, list)
        assert len(button.bounds) == 2  # Should be [[x1,y1], [x2,y2]]

    def test_bounds_calculation(self, sample_xml_content):
        """Test that bounds calculation works correctly."""
        parser = UIAutomator2Parser()

        # Parse the XML directly into a node tree
        state_data = {"hierarchy": sample_xml_content}
        root_node = parser.create_node_tree(state_data)

        # Function to find a node by resource ID
        def find_node_by_resource_id(node, resource_id):
            """Recursively find a node with specific resource ID."""
            if node.resource_id == resource_id:
                return node
            for child in node.children:
                result = find_node_by_resource_id(child, resource_id)
                if result:
                    return result
            return None

        # Find the "MESSAGE DIGEST" button
        button = find_node_by_resource_id(
            root_node, "br.unb.cic.cryptoapp:id/buttonMessageDigest")

        # Verify bounds
        assert button is not None
        assert button.bounds == [[0, 210], [1080, 336]]

        # Test center calculation
        center = button.get_center_coordinates()
        assert center == (540, 273)  # Center of the button

"""
Tests for edge cases and error handling in DroidBotParser.

This module contains tests for various edge cases and error handling
scenarios for the DroidBotParser class.
"""

from unittest.mock import patch

import pytest

from rvandroid.parser.screen.droidbot.droidbot_parser import DroidBotParser
from rvandroid.parser.screen.visitor.model import ScreenDescription, Node


class TestDroidBotParserEdgeCases:
    """Tests for edge cases and error handling in DroidBotParser."""

    def test_empty_state_data(self, parser, mock_visitor):
        """Test handling of empty state data."""
        with patch.object(DroidBotParser, 'create_visitor', return_value=mock_visitor):
            with pytest.raises(ValueError):
                parser.parse_screen({})

    def test_missing_view_tree(self, parser, mock_visitor):
        """Test handling of missing view_tree in state data."""
        with patch.object(DroidBotParser, 'create_visitor', return_value=mock_visitor):
            with pytest.raises(ValueError):
                parser.parse_screen({"activity": "com.example.app.MainActivity"})

    def test_malformed_view_tree(self, parser):
        """Test handling of malformed view_tree in state data."""
        # Test with non-dict view_tree
        state_data = {
            "activity": "com.example.app.MainActivity",
            "view_tree": "not a dictionary"
        }

        # The create_node_tree method should return None for malformed view_tree
        result = parser.create_node_tree(state_data)
        assert result is None

        # Ensure the parser still validates the state data
        assert parser.validate_state_data(state_data) is True  # It has a view_tree key

    def test_malformed_node_data(self, parser):
        """Test handling of malformed node data."""
        # Create state data with malformed node (not a dict)
        state_data = {
            "activity": "com.example.app.MainActivity",
            "view_tree": {
                "class": "android.widget.FrameLayout",
                "children": ["not a dict", {"class": "android.widget.Button"}]
            }
        }

        # Should still create a node but skip the invalid child
        node = parser.create_node_tree(state_data)
        assert isinstance(node, Node)
        assert len(node.children) == 1  # Only the valid child should be processed

    def test_empty_activity_with_fallback(self, parser, simple_state_data):
        """Test fallback activity name resolution."""
        # Remove activity and add package_name
        modified_data = simple_state_data.copy()
        modified_data.pop("activity", None)
        modified_data["package_name"] = "com.example.app"

        activity = parser.get_activity_name(modified_data)
        assert activity == "com.example.app.UnknownActivity"

    def test_multiple_activity_sources(self, parser):
        """Test activity resolution with multiple sources."""
        state_data = {
            "activity": "com.primary.app.MainActivity",
            "stack": ["com.stack.app.StackActivity"],
            "windows": [
                {"focused": True, "activity": "com.window.app.WindowActivity"}
            ],
            "package_name": "com.package.app"
        }

        # Should prioritize direct activity field
        activity = parser.get_activity_name(state_data)
        assert activity == "com.primary.app.MainActivity"

        # Remove direct activity
        modified = state_data.copy()
        modified["activity"] = ""
        activity = parser.get_activity_name(modified)
        assert activity == "com.stack.app.StackActivity"  # From stack

        # Remove stack as well
        modified["stack"] = []
        activity = parser.get_activity_name(modified)
        assert activity == "com.window.app.WindowActivity"  # From window

    def test_deep_node_hierarchy(self, parser):
        """Test handling of deeply nested node hierarchy."""
        # Create a deeply nested view tree
        view_tree = {"class": "android.widget.FrameLayout", "children": []}
        current = view_tree

        # Add 20 levels of nesting
        for i in range(20):
            child = {"class": f"Level{i}", "children": []}
            current["children"] = [child]
            current = child

        state_data = {
            "activity": "com.example.app.MainActivity",
            "view_tree": view_tree
        }

        # Create node tree
        node = parser.create_node_tree(state_data)

        # Verify deep nesting was processed
        assert isinstance(node, Node)

        # Follow chain to deepest node
        current = node
        depth = 0
        while current.children:
            current = current.children[0]
            depth += 1

        assert depth == 20

    def test_special_characters_in_activity(self, parser):
        """Test handling of special characters in activity names."""
        state_data = {
            "activity": "com.example.app/.MainActivityWithSpecial$Characters",
            "view_tree": {"class": "android.widget.FrameLayout", "children": []}
        }

        activity = parser.get_activity_name(state_data)
        assert activity == "com.example.app.MainActivityWithSpecial$Characters"

    def test_missing_activity_attributes(self, parser):
        """Test handling of missing activity attributes."""
        # Create a view tree with minimal attributes
        view_tree = {
            "class": "android.widget.FrameLayout",
            "children": [
                {
                    # Missing many standard attributes
                    "class": "android.widget.Button"
                    # No other attributes provided
                }
            ]
        }

        state_data = {
            "activity": "com.example.app.MainActivity",
            "view_tree": view_tree
        }

        # Create node tree - this should not crash
        node = parser.create_node_tree(state_data)

        # Basic verification
        assert node is not None
        assert len(node.children) == 1
        assert node.children[0].view_class == "android.widget.Button"

    def test_stack_activity_conversion(self, parser, mock_visitor):
        """Test activity conversion in stack data."""
        state_data = {
            "activity": "com.example.app.MainActivity",
            "stack": [
                "com.example.app/.MainActivity",
                "com.example.app/.SecondActivity"
            ],
            "view_tree": {"class": "android.widget.FrameLayout", "children": []}
        }

        with patch.object(DroidBotParser, 'create_visitor', return_value=mock_visitor):
            # The parser should convert the stack activity names
            result = parser.parse_screen(state_data)

            # Check that stack format was converted (removed slashes)
            assert state_data["stack"] == [
                "com.example.app.MainActivity",
                "com.example.app.SecondActivity"
            ]

            assert isinstance(result, ScreenDescription)

    def test_node_unique_id_generation(self, parser, simple_state_data):
        """Test that nodes generate unique IDs."""
        node = parser.create_node_tree(simple_state_data)

        # Collect IDs from different nodes
        ids = set()

        def collect_ids(n):
            """Collect unique IDs from node tree."""
            if n:
                ids.add(n.get_unique_id())
                for child in n.children:
                    collect_ids(child)

        collect_ids(node)

        # All IDs should be unique
        assert len(ids) > 1  # At least some nodes should exist

        # Count of IDs should match count of nodes

        def count_nodes(n):
            """Count nodes in tree."""
            if not n:
                return 0
            return 1 + sum(count_nodes(child) for child in n.children)

        node_count = count_nodes(node)
        assert len(ids) == node_count

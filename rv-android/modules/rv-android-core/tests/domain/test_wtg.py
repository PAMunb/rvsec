# tests/domain/test_wtg.py
"""
Unit tests for the Window Transition Graph module.

This module contains tests for the WindowTransition and WindowTransitionGraph classes
that represent the navigation structure of Android applications.
"""

from unittest.mock import MagicMock

import networkx as nx
import pytest
from rv_android_core.domain.widget import WidgetEventType
from rv_android_core.domain.window import Window
from rv_android_core.domain.wtg import WindowTransition, WindowTransitionGraph


class TestWindowTransition:
    """Tests for the WindowTransition class."""

    def test_init(self):
        """Test WindowTransition initialization with valid parameters."""
        # Arrange
        widget_id = "widget123"
        transition_type = WidgetEventType.CLICK
        method_signature = "com.example.MainActivity.onClick(android.view.View)"

        # Act
        transition = WindowTransition(widget_id, transition_type, method_signature)

        # Assert
        assert transition.widget_id == widget_id
        assert transition.event_type == transition_type
        assert transition.method == method_signature

    def test_to_json(self):
        """Test conversion to JSON representation."""
        # Arrange
        transition = WindowTransition(
            "widget123",
            WidgetEventType.CLICK,
            "com.example.MainActivity.onClick(android.view.View)",
        )

        # Act
        json_output = transition.to_json()

        # Assert
        assert json_output == {
            "widget_id": "widget123",
            "event_type": "CLICK",
            "method": "com.example.MainActivity.onClick(android.view.View)",
        }

    def test_str_representation(self):
        """Test string representation of the WindowTransition."""
        # Arrange
        transition = WindowTransition(
            "widget123",
            WidgetEventType.CLICK,
            "com.example.MainActivity.onClick(android.view.View)",
        )

        # Act
        str_representation = str(transition)

        # Assert
        assert "WindowTransition" in str_representation
        assert "widget_id=widget123" in str_representation
        assert "event_type=WidgetEventType.CLICK" in str_representation
        assert (
            "method=com.example.MainActivity.onClick(android.view.View)"
            in str_representation
        )

    def test_repr_representation(self):
        """Test __repr__ representation of the WindowTransition."""
        # Arrange
        transition = WindowTransition(
            "widget123",
            WidgetEventType.CLICK,
            "com.example.MainActivity.onClick(android.view.View)",
        )

        # Act
        repr_representation = repr(transition)

        # Assert
        assert (
            repr_representation == "com.example.MainActivity.onClick(android.view.View)"
        )


class TestWindowTransitionGraph:
    """Tests for the WindowTransitionGraph class."""

    @pytest.fixture
    def empty_graph(self):
        """Fixture providing an empty WindowTransitionGraph."""
        return WindowTransitionGraph()

    @pytest.fixture
    def mock_window_factory(self):
        """Fixture providing a factory for Window mocks."""

        def _create_window(window_id, name="TestWindow"):
            window = MagicMock(spec=Window)
            window.id = window_id
            window.name = name
            return window

        return _create_window

    @pytest.fixture
    def populated_graph(self, empty_graph, mock_window_factory):
        """Fixture providing a populated WindowTransitionGraph with test data."""
        # Create mock windows
        window1 = mock_window_factory("w1", "MainActivity")
        window2 = mock_window_factory("w2", "SecondActivity")
        window3 = mock_window_factory("w3", "ThirdActivity")

        # Create transitions
        transition1 = WindowTransition(
            "button1", WidgetEventType.CLICK, "com.example.MainActivity.goToSecond()"
        )
        transition2 = WindowTransition(
            "button2", WidgetEventType.CLICK, "com.example.SecondActivity.goToThird()"
        )

        # Add transitions to graph
        empty_graph.add_transition(window1, window2, [transition1])
        empty_graph.add_transition(window2, window3, [transition2])

        return empty_graph

    def test_init(self, empty_graph):
        """Test initialization of the WindowTransitionGraph."""
        assert isinstance(empty_graph.graph, nx.DiGraph)
        assert empty_graph.transitions == []
        assert empty_graph.window_ids == set()

    def test_add_transition(self, empty_graph, mock_window_factory):
        """Test adding a transition between windows."""
        # Arrange
        window1 = mock_window_factory("w1", "MainActivity")
        window2 = mock_window_factory("w2", "SecondActivity")

        transition = WindowTransition(
            "button1", WidgetEventType.CLICK, "com.example.MainActivity.goToSecond()"
        )

        # Act
        empty_graph.add_transition(window1, window2, [transition])

        # Assert
        assert empty_graph.has_window("w1")
        assert empty_graph.has_window("w2")
        assert len(empty_graph.transitions) == 1
        assert empty_graph.transitions[0]["source"] == "w1"
        assert empty_graph.transitions[0]["target"] == "w2"
        assert empty_graph.transitions[0]["widget_id"] == "button1"
        assert empty_graph.transitions[0]["event_type"] == WidgetEventType.CLICK
        assert (
            empty_graph.transitions[0]["method"]
            == "com.example.MainActivity.goToSecond()"
        )

    def test_get_transitions(self, populated_graph):
        """Test getting all transitions in the graph."""
        # Act
        transitions = populated_graph.get_transitions()

        # Assert
        assert len(transitions) == 2
        assert transitions[0]["source"] == "w1"
        assert transitions[0]["target"] == "w2"
        assert transitions[1]["source"] == "w2"
        assert transitions[1]["target"] == "w3"

    def test_has_window(self, populated_graph):
        """Test checking if a window exists in the graph."""
        # Assert
        assert populated_graph.has_window("w1")
        assert populated_graph.has_window("w2")
        assert populated_graph.has_window("w3")
        assert not populated_graph.has_window("nonexistent")

    def test_get_paths_from_window(self, populated_graph):
        """Test getting shortest paths from a source window."""
        # Act
        paths = populated_graph.get_paths_from_window("w1")

        # Assert
        assert "w1" in paths
        assert "w2" in paths
        assert "w3" in paths
        assert paths["w1"] == ["w1"]
        assert paths["w2"] == ["w1", "w2"]
        assert paths["w3"] == ["w1", "w2", "w3"]

        # Test with nonexistent window
        assert populated_graph.get_paths_from_window("nonexistent") == {}

    def test_get_window_transitions(self, populated_graph):
        """Test getting transitions originating from a specific window."""
        # Act
        transitions_w1 = populated_graph.get_window_transitions("w1")
        transitions_w2 = populated_graph.get_window_transitions("w2")

        # Assert
        assert len(transitions_w1) == 1
        assert transitions_w1[0]["source"] == "w1"
        assert transitions_w1[0]["target"] == "w2"

        assert len(transitions_w2) == 1
        assert transitions_w2[0]["source"] == "w2"
        assert transitions_w2[0]["target"] == "w3"

        # Test with nonexistent window
        assert populated_graph.get_window_transitions("nonexistent") == []

    def test_get_path_between_windows(self, populated_graph):
        """Test finding the shortest path between two windows."""
        # Act
        path_1_to_3 = populated_graph.get_path_between_windows("w1", "w3")
        path_2_to_3 = populated_graph.get_path_between_windows("w2", "w3")

        # Assert
        assert path_1_to_3 == ["w1", "w2", "w3"]
        assert path_2_to_3 == ["w2", "w3"]

        # Test with nonexistent window
        assert populated_graph.get_path_between_windows("w1", "nonexistent") == []
        assert populated_graph.get_path_between_windows("nonexistent", "w3") == []

        # Test with unconnected nodes (if we had any)
        # For now, we'll just test with the same node
        assert populated_graph.get_path_between_windows("w1", "w1") == ["w1"]

    def test_to_json(self, populated_graph):
        """Test conversion to JSON representation."""
        # Act
        json_output = populated_graph.to_json()

        # Assert
        assert "graph" in json_output
        assert "windows" in json_output
        assert "transitions_count" in json_output
        assert "transitions" in json_output

        assert json_output["transitions_count"] == 2
        assert len(json_output["windows"]) == 3
        assert "w1" in json_output["windows"]
        assert "w2" in json_output["windows"]
        assert "w3" in json_output["windows"]

        assert len(json_output["graph"]) == 2
        assert json_output["graph"][0]["from_window"] == "w1"
        assert json_output["graph"][0]["to_window"] == "w2"
        assert json_output["graph"][1]["from_window"] == "w2"
        assert json_output["graph"][1]["to_window"] == "w3"

    def test_str_representation(self, populated_graph):
        """Test string representation of the WindowTransitionGraph."""
        # Act
        str_representation = str(populated_graph)

        # Assert
        assert "WindowTransitionGraph" in str_representation
        assert "windows=3" in str_representation
        assert "transitions=2" in str_representation


if __name__ == "__main__":
    pytest.main(["-v"])

import networkx as nx
import pytest

from rvandroid.model.widget import WidgetEventType
from rvandroid.model.window import Window
from rvandroid.model.wtg import WindowTransition, WindowTransitionGraph


class TestWindowTransition:
    """Comprehensive tests for the WindowTransition class"""

    @pytest.fixture
    def sample_transition(self):
        """Create a sample window transition for testing"""
        return WindowTransition(
            widget_id="button1",
            transition_type=WidgetEventType.CLICK,
            method_signature="com.example.app.MainActivity.onClick(android.view.View)"
        )

    def test_window_transition_initialization(self, sample_transition):
        """Test WindowTransition constructor"""
        assert sample_transition.widget_id == "button1"
        assert sample_transition.event_type == WidgetEventType.CLICK
        assert sample_transition.method == "com.example.app.MainActivity.onClick(android.view.View)"

    def test_to_json(self, sample_transition):
        """Test to_json method"""
        json_data = sample_transition.to_json()

        assert json_data["widget_id"] == "button1"
        assert json_data["event_type"] == "CLICK"  # Enum converted to string name
        assert json_data["method"] == "com.example.app.MainActivity.onClick(android.view.View)"

    def test_string_representation(self, sample_transition):
        """Test __str__ method"""
        string_repr = str(sample_transition)

        assert "WindowTransition=" in string_repr
        assert "widget_id=button1" in string_repr
        assert "event_type=" in string_repr
        assert "method=com.example.app.MainActivity.onClick(android.view.View)" in string_repr

    def test_repr(self, sample_transition):
        """Test __repr__ method"""
        assert repr(sample_transition) == "com.example.app.MainActivity.onClick(android.view.View)"

    def test_different_event_types(self):
        """Test creating transitions with different event types"""
        click_transition = WindowTransition(
            "button1", WidgetEventType.CLICK, "com.example.app.onClick()"
        )
        assert click_transition.event_type == WidgetEventType.CLICK

        long_click_transition = WindowTransition(
            "button1", WidgetEventType.LONG_CLICK, "com.example.app.onLongClick()"
        )
        assert long_click_transition.event_type == WidgetEventType.LONG_CLICK

        text_change_transition = WindowTransition(
            "editText1", WidgetEventType.TEXT_CHANGE, "com.example.app.onTextChanged()"
        )
        assert text_change_transition.event_type == WidgetEventType.TEXT_CHANGE


class TestWindowTransitionGraph:
    """Comprehensive tests for the WindowTransitionGraph class"""

    @pytest.fixture
    def sample_graph(self):
        """Create a sample window transition graph for testing"""
        return WindowTransitionGraph()

    @pytest.fixture
    def sample_windows(self):
        """Create sample windows for testing"""
        window1 = Window("MainActivity")
        window1.id = "main_activity"

        window2 = Window("SettingsActivity")
        window2.id = "settings_activity"

        window3 = Window("ProfileActivity")
        window3.id = "profile_activity"

        return window1, window2, window3

    @pytest.fixture
    def sample_transitions(self):
        """Create sample transitions for testing"""
        transition1 = WindowTransition(
            widget_id="settings_button",
            transition_type=WidgetEventType.CLICK,
            method_signature="com.example.app.MainActivity.openSettings()"
        )

        transition2 = WindowTransition(
            widget_id="back_button",
            transition_type=WidgetEventType.CLICK,
            method_signature="com.example.app.SettingsActivity.goBack()"
        )

        transition3 = WindowTransition(
            widget_id="profile_button",
            transition_type=WidgetEventType.CLICK,
            method_signature="com.example.app.MainActivity.openProfile()"
        )

        return [transition1, transition2, transition3]

    def test_window_transition_graph_initialization(self, sample_graph):
        """Test WindowTransitionGraph constructor"""
        assert isinstance(sample_graph.graph, nx.DiGraph)
        assert len(sample_graph.graph.nodes()) == 0
        assert len(sample_graph.graph.edges()) == 0

    def test_add_transition(self, sample_graph, sample_windows, sample_transitions):
        """Test add_transition method"""
        window1, window2, window3 = sample_windows

        # Add transition from window1 to window2
        sample_graph.add_transition(window1, window2, [sample_transitions[0]])

        # Check graph nodes and edges
        assert len(sample_graph.graph.nodes()) == 2
        assert len(sample_graph.graph.edges()) == 1
        assert sample_graph.graph.has_edge(window1, window2)

        # Check edge data
        edge_data = sample_graph.graph.get_edge_data(window1, window2)
        assert "events" in edge_data
        assert len(edge_data["events"]) == 1
        assert edge_data["events"][0] == sample_transitions[0]

        # Add another transition from window2 to window1
        sample_graph.add_transition(window2, window1, [sample_transitions[1]])

        # Check updated graph
        assert len(sample_graph.graph.nodes()) == 2
        assert len(sample_graph.graph.edges()) == 2
        assert sample_graph.graph.has_edge(window2, window1)

        # Add a transition with multiple events
        sample_graph.add_transition(window1, window3, [sample_transitions[0], sample_transitions[2]])

        # Check updated graph
        assert len(sample_graph.graph.nodes()) == 3
        assert len(sample_graph.graph.edges()) == 3
        assert sample_graph.graph.has_edge(window1, window3)

        # Check edge data for multiple events
        edge_data = sample_graph.graph.get_edge_data(window1, window3)
        assert len(edge_data["events"]) == 2
        assert sample_transitions[0] in edge_data["events"]
        assert sample_transitions[2] in edge_data["events"]

    def test_to_json(self, sample_graph, sample_windows, sample_transitions):
        """Test to_json method"""
        window1, window2, _ = sample_windows

        # Add transitions in both directions
        sample_graph.add_transition(window1, window2, [sample_transitions[0]])
        sample_graph.add_transition(window2, window1, [sample_transitions[1]])

        json_data = sample_graph.to_json()

        assert "graph" in json_data
        assert len(json_data["graph"]) == 2  # Two edges

        # Check first edge
        edge1 = json_data["graph"][0]
        assert edge1["from_window"] in [window1.name, window2.name]

        # If first edge is from window1 to window2
        if edge1["from_window"] == window1.name:
            assert edge1["to_window"] == window2.name
            assert len(edge1["events"]) == 1
            assert edge1["events"][0]["widget_id"] == "settings_button"

            # Check second edge
            edge2 = json_data["graph"][1]
            assert edge2["from_window"] == window2.name
            assert edge2["to_window"] == window1.name
            assert len(edge2["events"]) == 1
            assert edge2["events"][0]["widget_id"] == "back_button"

        # If first edge is from window2 to window1
        else:
            assert edge1["to_window"] == window1.name
            assert len(edge1["events"]) == 1
            assert edge1["events"][0]["widget_id"] == "back_button"

            # Check second edge
            edge2 = json_data["graph"][1]
            assert edge2["from_window"] == window1.name
            assert edge2["to_window"] == window2.name
            assert len(edge2["events"]) == 1
            assert edge2["events"][0]["widget_id"] == "settings_button"

    def test_string_representation(self, sample_graph, sample_windows, sample_transitions):
        """Test __str__ method"""
        window1, window2, _ = sample_windows

        # Add a transition
        sample_graph.add_transition(window1, window2, [sample_transitions[0]])

        string_repr = str(sample_graph)

        assert "WindowTransitionGraph=" in string_repr
        assert "graph=" in string_repr

    def test_complex_graph(self, sample_graph, sample_windows, sample_transitions):
        """Test creating a complex graph with multiple windows and transitions"""
        window1, window2, window3 = sample_windows

        # Create a cyclic graph: window1 -> window2 -> window3 -> window1
        sample_graph.add_transition(window1, window2, [sample_transitions[0]])
        sample_graph.add_transition(window2, window3, [sample_transitions[1]])
        sample_graph.add_transition(window3, window1, [sample_transitions[2]])

        # Check the graph structure
        assert len(sample_graph.graph.nodes()) == 3
        assert len(sample_graph.graph.edges()) == 3

        # Verify all expected edges exist
        assert sample_graph.graph.has_edge(window1, window2)
        assert sample_graph.graph.has_edge(window2, window3)
        assert sample_graph.graph.has_edge(window3, window1)

        # Verify the json representation
        json_data = sample_graph.to_json()
        assert len(json_data["graph"]) == 3

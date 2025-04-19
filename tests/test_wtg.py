import pytest
from rvandroid.domain.wtg import WindowTransition, WindowTransitionGraph


def test_window_transition_init():
    window_transition = WindowTransition("widget1", "event_type1", "method1")
    assert window_transition.widget_id == "widget1"
    assert window_transition.event_type == "event_type1"
    assert window_transition.method == "method1"


def test_window_transition_to_json():
    window_transition = WindowTransition("widget1", "event_type1", "method1")
    json_output = window_transition.to_json()
    expected_json = {
        "widget_id": "widget1",
        "event_type": "event_type1",
        "method": "method1"
    }
    assert json_output == expected_json


def test_window_transition_str():
    window_transition = WindowTransition("widget1", "event_type1", "method1")
    str_output = str(window_transition)
    expected_str = f"WindowTransition=[widget_id=widget1, event_type=event_type1, method=method1]"
    assert str_output == expected_str


def test_window_transition_graph_init():
    window_transition_graph = WindowTransitionGraph()
    assert isinstance(window_transition_graph, WindowTransitionGraph)


def test_window_transition_graph_add_transition():
    window_transition_graph = WindowTransitionGraph()
    from_window = Window("window1")
    to_window = Window("window2")
    events = [WindowTransition("widget1", "event_type1", "method1")]
    window_transition_graph.add_transition(from_window, to_window, events)
    assert len(window_transition_graph.transitions) == 1


def test_window_transition_graph_get_transitions():
    window_transition_graph = WindowTransitionGraph()
    from_window = Window("window1")
    to_window = Window("window2")
    events = [WindowTransition("widget1", "event_type1", "method1")]
    window_transition_graph.add_transition(from_window, to_window, events)
    transitions = window_transition_graph.get_transitions()
    assert len(transitions) == 1


def test_window_transition_graph_has_window():
    window_transition_graph = WindowTransitionGraph()
    from_window = Window("window1")
    assert window_transition_graph.has_window(from_window.id)


def test_window_transition_graph_get_paths_from_window():
    window_transition_graph = WindowTransitionGraph()
    from_window = Window("window1")
    to_window = Window("window2")
    events = [WindowTransition("widget1", "event_type1", "method1")]
    window_transition_graph.add_transition(from_window, to_window, events)
    paths = window_transition_graph.get_paths_from_window(from_window.id)
    assert len(paths) == 1


def test_window_transition_graph_to_json():
    window_transition_graph = WindowTransitionGraph()
    json_output = window_transition_graph.to_json()
    expected_json = {
        "graph": [],
        "windows": [],
        "transitions_count": 0,
        "transitions": []
    }
    assert json_output == expected_json


def test_window_transition_graph_str():
    window_transition_graph = WindowTransitionGraph()
    str_output = str(window_transition_graph)
    expected_str = "WindowTransitionGraph=[windows=[], transitions=0]"
    assert str_output == expected_str

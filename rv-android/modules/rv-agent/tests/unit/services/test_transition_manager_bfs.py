"""
Tests for TransitionManager.plan_path_to_mop_activity() BFS (gh26 Group 6, tasks 6.3-6.4).

Verifies BFS on WTG transitions finds paths to activities with MOP methods,
prioritized by MOP density.
"""

from unittest.mock import MagicMock

from rv_agent.services.transition_manager import TransitionManager


def _make_window(window_id, name, activity=""):
    """Create a mock Window object."""
    w = MagicMock()
    w.id = window_id
    w.name = name
    w.activity = activity
    w.widgets = {}
    return w


def _make_method(class_name, name, reaches_target=False, directly_reaches_target=False):
    """Create a mock Method object."""
    m = MagicMock()
    m.class_name = class_name
    m.name = name
    m.reaches_target = reaches_target
    m.directly_reaches_target = directly_reaches_target
    return m


def _make_static_data(windows, methods, transitions):
    """Create mock StaticAnalysisData with WTG, windows, and classes.

    Args:
        windows: List of mock Window objects.
        methods: Dict of {signature: mock_method}.
        transitions: List of transition dicts with source, target, widget_id, etc.
    """
    static_data = MagicMock()

    # Windows
    windows_container = MagicMock()
    windows_container.windows = windows
    static_data.windows = windows_container

    # Classes / methods
    classes = MagicMock()
    classes.methods = methods
    static_data.classes = classes

    # WTG
    wtg = MagicMock()
    wtg.get_window_transitions = lambda wid: [
        t for t in transitions if t.get("source") == wid
    ]
    static_data.wtg = wtg

    return static_data


def _make_transition_manager(windows, methods, transitions):
    """Create TransitionManager with mock static data and graph."""
    static_data = _make_static_data(windows, methods, transitions)
    dynamic_graph = MagicMock()
    dynamic_graph.states = {}
    dynamic_graph.transitions = {}

    tm = TransitionManager(static_data=static_data, dynamic_graph=dynamic_graph)
    return tm


def _make_possible_action(widget_id, text="", coordinates=(100, 200)):
    """Create a mock ItemAction for coordinate resolution tests."""
    action = MagicMock()
    action.widget_id = widget_id
    action.text = text
    action.coordinates = coordinates
    action.target_view = {"class": "android.widget.Button"}
    action.id = 1
    return action


class TestPlanPathToMopActivity:
    """Test BFS to find path to activity with MOP methods."""

    def test_direct_neighbor_with_mop(self):
        """Direct neighbor has MOP methods -- path has 1 step."""
        win_a = _make_window("w1", "ActivityA", activity="com.example.ActivityA")
        win_b = _make_window("w2", "ActivityB", activity="com.example.ActivityB")

        methods = {
            "com.example.ActivityB.doEncrypt": _make_method(
                "com.example.ActivityB", "doEncrypt", reaches_target=True
            ),
        }

        transitions = [
            {
                "source": "w1",
                "target": "w2",
                "widget_id": "btn1",
                "event_type": "click",
            },
        ]

        tm = _make_transition_manager([win_a, win_b], methods, transitions)
        possible_actions = [_make_possible_action("btn1", coordinates=(200, 300))]

        result = tm.plan_path_to_mop_activity(
            "com.example.ActivityA", None, possible_actions=possible_actions
        )

        assert result is not None
        assert len(result) == 1
        assert result[0]["widget_id"] == "btn1"
        assert result[0]["reaches_target"] is True
        assert result[0]["coordinates"] == (200, 300)

    def test_two_hop_path_to_mop(self):
        """MOP activity is 2 hops away via intermediate window."""
        win_a = _make_window("w1", "ActivityA", activity="com.example.ActivityA")
        win_b = _make_window("w2", "ActivityB", activity="com.example.ActivityB")
        win_c = _make_window("w3", "ActivityC", activity="com.example.ActivityC")

        methods = {
            "com.example.ActivityC.decrypt": _make_method(
                "com.example.ActivityC", "decrypt", directly_reaches_target=True
            ),
        }

        transitions = [
            {
                "source": "w1",
                "target": "w2",
                "widget_id": "btn1",
                "event_type": "click",
            },
            {
                "source": "w2",
                "target": "w3",
                "widget_id": "btn2",
                "event_type": "click",
            },
        ]

        tm = _make_transition_manager([win_a, win_b, win_c], methods, transitions)
        # Both btn1 and btn2 must be resolvable on the current screen
        possible_actions = [
            _make_possible_action("btn1", coordinates=(100, 200)),
            _make_possible_action("btn2", coordinates=(300, 400)),
        ]

        result = tm.plan_path_to_mop_activity(
            "com.example.ActivityA", None, possible_actions=possible_actions
        )

        # Group 31 fix: only step 1 is resolved (subsequent steps re-planned on arrival)
        assert result is not None
        assert len(result) == 1
        assert result[0]["widget_id"] == "btn1"

    def test_no_mop_activity_reachable(self):
        """No reachable activity has MOP methods -- returns None."""
        win_a = _make_window("w1", "ActivityA", activity="com.example.ActivityA")
        win_b = _make_window("w2", "ActivityB", activity="com.example.ActivityB")

        methods = {}  # No MOP methods anywhere

        transitions = [
            {
                "source": "w1",
                "target": "w2",
                "widget_id": "btn1",
                "event_type": "click",
            },
        ]

        tm = _make_transition_manager([win_a, win_b], methods, transitions)

        result = tm.plan_path_to_mop_activity("com.example.ActivityA", None)

        assert result is None

    def test_prefers_higher_mop_density(self):
        """Prefers activity with more MOP methods over one with fewer."""
        win_a = _make_window("w1", "ActivityA", activity="com.example.ActivityA")
        win_b = _make_window("w2", "ActivityB", activity="com.example.ActivityB")
        win_c = _make_window("w3", "ActivityC", activity="com.example.ActivityC")

        methods = {
            "com.example.ActivityB.m1": _make_method(
                "com.example.ActivityB", "m1", reaches_target=True
            ),
            "com.example.ActivityC.m1": _make_method(
                "com.example.ActivityC", "m1", reaches_target=True
            ),
            "com.example.ActivityC.m2": _make_method(
                "com.example.ActivityC", "m2", directly_reaches_target=True
            ),
            "com.example.ActivityC.m3": _make_method(
                "com.example.ActivityC", "m3", reaches_target=True
            ),
        }

        # Both B and C reachable directly from A
        transitions = [
            {
                "source": "w1",
                "target": "w2",
                "widget_id": "btn_b",
                "event_type": "click",
            },
            {
                "source": "w1",
                "target": "w3",
                "widget_id": "btn_c",
                "event_type": "click",
            },
        ]

        tm = _make_transition_manager([win_a, win_b, win_c], methods, transitions)
        possible_actions = [
            _make_possible_action("btn_b", coordinates=(100, 200)),
            _make_possible_action("btn_c", coordinates=(300, 400)),
        ]

        result = tm.plan_path_to_mop_activity(
            "com.example.ActivityA", None, possible_actions=possible_actions
        )

        assert result is not None
        assert len(result) == 1
        # Should prefer ActivityC (3 MOP methods) over ActivityB (1 MOP method)
        assert result[0]["widget_id"] == "btn_c"

    def test_no_wtg_returns_none(self):
        """Returns None when WTG is not available."""
        dynamic_graph = MagicMock()
        dynamic_graph.states = {}
        dynamic_graph.transitions = {}
        tm = TransitionManager(static_data=None, dynamic_graph=dynamic_graph)

        result = tm.plan_path_to_mop_activity("com.example.ActivityA", None)

        assert result is None

    def test_unknown_activity_returns_none(self):
        """Returns None when current activity has no window mapping."""
        win_a = _make_window("w1", "ActivityA", activity="com.example.ActivityA")
        methods = {}
        transitions = []

        tm = _make_transition_manager([win_a], methods, transitions)

        result = tm.plan_path_to_mop_activity("com.example.UnknownActivity", None)

        assert result is None

    def test_no_outgoing_transitions(self):
        """Returns None when current window has no outgoing transitions."""
        win_a = _make_window("w1", "ActivityA", activity="com.example.ActivityA")
        methods = {}
        transitions = []  # No transitions at all

        tm = _make_transition_manager([win_a], methods, transitions)

        result = tm.plan_path_to_mop_activity("com.example.ActivityA", None)

        assert result is None

    def test_unresolvable_without_possible_actions(self):
        """Returns None when MOP path exists but no possible_actions for resolution."""
        win_a = _make_window("w1", "ActivityA", activity="com.example.ActivityA")
        win_b = _make_window("w2", "ActivityB", activity="com.example.ActivityB")

        methods = {
            "com.example.ActivityB.doEncrypt": _make_method(
                "com.example.ActivityB", "doEncrypt", reaches_target=True
            ),
        }

        transitions = [
            {
                "source": "w1",
                "target": "w2",
                "widget_id": "btn1",
                "event_type": "click",
            },
        ]

        tm = _make_transition_manager([win_a, win_b], methods, transitions)

        # No possible_actions → can't resolve coordinates → returns None
        result = tm.plan_path_to_mop_activity("com.example.ActivityA", None)
        assert result is None

    def test_unresolvable_widget_id_mismatch(self):
        """Returns None when widget_id doesn't match any possible action."""
        win_a = _make_window("w1", "ActivityA", activity="com.example.ActivityA")
        win_b = _make_window("w2", "ActivityB", activity="com.example.ActivityB")

        methods = {
            "com.example.ActivityB.doEncrypt": _make_method(
                "com.example.ActivityB", "doEncrypt", reaches_target=True
            ),
        }

        transitions = [
            {
                "source": "w1",
                "target": "w2",
                "widget_id": "btn_settings",
                "event_type": "click",
            },
        ]

        tm = _make_transition_manager([win_a, win_b], methods, transitions)
        # possible_actions has different widget_id and text doesn't match
        possible_actions = [
            _make_possible_action("other_btn", text="Home", coordinates=(100, 200))
        ]

        result = tm.plan_path_to_mop_activity(
            "com.example.ActivityA", None, possible_actions=possible_actions
        )
        assert result is None

    def test_resolves_via_activity_name_in_text(self):
        """Resolves WTG action via target activity simple name in action text."""
        win_a = _make_window("w1", "ActivityA", activity="com.example.ActivityA")
        win_b = _make_window("w2", "ActivityB", activity="com.example.EncryptActivity")

        methods = {
            "com.example.EncryptActivity.doEncrypt": _make_method(
                "com.example.EncryptActivity", "doEncrypt", reaches_target=True
            ),
        }

        transitions = [
            {
                "source": "w1",
                "target": "w2",
                "widget_id": "unknown_widget",
                "event_type": "click",
            },
        ]

        tm = _make_transition_manager([win_a, win_b], methods, transitions)
        # Text contains "encryptactivity" (case-insensitive match)
        possible_actions = [
            _make_possible_action(
                "btn_encrypt", text="Open EncryptActivity", coordinates=(500, 600)
            )
        ]

        result = tm.plan_path_to_mop_activity(
            "com.example.ActivityA", None, possible_actions=possible_actions
        )
        assert result is not None
        assert result[0]["coordinates"] == (500, 600)


class TestCountMopMethodsForActivity:
    """Test _count_mop_methods_for_activity helper."""

    def test_counts_reaches_and_direct(self):
        """Counts both reaches_target and directly_reaches_target methods."""
        win_a = _make_window("w1", "ActivityA", activity="com.example.ActivityA")

        methods = {
            "com.example.ActivityA.m1": _make_method(
                "com.example.ActivityA", "m1", reaches_target=True
            ),
            "com.example.ActivityA.m2": _make_method(
                "com.example.ActivityA", "m2", directly_reaches_target=True
            ),
            "com.example.ActivityA.m3": _make_method(
                "com.example.ActivityA",
                "m3",
                reaches_target=False,
                directly_reaches_target=False,
            ),
            "com.example.Other.m4": _make_method(
                "com.example.Other", "m4", reaches_target=True
            ),
        }

        tm = _make_transition_manager([win_a], methods, [])

        count = tm._count_mop_methods_for_activity("com.example.ActivityA")

        assert count == 2  # m1 (reaches) + m2 (directly)

    def test_no_static_data_returns_zero(self):
        """Returns 0 when no static data."""
        dynamic_graph = MagicMock()
        dynamic_graph.states = {}
        dynamic_graph.transitions = {}
        tm = TransitionManager(static_data=None, dynamic_graph=dynamic_graph)

        count = tm._count_mop_methods_for_activity("com.example.ActivityA")

        assert count == 0

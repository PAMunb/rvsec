"""
Unit tests for Group 36 data matching fixes.

Covers four bug fixes applied in gh26:

(a) Action description keys: transition_manager uses underscored keys
    (content_description, resource_id) instead of hyphenated ones
    (content-desc, resource-id).

(b) Widget_id matching: _find_action_by_widget_id and _resolve_wtg_action
    use equality (==), not substring (in).

(c) Self-loop guard in RVAgentStrategy.record_transition(): transitions
    where from_hash == to_hash skip graph/successor recording but still
    update the plateau detector.

(d) UICoverageTracker.find_nearest_element() returns None for an unknown
    screen_hash instead of falling back to a global element search.

(e) RVTRACK:SELF_LOOP is emitted when a self-loop transition is detected.

(f) RVTRACK:ELEMENT_MATCH logs cross_screen_rejected for unknown screen.
"""

import logging
from unittest.mock import MagicMock

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.element_id import make_element_id
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.services.transition_manager import TransitionManager
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy

# ---------------------------------------------------------------------------
# Shared helpers (mirrors test_plateau_detection_fix.py conventions)
# ---------------------------------------------------------------------------


def _make_config(**overrides):
    """Create a minimal mock config for RVAgentStrategy."""
    config = MagicMock()
    config.seed = None
    config.plateau_window = 10
    config.max_input_variations = 3
    config.mop_max_input_variations = 11
    config.stochastic_probability = 0.15
    config.stochastic_temperature = 1.0
    config.package_name = "com.test.app"
    config.device_dimensions = (1080, 1920)
    config.scroll_probability = 0.15
    config.backtrack_saturation_threshold = 0.8
    config.max_re_enables = 6
    config.ui_coverage_threshold = 0.9
    config.mop_direct_score = 500.0
    config.mop_transitive_score = 300.0
    config.wtg_guided_score = 150.0
    config.unsaturated_bonus = 100.0
    config.visitation_penalty_factor = -15.0
    config.strength_weight = 50.0
    config.gradual_decay_base = 200.0
    config.gradual_decay_rate = 0.7
    config.gradual_decay_min_visits = 5
    config.component_high_priority = 50.0
    config.component_medium_priority = 40.0
    config.reward_gamma = 0.8
    config.reward_score_weight = 1.0
    config.coverage_density_weight = 200.0
    for k, v in overrides.items():
        setattr(config, k, v)
    return config


def _make_strategy():
    """Build a minimal RVAgentStrategy with a real graph and coverage tracker."""
    config = _make_config()
    graph = DynamicStateGraph()
    ui_coverage = UICoverageTracker()
    return RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)


def _make_screen_desc(activity=".MainActivity"):
    """Create a mock ScreenDescription with one clickable action."""
    desc = MagicMock()
    desc.activity = activity
    action = MagicMock()
    action.coordinates = (540, 960)
    action.coords_for_matching = ((540, 960), "CLICK")
    action.event = MagicMock()
    action.event.name = "CLICK"
    action.event.value = 1
    action.text = "Button"
    action.target_view = {
        "class": "android.widget.Button",
        "package": "com.test.app",
        "bounds": [[490, 910], [590, 1010]],
    }
    action.widget_id = "btn_main"
    action.reaches_mop = False
    action.directly_reaches_mop = False
    action.callback_signature = None
    action.text_input = None
    mock_item = MagicMock()
    mock_item.view = {"package": "com.test.app"}
    mock_item.actions = [action]
    desc.items = [mock_item]
    desc.get_all_actions.return_value = [action]
    return desc


# ---------------------------------------------------------------------------
# (a) Action description uses underscored dict keys
# ---------------------------------------------------------------------------


class TestActionDescriptionKeys:
    """_get_action_description reads content_description and resource_id (underscored)."""

    def _make_transition_manager(self):
        static_data = MagicMock()
        static_data.wtg = None
        static_data.windows = None
        dynamic_graph = DynamicStateGraph()
        return TransitionManager(static_data=static_data, dynamic_graph=dynamic_graph)

    def test_content_description_key_is_read(self):
        """_get_action_description returns the value stored under content_description."""
        tm = self._make_transition_manager()

        action = MagicMock()
        action.text = "fallback"
        action.target_view = {"content_description": "Settings button"}

        result = tm._get_action_description(action)

        assert result == "Settings button"

    def test_hyphenated_content_desc_is_not_read(self):
        """content-desc (hyphenated) is NOT recognised; falls through to text."""
        tm = self._make_transition_manager()

        action = MagicMock()
        action.text = "fallback_text"
        action.target_view = {"content-desc": "Should not match"}

        result = tm._get_action_description(action)

        # content-desc is not the expected key — result should fall through
        assert result != "Should not match"

    def test_resource_id_key_is_read(self):
        """_get_action_description extracts the short name from resource_id."""
        tm = self._make_transition_manager()

        action = MagicMock()
        action.text = "fallback"
        action.target_view = {"resource_id": "com.example:id/button_save"}

        result = tm._get_action_description(action)

        assert result == "button save"

    def test_hyphenated_resource_id_is_not_read(self):
        """resource-id (hyphenated) is NOT recognised; falls through to class name."""
        tm = self._make_transition_manager()

        action = MagicMock()
        action.text = "fallback_text"
        action.target_view = {
            "resource-id": "com.example:id/button_save",
            "class": "android.widget.Button",
        }

        result = tm._get_action_description(action)

        # resource-id is not the expected key; result should not contain "button"
        assert "button_save" not in result


# ---------------------------------------------------------------------------
# (b) Widget_id matching uses equality, not substring
# ---------------------------------------------------------------------------


class TestWidgetIdEqualityMatching:
    """_find_action_by_widget_id and _resolve_wtg_action use ==, not 'in'."""

    def _make_transition_manager(self):
        static_data = MagicMock()
        static_data.wtg = None
        static_data.windows = None
        dynamic_graph = DynamicStateGraph()
        return TransitionManager(static_data=static_data, dynamic_graph=dynamic_graph)

    def _make_action_with_widget_id(self, widget_id: str):
        action = MagicMock()
        action.widget_id = widget_id
        action.coordinates = (100, 200)
        action.text = "Button"
        action.target_view = {"content_description": ""}
        return action

    def test_exact_widget_id_matches(self):
        """Exact widget_id match returns the action."""
        tm = self._make_transition_manager()

        target_action = self._make_action_with_widget_id("2131755177")
        screen_desc = MagicMock()
        screen_desc.events_by_id = {"1": target_action}

        result = tm._find_action_by_widget_id("2131755177", screen_desc)

        assert result is target_action

    def test_partial_widget_id_does_not_match(self):
        """A widget_id that is only a prefix is rejected by equality check."""
        tm = self._make_transition_manager()

        # Action has the full id; lookup uses a partial id that would match with 'in'
        target_action = self._make_action_with_widget_id("2131755177")
        screen_desc = MagicMock()
        screen_desc.events_by_id = {"1": target_action}

        # "213175" is a substring of "2131755177", but not equal
        result = tm._find_action_by_widget_id("213175", screen_desc)

        assert result is None

    def test_different_widget_id_does_not_match(self):
        """Non-matching widget_id returns None."""
        tm = self._make_transition_manager()

        target_action = self._make_action_with_widget_id("2131755177")
        screen_desc = MagicMock()
        screen_desc.events_by_id = {"1": target_action}

        result = tm._find_action_by_widget_id("9999999999", screen_desc)

        assert result is None

    def test_resolve_wtg_action_equality_match(self):
        """_resolve_wtg_action Strategy 1 uses == for widget_id matching."""
        tm = self._make_transition_manager()

        exact_action = self._make_action_with_widget_id("2131755177")
        # An action whose widget_id contains the target id as a substring
        substring_action = self._make_action_with_widget_id("2131755177_extra")

        # Only exact_action should match "2131755177"
        result = tm._resolve_wtg_action(
            wtg_widget_id="2131755177",
            target_activity=None,
            possible_actions=[substring_action, exact_action],
        )

        assert result is exact_action

    def test_resolve_wtg_action_no_substring_match(self):
        """_resolve_wtg_action does not match when id is only a substring."""
        tm = self._make_transition_manager()

        action = self._make_action_with_widget_id("2131755177_extended")

        result = tm._resolve_wtg_action(
            wtg_widget_id="2131755177",
            target_activity=None,
            possible_actions=[action],
        )

        # Strategy 1 (equality) fails; Strategies 2/3 fall back to activity name
        # matching — with target_activity=None those also fail.
        assert result is None


# ---------------------------------------------------------------------------
# (c) Self-loop guard: graph/successor recording skipped for same-hash transitions
# ---------------------------------------------------------------------------


class TestSelfLoopGuard:
    """record_transition() skips graph recording when from_hash == to_hash."""

    def test_self_loop_does_not_record_graph_transition(self):
        """A self-loop transition does not add an edge to the dynamic state graph."""
        strategy = _make_strategy()

        screen_desc = _make_screen_desc()
        strategy.select_next_action("state_A", screen_desc)

        initial_transition_count = len(strategy.graph.transitions)

        action_sig = ((540, 960), "CLICK")
        strategy.record_transition("state_A", "state_A", action_sig)

        # No new transition should have been recorded
        assert len(strategy.graph.transitions) == initial_transition_count

    def test_self_loop_does_not_record_successor(self):
        """A self-loop transition does not add a successor mapping."""
        strategy = _make_strategy()

        screen_desc = _make_screen_desc()
        strategy.select_next_action("state_A", screen_desc)

        initial_successors = dict(strategy.successor_tracker.successors)

        action_sig = ((540, 960), "CLICK")
        strategy.record_transition("state_A", "state_A", action_sig)

        # successor_tracker.successors should not have grown
        assert strategy.successor_tracker.successors == initial_successors

    def test_self_loop_still_updates_plateau_detector(self):
        """Plateau detector records every iteration including self-loops."""
        strategy = _make_strategy()

        screen_desc = _make_screen_desc()
        strategy.select_next_action("state_A", screen_desc)

        action_sig = ((540, 960), "CLICK")
        strategy.record_transition("state_A", "state_A", action_sig)

        # PlateauDetector.total_iterations must be at least 1
        assert strategy.plateau_detector.total_iterations >= 1

    def test_regular_transition_does_record_graph_entry(self):
        """A transition between different states does record a graph edge."""
        strategy = _make_strategy()

        screen_desc_a = _make_screen_desc(activity=".ActivityA")
        screen_desc_b = _make_screen_desc(activity=".ActivityB")

        strategy.select_next_action("state_A", screen_desc_a)
        strategy.select_next_action("state_B", screen_desc_b)

        before = len(strategy.graph.transitions)
        action_sig = ((540, 960), "CLICK")
        strategy.record_transition("state_A", "state_B", action_sig)

        assert len(strategy.graph.transitions) > before


# ---------------------------------------------------------------------------
# (d) find_nearest_element returns None for unknown screen_hash
# ---------------------------------------------------------------------------


class TestFindNearestElementUnknownScreen:
    """UICoverageTracker.find_nearest_element() returns None for unknown screen."""

    def _tracker_with_element(self, screen_hash: str, x: int, y: int):
        """Helper: create tracker with one registered element at (x, y)."""
        tracker = UICoverageTracker()
        element_id = make_element_id(x, y)
        tracker.element_types[element_id] = "Button"
        tracker.screen_elements[screen_hash] = {element_id}
        return tracker

    def test_unknown_screen_returns_none(self):
        """find_nearest_element with an unknown screen_hash returns None."""
        tracker = self._tracker_with_element("known_screen", 540, 960)

        result = tracker.find_nearest_element(
            x=540, y=960, screen_hash="unknown_screen"
        )

        assert result is None

    def test_known_screen_returns_match(self):
        """find_nearest_element with a known screen_hash returns the nearest element."""
        tracker = self._tracker_with_element("known_screen", 540, 960)

        result = tracker.find_nearest_element(x=540, y=960, screen_hash="known_screen")

        assert result is not None
        element_id, comp_type, distance = result
        assert distance == 0.0

    def test_no_screen_hash_falls_back_to_global(self):
        """find_nearest_element with screen_hash=None searches all registered elements."""
        tracker = self._tracker_with_element("some_screen", 100, 200)

        # No screen_hash specified — should search globally
        result = tracker.find_nearest_element(x=100, y=200, screen_hash=None)

        assert result is not None

    def test_unknown_screen_does_not_match_element_from_other_screen(self):
        """An element registered on screen A is not found when searching screen B."""
        tracker = self._tracker_with_element("screen_A", 540, 960)

        # screen_B is unknown; element at (540, 960) belongs to screen_A only
        result = tracker.find_nearest_element(x=540, y=960, screen_hash="screen_B")

        assert result is None


# ---------------------------------------------------------------------------
# (e) RVTRACK:SELF_LOOP is emitted when a self-loop is detected
# ---------------------------------------------------------------------------


class TestSelfLoopTrackingLog:
    """record_transition() emits [RVTRACK:SELF_LOOP] for same-hash transitions."""

    def test_self_loop_emits_rvtrack_self_loop(self, caplog):
        """A self-loop triggers a RVTRACK:SELF_LOOP log line."""
        strategy = _make_strategy()

        screen_desc = _make_screen_desc()
        strategy.select_next_action("state_A", screen_desc)

        action_sig = ((540, 960), "CLICK")
        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            strategy.record_transition("state_A", "state_A", action_sig)

        assert any("RVTRACK:SELF_LOOP" in r.message for r in caplog.records)

    def test_regular_transition_does_not_emit_self_loop(self, caplog):
        """A transition between different states does NOT emit RVTRACK:SELF_LOOP."""
        strategy = _make_strategy()

        screen_desc_a = _make_screen_desc(activity=".ActivityA")
        screen_desc_b = _make_screen_desc(activity=".ActivityB")
        strategy.select_next_action("state_A", screen_desc_a)
        strategy.select_next_action("state_B", screen_desc_b)

        action_sig = ((540, 960), "CLICK")
        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            strategy.record_transition("state_A", "state_B", action_sig)

        assert not any("RVTRACK:SELF_LOOP" in r.message for r in caplog.records)

    def test_self_loop_increments_counter(self):
        """Each self-loop increments the self_loop_skipped aggregate counter."""
        import rv_agent.tracking as track

        track.reset_counters()
        strategy = _make_strategy()

        screen_desc = _make_screen_desc()
        strategy.select_next_action("state_A", screen_desc)

        action_sig = ((540, 960), "CLICK")
        strategy.record_transition("state_A", "state_A", action_sig)

        counters = track.get_aggregate_counters()
        assert counters["self_loop_skipped"] >= 1


# ---------------------------------------------------------------------------
# (f) RVTRACK:ELEMENT_MATCH logs cross_screen_rejected for unknown screen
# ---------------------------------------------------------------------------


class TestElementMatchTrackingLog:
    """find_nearest_element() emits RVTRACK:ELEMENT_MATCH cross_screen_rejected."""

    def test_unknown_screen_emits_cross_screen_rejected(self, caplog):
        """Searching an unknown screen emits ELEMENT_MATCH cross_screen_rejected."""
        tracker = UICoverageTracker()
        element_id = make_element_id(540, 960)
        tracker.element_types[element_id] = "Button"
        tracker.screen_elements["known_screen"] = {element_id}

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            result = tracker.find_nearest_element(
                x=540, y=960, screen_hash="unknown_screen"
            )

        assert result is None
        assert any(
            "RVTRACK:ELEMENT_MATCH" in r.message
            and "cross_screen_rejected" in r.message
            for r in caplog.records
        )

    def test_known_screen_does_not_emit_cross_screen_rejected(self, caplog):
        """Searching a known screen does NOT emit cross_screen_rejected."""
        tracker = UICoverageTracker()
        element_id = make_element_id(540, 960)
        tracker.element_types[element_id] = "Button"
        tracker.screen_elements["known_screen"] = {element_id}

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            tracker.find_nearest_element(x=540, y=960, screen_hash="known_screen")

        assert not any("cross_screen_rejected" in r.message for r in caplog.records)

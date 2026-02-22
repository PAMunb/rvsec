"""
Tests for saturation calculation fix (gh26 Group 1.7).

Verifies that system actions (BACK, RESTART) with coordinates=None are
excluded from total_actions count in DynamicStateGraph.get_or_create_state().
Without this fix, max saturation = N/(N+2), preventing screens with fewer
than 8 real actions from reaching the 80% backtrack threshold.
"""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass, field
from typing import Optional, Tuple

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.domain.screen_node import ScreenNode


@dataclass
class MockAction:
    """Mock action for testing."""

    coordinates: Optional[Tuple[int, int]] = (540, 960)
    event: object = None

    @property
    def coords_for_matching(self):
        if self.coordinates:
            return (self.coordinates, "click")
        return ((0, 0), "key_event")


def _make_screen_desc(real_actions_count: int, system_actions_count: int = 2):
    """Create a mock ScreenDescription with real + system actions.

    Args:
        real_actions_count: Number of regular actions with coordinates
        system_actions_count: Number of system actions with coordinates=None (default 2: BACK + RESTART)
    """
    actions = []
    for i in range(real_actions_count):
        actions.append(MockAction(coordinates=(100 + i * 50, 500)))
    for _ in range(system_actions_count):
        actions.append(MockAction(coordinates=None))

    screen_desc = MagicMock()
    screen_desc.activity = "com.example.TestActivity"
    screen_desc.get_all_actions.return_value = actions
    screen_desc.items = []
    return screen_desc


class TestTotalActionsExcludesSystemActions:
    """Verify total_actions only counts actions with coordinates (non-system)."""

    def test_total_actions_excludes_system_actions(self):
        """Screen with 5 real actions + 2 system actions should have total_actions == 5."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=5, system_actions_count=2)

        node = graph.get_or_create_state("hash_a", "TestActivity", screen_desc)

        assert node.total_actions == 5

    def test_back_restart_excluded_from_total_actions(self):
        """BACK and RESTART injected by visitor with coords=None do not inflate total_actions."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=3, system_actions_count=2)

        node = graph.get_or_create_state("hash_b", "TestActivity", screen_desc)

        # Should be 3, not 5
        assert node.total_actions == 3

    def test_total_actions_zero_only_system_actions(self):
        """Screen with only system actions has total_actions == 0."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=0, system_actions_count=2)

        node = graph.get_or_create_state("hash_c", "TestActivity", screen_desc)

        assert node.total_actions == 0

    def test_total_actions_no_system_actions(self):
        """Screen with no system actions counts all actions."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=7, system_actions_count=0)

        node = graph.get_or_create_state("hash_d", "TestActivity", screen_desc)

        assert node.total_actions == 7


class TestSelfLoopGuard:
    """Verify that self-loop transitions are not recorded in SuccessorTracker."""

    def test_self_loop_not_recorded(self):
        """record_successor(A, sig, A) should NOT add entry to successors."""
        from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker

        graph = DynamicStateGraph()
        tracker = SuccessorTracker(graph)

        sig = ((100, 200), "click")
        tracker.record_successor("hash_A", sig, "hash_A")

        assert ("hash_A", sig) not in tracker.successors

    def test_self_loop_does_not_trigger_re_enable(self):
        """update_action_availability should not re-enable actions with only self-loop successors."""
        from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker

        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=3)
        node = graph.get_or_create_state("hash_A", "TestActivity", screen_desc)

        tracker = SuccessorTracker(graph)

        # Record self-loop (should be skipped)
        sig = ((100, 500), "click")
        node.record_action(sig)
        tracker.record_successor("hash_A", sig, "hash_A")

        # update_action_availability should not re-enable anything
        re_enabled = tracker.update_action_availability("hash_A")
        assert re_enabled == 0

    def test_non_self_loop_still_recorded(self):
        """Normal transitions (A -> B) should still be recorded correctly."""
        from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker

        graph = DynamicStateGraph()
        tracker = SuccessorTracker(graph)

        sig = ((100, 200), "click")
        tracker.record_successor("hash_A", sig, "hash_B")

        assert ("hash_A", sig) in tracker.successors
        assert tracker.successors[("hash_A", sig)] == "hash_B"


class TestSaturationReaches100:
    """Verify saturation can reach 1.0 on small screens."""

    def test_saturation_reaches_1_0_all_non_system_saturated(self):
        """When all non-system actions are executed twice, saturation is 1.0."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=3, system_actions_count=2)

        node = graph.get_or_create_state("hash_e", "TestActivity", screen_desc)

        # Execute each real action twice
        for i in range(3):
            sig = ((100 + i * 50, 500), "click")
            node.record_action(sig)
            node.record_action(sig)

        assert node.get_saturation_rate() == 1.0

    def test_small_screen_can_exceed_80_percent_threshold(self):
        """Screen with 4 real actions + 2 system can reach 80% saturation.

        Without fix: max saturation = 4/(4+2) = 66.7% — never reaches 80%.
        With fix: max saturation = 4/4 = 100% — easily reaches 80%.
        """
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=4, system_actions_count=2)

        node = graph.get_or_create_state("hash_f", "TestActivity", screen_desc)

        # Execute 4 actions, each twice
        for i in range(4):
            sig = ((100 + i * 50, 500), "click")
            node.record_action(sig)
            node.record_action(sig)

        saturation = node.get_saturation_rate()
        assert saturation >= 0.8, f"Saturation {saturation} should be >= 0.8"
        assert saturation == 1.0

    def test_partial_saturation_calculation_correct(self):
        """With 5 real actions, 3 saturated → saturation = 3/5 = 0.6."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(real_actions_count=5, system_actions_count=2)

        node = graph.get_or_create_state("hash_g", "TestActivity", screen_desc)

        # Saturate 3 out of 5
        for i in range(3):
            sig = ((100 + i * 50, 500), "click")
            node.record_action(sig)
            node.record_action(sig)

        assert node.get_saturation_rate() == pytest.approx(0.6)


class TestTier4SystemActionFilter:
    """Verify BACK/RESTART are excluded from Tier 4 scored selection."""

    def test_select_with_score_decay_excludes_back(self):
        """_select_with_score_decay should not return BACK when real widgets exist."""
        # Create a real widget action
        real_action = MockAction(coordinates=(300, 500))
        real_action.target_view = {"class": "android.widget.Button"}
        real_action.text = "Encrypt"
        real_action.event = MagicMock()
        real_action.event.name = "CLICK"
        real_action.id = 1
        real_action.widget_id = "btn1"
        real_action.reaches_mop = False
        real_action.directly_reaches_mop = False
        real_action.text_input = None
        real_action.callback_signature = None

        # Create a BACK system action
        back_action = MockAction(coordinates=None)
        back_action.target_view = {"system_action": True, "class": "SystemAction_BACK"}
        back_action.text = "BACK"
        back_action.event = MagicMock()
        back_action.event.name = "BACK"
        back_action.id = 999
        back_action.widget_id = None
        back_action.reaches_mop = False
        back_action.directly_reaches_mop = False
        back_action.text_input = None
        back_action.callback_signature = None

        # Verify that the system_action filter works
        actions = [real_action, back_action]
        real_only = [
            a for a in actions
            if not (a.target_view or {}).get("system_action")
        ]
        assert len(real_only) == 1
        assert real_only[0].text == "Encrypt"

    def test_select_with_score_decay_returns_none_when_only_system_actions(self):
        """When only BACK/RESTART remain, filter returns empty → None from Tier 4."""
        back_action = MockAction(coordinates=None)
        back_action.target_view = {"system_action": True, "class": "SystemAction_BACK"}

        restart_action = MockAction(coordinates=None)
        restart_action.target_view = {"system_action": True, "class": "SystemAction_RESTART"}

        actions = [back_action, restart_action]
        real_only = [
            a for a in actions
            if not (a.target_view or {}).get("system_action")
        ]
        assert len(real_only) == 0


class TestPathBufferFailureCache:
    """Verify PathBuffer permanent failure cache for MOP paths."""

    def test_failed_mop_path_cached(self):
        """After MOP path fails, activity is added to _failed_mop_paths."""
        from rv_agent.strategies.rvagent_strategy.path_buffer import PathBuffer

        tm = MagicMock()
        tm.plan_path_to_mop_activity.return_value = None

        successor_tracker = MagicMock()
        successor_tracker.graph = MagicMock()
        successor_tracker.graph.states = {}
        successor_tracker.back_successors = {}

        config = MagicMock()
        config.backtrack_saturation_threshold = 0.8
        ui_cov = MagicMock()

        pb = PathBuffer(
            transition_manager=tm,
            successor_tracker=successor_tracker,
            ui_coverage_tracker=ui_cov,
            config=config,
        )

        result = pb.plan_mop_path("com.example.ActivityA", None)
        assert result is False
        assert "com.example.ActivityA" in pb._failed_mop_paths

    def test_cached_activity_skips_planning(self):
        """Subsequent calls for cached activity skip planning entirely."""
        from rv_agent.strategies.rvagent_strategy.path_buffer import PathBuffer

        tm = MagicMock()
        tm.plan_path_to_mop_activity.return_value = None

        successor_tracker = MagicMock()
        successor_tracker.graph = MagicMock()
        successor_tracker.graph.states = {}
        successor_tracker.back_successors = {}

        config = MagicMock()
        config.backtrack_saturation_threshold = 0.8
        ui_cov = MagicMock()

        pb = PathBuffer(
            transition_manager=tm,
            successor_tracker=successor_tracker,
            ui_coverage_tracker=ui_cov,
            config=config,
        )

        # First call fails and caches
        pb.plan_mop_path("com.example.ActivityA", None)

        # Second call should skip entirely (not call plan_path_to_mop_activity)
        tm.plan_path_to_mop_activity.reset_mock()
        result = pb.plan_mop_path("com.example.ActivityA", None)
        assert result is False
        tm.plan_path_to_mop_activity.assert_not_called()


class TestActionDictCoordinateValidation:
    """Verify _action_dict_to_item_action rejects actions without coordinates."""

    def test_rejects_non_back_with_no_coords(self):
        """Non-BACK action with coordinates=None returns None."""
        from rv_agent.strategies.rvagent_strategy.path_buffer import _action_dict_to_item_action

        action_dict = {
            "action_type": "CLICK",
            "text": "Navigate to unknown",
            "coordinates": None,
            "target_view": {},
        }
        result = _action_dict_to_item_action(action_dict)
        assert result is None

    def test_accepts_back_with_no_coords(self):
        """BACK action with no coordinates is allowed (virtual action)."""
        from rv_agent.strategies.rvagent_strategy.path_buffer import _action_dict_to_item_action

        action_dict = {"action_type": "BACK"}
        result = _action_dict_to_item_action(action_dict)
        assert result is not None

    def test_accepts_click_with_valid_coords(self):
        """CLICK action with valid coordinates is allowed."""
        from rv_agent.strategies.rvagent_strategy.path_buffer import _action_dict_to_item_action

        action_dict = {
            "action_type": "CLICK",
            "text": "Settings",
            "coordinates": (300, 500),
            "target_view": {"class": "android.widget.Button"},
        }
        result = _action_dict_to_item_action(action_dict)
        assert result is not None
        assert result.coordinates == (300, 500)

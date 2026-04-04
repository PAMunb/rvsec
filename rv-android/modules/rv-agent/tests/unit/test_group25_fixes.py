"""
Tests for Group 25 bug fixes (gh26).

Covers four related fixes:
(a) H4: key_event excluded from saturation rate
(b) MopScorer scores based on MOP reachability (deferral dead code removed)
(c) M1: _has_untested_inputs uses make_element_id_from_tuple format
(d) H5: forced_back_count increments only once per forced-back event
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from unittest.mock import MagicMock

import pytest
from rv_agent.domain.screen_node import ScreenNode
from rv_agent.memory.element_id import make_element_id_from_tuple
from rv_agent.strategies.rvagent_strategy.ranking.context import RankingContext
from rv_agent.strategies.rvagent_strategy.ranking.scorers import MopScorer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class MockAction:
    """Minimal mock action for testing."""

    coordinates: Optional[Tuple[int, int]] = (540, 960)
    event: object = None
    action_type: str = "click"
    widget_id: Optional[str] = None
    reaches_mop: bool = False
    directly_reaches_mop: bool = False
    target_view: Optional[dict] = None

    @property
    def coords_for_matching(self):
        if self.coordinates:
            return (self.coordinates, "click")
        return ((0, 0), "key_event")


# ---------------------------------------------------------------------------
# (a) H4: key_event excluded from saturation numerator
# ---------------------------------------------------------------------------


class TestKeyEventExcludedFromSaturation:
    """Verify that actions with 'key_event' type do not inflate saturation rate."""

    def test_key_event_in_system_action_types(self):
        """SYSTEM_ACTION_TYPES includes 'key_event'."""
        assert "key_event" in ScreenNode.SYSTEM_ACTION_TYPES

    def test_saturation_excludes_key_event_actions(self):
        """Actions with type 'key_event' are excluded from the saturated count.

        Scenario: 2 real click actions + 1 key_event action. Both click actions
        are saturated. Saturation should be 2/2 = 1.0, not 3/2 (inflated by
        counting the key_event in the numerator).
        """
        node = ScreenNode(screen_hash="test_h4", activity="TestActivity")
        # total_actions counts only real (non-system) actions in the denominator.
        # Here we set it to 2 to represent 2 real click actions.
        node.total_actions = 2

        # Record two real click actions, each executed twice (saturated at threshold 2)
        click_sig_1 = ((100, 200), "click")
        click_sig_2 = ((300, 400), "click")
        node.record_action(click_sig_1)
        node.record_action(click_sig_1)
        node.record_action(click_sig_2)
        node.record_action(click_sig_2)

        # Record a key_event action (BACK), also executed twice
        key_event_sig = ((0, 0), "key_event")
        node.record_action(key_event_sig)
        node.record_action(key_event_sig)

        saturation = node.get_saturation_rate()
        # key_event should be excluded from saturated count.
        # saturated_count = 2 (only the two click sigs), total_actions = 2
        assert saturation == pytest.approx(1.0)

    def test_only_key_event_actions_gives_full_saturation(self):
        """If total_actions is 0 (no real actions), saturation is 1.0 (fully saturated)."""
        node = ScreenNode(screen_hash="test_h4b", activity="TestActivity")
        node.total_actions = 0

        key_event_sig = ((0, 0), "key_event")
        node.record_action(key_event_sig)

        assert node.get_saturation_rate() == 1.0


# ---------------------------------------------------------------------------
# (b) MopScorer scores based on MOP reachability (deferral dead code removed)
# ---------------------------------------------------------------------------


class TestMopScorerScoring:
    """MopScorer scores based on MOP reachability flags.

    The original deferral logic checked action.action_type, which doesn't
    exist on ItemAction — it was dead code and has been removed.
    """

    def test_direct_mop_scores_regardless_of_untested_inputs(self):
        """directly_reaches_mop=True gets full score even with untested inputs."""
        scorer = MopScorer()

        action = MockAction(directly_reaches_mop=True)

        context = MagicMock(spec=RankingContext)
        context.has_untested_inputs = True

        score = scorer.score(action, context)
        assert score == MopScorer.DEFAULT_DIRECT_SCORE

    def test_transitive_mop_scores_normally(self):
        """reaches_mop=True gets transitive score."""
        scorer = MopScorer()

        action = MockAction(reaches_mop=True)

        context = MagicMock(spec=RankingContext)
        context.has_untested_inputs = True

        score = scorer.score(action, context)
        assert score == MopScorer.DEFAULT_TRANSITIVE_SCORE

    def test_non_mop_returns_zero(self):
        """Non-MOP actions return 0.0."""
        scorer = MopScorer()

        action = MockAction()

        context = MagicMock(spec=RankingContext)
        context.has_untested_inputs = False

        score = scorer.score(action, context)
        assert score == 0.0


# ---------------------------------------------------------------------------
# (c) M1: _has_untested_inputs uses make_element_id_from_tuple format
# ---------------------------------------------------------------------------


class TestHasUntestedInputsFormat:
    """Verify _has_untested_inputs uses the same element_id format as _prepare_input_action."""

    def test_element_id_format_matches_prepare_input_action(self):
        """The element_id generated in _has_untested_inputs must match
        the 'coords:x,y' format from make_element_id_from_tuple.

        Before fix: used f'({x},{y})' format (e.g., '(100,200)')
        After fix: uses make_element_id_from_tuple (e.g., 'coords:100,200')
        """
        coords = (100, 200)
        expected_id = make_element_id_from_tuple(coords)
        assert expected_id == "coords:100,200"

        # The old format was wrong — verify it does NOT match
        old_format = f"({coords[0]},{coords[1]})"
        assert old_format != expected_id

    def test_has_untested_inputs_calls_make_element_id_from_tuple(self):
        """Verify _has_untested_inputs uses make_element_id_from_tuple via integration."""
        from rv_agent.strategies.rvagent_strategy.rvagent_strategy import (
            RVAgentStrategy,
        )

        # Build minimal strategy with mocked dependencies
        graph = MagicMock()
        ui_cov = MagicMock()
        config = MagicMock()
        config.stochastic_probability = 0.15
        config.stochastic_temperature = 1.0
        config.backtrack_saturation_threshold = 0.8
        config.mop_max_input_variations = 11
        config.mop_nav_weight = 2.0
        config.reward_gamma = 0.8
        config.reward_score_weight = 1.0
        config.coverage_density_weight = 200.0

        strategy = RVAgentStrategy.__new__(RVAgentStrategy)
        strategy.graph = graph
        strategy.ui_coverage = ui_cov

        # Create a mock value_generator that has remaining values for coords-format IDs
        value_gen = MagicMock()
        # Only return True for the correct format
        value_gen.has_remaining_values.side_effect = (
            lambda eid, **kw: eid == "coords:300,500"
        )
        strategy.value_generator = value_gen

        # Create a mock screen with one EditText action at (300, 500)
        edit_action = MagicMock()
        edit_action.target_view = {"class": "android.widget.EditText"}
        edit_action.widget_id = None
        edit_action.coordinates = (300, 500)

        screen_desc = MagicMock()
        screen_desc.get_all_actions.return_value = [edit_action]

        result = strategy._has_untested_inputs(screen_desc)
        assert result is True

        # Verify value_generator was called with the correct format and is_mop flag
        value_gen.has_remaining_values.assert_called_with(
            "coords:300,500",
            is_mop=edit_action.reaches_mop or edit_action.directly_reaches_mop,
        )

    def test_has_untested_inputs_false_when_old_format(self):
        """If value_generator only recognizes old format, _has_untested_inputs returns False.

        This proves the fix matters: the old f'({x},{y})' format would not
        match what _prepare_input_action stores.
        """
        from rv_agent.strategies.rvagent_strategy.rvagent_strategy import (
            RVAgentStrategy,
        )

        strategy = RVAgentStrategy.__new__(RVAgentStrategy)
        strategy.graph = MagicMock()
        strategy.ui_coverage = MagicMock()

        # Only return True for the OLD wrong format
        value_gen = MagicMock()
        value_gen.has_remaining_values.side_effect = (
            lambda eid, **kw: eid == "(300,500)"
        )
        strategy.value_generator = value_gen

        edit_action = MagicMock()
        edit_action.target_view = {"class": "android.widget.EditText"}
        edit_action.widget_id = None
        edit_action.coordinates = (300, 500)

        screen_desc = MagicMock()
        screen_desc.get_all_actions.return_value = [edit_action]

        # With the fix, _has_untested_inputs generates "coords:300,500",
        # which won't match "(300,500)" — so result is False
        result = strategy._has_untested_inputs(screen_desc)
        assert result is False


# ---------------------------------------------------------------------------
# (d) H5: forced_back_count increments only once (in algorithm_node)
# ---------------------------------------------------------------------------


class TestForcedBackCountSingleIncrement:
    """Verify forced_back_count is NOT incremented in decision_node."""

    def test_decision_node_does_not_increment_forced_back_count(self):
        """decision_router_node should not increment forced_back_count.

        Only algorithm_node should increment forced_back_count when it
        processes the forced BACK action.
        """
        from rv_agent.agent.nodes.decision_node import decision_router_node

        # Create mock agent with routing_manager
        agent = MagicMock()
        agent.routing_manager.mode = "pure_algorithm"
        agent.routing_manager.forced_back_count = 0

        state = {
            "iteration": 5,
            "force_back_action": True,
        }

        result = decision_router_node(agent, state)

        # decision_node should route to algorithm but NOT increment the counter
        assert result["decision_path"] == "algorithm"
        assert result["decision_maker"] == "stuck_recovery"
        assert agent.routing_manager.forced_back_count == 0

    def test_algorithm_node_increments_forced_back_count(self):
        """algorithm_node should increment forced_back_count when processing forced BACK."""
        from rv_agent.agent.nodes.algorithm_node import algorithm_node

        agent = MagicMock()
        agent.routing_manager.mode = "pure_algorithm"
        agent.routing_manager.forced_back_count = 0
        agent.consecutive_no_action = 5

        state = {
            "iteration": 5,
            "force_back_action": True,
            "force_restart_app": False,
            "force_fill_input": False,
            "current_screen": MagicMock(),
        }

        result = algorithm_node(agent, state)

        # algorithm_node should increment forced_back_count
        assert agent.routing_manager.forced_back_count == 1
        assert result["current_action"]["action_type"] == "BACK"

    def test_full_flow_increments_exactly_once(self):
        """End-to-end: decision_node + algorithm_node increments forced_back_count once."""
        from rv_agent.agent.nodes.algorithm_node import algorithm_node
        from rv_agent.agent.nodes.decision_node import decision_router_node

        agent = MagicMock()
        agent.routing_manager.mode = "pure_algorithm"
        agent.routing_manager.forced_back_count = 0
        agent.consecutive_no_action = 3

        state = {
            "iteration": 10,
            "force_back_action": True,
            "force_restart_app": False,
            "force_fill_input": False,
            "current_screen": MagicMock(),
        }

        # Step 1: decision_node routes to algorithm
        decision_result = decision_router_node(agent, state)
        assert decision_result["decision_path"] == "algorithm"

        # Step 2: algorithm_node processes forced BACK
        _ = algorithm_node(agent, state)

        # Counter should be exactly 1, not 2
        assert agent.routing_manager.forced_back_count == 1

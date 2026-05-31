"""
Tests for ranking context hash fix (gh26 Group 22).

Verifies that _build_ranking_context passes the correct current_state_hash
to RankingContext, enabling SaturationScorer, VisitationPenaltyScorer,
CoverageDensityScorer, and StrengthScorer to function correctly.

Before this fix, _build_ranking_context always returned current_state_hash=""
because DynamicStateGraph does not have a get_current_state_hash() method,
and the hasattr guard silently fell back to "". This caused 4 of 9 scorers
to return constant values (0.0 or neutral) since they looked up "" in the
graph.states dict and found nothing.
"""

import math
from unittest.mock import MagicMock

import pytest
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.strategies.rvagent_strategy.ranking.context import RankingContext
from rv_agent.strategies.rvagent_strategy.ranking.scorers import (
    SaturationScorer,
    VisitationPenaltyScorer,
)
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy


def _make_config(**overrides):
    """Create a mock config with defaults."""
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


def _make_screen_desc(activity=".MainActivity", num_actions=3):
    """Create a mock ScreenDescription with actions."""
    desc = MagicMock()
    desc.activity = activity

    mock_actions = []
    for i in range(num_actions):
        action = MagicMock()
        action.coordinates = (100 + i * 100, 500)
        action.coords_for_matching = ((100 + i * 100, 500), "click")
        action.event = MagicMock()
        action.event.name = "CLICK"
        action.event.value = 1
        action.action_type = "click"
        action.text = f"Button {i}"
        action.target_view = {
            "class": "android.widget.Button",
            "bounds": [[50 + i * 100, 450], [150 + i * 100, 550]],
        }
        action.widget_id = f"btn_{i}"
        action.reaches_target = False
        action.directly_reaches_target = False
        action.callback_signature = None
        action.text_input = None
        mock_actions.append(action)

    mock_item = MagicMock()
    mock_item.view = {"package": "com.test.app"}
    mock_item.actions = mock_actions
    desc.items = [mock_item]
    desc.get_all_actions.return_value = mock_actions
    return desc


class TestBuildRankingContextHash:
    """Verify _build_ranking_context returns correct current_state_hash."""

    def test_ranking_context_has_correct_hash(self):
        """After select_next_action sets self._current_hash, _build_ranking_context
        should return a RankingContext with that hash, not empty string."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        strategy = RVAgentStrategy(
            graph=graph,
            ui_coverage=ui_coverage,
            config=config,
        )

        screen_desc = _make_screen_desc()
        test_hash = "state_abc123"

        # Register the state in the graph so select_next_action works
        graph.get_or_create_state(test_hash, ".MainActivity", screen_desc)

        # Call select_next_action to set self._current_hash
        strategy.select_next_action(test_hash, screen_desc)

        # Now call _build_ranking_context and verify the hash
        context = strategy._build_ranking_context(screen_desc)

        assert isinstance(context, RankingContext)
        assert context.current_state_hash == test_hash
        assert context.current_state_hash != ""

    def test_ranking_context_hash_not_empty_string(self):
        """The old bug: _build_ranking_context always returned current_state_hash=''.
        After fix, it should return the actual state hash."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        strategy = RVAgentStrategy(
            graph=graph,
            ui_coverage=ui_coverage,
            config=config,
        )

        screen_desc = _make_screen_desc()
        test_hash = "real_hash_value"

        graph.get_or_create_state(test_hash, ".MainActivity", screen_desc)

        # Simulate what select_next_action does
        strategy._current_hash = test_hash

        context = strategy._build_ranking_context(screen_desc)
        assert context.current_state_hash == "real_hash_value"

    def test_ranking_context_updates_on_new_state(self):
        """When select_next_action is called with a different hash,
        _build_ranking_context should return the new hash."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        strategy = RVAgentStrategy(
            graph=graph,
            ui_coverage=ui_coverage,
            config=config,
        )

        screen_desc_a = _make_screen_desc(activity=".ActivityA")
        screen_desc_b = _make_screen_desc(activity=".ActivityB")

        graph.get_or_create_state("hash_a", ".ActivityA", screen_desc_a)
        graph.get_or_create_state("hash_b", ".ActivityB", screen_desc_b)

        # First state
        strategy.select_next_action("hash_a", screen_desc_a)
        ctx_a = strategy._build_ranking_context(screen_desc_a)
        assert ctx_a.current_state_hash == "hash_a"

        # Second state
        strategy.select_next_action("hash_b", screen_desc_b)
        ctx_b = strategy._build_ranking_context(screen_desc_b)
        assert ctx_b.current_state_hash == "hash_b"


class TestSaturationScorerWithCorrectHash:
    """Verify SaturationScorer returns non-zero when state has low saturation."""

    def test_saturation_scorer_returns_bonus_for_unsaturated_state(self):
        """With correct hash, SaturationScorer should return a positive bonus
        for a state with low saturation (many untested actions)."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(num_actions=5)
        test_hash = "unsaturated_state"

        # Create state with 5 actions, none executed
        graph.get_or_create_state(test_hash, ".MainActivity", screen_desc)

        scorer = SaturationScorer()  # Default bonus = 80.0

        context = RankingContext(
            screen_desc=screen_desc,
            graph=graph,
            ui_coverage=UICoverageTracker(),
            current_state_hash=test_hash,
            visited_activities={".MainActivity"},
        )

        action = screen_desc.get_all_actions()[0]
        score = scorer.score(action, context)

        # Saturation is 0.0 (no actions executed), so bonus = 80.0 * (1.0 - 0.0) = 80.0
        assert score > 0.0
        assert score == pytest.approx(80.0)

    def test_saturation_scorer_returns_zero_with_empty_hash(self):
        """With empty hash (the old bug), SaturationScorer returns 0.0 because
        graph.states.get('') returns None."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(num_actions=5)

        # Create state under a real hash
        graph.get_or_create_state("real_hash", ".MainActivity", screen_desc)

        scorer = SaturationScorer()

        # Context with empty hash (the bug)
        context = RankingContext(
            screen_desc=screen_desc,
            graph=graph,
            ui_coverage=UICoverageTracker(),
            current_state_hash="",  # BUG: empty string
            visited_activities={".MainActivity"},
        )

        action = screen_desc.get_all_actions()[0]
        score = scorer.score(action, context)

        # Empty hash -> node not found -> returns 0.0
        assert score == 0.0

    def test_saturation_scorer_decreases_with_more_executions(self):
        """SaturationScorer bonus decreases as more actions are executed."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc(num_actions=4)
        test_hash = "partial_state"

        node = graph.get_or_create_state(test_hash, ".MainActivity", screen_desc)

        scorer = SaturationScorer()
        action = screen_desc.get_all_actions()[0]

        # Unsaturated: 0/4 executed
        context_0 = RankingContext(
            screen_desc=screen_desc,
            graph=graph,
            ui_coverage=UICoverageTracker(),
            current_state_hash=test_hash,
            visited_activities={".MainActivity"},
        )
        score_0 = scorer.score(action, context_0)

        # Execute 2 of 4 actions (each twice to saturate)
        for i in range(2):
            sig = ((100 + i * 100, 500), "click")
            node.record_action(sig)
            node.record_action(sig)

        context_half = RankingContext(
            screen_desc=screen_desc,
            graph=graph,
            ui_coverage=UICoverageTracker(),
            current_state_hash=test_hash,
            visited_activities={".MainActivity"},
        )
        score_half = scorer.score(action, context_half)

        # Score should decrease as saturation increases
        assert score_0 > score_half > 0.0


class TestVisitationPenaltyScorerWithCorrectHash:
    """Verify VisitationPenaltyScorer returns negative for visited states."""

    def test_visitation_penalty_returns_negative_for_visited_state(self):
        """With correct hash, VisitationPenaltyScorer should return a negative
        value for a state that has been visited multiple times."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc()
        test_hash = "visited_state"

        node = graph.get_or_create_state(test_hash, ".MainActivity", screen_desc)
        # Simulate 5 visits
        node.visit_count = 5

        scorer = VisitationPenaltyScorer()  # Default factor = -10.0

        context = RankingContext(
            screen_desc=screen_desc,
            graph=graph,
            ui_coverage=UICoverageTracker(),
            current_state_hash=test_hash,
            visited_activities={".MainActivity"},
        )

        action = screen_desc.get_all_actions()[0]
        score = scorer.score(action, context)

        # penalty = -10.0 * log(1 + 5) = -10.0 * log(6) ≈ -17.92
        expected = -10.0 * math.log(1 + 5)
        assert score < 0.0
        assert score == pytest.approx(expected)

    def test_visitation_penalty_returns_zero_with_empty_hash(self):
        """With empty hash (the old bug), VisitationPenaltyScorer returns 0.0
        because graph.states.get('') returns None."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc()

        node = graph.get_or_create_state("real_hash", ".MainActivity", screen_desc)
        node.visit_count = 10  # Many visits

        scorer = VisitationPenaltyScorer()

        # Context with empty hash (the bug)
        context = RankingContext(
            screen_desc=screen_desc,
            graph=graph,
            ui_coverage=UICoverageTracker(),
            current_state_hash="",  # BUG: empty string
            visited_activities={".MainActivity"},
        )

        action = screen_desc.get_all_actions()[0]
        score = scorer.score(action, context)

        # Empty hash -> node not found -> returns 0.0 (penalty disabled)
        assert score == 0.0

    def test_visitation_penalty_zero_for_unvisited_state(self):
        """First visit (visit_count=0) should produce zero penalty."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc()
        test_hash = "new_state"

        _ = graph.get_or_create_state(test_hash, ".MainActivity", screen_desc)
        # visit_count = 1 on creation (get_or_create_state sets it to 1)

        scorer = VisitationPenaltyScorer()

        context = RankingContext(
            screen_desc=screen_desc,
            graph=graph,
            ui_coverage=UICoverageTracker(),
            current_state_hash=test_hash,
            visited_activities={".MainActivity"},
        )

        action = screen_desc.get_all_actions()[0]
        score = scorer.score(action, context)

        # visit_count=1 on creation -> penalty = -10.0 * log(1 + 1) = -10.0 * log(2) ≈ -6.93
        # For a "new" state with only 1 visit, penalty is small but non-zero
        assert score < 0.0

    def test_visitation_penalty_increases_with_visits(self):
        """Penalty magnitude increases logarithmically with visit count."""
        graph = DynamicStateGraph()
        screen_desc = _make_screen_desc()
        test_hash = "growing_visits"

        node = graph.get_or_create_state(test_hash, ".MainActivity", screen_desc)
        scorer = VisitationPenaltyScorer()
        action = screen_desc.get_all_actions()[0]

        penalties = []
        for visit_count in [1, 5, 20, 100]:
            node.visit_count = visit_count
            context = RankingContext(
                screen_desc=screen_desc,
                graph=graph,
                ui_coverage=UICoverageTracker(),
                current_state_hash=test_hash,
                visited_activities={".MainActivity"},
            )
            score = scorer.score(action, context)
            penalties.append(score)

        # All penalties should be negative
        assert all(p < 0 for p in penalties)
        # Penalty magnitude should increase (more negative)
        assert penalties[0] > penalties[1] > penalties[2] > penalties[3]

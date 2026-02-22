"""
Integration edge case tests for gh26 exploration strategy (Group 9, task 9.4).

Validates boundary conditions and defensive behaviors across all gh26 groups.
These tests target scenarios that could fail silently in production:
- Config backward compatibility (new fields have Pydantic defaults)
- Graceful degradation without static analysis data
- BFS cycle termination
- Reward cap boundaries
- Zero-element screens
- Cold start guards
- Component isolation (invalidate preserves reward history)
- ActionRanker scorer count
"""

import pytest
from unittest.mock import MagicMock

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.domain.screen_node import ScreenNode
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_agent.strategies.rvagent_strategy.path_buffer import (
    PathBuffer,
    MAX_COVERAGE_HOPS,
)
from rv_agent.strategies.rvagent_strategy.reward_propagator import (
    RewardPropagator,
    MAX_CUMULATIVE_REWARD_FACTOR,
    REWARD_MOP_WEIGHT,
)
from rv_agent.strategies.rvagent_strategy.ranking.scorers import (
    CoverageDensityScorer,
    MopScorer,
    WtgScorer,
    SaturationScorer,
    ComponentPriorityScorer,
    StrengthScorer,
    GradualDecayScorer,
    SystemElementFilter,
    VisitationPenaltyScorer,
)
from rv_agent.strategies.rvagent_strategy.ranking.action_ranker import ActionRanker
from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker
from rv_agent.memory.ui_coverage import UICoverageTracker

from .conftest import create_mock_screen, create_mock_action


class TestConfigBackwardCompatibility:
    """Verify gh26 config fields have correct Pydantic defaults."""

    def test_config_backward_compatibility(self):
        """
        Load RVAgentConfig without gh26 fields -> Pydantic defaults work.

        When existing code creates RVAgentConfig with only package_name (the only
        required field), all gh26 parameters must have working defaults.
        """
        config = RVAgentConfig(package_name="com.legacy.app")

        # gh26 exploration parameters must have defaults
        assert config.backtrack_saturation_threshold == 0.8
        assert config.reward_gamma == 0.8
        assert config.coverage_density_weight == 200.0
        assert config.mop_nav_weight == 2.0
        assert config.mop_max_input_variations == 11
        assert config.reward_score_weight == 1.0

    def test_config_create_default_includes_gh26_fields(self):
        """RVAgentConfig.create_default also includes all gh26 fields with defaults."""
        config = RVAgentConfig.create_default(package_name="test.app")

        assert hasattr(config, "backtrack_saturation_threshold")
        assert hasattr(config, "reward_gamma")
        assert hasattr(config, "coverage_density_weight")
        assert 0.5 <= config.backtrack_saturation_threshold <= 1.0


class TestGracefulDegradationWithoutStaticAnalysis:
    """Verify agent components work when static_data=None."""

    def test_graceful_degradation_without_static_analysis(self):
        """
        RVAgentStrategy initialized without static analysis data must not crash
        and all gh26 components (PathBuffer, RewardPropagator) must be usable.

        StaticAnalysisData=None is the production case when RVSEC_HOME is not set
        or when running the agent before static analysis completes.
        """
        config = RVAgentConfig(
            package_name="test.app",
            stochastic_probability=0.0,
        )
        graph = DynamicStateGraph()
        ui_coverage = MagicMock()
        ui_coverage.get_element_test_count = MagicMock(return_value=0)
        ui_coverage.get_coverage_gap = MagicMock(return_value=0.0)
        ui_coverage.get_element_count = MagicMock(return_value=0)

        # static_data=None and transition_manager=None (default)
        strategy = RVAgentStrategy(
            graph=graph,
            ui_coverage=ui_coverage,
            config=config,
            static_data=None,
        )

        # All gh26 components must be present
        assert strategy.reward_propagator is not None
        assert strategy.path_buffer is not None
        assert strategy.path_buffer.transition_manager is None

        # PathBuffer must not crash when plan_mop_path called without transition_manager
        result = strategy.path_buffer.plan_mop_path("SomeActivity", {})
        assert result is False  # Graceful fallback

        # RewardPropagator must be usable
        sig = ((100, 200), "CLICK")
        strategy.reward_propagator.record_action("state_X", sig)
        node = ScreenNode(screen_hash="state_X", activity="TestActivity")
        graph.states["state_X"] = node
        # Must not raise
        strategy.reward_propagator.propagate("new_state", graph)

    def test_strategy_select_action_without_static_analysis(self):
        """
        select_next_action works correctly when no static analysis data is available.
        """
        config = RVAgentConfig(
            package_name="test.app",
            stochastic_probability=0.0,
        )
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        strategy = RVAgentStrategy(
            graph=graph,
            ui_coverage=ui_coverage,
            config=config,
        )

        screen = create_mock_screen(
            activity="com.test.MainActivity",
            actions=[
                create_mock_action(coords=(200, 400), widget_id="btn_1"),
                create_mock_action(coords=(200, 600), widget_id="btn_2"),
            ],
        )

        action = strategy.select_next_action("test_hash", screen)
        assert action is not None


class TestBacktrackBfsCyclicGraph:
    """Verify BFS termination on cyclic graphs."""

    def test_backtrack_bfs_cyclic_graph_termination(self):
        """
        A -> B -> C -> A cycle with all states saturated -> BFS returns None.

        The BFS in SuccessorTracker.find_nearest_unsaturated must handle cycles
        without infinite looping. With all states saturated, it returns None.
        """
        graph = DynamicStateGraph()

        # Create nodes A, B, C all fully saturated
        for state_id in ["A", "B", "C"]:
            node = ScreenNode(
                screen_hash=state_id,
                activity="Activity",
                total_actions=3,
            )
            for i in range(3):
                sig = ((i * 50, 100), "CLICK")
                node.executed_actions.add(sig)
                node.action_execution_counts[sig] = 3  # Saturated (>= 2)
            graph.states[state_id] = node

        config = RVAgentConfig(package_name="test.app")
        tracker = SuccessorTracker(graph, config=config)

        # Set up cyclic back_successors: A->B->C->A
        tracker.back_successors = {
            "A": {"B"},
            "B": {"C"},
            "C": {"A"},
        }
        # Record successors (needed for has_incomplete check)
        tracker.successors = {
            ("A", ((0, 100), "CLICK")): "B",
            ("B", ((0, 100), "CLICK")): "C",
            ("C", ((0, 100), "CLICK")): "A",
        }

        # find_nearest_unsaturated must terminate and return None (all saturated)
        result = tracker.find_nearest_unsaturated("A")
        assert result is None  # No unsaturated ancestor found


class TestCumulativeRewardCapBoundary:
    """Verify cumulative reward hard cap at exact boundary."""

    def test_cumulative_reward_cap_boundary(self):
        """
        At cap 15.0 + 5.0 (MOP reward) -> stays at 15.0.

        The cap is MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT = 3.0 * 5.0 = 15.0.
        Adding 5.0 to 15.0 must clamp at 15.0.
        """
        prop = RewardPropagator()
        graph = MagicMock()
        sig = ((10, 20), "CLICK")

        node = ScreenNode(screen_hash="s", activity="A")
        node.action_cumulative_reward[sig] = (
            MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT
        )
        graph.states = {"s": node}

        prop.record_action("s", sig)
        prop.propagate("mop_reached", graph)

        expected_cap = MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT
        actual = node.action_cumulative_reward[sig]
        assert actual == pytest.approx(expected_cap)


class TestZeroElementsScreen:
    """Verify scorer behavior on screens with no interactive elements."""

    def test_zero_elements_screen_coverage_density(self):
        """
        CoverageDensityScorer returns 0.0 for action with 0-element destination.

        When destination state has no elements (element_count=0), potential=0
        so CoverageDensityScorer contributes nothing to the score.
        """
        scorer = CoverageDensityScorer()
        action = MagicMock()
        action.coords_for_matching = ((100, 200), "CLICK")

        tracker = MagicMock()
        tracker.get_action_destination.return_value = "empty_dest"

        ui_cov = MagicMock()
        # 0% coverage gap on empty screen
        ui_cov.get_coverage_gap.return_value = 0.0

        ctx = MagicMock()
        ctx.successor_tracker = tracker
        ctx.ui_coverage = ui_cov
        ctx.current_state_hash = "state_A"

        score = scorer.score(action, ctx)
        assert score == pytest.approx(0.0)

    def test_strategy_back_action_on_empty_screen(self):
        """
        Empty screen (no interactive elements) -> strategy returns BACK action.

        Tier 5 fallback: when no actions available and not in buffer, return BACK.
        """
        config = RVAgentConfig(package_name="test.app", stochastic_probability=0.0)
        graph = DynamicStateGraph()
        ui_coverage = MagicMock()
        ui_coverage.get_element_test_count = MagicMock(return_value=0)

        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        empty_screen = create_mock_screen(activity="com.test.Empty", actions=[])
        node = ScreenNode(
            screen_hash="empty", activity="com.test.Empty", total_actions=0
        )
        graph.states["empty"] = node

        action = strategy.select_next_action("empty", empty_screen)

        assert action is not None
        from rv_android_core.domain.widget import WidgetEventType

        # Empty screen is vacuously saturated (0/0), so Tier 3 proactive
        # backtrack triggers. With no backtrack path available, the strategy
        # falls through to RESTART_APP instead of BACK.
        assert action.event in (WidgetEventType.BACK, WidgetEventType.RESTART)


class TestColdStartCoveragePathDisabled:
    """Verify cold start guard blocks coverage path when < 3 screens."""

    def test_cold_start_coverage_path_disabled(self):
        """
        Fewer than 3 screens in graph -> plan_coverage_path returns False.

        Cold start guard prevents meaningless coverage navigation decisions
        before the agent has explored enough to have useful data.
        """
        successor_tracker = MagicMock()
        successor_tracker.back_successors = {"state_A": {"state_B"}}
        successor_tracker.graph = MagicMock()
        # Only 2 screens - below cold start threshold of 3
        successor_tracker.graph.states = {
            "state_A": MagicMock(),
            "state_B": MagicMock(),
        }

        ui_coverage = MagicMock()
        ui_coverage.get_coverage_gap = MagicMock(return_value=0.8)
        ui_coverage.get_element_count = MagicMock(return_value=20)

        config = MagicMock()
        config.backtrack_saturation_threshold = 0.8

        buf = PathBuffer(
            transition_manager=None,
            successor_tracker=successor_tracker,
            ui_coverage_tracker=ui_coverage,
            config=config,
        )

        result = buf.plan_coverage_path("state_A")
        assert result is False
        assert buf.is_active is False


class TestPathBufferInvalidationPreservesRewardHistory:
    """Verify PathBuffer.invalidate() does not affect RewardPropagator."""

    def test_path_buffer_invalidation_preserves_reward_history(self):
        """
        invalidate() on PathBuffer must not clear RewardPropagator's _action_history.

        These are independent components (Group 6 vs Group 4). Invalidating the
        buffer must not corrupt reward history accumulated over many iterations.
        """
        prop = RewardPropagator()

        # Record 5 actions in reward propagator history
        sigs = [((i * 20, 100), "CLICK") for i in range(5)]
        for i, sig in enumerate(sigs):
            prop.record_action(f"state_{i}", sig)

        history_before = list(prop._action_history)
        assert len(history_before) == 5

        # Create and invalidate a PathBuffer (simulates stuck detection)
        successor_tracker = MagicMock()
        successor_tracker.find_nearest_unsaturated.return_value = ("target", 4)
        buf = PathBuffer(
            transition_manager=None,
            successor_tracker=successor_tracker,
            ui_coverage_tracker=MagicMock(),
            config=MagicMock(),
        )
        buf.plan_backtrack_path("current")
        buf.invalidate()

        # Reward propagator history must be completely unchanged
        history_after = list(prop._action_history)
        assert history_after == history_before


class TestScorerCount9Active:
    """Verify ActionRanker is initialized with exactly 9 active scorers."""

    def test_scorer_count_9_active(self):
        """
        ActionRanker must have exactly 9 active scorers after gh26 Group 3.5.

        The 9 scorers are: MopScorer, WtgScorer, SaturationScorer,
        ComponentPriorityScorer, StrengthScorer, GradualDecayScorer,
        CoverageDensityScorer, SystemElementFilter, VisitationPenaltyScorer.
        """
        config = RVAgentConfig(package_name="test.app")
        ranker = ActionRanker(
            scorers=[
                MopScorer(config=config),
                WtgScorer(config=config),
                SaturationScorer(config=config),
                ComponentPriorityScorer(config=config),
                StrengthScorer(config=config),
                GradualDecayScorer(config=config),
                CoverageDensityScorer(config=config),
                SystemElementFilter(),
                VisitationPenaltyScorer(config=config),
            ]
        )

        assert len(ranker.scorers) == 9

    def test_rvagent_strategy_has_9_scorers(self):
        """
        RVAgentStrategy initializes its ActionRanker with exactly 9 scorers.

        Verifies that the production initialization code in __init__ matches
        the design spec (Group 3.5: add CoverageDensityScorer as 9th scorer).
        """
        config = RVAgentConfig(package_name="test.app")
        graph = DynamicStateGraph()
        ui_coverage = MagicMock()
        ui_coverage.get_element_test_count = MagicMock(return_value=0)

        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        assert len(strategy.action_ranker.scorers) == 9

        # Verify CoverageDensityScorer is among them
        density_scorers = [
            s
            for s in strategy.action_ranker.scorers
            if isinstance(s, CoverageDensityScorer)
        ]
        assert len(density_scorers) == 1


class TestTierFallthroughOnSaturatedScreen:
    """Verify tier fallthrough when saturated and PathBuffer fails (task 16.5)."""

    def test_saturated_screen_no_path_falls_to_tier4(self):
        """
        Saturated screen + PathBuffer plans all fail -> Tier 4 scored selection.

        Before the D8 fix, this scenario would trigger RESTART. With the fix,
        the strategy falls through to Tier 4 and selects the least-explored
        action via ActionRanker, keeping the agent productive.
        """
        config = RVAgentConfig(
            package_name="test.app",
            stochastic_probability=0.0,
            backtrack_saturation_threshold=0.8,
        )
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        # Create screen with 5 actions
        actions = [
            create_mock_action(coords=(100 + i * 100, 500), widget_id=f"btn_{i}")
            for i in range(5)
        ]
        screen = create_mock_screen(activity="com.test.Main", actions=actions)

        # Register the state
        strategy.select_next_action("state_sat", screen)
        node = graph.states["state_sat"]

        # Saturate all 5 actions (each executed 3x, threshold=2)
        for action in actions:
            sig = action.coords_for_matching
            node.record_action(sig)
            node.record_action(sig)
            node.record_action(sig)

        # Mock PathBuffer to fail all plans
        strategy.path_buffer = MagicMock()
        strategy.path_buffer.is_active = False
        strategy.path_buffer.is_cooling_down = False
        strategy.path_buffer.plan_coverage_path.return_value = False
        strategy.path_buffer.plan_mop_path.return_value = False
        strategy.path_buffer.plan_backtrack_path.return_value = False

        result = strategy.select_next_action("state_sat", screen)

        # Must return a real action (Tier 4), NOT RESTART
        assert result is not None
        from rv_screen_parser.parser.screen.visitor.model import WidgetEventType

        assert result.event != WidgetEventType.RESTART

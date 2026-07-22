"""
Integration tests for PathBuffer (gh26 Group 9, task 9.1).

Validates the buffer plan -> execute -> invalidation lifecycle using real
PathBuffer instances. Tests cross-group interactions between PathBuffer,
SuccessorTracker BFS, and UICoverageTracker coverage metrics.
"""

from unittest.mock import MagicMock

from rv_agent.strategies.rvagent_strategy.path_buffer import PathBuffer
from rv_agent.strategies.rvagent_strategy.reward_propagator import RewardPropagator
from rv_android_core.domain.widget import WidgetEventType


def _make_path_buffer(
    find_nearest_result=None,
    back_successors=None,
    graph_states=None,
    coverage_gaps=None,
    element_counts=None,
    transition_manager=None,
):
    """
    Create PathBuffer with configurable mock dependencies.

    Args:
        find_nearest_result: Return value for find_nearest_unsaturated (tuple or None)
        back_successors: Dict mapping state_hash -> set of ancestor hashes
        graph_states: Dict of state_hash -> MagicMock nodes (3 needed for coverage path)
        coverage_gaps: Dict of state_hash -> gap float for UICoverageTracker
        element_counts: Dict of state_hash -> element count for UICoverageTracker
        transition_manager: Optional mock TransitionManager
    """
    successor_tracker = MagicMock()
    successor_tracker.find_nearest_unsaturated.return_value = find_nearest_result
    successor_tracker.back_successors = back_successors or {}

    if graph_states is not None:
        successor_tracker.graph = MagicMock()
        successor_tracker.graph.states = graph_states
    else:
        successor_tracker.graph = MagicMock()
        successor_tracker.graph.states = {}

    ui_coverage = MagicMock()
    if coverage_gaps is not None:
        ui_coverage.get_coverage_gap = MagicMock(
            side_effect=lambda h: coverage_gaps.get(h, 0.0)
        )
    else:
        ui_coverage.get_coverage_gap = MagicMock(return_value=0.0)

    if element_counts is not None:
        ui_coverage.get_element_count = MagicMock(
            side_effect=lambda h: element_counts.get(h, 0)
        )
    else:
        ui_coverage.get_element_count = MagicMock(return_value=0)

    config = MagicMock()
    config.backtrack_saturation_threshold = 0.8

    return PathBuffer(
        transition_manager=transition_manager,
        successor_tracker=successor_tracker,
        ui_coverage_tracker=ui_coverage,
        config=config,
    )


class TestBufferPlanExecuteExhaust:
    """Verify the plan -> execute -> exhaust lifecycle."""

    def test_buffer_plan_execute_exhaust(self):
        """
        Plan 3 BACK actions, consume all 3, verify buffer is empty.

        Cross-group: PathBuffer (Group 6) consumes actions planned via
        SuccessorTracker BFS (Group 5). After exhaustion, is_active=False.
        """
        buf = _make_path_buffer(find_nearest_result=("target", 3))
        result = buf.plan_backtrack_path("current")

        assert result is True
        assert buf.remaining_steps == 3

        # Consume actions one by one
        for i in range(3):
            action = buf.get_next_action()
            assert action is not None
            assert action.event == WidgetEventType.BACK
            assert buf.remaining_steps == 2 - i

        # Buffer exhausted
        assert buf.get_next_action() is None
        assert buf.is_active is False
        assert buf.remaining_steps == 0

    def test_buffer_active_during_execution(self):
        """is_active transitions correctly during execution."""
        buf = _make_path_buffer(find_nearest_result=("ancestor", 2))
        buf.plan_backtrack_path("start")

        assert buf.is_active is True
        buf.get_next_action()
        assert buf.is_active is True  # Still 1 remaining
        buf.get_next_action()
        assert buf.is_active is False  # Exhausted


class TestBufferInvalidation:
    """Verify buffer invalidation clears all pending actions."""

    def test_buffer_invalidation_on_stuck(self):
        """
        Plan a path, simulate stuck (hash unchanged), verify invalidate() clears buffer.

        In the real system, learn_node calls invalidate() when the screen hash
        is unchanged after executing a buffered action (navigation didn't work).
        """
        buf = _make_path_buffer(find_nearest_result=("target", 5))
        buf.plan_backtrack_path("current")

        assert buf.remaining_steps == 5
        assert buf.is_active is True

        # Simulate stuck detection -> invalidate
        buf.invalidate()

        assert buf.remaining_steps == 0
        assert buf.is_active is False
        assert buf.get_next_action() is None

    def test_invalidation_does_not_affect_reward_propagator(self):
        """
        Invalidating PathBuffer must not clear RewardPropagator's action history.

        Cross-group: PathBuffer (Group 6) and RewardPropagator (Group 4) are
        independent components. Invalidating the buffer must not corrupt reward history.
        """
        prop = RewardPropagator()
        sig = ((100, 200), "CLICK")
        prop.record_action("state_A", sig)
        prop.record_action("state_B", sig)

        buf = _make_path_buffer(find_nearest_result=("target", 3))
        buf.plan_backtrack_path("current")
        buf.invalidate()

        # Reward propagator history must be intact
        assert len(prop._action_history) == 2

    def test_double_invalidation_is_safe(self):
        """Calling invalidate() on empty buffer does not raise."""
        buf = _make_path_buffer()
        buf.invalidate()  # First call on empty buffer
        buf.invalidate()  # Second call - must be safe

        assert buf.remaining_steps == 0
        assert buf.is_active is False


class TestCoveragePathSelectsBestAncestor:
    """Verify plan_coverage_path selects ancestor with highest exploration potential."""

    def test_coverage_path_selects_best_ancestor(self):
        """
        Set up graph with 3 ancestors at different coverage gaps, verify
        plan_coverage_path picks the one with highest exploration_potential
        (coverage_gap * element_count).

        ancestor_A: gap=0.1, elements=10 -> potential=1.0
        ancestor_B: gap=0.4, elements=20 -> potential=8.0 (winner)
        ancestor_C: gap=0.6, elements=5  -> potential=3.0
        """
        graph_states = {
            "current": MagicMock(),
            "ancestor_A": MagicMock(),
            "ancestor_B": MagicMock(),
            "ancestor_C": MagicMock(),
        }
        back_successors = {
            "current": {"ancestor_A", "ancestor_B", "ancestor_C"},
        }
        coverage_gaps = {
            "ancestor_A": 0.1,
            "ancestor_B": 0.4,
            "ancestor_C": 0.6,
        }
        element_counts = {
            "ancestor_A": 10,
            "ancestor_B": 20,
            "ancestor_C": 5,
        }

        buf = _make_path_buffer(
            back_successors=back_successors,
            graph_states=graph_states,
            coverage_gaps=coverage_gaps,
            element_counts=element_counts,
        )

        result = buf.plan_coverage_path("current")

        # ancestor_B has potential 8.0 (highest), 1 hop away
        assert result is True
        assert buf.remaining_steps == 1  # 1 hop to best ancestor

    def test_coverage_path_cold_start_blocked(self):
        """
        With only 2 screens in graph, plan_coverage_path returns False (cold start guard).

        Cold start guard prevents meaningless coverage decisions when exploration
        has barely begun (< 3 screens discovered).
        """
        buf = _make_path_buffer(
            graph_states={
                "current": MagicMock(),
                "other": MagicMock(),
            }
        )

        result = buf.plan_coverage_path("current")

        assert result is False
        assert buf.is_active is False

    def test_coverage_path_all_zero_potential_returns_false(self):
        """
        All reachable ancestors have 0 exploration potential -> returns False.

        Potential = gap * element_count. If all are 0, no point navigating anywhere.
        """
        graph_states = {
            "current": MagicMock(),
            "anc_1": MagicMock(),
            "anc_2": MagicMock(),
        }
        back_successors = {"current": {"anc_1", "anc_2"}}
        # All ancestors fully covered (gap = 0)
        coverage_gaps = {"anc_1": 0.0, "anc_2": 0.0}
        element_counts = {"anc_1": 10, "anc_2": 15}

        buf = _make_path_buffer(
            back_successors=back_successors,
            graph_states=graph_states,
            coverage_gaps=coverage_gaps,
            element_counts=element_counts,
        )

        result = buf.plan_coverage_path("current")

        assert result is False

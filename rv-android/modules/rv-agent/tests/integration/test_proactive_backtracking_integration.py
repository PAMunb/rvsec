"""
Integration tests for proactive backtracking (gh26 Group 9, task 9.1).

Validates cross-group interactions between DynamicStateGraph, saturation
detection, and PathBuffer. Tests use real component instances to verify
the full backtracking decision chain: saturated state -> should_backtrack
-> PathBuffer plans BACK actions.
"""

import pytest
from unittest.mock import MagicMock

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.domain.screen_node import ScreenNode
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_agent.strategies.rvagent_strategy.path_buffer import (
    PathBuffer,
    MAX_BACKTRACK_HOPS,
)
from rv_android_core.domain.widget import WidgetEventType

from .conftest import create_mock_screen, create_mock_action


def _make_strategy(backtrack_threshold=0.8):
    """Create RVAgentStrategy with real DynamicStateGraph."""
    config = RVAgentConfig(
        package_name="test.app",
        backtrack_saturation_threshold=backtrack_threshold,
        stochastic_probability=0.0,
    )
    graph = DynamicStateGraph()
    ui_coverage = MagicMock()
    ui_coverage.get_element_test_count = MagicMock(return_value=0)
    ui_coverage.get_coverage_gap = MagicMock(return_value=0.0)
    ui_coverage.get_element_count = MagicMock(return_value=0)
    strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)
    strategy.successor_tracker.has_incomplete_successors = MagicMock(return_value=False)
    return strategy


def _saturate_node(strategy, state_hash, total_actions, saturated_count):
    """
    Add a ScreenNode to the graph with the specified saturation level.

    Sets action_execution_counts >= 2 for saturated_count actions and
    = 1 for remaining actions (unsaturated). Uses direct graph manipulation
    to avoid coordinate conversion complexity.

    Args:
        strategy: RVAgentStrategy with real graph
        state_hash: Hash to register in graph
        total_actions: Total number of actions for this node
        saturated_count: Number of actions to mark as saturated (count >= 2)
    """
    node = ScreenNode(
        screen_hash=state_hash,
        activity="com.test.Activity",
        total_actions=total_actions,
    )
    for i in range(total_actions):
        sig = ((i * 50, 100), "CLICK")
        node.executed_actions.add(sig)
        # saturated_count actions executed >= 2 times, rest only once
        node.action_execution_counts[sig] = 2 if i < saturated_count else 1

    strategy.graph.states[state_hash] = node
    return node


class TestBacktrackAtThreshold:
    """Verify should_backtrack with real DynamicStateGraph and saturated states."""

    def test_backtrack_at_threshold_with_real_graph(self):
        """
        Create DynamicStateGraph, add saturated state >= 0.8, verify should_backtrack
        returns True and PathBuffer plans BACK actions.

        Saturation 0.8 (8/10 actions executed >= 2 times) at threshold 0.8 -> True.
        PathBuffer plans 3 BACK actions to reach the unsaturated ancestor.
        """
        strategy = _make_strategy(backtrack_threshold=0.8)

        # Saturate state A: 8/10 actions saturated -> saturation_rate = 0.8 = threshold
        _saturate_node(strategy, "state_A", total_actions=10, saturated_count=8)

        # Verify should_backtrack returns True (>= threshold)
        assert strategy.should_backtrack("state_A") is True

        # Set up PathBuffer to verify it plans BACK actions
        mock_successor_tracker = MagicMock()
        mock_successor_tracker.find_nearest_unsaturated.return_value = ("ancestor", 3)
        mock_ui_coverage = MagicMock()
        config = MagicMock()

        buf = PathBuffer(
            transition_manager=None,
            successor_tracker=mock_successor_tracker,
            ui_coverage_tracker=mock_ui_coverage,
            config=config,
        )

        result = buf.plan_backtrack_path("state_A")

        assert result is True
        assert buf.remaining_steps == 3
        assert buf.is_active is True
        # All buffered actions should be BACK
        for _ in range(3):
            action = buf.get_next_action()
            assert action.event == WidgetEventType.BACK

    def test_no_backtrack_below_threshold(self):
        """
        Saturation 0.7 (7/10 actions saturated) < threshold 0.8 -> should_backtrack False.

        Verifies that the saturation threshold guard prevents premature backtracking.
        """
        strategy = _make_strategy(backtrack_threshold=0.8)

        # 7/10 saturated -> 0.7 < 0.8 threshold
        _saturate_node(strategy, "state_B", total_actions=10, saturated_count=7)

        assert strategy.should_backtrack("state_B") is False

    def test_backtrack_with_successor_reenablement(self):
        """
        Saturated state (>=0.8) with incomplete successor -> should_backtrack False.

        INV-AGT-31: Incomplete successors override saturation check. The action
        that leads to the incomplete successor must be re-enabled, so we stay
        in the saturated state instead of backtracking.
        """
        strategy = _make_strategy(backtrack_threshold=0.8)

        # Fully saturated state
        _saturate_node(strategy, "state_C", total_actions=5, saturated_count=5)

        # Successor tracker reports incomplete successors (override)
        strategy.successor_tracker.has_incomplete_successors = MagicMock(
            return_value=True
        )

        # Despite saturation >= threshold, incomplete successors block backtrack
        assert strategy.should_backtrack("state_C") is False


class TestPathBufferWithRealGraph:
    """Verify PathBuffer integrates correctly with SuccessorTracker BFS."""

    def test_plan_backtrack_fills_buffer_correctly(self):
        """Plan 3-hop backtrack path, verify buffer fills with 3 BACK actions."""
        successor_tracker = MagicMock()
        successor_tracker.find_nearest_unsaturated.return_value = ("target", 3)

        buf = PathBuffer(
            transition_manager=None,
            successor_tracker=successor_tracker,
            ui_coverage_tracker=MagicMock(),
            config=MagicMock(),
        )

        result = buf.plan_backtrack_path("current_state")

        assert result is True
        assert buf.remaining_steps == 3
        assert buf.is_active is True

    def test_no_backtrack_when_no_unsaturated_ancestor(self):
        """PathBuffer returns False when no unsaturated ancestor exists."""
        successor_tracker = MagicMock()
        successor_tracker.find_nearest_unsaturated.return_value = None

        buf = PathBuffer(
            transition_manager=None,
            successor_tracker=successor_tracker,
            ui_coverage_tracker=MagicMock(),
            config=MagicMock(),
        )

        result = buf.plan_backtrack_path("current_state")

        assert result is False
        assert buf.is_active is False

    def test_backtrack_beyond_max_hops_rejected(self):
        """Ancestor too far (> MAX_BACKTRACK_HOPS) -> PathBuffer returns False."""
        successor_tracker = MagicMock()
        successor_tracker.find_nearest_unsaturated.return_value = (
            "far_ancestor",
            MAX_BACKTRACK_HOPS + 1,
        )

        buf = PathBuffer(
            transition_manager=None,
            successor_tracker=successor_tracker,
            ui_coverage_tracker=MagicMock(),
            config=MagicMock(),
        )

        result = buf.plan_backtrack_path("current_state")

        assert result is False
        assert buf.remaining_steps == 0

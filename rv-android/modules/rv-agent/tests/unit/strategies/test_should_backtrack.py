"""
Tests for should_backtrack() saturation threshold (gh26 Group 5).

Verifies INV-AGT-31: backtrack based on saturation threshold, not binary exhaustion.
"""

from unittest.mock import MagicMock

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.domain.screen_node import ScreenNode


def _make_strategy(backtrack_threshold=0.8, has_incomplete=False):
    """Create an RVAgentStrategy with mocked dependencies."""
    config = RVAgentConfig(
        package_name="test.app",
        backtrack_saturation_threshold=backtrack_threshold,
    )

    graph = MagicMock()
    graph.states = {}
    ui_coverage = MagicMock()

    from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy

    strategy = RVAgentStrategy(
        graph=graph,
        ui_coverage=ui_coverage,
        config=config,
    )
    # Patch the real successor_tracker's method
    strategy.successor_tracker.has_incomplete_successors = MagicMock(
        return_value=has_incomplete
    )
    return strategy


class TestShouldBacktrack:
    """Verify saturation-threshold-based backtracking."""

    def test_saturated_state_above_threshold(self):
        """Saturation 0.9 > threshold 0.8 -> True."""
        strategy = _make_strategy(backtrack_threshold=0.8)

        node = ScreenNode(screen_hash="s1", activity="Test", total_actions=10)
        for i in range(9):
            sig = ((i * 10, 0), "CLICK")
            node.executed_actions.add(sig)
            node.action_execution_counts[sig] = 2
        sig_unsaturated = ((90, 0), "CLICK")
        node.executed_actions.add(sig_unsaturated)
        node.action_execution_counts[sig_unsaturated] = 1

        strategy.graph.states["s1"] = node
        assert strategy.should_backtrack("s1") is True

    def test_partially_explored_below_threshold(self):
        """Saturation 0.7 < threshold 0.8 -> False."""
        strategy = _make_strategy(backtrack_threshold=0.8)

        node = ScreenNode(screen_hash="s1", activity="Test", total_actions=10)
        for i in range(7):
            sig = ((i * 10, 0), "CLICK")
            node.executed_actions.add(sig)
            node.action_execution_counts[sig] = 2

        strategy.graph.states["s1"] = node
        assert strategy.should_backtrack("s1") is False

    def test_at_exact_threshold(self):
        """Saturation 0.8 >= threshold 0.8 -> True."""
        strategy = _make_strategy(backtrack_threshold=0.8)

        node = ScreenNode(screen_hash="s1", activity="Test", total_actions=10)
        for i in range(8):
            sig = ((i * 10, 0), "CLICK")
            node.executed_actions.add(sig)
            node.action_execution_counts[sig] = 2

        strategy.graph.states["s1"] = node
        assert strategy.should_backtrack("s1") is True

    def test_incomplete_successors(self):
        """Incomplete successors -> False (regardless of saturation)."""
        strategy = _make_strategy(has_incomplete=True)

        node = ScreenNode(screen_hash="s1", activity="Test", total_actions=2)
        for i in range(2):
            sig = ((i * 10, 0), "CLICK")
            node.executed_actions.add(sig)
            node.action_execution_counts[sig] = 5

        strategy.graph.states["s1"] = node
        assert strategy.should_backtrack("s1") is False

    def test_state_not_in_graph(self):
        """Unknown state -> True (backtrack to known territory)."""
        strategy = _make_strategy()
        assert strategy.should_backtrack("unknown") is True

    def test_single_node_graph(self):
        """Single fully-saturated node -> True."""
        strategy = _make_strategy(backtrack_threshold=0.8)

        node = ScreenNode(screen_hash="s1", activity="Test", total_actions=3)
        for i in range(3):
            sig = ((i * 10, 0), "CLICK")
            node.executed_actions.add(sig)
            node.action_execution_counts[sig] = 3

        strategy.graph.states["s1"] = node
        assert strategy.should_backtrack("s1") is True

    def test_successor_reenablement(self):
        """Actions with incomplete successors are preserved (not backtracked)."""
        strategy = _make_strategy(has_incomplete=True, backtrack_threshold=0.8)

        node = ScreenNode(screen_hash="s1", activity="Test", total_actions=5)
        for i in range(5):
            sig = ((i * 10, 0), "CLICK")
            node.executed_actions.add(sig)
            node.action_execution_counts[sig] = 3

        strategy.graph.states["s1"] = node
        assert strategy.should_backtrack("s1") is False

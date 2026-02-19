"""
Tests for find_nearest_unsaturated() hop count (gh26 Group 5, task 5.5).

Verifies BFS returns correct distance to nearest unsaturated ancestor.
"""

import pytest
from unittest.mock import MagicMock

from rv_agent.domain.screen_node import ScreenNode
from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker


def _make_graph_with_nodes(node_data):
    """Create mock graph with ScreenNodes.

    Args:
        node_data: dict of {hash: (total_actions, saturated_count)}
    """
    graph = MagicMock()
    nodes = {}
    for h, (total, saturated) in node_data.items():
        node = ScreenNode(screen_hash=h, activity="Test", total_actions=total)
        for i in range(saturated):
            sig = ((i * 10, 0), "CLICK")
            node.executed_actions.add(sig)
            node.action_execution_counts[sig] = 2
        nodes[h] = node
    graph.states = nodes
    return graph


class TestFindNearestUnsaturatedHopCount:
    """Verify BFS returns (state_hash, hop_count) tuple."""

    def test_returns_hop_count_1(self):
        """Direct parent is unsaturated -> hop_count = 1."""
        graph = _make_graph_with_nodes({
            "s0": (5, 5),   # Current: fully saturated
            "s1": (5, 2),   # Parent: not saturated
        })
        config = MagicMock()
        config.backtrack_saturation_threshold = 0.8
        tracker = SuccessorTracker(graph, config=config)
        tracker.record_back_transition("s0", "s1")

        result = tracker.find_nearest_unsaturated("s0")

        assert result is not None
        state_hash, hop_count = result
        assert state_hash == "s1"
        assert hop_count == 1

    def test_returns_hop_count_3(self):
        """Unsaturated ancestor 3 hops away."""
        graph = _make_graph_with_nodes({
            "s0": (5, 5),   # Current: saturated
            "s1": (5, 5),   # Parent: saturated
            "s2": (5, 5),   # Grandparent: saturated
            "s3": (5, 2),   # Great-grandparent: NOT saturated
        })
        config = MagicMock()
        config.backtrack_saturation_threshold = 0.8
        tracker = SuccessorTracker(graph, config=config)
        tracker.record_back_transition("s0", "s1")
        tracker.record_back_transition("s1", "s2")
        tracker.record_back_transition("s2", "s3")

        result = tracker.find_nearest_unsaturated("s0")

        assert result is not None
        state_hash, hop_count = result
        assert state_hash == "s3"
        assert hop_count == 3

    def test_returns_none_all_saturated(self):
        """All reachable states saturated -> None."""
        graph = _make_graph_with_nodes({
            "s0": (3, 3),
            "s1": (3, 3),
        })
        config = MagicMock()
        config.backtrack_saturation_threshold = 0.8
        tracker = SuccessorTracker(graph, config=config)
        tracker.record_back_transition("s0", "s1")

        result = tracker.find_nearest_unsaturated("s0")
        assert result is None

    def test_picks_nearest_not_deepest(self):
        """BFS picks nearest unsaturated, not deepest."""
        graph = _make_graph_with_nodes({
            "s0": (5, 5),   # Current: saturated
            "s1": (5, 2),   # Parent 1 hop: NOT saturated
            "s2": (5, 2),   # Grandparent 2 hops: also NOT saturated
        })
        config = MagicMock()
        config.backtrack_saturation_threshold = 0.8
        tracker = SuccessorTracker(graph, config=config)
        tracker.record_back_transition("s0", "s1")
        tracker.record_back_transition("s1", "s2")

        result = tracker.find_nearest_unsaturated("s0")

        assert result is not None
        state_hash, hop_count = result
        assert state_hash == "s1"
        assert hop_count == 1

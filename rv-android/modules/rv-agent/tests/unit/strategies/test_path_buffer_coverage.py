"""
Tests for PathBuffer.plan_coverage_path() — Strategy C.

BFS on SuccessorTracker's back_successors to find the ancestor state with
highest exploration_potential (coverage_gap * element_count).
"""

import pytest
from unittest.mock import MagicMock

from rv_agent.strategies.rvagent_strategy.path_buffer import (
    PathBuffer,
    MAX_COVERAGE_HOPS,
)


@pytest.fixture
def mock_successor_tracker():
    tracker = MagicMock()
    tracker.back_successors = {}
    return tracker


@pytest.fixture
def mock_ui_coverage():
    return MagicMock()


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.backtrack_saturation_threshold = 0.8
    return config


def _make_path_buffer(successor_tracker, ui_coverage, config, transition_manager=None):
    return PathBuffer(
        transition_manager=transition_manager,
        successor_tracker=successor_tracker,
        ui_coverage_tracker=ui_coverage,
        config=config,
    )


class TestPlanCoveragePath:
    """Tests for PathBuffer Strategy C: coverage-based navigation."""

    def test_plan_coverage_path_highest_potential(
        self, mock_successor_tracker, mock_ui_coverage, mock_config
    ):
        """Screen with exploration_potential 7.5 preferred over 2.0."""
        # Current state -> ancestor_A (1 hop), ancestor_B (2 hops)
        mock_successor_tracker.back_successors = {
            "current": {"ancestor_A"},
            "ancestor_A": {"ancestor_B"},
        }

        # ancestor_A: gap=0.2, elements=10 -> potential=2.0
        # ancestor_B: gap=0.5, elements=15 -> potential=7.5
        def mock_gap(state_hash):
            return {"ancestor_A": 0.2, "ancestor_B": 0.5}.get(state_hash, 0.0)

        def mock_count(state_hash):
            return {"ancestor_A": 10, "ancestor_B": 15}.get(state_hash, 0)

        mock_ui_coverage.get_coverage_gap = MagicMock(side_effect=mock_gap)
        mock_ui_coverage.get_element_count = MagicMock(side_effect=mock_count)

        # Need at least 3 screens to avoid cold start
        mock_successor_tracker.graph = MagicMock()
        mock_successor_tracker.graph.states = {
            "current": MagicMock(),
            "ancestor_A": MagicMock(),
            "ancestor_B": MagicMock(),
        }

        pb = _make_path_buffer(mock_successor_tracker, mock_ui_coverage, mock_config)
        result = pb.plan_coverage_path("current")

        assert result is True
        # ancestor_B has higher potential (7.5 > 2.0), needs 2 BACK hops
        assert pb.remaining_steps == 2

    def test_plan_coverage_path_cold_start(
        self, mock_successor_tracker, mock_ui_coverage, mock_config
    ):
        """Fewer than 3 screens -> returns False."""
        mock_successor_tracker.graph = MagicMock()
        mock_successor_tracker.graph.states = {
            "state_A": MagicMock(),
            "state_B": MagicMock(),
        }

        pb = _make_path_buffer(mock_successor_tracker, mock_ui_coverage, mock_config)
        result = pb.plan_coverage_path("state_A")

        assert result is False
        assert pb.is_active is False

    def test_plan_coverage_path_max_hops(
        self, mock_successor_tracker, mock_ui_coverage, mock_config
    ):
        """Target beyond MAX_COVERAGE_HOPS -> not selected."""
        # Build a chain longer than MAX_COVERAGE_HOPS
        states = {}
        back_successors = {}
        prev = "current"
        for i in range(MAX_COVERAGE_HOPS + 2):
            name = f"far_{i}"
            states[name] = MagicMock()
            back_successors[prev] = {name}
            prev = name

        states["current"] = MagicMock()
        mock_successor_tracker.graph = MagicMock()
        mock_successor_tracker.graph.states = states
        mock_successor_tracker.back_successors = back_successors

        # Only the farthest state has high potential
        def mock_gap(state_hash):
            if state_hash == f"far_{MAX_COVERAGE_HOPS + 1}":
                return 0.8
            return 0.0  # All others fully covered

        def mock_count(state_hash):
            if state_hash == f"far_{MAX_COVERAGE_HOPS + 1}":
                return 20
            return 5

        mock_ui_coverage.get_coverage_gap = MagicMock(side_effect=mock_gap)
        mock_ui_coverage.get_element_count = MagicMock(side_effect=mock_count)

        pb = _make_path_buffer(mock_successor_tracker, mock_ui_coverage, mock_config)
        result = pb.plan_coverage_path("current")

        assert result is False  # Only high-potential target is beyond max hops

    def test_plan_coverage_path_all_covered(
        self, mock_successor_tracker, mock_ui_coverage, mock_config
    ):
        """All screens 95%+ covered -> returns False."""
        mock_successor_tracker.back_successors = {
            "current": {"ancestor_A", "ancestor_B"},
        }
        mock_successor_tracker.graph = MagicMock()
        mock_successor_tracker.graph.states = {
            "current": MagicMock(),
            "ancestor_A": MagicMock(),
            "ancestor_B": MagicMock(),
        }

        # All screens have 0 coverage gap (fully covered)
        mock_ui_coverage.get_coverage_gap = MagicMock(return_value=0.0)
        mock_ui_coverage.get_element_count = MagicMock(return_value=10)

        pb = _make_path_buffer(mock_successor_tracker, mock_ui_coverage, mock_config)
        result = pb.plan_coverage_path("current")

        assert result is False

    def test_strategy_c_before_b_ordering(
        self, mock_successor_tracker, mock_ui_coverage, mock_config
    ):
        """When both C and B can plan, C is evaluated first in Tier 3."""
        # Set up for C to succeed
        mock_successor_tracker.back_successors = {
            "current": {"ancestor"},
        }
        mock_successor_tracker.graph = MagicMock()
        mock_successor_tracker.graph.states = {
            "current": MagicMock(),
            "ancestor": MagicMock(),
            "other": MagicMock(),
        }
        mock_ui_coverage.get_coverage_gap = MagicMock(return_value=0.6)
        mock_ui_coverage.get_element_count = MagicMock(return_value=10)

        # Set up for B to also succeed
        mock_tm = MagicMock()
        mock_tm.plan_path_to_mop_activity = MagicMock(
            return_value=[{"action_type": "BACK"}]
        )

        pb = _make_path_buffer(
            mock_successor_tracker,
            mock_ui_coverage,
            mock_config,
            transition_manager=mock_tm,
        )

        # C succeeds
        c_result = pb.plan_coverage_path("current")
        assert c_result is True

        # In actual Tier 3 code: C > B > A ordering means B is NOT called if C succeeds
        # This test validates C works independently; the ordering is tested in
        # test_proactive_backtracking.py::test_action_selection_order

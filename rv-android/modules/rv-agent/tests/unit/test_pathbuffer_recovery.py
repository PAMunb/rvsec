"""
Unit tests for PathBuffer death spiral recovery (Group 12).

Tests invalidate_current_path() behavior and verifies that failed actions
are not re-emitted after invalidation.
"""

import pytest
from unittest.mock import MagicMock, patch

from rv_agent.strategies.rvagent_strategy.path_buffer import (
    PathBuffer,
    _create_back_action,
    MAX_BACKTRACK_HOPS,
)


def _make_path_buffer(
    successor_tracker=None,
    transition_manager=None,
    ui_coverage_tracker=None,
    config=None,
):
    """Create a PathBuffer with mocked dependencies."""
    if successor_tracker is None:
        successor_tracker = MagicMock()
        successor_tracker.graph = MagicMock()
        successor_tracker.graph.states = {"s1": MagicMock(), "s2": MagicMock(), "s3": MagicMock()}
        successor_tracker.back_successors = {}
    if ui_coverage_tracker is None:
        ui_coverage_tracker = MagicMock()
        ui_coverage_tracker.get_coverage_gap.return_value = 0.0
        ui_coverage_tracker.get_element_count.return_value = 0
    if config is None:
        config = MagicMock()
        config.backtrack_saturation_threshold = 0.8
    return PathBuffer(
        transition_manager=transition_manager,
        successor_tracker=successor_tracker,
        ui_coverage_tracker=ui_coverage_tracker,
        config=config,
    )


class TestInvalidateCurrentPath:
    """Tests for PathBuffer.invalidate_current_path()."""

    def test_invalidate_clears_buffer(self):
        """After invalidate_current_path(), the buffer is empty."""
        pb = _make_path_buffer()
        # Manually fill buffer with BACK actions
        pb._buffer = [_create_back_action() for _ in range(3)]
        assert pb.is_active
        assert pb.remaining_steps == 3

        pb.invalidate_current_path()

        assert not pb.is_active
        assert pb.remaining_steps == 0

    def test_invalidate_prevents_re_emission(self):
        """After invalidation, get_next_action returns None."""
        pb = _make_path_buffer()
        pb._buffer = [_create_back_action() for _ in range(2)]

        pb.invalidate_current_path()

        assert pb.get_next_action() is None

    def test_invalidate_on_empty_buffer_is_noop(self):
        """Calling invalidate_current_path on empty buffer does nothing."""
        pb = _make_path_buffer()
        assert not pb.is_active

        # Should not raise
        pb.invalidate_current_path()

        assert not pb.is_active

    def test_invalidate_vs_invalidate_current_path(self):
        """Both invalidate methods clear the buffer completely."""
        pb1 = _make_path_buffer()
        pb2 = _make_path_buffer()

        pb1._buffer = [_create_back_action() for _ in range(3)]
        pb2._buffer = [_create_back_action() for _ in range(3)]

        pb1.invalidate()
        pb2.invalidate_current_path()

        assert not pb1.is_active
        assert not pb2.is_active

    def test_plan_after_invalidation_works(self):
        """PathBuffer can plan a new path after invalidation."""
        successor_tracker = MagicMock()
        successor_tracker.find_nearest_unsaturated.return_value = ("target_hash", 2)
        successor_tracker.graph = MagicMock()
        successor_tracker.graph.states = {"s1": MagicMock(), "s2": MagicMock(), "s3": MagicMock()}

        pb = _make_path_buffer(successor_tracker=successor_tracker)

        # First path
        pb._buffer = [_create_back_action() for _ in range(3)]
        pb.invalidate_current_path()

        # Plan new path after invalidation
        result = pb.plan_backtrack_path("current_hash")
        assert result is True
        assert pb.is_active
        assert pb.remaining_steps == 2


class TestAlgorithmNodeInvalidation:
    """Tests for algorithm_node calling invalidate_current_path on coord failure."""

    def test_algorithm_node_invalidates_on_coord_failure(self):
        """When coords fail, algorithm_node calls invalidate_current_path."""
        from rv_agent.agent.nodes.algorithm_node import algorithm_node

        agent = MagicMock()
        agent.config.package_name = "com.test.app"
        agent.consecutive_no_action = 0
        agent.NO_ACTION_THRESHOLD = 10

        # Create a mock strategy with path_buffer
        agent.strategy = MagicMock()
        agent.strategy.path_buffer = MagicMock()

        # Create an ItemAction with no coordinates (will fail coord resolution)
        mock_item_action = MagicMock()
        mock_item_action.action_type = "CLICK"
        mock_item_action.event = MagicMock()
        mock_item_action.event.name = "CLICK"
        mock_item_action.id = 0
        mock_item_action.text = "Navigate to com.test.activity..."
        mock_item_action.get_execution_coordinates.return_value = None
        mock_item_action.target_view = {}

        agent.strategy.select_next_action.return_value = mock_item_action

        agent.routing_manager = MagicMock()
        agent.routing_manager.forced_back_count = 0

        state = {
            "current_screen_hash": "abc123",
            "screen_description": MagicMock(),
            "force_restart_app": False,
            "force_back_action": False,
            "force_fill_input": False,
        }

        result = algorithm_node(agent, state)

        # Verify invalidate_current_path was called
        agent.strategy.path_buffer.invalidate_current_path.assert_called_once()
        # Result should indicate no action
        assert result["current_action"] is None

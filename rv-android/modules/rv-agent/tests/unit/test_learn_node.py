"""
Unit tests for learn_node.

Tests memory updates, stuck detection, and UI coverage integration.
"""

from unittest.mock import MagicMock

from rv_agent.agent.nodes.learn_node import (
    learn_node,
)


class TestLearnNodeIntegration:
    """Test learn_node function with UI coverage integration."""

    def test_learn_node_does_not_call_ui_coverage_directly(self):
        """learn_node no longer calls UI coverage directly (moved to execute_node)."""
        # Setup comprehensive mock agent
        mock_ui_coverage = MagicMock()
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = mock_ui_coverage
        mock_screen_processor.device_dimensions = (1080, 1920)

        mock_memory_coordinator = MagicMock()
        mock_memory_coordinator.update_memories.return_value = {
            "recent_action_window": []
        }
        mock_memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "",
            "exploration_summary": "",
            "memory_insights": "",
            "navigation_path": "",
        }
        mock_memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [],
            "state_transitions": [],
        }
        mock_memory_coordinator.check_continuation.return_value = {
            "should_continue": True
        }

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor
        mock_agent.memory_coordinator = mock_memory_coordinator
        mock_agent.stuck_screen_count = 0
        mock_agent.last_screen_hash = "prev_hash"
        mock_agent.BASE_STUCK_THRESHOLD = 8
        mock_agent.STUCK_THRESHOLD_FACTOR = 1.5
        mock_agent.metrics_collector = None
        mock_agent._last_action_was_stuck_back = False
        mock_agent.stuck_recovery = None

        # Create mock screen description with element
        mock_item = MagicMock()
        mock_item.view = {"bounds": [[490, 910], [590, 1010]]}
        mock_screen_desc = MagicMock()
        mock_screen_desc.items = [mock_item]

        state = {
            "current_screen_hash": "new_hash",
            "current_activity": ".MainActivity",
            "current_action": {
                "action_type": "CLICK",
                "original_coords": [500, 500],  # Normalized coords
            },
            "screen_description": mock_screen_desc,
            "iteration": 1,
        }

        learn_node(mock_agent, state)

        # Verify ui_coverage.record_interaction was NOT called from learn_node
        # (UI coverage recording now happens in execute_node)
        mock_ui_coverage.record_interaction.assert_not_called()

    def test_learn_node_continues_on_ui_coverage_error(self):
        """learn_node continues even if ui_coverage fails."""
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = None  # No ui_coverage

        mock_memory_coordinator = MagicMock()
        mock_memory_coordinator.update_memories.return_value = {
            "recent_action_window": []
        }
        mock_memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "",
            "exploration_summary": "",
            "memory_insights": "",
            "navigation_path": "",
        }
        mock_memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [],
            "state_transitions": [],
        }
        mock_memory_coordinator.check_continuation.return_value = {
            "should_continue": True
        }

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor
        mock_agent.memory_coordinator = mock_memory_coordinator
        mock_agent.stuck_screen_count = 0
        mock_agent.last_screen_hash = "prev_hash"
        mock_agent.BASE_STUCK_THRESHOLD = 8
        mock_agent.STUCK_THRESHOLD_FACTOR = 1.5
        mock_agent.metrics_collector = None
        mock_agent._last_action_was_stuck_back = False
        mock_agent.stuck_recovery = None

        state = {
            "current_screen_hash": "new_hash",
            "current_activity": ".MainActivity",
            "current_action": {"action_type": "CLICK"},
            "iteration": 1,
        }

        # Should not raise
        result = learn_node(mock_agent, state)

        assert "should_continue" in result


class TestLearnNodeStuckDetection:
    """Test stuck state detection in learn_node."""

    def test_increments_stuck_count_on_same_hash(self):
        """Increments stuck count when screen unchanged."""
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = None

        mock_memory_coordinator = MagicMock()
        mock_memory_coordinator.update_memories.return_value = {
            "recent_action_window": []
        }
        mock_memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "",
            "exploration_summary": "",
            "memory_insights": "",
            "navigation_path": "",
        }
        mock_memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [],
            "state_transitions": [],
        }
        mock_memory_coordinator.check_continuation.return_value = {
            "should_continue": True
        }

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor
        mock_agent.memory_coordinator = mock_memory_coordinator
        mock_agent.stuck_screen_count = 0
        mock_agent.last_screen_hash = "same_hash"
        mock_agent.BASE_STUCK_THRESHOLD = 8
        mock_agent.STUCK_THRESHOLD_FACTOR = 1.5
        mock_agent.metrics_collector = None
        mock_agent._last_action_was_stuck_back = False
        mock_agent.stuck_recovery = None

        state = {"current_screen_hash": "same_hash", "iteration": 1}

        learn_node(mock_agent, state)

        assert mock_agent.stuck_screen_count == 1

    def test_resets_stuck_count_on_new_hash(self):
        """Resets stuck count when screen changes."""
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = None

        mock_memory_coordinator = MagicMock()
        mock_memory_coordinator.update_memories.return_value = {
            "recent_action_window": []
        }
        mock_memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "",
            "exploration_summary": "",
            "memory_insights": "",
            "navigation_path": "",
        }
        mock_memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [],
            "state_transitions": [],
        }
        mock_memory_coordinator.check_continuation.return_value = {
            "should_continue": True
        }

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor
        mock_agent.memory_coordinator = mock_memory_coordinator
        mock_agent.stuck_screen_count = 2
        mock_agent.last_screen_hash = "old_hash"
        mock_agent.BASE_STUCK_THRESHOLD = 8
        mock_agent.STUCK_THRESHOLD_FACTOR = 1.5
        mock_agent.metrics_collector = None
        mock_agent._last_action_was_stuck_back = False
        mock_agent.stuck_recovery = None

        state = {"current_screen_hash": "new_hash", "iteration": 1}

        learn_node(mock_agent, state)

        assert mock_agent.stuck_screen_count == 0

    def test_forces_back_on_stuck_threshold(self):
        """Forces BACK action when stuck threshold reached."""
        mock_screen_processor = MagicMock()
        mock_screen_processor.ui_coverage = None

        mock_memory_coordinator = MagicMock()
        mock_memory_coordinator.update_memories.return_value = {
            "recent_action_window": []
        }
        mock_memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "",
            "exploration_summary": "",
            "memory_insights": "",
            "navigation_path": "",
        }
        mock_memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [],
            "state_transitions": [],
        }
        mock_memory_coordinator.check_continuation.return_value = {
            "should_continue": True
        }

        mock_agent = MagicMock()
        mock_agent.screen_processor = mock_screen_processor
        mock_agent.memory_coordinator = mock_memory_coordinator
        mock_agent.stuck_screen_count = (
            7  # One below threshold (BASE_STUCK_THRESHOLD=8)
        )
        mock_agent.last_screen_hash = "stuck_hash"
        mock_agent.BASE_STUCK_THRESHOLD = 8
        mock_agent.STUCK_THRESHOLD_FACTOR = 1.5
        mock_agent.metrics_collector = None
        mock_agent._last_action_was_stuck_back = False
        mock_agent.stuck_recovery = None

        state = {"current_screen_hash": "stuck_hash", "iteration": 1}

        result = learn_node(mock_agent, state)

        assert result.get("force_back_action") is True
        assert mock_agent.stuck_screen_count == 0  # Reset after forcing back

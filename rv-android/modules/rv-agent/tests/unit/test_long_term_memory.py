"""
Unit tests for LongTermMemory.

Tests cross-session persistence including:
- State recording and tracking
- Action recording with success rates
- State transition tracking
- Guidance generation for ReAct
- Statistics calculation
"""

import pytest
import time
from unittest.mock import MagicMock, patch

from rv_agent.memory.long_term import LongTermMemory, MemoryState, MemoryAction


class TestMemoryState:
    """Test MemoryState dataclass."""

    def test_creation(self):
        """Creates state with required fields."""
        state = MemoryState(
            fingerprint="hash123",
            activity="MainActivity"
        )

        assert state.fingerprint == "hash123"
        assert state.activity == "MainActivity"
        assert state.visit_count == 0
        assert state.first_visit > 0
        assert state.last_visit > 0
        assert state.all_actions == set()
        assert state.outgoing_transitions == {}
        assert state.incoming_transitions == {}

    def test_first_visit_defaults_to_now(self):
        """First visit defaults to current time."""
        before = time.time()
        state = MemoryState(fingerprint="hash", activity="Main")
        after = time.time()

        assert before <= state.first_visit <= after

    def test_custom_initial_values(self):
        """Accepts custom initial values."""
        state = MemoryState(
            fingerprint="hash",
            activity="Main",
            visit_count=5,
            interactive_elements_count=10
        )

        assert state.visit_count == 5
        assert state.interactive_elements_count == 10


class TestMemoryAction:
    """Test MemoryAction dataclass."""

    def test_creation(self):
        """Creates action with required fields."""
        action = MemoryAction(
            id=1,
            text="click button",
            action_type="click"
        )

        assert action.id == 1
        assert action.text == "click button"
        assert action.action_type == "click"
        assert action.execution_count == 0
        assert action.success_count == 0
        assert action.reaches_mop is False

    def test_success_rate_no_executions(self):
        """Success rate is 0 with no executions."""
        action = MemoryAction(id=1, text="click", action_type="click")

        assert action.success_rate == 0.0

    def test_success_rate_all_success(self):
        """Success rate is 1.0 with all successes."""
        action = MemoryAction(
            id=1,
            text="click",
            action_type="click",
            execution_count=5,
            success_count=5
        )

        assert action.success_rate == 1.0

    def test_success_rate_partial(self):
        """Calculates partial success rate."""
        action = MemoryAction(
            id=1,
            text="click",
            action_type="click",
            execution_count=4,
            success_count=2
        )

        assert action.success_rate == 0.5

    def test_state_transitions_initialized(self):
        """State transitions are initialized as defaultdict."""
        action = MemoryAction(id=1, text="click", action_type="click")

        # Should not raise KeyError
        action.state_transitions["hash1"].append("hash2")

        assert "hash1" in action.state_transitions
        assert action.state_transitions["hash1"] == ["hash2"]


class TestLongTermMemoryInit:
    """Test LongTermMemory initialization."""

    @patch('rv_agent.memory.long_term.LoggingManager')
    @patch('rv_agent.memory.long_term.ErrorHandler')
    def test_initialization(self, mock_error, mock_logging):
        """Initializes with empty collections."""
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        mock_error.get_instance.return_value = MagicMock()

        memory = LongTermMemory()

        assert memory.states == {}
        assert memory.actions == {}
        assert memory.total_states == 0
        assert memory.total_activities == 0
        assert memory.total_actions == 0

    @patch('rv_agent.memory.long_term.LoggingManager')
    @patch('rv_agent.memory.long_term.ErrorHandler')
    def test_initialization_with_static_data(self, mock_error, mock_logging):
        """Accepts static data."""
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        mock_error.get_instance.return_value = MagicMock()
        static_data = MagicMock()

        memory = LongTermMemory(static_data=static_data)

        assert memory.static_data == static_data


class TestRecordState:
    """Test record_state method."""

    @pytest.fixture
    def memory(self):
        with patch('rv_agent.memory.long_term.LoggingManager') as mock_logging:
            with patch('rv_agent.memory.long_term.ErrorHandler') as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
                mock_error.get_instance.return_value = MagicMock()
                return LongTermMemory()

    def test_records_new_state(self, memory):
        """Records new state with fingerprint and activity."""
        memory.record_state("hash123", "MainActivity", 10)

        assert "hash123" in memory.states
        assert memory.states["hash123"].activity == "MainActivity"
        assert memory.states["hash123"].interactive_elements_count == 10
        assert memory.total_states == 1

    def test_updates_existing_state(self, memory):
        """Updates visit count for existing state."""
        memory.record_state("hash123", "MainActivity")
        memory.record_state("hash123", "MainActivity")

        assert memory.states["hash123"].visit_count == 2
        assert memory.total_states == 1  # Still only one unique state

    def test_tracks_activity_mapping(self, memory):
        """Tracks activity to state mapping."""
        memory.record_state("hash1", "MainActivity")
        memory.record_state("hash2", "MainActivity")
        memory.record_state("hash3", "SettingsActivity")

        assert len(memory.activities["MainActivity"]) == 2
        assert len(memory.activities["SettingsActivity"]) == 1
        assert memory.total_activities == 2

    def test_updates_last_visit(self, memory):
        """Updates last visit timestamp."""
        memory.record_state("hash123", "MainActivity")
        first_visit = memory.states["hash123"].last_visit

        time.sleep(0.01)  # Small delay
        memory.record_state("hash123", "MainActivity")
        second_visit = memory.states["hash123"].last_visit

        assert second_visit > first_visit


class TestRecordAction:
    """Test record_action method."""

    @pytest.fixture
    def memory(self):
        with patch('rv_agent.memory.long_term.LoggingManager') as mock_logging:
            with patch('rv_agent.memory.long_term.ErrorHandler') as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
                mock_error.get_instance.return_value = MagicMock()
                return LongTermMemory()

    def test_records_new_action(self, memory):
        """Records new action."""
        memory.record_action(1, "click button", "click", True, "hash1", "hash2")

        assert 1 in memory.actions
        assert memory.actions[1].text == "click button"
        assert memory.total_actions == 1

    def test_tracks_execution_count(self, memory):
        """Tracks execution count for action."""
        memory.record_action(1, "click", "click", True, "hash1")
        memory.record_action(1, "click", "click", False, "hash1")

        assert memory.actions[1].execution_count == 2

    def test_tracks_success_count(self, memory):
        """Tracks success count for action."""
        memory.record_action(1, "click", "click", True, "hash1")
        memory.record_action(1, "click", "click", True, "hash1")
        memory.record_action(1, "click", "click", False, "hash1")

        assert memory.actions[1].success_count == 2
        assert memory.actions[1].success_rate == 2/3

    def test_records_state_transition(self, memory):
        """Records state transition when to_state differs from from_state."""
        memory.record_action(1, "click", "click", True, "hash1", "hash2")

        assert "hash1" in memory.actions[1].state_transitions
        assert "hash2" in memory.actions[1].state_transitions["hash1"]
        assert len(memory.transitions) == 1

    def test_no_transition_for_same_state(self, memory):
        """No transition recorded when to_state equals from_state."""
        memory.record_action(1, "click", "click", True, "hash1", "hash1")

        assert len(memory.transitions) == 0

    def test_no_transition_when_to_state_none(self, memory):
        """No transition recorded when to_state is None."""
        memory.record_action(1, "click", "click", True, "hash1", None)

        assert len(memory.transitions) == 0


class TestGetStateGuidance:
    """Test get_state_guidance method."""

    @pytest.fixture
    def memory(self):
        with patch('rv_agent.memory.long_term.LoggingManager') as mock_logging:
            with patch('rv_agent.memory.long_term.ErrorHandler') as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
                mock_error.get_instance.return_value = MagicMock()
                return LongTermMemory()

    def test_unknown_state_guidance(self, memory):
        """Unknown state returns high priority."""
        guidance = memory.get_state_guidance("unknown_hash")

        assert guidance["is_known_state"] is False
        assert guidance["new_state"] is True
        assert guidance["exploration_priority"] == "high"

    def test_known_state_guidance(self, memory):
        """Known state returns visit info."""
        memory.record_state("hash123", "MainActivity", 10)
        memory.record_state("hash123", "MainActivity")  # Second visit

        guidance = memory.get_state_guidance("hash123")

        assert guidance["is_known_state"] is True
        assert guidance["visit_count"] == 2
        assert guidance["activity"] == "MainActivity"
        assert guidance["interactive_elements_count"] == 10

    def test_low_priority_frequently_visited(self, memory):
        """Frequently visited state has low priority."""
        memory.record_state("hash123", "MainActivity")
        for _ in range(4):
            memory.record_state("hash123", "MainActivity")

        guidance = memory.get_state_guidance("hash123")

        assert guidance["exploration_priority"] == "low"

    def test_includes_successful_actions(self, memory):
        """Includes successful actions from this state."""
        memory.record_state("hash1", "Main")
        memory.record_action(1, "click button", "click", True, "hash1", "hash2")
        memory.record_action(1, "click button", "click", True, "hash1", "hash2")

        guidance = memory.get_state_guidance("hash1")

        assert len(guidance["successful_actions"]) > 0
        assert guidance["successful_actions"][0]["text"] == "click button"

    def test_filters_low_success_actions(self, memory):
        """Filters out actions with low success rate."""
        memory.record_state("hash1", "Main")
        # 0.4 success rate (below 50% threshold)
        memory.record_action(1, "click", "click", True, "hash1", "hash2")
        memory.record_action(1, "click", "click", True, "hash1", "hash2")
        memory.record_action(1, "click", "click", False, "hash1")
        memory.record_action(1, "click", "click", False, "hash1")
        memory.record_action(1, "click", "click", False, "hash1")

        guidance = memory.get_state_guidance("hash1")

        assert len(guidance["successful_actions"]) == 0


class TestGetUnexploredTransitions:
    """Test get_unexplored_transitions method."""

    @pytest.fixture
    def memory(self):
        with patch('rv_agent.memory.long_term.LoggingManager') as mock_logging:
            with patch('rv_agent.memory.long_term.ErrorHandler') as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
                mock_error.get_instance.return_value = MagicMock()
                return LongTermMemory()

    def test_unknown_state_returns_suggestions(self, memory):
        """Unknown state returns exploration suggestions."""
        transitions = memory.get_unexplored_transitions("unknown")

        assert "explore_new_elements" in transitions
        assert "try_different_actions" in transitions

    def test_returns_underexplored_actions(self, memory):
        """Returns actions with low execution count."""
        memory.record_state("hash1", "Main")
        memory.record_action(1, "click button1", "click", True, "hash1", "hash2")
        memory.record_action(2, "click button2", "click", True, "hash1", "hash3")

        transitions = memory.get_unexplored_transitions("hash1")

        assert len(transitions) == 2
        assert "click button1" in transitions
        assert "click button2" in transitions

    def test_filters_well_explored_actions(self, memory):
        """Filters out actions with 3+ executions."""
        memory.record_state("hash1", "Main")
        # Action with 3 executions
        memory.record_action(1, "click", "click", True, "hash1", "hash2")
        memory.record_action(1, "click", "click", True, "hash1", "hash2")
        memory.record_action(1, "click", "click", True, "hash1", "hash2")

        transitions = memory.get_unexplored_transitions("hash1")

        assert "click" not in transitions


class TestGetStatistics:
    """Test get_statistics method."""

    @pytest.fixture
    def memory(self):
        with patch('rv_agent.memory.long_term.LoggingManager') as mock_logging:
            with patch('rv_agent.memory.long_term.ErrorHandler') as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
                mock_error.get_instance.return_value = MagicMock()
                return LongTermMemory()

    def test_empty_statistics(self, memory):
        """Empty memory returns zero stats."""
        stats = memory.get_statistics()

        assert stats["total_states"] == 0
        assert stats["total_activities"] == 0
        assert stats["total_action_types"] == 0
        assert stats["overall_success_rate"] == 0.0

    def test_comprehensive_statistics(self, memory):
        """Returns comprehensive statistics with data."""
        memory.record_state("hash1", "MainActivity")
        memory.record_state("hash2", "SettingsActivity")
        memory.record_action(1, "click", "click", True, "hash1", "hash2")
        memory.record_action(2, "type", "type", False, "hash2")

        stats = memory.get_statistics()

        assert stats["total_states"] == 2
        assert stats["total_activities"] == 2
        assert stats["total_action_types"] == 2
        assert stats["total_actions_executed"] == 2
        assert stats["total_successful_actions"] == 1
        assert stats["overall_success_rate"] == 0.5
        assert stats["total_transitions"] == 1

    def test_most_visited_states(self, memory):
        """Returns most visited states."""
        memory.record_state("hash1", "Main")
        memory.record_state("hash1", "Main")
        memory.record_state("hash1", "Main")
        memory.record_state("hash2", "Settings")

        stats = memory.get_statistics()

        assert len(stats["most_visited_states"]) == 2
        assert stats["most_visited_states"][0]["visit_count"] == 3


class TestClearMemory:
    """Test clear_memory method."""

    @pytest.fixture
    def memory(self):
        with patch('rv_agent.memory.long_term.LoggingManager') as mock_logging:
            with patch('rv_agent.memory.long_term.ErrorHandler') as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
                mock_error.get_instance.return_value = MagicMock()
                return LongTermMemory()

    def test_clears_all_data(self, memory):
        """Clears all memory data."""
        memory.record_state("hash1", "Main")
        memory.record_action(1, "click", "click", True, "hash1", "hash2")

        memory.clear_memory()

        assert len(memory.states) == 0
        assert len(memory.actions) == 0
        assert len(memory.activities) == 0
        assert len(memory.transitions) == 0
        assert memory.total_states == 0
        assert memory.total_activities == 0
        assert memory.total_actions == 0


class TestGetMostVisitedStates:
    """Test _get_most_visited_states method."""

    @pytest.fixture
    def memory(self):
        with patch('rv_agent.memory.long_term.LoggingManager') as mock_logging:
            with patch('rv_agent.memory.long_term.ErrorHandler') as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
                mock_error.get_instance.return_value = MagicMock()
                return LongTermMemory()

    def test_returns_sorted_states(self, memory):
        """Returns states sorted by visit count."""
        memory.record_state("hash1", "Main")
        memory.record_state("hash2", "Settings")
        memory.record_state("hash2", "Settings")
        memory.record_state("hash2", "Settings")

        most_visited = memory._get_most_visited_states(2)

        assert len(most_visited) == 2
        assert most_visited[0]["visit_count"] > most_visited[1]["visit_count"]

    def test_respects_limit(self, memory):
        """Respects limit parameter."""
        for i in range(10):
            memory.record_state(f"hash{i}", f"Activity{i}")

        most_visited = memory._get_most_visited_states(3)

        assert len(most_visited) == 3

    def test_includes_state_info(self, memory):
        """Includes state hash, activity, and element count."""
        memory.record_state("hash123456789", "MainActivity", 15)

        most_visited = memory._get_most_visited_states(1)

        assert most_visited[0]["state_hash"] == "hash12345678"  # Truncated to 12 chars
        assert most_visited[0]["activity"] == "MainActivity"
        assert most_visited[0]["elements_count"] == 15

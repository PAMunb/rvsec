"""
Unit tests for ShortTermMemory.

Tests screen-scoped memory management including:
- Iteration recording and management
- Execution result tracking
- LLM context generation
- Statistics calculation
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from rv_agent.memory.short_term import ShortTermMemory, Iteration


class TestIteration:
    """Test Iteration dataclass."""

    def test_iteration_creation(self):
        """Creates iteration with required fields."""
        iteration = Iteration(state_hash="hash123", activity="MainActivity")

        assert iteration.state_hash == "hash123"
        assert iteration.activity == "MainActivity"
        assert iteration.actions == []
        assert iteration.execution_results == []
        assert iteration.llm_reasoning == ""
        assert isinstance(iteration.timestamp, datetime)

    def test_add_action(self):
        """Adds action to iteration."""
        iteration = Iteration(state_hash="hash", activity="Main")

        iteration.add_action({"action_type": "CLICK", "x": 100})

        assert len(iteration.actions) == 1
        assert iteration.actions[0]["action_type"] == "CLICK"

    def test_add_execution_result(self):
        """Adds execution result to iteration."""
        iteration = Iteration(state_hash="hash", activity="Main")

        iteration.add_execution_result({"success": True, "action": "CLICK"})

        assert len(iteration.execution_results) == 1
        assert iteration.execution_results[0]["success"] is True

    def test_format_for_template_empty_actions(self):
        """Empty actions returns empty string."""
        iteration = Iteration(state_hash="hash", activity="Main")

        result = iteration.format_for_template()

        assert result == ""

    def test_format_for_template_with_actions(self):
        """Formats actions for template."""
        iteration = Iteration(state_hash="hash", activity="Main")
        iteration.add_action(
            {
                "element_id": "btn_submit",
                "action_type": "CLICK",
                "coordinates": [100, 200],
            }
        )

        result = iteration.format_for_template()

        assert "btn_submit" in result
        assert "(100, 200)" in result

    def test_format_for_template_with_results(self):
        """Includes success/failure markers in format."""
        iteration = Iteration(state_hash="hash", activity="Main")
        iteration.add_action({"element_id": "btn1", "coordinates": []})
        iteration.add_action({"element_id": "btn2", "coordinates": []})
        iteration.add_execution_result({"success": True})
        iteration.add_execution_result({"success": False})

        result = iteration.format_for_template()

        assert "✅" in result
        assert "❌" in result

    def test_format_for_template_uses_action_type_fallback(self):
        """Falls back to action_type when no element_id."""
        iteration = Iteration(state_hash="hash", activity="Main")
        iteration.add_action({"action_type": "SCROLL", "coordinates": [100, 200]})

        result = iteration.format_for_template()

        assert "SCROLL" in result

    def test_get_success_rate_no_results(self):
        """Success rate is 0 with no results."""
        iteration = Iteration(state_hash="hash", activity="Main")

        rate = iteration.get_success_rate()

        assert rate == 0.0

    def test_get_success_rate_all_success(self):
        """Success rate is 1.0 with all successes."""
        iteration = Iteration(state_hash="hash", activity="Main")
        iteration.add_execution_result({"success": True})
        iteration.add_execution_result({"success": True})

        rate = iteration.get_success_rate()

        assert rate == 1.0

    def test_get_success_rate_partial(self):
        """Calculates partial success rate correctly."""
        iteration = Iteration(state_hash="hash", activity="Main")
        iteration.add_execution_result({"success": True})
        iteration.add_execution_result({"success": False})
        iteration.add_execution_result({"success": True})
        iteration.add_execution_result({"success": False})

        rate = iteration.get_success_rate()

        assert rate == 0.5


class TestShortTermMemoryInit:
    """Test ShortTermMemory initialization."""

    @patch("rv_agent.memory.short_term.LoggingManager")
    @patch("rv_agent.memory.short_term.ErrorHandler")
    def test_initialization_defaults(self, mock_error, mock_logging):
        """Initializes with default max iterations."""
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        mock_error.get_instance.return_value = MagicMock()

        memory = ShortTermMemory()

        assert memory.iterations == []
        assert memory.current_activity is None

    @patch("rv_agent.memory.short_term.LoggingManager")
    @patch("rv_agent.memory.short_term.ErrorHandler")
    def test_initialization_custom_max(self, mock_error, mock_logging):
        """Accepts custom max iterations."""
        mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
        mock_error.get_instance.return_value = MagicMock()

        memory = ShortTermMemory(max_iterations=10)

        assert memory.max_iterations == 10


class TestRecordIteration:
    """Test record_iteration method."""

    @pytest.fixture
    def memory(self):
        with patch("rv_agent.memory.short_term.LoggingManager") as mock_logging:
            with patch("rv_agent.memory.short_term.ErrorHandler") as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = (
                    MagicMock()
                )
                mock_error.get_instance.return_value = MagicMock()
                return ShortTermMemory(max_iterations=5)

    def test_records_iteration(self, memory):
        """Records iteration with state and actions."""
        state = {"activity": "MainActivity", "hash_screen": "hash123"}
        actions = [{"action_type": "CLICK"}]

        memory.record_iteration(state, actions)

        assert len(memory.iterations) == 1
        assert memory.iterations[0].activity == "MainActivity"
        assert len(memory.iterations[0].actions) == 1

    def test_clears_on_activity_change(self, memory):
        """Clears memory when activity changes."""
        memory.record_iteration(
            {"activity": "MainActivity", "hash_screen": "hash1"},
            [{"action_type": "CLICK"}],
        )
        memory.record_iteration(
            {"activity": "SecondActivity", "hash_screen": "hash2"},
            [{"action_type": "SCROLL"}],
        )

        assert len(memory.iterations) == 1
        assert memory.current_activity == "SecondActivity"

    def test_inserts_recent_first(self, memory):
        """Inserts most recent iteration first."""
        memory.record_iteration(
            {"activity": "Main", "hash_screen": "hash1"}, [{"element_id": "first"}]
        )
        memory.record_iteration(
            {"activity": "Main", "hash_screen": "hash2"}, [{"element_id": "second"}]
        )

        assert memory.iterations[0].actions[0]["element_id"] == "second"
        assert memory.iterations[1].actions[0]["element_id"] == "first"

    def test_respects_max_iterations(self, memory):
        """Limits iterations to max_iterations."""
        for i in range(10):
            memory.record_iteration(
                {"activity": "Main", "hash_screen": f"hash{i}"},
                [{"element_id": f"action{i}"}],
            )

        assert len(memory.iterations) == 5

    def test_records_llm_reasoning(self, memory):
        """Records LLM reasoning with iteration."""
        memory.record_iteration(
            {"activity": "Main", "hash_screen": "hash1"},
            [],
            llm_reasoning="Testing element visibility",
        )

        assert memory.iterations[0].llm_reasoning == "Testing element visibility"

    def test_handles_missing_state_fields(self, memory):
        """Handles missing activity and hash_screen."""
        memory.record_iteration({}, [{"action_type": "CLICK"}])

        assert memory.iterations[0].activity == "unknown"
        assert memory.iterations[0].state_hash == "unknown"


class TestRecordExecutionResults:
    """Test record_execution_results method."""

    @pytest.fixture
    def memory(self):
        with patch("rv_agent.memory.short_term.LoggingManager") as mock_logging:
            with patch("rv_agent.memory.short_term.ErrorHandler") as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = (
                    MagicMock()
                )
                mock_error.get_instance.return_value = MagicMock()
                return ShortTermMemory(max_iterations=5)

    def test_records_results_to_latest(self, memory):
        """Records results to most recent iteration."""
        memory.record_iteration(
            {"activity": "Main", "hash_screen": "hash1"}, [{"action_type": "CLICK"}]
        )

        memory.record_execution_results([{"success": True}])

        assert len(memory.iterations[0].execution_results) == 1
        assert memory.iterations[0].execution_results[0]["success"] is True

    def test_handles_no_iterations(self, memory):
        """Handles case with no iterations to record results."""
        # Should not raise, just log warning
        memory.record_execution_results([{"success": True}])

        # No error should occur

    def test_records_multiple_results(self, memory):
        """Records multiple results at once."""
        memory.record_iteration(
            {"activity": "Main", "hash_screen": "hash1"},
            [{"action_type": "CLICK"}, {"action_type": "TYPE"}],
        )

        memory.record_execution_results([{"success": True}, {"success": False}])

        assert len(memory.iterations[0].execution_results) == 2


class TestGetRecentActionsSummary:
    """Test get_recent_actions_summary method."""

    @pytest.fixture
    def memory(self):
        with patch("rv_agent.memory.short_term.LoggingManager") as mock_logging:
            with patch("rv_agent.memory.short_term.ErrorHandler") as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = (
                    MagicMock()
                )
                mock_error.get_instance.return_value = MagicMock()
                return ShortTermMemory(max_iterations=5)

    def test_empty_memory_returns_message(self, memory):
        """Empty memory returns 'No recent actions'."""
        result = memory.get_recent_actions_summary()

        assert result == "No recent actions."

    def test_formats_recent_iterations(self, memory):
        """Formats recent iterations with timestamps."""
        memory.record_iteration(
            {"activity": "Main", "hash_screen": "hash1"},
            [{"element_id": "btn_submit", "coordinates": [100, 200]}],
        )

        result = memory.get_recent_actions_summary(count=1)

        assert "just now" in result
        assert "btn_submit" in result

    def test_includes_age_indicators(self, memory):
        """Includes age indicators for older iterations."""
        for i in range(3):
            memory.record_iteration(
                {"activity": "Main", "hash_screen": f"hash{i}"},
                [{"element_id": f"btn{i}", "coordinates": []}],
            )

        result = memory.get_recent_actions_summary(count=3)

        assert "just now" in result
        assert "1 iterations ago" in result
        assert "2 iterations ago" in result

    def test_handles_empty_format(self, memory):
        """Returns message when iterations have no formatted text."""
        memory.record_iteration(
            {"activity": "Main", "hash_screen": "hash1"}, []  # No actions
        )

        result = memory.get_recent_actions_summary()

        assert result == "Recent actions had no results."


class TestGetCurrentScreenContext:
    """Test get_current_screen_context method."""

    @pytest.fixture
    def memory(self):
        with patch("rv_agent.memory.short_term.LoggingManager") as mock_logging:
            with patch("rv_agent.memory.short_term.ErrorHandler") as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = (
                    MagicMock()
                )
                mock_error.get_instance.return_value = MagicMock()
                return ShortTermMemory(max_iterations=5)

    def test_new_screen_context(self, memory):
        """Empty memory returns new screen context."""
        context = memory.get_current_screen_context()

        assert context["screen_status"] == "new"
        assert context["interaction_count"] == 0
        assert context["suggested_strategy"] == "explore_elements"

    def test_partially_explored_screen(self, memory):
        """Single iteration returns partially explored."""
        memory.record_iteration(
            {"activity": "Main", "hash_screen": "hash1"}, [{"action_type": "CLICK"}]
        )

        context = memory.get_current_screen_context()

        assert context["screen_status"] == "partially_explored"
        assert context["interaction_count"] == 1

    def test_explored_screen(self, memory):
        """Multiple iterations returns explored."""
        for i in range(3):
            memory.record_iteration(
                {"activity": "Main", "hash_screen": f"hash{i}"},
                [{"action_type": "CLICK"}],
            )

        context = memory.get_current_screen_context()

        assert context["screen_status"] == "explored"

    def test_low_success_rate_strategy(self, memory):
        """Low success rate suggests different approach."""
        for i in range(3):
            memory.record_iteration(
                {"activity": "Main", "hash_screen": f"hash{i}"},
                [{"action_type": "CLICK"}],
            )
            memory.record_execution_results([{"success": False}])

        context = memory.get_current_screen_context()

        assert context["suggested_strategy"] == "try_different_approach"

    def test_high_success_rate_strategy(self, memory):
        """High success rate suggests deepening exploration."""
        for i in range(5):
            memory.record_iteration(
                {"activity": "Main", "hash_screen": f"hash{i}"},
                [{"action_type": "CLICK"}],
            )
            memory.record_execution_results([{"success": True}])

        context = memory.get_current_screen_context()

        assert context["suggested_strategy"] == "deepen_exploration"

    def test_includes_total_actions(self, memory):
        """Includes total actions count."""
        memory.record_iteration(
            {"activity": "Main", "hash_screen": "hash1"},
            [{"action_type": "CLICK"}, {"action_type": "TYPE"}],
        )

        context = memory.get_current_screen_context()

        assert context["total_actions_tried"] == 2


class TestFormatForTemplate:
    """Test format_for_template method."""

    @pytest.fixture
    def memory(self):
        with patch("rv_agent.memory.short_term.LoggingManager") as mock_logging:
            with patch("rv_agent.memory.short_term.ErrorHandler") as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = (
                    MagicMock()
                )
                mock_error.get_instance.return_value = MagicMock()
                return ShortTermMemory(max_iterations=5)

    def test_new_screen_template(self, memory):
        """Empty memory returns new screen message."""
        result = memory.format_for_template()

        assert "new screen" in result

    def test_includes_recent_actions(self, memory):
        """Includes recent actions in template."""
        memory.record_iteration(
            {"activity": "Main", "hash_screen": "hash1"},
            [{"element_id": "btn_submit", "coordinates": [100, 200]}],
        )

        result = memory.format_for_template()

        assert "Recent actions" in result
        assert "btn_submit" in result

    def test_includes_strategy_warning_low_success(self, memory):
        """Includes warning for low success rate."""
        for i in range(3):
            memory.record_iteration(
                {"activity": "Main", "hash_screen": f"hash{i}"},
                [{"action_type": "CLICK"}],
            )
            memory.record_execution_results([{"success": False}])

        result = memory.format_for_template()

        assert "⚠️" in result
        assert "Try different" in result

    def test_includes_strategy_success_message(self, memory):
        """Includes success message for high success rate."""
        for i in range(5):
            memory.record_iteration(
                {"activity": "Main", "hash_screen": f"hash{i}"},
                [{"action_type": "CLICK"}],
            )
            memory.record_execution_results([{"success": True}])

        result = memory.format_for_template()

        assert "✅" in result
        assert "Continue exploring" in result


class TestClear:
    """Test clear method."""

    @pytest.fixture
    def memory(self):
        with patch("rv_agent.memory.short_term.LoggingManager") as mock_logging:
            with patch("rv_agent.memory.short_term.ErrorHandler") as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = (
                    MagicMock()
                )
                mock_error.get_instance.return_value = MagicMock()
                return ShortTermMemory(max_iterations=5)

    def test_clears_all_iterations(self, memory):
        """Clear removes all iterations."""
        memory.record_iteration(
            {"activity": "Main", "hash_screen": "hash1"}, [{"action_type": "CLICK"}]
        )

        memory.clear()

        assert len(memory.iterations) == 0


class TestGetStatistics:
    """Test get_statistics method."""

    @pytest.fixture
    def memory(self):
        with patch("rv_agent.memory.short_term.LoggingManager") as mock_logging:
            with patch("rv_agent.memory.short_term.ErrorHandler") as mock_error:
                mock_logging.get_instance.return_value.get_logger.return_value = (
                    MagicMock()
                )
                mock_error.get_instance.return_value = MagicMock()
                return ShortTermMemory(max_iterations=5)

    def test_empty_statistics(self, memory):
        """Empty memory returns minimal stats."""
        stats = memory.get_statistics()

        assert stats["iteration_count"] == 0
        assert stats["memory_status"] == "empty"

    def test_comprehensive_statistics(self, memory):
        """Returns comprehensive statistics with data."""
        memory.record_iteration(
            {"activity": "MainActivity", "hash_screen": "hash1"},
            [{"action_type": "CLICK"}, {"action_type": "TYPE"}],
        )
        memory.record_execution_results([{"success": True}, {"success": False}])

        stats = memory.get_statistics()

        assert stats["iteration_count"] == 1
        assert stats["current_activity"] == "MainActivity"
        assert stats["total_actions_generated"] == 2
        assert stats["total_execution_results"] == 2
        assert stats["average_success_rate"] == 0.5
        assert "1/5" in stats["memory_utilization"]
        assert stats["latest_iteration"] is not None
        assert stats["latest_iteration"]["action_count"] == 2

    def test_multiple_iterations_statistics(self, memory):
        """Calculates stats across multiple iterations."""
        for i in range(3):
            memory.record_iteration(
                {"activity": "Main", "hash_screen": f"hash{i}"},
                [{"action_type": "CLICK"}],
            )
            memory.record_execution_results([{"success": i % 2 == 0}])

        stats = memory.get_statistics()

        assert stats["iteration_count"] == 3
        assert stats["total_actions_generated"] == 3
        assert stats["total_execution_results"] == 3

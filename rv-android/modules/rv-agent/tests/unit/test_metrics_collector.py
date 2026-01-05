"""
Unit tests for MetricsCollector and related dataclasses.
"""

import pytest
import time
from unittest.mock import patch

from rv_agent.validation.metrics_collector import (
    IterationMetrics,
    ValidationMetrics,
    MetricsCollector
)


# =============================================================================
# IterationMetrics Dataclass Tests
# =============================================================================

class TestIterationMetrics:
    """Tests for IterationMetrics dataclass."""

    def test_creation_with_required_fields(self):
        """Test creating IterationMetrics with required fields."""
        metrics = IterationMetrics(
            iteration=1,
            timestamp=1000.0,
            action_type="CLICK",
            valid_action=True,
            screen_hash="abc123",
            activity="MainActivity",
            element_count=10,
            element_types={"Button": 3, "TextView": 7}
        )

        assert metrics.iteration == 1
        assert metrics.action_type == "CLICK"
        assert metrics.valid_action is True
        assert metrics.element_count == 10

    def test_creation_with_optional_fields(self):
        """Test creating IterationMetrics with all optional fields."""
        metrics = IterationMetrics(
            iteration=1,
            timestamp=1000.0,
            action_type="CLICK",
            valid_action=True,
            screen_hash="abc123",
            activity="MainActivity",
            element_count=10,
            element_types={"Button": 3},
            message_count=5,
            tokens_input=500,
            tokens_output=100,
            llm_time_ms=150.0
        )

        assert metrics.message_count == 5
        assert metrics.tokens_input == 500
        assert metrics.tokens_output == 100
        assert metrics.llm_time_ms == 150.0

    def test_default_optional_values(self):
        """Test that optional fields have correct defaults."""
        metrics = IterationMetrics(
            iteration=1,
            timestamp=1000.0,
            action_type="CLICK",
            valid_action=True,
            screen_hash="abc123",
            activity="MainActivity",
            element_count=10,
            element_types={}
        )

        assert metrics.message_count == 0
        assert metrics.tokens_input == 0
        assert metrics.tokens_output == 0
        assert metrics.llm_time_ms == 0.0


# =============================================================================
# ValidationMetrics Dataclass Tests
# =============================================================================

class TestValidationMetrics:
    """Tests for ValidationMetrics dataclass."""

    def test_creation_basic(self):
        """Test creating ValidationMetrics with basic fields."""
        metrics = ValidationMetrics(
            app_name="test.apk",
            start_time=1000.0
        )

        assert metrics.app_name == "test.apk"
        assert metrics.start_time == 1000.0
        assert metrics.end_time == 0.0
        assert metrics.total_iterations == 0

    def test_default_collections(self):
        """Test that collections are properly initialized."""
        metrics = ValidationMetrics(
            app_name="test.apk",
            start_time=1000.0
        )

        assert metrics.actions_by_type == {}
        assert metrics.element_types_seen == set()
        assert metrics.unique_screens == set()
        assert metrics.iterations == []

    def test_to_dict_basic(self):
        """Test to_dict method with basic data."""
        metrics = ValidationMetrics(
            app_name="test.apk",
            start_time=1000.0,
            end_time=1100.0,
            total_iterations=10
        )

        result = metrics.to_dict()

        assert result['app_name'] == "test.apk"
        assert result['execution_time_s'] == 100.0
        assert result['total_iterations'] == 10

    def test_to_dict_actions(self):
        """Test to_dict actions section."""
        metrics = ValidationMetrics(
            app_name="test.apk",
            start_time=1000.0,
            valid_actions=8,
            invalid_actions=2,
            actions_by_type={"CLICK": 7, "BACK": 3}
        )

        result = metrics.to_dict()

        assert result['actions']['valid'] == 8
        assert result['actions']['invalid'] == 2
        assert result['actions']['valid_rate'] == 0.8
        assert result['actions']['by_type'] == {"CLICK": 7, "BACK": 3}

    def test_to_dict_valid_rate_zero_actions(self):
        """Test valid_rate calculation with zero actions."""
        metrics = ValidationMetrics(
            app_name="test.apk",
            start_time=1000.0,
            valid_actions=0,
            invalid_actions=0
        )

        result = metrics.to_dict()

        assert result['actions']['valid_rate'] == 0.0

    def test_to_dict_element_coverage(self):
        """Test to_dict element_coverage section."""
        metrics = ValidationMetrics(
            app_name="test.apk",
            start_time=1000.0
        )
        metrics.element_types_seen.add("Button")
        metrics.element_types_seen.add("TextView")
        metrics.element_type_counts = {"Button": 5, "TextView": 10}
        metrics.interactive_elements_total = 15

        result = metrics.to_dict()

        assert set(result['element_coverage']['types_seen']) == {"Button", "TextView"}
        assert result['element_coverage']['type_counts'] == {"Button": 5, "TextView": 10}
        assert result['element_coverage']['interactive_elements'] == 15

    def test_to_dict_exploration(self):
        """Test to_dict exploration section."""
        metrics = ValidationMetrics(
            app_name="test.apk",
            start_time=1000.0
        )
        metrics.unique_screens.add("screen1")
        metrics.unique_screens.add("screen2")
        metrics.screen_visits = {"screen1": 3, "screen2": 2}
        metrics.activities_seen.add("MainActivity")
        metrics.activities_seen.add("SettingsActivity")

        result = metrics.to_dict()

        assert result['exploration']['unique_screens'] == 2
        assert result['exploration']['screen_visits'] == {"screen1": 3, "screen2": 2}
        assert set(result['exploration']['activities']) == {"MainActivity", "SettingsActivity"}
        # revisit_rate = (3 + 2 - 2) / (3 + 2) = 3/5 = 0.6
        assert result['exploration']['revisit_rate'] == pytest.approx(0.6)

    def test_to_dict_revisit_rate_zero_visits(self):
        """Test revisit_rate with zero screen visits."""
        metrics = ValidationMetrics(
            app_name="test.apk",
            start_time=1000.0
        )

        result = metrics.to_dict()

        assert result['exploration']['revisit_rate'] == 0.0

    def test_to_dict_memory_graph(self):
        """Test to_dict memory_graph section."""
        metrics = ValidationMetrics(
            app_name="test.apk",
            start_time=1000.0,
            graph_states=5,
            graph_transitions=8,
            long_term_patterns=3,
            short_term_iterations=10
        )

        result = metrics.to_dict()

        assert result['memory_graph']['graph_states'] == 5
        assert result['memory_graph']['graph_transitions'] == 8
        assert result['memory_graph']['long_term_patterns'] == 3
        assert result['memory_graph']['short_term_iterations'] == 10

    def test_to_dict_llm(self):
        """Test to_dict llm section."""
        metrics = ValidationMetrics(
            app_name="test.apk",
            start_time=1000.0,
            total_iterations=10,
            total_tokens=5000,
            total_input_tokens=4000,
            total_output_tokens=1000,
            total_llm_time_ms=3000.0,
            avg_tokens_per_iteration=500.0,
            max_message_count=15
        )

        result = metrics.to_dict()

        assert result['llm']['total_tokens'] == 5000
        assert result['llm']['input_tokens'] == 4000
        assert result['llm']['output_tokens'] == 1000
        assert result['llm']['avg_tokens_per_iteration'] == 500.0
        assert result['llm']['max_message_count'] == 15
        assert result['llm']['total_time_ms'] == 3000.0
        assert result['llm']['avg_time_per_iteration_ms'] == 300.0

    def test_to_dict_llm_zero_iterations(self):
        """Test llm avg_time with zero iterations."""
        metrics = ValidationMetrics(
            app_name="test.apk",
            start_time=1000.0,
            total_iterations=0
        )

        result = metrics.to_dict()

        assert result['llm']['avg_time_per_iteration_ms'] == 0.0


# =============================================================================
# MetricsCollector Tests
# =============================================================================

class TestMetricsCollectorInit:
    """Tests for MetricsCollector initialization."""

    def test_init_creates_metrics(self):
        """Test initialization creates ValidationMetrics."""
        collector = MetricsCollector("test.apk")

        assert collector.metrics.app_name == "test.apk"
        assert collector.metrics.start_time > 0

    def test_init_sets_start_time(self):
        """Test that start_time is set to current time."""
        before = time.time()
        collector = MetricsCollector("test.apk")
        after = time.time()

        assert before <= collector.metrics.start_time <= after


class TestMetricsCollectorRecordIteration:
    """Tests for MetricsCollector.record_iteration()."""

    def test_record_basic_iteration(self):
        """Test recording a basic iteration."""
        collector = MetricsCollector("test.apk")

        collector.record_iteration(
            iteration=1,
            action_type="CLICK",
            valid_action=True,
            screen_hash="abc123",
            activity="MainActivity",
            element_count=10,
            element_types={"Button": 3, "TextView": 7}
        )

        assert collector.metrics.total_iterations == 1
        assert len(collector.metrics.iterations) == 1
        assert collector.metrics.valid_actions == 1

    def test_record_multiple_iterations(self):
        """Test recording multiple iterations."""
        collector = MetricsCollector("test.apk")

        for i in range(5):
            collector.record_iteration(
                iteration=i + 1,
                action_type="CLICK",
                valid_action=True,
                screen_hash=f"hash{i}",
                activity="MainActivity",
                element_count=10,
                element_types={}
            )

        assert collector.metrics.total_iterations == 5
        assert len(collector.metrics.iterations) == 5

    def test_record_updates_action_counts(self):
        """Test that action counts are updated."""
        collector = MetricsCollector("test.apk")

        collector.record_iteration(
            iteration=1, action_type="CLICK", valid_action=True,
            screen_hash="h1", activity="A", element_count=0, element_types={}
        )
        collector.record_iteration(
            iteration=2, action_type="CLICK", valid_action=False,
            screen_hash="h2", activity="A", element_count=0, element_types={}
        )
        collector.record_iteration(
            iteration=3, action_type="BACK", valid_action=True,
            screen_hash="h3", activity="A", element_count=0, element_types={}
        )

        assert collector.metrics.valid_actions == 2
        assert collector.metrics.invalid_actions == 1
        assert collector.metrics.actions_by_type["CLICK"] == 2
        assert collector.metrics.actions_by_type["BACK"] == 1

    def test_record_updates_element_coverage(self):
        """Test that element coverage is updated."""
        collector = MetricsCollector("test.apk")

        collector.record_iteration(
            iteration=1, action_type="CLICK", valid_action=True,
            screen_hash="h1", activity="A", element_count=10,
            element_types={"Button": 5, "TextView": 5}
        )
        collector.record_iteration(
            iteration=2, action_type="CLICK", valid_action=True,
            screen_hash="h2", activity="A", element_count=8,
            element_types={"Button": 3, "EditText": 5}
        )

        assert collector.metrics.element_types_seen == {"Button", "TextView", "EditText"}
        assert collector.metrics.element_type_counts["Button"] == 8
        assert collector.metrics.element_type_counts["TextView"] == 5
        assert collector.metrics.element_type_counts["EditText"] == 5

    def test_record_updates_exploration_metrics(self):
        """Test that exploration metrics are updated."""
        collector = MetricsCollector("test.apk")

        collector.record_iteration(
            iteration=1, action_type="CLICK", valid_action=True,
            screen_hash="screen1", activity="MainActivity",
            element_count=0, element_types={}
        )
        collector.record_iteration(
            iteration=2, action_type="CLICK", valid_action=True,
            screen_hash="screen2", activity="SettingsActivity",
            element_count=0, element_types={}
        )
        collector.record_iteration(
            iteration=3, action_type="BACK", valid_action=True,
            screen_hash="screen1", activity="MainActivity",  # Revisit
            element_count=0, element_types={}
        )

        assert collector.metrics.unique_screens == {"screen1", "screen2"}
        assert collector.metrics.screen_visits["screen1"] == 2
        assert collector.metrics.screen_visits["screen2"] == 1
        assert collector.metrics.activities_seen == {"MainActivity", "SettingsActivity"}

    def test_record_updates_llm_metrics(self):
        """Test that LLM metrics are updated."""
        collector = MetricsCollector("test.apk")

        collector.record_iteration(
            iteration=1, action_type="CLICK", valid_action=True,
            screen_hash="h1", activity="A", element_count=0, element_types={},
            message_count=5, tokens_input=400, tokens_output=100, llm_time_ms=150.0
        )
        collector.record_iteration(
            iteration=2, action_type="CLICK", valid_action=True,
            screen_hash="h2", activity="A", element_count=0, element_types={},
            message_count=10, tokens_input=500, tokens_output=150, llm_time_ms=200.0
        )

        assert collector.metrics.total_input_tokens == 900
        assert collector.metrics.total_output_tokens == 250
        assert collector.metrics.total_tokens == 1150
        assert collector.metrics.total_llm_time_ms == 350.0
        assert collector.metrics.max_message_count == 10
        assert collector.metrics.avg_tokens_per_iteration == 575.0


class TestMetricsCollectorRecordMemoryStats:
    """Tests for MetricsCollector.record_memory_stats()."""

    def test_record_memory_stats(self):
        """Test recording memory statistics."""
        collector = MetricsCollector("test.apk")

        collector.record_memory_stats(
            graph_states=10,
            graph_transitions=15,
            long_term_patterns=5,
            short_term_iterations=25
        )

        assert collector.metrics.graph_states == 10
        assert collector.metrics.graph_transitions == 15
        assert collector.metrics.long_term_patterns == 5
        assert collector.metrics.short_term_iterations == 25

    def test_record_memory_stats_overwrites(self):
        """Test that memory stats can be updated."""
        collector = MetricsCollector("test.apk")

        collector.record_memory_stats(5, 8, 3, 10)
        collector.record_memory_stats(10, 15, 5, 20)

        assert collector.metrics.graph_states == 10
        assert collector.metrics.graph_transitions == 15


class TestMetricsCollectorFinalize:
    """Tests for MetricsCollector.finalize()."""

    def test_finalize_sets_end_time(self):
        """Test that finalize sets end_time."""
        collector = MetricsCollector("test.apk")

        before = time.time()
        collector.finalize()
        after = time.time()

        assert before <= collector.metrics.end_time <= after

    def test_finalize_can_be_called_multiple_times(self):
        """Test that finalize can be called multiple times."""
        collector = MetricsCollector("test.apk")

        collector.finalize()
        first_end = collector.metrics.end_time

        time.sleep(0.01)
        collector.finalize()

        assert collector.metrics.end_time > first_end


class TestMetricsCollectorGetMetrics:
    """Tests for MetricsCollector.get_metrics()."""

    def test_get_metrics_returns_metrics(self):
        """Test that get_metrics returns the metrics object."""
        collector = MetricsCollector("test.apk")

        metrics = collector.get_metrics()

        assert metrics is collector.metrics
        assert metrics.app_name == "test.apk"


class TestMetricsCollectorGetActionDistribution:
    """Tests for MetricsCollector.get_action_distribution()."""

    def test_get_action_distribution(self):
        """Test getting action distribution as percentages."""
        collector = MetricsCollector("test.apk")

        collector.record_iteration(
            iteration=1, action_type="CLICK", valid_action=True,
            screen_hash="h", activity="A", element_count=0, element_types={}
        )
        collector.record_iteration(
            iteration=2, action_type="CLICK", valid_action=True,
            screen_hash="h", activity="A", element_count=0, element_types={}
        )
        collector.record_iteration(
            iteration=3, action_type="BACK", valid_action=True,
            screen_hash="h", activity="A", element_count=0, element_types={}
        )
        collector.record_iteration(
            iteration=4, action_type="HOME", valid_action=True,
            screen_hash="h", activity="A", element_count=0, element_types={}
        )

        distribution = collector.get_action_distribution()

        assert distribution["CLICK"] == pytest.approx(50.0)
        assert distribution["BACK"] == pytest.approx(25.0)
        assert distribution["HOME"] == pytest.approx(25.0)

    def test_get_action_distribution_empty(self):
        """Test getting distribution with no actions."""
        collector = MetricsCollector("test.apk")

        distribution = collector.get_action_distribution()

        assert distribution == {}


class TestMetricsCollectorGetElementCoverageRate:
    """Tests for MetricsCollector.get_element_coverage_rate()."""

    def test_get_element_coverage_rate(self):
        """Test getting element coverage rate."""
        collector = MetricsCollector("test.apk")
        collector.metrics.element_types_seen = {"Button", "TextView", "EditText"}
        collector.metrics.element_type_counts = {"Button": 5, "TextView": 10, "EditText": 3}
        collector.metrics.interactive_elements_total = 18

        rate = collector.get_element_coverage_rate()

        # 3 types seen / 3 types total = 100%
        assert rate == 100.0

    def test_get_element_coverage_rate_zero_total(self):
        """Test coverage rate with zero interactive elements."""
        collector = MetricsCollector("test.apk")
        collector.metrics.interactive_elements_total = 0

        rate = collector.get_element_coverage_rate()

        assert rate == 0.0


class TestMetricsCollectorGetContextGrowthRate:
    """Tests for MetricsCollector.get_context_growth_rate()."""

    def test_get_context_growth_rate(self):
        """Test getting context growth rate."""
        collector = MetricsCollector("test.apk")

        for i, msg_count in enumerate([1, 3, 5, 7, 10]):
            collector.record_iteration(
                iteration=i + 1, action_type="CLICK", valid_action=True,
                screen_hash="h", activity="A", element_count=0, element_types={},
                message_count=msg_count
            )

        growth = collector.get_context_growth_rate()

        assert growth == [1, 3, 5, 7, 10]

    def test_get_context_growth_rate_empty(self):
        """Test context growth with no iterations."""
        collector = MetricsCollector("test.apk")

        growth = collector.get_context_growth_rate()

        assert growth == []


class TestMetricsCollectorGetTokenUsagePerIteration:
    """Tests for MetricsCollector.get_token_usage_per_iteration()."""

    def test_get_token_usage_per_iteration(self):
        """Test getting token usage per iteration."""
        collector = MetricsCollector("test.apk")

        collector.record_iteration(
            iteration=1, action_type="CLICK", valid_action=True,
            screen_hash="h", activity="A", element_count=0, element_types={},
            tokens_input=400, tokens_output=100
        )
        collector.record_iteration(
            iteration=2, action_type="CLICK", valid_action=True,
            screen_hash="h", activity="A", element_count=0, element_types={},
            tokens_input=500, tokens_output=150
        )

        usage = collector.get_token_usage_per_iteration()

        assert usage == [500, 650]

    def test_get_token_usage_empty(self):
        """Test token usage with no iterations."""
        collector = MetricsCollector("test.apk")

        usage = collector.get_token_usage_per_iteration()

        assert usage == []

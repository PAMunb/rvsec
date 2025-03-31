import time
import pytest
from unittest.mock import Mock, patch

from rvandroid.util.performance_monitor import PerformanceMonitor, Metric, TimingMetric


class TestPerformanceMonitor:
    """
    Comprehensive unit tests for the PerformanceMonitor class.

    ### Test Strategy:
    - Validate singleton pattern implementation
    - Test metric recording and management
    - Verify context manager and measurement capabilities
    - Ensure subscriber and notification mechanisms work correctly
    """

    @pytest.fixture
    def performance_monitor(self):
        """
        Provide a fresh PerformanceMonitor instance for each test.
        Resets the singleton to ensure clean state.
        """
        # Reset the singleton instance before each test
        PerformanceMonitor._instance = None
        return PerformanceMonitor.get_instance()

    def test_singleton_pattern(self, performance_monitor):
        """
        Validate the singleton pattern implementation.

        Ensures that:
        - Multiple calls return the same instance
        - Instance is consistently created
        """
        second_instance = PerformanceMonitor.get_instance()
        assert performance_monitor is second_instance

    def test_record_metric(self, performance_monitor):
        """
        Test recording a general metric.

        Validates that:
        - Metric is correctly added to metrics list
        - Metric properties are set correctly
        """
        performance_monitor.record_metric(
            name="test_metric",
            value=42.5,
            unit="ms",
            context={"test": "context"}
        )

        # Verify last recorded metric
        assert len(performance_monitor.metrics) > 0
        last_metric = performance_monitor.metrics[-1]

        assert last_metric.name == "test_metric"
        assert last_metric.value == 42.5
        assert last_metric.unit == "ms"
        assert last_metric.context == {"test": "context"}
        assert last_metric.timestamp is not None

    def test_measure_time_context_manager(self, performance_monitor):
        """
        Test the time measurement context manager.

        Validates that:
        - Context manager measures execution time correctly
        - Metric is added with correct properties
        - Execution works with and without context
        """
        with performance_monitor.measure_time("test_operation") as metric:
            time.sleep(0.1)  # Simulate some work

        # Verify metric was recorded
        assert len(performance_monitor.metrics) > 0
        last_metric = performance_monitor.metrics[-1]

        assert isinstance(last_metric, TimingMetric)
        assert last_metric.name == "test_operation"
        assert last_metric.unit == "s"
        assert last_metric.value >= 0.1
        assert last_metric.start_time is not None
        assert last_metric.end_time is not None

    def test_measure_time_with_context(self, performance_monitor):
        """
        Test time measurement with additional context.

        Validates that:
        - Context is correctly passed and recorded
        - Metric includes additional context information
        """
        with performance_monitor.measure_time("contextual_op", {"component": "test"}):
            time.sleep(0.05)

        last_metric = performance_monitor.metrics[-1]
        assert last_metric.context == {"component": "test"}

    def test_get_metrics_by_name(self, performance_monitor):
        """
        Test retrieving metrics by name.

        Validates that:
        - Metrics can be filtered by name
        - Correct number of metrics are returned
        """
        # Record multiple metrics
        performance_monitor.record_metric("metric1", 10, "unit")
        performance_monitor.record_metric("metric1", 20, "unit")
        performance_monitor.record_metric("metric2", 30, "unit")

        # Retrieve metrics
        metric1_list = performance_monitor.get_metrics_by_name("metric1")
        metric2_list = performance_monitor.get_metrics_by_name("metric2")

        assert len(metric1_list) == 2
        assert len(metric2_list) == 1
        assert all(m.name == "metric1" for m in metric1_list)
        assert all(m.name == "metric2" for m in metric2_list)

    def test_get_metrics_stats(self, performance_monitor):
        """
        Test retrieving statistical information about metrics.

        Validates that:
        - Correct statistical calculations are performed
        - All statistical properties are computed
        """
        # Record multiple metrics for statistical analysis
        performance_monitor.record_metric("stat_metric", 10, "unit")
        performance_monitor.record_metric("stat_metric", 20, "unit")
        performance_monitor.record_metric("stat_metric", 30, "unit")

        stats = performance_monitor.get_metrics_stats("stat_metric")

        assert stats["count"] == 3
        assert stats["min"] == 10
        assert stats["max"] == 30
        assert stats["avg"] == 20
        assert stats["median"] == 20

    def test_get_metrics_stats_empty(self, performance_monitor):
        """
        Test metrics statistics for non-existent metric.

        Validates that:
        - Returns default statistics when no metrics exist
        - All statistical properties are None or zero
        """
        stats = performance_monitor.get_metrics_stats("non_existent_metric")

        assert stats["count"] == 0
        assert stats["min"] is None
        assert stats["max"] is None
        assert stats["avg"] is None
        assert stats["median"] is None

    def test_clear_metrics(self, performance_monitor):
        """
        Test clearing all recorded metrics.

        Validates that:
        - Metrics list is completely emptied
        - No metrics remain after clearing
        """
        # Record some metrics
        performance_monitor.record_metric("metric1", 10, "unit")
        performance_monitor.record_metric("metric2", 20, "unit")

        # Clear metrics
        performance_monitor.clear_metrics()

        # Verify
        assert len(performance_monitor.metrics) == 0

    def test_metric_subscribers(self, performance_monitor):
        """
        Test metric subscription mechanism.

        Validates that:
        - Subscribers are called when matching metrics are recorded
        - Global subscribers work for all metrics
        """
        # Mock subscribers
        specific_mock = Mock()
        global_mock = Mock()

        # Subscribe to specific and global metrics
        performance_monitor.subscribe("specific_metric", specific_mock)
        performance_monitor.subscribe("*", global_mock)

        # Record a metric
        performance_monitor.record_metric("specific_metric", 42, "unit")

        # Verify subscribers were called
        specific_mock.assert_called_once()
        global_mock.assert_called_once()

        # Verify the metric passed to subscribers
        specific_call_args = specific_mock.call_args[0][0]
        global_call_args = global_mock.call_args[0][0]

        assert isinstance(specific_call_args, Metric)
        assert specific_call_args.name == "specific_metric"
        assert specific_call_args.value == 42

    def test_track_action_execution(self, performance_monitor):
        """
        Test tracking action execution time.

        Validates that:
        - Action tracking creates a timing metric
        - Correct context is maintained
        """
        with performance_monitor.track_action_execution("click", action_id=1):
            time.sleep(0.05)  # Simulate action execution

        # Find the last metric
        action_metrics = [
            m for m in performance_monitor.metrics
            if m.name.startswith("action_execution:")
        ]

        assert len(action_metrics) > 0
        last_metric = action_metrics[-1]

        assert last_metric.name == "action_execution:click"
        assert last_metric.context == {
            "action_type": "click",
            "action_id": 1
        }
        assert last_metric.value >= 0.05
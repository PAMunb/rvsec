# rvandroid/util/performance_monitor.py
import statistics
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable

from rvandroid.util.logging_manager import LoggingManager


@dataclass
class Metric:
    """
    Represents a single measured metric.
    """
    name: str
    value: float
    unit: str
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimingMetric(Metric):
    """
    A metric specifically for timing measurements.
    """
    start_time: float = 0.0
    end_time: float = 0.0


class PerformanceMonitor:
    """
    Central system for tracking performance metrics in rv-android.
    Handles storing, aggregating, and reporting metrics.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = PerformanceMonitor()
            return cls._instance

    def __init__(self):
        """Initialize the performance monitor with standardized logging."""
        # Set up logging using LoggingManager
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "util.performance_monitor",
            {LoggingManager.CONTEXT_COMPONENT: "PerformanceMonitor"}
        )

        self.metrics: List[Metric] = []
        self.subscribers: Dict[str, List[Callable[[Metric], None]]] = {}

        # Set up default subscribers
        self._setup_default_subscribers()

    def _setup_default_subscribers(self):
        """Set up default subscribers for metrics."""

        # Log all metrics at debug level
        def log_metric(metric: Metric):
            with self.logger.with_context(
                    metric_name=metric.name,
                    metric_value=metric.value,
                    metric_unit=metric.unit,
                    **metric.context
            ):
                self.logger.debug(f"Metric: {metric.name}={metric.value}{metric.unit}")

        self.subscribe("*", log_metric)

    def record_metric(self, name: str, value: float, unit: str = "", context: Optional[Dict[str, Any]] = None):
        """
        Record a general metric.

        Args:
            name: Name of the metric
            value: Value of the metric
            unit: Unit of the metric (optional)
            context: Additional context for the metric (optional)
        """
        metric = Metric(
            name=name,
            value=value,
            unit=unit,
            timestamp=time.time(),
            context=context or {}
        )

        self.metrics.append(metric)
        self._notify_subscribers(metric)

    def record_timing(self, name: str, duration: float, context: Optional[Dict[str, Any]] = None):
        """
        Record a timing metric.

        Args:
            name: Name of the timing metric
            duration: Duration in seconds
            context: Additional context for the metric (optional)
        """
        metric = TimingMetric(
            name=name,
            value=duration,
            unit="s",
            timestamp=time.time(),
            context=context or {},
            start_time=time.time() - duration,
            end_time=time.time()
        )

        self.metrics.append(metric)
        self._notify_subscribers(metric)

    @contextmanager
    def measure_time(self, name: str, context: Optional[Dict[str, Any]] = None):
        """
        Context manager for measuring the execution time of a block of code.

        Args:
            name: Name of the timing metric
            context: Additional context for the metric (optional)

        Yields:
            Nothing, just executes the block and measures time
        """
        start_time = time.time()
        with self.logger.with_context(operation=name, **({} if context is None else context)):
            try:
                self.logger.debug(f"Starting timed operation: {name}")
                yield
            finally:
                end_time = time.time()
                duration = end_time - start_time

                metric = TimingMetric(
                    name=name,
                    value=duration,
                    unit="s",
                    timestamp=time.time(),
                    context=context or {},
                    start_time=start_time,
                    end_time=end_time
                )

                self.metrics.append(metric)
                self._notify_subscribers(metric)

                self.logger.debug(f"Completed timed operation: {name} in {duration:.2f}s")

    def get_metrics_by_name(self, name: str) -> List[Metric]:
        """
        Get all metrics with the given name.

        Args:
            name: Name of metrics to retrieve

        Returns:
            List of matching metrics
        """
        return [m for m in self.metrics if m.name == name]

    def get_metrics_stats(self, name: str):
        """
        Get statistical information about metrics with the given name.

        Args:
            name: Name of metrics to analyze

        Returns:
            Dictionary with statistics (count, min, max, avg, median)
        """
        metrics = self.get_metrics_by_name(name)
        if not metrics:
            return {
                "count": 0,
                "min": None,
                "max": None,
                "avg": None,
                "median": None
            }

        values = [m.value for m in metrics]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "median": statistics.median(values) if values else None
        }

    def clear_metrics(self):
        """Clear all stored metrics."""
        self.metrics = []

    def subscribe(self, metric_name: str, callback: Callable[[Metric], None]):
        """
        Subscribe to metrics with the given name.
        Use "*" as the name to subscribe to all metrics.

        Args:
            metric_name: Name of metrics to subscribe to, or "*" for all
            callback: Function to call when a matching metric is recorded
        """
        if metric_name not in self.subscribers:
            self.subscribers[metric_name] = []

        self.subscribers[metric_name].append(callback)

    def _notify_subscribers(self, metric: Metric):
        # TODO usar o event bus para isso
        """
        Notify subscribers about a new metric.

        Args:
            metric: The metric that was recorded
        """
        # Call specific subscribers
        for callback in self.subscribers.get(metric.name, []):
            try:
                callback(metric)
            except Exception as e:
                self.logger.error(LoggingManager.LOG_ERROR.format(
                    operation="metric subscriber",
                    error=str(e)
                ))

        # Call global subscribers
        for callback in self.subscribers.get("*", []):
            try:
                callback(metric)
            except Exception as e:
                self.logger.error(LoggingManager.LOG_ERROR.format(
                    operation="global metric subscriber",
                    error=str(e)
                ))

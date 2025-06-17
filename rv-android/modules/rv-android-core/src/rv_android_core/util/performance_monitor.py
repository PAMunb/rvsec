"""
Performance monitoring system for runtime verification operations.

This module provides comprehensive performance tracking and metric collection
for monitoring system resource usage and operation timing during experiment execution.
"""

import statistics
import threading
import time
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Callable
from pydantic import Field

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


@validated_model(['name', 'value', 'unit', 'timestamp'])
class Metric(BaseValidatedModel):
    """
    Validated data model for performance metric measurements.
    
    This model provides structured representation of performance measurements
    with validation and type safety for runtime verification monitoring.
    
    ### Architectural Role:
    - Provides standardized structure for performance data collection
    - Enables type-safe metric aggregation and analysis
    - Supports contextual information for detailed performance tracking
    - Facilitates metric comparison and trend analysis across experiments
    
    ### Integration Points:
    - Created by PerformanceMonitor during operation execution
    - Consumed by diagnostic tools for performance analysis
    - Used by reporting systems for performance visualization
    - Integrated with logging systems for performance debugging
    """
    
    name: str = Field(
        description="Metric name for identification and categorization"
    )
    value: float = Field(
        description="Numeric value of the measured metric"
    )
    unit: str = Field(
        description="Unit of measurement for the metric value"
    )
    timestamp: float = Field(
        description="Unix timestamp when the metric was recorded"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional contextual information for metric analysis"
    )


@validated_model(['name', 'value', 'unit', 'timestamp'])
class TimingMetric(Metric):
    """
    Validated data model for timing-specific performance measurements.
    
    This model extends the base Metric class with timing-specific fields
    for detailed temporal analysis of operation execution.
    
    ### Architectural Role:
    - Provides precise timing data for operation duration analysis
    - Enables temporal correlation between operation phases
    - Supports performance bottleneck identification and optimization
    - Facilitates timing trend analysis across multiple executions
    
    ### Critical Timing Data:
    The start_time and end_time fields provide precise timing boundaries
    for operations, enabling detailed performance analysis and optimization.
    """
    
    start_time: float = Field(
        default=0.0,
        description="Unix timestamp when the timed operation started"
    )
    end_time: float = Field(
        default=0.0,
        description="Unix timestamp when the timed operation completed"
    )


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
            {CONTEXT_COMPONENT: "PerformanceMonitor"}
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
        with self.logger.with_context(phase=name, **({} if context is None else context)):
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
                self.logger.error(LOG_ERROR.format(
                    phase="metric subscriber",
                    error=str(e)
                ))

        # Call global subscribers
        for callback in self.subscribers.get("*", []):
            try:
                callback(metric)
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    phase="global metric subscriber",
                    error=str(e)
                ))

    def track_action_execution(self, action_type: str, action_id: Optional[int] = None):
        """
        Track the execution of a specific action.

        Args:
            action_type: Type of action being executed
            action_id: Optional ID of the action

        Returns:
            Context manager for duration tracking
        """
        context = {
            "action_type": action_type,
            "action_id": action_id
        }
        return self.measure_time(f"action_execution:{action_type}", context)

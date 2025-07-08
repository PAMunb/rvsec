# rv_platform/components/performance_processor.py
"""
Performance metrics processor component for RV-Platform.

This component processes performance metrics collected during experiment execution
and generates CSV files for performance analysis and research purposes.
"""

import csv
import os
from datetime import datetime
from typing import Dict, Any, List

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_START,
    LOG_COMPLETE
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance.performance_monitor import PerformanceMonitor


class PerformanceProcessorComponent:
    """
    Performance metrics processor component for generating performance CSV files.
    
    This component extracts performance metrics from the PerformanceMonitor
    and generates standardized CSV files for performance analysis. It handles
    both enabled and disabled performance monitoring scenarios gracefully.
    
    ### Architectural Role:
    - Processes performance metrics collected during task execution
    - Generates standardized performance.csv files for analysis
    - Handles disabled performance monitoring scenarios gracefully
    - Provides performance insights for experiment optimization
    
    ### Key Capabilities:
    - Extract timing metrics from PerformanceMonitor
    - Generate performance CSV with task-level aggregation
    - Handle missing performance data gracefully
    - Support both detailed and summary performance reporting
    
    ### Integration Points:
    - Uses PerformanceMonitor for metric collection
    - Integrates with ErrorHandler for error processing
    - Uses LoggingManager for consistent logging
    - Called by ResultProcessorComponent for complete result generation
    """

    def __init__(self, tasks: List[Any], results_dir: str):
        """
        Initialize the performance processor component.

        Args:
            tasks: List of completed tasks to process
            results_dir: Directory for storing generated performance files
        """
        self.tasks = tasks
        self.results_dir = results_dir
        self.error_handler = ErrorHandler.get_instance()

        # Initialize logging with component context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'rv_platform.componentss.performance_processor',
            {CONTEXT_COMPONENT: 'PerformanceProcessorComponent'}
        )

        # Get performance monitor instance
        self.performance_monitor = PerformanceMonitor.get_instance()

        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)

    @ErrorHandler.handle_errors(component="PerformanceProcessorComponent", phase="initialization")
    def initialize(self, context: Dict[str, Any]) -> None:
        """
        Initialize the performance processor component.
        
        Args:
            context: Initialization context (unused for this component)
        """
        # self.logger.info(LOG_START.format(phase="performance processor initialization"))
        # No specific initialization required
        self.logger.info(LOG_COMPLETE.format(phase="performance processor initialization"))

    @ErrorHandler.handle_errors(component="PerformanceProcessorComponent", phase="performance_processing")
    def execute(self, context: Dict[str, Any]) -> None:
        """
        Execute performance metrics processing to generate CSV files.
        
        Args:
            context: Execution context (unused for this component)
        """
        with self.logger.with_context(phase="performance_processing"):
            self.logger.info(LOG_START.format(phase="performance metrics processing"))

            # Check if performance monitoring is enabled
            if self._is_performance_monitoring_enabled():
                self._generate_performance_csv_with_metrics()
            else:
                self._generate_performance_csv_basic()

            self.logger.info(LOG_COMPLETE.format(phase="performance metrics processing"))

    def cleanup(self) -> None:
        """
        Clean up resources used by the performance processor.
        """
        # No cleanup required for this component
        pass

    def _is_performance_monitoring_enabled(self) -> bool:
        """
        Check if performance monitoring is currently enabled.
        
        Returns:
            True if performance monitoring is enabled, False otherwise
        """
        try:
            # Check if performance monitor is enabled
            return self.performance_monitor._is_enabled()
        except Exception:
            # If there's any issue checking, assume disabled
            return False

    @ErrorHandler.handle_errors(component="PerformanceProcessorComponent", phase="performance_csv_with_metrics")
    def _generate_performance_csv_with_metrics(self) -> None:
        """
        Generate detailed performance CSV with collected metrics.
        """
        with self.logger.with_context(phase="performance_csv_with_metrics"):
            self.logger.info(LOG_START.format(phase="detailed performance CSV generation"))

            performance_file = os.path.join(self.results_dir, "performance.csv")

            with open(performance_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header for detailed performance metrics
                writer.writerow([
                    'apk', 'rep', 'timeout', 'tool', 'metric_name', 'metric_value',
                    'metric_unit', 'metric_timestamp', 'task_id', 'context_info'
                ])

                # Process each completed task
                for task in self.tasks:
                    self._write_task_performance_data_detailed(writer, task)

            self.logger.info(f"Detailed performance CSV generated: {performance_file}")

    @ErrorHandler.handle_errors(component="PerformanceProcessorComponent", phase="performance_csv_basic")
    def _generate_performance_csv_basic(self) -> None:
        """
        Generate basic performance CSV with task execution metrics only.
        """
        with self.logger.with_context(phase="performance_csv_basic"):
            self.logger.info(LOG_START.format(phase="basic performance CSV generation"))

            performance_file = os.path.join(self.results_dir, "performance.csv")

            with open(performance_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header for basic performance metrics
                writer.writerow([
                    'apk', 'rep', 'timeout', 'tool', 'execution_time_seconds',
                    'task_state', 'monitoring_enabled', 'timestamp'
                ])

                # Process each completed task with basic metrics
                for task in self.tasks:
                    self._write_task_performance_data_basic(writer, task)

            self.logger.info(f"Basic performance CSV generated: {performance_file}")

    def _write_task_performance_data_detailed(self, writer: csv.writer, task: Any) -> None:
        """
        Write detailed performance data for a single task to CSV.
        
        Args:
            writer: CSV writer instance
            task: Task to process for performance data
        """
        try:
            # Extract task configuration
            config = task.config
            apk_name = config.apk_name
            repetition = config.repetition
            timeout = config.timeout
            tool_name = config.tool_name
            task_id = task.id

            # Get performance metrics from the monitor
            all_metrics = self.performance_monitor.metrics

            # Filter metrics that might be related to this task
            # (this is approximate since metrics don't have direct task association)
            task_start_time = getattr(task.result, 'start_time', None)
            task_end_time = getattr(task.result, 'end_time', None)

            relevant_metrics = []
            if task_start_time and task_end_time:
                # Filter metrics by timestamp range
                start_timestamp = task_start_time.timestamp() if hasattr(task_start_time,
                                                                         'timestamp') else task_start_time
                end_timestamp = task_end_time.timestamp() if hasattr(task_end_time, 'timestamp') else task_end_time

                relevant_metrics = [
                    metric for metric in all_metrics
                    if start_timestamp <= metric.timestamp <= end_timestamp
                ]
            else:
                # If no timing info, include recent metrics (last 50)
                relevant_metrics = all_metrics[-50:] if all_metrics else []

            # Write metrics for this task
            if relevant_metrics:
                for metric in relevant_metrics:
                    context_info = "|".join([f"{k}:{v}" for k, v in metric.context.items()]) if metric.context else ""

                    writer.writerow([
                        apk_name,
                        repetition,
                        timeout,
                        tool_name,
                        metric.name,
                        metric.value,
                        metric.unit,
                        metric.timestamp,
                        task_id,
                        context_info
                    ])
            else:
                # Write a single row indicating no detailed metrics available
                writer.writerow([
                    apk_name,
                    repetition,
                    timeout,
                    tool_name,
                    "task_execution",
                    getattr(task.result, 'execution_time_seconds', 0),
                    "seconds",
                    datetime.now().timestamp(),
                    task_id,
                    "no_detailed_metrics_available"
                ])

        except Exception as e:
            self.logger.warning(f"Failed to write detailed performance data for task {task.id}: {e}")

    def _write_task_performance_data_basic(self, writer: csv.writer, task: Any) -> None:
        """
        Write basic performance data for a single task to CSV.
        
        Args:
            writer: CSV writer instance
            task: Task to process for performance data
        """
        try:
            # Extract task configuration
            config = task.config
            apk_name = config.apk_name
            repetition = config.repetition
            timeout = config.timeout
            tool_name = config.tool_name

            # Get basic execution metrics
            execution_time = getattr(task.result, 'execution_time_seconds', 0)
            task_state = getattr(task.result, 'state', 'unknown')

            writer.writerow([
                apk_name,
                repetition,
                timeout,
                tool_name,
                execution_time,
                task_state,
                False,  # monitoring_enabled = False
                datetime.now().timestamp()
            ])

        except Exception as e:
            self.logger.warning(f"Failed to write basic performance data for task {task.id}: {e}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get a summary of performance metrics for reporting.
        
        Returns:
            Dictionary with performance summary information
        """
        try:
            if not self._is_performance_monitoring_enabled():
                return {
                    "monitoring_enabled": False,
                    "total_tasks": len(self.tasks),
                    "total_metrics": 0,
                    "summary": "Performance monitoring disabled"
                }

            # Get performance statistics
            total_metrics = len(self.performance_monitor.metrics)

            # Calculate some basic statistics
            timing_metrics = [m for m in self.performance_monitor.metrics if m.unit == "s"]
            avg_timing = sum(m.value for m in timing_metrics) / len(timing_metrics) if timing_metrics else 0

            return {
                "monitoring_enabled": True,
                "total_tasks": len(self.tasks),
                "total_metrics": total_metrics,
                "timing_metrics_count": len(timing_metrics),
                "average_timing": round(avg_timing, 2),
                "summary": f"Collected {total_metrics} performance metrics"
            }

        except Exception as e:
            self.logger.warning(f"Failed to generate performance summary: {e}")
            return {
                "monitoring_enabled": False,
                "error": str(e),
                "summary": "Performance summary generation failed"
            }

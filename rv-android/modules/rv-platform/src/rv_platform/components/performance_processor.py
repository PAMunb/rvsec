# rv_platform/components/performance_processor.py
"""
Performance metrics processor component for RV-Platform.

This component processes task execution metrics and generates CSV files
for performance analysis and research purposes.
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


class PerformanceProcessorComponent:
    """
    Performance metrics processor component for generating performance CSV files.

    This component extracts task execution metrics and generates standardized
    CSV files for performance analysis.

    ### Architectural Role:
    - Generates standardized performance.csv files for analysis
    - Extracts timing data from task results
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
            'rv_platform.components.performance_processor',
            {CONTEXT_COMPONENT: 'PerformanceProcessorComponent'}
        )

        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)

    @ErrorHandler.handle_errors(component="PerformanceProcessorComponent", phase="performance_processing")
    def generate(self) -> None:
        """Generate performance CSV files from task execution metrics."""
        with self.logger.with_context(phase="performance_processing"):
            self.logger.info(LOG_START.format(phase="performance metrics processing"))
            self._generate_performance_csv()
            self.logger.info(LOG_COMPLETE.format(phase="performance metrics processing"))

    @ErrorHandler.handle_errors(component="PerformanceProcessorComponent", phase="performance_csv")
    def _generate_performance_csv(self) -> None:
        """Generate performance CSV with task execution metrics."""
        with self.logger.with_context(phase="performance_csv"):
            self.logger.info(LOG_START.format(phase="performance CSV generation"))

            performance_file = os.path.join(self.results_dir, "performance.csv")

            with open(performance_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow([
                    'apk', 'rep', 'timeout', 'tool', 'execution_time_seconds',
                    'task_state', 'timestamp'
                ])

                # Process each completed task
                for task in self.tasks:
                    self._write_task_performance_data(writer, task)

            self.logger.info(f"Performance CSV generated: {performance_file}")

    def _write_task_performance_data(self, writer: csv.writer, task: Any) -> None:
        """
        Write performance data for a single task to CSV.

        Args:
            writer: CSV writer instance
            task: Task to process for performance data
        """
        try:
            config = task.config
            apk_name = config.apk_name
            repetition = config.repetition
            timeout = config.timeout
            tool_name = config.tool_config.get_full_tool_name()

            execution_time = getattr(task.result, 'execution_time_seconds', 0)
            task_state = getattr(task.result, 'state', 'unknown')

            writer.writerow([
                apk_name,
                repetition,
                timeout,
                tool_name,
                execution_time,
                task_state,
                datetime.now().timestamp()
            ])

        except Exception as e:
            self.logger.warning(f"Failed to write performance data for task {task.id}: {e}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get a summary of performance metrics for reporting.

        Returns:
            Dictionary with performance summary information
        """
        try:
            return {
                "total_tasks": len(self.tasks),
                "summary": f"Processed {len(self.tasks)} tasks"
            }
        except Exception as e:
            self.logger.warning(f"Failed to generate performance summary: {e}")
            return {
                "error": str(e),
                "summary": "Performance summary generation failed"
            }

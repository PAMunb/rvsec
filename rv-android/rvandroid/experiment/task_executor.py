# rvandroid/experiment/task_executor.py
"""
Task executor implementation for running individual tasks.
Handles the execution of a single task and collects results.
"""

import logging
import os
import traceback
from typing import Optional, Dict, Any

from rvandroid.analysis.coverage_tracker import CoverageTracker
from rvandroid.experiment.event_system import EventBus, EventType
from rvandroid.experiment.task_model import Task
from rvandroid.model.coverage import LogcatRepository
from rvandroid.parser.static import static_analysis_parser
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.emulator_manager import EmulatorManager
from rvandroid.util.logcat_manager import LogcatManager
from rvandroid.util.performance_monitor import PerformanceMonitor
from rvandroid.util.spreadsheet_exporter import ExportContext, SpreadsheetExporter


class TaskExecutor:
    """
    Manages the execution of individual tasks within an experiment workflow.

    ### Architectural Decisions:
    - Implements a robust, context-managed approach to task execution
    - Uses dependency injection for component management
    - Supports comprehensive error handling and performance tracking
    - Provides flexible task lifecycle management

    ### Role in the System:
    - Coordinates the detailed execution flow of individual experiment tasks
    - Manages emulator interactions, app installation, and tool execution
    - Tracks and collects coverage data during task execution
    - Ensures proper resource management and cleanup

    ### Key Considerations:
    - Handles complex task configuration and runtime scenarios
    - Supports multiple testing tools and execution strategies
    - Implements comprehensive logging and performance monitoring
    - Manages intricate task state transitions

    ### Integration Strategy:
    - Interacts with emulator management, logcat tracking, and coverage systems
    - Compatible with various testing tools and experiment configurations
    - Uses event-driven architecture for communication
    - Supports dynamic task configuration

    ### Performance and Scalability:
    - Designed for efficient, parallel task execution
    - Minimizes resource overhead during task processing
    - Supports adaptable performance monitoring
    - Scales across different experiment configurations and complexities
    """

    def __init__(self, task: Task, tool: AbstractTool, event_bus: Optional[EventBus] = None):
        """
        Initialize with a task and tool.

        Args:
            task: Task to execute
            tool: Tool implementation to use
            event_bus: Optional event bus for notifications
        """
        self.task = task
        self.tool = tool
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus or EventBus.get_instance()

        # Component managers
        self.emulator_manager = EmulatorManager()
        self.logcat_manager = LogcatManager()
        self.coverage_tracker = None

        # Performance monitoring
        self.performance_monitor = PerformanceMonitor.get_instance()

    def execute(self) -> bool:
        """
        Execute the task through a comprehensive workflow, including performance monitoring,
        environment setup, tool execution, and error handling.

        Performs the following key steps:
        - Validates task configuration
        - Sets up Android environment
        - Initializes coverage tracking
        - Executes specified tool
        - Processes coverage data
        - Handles cleanup and error scenarios

        Returns:
            bool: True if task execution was successful, False otherwise
        """
        task_context = {
            "task_id": self.task.id,
            "apk_name": self.task.config.apk_name,
            "tool_name": self.task.config.tool_name,
            "repetition": self.task.config.repetition,
            "timeout": self.task.config.timeout
        }

        self.logger.info(f"Starting execution of task {self.task}")

        if not self.task.app:
            self.task.mark_error("Task has no app instance set")
            self.logger.error("Cannot execute task: app instance not set")
            self._publish_event(EventType.TASK_FAILED, {
                "error": "Task has no app instance set"
            })
            return False

        try:
            self.task.mark_started()
            self._publish_event(EventType.TASK_STARTED)

            # Measure the total execution time
            with self.performance_monitor.measure_time("task_execution_total", task_context):
                # Get static analysis data if not already available
                with self.performance_monitor.measure_time("load_static_data", task_context):
                    self._load_static_data()

                # Initialize coverage tracker
                with self.performance_monitor.measure_time("initialize_coverage_tracker", task_context):
                    self.coverage_tracker = CoverageTracker(
                        logcat_file=self.task.result.logcat_file,
                        static_data=self.task.static_data
                    )

                # Start emulator and run the task
                with self.performance_monitor.measure_time("environment_setup", task_context):
                    with self.emulator_manager.start_emulator("RVSec", self.task.config.no_window) as android:
                        self._publish_event(EventType.EMULATOR_STARTED, {"device_id": self.task.config.device_id})

                        # Install app if needed
                        if not self.task.config.skip_installation:
                            self.emulator_manager.install_app(self.task.app)
                            self._publish_event(EventType.APP_INSTALLED, {"app_name": self.task.app.name})

                        # Start logcat capture
                        with self.performance_monitor.measure_time("logcat_capture_setup", task_context):
                            self.logcat_manager.start_capture(
                                self.task.result.logcat_file,
                                clear_buffer=self.task.config.clean_logcat
                            )

                            # Start the coverage tracker after logcat capture is set up
                            self.coverage_tracker.start()
                            self._publish_event(EventType.COVERAGE_TRACKING_STARTED, {
                                "logcat_file": self.task.result.logcat_file
                            })

                        # Execute the tool
                        with self.performance_monitor.measure_time("tool_execution", task_context):
                            self._execute_tool()

                # Process coverage data outside the emulator context manager
                # (in case emulator shutdown causes issues)
                with self.performance_monitor.measure_time("process_coverage", task_context):
                    self._process_coverage_data()

            # Mark task as completed
            self.task.mark_completed()

            # Record metrics about the task
            self.performance_monitor.record_metric(
                name="task_duration",
                value=(self.task.result.end_time - self.task.result.start_time).total_seconds(),
                unit="s",
                context=task_context
            )

            self._publish_event(EventType.TASK_COMPLETED)
            self.logger.info(f"Task {self.task.id} executed successfully")
            return True

        except Exception as e:
            error_message = str(e)
            self.logger.error(f"Error executing task {self.task.id}: {error_message}")
            self.logger.error(traceback.format_exc())
            self.task.mark_error(error_message)

            # Record error metric
            self.performance_monitor.record_metric(
                name="task_error",
                value=1,
                context={**task_context, "error": error_message}
            )

            self._publish_event(EventType.TASK_FAILED, {
                "error": error_message,
                "traceback": traceback.format_exc()
            })

            # Clean up resources
            self._cleanup_resources()

            return False

    def _load_static_data(self):
        """Load static analysis data if not already available."""
        if not self.task.static_data:
            # Try to load static analysis data
            self.logger.info("Loading static analysis data")

            print(self.task.results_dir,
                self.task.config.apk_name,
                self.task.app.package_name)
            self.task.static_data = static_analysis_parser.read_static_analysis_files(
                self.task.results_dir,
                self.task.config.apk_name,
                self.task.app.package_name
            )

            if self.task.static_data:
                self.logger.info("Static analysis data loaded successfully")
            else:
                self.logger.warning("No static analysis data found, coverage tracking will be limited")

    def _execute_tool(self) -> None:
        """Execute the tool implementation"""
        self.logger.info(f"Executing tool: {self.tool.name}")
        self._publish_event(EventType.TOOL_STARTED, {"tool_name": self.tool.name})

        # Execute the tool with the task
        self.tool.execute(self.task, self.task.app)

        self._publish_event(EventType.TOOL_STOPPED, {"tool_name": self.tool.name})

    def _process_coverage_data(self) -> None:
        """
        Process coverage data after task execution using standardized repository model.
        Ensures consistent usage of LogcatRepository for all coverage data.

        This method:
        1. Stops the coverage tracker and logcat capture
        2. Retrieves the repository from the tracker
        3. Updates task result metrics from the repository
        4. Exports data to CSV if configured
        5. Logs a summary of coverage metrics
        6. Publishes coverage updated event
        """
        if not self.coverage_tracker:
            self.logger.warning("No coverage tracker available to process coverage data")
            return

        # Stop the coverage tracker
        self.coverage_tracker.stop()

        # Stop logcat capture
        self.logcat_manager.stop_capture()

        # Get repository from coverage tracker - this is the source of truth
        repository = self.coverage_tracker.repository

        # Calculate metrics using the repository
        metrics = repository.calculate_metrics()
        metrics_dict = metrics.to_dict()

        # Update task result with metrics from repository using standardized keys
        # to ensure consistency across the system
        self.task.result.coverage_metrics.update({
            "method_coverage": metrics_dict["method_coverage"],
            "activities_coverage": metrics_dict["activity_coverage"],
            "methods_jca_reachable_coverage": metrics_dict["mop_method_coverage"],
            "total_errors": metrics_dict["unique_errors"],
            "total_method_calls": metrics.called_methods
        })

        # Store the repository directly in the task
        # This ensures the task has direct access to the standardized data model
        self.task.repository = repository

        # Export data to CSV files
        self._export_repository_data(repository)

        # Log coverage summary
        metrics = self.task.result.coverage_metrics
        self.logger.info(
            f"Final coverage: Methods: {metrics.get('method_coverage', 0):.2f}%, "
            f"Activities: {metrics.get('activities_coverage', 0):.2f}%, "
            f"MOP Methods: {metrics.get('methods_jca_reachable_coverage', 0):.2f}%, "
            f"Errors: {metrics.get('total_errors', 0)}"
        )

        # Publish coverage updated event
        self._publish_event(EventType.COVERAGE_UPDATED, {
            "coverage_metrics": metrics,
            "error_count": metrics.get('total_errors', 0)
        })

    def _analyze_coverage(self) -> None:
        """
        Analyze coverage data directly from the coverage tracker's repository.

        This method:
        1. Gets coverage metrics directly from the repository
        2. Updates task result with standardized metrics
        3. Logs coverage statistics
        """
        if not self.coverage_tracker or not self.coverage_tracker.repository:
            self.logger.warning("No repository available for coverage analysis")
            return

        repository = self.coverage_tracker.repository

        # Get metrics directly from repository
        metrics = repository.calculate_metrics()

        # Update task metrics with standardized keys
        self.task.result.coverage_metrics.update({
            "method_coverage": metrics.method_coverage,
            "activity_coverage": metrics.activity_coverage,
            "methods_jca_coverage": metrics.mop_method_coverage,
            "total_errors": metrics.unique_errors,
            "total_method_calls": metrics.called_methods,
            "total_classes": metrics.total_classes,
            "called_classes": metrics.called_classes
        })

        # Log meaningful coverage statistics
        self.logger.info(
            f"Coverage analysis: {metrics.called_methods}/{metrics.total_methods} methods "
            f"({metrics.method_coverage:.2f}%), "
            f"{metrics.called_activities}/{metrics.total_activities} activities "
            f"({metrics.activity_coverage:.2f}%)"
        )

        # Store metrics in task for later retrieval
        self.task.metrics = metrics

    def _export_repository_data(self, repository: LogcatRepository) -> None:
        """
        Export repository data to CSV files.

        Args:
            repository: The LogcatRepository to export
        """
        try:
            # Check if export is enabled
            export_enabled = getattr(self.task.config, "export_to_csv", True)
            if not export_enabled:
                self.logger.debug("CSV export is disabled for this task")
                return

            # Create export context from task
            from rvandroid.util.spreadsheet_exporter import ExportContext, SpreadsheetExporter
            context = ExportContext.from_task(self.task)

            # Determine export files
            experiment_dir = os.path.dirname(os.path.dirname(self.task.results_dir))
            coverage_file = os.path.join(experiment_dir, "coverage_data.csv")
            error_file = os.path.join(experiment_dir, "error_data.csv")

            # Export data directly from repository
            exporter = SpreadsheetExporter()

            # Append to existing files or create new ones
            if os.path.exists(coverage_file):
                exporter.append_to_coverage_sheet(repository, context, coverage_file)
            else:
                exporter.export_coverage_data(repository, context, coverage_file)

            if os.path.exists(error_file):
                exporter.append_to_error_sheet(repository, context, error_file)
            else:
                exporter.export_error_data(repository, context, error_file)

            self.logger.info(f"Exported task data to CSV files")

        except Exception as e:
            self.logger.error(f"Error exporting repository data: {e}", exc_info=True)

    def _cleanup_resources(self) -> None:
        """Clean up resources in case of error."""
        # Stop coverage tracker if it's running
        if self.coverage_tracker:
            try:
                self.logger.debug("Stopping coverage tracker")
                self.coverage_tracker.stop()
            except Exception as e:
                self.logger.warning(f"Error stopping coverage tracker: {e}")

        # Stop logcat capture
        self.logcat_manager.stop_capture()

    def _publish_event(self, event_type: EventType, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish a task event.

        Args:
            event_type: Type of event
            details: Optional event details
        """
        if not self.event_bus:
            return

        if event_type in [EventType.TASK_STARTED, EventType.TASK_COMPLETED, EventType.TASK_FAILED,
                          EventType.EMULATOR_STARTED, EventType.EMULATOR_STOPPED,
                          EventType.APP_INSTALLED, EventType.TOOL_STARTED, EventType.TOOL_STOPPED]:
            # For task-related events
            self.event_bus.publish_task_event(
                event_type=event_type,
                task_id=self.task.id,
                task_config={
                    "apk_name": self.task.config.apk_name,
                    "repetition": self.task.config.repetition,
                    "timeout": self.task.config.timeout,
                    "tool_name": self.task.config.tool_name
                },
                details=details or {},
                source="TaskExecutor"
            )
        elif event_type in [EventType.COVERAGE_TRACKING_STARTED, EventType.COVERAGE_TRACKING_STOPPED,
                            EventType.COVERAGE_UPDATED]:
            # For analysis-related events
            self.event_bus.publish_analysis_event(
                event_type=event_type,
                data=details or {},
                related_task_id=self.task.id,
                source="TaskExecutor"
            )

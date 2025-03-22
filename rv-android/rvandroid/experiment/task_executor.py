# rvandroid/experiment/task_executor.py
import os
from typing import Optional, Dict, Any

from rvandroid.experiment.event_system import EventBus, EventType
from rvandroid.experiment.task_components import (
    StaticAnalysisComponent,
    CoverageComponent,
    EmulatorComponent,
    LogcatComponent,
    ToolExecutionComponent
)
from rvandroid.experiment.task_model import Task
from rvandroid.model.coverage import LogcatRepository
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.error_handler import ErrorHandler, handle_errors
from rvandroid.util.exceptions import TaskExecutionError
from rvandroid.util.logging_manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor
from rvandroid.util.spreadsheet_exporter import ExportContext, SpreadsheetExporter


class TaskExecutor:
    """
    Manages the execution of individual tasks within an experiment workflow using a component-based architecture.

    ### Architectural Decisions:
    - Implements a component-based approach to task execution
    - Uses dependency injection for component management
    - Supports comprehensive error handling and performance tracking
    - Provides flexible task lifecycle management

    ### Role in the System:
    - Coordinates the detailed execution flow of individual experiment tasks
    - Manages emulator interactions, app installation, and tool execution
    - Tracks and collects coverage data during task execution
    - Ensures proper resource management and cleanup
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
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()

        # Set up logging using LoggingManager
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "experiment.task_executor",
            {
                LoggingManager.CONTEXT_TASK_ID: task.id,
                LoggingManager.CONTEXT_APP_NAME: task.config.apk_name,
                LoggingManager.CONTEXT_TOOL_NAME: tool.name,
                LoggingManager.CONTEXT_COMPONENT: "TaskExecutor"
            }
        )

        # Initialize specialized components
        self.static_analysis = StaticAnalysisComponent(task, event_bus)
        self.coverage = CoverageComponent(task, event_bus)
        self.emulator = EmulatorComponent(task, event_bus)
        self.logcat = LogcatComponent(task, event_bus)
        self.tool_executor = ToolExecutionComponent(task, tool, event_bus)

        # Performance monitoring
        self.performance_monitor = PerformanceMonitor.get_instance()

    def execute(self) -> bool:
        """
        Execute the task with comprehensive error handling and performance monitoring.

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

        self.logger.info(LoggingManager.LOG_START.format(operation=f"execution of task {self.task}"))

        if not self.task.app:
            error_msg = "Task has no app instance set"
            self.task.mark_error(error_msg)
            self.logger.error(LoggingManager.LOG_ERROR.format(
                operation="task execution",
                error="app instance not set"
            ))
            self._publish_event(EventType.TASK_FAILED, {
                "error": error_msg
            })
            return False

        try:
            self.task.mark_started()
            self._publish_event(EventType.TASK_STARTED)

            # Measure the total execution time
            with self.performance_monitor.measure_time("task_execution_total", task_context):
                # Get static analysis data if not already available
                with self.logger.with_context(phase="load_static_data"):
                    with self.performance_monitor.measure_time("load_static_data", task_context):
                        self.static_analysis.load_static_data(task_context)

                # Initialize coverage tracker
                with self.logger.with_context(phase="initialize_coverage"):
                    with self.performance_monitor.measure_time("initialize_coverage_tracker", task_context):
                        with handle_errors(task_context):
                            self.coverage.initialize_tracker()

                # Start emulator and run the task
                with self.logger.with_context(phase="environment_setup"):
                    with self.performance_monitor.measure_time("environment_setup", task_context):
                        with self.emulator.start_emulator("RVSec") as android:
                            # Install app if needed
                            if not self.task.config.skip_installation:
                                with self.logger.with_context(phase="app_installation"):
                                    with handle_errors({**task_context, "phase": "app_installation"}):
                                        self.emulator.install_app(android, self.task.app)

                            # Start logcat capture
                            with self.logger.with_context(phase="logcat_setup"):
                                with self.performance_monitor.measure_time("logcat_capture_setup", task_context):
                                    with handle_errors({**task_context, "phase": "logcat_setup"}):
                                        self.logcat.start_capture()
                                        # Start the coverage tracker
                                        self.coverage.start_tracking()

                            # Execute the tool
                            with self.logger.with_context(phase="tool_execution"):
                                with self.performance_monitor.measure_time("tool_execution", task_context):
                                    try:
                                        self.tool_executor.execute_tool()
                                    except Exception as e:
                                        # Convert to TaskExecutionError with tool info
                                        task_error = TaskExecutionError(
                                            f"Tool execution failed: {str(e)}",
                                            self.task.id,
                                            e
                                        )
                                        self.error_handler.handle_error(task_error, task_context)
                                        raise task_error

                # Process coverage data
                with self.logger.with_context(phase="process_coverage"):
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
            self.logger.info(LoggingManager.LOG_COMPLETE.format(
                operation=f"Task {self.task.id}"
            ))
            return True

        except Exception as e:
            # Let the error handler process the error
            self.error_handler.handle_error(e, task_context)

            # Still need to update task status
            error_message = str(e)
            self.logger.error(LoggingManager.LOG_ERROR.format(
                operation=f"execution of task {self.task.id}",
                error=error_message
            ))
            self.task.mark_error(error_message)

            # Record error metric
            self.performance_monitor.record_metric(
                name="task_error",
                value=1,
                context={**task_context, "error": error_message}
            )

            self._publish_event(EventType.TASK_FAILED, {
                "error": error_message
            })

            # Clean up resources
            self._cleanup_resources()

            return False

    def _process_coverage_data(self) -> None:
        """Process coverage data after task execution."""
        # Stop coverage and logcat
        with self.logger.with_context(phase="stopping_coverage"):
            self.coverage.stop_tracking()
            self.logcat.stop_capture()

        # Process coverage results
        with self.logger.with_context(phase="processing_results"):
            self.coverage.process_results()

        # Get repository
        repository = self.coverage.get_repository()
        if repository:
            # Export data to CSV files if needed
            self._export_repository_data(repository)

    def _export_repository_data(self, repository: LogcatRepository) -> None:
        """Export repository data to CSV files with error handling."""
        try:
            # Check if export is enabled
            export_enabled = getattr(self.task.config, "export_to_csv", True)
            if not export_enabled:
                self.logger.debug(LoggingManager.LOG_SKIPPED.format(
                    operation="CSV export",
                    reason="export is disabled for this task"
                ))
                return

            with self.logger.with_context(phase="csv_export"):
                # Create export context from task
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

                self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="CSV data export"))

        except Exception as e:
            self.logger.error(LoggingManager.LOG_ERROR.format(
                operation="exporting repository data",
                error=str(e)
            ))
            # Don't raise - data export is not critical to task success

    def _cleanup_resources(self) -> None:
        """Clean up resources in case of error."""
        with self.logger.with_context(phase="resource_cleanup"):
            try:
                # Stop coverage tracking
                self.coverage.stop_tracking()
            except Exception as e:
                self.logger.warning(LoggingManager.LOG_ERROR.format(
                    operation="stopping coverage tracking",
                    error=str(e)
                ))

            try:
                # Stop logcat capture
                self.logcat.stop_capture()
            except Exception as e:
                self.logger.warning(LoggingManager.LOG_ERROR.format(
                    operation="stopping logcat capture",
                    error=str(e)
                ))

            try:
                # Clean up tool processes
                self.tool_executor.cleanup_processes()
            except Exception as e:
                self.logger.warning(LoggingManager.LOG_ERROR.format(
                    operation="cleaning up tool processes",
                    error=str(e)
                ))

    def _publish_event(self, event_type: EventType, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish a task event.

        Args:
            event_type: Type of event
            details: Optional event details
        """
        if not self.event_bus:
            return

        if event_type in [EventType.TASK_STARTED, EventType.TASK_COMPLETED, EventType.TASK_FAILED]:
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

# rvandroid/experiment/task/task_executor.py
import os
from typing import Optional, Dict, Any

from rvandroid.domain.coverage import LogcatRepository
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.task.components import (
    StaticAnalysisComponent,
    CoverageComponent,
    EmulatorComponent,
    LogcatComponent,
    ToolExecutionComponent
)
from rvandroid.experiment.task.task_model import Task
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.decorators import task_phase, log_execution
from rvandroid.util.error import handle_errors
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.exceptions import TaskExecutionError
from rvandroid.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, CONTEXT_TOOL_NAME, CONTEXT_COMPONENT, \
    LOG_START, LOG_ERROR, LOG_COMPLETE, LOG_SKIPPED
from rvandroid.util.performance_monitor import PerformanceMonitor
from rvandroid.util.spreadsheet_exporter import ExportContext, SpreadsheetExporter


@log_execution(logger_prefix="experiment.task_executor", component_name="TaskExecutor")
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

        # Initialize standardized context for all logging and events
        self.context = {
            CONTEXT_TASK_ID: task.id,
            CONTEXT_APP_NAME: task.config.apk_name,
            CONTEXT_TOOL_NAME: tool.name,
            CONTEXT_COMPONENT: "TaskExecutor"
        }

        # Initialize specialized components
        self.static_analysis = StaticAnalysisComponent(task, event_bus)
        self.coverage = CoverageComponent(task, event_bus)
        self.emulator = EmulatorComponent(task, event_bus)
        self.logcat = LogcatComponent(task, event_bus)
        self.tool_executor = ToolExecutionComponent(task, tool, event_bus)

        # Performance monitoring
        self.performance_monitor = PerformanceMonitor.get_instance()

    def _get_task_context(self) -> Dict[str, Any]:
        """
        Get the standard context for this task execution.
        Used by the task_phase decorator.

        Returns:
            Dictionary with task context
        """
        return {
            "task_id": self.task.id,
            "apk_name": self.task.config.apk_name,
            "tool_name": self.task.config.tool_name,
            "repetition": self.task.config.repetition,
            "timeout": self.task.config.timeout
        }

    def execute(self) -> bool:
        """
        Execute the task with comprehensive error handling and performance monitoring.

        Returns:
            bool: True if task execution was successful, False otherwise
        """
        self.logger.info(LOG_START.format(operation=f"execution of task {self.task}"))

        if not self.task.app:
            error_msg = "Task has no app instance set"
            self.task.mark_error(error_msg)
            self.logger.error(LOG_ERROR.format(
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
            with self.performance_monitor.measure_time("task_execution_total", self._get_task_context()):
                # Execute task phases in sequence
                self._load_static_data()
                self._initialize_coverage()
                self._run_emulator_session()
                self._process_coverage_data()

            # Mark task as completed
            self.task.mark_completed()

            # Record metrics about the task
            self.performance_monitor.record_metric(
                name="task_duration",
                value=(self.task.result.end_time - self.task.result.start_time).total_seconds(),
                unit="s",
                context=self._get_task_context()
            )

            self._publish_event(EventType.TASK_COMPLETED)
            self.logger.info(LOG_COMPLETE.format(
                operation=f"Task {self.task.id}"
            ))
            return True

        except Exception as e:
            # Let the error handler process the error
            self.error_handler.handle_error(e, self._get_task_context())

            # Still need to update task status
            error_message = str(e)
            self.logger.error(LOG_ERROR.format(
                operation=f"execution of task {self.task.id}",
                error=error_message
            ))
            self.task.mark_error(error_message)

            # Record error metric
            self.performance_monitor.record_metric(
                name="task_error",
                value=1,
                context={**self._get_task_context(), "error": error_message}
            )

            self._publish_event(EventType.TASK_FAILED, {
                "error": error_message
            })

            # Clean up resources
            self._cleanup_resources()

            return False

    @task_phase("load_static_data")
    def _load_static_data(self) -> None:
        """Load static analysis data for the task."""
        self.static_analysis.load_static_data(self._get_task_context())

    @task_phase("initialize_coverage")
    def _initialize_coverage(self) -> None:
        """Initialize the coverage tracker."""
        self.coverage.initialize_tracker()

    def _run_emulator_session(self) -> None:
        """Start emulator and run the task."""
        with self.performance_monitor.measure_time("environment_setup", self._get_task_context()):
            with self.emulator.start_emulator("RVSec") as android:
                # Install app if needed
                if not self.task.config.skip_installation:
                    with handle_errors({**self._get_task_context(), "phase": "app_installation"}):
                        self.emulator.install_app(android, self.task.app)

                # Set up logcat and coverage
                self._setup_logcat()

                # Execute the tool
                self._execute_tool()

    @task_phase("logcat_setup")
    def _setup_logcat(self) -> None:
        """Start logcat capture and coverage tracking."""
        self.logcat.start_capture()
        # Start the coverage tracker
        self.coverage.start_tracking()

    @task_phase("tool_execution")
    def _execute_tool(self) -> None:
        """Execute the testing tool."""
        try:
            self.tool_executor.execute_tool()
        except Exception as e:
            # Convert to TaskExecutionError with tool info
            task_error = TaskExecutionError(
                f"Tool execution failed: {str(e)}",
                self.task.id,
                e
            )
            self.error_handler.handle_error(task_error, self._get_task_context())
            raise task_error

    @task_phase("process_coverage")
    def _process_coverage_data(self) -> None:
        """Process coverage data after task execution."""
        # Stop coverage and logcat
        self.coverage.stop_tracking()
        self.logcat.stop_capture()

        # Process coverage results
        self.coverage.process_results()

        # Get repository
        repository = self.coverage.get_repository()
        if repository:
            # Export data to CSV files if needed
            self._export_repository_data(repository)

    @task_phase("csv_export", handle_task_errors=False)
    def _export_repository_data(self, repository: LogcatRepository) -> None:
        """
        Export repository data to CSV files with error handling.

        Args:
            repository: Coverage repository to export
        """
        # Check if export is enabled
        export_enabled = getattr(self.task.config, "export_to_csv", True)
        if not export_enabled:
            self.logger.debug(LOG_SKIPPED.format(
                operation="CSV export",
                reason="export is disabled for this task"
            ))
            return

        try:
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

            self.logger.info(LOG_COMPLETE.format(operation="CSV data export"))

        except Exception as e:
            self.logger.error(LOG_ERROR.format(
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
                self.logger.warning(LOG_ERROR.format(
                    operation="stopping coverage tracking",
                    error=str(e)
                ))

            try:
                # Stop logcat capture
                self.logcat.stop_capture()
            except Exception as e:
                self.logger.warning(LOG_ERROR.format(
                    operation="stopping logcat capture",
                    error=str(e)
                ))

            try:
                # Clean up tool processes
                self.tool_executor.cleanup_processes()
            except Exception as e:
                self.logger.warning(LOG_ERROR.format(
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

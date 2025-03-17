# rvandroid/experiment/task_executor.py - Modified to include coverage tracking
"""
Task executor implementation for running individual tasks.
Handles the execution of a single task and collects results.
"""

import logging
import traceback
from typing import Optional, Dict, Any

from rvandroid.analysis.coverage_tracker import CoverageTracker
from rvandroid.android import Android
from rvandroid.commands.command import Command
from rvandroid.experiment.event_system import EventBus, EventType
from rvandroid.experiment.task_model import Task
from rvandroid.parser.static import static_analysis_parser
from rvandroid.tools.tool_spec import AbstractTool


class TaskExecutor:
    """
    Executes a single task and collects results.
    Implements the command pattern for task execution.
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
        self.android: Optional[Android] = None
        self.logcat_process = None
        self.event_bus = event_bus or EventBus.get_instance()
        self.coverage_tracker = None

    def execute(self) -> bool:
        """
        Execute the task and collect results.

        Returns:
            True if execution was successful, False otherwise
        """
        # Get performance monitor
        from rvandroid.util.performance_monitor import PerformanceMonitor
        performance_monitor = PerformanceMonitor.get_instance()
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
            with performance_monitor.measure_time("task_execution_total", task_context):
                # Get static analysis data if not already available
                with performance_monitor.measure_time("load_static_data", task_context):
                    self._load_static_data()

                # Initialize coverage tracker
                with performance_monitor.measure_time("initialize_coverage_tracker", task_context):
                    self._initialize_coverage_tracker()

                # Initialize and start Android environment
                with performance_monitor.measure_time("environment_setup", task_context):
                    self._setup_environment()

                # Start logcat capture
                with performance_monitor.measure_time("logcat_capture_setup", task_context):
                    self._start_logcat_capture()

                # Execute the tool
                with performance_monitor.measure_time("tool_execution", task_context):
                    self._execute_tool()

                # Process coverage data
                with performance_monitor.measure_time("process_coverage", task_context):
                    self._process_coverage_data()

                # Cleanup
                with performance_monitor.measure_time("environment_cleanup", task_context):
                    self._cleanup_environment()

            # Mark task as completed
            self.task.mark_completed()

            # Record metrics about the task
            performance_monitor.record_metric(
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
            performance_monitor.record_metric(
                name="task_error",
                value=1,
                context={**task_context, "error": error_message}
            )

            self._publish_event(EventType.TASK_FAILED, {
                "error": error_message,
                "traceback": traceback.format_exc()
            })

            # Try to clean up even after error
            try:
                with performance_monitor.measure_time("error_cleanup", task_context):
                    self._cleanup_environment()
            except Exception as cleanup_error:
                self.logger.warning(f"Error during cleanup after task failure: {cleanup_error}")

            return False

    def _load_static_data(self):
        """Load static analysis data if not already available."""
        if not self.task.static_data:
            # Try to load static analysis data
            self.logger.info("Loading static analysis data")

            self.task.static_data = static_analysis_parser.read_static_analysis_files(
                self.task.results_dir,
                self.task.config.apk_name,
                self.task.app.package_name
            )
            print(f"self.task.static_data={self.task.static_data}")
            if self.task.static_data:
                self.logger.info("Static analysis data loaded successfully")
            else:
                self.logger.warning("No static analysis data found, coverage tracking will be limited")

    def _initialize_coverage_tracker(self):
        """Initialize the coverage tracker."""
        self.logger.info("Initializing coverage tracker")
        self.coverage_tracker = CoverageTracker(
            logcat_file=self.task.result.logcat_file,
            static_data=self.task.static_data
        )

    def _setup_environment(self) -> None:
        """Set up the Android environment for task execution"""
        self.logger.debug("Setting up Android environment")

        # Create Android instance
        self.android = Android()

        # Start emulator
        self.logger.info("Starting emulator")
        self.android.start_emulator("RVSec", self.task.config.no_window)
        self._publish_event(EventType.EMULATOR_STARTED, {"device_id": self.task.config.device_id})

        # Install app if needed
        if not self.task.config.skip_installation:
            self.logger.info(f"Installing app {self.task.app.name}")
            self.android.install_with_permissions(self.task.app)
            self._publish_event(EventType.APP_INSTALLED, {"app_name": self.task.app.name})

    def _start_logcat_capture(self) -> None:
        """Start capturing logcat output and initialize coverage tracking."""
        self.logger.debug("Starting logcat capture")

        # Clear logcat buffer if requested
        if self.task.config.clean_logcat:
            clear_cmd = Command("adb", ["logcat", "-c"])
            clear_cmd.invoke()

        # Start logcat capture process
        logcat_cmd = Command("adb", ["logcat", "-v", "threadtime", "-s", "RVSEC", "RVSEC-COV"])

        with open(self.task.result.logcat_file, "wb") as log_file:
            self.logcat_process = logcat_cmd.invoke_as_deamon(stdout=log_file)

        # Start coverage tracker
        self.coverage_tracker.start()

        # Publish event for logcat started
        self._publish_event(EventType.COVERAGE_TRACKING_STARTED, {
            "logcat_file": self.task.result.logcat_file
        })

    def _execute_tool(self) -> None:
        """Execute the tool implementation"""
        self.logger.info(f"Executing tool: {self.tool.name}")
        self._publish_event(EventType.TOOL_STARTED, {"tool_name": self.tool.name})

        # Execute the tool with the task
        self.tool.execute(self.task, self.task.app)

        self._publish_event(EventType.TOOL_STOPPED, {"tool_name": self.tool.name})

    # In TaskExecutor._process_coverage_data:
    def _process_coverage_data(self) -> None:
        """Process coverage data after task execution."""
        if not self.coverage_tracker:
            self.logger.warning("No coverage tracker available to process coverage data")
            return

        # Stop the coverage tracker
        self.coverage_tracker.stop()

        # Log the raw counts for debugging
        class_count = len(self.coverage_tracker.class_methods)
        method_count = sum(len(methods) for methods in self.coverage_tracker.class_methods.values())
        self.logger.info(f"Processing coverage data: {class_count} classes, {method_count} methods")

        # Make sure we have static data
        if not self.task.static_data:
            self.logger.warning("No static data available in task for coverage calculation")

        # Update coverage metrics one final time
        self.coverage_tracker._update_coverage_metrics()

        # Copy coverage data to task
        self.task.class_methods = self.coverage_tracker.class_methods
        self.task.errors = self.coverage_tracker.errors
        self.task.coverage = self.coverage_tracker.coverage

        # Additional explicit copy of formatted methods
        self.task.called_methods = self.coverage_tracker.formatted_methods

        # Explicitly update task coverage
        self.task.update_coverage()

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

    def _cleanup_environment(self) -> None:
        """Clean up the environment after execution"""
        self.logger.debug("Cleaning up environment")

        # Stop coverage tracker if it's still running
        if self.coverage_tracker and self.coverage_tracker.is_running:
            self.coverage_tracker.stop()

        # Stop logcat process
        if self.logcat_process:
            self.logger.debug("Stopping logcat process")
            try:
                self.logcat_process.kill()
            except Exception as e:
                self.logger.warning(f"Error stopping logcat: {e}")

        # Kill the emulator if needed
        if self.android:
            self.logger.debug("Stopping emulator")
            try:
                self.android.kill_emulator(self.task.config.device_id)
                self._publish_event(EventType.EMULATOR_STOPPED, {"device_id": self.task.config.device_id})
            except Exception as e:
                self.logger.warning(f"Error stopping emulator: {e}")

        self.logger.debug("Environment cleanup completed")

    def _publish_event(self, event_type: EventType, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish a task event.

        Args:
            event_type: Type of event
            details: Optional event details
        """
        if self.event_bus:
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

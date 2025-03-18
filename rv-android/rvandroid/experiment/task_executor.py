# rvandroid/experiment/task_executor.py
"""
Task executor implementation for running individual tasks.
Handles the execution of a single task and collects results.
"""

import logging
import os
import traceback
from contextlib import contextmanager
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
    The TaskExecutor class is responsible for managing the execution of individual
    tasks within an experiment. It processes tasks sequentially or in parallel,
    ensuring proper scheduling and monitoring.

    ### Architectural Decisions:
    - Implements a task queue to manage execution order and dependencies.
    - Uses multithreading to allow concurrent execution of independent tasks.
    - Provides error handling and logging mechanisms for robust task execution.

    ### Role in the System:
    - Facilitates the execution of automated test cases and analysis tasks.
    - Ensures that experiments run efficiently by optimizing task scheduling.
    - Integrates with the EventSystem to trigger and respond to execution events.
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
        self.android = None
        self.logcat_process = None
        self.logcat_file_handle = None
        self.coverage_tracker = None

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
                    self.coverage_tracker = CoverageTracker(
                        logcat_file=self.task.result.logcat_file,
                        static_data=self.task.static_data
                    )

                # Initialize and start Android environment
                with performance_monitor.measure_time("environment_setup", task_context):
                    self._setup_environment()

                # Start logcat capture
                with performance_monitor.measure_time("logcat_capture_setup", task_context):
                    self._start_logcat_capture()
                    # Start the coverage tracker after logcat capture is set up
                    self.coverage_tracker.start()

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

            if self.task.static_data:
                self.logger.info("Static analysis data loaded successfully")
            else:
                self.logger.warning("No static analysis data found, coverage tracking will be limited")

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
        """Start capturing logcat output with improved resource management."""
        self.logger.debug("Starting logcat capture")

        try:
            # Clear logcat buffer if requested
            if self.task.config.clean_logcat:
                clear_cmd = Command("adb", ["logcat", "-c"])
                clear_cmd.invoke()
                self.logger.debug("Cleared logcat buffer")

            # Create output directory if it doesn't exist
            logcat_dir = os.path.dirname(self.task.result.logcat_file)
            if not os.path.exists(logcat_dir):
                os.makedirs(logcat_dir, exist_ok=True)

            # Start logcat capture process
            logcat_cmd = Command("adb", ["logcat", "-v", "threadtime", "-s", "RVSEC", "RVSEC-COV"])

            # Open the file with proper context management
            log_file = open(self.task.result.logcat_file, "wb")

            try:
                self.logcat_process = logcat_cmd.invoke_as_deamon(stdout=log_file)

                # Store the log file handle for later cleanup
                self.logcat_file_handle = log_file

                # Publish event for logcat started
                self._publish_event(EventType.COVERAGE_TRACKING_STARTED, {
                    "logcat_file": self.task.result.logcat_file
                })

                self.logger.info(f"Logcat capture started to {self.task.result.logcat_file}")

            except Exception:
                # Close the file handle if the command fails
                log_file.close()
                raise

        except Exception as e:
            self.logger.error(f"Failed to start logcat capture: {e}")

            # Clean up any resources if initialization fails
            if hasattr(self, 'logcat_process') and self.logcat_process:
                try:
                    self.logcat_process.kill()
                    self.logcat_process = None
                except Exception:
                    pass

            raise

    def _execute_tool(self) -> None:
        """Execute the tool implementation"""
        self.logger.info(f"Executing tool: {self.tool.name}")
        self._publish_event(EventType.TOOL_STARTED, {"tool_name": self.tool.name})

        # Execute the tool with the task
        self.tool.execute(self.task, self.task.app)

        self._publish_event(EventType.TOOL_STOPPED, {"tool_name": self.tool.name})

    def _process_coverage_data(self) -> None:
        """Process coverage data after task execution."""
        if not hasattr(self, 'coverage_tracker') or not self.coverage_tracker:
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
        """Clean up the environment after execution with improved resource management."""
        self.logger.debug("Cleaning up environment")

        # Stop coverage tracker if it's running
        if hasattr(self, 'coverage_tracker') and self.coverage_tracker:
            try:
                self.logger.debug("Stopping coverage tracker")
                self.coverage_tracker.stop()
            except Exception as e:
                self.logger.warning(f"Error stopping coverage tracker: {e}")

        # Kill logcat process
        if hasattr(self, 'logcat_process') and self.logcat_process:
            try:
                self.logger.debug("Stopping logcat process")
                self.logcat_process.kill()
                self.logcat_process = None
            except Exception as e:
                self.logger.warning(f"Error stopping logcat process: {e}")

        # Close logcat file handle
        if hasattr(self, 'logcat_file_handle') and self.logcat_file_handle:
            try:
                self.logger.debug("Closing logcat file")
                self.logcat_file_handle.close()
                self.logcat_file_handle = None
            except Exception as e:
                self.logger.warning(f"Error closing logcat file: {e}")

        # Kill the emulator if needed
        if self.android:
            self.logger.debug("Stopping emulator")
            try:
                self.android.kill_emulator("RVSec")
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
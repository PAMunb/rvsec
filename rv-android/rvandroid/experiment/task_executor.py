# rvandroid/experiment/task_executor.py
"""
Task executor implementation for running individual tasks.
Handles the execution of a single task and collects results.
"""

import logging
import traceback
from typing import Optional, Dict, Any

from rvandroid.android import Android
from rvandroid.commands.command import Command
from rvandroid.experiment.event_system import EventBus, EventType
from rvandroid.experiment.task_model import Task
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

    def execute(self) -> bool:
        """
        Execute the task and collect results.

        Returns:
            True if execution was successful, False otherwise
        """
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

            # Initialize and start Android environment
            self._setup_environment()

            # Start logcat capture
            self._start_logcat_capture()

            # Execute the tool
            self._execute_tool()

            # Cleanup
            self._cleanup_environment()

            # Mark task as completed
            self.task.mark_completed()
            self._publish_event(EventType.TASK_COMPLETED)
            self.logger.info(f"Task {self.task.id} executed successfully")
            return True

        except Exception as e:
            error_message = str(e)
            self.logger.error(f"Error executing task {self.task.id}: {error_message}")
            self.logger.error(traceback.format_exc())
            self.task.mark_error(error_message)
            self._publish_event(EventType.TASK_FAILED, {
                "error": error_message,
                "traceback": traceback.format_exc()
            })

            # Try to clean up even after error
            self._cleanup_environment()
            return False

    def _setup_environment(self) -> None:
        """Set up the Android environment for task execution"""
        self.logger.debug("Setting up Android environment")

        # Create Android instance
        self.android = Android()

        # Start emulator
        self.logger.info("Starting emulator")
        # self.android.start_emulator(self.task.config.device_id, self.task.config.no_window) # TODO arrumar ...... foi assim que o claude gerou
        self.android.start_emulator("RVSec", self.task.config.no_window)
        self._publish_event(EventType.EMULATOR_STARTED, {"device_id": self.task.config.device_id})

        # Install app if needed
        if not self.task.config.skip_installation:
            self.logger.info(f"Installing app {self.task.app.name}")
            self.android.install_with_permissions(self.task.app)
            self._publish_event(EventType.APP_INSTALLED, {"app_name": self.task.app.name})

    def _start_logcat_capture(self) -> None:
        """Start capturing logcat output"""
        self.logger.debug("Starting logcat capture")

        # Clear logcat buffer if requested
        if self.task.config.clean_logcat:
            clear_cmd = Command("adb", ["logcat", "-c"])
            clear_cmd.invoke()

        # Start logcat capture process
        logcat_cmd = Command("adb", ["logcat", "-v", "threadtime", "-s", "RVSEC", "RVSEC-COV"])

        with open(self.task.result.logcat_file, "wb") as log_file:
            self.logcat_process = logcat_cmd.invoke_as_deamon(stdout=log_file)

    def _execute_tool(self) -> None:
        """Execute the tool implementation"""
        self.logger.info(f"Executing tool: {self.tool.name}")
        self._publish_event(EventType.TOOL_STARTED, {"tool_name": self.tool.name})

        # Execute the tool with the task
        self.tool.execute(self.task, self.task.app)

        self._publish_event(EventType.TOOL_STOPPED, {"tool_name": self.tool.name})

    def _cleanup_environment(self) -> None:
        """Clean up the environment after execution"""
        self.logger.debug("Cleaning up environment")

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

# rv_platform/components/tool_execution.py
"""
Tool execution component for rv-platform.

This component handles tool invocation and result processing in a simplified,
standalone manner suitable for the platform architecture.
"""

from typing import Any, Dict

from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import (
    CONTEXT_APP_NAME,
    CONTEXT_TASK_ID,
    CONTEXT_TOOL_NAME,
    LOG_COMPLETE,
    LOG_ERROR,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager


class ToolExecutionComponent:
    """
    Component responsible for managing tool execution.
    Handles tool invocation and result processing.

    ### Architectural Decisions:
    - Encapsulates tool execution functionality
    - Implements clear separation of concerns for task execution
    - Provides focused error handling for tool operations

    ### Role in the System:
    - Manages testing tool execution during tasks
    - Reports tool lifecycle via logging
    - Ensures proper process cleanup after execution
    """

    def __init__(self, task: Task, tool: AbstractTool):
        """Initialize with task and tool."""
        self.name = "ToolExecutionComponent"
        self.task = task
        self.tool = tool

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_platform.components.tool_execution",
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: task.config.apk_name,
                CONTEXT_TOOL_NAME: tool.name,
            },
        )

        # Error handler
        self.error_handler = ErrorHandler.get_instance()

    def initialize(self, context: Dict[str, Any]) -> bool:
        """
        Initialize the component.

        Args:
            context: Task execution context

        Returns:
            True if initialization was successful
        """
        self.logger.debug(f"Initializing {self.name}")
        return True

    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the testing tool for the task.

        Args:
            context: Task execution context

        Returns:
            True if tool execution was successful
        """
        return self.run_tool()

    def cleanup(self, context: Dict[str, Any]) -> None:
        """
        Clean up component resources.

        Args:
            context: Task execution context
        """
        self.cleanup_processes()

    def run_tool(self) -> bool:
        """
        Execute the tool on the current task.

        Returns:
            Success status
        """
        try:
            self.logger.info(LOG_START.format(phase=f"tool: {self.tool.name}"))
            self.logger.info(f"Tool started: {self.tool.name} for task {self.task.id}")

            # Dispatch to the tool's execute() method. This is a blocking call
            # that runs the tool for the configured timeout duration. Each tool
            # type (MonkeyTool, DroidbotTool, RVAgentTool) implements execute()
            # differently, but all interact with the emulator through ADB and
            # raise RVToolTimeoutError when the timeout expires.
            self.tool.execute(self.task, self.task.app)
            self.logger.info(LOG_COMPLETE.format(phase=f"tool: {self.tool.name}"))
            self.logger.info(f"Tool stopped: {self.tool.name} for task {self.task.id}")

            return True

        except Exception as e:
            # Check if this is a timeout exception (already logged)
            from rv_android_core.util.error.exceptions import RVToolTimeoutError

            if isinstance(e, RVToolTimeoutError):
                # Timeout is EXPECTED behavior in bounded-time experiments. The
                # tool ran for the configured duration and was interrupted — this
                # counts as a successful execution. Coverage and MOP violation
                # data collected up to the timeout point are valid results.
                self.logger.info(
                    LOG_COMPLETE.format(phase=f"tool: {self.tool.name} (timeout)")
                )
                self.logger.info(
                    f"Tool stopped: {self.tool.name} for task {self.task.id} (timeout)"
                )

                return True
            else:
                # Actual failure - reduced logging (tool already logged the details)
                self.logger.error(
                    LOG_ERROR.format(
                        phase=f"executing tool {self.tool.name}", error=str(e)
                    )
                )

                self.logger.error(f"Task failed: {self.task.id}")

                return False

    def cleanup_processes(self) -> None:
        """Clean up any hanging processes related to the tool."""
        # Some tools (DroidBot, RVSmart) spawn child processes that may survive
        # after the tool's main process exits. Each tool defines a process_pattern
        # regex (e.g., "droidbot" or "app_process") used to pkill lingering
        # processes. This prevents resource leaks across consecutive tasks.
        if hasattr(self.tool, "process_pattern") and self.tool.process_pattern:
            try:
                self.logger.debug(
                    LOG_START.format(
                        phase=f"cleaning up processes for tool: {self.tool.name}"
                    )
                )
                self.tool.kill_related_processes(self.tool.process_pattern)
                self.logger.debug(
                    LOG_COMPLETE.format(
                        phase=f"cleaning up processes for tool: {self.tool.name}"
                    )
                )
            except Exception as e:
                self.logger.warning(
                    LOG_ERROR.format(
                        phase=f"cleaning up processes for tool: {self.tool.name}",
                        error=str(e),
                    )
                )

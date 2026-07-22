"""
Abstract base class for all testing tools in the RV-Android framework.

This module defines the core contract and template method pattern for
monitored operations testing tools.
"""

import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    pass

from rv_android_core.commands.command import Command
from rv_android_core.commands.command_result import CommandResult
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import (
    RVCommandTimeoutError,
    RVToolExecutionError,
    RVToolTimeoutError,
)
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, CONTEXT_TOOL_NAME
from rv_android_core.util.logging.manager import LoggingManager


class AbstractTool(ABC):
    """
    Base class defining the contract and template method for testing tools.

    ### Architectural Decisions:
    - Template method pattern: execute() orchestrates the workflow, subclasses
      implement execute_tool_specific_logic() for custom behavior.
    - Variant system: get_variants() provides named parameter presets that
      ToolFactory resolves during tool creation.
    - Timeout conversion: RVCommandTimeoutError from Command is converted to
      RVToolTimeoutError for uniform handling by the platform.

    ### Role in the System:
    - Foundational abstraction for all testing tools (Monkey, DroidBot, APE-RV, etc.)
    - Registered in ToolRegistry via get_tool_spec() for dynamic discovery
    - Executed by ToolExecutionComponent during task processing

    ### Integration Points:
    - Configured by ToolFactory with resolved variant parameters
    - Uses Command infrastructure for subprocess execution
    - Integrates with ErrorHandler and LoggingManager from rv-android-core
    - Provides process cleanup via ADB for device-side processes
    """

    def __init__(self, name: str, description: str, process_pattern: str):
        """
        Initialize the abstract tool with identity, logging, and error handling.

        Args:
            name: Unique tool identifier (e.g., "monkey", "droidbot", "aperv")
            description: Human-readable tool description
            process_pattern: Pattern for identifying device-side processes to kill on cleanup

        State:
            self.name: Tool identifier used in logging, registry, and result tracking.
            self.description: Human-readable description for diagnostics.
            self.process_pattern: grep pattern for ADB process cleanup after execution.
            self.logger: Contextualized logger with tool name in structured fields.
            self.error_handler: Singleton ErrorHandler instance for error management.
        """
        self.name = name
        self.description = description
        self.process_pattern = process_pattern

        # Set up standardized logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"rv_tools.builtin.{name}",
            {CONTEXT_COMPONENT: f"{name.title()}Tool", CONTEXT_TOOL_NAME: name},
        )

        # Initialize error handler
        self.error_handler = ErrorHandler.get_instance()

        super().__init__()

    @classmethod
    @abstractmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Return available variant configurations for this tool.

        Must include at least a 'default' variant. Each variant maps a name
        to a dictionary of tool-specific parameters used by ToolFactory
        during configuration resolution.

        Returns:
            Dictionary mapping variant names to parameter dictionaries.

        Example::

            {
                "default": {"policy": "dfs_naive", "timeout": 300},
                "greedy": {"policy": "dfs_greedy", "count": 5000, "timeout": 600},
            }
        """

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure tool with resolved variant parameters.

        Receive the final configuration dictionary (variant defaults merged
        with experiment overrides) and store parameters as instance state.
        Do not perform heavy operations here -- defer to execution phase.

        Args:
            config: Configuration dictionary with tool-specific parameters

        Raises:
            ConfigurationError: If configuration is invalid or incomplete
        """

    @classmethod
    @abstractmethod
    def get_tool_spec(cls):
        """
        Get tool specification for registration.

        This method must be implemented by all tools to provide
        specification information for registry registration.

        Returns:
            ToolSpec instance with tool metadata
        """

    @abstractmethod
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute tool-specific testing logic.

        This is the main extension point that every tool implementation must provide.
        It should contain the core testing logic specific to each tool.

        Args:
            task: Task configuration and context (can be Task or task_model.Task)
            app: Application under test

        Raises:
            NotImplementedError: If not implemented by subclass
        """

    def execute(self, task: Task, app: App) -> None:
        """
        Execute the tool using template method pattern with unified error handling.

        This method implements the standard execution workflow that delegates
        to the abstract method for tool-specific logic, then performs cleanup.
        Provides centralized timeout and error handling for all tools.

        ### Execution Workflow:
        1. Log tool execution start
        2. Delegate to tool-specific logic implementation
        3. Handle command timeouts and convert to tool timeouts
        4. Perform process cleanup and resource management
        5. Handle any errors that occur during execution
        6. Log success only if no exceptions occurred

        Args:
            task: Task configuration and context
            app: Application under test
        """

        try:
            # Phase 1: Execute tool-specific logic (subclass implementation)
            self.logger.info(f"Executing monitored operations tool: {self.name}")
            self.logger.debug(f"Tool description: {self.description}")
            self.execute_tool_specific_logic(task, app)

            # Phase 2: Cleanup device-side processes spawned by the tool
            self.kill_related_processes(self.process_pattern)

            self.logger.info(f"Tool {self.name} execution completed successfully")

        except RVCommandTimeoutError as e:
            # RVCommandTimeoutError (from Command.invoke) is an infrastructure-level
            # exception. Convert to RVToolTimeoutError so the platform layer can
            # handle all tool timeouts uniformly without knowing about Command internals.
            timeout_msg = (
                f"{self.name} execution timed out after {e.timeout_seconds} seconds"
            )
            self.logger.info(f"Tool timeout detected: {timeout_msg}")

            # Raise tool timeout exception (handled gracefully by error handler)
            raise RVToolTimeoutError(
                timeout_msg,
                tool_name=self.name,
                timeout_seconds=e.timeout_seconds,
                cause=e,
            )

        except Exception:
            # Re-raise to caller (ToolExecutionComponent) — @handle_errors on
            # execute_tool_specific_logic already logged the first entry
            raise

    def _execute_and_check_command(
        self, command: Command, stdout=None, stderr=None, stdin=None
    ) -> CommandResult:
        """
        Execute command with unified error handling.

        This method centralizes all command execution logic providing consistent
        behavior across all tools. It handles timeout conversion and failure
        detection for tool command execution.

        ### Command Execution Strategy:
        1. Execute command using Command infrastructure with timeout handling
        2. Check result.is_failure() and raise RVToolExecutionError for failures
        3. Convert command timeouts to tool-level timeout exceptions
        4. Provide detailed error context for debugging and trace file logging

        Args:
            command: Command instance to execute
            stdout: Where to redirect standard output (default: PIPE)
            stderr: Where to redirect standard error (default: PIPE)
            stdin: Input to pass to the command (default: None)

        Returns:
            CommandResult on successful execution

        Raises:
            RVToolTimeoutError: When command times out (converted from RVCommandTimeoutError)
            RVToolExecutionError: When command fails with non-zero exit code
        """
        try:
            # Execute command - may raise RVCommandTimeoutError
            result = command.invoke(stdout=stdout, stderr=stderr, stdin=stdin)

            # Check for command failure
            if result.is_failure():
                error_msg = f"{self.name} command failed with exit code {result.code}"
                if result.has_error_output():
                    error_msg += f". Error output: {result.get_stderr_text()}"

                # Log error details for debugging
                self.logger.error(f"Command execution failed: {error_msg}")

                raise RVToolExecutionError(error_msg, tool_name=self.name, cause=None)

            return result

        except RVCommandTimeoutError as e:
            timeout_msg = (
                f"{self.name} execution timed out after {e.timeout_seconds} seconds"
            )
            self.logger.info(
                f"Tool timeout detected during command execution: {timeout_msg}"
            )

            raise RVToolTimeoutError(
                timeout_msg,
                tool_name=self.name,
                timeout_seconds=e.timeout_seconds,
                cause=e,
            )

    def kill_related_processes(self, process_pattern: str) -> None:
        """
        Terminate processes related to this tool for cleanup.

        This method identifies and kills processes that match the given pattern
        to ensure clean tool termination and prevent resource leaks.

        Args:
            process_pattern: Pattern to match processes for termination
        """
        if not process_pattern:
            self.logger.debug("No process pattern specified, skipping process cleanup")
            return

        try:
            self.logger.debug(
                f"Cleaning up processes matching pattern: {process_pattern}"
            )

            # Run "ps | grep" inside the device shell to find tool-related processes.
            # The pipe runs on-device (adb shell), not on the host.
            get_processes_cmd = Command(
                "adb", ["shell", "ps", "|", "grep", process_pattern]
            )

            get_processes_result = get_processes_cmd.invoke()

            if not get_processes_result.stdout:
                self.logger.debug("No matching processes found for cleanup")
                return

            # Parse ps output: second token in each line is the PID (Android ps format)
            killed_count = 0
            for line in get_processes_result.stdout.decode("ascii").split(os.linesep):
                line = line.strip()
                if line:
                    tokens = line.split()
                    if len(tokens) >= 2:
                        process_id = tokens[1]
                        try:
                            kill_process_cmd = Command(
                                "adb", ["shell", "kill", process_id]
                            )
                            kill_process_cmd.invoke()
                            killed_count += 1
                            self.logger.debug(f"Killed process {process_id}")
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to kill process {process_id}: {str(e)}"
                            )

            if killed_count > 0:
                self.logger.info(f"Cleaned up {killed_count} related processes")

        except Exception as e:
            self.logger.warning(f"Error during process cleanup: {str(e)}")
            # Don't raise here as cleanup errors shouldn't fail the main execution

    def get_tool_info(self) -> dict:
        """
        Get tool information and metadata.

        Returns:
            Dictionary containing tool name, description, and process pattern
        """
        return {
            "name": self.name,
            "description": self.description,
            "process_pattern": self.process_pattern,
        }

    def __str__(self) -> str:
        """String representation of the tool."""
        return f"{self.__class__.__name__}(name='{self.name}', description='{self.description}')"

    def __repr__(self) -> str:
        """Detailed string representation of the tool."""
        return (
            f"{self.__class__.__name__}(name='{self.name}', "
            f"description='{self.description}', process_pattern='{self.process_pattern}')"
        )

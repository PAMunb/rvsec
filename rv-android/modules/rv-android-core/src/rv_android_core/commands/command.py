# rvandroid/commands/command.py - Pydantic v2 migrated version

import os
import signal
from subprocess import PIPE, Popen, TimeoutExpired
from typing import List, Optional

import psutil
from pydantic import ConfigDict, Field, field_validator
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import (
    CommandValidationError,
    RVCommandTimeoutError,
)
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_COMPLETE,
    LOG_ERROR,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model

from .command_not_found_error import CommandNotFoundError
from .command_result import CommandResult


def kill_process_tree(pid: int):
    """
    Recursively kill a process and all its children.

    Args:
        pid (int): Process ID of the parent process to kill
    """
    try:
        parent = psutil.Process(pid)

        # Kill all child processes
        for child in parent.children(recursive=True):
            try:
                os.kill(child.pid, signal.SIGKILL)
            except OSError:
                # Process might already be gone
                pass

        # Kill the parent process
        os.kill(parent.pid, signal.SIGKILL)
    except (psutil.NoSuchProcess, OSError):
        # Process might already be gone
        pass


@validated_model(["command", "args", "timeout"])
class Command(BaseValidatedModel):
    """
    Execute system commands with timeout enforcement, process management, and validation.

    ### Role in the System:
    - Uniform interface for shell commands, ADB operations, and tool invocations
      across all RV-Android modules.

    ### Key Features:
    - Synchronous execution with timeout (invoke)
    - Daemon execution without blocking (invoke_as_deamon)
    - Process-group execution for parallel environments (invoke_as_process)
    - Recursive process tree termination on timeout via kill_process_tree
    - Pydantic validation for command, args, and timeout fields

    ### Integration Points:
    - Used by AbstractTool for tool command execution
    - Used by Android utilities (ADB install, emulator management, logcat)
    - Returns CommandResult for uniform output/error processing
    """

    model_config = ConfigDict(
        # Allow logger object as arbitrary type
        arbitrary_types_allowed=True,
        # Validate assignments for runtime safety
        validate_assignment=True,
    )

    command: str = Field(description="The command to execute")

    args: List[str] = Field(
        default_factory=list, description="List of command arguments"
    )

    timeout: Optional[float] = Field(
        default=None, description="Timeout in seconds for command execution"
    )

    @field_validator("command")
    @classmethod
    def validate_command(cls, v):
        """Validate command using system exceptions."""
        if not v or not isinstance(v, str) or len(v.strip()) == 0:
            raise CommandValidationError(
                "Command must be a non-empty string", field_name="command"
            )
        return v.strip()

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v):
        """Validate timeout using system exceptions."""
        if v is not None:
            if not isinstance(v, (int, float)):
                raise CommandValidationError(
                    "Timeout must be a number", field_name="timeout"
                )
            if v < 0:
                raise CommandValidationError(
                    "Timeout must be non-negative", field_name="timeout"
                )
        return v

    @field_validator("args")
    @classmethod
    def validate_args(cls, v):
        """Validate arguments using system exceptions."""
        if v is None:
            return []
        if not isinstance(v, list):
            raise CommandValidationError("Arguments must be a list", field_name="args")
        for i, arg in enumerate(v):
            if not isinstance(arg, str):
                raise CommandValidationError(
                    f"Argument at position {i} must be a string", field_name="args"
                )
        return v

    def model_post_init(self, __context):
        """Initialize logger and error handler after Pydantic validation.

        Use object.__setattr__ to bypass Pydantic's validate_assignment
        for non-model attributes (logger, error_handler).
        """
        # object.__setattr__ is required because validate_assignment=True in model_config
        # causes Pydantic to intercept normal attribute assignment and reject non-Field
        # attributes like logger and error_handler.
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_android_core.commands.command", {CONTEXT_COMPONENT: "Command"}
        )
        object.__setattr__(self, "logger", logger)

        error_handler = ErrorHandler.get_instance()
        object.__setattr__(self, "error_handler", error_handler)

    def invoke(self, stdout=PIPE, stderr=PIPE, stdin=None) -> CommandResult:
        """
        Execute the command and wait for completion.

        Args:
            stdout: Where to redirect standard output (default: PIPE)
            stderr: Where to redirect standard error (default: PIPE)
            stdin: Input to pass to the command (default: None)

        Returns:
            CommandResult: Object containing execution results

        Raises:
            CommandNotFoundError: If the command is not found
            TimeoutExpired: If the command exceeds timeout
        """
        cmd_args = [self.command, *self.args]
        cmd_str = " ".join(cmd_args)

        with self.logger.with_context(command=cmd_str, timeout=self.timeout):
            self.logger.debug(LOG_START.format(phase=f"command: {cmd_str}"))

            # Normalize stdin if it's a string
            if isinstance(stdin, str):
                stdin = stdin.encode()

            try:
                # Popen without shell=True to avoid shell injection and enable
                # reliable process tree cleanup via kill_process_tree().
                proc = Popen(cmd_args, stderr=stderr, stdout=stdout)
                stdout_data, stderr_data = proc.communicate(stdin, timeout=self.timeout)

                # Log command completion with exit code
                if proc.returncode != 0:
                    self.logger.warning(
                        f"Command failed with exit code {proc.returncode}: {cmd_str}",
                        extra={
                            "command": self.command,
                            "command_args": self.args,
                            "exit_code": proc.returncode,
                            "timeout": self.timeout,
                        },
                    )
                else:
                    self.logger.debug(
                        LOG_COMPLETE.format(
                            phase=f"command with exit code {proc.returncode}"
                        )
                    )

                return CommandResult(proc.returncode, stdout_data, stderr_data)

            except TimeoutExpired:
                self.logger.warning(f"Command timed out after {self.timeout} seconds")
                self.kill_process(proc)

                # Raise timeout exception with detailed context
                raise RVCommandTimeoutError(
                    f"Command '{cmd_str}' timed out after {self.timeout} seconds",
                    timeout_seconds=self.timeout,
                    command=cmd_str,
                )

            except OSError as e:
                self.logger.error(
                    LOG_ERROR.format(phase=f"executing command {cmd_str}", error=str(e))
                )
                raise CommandNotFoundError(f"The command {self.command} was not found")

    def kill_process(self, p):
        """
        Kill a process when timeout occurs.
        Uses kill_process_tree to ensure all child processes are terminated.

        Args:
            p: Process object to kill
        """
        self.logger.warning(f"The command has timed out after {self.timeout} seconds")
        try:
            kill_process_tree(p.pid)
        except Exception as e:
            self.logger.error(f"Error killing process {p.pid}: {str(e)}")

    def invoke_as_deamon(self, stdout=PIPE, stderr=PIPE):
        """
        Execute the command as a daemon process.

        Starts the command in a separate non-blocking process and returns the
        process object without waiting for completion.

        Args:
            stdout: Where to redirect standard output (default: PIPE)
            stderr: Where to redirect standard error (default: PIPE)

        Returns:
            Process: The created process object

        Raises:
            CommandNotFoundError: If the command is not found
        """
        cmd_args = [self.command, *self.args]
        cmd_str = " ".join(cmd_args)

        with self.logger.with_context(command=cmd_str):
            self.logger.debug(LOG_START.format(phase=f"daemon command: {cmd_str}"))

            try:
                process = Popen(cmd_args, stderr=stderr, stdout=stdout)
                self.logger.debug(f"Started daemon process with PID: {process.pid}")
                return process
            except OSError as e:
                self.logger.error(
                    LOG_ERROR.format(
                        phase=f"starting daemon process for command {cmd_str}",
                        error=str(e),
                    )
                )
                raise CommandNotFoundError(f"The command {self.command} was not found")

    def invoke_as_process(self, stdout=PIPE, stderr=PIPE):
        """
        Execute the command as a single process without daemon fork.

        Alternative to invoke_as_deamon that uses subprocess.Popen directly
        without creating daemon/fork processes that can cause duplication.

        This method prevents process duplication issues seen with invoke_as_deamon
        in parallel execution environments by using subprocess with process groups
        for proper cleanup.

        Args:
            stdout: Where to redirect standard output (default: PIPE)
            stderr: Where to redirect standard error (default: PIPE)

        Returns:
            Process: The created process object

        Raises:
            CommandNotFoundError: If the command is not found
        """
        import os

        cmd_args = [self.command, *self.args]
        cmd_str = " ".join(cmd_args)

        with self.logger.with_context(command=cmd_str):
            self.logger.debug(LOG_START.format(phase=f"process command: {cmd_str}"))

            try:
                # os.setsid creates a new process group so that the entire subtree
                # can be killed with os.killpg() instead of chasing individual PIDs.
                # This prevents orphan processes when running tools in parallel.
                process = Popen(
                    cmd_args,
                    stderr=stderr,
                    stdout=stdout,
                    preexec_fn=os.setsid,
                )
                self.logger.debug(f"Started single process with PID: {process.pid}")
                return process
            except OSError as e:
                self.logger.error(
                    LOG_ERROR.format(
                        phase=f"starting single process for command {cmd_str}",
                        error=str(e),
                    )
                )
                raise CommandNotFoundError(f"The command {self.command} was not found")

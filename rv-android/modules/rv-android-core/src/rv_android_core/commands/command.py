# rvandroid/commands/command.py - Pydantic v2 migrated version

import os
import signal
import sys
from subprocess import PIPE, Popen
from threading import Timer
from typing import List, Optional, Any

import psutil
from pydantic import Field, ConfigDict, field_validator, ValidationError as PydanticValidationError

# Import TimeoutExpired for Python 3.3+
if sys.version_info.major == 3 and sys.version_info.minor >= 3:
    from subprocess import TimeoutExpired

from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.exceptions import CommandValidationError
from rv_android_core.util.error.error_handler import ErrorHandler
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


@validated_model(['command', 'args', 'timeout'])
class Command(BaseValidatedModel):
    """
    A system command execution utility with process management and error handling capabilities.

    ### Architectural Decisions:
    - Inherits from BaseValidatedModel for comprehensive validation and type safety
    - Implements flexible and secure approach to system command execution
    - Provides validated handling of command invocation and result processing
    - Supports timeout enforcement and process tree management with validated parameters
    - Ensures consistent output and error capturing across different command scenarios

    ### Role in the System:
    - Acts as a utility for executing system commands across the RV-Android framework
    - Abstracts low-level command execution complexities with type-safe parameters
    - Provides a uniform interface for invoking shell commands, ADB operations, and tool interactions
    - Manages process lifecycle, including timeout handling and clean termination
    - Enables reliable and predictable command execution in testing and automation workflows

    ### Key Considerations:
    - Handles cross-platform command execution challenges
    - Implements process management and termination strategies
    - Supports multiple execution modes (synchronous and daemon)
    - Provides error handling and reporting with comprehensive logging integration
    - Ensures secure and controlled command invocation with validated inputs

    ### Integration Strategy:
    - Integrated with Android testing and instrumentation tools
    - Compatible with various system command scenarios
    - Supports flexible timeout and process management configurations
    - Enables command execution across different modules
    - Provides result object for consistent processing

    ### Performance and Scalability:
    - Designed for efficient and lightweight command execution
    - Minimizes resource overhead during command processing
    - Supports timeout mechanisms to prevent long-running commands
    - Implements recursive process tree termination for cleanup
    - Adaptable to different command complexity and system environments

    ### Validation Features:
    - Command string validation to prevent empty commands
    - Argument list validation for proper parameter passing
    - Timeout value validation to ensure positive values
    - Type safety for all command execution parameters
    """

    model_config = ConfigDict(
        # Allow logger object as arbitrary type
        arbitrary_types_allowed=True,
        # Validate assignments for runtime safety
        validate_assignment=True,
    )

    command: str = Field(
        description="The command to execute"
    )
    
    args: List[str] = Field(
        default_factory=list,
        description="List of command arguments"
    )
    
    timeout: Optional[float] = Field(
        default=None,
        description="Timeout in seconds for command execution"
    )

    @field_validator('command')
    @classmethod
    def validate_command(cls, v):
        """Validate command using system exceptions."""
        if not v or not isinstance(v, str) or len(v.strip()) == 0:
            raise CommandValidationError(
                "Command must be a non-empty string",
                field_name="command"
            )
        return v.strip()

    @field_validator('timeout')
    @classmethod  
    def validate_timeout(cls, v):
        """Validate timeout using system exceptions."""
        if v is not None:
            if not isinstance(v, (int, float)):
                raise CommandValidationError(
                    "Timeout must be a number",
                    field_name="timeout" 
                )
            if v < 0:
                raise CommandValidationError(
                    "Timeout must be non-negative",
                    field_name="timeout"
                )
        return v

    @field_validator('args')
    @classmethod
    def validate_args(cls, v):
        """Validate arguments using system exceptions."""
        if v is None:
            return []
        if not isinstance(v, list):
            raise CommandValidationError(
                "Arguments must be a list",
                field_name="args"
            )
        for i, arg in enumerate(v):
            if not isinstance(arg, str):
                raise CommandValidationError(
                    f"Argument at position {i} must be a string",
                    field_name="args"
                )
        return v

    def model_post_init(self, __context):
        """Initialize logging and error handling after model validation."""
        # Use object.__setattr__ to bypass Pydantic validation for logger
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "commands.command",
            {CONTEXT_COMPONENT: "Command"}
        )
        object.__setattr__(self, 'logger', logger)
        
        # Initialize error handler for integrated error management
        error_handler = ErrorHandler.get_instance()
        object.__setattr__(self, 'error_handler', error_handler)

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
        cmd_str = ' '.join(cmd_args)

        with self.logger.with_context(command=cmd_str, timeout=self.timeout):
            self.logger.debug(LOG_START.format(phase=f"command: {cmd_str}"))

            # Normalize stdin if it's a string
            if isinstance(stdin, str):
                stdin = stdin.encode()

            # Python 3.3+ has built-in timeout support
            if sys.version_info.major == 3 and sys.version_info.minor >= 3:
                try:
                    proc = Popen(cmd_args, stderr=stderr, stdout=stdout)
                    stdout_data, stderr_data = proc.communicate(stdin, timeout=self.timeout)

                    self.logger.debug(LOG_COMPLETE.format(
                        phase=f"command with exit code {proc.returncode}"
                    ))

                    return CommandResult(proc.returncode, stdout_data, stderr_data)

                except TimeoutExpired:
                    self.logger.warning(f"Command timed out after {self.timeout} seconds")
                    self.kill_process(proc)
                    stdout_data, stderr_data = proc.communicate()

                    return CommandResult(proc.returncode, stdout_data, stderr_data)

                except OSError as e:
                    self.logger.error(LOG_ERROR.format(
                        phase=f"executing command {cmd_str}",
                        error=str(e)
                    ))
                    raise CommandNotFoundError(f"The command {self.command} was not found")

            else:
                # Legacy Python support
                try:
                    proc = Popen(cmd_args, stderr=stderr, stdout=stdout)

                    # Setup timer for timeout if specified
                    if self.timeout is not None:
                        timer = Timer(self.timeout, self.kill_process, [proc])
                        timer.start()

                    stdout_data, stderr_data = proc.communicate(stdin)

                    # Cancel timer if it's still running
                    if self.timeout is not None:
                        timer.cancel()

                    self.logger.debug(LOG_COMPLETE.format(
                        phase=f"command with exit code {proc.returncode}"
                    ))

                    return CommandResult(proc.returncode, stdout_data, stderr_data)

                except OSError as e:
                    self.logger.error(LOG_ERROR.format(
                        phase=f"executing command {cmd_str}",
                        error=str(e)
                    ))
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
        cmd_str = ' '.join(cmd_args)

        with self.logger.with_context(command=cmd_str):
            self.logger.debug(LOG_START.format(phase=f"daemon command: {cmd_str}"))

            try:
                process = Popen(cmd_args, stderr=stderr, stdout=stdout)
                self.logger.debug(f"Started daemon process with PID: {process.pid}")
                return process
            except OSError as e:
                self.logger.error(LOG_ERROR.format(
                    phase=f"starting daemon process for command {cmd_str}",
                    error=str(e)
                ))
                raise CommandNotFoundError(f"The command {self.command} was not found")
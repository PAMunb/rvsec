# rvandroid/commands/command.py
import os
import signal
import sys
from subprocess import PIPE, Popen
from threading import Timer

import psutil

# Import TimeoutExpired for Python 3.3+
if sys.version_info.major == 3 and sys.version_info.minor >= 3:
    from subprocess import TimeoutExpired

from rvandroid.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rvandroid.util.logging.manager import LoggingManager
from .command_not_found_error import CommandNotFoundError
from .command_result import CommandResult


def kill_process_tree(pid: int):
    """
    Recursively kill a process and all its children.

    Args:
        pid (int): Process ID of the parent process to kill
    """
    parent = psutil.Process(pid)

    # Kill all child processes
    for child in parent.children(recursive=True):
        os.kill(child.pid, signal.SIGKILL)

    # Kill the parent process
    os.kill(parent.pid, signal.SIGKILL)


class Command:
    """
    A robust system command execution utility with comprehensive process management and error handling capabilities.

    ### Architectural Decisions:
    - Implements a flexible and secure approach to system command execution
    - Provides standardized handling of command invocation and result processing
    - Supports timeout enforcement and process tree management
    - Ensures consistent output and error capturing across different command scenarios

    ### Role in the System:
    - Acts as a critical utility for executing system commands across the RV-Android framework
    - Abstracts low-level command execution complexities
    - Provides a uniform interface for invoking shell commands, ADB operations, and tool interactions
    - Manages process lifecycle, including timeout handling and clean termination
    - Enables reliable and predictable command execution in testing and automation workflows

    ### Key Considerations:
    - Handles cross-platform command execution challenges
    - Implements robust process management and termination strategies
    - Supports multiple execution modes (synchronous and daemon)
    - Provides comprehensive error handling and reporting
    - Ensures secure and controlled command invocation

    ### Integration Strategy:
    - Deeply integrated with Android testing and instrumentation tools
    - Compatible with various system command scenarios
    - Supports flexible timeout and process management configurations
    - Enables seamless command execution across different modules
    - Provides standardized result object for consistent processing

    ### Performance and Scalability:
    - Designed for efficient and lightweight command execution
    - Minimizes resource overhead during command processing
    - Supports timeout mechanisms to prevent long-running commands
    - Implements recursive process tree termination for comprehensive cleanup
    - Adaptable to different command complexity and system environments
    """

    def __init__(self, command: str, args: list = None, timeout: float = None):
        """
        Initialize Command with execution parameters.

        Args:
            command (str): The command to execute
            args (list): List of command arguments
            timeout (float): Timeout in seconds for command execution
        """
        # Set up logging using LoggingManager
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "commands.command",
            {CONTEXT_COMPONENT: "Command"}
        )

        self._command = command
        self._args = args or []
        self._timeout = timeout

    @property
    def command(self) -> str:
        """Return the command string"""
        return self._command

    @command.setter
    def command(self, value: str):
        """Set the command string"""
        self._command = value

    @property
    def args(self) -> list:
        """Return the command arguments"""
        return self._args

    @args.setter
    def args(self, value: list):
        """Set the command arguments"""
        self._args = value

    @property
    def timeout(self) -> float:
        """Return the command timeout"""
        return self._timeout

    @timeout.setter
    def timeout(self, value: float):
        """Set the command timeout"""
        self._timeout = value

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
        cmd_args = [self._command, *self._args]
        cmd_str = ' '.join(cmd_args)

        with self.logger.with_context(command=cmd_str, timeout=self._timeout):
            self.logger.debug(LOG_START.format(operation=f"command: {cmd_str}"))

            if sys.version_info.major == 3 and sys.version_info.minor >= 3:
                try:
                    proc = Popen(cmd_args, stderr=stderr, stdout=stdout)
                    stdout, stderr = proc.communicate(stdin, timeout=self._timeout)
                    self.logger.debug(LOG_COMPLETE.format(operation=f"command with exit code {proc.returncode}"))
                    return CommandResult(proc.returncode, stdout, stderr)
                except TimeoutExpired:
                    self.kill_process(proc)
                    stdout, stderr = proc.communicate(stdin)
                    self.logger.warning(f"Command timed out after {self._timeout} seconds")
                    return CommandResult(proc.returncode, stdout, stderr)
                except OSError as e:
                    self.logger.error(LOG_ERROR.format(
                        operation=f"executing command {cmd_str}",
                        error=str(e)
                    ))
                    raise CommandNotFoundError(f"The command {self._command} was not found")
            else:
                # Legacy Python support
                try:
                    proc = Popen(cmd_args, stderr=PIPE, stdout=PIPE)
                    if self._timeout is not None:
                        timer = Timer(self._timeout, self.kill_process, [proc])
                        timer.start()

                    stdout, stderr = proc.communicate(stdin)
                    if self._timeout is not None:
                        timer.cancel()

                    self.logger.debug(LOG_COMPLETE.format(operation=f"command with exit code {proc.returncode}"))
                    return CommandResult(proc.returncode, stdout, stderr)
                except OSError as e:
                    self.logger.error(LOG_ERROR.format(
                        operation=f"executing command {cmd_str}",
                        error=str(e)
                    ))
                    raise CommandNotFoundError(f"The command {self._command} was not found")

    def kill_process(self, p):
        """
        Kill a process when timeout occurs.

        Args:
            p: Process object to kill
        """
        self.logger.warning(f"The command has timed out after {self._timeout} seconds")
        kill_process_tree(p.pid)

    def invoke_as_deamon(self, stdout=PIPE, stderr=PIPE):
        """
        Execute the command as a daemon process.

        Args:
            stdout: Where to redirect standard output (default: PIPE)
            stderr: Where to redirect standard error (default: PIPE)

        Returns:
            Process: The created process object

        Raises:
            CommandNotFoundError: If the command is not found
        """
        cmd_args = [self._command, *self._args]
        cmd_str = ' '.join(cmd_args)

        with self.logger.with_context(command=cmd_str):
            self.logger.debug(LOG_START.format(operation=f"daemon command: {cmd_str}"))

            try:
                process = Popen(cmd_args, stderr=stderr, stdout=stdout)
                self.logger.debug(f"Started daemon process with PID: {process.pid}")
                return process
            except OSError as e:
                self.logger.error(LOG_ERROR.format(
                    operation=f"starting daemon process for command {cmd_str}",
                    error=str(e)
                ))
                raise CommandNotFoundError(f"The command {self._command} was not found")

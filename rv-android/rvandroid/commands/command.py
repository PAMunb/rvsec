import logging as logging_api
import os
import signal
import sys
from subprocess import PIPE, Popen
from threading import Timer

import psutil

# Import TimeoutExpired for Python 3.3+
if sys.version_info.major == 3 and sys.version_info.minor >= 3:
    from subprocess import TimeoutExpired

from .command_not_found_error import CommandNotFoundError
from .command_result import CommandResult

# Configure logging
logging = logging_api.getLogger(__name__)


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
    The Command class provides an abstraction for executing system commands
    within the rvandroid framework. It is designed to standardize command execution,
    handling output, errors, and timeouts in a controlled manner.

    ### Architectural Decisions:
    - Uses subprocess calls to execute system commands securely.
    - Implements output capturing to facilitate debugging and logging.
    - Supports timeout enforcement to prevent long-running or stuck processes.

    ### Role in the System:
    - Acts as a utility for executing ADB, emulator, and analysis-related commands.
    - Ensures consistent handling of command execution across different modules.
    - Provides error reporting mechanisms to detect failures and log execution results.
    - Facilitates automation by integrating with experiment workflows and instrumentation tools.
    """

    def __init__(self, command: str, args: list = None, timeout: float = None):
        """
        Initialize Command with execution parameters.
        
        Args:
            command (str): The command to execute
            args (list): List of command arguments
            timeout (float): Timeout in seconds for command execution
        """
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
        logging.debug('Command executed: {0}'.format(' '.join(cmd_args)))

        if sys.version_info.major == 3 and sys.version_info.minor >= 3:
            try:
                proc = Popen(cmd_args, stderr=stderr, stdout=stdout)
                stdout, stderr = proc.communicate(stdin, timeout=self._timeout)
                return CommandResult(proc.returncode, stdout, stderr)
            except TimeoutExpired:
                self.kill_process(proc)
                stdout, stderr = proc.communicate(stdin)
                return CommandResult(proc.returncode, stdout, stderr)
            except OSError:
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
                return CommandResult(proc.returncode, stdout, stderr)
            except OSError:
                raise CommandNotFoundError(f"The command {self._command} was not found")

    def kill_process(self, p):
        """
        Kill a process when timeout occurs.
        
        Args:
            p: Process object to kill
        """
        logging.info(f"The command has timeout after {self._timeout} seconds")
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
        logging.debug('Command executed: {0}'.format(' '.join(cmd_args)))

        try:
            return Popen(cmd_args, stderr=stderr, stdout=stdout)
        except OSError:
            raise CommandNotFoundError(f"The command {self._command} was not found")

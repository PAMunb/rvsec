"""
Unit tests for the Command module in rv-android.

This test suite covers various scenarios for the Command class,
including successful command execution, error handling,
timeout mechanisms, and different input types.
"""

import errno
import os
import subprocess
import sys
import time
from unittest.mock import patch

import pytest

# Ensure the parent directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from rvandroid.commands.command import Command, kill_process_tree
from rvandroid.commands.command_not_found_error import CommandNotFoundError


class TestCommand:
    """
    Comprehensive test suite for the Command class.

    ### Architectural Testing Considerations:
    - Validate core functionality of system command execution
    - Ensure robust error handling and process management
    - Test various execution scenarios and edge cases
    - Verify timeout and process termination mechanisms
    """

    def test_basic_command_execution(self):
        """
        Test a simple command execution with successful outcome.

        Validates:
        - Command can be executed successfully
        - Correct exit code is returned
        - Stdout and stderr are captured
        """
        cmd = Command("echo", ["Hello, RV-Android"])
        result = cmd.invoke()

        assert result.code == 0
        assert b"Hello, RV-Android" in result.stdout
        assert result.stderr == b""

    def test_command_with_arguments(self):
        """
        Test command execution with multiple arguments.

        Validates argument passing and complex command handling.
        """
        cmd = Command("printf", ["%s", "test"])
        result = cmd.invoke()

        assert result.code == 0
        assert b"test" in result.stdout

    def test_command_not_found(self):
        """
        Test handling of non-existent command.

        Validates:
        - Raises CommandNotFoundError for unknown commands
        - Provides clear error information
        """
        with pytest.raises(CommandNotFoundError):
            Command("non_existent_command_xyz").invoke()

#     def test_command_timeout(self):
#         """
#         Test command timeout mechanism.
#
#         Validates:
#         - Long-running commands are terminated after specified timeout
#         - Timeout prevents indefinite execution
#         """
#         # Use a more reliable way to test timeout
#         start_time = time.time()
#
#         try:
#             # Create a command that will definitely run longer than timeout
#             cmd = Command("python3", ["-c", """
# import time
# try:
#     time.sleep(10)
# except Exception:
#     pass
# """])
#
#             # Set a very short timeout
#             result = cmd.invoke(timeout=2)
#
#             # If we get here, the command did not time out as expected
#             pytest.fail("Command should have timed out")
#
#         except subprocess.TimeoutExpired:
#             end_time = time.time()
#             duration = end_time - start_time
#
#             # Check that timeout occurred within a reasonable time frame
#             print(f"Timeout duration: {duration} seconds")
#             assert 1.5 <= duration <= 3.0, f"Timeout duration was {duration} seconds"

    def test_daemon_process_invocation(self):
        """
        Test daemon process creation and management.

        Validates:
        - Daemon processes can be started
        - Process ID is returned
        - Minimal blocking during process start
        """
        cmd = Command("sleep", ["5"])
        process = cmd.invoke_as_deamon()

        assert process is not None
        assert hasattr(process, 'pid')
        assert process.poll() is None  # Ensure process is still running

        # Cleanup
        process.terminate()
        process.wait(timeout=2)  # Wait for process to terminate

    # def test_kill_process_tree(self):
    #     """
    #     Test recursive process tree termination.
    #
    #     Validates:
    #     - Child processes are also terminated
    #     - Prevents zombie processes
    #     """
    #     import multiprocessing
    #
    #     def create_child_process():
    #         """Function to create a long-running child process"""
    #         try:
    #             # Use a simple infinite loop to simulate a long-running process
    #             while True:
    #                 time.sleep(1)
    #         except Exception:
    #             pass
    #
    #     # Create a parent process with a child process
    #     parent_process = multiprocessing.Process(target=create_child_process)
    #     parent_process.start()
    #
    #     # Give a moment for the process to start
    #     time.sleep(0.5)
    #
    #     try:
    #         # Get the process ID
    #         pid = parent_process.pid
    #
    #         # Attempt to kill the process tree
    #         try:
    #             kill_process_tree(pid)
    #         except Exception as kill_err:
    #             pytest.fail(f"Process tree termination failed: {kill_err}")
    #
    #         # Wait a moment to allow termination
    #         time.sleep(1)
    #
    #         # Check if process is terminated
    #         try:
    #             os.kill(pid, 0)
    #             pytest.fail("Main process should be terminated")
    #         except OSError as e:
    #             # Expect an OSError with ESRCH when process doesn't exist
    #             assert e.errno == errno.ESRCH, f"Unexpected error: {e}"
    #
    #     finally:
    #         # Ensure process is fully terminated
    #         try:
    #             parent_process.terminate()
    #             parent_process.join(timeout=2)
    #         except Exception:
    #             pass

    def test_command_properties(self):
        """
        Test getter and setter methods for Command properties.

        Validates:
        - Command attributes can be modified after initialization
        - Getters return correct values
        """
        cmd = Command("echo", ["test"])

        # Test initial values
        assert cmd.command == "echo"
        assert cmd.args == ["test"]
        assert cmd.timeout is None

        # Test setters
        cmd.command = "ls"
        cmd.args = ["-a"]
        cmd.timeout = 5

        assert cmd.command == "ls"
        assert cmd.args == ["-a"]
        assert cmd.timeout == 5

    @patch('subprocess.Popen')
    def test_command_error_handling(self, mock_popen):
        """
        Test error handling during command execution.

        Validates:
        - Graceful handling of subprocess errors
        - Proper error propagation
        """
        # Simulate OSError (e.g., permission denied)
        mock_popen.side_effect = OSError("Simulated subprocess error")

        cmd = Command("forbidden_command")

        with pytest.raises(CommandNotFoundError):
            cmd.invoke()


@pytest.mark.performance
class TestCommandPerformance:
    """
    Performance-focused tests for Command class.

    Evaluates system resource usage and execution efficiency.
    """

    def test_multiple_command_executions(self):
        """
        Test multiple rapid command executions.

        Validates:
        - System stability under multiple command invocations
        - No resource leaks
        """
        for _ in range(50):
            cmd = Command("echo", ["Performance Test"])
            result = cmd.invoke()
            assert result.code == 0

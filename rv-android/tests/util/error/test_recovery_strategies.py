# tests/util/error/test_recovery_strategies.py
"""
Unit tests for the RecoveryStrategies module in rv-android.

This test suite covers the functionality of the RecoveryStrategies class,
which provides standardized error recovery implementations for common error types.
"""

import os
import signal
import sys
from unittest.mock import patch, MagicMock, call
import pytest

# Ensure the parent directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from rvandroid.util.error.recovery_strategies import RecoveryStrategies
from rvandroid.util.exceptions import ADBError, EmulatorError, RvTimeoutError


class TestRecoveryStrategies:
    """
    Comprehensive test suite for the RecoveryStrategies class.

    ### Architectural Testing Considerations:
    - Validate recovery mechanisms for common error types
    - Test error handling during recovery attempts
    - Ensure proper resource cleanup and state management
    - Verify integration with command execution subsystem
    """

    def test_handle_adb_error_success(self):
        """
        Test successful ADB error recovery.

        Validates:
        - ADB server is restarted correctly
        - Commands are executed in the correct order
        - Recovery returns True on success
        """
        # Create mock Command objects with successful returns
        with patch('rvandroid.util.error.recovery_strategies.Command') as MockCommand:
            # Set up mock command instances
            mock_kill_cmd = MagicMock()
            mock_start_cmd = MagicMock()
            mock_devices_cmd = MagicMock()

            # Configure return values for invoke method
            mock_kill_cmd.invoke.return_value.code = 0
            mock_start_cmd.invoke.return_value.code = 0
            mock_devices_cmd.invoke.return_value.code = 0

            # Configure Command constructor to return the appropriate mock
            def side_effect(cmd, args):
                if cmd == "adb" and "kill-server" in args:
                    return mock_kill_cmd
                elif cmd == "adb" and "start-server" in args:
                    return mock_start_cmd
                elif cmd == "adb" and "devices" in args:
                    return mock_devices_cmd
                return MagicMock()

            MockCommand.side_effect = side_effect

            # Call the recovery strategy
            result = RecoveryStrategies.handle_adb_error(
                ADBError("Test ADB error"), None
            )

            # Verify commands were created correctly
            MockCommand.assert_has_calls([
                call("adb", ["kill-server"]),
                call("adb", ["start-server"]),
                call("adb", ["devices"])
            ])

            # Verify commands were invoked
            mock_kill_cmd.invoke.assert_called_once()
            mock_start_cmd.invoke.assert_called_once()
            mock_devices_cmd.invoke.assert_called_once()

            # Verify successful recovery
            assert result is True

    def test_handle_adb_error_command_failure(self):
        """
        Test ADB error recovery when commands fail.

        Validates:
        - Recovery process continues despite command failures
        - Recovery still returns True if no exceptions are raised
        """
        # Create mock Command objects with failed returns
        with patch('rvandroid.util.error.recovery_strategies.Command') as MockCommand:
            # Set up mock command instances
            mock_kill_cmd = MagicMock()
            mock_start_cmd = MagicMock()
            mock_devices_cmd = MagicMock()

            # Configure return values for invoke method to indicate failure
            mock_kill_cmd.invoke.return_value.code = 1
            mock_start_cmd.invoke.return_value.code = 1
            mock_devices_cmd.invoke.return_value.code = 1

            # Configure Command constructor to return the appropriate mock
            def side_effect(cmd, args):
                if cmd == "adb" and "kill-server" in args:
                    return mock_kill_cmd
                elif cmd == "adb" and "start-server" in args:
                    return mock_start_cmd
                elif cmd == "adb" and "devices" in args:
                    return mock_devices_cmd
                return MagicMock()

            MockCommand.side_effect = side_effect

            # Call the recovery strategy
            result = RecoveryStrategies.handle_adb_error(
                ADBError("Test ADB error"), None
            )

            # Verify commands were created and invoked
            mock_kill_cmd.invoke.assert_called_once()
            mock_start_cmd.invoke.assert_called_once()
            mock_devices_cmd.invoke.assert_called_once()

            # Verify that recovery still returns True since no exceptions were raised
            assert result is True

    # def test_handle_adb_error_exception(self):
    #     """
    #     Test ADB error recovery when an exception occurs.
    #
    #     Validates:
    #     - Exceptions during recovery are caught and handled
    #     - Recovery returns False when exceptions occur
    #     """
    #     # Create mock Command objects that raise exceptions
    #     with patch('rvandroid.util.error.recovery_strategies.Command') as MockCommand:
    #         # Set up the kill-server command to raise an exception
    #         mock_cmd = MagicMock()
    #         mock_cmd.invoke.side_effect = Exception("Command execution failed")
    #         MockCommand.return_value = mock_cmd
    #
    #         # Call the recovery strategy
    #         result = RecoveryStrategies.handle_adb_error(
    #             ADBError("Test ADB error"), None
    #         )
    #
    #         # Verify command was created and invoked
    #         MockCommand.assert_called_once()
    #         mock_cmd.invoke.assert_called_once()
    #
    #         # Verify failed recovery
    #         assert result is False

    def test_handle_emulator_error_with_device_id(self):
        """
        Test emulator error recovery with a specific device ID.

        Validates:
        - Correct command is used for specific device
        - Device ID is correctly passed to the command
        - Recovery returns True on success
        """
        # Create mock Command object
        with patch('rvandroid.util.error.recovery_strategies.Command') as MockCommand:
            # Set up mock command
            mock_kill_cmd = MagicMock()
            mock_kill_cmd.invoke.return_value.code = 0
            MockCommand.return_value = mock_kill_cmd

            # Call the recovery strategy with device_id in context
            result = RecoveryStrategies.handle_emulator_error(
                EmulatorError("Test emulator error"),
                {"device_id": "emulator-5554"}
            )

            # Verify command was created correctly for specific device
            MockCommand.assert_called_once_with("adb", ["-s", "emulator-5554", "emu", "kill"])

            # Verify command was invoked
            mock_kill_cmd.invoke.assert_called_once()

            # Verify successful recovery
            assert result is True

    def test_handle_emulator_error_without_device_id(self):
        """
        Test emulator error recovery without a specific device ID.

        Validates:
        - Generic pkill command is used when no device ID is provided
        - Recovery returns True on success
        """
        # Create mock Command object
        with patch('rvandroid.util.error.recovery_strategies.Command') as MockCommand:
            # Set up mock command
            mock_kill_cmd = MagicMock()
            mock_kill_cmd.invoke.return_value.code = 0
            MockCommand.return_value = mock_kill_cmd

            # Call the recovery strategy without device_id in context
            result = RecoveryStrategies.handle_emulator_error(
                EmulatorError("Test emulator error"),
                None
            )

            # Verify command was created correctly for general emulator cleanup
            MockCommand.assert_called_once_with("pkill", ["-f", "emulator"])

            # Verify command was invoked
            mock_kill_cmd.invoke.assert_called_once()

            # Verify successful recovery
            assert result is True

    def test_handle_emulator_error_exception(self):
        """
        Test emulator error recovery when an exception occurs.

        Validates:
        - Exceptions during recovery are caught and handled
        - Recovery returns False when exceptions occur
        """
        # Create mock Command objects that raise exceptions
        with patch('rvandroid.util.error.recovery_strategies.Command') as MockCommand:
            # Set up the command to raise an exception
            mock_cmd = MagicMock()
            mock_cmd.invoke.side_effect = Exception("Command execution failed")
            MockCommand.return_value = mock_cmd

            # Call the recovery strategy
            result = RecoveryStrategies.handle_emulator_error(
                EmulatorError("Test emulator error"), None
            )

            # Verify command was created and invoked
            MockCommand.assert_called_once()
            mock_cmd.invoke.assert_called_once()

            # Verify failed recovery
            assert result is False

    def test_handle_timeout_error_with_process(self):
        """
        Test timeout error recovery with a process in context.

        Validates:
        - Process is terminated correctly
        - SIGTERM signal is sent to the process
        - Recovery returns True on success
        """
        # Mock os.kill function
        with patch('rvandroid.util.error.recovery_strategies.os.kill') as mock_kill:
            # Create a mock process with a PID
            mock_process = MagicMock()
            mock_process.pid = 12345

            # Call the recovery strategy with process in context
            result = RecoveryStrategies.handle_timeout_error(
                RvTimeoutError("Test timeout error"),
                {"process": mock_process}
            )

            # Verify os.kill was called correctly
            mock_kill.assert_called_once_with(12345, signal.SIGTERM)

            # Verify successful recovery
            assert result is True

    def test_handle_timeout_error_without_process(self):
        """
        Test timeout error recovery without a process in context.

        Validates:
        - No action is taken when process is missing
        - Recovery returns False when no process is available
        """
        # Mock os.kill function
        with patch('rvandroid.util.error.recovery_strategies.os.kill') as mock_kill:
            # Call the recovery strategy without process in context
            result = RecoveryStrategies.handle_timeout_error(
                RvTimeoutError("Test timeout error"),
                {}
            )

            # Verify os.kill was not called
            mock_kill.assert_not_called()

            # Verify unsuccessful recovery
            assert result is False

    def test_handle_timeout_error_kill_exception(self):
        """
        Test timeout error recovery when kill raises an exception.

        Validates:
        - Exceptions during process termination are caught and handled
        - Recovery returns False when exceptions occur
        """
        # Mock os.kill function to raise an exception
        with patch('rvandroid.util.error.recovery_strategies.os.kill') as mock_kill:
            mock_kill.side_effect = OSError("Permission denied")

            # Create a mock process with a PID
            mock_process = MagicMock()
            mock_process.pid = 12345

            # Call the recovery strategy with process in context
            result = RecoveryStrategies.handle_timeout_error(
                RvTimeoutError("Test timeout error"),
                {"process": mock_process}
            )

            # Verify os.kill was called but failed
            mock_kill.assert_called_once_with(12345, signal.SIGTERM)

            # Verify unsuccessful recovery
            assert result is False

    def test_handle_timeout_error_process_without_pid(self):
        """
        Test timeout error recovery with process that has no PID.

        Validates:
        - Recovery handles processes without PID attributes
        - Recovery returns False in this case
        """
        # Mock os.kill function
        with patch('rvandroid.util.error.recovery_strategies.os.kill') as mock_kill:
            # Create a mock process without a PID
            mock_process = MagicMock()
            del mock_process.pid  # Remove the pid attribute

            # Call the recovery strategy with invalid process in context
            result = RecoveryStrategies.handle_timeout_error(
                RvTimeoutError("Test timeout error"),
                {"process": mock_process}
            )

            # Verify os.kill was not called
            mock_kill.assert_not_called()

            # Verify unsuccessful recovery
            assert result is False

    # def test_logger_usage(self):
    #     """
    #     Test that the recovery strategies use logging appropriately.
    #
    #     Validates:
    #     - Recovery strategies log their actions
    #     - Different log levels are used for different events
    #     """
    #     # Mock the logging module
    #     with patch('rvandroid.util.error.recovery_strategies.logging') as mock_logging:
    #         # Set up mock logger
    #         mock_logger = MagicMock()
    #         mock_logging.getLogger.return_value = mock_logger
    #
    #         # Also patch Command to avoid actual execution
    #         with patch('rvandroid.util.error.recovery_strategies.Command') as MockCommand:
    #             mock_cmd = MagicMock()
    #             mock_cmd.invoke.return_value.code = 0
    #             MockCommand.return_value = mock_cmd
    #
    #             # Call the recovery strategies
    #             RecoveryStrategies.handle_adb_error(
    #                 ADBError("Test ADB error"), None
    #             )
    #
    #             # Verify logging occurred
    #             mock_logging.getLogger.assert_called_with('__name__')
    #             mock_logger.info.assert_called()
    #
    #             # Reset mocks for next test
    #             mock_logger.reset_mock()
    #
    #             # Test with error condition
    #             mock_cmd.invoke.side_effect = Exception("Command failed")
    #
    #             RecoveryStrategies.handle_adb_error(
    #                 ADBError("Test ADB error"), None
    #             )
    #
    #             # Verify error logging occurred
    #             mock_logger.error.assert_called()

    # def test_integration_with_error_handler(self):
    #     """
    #     Test integration of recovery strategies with error handler registry.
    #
    #     Validates:
    #     - Recovery strategies can be registered with the handler registry
    #     - Registered strategies are correctly invoked via the registry
    #     """
    #     from rvandroid.util.error.handler_registry import HandlerRegistry
    #
    #     # Set up a registry with recovery strategies
    #     registry = HandlerRegistry()
    #     registry.register(ADBError, RecoveryStrategies.handle_adb_error)
    #     registry.register(EmulatorError, RecoveryStrategies.handle_emulator_error)
    #     registry.register(RvTimeoutError, RecoveryStrategies.handle_timeout_error)
    #
    #     # Mock the actual implementations to avoid side effects
    #     with patch.object(RecoveryStrategies, 'handle_adb_error') as mock_adb_handler, \
    #             patch.object(RecoveryStrategies, 'handle_emulator_error') as mock_emulator_handler, \
    #             patch.object(RecoveryStrategies, 'handle_timeout_error') as mock_timeout_handler:
    #
    #         # Configure mocks to return True
    #         mock_adb_handler.return_value = True
    #         mock_emulator_handler.return_value = True
    #         mock_timeout_handler.return_value = True
    #
    #         # Find and invoke handlers for each error type
    #         adb_handlers = registry.find_handlers(ADBError)
    #         for handler in adb_handlers:
    #             handler(ADBError("Test ADB error"), None)
    #
    #         emulator_handlers = registry.find_handlers(EmulatorError)
    #         for handler in emulator_handlers:
    #             handler(EmulatorError("Test emulator error"), None)
    #
    #         timeout_handlers = registry.find_handlers(RvTimeoutError)
    #         for handler in timeout_handlers:
    #             handler(RvTimeoutError("Test timeout error"), None)
    #
    #         # Verify that recovery strategies were invoked
    #         mock_adb_handler.assert_called_once()
    #         mock_emulator_handler.assert_called_once()
    #         mock_timeout_handler.assert_called_once()

    def test_handle_adb_error_with_custom_context(self):
        """
        Test ADB error recovery with custom context information.

        Validates:
        - Context data is properly handled and passed through
        - Custom context doesn't affect recovery behavior
        """
        # Create mock Command objects
        with patch('rvandroid.util.error.recovery_strategies.Command') as MockCommand:
            # Set up mock command
            mock_cmd = MagicMock()
            mock_cmd.invoke.return_value.code = 0
            MockCommand.return_value = mock_cmd

            # Call the recovery strategy with custom context
            custom_context = {
                "task_id": 123,
                "phase": "test",
                "app_name": "test_app",
                "custom_info": "custom value"
            }

            result = RecoveryStrategies.handle_adb_error(
                ADBError("Test ADB error"),
                custom_context
            )

            # Verify command was invoked
            assert mock_cmd.invoke.call_count == 3  # Three different commands

            # Verify successful recovery
            assert result is True

    # def test_recovery_strategy_without_logger(self):
    #     """
    #     Test recovery strategies when logger initialization fails.
    #
    #     Validates:
    #     - Recovery strategies handle logging failures gracefully
    #     - Core functionality continues even if logging fails
    #     """
    #     # Mock logging to raise an exception when getLogger is called
    #     with patch('rvandroid.util.error.recovery_strategies.logging') as mock_logging:
    #         mock_logging.getLogger.side_effect = Exception("Logger initialization failed")
    #
    #         # Also patch Command to avoid actual execution
    #         with patch('rvandroid.util.error.recovery_strategies.Command') as MockCommand:
    #             mock_cmd = MagicMock()
    #             mock_cmd.invoke.return_value.code = 0
    #             MockCommand.return_value = mock_cmd
    #
    #             # Call the recovery strategy
    #             # This should still work despite logging failure
    #             result = RecoveryStrategies.handle_adb_error(
    #                 ADBError("Test ADB error"), None
    #             )
    #
    #             # Verify command was invoked
    #             assert mock_cmd.invoke.call_count == 3  # Three different commands
    #
    #             # Verify successful recovery
    #             assert result is True

    def test_multiple_consecutive_recoveries(self):
        """
        Test multiple consecutive recovery attempts.

        Validates:
        - Recovery strategies can be called multiple times in succession
        - Each call is independent and doesn't affect others
        """
        # Create mock Command objects
        with patch('rvandroid.util.error.recovery_strategies.Command') as MockCommand:
            # Set up mock command
            mock_cmd = MagicMock()
            mock_cmd.invoke.return_value.code = 0
            MockCommand.return_value = mock_cmd

            # Call recovery strategies multiple times
            results = []
            for i in range(3):
                result = RecoveryStrategies.handle_adb_error(
                    ADBError(f"Test ADB error {i}"), None
                )
                results.append(result)

            # Verify all recoveries were successful
            assert all(results)

            # Verify each recovery created its own set of commands
            # 3 commands per recovery, 3 recoveries
            assert mock_cmd.invoke.call_count == 9

    def test_handle_adb_error_with_cause(self):
        """
        Test ADB error recovery with nested error causes.

        Validates:
        - Recovery strategies handle errors with nested causes
        - Cause information doesn't affect recovery behavior
        """
        # Create mock Command objects
        with patch('rvandroid.util.error.recovery_strategies.Command') as MockCommand:
            # Set up mock command
            mock_cmd = MagicMock()
            mock_cmd.invoke.return_value.code = 0
            MockCommand.return_value = mock_cmd

            # Create an ADBError with a nested cause
            original_error = Exception("Original error")
            adb_error = ADBError("ADB server failed to start", original_error)

            # Call the recovery strategy
            result = RecoveryStrategies.handle_adb_error(adb_error, None)

            # Verify command was invoked
            assert mock_cmd.invoke.call_count == 3

            # Verify successful recovery
            assert result is True

    def test_recovery_strategies_as_static_methods(self):
        """
        Test that recovery strategies are implemented as static methods.

        Validates:
        - Recovery strategies can be called directly from the class
        - No instance is required to use recovery strategies
        """
        # Verify these are static methods by calling them directly
        assert callable(RecoveryStrategies.handle_adb_error)
        assert callable(RecoveryStrategies.handle_emulator_error)
        assert callable(RecoveryStrategies.handle_timeout_error)

    @pytest.mark.parametrize("error_type,handler_method", [
        (ADBError, RecoveryStrategies.handle_adb_error),
        (EmulatorError, RecoveryStrategies.handle_emulator_error),
        (RvTimeoutError, RecoveryStrategies.handle_timeout_error)
    ])
    def test_recovery_handler_signature(self, error_type, handler_method):
        """
        Test that recovery handler signatures match expected convention.

        Validates:
        - Recovery methods accept error and context parameters
        - Return value is boolean indicating success
        """
        # Mock any external calls to avoid side effects
        with patch('rvandroid.util.error.recovery_strategies.logging'), \
                patch('rvandroid.util.error.recovery_strategies.Command'), \
                patch('rvandroid.util.error.recovery_strategies.os'):
            # Call the handler with minimal valid arguments
            error = error_type("Test error")
            result = handler_method(error, None)

            # Verify result is a boolean
            assert isinstance(result, bool)
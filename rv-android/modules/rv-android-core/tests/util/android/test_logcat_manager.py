# tests/util/test_logcat_manager.py - Fixed version
"""
Unit tests for the LogcatManager module.

This module tests the functionality of the LogcatManager class, which is responsible for
managing logcat operations for Android devices, including capturing output and clearing buffers.

### Architectural Decisions:
- Uses mocking to isolate LogcatManager functionality from external dependencies
- Tests both normal operation and error handling pathways
- Validates proper resource management and cleanup
- Ensures correct command execution and file handling

### Role in the System:
- Ensures reliable logcat capture and processing for test execution
- Validates proper resource cleanup after operations
- Confirms appropriate error handling during logcat operations
- Verifies correct interaction with the Android Debug Bridge (ADB)
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.util.android.logcat_manager import DIAGNOSTIC_TAGS, LogcatManager


class TestLogcatManager:
    """Tests for the LogcatManager class."""

    @pytest.fixture
    def logcat_manager(self):
        """Create a fresh LogcatManager instance for testing."""
        return LogcatManager()

    def test_init(self, logcat_manager):
        """Test LogcatManager initialization."""
        assert logcat_manager.logcat_process is None
        assert logcat_manager.logcat_file_handle is None

    @patch("rv_android_core.util.android.logcat_manager.Command")
    @patch("builtins.open")
    @patch("os.makedirs")
    def test_start_capture_success(
        self, mock_makedirs, mock_open_file, mock_command_class, logcat_manager
    ):
        """Test successful start of logcat capture."""
        # Configure mocks properly to avoid hanging
        mock_file = MagicMock()
        mock_open_file.return_value = mock_file

        mock_process = MagicMock()

        # Mock both command instances separately
        mock_clear_command = MagicMock()
        mock_clear_command.invoke.return_value = MagicMock()

        mock_logcat_command = MagicMock()
        mock_logcat_command.invoke_as_process.return_value = mock_process

        # Configure the Command mock to return different instances
        mock_command_class.side_effect = [mock_clear_command, mock_logcat_command]

        # Call the method
        result = logcat_manager.start_capture("/test/output.log")

        # Verify directory creation
        mock_makedirs.assert_called_once_with("/test", exist_ok=True)

        # Verify commands were created correctly with device serial
        # Tags get :V (Verbose) suffix for proper logcat filtering
        assert mock_command_class.call_count == 2
        mock_command_class.assert_any_call(
            "adb", ["-s", "emulator-5554", "logcat", "-c"]
        )
        mock_command_class.assert_any_call(
            "adb",
            [
                "-s",
                "emulator-5554",
                "logcat",
                "-v",
                "threadtime",
                "-s",
                "RVSEC:V",
                "RVSEC-COV:V",
            ],
        )

        # Verify commands were executed
        mock_clear_command.invoke.assert_called_once()
        mock_logcat_command.invoke_as_process.assert_called_once_with(stdout=mock_file)

        # Verify state and result
        assert logcat_manager.logcat_process == mock_process
        assert logcat_manager.logcat_file_handle == mock_file
        assert result is True

    @patch("rv_android_core.util.android.logcat_manager.Command")
    @patch("builtins.open")
    @patch("os.makedirs")
    def test_start_capture_custom_tags(
        self, mock_makedirs, mock_open_file, mock_command_class, logcat_manager
    ):
        """Test logcat capture with custom tags."""
        # Configure mocks
        mock_file = MagicMock()
        mock_open_file.return_value = mock_file

        mock_process = MagicMock()

        # Mock both command instances separately
        mock_clear_command = MagicMock()
        mock_clear_command.invoke.return_value = MagicMock()

        mock_logcat_command = MagicMock()
        mock_logcat_command.invoke_as_process.return_value = mock_process

        # Configure the Command mock to return different instances
        mock_command_class.side_effect = [mock_clear_command, mock_logcat_command]

        # Call the method with custom tags
        result = logcat_manager.start_capture(
            "/test/output.log", tags=["CUSTOM", "DEBUG"]
        )

        # Verify correct command arguments with device serial
        # Tags get :V (Verbose) suffix for proper logcat filtering
        mock_command_class.assert_any_call(
            "adb",
            [
                "-s",
                "emulator-5554",
                "logcat",
                "-v",
                "threadtime",
                "-s",
                "CUSTOM:V",
                "DEBUG:V",
            ],
        )
        assert result is True

    @patch("rv_android_core.util.android.logcat_manager.Command")
    @patch("builtins.open")
    @patch("os.makedirs")
    def test_start_capture_without_clear(
        self, mock_makedirs, mock_open_file, mock_command_class, logcat_manager
    ):
        """Test logcat capture without clearing the buffer."""
        # Configure mocks
        mock_file = MagicMock()
        mock_open_file.return_value = mock_file

        mock_process = MagicMock()
        mock_logcat_command = MagicMock()
        mock_logcat_command.invoke_as_process.return_value = mock_process

        mock_command_class.return_value = mock_logcat_command

        # Call the method without clearing buffer
        result = logcat_manager.start_capture("/test/output.log", clear_buffer=False)

        # Verify command creation and execution with device serial
        # Tags get :V (Verbose) suffix for proper logcat filtering
        mock_command_class.assert_called_once_with(
            "adb",
            [
                "-s",
                "emulator-5554",
                "logcat",
                "-v",
                "threadtime",
                "-s",
                "RVSEC:V",
                "RVSEC-COV:V",
            ],
        )
        mock_logcat_command.invoke_as_process.assert_called_once_with(stdout=mock_file)

        assert result is True

    @patch("os.makedirs")
    def test_start_capture_directory_error(self, mock_makedirs, logcat_manager):
        """Test handling of directory creation errors."""
        # Configure mock to raise an exception
        mock_makedirs.side_effect = PermissionError("Permission denied")

        # Call the method
        result = logcat_manager.start_capture("/test/output.log")

        # Verify result
        assert result is False

    @patch("rv_android_core.util.android.logcat_manager.Command")
    @patch("builtins.open")
    @patch("os.makedirs")
    def test_start_capture_command_error(
        self, mock_makedirs, mock_open_file, mock_command_class, logcat_manager
    ):
        """Test handling of command execution errors."""
        # Configure mocks
        mock_file = MagicMock()
        mock_open_file.return_value = mock_file

        # First command succeeds (clear buffer)
        mock_clear_command = MagicMock()
        mock_clear_command.invoke.return_value = MagicMock()

        # Second command fails (logcat)
        mock_logcat_command = MagicMock()
        mock_logcat_command.invoke_as_process.side_effect = Exception("Command failed")

        mock_command_class.side_effect = [mock_clear_command, mock_logcat_command]

        # Call the method
        result = logcat_manager.start_capture("/test/output.log")

        # Verify file cleanup
        mock_file.close.assert_called_once()

        # Verify result
        assert result is False

    def test_stop_capture_success(self, logcat_manager):
        """Test successful stop of logcat capture."""
        # Set up manager with mocked process and file
        mock_process = MagicMock()
        mock_file = MagicMock()

        logcat_manager.logcat_process = mock_process
        logcat_manager.logcat_file_handle = mock_file

        # Call the method
        result = logcat_manager.stop_capture()

        # Verify process and file cleanup
        mock_process.kill.assert_called_once()
        mock_file.close.assert_called_once()
        assert logcat_manager.logcat_process is None
        assert logcat_manager.logcat_file_handle is None
        assert result is True

    def test_stop_capture_process_error(self, logcat_manager):
        """Test handling of process termination errors."""
        # Set up manager with mocked process and file
        mock_process = MagicMock()
        mock_process.kill.side_effect = Exception("Failed to kill process")

        mock_file = MagicMock()

        logcat_manager.logcat_process = mock_process
        logcat_manager.logcat_file_handle = mock_file

        # Call the method
        result = logcat_manager.stop_capture()

        # Verify file cleanup still occurs
        mock_file.close.assert_called_once()
        assert logcat_manager.logcat_file_handle is None
        assert result is False  # Operation overall failed

    def test_stop_capture_file_error(self, logcat_manager):
        """Test handling of file closing errors."""
        # Set up manager with mocked process and file
        mock_process = MagicMock()

        mock_file = MagicMock()
        mock_file.close.side_effect = Exception("Failed to close file")

        logcat_manager.logcat_process = mock_process
        logcat_manager.logcat_file_handle = mock_file

        # Call the method
        result = logcat_manager.stop_capture()

        # Verify process cleanup still occurs
        mock_process.kill.assert_called_once()
        assert logcat_manager.logcat_process is None
        assert result is False  # Operation overall failed

    def test_stop_capture_no_active_capture(self, logcat_manager):
        """Test stop_capture with no active capture."""
        # Call with no active process or file
        result = logcat_manager.stop_capture()

        # Should succeed trivially
        assert result is True

    @patch("rv_android_core.util.android.logcat_manager.Command")
    @patch("builtins.open")
    @patch("os.makedirs")
    def test_diagnostics_flag_off_byte_identical_command(
        self, mock_makedirs, mock_open_file, mock_command_class, logcat_manager
    ):
        """INV-CORE-37: with no diagnostic tags the emitted command is the baseline,
        byte-for-byte (`-v threadtime -s RVSEC:V RVSEC-COV:V`)."""
        mock_open_file.return_value = MagicMock()
        mock_clear_command = MagicMock()
        mock_logcat_command = MagicMock()
        mock_command_class.side_effect = [mock_clear_command, mock_logcat_command]

        result = logcat_manager.start_capture("/test/output.log")

        mock_command_class.assert_any_call(
            "adb",
            [
                "-s",
                "emulator-5554",
                "logcat",
                "-v",
                "threadtime",
                "-s",
                "RVSEC:V",
                "RVSEC-COV:V",
            ],
        )
        assert result is True

    @patch("rv_android_core.util.android.logcat_manager.Command")
    @patch("builtins.open")
    @patch("os.makedirs")
    def test_diagnostics_tags_additive(
        self, mock_makedirs, mock_open_file, mock_command_class, logcat_manager
    ):
        """INV-CORE-38: diagnostic tags are appended after RVSEC/RVSEC-COV (which are
        preserved unchanged), and priority-bearing tags keep their `:E`/`:W` suffix
        verbatim (no spurious `:V`)."""
        mock_open_file.return_value = MagicMock()
        mock_clear_command = MagicMock()
        mock_logcat_command = MagicMock()
        mock_command_class.side_effect = [mock_clear_command, mock_logcat_command]

        result = logcat_manager.start_capture(
            "/test/output.log",
            tags=logcat_manager.default_tags + DIAGNOSTIC_TAGS,
        )

        mock_command_class.assert_any_call(
            "adb",
            [
                "-s",
                "emulator-5554",
                "logcat",
                "-v",
                "threadtime",
                "-s",
                "RVSEC:V",
                "RVSEC-COV:V",
                "AndroidRuntime:E",
                "art:E",
                "dalvikvm:E",
                "ActivityManager:W",
            ],
        )
        assert result is True

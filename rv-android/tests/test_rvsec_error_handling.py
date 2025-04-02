from unittest.mock import patch, MagicMock

import pytest

from rvandroid.commands.command_exception import CommandException
from rvandroid.rvsec import RVSec


class TestRVSecErrorHandling:
    """Tests focused on error handling in the RVSec class."""

    @pytest.fixture
    def mock_paths(self):
        """Fixture that patches all path constants."""
        with patch('rvandroid.rvsec.MOP_OUT_DIR', 'mocked_mop_out_dir'), \
                patch('rvandroid.rvsec.MOP_DIR', 'mocked_mop_dir'), \
                patch('rvandroid.rvsec.JAVAMOP_BIN', 'mocked_javamop_bin'), \
                patch('rvandroid.rvsec.RV_MONITOR_BIN', 'mocked_rv_monitor_bin'), \
                patch('rvandroid.rvsec.ASPECTS_DIR', 'mocked_aspects_dir'), \
                patch('rvandroid.rvsec.EXTENSION_MOP', '.mop'), \
                patch('rvandroid.rvsec.EXTENSION_AJ', '.aj'), \
                patch('rvandroid.rvsec.EXTENSION_RVM', '.rvm'):
            yield

    @pytest.fixture
    def mock_utils(self):
        """Fixture that patches the utils module."""
        with patch('rvandroid.rvsec.utils') as mock_utils:
            yield mock_utils

    @pytest.fixture
    def mock_command(self):
        """Fixture that patches the Command class."""
        with patch('rvandroid.rvsec.Command') as mock_command:
            yield mock_command

    @pytest.fixture
    def mock_logging(self):
        """Fixture that patches the logging module."""
        with patch('rvandroid.rvsec.logging') as mock_logging:
            yield mock_logging

    def test_command_exception_in_java_mop(self, mock_paths, mock_utils, mock_command, mock_logging):
        """Test handling of CommandException in __java_mop."""
        # Configure mock to raise CommandException
        mock_utils.execute_command.side_effect = CommandException(
            "javamop", 1, "Syntax error in MOP specification"
        )

        # Call the method and verify exception propagation
        with pytest.raises(CommandException) as excinfo:
            RVSec._RVSec__java_mop()

        # Verify exception details
        assert excinfo.value.tool == "javamop"
        assert excinfo.value.code == 1
        assert excinfo.value.message == "Syntax error in MOP specification"

    def test_command_exception_in_rv_monitor(self, mock_paths, mock_utils, mock_command, mock_logging):
        """Test handling of CommandException in __rv_monitor."""
        # Configure mock to raise CommandException
        mock_utils.execute_command.side_effect = CommandException(
            "rvmonitor", 1, "Failed to process RVM files"
        )

        # Call the method and verify exception propagation
        with pytest.raises(CommandException) as excinfo:
            RVSec._RVSec__rv_monitor()

        # Verify exception details
        assert excinfo.value.tool == "rvmonitor"
        assert excinfo.value.code == 1
        assert excinfo.value.message == "Failed to process RVM files"

    def test_file_operation_error_in_generate_monitors(self, mock_paths, mock_utils, mock_logging):
        """Test error handling with file operation errors."""
        # Create RVSec instance
        rvsec = RVSec()

        # Configure mock for reset_folder to work but move_files_by_extension to fail
        def mock_side_effects(*args, **kwargs):
            if args[0] == "move_files_by_extension":
                raise OSError("Permission denied")
            return MagicMock()

        # Configure utils.move_files_by_extension to raise OSError
        mock_utils.move_files_by_extension.side_effect = OSError("Permission denied")

        # Call method and verify exception is propagated
        with pytest.raises(OSError) as excinfo:
            # Mock the __java_mop method to avoid having to mock everything
            with patch.object(RVSec, '_RVSec__java_mop') as mock_java_mop:
                mock_java_mop.side_effect = OSError("Permission denied")
                rvsec.generate_monitors()

        # Verify exception details
        assert "Permission denied" in str(excinfo.value)

    def test_command_not_found_in_java_mop(self, mock_paths, mock_utils, mock_command, mock_logging):
        """Test handling of command not found in __java_mop."""
        # Configure mock to raise CommandException with command not found error
        mock_utils.execute_command.side_effect = CommandException(
            "javamop", 127, "Command not found"
        )

        # Call the method and verify exception propagation
        with pytest.raises(CommandException) as excinfo:
            RVSec._RVSec__java_mop()

        # Verify exception details
        assert excinfo.value.tool == "javamop"
        assert excinfo.value.code == 127
        assert excinfo.value.message == "Command not found"

    def test_error_propagation_chain(self, mock_paths, mock_utils, mock_logging):
        """Test error propagation chain from utilities through private methods to public API."""
        # Create RVSec instance
        rvsec = RVSec()

        # Setup error that will be thrown by utils.reset_folder
        original_error = OSError("Disk full")
        mock_utils.reset_folder.side_effect = original_error

        # Call generate_monitors and check error propagation
        with pytest.raises(OSError) as excinfo:
            rvsec.generate_monitors()

        # Verify the original error was propagated
        assert excinfo.value is original_error

    def test_multiple_errors_in_sequence(self, mock_paths, mock_utils, mock_command, mock_logging):
        """Test handling of multiple errors occurring in sequence."""
        # Create RVSec instance
        rvsec = RVSec()

        # Patch private methods to throw different errors
        with patch.object(RVSec, '_RVSec__java_mop') as mock_java_mop, \
                patch.object(RVSec, '_RVSec__rv_monitor') as mock_rv_monitor:
            # First call to __java_mop succeeds
            mock_java_mop.return_value = None

            # First call to __rv_monitor fails
            mock_rv_monitor.side_effect = CommandException(
                "rvmonitor", 1, "Error in monitor generation"
            )

            # Call generate_monitors and check that first error is propagated
            with pytest.raises(CommandException) as excinfo:
                rvsec.generate_monitors()

            # Verify the error details
            assert excinfo.value.tool == "rvmonitor"
            assert excinfo.value.code == 1

            # Change error in __java_mop to test second case
            mock_java_mop.side_effect = OSError("File not found")
            mock_rv_monitor.side_effect = None

            # Call generate_monitors again and check that new error is propagated
            with pytest.raises(OSError) as excinfo:
                rvsec.generate_monitors()

            # Verify it's the correct error
            assert "File not found" in str(excinfo.value)

    def test_error_in_reset_folder(self, mock_paths, mock_utils, mock_logging):
        """Test error handling when reset_folder fails."""
        # Create RVSec instance
        rvsec = RVSec()

        # Configure mock_utils.reset_folder to raise an exception
        mock_utils.reset_folder.side_effect = PermissionError("Permission denied")

        # Call generate_monitors and verify exception propagation
        with pytest.raises(PermissionError) as excinfo:
            rvsec.generate_monitors()

        # Verify exception details
        assert "Permission denied" in str(excinfo.value)

        # Verify logging
        mock_logging.info.assert_called_with("Generating Monitors ...")
        mock_logging.debug.assert_called_with("Recreating mocked_mop_out_dir")

    def test_error_in_move_files(self, mock_paths, mock_utils, mock_command, mock_logging):
        """Test error handling when move_files_by_extension fails."""
        # Configure mock to raise exception during file move
        mock_utils.move_files_by_extension.side_effect = IOError("File system error")

        # Configure other mocks to prevent earlier errors
        mock_cmd_instance = MagicMock()
        mock_command.return_value = mock_cmd_instance

        # Call the method and verify exception propagation
        with pytest.raises(IOError) as excinfo:
            RVSec._RVSec__java_mop()

        # Verify exception details
        assert "File system error" in str(excinfo.value)

        # Verify that the command was executed before the error
        mock_utils.execute_command.assert_called_once()

    def test_error_in_copy_files(self, mock_paths, mock_utils, mock_command, mock_logging):
        """Test error handling when copy_files_by_extension fails."""

        # Configure mock to raise exception during file copy
        def side_effect_func(*args, **kwargs):
            if args[0] == '.aj':  # Only fail on copy_files_by_extension
                raise IOError("Copy operation failed")

        mock_utils.copy_files_by_extension.side_effect = IOError("Copy operation failed")

        # Configure other mocks to prevent earlier errors
        mock_cmd_instance = MagicMock()
        mock_command.return_value = mock_cmd_instance

        # Call the method and verify exception propagation
        with pytest.raises(IOError) as excinfo:
            RVSec._RVSec__java_mop()

        # Verify exception details
        assert "Copy operation failed" in str(excinfo.value)

        # Verify that move_files was called before the error
        mock_utils.move_files_by_extension.assert_called_once()

    def test_error_in_delete_files(self, mock_paths, mock_utils, mock_command, mock_logging):
        """Test error handling when delete_files_by_extension fails."""
        # Configure mock to raise exception during file deletion
        mock_utils.delete_files_by_extension.side_effect = IOError("Delete operation failed")

        # Configure other mocks to prevent earlier errors
        mock_cmd_instance = MagicMock()
        mock_command.return_value = mock_cmd_instance

        # Call the method and verify exception propagation
        with pytest.raises(IOError) as excinfo:
            RVSec._RVSec__rv_monitor()

        # Verify exception details
        assert "Delete operation failed" in str(excinfo.value)

        # Verify that the command was executed before the error
        mock_utils.execute_command.assert_called_once()

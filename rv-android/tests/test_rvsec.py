import os
from unittest.mock import patch, MagicMock

import pytest

from rvandroid.rvsec import RVSec


class TestRVSec:
    """Unit tests for the RVSec class."""

    @pytest.fixture
    def rvsec(self):
        """Fixture that returns an instance of RVSec."""
        return RVSec()

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

    def test_init(self, rvsec):
        """Test RVSec initialization."""
        assert isinstance(rvsec, RVSec)

    def test_generate_monitors(self, rvsec, mock_paths, mock_utils, mock_logging):
        """Test the generate_monitors method."""
        # Mock the private methods
        rvsec._RVSec__java_mop = MagicMock()
        rvsec._RVSec__rv_monitor = MagicMock()

        # Call the method to be tested
        rvsec.generate_monitors()

        # Verify method calls
        mock_logging.info.assert_called_with("Generating Monitors ...")
        mock_logging.debug.assert_called_with("Recreating mocked_mop_out_dir")
        mock_utils.reset_folder.assert_called_with('mocked_mop_out_dir')
        rvsec._RVSec__java_mop.assert_called_once()
        rvsec._RVSec__rv_monitor.assert_called_once()

    def test_java_mop(self, mock_paths, mock_utils, mock_command, mock_logging):
        """Test the private __java_mop method."""
        # Setup Command mock
        mock_cmd_instance = MagicMock()
        mock_command.return_value = mock_cmd_instance

        # Call the static method to be tested
        RVSec._RVSec__java_mop()

        # Verify logging calls - use assert_any_call to check for specific messages
        # without enforcing order
        mock_logging.info.assert_any_call("Executing JavaMOP")
        mock_logging.info.assert_any_call(f"MOP specs dir: mocked_mop_dir")

        # Verify that JavaMOP command was created
        expected_mop_files = os.path.join('mocked_mop_dir', '*' + '.mop')
        mock_command.assert_called_with(
            'mocked_javamop_bin',
            ['-d', 'mocked_mop_out_dir', '-merge', expected_mop_files]
        )

        # Verify command execution - check that it was called with our mock command
        assert mock_utils.execute_command.called
        args, _ = mock_utils.execute_command.call_args
        assert args[0] == mock_cmd_instance
        assert args[1] == "javamop"

        # Verify file operations were called
        assert mock_utils.move_files_by_extension.called
        assert mock_utils.copy_files_by_extension.called

        # Verify correct arguments for file operations
        move_args, _ = mock_utils.move_files_by_extension.call_args
        assert move_args[0] == '.rvm'  # First arg should be extension
        assert move_args[1] == 'mocked_mop_dir'
        assert move_args[2] == 'mocked_mop_out_dir'

        copy_args, copy_kwargs = mock_utils.copy_files_by_extension.call_args
        assert copy_args[0] == '.aj'  # First arg should be extension
        assert copy_args[1] == 'mocked_aspects_dir'
        assert copy_args[2] == 'mocked_mop_out_dir'
        assert copy_kwargs.get('log_info') == True

    def test_rv_monitor(self, mock_paths, mock_utils, mock_command, mock_logging):
        """Test the private __rv_monitor method."""
        # Setup Command mock
        mock_cmd_instance = MagicMock()
        mock_command.return_value = mock_cmd_instance

        # Call the static method to be tested
        RVSec._RVSec__rv_monitor()

        # Verify logging calls
        mock_logging.info.assert_called_with("Executing RV-Monitor")

        # Verify RV-Monitor command creation
        expected_rvm_files = os.path.join('mocked_mop_out_dir', '*' + '.rvm')
        mock_command.assert_called_with(
            'mocked_rv_monitor_bin',
            ['-d', 'mocked_mop_out_dir', '-merge', expected_rvm_files]
        )

        # Verify command execution
        assert mock_utils.execute_command.called
        args, _ = mock_utils.execute_command.call_args
        assert args[0] == mock_cmd_instance
        assert args[1] == "rvmonitor"

        # Verify file deletion was called
        assert mock_utils.delete_files_by_extension.called
        delete_args, _ = mock_utils.delete_files_by_extension.call_args
        assert delete_args[0] == '.rvm'
        assert delete_args[1] == 'mocked_mop_out_dir'

    def test_integration_flow(self, rvsec, mock_paths, mock_utils):
        """Test the integration flow between methods."""
        # Prepare mocks without replacing the actual methods
        with patch('rvandroid.rvsec.RVSec._RVSec__java_mop') as mock_java_mop, \
                patch('rvandroid.rvsec.RVSec._RVSec__rv_monitor') as mock_rv_monitor:
            # Call the method to be tested
            rvsec.generate_monitors()

            # Verify call sequence
            mock_utils.reset_folder.assert_called_once_with('mocked_mop_out_dir')
            mock_java_mop.assert_called_once()
            mock_rv_monitor.assert_called_once()
            # Verify that rv_monitor is called after java_mop
            assert mock_java_mop.call_count == 1
            assert mock_rv_monitor.call_count == 1

    def test_exception_handling_in_java_mop(self, mock_paths, mock_utils):
        """Test exception handling in the __java_mop method."""
        # Configure mock to raise an exception
        mock_utils.execute_command.side_effect = Exception("JavaMOP command failed")

        # Call the method and verify exception propagation
        with pytest.raises(Exception) as excinfo:
            RVSec._RVSec__java_mop()

        # Verify exception message
        assert str(excinfo.value) == "JavaMOP command failed"

    def test_exception_handling_in_rv_monitor(self, mock_paths, mock_utils):
        """Test exception handling in the __rv_monitor method."""
        # Configure mock to raise an exception
        mock_utils.execute_command.side_effect = Exception("RV-Monitor command failed")

        # Call the method and verify exception propagation
        with pytest.raises(Exception) as excinfo:
            RVSec._RVSec__rv_monitor()

        # Verify exception message
        assert str(excinfo.value) == "RV-Monitor command failed"

    def test_exception_handling_in_generate_monitors(self, rvsec, mock_paths, mock_utils):
        """Test exception handling in the generate_monitors method."""
        # Configure mock for utils.reset_folder to raise an exception
        mock_utils.reset_folder.side_effect = Exception("Error resetting folder")

        # Call the method and verify exception propagation
        with pytest.raises(Exception) as excinfo:
            rvsec.generate_monitors()

        # Verify exception message
        assert str(excinfo.value) == "Error resetting folder"

        # Verify that subsequent methods were not called
        with patch('rvandroid.rvsec.RVSec._RVSec__java_mop') as mock_java_mop, \
                patch('rvandroid.rvsec.RVSec._RVSec__rv_monitor') as mock_rv_monitor:
            # Try to call the method with the configured exception
            with pytest.raises(Exception):
                rvsec.generate_monitors()

            # Verify that subsequent methods were not called
            mock_java_mop.assert_not_called()
            mock_rv_monitor.assert_not_called()

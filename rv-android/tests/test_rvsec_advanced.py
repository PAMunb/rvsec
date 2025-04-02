import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from rvandroid.commands.command_exception import CommandException
from rvandroid.rvsec import RVSec


class TestRVSecAdvanced:
    """Advanced tests for the RVSec class."""

    @pytest.fixture
    def setup_temp_dirs(self):
        """Fixture that sets up temporary directories for testing."""
        # Create temporary directories to simulate real environment
        temp_dir = tempfile.mkdtemp()
        mop_dir = os.path.join(temp_dir, 'mop')
        mop_out_dir = os.path.join(temp_dir, 'mop_out')
        aspects_dir = os.path.join(temp_dir, 'aspects')

        # Create directories
        os.makedirs(mop_dir, exist_ok=True)
        os.makedirs(mop_out_dir, exist_ok=True)
        os.makedirs(aspects_dir, exist_ok=True)

        # Create test files
        with open(os.path.join(mop_dir, 'test1.mop'), 'w') as f:
            f.write('// Test MOP file')

        with open(os.path.join(mop_dir, 'test2.mop'), 'w') as f:
            f.write('// Another test MOP file')

        # Create test AspectJ file
        with open(os.path.join(aspects_dir, 'logging.aj'), 'w') as f:
            f.write('// Test AspectJ file')

        # Yield the paths to the test
        yield {
            'temp_dir': temp_dir,
            'mop_dir': mop_dir,
            'mop_out_dir': mop_out_dir,
            'aspects_dir': aspects_dir
        }

        # Clean up
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def patched_rvsec(self, setup_temp_dirs):
        """Fixture that patches RVSec with the temporary directories."""
        paths = setup_temp_dirs

        with patch('rvandroid.rvsec.MOP_DIR', paths['mop_dir']), \
                patch('rvandroid.rvsec.MOP_OUT_DIR', paths['mop_out_dir']), \
                patch('rvandroid.rvsec.ASPECTS_DIR', paths['aspects_dir']), \
                patch('rvandroid.rvsec.JAVAMOP_BIN', 'javamop'), \
                patch('rvandroid.rvsec.RV_MONITOR_BIN', 'rv-monitor'):
            yield RVSec(), paths

    def test_generate_monitors_with_command_exception(self, patched_rvsec):
        """Test handling of CommandException in generate_monitors."""
        rvsec, paths = patched_rvsec

        # Patch utils.execute_command to raise CommandException
        with patch('rvandroid.rvsec.utils.execute_command') as mock_execute_command, \
                patch('rvandroid.rvsec.utils.reset_folder'):
            # Configure the mock to raise CommandException
            mock_execute_command.side_effect = CommandException(
                "javamop", 127, "Command not found"
            )

            # Call the method and verify exception propagation
            with pytest.raises(CommandException) as excinfo:
                rvsec.generate_monitors()

            # Verify exception details
            assert excinfo.value.tool == "javamop"
            assert excinfo.value.code == 127
            assert excinfo.value.message == "Command not found"

    def test_handling_of_empty_mop_dir(self, patched_rvsec):
        """Test handling of an empty MOP directory."""
        rvsec, paths = patched_rvsec

        # Remove all files from MOP directory
        for file in os.listdir(paths['mop_dir']):
            os.remove(os.path.join(paths['mop_dir'], file))

        # Patch utils to track actual calls but not execute them
        with patch('rvandroid.rvsec.utils.execute_command') as mock_execute_command, \
                patch('rvandroid.rvsec.utils.reset_folder') as mock_reset_folder, \
                patch('rvandroid.rvsec.utils.move_files_by_extension') as mock_move, \
                patch('rvandroid.rvsec.utils.copy_files_by_extension') as mock_copy, \
                patch('rvandroid.rvsec.utils.delete_files_by_extension') as mock_delete, \
                patch('rvandroid.rvsec.Command') as mock_command:
            # Mock command object
            mock_cmd = MagicMock()
            mock_command.return_value = mock_cmd

            # Call generate_monitors
            rvsec.generate_monitors()

            # Verify that execute_command was called with empty MOP directory
            assert mock_execute_command.call_count > 0

            # Verify folder reset was called
            mock_reset_folder.assert_called_once_with(paths['mop_out_dir'])

    def test_java_mop_with_real_files(self, patched_rvsec):
        """Test __java_mop with real files instead of mocking file operations."""
        rvsec, paths = patched_rvsec

        # Create custom implementation for move_files_by_extension
        def fake_move_files(ext, src_dir, dest_dir):
            for file in os.listdir(src_dir):
                if file.endswith(ext):
                    src_path = os.path.join(src_dir, file)
                    dest_path = os.path.join(dest_dir, file)
                    shutil.copy(src_path, dest_path)

        # Create custom implementation for copy_files_by_extension
        def fake_copy_files(ext, src_dir, dest_dir, log_info=False):
            for file in os.listdir(src_dir):
                if file.endswith(ext):
                    src_path = os.path.join(src_dir, file)
                    dest_path = os.path.join(dest_dir, file)
                    shutil.copy(src_path, dest_path)

        # Create an RVM file in mop_dir to test the file moving
        rvm_file_path = os.path.join(paths['mop_dir'], 'test.rvm')
        with open(rvm_file_path, 'w') as f:
            f.write('// Test RVM file')

        # Patch only the command execution, not the file operations
        with patch('rvandroid.rvsec.utils.execute_command') as mock_execute_command, \
                patch('rvandroid.rvsec.utils.move_files_by_extension', side_effect=fake_move_files) as mock_move, \
                patch('rvandroid.rvsec.utils.copy_files_by_extension', side_effect=fake_copy_files) as mock_copy, \
                patch('rvandroid.rvsec.Command') as mock_command:

            mock_cmd = MagicMock()
            mock_command.return_value = mock_cmd

            # Call the method
            RVSec._RVSec__java_mop()

            # Verify file operations were called
            mock_move.assert_called_once_with('.rvm', paths['mop_dir'], paths['mop_out_dir'])
            mock_copy.assert_called_once_with('.aj', paths['aspects_dir'], paths['mop_out_dir'], log_info=True)

            # Verify the RVM file was moved
            assert os.path.exists(os.path.join(paths['mop_out_dir'], 'test.rvm'))

    def test_rv_monitor_with_real_files(self, patched_rvsec):
        """Test __rv_monitor with real files instead of mocking file operations."""
        rvsec, paths = patched_rvsec

        # Create custom implementation for delete_files_by_extension
        def fake_delete_files(ext, dir_path):
            for file in os.listdir(dir_path):
                if file.endswith(ext):
                    os.remove(os.path.join(dir_path, file))

        # Create RVM files in mop_out_dir to test deletion
        for i in range(3):
            rvm_file_path = os.path.join(paths['mop_out_dir'], f'test{i}.rvm')
            with open(rvm_file_path, 'w') as f:
                f.write(f'// Test RVM file {i}')

        # Verify RVM files exist before test
        assert len([f for f in os.listdir(paths['mop_out_dir']) if f.endswith('.rvm')]) == 3

        # Patch only the command execution, not the file operations
        with patch('rvandroid.rvsec.utils.execute_command') as mock_execute_command, \
                patch('rvandroid.rvsec.utils.delete_files_by_extension', side_effect=fake_delete_files) as mock_delete, \
                patch('rvandroid.rvsec.Command') as mock_command:

            mock_cmd = MagicMock()
            mock_command.return_value = mock_cmd

            # Call the method
            RVSec._RVSec__rv_monitor()

            # Verify file deletion was called
            mock_delete.assert_called_once_with('.rvm', paths['mop_out_dir'])

            # Verify the RVM files were deleted
            assert len([f for f in os.listdir(paths['mop_out_dir']) if f.endswith('.rvm')]) == 0

    def test_complete_workflow_with_mocked_commands(self, patched_rvsec):
        """Test the complete workflow with mocked commands but real file operations."""
        rvsec, paths = patched_rvsec

        # Create custom implementations for file operations
        def fake_reset_folder(dir_path):
            if os.path.exists(dir_path):
                for item in os.listdir(dir_path):
                    item_path = os.path.join(dir_path, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    else:
                        shutil.rmtree(item_path)
            else:
                os.makedirs(dir_path, exist_ok=True)

        def fake_move_files(ext, src_dir, dest_dir):
            for file in os.listdir(src_dir):
                if file.endswith(ext):
                    src_path = os.path.join(src_dir, file)
                    dest_path = os.path.join(dest_dir, file)
                    shutil.copy(src_path, dest_path)

        def fake_copy_files(ext, src_dir, dest_dir, log_info=False):
            for file in os.listdir(src_dir):
                if file.endswith(ext):
                    src_path = os.path.join(src_dir, file)
                    dest_path = os.path.join(dest_dir, file)
                    shutil.copy(src_path, dest_path)

        def fake_delete_files(ext, dir_path):
            for file in os.listdir(dir_path):
                if file.endswith(ext):
                    os.remove(os.path.join(dir_path, file))

        # Create an RVM file to test file movement
        rvm_file_path = os.path.join(paths['mop_dir'], 'test.rvm')
        with open(rvm_file_path, 'w') as f:
            f.write('// Test RVM file')

        # Patch utils methods with our custom implementations
        with patch('rvandroid.rvsec.utils.reset_folder', side_effect=fake_reset_folder) as mock_reset, \
                patch('rvandroid.rvsec.utils.move_files_by_extension', side_effect=fake_move_files) as mock_move, \
                patch('rvandroid.rvsec.utils.copy_files_by_extension', side_effect=fake_copy_files) as mock_copy, \
                patch('rvandroid.rvsec.utils.delete_files_by_extension', side_effect=fake_delete_files) as mock_delete, \
                patch('rvandroid.rvsec.utils.execute_command') as mock_execute, \
                patch('rvandroid.rvsec.Command') as mock_command:

            # Mock command execution
            mock_cmd = MagicMock()
            mock_command.return_value = mock_cmd

            # Execute the full generate_monitors workflow
            rvsec.generate_monitors()

            # Verify reset_folder was called
            mock_reset.assert_called_once_with(paths['mop_out_dir'])

            # Verify both JavaMOP and RV-Monitor commands were created
            assert mock_command.call_count == 2

            # Verify file operations were performed
            mock_move.assert_called_once()
            mock_copy.assert_called_once()
            mock_delete.assert_called_once()

            # Verify execute_command was called twice (once for JavaMOP, once for RV-Monitor)
            assert mock_execute.call_count == 2

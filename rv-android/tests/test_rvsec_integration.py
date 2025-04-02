import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from rvandroid.commands.command_exception import CommandException
from rvandroid.rvsec import RVSec


class TestRVSecIntegration:
    """Integration tests for the RVSec class with real filesystem operations."""

    @pytest.fixture
    def temp_env(self):
        """Create a temporary environment for testing with real files."""
        # Create temporary directory structure
        base_dir = tempfile.mkdtemp()
        mop_dir = os.path.join(base_dir, 'mop')
        mop_out_dir = os.path.join(base_dir, 'mop_out')
        aspects_dir = os.path.join(base_dir, 'aspects')

        # Create the directories
        os.makedirs(mop_dir)
        os.makedirs(mop_out_dir)
        os.makedirs(aspects_dir)

        # Create test files
        # Create MOP files
        for i in range(2):
            mop_path = os.path.join(mop_dir, f'test{i}.mop')
            with open(mop_path, 'w') as f:
                f.write(f'// Test MOP file {i}')

        # Create RVM file (simulating JavaMOP output)
        rvm_path = os.path.join(mop_dir, 'test.rvm')
        with open(rvm_path, 'w') as f:
            f.write('// Test RVM file')

        # Create AspectJ file
        aj_path = os.path.join(aspects_dir, 'logging.aj')
        with open(aj_path, 'w') as f:
            f.write('// Test AspectJ file')

        # Return the paths
        env = {
            'base_dir': base_dir,
            'mop_dir': mop_dir,
            'mop_out_dir': mop_out_dir,
            'aspects_dir': aspects_dir
        }

        yield env

        # Cleanup after the test
        shutil.rmtree(base_dir)

    @pytest.fixture
    def patched_paths(self, temp_env):
        """Patch RVSec to use the temporary environment."""
        with patch('rvandroid.rvsec.MOP_DIR', temp_env['mop_dir']), \
                patch('rvandroid.rvsec.MOP_OUT_DIR', temp_env['mop_out_dir']), \
                patch('rvandroid.rvsec.ASPECTS_DIR', temp_env['aspects_dir']), \
                patch('rvandroid.rvsec.JAVAMOP_BIN', 'javamop'), \
                patch('rvandroid.rvsec.RV_MONITOR_BIN', 'rvmonitor'):
            yield

    def test_java_mop_real_filesystem(self, temp_env, patched_paths):
        """Test __java_mop with real filesystem operations but mocked commands."""

        # Create custom implementations for file operations to use real filesystem
        def real_move_files(ext, src_dir, dest_dir):
            for file in os.listdir(src_dir):
                if file.endswith(ext):
                    src_path = os.path.join(src_dir, file)
                    dest_path = os.path.join(dest_dir, file)
                    shutil.copy2(src_path, dest_path)

        def real_copy_files(ext, src_dir, dest_dir, log_info=False):
            for file in os.listdir(src_dir):
                if file.endswith(ext):
                    src_path = os.path.join(src_dir, file)
                    dest_path = os.path.join(dest_dir, file)
                    shutil.copy2(src_path, dest_path)

        # Patch only command execution, use real file operations
        with patch('rvandroid.rvsec.Command') as mock_command, \
                patch('rvandroid.rvsec.utils.execute_command') as mock_execute, \
                patch('rvandroid.rvsec.utils.move_files_by_extension', side_effect=real_move_files), \
                patch('rvandroid.rvsec.utils.copy_files_by_extension', side_effect=real_copy_files):

            # Setup command mock
            mock_cmd = MagicMock()
            mock_command.return_value = mock_cmd

            # Call the method
            RVSec._RVSec__java_mop()

            # Verify that the files were copied to the output directory
            assert os.path.exists(os.path.join(temp_env['mop_out_dir'], 'test.rvm'))
            assert os.path.exists(os.path.join(temp_env['mop_out_dir'], 'logging.aj'))

            # Verify command execution
            mock_execute.assert_called_once()

    def test_rv_monitor_real_filesystem(self, temp_env, patched_paths):
        """Test __rv_monitor with real filesystem operations but mocked commands."""

        # Create custom implementation for file deletion to use real filesystem
        def real_delete_files(ext, dir_path):
            for file in os.listdir(dir_path):
                if file.endswith(ext):
                    os.remove(os.path.join(dir_path, file))

        # Create test RVM files in the output directory
        for i in range(3):
            rvm_path = os.path.join(temp_env['mop_out_dir'], f'test{i}.rvm')
            with open(rvm_path, 'w') as f:
                f.write(f'// Test RVM file {i}')

        # Verify RVM files exist before test
        assert len([f for f in os.listdir(temp_env['mop_out_dir']) if f.endswith('.rvm')]) == 3

        # Patch only command execution, use real file operations
        with patch('rvandroid.rvsec.Command') as mock_command, \
                patch('rvandroid.rvsec.utils.execute_command') as mock_execute, \
                patch('rvandroid.rvsec.utils.delete_files_by_extension', side_effect=real_delete_files):

            # Setup command mock
            mock_cmd = MagicMock()
            mock_command.return_value = mock_cmd

            # Call the method
            RVSec._RVSec__rv_monitor()

            # Verify that the RVM files were deleted
            assert len([f for f in os.listdir(temp_env['mop_out_dir']) if f.endswith('.rvm')]) == 0

            # Verify command execution
            mock_execute.assert_called_once()

    def test_generate_monitors_full_process(self, temp_env, patched_paths):
        """Test the full generate_monitors process with real filesystem but mocked commands."""

        # Create custom implementations for file operations
        def real_reset_folder(dir_path):
            if os.path.exists(dir_path):
                # Clear directory contents
                for item in os.listdir(dir_path):
                    item_path = os.path.join(dir_path, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    else:
                        shutil.rmtree(item_path)
            else:
                os.makedirs(dir_path)

        def real_move_files(ext, src_dir, dest_dir):
            for file in os.listdir(src_dir):
                if file.endswith(ext):
                    src_path = os.path.join(src_dir, file)
                    dest_path = os.path.join(dest_dir, file)
                    shutil.copy2(src_path, dest_path)

        def real_copy_files(ext, src_dir, dest_dir, log_info=False):
            for file in os.listdir(src_dir):
                if file.endswith(ext):
                    src_path = os.path.join(src_dir, file)
                    dest_path = os.path.join(dest_dir, file)
                    shutil.copy2(src_path, dest_path)

        def real_delete_files(ext, dir_path):
            for file in os.listdir(dir_path):
                if file.endswith(ext):
                    os.remove(os.path.join(dir_path, file))

        # Create a test file to verify reset_folder works
        test_file_path = os.path.join(temp_env['mop_out_dir'], 'test_file.txt')
        with open(test_file_path, 'w') as f:
            f.write('This file should be deleted by reset_folder')

        # Patch utils methods with real filesystem operations
        with patch('rvandroid.rvsec.Command') as mock_command, \
                patch('rvandroid.rvsec.utils.execute_command') as mock_execute, \
                patch('rvandroid.rvsec.utils.reset_folder', side_effect=real_reset_folder), \
                patch('rvandroid.rvsec.utils.move_files_by_extension', side_effect=real_move_files), \
                patch('rvandroid.rvsec.utils.copy_files_by_extension', side_effect=real_copy_files), \
                patch('rvandroid.rvsec.utils.delete_files_by_extension', side_effect=real_delete_files):

            # Setup command mock
            mock_cmd = MagicMock()
            mock_command.return_value = mock_cmd

            # Create RVSec instance and call generate_monitors
            rvsec = RVSec()
            rvsec.generate_monitors()

            # Verify that reset_folder worked
            assert not os.path.exists(test_file_path)

            # Verify that the MOP directory was processed
            # First check the AspectJ file was copied
            assert os.path.exists(os.path.join(temp_env['mop_out_dir'], 'logging.aj'))

            # Check that RVM files are gone (should be deleted by rv_monitor)
            assert len([f for f in os.listdir(temp_env['mop_out_dir']) if f.endswith('.rvm')]) == 0

            # Verify command execution count (once for JavaMOP, once for RV-Monitor)
            assert mock_execute.call_count == 2

    def test_command_exception_handling(self, temp_env, patched_paths):
        """Test handling of CommandException during generate_monitors."""
        # Create RVSec instance
        rvsec = RVSec()

        # Patch utils methods
        with patch('rvandroid.rvsec.utils.reset_folder'), \
                patch('rvandroid.rvsec.utils.execute_command') as mock_execute, \
                patch('rvandroid.rvsec.Command'):
            # Configure first command execution to fail with CommandException
            mock_execute.side_effect = CommandException("javamop", 1, "Failed to process MOP files")

            # Call generate_monitors and verify exception propagation
            with pytest.raises(CommandException) as excinfo:
                rvsec.generate_monitors()

            # Verify exception details
            assert excinfo.value.tool == "javamop"
            assert excinfo.value.message == "Failed to process MOP files"

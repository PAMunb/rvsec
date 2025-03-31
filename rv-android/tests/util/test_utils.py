"""
Unit tests for the utils module.

This module contains comprehensive tests for utility functions
used across the RV-Android framework.

### Test Strategy:
- Cover all utility functions with varied input scenarios
- Test both successful and failure cases
- Validate file and directory operations
- Ensure proper error handling and edge cases
"""

import json
import os
import tempfile
from unittest.mock import Mock

import pytest

from rvandroid.commands.command import Command
from rvandroid.commands.command_exception import CommandException
from rvandroid.constants import EXTENSION_APK
from rvandroid.util import utils


class TestUtils:
    """
    Comprehensive unit tests for the utils module.

    ### Test Strategy:
    - Cover all utility functions with varied input scenarios
    - Test both successful and failure cases
    - Validate file and directory operations
    - Ensure proper error handling
    """

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for file operations."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            yield tmpdirname

    def test_execute_command_success(self, monkeypatch):
        """
        Test successful command execution.

        Validates that:
        - Command is executed without exceptions
        - Logging occurs correctly
        """
        # Create mock logging
        mock_logger = Mock()
        mock_logging_manager = Mock()
        mock_logging_manager.get_logger.return_value = mock_logger

        # Patch logging manager
        monkeypatch.setattr(
            'rvandroid.util.utils.logging_manager',
            mock_logging_manager
        )

        # Create a mock Command with expected behavior
        mock_result = Mock()
        mock_result.code = 0
        mock_result.stderr = b''
        mock_cmd = Mock(spec=Command)
        mock_cmd.invoke.return_value = mock_result
        mock_cmd.command = "test_command"
        mock_cmd.args = ["arg1", "arg2"]

        # Execute the utility function
        try:
            utils.execute_command(mock_cmd, "test_tag")
        except Exception as e:
            pytest.fail(f"Unexpected exception raised: {e}")

        # Verify command was invoked
        mock_cmd.invoke.assert_called_once_with(stdout=None)

        # Verify logging
        mock_logger.debug.assert_any_call(
            f"Executing command: {mock_cmd.command} {' '.join(mock_cmd.args)}"
        )
        mock_logger.debug.assert_any_call("Command executed successfully")

    def test_execute_command_failure(self, monkeypatch):
        """
        Test command execution failure.

        Validates that:
        - CommandException is raised on non-zero exit code
        - Error details are captured correctly
        """
        # Create mock logging
        mock_logger = Mock()
        mock_logging_manager = Mock()
        mock_logging_manager.get_logger.return_value = mock_logger

        # Patch logging manager
        monkeypatch.setattr(
            'rvandroid.util.utils.logging_manager',
            mock_logging_manager
        )

        # Create a mock Command with failure scenario
        mock_result = Mock()
        mock_result.code = 1
        mock_result.stderr = b'Test error message'
        mock_cmd = Mock(spec=Command)
        mock_cmd.invoke.return_value = mock_result
        mock_cmd.command = "test_command"
        mock_cmd.args = ["arg1", "arg2"]

        # Attempt to execute and expect CommandException
        with pytest.raises(CommandException) as excinfo:
            utils.execute_command(mock_cmd, "test_tag")

        # Verify exception details
        expected_str = "CommandException[tool=test_tag ::: code=1 ::: message=Test error message]"
        assert str(excinfo.value) == expected_str
        assert excinfo.value.tool == "test_tag"
        assert excinfo.value.code == 1
        assert excinfo.value.message == "Test error message"

        # Verify logging
        mock_logger.debug.assert_any_call(
            f"Executing command: {mock_cmd.command} {' '.join(mock_cmd.args)}"
        )
        mock_logger.error.assert_called_once()

    def test_file_hash_success(self, temp_dir):
        """
        Test file hash generation.

        Validates that:
        - Hash is generated correctly
        - Works with different file contents
        """
        # Create a test file
        test_file_path = os.path.join(temp_dir, "test_hash.txt")
        with open(test_file_path, 'w') as f:
            f.write("Test content")

        # Generate hash
        file_hash = utils.file_hash(test_file_path)

        # Verify hash generation
        assert isinstance(file_hash, str)
        assert len(file_hash) == 64  # SHA-256 hash length

        # Regenerate and compare
        same_hash = utils.file_hash(test_file_path)
        assert file_hash == same_hash

    def test_file_hash_nonexistent_file(self):
        """
        Test file hash generation for non-existent file.

        Validates that:
        - Appropriate exception is raised
        """
        with pytest.raises(FileNotFoundError):
            utils.file_hash("/path/to/nonexistent/file")

    def test_create_folder_if_not_exists(self, temp_dir):
        """
        Test folder creation utility.

        Validates that:
        - Folder is created when it doesn't exist
        - No error occurs when folder already exists
        """
        new_folder = os.path.join(temp_dir, "new_folder")

        # First call should create the folder
        utils.create_folder_if_not_exists(new_folder)
        assert os.path.exists(new_folder)
        assert os.path.isdir(new_folder)

        # Second call should not raise an exception
        try:
            utils.create_folder_if_not_exists(new_folder)
        except Exception as e:
            pytest.fail(f"Unexpected exception: {e}")

    def test_reset_folder(self, temp_dir):
        """
        Test folder reset utility.

        Validates that:
        - Existing folder is cleared
        - New empty folder is created
        """
        test_folder = os.path.join(temp_dir, "test_reset")
        os.makedirs(test_folder)

        # Create some files
        open(os.path.join(test_folder, "file1.txt"), 'w').close()
        open(os.path.join(test_folder, "file2.txt"), 'w').close()

        # Reset the folder
        utils.reset_folder(test_folder)

        # Verify folder exists and is empty
        assert os.path.exists(test_folder)
        assert os.path.isdir(test_folder)
        assert len(os.listdir(test_folder)) == 0

    def test_move_files_by_extension(self, temp_dir):
        """
        Test moving files by extension.

        Validates that:
        - Files with specified extension are moved
        - Only matching files are moved
        """
        source_dir = os.path.join(temp_dir, "source")
        dest_dir = os.path.join(temp_dir, "destination")
        os.makedirs(source_dir)
        os.makedirs(dest_dir)

        # Create test files
        open(os.path.join(source_dir, "file1.txt"), 'w').close()
        open(os.path.join(source_dir, "file2.txt"), 'w').close()
        open(os.path.join(source_dir, "file3.log"), 'w').close()

        # Move .txt files
        utils.move_files_by_extension(".txt", source_dir, dest_dir)

        # Verify files
        assert len(os.listdir(source_dir)) == 1  # Only .log file remains
        assert len(os.listdir(dest_dir)) == 2  # Two .txt files moved

    def test_to_readable_time(self):
        """
        Test conversion of seconds to human-readable time.

        Validates different time ranges.
        """
        # Test seconds
        assert utils.to_readable_time(30) == "30 seconds"

        # Test minutes
        assert utils.to_readable_time(125) == "2 minutes and 5 seconds"

        # Test hours
        assert utils.to_readable_time(3661) == "1 hours, 1 minutes and 1 seconds"

    def test_get_env_or_default(self, monkeypatch):
        """
        Test environment variable retrieval with defaults.

        Validates different type conversions and default handling.
        """
        # Mock environment variables
        monkeypatch.setenv('TEST_STR', 'value')
        monkeypatch.setenv('TEST_INT', '42')
        monkeypatch.setenv('TEST_BOOL', 'true')

        # String conversion
        assert utils.get_env_or_default('TEST_STR', 'default') == 'value'

        # Integer conversion
        assert utils.get_env_or_default('TEST_INT', 0, value_type=int) == 42

        # Boolean conversion
        assert utils.get_env_or_default('TEST_BOOL', False, value_type=bool) is True

        # Default when not set
        assert utils.get_env_or_default('UNSET_VAR', 'default') == 'default'

    def test_read_json(self, temp_dir):
        """
        Test JSON file reading.

        Validates:
        - Successful JSON parsing
        - Error handling for invalid files
        """
        # Valid JSON file
        valid_json_path = os.path.join(temp_dir, "valid.json")
        with open(valid_json_path, 'w') as f:
            json.dump({"key": "value"}, f)

        # Read valid JSON
        data = utils.read_json(valid_json_path)
        assert data == {"key": "value"}

        # Non-existent file
        non_existent_path = os.path.join(temp_dir, "nonexistent.json")
        data = utils.read_json(non_existent_path)
        assert data == {}

        # Invalid JSON file
        invalid_json_path = os.path.join(temp_dir, "invalid.json")
        with open(invalid_json_path, 'w') as f:
            f.write("{invalid json")

        data = utils.read_json(invalid_json_path)
        assert data == {}

    def test_get_apks(self, temp_dir, monkeypatch):
        """
        Test APK file retrieval.

        Validates that:
        - Only APK files are returned
        - App objects are created correctly
        """
        # Create APK-like files
        apk_contents = b'\x50\x4b\x03\x04\x14\x00\x08\x00\x08\x00'  # Minimal valid ZIP/APK header

        # Create files with APK extension
        apk_paths = [
            os.path.join(temp_dir, "app1.apk"),
            os.path.join(temp_dir, "app2.APK"),
            os.path.join(temp_dir, "not_an_apk.txt")
        ]

        # Write APK-like content to first two files
        for path in apk_paths[:2]:
            with open(path, 'wb') as f:
                f.write(apk_contents)

        # Create a non-APK file
        open(apk_paths[2], 'w').close()

        # Create a mock App class
        def mock_app_init(path):
            mock_app = Mock()
            mock_app.path = path
            mock_app.name = os.path.basename(path)
            return mock_app

        # Patch App initialization
        monkeypatch.setattr('rvandroid.util.utils.App', mock_app_init)

        # Patch Androguard APK parsing to always succeed
        def mock_apk_init(path):
            mock_apk = Mock()
            mock_apk.get_package.return_value = 'test.package'
            mock_apk.get_effective_target_sdk_version.return_value = 30
            mock_apk.get_permissions.return_value = []
            mock_apk.get_min_sdk_version.return_value = 21
            return mock_apk

        monkeypatch.setattr('rvandroid.app.APK', mock_apk_init)

        # Retrieve APKs
        apks = utils.get_apks(temp_dir)

        # Verify
        assert len(apks) == 2, f"Expected 2 APKs, found {len(apks)}"
        assert all(apk.name.lower().endswith(EXTENSION_APK) for apk in apks)

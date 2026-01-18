import pytest
from unittest.mock import MagicMock, patch, call
import os
import shutil
import hashlib
import json
from datetime import datetime, timezone
from zipfile import ZipFile, ZIP_DEFLATED

from rv_android_core.util.utils import (
    execute_command,
    file_hash,
    create_folder_if_not_exists,
    reset_folder,
    move_files_by_extension,
    copy_files_by_extension,
    copy_files,
    delete_files_by_extension,
    delete_file,
    delete_dir,
    check_folder_exists,
    get_apks,
    unzip,
    zip_dir_content,
    to_readable_time,
    datetime_to_milliseconds,
    datetime_to_string,
    milliseconds_to_datetime,
    get_env_or_default,
    get_env_or_exception,
    read_json,
)
from rv_android_core.commands.command import Command
from rv_android_core.commands.command_exception import CommandException
from rv_android_core.domain.app import App
from rv_android_core.constants import EXTENSION_APK
from rv_android_core.util.error.exceptions import RVAndroidError
from rv_android_core.util.logging.manager import LoggingManager


# Mock LoggingManager globally
@pytest.fixture(autouse=True)
def mock_logging_manager(monkeypatch):
    mock_manager = MagicMock()
    mock_logger_instance = MagicMock()
    mock_manager.get_logger.return_value = mock_logger_instance
    monkeypatch.setattr("rv_android_core.util.utils.logging_manager", mock_manager)
    yield mock_manager


# Mock os and shutil functions
@pytest.fixture(autouse=True)
def mock_os_shutil():
    with patch("os.path.exists") as mock_exists, patch(
        "os.makedirs"
    ) as mock_makedirs, patch("os.listdir") as mock_listdir, patch(
        "os.remove"
    ) as mock_remove, patch(
        "os.getenv"
    ) as mock_getenv, patch(
        "shutil.rmtree"
    ) as mock_rmtree, patch(
        "shutil.move"
    ) as mock_move, patch(
        "shutil.copy2"
    ) as mock_copy2, patch(
        "os.path.isfile"
    ) as mock_isfile, patch(
        "os.path.isdir"
    ) as mock_isdir, patch(
        "os.walk"
    ) as mock_walk, patch(
        "os.path.relpath"
    ) as mock_relpath, patch(
        "os.stat"
    ) as mock_stat:
        yield {
            "exists": mock_exists,
            "makedirs": mock_makedirs,
            "listdir": mock_listdir,
            "remove": mock_remove,
            "getenv": mock_getenv,
            "rmtree": mock_rmtree,
            "move": mock_move,
            "copy2": mock_copy2,
            "isfile": mock_isfile,
            "isdir": mock_isdir,
            "walk": mock_walk,
            "relpath": mock_relpath,
            "stat": mock_stat,
        }


# Mock Command class
@pytest.fixture
def mock_command_class():
    with patch("rv_android_core.util.utils.Command") as mock_cmd:
        yield mock_cmd


# Mock App class
@pytest.fixture
def mock_app_class():
    with patch("rv_android_core.util.utils.App") as mock_app:
        yield mock_app


class TestUtils:

    # Tests for execute_command
    def test_execute_command_success(self, mock_command_class, mock_logging_manager):
        mock_cmd_instance = MagicMock()
        mock_cmd_instance.invoke.return_value = MagicMock(
            code=0, stdout=b"output", stderr=b""
        )
        mock_command_class.return_value = mock_cmd_instance

        result = execute_command(mock_cmd_instance, "test_tag")
        mock_cmd_instance.invoke.assert_called_once()
        assert result.stdout == b"output"
        mock_logging_manager.get_logger.return_value.debug.assert_called_with(
            "Command executed successfully"
        )

    def test_execute_command_failure_with_stderr(
        self, mock_command_class, mock_logging_manager
    ):
        mock_cmd_instance = MagicMock()
        mock_cmd_instance.invoke.return_value = MagicMock(
            code=1, stdout=b"", stderr=b"error"
        )
        mock_command_class.return_value = mock_cmd_instance

        with pytest.raises(CommandException) as excinfo:
            execute_command(mock_cmd_instance, "test_tag")
        assert excinfo.value.tool == "test_tag"
        assert excinfo.value.code == 1
        assert "error" in excinfo.value.message
        mock_logging_manager.get_logger.return_value.error.assert_called_once_with(
            "Command execution failed: error"
        )

    def test_execute_command_failure_without_stderr_check(
        self, mock_command_class, mock_logging_manager
    ):
        mock_cmd_instance = MagicMock()
        mock_cmd_instance.invoke.return_value = MagicMock(
            code=1, stdout=b"", stderr=b"error"
        )
        mock_command_class.return_value = mock_cmd_instance

        result = execute_command(mock_cmd_instance, "test_tag", skip_stderr=True)
        mock_cmd_instance.invoke.assert_called_once()
        assert result.code == 1
        mock_logging_manager.get_logger.return_value.debug.assert_called_with(
            "Command executed successfully"
        )

    # Tests for file_hash
    def test_file_hash_success(self, mock_logging_manager):
        mock_file_content = b"test content"
        with patch("builtins.open", MagicMock()) as mock_open:
            mock_open.return_value.__enter__.return_value.read.side_effect = [
                mock_file_content,
                b"",
            ]
            expected_hash = hashlib.sha256(mock_file_content).hexdigest()

            result = file_hash("dummy_path.txt")
            assert result == expected_hash
            mock_logging_manager.get_logger.return_value.error.assert_not_called()

    def test_file_hash_file_not_found(self, mock_logging_manager):
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                file_hash("non_existent.txt")
            mock_logging_manager.get_logger.return_value.error.assert_called_once()

    # Tests for create_folder_if_not_exists
    def test_create_folder_if_not_exists_new_folder(
        self, mock_os_shutil, mock_logging_manager
    ):
        mock_os_shutil["exists"].return_value = False
        create_folder_if_not_exists("/new/path")
        mock_os_shutil["makedirs"].assert_called_once_with("/new/path")
        mock_logging_manager.get_logger.return_value.debug.assert_called_with(
            "Creating folder: /new/path"
        )

    def test_create_folder_if_not_exists_folder_exists(
        self, mock_os_shutil, mock_logging_manager
    ):
        mock_os_shutil["exists"].return_value = True
        create_folder_if_not_exists("/existing/path")
        mock_os_shutil["makedirs"].assert_not_called()
        mock_logging_manager.get_logger.return_value.debug.assert_not_called()

    def test_create_folder_if_not_exists_os_error(
        self, mock_os_shutil, mock_logging_manager
    ):
        mock_os_shutil["exists"].return_value = False
        mock_os_shutil["makedirs"].side_effect = OSError("Permission denied")
        with pytest.raises(OSError):
            create_folder_if_not_exists("/protected/path")
        mock_logging_manager.get_logger.return_value.error.assert_called_once()

    # Tests for reset_folder
    def test_reset_folder(self, mock_os_shutil, mock_logging_manager):
        reset_folder("/test/path")
        mock_os_shutil["rmtree"].assert_called_once_with(
            "/test/path", ignore_errors=True
        )
        mock_os_shutil["makedirs"].assert_called_once_with("/test/path")
        mock_logging_manager.get_logger.return_value.debug.assert_called_with(
            "Resetting folder: /test/path"
        )

    # Tests for move_files_by_extension
    def test_move_files_by_extension_success(
        self, mock_os_shutil, mock_logging_manager
    ):
        mock_os_shutil["exists"].return_value = True
        mock_os_shutil["listdir"].return_value = ["file1.txt", "file2.log", "file3.txt"]

        with patch(
            "rv_android_core.util.utils.check_folder_exists"
        ) as mock_check_folder_exists:
            move_files_by_extension(".txt", "/src", "/dest")
            mock_check_folder_exists.assert_called_once_with(["/src", "/dest"])
            assert mock_os_shutil["move"].call_count == 2
            mock_os_shutil["move"].assert_has_calls(
                [
                    call(os.path.join("/src", "file1.txt"), "/dest"),
                    call(os.path.join("/src", "file3.txt"), "/dest"),
                ],
                any_order=True,
            )
            mock_logging_manager.get_logger.return_value.debug.assert_called_with(
                "Moved 2 files"
            )

    def test_move_files_by_extension_no_match(
        self, mock_os_shutil, mock_logging_manager
    ):
        mock_os_shutil["exists"].return_value = True
        mock_os_shutil["listdir"].return_value = ["file1.log", "file2.log"]
        with patch("rv_android_core.util.utils.check_folder_exists"):
            move_files_by_extension(".txt", "/src", "/dest")
            mock_os_shutil["move"].assert_not_called()
            mock_logging_manager.get_logger.return_value.debug.assert_called_with(
                "Moved 0 files"
            )

    def test_move_files_by_extension_os_error(
        self, mock_os_shutil, mock_logging_manager
    ):
        mock_os_shutil["exists"].return_value = True
        mock_os_shutil["listdir"].return_value = ["file1.txt"]
        mock_os_shutil["move"].side_effect = OSError("Disk full")
        with patch("rv_android_core.util.utils.check_folder_exists"):
            with pytest.raises(Exception) as excinfo:
                move_files_by_extension(".txt", "/src", "/dest")
            assert "Disk full" in str(excinfo.value)
            mock_logging_manager.get_logger.return_value.error.assert_called_once()

    # Tests for copy_files_by_extension
    def test_copy_files_by_extension_success(
        self, mock_os_shutil, mock_logging_manager
    ):
        mock_os_shutil["exists"].return_value = True
        mock_os_shutil["listdir"].return_value = ["file1.txt", "file2.log", "file3.txt"]
        with patch("rv_android_core.util.utils.check_folder_exists"):
            copy_files_by_extension(".txt", "/src", "/dest")
            assert mock_os_shutil["copy2"].call_count == 2
            mock_os_shutil["copy2"].assert_has_calls(
                [
                    call(os.path.join("/src", "file1.txt"), "/dest"),
                    call(os.path.join("/src", "file3.txt"), "/dest"),
                ],
                any_order=True,
            )
            mock_logging_manager.get_logger.return_value.debug.assert_called_with(
                "Copied 2 files with extension .txt"
            )

    def test_copy_files_by_extension_log_info(
        self, mock_os_shutil, mock_logging_manager
    ):
        mock_os_shutil["exists"].return_value = True
        mock_os_shutil["listdir"].return_value = ["file1.txt"]
        with patch("rv_android_core.util.utils.check_folder_exists"):
            copy_files_by_extension(".txt", "/src", "/dest", log_info=True)
            mock_logging_manager.get_logger.return_value.info.assert_called_with(
                "Copying 'file1.txt' to /dest"
            )

    # Tests for copy_files
    def test_copy_files_success(self, mock_os_shutil, mock_logging_manager):
        mock_os_shutil["exists"].return_value = True
        mock_os_shutil["listdir"].return_value = ["file1.txt", "dir1"]
        mock_os_shutil["isfile"].side_effect = lambda x: x.endswith(".txt")
        with patch("rv_android_core.util.utils.check_folder_exists"):
            copy_files("/src", "/dest")
            mock_os_shutil["copy2"].assert_called_once_with(
                os.path.join("/src", "file1.txt"), "/dest"
            )
            mock_logging_manager.get_logger.return_value.debug.assert_called_with(
                "Copied 1 files"
            )

    # Tests for delete_files_by_extension
    def test_delete_files_by_extension_success(
        self, mock_os_shutil, mock_logging_manager
    ):
        mock_os_shutil["exists"].return_value = True
        mock_os_shutil["listdir"].return_value = ["file1.txt", "file2.log", "file3.txt"]
        with patch("rv_android_core.util.utils.check_folder_exists"):
            delete_files_by_extension(".txt", "/src")
            assert mock_os_shutil["remove"].call_count == 2
            mock_os_shutil["remove"].assert_has_calls(
                [
                    call(os.path.join("/src", "file1.txt")),
                    call(os.path.join("/src", "file3.txt")),
                ],
                any_order=True,
            )
            mock_logging_manager.get_logger.return_value.debug.assert_called_with(
                "Deleted 2 files with extension .txt"
            )

    # Tests for delete_file
    def test_delete_file_exists(self, mock_os_shutil, mock_logging_manager):
        mock_os_shutil["exists"].return_value = True
        delete_file("/path/to/file.txt")
        mock_os_shutil["remove"].assert_called_once_with("/path/to/file.txt")
        mock_logging_manager.get_logger.return_value.debug.assert_called_with(
            "Deleted file: /path/to/file.txt"
        )

    def test_delete_file_not_exists(self, mock_os_shutil, mock_logging_manager):
        mock_os_shutil["exists"].return_value = False
        delete_file("/path/to/non_existent.txt")
        mock_os_shutil["remove"].assert_not_called()

    # Tests for delete_dir
    def test_delete_dir_exists(self, mock_os_shutil, mock_logging_manager):
        mock_os_shutil["exists"].return_value = True
        mock_os_shutil["isdir"].return_value = True
        delete_dir("/path/to/dir")
        mock_os_shutil["rmtree"].assert_called_once_with("/path/to/dir")
        mock_logging_manager.get_logger.return_value.debug.assert_called_with(
            "Deleted directory: /path/to/dir"
        )

    def test_delete_dir_not_exists(self, mock_os_shutil, mock_logging_manager):
        mock_os_shutil["exists"].return_value = False
        delete_dir("/path/to/non_existent_dir")
        mock_os_shutil["rmtree"].assert_not_called()

    # Tests for check_folder_exists
    def test_check_folder_exists_all_exist(self, mock_os_shutil):
        mock_os_shutil["exists"].return_value = True
        check_folder_exists(["/path1", "/path2"])
        assert mock_os_shutil["exists"].call_count == 2

    def test_check_folder_exists_one_missing(
        self, mock_os_shutil, mock_logging_manager
    ):
        mock_os_shutil["exists"].side_effect = [True, False]
        with pytest.raises(Exception) as excinfo:
            check_folder_exists(["/path1", "/path2"])
        assert "Folder does not exist: /path2" in str(excinfo.value)
        mock_logging_manager.get_logger.return_value.error.assert_called_once_with(
            "Folder does not exist: /path2"
        )

    # Tests for get_apks
    def test_get_apks_success(
        self, mock_os_shutil, mock_app_class, mock_logging_manager
    ):
        mock_os_shutil["exists"].return_value = True
        mock_os_shutil["isdir"].return_value = True
        mock_os_shutil["listdir"].return_value = ["app1.apk", "not_apk.txt", "app2.APK"]
        mock_app_instance1 = MagicMock(spec=App)
        mock_app_instance2 = MagicMock(spec=App)
        mock_app_class.side_effect = [mock_app_instance1, mock_app_instance2]

        apks = get_apks("/apks")
        assert len(apks) == 2
        assert apks[0] == mock_app_instance1
        assert apks[1] == mock_app_instance2
        mock_logging_manager.get_logger.return_value.info.assert_called_with(
            "Found 2 APK files in /apks"
        )

    def test_get_apks_empty_dir(self, mock_os_shutil, mock_logging_manager):
        mock_os_shutil["exists"].return_value = True
        mock_os_shutil["isdir"].return_value = True
        mock_os_shutil["listdir"].return_value = ["not_apk.txt"]
        apks = get_apks("/apks")
        assert len(apks) == 0
        mock_logging_manager.get_logger.return_value.info.assert_called_with(
            "Found 0 APK files in /apks"
        )

    def test_get_apks_non_existent_dir(self, mock_os_shutil, mock_logging_manager):
        mock_os_shutil["exists"].return_value = False
        apks = get_apks("/non_existent")
        assert len(apks) == 0
        mock_logging_manager.get_logger.return_value.info.assert_called_with(
            "Found 0 APK files in /non_existent"
        )

    # Tests for unzip
    def test_unzip_success(self, mock_logging_manager):
        mock_zip_file_instance = MagicMock()
        with patch("zipfile.ZipFile", autospec=True) as mock_zipfile_class:
            mock_zipfile_class.return_value.__enter__.return_value = (
                mock_zip_file_instance
            )
            unzip("test.zip", "/out")
            mock_zipfile_class.assert_called_once_with("test.zip", "r")
            mock_zip_file_instance.extractall.assert_called_once_with(path="/out")
            mock_logging_manager.get_logger.return_value.debug.assert_called_with(
                "Extraction completed successfully"
            )

    def test_unzip_failure(self, mock_logging_manager):
        with patch("zipfile.ZipFile", autospec=True) as mock_zipfile_class:
            mock_zipfile_class.side_effect = Exception("Corrupt zip")
            with pytest.raises(Exception) as excinfo:
                unzip("corrupt.zip", "/out")
            assert "Corrupt zip" in str(excinfo.value)
            mock_logging_manager.get_logger.return_value.error.assert_called_once()

    # Tests for zip_dir_content
    def test_zip_dir_content_success(self, mock_os_shutil, mock_logging_manager):
        mock_os_shutil["walk"].return_value = [("/in", [], ["file1.txt", "file2.log"])]
        mock_os_shutil["stat"].return_value = MagicMock(
            st_size=100, st_mtime=time.time()
        )
        mock_zip_file_instance = MagicMock()
        with patch("zipfile.ZipFile", autospec=True) as mock_zipfile_class:
            mock_zipfile_class.return_value.__enter__.return_value = (
                mock_zip_file_instance
            )
            zip_dir_content("output.zip", "/in")
            mock_zipfile_class.assert_called_once_with("output.zip", "w", ZIP_DEFLATED)
            assert mock_zip_file_instance.write.call_count == 2
            mock_logging_manager.get_logger.return_value.debug.assert_called_with(
                "Compressed 2 files successfully"
            )

    def test_zip_dir_content_failure(self, mock_os_shutil, mock_logging_manager):
        mock_os_shutil["walk"].return_value = [("/in", [], ["file1.txt"])]
        mock_os_shutil["stat"].return_value = MagicMock(
            st_size=100, st_mtime=time.time()
        )
        mock_zip_file_instance = MagicMock()
        mock_zip_file_instance.__enter__.return_value.write.side_effect = Exception(
            "Disk full"
        )
        with patch("zipfile.ZipFile", autospec=True) as mock_zipfile_class:
            mock_zipfile_class.return_value.__enter__.return_value = (
                mock_zip_file_instance
            )
            with pytest.raises(Exception) as excinfo:
                zip_dir_content("output.zip", "/in")
            assert "Disk full" in str(excinfo.value)
            mock_logging_manager.get_logger.return_value.error.assert_called_once()

    # Tests for to_readable_time
    def test_to_readable_time_seconds(self):
        assert to_readable_time(30) == "30 seconds"

    def test_to_readable_time_minutes(self):
        assert to_readable_time(150) == "2 minutes and 30 seconds"

    def test_to_readable_time_hours(self):
        assert to_readable_time(3700) == "1 hours, 1 minutes and 40 seconds"

    # Tests for get_env_or_default
    def test_get_env_or_default_str_exists(self, mock_os_shutil):
        mock_os_shutil["getenv"].return_value = "env_value"
        assert get_env_or_default("TEST_VAR", "default") == "env_value"

    def test_get_env_or_default_str_default(self, mock_os_shutil):
        mock_os_shutil["getenv"].return_value = None
        assert get_env_or_default("TEST_VAR", "default") == "default"

    def test_get_env_or_default_int(self, mock_os_shutil):
        mock_os_shutil["getenv"].return_value = "123"
        assert get_env_or_default("TEST_VAR", 0, value_type=int) == 123

    def test_get_env_or_default_bool(self, mock_os_shutil):
        mock_os_shutil["getenv"].return_value = "True"
        assert get_env_or_default("TEST_VAR", False, value_type=bool) is True

    def test_get_env_or_default_list_str(self, mock_os_shutil):
        mock_os_shutil["getenv"].return_value = "item1 item2"
        assert get_env_or_default("TEST_VAR", [], value_type=list, separator=" ") == [
            "item1",
            "item2",
        ]

    def test_get_env_or_default_list_int(self, mock_os_shutil):
        mock_os_shutil["getenv"].return_value = "1 2 3"
        assert get_env_or_default(
            "TEST_VAR", [], value_type=list[int], separator=" "
        ) == [1, 2, 3]

    def test_get_env_or_default_conversion_error(
        self, mock_os_shutil, mock_logging_manager
    ):
        mock_os_shutil["getenv"].return_value = "not_an_int"
        result = get_env_or_default("TEST_VAR", 0, value_type=int)
        assert result == 0
        mock_logging_manager.get_logger.return_value.error.assert_called_once()

    # Tests for get_env_or_exception
    def test_get_env_or_exception_exists(self, mock_os_shutil):
        mock_os_shutil["getenv"].return_value = "env_value"
        assert get_env_or_exception("TEST_VAR") == "env_value"

    def test_get_env_or_exception_not_exists(self, mock_os_shutil):
        mock_os_shutil["getenv"].return_value = None
        with pytest.raises(RVAndroidError) as excinfo:
            get_env_or_exception("TEST_VAR")
        assert "Environment variable TEST_VAR is not set" in str(excinfo.value)

    # Tests for read_json
    def test_read_json_success(self, mock_logging_manager):
        mock_json_content = '{"key": "value"}'
        with patch("builtins.open", MagicMock()) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                mock_json_content
            )
            with patch("json.load", return_value={"key": "value"}) as mock_json_load:
                result = read_json("test.json")
                assert result == {"key": "value"}
                mock_json_load.assert_called_once()
                mock_logging_manager.get_logger.return_value.debug.assert_called_with(
                    "Reading JSON file: test.json"
                )

    def test_read_json_file_not_found(self, mock_logging_manager):
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = read_json("non_existent.json")
            assert result == {}
            mock_logging_manager.get_logger.return_value.error.assert_called_with(
                "File not found: non_existent.json"
            )

    def test_read_json_decode_error(self, mock_logging_manager):
        mock_json_content = '{"key": "value"'
        with patch("builtins.open", MagicMock()) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                mock_json_content
            )
            with patch(
                "json.load", side_effect=json.JSONDecodeError("Invalid JSON", "", 0)
            ):
                result = read_json("malformed.json")
                assert result == {}
                mock_logging_manager.get_logger.return_value.error.assert_called_with(
                    "Failed to parse JSON from file: malformed.json"
                )

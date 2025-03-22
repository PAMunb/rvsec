# utils.py
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from typing import Union, List
from zipfile import ZipFile, ZIP_DEFLATED

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.commands.command_exception import CommandException
from rvandroid.constants import EXTENSION_APK
from rvandroid.util.logging_manager import LoggingManager

# Get the singleton logging manager
logging_manager = LoggingManager.get_instance()


def execute_command(cmd: Command, tag: str, skip_stderr=False):
    """
    Execute a command with proper error handling.

    Args:
        cmd: Command to execute
        tag: Tag for command identification
        skip_stderr: Whether to skip checking stderr for errors

    Raises:
        CommandException: If command execution fails
    """
    logger = logging_manager.get_logger("util.utils.execute_command", {"command": tag})

    logger.debug(f"Executing command: {cmd.command} {' '.join(cmd.args)}")
    cmd_result = cmd.invoke(stdout=sys.stdout)

    cond = cmd_result.code != 0
    if not skip_stderr:
        cond = cond or cmd_result.stderr

    if cond:
        error_msg = str(cmd_result.stderr, "UTF-8")
        logger.error(f"Command execution failed: {error_msg}")
        raise CommandException(tag, cmd_result.code, error_msg)

    logger.debug("Command executed successfully")


def file_hash(file_path: str):
    """
    Generate SHA-256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        Hexadecimal hash string
    """
    logger = logging_manager.get_logger("util.utils.file_hash")

    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read and update hash value in blocks of 4K
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate hash for {file_path}: {e}")
        raise


def create_folder_if_not_exists(path: str):
    """
    Create a folder if it doesn't exist.

    Args:
        path: Folder path to create

    Raises:
        OSError: If folder creation fails
    """
    logger = logging_manager.get_logger("util.utils.create_folder_if_not_exists")

    if not os.path.exists(path):
        try:
            logger.debug(f"Creating folder: {path}")
            os.makedirs(path)
        except OSError as e:
            error_msg = f'Error while creating folder {path}. Error: {e}'
            logger.error(error_msg)
            raise e


def reset_folder(path: str):
    """
    Remove a folder and recreate it.

    Args:
        path: Folder path to reset
    """
    logger = logging_manager.get_logger("util.utils.reset_folder")
    logger.debug(f"Resetting folder: {path}")

    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path)


def move_files_by_extension(extension: str, in_folder: str, destination_folder: str):
    """
    Move files with specific extension from one folder to another.

    Args:
        extension: File extension to match
        in_folder: Source folder
        destination_folder: Destination folder

    Raises:
        Exception: If file moving fails
    """
    logger = logging_manager.get_logger("util.utils.move_files_by_extension")

    try:
        check_folder_exists([in_folder, destination_folder])
        logger.debug(f"Moving files with extension {extension} from {in_folder} to {destination_folder}")

        moved_count = 0
        for file in os.listdir(in_folder):
            if file.casefold().endswith(extension):
                file_path = os.path.join(in_folder, file)
                shutil.move(file_path, destination_folder)
                moved_count += 1

        logger.debug(f"Moved {moved_count} files")

    except OSError as e:
        error_msg = f'Error while moving files from {in_folder} to {destination_folder}. Error: {e}'
        logger.error(error_msg)
        raise Exception(error_msg)


def copy_files_by_extension(extension: str, in_folder: str, destination_folder: str, log_info=False):
    """
    Copy files with specific extension from one folder to another.

    Args:
        extension: File extension to match
        in_folder: Source folder
        destination_folder: Destination folder
        log_info: Whether to log at INFO level

    Raises:
        Exception: If file copying fails
    """
    logger = logging_manager.get_logger("util.utils.copy_files_by_extension")

    try:
        check_folder_exists([in_folder, destination_folder])
        logger.debug(f"Copying files with extension {extension} from {in_folder} to {destination_folder}")

        copied_count = 0
        for file in os.listdir(in_folder):
            if file.casefold().endswith(extension):
                if log_info:
                    logger.info(f"Copying '{file}' to {destination_folder}")
                file_path = os.path.join(in_folder, file)
                shutil.copy2(file_path, destination_folder)
                copied_count += 1

        if copied_count > 0:
            logger.debug(f"Copied {copied_count} files with extension {extension}")
        else:
            logger.debug(f"No files with extension {extension} found to copy")

    except OSError as e:
        error_msg = f'Error while copying files from {in_folder} to {destination_folder}. Error: {e}'
        logger.error(error_msg)
        raise Exception(error_msg)


def copy_files(in_folder: str, destination_folder: str):
    """
    Copy all files from one folder to another.

    Args:
        in_folder: Source folder
        destination_folder: Destination folder

    Raises:
        Exception: If file copying fails
    """
    logger = logging_manager.get_logger("util.utils.copy_files")

    try:
        check_folder_exists([in_folder, destination_folder])
        logger.debug(f"Copying files from {in_folder} to {destination_folder}")

        copied_count = 0
        for file in os.listdir(in_folder):
            file_path = os.path.join(in_folder, file)
            if os.path.isfile(file_path):
                shutil.copy2(file_path, destination_folder)
                copied_count += 1

        logger.debug(f"Copied {copied_count} files")

    except OSError as e:
        error_msg = f'Error while copying files from {in_folder} to {destination_folder}. Error: {e}'
        logger.error(error_msg)
        raise Exception(error_msg)


def delete_files_by_extension(extension: str, in_folder: str):
    """
    Delete files with specific extension from a folder.

    Args:
        extension: File extension to match
        in_folder: Folder to delete from

    Raises:
        Exception: If file deletion fails
    """
    logger = logging_manager.get_logger("util.utils.delete_files_by_extension")

    try:
        check_folder_exists([in_folder])
        logger.debug(f"Deleting files with extension {extension} from {in_folder}")

        deleted_count = 0
        for file in os.listdir(in_folder):
            if file.casefold().endswith(extension):
                file_path = os.path.join(in_folder, file)
                os.remove(file_path)
                deleted_count += 1

        logger.debug(f"Deleted {deleted_count} files with extension {extension}")

    except OSError as e:
        error_msg = f'Error while deleting files from {in_folder}. Error: {e}'
        logger.error(error_msg)
        raise Exception(error_msg)


def delete_file(file_path: str):
    """
    Delete a file if it exists.

    Args:
        file_path: Path to the file
    """
    logger = logging_manager.get_logger("util.utils.delete_file")

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.debug(f"Deleted file: {file_path}")
        except OSError as e:
            logger.error(f"Failed to delete file {file_path}: {e}")


def delete_dir(dir_path: str):
    """
    Delete a directory if it exists.

    Args:
        dir_path: Path to the directory
    """
    logger = logging_manager.get_logger("util.utils.delete_dir")

    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        try:
            shutil.rmtree(dir_path)
            logger.debug(f"Deleted directory: {dir_path}")
        except OSError as e:
            logger.error(f"Failed to delete directory {dir_path}: {e}")


def check_folder_exists(folders: list):
    """
    Check if all folders in a list exist.

    Args:
        folders: List of folder paths

    Raises:
        Exception: If any folder doesn't exist
    """
    logger = logging_manager.get_logger("util.utils.check_folder_exists")

    for folder in folders:
        if not os.path.exists(folder):
            logger.error(f"Folder does not exist: {folder}")
            raise Exception(f"Folder does not exist: {folder}")


def get_apks(apks_dir: str) -> list[App]:
    """
    Get all APK files from a directory as App objects.

    Args:
        apks_dir: Directory containing APK files

    Returns:
        List of App objects
    """
    logger = logging_manager.get_logger("util.utils.get_apks")

    apks: list[App] = []
    if os.path.exists(apks_dir) and os.path.isdir(apks_dir):
        for file in os.listdir(apks_dir):
            if file.casefold().endswith(EXTENSION_APK):
                try:
                    apk_path = os.path.join(apks_dir, file)
                    apks.append(App(apk_path))
                    logger.debug(f"Found APK: {file}")
                except Exception as e:
                    logger.error(f"Error processing APK {file}: {e}")

    logger.info(f"Found {len(apks)} APK files in {apks_dir}")
    return apks


def unzip(zip_file: str, out_dir: str):
    """
    Extract a ZIP file to a directory.

    Args:
        zip_file: Path to the ZIP file
        out_dir: Output directory
    """
    logger = logging_manager.get_logger("util.utils.unzip")

    try:
        logger.debug(f"Extracting {zip_file} to {out_dir}")
        with ZipFile(zip_file, 'r') as zObject:
            zObject.extractall(path=out_dir)
        logger.debug(f"Extraction completed successfully")
    except Exception as e:
        logger.error(f"Failed to extract {zip_file}: {e}")
        raise


def zip_dir_content(zip_file: str, in_dir: str):
    """
    Compress directory contents to a ZIP file.

    Args:
        zip_file: Output ZIP file path
        in_dir: Input directory
    """
    logger = logging_manager.get_logger("util.utils.zip_dir_content")

    try:
        logger.debug(f"Compressing contents of {in_dir} to {zip_file}")
        with ZipFile(zip_file, 'w', ZIP_DEFLATED) as zipf:
            file_count = 0
            for root, dirs, files in os.walk(in_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    archive_path = os.path.relpath(file_path, in_dir)
                    zipf.write(file_path, archive_path)
                    file_count += 1

        logger.debug(f"Compressed {file_count} files successfully")
    except Exception as e:
        logger.error(f"Failed to compress directory: {e}")
        raise


def to_readable_time(duration: float):
    """
    Convert duration in seconds to human-readable format.

    Args:
        duration: Duration in seconds

    Returns:
        Formatted time string
    """
    if duration > 60:
        if duration > 3600:
            hours = int(duration / 3600)
            minutes = int((duration % 3600) / 60)
            seconds = int((duration % 3600) % 60)
            return f"{hours} hours, {minutes} minutes and {seconds} seconds"
        else:
            minutes = int(duration / 60)
            seconds = int(duration % 60)
            return f"{minutes} minutes and {seconds} seconds"
    else:
        return f"{int(duration)} seconds"


def datetime_to_milliseconds(date: datetime) -> float:
    """
    Convert datetime to milliseconds timestamp.

    Args:
        date: Datetime object

    Returns:
        Timestamp in milliseconds
    """
    return date.timestamp() * 1000


def datetime_to_string(date: datetime) -> str:
    """
    Convert datetime to formatted string.

    Args:
        date: Datetime object

    Returns:
        Formatted date string
    """
    return date.strftime("%d/%b/%Y %H:%M:%S.%f")


def milliseconds_to_datetime(timestamp: float) -> datetime:
    """
    Convert milliseconds timestamp to datetime.

    Args:
        timestamp: Timestamp in milliseconds

    Returns:
        Datetime object
    """
    return datetime.fromtimestamp(timestamp / 1000)


def get_env_or_default(env_var: str, default_value: Union[str, int, bool, List], value_type: type = str,
                       separator: str = " ") -> Union[str, int, bool, List]:
    """
    Get a value from environment variables or use a default.

    Args:
        env_var: Environment variable name
        default_value: Default value if not found in environment
        value_type: Expected value type
        separator: Separator for list types

    Returns:
        Value from environment or default
    """
    logger = logging_manager.get_logger("util.utils.get_env_or_default")

    value = os.getenv(env_var)
    if value is None:
        return default_value

    try:
        if value_type == str:
            return str(value)
        elif value_type == int:
            return int(value)
        elif value_type == bool:
            return value.lower() == "true"
        elif value_type == list:
            return value.split(separator)
        elif value_type == list[str]:
            return [str(item) for item in value.split(separator)]
        elif value_type == list[int]:
            return [int(item) for item in value.split(separator)]
        else:
            return value
    except Exception as e:
        logger.error(f"Error converting environment variable {env_var}: {e}")
        return default_value


def read_json(file_path: str):
    """
    Read and parse a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Parsed JSON data or empty dict if failed
    """
    logger = logging_manager.get_logger("util.utils.read_json")

    try:
        logger.debug(f"Reading JSON file: {file_path}")
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON from file: {file_path}")
        return {}

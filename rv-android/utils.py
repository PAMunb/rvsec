import hashlib
import logging
import os
import shutil
import sys
from zipfile import ZipFile, ZIP_DEFLATED

from app import App
from commands.command import Command
from commands.command_exception import CommandException


def execute_command(cmd: Command, tag: str, skip_stderr=False):
    cmd_result = cmd.invoke(stdout=sys.stdout)  # , stderr=sys.stderr)
    cond = cmd_result.code != 0
    if not skip_stderr:
        cond = cond or cmd_result.stderr
    if cond:
        raise CommandException(tag, cmd_result.code, str(cmd_result.stderr, "UTF-8"))


def file_hash(file_path: str):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def create_folder_if_not_exists(path: str):
    if not os.path.exists(path):
        try:
            logging.debug("Creating folder: " + path)
            os.makedirs(path)
        except OSError as e:
            error_msg = 'Error while creating folder {0}. Error: {1}'.format(path, e)
            logging.error(error_msg)
            raise e


def reset_folder(path: str):
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path)


# TODO refatorar esses metodos praticamente iguais

def move_files_by_extension(extension: str, in_folder: str, destination_folder: str):
    try:
        check_folder_exists([in_folder, destination_folder])
        logging.debug("Moving files with extension {} from {} to {}".format(extension, in_folder, destination_folder))
        for file in os.listdir(in_folder):
            if file.casefold().endswith(extension):
                file_path = os.path.join(in_folder, file)
                shutil.move(file_path, destination_folder)
    except OSError as e:
        error_msg = 'Error while moving files from {0} to {1}. Error: {2}'.format(in_folder, destination_folder, e)
        logging.error(error_msg)
        raise Exception(error_msg)


def copy_files_by_extension(extension: str, in_folder: str, destination_folder: str):
    try:
        check_folder_exists([in_folder, destination_folder])
        logging.debug("Copying files with extension {} from {} to {}".format(extension, in_folder, destination_folder))
        for file in os.listdir(in_folder):
            if file.casefold().endswith(extension):
                file_path = os.path.join(in_folder, file)
                shutil.copy2(file_path, destination_folder)
    except OSError as e:
        error_msg = 'Error while copying files from {0} to {1}. Error: {2}'.format(in_folder, destination_folder, e)
        logging.error(error_msg)
        raise Exception(error_msg)


def copy_files(in_folder: str, destination_folder: str):
    try:
        check_folder_exists([in_folder, destination_folder])
        logging.debug("Copying files with from {} to {}".format(in_folder, destination_folder))
        for file in os.listdir(in_folder):
            # if os.path.isfile(file):
            file_path = os.path.join(in_folder, file)
            shutil.copy2(file_path, destination_folder)
    except OSError as e:
        error_msg = 'Error while copying files from {0} to {1}. Error: {2}'.format(in_folder, destination_folder, e)
        logging.error(error_msg)
        raise Exception(error_msg)


def delete_files_by_extension(extension: str, in_folder: str):
    try:
        check_folder_exists([in_folder])
        logging.debug("Deleting files with extension {} from {}".format(extension, in_folder))
        for file in os.listdir(in_folder):
            if file.casefold().endswith(extension):
                file_path = os.path.join(in_folder, file)
                os.remove(file_path)
    except OSError as e:
        error_msg = 'Error while deleting files from {0}. Error: {1}'.format(in_folder, e)
        logging.error(error_msg)
        raise Exception(error_msg)


def delete_file(file_path: str):
    if os.path.exists(file_path):
        os.remove(file_path)


def delete_dir(dir_path: str):
    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        shutil.rmtree(dir_path)


def check_folder_exists(folders: list):
    for folder in folders:
        if not os.path.exists(folder):
            raise Exception("Folder does not exist: {}".format(folder))


def get_apks(apks_dir: str) -> list[App]:
    apks: list[App] = []
    if os.path.exists(apks_dir) and os.path.isdir(apks_dir):
        for file in os.listdir(apks_dir):
            if file.casefold().endswith(".apk"):
                apks.append(App(os.path.join(apks_dir, file)))
    return apks


def unzip(zip_file: str, out_dir: str):
    with ZipFile(zip_file, 'r') as zObject:
        zObject.extractall(path=out_dir)


# def zip(zip_file: str, in_dir: str):
#     with ZipFile(zip_file, 'w') as zip_object:
#         for folder_name, sub_folders, file_names in os.walk(in_dir):
#             for filename in file_names:
#                 file_path = os.path.join(folder_name, filename)
#                 zip_object.write(file_path, os.path.basename(file_path))
#         zip_object.close()


def zip_dir_content(zip_file: str, in_dir: str):
    with ZipFile(zip_file, 'w', ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(in_dir):
            for file in files:
                file_path = os.path.join(root, file)
                archive_path = os.path.relpath(file_path, in_dir)
                zipf.write(file_path, archive_path)


def to_readable_time(duration: float):
    time = ""
    if duration > 60:
        if duration > 3600:
            msg = '{0} hours, {1} minutes and {2} seconds'
            time = msg.format(int(duration / 3600), int((duration % 3600) / 60), int((duration % 3600) % 60))
        else:
            time = '{0} minutes and {1} seconds'.format(int(duration / 60), int(duration % 60))
    else:
        time = '{0} seconds'.format(int(duration))
    return time

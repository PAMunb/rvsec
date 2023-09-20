import os
import logging
import shutil


def create_folder_if_not_exists(path: str):
    if not os.path.exists(path):
        try:
            logging.debug("Creating folder: " + path)
            os.mkdir(path)
        except OSError as e:
            error_msg = 'Error while creating folder {0}. Error: {1}'.format(path, e)
            logging.error(error_msg)
            raise Exception(error_msg)


def move_files_by_extension(extension: str, in_folder: str, destination_folder: str):
    try:
        assert_folder_exists([in_folder, destination_folder])
        logging.debug("Moving files with extension {} from {} to {}".format(extension, in_folder, destination_folder))
        for file in os.listdir(in_folder):
            if file.endswith(extension):
                file_path = os.path.join(in_folder, file)
                shutil.move(file_path, destination_folder)
    except OSError as e:
        error_msg = 'Error while moving files from {0} to {1}. Error: {2}'.format(in_folder, destination_folder, e)
        logging.error(error_msg)
        raise Exception(error_msg)


def copy_files_by_extension(extension: str, in_folder: str, destination_folder: str):
    try:
        assert_folder_exists([in_folder, destination_folder])
        logging.debug("Copying files with extension {} from {} to {}".format(extension, in_folder, destination_folder))
        for file in os.listdir(in_folder):
            if file.endswith(extension):
                file_path = os.path.join(in_folder, file)
                shutil.copy2(file_path, destination_folder)
    except OSError as e:
        error_msg = 'Error while copying files from {0} to {1}. Error: {2}'.format(in_folder, destination_folder, e)
        logging.error(error_msg)
        raise Exception(error_msg)


def delete_files_by_extension(extension: str, in_folder: str):
    try:
        assert_folder_exists([in_folder])
        logging.debug("Deleting files with extension {} from {}".format(extension, in_folder))
        for file in os.listdir(in_folder):
            if file.endswith(extension):
                file_path = os.path.join(in_folder, file)
                shutil.rmtree(file_path)
    except OSError as e:
        error_msg = 'Error while deleting files from {0}. Error: {1}'.format(in_folder, e)
        logging.error(error_msg)
        raise Exception(error_msg)


def assert_folder_exists(folders: list):
    for folder in folders:
        if not os.path.exists(folder):
            raise Exception("Folder does not exist: {}".format(folder))

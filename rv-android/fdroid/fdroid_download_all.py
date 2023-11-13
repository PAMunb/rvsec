import os
import tempfile

import requests
import random

from csv import DictReader


def execute(csv_path, out_dir):
    apps = read_csv(csv_path)
    cont = 0
    for app in apps:
        if app['mop'] == 'Yes':
            download_apk(app['file'], out_dir)


def read_csv(csv_path):
    with open(csv_path, 'r') as f:
        dict_reader = DictReader(f)
        list_of_dict = list(dict_reader)
        return list_of_dict


def download_apk(apk_filename, out_dir):
    if os.path.exists(os.path.join(out_dir, apk_filename)):
        print("File already exists: {}".format(apk_filename))
        return

    apk_path = os.path.join(out_dir, apk_filename)
    base_url = "https://f-droid.org/repo/"
    apk_url = base_url + apk_filename
    print("Downloading apk: {}".format(apk_url))
    response = requests.get(apk_url)
    with open(apk_path, mode="wb") as file:
        file.write(response.content)
    print(f"Downloaded file {apk_path}")
    return apk_path


if __name__ == '__main__':
    # csv_path = "final_apps_to_download_mini.csv"
    csv_file = "final_apps_to_download.csv"
    out_dir = "../apks"
    execute(csv_file, out_dir)

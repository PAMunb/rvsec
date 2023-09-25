import os
import tempfile

import requests

from csv import DictReader



def execute(csv_path, out_dir):
    apps = read_csv(csv_path)
    cont = 0
    for app in apps:
        cont += 1
        if cont == 22:
            break
        download_apk(app['file'], out_dir)


def read_csv(csv_path):
    with open(csv_path, 'r') as f:
        dict_reader = DictReader(f)
        list_of_dict = list(dict_reader)
        return list_of_dict

def download_apk(apk_filename, out_dir):
    base_url = "https://f-droid.org/repo/"
    apk_url = base_url + apk_filename
    print("Downloading apk: {}".format(apk_url))
    response = requests.get(apk_url)
    if "content-disposition" in response.headers:
        content_disposition = response.headers["content-disposition"]
        filename = content_disposition.split("filename=")[1]
    else:
        filename = apk_url.split("/")[-1]
    apk_path = os.path.join(out_dir, filename)
    with open(apk_path, mode="wb") as file:
        file.write(response.content)
    print(f"Downloaded file {apk_path}")
    return apk_path


if __name__ == '__main__':
    csv_path = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/final_apps_to_download_mini.csv"
    out_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks"
    execute(csv_path, out_dir)

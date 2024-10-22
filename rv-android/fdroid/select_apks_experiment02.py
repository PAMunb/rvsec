import csv
import datetime
import json
import logging
import os
import shutil
import sys
from csv import DictReader

import requests
from google_play_scraper import app

URL = "url"
REVIEWS = "reviews"
RATINGS = "ratings"
SCORE = "score"
DOWNLOADS = "downloads"
PLAYSTORE = "playstore"
FDROID = "fdroid"
APP_ID = "app_id"
NAME = "name"
FILENAME = "filename"


def execute(fdroid_file: str, results_file: str, out_file: str) -> None:
    apks = get_instrumented_apks(fdroid_file, results_file)
    print("Instrumented apks: {}".format(len(apks)))
    get_app_id_from_fdroid_index(apks)
    filter_apps_in_playstore(apks)
    save_results(apks, out_file)
    print("End of execution !!!")


def get_instrumented_apks(fdroid_file: str, results_file: str) -> list[dict]:
    # pega as linhas da planilha fdroid q contem apks que foram instrumentados no experimento 01 (results_file)
    print("Recovering instrumented apks ...")
    apks: list[dict] = []
    with open(fdroid_file, "r") as f:
        with open(results_file, "r") as r:
            result = json.load(r)
            for fdroid in DictReader(f):
                apk_filename = fdroid["file"]
                if apk_filename in result:
                    data_item = {FILENAME: apk_filename,
                                 NAME: fdroid["name"],
                                 APP_ID: "",  # package name
                                 FDROID: False,  # (still) exists in fdroid
                                 PLAYSTORE: False,
                                 DOWNLOADS: 0,
                                 SCORE: 0.0,
                                 RATINGS: 0,
                                 REVIEWS: 0,
                                 URL: ""}
                    apks.append(data_item)
    return apks


def get_app_id_from_fdroid_index(instrumented_apks: list[dict]) -> None:
    print("Checking if the app still exists on fdroid ...")
    response = requests.get("https://f-droid.org/repo/index-v2.json")
    fdroid_index = response.json()

    map_filename_to_app_id = {}
    for app_id in fdroid_index["packages"]:
        data = fdroid_index["packages"][app_id]
        for version in data["versions"]:
            filename = data["versions"][version]["file"]["name"]
            filename = filename[1:]
            map_filename_to_app_id[filename] = app_id

    cont_not_exist = 0
    for apk in instrumented_apks:
        filename = apk[FILENAME]
        if filename in map_filename_to_app_id:
            apk[FDROID] = True
            app_id = map_filename_to_app_id[filename]
            apk[APP_ID] = app_id
            last_updated = fdroid_index["packages"][app_id]["metadata"]["lastUpdated"]
            last_updated_date = datetime.datetime.fromtimestamp(last_updated / 1000)
            apk["updated"] = last_updated_date.strftime("%Y-%m-%d")
        else:
            cont_not_exist += 1
    print("Apps that no longer exist on fdroid: {}".format(cont_not_exist))


def filter_apps_in_playstore(instrumented_apks: list[dict]) -> None:
    print("Recovering app data from playstore ...")
    cont = 0  # qtde que existe na playstore
    total_apks = len(instrumented_apks)
    cont_apk = 0
    for apk in instrumented_apks:
        cont_apk += 1
        status_pct = (cont_apk * 100) / total_apks
        print(f"\rProgress: {status_pct:.2f}%", end="")

        if not apk[FDROID]:
            continue

        app_id = apk[APP_ID]
        try:
            app_info = app(app_id)
            apk[PLAYSTORE] = True
            apk[DOWNLOADS] = app_info["realInstalls"]
            apk[SCORE] = app_info["score"]
            apk[RATINGS] = app_info["ratings"]
            apk[REVIEWS] = app_info["reviews"]
            apk[URL] = app_info["url"]
            cont += 1
        except:
            pass
    print("\nNumber of apps that exist in playstore: {}".format(cont))


def save_results(apks: list[dict], out: str) -> None:
    print("Saving the results ... ")
    headers: list[str] = [FILENAME, NAME, APP_ID, FDROID, PLAYSTORE, DOWNLOADS, SCORE, RATINGS, REVIEWS, 'updated', URL]
    with open(out, "w") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(apks)
    print("Results saved in: {}".format(out))


def copy_apks_to_folder(out_file, output_directory, base_directory):
    with open(out_file, mode='r') as file:
        csv_file = csv.DictReader(file)
        for line in csv_file:
            if eval(line["fdroid"]) and eval(line["playstore"]):
                filename = line["filename"]
                find_and_copy_file(filename, output_directory, base_directory)


def find_and_copy_file(filename, output_directory, base_directory):
    def walk_directory(directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file == filename:
                    full_path = os.path.join(root, file)
                    shutil.copy2(full_path, output_directory)
                    print(f"File {filename} found and copied to {output_directory}")

    walk_directory(base_directory)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.ERROR)

    base_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
    fdroid_file = os.path.join(base_dir, "fdroid", "final_apps_to_download.csv")
    results_file = os.path.join(base_dir, "final_results_analysis_jca.json")
    out_file = "/home/pedro/tmp/teste_playstore_novo.csv"

    # execute(fdroid_file, results_file, out_file)

    base_directory = "/home/pedro/desenvolvimento/RV_ANDROID/apks"
    output_directory = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_experiment02/original"
    copy_apks_to_folder(out_file, output_directory, base_directory)

    print("FIM DE FESTA!!!")

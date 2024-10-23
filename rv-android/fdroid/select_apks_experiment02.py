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
import numpy as np
from scikitmcda.constants import MAX, EnhancedAccuracy_
from scikitmcda.topsis import TOPSIS

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
    get_info_from_fdroid_index(apks)
    get_info_from_playstore(apks)
    select_apks(apks)
    save_results(apks, out_file)
    print("End of execution !!!")


def get_instrumented_apks(fdroid_file: str, results_file: str) -> list[dict]:
    print("Recovering instrumented apks ...")
    apks: list[dict] = []
    with open(fdroid_file, "r") as f:
        with open(results_file, "r") as r:
            result = json.load(r)
            for fdroid in DictReader(f):
                apk_filename = fdroid["file"]
                if apk_filename in result:
                    summary = result[apk_filename]["summary"]
                    data_item = {FILENAME: apk_filename,
                                 NAME: fdroid["name"],
                                 APP_ID: get_app_id(apk_filename),  # package name
                                 "selection_rank": 0, # mcda rank
                                 "selection_score": 0.0,  # mcda score
                                 "categories": fdroid["categories"],
                                 "package": fdroid["package"],
                                 FDROID: False,  # (still) exists in fdroid
                                 PLAYSTORE: False,
                                 "apk_date": 0,
                                 "apk_date_str": "",
                                 "last_update": 0,
                                 "last_update_str": "",
                                 DOWNLOADS: 0,
                                 SCORE: 0.0,
                                 RATINGS: 0,
                                 REVIEWS: 0,
                                 "min_sdk": fdroid["min_sdk"],
                                 "target_sdk": fdroid["target_sdk"],
                                 "classes": summary["total_classes"],
                                 "activities": summary["total_activities"],
                                 "methods": summary["total_methods"],
                                 "act_cov": summary["activities_coverage_avg"],
                                 "method_cov": summary["method_coverage_avg"],
                                 "rvsec_errors": len(result[apk_filename]["rvsec_errors"]),
                                 "summary": "",
                                 URL: "",
                                 "source": fdroid["sourceCode"]}
                    apks.append(data_item)
    return apks


def get_info_from_fdroid_index(instrumented_apks: list[dict]) -> None:
    print("Checking if the app still exists on fdroid ...")
    response = requests.get("https://f-droid.org/repo/index-v2.json")
    fdroid_index = response.json()
    print("Number of applications in fdroid index: {}".format(len(fdroid_index["packages"])))

    # cont = 0
    # for apk in instrumented_apks:
    #     app_id = apk["app_id"]
    #     if app_id in fdroid_index["packages"]:
    #         print(fdroid_index["packages"][app_id])
    #         apk[FDROID] = True
    #         # exit(1)
    #     else:
    #         cont += 1
    #         # print(apk)
    # print(cont)

    map_filename_to_app_id = {}
    for app_id in fdroid_index["packages"]:
        data = fdroid_index["packages"][app_id]
        for version in data["versions"]:
            filename = data["versions"][version]["file"]["name"]
            filename = filename[1:]
            apk_date = data["versions"][version]["added"]
            apk_date_obj = datetime.datetime.fromtimestamp(apk_date / 1000)
            map_filename_to_app_id[filename] = {"app_id": app_id,
                                                "apk_date": apk_date,
                                                "apk_date_str": apk_date_obj.strftime("%Y-%m-%d")}

    cont_not_exist = 0
    for apk in instrumented_apks:
        filename = apk[FILENAME]
        if filename in map_filename_to_app_id:
            apk[FDROID] = True
            app_info = map_filename_to_app_id[filename]
            app_id = app_info["app_id"]
            apk[APP_ID] = app_id
            apk["apk_date"] = app_info["apk_date"]
            apk["apk_date_str"] = app_info["apk_date_str"]
            metadata = fdroid_index["packages"][app_id]["metadata"]
            apk["summary"] = get_summary(metadata)
            last_updated = metadata["lastUpdated"]
            last_updated_date = datetime.datetime.fromtimestamp(last_updated / 1000)
            apk["last_update"] = last_updated
            apk["last_update_str"] = last_updated_date.strftime("%Y-%m-%d")
        else:
            cont_not_exist += 1
    print("Apps that no longer exist on fdroid: {}".format(cont_not_exist))


def get_summary(metadata):
    summary = ""
    if "en-US" in metadata["summary"]:
        summary = metadata["summary"]["en-US"]
    else:
        key = next(iter(metadata["summary"]))
        if key:
            summary = metadata["summary"][key]
    return summary


def get_info_from_playstore(instrumented_apks: list[dict]) -> None:
    print("Recovering app data from playstore ...")
    cont = 0  # qtde que existe na playstore
    total_apks = len(instrumented_apks)
    cont_apk = 0
    for apk in instrumented_apks:
        cont_apk += 1
        status_pct = (cont_apk * 100) / total_apks
        print(f"\rProgress: {status_pct:.2f}%", end="")

        # if not apk[FDROID]:
        #     continue

        app_id = apk[APP_ID]
        try:
            app_info = app(app_id)
            apk[PLAYSTORE] = True
            apk[DOWNLOADS] = app_info["realInstalls"]
            apk[SCORE] = app_info["score"]
            apk[RATINGS] = app_info["ratings"]
            apk[REVIEWS] = app_info["reviews"]
            apk[URL] = app_info["url"]
            last_updated = app_info["updated"]
            last_updated_date = datetime.datetime.fromtimestamp(last_updated)
            apk["last_update"] = last_updated
            apk["last_update_str"] = last_updated_date.strftime("%Y-%m-%d")
            cont += 1
        except:
            pass
    print("\nNumber of apps that exist in playstore: {}".format(cont))


def select_apks(apks: list[dict]) -> None:
    print("Selecting apks ...")

    # criteria_labels = ["category", "min_sdk", "target_sdk", "updated", "classes", "activities", "methods"]
    # criteria_weights = normalize_to_one([8, 2, 5, 8, 9, 10, 10]).tolist()
    # # criteria_weights = [0.05, 0.05, 0.15, 0.2, 0.15, 0.2, 0.2]
    # criteria_signals = [MAX, MAX, MAX, MAX, MAX, MAX, MAX]
    criteria_labels = [DOWNLOADS, "last_update"]
    criteria_weights = normalize_to_one([4, 6]).tolist()
    criteria_signals = [MAX, MAX]

    data = []
    names = []
    apk_by_name = {}
    for apk in apks:
        if apk[PLAYSTORE]: # TODO
            data_item = [apk[DOWNLOADS], apk["last_update"]]
            data.append(data_item)
            apk_name = apk[FILENAME]
            names.append(apk_name)
            apk_by_name[apk_name] = apk

    topsis = TOPSIS()
    topsis.dataframe(data, names, criteria_labels)
    topsis.set_weights_manually(criteria_weights)
    topsis.set_signals(criteria_signals)
    # topsis.decide()
    topsis.decide(EnhancedAccuracy_)
    aaa = topsis.df_decision
    df = aaa.sort_values(by=["rank"], ascending=True, ignore_index=True)
    result = df  #.head(10)
    # print(result)
    for ind in result.index:
        apk_name = df['alternatives'][ind]
        apk = apk_by_name[apk_name]
        apk["selection_rank"] = df['rank'][ind]
        apk["selection_score"] = df['performance score'][ind]
        # print("{} ({}) = {}".format(df['rank'][ind], df['performance score'][ind], apk))


def save_results(apks: list[dict], out: str) -> None:
    print("Saving the results ... ")

    keys = list(apks[0].keys())
    with open(out, "w") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(apks)

    # selected_keys: list[str] = [FILENAME, NAME, APP_ID, FDROID, PLAYSTORE, DOWNLOADS, SCORE, RATINGS, REVIEWS,
    #                             "last_update_str", URL]
    # with open(out, "w") as csvfile:
    #     writer = csv.writer(csvfile)
    #     writer.writerow(selected_keys)
    #     for item in apks:
    #         writer.writerow([item[key] for key in selected_keys])
    #
    # # #ValueError: dict contains fields not in fieldnames: 'apk_date', 'last_update', 'classes', 'summary', 'method_cov',
    # # # 'source', 'apk_date_str', 'package', 'activities', 'min_sdk', 'methods', 'categories', 'rvsec_errors', 'selection_score', 'last_update_str', 'act_cov', 'target_sdk'
    # # selected_keys: list[str] = [FILENAME, NAME, APP_ID, FDROID, PLAYSTORE, DOWNLOADS, SCORE, RATINGS, REVIEWS, 'updated', URL]
    # # with open(out, "w") as csvfile:
    # #     writer = csv.writer(csvfile)
    # #     writer.writerow(selected_keys)
    # #     writer.writerow([apks[key] for key in selected_keys])
    # # # with open(out, "w") as csvfile:
    # # #     writer = csv.DictWriter(csvfile)  #, fieldnames=headers)
    # # #     # writer.writeheader()
    # # #     writer.writerows(apks)
    print("Results saved in: {}".format(out))


def get_app_id(apk_filename):
    last_underscore_idx = apk_filename.rfind('_')
    if last_underscore_idx == -1:
        return apk_filename
    else:
        return apk_filename[:last_underscore_idx]


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


def normalize_to_one(arr):
    return arr / np.sum(arr)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.ERROR)

    base_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
    fdroid_file = os.path.join(base_dir, "fdroid", "final_apps_to_download.csv")
    results_file = os.path.join(base_dir, "final_results_analysis_jca.json")
    out_file = "/home/pedro/tmp/teste_playstore_novo.csv"

    execute(fdroid_file, results_file, out_file)

    # base_directory = "/home/pedro/desenvolvimento/RV_ANDROID/apks"
    # output_directory = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_experiment02/original"
    # copy_apks_to_folder(out_file, output_directory, base_directory)

    print("FIM DE FESTA!!!")

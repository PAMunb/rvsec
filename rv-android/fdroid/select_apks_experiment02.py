import csv
import json
import logging
import os
import shutil
import sys
from csv import DictReader
from datetime import datetime

import numpy as np
import requests
from google_play_scraper import app
from scikitmcda.constants import MAX, EnhancedAccuracy_
from scikitmcda.topsis import TOPSIS

DATE_FORMAT = "%Y-%m-%d"


def execute(fdroid_file: str, results_file: str, out_file: str) -> None:
    # Retrieve the rows from the F-Droid spreadsheet (previously generated) corresponding to the applications
    # that were instrumented in experiment 01
    apks = get_instrumented_apks(fdroid_file, results_file)
    print("Instrumented apks: {}".format(len(apks)))

    # Fetches the F-Droid index and adds extra app details, including if it's still available on F-Droid,
    # the date of the current version, the last update date, and more.
    get_info_from_fdroid_index(apks)

    # Retrieves information from the Play Store using the app ID (package name), even if it's no longer
    # available on F-Droid, such as the last update date (overwriting the value captured in the F-Droid index),
    # number of downloads, summaries, and others
    get_info_from_playstore(apks)

    # Ranks applications using a Multi-Criteria Decision Analysis (MCDA) method,
    # considering the specified attributes and their corresponding weights.
    rank_apks(apks)

    # Stores the gathered app data in a spreadsheet format
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
                    last_update_str = fdroid["lastUpdated"]
                    last_update = datetime.strptime(last_update_str, DATE_FORMAT).timestamp()
                    data_item = {FILENAME: apk_filename,
                                 NAME: fdroid["name"],
                                 APP_ID: get_app_id(apk_filename),  # package name
                                 SELECTION_RANK: 1000,  # mcda rank
                                 SELECTION_SCORE: 0.0,  # mcda score
                                 CATEGORIES: fdroid["categories"],
                                 PACKAGE: fdroid["package"],
                                 FDROID: False,  # (still) exists in fdroid
                                 PLAYSTORE: False,
                                 APK_DATE: last_update,  # date of the application version being used
                                 APK_DATE_STR: last_update_str,
                                 LAST_UPDATE: last_update,  # date of last update on playstore
                                 LAST_UPDATE_STR: last_update_str,
                                 DOWNLOADS: 0,
                                 SCORE: 0.0,
                                 RATINGS: 0,
                                 REVIEWS: 0,
                                 MIN_SDK: fdroid["min_sdk"],
                                 TARGET_SDK: fdroid["target_sdk"],
                                 CLASSES: summary["total_classes"],
                                 ACTIVITIES: summary["total_activities"],
                                 METHODS: summary["total_methods"],
                                 ACT_COV: summary["activities_coverage_avg"],
                                 METHOD_COV: summary["method_coverage_avg"],
                                 ERRORS: len(result[apk_filename]["rvsec_errors"]),
                                 SUMMARY: "",
                                 URL: "",  # playstore url
                                 SOURCE: fdroid["sourceCode"]}
                    apks.append(data_item)
    return apks


def get_info_from_fdroid_index(instrumented_apks: list[dict]) -> None:
    print("Recovering app data from F-Droid index ...")
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
            apk_date_obj = datetime.fromtimestamp(apk_date / 1000)
            map_filename_to_app_id[filename] = {APP_ID: app_id,
                                                APK_DATE: apk_date,
                                                APK_DATE_STR: apk_date_obj.strftime(DATE_FORMAT)}

    nao_existe = []
    cont_not_exist = 0
    for apk in instrumented_apks:
        filename = apk[FILENAME]
        if filename in map_filename_to_app_id:
            apk[FDROID] = True
            app_info = map_filename_to_app_id[filename]
            app_id = app_info[APP_ID]
            apk[APP_ID] = app_id
            apk[APK_DATE] = app_info[APK_DATE]
            apk[APK_DATE_STR] = app_info[APK_DATE_STR]
            metadata = fdroid_index["packages"][app_id]["metadata"]
            apk[SUMMARY] = get_summary(metadata)
            last_updated = metadata["lastUpdated"]
            last_updated_date = datetime.fromtimestamp(last_updated / 1000)
            apk[LAST_UPDATE] = last_updated
            apk[LAST_UPDATE_STR] = last_updated_date.strftime(DATE_FORMAT)
        else:
            cont_not_exist += 1
            nao_existe.append(apk)
    salvarNaoExiste(nao_existe)
    print("Apps that no longer exist on fdroid: {}".format(cont_not_exist))


# TODO remover ... apenas para teste
def salvarNaoExiste(nao_existe):
    tmp_file = "/home/pedro/tmp/teste_playstore_naoexiste_fdroid.csv"
    keys = list(nao_existe[0].keys())
    with open(tmp_file, "w") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(nao_existe)
        print(f">>>>>>>>>> salvou: {tmp_file}")


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
    cont = 0  # number of apps that exist in the play store too
    total_apks = len(instrumented_apks)
    cont_apk = 0
    for apk in instrumented_apks:
        cont_apk += 1
        status_pct = (cont_apk * 100) / total_apks
        print(f"\rProgress: {status_pct:.2f}%", end="")

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
            last_updated_date = datetime.fromtimestamp(last_updated)
            apk[LAST_UPDATE] = last_updated
            apk[LAST_UPDATE_STR] = last_updated_date.strftime(DATE_FORMAT)
            cont += 1
        except:
            pass
    print("\nNumber of apps that exist in playstore: {}".format(cont))


def rank_apks(apks: list[dict]) -> None:
    print("Ranking apks ...")

    # criteria_labels = ["category", "min_sdk", "target_sdk", "updated", "classes", "activities", "methods"]
    # criteria_weights = normalize_to_one([8, 2, 5, 8, 9, 10, 10]).tolist()
    # # criteria_weights = [0.05, 0.05, 0.15, 0.2, 0.15, 0.2, 0.2]
    # criteria_signals = [MAX, MAX, MAX, MAX, MAX, MAX, MAX]
    criteria_labels = [DOWNLOADS, LAST_UPDATE]
    criteria_weights = normalize_to_one([4, 6]).tolist()
    print(f">>>>>>>>>> criteria_weights={criteria_weights}")
    criteria_signals = [MAX, MAX]

    data = []
    alternatives = []
    apk_by_name = {}
    for apk in apks:
        if apk[PLAYSTORE]:
            data_item = [apk[DOWNLOADS], apk[LAST_UPDATE]]
            data.append(data_item)
            apk_name = apk[FILENAME]
            alternatives.append(apk_name)
            apk_by_name[apk_name] = apk

    topsis = TOPSIS()
    topsis.dataframe(data, alternatives, criteria_labels)
    topsis.set_weights_manually(criteria_weights)
    topsis.set_signals(criteria_signals)
    # topsis.decide()
    topsis.decide(EnhancedAccuracy_)
    df = topsis.df_decision.sort_values(by=["rank"], ascending=True, ignore_index=True)
    result = df  # .head(10)
    # print(result)
    for ind in result.index:
        apk_name = result["alternatives"][ind]
        apk = apk_by_name[apk_name]
        apk[SELECTION_RANK] = int(result["rank"][ind])
        apk[SELECTION_SCORE] = result["performance score"][ind]


def save_results(apks: list[dict], out: str) -> None:
    print("Saving the results ... ")

    keys = list(apks[0].keys())
    with open(out, "w") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(apks)

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
            #if eval(line[FDROID]) and eval(line[PLAYSTORE]):
            if eval(line[PLAYSTORE]):
                filename = line[FILENAME]
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


SELECTION_RANK = "selection_rank"
SELECTION_SCORE = "selection_score"
CATEGORIES = "categories"
PACKAGE = "package"
APK_DATE = "apk_date"
APK_DATE_STR = "apk_date_str"
LAST_UPDATE = "last_update"
LAST_UPDATE_STR = "last_update_str"
TARGET_SDK = "target_sdk"
MIN_SDK = "min_sdk"
SOURCE = "source"
SUMMARY = "summary"
ERRORS = "rvsec_errors"
METHOD_COV = "method_cov"
ACT_COV = "act_cov"
METHODS = "methods"
ACTIVITIES = "activities"
CLASSES = "classes"
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


def tmp_mcda(file: str):
    print(f"Reading file: {file}")
    apks = []
    with open(file, "r") as f:
        dict_reader = DictReader(f)
        apks = list(dict_reader)

    for apk in apks:
        apk[DOWNLOADS] = int(apk[DOWNLOADS])
        apk[LAST_UPDATE] = int(float(apk[LAST_UPDATE]))
        apk[SELECTION_RANK] = 1000
        apk[SELECTION_SCORE] = 0.0
        play = False
        if "True" == apk[PLAYSTORE]:
            play = True
        apk[PLAYSTORE] = play

    rank_apks(apks)

    sorted_apks = sorted(apks, key=lambda x: (x[SELECTION_RANK], x[DOWNLOADS]))
    for i in range(20):
        # print("{} = {}".format(sorted_apks[i][SELECTION_RANK], sorted_apks[i]))
        print("{} = [name={}, updated={}, downloads={}]".format(sorted_apks[i][SELECTION_RANK],
                                                                sorted_apks[i][NAME],
                                                                sorted_apks[i][LAST_UPDATE_STR],
                                                                sorted_apks[i][DOWNLOADS]))


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

    # tmp_mcda(out_file)

    print("FIM DE FESTA!!!")

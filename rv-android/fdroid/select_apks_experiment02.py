import csv
import json
import logging
import os
import sys
from csv import DictReader

import requests
from google_play_scraper import app


def execute(fdroid_file: str, results_file: str, out_file: str):
    apks = get_instrumented_apks(fdroid_file, results_file)
    print("Instrumented apks: {}".format(len(apks)))
    get_app_id_from_fdroid_index(apks)
    filter_apps_in_playstore(apks)
    save_results(apks, out_file)
    print("End of execution !!!")


def get_instrumented_apks(fdroid_file: str, results_file: str):
    # pega as linhas da planilha fdroid q contem apks que foram instrumentados no experimento 01 (results_file)
    print("Recovering instrumented apks: fdroid_file={}, results_file={}".format(fdroid_file, results_file))
    apks = []
    with open(fdroid_file, 'r') as f:
        with open(results_file, "r") as r:
            result = json.load(r)
            for line in DictReader(f):
                apk_filename = line['file']
                if apk_filename in result:
                    data_item = {"filename": apk_filename,
                                 "name": line['name'],
                                 "app_id": "",  # package name
                                 "fdroid": False,  # (still) exists in fdroid
                                 "playstore": False,
                                 "downloads": 0,
                                 "score": 0.0,
                                 "ratings": 0,
                                 "reviews": 0,
                                 "url": ""
                                 }
                    apks.append(data_item)
    return apks


def get_app_id_from_fdroid_index(instrumented_apks):
    print("Checking if the app still exists on fdroid ...")
    response = requests.get('https://f-droid.org/repo/index-v2.json')
    fdroid_index = response.json()

    map_filename_to_app_id = {}
    for app in fdroid_index["packages"]:
        for version in fdroid_index["packages"][app]["versions"]:
            filename = fdroid_index["packages"][app]["versions"][version]["file"]["name"]
            filename = filename[1:]
            map_filename_to_app_id[filename] = app

    cont_not_exists = 0
    for apk in instrumented_apks:
        filename = apk["filename"]
        if filename in map_filename_to_app_id:
            apk["app_id"] = map_filename_to_app_id[filename]
            apk["fdroid"] = True
        else:
            cont_not_exists += 1
    print("Apps that no longer exist on fdroid: {}".format(cont_not_exists))


def filter_apps_in_playstore(instrumented_apks):
    print("Recovering app data from playstore ...")
    cont = 0
    for apk in instrumented_apks:
        if not apk["fdroid"]:
            continue
        app_id = apk['app_id']
        try:
            app_info = app(app_id)
            # if app_info:
            apk["playstore"] = True
            apk["downloads"] = app_info['realInstalls']
            apk["score"] = app_info['score']
            apk["ratings"] = app_info['ratings']
            apk["reviews"] = app_info['reviews']
            apk["url"] = app_info['url']
            cont += 1
        except:
            pass
    print("Number of apps that exist in the playstore: {}".format(cont))


def save_results(apks, out_file: str):
    print("Saving the results ... ")
    headers = ["filename", "name", "app_id", "fdroid", "playstore", "downloads", "score", "ratings", "reviews", "url"]
    with open(out_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(apks)
    print("Results saved in: {}".format(out_file))
    #
    # print("RESULTS: {}".format(len(apks)))
    # for apk in apks:
    #     print(apk)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.ERROR)

    base_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
    fdroid_file = os.path.join(base_dir, "fdroid/final_apps_to_download.csv")
    results_file = os.path.join(base_dir, "final_results_analysis_jca.json")
    out_file = "/home/pedro/tmp/teste_playstore.csv"

    execute(fdroid_file, results_file, out_file)

    print("FIM DE FESTA!!!")

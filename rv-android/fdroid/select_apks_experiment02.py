import json
import logging
import os
import sys
from csv import DictReader

import numpy as np
from scikitmcda.constants import MAX, EnhancedAccuracy_
from scikitmcda.topsis import TOPSIS

categories_score = {
    "Connectivity": 6,
    "Development": 5,
    "Games": 1,
    "Graphics": 3,
    "Internet": 8,
    "Money": 9,
    "Multimedia": 4,
    "Navigation": 5,
    "Phone & SMS": 5,
    "Reading": 4,
    "Science & Education": 3,
    "Security": 10,
    "Sports & Health": 3,
    "System": 9,
    "Theming": 1,
    "Time": 2,
    "Writing": 3,
}


def execute(fdroid_file: str, results_file: str):
    instrumented_apks = get_instrumented_apks(fdroid_file, results_file)
    # apks = filter_apks_in_playstore(instrumented_apks)
    # print(apks)
    # select_apks(apks)


def filter_apks_in_playstore(instrumented_apks):
    return instrumented_apks


def search_app_in_playstore(app_name: str):
    # #pip install google-play-scraper
    # from google_play_scraper import Sort, reviews, app
    # # Busca pelo aplicativo
    # # results = app(app_name, lang='pt_BR', country='br')
    # results = app(app_name)
    # print("results={}".format(results))

    from google_play_scraper import app

    # Substitua 'com.whatsapp' pelo ID do aplicativo desejado
    app_info = app('com.whatsapp')

    if app_info:
        print(app_info['appId'])
        print(app_info['title'])
        print(app_info['realInstalls'])
        print(app_info['score'])
        print(app_info['ratings'])
        print(app_info['reviews'])
        print(app_info['url'])


    # import requests
    # from bs4 import BeautifulSoup
    # url = f"https://play.google.com/store/apps/details?id={app_name}"
    # response = requests.get(url)
    # print(response.content)
    # soup = BeautifulSoup(response.content, 'html.parser')
    # print(soup)
    #
    #
    # # Extrair informações relevantes (título, descrição, etc.)
    # title = soup.find('h1', {'class': 'title'}).text
    # description = soup.find('div', {'class': 'description'}).text
    #
    # return title, description


def select_apks(apks):
    print("select_apks ..........")

    # TODO incluir dados de reachability ?
    criteria_labels = ["category", "min_sdk", "target_sdk", "updated", "classes", "activities", "methods"]
    criteria_weights = normalize_to_one([8, 2, 5, 8, 9, 10, 10]).tolist()
    # criteria_weights = [0.05, 0.05, 0.15, 0.2, 0.15, 0.2, 0.2]
    print("criteria_weights={}".format(criteria_weights))
    criteria_signals = [MAX, MAX, MAX, MAX, MAX, MAX, MAX]
    data = []
    names = []
    apk_by_name = {}

    for apk in apks:
        min_sdk = 0
        if apk["min_sdk"]:
            min_sdk = int(apk["min_sdk"])
        data_item = [apk["categories"], min_sdk, int(apk["target_sdk"]), apk["last_updated_str"],
                     apk["total_classes"], apk["total_activities"], apk["total_methods"]]
        data.append(data_item)
        apk_name = apk['apk']
        names.append(apk_name)
        apk_by_name[apk_name] = apk

    # print(data)

    topsis = TOPSIS()
    topsis.dataframe(data, names, criteria_labels)
    topsis.set_weights_manually(criteria_weights)
    topsis.set_signals([MAX, MAX, MAX, MAX, MAX, MAX, MAX])
    # topsis.decide()
    topsis.decide(EnhancedAccuracy_)
    aaa = topsis.df_decision
    df = aaa.sort_values(by=['rank'], ascending=True, ignore_index=True)
    result = df.head(10)
    print(result)
    for ind in result.index:
        print("{} = {}".format(df['rank'][ind], apk_by_name[df['alternatives'][ind]]))


def normalize_to_one(arr):
    return arr / np.sum(arr)


def get_category_score(category: str):
    if category in categories_score:
        return categories_score[category]
    return 0


def get_category(categories: str):
    # retorna o score da categora com maior valor
    higher = -1
    tmp = categories.replace("['", "")
    tmp = tmp.replace("']", "")
    tmp = tmp.replace("'", "")
    for t in tmp.split(","):
        category = t.strip()
        score = get_category_score(category)
        if score > higher:
            higher = score
    return higher


def get_instrumented_apks(fdroid_file: str, results_file: str):
    # pega as linhas da planilha fdroid q contem apks que foram instrumentados no experimento 01 (results_file)
    data = []
    with open(fdroid_file, 'r') as f:
        with open(results_file, "r") as r:
            result = json.load(r)
            for line in DictReader(f):
                apk_filename = line['file']
                if apk_filename in result:
                    category = get_category(line["categories"])
                    # print("category={}".format(category))
                    data_item = {"apk": apk_filename,
                                 "name": line['name'],
                                 "categories": category,  # TODO rank de categoria (transformar em numero)
                                 "min_sdk": line['min_sdk'],
                                 "target_sdk": line['target_sdk'],
                                 "last_updated_str": date_str_to_milliseconds(line['lastUpdated']),  # TODO to timestamp
                                 "total_classes": result[apk_filename]['summary']['total_classes'],
                                 "total_activities": result[apk_filename]['summary']['total_activities'],
                                 "total_methods": result[apk_filename]['summary']['total_methods'],
                                 "total_methods_jca_reachable": result[apk_filename]['summary'][
                                     'total_methods_jca_reachable']}
                    data.append(data_item)
    return data


# def tmp02():
#     print("Recuperando indice do repositorio do f-froid: https://f-droid.org/repo/index-v2.json")
#     import requests
#     response = requests.get('https://f-droid.org/repo/index-v2.json')
#     data = response.json()
#     for package_name in data["packages"]:
#         print("\n\n>>> {}".format(data["packages"][package_name]))


def date_str_to_milliseconds(date: str):
    from datetime import datetime
    date_format = "%Y-%m-%d"
    date = datetime.strptime(date, date_format)
    return round(date.timestamp() * 1000)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.ERROR)

    base_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
    fdroid_file = os.path.join(base_dir, "fdroid/final_apps_to_download.csv")
    results_file = os.path.join(base_dir, "final_results_analysis_jca.json")

    # execute(fdroid_file, results_file)
    # tmp02()
    search_app_in_playstore("com.google.android.youtube")

    print("FIM DE FESTA!!!")

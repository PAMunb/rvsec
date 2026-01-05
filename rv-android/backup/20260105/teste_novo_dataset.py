import concurrent
import concurrent.futures
import csv
import logging
import sys
from csv import DictReader
from datetime import datetime

import numpy as np
import requests
from google_play_scraper import app
from scikitmcda.constants import MAX, EnhancedAccuracy_
from scikitmcda.topsis import TOPSIS

from rvandroid.constants import *
from rvandroid import RvAndroid, analysis as reach
from rvandroid.rvsec import RVSec
from settings import *


class Counter(object):
    def __init__(self):
        self.cont = 0
        self.apks = set()

    def add(self, apk):
        if apk not in self.apks:
            self.apks.add(apk)
            self.cont += 1

    def reset(self):
        self.apks = set()
        self.cont = 0


DATE_FORMAT = "%Y-%m-%d"


def execute(spreadsheet, apks_dir):
    # apks = get_fdroid_info()
    # get_playstore_info(apks)
    # save_results(apks, spreadsheet)

    apks = read_file(spreadsheet)

    # download_apks(apks, apks_dir)
    # save_results(apks, spreadsheet)

    # reachability_analysis(apks, apks_dir, spreadsheet)
    instrument_apks(apks, apks_dir)
    save_results(apks, spreadsheet)

    # rank_apks(apks)
    # save_results(apks, spreadsheet)
    print("FIM DE FESTA !!!")


def get_fdroid_info():
    print("Recovering app data from F-Droid index ...")
    response = requests.get("https://f-droid.org/repo/index-v2.json")
    fdroid_index = response.json()
    print("Number of applications in fdroid index: {}".format(len(fdroid_index["packages"])))
    result = []
    for app_id in fdroid_index["packages"]:
        data = fdroid_index["packages"][app_id]
        apk = {
            FILENAME: "",
            "package": app_id,
            "name": get_text(data, "name"),
            PLAYSTORE: False,
            "downloaded": False,
            "reachesMOP": False,
            "reachable": False,
            "instrument": False,
            SELECTION_RANK: 1000,  # mcda rank
            SELECTION_SCORE: 0.0,  # mcda score
            LAST_UPDATE: 0,
            "playstoreLastUpdated": 0,
            DOWNLOADS: 0,
            "score": 0,
            "ratings": 0,
            "reviews": 0,
            "minSdk": 0,
            "targetSdk": 0,
            "classes": 0,
            "activities": 0,
            "methods": 0,
            "mop_methods": 0,
            "categories": data["metadata"]["categories"],
            "sourceFile": "",
            "source": "",
            "issueTracker": "",
            "playstoreUrl": "",
            "permissions": [],
            "summary": get_text(data, "summary"),
            "description": get_text(data, "description")
        }

        if "issueTracker" in data["metadata"]:
            apk["issueTracker"] = data["metadata"]["issueTracker"]
        if "sourceCode" in data["metadata"]:
            apk["source"] = data["metadata"]["sourceCode"]

        find_last_version(data, apk)
        result.append(apk)
    return result


def find_last_version(data, apk):
    versions = data["versions"]
    metadata = data["metadata"]
    last_update = metadata["lastUpdated"]
    for v in versions:
        version = versions[v]
        added = version["added"]
        if last_update == added:
            apk_date_obj = datetime.fromtimestamp(added / 1000)
            apk[LAST_UPDATE] = apk_date_obj.strftime(DATE_FORMAT)
            apk[FILENAME] = version["file"]["name"][1:]
            get_sdk(apk, version)
            get_source_file(apk, version)
            get_permissions(apk, version)


def get_source_file(apk, version):
    if "src" in version:
        apk["sourceFile"] = version["src"]["name"][1:]


def get_sdk(apk, version):
    if "usesSdk" in version["manifest"]:
        apk["minSdk"] = version["manifest"]["usesSdk"]["minSdkVersion"]
        apk["targetSdk"] = version["manifest"]["usesSdk"]["targetSdkVersion"]


def get_permissions(apk, version):
    if "usesPermission" in version["manifest"]:
        permissions = []
        for permission in version["manifest"]["usesPermission"]:
            permissions.append(permission["name"])
        apk["permissions"] = permissions


def get_playstore_info(apks):
    print("Recovering app data from playstore ...")
    cont = 0  # number of apps that exist in the play store too
    total_apks = len(apks)
    cont_apk = 0
    for apk in apks:
        cont_apk += 1
        status_pct = (cont_apk * 100) / total_apks
        print(f"\rProgress: {status_pct:.2f}%", end="")

        app_id = apk["package"]
        try:
            app_info = app(app_id)
            apk[PLAYSTORE] = True
            apk[DOWNLOADS] = app_info["realInstalls"]
            apk["score"] = app_info["score"]
            apk["ratings"] = app_info["ratings"]
            apk["reviews"] = app_info["reviews"]
            apk["playstoreUrl"] = app_info["url"]
            last_updated = app_info["updated"]
            last_updated_date = datetime.fromtimestamp(last_updated)
            apk["playstoreLastUpdated"] = last_updated_date.strftime(DATE_FORMAT)
            cont += 1
        except:
            pass
    print("\nNumber of apps that exist in playstore: {}".format(cont))


def save_results(apks: list[dict], out: str, log=True) -> None:
    if log:
        print("Saving the results ... ")

    keys = list(apks[0].keys())
    with open(out, "w") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(apks)

    if log:
        print("Results saved in: {}".format(out))


def download_apks(apks, apks_dir):
    download_apks_concurrent(apks, apks_dir)
    update_download_info(apks, apks_dir)


def update_download_info(apks, apks_dir):
    apks_downloaded = set()
    if os.path.exists(apks_dir) and os.path.isdir(apks_dir):
        for file in os.listdir(apks_dir):
            if file.casefold().endswith(EXTENSION_APK):
                apks_downloaded.add(file)
    for apk in apks:
        if apk[FILENAME] in apks_downloaded:
            apk["downloaded"] = True


def download_apks_concurrent(apks, apks_dir, max_workers=50):
    print("Downloading APKs ...")
    cont = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for apk in apks:
            # must exist in playstore and lastUpdate this year (2024)
            if apk[PLAYSTORE] and ("2024" in apk[LAST_UPDATE]):
                cont += 1
                filename = apk[FILENAME]
                future = executor.submit(download_apk, filename, apks_dir)
                futures.append(future)
        concurrent.futures.wait(futures)
    print(f"APKs ({cont}) downloaded to: {apks_dir}")


def reachability_analysis(apks, apks_dir, out_file, max_workers=30):
    print("Reachability analysis ...")

    counter = Counter()

    # sequencial
    cont = 0
    total_apks = len(apks)
    for apk in apks:
        cont += 1
        status_pct = (cont * 100) / total_apks
        apk_path = os.path.join(apks_dir, apk["apk"])
        if os.path.exists(apk_path):
            try:
                process_reach(apk, apk_path, counter, apks, out_file)
            except:
                print(f"ERROR: {apk_path}")
        print(f"\rProgress: {status_pct:.2f}% ({cont}/{total_apks}), reachesMOP={counter.cont}", end="")

    # with multiprocessing.Pool(processes=max_workers) as pool:
    #     total_apks = 0
    #     results = []
    #     for apk in apks:
    #         apk_path = os.path.join(apks_dir, apk[FILENAME])
    #         if os.path.exists(apk_path) and apk_path.casefold().endswith(EXTENSION_APK):
    #             result = pool.apply_async(process_reach, args=(apk, apk_path, counter, apks, out_file))
    #             results.append(result)
    #             total_apks += 1
    #     progress_thread = threading.Thread(target=track_progress, args=(results, total_apks, counter))
    #     progress_thread.start()
    #     for result in results:
    #         result.get()
    #     progress_thread.join()  # Wait for the progress thread to finish
    #     print("\nAll tasks completed.")

    # with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    #     futures = []
    #     for apk in apks:
    #         apk_path = os.path.join(apks_dir, apk[FILENAME])
    #         if os.path.exists(apk_path):
    #             future = executor.submit(process_reach, apk, apk_path, counter, apks, out_file)
    #             futures.append(future)
    #     concurrent.futures.wait(futures)

    # with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    #     futures = []
    #     total_apks = 0
    #     for apk in apks:
    #         apk_path = os.path.join(apks_dir, apk[FILENAME])
    #         if os.path.exists(apk_path):
    #             future = executor.submit(process_reach, apk, apk_path, counter, apks, out_file)
    #             futures.append(future)
    #             total_apks += 1
    #     progress_thread = threading.Thread(target=track_progress_02, args=(futures, total_apks))
    #     progress_thread.start()
    #     concurrent.futures.wait(futures)
    #     # for future in futures:
    #     #     future.result()
    #     progress_thread.join()
    #     print("\nAll tasks completed.")


def track_progress_02(futures, total_tasks):
    completed = 0
    while completed < total_tasks:
        completed = sum(future.done() for future in futures)
        progress = (completed / total_tasks) * 100
        print(f"Progress: {progress:.2f}% ({completed}/{total_tasks})", end='\r')
        time.sleep(3)


def process_reach(apk, apk_path, counter, apks, out_file):
    reaches_mop = reaches(apk, apk_path, counter)
    if reaches_mop:
        save_results(apks, out_file, False)


def reaches(apk, apk_path, counter):
    # print(f"reaches .... apk_path={apk_path} .... apk={apk}")
    reaches_mop = False
    classes = 0
    activities = 0
    methods = 0
    mop_methods = 0
    apk["reachable"] = False
    reachable = reach.reachable_methods_that_uses_jca(apk_path)
    for clazz in reachable:
        classes += 1
        if reachable[clazz][IS_ACTIVITY]:
            activities += 1
        for m in reachable[clazz][METHODS]:
            methods += 1
            method = reachable[clazz][METHODS][m]
            if method[REACHABLE]:
                apk["reachable"] = True
            if method[USE_JCA]:  # and method[REACHABLE]:
                mop_methods += 1
                # print(f"********************************  REACHES MOP: {apk_path}")
                apk["reachesMOP"] = True
                reaches_mop = True
                counter.add(apk[FILENAME])
    apk["classes"] = classes
    apk["activities"] = activities
    apk["methods"] = methods
    apk["mop_methods"] = mop_methods
    return reaches_mop


def track_progress(results, total_apks, counter):
    completed = 0
    while completed < total_apks:
        completed = sum(result.ready() for result in results)
        progress = (completed / total_apks) * 100
        print(f"\rProgress: {progress:.2f}% ({completed}/{total_apks}), reachesMOP={counter.cont}", end="")
        time.sleep(3)


def instrument_apks(apks, apks_dir):
    print("Instrumenting ...")

    remove_unused_apks(apks, apks_dir)
    print(f"Amount of apks reaching MOP: {count_apk_files(apks_dir)}")

    rvsec = RVSec()
    rvsec.generate_monitors()

    rvandroid = RvAndroid()
    errors = rvandroid.instrument_apks(results_dir=INSTRUMENTED_DIR, apks_dir=apks_dir)

    for apk in apks:
        if apk[FILENAME] not in errors:
            apk["instrument"] = True

    # cont = 0
    # total_apks = len(apks)
    # # rvandroid.prepare_instrumentation(INSTRUMENTED_DIR)
    # for apk in apks:
    #     print(f"apk={apk["apk"]}, reachesMOP={apk["reachesMOP"]}")
    #     if apk["reachesMOP"]:
    #         print(f"******************************* instrument={apk["apk"]}")
    # #         cont += 1
    # #         try:
    # #             print("Starting instrumentation {}/{}".format(cont, total_apks))
    # #             _app: App = App(os.path.join(apks_dir, apk["apk"]))
    # #             rvandroid.instrument(_app)
    # #             rvandroid.check_if_instrumented(_app)
    # #             apk["instrument"] = True
    # #         except Exception as ex:
    # #             print("Error while instrumenting APK: {}. {}".format(apk["apk"], ex))
    # #         finally:
    # #             rvandroid.clear([TMP_DIR, RVM_TMP_DIR])
    # # rvandroid.clear([LIB_TMP_DIR])


def rank_apks(apks):
    print("Ranking apks ...")

    criteria_labels = [DOWNLOADS, LAST_UPDATE]
    criteria_weights = normalize_to_one([4, 6]).tolist()
    # criteria_weights = [0.48, 0.52]
    print(f">>>>>>>>>> criteria_weights={criteria_weights}")
    criteria_signals = [MAX, MAX]

    data = []
    alternatives = []
    apk_by_name = {}
    for apk in apks:
        apk[SELECTION_RANK] = 1000
        apk[SELECTION_SCORE] = 0.0
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


def to_boolean(line, fields):
    for field in fields:
        if field in line and line[field] == "True":
            line[field] = True
        else:
            line[field] = False


def read_file(input_file: str):
    lines: list[dict] = []
    with open(input_file, 'r') as f:
        dict_reader = DictReader(f)
        dict_lines = list(dict_reader)
        for line in dict_lines:
            tmp = ["playstore", "reachesMOP", "instrument", "downloaded", "reachable"]
            to_boolean(line, tmp)
            lines.append(line)
    return lines


def download_apk(apk_filename: str, out_dir: str):
    if os.path.exists(os.path.join(out_dir, apk_filename)):
        # print("File already exists: {}".format(apk_filename))
        return

    base_url = "https://f-droid.org/repo/"
    apk_url = base_url + apk_filename
    # print(f"Downloading apk: {apk_url}")
    response = requests.get(apk_url)
    if "content-disposition" in response.headers:
        content_disposition = response.headers["content-disposition"]
        filename = content_disposition.split("filename=")[1]
    else:
        filename = apk_url.split("/")[-1]
    apk_path = os.path.join(out_dir, filename)
    with open(apk_path, mode="wb") as file:
        file.write(response.content)
    # print(f"Downloaded file {apk_path}")
    return apk_path


def get_text(data, field):
    if field in data["metadata"]:
        names: dict = data["metadata"][field]
        if "en-US" in names:
            return names["en-US"]
        else:
            keys = list(names.keys())
            if len(keys) > 0:
                key = keys[0]
                return names[key]
    return ""


def remove_unused_apks(apks, apks_dir):
    for apk in apks:
        if not apk["reachesMOP"]:
            filename = apk[FILENAME]
            filepath = os.path.join(apks_dir, filename)
            if os.path.exists(filepath) and filename.endswith(EXTENSION_APK):
                print(f"Removing APK: {filepath}")
                os.remove(filepath)


def count_apk_files(directory):
    count = 0
    for file in os.listdir(directory):
        if file.endswith(EXTENSION_APK):
            count += 1
    return count


def normalize_to_one(arr):
    return arr / np.sum(arr)


DOWNLOADS = "downloads"
LAST_UPDATE = "lastUpdated"
PLAYSTORE = "playstore"
FILENAME = "apk"
SELECTION_RANK = "selection_rank"
SELECTION_SCORE = "selection_score"

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.ERROR)

    out_filename = "/home/pedro/tmp/planilha_novo_dataset.csv"
    apps_dir = "/home/pedro/tmp/novos_apks"
    execute(out_filename, apps_dir)

    # apk = {}
    # apk_path = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini/cryptoapp.apk"
    # reaches(apk, apk_path)

import csv
import os
import sys

from commands.command import Command
from settings import LIB_DIR, ANDROID_PLATFORMS_DIR, INSTRUMENTED_DIR
from app import App


# def process_coverage(results_dir: str):
#     all_methods = {}
#     coverage = {}
#     if os.path.exists(results_dir) and os.path.isdir(results_dir):
#         for apk_name in os.listdir(results_dir):
#             folder_path = os.path.join(results_dir, apk_name)
#             if os.path.isdir(folder_path):
#                 apk_path = os.path.join(INSTRUMENTED_DIR, apk_name)
#                 print("APK: {} ... exists? {}".format(apk_path, os.path.exists(apk_path)))
#
#                 if apk_name not in all_methods
#                 classes = get_all_methods(apk_path)



def get_all_methods(apk_path: str):
    app = App(apk_path)
    out_file = "/home/pedro/tmp/teste_soot.csv"
    __execute_soot(apk_path, app.package_name, out_file)
    return __parse_soot_result(out_file)


def __parse_soot_result(soot_result: str):
    classes = {}
    with open(soot_result) as f:
        while True:
            line = f.readline()
            if not line:
                break

            split = line.split(";")
            clazz = split[0]
            method = split[1]

            if clazz not in classes:
                classes[clazz] = set()
            classes[clazz].add(method)
    return classes


def __execute_soot(apk_path: str, package: str, out_file: str):
    extractor_jar = os.path.join(LIB_DIR, 'methods-extractor', 'methods-extractor.jar')
    print("JAR: {}".format(extractor_jar))
    extractor_cmd = Command("java", [
        "-jar", extractor_jar,
        "--apk", apk_path,
        "--apk-package", package,
        "--android-dir", ANDROID_PLATFORMS_DIR,
        "--output", out_file
    ])
    extractor_result = extractor_cmd.invoke(stdout=sys.stdout)
    if extractor_result.code != 0:
        raise Exception("Error while finding all methods in APK: {0}. {1}".format(apk_path,
                                                                                    extractor_result.stderr))


if __name__ == '__main__':
    result_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/teste"
    execute(result_dir)

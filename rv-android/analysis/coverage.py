import csv
import os
import sys

from commands.command import Command
from settings import LIB_DIR, ANDROID_PLATFORMS_DIR, INSTRUMENTED_DIR, APKS_DIR
from app import App
from constants import EXTENSION_METHODS
# import methods_extractor as me

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

def execute(called_methods: dict[str, set[str]], all_methods: dict[str, set[str]]):
    coverage = {}

    for clazz in all_methods:
        if clazz not in coverage:
            coverage[clazz] = {'is_activity': False, 'methods': {}}
        for m in all_methods[clazz]:
            if m not in coverage[clazz]['methods']:
                coverage[clazz]['methods'][m] = False

    for clazz in called_methods:
        cont = 0
        for m in called_methods[clazz]:
            coverage[clazz]['methods'][m] = True
            cont = cont + 1
        total = len(coverage[clazz]['methods'])
        coverage[clazz]['summary'] = {'total_methods': total, 'called_methods': cont,
                                      'method_coverage': (cont * 100 / total)}

    return coverage

# def process_coverage(called_methods: dict[str, set[str]], apk_name: str, apk_results_dir: str):
#     coverage = {}
#     # apk_path = os.path.join(APKS_DIR, apk_name)
#     # app = App(apk_path)
#     all_methods_file_name = apk_name + EXTENSION_SOOT
#     all_methods_file = os.path.join(apk_results_dir, all_methods_file_name)
#     all_methods: dict[str, set[str]]
#     if os.path.exists(all_methods_file):
#         all_methods = me.parse_soot_result(all_methods_file)
#         for clazz in all_methods:
#             if clazz not in coverage:
#                 coverage[clazz] = {'is_activity': False, 'methods': {}}
#             for m in all_methods[clazz]:
#                 if m not in coverage[clazz]['methods']:
#                     coverage[clazz]['methods'][m] = False
#         for clazz in called_methods:
#             cont = 0
#             for m in called_methods[clazz]:
#                 coverage[clazz]['methods'][m] = True
#                 cont = cont + 1
#             total = len(coverage[clazz]['methods'])
#             coverage[clazz]['summary'] = {'total_methods': total, 'called_methods': cont, 'method_coverage': (cont*100/total)}
#     else:
#         #TODO
#         pass
#
#     return coverage


# def get_all_methods(apk_path: str):
#     app = App(apk_path)
#     out_file = "/home/pedro/tmp/teste_soot.csv"
#     __execute_soot(apk_path, app.package_name, out_file)
#     return __parse_soot_result(out_file)

#
# def __parse_soot_result(soot_result: str):
#     classes = {}
#     first_line = True
#     with open(soot_result) as f:
#         while True:
#             line = f.readline()
#             if not line:
#                 break
#             if first_line:
#                 first_line = False
#                 continue
#
#             split = line.split(";")
#             clazz = split[0]
#             method = split[1].replace('\n', '')
#
#             if clazz not in classes:
#                 classes[clazz] = set()
#             classes[clazz].add(method)
#     return classes
#
#
# def __execute_soot(apk_path: str, package: str, out_file: str):
#     extractor_jar = os.path.join(LIB_DIR, 'methods-extractor', 'methods-extractor.jar')
#     print("JAR: {}".format(extractor_jar))
#     extractor_cmd = Command("java", [
#         "-jar", extractor_jar,
#         "--apk", apk_path,
#         "--apk-package", package,
#         "--android-dir", ANDROID_PLATFORMS_DIR,
#         "--output", out_file
#     ])
#     extractor_result = extractor_cmd.invoke(stdout=sys.stdout)
#     if extractor_result.code != 0:
#         raise Exception("Error while finding all methods in APK: {0}. {1}".format(apk_path,
#                                                                                     extractor_result.stderr))

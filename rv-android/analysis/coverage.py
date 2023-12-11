import copy
import csv
import os
import sys

from commands.command import Command
from settings import LIB_DIR, ANDROID_PLATFORMS_DIR, INSTRUMENTED_DIR, APKS_DIR
from app import App
from constants import *




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

def execute(called_methods: dict[str, set[str]], all_methods: dict):
    coverage = copy.deepcopy(all_methods)

    coverage[SUMMARY] = {TOTAL_CLASSES: len(coverage), TOTAL_ACTIVITIES: 0, CALLED_ACTIVITIES: 0,
                         ACTIVITIES_COVERAGE: 0, 'activities_coverage_total': 0,
                         TOTAL_METHODS: 0, CALLED_METHODS: 0, METHOD_COVERAGE: 0,
                                TOTAL_METHODS_JCA_REACHABLE: 0, METHODS_JCA_REACHABLE: 0,
                                'methods_jca_reachable_coverage': 0, 'methods_jca_reachable_coverage_total': 0}
    for clazz in all_methods:
        coverage[clazz][SUMMARY] = {TOTAL_METHODS: 0, CALLED_METHODS: 0, METHOD_COVERAGE: 0,
                                           TOTAL_METHODS_JCA_REACHABLE: 0, METHODS_JCA_REACHABLE: 0,
                                           'methods_jca_reachable_coverage': 0, 'methods_jca_reachable_coverage_total': 0}

        print("CLAZZ: {}".format(clazz))

        if coverage[clazz][IS_ACTIVITY]:
            coverage[SUMMARY][TOTAL_ACTIVITIES] += 1
        for m in coverage[clazz][METHODS]:
            coverage[clazz][METHODS][m][CALLED] = False
            coverage[clazz][SUMMARY][TOTAL_METHODS] += 1
            coverage[SUMMARY][TOTAL_METHODS] += 1
            if coverage[clazz][METHODS][m][REACHABLE] and coverage[clazz][METHODS][m][USE_JCA]:
                coverage[clazz][SUMMARY][TOTAL_METHODS_JCA_REACHABLE] += 1
                coverage[SUMMARY][TOTAL_METHODS_JCA_REACHABLE] += 1

    for clazz in called_methods:
        if coverage[clazz][IS_ACTIVITY]:
            coverage[SUMMARY][CALLED_ACTIVITIES] += 1
        for m in called_methods[clazz]:
            coverage[clazz][METHODS][m][CALLED] = True
            coverage[clazz][SUMMARY][CALLED_METHODS] += 1
            coverage[SUMMARY][CALLED_METHODS] += 1
            if coverage[clazz][METHODS][m][REACHABLE] and coverage[clazz][METHODS][m][USE_JCA]:
                coverage[clazz][SUMMARY][METHODS_JCA_REACHABLE] += 1
                coverage[SUMMARY][METHODS_JCA_REACHABLE] += 1

        method_coverage = calculate_coverage(coverage[clazz][SUMMARY][TOTAL_METHODS], coverage[clazz][SUMMARY][CALLED_METHODS])
        methods_jca_reachable_coverage = calculate_coverage(coverage[clazz][SUMMARY][TOTAL_METHODS_JCA_REACHABLE], coverage[clazz][SUMMARY][METHODS_JCA_REACHABLE])
        methods_jca_reachable_coverage_total = calculate_coverage(coverage[clazz][SUMMARY][TOTAL_METHODS], coverage[clazz][SUMMARY][METHODS_JCA_REACHABLE])

        coverage[clazz][SUMMARY][METHOD_COVERAGE] = method_coverage
        coverage[clazz][SUMMARY]['methods_jca_reachable_coverage'] = methods_jca_reachable_coverage
        coverage[clazz][SUMMARY]['methods_jca_reachable_coverage_total'] = methods_jca_reachable_coverage_total

    coverage[SUMMARY][ACTIVITIES_COVERAGE] = calculate_coverage(coverage[SUMMARY][TOTAL_ACTIVITIES], coverage[SUMMARY][CALLED_ACTIVITIES])
    coverage[SUMMARY]['activities_coverage_total'] = calculate_coverage(coverage[SUMMARY][TOTAL_CLASSES], coverage[SUMMARY][CALLED_ACTIVITIES])
    coverage[SUMMARY][METHOD_COVERAGE] = calculate_coverage(coverage[SUMMARY][TOTAL_METHODS], coverage[SUMMARY][CALLED_METHODS])
    coverage[SUMMARY]['methods_jca_reachable_coverage'] = calculate_coverage(coverage[SUMMARY][TOTAL_METHODS_JCA_REACHABLE], coverage[SUMMARY][METHODS_JCA_REACHABLE])
    coverage[SUMMARY]['methods_jca_reachable_coverage_total'] = calculate_coverage(coverage[SUMMARY][TOTAL_METHODS], coverage[SUMMARY][METHODS_JCA_REACHABLE])

    return coverage


def calculate_coverage(total: int, called: int):
    coverage = 0
    if called > 0:
        coverage = (called * 100) / total
    return coverage

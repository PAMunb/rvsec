import json
import os

from constants import *
import analysis.logcat_parser as parser
import analysis.reachable_methods_mop as reach
import analysis.coverage as cov

def process_results(results_dir: str):
    parse_results(results_dir)





def parse_results(results_dir: str):
    results = {}
    if os.path.exists(results_dir) and os.path.isdir(results_dir):
        for apk_folder in os.listdir(results_dir):
            apk_folder_path = os.path.join(results_dir, apk_folder)
            if os.path.isdir(apk_folder_path):
                print("FOLDER: {}".format(apk_folder))
                all_methods = parse_all_methods_file(results_dir, apk_folder)
                for file in os.listdir(apk_folder_path):
                    if file.casefold().endswith(EXTENSION_LOGCAT):
                        apk, rep, timeout, tool = parse_filename(file)

                        if apk not in results:
                            results[apk] = {'repetitions': {}, SUMMARY: {'jca_error': False, 'activity_coverage': 0.0, 'methods_coverage': 0.0}, 'classes': []}

                        if rep not in results[apk]['repetitions']:
                            results[apk]['repetitions'][rep] = {'timeouts': {}, SUMMARY: {'jca_error': False, 'activity_coverage': 0.0, 'methods_coverage': 0.0}}

                        if timeout not in results[apk]['repetitions'][rep]['timeouts']:
                            results[apk]['repetitions'][rep]['timeouts'][timeout] = {'tools': {}, 'summary': {'jca_error': False, 'activity_coverage': 0.0, 'methods_coverage': 0.0}}

                        if tool not in results[apk]['repetitions'][rep]['timeouts'][timeout]['tools']:
                            rvsec_errors, called_methods = parser.parse_logcat_file(os.path.join(apk_folder_path, file))
                            coverage = cov.execute(called_methods, all_methods)

                            results[apk][SUMMARY][TOTAL_CLASSES] = coverage[SUMMARY][TOTAL_CLASSES]
                            results[apk][SUMMARY][TOTAL_ACTIVITIES] = coverage[SUMMARY][TOTAL_ACTIVITIES]
                            results[apk][SUMMARY][TOTAL_METHODS] = coverage[SUMMARY][TOTAL_METHODS]
                            results[apk][SUMMARY][TOTAL_METHODS_JCA_REACHABLE] = coverage[SUMMARY][TOTAL_METHODS_JCA_REACHABLE]

                            summary = {CALLED_ACTIVITIES: coverage[SUMMARY][CALLED_ACTIVITIES],
                                       CALLED_METHODS: coverage[SUMMARY][CALLED_METHODS],
                                       METHODS_JCA_REACHABLE: coverage[SUMMARY][METHODS_JCA_REACHABLE],
                                       ACTIVITIES_COVERAGE: coverage[SUMMARY][ACTIVITIES_COVERAGE],
                                       METHOD_COVERAGE: coverage[SUMMARY][METHOD_COVERAGE],
                                       }
                            # results[apk]['repetitions'][rep]['timeouts'][timeout]['tools'][tool][SUMMARY] = summary
                            results[apk]['repetitions'][rep]['timeouts'][timeout]['tools'][tool] = {SUMMARY: summary}


                            # # jca_error, activity_coverage, method_coverage = parse_result(os.path.join(apk_folder_path, file))
                            # tmp = process_result_file(os.path.join(apk_folder_path, file), all_methods)
                            # results[apk]['repetitions'][rep]['timeouts'][timeout]['tools'][tool] = tmp
                            # # results[apk]['repetitions'][rep]['timeouts'][timeout]['tools'][tool] = {'summary': {'jca_error': jca_error, 'activity_coverage': activity_coverage, 'methods_coverage': method_coverage}}

    json_formatted_str = json.dumps(results, indent=2)
    print(json_formatted_str)
    # print(results)
    with open("results_analysis.json", "w") as outfile:
        outfile.write(json_formatted_str)


def parse_filename(name: str):
    print("Parsing file: {}".format(name))
    parts = name.split("__")
    return parts[0], parts[1], parts[2], parts[3][:-len(EXTENSION_LOGCAT)]


def parse_all_methods_file(results_dir, apk_name):
    all_methods_file_name = apk_name + EXTENSION_METHODS
    all_methods_file = os.path.join(results_dir, apk_name, all_methods_file_name)
    print("parse_all_methods_file : {}".format(all_methods_file))
    all_methods = {}
    if os.path.exists(all_methods_file):
        all_methods = reach.read_reachable_methods(all_methods_file)
    return all_methods


def process_result_file(result_file: str, all_methods):
    print("Parsing file: {}".format(result_file))
    summary = {}
    rvsec_errors, called_methods = parser.parse_logcat_file(result_file)
    if len(all_methods) > 0:
        coverage = cov.execute(called_methods, all_methods)
        #summary = {SUMMARY: coverage[SUMMARY]}
        summary = coverage[SUMMARY]

    return summary


# def parse_result(result_file: str):
#     jca_errors = []
#     jca_error = False
#     activity_coverage = 0.0
#     method_coverage = 0.0
#     print("Parsing file: {}".format(result_file))
#     rvsec_errors, called_methods = parser.parse_logcat_file(result_file)
#     #TODO
#     return jca_error, activity_coverage, method_coverage


if __name__ == '__main__':
    dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/teste"

    process_results(dir)

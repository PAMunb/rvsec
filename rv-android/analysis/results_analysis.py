import json
import os

from constants import EXTENSION_LOGCAT
import logcat_parser as parser

def process_results(results_dir: str):
    parse_results(results_dir)





def parse_results(results_dir: str):
    results = {}
    if os.path.exists(results_dir) and os.path.isdir(results_dir):
        for folder in os.listdir(results_dir):
            folder_path = os.path.join(results_dir, folder)
            if os.path.isdir(folder_path):
                print("FOLDER: {}".format(folder))
                for file in os.listdir(folder_path):
                    if file.casefold().endswith(EXTENSION_LOGCAT):
                        apk, rep, timeout, tool = parse_filename(file)

                        if apk not in results:
                            results[apk] = {'repetitions': {}, 'summary': {'jca_error': False, 'activity_coverage': 0.0, 'methods_coverage': 0.0}, 'classes': []}

                        if rep not in results[apk]['repetitions']:
                            results[apk]['repetitions'][rep] = {'timeouts': {}, 'summary': {'jca_error': False, 'activity_coverage': 0.0, 'methods_coverage': 0.0}}

                        if timeout not in results[apk]['repetitions'][rep]['timeouts']:
                            results[apk]['repetitions'][rep]['timeouts'][timeout] = {'tools': {}, 'summary': {'jca_error': False, 'activity_coverage': 0.0, 'methods_coverage': 0.0}}

                        if tool not in results[apk]['repetitions'][rep]['timeouts'][timeout]['tools']:
                            jca_error, activity_coverage, method_coverage = parse_result(os.path.join(folder_path, file))
                            results[apk]['repetitions'][rep]['timeouts'][timeout]['tools'][tool] = {'summary': {'jca_error': jca_error, 'activity_coverage': activity_coverage, 'methods_coverage': method_coverage}}

    json_formatted_str = json.dumps(results, indent=2)
    print(json_formatted_str)
    # print(results)
    with open("results_analysis.json", "w") as outfile:
        outfile.write(json_formatted_str)


def parse_filename(name: str):
    print("Parsing file: {}".format(name))
    parts = name.split("__")
    return parts[0], parts[1], parts[2], parts[3][:-len(EXTENSION_LOGCAT)]


def parse_result(result_file: str):
    jca_errors = []
    jca_error = False
    activity_coverage = 0.0
    method_coverage = 0.0
    print("Parsing file: {}".format(result_file))
    rvsec_errors, called_methods = parser.parse_logcat_file(result_file)
    #TODO
    return jca_error, activity_coverage, method_coverage


if __name__ == '__main__':
    dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/teste"

    process_results(dir)

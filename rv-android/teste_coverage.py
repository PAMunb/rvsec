import json
import os
import analysis.coverage as cov
import analysis.logcat_parser as parser
import analysis.reachable_methods_mop as reach
from constants import EXTENSION_METHODS


def tmp01():
    result_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/20231212113846/app-debug.apk"
    result_file = os.path.join(result_dir, "app-debug.apk__1__120__monkey.logcat")
    apk_name = "app-debug.apk"
    exec(apk_name, result_dir, result_file)


def tmp02():
    apk_name = "com.example.openpass_1.apk"
    result_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/20231212113846/com.example.openpass_1.apk"
    result_file = os.path.join(result_dir, "com.example.openpass_1.apk__1__120__monkey.logcat")
    exec(apk_name, result_dir, result_file)


def exec(apk_name, result_dir, result_file):
    rvsec_errors, called_methods = parser.parse_logcat_file(result_file)

    all_methods = {}
    all_methods_file_name = apk_name + EXTENSION_METHODS
    all_methods_file = os.path.join(result_dir, all_methods_file_name)
    if os.path.exists(all_methods_file):
        all_methods = reach.read_reachable_methods(all_methods_file)
        # json_formatted_str = json.dumps(all_methods, indent=2)
        # print(json_formatted_str)

    coverage = cov.process_coverage(called_methods, all_methods)

    json_formatted_str = json.dumps(coverage, indent=2)
    print(json_formatted_str)


if __name__ == '__main__':
    tmp01()
    # tmp02()

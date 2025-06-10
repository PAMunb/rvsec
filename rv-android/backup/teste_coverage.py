import json
import os
from rvandroid import analysis as cov, analysis as reach
import rvandroid.log.logcat_parser as parser
from rvandroid.constants import EXTENSION_METHODS


def tmp01():
    apk_name = "cryptoapp.apk"
    base_results_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results"
    result_dir = os.path.join(base_results_dir, "20241105090059", apk_name)
    result_file = os.path.join(result_dir, "cryptoapp.apk__1__60__monkey.logcat")
    execute(apk_name, result_dir, result_file)


def execute(apk_name, result_dir, result_file):
    rvsec_errors, called_methods, _ = parser.parse_logcat_file(result_file)

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

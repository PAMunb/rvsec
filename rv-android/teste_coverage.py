import json
import os
import analysis.coverage as cov
from constants import EXTENSION_METHODS

if __name__ == '__main__':
    result_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/20231206110817/app-debug.apk"
    result_file = os.path.join(result_dir, "app-debug.apk__1__90__monkey.logcat")
    apk_name = "app-debug.apk"
    all_methods_file_name = apk_name + EXTENSION_METHODS
    all_methods_file = os.path.join(result_dir, all_methods_file_name)
    import analysis.logcat_parser as parser
    import analysis.methods_extractor as me
    import analysis.reachable_methods_mop as reach

    rvsec_errors, called_methods = parser.parse_logcat_file(result_file)

    all_methods = {}
    if os.path.exists(all_methods_file):
        # all_methods = me.parse(all_methods_file)
        all_methods = reach.read_reachable_methods(all_methods_file)
        # json_formatted_str = json.dumps(all_methods, indent=2)
        # print(json_formatted_str)

    coverage = cov.execute(called_methods, all_methods)

    json_formatted_str = json.dumps(coverage, indent=2)
    print(json_formatted_str)

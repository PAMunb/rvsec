import json
import os
import analysis.coverage as cov
from constants import EXTENSION_SOOT

if __name__ == '__main__':
    result_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/teste/cryptoapp.apk"
    result_file = os.path.join(result_dir, "cryptoapp.apk__1__90__monkey.logcat")
    apk_name = "cryptoapp.apk"
    all_methods_file_name = apk_name + EXTENSION_SOOT
    all_methods_file = os.path.join(result_dir, all_methods_file_name)
    import analysis.logcat_parser as parser
    import analysis.methods_extractor as me

    rvsec_errors, called_methods = parser.parse_logcat_file(result_file)

    all_methods: dict[str, set[str]] = {}
    if os.path.exists(all_methods_file):
        all_methods = me.parse_soot_result(all_methods_file)

    coverage = cov.execute(called_methods, all_methods)

    json_formatted_str = json.dumps(coverage, indent=2)
    print(json_formatted_str)

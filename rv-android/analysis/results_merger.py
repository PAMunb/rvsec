import glob
import json
import os.path


def merge(base_dir, out_dir):
    merged_results_file = os.path.join(out_dir, "merged_results_analysis.json")
    merged_instrument_errors = os.path.join(out_dir, "merged_instrument_errors.json")

    global_results = {}
    search_dir = base_dir + "/**/results_analysis.json"
    _merge(search_dir, global_results)
    save(merged_results_file, global_results)

    global_instrument = {}
    search_dir = base_dir + "/**/instrument_errors.json"
    _merge(search_dir, global_instrument)
    save(merged_instrument_errors, global_instrument)

    print("APKS_TESTADOS={}".format(len(global_results)))
    print("ERROS={}".format(len(global_instrument)))


def _merge(search_dir, global_dict):
    files = glob.glob(pathname=search_dir, recursive=True)
    for file in files:
        with open(file, "r") as f:
            result = json.load(f)
            global_dict.update(result)


def save(out_file, merged_dict):
    with open(out_file, "w") as f:
        json.dump(merged_dict, f, indent=4)
    print("File saved: {}".format(out_file))

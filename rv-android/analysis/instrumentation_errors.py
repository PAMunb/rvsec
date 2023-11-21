import csv
import json
import os.path


def execute(errors_file: str, out_file: str):
    apks = complete(errors_file)

    with open(out_file, 'w') as f:
        f.write("file,min_sdk,target_sdk,lastUpdated,tag,error \n")
        for file in apks:
            apk = apks[file]
            f.write("{},{},{},{},{},{}\n".format(file, apk["min_sdk"], apk["target_sdk"], apk["lastUpdated"],
                                                 apk["tag"], apk["error"]))


def complete(file: str):
    with open(file) as error_file:
        errors = json.load(error_file)

        apks = create_base_dict()
        for error in errors:
            apks[error]["error"] = "True"
            apks[error]["tag"] = errors[error]["tool"]
    return apks


def simple(errors_file: str):
    with open(errors_file) as error_file:
        errors = json.load(error_file)

        stats = {}
        for error in errors:
            tool = errors[error]["tool"]
            if tool not in stats:
                stats[tool] = 0
            stats[tool] = stats[tool] + 1

        print("TOTAL ERRORS: {}".format(len(errors)))
        for tool in stats:
            print(" - {} = {}".format(tool, stats[tool]))


def create_base_dict():
    parent_dir = os.path.join(os.getcwd(), os.path.abspath('..'))
    fdroid_csv = os.path.join(parent_dir, "fdroid", "final_apps_to_download_mop_enabled.csv")
    new_dict = {}
    with open(fdroid_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # multidex, size
            new_dict[row["file"]] = {'min_sdk': row["min_sdk"], 'target_sdk': row["target_sdk"],
                                     'lastUpdated': row["lastUpdated"], 'error': 'False', 'tag': 'ok'}
    return new_dict


if __name__ == '__main__':
    errors_file = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/instrument_errors_23specs_598apks.json"
    out_file = "teste_analise.csv"
    execute(errors_file, out_file)

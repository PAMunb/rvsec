import os
from csv import DictReader, DictWriter

from androguard.core.analysis.analysis import Analysis, MethodAnalysis, ClassAnalysis
from androguard.core.bytecodes.apk import APK
from androguard.misc import AnalyzeAPK


def execute(apks_dir, csv_path):
    mapa = map_column_package(apks_dir)
    apps = read_csv(csv_path)
    for app in apps:
        package = False
        if app['file'] in mapa:
            package = mapa[app['file']]
        app['package'] = package
    write_csv(apps, csv_path)
    print("FIM DE FESTA!!!")


def map_column_package(apks_dir):
    apk: APK
    a: Analysis
    clazz: ClassAnalysis
    mapa = {}
    files = os.listdir(apks_dir)
    total = len(files)
    cont = 1
    for filename in files:
        print("Analyzing [{}/{}]: {}".format(cont, total, filename))
        cont = cont + 1

        apk_path = os.path.join(apks_dir, filename)

        apk, _, a = AnalyzeAPK(apk_path)

        has_implementation_in_package = False
        for clazz in a.get_classes():
            if apk.package.replace(".", "/") in str(clazz.name):
                has_implementation_in_package = True
                break
        mapa[filename] = has_implementation_in_package

    return mapa


def read_csv(csv_path):
    print("Reading CSV ...")
    with open(csv_path, 'r') as f:
        dict_reader = DictReader(f)
        list_of_dict = list(dict_reader)
        return list_of_dict


def write_csv(apps: list, csv_path):
    print("Writing CSV ...")
    # field_names = list(apps[0].keys())
    field_names = ['name', 'categories', 'mop', 'package', 'min_sdk', 'target_sdk', 'file', 'sourceCode', 'lastUpdated']

    with open(csv_path, 'w') as csvfile:
        writer = DictWriter(csvfile, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(apps)


if __name__ == '__main__':
    csv_file = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/fdroid/final_apps_to_download.csv"
    apks_path = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks"
    execute(apks_path, csv_file)

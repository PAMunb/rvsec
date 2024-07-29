import os
import json
from csv import DictReader, DictWriter
import numpy as np
import json
import pandas as pd
import matplotlib.pyplot as plt

from androguard.core.analysis.analysis import Analysis, MethodAnalysis, ClassAnalysis
from androguard.core.bytecodes.apk import APK
from androguard.misc import AnalyzeAPK
from constants import EXTENSION_METHODS, RVSEC_ERRORS, REPETITIONS, TIMEOUTS, TOOLS, SUMMARY, METHOD_COVERAGE, \
    METHODS_JCA_COVERAGE, ACTIVITIES_COVERAGE

DECLARED_PACKAGE = "declared_package"
USED_PACKAGES = "used_packages"
SAME_PACKAGE = "package"

#dos 4162 apks do froid, 629 usam jca ... mas apenas 557 conseguiram ser baixados para o experimento ... 557 + 72 = 629

def execute(apks_path, csv_path):
    cont_not_in_map = 0
    cont_in_map = 0
    cont_in_map_same_package = 0
    apks = find_apk_files(apks_path)
    mapa = map_column_package(apks)
    apps = read_csv(csv_path)
    for app in apps:
        app[DECLARED_PACKAGE] = ""
        app[USED_PACKAGES] = ""
        package = False
        if app['file'] in mapa:
            cont_in_map+=1
        # if app['mop'] != 'No':
            package = mapa[app['file']][SAME_PACKAGE]
            if mapa[app['file']][SAME_PACKAGE]:
                cont_in_map_same_package+=1
            app[DECLARED_PACKAGE] = mapa[app['file']][DECLARED_PACKAGE]
            app[USED_PACKAGES] = mapa[app['file']][USED_PACKAGES]
        # elif app['mop'] != 'No':
        #     cont_not_in_map += 1
        #     print(app['file'])
        app['package'] = package
    write_csv(apps, csv_path)
    print("cont_not_in_map={}".format(cont_not_in_map))
    print("cont_in_map={}".format(cont_in_map))
    print("cont_in_map_same_package={}".format(cont_in_map_same_package))
    print("FIM DE FESTA!!!")


def map_column_package(apks):
    apk: APK
    a: Analysis
    clazz: ClassAnalysis
    mapa = {}
    total = len(apks)
    cont = 1
    xxx = 0
    for apk_path in apks:
        print("Analyzing [{}/{}]: {}".format(cont, total, apk_path))
        cont = cont + 1

        apk = APK(apk_path)
        has_implementation_in_package = False
        print("{}={}".format(apk.package, apk.get_activities()))
        for activity in apk.get_activities():
            if apk.package in activity:
                has_implementation_in_package = True
                xxx+=1
                break
        print(has_implementation_in_package)
        filename = os.path.basename(apk.filename)
        mapa[filename] = {}
        mapa[filename][SAME_PACKAGE] = has_implementation_in_package
        mapa[filename][DECLARED_PACKAGE] = apk.package
        mapa[filename][USED_PACKAGES] = list(get_packages(apk))
    print("CONT= {}".format(xxx))
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
    field_names = ['name', 'categories', 'mop', SAME_PACKAGE, 'min_sdk', 'target_sdk', 'file', 'sourceCode', 'lastUpdated', DECLARED_PACKAGE, USED_PACKAGES]

    cont = 0
    for app in apps:
        if app['package']:
            cont += 1
    print("write_csv_cont={}".format(cont))


    with open(csv_path, 'w') as csvfile:
        writer = DictWriter(csvfile, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(apps)

def find_apk_files(directory_path):
    apks = []
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.apk'):
                apks.append(os.path.join(root, file))
    return apks


def tmp_verifica_package(apks_path):
    apks = find_apk_files(apks_path)
    for a in apks:
        apk = APK(a)

        packages = get_packages(apk)
        print("{}={}".format(apk.package, packages))
        # print("{}={}".format(apk.package, common_prefix(packages)))

        # is_in_package = False
        # print("{}={}".format(apk.package, apk.get_activities()))
        # for activity in apk.get_activities():
        #     if apk.package in activity:
        #         is_in_package = True
        # print("{}={}".format(apk.package, is_in_package))


def get_packages(apk: APK):
    packages = set()
    packages.add(apk.package)

    packages.update(aux_get_packages(apk, apk.get_activities()))
    packages.update(aux_get_packages(apk, apk.get_services()))
    packages.update(aux_get_packages(apk, apk.get_receivers()))

    return packages


def aux_get_packages(apk: APK, lista: list):
    packages = set()
    for item in lista:
        if apk.package not in item:
            package = item[:item.rfind(".")]
            packages.add(package)
    return packages

def common_prefix(strings: set[str]) -> str:
    # common prefix cannot be larger than the smallest str
    min_length = min(len(string) for string in strings)
    strings = [string[:min_length] for string in strings]

    import numpy as np
    array = np.array([list(x) for x in strings])  # covert to numpy matrix for column-wise operations
    for i in range(min_length):
        # for every column check if all char values are the same (same as first)
        if not all(array[:, i] == array[0][i]):
            # if not return the substring before the first char difference
            return strings[0][:i]

    # the common prefix is the full (shortest) str
    return strings[0]


def cont_mop(csv_path):
    cont = 0
    apps = read_csv(csv_path)
    for app in apps:
        if app['mop'] != 'No':
            cont += 1
    return cont

def checar_package_na_cobertura(results_file):
    data = {}
    with open(results_file, "r") as f:
        result = json.load(f)
        for apk in result:
            data[apk] = {'activity': [],
                         'method': [],
                         'mop': []}
            for rep in result[apk][REPETITIONS]:
                for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
                    for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                        summary = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool][SUMMARY]
                        print(summary[ACTIVITIES_COVERAGE])
                        data[apk]['activity'].append(summary[ACTIVITIES_COVERAGE])
                        data[apk]['method'].append(summary[METHOD_COVERAGE])
                        data[apk]['mop'].append(summary[METHODS_JCA_COVERAGE])
    coverage_by_apk = []
    for apk in data:
        coverage_by_apk.append([apk, np.mean(np.array(data[apk]['activity'])), np.mean(np.array(data[apk]['method'])), np.mean(np.array(data[apk]['mop']))])

    df = pd.DataFrame(coverage_by_apk, columns=['apk', 'activity', 'method', 'mop'])
    # print(df)

    # df.plot()
    # df["activity"].plot(kind='hist')
    # df.plot(x="apk", y=['activity', 'method', 'mop'])
    df.sample(n=10).plot(x="apk", y=['activity', 'method', 'mop'], kind='bar')

    plt.show()


def parse_nova_spec(texto: str):
    s01 = texto.split(":::")
    tmp = s01[0].split("(")[0]

    last_dot_idx = tmp.rfind('.')
    clazz = tmp[:last_dot_idx].strip()
    method = tmp[last_dot_idx+1:].strip()

    a = s01[1].strip()
    spec = a.split(" ")[0].strip()
    msg = a.strip()

    return clazz, method, spec, msg

def parse_jca(texto: str):
    s01 = texto.split(",")
    spec = s01[0].strip()
    clazz = s01[1].strip()
    method = s01[3].strip()

    x = s01[4]
    idx = texto.rfind(x)
    msg = texto[idx+len(x)+1:].strip()

    return clazz, method, spec, msg

def tmp_mostrar_erros(results_file):
    with open(results_file, "r") as f:
        data = []
        result = json.load(f)
        for apk in result:
            for rep in result[apk][REPETITIONS]:
                for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
                    for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                        tool_result = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool]
                        errors = tool_result[RVSEC_ERRORS]
                        if errors:
                            data.append([str(tool), int(rep), int(timeout), len(set(errors))])

    df = pd.DataFrame(data, columns=['tool', 'rep', 'timeout', 'errors'])
    # print(df)
    df.query("rep == 1 and tool == 'droidbot' ").plot(x="timeout", y=["errors"])

    # df.set_index('timeout', inplace=True)
    # # group data by tool and display errors as line chart
    # df = df.query("rep == 1").groupby('tool', group_keys=True)['errors']
    # print(df.describe())
    # # df = df.query("rep == '1'").groupby(['timeout'],  group_keys=True)['errors']
    # df.plot(legend=True)
    plt.show()

    #df.unstack().plot()
    #df.plot(x="timeout", y=["errors"])
    # plt.xticks(rotation=45)

    # df = pd.DataFrame({'day': [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
    #                    'product': ['A', 'A', 'A', 'A', 'A', 'B', 'B', 'B', 'B', 'B'],
    #                    'sales': [4, 7, 8, 12, 15, 8, 11, 14, 19, 20]})
    # # define index column
    # df.set_index('day', inplace=True)
    #
    # # group data by product and display sales as line chart
    # df.groupby('product')['sales'].plot(legend=True)
    #
    # pd.pivot_table(df.reset_index(),
    #                index='day', columns='product', values='sales'
    #                ).plot(subplots=True)
    # plt.show()

def tmp_mostrar_erros2(results_file):
    is_jca=True
    data = {}
    with open(results_file, "r") as f:
        result = json.load(f)
        for apk in result:
            for rep in result[apk][REPETITIONS]:
                if rep not in data:
                    data[rep] = {}
                for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
                    if timeout not in data[rep]:
                        data[rep][timeout] = {}
                    for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                        if tool not in data[rep][timeout]:
                            data[rep][timeout][tool] = {"errors": set(), "total": 0}
                        tool_result = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool]
                        errors = tool_result[RVSEC_ERRORS]
                        for error in errors:
                            data[rep][timeout][tool]["total"] = data[rep][timeout][tool]["total"] + 1
                            data[rep][timeout][tool]["errors"].add(error)

    tmp = []
    for rep in data:
        for timeout in data[rep]:
            for tool in data[rep][timeout]:
                tmp.append([str(tool), int(rep), int(timeout), len(data[rep][timeout][tool]["errors"])])

    df = pd.DataFrame(tmp, columns=['tool', 'rep', 'timeout', 'errors'])
    df = df.sort_values(by=['timeout'], ascending=False, ignore_index=True)
    # print(df)
    # df.query("rep == 1 and tool == 'droidbot' ").plot(x="timeout", y=["errors"])

    df.set_index('timeout', inplace=True)
    # group data by tool and display errors as line chart
    df = df.query("rep == 1").groupby('tool', group_keys=True)['errors']
    print(df.describe())
    # df = df.query("rep == '1'").groupby(['timeout'],  group_keys=True)['errors']
    df.plot(legend=True)
    plt.xticks([60, 120, 180, 300])
    plt.show()

# def checar_package_na_cobertura(results_file):
#     data = {}
#     with open(results_file, "r") as f:
#         result = json.load(f)
#         for apk in result:
#             data[apk] = {'soma': 0.0, 'qtde': 0}
#             for rep in result[apk][REPETITIONS]:
#                 for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
#                     for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
#                         summary = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool][SUMMARY]
#                         print(summary[ACTIVITIES_COVERAGE])
#                         activities_coverage = summary[ACTIVITIES_COVERAGE]
#                         data[apk]['soma'] = data[apk]['soma'] + activities_coverage
#                         data[apk]['qtde'] = data[apk]['qtde'] + 1
#     cont_zero = 0
#     for apk in data:
#         media = (data[apk]['soma'] / data[apk]['qtde'])
#         if media == 0:
#             cont_zero += 1
#         print("{}={}".format(apk, (data[apk]['soma'] / data[apk]['qtde']) ))
#     print("cont_zero={}".format(cont_zero))

def get_categories(app):
    categories = []
    cat_str = app["categories"].replace('[', '').replace(']', '').replace("'", "")
    cat_split = cat_str.split(',')
    for cat in cat_split:
        if cat not in categories:
            categories.append(cat.strip())
    return categories
def teste_categorias(csv_path, results_file):
    data = {}

    apps_fdroid = read_csv(csv_path)
    apps_fdroid_by_apk = {}
    for app in apps_fdroid:
        apps_fdroid_by_apk[app["file"]] = app
        if app["mop"] == 'No':
            continue
        categories = get_categories(app)
        for c in categories:
            if c not in data:
                data[c] = {"cont": 0, "errors_total": 0, "errors": set()}
            data[c]["cont"] = data[c]["cont"] + 1

    with open(results_file, "r") as f:
        result = json.load(f)
        for apk in result:
            for rep in result[apk][REPETITIONS]:
                for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
                    for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                        tool_result = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool]
                        errors = tool_result[RVSEC_ERRORS]
                        for error in errors:
                            categories = get_categories(apps_fdroid_by_apk[apk])
                            for cat in categories:
                                data[cat]["errors_total"] = data[cat]["errors_total"] + 1
                                data[cat]["errors"].add(error)

    categories = []
    for cat in data:
        categories.append([cat, data[cat]["cont"], data[cat]["errors_total"], len(data[cat]["errors"])])

    df = pd.DataFrame(categories, columns=['Category', 'Cont', 'Errors_total', 'errors'])

    df1 = df.sort_values(by=['Cont'], ascending=False, ignore_index=True)
    print(df1)

    df2 = df.sort_values(by=['Errors_total'], ascending=False, ignore_index=True)
    print(df2)


if __name__ == '__main__':
    csv_file = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/fdroid/final_apps_to_download.csv"
    results_file = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/merged_results_analysis.json"
    apks_path = "/pedro/desenvolvimento/RV_ANDROID/apks"

    # print(cont_mop(csv_file))
    # tmp_verifica_package(apks_path)
    # checar_package_na_cobertura(results_file)
    # tmp_mostrar_erros(results_file)
    # tmp_mostrar_erros2(results_file)
    # execute(apks_path, csv_file)
    teste_categorias(csv_file, results_file)

import csv
import glob
import json
import logging
import os
import sys
from csv import DictReader, DictWriter
import analysis.coverage as cov
from constants import *
import numpy as np
import json
import pandas as pd
import matplotlib.pyplot as plt


import analysis.results_merger as merger

def read_fdroid(planilha_fdroid_path):
    apps = {}
    with open(planilha_fdroid_path, 'r') as f:
        dict_reader = DictReader(f)
        list_of_dict = list(dict_reader)
        for app in list_of_dict:
            app['mop'] = False if app['mop'] == 'No' else True
            app['package'] = False if app['package'] == 'False' else True

            apps[app['file']] = app
    return apps

def execute(planilha_fdroid_path, results_file):
    fdroid = read_fdroid(planilha_fdroid_path)

    data = []
    with open(results_file, "r") as f:
        result = json.load(f)
        for apk in result:
            if len(result[apk][RVSEC_ERRORS]) > 0:
                data.append([int(fdroid[apk]["min_sdk"]), int(fdroid[apk]["target_sdk"]), pd.to_datetime(fdroid[apk]["lastUpdated"]) ])

    df = pd.DataFrame(data, columns=['min', 'target', 'update'])
    # print(df.dtypes)
    print(df['min'].describe())
    print(df['target'].describe())
    print(df['update'].describe(datetime_is_numeric=True))

    # MIN_SDK
    min_sdk_bruto = {}
    with open(results_file, "r") as f:
        result = json.load(f)
        for apk in result:
            if len(result[apk][RVSEC_ERRORS]) > 0:
                tmp = int(fdroid[apk]["min_sdk"])
                if tmp not in min_sdk_bruto:
                    min_sdk_bruto[tmp] = 0
                min_sdk_bruto[tmp] = min_sdk_bruto[tmp] + 1

    total_apks_with_errors = 88
    min_sdk = []
    for tmp in min_sdk_bruto:
        value = min_sdk_bruto[tmp]
        min_sdk.append([tmp, value, ((value*100)/total_apks_with_errors)])
    df = pd.DataFrame(min_sdk, columns=['min', 'cont', 'pct'])
    # print(df.describe())
    df1 = df.sort_values(by=['cont'], ascending=False, ignore_index=True)
    df1.plot(x="min", y='cont', kind='bar', title='titulo', grid=True, xlabel="category",
             ylabel="quantidade", legend=False)
    df2 = df.sort_values(by=['pct'], ascending=False, ignore_index=True)
    df2.plot(x="min", y='pct', kind='bar', title='titulo', grid=True, xlabel="category",
             ylabel="percentual (do total com erro)", legend=False)
    df3 = df.sort_values(by=['min'], ascending=False, ignore_index=True)
    df3.plot(x="min", y='pct', kind='bar', title='titulo', grid=True, xlabel="category",
             ylabel="percentual (do total com erro)", legend=False)

    hist = df.hist(bins=5)

    plt.show()

    # lastUpdated
    updated_bruto = {}
    with open(results_file, "r") as f:
        result = json.load(f)
        for apk in result:
            if len(result[apk][RVSEC_ERRORS]) > 0:
                tmp = pd.to_datetime(fdroid[apk]["lastUpdated"])
                year = tmp.year
                if year not in updated_bruto:
                    updated_bruto[year] = 0
                updated_bruto[year] = updated_bruto[year] + 1

    updated = []
    for tmp in updated_bruto:
        value = updated_bruto[tmp]
        updated.append([tmp, value, ((value * 100) / total_apks_with_errors)])
    df = pd.DataFrame(updated, columns=['updated', 'cont', 'pct'])
    # print(df.describe())
    df1 = df.sort_values(by=['cont'], ascending=False, ignore_index=True)
    df1.plot(x="min", y='cont', kind='bar', title='titulo', grid=True, xlabel="category",
             ylabel="quantidade", legend=False)
    df2 = df.sort_values(by=['pct'], ascending=False, ignore_index=True)
    df2.plot(x="min", y='pct', kind='bar', title='titulo', grid=True, xlabel="category",
             ylabel="percentual (do total com erro)", legend=False)
    df3 = df.sort_values(by=['updated'], ascending=False, ignore_index=True)
    df3.plot(x="updated", y='pct', kind='bar', title='titulo', grid=True, xlabel="category",
             ylabel="percentual (do total com erro)", legend=False)

    plt.show()


def cobertura_por_timeout(results_file):
    data = {}
    with open(results_file, "r") as f:
        result = json.load(f)
        for apk in result:
            for rep in result[apk][REPETITIONS]:
                for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
                    if timeout not in data:
                        data[timeout] = {'activity': [],
                                      'method': [],
                                      'mop': []}
                    for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                        summary = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool][SUMMARY]
                        data[timeout]['activity'].append(summary[ACTIVITIES_COVERAGE])
                        data[timeout]['method'].append(summary[METHOD_COVERAGE])
                        data[timeout]['mop'].append(summary[METHODS_JCA_COVERAGE])
    coverage_by_apk = []
    for timeout in data:
        coverage_by_apk.append(
            [int(timeout), np.mean(np.array(data[timeout]['activity'])), np.mean(np.array(data[timeout]['method'])),
             np.mean(np.array(data[timeout]['mop']))])

    df = pd.DataFrame(coverage_by_apk, columns=['timeout', 'activity', 'method', 'mop'])

    df = df.sort_values(by=['timeout'], ascending=False, ignore_index=True)
    # print(df)
    # print(df.dtypes)

    df.plot(x="timeout", y=['activity', 'method', 'mop'],grid=True, xlabel="timeout", ylabel="yyy", legend=True)
    # plt.xticks([60, 120, 180, 300])

    plt.show()


def cobertura_02(results_file):
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
                            data[rep][timeout][tool] = {"apks": set(), "total": 0}
                        tool_result = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool]
                        errors = tool_result[RVSEC_ERRORS]
                        if len(errors) > 0:
                            for error in errors:
                                data[rep][timeout][tool]["total"] = data[rep][timeout][tool]["total"] + 1
                            data[rep][timeout][tool]["apks"].add(apk)

    tmp = []
    for rep in data:
        for timeout in data[rep]:
            for tool in data[rep][timeout]:
                tmp.append([str(tool), int(rep), int(timeout), len(data[rep][timeout][tool]["apks"])])

    df = pd.DataFrame(tmp, columns=['tool', 'rep', 'timeout', 'apks'])
    df = df.sort_values(by=['timeout'], ascending=False, ignore_index=True)
    # print(df)
    # df.query("rep == 1 and tool == 'droidbot' ").plot(x="timeout", y=["errors"])

    df.set_index('timeout', inplace=True)
    # group data by tool and display errors as line chart
    df = df.query("rep == 1").groupby('tool', group_keys=True)['apks']
    print(df.describe())
    # df = df.query("rep == '1'").groupby(['timeout'],  group_keys=True)['errors']
    # df.plot(title='titulo', grid=True, xlabel="timeout", ylabel="quantidade", legend=True)
    df.plot(grid=True, xlabel="timeout", ylabel="quantidade de apps com bugs", legend=True)
    plt.xticks([60, 120, 180, 300])
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

def erros_por_ferramenta(results_file):
    is_jca = True
    with open(results_file, "r") as f:
        data = {}
        result = json.load(f)
        for apk in result:
            for rep in result[apk][REPETITIONS]:
                for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
                    for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                        if tool not in data:
                            data[tool] = {"errors": set(), "total": 0}
                        tool_result = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool]
                        errors = tool_result[RVSEC_ERRORS]
                        for error in errors:
                            if is_jca:
                                clazz, method, spec, msg = parse_jca(error)
                            else:
                                clazz, method, spec, msg = parse_nova_spec(error)

                            data[tool]["total"] = data[tool]["total"] + 1
                            data[tool]["errors"].add(msg)

    print("Quantidade de Ferramentas que encontraram algum erro: {}".format(len(data)))

    tools_totals = []
    for tool in data:
        tools_totals.append([tool, data[tool]["total"], len(data[tool]["errors"])])

    df = pd.DataFrame(tools_totals, columns=['Tool', 'Cont', 'Errors'])
    df = df.sort_values(by=['Cont'], ascending=False, ignore_index=True)
    print(df)

    df.plot(x="Tool", y='Errors', kind='bar', title='titulo', grid=True, xlabel="xxx", ylabel="yyy", legend=False)
    plt.show()

    print("**** Erros unicos por spec:")
    df = df.sort_values(by=['Errors'], ascending=False, ignore_index=True)
    print(df)
    for ind in df.index:
        spec = df['Tool'][ind]
        print("{} ({})".format(spec, len(data[spec]["errors"])))
        errors = sorted(list(data[spec]["errors"]))
        for err in errors:
            print("\t- {}".format(err))


def erros_por_apk_e_ferramenta_binario(results_file):
    is_jca = True
    with open(results_file, "r") as f:
        data = {}
        result = json.load(f)
        for apk in result:
            data[apk] = {}
            for rep in result[apk][REPETITIONS]:
                for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
                    for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                        if tool not in data[apk]:
                            data[apk][tool] = False
                        errors = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool][RVSEC_ERRORS]
                        if len(errors) > 0:
                            data[apk][tool] = True
    sorted_tools = []
    apks_totals = []
    for apk in data:
        line = []#[apk]
        sorted_tools = list(data[apk].keys())
        sorted_tools.sort()
        sorted_dict = {i: data[apk][i] for i in sorted_tools}
        for tool in sorted_dict:
            line.append(data[apk][tool])
        apks_totals.append(line)
    print(apks_totals)

    headers = []#['APK']
    for tool in sorted_tools:
        headers.append(tool)
    df = pd.DataFrame(apks_totals, columns=headers)

    print(df)

    # import plotly.express as px
    # import numpy as np
    # img = np.arange(15 ** 2).reshape((15, 15))
    # print(img)
    # fig = px.imshow(img)
    # fig.show()

    # import plotly.express as px
    # fig = px.imshow(df, aspect="auto")
    # fig.show()


def erros_por_apk_e_ferramenta_heatmap2(results_file):
    is_jca = True
    with open(results_file, "r") as f:
        data = {}
        result = json.load(f)
        for apk in result:
            data[apk] = {}
            for rep in result[apk][REPETITIONS]:
                for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
                    for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                        if tool not in data[apk]:
                            data[apk][tool] = {"total":0, "errors": set()}
                        errors = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool][RVSEC_ERRORS]
                        errors = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool][RVSEC_ERRORS]
                        for error in errors:
                            if is_jca:
                                clazz, method, spec, msg = parse_jca(error)
                            else:
                                clazz, method, spec, msg = parse_nova_spec(error)

                            data[apk][tool]["total"] = data[apk][tool]["total"] + 1
                            data[apk][tool]["errors"].add(msg)

    # tmp = {}
    # for apk in data:
    #     for tool in data[apk]:
    #         if data[apk][tool]["total"] > 0:
    #             if tool not in tmp:
    #                 tmp[tool] = set()
    #             tmp[tool].update(data[apk][tool]["errors"])
    # for tool in tmp:
    #     print("{}={}".format(tool, len(tmp[tool])))


    sorted_tools = []
    apks_totals = []
    for apk in data:
        line = []#[apk]
        sorted_tools = list(data[apk].keys())
        sorted_tools.sort()
        sorted_dict = {i: data[apk][i] for i in sorted_tools}
        for tool in sorted_dict:
            line.append(len(data[apk][tool]["errors"]))
        apks_totals.append(line)
    print(apks_totals)

    headers = []#['APK']
    for tool in sorted_tools:
        headers.append(tool)
    df = pd.DataFrame(apks_totals, columns=headers)
    print(df)

    import plotly.express as px
    # fig = px.imshow(df, aspect="auto", template="ggplot2")
    fig = px.imshow(df,
                    labels=dict(x="Tool", y="APK", color="Errors (unique)"),
                    aspect="auto")#, color_continuous_scale='blues')
    fig.show()


def erros_por_apk_e_ferramenta_heatmap(results_file):
    is_jca = True
    with open(results_file, "r") as f:
        data = {}
        result = json.load(f)
        for apk in result:
            data[apk] = {}
            for rep in result[apk][REPETITIONS]:
                for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
                    for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                        if tool not in data[apk]:
                            data[apk][tool] = 0
                        errors = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool][RVSEC_ERRORS]
                        data[apk][tool] = data[apk][tool] + len(errors)
    sorted_tools = []
    apks_totals = []
    for apk in data:
        line = []#[apk]
        sorted_tools = list(data[apk].keys())
        sorted_tools.sort()
        sorted_dict = {i: data[apk][i] for i in sorted_tools}
        for tool in sorted_dict:
            line.append(data[apk][tool])
        apks_totals.append(line)
    print(apks_totals)

    headers = []#['APK']
    for tool in sorted_tools:
        headers.append(tool)
    df = pd.DataFrame(apks_totals, columns=headers)
    print(df)

    import plotly.express as px
    # fig = px.imshow(df, aspect="auto", template="ggplot2")
    fig = px.imshow(df,
                    labels=dict(x="Tool", y="APK", color="Error Count"),
                    aspect="auto")#, color_continuous_scale='blues')
    fig.show()


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    planilha_fdroid_path = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/fdroid/final_apps_to_download.csv"
    results_file = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/merged_results_analysis.json"

    # execute(planilha_fdroid_path, results_file)

    # cobertura_por_timeout(results_file)
    # cobertura_02(results_file)
    # erros_por_ferramenta(results_file)
    # erros_por_apk_e_ferramenta_binario(results_file)
    erros_por_apk_e_ferramenta_heatmap2(results_file)
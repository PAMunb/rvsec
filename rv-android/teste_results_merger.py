import csv
import glob
import json
import logging
import os
import sys

import analysis.coverage as cov
from constants import EXTENSION_METHODS, RVSEC_ERRORS, REPETITIONS, TIMEOUTS, TOOLS, SUMMARY, METHOD_COVERAGE, \
    METHODS_JCA_COVERAGE, ACTIVITIES_COVERAGE

import analysis.results_merger as merger


def cont_apks_with_rvsec_errors(file):
    cont = 0
    with open(file, "r") as f:
        result = json.load(f)
        for apk in result:
            qtde_erros = len(result[apk][RVSEC_ERRORS])
            print("APK={} .... {}".format(apk, qtde_erros))
            if qtde_erros > 0:
                cont = cont + 1
    print("CONT={}".format(cont))


def gerar_planilha(file, out_file):
    data = []
    data.append(['apk','repetition','timeout', 'tool', 'rvsec_errors', 'activities_coverage', 'method_coverage', 'method_rvsec_coverage'])
    with open(file, "r") as f:
        result = json.load(f)
        for apk in result:
            for rep in result[apk][REPETITIONS]:
                print("rep={}".format(rep))
                for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
                    for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                        xxx = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool]
                        print(xxx)
                        data.append([apk, rep, timeout, tool, len(xxx[RVSEC_ERRORS]),
                                     xxx[SUMMARY][ACTIVITIES_COVERAGE],
                                     xxx[SUMMARY][METHOD_COVERAGE],
                                     xxx[SUMMARY][METHODS_JCA_COVERAGE]])

    with open(out_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)
    print("File saved: {}".format(out_file))


def test_blank_results(base_dir):
    search_dir = base_dir + "/**/results_analysis.json"
    files = glob.glob(pathname=search_dir, recursive=True)
    cont_file = 0
    lista = []
    for file in files:
        with open(file, "r") as f:
            result = json.load(f)
            # print(">>>> {}={}".format(file, len(result)))
            cont_file = cont_file + 1
            lista.append(file)
    print("CONT={}".format(cont_file))
    lista.sort()
    for f in lista:
        print(f)





if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    folder = "/home/pedro/desenvolvimento/RV_ANDROID/RESULTS_experimento01"
    results = "/home/pedro/desenvolvimento/RV_ANDROID/RESULTS_experimento01"
    # merger.merge(folder, results)


    original_results_file = "/home/pedro/tmp/rvandroid/original/results_analysis.json"
    new_tools_results_file = "/home/pedro/tmp/rvandroid/ape/results_analysis.json"
    final_results_file = "/home/pedro/tmp/rvandroid/final_results_analysis.json"
    merger.merge_files(original_results_file, new_tools_results_file, final_results_file)

    file = "/home/pedro/desenvolvimento/RV_ANDROID/RESULTS_experimento01/merged_results_analysis.json"
    # test_blank_results(folder)
    # cont_apks_with_rvsec_errors(file)

    # planilha = os.path.join(folder, "planilha.csv")
    # gerar_planilha(file, planilha)
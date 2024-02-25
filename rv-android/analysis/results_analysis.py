import logging as logging_api

import json
import os

from constants import *
import analysis.logcat_parser as parser
import analysis.reachable_methods_mop as reach
import analysis.coverage as cov

logging = logging_api.getLogger(__name__)

def process_results(results_dir: str, save_file=True):
    logging.info("Processing results in: {}".format(results_dir))
    results = initialize_results(results_dir)
    for apk in results:
        process_apk(results[apk])

    if save_file:
        results_file = os.path.join(results_dir, "results_analysis.json")
        json_formatted_str = json.dumps(results, indent=2)
        with open(results_file, "w") as outfile:
            outfile.write(json_formatted_str)
        logging.info("Results saved in: {}".format(results_file))

    return results

def process_apk(result):
    rvsec_errors = set()
    rvsec_methods_called = set()

    for rep in result[REPETITIONS]:
        err, met = process_execution(result[REPETITIONS][rep])
        rvsec_errors.update(err)
        rvsec_methods_called.update(met)

    result[RVSEC_ERRORS] = list(rvsec_errors)
    result[RVSEC_METHODS_CALLED] = list(rvsec_methods_called)


def process_execution(result):
    rvsec_errors = set()
    rvsec_methods_called = set()

    for timeout in result[TIMEOUTS]:
        err, met = process_timeout(result[TIMEOUTS][timeout])
        rvsec_errors.update(err)
        rvsec_methods_called.update(met)

    result[RVSEC_ERRORS] = list(rvsec_errors)
    result[RVSEC_METHODS_CALLED] = list(rvsec_methods_called)

    return rvsec_errors, rvsec_methods_called


def process_timeout(result):
    rvsec_errors = set()
    rvsec_methods_called = set()
    sum_act_cov = 0
    sum_method_cov = 0
    sum_method_jca_reachable_cov = 0

    for t in result[TOOLS]:
        tool = result[TOOLS][t]

        rvsec_errors.update(tool[RVSEC_ERRORS])
        rvsec_methods_called.update((tool[RVSEC_METHODS_CALLED]))
        sum_act_cov += tool[SUMMARY][ACTIVITIES_COVERAGE]
        sum_method_cov += tool[SUMMARY][METHOD_COVERAGE]
        sum_method_jca_reachable_cov += tool[SUMMARY][METHODS_JCA_COVERAGE]

    result[SUMMARY] = {ACTIVITIES_COVERAGE_AVG: (sum_act_cov / len(result[TOOLS])),
                       METHOD_COVERAGE_AVG: (sum_method_cov / len(result[TOOLS])),
                       METHODS_JCA_COVERAGE_AVG: (sum_method_jca_reachable_cov / len(result[TOOLS])),
                       RVSEC_ERRORS_COUNT: len(rvsec_errors)}
    result[RVSEC_ERRORS] = list(rvsec_errors)
    result[RVSEC_METHODS_CALLED] = list(rvsec_methods_called)

    return rvsec_errors, rvsec_methods_called


def initialize_results(results_dir):
    results = {}
    if os.path.exists(results_dir) and os.path.isdir(results_dir):
        for apk_folder in os.listdir(results_dir):
            apk_folder_path = os.path.join(results_dir, apk_folder)
            if os.path.isdir(apk_folder_path):
                # read list_of.methods (CSV: class,is_activity,method,reachable,use_jca)
                all_methods = parse_all_methods_file(results_dir, apk_folder)
                for file in os.listdir(apk_folder_path):
                    if file.casefold().endswith(EXTENSION_LOGCAT):
                        # recupera informacoes contidas no nome do arquivo
                        apk, rep, timeout, tool = parse_filename(file)

                        if apk not in results:
                            results[apk] = {REPETITIONS: {}, SUMMARY: {},
                                            METHODS_JCA_REACHABLE: list(get_methods_jca_reachable(all_methods))}

                        if rep not in results[apk][REPETITIONS]:
                            results[apk][REPETITIONS][rep] = {TIMEOUTS: {}, SUMMARY: {}}

                        if timeout not in results[apk][REPETITIONS][rep][TIMEOUTS]:
                            results[apk][REPETITIONS][rep][TIMEOUTS][timeout] = {TOOLS: {}, SUMMARY: {}}

                        if tool not in results[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                            # le o arquivo de log e retorna:
                            # - o conjunto de erros (crypto misuse) encontrados
                            # - um mapa contendo os métodos chamados durante a execução (não conta a quantidade de vezes que foi chamado, apenas se foi chamado)
                            #   as chaves são os nomes das classes e o valor é o conjunto dos métodos chamados
                            rvsec_errors, called_methods = parser.parse_logcat_file(os.path.join(apk_folder_path, file))

                            # calcula a cobertura de codigo
                            coverage = cov.process_coverage(called_methods, all_methods)

                            results[apk][SUMMARY][TOTAL_CLASSES] = coverage[SUMMARY][TOTAL_CLASSES]
                            results[apk][SUMMARY][TOTAL_ACTIVITIES] = coverage[SUMMARY][TOTAL_ACTIVITIES]
                            results[apk][SUMMARY][TOTAL_METHODS] = coverage[SUMMARY][TOTAL_METHODS]
                            results[apk][SUMMARY][TOTAL_METHODS_JCA_REACHABLE] = coverage[SUMMARY][TOTAL_METHODS_JCA_REACHABLE]

                            summary = {CALLED_ACTIVITIES: coverage[SUMMARY][CALLED_ACTIVITIES],
                                       CALLED_METHODS: coverage[SUMMARY][CALLED_METHODS],
                                       CALLED_METHODS_JCA_REACHABLE: coverage[SUMMARY][CALLED_METHODS_JCA_REACHABLE],
                                       ACTIVITIES_COVERAGE: coverage[SUMMARY][ACTIVITIES_COVERAGE],
                                       METHOD_COVERAGE: coverage[SUMMARY][METHOD_COVERAGE],
                                       METHODS_JCA_COVERAGE: coverage[SUMMARY][METHODS_JCA_COVERAGE],
                                       RVSEC_ERRORS_COUNT: len(rvsec_errors)}

                            jca_methods_called = set()
                            for clazz in called_methods:
                                #TODO se a classe nao estiver em coverage provavelmente declarou um pacote no manifest e implementou as coisas em outro pacote
                                if clazz in coverage:
                                    for method in called_methods[clazz]:
                                        sig = "{}.{}".format(clazz, method)
                                        if sig not in jca_methods_called and \
                                                method in coverage[clazz][METHODS].keys() and \
                                                coverage[clazz][METHODS][method][CALLED] and \
                                                coverage[clazz][METHODS][method][USE_JCA]:
                                            jca_methods_called.add(sig)

                            results[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool] = {SUMMARY: summary,
                                                                                              RVSEC_ERRORS: list(rvsec_errors),
                                                                                              RVSEC_METHODS_CALLED: list(jca_methods_called)}
    return results


def get_methods_jca_reachable(all_methods):
    methods = set()
    for clazz in all_methods:
        for m in all_methods[clazz][METHODS]:
            if all_methods[clazz][METHODS][m][REACHABLE] and all_methods[clazz][METHODS][m][USE_JCA]:
                sig = "{}.{}".format(clazz, m)
                methods.add(sig)
    return methods


def parse_filename(name: str):
    # print("Parsing file: {}".format(name))
    parts = name.split("__")
    return parts[0], parts[1], parts[2], parts[3][:-len(EXTENSION_LOGCAT)]


def parse_all_methods_file(results_dir, apk_name):
    all_methods_file_name = apk_name + EXTENSION_METHODS
    all_methods_file = os.path.join(results_dir, apk_name, all_methods_file_name)
    all_methods = {}
    if os.path.exists(all_methods_file):
        all_methods = reach.read_reachable_methods(all_methods_file)
    return all_methods

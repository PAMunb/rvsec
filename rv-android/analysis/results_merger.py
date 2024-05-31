import glob
import json
import os.path

from constants import *

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


def merge_files(source_path, target_path, out_file):
    target = {}
    with open(target_path, "r") as f:
        target = json.load(f)

    result = {}
    with open(source_path, "r") as f:
        result = json.load(f)
        for apk in result:
            for rep in result[apk][REPETITIONS]:
                for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
                    for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                        tool_result = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool]
                        target[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool] = tool_result
    # recomputa sumarios ...
    for apk in target:
        apk_atv_soma = 0.0
        apk_method_soma = 0.0
        apk_jca_soma = 0.0
        apk_erros_cont = 0
        apk_erros_unicos = set()
        apk_rvsec_methods_called = set()
        for rep in target[apk][REPETITIONS]:
            rep_atv_soma = 0.0
            rep_method_soma = 0.0
            rep_jca_soma = 0.0
            rep_erros_cont = 0
            rep_erros_unicos = set()
            rep_rvsec_methods_called = set()
            for timeout in target[apk][REPETITIONS][rep][TIMEOUTS]:
                timeout_atv_soma = 0.0
                timeout_method_soma = 0.0
                timeout_jca_soma = 0.0
                timeout_erros_cont = 0
                timeout_erros_unicos = set()
                timeout_rvsec_methods_called = set()
                for tool in target[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                    tool_result = target[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool]
                    timeout_atv_soma = timeout_atv_soma + tool_result[SUMMARY][ACTIVITIES_COVERAGE]
                    timeout_method_soma = timeout_method_soma + tool_result[SUMMARY][METHOD_COVERAGE]
                    timeout_jca_soma = timeout_jca_soma + tool_result[SUMMARY][METHODS_JCA_COVERAGE]
                    timeout_erros_cont = timeout_erros_cont + len(tool_result[RVSEC_ERRORS])
                    timeout_erros_unicos.update(tool_result[RVSEC_ERRORS])
                    timeout_rvsec_methods_called.update(tool_result[RVSEC_METHODS_CALLED])
                    tmp = "\t\t\ttool={}: atv={}, method={}, jca={}, e_cont={}, rv_method={}"
                    print(tmp.format(tool,
                                     tool_result[SUMMARY][ACTIVITIES_COVERAGE],
                                     tool_result[SUMMARY][METHOD_COVERAGE],
                                     tool_result[SUMMARY][METHODS_JCA_COVERAGE],
                                     len(tool_result[RVSEC_ERRORS]),
                                     len(tool_result[RVSEC_METHODS_CALLED])
                                     ))

                # tmp = "\t\ttimeout={}: atv={}, method={}, jca={}, e_cont={}, e_unico={}, rv_method={}, qtde_tools={}"
                # print(tmp.format(timeout,
                #                  timeout_atv_soma,
                #                  timeout_method_soma,
                #                  timeout_jca_soma,
                #                  timeout_erros_cont,
                #                  len(timeout_erros_unicos),
                #                  len(timeout_rvsec_methods_called),
                #                  len(target[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS])
                #                  ))
                # atualizar/recriar o sumario do timeout
                timeout_summary = target[apk][REPETITIONS][rep][TIMEOUTS][timeout][SUMMARY]
                qtde_tools = len(target[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS])
                timeout_summary[ACTIVITIES_COVERAGE_AVG] = media(timeout_atv_soma, qtde_tools)
                timeout_summary[METHOD_COVERAGE_AVG] = media(timeout_method_soma, qtde_tools)
                timeout_summary[METHODS_JCA_COVERAGE_AVG] = media(timeout_jca_soma, qtde_tools)
                timeout_summary[RVSEC_ERRORS_COUNT] = timeout_erros_cont #TODO decidir ... len(timeout_erros_unicos)
                target[apk][REPETITIONS][rep][TIMEOUTS][timeout][RVSEC_ERRORS] = list(timeout_erros_unicos)
                target[apk][REPETITIONS][rep][TIMEOUTS][timeout][RVSEC_METHODS_CALLED] = list(timeout_rvsec_methods_called)

                tmp = "\t\ttimeout={}: atv={}, method={}, jca={}, e_cont={}, e_unico={}, rv_method={}"
                print(tmp.format(timeout,
                                 timeout_summary[ACTIVITIES_COVERAGE_AVG],
                                 timeout_summary[METHOD_COVERAGE_AVG],
                                 timeout_summary[METHODS_JCA_COVERAGE_AVG],
                                 timeout_summary[RVSEC_ERRORS_COUNT],
                                 len(target[apk][REPETITIONS][rep][TIMEOUTS][timeout][RVSEC_ERRORS]),
                                 len(target[apk][REPETITIONS][rep][TIMEOUTS][timeout][RVSEC_METHODS_CALLED])
                                 ))

                rep_atv_soma = rep_atv_soma + timeout_summary[ACTIVITIES_COVERAGE_AVG]
                rep_method_soma = rep_method_soma + timeout_summary[METHOD_COVERAGE_AVG]
                rep_jca_soma = rep_jca_soma + timeout_summary[METHODS_JCA_COVERAGE_AVG]
                rep_erros_cont = rep_erros_cont + timeout_summary[RVSEC_ERRORS_COUNT] #len(target[apk][REPETITIONS][rep][TIMEOUTS][timeout][RVSEC_ERRORS])
                rep_erros_unicos.update(timeout_erros_unicos)
                rep_rvsec_methods_called.update(timeout_rvsec_methods_called)

            # atualizar/recriar o sumario da repeticao
            rep_summary = target[apk][REPETITIONS][rep][SUMMARY]
            qtde_timeouts = len(target[apk][REPETITIONS][rep][TIMEOUTS])
            rep_summary[ACTIVITIES_COVERAGE_AVG] = media(rep_atv_soma, qtde_timeouts)
            rep_summary[METHOD_COVERAGE_AVG] = media(rep_method_soma, qtde_timeouts)
            rep_summary[METHODS_JCA_COVERAGE_AVG] = media(rep_jca_soma, qtde_timeouts)
            rep_summary[RVSEC_ERRORS_COUNT] = rep_erros_cont  # TODO decidir ... len(rep_erros_unicos)
            target[apk][REPETITIONS][rep][RVSEC_ERRORS] = list(rep_erros_unicos)
            target[apk][REPETITIONS][rep][RVSEC_METHODS_CALLED] = list(rep_rvsec_methods_called)

            tmp = "\trep={}: atv={}, method={}, jca={}, e_cont={}, e_unico={}, rv_method={}"
            print(tmp.format(rep,
                             rep_summary[ACTIVITIES_COVERAGE_AVG],
                             rep_summary[METHOD_COVERAGE_AVG],
                             rep_summary[METHODS_JCA_COVERAGE_AVG],
                             rep_summary[RVSEC_ERRORS_COUNT],
                             len(target[apk][REPETITIONS][rep][RVSEC_ERRORS]),
                             len(target[apk][REPETITIONS][rep][RVSEC_METHODS_CALLED])
                             ))

            apk_atv_soma = apk_atv_soma + rep_summary[ACTIVITIES_COVERAGE_AVG]
            apk_method_soma = apk_method_soma + rep_summary[METHOD_COVERAGE_AVG]
            apk_jca_soma = apk_jca_soma + rep_summary[METHODS_JCA_COVERAGE_AVG]
            apk_erros_cont = apk_erros_cont + rep_summary[RVSEC_ERRORS_COUNT]
            apk_erros_unicos.update(rep_erros_unicos)
            apk_rvsec_methods_called.update(rep_rvsec_methods_called)
        # atualizar/recriar o sumario do apk
        apk_summary = target[apk][SUMMARY]
        qtde_reps = len(target[apk][REPETITIONS])
        apk_summary[ACTIVITIES_COVERAGE_AVG] = media(apk_atv_soma, qtde_reps)
        apk_summary[METHOD_COVERAGE_AVG] = media(apk_method_soma, qtde_reps)
        apk_summary[METHODS_JCA_COVERAGE_AVG] = media(apk_jca_soma, qtde_reps)
        apk_summary[RVSEC_ERRORS_COUNT] = apk_erros_cont  # TODO decidir ... len(apk_erros_unicos)
        target[apk][RVSEC_ERRORS] = list(apk_erros_unicos)
        target[apk][RVSEC_METHODS_CALLED] = list(apk_rvsec_methods_called)

        tmp = "apk={}: atv={}, method={}, jca={}, e_cont={}, e_unico={}, rv_method={}"
        print(tmp.format(apk,
                         apk_summary[ACTIVITIES_COVERAGE_AVG],
                         apk_summary[METHOD_COVERAGE_AVG],
                         apk_summary[METHODS_JCA_COVERAGE_AVG],
                         apk_summary[RVSEC_ERRORS_COUNT],
                         len(target[apk][RVSEC_ERRORS]),
                         len(target[apk][RVSEC_METHODS_CALLED])
                         ))
    #salvar o resultado
    save(out_file, target)
    print("Arquivo salvo: {}".format(out_file))


def media(soma: float, cont: int):
    if cont == 0:
        return 0
    return soma / cont


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

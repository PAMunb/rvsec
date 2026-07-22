import json
import os
import time

import pandas as pd

import analysis.reachable_methods_mop as reach
import log.logcat_parser as parser
import log.logcat_parser_exp01 as parser_exp01
from constants import *
from constants import ACTIVITIES_COVERAGE, EXECUTION_MEMORY_FILENAME, EXTENSION_LOGCAT, EXTENSION_METHODS, \
    METHODS_JCA_COVERAGE, METHOD_COVERAGE, REPETITIONS, RVSEC_ERRORS, SUMMARY, TIMEOUTS, TOOLS
from experiment.memory import Memory
from experiment.task import Task
from log.log import RvCoverage, RvError

# fdroid_spreadsheet = "fdroid/final_apps_to_download.csv"

# https://drive.google.com/file/d/1TPAAzWHarsoFP1poZcidBZKtlDoBOtkP/view?usp=drive_link
exp01_generic_instrument_errors_file = "exp01_generic_instrument_errors.json"
exp01_generic_results_file = "exp01_generic_results.json"
exp01_jca_instrument_errors_file = "exp01_jca_instrument_errors.json"
exp01_jca_results_file = "exp01_jca_results.json"
exp02_generic_instrument_errors_file = "exp02_generic_instrument_errors.json"
exp02_generic_results_file = "exp02_generic_results.json"
exp02_jca_instrument_errors_file = "exp02_jca_instrument_errors.json"
exp02_jca_results_file = "exp02_jca_results.json"

# https://drive.google.com/file/d/1-VeROahuYKQGEKzPYyy3gRNKls1VpEzH/view?usp=drive_link
base_results_dir = "/home/pedro/desenvolvimento/RV_ANDROID"
exp01_generic_results_dir = base_results_dir + "/ALL_RESULTS_LOGCAT/experiment01/generic"
exp01_jca_results_dir = base_results_dir + "/ALL_RESULTS_LOGCAT/experiment01/jca"
exp02_generic_results_dir = base_results_dir + "/ALL_RESULTS_LOGCAT/experiment02/generic"
exp02_jca_results_dir = base_results_dir + "/ALL_RESULTS_LOGCAT/experiment02/jca"

# https://drive.google.com/file/d/1U3_aoOzAa3FgR6z3duFI7KCW_HmUMCby/view?usp=drive_link
all_methods_dir = base_results_dir + "/ALL_METHODS"

output_dir = "/home/pedro/tmp/RV"


def get_summary_df(results_file: str):
    if not os.path.exists(results_file):
        return None
    header = ["apk", "rep", "timeout", "tool", "cov_act", "cov_method", "cov_rv_method", "errors"]
    data = []
    with open(results_file, "r") as f:
        result = json.load(f)
        for apk in result:
            for rep in result[apk][REPETITIONS]:
                for timeout in result[apk][REPETITIONS][rep][TIMEOUTS]:
                    for tool in result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS]:
                        summary = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool][SUMMARY]
                        errors = result[apk][REPETITIONS][rep][TIMEOUTS][timeout][TOOLS][tool][RVSEC_ERRORS]
                        cont_error = cont_errors(errors)
                        data.append([apk, int(rep), int(timeout), tool,
                                     summary[ACTIVITIES_COVERAGE],
                                     summary[METHOD_COVERAGE],
                                     summary[METHODS_JCA_COVERAGE],
                                     cont_error])
        return pd.DataFrame(data, columns=header)


def cont_errors(errors):
    if "total" in errors:
        cont_error = errors["total"]
    else:
        cont_error = len(errors)
    return cont_error


def get_errors_df(logcat_file_path: str, tasks: dict, exp01=False):
    if not os.path.exists(logcat_file_path):
        return pd.DataFrame()

    logcat_file, _ = os.path.splitext(logcat_file_path)
    apk, repetition, timeout, tool = __from_logcat_filename(logcat_file)
    rvsec_errors, _, _ = parse_logcat_file(logcat_file_path, exp01)

    task = get_task(apk, repetition, tasks, timeout, tool)

    handled_errors: set[str] = set()

    header = ["apk", "rep", "timeout", "tool", "time", "spec", "class", "method", "message", "unique_msg"]
    data = []
    error: RvError
    for error in rvsec_errors:
        if error.unique_msg in handled_errors:
            continue
        handled_errors.add(error.unique_msg)
        update_time(task, error)
        data.append([
            apk, repetition, timeout, tool,
            error.time_since_task_start,
            error.spec,
            error.class_full_name,
            error.method,
            error.message,
            error.unique_msg
        ])
    return pd.DataFrame(data, columns=header)


def get_coverage_df(logcat_file_path: str, tasks: dict, exp01=False):
    if not os.path.exists(logcat_file_path):
        return pd.DataFrame()

    logcat_file, _ = os.path.splitext(logcat_file_path)
    apk, repetition, timeout, tool = __from_logcat_filename(logcat_file)
    covered_methods: list[RvCoverage]
    _, _, covered_methods = parse_logcat_file(logcat_file_path, exp01)

    all_methods = read_all_methods_file(apk)
    tracker = CoverageTracker(all_methods)

    task = get_task(apk, repetition, tasks, timeout, tool)

    handled_methods: set[str] = set()

    header = ["apk", "rep", "timeout", "tool",
              "time",
              "class", "method", "signature",
              "cov_class", "cov_act", "cov_method", "cov_rv_method"]
    data = []
    for cov in covered_methods:
        sig = "{}.{}".format(cov.clazz, cov.method)
        if sig in handled_methods:
            continue
        handled_methods.add(sig)
        update_time(task, cov)
        class_coverage, activity_coverage, method_coverage, mop_method_coverage = tracker.call(cov)
        data.append([
            apk, repetition, timeout, tool,
            cov.time_since_task_start,
            cov.clazz, cov.method, sig,
            class_coverage, activity_coverage, method_coverage, mop_method_coverage
        ])

    return pd.DataFrame(data, columns=header)


def get_task(apk, repetition, tasks, timeout, tool):
    try:
        task: Task | None = tasks[apk][repetition][timeout][tool]
    except KeyError:
        task = None
    return task


class CoverageTracker:
    def __init__(self, all_methods):
        self.all_methods = all_methods
        self.total_classes = 0
        self.total_activities = 0
        self.total_methods = 0
        self.total_mop_methods = 0
        self.visited_classes: set[str] = set()
        self.visited_activities: set[str] = set()
        self.visited_methods: set[str] = set()
        self.visited_mop_methods: set[str] = set()
        self.__start()

    def __start(self):
        for clazz in self.all_methods:
            self.total_classes += 1
            if self.all_methods[clazz][IS_ACTIVITY]:
                self.total_activities += 1
            for method in self.all_methods[clazz][METHODS]:
                self.total_methods += 1
                if self.all_methods[clazz][METHODS][method][USE_JCA]:
                    self.total_mop_methods += 1

    def call(self, cov: RvCoverage):
        if cov.clazz in self.all_methods:
            sig = "{}.{}".format(cov.clazz, cov.method)
            if cov.clazz not in self.visited_classes:
                self.visited_classes.add(cov.clazz)
            if self.all_methods[cov.clazz][IS_ACTIVITY] and cov.clazz not in self.visited_activities:
                self.visited_activities.add(cov.clazz)
            if cov.method in self.all_methods[cov.clazz][METHODS]:
                self.visited_methods.add(sig)
                if self.all_methods[cov.clazz][METHODS][cov.method][USE_JCA]:
                    self.visited_mop_methods.add(sig)
        return self.coverage()

    def coverage(self):
        class_coverage = self.__pct(self.visited_classes, self.total_classes)
        activity_coverage = self.__pct(self.visited_activities, self.total_activities)
        method_coverage = self.__pct(self.visited_methods, self.total_methods)
        mop_method_coverage = self.__pct(self.visited_mop_methods, self.total_mop_methods)
        return class_coverage, activity_coverage, method_coverage, mop_method_coverage

    def __pct(self, collection: set, total: int):
        return 0 if total == 0 else (len(collection) * 100) / total


def timer(func):
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        print(f"Function '{func.__name__}' executed in: {end_time - start_time: .3f} seconds")
        return result

    return wrapper_timer


def update_time(task: Task, item: RvError | RvCoverage):
    if task is None:
        return
    elapsed = (item.time_occurred - task.start_time).total_seconds() - task.timeout
    item.time_since_task_start = int(elapsed)


def parse_logcat_file(logcat_file_path: str, exp01=False):
    if exp01:
        return parser_exp01.parse_logcat_file(logcat_file_path)
    else:
        return parser.parse_logcat_file(logcat_file_path)


def __from_logcat_filename(logcat_file: str):
    logcat_filename = os.path.basename(logcat_file)
    s = logcat_filename.split("__")
    apk = s[0]
    repetition = s[1]
    timeout = s[2]
    tool = s[3]
    return apk, repetition, timeout, tool


@timer
def sheet_summary(results_file: str, out_file: str):
    df = get_summary_df(results_file)
    df.to_csv(out_file, index=False)
    print(f"File saved: {out_file}")


@timer
def sheet_errors(results_dir: str, out_file: str, exp01=False):
    print(f"Processing errors in: {results_dir}")
    tasks = read_execution_files(results_dir)
    df = visit_logcat_files(exp01, results_dir, tasks, get_errors_df)
    df.to_csv(out_file, index=False)
    print(f"File saved: {out_file}")


@timer
def sheet_coverage(results_dir: str, out_file: str, exp01=False):
    print(f"Processing coverage in: {results_dir}")
    tasks = read_execution_files(results_dir)
    df = visit_logcat_files(exp01, results_dir, tasks, get_coverage_df)
    df.to_csv(out_file, index=False)
    print(f"File saved: {out_file}")


def visit_logcat_files(exp01, results_dir, tasks, func):
    df = pd.DataFrame()
    for root, dirs, files in os.walk(results_dir):
        for file in files:
            if file.endswith(EXTENSION_LOGCAT):
                logcat_file = os.path.join(root, file)
                coverage_df = func(logcat_file, tasks, exp01)
                df = pd.concat([df, coverage_df], axis=0)
    return df


@timer
def create_summary():
    print("[+] Creating summaries ...")
    sheet_summary(exp01_generic_results_file, f"{output_dir}/exp01_generic_summary.csv")
    sheet_summary(exp01_jca_results_file, f"{output_dir}/exp01_jca_summary.csv")
    sheet_summary(exp02_generic_results_file, f"{output_dir}/exp02_generic_summary.csv")
    sheet_summary(exp02_jca_results_file, f"{output_dir}/exp02_jca_summary.csv")


@timer
def create_errors():
    print("[+] Creating ERROR spreadsheets ...")
    sheet_errors(exp01_generic_results_dir, f"{output_dir}/exp01_generic_errors.csv", True)
    sheet_errors(exp01_jca_results_dir, f"{output_dir}/exp01_jca_errors.csv", True)
    sheet_errors(exp02_generic_results_dir, f"{output_dir}/exp02_generic_errors.csv")
    sheet_errors(exp02_jca_results_dir, f"{output_dir}/exp02_jca_errors.csv")


@timer
def create_coverage():
    print("[+] Creating COVERAGE spreadsheets ...")
    # sheet_coverage(exp01_generic_results_dir, f"{output_dir}/exp01_generic_coverage.csv", True)
    sheet_coverage(exp01_jca_results_dir, f"{output_dir}/exp01_jca_coverage.csv", True)
    # sheet_coverage(exp02_generic_results_dir, f"{output_dir}/exp02_generic_coverage.csv")
    # sheet_coverage(exp02_jca_results_dir, f"{output_dir}/exp02_jca_coverage.csv")


def read_execution_files(results_dir: str):
    tasks = {}
    for root, dirs, files in os.walk(results_dir):
        for file in files:
            if file == EXECUTION_MEMORY_FILENAME:
                memory_file = os.path.join(root, file)
                memory = Memory.read(memory_file)
                tasks.update(memory.tasks_map)
    return tasks


def read_all_methods_file(apk):
    all_methods_file_name = apk + EXTENSION_METHODS
    all_methods_file = os.path.join(all_methods_dir, all_methods_file_name)
    if os.path.exists(all_methods_file):
        return reach.read_reachable_methods(all_methods_file)
    return {}


@timer
def create_spreadsheets():
    # create_summary()
    # create_errors()
    create_coverage()


# TODO ........................
# summary
# --- "apk", "rep", "timeout", "tool", "cov_act", "cov_method", "cov_rv_method", "errors"
# errors
# --- "apk", "rep", "timeout", "tool", "time", "error"
# coverage
# --- "apk", "rep", "timeout", "tool", "time", "signature", "cov_act", "cov_method", "cov_rv_method"
# all_methods: copiar os .methods       
# instrument_errors         
if __name__ == '__main__':
    create_spreadsheets()

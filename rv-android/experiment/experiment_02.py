import importlib
import logging as logging_api
import os.path
import shutil
import sys

# import analysis.methods_extractor as me
import analysis.reachable_methods_mop as reach
import analysis.results_analysis as res
import utils
from android import Android
from app import App
from commands.command import Command
from constants import EXTENSION_APK, EXTENSION_METHODS, EXTENSION_LOGCAT, EXTENSION_TRACE
from rvandroid import RvAndroid
from rvsec import RVSec
# from task import Task
from experiment.task import Task
from experiment.execution import ExecutionManager
from settings import *
from tools.tool_spec import AbstractTool
from constants import EXTENSION_METHODS, RVSEC_ERRORS, REPETITIONS, TIMEOUTS, TOOLS, SUMMARY, METHOD_COVERAGE, \
    METHODS_JCA_COVERAGE, ACTIVITIES_COVERAGE
from experiment import config as x

logging = logging_api.getLogger(__name__)

apks_map = {}
tools_map = {}
rerun = True

def execute():
    _execute(x.repetitions, x.timeouts, x.tools, x.memory_file, x.generate_monitors, x.instrument,
             x.skip_experiment, x.no_window, x.static_analysis)


def _execute(repetitions: int, timeouts: list[int], tools: list[AbstractTool], memory_file="", generate_monitors=True,
             instrument=True, static_analysis=True, skip_experiment=False, no_window=False):
    logging.info("Executing Experiment ...")

    # generate monitors, instrument APKs and static analysis
    pre_process_apks(generate_monitors, instrument, static_analysis, INSTRUMENTED_DIR)

    if not skip_experiment:
        run_experiment(repetitions, timeouts, tools, memory_file, no_window)

    # TODO post process

    logging.info('Finished !!!')


def run_experiment(repetitions, timeouts, tools, memory_file, no_window):
    # retrieve the instrumented apks
    apks = utils.get_apks(INSTRUMENTED_DIR)
    logging.info(f"Instrumented APKs: {len(apks)}")

    init_maps(apks, tools)

    exec_manager = ExecutionManager()
    exec_order = lambda x: (x.repetition, x.timeout, x.tool, x.apk)
    # exec_order = lambda x: (x.repetition, x.apk, x.timeout, x.tool)
    exec_manager.create_memory(repetitions, timeouts, tools, apks, memory_file, exec_order)

    # cont = 0

    logging.info(exec_manager.statistics())
    for task in exec_manager.tasks:

        # cont += 1
        # if (cont == 50):
        #     exit(1)

        if task.executed:
            logging.info(f"Skipping already executed task: {task}")
        else:
            try:
                exec_manager.start_task(task)
                run(task, exec_manager.base_results_dir, no_window)
                exec_manager.finish_task(task)
                logging.info(f"Status: {exec_manager.statistics()}")
            except Exception as ex:
                error_msg = f"Error while running task: {task}. {ex}"
                logging.error(error_msg)
    logging.debug(f"Execution memory file: {exec_manager.memory_file}")
    logging.info(f"Status: {exec_manager.statistics()}")

    #TODO
    # if rerun and exec_manager.statistics()["pct"] != 100:
    #     rerun = False
    #     run_experiment(repetitions, timeouts, tools, memory_file, no_window)

    # # for each instrumented apk ...
    # for rep in range(repetitions):
    #     repetition = rep + 1
    #     for timeout in timeouts:
    #         for apk in apks:
    #             for tool in tools:
    #                 try:
    #                     run(apk, repetition, timeout, tool, base_results_dir, no_window)
    #                 except Exception as ex:
    #                     msg = "Error while running: APK={0}, rep={1}, timeout={2}, tool={3}. {4}"
    #                     logging.error(msg.format(apk.name, repetition, timeout, tool.name, ex))
    #
    # post_process(base_results_dir)


def run(task: Task, results_dir: str, no_window: bool):
    # xxx(apks_map[task.apk], task.repetition, task.timeout, tools_map[task.tool], results_dir, no_window)
    logging.info(f"Running: {task}")

    # logcat_cmd = Command('adb', ['logcat', '-v', 'tag', '-s', 'RVSEC', 'RVSEC-COV'])
    #
    # app = apks_map[task.apk]
    # app_results_dir = os.path.join(results_dir, app.name)
    # utils.create_folder_if_not_exists(app_results_dir)
    #
    # copy_methods_file(app, app_results_dir)
    #
    # base_name = "{0}__{1}__{2}__{3}".format(app.name, task.repetition, task.timeout, task.tool)
    # logcat_file = os.path.join(app_results_dir, "{}{}".format(base_name, EXTENSION_LOGCAT))
    # log_file = os.path.join(app_results_dir, "{}{}".format(base_name, EXTENSION_TRACE))
    #
    # time.sleep(5)
    # android = Android()
    # with android.create_emulator(AVD_NAME, no_window) as emulator:
    #     android.install_with_permissions(app)
    #     # android.simulate_reboot() # TODO pq? eh usado no droidxp ...
    #     with open(logcat_file, 'wb') as log_cat:
    #         proc = logcat_cmd.invoke_as_deamon(stdout=log_cat)
    #         tool = tools_map[task.tool]
    #         tool.execute(app, task.timeout, log_file)
    #         proc.kill()


def init_maps(apks, tools):
    for apk in apks:
        apks_map[apk.name] = apk
    # for tool in available_tools: #TODO
    for tool in tools:
        tools_map[tool.name] = tool


def pre_process_apks(generate_monitors: bool, instrument: bool, static_analysis: bool, base_results_dir: str):
    if generate_monitors:
        rvsec = RVSec()
        rvsec.generate_monitors()
    if instrument:
        rvandroid = RvAndroid()
        rvandroid.instrument_apks(results_dir=base_results_dir)
        extract_all_methods()
    if static_analysis:
        pass


def post_process(base_results_dir: str):
    logging.info("Processing results")
    res.process_results(base_results_dir)


def extract_all_methods():
    logging.info("Extracting methods")
    for file in os.listdir(INSTRUMENTED_DIR):
        if file.casefold().endswith(EXTENSION_APK):
            app = App(os.path.join(APKS_DIR, file))
            methods_file_name = app.name + EXTENSION_METHODS
            methods_file = os.path.join(INSTRUMENTED_DIR, methods_file_name)
            if not os.path.exists(methods_file):
                # class,is_activity,method,reachable,use_jca
                reach.extract_reachable_methods(app.path, methods_file)






# def xxx(app: App, rep: int, timeout: int, tool: AbstractTool, results_dir: str, no_window: bool):
#     logging.info("Running: APK={0}, rep={1}, timeout={2}, tool={3}".format(app.name, rep, timeout, tool.name))
#
#     # logcat_cmd = Command('adb', ['logcat', '-v', 'tag', '-s', 'RVSEC', 'RVSEC-COV'])
#     #
#     # app_results_dir = os.path.join(results_dir, app.name)
#     # utils.create_folder_if_not_exists(app_results_dir)
#     #
#     # copy_methods_file(app, app_results_dir)
#     #
#     # base_name = "{0}__{1}__{2}__{3}".format(app.name, rep, timeout, tool.name)
#     # logcat_file = os.path.join(app_results_dir, "{}{}".format(base_name, EXTENSION_LOGCAT))
#     # log_file = os.path.join(app_results_dir, "{}{}".format(base_name, EXTENSION_TRACE))
#     #
#     # time.sleep(5)
#     # android = Android()
#     # with android.create_emulator(AVD_NAME, no_window) as emulator:
#     #     android.install_with_permissions(app)
#     #     # android.simulate_reboot() # TODO pq? eh usado no droidxp ...
#     #     with open(logcat_file, 'wb') as log_cat:
#     #         proc = logcat_cmd.invoke_as_deamon(stdout=log_cat)
#     #         tool.execute(app, timeout, log_file)
#     #         proc.kill()


def copy_methods_file(app, app_results_dir):
    methods_file_name = app.name + EXTENSION_METHODS
    methods_file = os.path.join(INSTRUMENTED_DIR, methods_file_name)
    if os.path.exists(methods_file):
        shutil.copy(methods_file, app_results_dir)
    else:
        # TODO excecao? ... nao tem como tratar a cobertura depois
        pass


# def create_results_dir():
#     results_dir = os.path.join(RESULTS_DIR, TIMESTAMP)
#     utils.create_folder_if_not_exists(results_dir)
#     return results_dir

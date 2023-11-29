import logging as logging_api
import shutil

import analysis.methods_extractor as me
import utils
from android import Android
from app import App
from commands.command import Command
from constants import EXTENSION_APK, EXTENSION_SOOT, EXTENSION_LOGCAT, EXTENSION_TRACE
from rvandroid import RvAndroid
from rvsec import RVSec
from settings import *
from tools.tool_spec import AbstractTool

logging = logging_api.getLogger(__name__)


def execute(repetitions: int, timeouts: list[int], tools: list[AbstractTool], generate_monitors=True, instrument=True,
            no_window=False, skip_experiment=False):
    logging.info("Executing Experiment ...")

    # create base results dir (timestamp)
    base_results_dir = create_results_dir()

    # generate monitors, instrument APKs and static analysis
    pre_process_apks(generate_monitors, instrument, base_results_dir)

    if not skip_experiment:
        # retrieve the instrumented apks
        apks = utils.get_apks(INSTRUMENTED_DIR)
        logging.info("Instrumented APKs: {0}".format(len(apks)))

        # for each instrumented apk
        for rep in range(repetitions):
            repetition = rep + 1
            for timeout in timeouts:
                for apk in apks:
                    for tool in tools:
                        try:
                            run(apk, repetition, timeout, tool, base_results_dir, no_window)
                        except Exception as ex:
                            msg = "Error while running: APK={0}, rep={1}, timeout={2}, tool={3}. {4}"
                            logging.error(msg.format(apk.name, repetition, timeout, tool.name, ex))

    logging.info('Finished !!!')


def pre_process_apks(generate_monitors: bool, instrument: bool, base_results_dir: str):
    if generate_monitors:
        rvsec = RVSec()
        rvsec.generate_monitors()
    if instrument:
        rvandroid = RvAndroid()
        rvandroid.instrument_apks(results_dir=base_results_dir)
        extract_all_methods()


def extract_all_methods():
    logging.info("Extracting all methods")
    for file in os.listdir(INSTRUMENTED_DIR):
        if file.casefold().endswith(EXTENSION_APK):
            app = App(os.path.join(APKS_DIR, file))
            all_methods_file_name = app.name + EXTENSION_SOOT
            all_methods_file = os.path.join(INSTRUMENTED_DIR, all_methods_file_name)
            if not os.path.exists(all_methods_file):
                me.extract_methods(app.path, app.package_name, all_methods_file)


def run(app: App, rep: int, timeout: int, tool: AbstractTool, results_dir: str, no_window: bool):
    logging.info("Running: APK={0}, rep={1}, timeout={2}, tool={3}".format(app.name, rep, timeout, tool.name))

    logcat_cmd = Command('adb', ['logcat', '-v', 'tag', '-s', 'RVSEC', 'RVSEC-COV'])

    app_results_dir = os.path.join(results_dir, app.name)
    utils.create_folder_if_not_exists(app_results_dir)

    copy_all_methods_file(app, app_results_dir)

    base_name = "{0}__{1}__{2}__{3}".format(app.name, rep, timeout, tool.name)
    logcat_file = os.path.join(app_results_dir, "{}{}".format(base_name, EXTENSION_LOGCAT))
    log_file = os.path.join(app_results_dir, "{}{}".format(base_name, EXTENSION_TRACE))

    android = Android()
    with android.create_emulator(AVD_NAME, no_window) as emulator:
        android.install_with_permissions(app)
        # android.simulate_reboot() # TODO pq? eh usado no droidxp ...
        with open(logcat_file, 'wb') as log_cat:
            proc = logcat_cmd.invoke_as_deamon(stdout=log_cat)
            tool.execute(app, timeout, log_file)
            proc.kill()


def copy_all_methods_file(app, app_results_dir):
    all_methods_file_name = app.name + EXTENSION_SOOT
    all_methods_file = os.path.join(INSTRUMENTED_DIR, all_methods_file_name)
    if os.path.exists(all_methods_file):
        shutil.copy(all_methods_file, app_results_dir)
    else:
        # TODO excecao? ... nao tem como tratar a cobertura depois
        pass


def create_results_dir():
    results_dir = os.path.join(RESULTS_DIR, TIMESTAMP)
    utils.create_folder_if_not_exists(results_dir)
    return results_dir

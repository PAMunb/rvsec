import logging as logging_api
import sys

import utils
from android import Android
from app import App
from commands.command import Command
from rvandroid import RvAndroid
from rvsec import RVSec
from settings import *
from tools.tool_spec import AbstractTool

android = Android()

logging = logging_api.getLogger(__name__)


def execute(repetitions: int, timeouts: list[int], tools: list[AbstractTool], generate_monitors=True, instrument=True,
            no_window=False):
    logging.info("Executing Experiment ...")

    # create base results dir (timestamp)
    base_results_dir = create_results_dir()

    # generate monitors and instrument APKs
    runtime_verification(generate_monitors, instrument)

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


def runtime_verification(generate_monitors: bool, instrument: bool):
    if generate_monitors:
        rvsec = RVSec()
        rvsec.generate_monitors()
    if instrument:
        rvandroid = RvAndroid()
        rvandroid.instrument_apks()


def run(apk: App, rep: int, timeout: int, tool: AbstractTool, results_dir: str, no_window: bool):
    logging.info("Running: APK={0}, rep={1}, timeout={2}, tool={3}".format(apk.name, rep, timeout, tool.name))

    logcat_cmd = Command('adb', ['logcat', '-v', 'tag', '-s', 'RVSEC', 'RVSEC-COV'])

    logcat_file = os.path.join(results_dir, "{0}__{1}__{2}__{3}.logcat".format(apk.name, rep, timeout, tool.name))
    log_file = os.path.join(results_dir, "{0}__{1}__{2}__{3}.trace".format(apk.name, rep, timeout, tool.name))

    with android.create_emulator(AVD_NAME, no_window) as emulator:
        android.install_with_permissions(apk)
        # android.simulate_reboot() # TODO pq? eh usado no droidxp ...
        with open(logcat_file, 'wb') as log_cat:
            proc = logcat_cmd.invoke_as_deamon(stdout=log_cat)
            tool.execute(apk, timeout, log_file)
            proc.kill()


def create_results_dir():
    results_dir = os.path.join(RESULTS_DIR, TIMESTAMP)
    utils.create_folder_if_not_exists(results_dir)
    return results_dir

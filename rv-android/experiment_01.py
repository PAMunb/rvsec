import logging
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
rvandroid = RvAndroid()
rvsec = RVSec()


def execute(repetitions: int, timeouts: list[int], tools: list[AbstractTool], generate_monitors=True, instrument=True,
            no_window=False):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.info("Executing Experiment ...")

    print("tools={}".format(tools))

    # create results dir
    base_results_dir = create_results_dir()

    # generate monitors
    if generate_monitors:
        rvsec.generate_monitors()

    # instrument apks
    if instrument:
        rvandroid.instrument_apks()

    # retrieve the instumented apks
    apks = utils.get_apks(INSTRUMENTED_DIR)
    logging.info("Instrumented APKs: {0}".format(len(apks)))

    # for each instrumented apk
    for rep in range(repetitions):
        repetition = rep + 1
        for timeout in timeouts:
            for apk in apks:
                for tool in tools:
                    try:
                        run(apk, repetition, timeout, tool, base_results_dir)
                    except Exception as ex:
                        # TODO melhorar mensagem
                        logging.error("Error while executing APK: {}. {}".format(apk.name, ex))

    logging.info('Finished !!!')


def run(apk: App, rep: int, timeout: int, tool: AbstractTool, results_dir: str):
    logging.info("Running: APK={0}, rep={1}, timeout={2}, tool={3}".format(apk.name, rep, timeout, tool.name))
    logcat_cmd = Command('adb', ['logcat', '-v', 'raw', '-s', 'RVSEC', 'RVSEC-COV'])

    logcat_file = os.path.join(results_dir, "{0}__{1}__{2}__{3}.logcat".format(apk.name, rep, timeout, tool.name))
    log_file = os.path.join(results_dir, "{0}__{1}__{2}__{3}.trace".format(apk.name, rep, timeout, tool.name))

    with android.create_emulator(AVD_NAME) as emulator:
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

# if __name__ == '__main__':
#     execute(generate_monitors=False, instrument=False)

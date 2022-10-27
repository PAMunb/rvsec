import os
import sys
import logging

from settings import MOP_DIR, AVD_NAME, RESULTS_DIR, TIMESTAMP, INSTRUMENTED_DIR, APKS_DIR
from commands.command import Command
from android import Android


TIMEOUTS = [60]
POLICY = ["monkey"]

android = Android()


def execute(instrument=True):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.info("Executing")

    # create results dir
    create_results_dir()

    # instrument apks
    if instrument:
        instrument_apks()

    # retrieve the instumented apks
    apks = get_apks(INSTRUMENTED_DIR)
    logging.info("Instrumented APKs: {0}".format(len(apks)))

    # for each instrumented apk
    for apk in apks:
        for timeout in TIMEOUTS:
            logging.info("TIMEOUT: "+str(timeout))
            for policy in POLICY:
                logging.info("POLICY: "+policy)
                run(apk, timeout, policy)

    logging.info('Finished !!!')


def run(apk, timeout, policy):
    logging.info("Running: APK={0}, timeout={1}, policy={2}".format(apk, timeout, policy))

    apk_path = os.path.join(INSTRUMENTED_DIR, apk)
    #logcat_cmd = Command('adb', ['logcat', '-v', 'raw', '-s', LOGCAT_TAG])
    logcat_cmd = Command('adb', ['logcat', '-v', 'raw', '-s', 'RV-MONITOR'])
    logcat_file = os.path.join(RESULTS_DIR, TIMESTAMP, "{0}_{1}_{2}.txt".format(apk, timeout, policy))    

    with android.create_emulator(AVD_NAME) as emulator:
        with open(logcat_file, 'wb') as log_cat:
            proc = logcat_cmd.invoke_as_deamon(stdout=log_cat)
            run_droidbot(apk_path, timeout, policy)
            proc.kill()


def instrument_apks():
    # TODO recriar/zerar o diretorio de saida

    apks = get_apks(APKS_DIR)
    logging.info("Instrumenting {0} apks".format(len(apks)))
    for apk in apks:
        apk_path = os.path.join(APKS_DIR, apk)
        instrument(apk_path)


def instrument(apk):
    logging.info("Instrumenting: "+apk)
    instrument_cmd = Command('sh', [
        'mop.sh',
        apk,
        MOP_DIR
    ], 1200)
    #instrument_result = instrument_cmd.invoke(stdout=sys.stdout)
    instrument_result = instrument_cmd.invoke()
    if instrument_result.code != 0:
        raise Exception("Error while instrumenting")


def run_droidbot(apk_path, timeout, policy):
    logging.info("Running droidbot: "+apk_path)
    droidbot_cmd = Command('droidbot', [
        '-d',
        'emulator-5554',
        '-a',
        apk_path,
        '-policy',
        policy,
        '-is_emulator'
    ], timeout)
    droidbot_cmd.invoke(stdout=sys.stdout)


def get_apks(dir):
    apks = []
    for file in os.listdir(dir):
        if file.casefold().endswith(".apk"):
            apks.append(file)
    return apks


def create_results_dir():
    results_dir = os.path.join(RESULTS_DIR, TIMESTAMP)
    create_folder(RESULTS_DIR)
    create_folder(results_dir)


def create_folder(folder_name):
    if not os.path.exists(folder_name):
        try:
            logging.debug("Creating folder: "+folder_name)
            os.mkdir(folder_name)
        except OSError:
            error_msg = 'Error while creating folder {0}'.format(folder_name)
            logging.error(error_msg)
            raise Exception(error_msg)


if __name__ == '__main__':
    execute()

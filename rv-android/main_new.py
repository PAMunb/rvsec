import os
import sys
import logging
import importlib
import fnmatch, shutil

from settings import MOP_DIR, MOP_OUT_DIR, AVD_NAME, RESULTS_DIR, TIMESTAMP, INSTRUMENTED_DIR, APKS_DIR, JAVAMOP_BIN, RV_MONITOR_BIN
from commands.command import Command
from android import Android
from app import App
from rvandroid import RvAndroid
import utils

REPETITION = 1
TIMEOUTS = [180]
#POLICY = ["monkey","dfs_naive","dfs_greedy","bfs_naive","bfs_greedy"]
#POLICY = ["dfs_greedy"]

android = Android()
rvandroid = RvAndroid()

tools = {}




def execute(instrument=True):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.info("Executing")

    load_tools()

    # create results dir
    results_dir = create_results_dir()

    # instrument apks
    if instrument:
        rvandroid.instrument_apks()
        # runtime_verification()
        # instrument_apks()

    # retrieve the instumented apks
    # apks = utils.get_apks(INSTRUMENTED_DIR)
    # logging.info("Instrumented APKs: {0}".format(len(apks)))
    #
    # # for each instrumented apk
    # for rep in range(REPETITION):
    #     logging.info("REPETITION: " + str(rep))
    #     for timeout in TIMEOUTS:
    #         logging.info("TIMEOUT: "+str(timeout))
    #         for apk in apks:
    #             logging.info("APK: " + apk.name)
    #             for tool in tools:
    #                 logging.info("TOOL: " + tool)
    #                 #run(apk, rep, timeout, policy, results_dir)

    logging.info('Finished !!!')


def run(apk, rep, timeout, tool, results_dir):
    logging.info("Running: APK={0}, rep={1}, timeout={2}, tool={3}".format(apk, rep, timeout, tool))

    apk_path = os.path.join(INSTRUMENTED_DIR, apk)
    logcat_cmd = Command('adb', ['logcat', '-v', 'raw', '-s', 'RVSEC', 'RVSEC-COV'])
    logcat_file = os.path.join(results_dir, "{0}__{1}__{2}__{3}.txt".format(apk, rep, timeout, tool))

    with android.create_emulator(AVD_NAME) as emulator:
        with open(logcat_file, 'wb') as log_cat:
            proc = logcat_cmd.invoke_as_deamon(stdout=log_cat)
            run_droidbot(apk_path, timeout, tool)
            proc.kill()

def run_old(apk, rep, timeout, policy, results_dir):
    logging.info("Running: APK={0}, rep={1}, timeout={2}, policy={3}".format(apk, rep, timeout, policy))

    apk_path = os.path.join(INSTRUMENTED_DIR, apk)
    logcat_cmd = Command('adb', ['logcat', '-v', 'raw', '-s', 'RVSEC', 'RVSEC-COV'])
    logcat_file = os.path.join(results_dir, "{0}_{1}_{2}_{3}.txt".format(apk, rep, timeout, policy))

    with android.create_emulator(AVD_NAME) as emulator:
        with open(logcat_file, 'wb') as log_cat:
            proc = logcat_cmd.invoke_as_deamon(stdout=log_cat)
            run_droidbot(apk_path, timeout, policy)
            proc.kill()


def runtime_verification():
    create_folder(MOP_OUT_DIR)
    java_mop()
    rv_monitor()


def java_mop():
    logging.info("Executing JavaMOP ")
    mop_files = os.path.join(MOP_DIR, "*.mop")
    javamop_cmd = Command(JAVAMOP_BIN, [   
        '-d',
        MOP_OUT_DIR,     
        '-merge',        
        mop_files,
    ])
    javamop_result = javamop_cmd.invoke(stdout=sys.stdout)
    if javamop_result.code != 0:
        raise Exception("Error while executing JavaMOP: {0}. {1}".format(javamop_result.code, javamop_result.stderr)) 


def rv_monitor():   
    logging.info("Executing RV-Monitor ")
    rvm_files = os.path.join(MOP_DIR, "*.rvm")
    rvmonitor_cmd = Command(RV_MONITOR_BIN, [
        '-merge',
        '-d',
        MOP_OUT_DIR,        
        rvm_files,
    ])
    rvmonitor_result = rvmonitor_cmd.invoke(stdout=sys.stdout)
    if rvmonitor_result.code != 0:
        raise Exception("Error while executing rvmonitor: {0}. {1}".format(rvmonitor_result.code, rvmonitor_result.stderr))


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
        'instrument.sh',
        apk,
        MOP_OUT_DIR
    ], 1200)
    #instrument_result = instrument_cmd.invoke(stdout=sys.stdout)
    instrument_result = instrument_cmd.invoke()
    if instrument_result.code != 0:
        raise Exception("Error while instrumenting: {0}. {1}".format(
            instrument_result.code, instrument_result.stderr))


def run_droidbot(apk_path, timeout, policy):
    logging.info("Running droidbot: "+apk_path)
    droidbot_cmd = Command('droidbot', [
        '-d',
        'emulator-5554',
        '-a',
        apk_path,
        '-policy',
        policy,
        '-is_emulator',
        '-count',
        '10000000',
        '-grant_perm',
        '-ignore_ad'
    ], timeout)
    droidbot_cmd.invoke(stdout=sys.stdout)



def qualified_name(p):
    return p.replace(".py", "").replace("./", "").replace("/", ".")


def load_tools():
    '''Load all available tools.

     A tool must be defined in a subdirectory within
     the tools folder, in a python module named tool.py.
     This module must also declare a class named ToolSpec,
     which shoud inherit from AbstractToo.
    '''
    for subdir, dirs, files in os.walk('.' + os.sep + 'tools'):
        for filename in files:
            if filename == 'tool.py':
                tool_module = importlib.import_module(qualified_name(subdir + os.sep + filename))
                tool_class = getattr(tool_module, 'ToolSpec')
                tool_instance = tool_class()
                tools[tool_instance.name] = tool_instance

def create_results_dir():
    results_dir = os.path.join(RESULTS_DIR, TIMESTAMP)
    create_folder(RESULTS_DIR)
    create_folder(results_dir)
    return results_dir


def create_folder(folder_name):
    if not os.path.exists(folder_name):
        try:
            logging.debug("Creating folder: "+folder_name)
            os.mkdir(folder_name)
        except OSError:
            error_msg = 'Error while creating folder {0}'.format(folder_name)
            logging.error(error_msg)
            raise Exception(error_msg)


def copy_files(srcdir, dstdir, filepattern):
    def failed(exc):
        raise exc

    for dirpath, dirs, files in os.walk(srcdir, topdown=True, onerror=failed):
        for file in fnmatch.filter(files, filepattern):
            shutil.copy2(os.path.join(dirpath, file), dstdir)
        break # no recursion


if __name__ == '__main__':
    execute()

import os
import sys
import logging
import importlib
import fnmatch, shutil
import utils

from settings import *
from commands.command import Command
from android import Android
from app import App
from rvandroid import RvAndroid


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
    utils.create_folder_if_not_exists(RESULTS_DIR)
    utils.create_folder_if_not_exists(results_dir)
    return results_dir
        
if __name__ == '__main__':
    execute()

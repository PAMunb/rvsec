import logging as logging_api
import os.path
import sys

# import analysis.methods_extractor as me
import utils
from commands.command import Command
from constants import EXTENSION_GESDA
# from task import Task
from settings import *
from app import App

logging = logging_api.getLogger(__name__)


class StaticAnalysisException(Exception):
    pass


def run_gesda(app: App, gesda_file: str):
    if os.path.isfile(gesda_file):
        logging.info("Skipping APK already analyzed with GESDA: {}".format(app.name))
        return
    logging.info("Executing analysis on apk {}: GESDA".format(app.name))
    print("apk={}".format(app.path))
    print("gesda_file={}".format(gesda_file))
    gesda_jar = os.path.join(LIB_DIR, 'gesda', 'rvsec-gesda.jar')
    print("gesda_jar={}".format(gesda_jar))
    gesda_cmd = Command("java", [
        '-jar',
        gesda_jar,
        '--android-dir',
        ANDROID_PLATFORMS_DIR,
        '--rt-jar',
        RT_JAR,
        '--output',
        gesda_file,
        '--apk',
        app.path
    ])
    print("gesda_cmd={}".format(gesda_cmd))
    gesda_result = gesda_cmd.invoke(stdout=sys.stdout)
    if gesda_result.code != 0:
        raise StaticAnalysisException("Error while executing GESDA: {0}. {1}".format(gesda_result.code,
                                                                                     gesda_result.stderr))


def runXXX(apks_dir: str):
    apks = utils.get_apks(apks_dir)
    for apk in apks:
        logging.info("Analysing APK: {}".format(apk.name))
        gesda_file = os.path.join(apks_dir, "{}{}".format(apk.name, EXTENSION_GESDA))
        # TODO try/catch
        run_gesda(apk, gesda_file)


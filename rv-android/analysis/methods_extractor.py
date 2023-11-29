import os
import sys
import logging as logging_api

from app import App
from commands.command import Command
from settings import LIB_DIR, ANDROID_PLATFORMS_DIR

logging = logging_api.getLogger(__name__)


def parse_soot_result(soot_result: str) -> dict[str, set[str]]:
    classes = {}
    first_line = True
    with open(soot_result) as f:
        while True:
            line = f.readline()
            if not line:
                break
            if first_line:
                first_line = False
                continue

            split = line.split(";")
            clazz = split[0]
            method = split[1].replace('\n', '')

            if clazz not in classes:
                classes[clazz] = set()
            classes[clazz].add(method)
    return classes


def extract_methods(apk_path: str, package: str, out_file: str):
    logging.info("Extracting methods from: {}".format(apk_path))
    extractor_jar = os.path.join(LIB_DIR, 'methods-extractor', 'methods-extractor.jar')
    extractor_cmd = Command("java", [
        "-jar", extractor_jar,
        "--apk", apk_path,
        "--apk-package", package,
        "--android-dir", ANDROID_PLATFORMS_DIR,
        "--output", out_file
    ])
    extractor_result = extractor_cmd.invoke(stdout=sys.stdout)
    if extractor_result.code != 0:
        raise Exception("Error while finding all methods in APK: {0}. {1}".format(apk_path,
                                                                                  extractor_result.stderr))

import os

from rvandroid.constants import *
from rvandroid.parser import gesda_parser, reach_parser, gator_parser
from rvandroid.parser.classes import *


def __read_reach_file(results_dir: str, apk: str) -> Classes:
    print("__read_reach_file")
    reach_file = os.path.join(results_dir, apk + EXTENSION_REACH)
    print(f"reach_file={reach_file}")
    if not os.path.exists(reach_file):
        return Classes()
    return reach_parser.read_reachable_methods(reach_file)


def __read_gesda_file(results_dir: str, apk: str, classes: Classes) -> dict[str, Window]:
    print("__read_gesda_file")
    gesda_file = os.path.join(results_dir, apk + EXTENSION_GESDA)
    print(f"gesda_file={gesda_file}")
    if not os.path.exists(gesda_file):
        return {}
    return gesda_parser.parse_gesda_file(gesda_file, classes)


def __read_gator_file(results_dir: str, apk: str, package: str, classes: Classes, windows: dict[str, Window]):
    print("__read_gator_file")
    gator_file = os.path.join(results_dir, apk + EXTENSION_GATOR)
    print(f"gator_file={gator_file}")
    if os.path.exists(gator_file):
        gator_parser.parse_gator_file(gator_file, classes, windows, package)


def read_static_analysis_files(results_dir: str, apk: str, package: str):
    print("__read_static_analysis_files")
    classes = __read_reach_file(results_dir, apk)
    windows = __read_gesda_file(results_dir, apk, classes)
    __read_gator_file(results_dir, apk, package, classes, windows)
    return classes, windows

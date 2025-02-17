import os

from rvandroid.constants import *
from rvandroid.parser import gesda_parser, reach_parser, gator_parser
from rvandroid.parser.classes import *


def __read_reach_file(results_dir: str, apk: str) -> Classes:
    reach_file = os.path.join(results_dir, apk + EXTENSION_REACH)
    if not os.path.exists(reach_file):
        return Classes()
    return reach_parser.read_reachable_methods(reach_file)


def __read_gesda_file(results_dir: str, apk: str, package: str, classes: Classes, windows: Windows):
    gesda_file = os.path.join(results_dir, apk + EXTENSION_GESDA)
    if os.path.exists(gesda_file):
        gesda_parser.parse_gesda_file(gesda_file, package, classes, windows)


def __read_gator_file(results_dir: str, apk: str, package: str, classes: Classes,
                      windows: Windows) -> WindowTransitionGraph:
    gator_file = os.path.join(results_dir, apk + EXTENSION_GATOR)
    if os.path.exists(gator_file):
        return gator_parser.parse_gator_file(gator_file, package, classes, windows)


def read_static_analysis_files(results_dir: str, apk: str, package: str):
    windows = Windows()
    classes = __read_reach_file(results_dir, apk)
    __read_gesda_file(results_dir, apk, package, classes, windows)
    wtg = __read_gator_file(results_dir, apk, package, classes, windows)
    return classes, windows, wtg

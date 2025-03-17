"""
Module for coordinating the parsing of various static analysis results.
This module handles the integration of multiple analysis results including
reachability analysis, GESDA analysis, and Gator analysis for Android applications.
"""

import os
from typing import Optional

from rvandroid.constants import *
from rvandroid.model.classes import Classes
from rvandroid.model.static import StaticAnalysisData
from rvandroid.model.window import Windows
from rvandroid.model.wtg import WindowTransitionGraph
from rvandroid.parser.static import gator_parser, reach_parser, gesda_parser


def parse(reach_file, gator_file, gesda_file, package):
    windows = Windows()
    classes = _parse_reach(reach_file)
    wtg = _parse_gator(gator_file, package, classes, windows)
    _parse_gesda(gesda_file, package, classes, windows)
    return StaticAnalysisData(classes, windows, wtg)


def read_static_analysis_files(
        results_dir: str,
        apk: str,
        package: str
) -> StaticAnalysisData:
    """
    Coordinate the parsing of all static analysis results for an APK.

    Args:
        results_dir (str): Directory containing analysis result files
        apk (str): Name of the APK being analyzed
        package (str): Package name of the application

    Returns:
        Tuple containing:
        - Classes: Parsed class and method information
        - Windows: Window hierarchy information
        - WindowTransitionGraph: Window transition information (None if not available)
    """
    windows = Windows()
    classes = _parse_reach_analysis(results_dir, apk)
    wtg = _parse_gator_analysis(results_dir, apk, package, classes, windows)
    _parse_gesda_analysis(results_dir, apk, package, classes, windows)
    data = StaticAnalysisData(classes, windows, wtg)

    print("STATIC ANALYSIS DATA:")
    print("Classes: {}".format(classes))
    for clazz in classes.classes:
        print(" --- Class: {}".format(clazz))
    print("Windows: {}".format(windows))
    print("WTG: {}".format(wtg))

    return data


def _parse_reach_analysis(results_dir: str, apk: str) -> Classes:
    """
    Parse reachability analysis results if available.

    Args:
        results_dir (str): Directory containing analysis files
        apk (str): Name of the APK

    Returns:
        Classes: Parsed class information, empty if file not found
    """
    reach_file = os.path.join(results_dir, apk + EXTENSION_REACH)
    print(f"reach_file={reach_file} .... existe? {os.path.exists(reach_file)}")
    return _parse_reach(reach_file)


def _parse_reach(reach_file):
    return (reach_parser.read_reachable_methods(reach_file)
            if os.path.exists(reach_file) else Classes())


def _parse_gesda_analysis(
        results_dir: str,
        apk: str,
        package: str,
        classes: Classes,
        windows: Windows
) -> None:
    """
    Parse GESDA analysis results if available.

    Args:
        results_dir (str): Directory containing analysis files
        apk (str): Name of the APK
        package (str): Package name of the application
        classes (Classes): Existing Classes object to update
        windows (Windows): Existing Windows object to update
    """
    gesda_file = os.path.join(results_dir, apk + EXTENSION_GESDA)
    _parse_gesda(gesda_file, package, classes, windows)


def _parse_gesda(gesda_file, package: str, classes: Classes, windows: Windows):
    if os.path.exists(gesda_file):
        gesda_parser.parse_gesda_file(gesda_file, package, classes, windows)


def _parse_gator_analysis(
        results_dir: str,
        apk: str,
        package: str,
        classes: Classes,
        windows: Windows
) -> Optional[WindowTransitionGraph]:
    """
    Parse Gator analysis results if available.

    Args:
        results_dir (str): Directory containing analysis files
        apk (str): Name of the APK
        package (str): Package name of the application
        classes (Classes): Existing Classes object to use
        windows (Windows): Existing Windows object to use

    Returns:
        WindowTransitionGraph: Parsed transition graph, None if file not found
    """
    gator_file = os.path.join(results_dir, apk + EXTENSION_GATOR)
    return (gator_parser.parse_gator_file(gator_file, package, classes, windows)
            if os.path.exists(gator_file) else None)


def _parse_gator(gator_file, package, classes, windows):
    return (gator_parser.parse_gator_file(gator_file, package, classes, windows)
            if os.path.exists(gator_file) else None)

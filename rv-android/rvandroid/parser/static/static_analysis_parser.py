# static_analysis_parser.py
import os
from typing import Optional

from rvandroid.constants import *
from rvandroid.model.classes import Classes
from rvandroid.model.static import StaticAnalysisData
from rvandroid.model.window import Windows
from rvandroid.model.wtg import WindowTransitionGraph
from rvandroid.parser.static import gator_parser, reach_parser, gesda_parser
from rvandroid.util.logging_manager import LoggingManager


def parse(reach_file, gator_file, gesda_file, package):
    """
    Parse all static analysis files for an application.

    Args:
        reach_file: Path to reachability analysis file
        gator_file: Path to Gator output file
        gesda_file: Path to GESDA output file
        package: Package name of the application

    Returns:
        StaticAnalysisData containing parsed information
    """
    # Configure logging
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger("parser.static.static_analysis_parser.parse")

    logger.info("Parsing static analysis files")
    windows = Windows()
    classes = _parse_reach(reach_file)
    wtg = _parse_gator(gator_file, package, classes, windows)
    _parse_gesda(gesda_file, package, classes, windows)

    logger.debug(f"Parsed {len(classes.classes)} classes, {len(windows.windows)} windows")
    return StaticAnalysisData(classes, windows, wtg)


def read_static_analysis_files(
        results_dir: str,
        apk: str,
        package: str
) -> StaticAnalysisData:
    """
    Coordinate the parsing of all static analysis results for an APK.

    Args:
        results_dir: Directory containing analysis result files
        apk: Name of the APK being analyzed
        package: Package name of the application

    Returns:
        StaticAnalysisData with parsed information
    """
    # Configure logging
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger("parser.static.static_analysis_parser.read_static_analysis_files", {
        "apk": apk,
        "package": package
    })

    logger.info(f"Reading static analysis files for {apk}")

    windows = Windows()
    classes = _parse_reach_analysis(results_dir, apk)
    wtg = _parse_gator_analysis(results_dir, apk, package, classes, windows)
    _parse_gesda_analysis(results_dir, apk, package, classes, windows)

    data = StaticAnalysisData(classes, windows, wtg)

    # Log summary of parsed data
    logger.info(f"Parsed static analysis data: {len(classes.classes)} classes, {len(windows.windows)} windows")

    # Detailed logging for debugging
    logger.debug("Classes:")
    for clazz in classes.classes:
        logger.debug(f" - {clazz}")

    logger.debug("Windows:")
    for window in windows.windows:
        logger.debug(f" - {window.name} ({len(window.widgets)} widgets)")

    logger.debug(f"WindowTransitionGraph: {wtg is not None}")

    return data


def _parse_reach_analysis(results_dir: str, apk: str) -> Classes:
    """
    Parse reachability analysis results if available.

    Args:
        results_dir: Directory containing analysis files
        apk: Name of the APK

    Returns:
        Classes object with parsed data
    """
    # Configure logging
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger("parser.static.static_analysis_parser._parse_reach_analysis", {"apk": apk})

    reach_file = os.path.join(results_dir, apk + EXTENSION_REACH)
    logger.debug(f"Looking for reachability file: {reach_file}")

    if os.path.exists(reach_file):
        logger.info(f"Found reachability file: {reach_file}")
        return reach_parser.read_reachable_methods(reach_file)
    else:
        logger.warning(f"Reachability file not found: {reach_file}")
        return Classes()


def _parse_reach(reach_file):
    """
    Parse a reachability file if it exists.

    Args:
        reach_file: Path to reachability file

    Returns:
        Classes object with parsed data
    """
    # Configure logging
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger("parser.static.static_analysis_parser._parse_reach")

    if os.path.exists(reach_file):
        logger.info(f"Parsing reachability file: {reach_file}")
        return reach_parser.read_reachable_methods(reach_file)
    else:
        logger.warning(f"Reachability file not found: {reach_file}")
        return Classes()


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
        results_dir: Directory containing analysis files
        apk: Name of the APK
        package: Package name of the application
        classes: Existing Classes object to update
        windows: Existing Windows object to update
    """
    # Configure logging
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger("parser.static.static_analysis_parser._parse_gesda_analysis", {
        "apk": apk,
        "package": package
    })

    gesda_file = os.path.join(results_dir, apk + EXTENSION_GESDA)
    logger.debug(f"Looking for GESDA file: {gesda_file}")

    _parse_gesda(gesda_file, package, classes, windows)


def _parse_gesda(gesda_file, package: str, classes: Classes, windows: Windows):
    """
    Parse a GESDA file if it exists.

    Args:
        gesda_file: Path to GESDA file
        package: Package name
        classes: Classes object to update
        windows: Windows object to update
    """
    # Configure logging
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger("parser.static.static_analysis_parser._parse_gesda")

    if os.path.exists(gesda_file):
        logger.info(f"Parsing GESDA file: {gesda_file}")
        gesda_parser.parse_gesda_file(gesda_file, package, classes, windows)
    else:
        logger.warning(f"GESDA file not found: {gesda_file}")


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
        results_dir: Directory containing analysis files
        apk: Name of the APK
        package: Package name of the application
        classes: Existing Classes object to use
        windows: Existing Windows object to use

    Returns:
        WindowTransitionGraph if file exists, None otherwise
    """
    # Configure logging
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger("parser.static.static_analysis_parser._parse_gator_analysis", {
        "apk": apk,
        "package": package
    })

    gator_file = os.path.join(results_dir, apk + EXTENSION_GATOR)
    logger.debug(f"Looking for Gator file: {gator_file}")

    return _parse_gator(gator_file, package, classes, windows)


def _parse_gator(gator_file, package, classes, windows):
    """
    Parse a Gator file if it exists.

    Args:
        gator_file: Path to Gator file
        package: Package name
        classes: Classes object to update
        windows: Windows object to update

    Returns:
        WindowTransitionGraph if file exists, None otherwise
    """
    # Configure logging
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger("parser.static.static_analysis_parser._parse_gator")

    if os.path.exists(gator_file):
        logger.info(f"Parsing Gator file: {gator_file}")
        return gator_parser.parse_gator_file(gator_file, package, classes, windows)
    else:
        logger.warning(f"Gator file not found: {gator_file}")
        return None

# static_analysis_parser.py
import os

import rv_android_core.constants as constants
from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_android_core.util.logging.manager import LoggingManager
from rv_static_analysis.parser.static.gator_parser import GatorParser
from rv_static_analysis.parser.static.gesda_parser import GesdaParser
from rv_static_analysis.parser.static.reach_parser import ReachParser


class StaticAnalysisParser:
    """
    Coordinates parsing of all static analysis files for an Android application.
    
    This class acts as a facade for various static analysis parsers, orchestrating
    their execution and combining their results.
    """

    def __init__(self):
        """Initialize the static analysis parser."""
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger("parser.static.static_analysis_parser")

        # Create parser instances
        self.reach_parser = ReachParser()
        self.gator_parser = GatorParser()
        self.gesda_parser = GesdaParser()

    def parse(self, reach_file: str, gator_file: str, gesda_file: str, package: str) -> StaticAnalysisData:
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
        self.logger.info("Parsing static analysis files")

        # Initialize data structures
        windows = Windows()
        classes = Classes()

        # Parse each file
        try:
            classes = self.reach_parser.parse_file(reach_file, package, classes, None)
        except Exception as e:
            self.logger.error(f"Error parsing reach file: {e}")

        try:
            wtg = self.gator_parser.parse_file(gator_file, package, classes, windows)
        except Exception as e:
            self.logger.error(f"Error parsing gator file: {e}")
            wtg = WindowTransitionGraph()

        try:
            self.gesda_parser.parse_file(gesda_file, package, classes, windows)
        except Exception as e:
            self.logger.error(f"Error parsing gesda file: {e}")

        self.logger.debug(f"Parsed {len(classes.classes)} classes, {len(windows.windows)} windows")
        return StaticAnalysisData(classes, windows, wtg)

    def read_static_analysis_files(self, results_dir: str, apk: str, package: str) -> StaticAnalysisData:
        """
        Coordinate the parsing of all static analysis results for an APK.

        Args:
            results_dir: Directory containing analysis result files
            apk: Name of the APK being analyzed
            package: Package name of the application

        Returns:
            StaticAnalysisData with parsed information
        """
        logger = self.logging_manager.get_logger("parser.static.static_analysis_parser.read_static_analysis_files", {
            "apk": apk,
            "package": package
        })

        logger.info(f"Reading static analysis files for {apk}")

        # Initialize data structures
        windows = Windows()
        classes = Classes()

        # Build file paths
        reach_file = os.path.join(results_dir, apk + constants.EXTENSION_REACH)
        gator_file = os.path.join(results_dir, apk + constants.EXTENSION_GATOR)
        gesda_file = os.path.join(results_dir, apk + constants.EXTENSION_GESDA)

        # Parse each file
        logger.debug(f"Looking for reachability file: {reach_file}")
        try:
            classes = self.reach_parser.parse_file(reach_file, package, classes, None)
        except Exception as e:
            logger.error(f"Error parsing reach file: {e}")

        logger.debug(f"Looking for Gator file: {gator_file}")
        try:
            wtg = self.gator_parser.parse_file(gator_file, package, classes, windows)
        except Exception as e:
            logger.error(f"Error parsing gator file: {e}")
            wtg = WindowTransitionGraph()

        logger.debug(f"Looking for GESDA file: {gesda_file}")
        try:
            windows = self.gesda_parser.parse_file(gesda_file, package, classes, windows)
        except Exception as e:
            logger.error(f"Error parsing gesda file: {e}")

        # Create the final data object
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


# Create a global instance for convenience
_instance = StaticAnalysisParser()


# Public functions that use the singleton instance
def parse(reach_file: str, gator_file: str, gesda_file: str, package: str) -> StaticAnalysisData:
    """Wrapper for StaticAnalysisParser.parse"""
    return _instance.parse(reach_file, gator_file, gesda_file, package)


def read_static_analysis_files(results_dir: str, apk: str, package: str) -> StaticAnalysisData:
    """Wrapper for StaticAnalysisParser.read_static_analysis_files"""
    return _instance.read_static_analysis_files(results_dir, apk, package)


# deprecated
def parse_all(apk, gesda_file: str, gator_file: str, reach_file: str) -> StaticAnalysisData:
    """
    Parse all static analysis files for an application.
    
    Args:
        apk: App object or package name string
        gesda_file: Path to GESDA output file
        gator_file: Path to Gator output file
        reach_file: Path to reachability analysis file
        
    Returns:
        StaticAnalysisData containing parsed information
    """
    package = apk.package_name if hasattr(apk, 'package_name') else apk
    return _instance.parse(reach_file, gator_file, gesda_file, package)

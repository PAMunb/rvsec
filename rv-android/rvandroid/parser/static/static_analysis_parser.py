# rvandroid/parser/static/static_analysis_parser.py

"""
Static analysis parser for extracting application structure.
Creates standardized model objects from static analysis output files.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

from rvandroid.constants import EXTENSION_REACH, EXTENSION_GATOR, EXTENSION_GESDA, EXTENSION_METHODS
from rvandroid.model.classes import Classes, Clazz, Method
from rvandroid.model.static import StaticAnalysisData
from rvandroid.model.window import Windows, Window, WindowType
from rvandroid.model.wtg import WindowTransitionGraph


def read_static_analysis_files(app_dir: str, app_name: str, package_name: str) -> Optional[StaticAnalysisData]:
    """
    Read static analysis files and create a StaticAnalysisData object.
    Uses standardized models for consistent data representation.

    Args:
        app_dir: Directory containing static analysis files
        app_name: Name of the application
        package_name: Package name of the application

    Returns:
        StaticAnalysisData object or None if files not found
    """
    logger = logging.getLogger(__name__)

    try:
        # Check required files
        methods_file = os.path.join(app_dir, f"{app_name}{EXTENSION_METHODS}")
        gesture_file = os.path.join(app_dir, f"{app_name}{EXTENSION_GESDA}")
        gator_file = os.path.join(app_dir, f"{app_name}{EXTENSION_GATOR}")
        reach_file = os.path.join(app_dir, f"{app_name}{EXTENSION_REACH}")

        # Check if essential files exist
        if not (os.path.exists(methods_file) and os.path.exists(reach_file)):
            logger.warning(f"Required static analysis files not found for {app_name}")
            return None

        # Parse files into standardized models
        classes = parse_methods_file(methods_file, package_name)

        # Parse reachability data if available
        if os.path.exists(reach_file):
            parse_reach_file(reach_file, classes)

        # Parse window data if available
        windows = Windows()
        wtg = WindowTransitionGraph()

        if os.path.exists(gator_file):
            parse_gator_file(gator_file, windows)

        if os.path.exists(gesture_file):
            parse_gesture_file(gesture_file, windows, wtg)

        # Create static analysis data
        static_data = StaticAnalysisData(classes, windows, wtg)
        logger.info(f"Loaded static analysis data for {app_name}")

        return static_data

    except Exception as e:
        logger.error(f"Error parsing static analysis files for {app_name}: {e}", exc_info=True)
        return None


def parse_methods_file(methods_file: str, package_name: str) -> Classes:
    """
    Parse the methods file into Classes model.

    Args:
        methods_file: Path to methods file
        package_name: Package name for filtering

    Returns:
        Classes object populated with methods
    """
    logger = logging.getLogger(__name__)
    classes = Classes()

    try:
        with open(methods_file, 'r') as f:
            data = json.load(f)

        # Create classes and methods
        for class_data in data.get("classes", []):
            class_name = class_data.get("class", "")

            # Skip classes not in the package
            if not class_name.startswith(package_name):
                continue

            is_activity = class_data.get("is_activity", False)
            is_main_activity = class_data.get("is_main_activity", False)

            # Create class
            clazz = classes.add_clazz(class_name, is_activity, is_main_activity)

            # Add methods
            for method_data in class_data.get("methods", []):
                method_name = method_data.get("name", "")
                signature = method_data.get("signature", "")
                params = method_data.get("params", [])

                method = Method(
                    class_name=class_name,
                    name=method_name,
                    params=params,
                    signature=signature,
                    reachable=False,  # Will be updated from reach file
                    reaches_mop=False,  # Will be updated from reach file
                    directly_reaches_mop=False  # Will be updated from reach file
                )

                classes.add_method(method)

        logger.info(f"Parsed {len(classes.classes)} classes from methods file")
        return classes

    except Exception as e:
        logger.error(f"Error parsing methods file {methods_file}: {e}", exc_info=True)
        return classes


def parse_reach_file(reach_file: str, classes: Classes) -> None:
    """
    Parse reach file to update method reachability.

    Args:
        reach_file: Path to reach file
        classes: Classes object to update
    """
    logger = logging.getLogger(__name__)

    try:
        with open(reach_file, 'r') as f:
            data = json.load(f)

        # Update reachability data
        for class_name, methods_data in data.items():
            clazz = classes.get_clazz(class_name)
            if not clazz:
                continue

            for signature, reach_data in methods_data.items():
                method = next((m for m in clazz.methods if m.signature == signature), None)
                if not method:
                    continue

                # Update reachability information
                method.reachable = reach_data.get("reachable", False)
                method.reaches_mop = reach_data.get("reaches_mop", False)
                method.directly_reaches_mop = reach_data.get("directly_reaches_mop", False)

        logger.info(f"Updated reachability data from {reach_file}")

    except Exception as e:
        logger.error(f"Error parsing reach file {reach_file}: {e}", exc_info=True)


def parse_gator_file(gator_file: str, windows: Windows) -> None:
    """
    Parse Gator file to populate windows data.

    Args:
        gator_file: Path to Gator file
        windows: Windows object to update
    """
    logger = logging.getLogger(__name__)

    try:
        with open(gator_file, 'r') as f:
            data = json.load(f)

        # Process windows
        for window_data in data.get("windows", []):
            window_name = window_data.get("name", "")
            window_type_str = window_data.get("type", "ACTIVITY")

            # Create window
            window = Window(window_name)
            window.type = WindowType.from_string(window_type_str) or WindowType.ACTIVITY
            window.layout_file = window_data.get("layout_file", "")

            # Add widgets
            for widget_data in window_data.get("widgets", []):
                # Process widget (implementation omitted for brevity)
                pass

            # Add window to collection
            windows.add_window(window)

        logger.info(f"Parsed {len(windows.windows)} windows from Gator file")

    except Exception as e:
        logger.error(f"Error parsing Gator file {gator_file}: {e}", exc_info=True)


def parse_gesture_file(gesture_file: str, windows: Windows, wtg: WindowTransitionGraph) -> None:
    """
    Parse gesture file to populate transitions.

    Args:
        gesture_file: Path to gesture file
        windows: Windows object to reference
        wtg: WindowTransitionGraph to update
    """
    logger = logging.getLogger(__name__)

    try:
        with open(gesture_file, 'r') as f:
            data = json.load(f)

        # Process transitions
        for transition_data in data.get("transitions", []):
            from_window_name = transition_data.get("from", "")
            to_window_name = transition_data.get("to", "")

            from_window = next((w for w in windows.windows if w.name == from_window_name), None)
            to_window = next((w for w in windows.windows if w.name == to_window_name), None)

            if from_window and to_window:
                # Process transition events (implementation omitted for brevity)
                pass

        logger.info(f"Parsed transitions from gesture file")

    except Exception as e:
        logger.error(f"Error parsing gesture file {gesture_file}: {e}", exc_info=True)

"""
Parser module for Gator output files.
Gator is a program analysis toolkit for Android that generates window transition graphs.
This module processes the JSON output from Gator to create window transitions and widget events.
"""

import logging
import os
import re
from typing import Tuple

import rvandroid.utils as utils
from rvandroid.parser.classes import (
    Classes,
    Widget,
    WidgetEventType,
    WidgetListener,
    WidgetType,
    WindowTransition,
    WindowTransitionGraph,
    Windows,
)

logger = logging.getLogger(__name__)


def parse_gator_file(gator_file: str, package: str, classes: Classes, windows: Windows) -> WindowTransitionGraph:
    """
    Parse a Gator output file to extract window transitions and widget information.
    
    Args:
        gator_file: Path to the Gator JSON output file
        package: Android package name
        classes: Collection of application classes
        windows: Collection of application windows
        
    Returns:
        WindowTransitionGraph containing the parsed transitions
    """
    logger.debug(f"Starting parse gator file: {gator_file}")
    if not os.path.exists(gator_file):
        logger.error(f"File '{gator_file}' not found!")
        return WindowTransitionGraph()

    gator_data = utils.read_json(gator_file)
    process_windows(package, classes, windows, gator_data)
    return process_transitions(windows, gator_data)


def process_windows(package: str, classes: Classes, windows: Windows, gator_data: dict) -> None:
    """
    Process window definitions from Gator data.
    
    Args:
        package: Android package name
        classes: Collection of application classes
        windows: Collection of application windows
        gator_data: Parsed Gator JSON data
    """
    if "windows" not in gator_data:
        logger.error("No windows found in gator file!")
        return

    for window in gator_data["windows"]:
        class_name = window["name"]
        logger.debug(f"Processing window: {class_name}")

        if package in class_name and class_name not in classes.classes:
            classes.add_clazz(class_name, True, False)

        window_id = str(window["id"])
        screen = windows.get_or_create(class_name, window_id)
        screen.id = window_id


def process_transitions(windows: Windows, gator_data: dict) -> WindowTransitionGraph:
    """
    Process window transitions from Gator data.
    
    Args:
        windows: Collection of application windows
        gator_data: Parsed Gator JSON data
        
    Returns:
        WindowTransitionGraph containing the parsed transitions
    """
    wtg = WindowTransitionGraph()

    for transition in gator_data["transitions"]:
        source_id = str(transition["sourceId"])
        target_id = str(transition["targetId"])

        source = windows.get_window_by_id(source_id)
        target = windows.get_window_by_id(target_id)

        if source == target:
            continue

        events = process_transition_events(transition, windows)
        if events:
            wtg.add_transition(source, target, events)

    return wtg


def process_transition_events(transition: dict, windows: Windows) -> list[WindowTransition]:
    """
    Process events associated with a window transition.
    
    Args:
        transition: Dictionary containing transition event data
        windows: Collection of application windows
        
    Returns:
        List of WindowTransition objects
    """
    events = []

    for event_dict in transition["events"]:
        event_type = event_dict["type"]
        event = to_event(event_type)

        if event is WidgetEventType.OTHER:
            continue

        handler = event_dict["handler"]
        class_name, method_name = from_signature(handler)

        window = windows.get_or_create(class_name)
        widget_id = str(event_dict["widgetId"])

        widget = windows.get_widget(widget_id)
        if widget is None:
            logging.debug(f"Creating widget {widget_id}!")
            widget = create_widget(event_dict)
            if widget:
                window.add_widget(widget)
            else:
                continue

        widget.add_listener(WidgetListener(event, class_name, method_name, handler))
        events.append(WindowTransition(widget_id, event, handler))

    return events


def create_widget(event_dict: dict) -> Widget | None:
    """
    Create a Widget object from event dictionary data.
    
    Args:
        event_dict: Dictionary containing widget event data
        
    Returns:
        Widget object or None if widget type is OTHER
    """
    widget_type = WidgetType.from_class_name(event_dict["widgetClass"])
    if widget_type is WidgetType.OTHER:
        return None

    widget_id = str(event_dict["widgetId"])
    widget_name = event_dict.get("widgetName", "")
    return Widget(widget_id, widget_name, widget_type)


def from_signature(signature: str) -> Tuple[str, str]:
    """
    Extract class name and method name from a Soot-style method signature.
    
    Args:
        signature: Soot-style method signature string
        
    Returns:
        Tuple of (class_name, method_name)
    """
    pattern = r"<(.*): .* (.*)\(.*\)>"
    match = re.search(pattern, signature)

    if match:
        return match.group(1), match.group(2)
    return "", ""


def to_event(event_str: str) -> WidgetEventType:
    """
    Convert Gator event string to WidgetEventType.
    
    Args:
        event_str: Event type string from Gator
        
    Returns:
        Corresponding WidgetEventType enum value
    """
    click_events = {
        "click", "item_click", "dialog_negative_button",
        "dialog_neutral_button", "dialog_cancel", "dialog_dismiss",
        "dialog_positive_button"
    }

    long_click_events = {"long_click", "item_long_click"}
    selection_events = {"select", "item_selected"}

    if event_str in click_events:
        return WidgetEventType.CLICK
    elif event_str in long_click_events:
        return WidgetEventType.LONG_CLICK
    elif event_str in selection_events:
        return WidgetEventType.SELECTION

    # Map other specific events
    event_map = {
        "scroll": WidgetEventType.SCROLL,
        "swipe": WidgetEventType.GESTURE,
        "zoom_in": WidgetEventType.GESTURE,
        "zoom_out": WidgetEventType.GESTURE,
        "drag": WidgetEventType.DRAG,
        "touch": WidgetEventType.TOUCH,
        "focus_change": WidgetEventType.FOCUS,
        "press_key": WidgetEventType.KEY,
        "editor_action": WidgetEventType.KEY,
        "dialog_press_key": WidgetEventType.KEY,
        "enter_text": WidgetEventType.TEXT_CHANGE
    }

    return event_map.get(event_str, WidgetEventType.OTHER)

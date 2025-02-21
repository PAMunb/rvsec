"""
Parser module for GESDA (GUI Element Static Detection for Android) output files.
GESDA analyzes Android applications to detect GUI elements and their properties.
This module processes GESDA's JSON output to extract window and widget information.
"""

import logging
import os
from typing import List, Set

import rvandroid.utils as utils
from rvandroid.parser.classes import (
    Classes,
    Widget,
    WidgetEventType,
    Window,
    WindowType,
    WidgetType,
    WidgetEvent,
    Windows
)

logger = logging.getLogger(__name__)


def parse_gesda_file(gesda_file: str, package: str, classes: Classes, windows: Windows) -> None:
    """
    Parse a GESDA output file to extract window and widget information.
    
    Args:
        gesda_file: Path to the GESDA JSON output file
        package: Android package name to filter relevant classes
        classes: Collection of application classes
        windows: Collection of application windows
    """
    logger.debug(f"Starting parse gesda file: {gesda_file}")
    if not os.path.exists(gesda_file):
        logger.error(f"File '{gesda_file}' not found!")
        return
    gesda_data = utils.read_json(gesda_file)
    if gesda_data and "windows" in gesda_data:
        for window in gesda_data["windows"]:
            process_window(window, package, classes, windows)


def process_window(window_dict: dict, package: str, classes: Classes, windows: Windows) -> None:
    """
    Process a single window entry from GESDA data.
    
    Args:
        window: Dictionary containing window data
        package: Android package name
        classes: Collection of application classes
        windows: Collection of application windows
    """
    class_name: str = window_dict["name"]
    logger.debug(f"Processing window={class_name}")

    if package and package not in class_name:
        logger.warning(f"Class '{class_name}' not in package '{package}'")
        return

    if class_name not in classes.classes:
        classes.add_clazz(window_dict["name"], True, window_dict["isMain"])

    window = create_window(window_dict, windows)
    if "widgets" in window_dict:
        for widget in parse_widgets(window_dict["widgets"], window, windows):
            window.add_widget(widget)

    windows.add_window(window)


def create_window(window_dict: dict, windows: Windows) -> Window:
    """
    Create a Window object from GESDA window data.
    
    Args:
        window: Dictionary containing window data
        
    Returns:
        Window object with populated properties
    """
    print(f"*** window_dict={window_dict}")
    window = windows.get_window(window_dict["name"])
    if window is None:
        logger.debug(f"Creating new window: {window_dict['name']}")
        window = Window(window_dict["name"])
    
    window.type = WindowType.from_string(window_dict["type"])

    if "layoutFileName" in window_dict:
        window.layout_file = window_dict["layoutFileName"]

    return window


def parse_widgets(widgets_list: List[dict], window: Window, windows: Windows) -> List[Widget]:
    """
    Parse widget entries from GESDA data.
    
    Args:
        widgets_list: List of dictionaries containing widget data
        
    Returns:
        List of Widget objects
    """
    widgets: List[Widget] = []

    for widget_dict in widgets_list:
        widget = get_or_create_widget(widget_dict, window, windows)

        if "listeners" in widget_dict:
            events = parse_listeners(widget_dict["listeners"])
            for event in events:
                widget.add_event(event)            

        widgets.append(widget)

    return widgets


def get_or_create_widget(widget_dict: dict, window: Window, windows: Windows) -> Widget:
    """
    Create a Widget object from GESDA widget data.
    
    Args:
        widget_dict: Dictionary containing widget data
        
    Returns:
        Widget object with populated properties
    """
    widget = windows.get_widget(widget_dict["widgetId"])
    if widget is None:
        widget_type = WidgetType.from_string(widget_dict["type"])
        print(f"create_widget::type={type}")
        logger.debug(f"Creating new widget: {widget_dict['widgetId']}")
        widget = Widget(
            str(widget_dict["widgetId"]),
            widget_dict["name"] if "name" in widget_dict else "",
            widget_type # TODO rever tipo ...........................
        )
        print(f"window ({type(window)})={window}")        
        windows.add_widget(window, widget)

    # Set optional properties
    widget.field = widget_dict.get("field")
    widget.text = widget_dict.get("text")
    widget.hint = widget_dict.get("hint")
    widget.entries = widget_dict.get("entries")
    widget.input_type = widget_dict.get("inputType")

    return widget


def parse_listeners(events_list: List[dict]) -> Set[WidgetEvent]:
    """
    Parse event entries from GESDA widget data.
    
    Args:
        events_list: List of dictionaries containing listener data
        
    Returns:
        Set of WidgetEvent objects
    """
    events = set()

    for listener_dict in events_list:
        event_type = to_event(listener_dict["type"])
        if event_type is WidgetEventType.OTHER:
            continue

        callback = listener_dict["callbackMethod"]
        event = WidgetEvent(
            event_type,
            callback["className"],
            callback["name"],
            callback["signature"]
        )
        events.add(event)

    return events


def to_event(event_str: str) -> WidgetEventType:
    """
    Convert GESDA listener type string to WidgetEventType.
    
    Args:
        event_str: Listener type string from GESDA
        
    Returns:
        Corresponding WidgetEventType enum value
    """
    event_map = {
        "OnClickListener": WidgetEventType.CLICK,
        "OnItemClickListener": WidgetEventType.CLICK,
        "OnMenuItemClickListener": WidgetEventType.CLICK,
        "OnCheckedChangeListener": WidgetEventType.CLICK,
        "OnLongClickListener": WidgetEventType.LONG_CLICK,
        "OnItemLongClickListener": WidgetEventType.LONG_CLICK,
        "OnItemSelectedListener": WidgetEventType.SELECTION,
        "OnScrollListener": WidgetEventType.SCROLL,
        "OnGestureListener": WidgetEventType.GESTURE,
        "OnDragListener": WidgetEventType.DRAG,
        "OnHoverListener": WidgetEventType.HOVER,
        "OnTouchListener": WidgetEventType.TOUCH,
        "OnFocusChangeListener": WidgetEventType.FOCUS,
        "OnKeyListener": WidgetEventType.KEY
    }

    return event_map.get(event_str, WidgetEventType.OTHER)

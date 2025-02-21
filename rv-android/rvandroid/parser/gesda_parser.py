"""
Parser module for GESDA (GUI Element Static Detection for Android) output files.
GESDA analyzes Android applications to detect GUI elements and their properties.
This module processes GESDA's JSON output to extract window and widget information.
"""

import logging
from typing import List, Set

import rvandroid.utils as utils
from rvandroid.parser.classes import (
    Classes,
    Widget,
    WidgetEventType,
    Window,
    WindowType,
    WidgetType,
    WidgetListener,
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
    gesda_data = utils.read_json(gesda_file)

    for window in gesda_data["windows"]:
        process_window(window, package, classes, windows)


def process_window(window: dict, package: str, classes: Classes, windows: Windows) -> None:
    """
    Process a single window entry from GESDA data.
    
    Args:
        window: Dictionary containing window data
        package: Android package name
        classes: Collection of application classes
        windows: Collection of application windows
    """
    class_name: str = window["name"]
    logger.debug(f"Processing window={class_name}")

    if package and package not in class_name:
        logger.warning(f"Class '{class_name}' not in package '{package}'")
        return

    if class_name not in classes.classes:
        classes.add_clazz(window["name"], True, window["isMain"])

    screen = create_window(window)
    if "widgets" in window:
        for widget in parse_widgets(window["widgets"]):
            screen.add_widget(widget)

    windows.add_window(screen)


def create_window(window: dict) -> Window:
    """
    Create a Window object from GESDA window data.
    
    Args:
        window: Dictionary containing window data
        
    Returns:
        Window object with populated properties
    """
    screen = Window(window["name"])
    screen.type = WindowType.from_string(window["type"])

    if "layoutFileName" in window:
        screen.layout_file = window["layoutFileName"]

    return screen


def parse_widgets(widgets_list: List[dict]) -> List[Widget]:
    """
    Parse widget entries from GESDA data.
    
    Args:
        widgets_list: List of dictionaries containing widget data
        
    Returns:
        List of Widget objects
    """
    widgets: List[Widget] = []

    for widget_dict in widgets_list:
        widget = create_widget(widget_dict)

        if "listeners" in widget_dict:
            widget.listeners = parse_listeners(widget_dict["listeners"])

        widgets.append(widget)

    return widgets


def create_widget(widget_dict: dict) -> Widget:
    """
    Create a Widget object from GESDA widget data.
    
    Args:
        widget_dict: Dictionary containing widget data
        
    Returns:
        Widget object with populated properties
    """
    widget = Widget(
        str(widget_dict["widgetId"]),
        widget_dict["name"] if "name" in widget_dict else "",
        WidgetType.from_string(widget_dict["type"]) # TODO rever tipo ...........................
    )

    # Set optional properties
    widget.field = widget_dict.get("field")
    widget.text = widget_dict.get("text")
    widget.hint = widget_dict.get("hint")
    widget.entries = widget_dict.get("entries")
    widget.input_type = widget_dict.get("inputType")

    return widget


def parse_listeners(listeners_list: List[dict]) -> Set[WidgetListener]:
    """
    Parse listener entries from GESDA widget data.
    
    Args:
        listeners_list: List of dictionaries containing listener data
        
    Returns:
        Set of WidgetListener objects
    """
    listeners = set()

    for listener_dict in listeners_list:
        event_type = to_event(listener_dict["type"])
        if event_type is WidgetEventType.OTHER:
            continue

        callback = listener_dict["callbackMethod"]
        listener = WidgetListener(
            event_type,
            callback["className"],
            callback["name"],
            callback["signature"]
        )
        listeners.add(listener)

    return listeners


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

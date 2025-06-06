"""
Parser module for GESDA (GUI Element Static Detection for Android) output files.
GESDA analyzes Android applications to detect GUI elements and their properties.
This module processes GESDA's JSON output to extract window and widget information.
"""

import os
from typing import List, Optional
from typing import Set

import rv_android_core.util.utils as utils
from rv_android_core.domain.classes import Classes
from rv_android_core.domain.widget import WidgetEventType, WidgetEvent, WidgetType, Widget
from rv_android_core.domain.window import WindowType, Window
from rv_android_core.domain.window import Windows
from rv_android_core.parser.static.base_parser import BaseStaticAnalysisParser


class GesdaParser(BaseStaticAnalysisParser):

    def __init__(self):
        """Initialize the Gesda parser."""
        super().__init__("gesda")

    def parse_file(self, file_path: str, package: Optional[str], classes: Optional[Classes],
                   windows: Optional[Windows]) -> Windows:
        self.log_parse_start(file_path)

        if not os.path.exists(file_path):
            self.logger.warning(f"File {file_path} does not exist, returning empty windows")
            return windows if windows is not None else Windows()

        try:
            if windows is None:
                windows = Windows()

            gesda_data = utils.read_json(file_path)
            if gesda_data and "windows" in gesda_data:
                for window in gesda_data["windows"]:
                    self.process_window(window, package, classes, windows)

            # Log successful parsing
            stats = {
                "windows": len(windows.windows),
                "widgets": len(windows.widgets)
            }
            self.log_parse_complete(file_path, stats)

            return windows
        except Exception as e:
            self.log_parse_error(file_path, e)
            return Windows()

    def process_window(self, window_dict: dict, package: str, classes: Classes, windows: Windows) -> None:
        """
        Process a single window entry from GESDA data.

        Args:
            window: Dictionary containing window data
            package: Android package name
            classes: Collection of application classes
            windows: Collection of application windows
        """
        class_name: str = window_dict["name"]
        self.logger.debug(f"Processing window={class_name}")

        if package and package not in class_name:
            self.logger.warning(f"Class '{class_name}' not in package '{package}'")
            return

        if class_name not in classes.classes:
            classes.add_clazz(window_dict["name"], True, window_dict["isMain"])

        window = self.create_window(window_dict, windows)
        if "widgets" in window_dict:
            for widget in self.parse_widgets(window_dict["widgets"], window, windows):
                window.add_widget(widget)

        windows.add_window(window)

    def create_window(self, window_dict: dict, windows: Windows) -> Window:
        """
        Create a Window object from GESDA window data.

        Args:
            window: Dictionary containing window data

        Returns:
            Window object with populated properties
        """
        # print(f"*** window_dict={window_dict}")
        window_name = window_dict["name"]
        window = windows.get_window(window_name)

        if window is None:
            self.logger.debug(f"Creating new window: {window_name}")
            window = Window(window_name)

        window.type = WindowType.from_string(window_dict["type"])

        if "layoutFileName" in window_dict:
            window.layout_file = window_dict["layoutFileName"]

        # Set activity name if this appears to be an Activity
        is_main = window_dict.get("isMain", False)
        if window.type == WindowType.ACTIVITY or "Activity" in window_name or is_main:
            window.activity = window_name
            window.class_name = window_name
            self.logger.debug(f"Setting activity name for window {window_name}")

        # Update class_name from name
        if not window.class_name and window_name:
            window.class_name = window_name

        return window

    def parse_widgets(self, widgets_list: List[dict], window: Window, windows: Windows) -> List[Widget]:
        """
        Parse widget entries from GESDA data.

        Args:
            widgets_list: List of dictionaries containing widget data

        Returns:
            List of Widget objects
        """
        widgets: List[Widget] = []

        for widget_dict in widgets_list:
            widget = self.get_or_create_widget(widget_dict, window, windows)

            if "listeners" in widget_dict:
                events = self.parse_listeners(widget_dict["listeners"])
                for event in events:
                    widget.add_event(event)

            widgets.append(widget)

        return widgets

    def get_or_create_widget(self, widget_dict: dict, window: Window, windows: Windows) -> Widget:
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
            # print(f"create_widget::type={type}")
            self.logger.debug(f"Creating new widget: {widget_dict['widgetId']}")
            widget = Widget(
                str(widget_dict["widgetId"]),
                widget_dict["name"] if "name" in widget_dict else "",
                widget_type  # TODO rever tipo ...........................
            )
            # print(f"window ({type(window)})={window}")
            windows.add_widget(window, widget)

        # Set optional properties
        widget.field = widget_dict.get("field")
        widget.text = widget_dict.get("text")
        widget.hint = widget_dict.get("hint")
        widget.entries = widget_dict.get("entries")
        widget.input_type = widget_dict.get("inputType")

        return widget

    def parse_listeners(self, events_list: List[dict]) -> Set[WidgetEvent]:
        """
        Parse event entries from GESDA widget data.

        Args:
            events_list: List of dictionaries containing listener data

        Returns:
            Set of WidgetEvent objects
        """
        events = set()

        for listener_dict in events_list:
            event_type = self.to_event(listener_dict["type"])
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

    def to_event(self, event_str: str) -> WidgetEventType:
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


def parse_gesda_file(gesda_file: str, package: str, classes: Classes, windows: Windows):
    parser = GesdaParser()
    parser.parse_file(gesda_file, package, classes, windows)

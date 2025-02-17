import logging as logging_api

import rvandroid.utils as utils
from rvandroid.parser.classes import Classes, Widget, WidgetEventType, Window, WindowType, WidgetType, WidgetListener, \
    Windows

logging = logging_api.getLogger(__name__)


def parse_gesda_file(gesda_file: str, package: str, classes: Classes, windows: Windows):
    logging.debug(f"Starting parse gesda file: {gesda_file}")
    gesda = utils.read_json(gesda_file)
    for window in gesda["windows"]:
        clazz_name: str = window["name"]
        logging.debug(f"Processing window={clazz_name}")
        if package is not None and package not in clazz_name:
            logging.warning(f"Class '{clazz_name}' not in package '{package}'")
            continue

        if clazz_name not in classes.classes:
            classes.add_clazz(window["name"], True, window["isMain"])

        screen = Window(clazz_name)
        screen.type = WindowType.from_string(window["type"])
        screen.layout_file = window["layoutFileName"]
        for widget in get_widgets(window["widgets"]):
            screen.add_widget(widget)
        windows.add_window(screen)


def to_event(event_str: str):
    match event_str:
        case "OnClickListener" | "OnItemClickListener" | "OnMenuItemClickListener" | "OnCheckedChangeListener":
            return WidgetEventType.CLICK
        case "OnLongClickListener" | "OnItemLongClickListener":
            return WidgetEventType.LONG_CLICK
        case "OnItemSelectedListener":
            return WidgetEventType.SELECTION
        case "OnScrollListener":
            return WidgetEventType.SCROLL
        case "OnGestureListener":
            return WidgetEventType.GESTURE
        case "OnDragListener":
            return WidgetEventType.DRAG
        case "OnHoverListener":
            return WidgetEventType.HOVER
        case "OnTouchListener":
            return WidgetEventType.TOUCH
        case "OnFocusChangeListener":
            return WidgetEventType.FOCUS
        case "OnKeyListener":
            return WidgetEventType.KEY
        case _:
            return WidgetEventType.OTHER


def get_listeners(param: list[dict]):
    listeners = set()
    for listener_dict in param:
        print(f"listener_dict: {listener_dict}")

        event_type = to_event(listener_dict["type"])
        print(f"event_type={event_type}")
        if event_type is WidgetEventType.OTHER:
            continue

        listener_class = listener_dict["callbackMethod"]["className"]
        listener_method = listener_dict["callbackMethod"]["name"]
        listener_signature = listener_dict["callbackMethod"]["signature"]

        listener = WidgetListener(event_type, listener_class, listener_method, listener_signature)
        print(f"listener={listener}")
        listeners.add(listener)
    return listeners


def get_widgets(widgets_list: list[dict]) -> list[Widget]:
    widgets: list[Widget] = []

    for widget_dict in widgets_list:
        print(f"\n\nwidget_dict={widget_dict}")

        widget_id = str(widget_dict["widgetId"])
        widget_type = WidgetType.from_string(widget_dict["type"])
        widget_name = widget_dict["name"]

        widget = Widget(widget_id, widget_type, widget_name)

        # Using the dict.get() method with default values (None)       
        widget.field = widget_dict.get("field")
        widget.text = widget_dict.get("text")
        widget.hint = widget_dict.get("hint")
        widget.entries = widget_dict.get("entries")
        widget.input_type = widget_dict.get("inputType")

        if "listeners" in widget_dict:
            print("**********************************************")
            widget.listeners = get_listeners(widget_dict["listeners"])

        widgets.append(widget)

    return widgets

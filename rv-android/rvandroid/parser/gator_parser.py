import logging as logging_api
import os
import re

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

logging = logging_api.getLogger(__name__)


def parse_gator_file(gator_file: str, package: str, classes: Classes, windows: Windows):
    logging.debug(f"Starting parse gator file: {gator_file}")
    if not os.path.exists(gator_file):
        logging.error(f"File '{gator_file}' not found!")
        return WindowTransitionGraph()

    gator = utils.read_json(gator_file)

    process_windows(package, classes, windows, gator)

    return process_transitions(windows, gator)


def process_transitions(windows, gator):
    wtg = WindowTransitionGraph()
    for transition in gator["transitions"]:
        print(f"**************** transition_dict={transition}")

        source_id = str(transition["sourceId"])
        target_id = str(transition["targetId"])
        print(f"\ttransition_id: {source_id} --> {target_id}")
        source = windows.get_window_by_id(source_id)
        target = windows.get_window_by_id(target_id)
        print(f"\ttransition: {source.name} --> {target.name}")
        if source == target:
            continue

        events = []

        for event_dict in transition["events"]:
            print(f"\t-event_dict={event_dict}")

            event_type = event_dict["type"]
            event = to_event(event_type)
            print(f"\t-event={event}")
            if event is WidgetEventType.OTHER:
                continue

            handler = event_dict["handler"]
            class_name, method_name = from_signature(handler)
            # class_name = class_name.split("$")[0]  # TODO dealing with inner classes
            print(f"\t-handler={handler}")
            print(f"\t-class_name={class_name}")
            print(f"\t-method_name={method_name}")

            window = windows.get_or_create(class_name)
            # window = windows.get_window(class_name)
            print(f"\t-window={window}")
            widget_id = str(event_dict["widgetId"])
            print(f"\t-widget_id={widget_id}")

            widget = windows.get_widget(widget_id)
            print(f"\t-widget={widget}")
            if widget is None:
                widget_type = WidgetType.from_class_name(event_dict["widgetClass"])
                print(f"\t-widget_type={widget_type}")
                if widget_type is WidgetType.OTHER:
                    continue
                widget_name = ""
                if "widgetName" in event_dict:
                    widget_name = event_dict["widgetName"]
                widget = Widget(widget_id, widget_name, widget_type)
                window.add_widget(widget)

            widget.add_listener(WidgetListener(event, class_name, method_name, handler))
            events.append(WindowTransition(widget_id, event, handler))
        if len(events) > 0:
            wtg.add_transition(source, target, events)
    # wtg.graph.remove_node("presto.android.gui.stubs.PrestoFakeLauncherNodeClass")
    return wtg


def process_windows(package, classes, windows, gator):
    for window in gator["windows"]:
        print(f"window_dict={window}")
        clazz_name = window["name"]
        # clazz_name = clazz_name.split("$")[0]  # TODO dealing with inner classes
        logging.debug(f"************************** Processing window={clazz_name}")

        # if package is not None and package not in clazz_name:
        #     logging.warning(f"Class '{clazz_name}' not in package '{package}'")
        #     continue

        if clazz_name not in classes.classes and package in clazz_name:
            classes.add_clazz(clazz_name, True, False)

        screen = windows.get_or_create(clazz_name)
        screen.id = str(window["id"])
        # if "android.view.Menu" in clazz_name:
        #     screen.type = WindowType.OPTIONSMENU
        # windows.add_window(screen)

        print(f"screen={screen}")


def from_signature(signature: str) -> tuple[str, str]:
    """
    Extracts the class name and method name from a Soot-style method signature.

    Args:
        signature: The Soot-style method signature string.

    Returns:
        A tuple containing the class name and method name, or empty strings if
        the signature is invalid.
    """
    pattern = r"<(.*): .* (.*)\(.*\)>"
    match = re.search(pattern, signature)

    if match:
        class_name = match.group(1)
        method_name = match.group(2)
        return class_name, method_name
    return "", ""


def to_event(event_str: str) -> WidgetEventType:
    match event_str:
        case (
        "click"
        | "item_click"
        | "dialog_negative_button"
        | "dialog_neutral_button"
        | "dialog_cancel"
        | "dialog_dismiss"
        | "dialog_positive_button"
        ):
            return WidgetEventType.CLICK
        case "long_click" | "item_long_click":
            return WidgetEventType.LONG_CLICK
        case "select" | "item_selected":
            return WidgetEventType.SELECTION
        case "scroll":
            return WidgetEventType.SCROLL
        case "swipe" | "zoom_in" | "zoom_out":
            return WidgetEventType.GESTURE
        case "drag":
            return WidgetEventType.DRAG
        case "touch":
            return WidgetEventType.TOUCH
        case "focus_change":
            return WidgetEventType.FOCUS
        case "press_key" | "editor_action" | "dialog_press_key":
            return WidgetEventType.KEY
        case "enter_text":
            return WidgetEventType.TEXT_CHANGE
        case _:
            return WidgetEventType.OTHER

# Eventos do gator
# // "usual" ones
#   click,
#   long_click,
#   // This is for selectable objects - radio button, check box, etc.
#   select,
#   scroll,

#   // Quickly slide through the screen without long impact
#   swipe,
#   // Swipe through the screen but hold for long enough
#   drag,
#   // The general multi-touch event
#   touch,

#   // Not sure if this should be a user event
#   focus_change,

#   // This does not need to happen for a text box (but it can)
#   press_key,
#   // This is for text boxes
#   enter_text,
#   // Special editor action performed on a text view - when the enter key is
#   // pressed, or when an action supplied to the IME is selected by the user.
#   editor_action,

#   // For any composite views (ListView, Menu, etc) - the user sees a list, and
#   // intends to interact with one of its items. Additional events may be
#   // triggered simultaneously on the specific item object.
#   item_click,
#   item_long_click,
#   item_selected,

#   zoom_in,
#   zoom_out,

#   // Dialog events
#   dialog_negative_button, // TODO(tony): remove soon
#   dialog_neutral_button, // TODO(tony): remove soon
#   dialog_cancel,
#   dialog_dismiss,
#   dialog_press_key,
#   dialog_positive_button, // TODO(tony): remove soon

#   EXPLICIT_IMPLICIT_SEPARATOR,

#   // View
#   implicit_create_context_menu,
#   implicit_hierarchy_change,
#   implicit_time_tick,
#   implicit_system_ui_change,

#   // Temporarily added for model construction
#   // event related with activity create, resume, stop, pause
#   implicit_lifecycle_event,
#   // event related with onActivityResult
#   implicit_on_activity_result,
#   // event related with onNewIntent
#   implicit_on_activity_newIntent,
#   // back event
#   implicit_back_event,
#   // rotate
#   implicit_rotate_event,
#   // home
#   implicit_home_event,
#   // power
#   implicit_power_event,
#   // launcher
#   implicit_launch_event,
#   // asynchronous operations: Activity.runOnUiThread, View.post, View.postDelayed
#   implicit_async_event,

#   END_MARKER_NEVER_USE;

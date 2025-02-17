import logging as logging_api
from enum import Enum

import networkx as nx


class Method:
    # signature_template = "{}.{}({})" # CLASS_NAME.METHOD_NAME(PARAMS) : br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil.hash(byte[],java.lang.String)

    def __init__(self, class_name: str, name: str, params: list[str], signature: str, reachable: bool,
                 reaches_mop: bool, directly_reaches_mop: bool, directly_reachable_mop: list[str]):
        self.class_name = class_name  # class full name
        self.name = name  # method name
        self.params = params  # method parameters
        self.signature = signature  # soot signature
        self.reachable = reachable  # is reachable from any entrypoint?
        self.reaches_mop = reaches_mop  # reaches any MOP method?
        self.directly_reaches_mop = directly_reaches_mop  # reaches any MOP method directly?
        self.directly_reachable_mop = directly_reachable_mop  # list of methods that are directly reachable from this method
        self.reached = False  # has been reached during exxecution?

    # @property
    # def signature(self):
    #     return Method.signature_template.format(self.class_name, self.name, self.params)

    def __eq__(self, other):
        if isinstance(other, Method):
            return self.signature == other.signature
        return False

    def __hash__(self):
        return hash(self.signature)

    def __str__(self):
        return f"Method=[name={self.name},signature={self.signature},reachable={self.reachable},reaches_mop={self.reaches_mop}, directly_reaches_mop={self.directly_reaches_mop}"

    def __repr__(self):
        return f"{self.signature}"


class Clazz:
    def __init__(self, name: str, is_activity: bool, is_main_activity: bool):
        self.name = name  # class full name
        self.is_activity = is_activity  # is this class an activity?
        self.is_main_activity = is_main_activity  # is this class the main activity?
        self.methods: set[Method] = set()  # set of methods in this class
        self.fields = set()  # set of fields in this class

    def add_method(self, method: Method):
        if method in self.methods:
            return False
        self.methods.add(method)
        return True

    def add_field(self, field: str):
        self.fields.add(field)

    def __str__(self):
        return f"Clazz=[name={self.name},is_activity={self.is_activity},is_main={self.is_main_activity},method={self.methods}, fields={self.fields}]"

    def __repr__(self):
        return f"[{self.name},{self.is_activity},{self.is_main_activity}]"


class Classes:
    def __init__(self):
        self.logging = logging_api.getLogger("rvandroid.parser.classes.Classes")
        self.classes: dict[str, Clazz] = {}
        self.methods: dict[str, Method] = {}

    def get_classes(self):
        return [self.classes[name] for name in self.classes.keys()]

    def add_clazz(self, name: str, is_activity: bool, is_main_activity: bool) -> Clazz:
        # self.logging.debug(f"Adding class {name}")
        if name not in self.classes:
            self.logging.debug(f"Class {name} not found, adding")
            self.classes[name] = Clazz(name, is_activity, is_main_activity)
        return self.classes[name]

    def get_clazz(self, name: str) -> Clazz | None:
        if name in self.classes:
            return self.classes[name]
        return None

    def add_method(self, method: Method):
        if method.signature not in self.methods:
            clazz = self.get_clazz(method.class_name)
            if clazz and clazz.add_method(method):
                self.methods[method.signature] = method
                self.logging.debug(f"Added method {method.signature}")
                return True
        return False

    def __str__(self):
        text = []
        for name in self.classes:
            text.append(str(self.classes[name]))
        return f"Classes=[classes={text}]"


class WidgetEventType(Enum):
    CLICK = 1
    LONG_CLICK = 2
    SCROLL = 3
    DRAG = 4
    HOVER = 5
    TOUCH = 6
    FOCUS = 7
    KEY = 8
    TEXT_CHANGE = 9
    GESTURE = 10
    SELECTION = 11
    OTHER = 12


class WidgetListener:
    def __init__(self, event_type: WidgetEventType, clazz: str, method: str, signature: str):
        self.type = event_type
        self.clazz = clazz
        self.method = method
        self.signature = signature

    def __str__(self):
        return f"WidgetListener=[type={self.type},clazz={self.clazz},method={self.method},signature={self.signature}]"

    def __repr__(self):
        return f"{self.signature}"

    def __eq__(self, other):
        if isinstance(other, WidgetListener):
            return (self.signature, self.type) == (other.signature, other.type)
        return False

    def __hash__(self):
        return hash((self.signature, self.type))


class WidgetType(Enum):
    BUTTON = "android.widget.Button"
    CHECKBOX = "android.widget.CheckBox"
    CHECKED_TEXT_VIEW = "android.widget.CheckedTextView"
    EDIT_TEXT = "android.widget.EditText"
    IMAGE_BUTTON = "android.widget.ImageButton"
    IMAGE_VIEW = "android.widget.ImageView"
    MENU_ITEM = "android.view.MenuItem"
    RADIO_BUTTON = "android.widget.RadioButton"
    SPINNER = "android.widget.Spinner"
    SUB_MENU = "android.view.SubMenu"
    TEXT_VIEW = "android.widget.TextView"
    TOGGLE_BUTTON = "android.widget.ToggleButton"
    OTHER = "OTHER"

    @staticmethod
    def from_string(type_str: str):
        if type_str == "BUTTON":
            return WidgetType.BUTTON
        if type_str == "CHECKBOX":
            return WidgetType.CHECKBOX
        if type_str == "CHECKED_TEXT_VIEW":
            return WidgetType.CHECKED_TEXT_VIEW
        if type_str == "EDIT_TEXT":
            return WidgetType.EDIT_TEXT
        if type_str == "IMAGE_BUTTON":
            return WidgetType.IMAGE_BUTTON
        if type_str == "IMAGE_VIEW":
            return WidgetType.IMAGE_VIEW
        if type_str == "MENU_ITEM":
            return WidgetType.MENU_ITEM
        if type_str == "RADIO_BUTTON":
            return WidgetType.RADIO_BUTTON
        if type_str == "SPINNER":
            return WidgetType.SPINNER
        if type_str == "SUB_MENU":
            return WidgetType.SUB_MENU
        if type_str == "TEXT_VIEW":
            return WidgetType.TEXT_VIEW
        if type_str == "TOGGLE_BUTTON":
            return

    def from_class_name(class_name: str):
        if class_name == "android.widget.Button":
            return WidgetType.BUTTON
        if class_name == "android.widget.CheckBox":
            return WidgetType.CHECKBOX
        if class_name == "android.widget.CheckedTextView":
            return WidgetType.CHECKED_TEXT_VIEW
        if class_name == "android.widget.EditText":
            return WidgetType.EDIT_TEXT
        if class_name == "android.widget.ImageButton":
            return WidgetType.IMAGE_BUTTON
        if class_name == "android.widget.ImageView":
            return WidgetType.IMAGE_VIEW
        if class_name == "android.view.MenuItem":
            return WidgetType.MENU_ITEM
        if class_name == "android.widget.RadioButton":
            return WidgetType.RADIO_BUTTON
        if class_name == "android.widget.Spinner":
            return WidgetType.SPINNER
        if class_name == "android.view.SubMenu":
            return WidgetType.SUB_MENU
        if class_name == "android.widget.TextView":
            return WidgetType.TEXT_VIEW
        if class_name == "android.widget.ToggleButton":
            return WidgetType.TOGGLE_BUTTON
        return WidgetType.OTHER


class Widget:
    def __init__(self, widget_id: str, name: str, widget_type: WidgetType):
        self.logging = logging_api.getLogger("rvandroid.parser.classes.Widget")
        self.id = widget_id
        self.type = widget_type
        self.name = name
        self.text = ""
        self.hint = ""
        self.field = ""
        self.input_type = ""
        self.entries: list[str] = []
        self.listeners: set[WidgetListener] = set()

    def add_listener(self, listener: WidgetListener):
        if listener in self.listeners:
            self.logging.debug(f"Listener '{listener.signature}' already exists")
            return False
        self.logging.debug(f">>> Adding listener '{listener.signature}': {listener}")
        self.listeners.add(listener)
        return True

    def __str__(self):
        return f"Widget=[id={self.id},type={self.type},name={self.name},text={self.text},hint={self.hint},field={self.field},input_type={self.input_type},entries={self.entries},listeners={self.listeners}]"

    def __repr__(self):
        return f"{self.id}"


class WindowType(Enum):
    ACTIVITY = 1
    OPTIONSMENU = 2
    CONTEXTMENU = 3
    DIALOG = 4
    FRAGMENT = 5

    @staticmethod
    def from_string(window_type: str):
        if window_type == "ACT":
            return WindowType.ACTIVITY
        if window_type == "OPTIONS_MENU":
            return WindowType.OPTIONSMENU
        if window_type == "CONTEXT_MENU":
            return WindowType.CONTEXTMENU
        if window_type == "DIALOG":
            return WindowType.DIALOG
        if window_type == "FRAGMENT":
            return WindowType.FRAGMENT
        return None


class Window:
    def __init__(self, name: str):
        self.logging = logging_api.getLogger("rvandroid.parser.classes.Window")
        self.id = ""  # TODO
        self.name = name
        self.type: WindowType = WindowType.ACTIVITY
        self.layout_file = ""
        self.widgets: dict[str, Widget] = {}
        self.fields = set()  # TODO

    def add_widget(self, widget: Widget):
        widget_id = str(widget.id)
        if widget_id in self.widgets:
            self.logging.debug(f"Widget {widget_id} already exists")
            return False
        self.widgets[widget_id] = widget
        self.logging.debug(f">>> Widget {widget_id} added: {widget}")
        return True

    def get_widget(self, widget_id: str):
        self.logging.debug(f"Getting widget {widget_id} from window {self.name}")
        if widget_id in self.widgets:
            self.logging.debug(f"Widget {widget_id} found: {self.widgets[widget_id]}")
            return self.widgets[widget_id]
        self.logging.warning(f"Widget {widget_id} not found")
        return None

    def __str__(self):
        return f"Window=[name={self.name},type={self.type},widgets={self.widgets}]"

    def __repr__(self):
        return f"{self.name}"


class WindowTransition:  # TODO
    def __init__(self, widget_id: str, transition_type: WidgetEventType, method_signature: str):
        self.widget_id = widget_id
        self.event_type = transition_type
        self.method = method_signature

    def __str__(self):
        return f"WindowTransition=[widget_id={self.widget_id},event_type={self.event_type},method={self.method}]"

    def __repr__(self):
        return f"{self.method}"


class WindowTransitionGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_transition(self, from_window: Window, to_window: Window, events: list[WindowTransition]):
        self.graph.add_edge(from_window, to_window, events=events)

    def __str__(self):
        return f"WindowTransitionGraph=[graph={self.graph.edges(data=True)}]"


class Windows:
    def __init__(self):
        self.logging = logging_api.getLogger("rvandroid.parser.classes.Windows")
        self.windows: dict[str, Window] = {}  # name --> Window
        self.widgets: dict[str, Widget] = {}  # id --> Widget

    def add_window(self, window: Window) -> bool:
        # self.logging.debug(f"Adding window {window.name}")
        if window.name in self.windows:
            self.logging.debug(f"Window {window.name} already exists")
            return False
        self.logging.debug(f">>>>>>>>>>>>>>>>> Window {window.name} added: {window}")
        self.windows[window.name] = window
        for widget_id in window.widgets:
            widget = window.widgets[widget_id]
            self.logging.debug(f"Adding widget {widget.id}: {widget}")
            self.widgets[widget.id] = widget
            window.add_widget(widget)
        return True

    # def add_widget(self, widget: Widget) -> bool: # TODO adicionar na instancia de Window ......................
    #     # self.logging.debug(f"Adding widget {widget.id}")
    #     if widget.id in self.widgets:
    #         self.logging.debug(f"Widget {widget.id} already exists")
    #         return False
    #     self.widgets[widget.id] = widget
    #     self.logging.debug(f">>> Widget {widget.id} added: {widget}")
    #     return True
    def get_or_create(self, window_name: str) -> Window:
        self.logging.debug(f"Getting or creating window {window_name}")
        if window_name in self.windows:
            self.logging.debug(f"Window {window_name} found: {self.windows[window_name]}")
            return self.windows[window_name]
        self.logging.debug(f"Window {window_name} not found, creating new window")
        window = Window(window_name)
        if "android.view.Menu" == window_name:
            window.type = WindowType.OPTIONSMENU
        self.windows[window_name] = window
        return window

    def get_window_by_id(self, window_id: str) -> Window | None:
        self.logging.debug(f"Getting window by id {window_id}")
        for window_name in self.windows:
            window = self.windows[window_name]
            print(f"ID={window.id} :: {window}")
            print(f"window.id={type(window.id)}")
            print(f"window_id={type(window_id)}")
            if window.id == window_id:
                self.logging.debug(f"Window {window.name} found: {window}")
                return window
        self.logging.debug(f"Window {window_id} not found")
        return None

    def get_window(self, window_name: str) -> Window | None:
        self.logging.debug(f"Getting window {window_name}")
        if window_name in self.windows:
            self.logging.debug(f"Window {window_name} found: {self.windows[window_name]}")
            return self.windows[window_name]
        self.logging.debug(f"Window {window_name} not found")
        return None

    def get_widget(self, widget_id: str) -> Widget | None:
        # self.logging.debug(f"Getting widget {widget_id}")
        if widget_id in self.widgets:
            self.logging.debug(f"Widget {widget_id}: {self.widgets[widget_id]}")
            return self.widgets[widget_id]
        self.logging.debug(f"Widget {widget_id} not found")
        return None

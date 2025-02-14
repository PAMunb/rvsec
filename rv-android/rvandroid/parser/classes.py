from enum import Enum


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
        self.classes: dict[str, Clazz] = {}
        self.methods: dict[str, Method] = {}

    def get_classes(self):
        return [self.classes[name] for name in self.classes.keys()]

    def add_clazz(self, name: str, is_activity: bool, is_main_activity: bool) -> Clazz:
        if name not in self.classes:
            self.classes[name] = Clazz(name, is_activity, is_main_activity)
        return self.classes[name]

    def get_clazz(self, name: str):
        if name in self.classes:
            return self.classes[name]
        return None

    def add_method(self, method: Method):
        if method.signature not in self.methods:
            clazz = self.get_clazz(method.class_name)
            if clazz and clazz.add_method(method):
                self.methods[method.signature] = method
                return True
        return False

    def __str__(self):
        text = []
        for name in self.classes:
            text.append(str(self.classes[name]))
        return f"Classes=[classes={text}]"


class WidgetListener:
    def __init__(self, listener_type: str, clazz: str, method: str, signature: str):
        self.type = listener_type  # TODO
        self.clazz = clazz
        self.method = method
        self.signature = signature

    def __str__(self):
        return f"WidgetListener=[type={self.type},clazz={self.clazz},method={self.method},signature={self.signature}]"

    def __repr__(self):
        return f"{self.signature}"


class WidgetType(Enum):
    TEXT_VIEW = 1
    BUTTON = 2
    EDIT_TEXT = 3
    CHECK_BOX = 4
    RADIO_BUTTON = 5
    SPINNER = 6
    OTHER = 51

    # TODO pegar os outros tipos de widgets
    @staticmethod
    def from_string(widget_type: str):
        if widget_type == "TEXT_VIEW":
            return WidgetType.TEXT_VIEW
        if widget_type == "BUTTON":
            return WidgetType.BUTTON
        if widget_type == "EDIT_TEXT":
            return WidgetType.EDIT_TEXT
        if widget_type == "CHECK_BOX":
            return WidgetType.CHECK_BOX
        if widget_type == "RADIO_BUTTON":
            return WidgetType.RADIO_BUTTON
        if widget_type == "SPINNER":
            return WidgetType.SPINNER
        return WidgetType.OTHER


class Widget:
    def __init__(self, widget_id: str, name: str, widget_type: WidgetType):
        self.id = widget_id
        self.type = widget_type
        self.name = name
        self.text = ""
        self.hint = ""
        self.field = ""
        self.input_type = ""
        self.entries: list[str] = []
        self.listeners: list[WidgetListener] = []

    def __str__(self):
        return f"Widget=[id={self.id},type={self.type},name={self.name},text={self.text},hint={self.hint},field={self.field},input_type={self.input_type},entries={self.entries},listeners={self.listeners}]"

    def __repr__(self):
        return f"{self.id}"


class WindowType(Enum):
    ACTIVITY = 1

    # TODO pegar os outros tipos de janelas
    @staticmethod
    def from_string(window_type: str):
        if window_type == "ACT":
            return WindowType.ACTIVITY
        return None


class Window:
    def __init__(self, name: str):
        self.id = "" # TODO
        self.name = name
        self.type: WindowType = WindowType.ACTIVITY
        self.layout_file = ""
        self.widgets: dict[str, Widget] = {}
        self.fields = set()  # TODO

    def add_widget(self, widget: Widget):
        if widget.id in self.widgets:
            return False
        self.widgets[widget.id] = widget
        return True

    def get_widget(self, widget_id: str):
        if widget_id in self.widgets:
            return self.widgets[widget_id]
        return None

    def __str__(self):
        return f"Window=[name={self.name},type={self.type},widgets={self.widgets}]"

    def __repr__(self):
        return f"{self.name}"


class WidgetListenerType(Enum):
    CLICK = 1
    LONG_CLICK = 2
    FOCUS_CHANGE = 3
    TEXT_CHANGED = 4
    ITEM_SELECTED = 5
    ITEM_CLICKED = 6
    ITEM_LONG_CLICKED = 7
    ITEM_FOCUSED = 8
    ITEM_PRESSED = 9
    ITEM_SELECTED_LISTENER = 10
    ITEM_CLICKED_LISTENER = 11
    ITEM_LONG_CLICKED_LISTENER = 12
    ITEM_FOCUSED_LISTENER = 13
    ITEM_PRESSED_LISTENER = 14
    # ITEM_SELECTED_LISTENER_2 =


class WindowTransition:
    def __init__(self, widget_id: str, transition_type: WidgetListenerType, widget_listener: WidgetListener):
        self.widget_id = widget_id
        self.transition_type = transition_type
        self.widget_listener = widget_listener


class WindowTransitionGraph:
    def __init__(self):
        self.windows: dict[str, Window] = {}
        self.transitions: list[WindowTransition] = []  # TODO set

    def add_transition(self, from_window: Window, to_window: Window, transition: WindowTransition):
        if from_window.id not in self.windows:
            self.windows[from_window.id] = from_window
        if to_window.id not in self.windows:
            self.windows[to_window.id] = to_window
        self.transitions.append(transition)

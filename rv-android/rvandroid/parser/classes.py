# Part 1: Imports and Basic Classes
import logging as logging_api
from enum import Enum
from typing import Optional, Set, Dict, List

import networkx as nx


class Method:
    """
    Represents a method in a class with its properties and relationships.
    Used for tracking method reachability and MOP (Method Operating Point) analysis.
    """

    def __init__(
            self,
            class_name: str,
            name: str,
            params: List[str],
            signature: str,
            reachable: bool,
            reaches_mop: bool,
            directly_reaches_mop: bool,
            directly_reachable_mop: List[str], # TODO remover ... não sera usado ... eh uma lista dos metodos (assinaturas soot) que sao (ou podem ser) chamados diretamente no corpo deste metodo
    ):
        self.class_name = class_name
        self.name = name
        self.params = params
        self.signature = signature
        self.reachable = reachable
        self.reaches_mop = reaches_mop
        self.directly_reaches_mop = directly_reaches_mop
        self.directly_reachable_mop = directly_reachable_mop
        self.reached = False
    
    def to_json(self):
        print(f"METHOD to json: {self.signature}")
        return {
            "class": self.class_name,
            "name": self.name,
            "params": self.params,
            "signature": self.signature,
            "reachable": self.reachable,
            "reaches_mop": self.reaches_mop,
            "directly_reaches_mop": self.directly_reaches_mop
        }

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Method):
            return self.signature == other.signature
        return False

    def __hash__(self) -> int:
        return hash(self.signature)

    def __str__(self) -> str:
        return (f"Method=[name={self.name}, signature={self.signature}, "
                f"reachable={self.reachable}, reaches_mop={self.reaches_mop}, "
                f"directly_reaches_mop={self.directly_reaches_mop}]")

    def __repr__(self) -> str:
        return self.signature


class Clazz:
    """
    Represents a class in the application, tracking its activities and methods.
    Manages the relationship between classes, methods, and fields.
    """

    def __init__(self, name: str, is_activity: bool, is_main_activity: bool):
        self.name = name
        self.is_activity = is_activity
        self.is_main_activity = is_main_activity
        self.methods: Set[Method] = set()
        self.fields: Set[str] = set()

    def add_method(self, method: Method) -> bool:
        """Adds a method to the class if it doesn't already exist."""
        if method in self.methods:
            return False
        self.methods.add(method)
        return True

    def add_field(self, field: str) -> None:
        """Adds a field to the class's field set."""
        self.fields.add(field)
    
    def to_json(self):
        print(f"CLASS to json: {self.name}")
        return {
            "name": self.name,
            "is_activity": self.is_activity,
            "is_main_activity": self.is_main_activity,
            "methods": [method.to_json() for method in self.methods],
            "fields": list(self.fields)
        }

    def __str__(self) -> str:
        return (f"Clazz=[name={self.name}, is_activity={self.is_activity}, "
                f"is_main={self.is_main_activity}, methods={self.methods}, "
                f"fields={self.fields}]")

    def __repr__(self) -> str:
        return f"[{self.name},{self.is_activity},{self.is_main_activity}]"


# Part 2: Classes Manager and Event Types
class Classes:
    """
    Manages all classes and methods in the application.
    Provides functionality to add and retrieve classes and methods.
    """

    def __init__(self):
        self.logging = logging_api.getLogger("rvandroid.parser.classes.Classes")
        self.classes: Dict[str, Clazz] = {}
        self.methods: Dict[str, Method] = {}

    def get_classes(self) -> List[Clazz]:
        """Returns a list of all classes."""
        return list(self.classes.values())

    def add_clazz(self, name: str, is_activity: bool, is_main_activity: bool) -> Clazz:
        """Adds a new class or returns existing one."""
        if name not in self.classes:
            self.logging.debug(f"Class {name} not found, adding")
            self.classes[name] = Clazz(name, is_activity, is_main_activity)
        return self.classes[name]

    def get_clazz(self, name: str) -> Optional[Clazz]:
        """Retrieves a class by name if it exists."""
        return self.classes.get(name)

    def add_method(self, method: Method) -> bool:
        """Adds a method to both the class and the method's dictionary."""
        if method.signature not in self.methods:
            clazz = self.get_clazz(method.class_name)
            if clazz and clazz.add_method(method):
                self.methods[method.signature] = method
                self.logging.debug(f"Added method {method.signature}")
                return True
        return False
        
    def to_json(self):
        print("Converting classes to json")
        return {
            "classes": [clazz.to_json() for clazz in self.classes.values()]
        }
    
    # def __str__(self):
    #     text = []
    #     for name in self.classes:
    #         text.append(str(self.classes[name]))
    #     return f"Classes=[classes={text}]"


class WidgetEventType(Enum):
    """Enumeration of possible widget event types in the application."""
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


# Part 3: Widget Related Classes
class WidgetEvent:
    """
    Represents a listener for widget events.
    Tracks the event type and associated method information.
    """

    def __init__(self, event_type: WidgetEventType, clazz: str, method: str, signature: str):
        self.type = event_type
        self.clazz = clazz
        self.method = method
        self.signature = signature

    def to_json(self):
        return {
            "type": self.type.name,
            "signature": self.signature
        }

    def __eq__(self, other: object) -> bool:
        if isinstance(other, WidgetEvent):
            return (self.signature, self.type) == (other.signature, other.type)
        return False

    def __hash__(self) -> int:
        return hash((self.signature, self.type))

    def __str__(self) -> str:
        return (f"WidgetEvent=[type={self.type}, clazz={self.clazz}, "
                f"method={self.method}, signature={self.signature}]")

    def __repr__(self) -> str:
        return f"({self.type.name},{self.signature})"


class WidgetType(Enum):
    """
    Enumeration of Android widget types.
    Includes common Android UI elements and utility methods.
    """
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
    def from_string(type_str: str) -> 'WidgetType':
        """Converts a string to WidgetType enum value."""
        try:
            return WidgetType[type_str]
        except KeyError:
            return WidgetType.OTHER

    @staticmethod
    def from_class_name(class_name: str) -> 'WidgetType':
        """Converts a class name to corresponding WidgetType."""
        return next((wt for wt in WidgetType if wt.value == class_name), WidgetType.OTHER)


class Widget:
    """
    Represents a UI widget in the application.
    Manages widget properties and associated listeners.
    """

    def __init__(self, widget_id: str, name: str, widget_type: WidgetType):
        self.logging = logging_api.getLogger("rvandroid.parser.classes.Widget")
        self.id = widget_id
        self.type = widget_type
        self.name = name
        self.text = ""
        self.hint = ""
        self.field = ""
        self.input_type = ""
        self.entries: List[str] = []
        self.events: Set[WidgetEvent] = set()

    def add_event(self, event: WidgetEvent) -> bool:
        """Adds a new event if it doesn't already exist."""
        if event in self.events:
            self.logging.debug(f"Event '{event.signature}' already exists")
            return False
        self.logging.debug(f">>> Adding event '{event.signature}': {event}")
        self.events.add(event)
        return True

    def to_json(self):
        return {
            "id": self.id,
            "type": self.type.name,
            "name": self.name,
            "text": self.text,
            "hint": self.hint,
            "field": self.field,
            "input_type": self.input_type,
            "entries": self.entries,
            "events": [event.to_json() for event in self.events]
        }

    def __eq__(self, value):
        if isinstance(value, Widget):
            return self.id == value.id
        return False

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return f"Widget=[id={self.id}, type={self.type}, name={self.name}, text={self.text}, hint={self.hint}, field={self.field}, input_type={self.input_type}, entries={self.entries}, events={self.events}]"

    def __repr__(self):
        return f"{self.id}"


# Part 4: Window Management Classes
class WindowType(Enum):
    """Enumeration of different window types in the application."""
    ACTIVITY = 1
    OPTIONSMENU = 2
    CONTEXTMENU = 3
    DIALOG = 4
    FRAGMENT = 5

    @staticmethod
    def from_string(window_type: str) -> Optional['WindowType']:
        """Converts a string representation to WindowType enum value."""
        type_mapping = {
            "ACT": WindowType.ACTIVITY,
            "OPTIONS_MENU": WindowType.OPTIONSMENU,
            "CONTEXT_MENU": WindowType.CONTEXTMENU,
            "DIALOG": WindowType.DIALOG,
            "FRAGMENT": WindowType.FRAGMENT
        }
        return type_mapping.get(window_type)


class Window:
    """
    Represents a window in the application.
    Manages window properties and associated widgets.
    """

    def __init__(self, name: str):
        self.logging = logging_api.getLogger("rvandroid.parser.classes.Window")
        self.id = ""
        self.name = name
        self.type: WindowType = WindowType.ACTIVITY
        self.layout_file = ""
        self.widgets: Dict[str, Widget] = {}
        self.fields: Set[str] = set()

    def add_widget(self, widget: Widget) -> bool:
        """Adds a widget to the window if it doesn't already exist."""
        widget_id = str(widget.id)
        if widget_id in self.widgets:
            self.logging.debug(f"Widget {widget_id} already exists")
            return False
        self.widgets[widget_id] = widget
        self.logging.debug(f">>> Widget {widget_id} added: {widget}")
        return True

    def get_widget(self, widget_id: str) -> Optional[Widget]:
        """Retrieves a widget by ID if it exists."""
        self.logging.debug(f"Getting widget {widget_id} from window {self.name}")
        widget = self.widgets.get(widget_id)
        if widget:
            self.logging.debug(f"Widget {widget_id} found: {widget}")
            return widget
        self.logging.warning(f"Widget {widget_id} not found")
        return None

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.name,
            "layout_file": self.layout_file,
            "widgets": [widget.to_json() for widget in self.widgets.values()],
            "fields": list(self.fields)
        }

    def __str__(self):
        return f"Window=[id={self.id}, name={self.name}, type={self.type}, layout_file={self.layout_file}]"

    def __repr__(self):
        return self.name


# Part 5: Window Transition Classes
class WindowTransition:
    """
    Represents a transition between windows triggered by a widget event.
    """

    def __init__(
            self,
            widget_id: str,
            transition_type: WidgetEventType,
            method_signature: str
    ):
        self.widget_id = widget_id
        self.event_type = transition_type
        self.method = method_signature
        
    def to_json(self):
        return {
            "widget_id": self.widget_id,
            "event_type": self.event_type.name,
            "method": self.method
        }

    def __str__(self) -> str:
        return (f"WindowTransition=[widget_id={self.widget_id}, "
                f"event_type={self.event_type}, method={self.method}]")

    def __repr__(self) -> str:
        return self.method


class WindowTransitionGraph:
    """
    Manages the graph of transitions between windows.
    Uses NetworkX for graph representation.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_transition(
            self,
            from_window: Window,
            to_window: Window,
            events: List[WindowTransition]
    ) -> None:
        """Adds a transition edge between windows with associated events."""
        self.graph.add_edge(from_window, to_window, events=events)

    def to_json(self):
        return {
            "graph": [
                {
                    "from_window": from_window.name,
                    "to_window": to_window.name,
                    "events": [event.to_json() for event in events]
                }
                for from_window, to_window, events in self.graph.edges(data="events")
            ]
        }

    def __str__(self) -> str:
        return f"WindowTransitionGraph=[graph={self.graph.edges(data=True)}]"


class Windows:
    """
    Manages all windows and their widgets in the application.
    Provides functionality to add and retrieve windows and widgets.
    """

    def __init__(self):
        self.logging = logging_api.getLogger("rvandroid.parser.classes.Windows")
        self.windows: Set[Window] = set()
        self.widgets: Dict[str, Widget] = {}

    def add_window(self, window: Window) -> bool:
        """Adds a window and its widgets if they don't already exist."""
        if window in self.windows:
            self.logging.debug(f"Window {window.name} already exists")
            return False
        self.windows.add(window)
        self.logging.debug(f">>> Window {window.name} added: {window}")
        self.__update_widgets_of_window(window)        
        return True

    def create_new_window(self, window_name: str, window_id: str = "") -> Window:
        """Helper method to create a new window."""
        window = Window(window_name)
        if window_name == "android.view.Menu":
            window.type = WindowType.OPTIONSMENU        
        if window_id:
            window.id = window_id
        self.add_window(window)
        self.logging.debug(f"Window created: {window}")        
        return window
    
    def __update_widgets_of_window(self, window: Window):
        for widget_id, widget in window.widgets.items():
            self.logging.debug(f"Adding widget {widget.id}: {widget}")
            self.widgets[widget.id] = widget            

    def get_window_by_id(self, window_id: str) -> Optional[Window]:
        """Retrieves a window by its ID."""
        return next((w for w in self.windows if w.id == window_id), None)

    def get_window(self, window_name: str) -> Optional[Window]:
        """Retrieves a window by its name."""
        return next((w for w in self.windows if w.name == window_name), None)

    def add_widget(self, window: Window, widget: Widget) -> bool:
        """Adds a widget to a window if it doesn't already exist."""
        if window.add_widget(widget):
            self.widgets[widget.id] = widget
            self.logging.debug(f"Widget {widget.id} added: {widget}")
            return True
        self.logging.debug(f"Widget {widget.id} already exists")
        return False

    def get_widget(self, widget_id: str) -> Optional[Widget]:
        """Retrieves a widget by its ID."""
        widget = self.widgets.get(widget_id)
        if widget:
            self.logging.debug(f"Widget {widget_id}: {widget}")
        else:
            self.logging.debug(f"Widget {widget_id} not found")
        return widget
    
    def to_json(self):
        return {
            "windows": [window.to_json() for window in self.windows]
        }
    
# def get_or_create(self, window_name: str, window_id: str = "") -> Window:
#     """Gets an existing window or creates a new one."""
#     self.logging.debug(f"Getting or creating window {window_name} :: ID= {window_id}")
#     window = self.get_window(window_name)
#     self.logging.debug(f"Window {window_name} found: {window}")
#     if window:
#         if window_id:
#             if window.id == window_id:
#                 self.logging.debugself.logging.debug(f"Window {window_name} found (by id): {window}")
#                 return window
#             elif not window.id:
#                 self.logging.debug(f"Window {window_name} ... update id: {window}")
#                 window.id = window_id
#             else:
#                 self.logging.debug(f"Window {window_name} ... new window: {window}")
#                 window = self.create_new_window(window_name, window_id)
#         self.logging.debug(f"Window {window_name} ... returning: {window}")
#         return window
#     self.logging.debug(f"Window {window_name} not found ... creating new window")
#     return self.create_new_window(window_name, window_id)

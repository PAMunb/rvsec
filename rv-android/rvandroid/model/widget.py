import logging as logging_api
from enum import Enum
from typing import List, Set


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


class WidgetEvent:
    """
    Represents an event for widget.
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
        self.logging = logging_api.getLogger("rvandroid.model.widget.Widget")
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

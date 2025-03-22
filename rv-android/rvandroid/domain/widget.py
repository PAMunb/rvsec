# widget.py
from enum import Enum
from typing import List, Set

from rvandroid.util.logging_manager import LoggingManager


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
        """
        Initialize a widget event.

        Args:
            event_type: Type of the event
            clazz: Class name handling the event
            method: Method name handling the event
            signature: Full method signature
        """
        self.type = event_type
        self.clazz = clazz
        self.method = method
        self.signature = signature

    def to_json(self):
        """
        Convert event to JSON format.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "type": self.type.name,
            "signature": self.signature
        }

    def __eq__(self, other: object) -> bool:
        """
        Compare this event with another for equality.

        Args:
            other: Object to compare with

        Returns:
            True if equal, False otherwise
        """
        if isinstance(other, WidgetEvent):
            return (self.signature, self.type) == (other.signature, other.type)
        return False

    def __hash__(self) -> int:
        """
        Get hash value for this event.

        Returns:
            Hash value based on signature and type
        """
        return hash((self.signature, self.type))

    def __str__(self) -> str:
        """
        Get string representation of this event.

        Returns:
            String representation
        """
        return (f"WidgetEvent=[type={self.type}, clazz={self.clazz}, "
                f"method={self.method}, signature={self.signature}]")

    def __repr__(self) -> str:
        """
        Get representation string for this event.

        Returns:
            Representation string
        """
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
        """
        Convert a string to WidgetType enum value.

        Args:
            type_str: String representation of type

        Returns:
            Corresponding WidgetType enum value
        """
        try:
            return WidgetType[type_str]
        except KeyError:
            return WidgetType.OTHER

    @staticmethod
    def from_class_name(class_name: str) -> 'WidgetType':
        """
        Convert a class name to corresponding WidgetType.

        Args:
            class_name: Full class name

        Returns:
            Corresponding WidgetType enum value
        """
        return next((wt for wt in WidgetType if wt.value == class_name), WidgetType.OTHER)


class Widget:
    """
    Represents a UI widget in the application.
    Manages widget properties and associated listeners.
    """

    def __init__(self, widget_id: str, name: str, widget_type: WidgetType):
        """
        Initialize a widget.

        Args:
            widget_id: Unique widget identifier
            name: Widget name
            widget_type: Type of the widget
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger("model.widget.Widget", {
            "widget_id": widget_id,
            "widget_type": widget_type.name
        })

        self.id = widget_id
        self.type = widget_type
        self.name = name
        self.text = ""
        self.hint = ""
        self.field = ""
        self.input_type = ""
        self.entries: List[str] = []
        self.events: Set[WidgetEvent] = set()

        self.logger.debug(f"Widget created: {self.name or widget_id}")

    def add_event(self, event: WidgetEvent) -> bool:
        """
        Add a new event if it doesn't already exist.

        Args:
            event: Event to add

        Returns:
            True if event was added, False if it already exists
        """
        if event in self.events:
            self.logger.debug(f"Event '{event.signature}' already exists for widget {self.id}")
            return False

        self.logger.debug(f"Adding event '{event.signature}' to widget {self.id}")
        self.events.add(event)
        return True

    def to_json(self):
        """
        Convert widget to JSON format.

        Returns:
            Dictionary representation for JSON serialization
        """
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
        """
        Compare this widget with another for equality.

        Args:
            value: Object to compare with

        Returns:
            True if equal, False otherwise
        """
        if isinstance(value, Widget):
            return self.id == value.id
        return False

    def __hash__(self):
        """
        Get hash value for this widget.

        Returns:
            Hash value based on id
        """
        return hash(self.id)

    def __str__(self):
        """
        Get string representation of this widget.

        Returns:
            String representation
        """
        return f"Widget=[id={self.id}, type={self.type}, name={self.name}, text={self.text}, hint={self.hint}, field={self.field}, input_type={self.input_type}, entries={self.entries}, events={self.events}]"

    def __repr__(self):
        """
        Get representation string for this widget.

        Returns:
            Representation string
        """
        return f"{self.id}"

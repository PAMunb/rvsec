import logging as logging_api
from enum import Enum
from typing import Optional, Dict, Set

from rvandroid.model.widget import Widget


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
        self.logging = logging_api.getLogger("rvandroid.model.window.Window")
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
    
    def get_widget_by_name(self, widget_name: str) -> Optional[Widget]:
        """Retrieves a widget by its name if it exists."""
        self.logging.debug(f"Getting widget '{widget_name}' from window {self.name}")
        for widget in self.widgets.values():
            if widget.name == widget_name:
                self.logging.debug(f"Widget {widget_name} found: {widget}")
                return widget
        self.logging.warning(f"Widget {widget_name} not found")
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


class Windows:
    """
    Manages all windows and their widgets in the application.
    Provides functionality to add and retrieve windows and widgets.
    """

    def __init__(self):
        self.logging = logging_api.getLogger("rvandroid.model.window.Windows")
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

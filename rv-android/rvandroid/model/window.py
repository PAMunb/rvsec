# window.py
from enum import Enum
from typing import Optional, Dict, Set

from rvandroid.model.widget import Widget
from rvandroid.util.logging_manager import LoggingManager


class WindowType(Enum):
    """Enumeration of different window types in the application."""
    ACTIVITY = 1
    OPTIONSMENU = 2
    CONTEXTMENU = 3
    DIALOG = 4
    FRAGMENT = 5

    @staticmethod
    def from_string(window_type: str) -> Optional['WindowType']:
        """
        Convert a string representation to WindowType enum value.

        Args:
            window_type: String representation of window type

        Returns:
            Corresponding WindowType or None if not found
        """
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
        """
        Initialize a window with its name.

        Args:
            name: Window name
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger("model.window.Window", {"window": name})

        self.id = ""
        self.name = name
        self.type: WindowType = WindowType.ACTIVITY
        self.layout_file = ""
        self.widgets: Dict[str, Widget] = {}
        self.fields: Set[str] = set()

        self.logger.debug(f"Window created: {name}")

    def add_widget(self, widget: Widget) -> bool:
        """
        Add a widget to the window if it doesn't already exist.

        Args:
            widget: Widget to add

        Returns:
            True if widget was added, False if already exists
        """
        widget_id = str(widget.id)
        if widget_id in self.widgets:
            self.logger.debug(f"Widget {widget_id} already exists in window {self.name}")
            return False

        self.widgets[widget_id] = widget
        self.logger.debug(f"Added widget {widget_id} to window {self.name}")
        return True

    def get_widget(self, widget_id: str) -> Optional[Widget]:
        """
        Retrieve a widget by ID if it exists.

        Args:
            widget_id: Widget ID to look for

        Returns:
            Widget if found, None otherwise
        """
        self.logger.debug(f"Getting widget {widget_id} from window {self.name}")
        widget = self.widgets.get(widget_id)

        if widget:
            self.logger.debug(f"Widget {widget_id} found")
            return widget

        self.logger.debug(f"Widget {widget_id} not found")
        return None

    def get_widget_by_name(self, widget_name: str) -> Optional[Widget]:
        """
        Retrieve a widget by its name if it exists.

        Args:
            widget_name: Widget name to look for

        Returns:
            Widget if found, None otherwise
        """
        self.logger.debug(f"Looking for widget '{widget_name}' in window {self.name}")

        for widget in self.widgets.values():
            if widget.name == widget_name:
                self.logger.debug(f"Widget '{widget_name}' found")
                return widget

        self.logger.debug(f"Widget '{widget_name}' not found")
        return None

    def to_json(self):
        """
        Convert window to JSON format.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.name,
            "layout_file": self.layout_file,
            "widgets": [widget.to_json() for widget in self.widgets.values()],
            "fields": list(self.fields)
        }

    def __str__(self):
        """
        Get string representation of this window.

        Returns:
            String representation
        """
        return f"Window=[id={self.id}, name={self.name}, type={self.type}, layout_file={self.layout_file}]"

    def __repr__(self):
        """
        Get representation string for this window.

        Returns:
            Representation string
        """
        return self.name


class Windows:
    """
    Manages all windows and their widgets in the application.
    Provides functionality to add and retrieve windows and widgets.
    """

    def __init__(self):
        """Initialize the Windows container with logging."""
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger("model.window.Windows")

        self.windows: Set[Window] = set()
        self.widgets: Dict[str, Widget] = {}

        self.logger.debug("Windows container initialized")

    def add_window(self, window: Window) -> bool:
        """
        Add a window and its widgets if they don't already exist.

        Args:
            window: Window to add

        Returns:
            True if window was added, False if already exists
        """
        if window in self.windows:
            self.logger.debug(f"Window {window.name} already exists")
            return False

        self.windows.add(window)
        self.logger.debug(f"Added window: {window.name}")
        self.__update_widgets_of_window(window)
        return True

    def create_new_window(self, window_name: str, window_id: str = "") -> Window:
        """
        Create a new window and add it to the collection.

        Args:
            window_name: Name of the window
            window_id: Optional window ID

        Returns:
            The created window
        """
        window = Window(window_name)

        # Set window type and ID
        if window_name == "android.view.Menu":
            window.type = WindowType.OPTIONSMENU

        if window_id:
            window.id = window_id

        self.add_window(window)
        self.logger.debug(f"Created new window: {window_name} (ID: {window_id or 'not set'})")
        return window

    def __update_widgets_of_window(self, window: Window):
        """
        Update the global widgets dictionary with widgets from a window.

        Args:
            window: Window containing widgets to update
        """
        for widget_id, widget in window.widgets.items():
            self.logger.debug(f"Adding widget {widget.id} from window {window.name}")
            self.widgets[widget.id] = widget

    def get_window_by_id(self, window_id: str) -> Optional[Window]:
        """
        Retrieve a window by its ID.

        Args:
            window_id: Window ID to look for

        Returns:
            Window if found, None otherwise
        """
        return next((w for w in self.windows if w.id == window_id), None)

    def get_window(self, window_name: str) -> Optional[Window]:
        """
        Retrieve a window by its name.

        Args:
            window_name: Window name to look for

        Returns:
            Window if found, None otherwise
        """
        return next((w for w in self.windows if w.name == window_name), None)

    def add_widget(self, window: Window, widget: Widget) -> bool:
        """
        Add a widget to a window if it doesn't already exist.

        Args:
            window: Window to add widget to
            widget: Widget to add

        Returns:
            True if widget was added, False if already exists
        """
        if window.add_widget(widget):
            self.widgets[widget.id] = widget
            self.logger.debug(f"Added widget {widget.id} to window {window.name}")
            return True

        self.logger.debug(f"Widget {widget.id} already exists in window {window.name}")
        return False

    def get_widget(self, widget_id: str) -> Optional[Widget]:
        """
        Retrieve a widget by its ID.

        Args:
            widget_id: Widget ID to look for

        Returns:
            Widget if found, None otherwise
        """
        widget = self.widgets.get(widget_id)

        if widget:
            self.logger.debug(f"Found widget {widget_id}")
        else:
            self.logger.debug(f"Widget {widget_id} not found")

        return widget

    def to_json(self):
        """
        Convert all windows to JSON format.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "windows": [window.to_json() for window in self.windows]
        }

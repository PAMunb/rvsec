"""
Window and screen models for Android application UI analysis.

This module provides validated data models for representing Android application
windows, screens, and their associated UI components for comprehensive UI analysis.
"""

from enum import Enum
from typing import Optional, Dict, Set, List, Any
from pydantic import Field

from rv_android_core.domain.widget import Widget
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


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


@validated_model(['name'])
class Window(BaseValidatedModel):
    """
    Validated data model for Android application window representation.
    
    This model provides comprehensive representation of Android application windows
    or screens with their associated UI widgets and metadata for static analysis
    and dynamic exploration.
    
    ### Architectural Role:
    - Represents individual screens or activities in Android applications
    - Aggregates UI widgets and their interaction capabilities
    - Provides window-level metadata for navigation and exploration
    - Enables correlation between static analysis and dynamic exploration data
    
    ### Integration Points:
    - Created during static analysis of application UI structure
    - Used by window transition graph for navigation modeling
    - Consumed by exploration tools for systematic UI interaction
    - Integrated with coverage analysis for screen-level metrics
    
    ### Critical Navigation Data:
    The activity and class_name fields provide essential mapping between
    UI screens and their corresponding Android Activity implementations.
    """
    
    name: str = Field(
        description="Window identifier or screen name"
    )
    id: str = Field(
        default="",
        description="Unique window identifier within the application"
    )
    type: WindowType = Field(
        default=WindowType.ACTIVITY,
        description="Window type classification (Activity, Dialog, Menu, etc.)"
    )
    layout_file: str = Field(
        default="",
        description="Associated layout XML file path from static analysis"
    )
    widgets: Dict[str, Widget] = Field(
        default_factory=dict,
        description="Dictionary mapping widget IDs to Widget instances in this window"
    )
    fields: Set[str] = Field(
        default_factory=set,
        description="Set of data fields or attributes associated with this window"
    )
    activity: str = Field(
        default="",
        description="Android Activity class name associated with this window"
    )
    class_name: str = Field(
        default="",
        description="Fully qualified class name of the Activity implementation"
    )
    
    def model_post_init(self, __context) -> None:
        """Initialize logging after model validation."""
        logging_manager = LoggingManager.get_instance()
        object.__setattr__(self, 'logger', logging_manager.get_logger("rvandroid_core.domain.window.Window", {"window": self.name}))
        self.logger.debug(f"Window created: {self.name}")

    def add_widget(self, widget: Widget) -> bool:
        """
        Add a widget to the window if it doesn't already exist.

        Args:
            widget: Widget to add

        Returns:
            True if widget was added, False if already exists
        """
        widget_id = str(widget.widget_id)
        if widget_id in self.widgets:
            if hasattr(self, 'logger'):
                self.logger.debug(f"Widget {widget_id} already exists in window {self.name}")
            return False

        self.widgets[widget_id] = widget
        if hasattr(self, 'logger'):
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
        if hasattr(self, 'logger'):
            self.logger.debug(f"Getting widget {widget_id} from window {self.name}")
        widget = self.widgets.get(widget_id)

        if widget:
            if hasattr(self, 'logger'):
                self.logger.debug(f"Widget {widget_id} found")
            return widget

        if hasattr(self, 'logger'):
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
        if hasattr(self, 'logger'):
            self.logger.debug(f"Looking for widget '{widget_name}' in window {self.name}")

        for widget in self.widgets.values():
            if widget.name == widget_name:
                if hasattr(self, 'logger'):
                    self.logger.debug(f"Widget '{widget_name}' found")
                return widget

        if hasattr(self, 'logger'):
            self.logger.debug(f"Widget '{widget_name}' not found")
        return None
        
    def get_widgets(self) -> List[Widget]:
        """
        Get all widgets associated with this window.
        
        Returns:
            List of all widgets in this window
        """
        if hasattr(self, 'logger'):
            self.logger.debug(f"Getting all widgets for window {self.name}, found {len(self.widgets)}")
        return list(self.widgets.values())

    def to_json(self) -> Dict[str, Any]:
        """
        Convert window to JSON format.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "id": self.id,
            "name": self.name,
            "activity": self.activity, 
            "class_name": self.class_name,
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


class Windows(BaseValidatedModel):
    """
    Validated data model for managing all application windows and UI widgets.
    
    This model provides centralized management of Android application windows
    and their associated widgets for comprehensive UI analysis and exploration.
    
    ### Architectural Role:
    - Provides centralized repository for all application windows
    - Aggregates widgets across all windows for global UI analysis
    - Enables efficient window and widget lookup operations
    - Supports comprehensive UI structure analysis and reporting
    
    ### Integration Points:
    - Populated during static analysis of application UI structure
    - Used by window transition graph for complete UI modeling
    - Consumed by exploration tools for systematic UI navigation
    - Integrated with coverage systems for application-wide UI metrics
    
    ### Performance Considerations:
    Maintains both window-specific and global widget collections for
    efficient access patterns during analysis and exploration operations.
    """
    
    windows: Set[Window] = Field(
        default_factory=set,
        description="Set of all windows in the application"
    )
    widgets: Dict[str, Widget] = Field(
        default_factory=dict,
        description="Global dictionary mapping widget IDs to Widget instances across all windows"
    )
    
    def model_post_init(self, __context) -> None:
        """Initialize logging after model validation."""
        logging_manager = LoggingManager.get_instance()
        object.__setattr__(self, 'logger', logging_manager.get_logger("rvandroid_core.domain.window.Windows"))
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
            if hasattr(self, 'logger'):
                self.logger.debug(f"Window {window.name} already exists")
            return False

        self.windows.add(window)
        if hasattr(self, 'logger'):
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
        elif window.type == WindowType.ACTIVITY:
            # If it's an Activity, the window name is usually the fully qualified class name
            window.activity = window_name
            window.class_name = window_name
        
        # Set activity name if it appears to be an Android component
        if "Activity" in window_name or window_name.startswith("com.") or window_name.startswith("android."):
            window.activity = window_name
            window.class_name = window_name

        if window_id:
            window.id = window_id

        self.add_window(window)
        if hasattr(self, 'logger'):
            self.logger.debug(f"Created new window: {window_name} (ID: {window_id or 'not set'})")
        return window

    def __update_widgets_of_window(self, window: Window):
        """
        Update the global widgets dictionary with widgets from a window.

        Args:
            window: Window containing widgets to update
        """
        for widget_id, widget in window.widgets.items():
            if hasattr(self, 'logger'):
                self.logger.debug(f"Adding widget {widget.widget_id} from window {window.name}")
            self.widgets[widget.widget_id] = widget

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

        Supports both exact matching and partial matching for relative Android
        activity names (e.g., ".TutorialActivity" matches
        "com.example.app.TutorialActivity").

        Args:
            window_name: Window name to look for (can be relative or absolute)

        Returns:
            Window if found, None otherwise
        """
        # Strategy 1: Exact match
        result = next((w for w in self.windows if w.name == window_name), None)
        if result:
            return result

        # Strategy 2: Relative name match (e.g., ".TutorialActivity" or ".tutorial.TutorialActivity")
        # Android uses relative activity names starting with '.'
        if window_name.startswith('.'):
            result = next((w for w in self.windows if w.name.endswith(window_name)), None)
            if result:
                return result

        # Strategy 3: Match by activity class name (last part)
        # e.g., "TutorialActivity" matches "com.example.app.tutorial.TutorialActivity"
        class_name = window_name.split('.')[-1] if '.' in window_name else window_name
        if class_name:
            result = next((w for w in self.windows if w.name.endswith(class_name)), None)
            if result:
                return result

        return None

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
            self.widgets[widget.widget_id] = widget
            if hasattr(self, 'logger'):
                self.logger.debug(f"Added widget {widget.widget_id} to window {window.name}")
            return True

        if hasattr(self, 'logger'):
            self.logger.debug(f"Widget {widget.widget_id} already exists in window {window.name}")
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
            if hasattr(self, 'logger'):
                self.logger.debug(f"Found widget {widget_id}")
        else:
            if hasattr(self, 'logger'):
                self.logger.debug(f"Widget {widget_id} not found")

        return widget
        
    def get_windows(self) -> Set[Window]:
        """
        Get all windows.
        
        Returns:
            Set of all windows
        """
        if hasattr(self, 'logger'):
            self.logger.debug(f"Getting all windows, found {len(self.windows)}")
        return self.windows

    def to_json(self) -> Dict[str, Any]:
        """
        Convert all windows to JSON format.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "windows": [window.to_json() for window in self.windows]
        }
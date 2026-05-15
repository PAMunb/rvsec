"""
Widget and UI element models for Android application analysis.

This module provides validated data models for representing Android UI widgets,
their events, and associated metadata from static analysis and dynamic exploration.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import Field
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


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
    BACK = 12
    RESTART = 13
    OTHER = 14


@validated_model(["event_type", "clazz", "method", "signature"])
class WidgetEvent(BaseValidatedModel):
    """
    Validated data model for widget interaction events.

    This model represents user interaction events with UI widgets and their
    associated callback methods for comprehensive UI analysis.

    ### Architectural Role:
    - Maps UI events to application code execution paths
    - Provides structured representation of widget interaction capabilities
    - Enables correlation between UI elements and monitored methods
    - Supports comprehensive UI coverage analysis and testing

    ### Integration Points:
    - Created during static analysis of UI event handlers
    - Used by widget exploration for interaction simulation
    - Consumed by coverage analysis for UI-to-code mapping
    - Integrated with monitoring systems for event tracking
    """

    event_type: WidgetEventType = Field(
        alias="type",
        description="Type of user interaction event (click, long_click, etc.)",
    )
    clazz: str = Field(
        description="Fully qualified class name containing the event handler method"
    )
    method: str = Field(description="Method name that handles this widget event")
    signature: str = Field(
        description="Complete method signature including parameters and return type"
    )

    @property
    def type(self) -> WidgetEventType:
        """Compatibility property for accessing event_type."""
        return self.event_type

    def to_json(self):
        """
        Convert event to JSON format.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {"type": self.type.name, "signature": self.signature}

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
        return (
            f"WidgetEvent=[type={self.type}, clazz={self.clazz}, "
            f"method={self.method}, signature={self.signature}]"
        )

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
    def from_string(type_str: str) -> "WidgetType":
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
    def from_class_name(class_name: str) -> "WidgetType":
        """
        Convert a class name to corresponding WidgetType.

        Args:
            class_name: Full class name

        Returns:
            Corresponding WidgetType enum value
        """
        return next(
            (wt for wt in WidgetType if wt.value == class_name), WidgetType.OTHER
        )


@validated_model(["widget_id", "name", "widget_type"])
class Widget(BaseValidatedModel):
    """
    Validated data model for Android UI widget representation.

    This model provides comprehensive representation of Android UI elements
    with their properties, events, and associated handlers for static analysis
    and dynamic exploration integration.

    ### Architectural Role:
    - Provides structured representation of Android UI components
    - Maps UI elements to event handlers and callback methods
    - Enables correlation between UI interactions and monitored operations
    - Supports comprehensive UI coverage analysis and exploration optimization

    ### Integration Points:
    - Created during static analysis of application UI structure
    - Used by exploration tools for systematic UI interaction
    - Consumed by coverage analysis for UI-to-code correlation
    - Integrated with monitoring systems for interaction tracking

    ### Critical UI Analysis Data:
    The reaches_mop and directly_reaches_mop fields provide essential information
    for prioritizing UI elements during exploration based on their potential
    to trigger monitored operations and security-relevant code paths.
    """

    widget_id: str = Field(
        alias="id",
        description="Unique identifier for the widget within the application",
    )
    name: str = Field(description="Human-readable name or label of the widget")
    widget_type: WidgetType = Field(
        alias="type", description="Android widget type classification"
    )
    text: str = Field(
        default="", description="Visible text content displayed by the widget"
    )
    hint: str = Field(
        default="", description="Hint text or placeholder content for input widgets"
    )
    field: str = Field(
        default="", description="Associated data field or attribute name"
    )
    input_type: str = Field(
        default="", description="Input type specification for text input widgets"
    )
    resource_id: str = Field(
        default="", description="Android resource identifier from layout XML"
    )
    class_name: str = Field(
        default="",
        description="Fully qualified class name of the widget implementation",
    )
    entries: List[str] = Field(
        default_factory=list,
        description="List of predefined entries for selection widgets",
    )
    prompt: Optional[str] = Field(
        default=None,
        description=(
            "Resolved value of android:prompt (Spinner dialog title). "
            "None when the attribute is absent from the layout XML."
        ),
    )
    spinner_mode: Optional[str] = Field(
        default=None,
        description=(
            "Resolved value of android:spinnerMode ('dropdown' | 'dialog'). "
            "None when the attribute is absent from the layout XML."
        ),
    )
    content_description: Optional[str] = Field(
        default=None,
        description=(
            "Resolved value of android:contentDescription (accessibility "
            "label). None when the attribute is absent."
        ),
    )
    tooltip_text: Optional[str] = Field(
        default=None,
        description=(
            "Resolved value of android:tooltipText (long-press hint). "
            "None when the attribute is absent."
        ),
    )
    events: Set[WidgetEvent] = Field(
        default_factory=set,
        description="Set of interaction events supported by this widget",
    )
    handlers: List[str] = Field(
        default_factory=list,
        description="List of event handler method signatures associated with the widget",
    )
    reaches_mop: bool = Field(
        default=False,
        description="Whether this widget can trigger paths to monitored operations",
    )
    directly_reaches_mop: bool = Field(
        default=False,
        description="Whether this widget directly invokes monitored operations",
    )

    @property
    def id(self) -> str:
        """Compatibility property for accessing widget_id."""
        return self.widget_id

    @property
    def type(self) -> WidgetType:
        """Compatibility property for accessing widget_type."""
        return self.widget_type

    def model_post_init(self, __context) -> None:
        """Initialize logging after model validation."""
        logging_manager = LoggingManager.get_instance()
        object.__setattr__(
            self,
            "logger",
            logging_manager.get_logger(
                "rv_android_core.domain.widget",
                {"widget_id": self.widget_id, "widget_type": self.widget_type.name},
            ),
        )
        self.logger.debug(f"Widget created: {self.name or self.widget_id}")

    def add_event(self, event: WidgetEvent) -> bool:
        """
        Add a new event if it doesn't already exist.

        Args:
            event: Event to add

        Returns:
            True if event was added, False if it already exists
        """
        if event in self.events:
            if hasattr(self, "logger"):
                self.logger.debug(
                    f"Event '{event.signature}' already exists for widget {self.widget_id}"
                )
            return False

        if hasattr(self, "logger"):
            self.logger.debug(
                f"Adding event '{event.signature}' to widget {self.widget_id}"
            )
        self.events.add(event)
        return True

    def to_json(self) -> Dict[str, Any]:
        """
        Convert widget to JSON format.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "id": self.widget_id,
            "type": self.widget_type.name,
            "name": self.name,
            "text": self.text,
            "hint": self.hint,
            "field": self.field,
            "input_type": self.input_type,
            "resource_id": self.resource_id,
            "class_name": self.class_name,
            "entries": self.entries,
            "events": [event.to_json() for event in self.events],
            "handlers": self.handlers,
            "reaches_mop": self.reaches_mop,
            "directly_reaches_mop": self.directly_reaches_mop,
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
            return self.widget_id == value.widget_id
        return False

    def __hash__(self):
        """
        Get hash value for this widget.

        Returns:
            Hash value based on id
        """
        return hash(self.widget_id)

    def __str__(self):
        """
        Get string representation of this widget.

        Returns:
            String representation
        """
        return f"Widget=[id={self.widget_id}, type={self.widget_type}, name={self.name}, text={self.text}, hint={self.hint}, field={self.field}, input_type={self.input_type}, entries={self.entries}, events={self.events}]"

    def __repr__(self):
        """
        Get representation string for this widget.

        Returns:
            Representation string
        """
        return f"{self.widget_id}"

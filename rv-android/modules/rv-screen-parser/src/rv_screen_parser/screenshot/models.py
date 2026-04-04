#!/usr/bin/env python3
"""
Screenshot analysis data models for the RV-Android framework.

This module defines Pydantic models for structured representation of screenshot
analysis results, replacing generic dictionary structures with strongly typed
classes that provide validation and enhanced IDE support.

### Architectural Decisions:
- Uses BaseValidatedModel for consistency with framework patterns
- Implements comprehensive validation for coordinate and confidence data
- Provides specialized models for different UI element types
- Maintains serialization compatibility through built-in Pydantic methods
- Follows established error handling patterns through specific exceptions

### Role in the System:
- Provides type-safe data structures for screenshot analysis components
- Enables robust validation of visual element detection results
- Facilitates reliable data exchange between analysis and complementor components
- Supports comprehensive error detection and validation reporting
"""

from enum import Enum
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVValidationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation.base import BaseValidatedModel


class DetectionMethod(str, Enum):
    """Enumeration of detection methods used for UI element identification."""

    SHAPE = "shape"
    SHAPE_WITH_TEXT = "shape_with_text"
    TEXT = "text"
    COLOR = "color"
    ICON = "icon"
    DIALOG = "dialog"
    DIALOG_TEXT = "dialog_text"
    TOAST = "toast"
    VALIDATION = "validation"
    PATTERN = "pattern"
    GRID = "grid"


class InteractiveElementType(str, Enum):
    """Enumeration of interactive element types detected in game UIs."""

    JOYSTICK = "joystick"
    SLIDER_HORIZONTAL = "slider_horizontal"
    SLIDER_VERTICAL = "slider_vertical"
    SLIDER = "slider"  # Generic slider
    GRID_CELL = "grid_cell"
    DPAD = "dpad"
    DPAD_BUTTON_0 = "dpad_button_0"
    DPAD_BUTTON_1 = "dpad_button_1"
    DPAD_BUTTON_2 = "dpad_button_2"
    DPAD_BUTTON_3 = "dpad_button_3"
    SWITCH = "switch"
    NAVIGATION = "navigation"
    CLICKABLE = "clickable"
    INPUT_FIELD = "input_field"
    # Board game elements (generic for chess, checkers, ludo, etc.)
    BOARD_GAME_PIECE = "board_game_piece"
    BOARD_GAME_POSITION = "board_game_position"


class ErrorType(str, Enum):
    """Enumeration of error indicator types for classification."""

    GENERAL_ERROR = "general_error"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"
    UI_ERROR = "ui_error"
    CRITICAL_ERROR = "critical_error"
    WARNING = "warning"
    INFO = "info"
    ALERT = "alert"
    VISUAL_INDICATOR = "visual_indicator"
    COLOR_ERROR = "color_error"
    TEXT_GENERAL_ERROR = "text_general_error"
    TEXT_NETWORK_ERROR = "text_network_error"
    TEXT_PERMISSION_ERROR = "text_permission_error"
    TEXT_VALIDATION_ERROR = "text_validation_error"
    TEXT_SYSTEM_ERROR = "text_system_error"
    ICON_ERROR = "icon_error"
    DIALOG_ERROR = "dialog_error"
    DIALOG_TEXT_ERROR = "dialog_text_error"
    TOAST_NOTIFICATION = "toast_notification"
    UNKNOWN_ERROR = "unknown_error"


class IconType(str, Enum):
    """Enumeration of icon types for visual error indicators."""

    ERROR_CIRCLE = "error_circle"
    INFO_CIRCLE = "info_circle"
    GENERIC_CIRCLE = "generic_circle"
    WARNING_TRIANGLE = "warning_triangle"
    GENERIC_TRIANGLE = "generic_triangle"
    EXCLAMATION_MARK = "exclamation_mark"
    X_MARK = "x_mark"


class ImageDimensions(BaseValidatedModel):
    """
    Model representing image dimensions with validation.

    Provides structured representation of screenshot dimensions with
    automatic validation of positive integer values.
    """

    width: int = Field(..., gt=0, description="Image width in pixels")
    height: int = Field(..., gt=0, description="Image height in pixels")

    @field_validator("width", "height")
    @classmethod
    def validate_positive_dimensions(cls, v):
        """Ensure dimensions are positive integers."""
        if v <= 0:
            raise RVValidationError(
                f"Image dimension must be positive, got {v}", field_name="dimensions"
            )
        return v


class BoundingBox(BaseValidatedModel):
    """
    Model representing rectangular bounding box coordinates.

    Provides structured coordinate representation with validation
    for UI element positioning and size constraints.
    """

    x: int = Field(..., ge=0, description="Left coordinate in pixels")
    y: int = Field(..., ge=0, description="Top coordinate in pixels")
    width: int = Field(..., gt=0, description="Width in pixels")
    height: int = Field(..., gt=0, description="Height in pixels")

    @field_validator("width", "height")
    @classmethod
    def validate_positive_size(cls, v):
        """Ensure width and height are positive."""
        if v <= 0:
            raise RVValidationError(
                f"Bounding box size must be positive, got {v}",
                field_name="bounding_box",
            )
        return v

    @property
    def area(self) -> int:
        """Calculate bounding box area."""
        return self.width * self.height

    @property
    def center_x(self) -> int:
        """Calculate center X coordinate."""
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        """Calculate center Y coordinate."""
        return self.y + self.height // 2

    @property
    def right(self) -> int:
        """Calculate right boundary coordinate."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Calculate bottom boundary coordinate."""
        return self.y + self.height


class DetectedText(BaseValidatedModel):
    """
    Model representing text elements detected through OCR analysis.

    Captures text content with confidence metrics and contextual flags
    for button-like and error-like text identification.
    """

    text: str = Field(..., min_length=1, description="Detected text content")
    confidence: int = Field(..., ge=0, le=100, description="OCR confidence percentage")
    bbox: BoundingBox = Field(..., description="Text bounding box coordinates")
    is_button_like: bool = Field(
        default=False, description="Text appears to be button label"
    )
    is_error_like: bool = Field(
        default=False, description="Text appears to be error message"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, v):
        """Ensure confidence is within valid percentage range."""
        if not 0 <= v <= 100:
            raise RVValidationError(
                f"Confidence must be between 0 and 100, got {v}",
                field_name="confidence",
            )
        return v

    @field_validator("text")
    @classmethod
    def validate_non_empty_text(cls, v):
        """Ensure text content is not empty or whitespace only."""
        if not v or not v.strip():
            raise RVValidationError(
                "Text content cannot be empty or whitespace only", field_name="text"
            )
        return v.strip()


class DetectedButton(BaseValidatedModel):
    """
    Model representing button elements detected through visual analysis.

    Captures button positioning, detection confidence, and associated
    text content when available.
    """

    x: int = Field(..., ge=0, description="Button left coordinate")
    y: int = Field(..., ge=0, description="Button top coordinate")
    width: int = Field(..., gt=0, description="Button width")
    height: int = Field(..., gt=0, description="Button height")
    area: float = Field(..., gt=0, description="Button area in pixels")
    aspect_ratio: float = Field(..., gt=0, description="Width to height ratio")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    detection_method: DetectionMethod = Field(
        ..., description="Method used for detection"
    )
    text: Optional[str] = Field(None, description="Button text if available")

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, v):
        """Ensure aspect ratio is positive."""
        if v <= 0:
            raise RVValidationError(
                f"Aspect ratio must be positive, got {v}", field_name="aspect_ratio"
            )
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence_bounds(cls, v):
        """Ensure confidence is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise RVValidationError(
                f"Confidence must be between 0.0 and 1.0, got {v}",
                field_name="confidence",
            )
        return v

    @property
    def bbox(self) -> BoundingBox:
        """Get button bounding box."""
        return BoundingBox(x=self.x, y=self.y, width=self.width, height=self.height)


class ErrorIndicator(BaseValidatedModel):
    """
    Model representing error indicators detected in the UI.

    Captures error positioning, classification, and associated metadata
    for different types of error visual cues.
    """

    x: int = Field(..., ge=0, description="Error indicator left coordinate")
    y: int = Field(..., ge=0, description="Error indicator top coordinate")
    width: int = Field(..., gt=0, description="Error indicator width")
    height: int = Field(..., gt=0, description="Error indicator height")
    detection_method: DetectionMethod = Field(..., description="Detection method used")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    error_type: ErrorType = Field(..., description="Classified error type")

    # Optional fields based on detection method
    text: Optional[str] = Field(None, description="Error message text")
    area: Optional[float] = Field(None, gt=0, description="Error indicator area")
    red_dominance: Optional[float] = Field(
        None, ge=0, description="Red color dominance ratio"
    )
    circularity: Optional[float] = Field(
        None, ge=0, le=2.0, description="Shape circularity measure"
    )
    icon_type: Optional[IconType] = Field(
        None, description="Icon type for icon-based errors"
    )
    error_category: Optional[str] = Field(
        None, description="Error category classification"
    )

    # Dialog-specific fields
    centering: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Dialog centering measure"
    )
    contains_texts: Optional[int] = Field(
        None, ge=0, description="Number of contained texts"
    )
    contains_error_texts: Optional[int] = Field(
        None, ge=0, description="Number of error texts"
    )
    contains_buttons: Optional[int] = Field(
        None, ge=0, description="Number of contained buttons"
    )
    parent_dialog: Optional[int] = Field(
        None, ge=0, description="Reference to parent dialog"
    )

    # Validation-specific fields
    field_x: Optional[int] = Field(
        None, ge=0, description="Associated form field X coordinate"
    )
    field_y: Optional[int] = Field(
        None, ge=0, description="Associated form field Y coordinate"
    )
    field_width: Optional[int] = Field(
        None, gt=0, description="Associated form field width"
    )
    field_height: Optional[int] = Field(
        None, gt=0, description="Associated form field height"
    )

    # Toast-specific fields
    contains_error_text: Optional[bool] = Field(
        None, description="Contains error text flag"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence_bounds(cls, v):
        """Ensure confidence is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise RVValidationError(
                f"Confidence must be between 0.0 and 1.0, got {v}",
                field_name="confidence",
            )
        return v

    @property
    def bbox(self) -> BoundingBox:
        """Get error indicator bounding box."""
        return BoundingBox(x=self.x, y=self.y, width=self.width, height=self.height)


class InteractiveElement(BaseValidatedModel):
    """
    Model representing interactive elements detected in game UIs.

    Captures game-specific UI elements like joysticks, sliders, and
    D-pad controls with their geometric and behavioral properties.
    """

    x: int = Field(..., ge=0, description="Element left coordinate")
    y: int = Field(..., ge=0, description="Element top coordinate")
    width: int = Field(..., gt=0, description="Element width")
    height: int = Field(..., gt=0, description="Element height")
    type: InteractiveElementType = Field(..., description="Type of interactive element")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    detection_method: DetectionMethod = Field(..., description="Detection method used")

    # Optional type-specific fields
    circularity: Optional[float] = Field(
        None, ge=0, le=2.0, description="Shape circularity for joysticks"
    )
    aspect_ratio: Optional[float] = Field(
        None, gt=0, description="Width to height ratio"
    )
    button_count: Optional[int] = Field(
        None, ge=0, description="Number of buttons for D-pad"
    )
    parent_dpad: Optional[int] = Field(
        None, ge=0, description="Reference to parent D-pad"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence_bounds(cls, v):
        """Ensure confidence is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise RVValidationError(
                f"Confidence must be between 0.0 and 1.0, got {v}",
                field_name="confidence",
            )
        return v

    @property
    def bbox(self) -> BoundingBox:
        """Get interactive element bounding box."""
        return BoundingBox(x=self.x, y=self.y, width=self.width, height=self.height)


class ScreenshotAnalysisResult(BaseValidatedModel):
    """
    Comprehensive model for screenshot analysis results.

    ### Architectural Role:
    This model serves as the primary data structure for screenshot analysis
    results, replacing the previous dataclass implementation with type-safe
    Pydantic validation and serialization capabilities.

    ### Design Decisions:
    - Uses strongly typed lists instead of generic Dict[str, Any] structures
    - Implements comprehensive validation for all coordinate and confidence data
    - Maintains backward compatibility through JSON serialization methods
    - Provides computed properties for common analysis metrics
    - Integrates with framework error handling patterns

    ### Integration Points:
    - Used by ScreenshotAnalyzer for result generation
    - Consumed by ScreenshotActionComplementor for UI element association
    - Processed by state enrichment components for prompt generation
    """

    image_path: str = Field(
        ..., min_length=1, description="Path to analyzed screenshot"
    )
    dimensions: ImageDimensions = Field(
        default_factory=lambda: ImageDimensions(width=0, height=0),
        description="Screenshot dimensions",
    )
    texts: List[DetectedText] = Field(
        default_factory=list, description="Detected text elements"
    )
    buttons: List[DetectedButton] = Field(
        default_factory=list, description="Detected button elements"
    )
    error_indicators: List[ErrorIndicator] = Field(
        default_factory=list, description="Detected error indicators"
    )
    interactive_elements: List[InteractiveElement] = Field(
        default_factory=list, description="Detected interactive elements"
    )
    processing_time: float = Field(
        default=0.0, ge=0.0, description="Analysis processing time in seconds"
    )
    success: bool = Field(default=True, description="Analysis success flag")
    error_message: str = Field(
        default="", description="Error message if analysis failed"
    )

    @field_validator("image_path")
    @classmethod
    def validate_image_path(cls, v):
        """Ensure image path is not empty."""
        if not v or not v.strip():
            raise RVValidationError(
                "Image path cannot be empty", field_name="image_path"
            )
        return v.strip()

    @field_validator("processing_time")
    @classmethod
    def validate_processing_time(cls, v):
        """Ensure processing time is non-negative."""
        if v < 0:
            raise RVValidationError(
                f"Processing time cannot be negative, got {v}",
                field_name="processing_time",
            )
        return v

    @model_validator(mode="after")
    def validate_error_state(self):
        """Validate consistency between success flag and error message."""
        if not self.success and not self.error_message.strip():
            raise RVValidationError(
                "Error message must be provided when success is False",
                field_name="error_message",
            )

        return self

    def to_json(self) -> str:
        """
        Convert the result to a JSON string for backward compatibility.

        This method maintains compatibility with existing code that expects
        JSON serialization of analysis results.

        Returns:
            JSON string representation of the analysis result
        """
        try:
            # Use Pydantic's built-in JSON serialization
            return self.model_dump_json(exclude_unset=False)
        except Exception as e:
            # Log error and raise appropriate exception
            error_handler = ErrorHandler.get_instance()
            error = RVValidationError(
                f"Failed to serialize ScreenshotAnalysisResult to JSON: {str(e)}",
                field_name="serialization",
            )
            error_handler.handle_error(
                error,
                context={
                    "component": "ScreenshotAnalysisResult",
                    "method": "to_json",
                    "image_path": self.image_path,
                },
            )
            raise error

    @property
    def total_elements(self) -> int:
        """Get total count of all detected elements."""
        return (
            len(self.texts)
            + len(self.buttons)
            + len(self.error_indicators)
            + len(self.interactive_elements)
        )

    @property
    def has_errors(self) -> bool:
        """Check if any error indicators were detected."""
        return len(self.error_indicators) > 0

    @property
    def high_confidence_elements(self) -> int:
        """Count elements with high detection confidence (>= 0.8)."""
        count = 0
        count += sum(1 for btn in self.buttons if btn.confidence >= 0.8)
        count += sum(1 for err in self.error_indicators if err.confidence >= 0.8)
        count += sum(1 for elem in self.interactive_elements if elem.confidence >= 0.8)
        return count

    @property
    def text_confidence_average(self) -> float:
        """Calculate average confidence of detected text elements."""
        if not self.texts:
            return 0.0
        return sum(text.confidence for text in self.texts) / len(self.texts)


# Error handling setup for screenshot analysis models
def _setup_screenshot_model_error_handlers():
    """
    Register error handlers for screenshot analysis model validation.

    This function sets up specialized error handling for validation errors
    that may occur during screenshot analysis model creation and processing.
    """
    error_handler = ErrorHandler.get_instance()
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger(
        "screenshot.models", {CONTEXT_COMPONENT: "ScreenshotModels"}
    )

    @ErrorHandler.handle_errors(component="ScreenshotModels", phase="validation")
    def handle_screenshot_validation_error(
        error: RVValidationError, context: dict
    ) -> bool:
        """Handle validation errors in screenshot analysis models."""
        logger.error(f"Screenshot model validation error: {error.message}")
        if hasattr(error, "field_name") and error.field_name:
            logger.error(f"Invalid field: {error.field_name}")
        return True

    # Register the handler
    error_handler.register_handler(
        RVValidationError, handle_screenshot_validation_error
    )
    logger.debug("Registered screenshot model error handlers")


# Initialize error handlers when module is imported
_setup_screenshot_model_error_handlers()

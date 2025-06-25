#!/usr/bin/env python3
"""
Conversion utilities for screenshot analysis data structures.

This module provides conversion functions to transform legacy dictionary-based
data structures into the new Pydantic models, facilitating migration from
the old ScreenshotAnalysisResult dataclass implementation.

### Architectural Role:
- Provides seamless migration path from dictionary-based structures
- Enables gradual adoption of new type-safe models
- Handles data validation and error reporting during conversion
- Maintains compatibility with existing analysis pipelines

### Design Decisions:
- Implements defensive programming with comprehensive error handling
- Uses framework error handling patterns for consistent error reporting
- Provides detailed validation feedback for debugging migration issues
- Supports both individual element and batch conversion operations
"""

from typing import Dict, List, Any, Optional, Union
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.exceptions import RVValidationError, RVParsingError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

from .models import (
    ImageDimensions, BoundingBox, DetectedText, DetectedButton,
    ErrorIndicator, InteractiveElement, ScreenshotAnalysisResult,
    DetectionMethod, InteractiveElementType, ErrorType, IconType
)


class ScreenshotDataConverter:
    """
    Converter class for transforming legacy screenshot analysis data.
    
    Provides methods to convert dictionary-based analysis results into
    strongly typed Pydantic models with comprehensive validation and
    error handling.
    """
    
    def __init__(self):
        """Initialize the converter with logging and error handling."""
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "screenshot.converters",
            {CONTEXT_COMPONENT: "ScreenshotDataConverter"}
        )
        self.error_handler = ErrorHandler.get_instance()
    
    @ErrorHandler.handle_errors(component="ScreenshotDataConverter", phase="conversion")
    def convert_dimensions(self, dimensions_dict: Dict[str, int]) -> ImageDimensions:
        """
        Convert legacy dimensions dictionary to ImageDimensions model.
        
        Args:
            dimensions_dict: Dictionary containing 'width' and 'height' keys
            
        Returns:
            ImageDimensions model instance
            
        Raises:
            RVValidationError: If dimensions data is invalid
        """
        try:
            return ImageDimensions(
                width=dimensions_dict.get('width', 0),
                height=dimensions_dict.get('height', 0)
            )
        except Exception as e:
            raise RVValidationError(
                f"Failed to convert dimensions: {str(e)}",
                field_name="dimensions"
            ) from e
    
    @ErrorHandler.handle_errors(component="ScreenshotDataConverter", phase="conversion")
    def convert_bounding_box(self, bbox_dict: Dict[str, int]) -> BoundingBox:
        """
        Convert legacy bounding box dictionary to BoundingBox model.
        
        Args:
            bbox_dict: Dictionary containing 'x', 'y', 'width', 'height' keys
            
        Returns:
            BoundingBox model instance
            
        Raises:
            RVValidationError: If bounding box data is invalid
        """
        try:
            return BoundingBox(
                x=bbox_dict.get('x', 0),
                y=bbox_dict.get('y', 0),
                width=bbox_dict.get('width', 0),
                height=bbox_dict.get('height', 0)
            )
        except Exception as e:
            raise RVValidationError(
                f"Failed to convert bounding box: {str(e)}",
                field_name="bounding_box"
            ) from e
    
    @ErrorHandler.handle_errors(component="ScreenshotDataConverter", phase="conversion")
    def convert_text_element(self, text_dict: Dict[str, Any]) -> DetectedText:
        """
        Convert legacy text element dictionary to DetectedText model.
        
        Args:
            text_dict: Dictionary containing text element data
            
        Returns:
            DetectedText model instance
            
        Raises:
            RVValidationError: If text element data is invalid
        """
        try:
            bbox_data = text_dict.get('bbox', {})
            bbox = self.convert_bounding_box(bbox_data)
            
            return DetectedText(
                text=text_dict.get('text', ''),
                confidence=text_dict.get('confidence', 0),
                bbox=bbox,
                is_button_like=text_dict.get('is_button_like', False),
                is_error_like=text_dict.get('is_error_like', False)
            )
        except Exception as e:
            raise RVValidationError(
                f"Failed to convert text element: {str(e)}",
                field_name="text_element"
            ) from e
    
    @ErrorHandler.handle_errors(component="ScreenshotDataConverter", phase="conversion")
    def convert_button_element(self, button_dict: Dict[str, Any]) -> DetectedButton:
        """
        Convert legacy button element dictionary to DetectedButton model.
        
        Args:
            button_dict: Dictionary containing button element data
            
        Returns:
            DetectedButton model instance
            
        Raises:
            RVValidationError: If button element data is invalid
        """
        try:
            # Convert detection method string to enum
            detection_method_str = button_dict.get('detection_method', 'shape')
            detection_method = self._convert_detection_method(detection_method_str)
            
            return DetectedButton(
                x=button_dict.get('x', 0),
                y=button_dict.get('y', 0),
                width=button_dict.get('width', 0),
                height=button_dict.get('height', 0),
                area=float(button_dict.get('area', 0)),
                aspect_ratio=float(button_dict.get('aspect_ratio', 1.0)),
                confidence=float(button_dict.get('confidence', 0.0)),
                detection_method=detection_method,
                text=button_dict.get('text')
            )
        except Exception as e:
            raise RVValidationError(
                f"Failed to convert button element: {str(e)}",
                field_name="button_element"
            ) from e
    
    @ErrorHandler.handle_errors(component="ScreenshotDataConverter", phase="conversion")
    def convert_error_indicator(self, error_dict: Dict[str, Any]) -> ErrorIndicator:
        """
        Convert legacy error indicator dictionary to ErrorIndicator model.
        
        Args:
            error_dict: Dictionary containing error indicator data
            
        Returns:
            ErrorIndicator model instance
            
        Raises:
            RVValidationError: If error indicator data is invalid
        """
        try:
            # Convert detection method string to enum
            detection_method_str = error_dict.get('detection_method', 'color')
            detection_method = self._convert_detection_method(detection_method_str)
            
            # Convert error type string to enum
            error_type_str = error_dict.get('error_type', 'unknown_error')
            error_type = self._convert_error_type(error_type_str)
            
            # Convert icon type if present
            icon_type = None
            if 'icon_type' in error_dict:
                icon_type = self._convert_icon_type(error_dict['icon_type'])
            
            return ErrorIndicator(
                x=error_dict.get('x', 0),
                y=error_dict.get('y', 0),
                width=error_dict.get('width', 0),
                height=error_dict.get('height', 0),
                detection_method=detection_method,
                confidence=float(error_dict.get('confidence', 0.0)),
                error_type=error_type,
                text=error_dict.get('text'),
                area=error_dict.get('area'),
                red_dominance=error_dict.get('red_dominance'),
                circularity=error_dict.get('circularity'),
                icon_type=icon_type,
                error_category=error_dict.get('error_category'),
                centering=error_dict.get('centering'),
                contains_texts=error_dict.get('contains_texts'),
                contains_error_texts=error_dict.get('contains_error_texts'),
                contains_buttons=error_dict.get('contains_buttons'),
                parent_dialog=error_dict.get('parent_dialog'),
                field_x=error_dict.get('field_x'),
                field_y=error_dict.get('field_y'),
                field_width=error_dict.get('field_width'),
                field_height=error_dict.get('field_height'),
                contains_error_text=error_dict.get('contains_error_text')
            )
        except Exception as e:
            raise RVValidationError(
                f"Failed to convert error indicator: {str(e)}",
                field_name="error_indicator"
            ) from e
    
    @ErrorHandler.handle_errors(component="ScreenshotDataConverter", phase="conversion")
    def convert_interactive_element(self, element_dict: Dict[str, Any]) -> InteractiveElement:
        """
        Convert legacy interactive element dictionary to InteractiveElement model.
        
        Args:
            element_dict: Dictionary containing interactive element data
            
        Returns:
            InteractiveElement model instance
            
        Raises:
            RVValidationError: If interactive element data is invalid
        """
        try:
            # Convert element type string to enum
            element_type_str = element_dict.get('type', 'joystick')
            element_type = self._convert_interactive_element_type(element_type_str)
            
            # Convert detection method string to enum
            detection_method_str = element_dict.get('detection_method', 'shape')
            detection_method = self._convert_detection_method(detection_method_str)
            
            return InteractiveElement(
                x=element_dict.get('x', 0),
                y=element_dict.get('y', 0),
                width=element_dict.get('width', 0),
                height=element_dict.get('height', 0),
                type=element_type,
                confidence=float(element_dict.get('confidence', 0.0)),
                detection_method=detection_method,
                circularity=element_dict.get('circularity'),
                aspect_ratio=element_dict.get('aspect_ratio'),
                button_count=element_dict.get('button_count'),
                parent_dpad=element_dict.get('parent_dpad')
            )
        except Exception as e:
            raise RVValidationError(
                f"Failed to convert interactive element: {str(e)}",
                field_name="interactive_element"
            ) from e
    
    @ErrorHandler.handle_errors(component="ScreenshotDataConverter", phase="conversion")
    def convert_analysis_result(self, result_data: Dict[str, Any]) -> ScreenshotAnalysisResult:
        """
        Convert complete legacy analysis result to ScreenshotAnalysisResult model.
        
        Args:
            result_data: Dictionary containing complete analysis result data
            
        Returns:
            ScreenshotAnalysisResult model instance
            
        Raises:
            RVParsingError: If analysis result conversion fails
        """
        try:
            self.logger.debug(f"Converting analysis result for image: {result_data.get('image_path', 'unknown')}")
            
            # Convert dimensions
            dimensions_data = result_data.get('dimensions', {})
            dimensions = self.convert_dimensions(dimensions_data)
            
            # Convert text elements
            texts = []
            for text_dict in result_data.get('texts', []):
                try:
                    texts.append(self.convert_text_element(text_dict))
                except Exception as e:
                    self.logger.warning(f"Failed to convert text element: {e}")
                    # Continue processing other elements
            
            # Convert button elements
            buttons = []
            for button_dict in result_data.get('buttons', []):
                try:
                    buttons.append(self.convert_button_element(button_dict))
                except Exception as e:
                    self.logger.warning(f"Failed to convert button element: {e}")
                    # Continue processing other elements
            
            # Convert error indicators
            error_indicators = []
            for error_dict in result_data.get('error_indicators', []):
                try:
                    error_indicators.append(self.convert_error_indicator(error_dict))
                except Exception as e:
                    self.logger.warning(f"Failed to convert error indicator: {e}")
                    # Continue processing other elements
            
            # Convert interactive elements
            interactive_elements = []
            for element_dict in result_data.get('interactive_elements', []):
                try:
                    interactive_elements.append(self.convert_interactive_element(element_dict))
                except Exception as e:
                    self.logger.warning(f"Failed to convert interactive element: {e}")
                    # Continue processing other elements
            
            # Create final result
            result = ScreenshotAnalysisResult(
                image_path=result_data.get('image_path', ''),
                dimensions=dimensions,
                texts=texts,
                buttons=buttons,
                error_indicators=error_indicators,
                interactive_elements=interactive_elements,
                processing_time=float(result_data.get('processing_time', 0.0)),
                success=result_data.get('success', True),
                error_message=result_data.get('error_message', '')
            )
            
            self.logger.debug(f"Successfully converted analysis result with {result.total_elements} elements")
            return result
            
        except Exception as e:
            error = RVParsingError(
                f"Failed to convert screenshot analysis result: {str(e)}",
                parser_type="ScreenshotDataConverter"
            )
            self.error_handler.handle_error(error, context={
                "image_path": result_data.get('image_path', 'unknown'),
                "conversion_phase": "analysis_result"
            })
            raise error from e
    
    def _convert_detection_method(self, method_str: str) -> DetectionMethod:
        """Convert detection method string to enum value."""
        try:
            return DetectionMethod(method_str.lower())
        except ValueError:
            self.logger.warning(f"Unknown detection method: {method_str}, using default")
            return DetectionMethod.SHAPE
    
    def _convert_error_type(self, error_type_str: str) -> ErrorType:
        """Convert error type string to enum value."""
        try:
            return ErrorType(error_type_str.lower())
        except ValueError:
            self.logger.warning(f"Unknown error type: {error_type_str}, using default")
            return ErrorType.UNKNOWN_ERROR
    
    def _convert_icon_type(self, icon_type_str: str) -> IconType:
        """Convert icon type string to enum value."""
        try:
            return IconType(icon_type_str.lower())
        except ValueError:
            self.logger.warning(f"Unknown icon type: {icon_type_str}, using default")
            return IconType.GENERIC_CIRCLE
    
    def _convert_interactive_element_type(self, type_str: str) -> InteractiveElementType:
        """Convert interactive element type string to enum value."""
        try:
            return InteractiveElementType(type_str.lower())
        except ValueError:
            self.logger.warning(f"Unknown interactive element type: {type_str}, using default")
            return InteractiveElementType.JOYSTICK


# Global converter instance for convenient access
_converter = None

def get_converter() -> ScreenshotDataConverter:
    """
    Get the global screenshot data converter instance.
    
    Returns:
        ScreenshotDataConverter instance
    """
    global _converter
    if _converter is None:
        _converter = ScreenshotDataConverter()
    return _converter


# Convenience functions for direct conversion operations

def convert_to_analysis_result(legacy_data: Union[Dict[str, Any], Any]) -> ScreenshotAnalysisResult:
    """
    Convert legacy analysis result data to new ScreenshotAnalysisResult model.
    
    This function handles both dictionary-based legacy data and dataclass instances,
    providing a unified conversion interface for migration scenarios.
    
    Args:
        legacy_data: Legacy analysis result data (dict or dataclass)
        
    Returns:
        ScreenshotAnalysisResult model instance
        
    Raises:
        RVParsingError: If conversion fails
    """
    converter = get_converter()
    
    # Handle dataclass instances by converting to dictionary first
    if hasattr(legacy_data, '__dict__') and not isinstance(legacy_data, dict):
        # Convert dataclass to dictionary
        import dataclasses
        if dataclasses.is_dataclass(legacy_data):
            legacy_data = dataclasses.asdict(legacy_data)
        else:
            # Use object's __dict__ for regular objects
            legacy_data = legacy_data.__dict__
    
    # Ensure we have a dictionary
    if not isinstance(legacy_data, dict):
        raise RVParsingError(
            f"Expected dictionary or dataclass, got {type(legacy_data)}",
            parser_type="ScreenshotDataConverter"
        )
    
    return converter.convert_analysis_result(legacy_data)


def convert_element_list(element_list: List[Dict[str, Any]], 
                        element_type: str) -> List[Union[DetectedText, DetectedButton, 
                                                       ErrorIndicator, InteractiveElement]]:
    """
    Convert a list of legacy element dictionaries to typed model instances.
    
    Args:
        element_list: List of element dictionaries
        element_type: Type of elements ('text', 'button', 'error', 'interactive')
        
    Returns:
        List of converted model instances
        
    Raises:
        RVValidationError: If element type is invalid or conversion fails
    """
    converter = get_converter()
    
    conversion_methods = {
        'text': converter.convert_text_element,
        'button': converter.convert_button_element,
        'error': converter.convert_error_indicator,
        'interactive': converter.convert_interactive_element
    }
    
    if element_type not in conversion_methods:
        raise RVValidationError(
            f"Invalid element type: {element_type}. Must be one of: {list(conversion_methods.keys())}",
            field_name="element_type"
        )
    
    convert_func = conversion_methods[element_type]
    converted_elements = []
    
    for element_dict in element_list:
        try:
            converted_elements.append(convert_func(element_dict))
        except Exception as e:
            converter.logger.warning(f"Failed to convert {element_type} element: {e}")
            # Continue processing remaining elements
    
    return converted_elements
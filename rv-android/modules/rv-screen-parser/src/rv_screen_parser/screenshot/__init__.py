"""
Screenshot analysis module for the RV-Android framework.

This module provides comprehensive screenshot analysis capabilities including
OCR text detection, UI element recognition, error indicator identification,
and interactive element detection for game UIs.

### Key Components:
- models: Pydantic data models for type-safe analysis results
- converters: Utilities for migrating from legacy dictionary structures
- screenshot_analyzer: Core analysis engine for screenshot processing

### Exports:
- ScreenshotAnalysisResult: Main result model for screenshot analysis
- All component models: ImageDimensions, BoundingBox, DetectedText, etc.
- Conversion utilities: convert_to_analysis_result, get_converter
- ScreenshotAnalyzer: Core analysis class
"""

# Import core analysis class
from .screenshot_analyzer import ScreenshotAnalyzer

# Import all Pydantic models
from .models import (
    # Core result model
    ScreenshotAnalysisResult,
    
    # Component models
    ImageDimensions,
    BoundingBox,
    DetectedText,
    DetectedButton,
    ErrorIndicator,
    InteractiveElement,
    
    # Enumerations
    DetectionMethod,
    InteractiveElementType,
    ErrorType,
    IconType
)

# Import conversion utilities
from .converters import (
    ScreenshotDataConverter,
    get_converter,
    convert_to_analysis_result,
    convert_element_list
)

# Define public API
__all__ = [
    # Core classes
    'ScreenshotAnalyzer',
    'ScreenshotAnalysisResult',
    
    # Data models
    'ImageDimensions',
    'BoundingBox', 
    'DetectedText',
    'DetectedButton',
    'ErrorIndicator',
    'InteractiveElement',
    
    # Enumerations
    'DetectionMethod',
    'InteractiveElementType',
    'ErrorType',
    'IconType',
    
    # Conversion utilities
    'ScreenshotDataConverter',
    'get_converter',
    'convert_to_analysis_result',
    'convert_element_list'
]
"""
Detection components for screenshot analysis.

This package provides specialized detector components for different types
of UI elements including text, buttons, error indicators, and interactive
elements found in mobile applications and games.
"""

from .button_detector import ButtonDetector, get_button_detector
from .error_detector import ErrorDetector, get_error_detector
from .interactive_element_detector import (
    InteractiveElementDetector,
    get_interactive_element_detector,
)
from .text_detector import TextDetector, get_text_detector

__all__ = [
    "TextDetector",
    "get_text_detector",
    "ButtonDetector",
    "get_button_detector",
    "ErrorDetector",
    "get_error_detector",
    "InteractiveElementDetector",
    "get_interactive_element_detector",
]

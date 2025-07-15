"""Specialized information fragments for the prompt system.

This package contains specialized information fragments that collect and format
information from various sources for use in prompt generation.
"""

from .monitored_operations_fragment import MonitoredOperationsFragment
from .screenshot_fragment import ScreenshotFragment
from .ui_pattern_fragment import UIPatternFragment

__all__ = [
    "MonitoredOperationsFragment",
    "ScreenshotFragment",
    "UIPatternFragment",
]
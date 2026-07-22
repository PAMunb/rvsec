"""Information layer for the prompt system.

This package provides the information layer components of the prompt system,
which are responsible for collecting and formatting information from various
sources for use in prompt generation.
"""

from .base_fragment import InformationFragment
from .fragment_manager import InformationManager
from .fragments.monitored_operations_fragment import MonitoredOperationsFragment
from .fragments.screenshot_fragment import ScreenshotFragment
from .fragments.ui_pattern_fragment import UIPatternFragment

__all__ = [
    "InformationFragment",
    "InformationManager",
    "MonitoredOperationsFragment",
    "ScreenshotFragment",
    "UIPatternFragment",
]
# rvandroid/analysis/patterns/__init__.py
"""
UI Pattern Detection System for RV-Android.

This module provides a pattern detection system that can identify UI patterns
such as forms, lists, tabs, and navigation elements. These patterns are used
to generate batch actions for more efficient testing.
"""

from rvandroid.analysis.patterns.dialog_detector import DialogDetector
from rvandroid.analysis.patterns.form_detector import FormDetector
from rvandroid.analysis.patterns.list_detector import ListDetector
from rvandroid.analysis.patterns.navigation_detector import NavigationDetector
from rvandroid.analysis.patterns.pattern_data import PatternType, PatternData, PatternResult
from rvandroid.analysis.patterns.pattern_detector import (
    IPatternDetector, BasePatternDetector, PatternDetectorRegistry, UIPatternDetectorManager
)
from rvandroid.analysis.patterns.tab_detector import TabDetector
from rvandroid.analysis.patterns.ui_pattern_utils import UIPatternUtils

# Register all the detectors
PatternDetectorRegistry.register(DialogDetector)
PatternDetectorRegistry.register(FormDetector)
PatternDetectorRegistry.register(ListDetector)
PatternDetectorRegistry.register(NavigationDetector)
PatternDetectorRegistry.register(TabDetector)

__all__ = [
    'PatternType',
    'PatternData',
    'PatternResult',
    'IPatternDetector',
    'BasePatternDetector',
    'UIPatternDetectorManager',
    'DialogDetector',
    'FormDetector',
    'ListDetector',
    'NavigationDetector',
    'TabDetector',
    'UIPatternUtils',
]

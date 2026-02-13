# rvandroid/rvdroid/ui/__init__.py
"""
UI adapter module for RVDroid.

This module provides adapters for interacting with Android device UIs 
through different automation technologies like UIAutomator2.
"""

from rvdroid_tool.ui.adapter import UIAdapter
from rvdroid_tool.ui.uiautomator import UIAutomator2Adapter

__all__ = ['UIAdapter', 'UIAutomator2Adapter']
"""
UI Adapter components for device interaction.

This package contains the adapter interface and implementations for
interacting with Android devices through various automation frameworks.
"""

from .base import UIAdapter
from .uiautomator2 import UIAutomator2Adapter

__all__ = ["UIAdapter", "UIAutomator2Adapter"]

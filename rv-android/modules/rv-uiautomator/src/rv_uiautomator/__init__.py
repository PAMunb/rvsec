"""
RV-UIAutomator: Shared UIAutomator components for RV-Android tools.

This package provides unified UIAutomator components that can be shared across
different testing tools, eliminating code duplication and ensuring consistent
device interaction patterns.
"""

from .adapter.base import UIAdapter
from .adapter.uiautomator2 import UIAutomator2Adapter
from .executor.action_executor import UIAutomatorActionExecutor
from .state.converter import StateConverter

__all__ = [
    "UIAdapter",
    "UIAutomator2Adapter",
    "UIAutomatorActionExecutor",
    "StateConverter",
]

__version__ = "0.1.0"

"""
Action execution components for UIAutomator framework.

This package contains action execution logic that translates
generated actions into device interactions.
"""

from .action_executor import UIAutomatorActionExecutor

__all__ = [
    "UIAutomatorActionExecutor"
]
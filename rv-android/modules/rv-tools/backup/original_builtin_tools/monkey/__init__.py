"""
Android Monkey testing tool.

Monkey generates pseudo-random streams of user events such as clicks, touches,
gestures, and system-level events for stress testing Android applications.
"""

from .tool import MonkeyTool

__all__ = ["MonkeyTool"]
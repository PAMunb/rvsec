"""
RVDroid: A UIAutomator2-based Android testing tool integrated with RV-Android.

This package provides components for Android UI testing using UIAutomator2,
with optional LLM strategic guidance through the RV-Android framework.
"""

# Basic imports for tool functionality
from rvdroid_tool.tools.tool import RVDroidTool
from rvdroid_tool.config.tool_config import RVDroidToolConfig

__all__ = ['RVDroidTool', 'RVDroidToolConfig']

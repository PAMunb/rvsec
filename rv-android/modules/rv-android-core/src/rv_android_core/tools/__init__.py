"""
Base classes for tool implementations.

This package provides the foundational abstractions for all testing tools
in the RV-Android monitored operations framework.
"""

from .abstract_tool import AbstractTool
from .tool_spec import ToolSpec

__all__ = ["AbstractTool", "ToolSpec"]

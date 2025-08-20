"""
Tool registration system for rv-experiment execution.

This module provides external tool registration using constants and modern
architecture patterns. All legacy code has been removed and moved to backup.
"""

from .experiment_tools import ExperimentToolRegistry

__all__ = [
    "ExperimentToolRegistry"
]
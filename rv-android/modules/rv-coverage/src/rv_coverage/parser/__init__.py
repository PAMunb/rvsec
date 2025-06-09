"""
Parsing components for logcat and other data sources.

Provides parsers for extracting coverage information and formal property
violations from Android logcat output.
"""

from .log.logcat_parser import parse_logcat_line, parse_logcat_file

__all__ = [
    "parse_logcat_line",
    "parse_logcat_file"
]
"""
RVAgent CLI Module - Command-line interface for autonomous Android testing.

Provides standalone execution capabilities for the RVAgent MVP.
"""

from .main import cli, main, test_connection

__all__ = ["cli", "main", "test_connection"]
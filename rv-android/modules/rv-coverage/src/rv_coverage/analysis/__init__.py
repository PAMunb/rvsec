"""
Analysis components for coverage tracking and calculation.

Provides classes for both real-time coverage tracking during test execution
and batch analysis of coverage data from logcat files.
"""

from .coverage.analyzer import CoverageAnalyzer
from .coverage.tracker import CoverageTracker

__all__ = ["CoverageAnalyzer", "CoverageTracker"]

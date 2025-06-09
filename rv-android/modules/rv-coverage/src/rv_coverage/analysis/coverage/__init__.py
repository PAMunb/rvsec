"""
Coverage analysis components.

This package provides core coverage analysis functionality including:
- Real-time coverage tracking during test execution
- Batch analysis of coverage data from logcat files
- Coverage metrics calculation and reporting
"""

from .analyzer import CoverageAnalyzer
from .tracker import CoverageTracker

__all__ = [
    "CoverageAnalyzer",
    "CoverageTracker"
]

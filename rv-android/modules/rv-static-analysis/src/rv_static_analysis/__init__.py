"""
RV Static Analysis Module

Unified GATOR-based static analysis for Android applications,
producing reachability, windows, and transitions data.
"""

from .analysis.static.static_analysis import (
    StaticAnalysisException,
    StaticAnalysisResult,
    StaticAnalyzer,
)
from .config import RVStaticAnalysisConfig

__version__ = "0.1.0"
__all__ = [
    "RVStaticAnalysisConfig",
    "StaticAnalyzer",
    "StaticAnalysisResult",
    "StaticAnalysisException",
]

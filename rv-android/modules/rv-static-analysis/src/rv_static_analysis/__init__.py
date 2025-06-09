"""
RV Static Analysis Module

Static analysis tools integration (GATOR, GESDA, REACH) and result parsing
for Android applications with runtime verification monitor integration.
"""

from .config import RVStaticAnalysisConfig
from .analysis.static.static_analysis import (
    StaticAnalyzer,
    StaticAnalysisResult,
    StaticAnalysisException
)

__version__ = "0.1.0"
__all__ = [
    "RVStaticAnalysisConfig",
    "StaticAnalyzer", 
    "StaticAnalysisResult",
    "StaticAnalysisException"
]
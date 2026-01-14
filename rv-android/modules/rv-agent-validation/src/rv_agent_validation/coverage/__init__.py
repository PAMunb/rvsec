"""
Coverage calculation module for validation experiments.

Parses .methods files and logcat to calculate method coverage metrics.

This module uses a custom implementation instead of rv-coverage to maintain
compatibility with the .methods file format from previous experiments,
allowing direct comparison of results across experiment iterations.
"""

from rv_agent_validation.coverage.methods_parser import MethodsParser, MethodData
from rv_agent_validation.coverage.logcat_parser import (
    LogcatCoverageParser,
    CoverageEntry,
    ErrorEntry,
)
from rv_agent_validation.coverage.tracker import (
    CoverageTracker,
    CoverageResult,
    calculate_coverage,
)
from rv_agent_validation.coverage.signature_normalizer import SignatureNormalizer

__all__ = [
    "MethodsParser",
    "MethodData",
    "LogcatCoverageParser",
    "CoverageEntry",
    "ErrorEntry",
    "CoverageTracker",
    "CoverageResult",
    "calculate_coverage",
    "SignatureNormalizer",
]

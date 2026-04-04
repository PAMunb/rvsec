"""
RV Coverage Module

Logcat parsing and coverage analysis for runtime verification of Android applications.
Provides real-time coverage tracking and formal property violation detection.

### Architectural Role:
- Parses logcat output for coverage and error information
- Tracks method execution coverage in real-time
- Detects and reports formal property violations (MOP errors)
- Calculates comprehensive coverage metrics

### Key Components:
- CoverageAnalyzer: Batch analysis of coverage data
- CoverageTracker: Real-time coverage tracking
- LogcatParser: Parsing logcat entries for coverage information

### Integration Points:
- LoggingManager: Standardized logging infrastructure
- ErrorHandler: Centralized error handling patterns
"""

from .analysis.coverage.analyzer import CoverageAnalyzer
from .analysis.coverage.tracker import CoverageTracker
from .parser.log.logcat_parser import parse_logcat_line, parse_logcat_file

__version__ = "0.1.0"
__all__ = [
    "CoverageAnalyzer",
    "CoverageTracker",
    "parse_logcat_line",
    "parse_logcat_file",
]

"""
Provide unified GATOR-based static analysis for Android applications.

Run the RvsecAnalysisClient (a GATOR Java client) on APKs and parse the
resulting JSON into domain objects (Classes, Windows, WindowTransitionGraph,
Components). The analysis produces a single JSON file per APK with sections
written in priority order, enabling graceful degradation on timeout.

### Architectural Decisions:

- Single public API surface: export StaticAnalyzer, StaticAnalysisResult,
  StaticAnalysisException, and RVStaticAnalysisConfig from the package root
  so consumers do not need to know the internal directory structure
- Parser is not re-exported here because it is used internally by
  StaticAnalyzer.get_static_data() and rarely needed by external callers

### Role in the System:

- Called by rv-platform's StaticAnalysisComponent during pre-processing
- Produces StaticAnalysisData consumed by rv-agent (navigation guidance,
  MOP prioritization) and rv-coverage (method universe for coverage %)

### Integration Points:

- Input: App instances from rv-android-core, RVSEC_HOME environment
- Output: StaticAnalysisData domain objects via StaticAnalyzer.get_static_data()
- Dependencies: rv-android-core (domain models, error handling, logging)
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

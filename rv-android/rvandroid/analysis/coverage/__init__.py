# rvandroid/analysis/coverage/__init__.py
from rvandroid.analysis.coverage.analyzer import CoverageAnalyzer
from rvandroid.analysis.coverage.tracker import CoverageTracker

# Export the coverage API
# Note: CoverageRepository wrapper has been eliminated in favor of direct LogcatRepository usage
__all__ = [
    'CoverageAnalyzer',
    'CoverageTracker'
]

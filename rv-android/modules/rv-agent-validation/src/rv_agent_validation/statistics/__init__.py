"""
Statistical analysis for experiment results.

Provides:
- DescriptiveStats: Basic statistics (mean, std, median, etc.)
- SignificanceTests: Statistical significance tests (Kruskal-Wallis, Wilcoxon)
- EffectSize: Effect size calculations (Cliff's Delta, Cohen's d)
- CompositeScorer: Multi-objective scoring for strategy comparison
"""

from .descriptive import DescriptiveStats
from .significance import SignificanceTests
from .effect_size import EffectSize
from .composite_score import CompositeScorer

__all__ = [
    "DescriptiveStats",
    "SignificanceTests",
    "EffectSize",
    "CompositeScorer",
]

"""
Statistical analysis for experiment results.

Provides:
- DescriptiveStats: Basic statistics (mean, std, median, etc.)
- SignificanceTests: Statistical significance tests (Kruskal-Wallis, Wilcoxon)
- EffectSize: Effect size calculations (Cliff's Delta, Cohen's d)
- CompositeScorer: Multi-objective scoring for strategy comparison
"""

from .composite_score import CompositeScorer
from .descriptive import DescriptiveStats
from .effect_size import EffectSize
from .significance import SignificanceTests

__all__ = [
    "DescriptiveStats",
    "SignificanceTests",
    "EffectSize",
    "CompositeScorer",
]

"""
Effect size calculations for experiment results.
"""

from typing import Dict, List, Any, Tuple
from itertools import combinations
import numpy as np


class EffectSize:
    """
    Effect size calculations for comparing strategies.

    Implements:
    - Cliff's Delta (non-parametric, recommended)
    - Cohen's d (parametric, for reference)
    """

    # Cliff's Delta interpretation thresholds
    CLIFF_NEGLIGIBLE = 0.147
    CLIFF_SMALL = 0.33
    CLIFF_MEDIUM = 0.474

    # Cohen's d interpretation thresholds
    COHEN_SMALL = 0.2
    COHEN_MEDIUM = 0.5
    COHEN_LARGE = 0.8

    @staticmethod
    def cliffs_delta(x: List[float], y: List[float]) -> Tuple[float, str]:
        """
        Calculate Cliff's Delta effect size.

        Non-parametric measure of effect size for ordinal data.
        Measures the probability that a randomly selected value
        from one group is greater than a randomly selected value
        from the other group.

        Args:
            x: First group values.
            y: Second group values.

        Returns:
            Tuple of (delta, interpretation).
        """
        if not x or not y:
            return 0.0, "undefined"

        n_x, n_y = len(x), len(y)

        # Count dominance
        greater = sum(1 for xi in x for yi in y if xi > yi)
        less = sum(1 for xi in x for yi in y if xi < yi)

        delta = (greater - less) / (n_x * n_y)

        # Interpret
        abs_delta = abs(delta)
        if abs_delta < EffectSize.CLIFF_NEGLIGIBLE:
            interpretation = "negligible"
        elif abs_delta < EffectSize.CLIFF_SMALL:
            interpretation = "small"
        elif abs_delta < EffectSize.CLIFF_MEDIUM:
            interpretation = "medium"
        else:
            interpretation = "large"

        return round(delta, 4), interpretation

    @staticmethod
    def cohens_d(x: List[float], y: List[float]) -> Tuple[float, str]:
        """
        Calculate Cohen's d effect size.

        Parametric measure of effect size based on standardized
        mean difference.

        Args:
            x: First group values.
            y: Second group values.

        Returns:
            Tuple of (d, interpretation).
        """
        if not x or not y:
            return 0.0, "undefined"

        n_x, n_y = len(x), len(y)
        mean_x, mean_y = np.mean(x), np.mean(y)
        var_x, var_y = np.var(x, ddof=1), np.var(y, ddof=1)

        # Pooled standard deviation
        pooled_std = np.sqrt(
            ((n_x - 1) * var_x + (n_y - 1) * var_y) / (n_x + n_y - 2)
        )

        if pooled_std == 0:
            return 0.0, "undefined"

        d = (mean_x - mean_y) / pooled_std

        # Interpret
        abs_d = abs(d)
        if abs_d < EffectSize.COHEN_SMALL:
            interpretation = "negligible"
        elif abs_d < EffectSize.COHEN_MEDIUM:
            interpretation = "small"
        elif abs_d < EffectSize.COHEN_LARGE:
            interpretation = "medium"
        else:
            interpretation = "large"

        return round(d, 4), interpretation

    @staticmethod
    def compare_strategies(
        results: List[Dict[str, Any]],
        metric: str,
        strategy_a: str,
        strategy_b: str
    ) -> Dict[str, Any]:
        """
        Calculate effect sizes between two strategies.

        Args:
            results: List of run results.
            metric: Metric to compare.
            strategy_a: First strategy.
            strategy_b: Second strategy.

        Returns:
            Effect size results.
        """
        values_a = [
            r[metric] for r in results
            if r.get("strategy") == strategy_a and r.get(metric) is not None
        ]
        values_b = [
            r[metric] for r in results
            if r.get("strategy") == strategy_b and r.get(metric) is not None
        ]

        cliff_delta, cliff_interp = EffectSize.cliffs_delta(values_a, values_b)
        cohen_d, cohen_interp = EffectSize.cohens_d(values_a, values_b)

        return {
            "comparison": f"{strategy_a}_vs_{strategy_b}",
            "metric": metric,
            "cliff_delta": cliff_delta,
            "cliff_interpretation": cliff_interp,
            "cohen_d": cohen_d,
            "cohen_interpretation": cohen_interp,
            "n_a": len(values_a),
            "n_b": len(values_b),
            "direction": "a > b" if cliff_delta > 0 else "b > a" if cliff_delta < 0 else "equal",
        }

    @staticmethod
    def all_pairwise(
        results: List[Dict[str, Any]],
        metric: str,
        strategies: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Calculate effect sizes for all strategy pairs.

        Args:
            results: List of run results.
            metric: Metric to compare.
            strategies: List of strategy names.

        Returns:
            List of effect size results.
        """
        comparisons = []
        for s1, s2 in combinations(strategies, 2):
            result = EffectSize.compare_strategies(results, metric, s1, s2)
            comparisons.append(result)
        return comparisons

    @staticmethod
    def summary_matrix(
        results: List[Dict[str, Any]],
        metric: str,
        strategies: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Create effect size matrix.

        Args:
            results: List of run results.
            metric: Metric to compare.
            strategies: List of strategy names.

        Returns:
            Matrix of Cliff's Delta values.
        """
        matrix = {s: {} for s in strategies}

        for s1, s2 in combinations(strategies, 2):
            values_a = [
                r[metric] for r in results
                if r.get("strategy") == s1 and r.get(metric) is not None
            ]
            values_b = [
                r[metric] for r in results
                if r.get("strategy") == s2 and r.get(metric) is not None
            ]

            delta, _ = EffectSize.cliffs_delta(values_a, values_b)
            matrix[s1][s2] = delta
            matrix[s2][s1] = -delta

        for s in strategies:
            matrix[s][s] = 0.0

        return matrix

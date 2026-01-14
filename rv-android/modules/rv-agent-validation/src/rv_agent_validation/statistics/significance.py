"""
Significance tests for experiment results.
"""

from typing import Dict, List, Any, Tuple
from itertools import combinations
import numpy as np

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class SignificanceTests:
    """
    Statistical significance tests for comparing strategies.

    Uses non-parametric tests suitable for small samples:
    - Kruskal-Wallis H-test (multiple groups)
    - Wilcoxon signed-rank test (pairwise, paired)
    """

    # Bonferroni-corrected alpha for 4 strategies (6 comparisons)
    ALPHA = 0.05
    N_COMPARISONS = 6  # C(4,2) = 6
    BONFERRONI_ALPHA = ALPHA / N_COMPARISONS  # 0.0083

    @staticmethod
    def kruskal_wallis(
        results: List[Dict[str, Any]],
        metric: str,
        strategies: List[str]
    ) -> Dict[str, Any]:
        """
        Kruskal-Wallis H-test for comparing multiple strategies.

        Tests H0: All strategies have the same distribution.

        Args:
            results: List of run results.
            metric: Metric to compare.
            strategies: List of strategy names.

        Returns:
            Test results with H statistic and p-value.
        """
        if not SCIPY_AVAILABLE:
            return {"error": "scipy not available"}

        # Group values by strategy
        groups = []
        for strategy in strategies:
            values = [
                r[metric] for r in results
                if r.get("strategy") == strategy and r.get(metric) is not None
            ]
            if values:
                groups.append(values)

        if len(groups) < 2:
            return {"error": "Need at least 2 groups with data"}

        try:
            h_stat, p_value = stats.kruskal(*groups)
            return {
                "test": "kruskal_wallis",
                "H_statistic": round(float(h_stat), 4),
                "p_value": round(float(p_value), 6),
                "significant": p_value < SignificanceTests.ALPHA,
                "alpha": SignificanceTests.ALPHA,
                "n_groups": len(groups),
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def wilcoxon_pairwise(
        results: List[Dict[str, Any]],
        metric: str,
        strategy_a: str,
        strategy_b: str
    ) -> Dict[str, Any]:
        """
        Wilcoxon signed-rank test for paired comparison.

        Tests H0: The two strategies have the same distribution.
        Uses paired data (same app) for comparison.

        Args:
            results: List of run results.
            metric: Metric to compare.
            strategy_a: First strategy.
            strategy_b: Second strategy.

        Returns:
            Test results with W statistic and p-value.
        """
        if not SCIPY_AVAILABLE:
            return {"error": "scipy not available"}

        # Group by app to get paired data
        apps = set(r["app"] for r in results if "app" in r)
        pairs_a = []
        pairs_b = []

        for app in apps:
            # Get mean for each strategy on this app
            values_a = [
                r[metric] for r in results
                if r.get("app") == app and r.get("strategy") == strategy_a
                and r.get(metric) is not None
            ]
            values_b = [
                r[metric] for r in results
                if r.get("app") == app and r.get("strategy") == strategy_b
                and r.get(metric) is not None
            ]

            if values_a and values_b:
                pairs_a.append(np.mean(values_a))
                pairs_b.append(np.mean(values_b))

        if len(pairs_a) < 5:
            return {
                "error": f"Need at least 5 paired samples, got {len(pairs_a)}",
                "comparison": f"{strategy_a}_vs_{strategy_b}"
            }

        try:
            w_stat, p_value = stats.wilcoxon(pairs_a, pairs_b)
            return {
                "test": "wilcoxon_signed_rank",
                "comparison": f"{strategy_a}_vs_{strategy_b}",
                "W_statistic": round(float(w_stat), 4),
                "p_value": round(float(p_value), 6),
                "significant": p_value < SignificanceTests.ALPHA,
                "significant_bonferroni": p_value < SignificanceTests.BONFERRONI_ALPHA,
                "alpha": SignificanceTests.ALPHA,
                "alpha_bonferroni": round(SignificanceTests.BONFERRONI_ALPHA, 4),
                "n_pairs": len(pairs_a),
            }
        except Exception as e:
            return {"error": str(e), "comparison": f"{strategy_a}_vs_{strategy_b}"}

    @staticmethod
    def all_pairwise(
        results: List[Dict[str, Any]],
        metric: str,
        strategies: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Run all pairwise Wilcoxon tests.

        Args:
            results: List of run results.
            metric: Metric to compare.
            strategies: List of strategy names.

        Returns:
            List of pairwise test results.
        """
        comparisons = []
        for s1, s2 in combinations(strategies, 2):
            result = SignificanceTests.wilcoxon_pairwise(results, metric, s1, s2)
            comparisons.append(result)
        return comparisons

    @staticmethod
    def full_analysis(
        results: List[Dict[str, Any]],
        metric: str,
        strategies: List[str]
    ) -> Dict[str, Any]:
        """
        Run complete significance analysis.

        Args:
            results: List of run results.
            metric: Metric to analyze.
            strategies: List of strategy names.

        Returns:
            Complete analysis results.
        """
        return {
            "metric": metric,
            "kruskal_wallis": SignificanceTests.kruskal_wallis(results, metric, strategies),
            "pairwise_wilcoxon": SignificanceTests.all_pairwise(results, metric, strategies),
        }

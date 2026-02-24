"""
Descriptive statistics for experiment results.
"""

from typing import Any, Dict, List

import numpy as np


class DescriptiveStats:
    """
    Calculates descriptive statistics for experiment metrics.
    """

    @staticmethod
    def calculate(values: List[float]) -> Dict[str, float]:
        """
        Calculate descriptive statistics for a list of values.

        Args:
            values: List of numeric values.

        Returns:
            Dictionary with statistics.
        """
        if not values:
            return {
                "n": 0,
                "mean": 0.0,
                "std": 0.0,
                "median": 0.0,
                "min": 0.0,
                "max": 0.0,
                "q1": 0.0,
                "q3": 0.0,
                "iqr": 0.0,
            }

        arr = np.array(values)
        q1, median, q3 = np.percentile(arr, [25, 50, 75])

        return {
            "n": len(values),
            "mean": round(float(np.mean(arr)), 4),
            "std": round(float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0, 4),
            "median": round(float(median), 4),
            "min": round(float(np.min(arr)), 4),
            "max": round(float(np.max(arr)), 4),
            "q1": round(float(q1), 4),
            "q3": round(float(q3), 4),
            "iqr": round(float(q3 - q1), 4),
        }

    @staticmethod
    def aggregate_by_strategy(
        results: List[Dict[str, Any]], metric: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Aggregate metrics by strategy.

        Args:
            results: List of run results.
            metric: Metric name to aggregate.

        Returns:
            Dictionary mapping strategy to statistics.
        """
        # Group by strategy
        by_strategy: Dict[str, List[float]] = {}
        for result in results:
            strategy = result.get("strategy", "unknown")
            value = result.get(metric)
            if value is not None:
                if strategy not in by_strategy:
                    by_strategy[strategy] = []
                by_strategy[strategy].append(float(value))

        # Calculate stats for each strategy
        stats = {}
        for strategy, values in by_strategy.items():
            stats[strategy] = DescriptiveStats.calculate(values)

        return stats

    @staticmethod
    def aggregate_by_app(
        results: List[Dict[str, Any]], metric: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Aggregate metrics by app.

        Args:
            results: List of run results.
            metric: Metric name to aggregate.

        Returns:
            Dictionary mapping app to statistics.
        """
        # Group by app
        by_app: Dict[str, List[float]] = {}
        for result in results:
            app = result.get("app", "unknown")
            value = result.get(metric)
            if value is not None:
                if app not in by_app:
                    by_app[app] = []
                by_app[app].append(float(value))

        # Calculate stats for each app
        stats = {}
        for app, values in by_app.items():
            stats[app] = DescriptiveStats.calculate(values)

        return stats

    @staticmethod
    def summary_table(
        results: List[Dict[str, Any]], metrics: List[str]
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Generate summary table for multiple metrics by strategy.

        Args:
            results: List of run results.
            metrics: List of metric names.

        Returns:
            Nested dictionary: metric -> strategy -> statistics.
        """
        summary = {}
        for metric in metrics:
            summary[metric] = DescriptiveStats.aggregate_by_strategy(results, metric)
        return summary

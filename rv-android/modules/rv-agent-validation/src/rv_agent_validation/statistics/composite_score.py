"""
Composite scoring for strategy comparison.

Implements multi-objective scoring that balances:
- Coverage (UI + states)
- MOP (security method prioritization)
- Efficiency (states per action)
- Robustness (validity, crashes)
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class CompositeScorer:
    """
    Calculates composite strategy scores from multiple metrics.

    Score composition (default weights):
    - 30% Coverage: UI coverage + states discovered
    - 25% MOP: MOP method selection rate
    - 25% Efficiency: States per action, low repetition
    - 20% Robustness: Action validity, no crashes

    All scores are normalized to [0, 100].
    """

    # Default weights (must sum to 1.0)
    DEFAULT_WEIGHTS = {
        "coverage": 0.30,
        "mop": 0.25,
        "efficiency": 0.25,
        "robustness": 0.20,
    }

    # Normalization constants (can be adjusted based on dataset)
    MAX_STATES = 50  # Expected max states in 3 min exploration
    MAX_MOP_METHODS = 20  # Expected max MOP methods
    MAX_ACTIONS_PER_STATE = 20  # Expected max actions per state

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize scorer with optional custom weights.

        Args:
            weights: Custom weight dictionary. Must sum to ~1.0.
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

        # Validate weights sum to approximately 1.0
        total = sum(self.weights.values())
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

    def calculate_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate composite score for a single run result.

        Args:
            metrics: Dictionary with run metrics.

        Returns:
            Composite score [0-100].
        """
        coverage_score = self._calculate_coverage_score(metrics)
        mop_score = self._calculate_mop_score(metrics)
        efficiency_score = self._calculate_efficiency_score(metrics)
        robustness_score = self._calculate_robustness_score(metrics)

        composite = (
            self.weights["coverage"] * coverage_score
            + self.weights["mop"] * mop_score
            + self.weights["efficiency"] * efficiency_score
            + self.weights["robustness"] * robustness_score
        )

        return round(composite * 100, 2)

    def _calculate_coverage_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate coverage component score [0-1].

        Components:
        - 50% UI coverage percentage (0-100 -> 0-1)
        - 50% States discovered (normalized to MAX_STATES)
        """
        ui_coverage = metrics.get("ui_coverage_percentage", 0.0)
        states = metrics.get("states_discovered", 0)

        ui_score = min(ui_coverage / 100.0, 1.0)
        states_score = min(states / self.MAX_STATES, 1.0)

        return 0.5 * ui_score + 0.5 * states_score

    def _calculate_mop_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate MOP prioritization component score [0-1].

        Components:
        - 60% MOP selection rate (percentage of MOP actions selected)
        - 40% MOP methods reached (normalized to MAX_MOP_METHODS)
        """
        mop_selection_rate = metrics.get("mop_selection_rate", 0.0)
        mop_methods = metrics.get("mop_methods_reached", 0)

        selection_score = min(mop_selection_rate / 100.0, 1.0)
        methods_score = min(mop_methods / self.MAX_MOP_METHODS, 1.0)

        return 0.6 * selection_score + 0.4 * methods_score

    def _calculate_efficiency_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate efficiency component score [0-1].

        Components:
        - 70% States per action (higher is better, max ~1.0)
        - 30% Low repetition rate (inverse of repetition)
        """
        states_per_action = metrics.get("states_per_action", 0.0)
        repetition_rate = metrics.get("action_repetition_rate", 0.0)

        # States per action: 0.5 states/action is considered excellent
        spa_score = min(states_per_action * 2, 1.0)

        # Repetition: 0% is best, 100% is worst
        repetition_score = 1.0 - min(repetition_rate / 100.0, 1.0)

        return 0.7 * spa_score + 0.3 * repetition_score

    def _calculate_robustness_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate robustness component score [0-1].

        Components:
        - 60% Action validity rate (percentage of valid actions)
        - 40% No crashes (inverse of crash count)
        """
        validity_rate = metrics.get("action_validity_rate", 0.0)
        crashes = metrics.get("app_crashes", 0)

        validity_score = min(validity_rate / 100.0, 1.0)

        # Crashes: 0 is best, 10+ is terrible
        crash_score = max(1.0 - (crashes / 10.0), 0.0)

        return 0.6 * validity_score + 0.4 * crash_score

    def calculate_component_scores(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate individual component scores for analysis.

        Args:
            metrics: Dictionary with run metrics.

        Returns:
            Dictionary with component scores [0-100] and composite.
        """
        return {
            "coverage_score": round(self._calculate_coverage_score(metrics) * 100, 2),
            "mop_score": round(self._calculate_mop_score(metrics) * 100, 2),
            "efficiency_score": round(
                self._calculate_efficiency_score(metrics) * 100, 2
            ),
            "robustness_score": round(
                self._calculate_robustness_score(metrics) * 100, 2
            ),
            "composite_score": self.calculate_score(metrics),
        }

    def rank_strategies(
        self, results: List[Dict[str, Any]]
    ) -> List[Tuple[str, float, Dict[str, float]]]:
        """
        Rank strategies by average composite score.

        Args:
            results: List of run results with 'strategy' field.

        Returns:
            List of (strategy, avg_score, component_scores) tuples,
            sorted by score descending.
        """
        by_strategy: Dict[str, List[Dict[str, float]]] = defaultdict(list)

        for result in results:
            strategy = result.get("strategy", "unknown")
            if result.get("status") != "completed":
                continue

            scores = self.calculate_component_scores(result)
            by_strategy[strategy].append(scores)

        rankings = []
        for strategy, score_list in by_strategy.items():
            if not score_list:
                continue

            # Average each component
            avg_scores = {}
            for key in score_list[0].keys():
                values = [s[key] for s in score_list]
                avg_scores[key] = round(np.mean(values), 2)

            composite = avg_scores["composite_score"]
            rankings.append((strategy, composite, avg_scores))

        # Sort by composite score descending
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings

    def rank_by_metric(
        self, results: List[Dict[str, Any]], metric: str, ascending: bool = False
    ) -> List[Tuple[str, float]]:
        """
        Rank strategies by a specific metric.

        Args:
            results: List of run results.
            metric: Metric name to rank by.
            ascending: If True, lower is better.

        Returns:
            List of (strategy, avg_value) tuples, sorted.
        """
        by_strategy: Dict[str, List[float]] = defaultdict(list)

        for result in results:
            strategy = result.get("strategy", "unknown")
            value = result.get(metric)

            if value is not None and result.get("status") == "completed":
                by_strategy[strategy].append(float(value))

        rankings = []
        for strategy, values in by_strategy.items():
            if values:
                avg = round(np.mean(values), 4)
                rankings.append((strategy, avg))

        rankings.sort(key=lambda x: x[1], reverse=not ascending)
        return rankings

    def get_strategy_summary(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate comprehensive summary for each strategy.

        Args:
            results: List of run results.

        Returns:
            Dictionary mapping strategy to summary statistics.
        """
        by_strategy: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for result in results:
            strategy = result.get("strategy", "unknown")
            if result.get("status") == "completed":
                by_strategy[strategy].append(result)

        summary = {}
        for strategy, runs in by_strategy.items():
            if not runs:
                continue

            # Collect key metrics
            scores = [self.calculate_score(r) for r in runs]
            states = [r.get("states_discovered", 0) for r in runs]
            actions = [r.get("total_actions", 0) for r in runs]
            ui_cov = [r.get("ui_coverage_percentage", 0) for r in runs]
            mop = [r.get("mop_methods_reached", 0) for r in runs]
            efficiency = [r.get("states_per_action", 0) for r in runs]

            summary[strategy] = {
                "n_runs": len(runs),
                "composite_score": {
                    "mean": round(np.mean(scores), 2),
                    "std": round(np.std(scores), 2),
                    "min": round(min(scores), 2),
                    "max": round(max(scores), 2),
                },
                "states_discovered": {
                    "mean": round(np.mean(states), 2),
                    "std": round(np.std(states), 2),
                },
                "total_actions": {
                    "mean": round(np.mean(actions), 2),
                    "std": round(np.std(actions), 2),
                },
                "ui_coverage_percentage": {
                    "mean": round(np.mean(ui_cov), 2),
                    "std": round(np.std(ui_cov), 2),
                },
                "mop_methods_reached": {
                    "mean": round(np.mean(mop), 2),
                    "std": round(np.std(mop), 2),
                },
                "states_per_action": {
                    "mean": round(np.mean(efficiency), 4),
                    "std": round(np.std(efficiency), 4),
                },
            }

        return summary

    def recommend_best_strategy(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Recommend the best strategy based on composite score.

        Args:
            results: List of run results.

        Returns:
            Recommendation with strategy name, score, and confidence.
        """
        rankings = self.rank_strategies(results)

        if not rankings:
            return {
                "recommendation": None,
                "reason": "No completed runs found",
            }

        best = rankings[0]
        second = rankings[1] if len(rankings) > 1 else None

        recommendation = {
            "recommendation": best[0],
            "composite_score": best[1],
            "component_scores": best[2],
        }

        # Calculate confidence based on gap to second place
        if second:
            gap = best[1] - second[1]
            recommendation["gap_to_second"] = round(gap, 2)
            recommendation["second_place"] = second[0]

            # Confidence levels based on gap
            if gap >= 10:
                recommendation["confidence"] = "high"
            elif gap >= 5:
                recommendation["confidence"] = "medium"
            else:
                recommendation["confidence"] = "low"
        else:
            recommendation["confidence"] = "only_one_strategy"

        return recommendation

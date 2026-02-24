"""
JSON export for experiment results.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from statistics import DescriptiveStats, EffectSize, SignificanceTests

import numpy as np


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types."""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)


class JSONExporter:
    """
    Exports experiment results to JSON format.
    """

    @staticmethod
    def export_aggregate(
        results: List[Dict[str, Any]],
        config: Dict[str, Any],
        output_path: Path,
        strategies: List[str],
        metrics: List[str],
    ) -> Path:
        """
        Export aggregated results to JSON.

        Args:
            results: List of run results.
            config: Experiment configuration.
            output_path: Output file path.
            strategies: List of strategies.
            metrics: List of metrics to analyze.

        Returns:
            Path to output file.
        """
        # Calculate statistics
        summary_by_strategy = {}
        for strategy in strategies:
            strategy_results = [r for r in results if r.get("strategy") == strategy]
            summary_by_strategy[strategy] = {}
            for metric in metrics:
                values = [
                    r[metric] for r in strategy_results if r.get(metric) is not None
                ]
                summary_by_strategy[strategy][metric] = DescriptiveStats.calculate(
                    values
                )

        # Significance tests
        statistical_tests = {}
        for metric in metrics:
            statistical_tests[metric] = {
                "kruskal_wallis": SignificanceTests.kruskal_wallis(
                    results, metric, strategies
                ),
                "pairwise_wilcoxon": SignificanceTests.all_pairwise(
                    results, metric, strategies
                ),
            }

        # Effect sizes
        effect_sizes = {}
        for metric in metrics:
            effect_sizes[metric] = EffectSize.all_pairwise(results, metric, strategies)

        # Build output
        output = {
            "experiment": {
                "id": config.get("experiment_id", "unknown"),
                "name": config.get("experiment_name", "Strategy Validation"),
                "timestamp": datetime.now().isoformat(),
                "total_runs": len(results),
                "completed_runs": len(
                    [r for r in results if r.get("status") == "completed"]
                ),
                "failed_runs": len(
                    [r for r in results if r.get("status") != "completed"]
                ),
            },
            "configuration": config,
            "summary_by_strategy": summary_by_strategy,
            "statistical_tests": statistical_tests,
            "effect_sizes": effect_sizes,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2, cls=NumpyEncoder)

        return output_path

    @staticmethod
    def load_results(results_dir: Path) -> List[Dict[str, Any]]:
        """
        Load all run results from directory.

        Args:
            results_dir: Directory containing run JSON files.

        Returns:
            List of run results.
        """
        results = []
        runs_dir = results_dir / "runs"

        if runs_dir.exists():
            for result_file in runs_dir.glob("*.json"):
                try:
                    with open(result_file, "r") as f:
                        results.append(json.load(f))
                except Exception as e:
                    print(f"Error loading {result_file}: {e}")

        return results

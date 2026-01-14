"""
CSV export for experiment results.
"""

import csv
from pathlib import Path
from typing import Dict, List, Any


class CSVExporter:
    """
    Exports experiment results to CSV format.
    """

    @staticmethod
    def export_per_run(
        results: List[Dict[str, Any]],
        output_path: Path,
        metrics: List[str]
    ) -> Path:
        """
        Export per-run metrics to CSV.

        Args:
            results: List of run results.
            output_path: Output file path.
            metrics: List of metrics to include.

        Returns:
            Path to output file.
        """
        fieldnames = ["run_id", "app", "strategy", "repetition", "seed", "status"]
        fieldnames.extend(metrics)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for result in sorted(results, key=lambda x: x.get("run_id", "")):
                row = {k: result.get(k, "") for k in fieldnames}
                writer.writerow(row)

        return output_path

    @staticmethod
    def export_summary(
        summary_by_strategy: Dict[str, Dict[str, Dict[str, float]]],
        output_path: Path,
        metrics: List[str]
    ) -> Path:
        """
        Export strategy summary to CSV.

        Args:
            summary_by_strategy: Summary statistics by strategy.
            output_path: Output file path.
            metrics: List of metrics.

        Returns:
            Path to output file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build rows
        rows = []
        for strategy, strategy_stats in summary_by_strategy.items():
            row = {"strategy": strategy}
            for metric in metrics:
                if metric in strategy_stats:
                    stats = strategy_stats[metric]
                    row[f"{metric}_mean"] = stats.get("mean", "")
                    row[f"{metric}_std"] = stats.get("std", "")
                    row[f"{metric}_median"] = stats.get("median", "")
            rows.append(row)

        # Build fieldnames
        fieldnames = ["strategy"]
        for metric in metrics:
            fieldnames.extend([f"{metric}_mean", f"{metric}_std", f"{metric}_median"])

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return output_path

    @staticmethod
    def export_pairwise(
        pairwise_results: List[Dict[str, Any]],
        output_path: Path
    ) -> Path:
        """
        Export pairwise comparison results to CSV.

        Args:
            pairwise_results: List of pairwise test results.
            output_path: Output file path.

        Returns:
            Path to output file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "comparison", "p_value", "significant", "significant_bonferroni",
            "cliff_delta", "cliff_interpretation"
        ]

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for result in pairwise_results:
                writer.writerow(result)

        return output_path

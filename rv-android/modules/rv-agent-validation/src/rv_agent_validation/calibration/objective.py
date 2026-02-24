"""
Objective function for RVAgent calibration.

Computes a composite score from method coverage, MOP errors, and UI coverage.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ObjectiveFunction:
    """
    Objective function for calibration optimization.

    Computes a weighted score: 40% method coverage + 40% normalized MOP errors
    + 20% UI element coverage (from rvagent_metrics.json).

    Higher error count is BETTER - indicates more monitored operations triggered.
    Higher UI coverage is BETTER - indicates more UI elements interacted with.
    """

    def __init__(
        self,
        coverage_weight: float = 0.40,
        errors_weight: float = 0.40,
        ui_coverage_weight: float = 0.20,
        baseline_max_errors: Optional[float] = None,
    ):
        """
        Initialize objective function.

        Args:
            coverage_weight: Weight for method coverage (0-1)
            errors_weight: Weight for MOP errors (0-1)
            ui_coverage_weight: Weight for UI element coverage (0-1)
            baseline_max_errors: Max errors from baseline for normalization.
                                 If None, uses fallback normalization.
        """
        self.coverage_weight = coverage_weight
        self.errors_weight = errors_weight
        self.ui_coverage_weight = ui_coverage_weight
        self.baseline_max_errors = baseline_max_errors

        total = coverage_weight + errors_weight + ui_coverage_weight
        if abs(total - 1.0) > 0.001:
            logger.warning(
                f"Weights don't sum to 1.0: {coverage_weight} + {errors_weight} "
                f"+ {ui_coverage_weight} = {total}"
            )

    def compute(self, results_dir: str) -> float:
        """
        Compute objective score from experiment results.

        Reads method coverage and MOP errors from summary.csv (rv-platform),
        and UI element coverage from *.rvagent_metrics.json (rv-agent).

        Args:
            results_dir: Path to experiment results directory

        Returns:
            Objective score (0-100 scale), higher is better
        """
        results_path = Path(results_dir)
        summary_path = self._find_summary_csv(results_path)

        if summary_path is None:
            logger.warning(f"summary.csv not found in {results_dir}")
            return 0.0

        try:
            summary = pd.read_csv(summary_path)
        except Exception as e:
            logger.warning(f"Error reading summary.csv: {e}")
            return 0.0

        if summary.empty:
            logger.warning(f"summary.csv is empty in {results_dir}")
            return 0.0

        # Method coverage and MOP errors from summary.csv
        avg_method_cov = summary["cov_method"].mean()  # 0-100%
        avg_errors = summary["errors"].mean()  # Raw count
        normalized_errors = self._normalize_errors(avg_errors)

        # UI element coverage from rvagent_metrics.json files
        avg_ui_cov = self._compute_avg_ui_coverage(results_path)

        # Composite score
        score = (
            self.coverage_weight * avg_method_cov
            + self.errors_weight * normalized_errors
            + self.ui_coverage_weight * avg_ui_cov
        )

        logger.info(
            f"Objective score: {score:.2f} "
            f"(cov={avg_method_cov:.1f}%, errors={avg_errors:.1f} -> "
            f"{normalized_errors:.1f}, ui_cov={avg_ui_cov:.1f}%)"
        )

        return score

    def _compute_avg_ui_coverage(self, results_path: Path) -> float:
        """
        Compute average UI element coverage from rvagent_metrics.json files.

        rv-agent exports a JSON file per APK run containing ui_coverage.element_coverage
        (0-100 scale). This method finds all such files and averages the values.

        Args:
            results_path: Base path to search for metrics files

        Returns:
            Average UI element coverage (0-100), or 0.0 if no files found
        """
        metrics_files = self._find_rvagent_metrics(results_path)

        if not metrics_files:
            logger.debug(f"No rvagent_metrics.json files found in {results_path}")
            return 0.0

        coverages = []
        for metrics_file in metrics_files:
            try:
                with open(metrics_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                element_cov = data.get("ui_coverage", {}).get("element_coverage", 0.0)
                coverages.append(float(element_cov))
            except (json.JSONDecodeError, ValueError, OSError) as e:
                logger.debug(f"Failed to read {metrics_file}: {e}")
                continue

        if not coverages:
            return 0.0

        avg = sum(coverages) / len(coverages)
        logger.debug(f"UI coverage from {len(coverages)} files: avg={avg:.1f}%")
        return avg

    def _find_rvagent_metrics(self, results_path: Path) -> List[Path]:
        """
        Find all rvagent_metrics.json files in the results directory.

        Args:
            results_path: Base path to search

        Returns:
            List of paths to rvagent_metrics.json files
        """
        return list(results_path.rglob("*.rvagent_metrics.json"))

    def _find_summary_csv(self, results_path: Path) -> Optional[Path]:
        """
        Find summary.csv in results directory.

        Searches recursively since rv-experiment creates timestamped subdirectories.

        Args:
            results_path: Base path to search

        Returns:
            Path to summary.csv or None if not found
        """
        # Direct path
        direct_path = results_path / "summary.csv"
        if direct_path.exists():
            return direct_path

        # Search in subdirectories (rv-experiment creates results/cli_experiment_*/summary.csv)
        for csv_file in results_path.rglob("summary.csv"):
            logger.debug(f"Found summary.csv at {csv_file}")
            return csv_file

        return None

    def _normalize_errors(self, avg_errors: float) -> float:
        """
        Normalize error count to 0-100 scale.

        Uses baseline_max_errors if available, otherwise fallback.

        Args:
            avg_errors: Average error count per APK

        Returns:
            Normalized error score (0-100)
        """
        if self.baseline_max_errors and self.baseline_max_errors > 0:
            # Adaptive normalization using baseline
            normalized = (avg_errors / self.baseline_max_errors) * 100
        else:
            # Fallback: assume max ~10 errors per app is excellent
            normalized = avg_errors * 10

        return min(normalized, 100.0)

    def set_baseline_max_errors(self, max_errors: float):
        """
        Set baseline max errors for adaptive normalization.

        Call this after running baseline (Phase B) to enable
        adaptive error normalization.

        Args:
            max_errors: Maximum average errors from baseline tools
        """
        self.baseline_max_errors = max_errors
        logger.info(f"Baseline max errors set to {max_errors:.2f}")

    @staticmethod
    def compute_baseline_max_errors(baseline_dir: str) -> float:
        """
        Compute max average errors from baseline results.

        Args:
            baseline_dir: Path to baseline experiment directory

        Returns:
            Maximum average error count across all tools
        """
        baseline_path = Path(baseline_dir)
        summary_path = baseline_path / "summary.csv"

        if not summary_path.exists():
            logger.warning(f"Baseline summary.csv not found: {summary_path}")
            return 10.0  # Fallback

        try:
            summary = pd.read_csv(summary_path)

            # Group by tool, compute average errors per tool
            if "tool" in summary.columns:
                tool_errors = summary.groupby("tool")["errors"].mean()
                max_errors = tool_errors.max()
            else:
                max_errors = summary["errors"].mean()

            logger.info(f"Computed baseline max errors: {max_errors:.2f}")
            return max(max_errors, 1.0)  # Minimum 1 to avoid division by zero

        except Exception as e:
            logger.warning(f"Error computing baseline max errors: {e}")
            return 10.0  # Fallback

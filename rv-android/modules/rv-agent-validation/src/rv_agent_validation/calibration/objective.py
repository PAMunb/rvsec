"""
Objective function for RVAgent calibration.

Computes a composite score from method coverage and MOP errors.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ObjectiveFunction:
    """
    Objective function for calibration optimization.

    Computes a balanced score: 50% method coverage + 50% normalized errors.
    Higher error count is BETTER - indicates more monitored operations triggered.
    """

    def __init__(
        self,
        coverage_weight: float = 0.50,
        errors_weight: float = 0.50,
        baseline_max_errors: Optional[float] = None
    ):
        """
        Initialize objective function.

        Args:
            coverage_weight: Weight for method coverage (0-1)
            errors_weight: Weight for MOP errors (0-1)
            baseline_max_errors: Max errors from baseline for normalization.
                                 If None, uses fallback normalization.
        """
        self.coverage_weight = coverage_weight
        self.errors_weight = errors_weight
        self.baseline_max_errors = baseline_max_errors

        if abs(coverage_weight + errors_weight - 1.0) > 0.001:
            logger.warning(
                f"Weights don't sum to 1.0: {coverage_weight} + {errors_weight}"
            )

    def compute(self, results_dir: str) -> float:
        """
        Compute objective score from experiment results.

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

        # Average across all APKs
        avg_method_cov = summary['cov_method'].mean()  # 0-100%
        avg_errors = summary['errors'].mean()  # Raw count

        # Normalize errors to 0-100 scale
        normalized_errors = self._normalize_errors(avg_errors)

        # Composite score
        score = (
            self.coverage_weight * avg_method_cov +
            self.errors_weight * normalized_errors
        )

        logger.info(
            f"Objective score: {score:.2f} "
            f"(cov={avg_method_cov:.1f}%, errors={avg_errors:.1f} -> {normalized_errors:.1f})"
        )

        return score

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
            if 'tool' in summary.columns:
                tool_errors = summary.groupby('tool')['errors'].mean()
                max_errors = tool_errors.max()
            else:
                max_errors = summary['errors'].mean()

            logger.info(f"Computed baseline max errors: {max_errors:.2f}")
            return max(max_errors, 1.0)  # Minimum 1 to avoid division by zero

        except Exception as e:
            logger.warning(f"Error computing baseline max errors: {e}")
            return 10.0  # Fallback

"""Objective function for APE-RV calibration via Optuna.

Computes a single scalar score for a calibration trial, used by Optuna to
evaluate parameter configurations. The score is a weighted combination of
MOP coverage (monitored operations reached) and method coverage.

    Score = 50% MOP coverage + 50% method coverage (0-100 scale).

Uses trimmed mean (10% cut) instead of simple mean for robustness against
outlier APKs (e.g., apps that crash early produce 0% coverage, which would
distort the score of an otherwise good parameter configuration).

Reads from summary.csv produced by rv-platform's ResultProcessor. The CSV
has columns: apk, rep, timeout, tool, cov_act, cov_method, cov_rv_method, errors.

This module is imported dynamically by ``calibration_orchestrator.py`` when
the ``--tool`` flag starts with ``aperv``.

Usage:
    from aperv_objective import compute_score

    score = compute_score("results/trial_42/")
"""

import logging
from pathlib import Path

import pandas as pd
from scipy.stats import trim_mean

log = logging.getLogger(__name__)

# Equal weights: both coverage dimensions are equally important for calibration.
# MOP coverage measures how well the tool reaches monitored operations (the
# primary goal of RV-guided testing). Method coverage measures general
# exploration depth. The 50/50 split prevents over-optimizing for one metric.
MOP_WEIGHT = 0.50
METHOD_WEIGHT = 0.50

# Fraction to cut from each end of the distribution (10% = top/bottom 10%).
# This makes the score robust to a few APKs that crash on launch (0% coverage)
# or have anomalously high coverage (trivially small apps).
TRIM_PROPORTION = 0.1


def compute_score(results_dir: str) -> float:
    """Compute calibration score from a trial's summary.csv.

    Uses trimmed mean (cuts 10% extremes from each side) for robustness
    against outlier APKs that crash or get stuck.

    Args:
        results_dir: Path to the trial results directory (contains summary.csv).

    Returns:
        Composite score in [0, 100]. Returns 0.0 on error.
    """
    summary_path = Path(results_dir) / "summary.csv"
    if not summary_path.exists():
        log.warning(f"summary.csv not found in {results_dir}")
        return 0.0

    try:
        df = pd.read_csv(summary_path)
    except Exception as e:
        log.warning(f"Failed to read {summary_path}: {e}")
        return 0.0

    if df.empty:
        log.warning(f"Empty summary.csv in {results_dir}")
        return 0.0

    # When reps > 1, each APK has multiple rows. First average within each APK
    # (noise reduction), then apply trimmed mean across APK averages (outlier
    # robustness). With 1 rep this is a no-op (groupby returns same values).
    apk_means = df.groupby("apk")[["cov_method", "cov_rv_method"]].mean()
    avg_method = trim_mean(apk_means["cov_method"].values, TRIM_PROPORTION)
    avg_mop = trim_mean(apk_means["cov_rv_method"].values, TRIM_PROPORTION)

    score = MOP_WEIGHT * avg_mop + METHOD_WEIGHT * avg_method

    log.info(
        f"Score={score:.2f} (method={avg_method:.2f}%, mop={avg_mop:.2f}%) "
        f"from {len(apk_means)} APKs ({len(df)} rows) in {results_dir} "
        f"[trimmed mean, cut={TRIM_PROPORTION}]"
    )
    return score

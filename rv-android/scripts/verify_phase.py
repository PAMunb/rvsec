#!/usr/bin/env python3
"""Phase verification for the calibration execution campaign.

Each function validates the outputs of one calibration phase, checking file
existence, row counts, data integrity, and phase-specific acceptance criteria.
All verification functions are pure (Path in, VerificationResult out) and
unit-testable without Docker or actual experiment results.

Usage:
    uv run python scripts/verify_phase.py b --results-dir ./results/baseline_v2
    uv run python scripts/verify_phase.py c --results-dir ./results/calibration_macro_v2
    uv run python scripts/verify_phase.py d --results-dir ./results/calibration_micro_v2 --macro-dir ./results/calibration_macro_v2
    uv run python scripts/verify_phase.py e --results-dir ./results/validation_v2 --baseline-dir ./results/baseline_v2
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass
class Check:
    """A single verification check result."""

    name: str
    passed: bool
    detail: str


@dataclass
class VerificationResult:
    """Result of verifying a phase's outputs."""

    phase: str
    checks: list[Check] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def summary(self) -> str:
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c.passed)
        return f"Phase {self.phase}: {passed}/{total} checks passed"


def verify_phase_b(results_dir: Path, n_batches: int = 6, expected_rows: int = 945) -> VerificationResult:
    """Verify Phase B (baseline) results.

    Checks:
    - All batch summary CSVs exist
    - Aggregated summary.csv exists with expected row count
    - All 3 tools present in summary
    - BASELINE_MAX_ERRORS is a finite positive number
    - aggregated_summary.csv symlink exists
    """
    result = VerificationResult(phase="B")

    # Check batch summaries exist
    missing_batches = []
    for i in range(n_batches):
        csv_path = results_dir / f"batch_{i}" / f"batch_{i}" / "summary.csv"
        if not csv_path.exists():
            missing_batches.append(i)
    result.checks.append(Check(
        name="batch_summaries_exist",
        passed=len(missing_batches) == 0,
        detail=f"Missing batches: {missing_batches}" if missing_batches else f"All {n_batches} batch summaries found",
    ))

    # Check aggregated summary
    summary_path = results_dir / "summary.csv"
    if summary_path.exists():
        df = pd.read_csv(summary_path)
        row_count = len(df)
        result.checks.append(Check(
            name="aggregated_row_count",
            passed=row_count == expected_rows,
            detail=f"{row_count} rows (expected {expected_rows})",
        ))

        # Check tools
        expected_tools = {"ape", "fastbot", "rvagent"}
        actual_tools = set(df["tool"].unique()) if "tool" in df.columns else set()
        # Normalize: rvagent may appear as rvagent:pure_algorithm
        normalized_tools = set()
        for t in actual_tools:
            base = t.split(":")[0] if ":" in t else t
            normalized_tools.add(base)
        result.checks.append(Check(
            name="all_tools_present",
            passed=expected_tools.issubset(normalized_tools),
            detail=f"Tools found: {sorted(actual_tools)}",
        ))

        # Check BASELINE_MAX_ERRORS
        if "tool" in df.columns and "errors" in df.columns:
            max_errors = df.groupby("tool")["errors"].mean().max()
            is_valid = pd.notna(max_errors) and max_errors > 0
            result.checks.append(Check(
                name="baseline_max_errors",
                passed=is_valid,
                detail=f"BASELINE_MAX_ERRORS = {max_errors:.2f}" if is_valid else f"Invalid value: {max_errors}",
            ))
        else:
            result.checks.append(Check(
                name="baseline_max_errors",
                passed=False,
                detail="Missing 'tool' or 'errors' column in summary.csv",
            ))
    else:
        result.checks.append(Check(
            name="aggregated_row_count",
            passed=False,
            detail=f"summary.csv not found at {summary_path}",
        ))

    # Check symlink
    symlink_path = results_dir / "aggregated_summary.csv"
    result.checks.append(Check(
        name="aggregated_symlink",
        passed=symlink_path.is_symlink(),
        detail="Symlink exists" if symlink_path.is_symlink() else "Symlink missing",
    ))

    return result


def verify_phase_c(results_dir: Path, expected_trials: int = 80) -> VerificationResult:
    """Verify Phase C (macro calibration) results.

    Checks:
    - trial_history.json exists with expected trial count
    - best_score > 0.0 in optimal_params.json
    - Convergence: last 20 trials score higher than first 20 on average
    - param_string.txt exists and is non-empty
    """
    result = VerificationResult(phase="C")

    # Check trial history
    history_path = results_dir / "trial_history.json"
    trials = _load_trial_history(history_path)
    if trials is not None:
        result.checks.append(Check(
            name="trial_count",
            passed=len(trials) == expected_trials,
            detail=f"{len(trials)} trials (expected {expected_trials})",
        ))

        # Check convergence
        scores = [t["value"] for t in trials if t.get("value") is not None]
        if len(scores) >= 40:
            mean_first_20 = sum(scores[:20]) / 20
            mean_last_20 = sum(scores[-20:]) / 20
            converged = mean_last_20 > mean_first_20
            result.checks.append(Check(
                name="convergence",
                passed=converged,
                detail=f"First 20 mean: {mean_first_20:.4f}, Last 20 mean: {mean_last_20:.4f}",
            ))
        else:
            result.checks.append(Check(
                name="convergence",
                passed=False,
                detail=f"Not enough scored trials ({len(scores)}) to check convergence",
            ))
    else:
        result.checks.append(Check(
            name="trial_count",
            passed=False,
            detail=f"trial_history.json not found at {history_path}",
        ))

    # Check optimal params
    _check_optimal_params(result, results_dir)

    # Check param_string.txt
    param_string_path = results_dir / "param_string.txt"
    if param_string_path.exists():
        content = param_string_path.read_text().strip()
        result.checks.append(Check(
            name="param_string",
            passed=len(content) > 0 and "=" in content,
            detail=f"DSL: {content[:80]}..." if len(content) > 80 else f"DSL: {content}",
        ))
    else:
        result.checks.append(Check(
            name="param_string",
            passed=False,
            detail="param_string.txt not found",
        ))

    return result


def verify_phase_d(results_dir: Path, macro_dir: Path | None = None, expected_trials: int = 100) -> VerificationResult:
    """Verify Phase D (micro calibration) results.

    Checks:
    - trial_history.json exists with expected trial count
    - best_score > 0.0 in optimal_params.json
    - optimal_params.json contains all 24 parameters (8 macro + 16 micro)
    - Score improvement over macro phase (if macro_dir provided)
    """
    result = VerificationResult(phase="D")

    # Check trial history
    history_path = results_dir / "trial_history.json"
    trials = _load_trial_history(history_path)
    if trials is not None:
        result.checks.append(Check(
            name="trial_count",
            passed=len(trials) == expected_trials,
            detail=f"{len(trials)} trials (expected {expected_trials})",
        ))
    else:
        result.checks.append(Check(
            name="trial_count",
            passed=False,
            detail=f"trial_history.json not found at {history_path}",
        ))

    # Check optimal params
    _check_optimal_params(result, results_dir)

    # Check parameter count (should be 24 = 8 macro + 16 micro)
    optimal_path = results_dir / "optimal_params.json"
    if optimal_path.exists():
        with open(optimal_path) as f:
            data = json.load(f)
        param_count = len(data.get("best_params", {}))
        result.checks.append(Check(
            name="parameter_count",
            passed=param_count == 24,
            detail=f"{param_count} parameters (expected 24)",
        ))
    else:
        result.checks.append(Check(
            name="parameter_count",
            passed=False,
            detail="optimal_params.json not found",
        ))

    # Compare with macro score
    if macro_dir is not None:
        macro_optimal = macro_dir / "optimal_params.json"
        if macro_optimal.exists() and optimal_path.exists():
            with open(macro_optimal) as f:
                macro_data = json.load(f)
            with open(optimal_path) as f:
                micro_data = json.load(f)
            macro_score = macro_data.get("best_score", 0)
            micro_score = micro_data.get("best_score", 0)
            if macro_score > 0:
                improvement = (micro_score - macro_score) / macro_score * 100
                result.checks.append(Check(
                    name="score_improvement",
                    passed=micro_score >= macro_score,
                    detail=f"Macro: {macro_score:.4f}, Micro: {micro_score:.4f} ({improvement:+.1f}%)",
                ))
            else:
                result.checks.append(Check(
                    name="score_improvement",
                    passed=False,
                    detail=f"Macro score is 0 — cannot compute improvement",
                ))

    return result


def verify_phase_e(
    results_dir: Path,
    baseline_dir: Path | None = None,
    expected_rows: int = 270,
) -> VerificationResult:
    """Verify Phase E (validation) results.

    Checks:
    - summary.csv exists with expected row count
    - All 3 tools present
    - Statistical comparison with baseline (if baseline_dir provided)
    """
    result = VerificationResult(phase="E")

    summary_path = results_dir / "summary.csv"
    if summary_path.exists():
        df = pd.read_csv(summary_path)
        row_count = len(df)
        result.checks.append(Check(
            name="row_count",
            passed=row_count == expected_rows,
            detail=f"{row_count} rows (expected {expected_rows})",
        ))

        # Check tools
        expected_tools = {"ape", "fastbot", "rvagent"}
        actual_tools = set(df["tool"].unique()) if "tool" in df.columns else set()
        normalized_tools = set()
        for t in actual_tools:
            base = t.split(":")[0] if ":" in t else t
            normalized_tools.add(base)
        result.checks.append(Check(
            name="all_tools_present",
            passed=expected_tools.issubset(normalized_tools),
            detail=f"Tools found: {sorted(actual_tools)}",
        ))

        # Statistical comparison
        if baseline_dir is not None:
            baseline_summary = baseline_dir / "summary.csv"
            if baseline_summary.exists() and "cov_method" in df.columns:
                baseline_df = pd.read_csv(baseline_summary)
                holdout_apks = set(df["apk"].unique())

                base_rv = baseline_df[
                    (baseline_df["apk"].isin(holdout_apks))
                    & (baseline_df["tool"].str.startswith("rvagent"))
                ]
                val_rv = df[df["tool"].str.startswith("rvagent")]

                if len(base_rv) > 0 and len(val_rv) > 0:
                    base_cov = base_rv["cov_method"].mean()
                    val_cov = val_rv["cov_method"].mean()
                    improvement = val_cov - base_cov

                    result.checks.append(Check(
                        name="coverage_comparison",
                        passed=True,  # Informational — no hard gate
                        detail=f"Baseline RVAgent: {base_cov:.2f}%, Calibrated: {val_cov:.2f}% (diff: {improvement:+.2f}%)",
                    ))

                    if "errors" in base_rv.columns and "errors" in val_rv.columns:
                        base_err = base_rv["errors"].mean()
                        val_err = val_rv["errors"].mean()
                        result.checks.append(Check(
                            name="error_comparison",
                            passed=True,  # Informational
                            detail=f"Baseline errors: {base_err:.2f}, Calibrated: {val_err:.2f}",
                        ))
    else:
        result.checks.append(Check(
            name="row_count",
            passed=False,
            detail=f"summary.csv not found at {summary_path}",
        ))

    return result


# --- Helper functions ---


def _load_trial_history(path: Path) -> list[dict] | None:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _check_optimal_params(result: VerificationResult, results_dir: Path) -> None:
    optimal_path = results_dir / "optimal_params.json"
    if optimal_path.exists():
        with open(optimal_path) as f:
            data = json.load(f)
        best_score = data.get("best_score", 0)
        result.checks.append(Check(
            name="best_score",
            passed=best_score > 0.0,
            detail=f"Best score: {best_score:.4f}",
        ))
    else:
        result.checks.append(Check(
            name="best_score",
            passed=False,
            detail="optimal_params.json not found",
        ))


def _print_result(result: VerificationResult) -> None:
    print(f"\n{'=' * 50}")
    print(result.summary)
    print(f"{'=' * 50}")
    for check in result.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"  [{status}] {check.name}: {check.detail}")

    if result.passed:
        print(f"\nPhase {result.phase} verification PASSED — gate open for next phase.")
    else:
        failed = [c.name for c in result.checks if not c.passed]
        print(f"\nPhase {result.phase} verification FAILED — blocked checks: {failed}")


# --- CLI ---


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify calibration phase results.")
    parser.add_argument("phase", choices=["b", "c", "d", "e"], help="Phase to verify")
    parser.add_argument("--results-dir", required=True, type=Path, help="Path to phase results")
    parser.add_argument("--baseline-dir", type=Path, help="Path to baseline results (Phase E)")
    parser.add_argument("--macro-dir", type=Path, help="Path to macro results (Phase D)")
    args = parser.parse_args()

    if args.phase == "b":
        result = verify_phase_b(args.results_dir)
    elif args.phase == "c":
        result = verify_phase_c(args.results_dir)
    elif args.phase == "d":
        result = verify_phase_d(args.results_dir, macro_dir=args.macro_dir)
    elif args.phase == "e":
        result = verify_phase_e(args.results_dir, baseline_dir=args.baseline_dir)

    _print_result(result)
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()

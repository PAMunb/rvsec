"""Unit tests for scripts/verify_phase.py.

All tests use tmp_path fixtures to create synthetic result structures.
No Docker, no actual experiment results required.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

# Import from scripts/ — add to path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from verify_phase import (
    Check,
    VerificationResult,
    verify_phase_b,
    verify_phase_c,
    verify_phase_d,
    verify_phase_e,
)


# --- Helpers ---


def _create_summary_csv(path: Path, rows: list[dict]) -> None:
    """Create a summary.csv file from row dicts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)


def _create_baseline_structure(base_dir: Path, n_batches: int = 6, rows_per_batch: int = 158) -> None:
    """Create a complete Phase B directory structure."""
    all_rows = []
    tools = ["ape", "fastbot", "rvagent"]

    for i in range(n_batches):
        batch_rows = []
        for j in range(rows_per_batch):
            tool = tools[j % len(tools)]
            batch_rows.append({
                "apk": f"app_{i * rows_per_batch + j}.apk",
                "tool": tool,
                "cov_method": 45.0 + j * 0.1,
                "errors": 3.0 + (j % 5),
            })
        _create_summary_csv(
            base_dir / f"batch_{i}" / f"batch_{i}" / "summary.csv",
            batch_rows,
        )
        all_rows.extend(batch_rows)

    # Aggregated summary (truncate to expected_rows if needed)
    _create_summary_csv(base_dir / "summary.csv", all_rows)
    # Symlink
    symlink_path = base_dir / "aggregated_summary.csv"
    if symlink_path.exists():
        symlink_path.unlink()
    symlink_path.symlink_to("summary.csv")


def _create_calibration_structure(
    results_dir: Path,
    n_trials: int,
    best_score: float = 0.35,
    best_params: dict | None = None,
    scores: list[float] | None = None,
) -> None:
    """Create a complete Phase C or D directory structure."""
    if best_params is None:
        best_params = {"mop_direct_score": 350.0, "stochastic_probability": 0.55}
    if scores is None:
        # Simulate convergence: first half lower, second half higher
        scores = [0.1 + i * 0.005 for i in range(n_trials)]

    results_dir.mkdir(parents=True, exist_ok=True)

    # trial_history.json
    trials = []
    for i, score in enumerate(scores):
        trials.append({
            "number": i,
            "params": best_params,
            "value": score,
            "state": "COMPLETE",
        })
    with open(results_dir / "trial_history.json", "w") as f:
        json.dump(trials, f)

    # optimal_params.json
    with open(results_dir / "optimal_params.json", "w") as f:
        json.dump({
            "phase": "macro",
            "seed": 42,
            "best_score": best_score,
            "best_params": best_params,
            "n_trials": n_trials,
        }, f)

    # param_string.txt
    parts = []
    for k, v in best_params.items():
        if isinstance(v, float):
            parts.append(f"{k}={v:.4f}")
        else:
            parts.append(f"{k}={v}")
    with open(results_dir / "param_string.txt", "w") as f:
        f.write(",".join(parts))


# --- Phase B Tests ---


class TestVerifyPhaseB:
    def test_all_checks_pass(self, tmp_path):
        """Complete baseline structure passes all checks."""
        # 6 batches, 158 rows each = 948. We use 945 to match expected.
        # Simpler: use n_batches=3, rows_per_batch=315 = 945
        base_dir = tmp_path / "baseline"
        base_dir.mkdir()
        # Create 6 batch summaries and aggregated with exactly 945 rows
        tools = ["ape", "fastbot", "rvagent"]
        all_rows = []
        for i in range(6):
            batch_rows = []
            for j in range(158 if i < 3 else 157):
                tool = tools[j % len(tools)]
                batch_rows.append({
                    "apk": f"app_{len(all_rows)}.apk",
                    "tool": tool,
                    "cov_method": 45.0,
                    "errors": 3.0,
                })
                all_rows.append(batch_rows[-1])
            _create_summary_csv(
                base_dir / f"batch_{i}" / f"batch_{i}" / "summary.csv",
                batch_rows,
            )
        _create_summary_csv(base_dir / "summary.csv", all_rows)
        (base_dir / "aggregated_summary.csv").symlink_to("summary.csv")

        result = verify_phase_b(base_dir, n_batches=6, expected_rows=len(all_rows))
        assert result.passed
        assert result.phase == "B"

    def test_missing_batch(self, tmp_path):
        """Missing batch directory fails the batch_summaries_exist check."""
        base_dir = tmp_path / "baseline"
        base_dir.mkdir()
        # Create only 5 of 6 batches
        for i in range(5):
            _create_summary_csv(
                base_dir / f"batch_{i}" / f"batch_{i}" / "summary.csv",
                [{"apk": "a.apk", "tool": "ape", "cov_method": 50, "errors": 1}],
            )
        result = verify_phase_b(base_dir, n_batches=6, expected_rows=5)
        batch_check = next(c for c in result.checks if c.name == "batch_summaries_exist")
        assert not batch_check.passed
        assert "5" in batch_check.detail

    def test_wrong_row_count(self, tmp_path):
        """Aggregated CSV with wrong row count fails."""
        base_dir = tmp_path / "baseline"
        base_dir.mkdir()
        _create_summary_csv(
            base_dir / "summary.csv",
            [{"apk": f"a{i}.apk", "tool": "ape", "cov_method": 50, "errors": 1} for i in range(100)],
        )
        result = verify_phase_b(base_dir, n_batches=0, expected_rows=945)
        row_check = next(c for c in result.checks if c.name == "aggregated_row_count")
        assert not row_check.passed

    def test_missing_tool(self, tmp_path):
        """Summary with only 2 tools fails the all_tools_present check."""
        base_dir = tmp_path / "baseline"
        base_dir.mkdir()
        rows = [
            {"apk": "a.apk", "tool": "ape", "cov_method": 50, "errors": 1},
            {"apk": "b.apk", "tool": "fastbot", "cov_method": 50, "errors": 1},
        ]
        _create_summary_csv(base_dir / "summary.csv", rows)
        result = verify_phase_b(base_dir, n_batches=0, expected_rows=2)
        tools_check = next(c for c in result.checks if c.name == "all_tools_present")
        assert not tools_check.passed

    def test_missing_symlink(self, tmp_path):
        """Missing aggregated_summary.csv symlink fails."""
        base_dir = tmp_path / "baseline"
        base_dir.mkdir()
        _create_summary_csv(
            base_dir / "summary.csv",
            [{"apk": "a.apk", "tool": "ape", "cov_method": 50, "errors": 1}],
        )
        result = verify_phase_b(base_dir, n_batches=0, expected_rows=1)
        symlink_check = next(c for c in result.checks if c.name == "aggregated_symlink")
        assert not symlink_check.passed

    def test_baseline_max_errors(self, tmp_path):
        """BASELINE_MAX_ERRORS computed correctly from tool means."""
        base_dir = tmp_path / "baseline"
        base_dir.mkdir()
        rows = [
            {"apk": "a.apk", "tool": "ape", "cov_method": 50, "errors": 10},
            {"apk": "b.apk", "tool": "ape", "cov_method": 50, "errors": 6},
            {"apk": "a.apk", "tool": "fastbot", "cov_method": 50, "errors": 2},
            {"apk": "b.apk", "tool": "fastbot", "cov_method": 50, "errors": 4},
            {"apk": "a.apk", "tool": "rvagent", "cov_method": 50, "errors": 5},
            {"apk": "b.apk", "tool": "rvagent", "cov_method": 50, "errors": 5},
        ]
        _create_summary_csv(base_dir / "summary.csv", rows)
        (base_dir / "aggregated_summary.csv").symlink_to("summary.csv")
        result = verify_phase_b(base_dir, n_batches=0, expected_rows=6)
        errors_check = next(c for c in result.checks if c.name == "baseline_max_errors")
        assert errors_check.passed
        # ape mean = 8.0, fastbot mean = 3.0, rvagent mean = 5.0 -> max = 8.0
        assert "8.00" in errors_check.detail


# --- Phase C Tests ---


class TestVerifyPhaseC:
    def test_all_checks_pass(self, tmp_path):
        """Complete macro calibration structure passes all checks."""
        results_dir = tmp_path / "macro"
        _create_calibration_structure(results_dir, n_trials=80, best_score=0.35)
        result = verify_phase_c(results_dir, expected_trials=80)
        assert result.passed

    def test_wrong_trial_count(self, tmp_path):
        """Fewer trials than expected fails."""
        results_dir = tmp_path / "macro"
        _create_calibration_structure(results_dir, n_trials=50, best_score=0.35)
        result = verify_phase_c(results_dir, expected_trials=80)
        trial_check = next(c for c in result.checks if c.name == "trial_count")
        assert not trial_check.passed

    def test_zero_best_score(self, tmp_path):
        """Best score of 0.0 fails."""
        results_dir = tmp_path / "macro"
        _create_calibration_structure(results_dir, n_trials=80, best_score=0.0)
        result = verify_phase_c(results_dir, expected_trials=80)
        score_check = next(c for c in result.checks if c.name == "best_score")
        assert not score_check.passed

    def test_no_convergence(self, tmp_path):
        """Decreasing scores (no convergence) fails the convergence check."""
        results_dir = tmp_path / "macro"
        # Reverse: high scores first, low scores last
        scores = [0.5 - i * 0.005 for i in range(80)]
        _create_calibration_structure(results_dir, n_trials=80, best_score=0.5, scores=scores)
        result = verify_phase_c(results_dir, expected_trials=80)
        conv_check = next(c for c in result.checks if c.name == "convergence")
        assert not conv_check.passed

    def test_missing_param_string(self, tmp_path):
        """Missing param_string.txt fails."""
        results_dir = tmp_path / "macro"
        _create_calibration_structure(results_dir, n_trials=80)
        (results_dir / "param_string.txt").unlink()
        result = verify_phase_c(results_dir, expected_trials=80)
        param_check = next(c for c in result.checks if c.name == "param_string")
        assert not param_check.passed

    def test_missing_trial_history(self, tmp_path):
        """Missing trial_history.json fails."""
        results_dir = tmp_path / "macro"
        results_dir.mkdir(parents=True)
        result = verify_phase_c(results_dir, expected_trials=80)
        trial_check = next(c for c in result.checks if c.name == "trial_count")
        assert not trial_check.passed


# --- Phase D Tests ---


class TestVerifyPhaseD:
    def test_all_checks_pass(self, tmp_path):
        """Complete micro calibration with 24 params passes."""
        results_dir = tmp_path / "micro"
        # 24 parameters (8 macro + 16 micro)
        params = {f"param_{i}": float(i) for i in range(24)}
        _create_calibration_structure(results_dir, n_trials=100, best_score=0.40, best_params=params)
        result = verify_phase_d(results_dir, expected_trials=100)
        assert result.passed

    def test_wrong_parameter_count(self, tmp_path):
        """Fewer than 24 parameters fails."""
        results_dir = tmp_path / "micro"
        params = {f"param_{i}": float(i) for i in range(16)}
        _create_calibration_structure(results_dir, n_trials=100, best_score=0.40, best_params=params)
        result = verify_phase_d(results_dir, expected_trials=100)
        param_check = next(c for c in result.checks if c.name == "parameter_count")
        assert not param_check.passed

    def test_score_improvement_over_macro(self, tmp_path):
        """Micro score higher than macro passes score_improvement."""
        macro_dir = tmp_path / "macro"
        micro_dir = tmp_path / "micro"
        params = {f"param_{i}": float(i) for i in range(24)}
        _create_calibration_structure(macro_dir, n_trials=80, best_score=0.30, best_params=params)
        _create_calibration_structure(micro_dir, n_trials=100, best_score=0.40, best_params=params)
        result = verify_phase_d(micro_dir, macro_dir=macro_dir, expected_trials=100)
        improvement_check = next(c for c in result.checks if c.name == "score_improvement")
        assert improvement_check.passed
        assert "+33.3%" in improvement_check.detail

    def test_score_regression(self, tmp_path):
        """Micro score lower than macro fails score_improvement."""
        macro_dir = tmp_path / "macro"
        micro_dir = tmp_path / "micro"
        params = {f"param_{i}": float(i) for i in range(24)}
        _create_calibration_structure(macro_dir, n_trials=80, best_score=0.40, best_params=params)
        _create_calibration_structure(micro_dir, n_trials=100, best_score=0.35, best_params=params)
        result = verify_phase_d(micro_dir, macro_dir=macro_dir, expected_trials=100)
        improvement_check = next(c for c in result.checks if c.name == "score_improvement")
        assert not improvement_check.passed


# --- Phase E Tests ---


class TestVerifyPhaseE:
    def test_all_checks_pass(self, tmp_path):
        """Complete validation results pass."""
        results_dir = tmp_path / "validation"
        results_dir.mkdir()
        tools = ["ape", "fastbot", "rvagent:multimode"]
        rows = []
        for i in range(90):  # 270 total = 90 per tool
            for tool in tools:
                rows.append({
                    "apk": f"holdout_{i % 30}.apk",
                    "tool": tool,
                    "cov_method": 50.0,
                    "errors": 2.0,
                })
        _create_summary_csv(results_dir / "summary.csv", rows)
        result = verify_phase_e(results_dir, expected_rows=270)
        assert result.passed

    def test_wrong_row_count(self, tmp_path):
        """Wrong row count fails."""
        results_dir = tmp_path / "validation"
        results_dir.mkdir()
        _create_summary_csv(
            results_dir / "summary.csv",
            [{"apk": "a.apk", "tool": "ape", "cov_method": 50, "errors": 1}],
        )
        result = verify_phase_e(results_dir, expected_rows=270)
        row_check = next(c for c in result.checks if c.name == "row_count")
        assert not row_check.passed

    def test_baseline_comparison(self, tmp_path):
        """Statistical comparison with baseline produces coverage_comparison check."""
        baseline_dir = tmp_path / "baseline"
        baseline_dir.mkdir()
        validation_dir = tmp_path / "validation"
        validation_dir.mkdir()

        holdout_apks = [f"holdout_{i}.apk" for i in range(10)]
        baseline_rows = []
        for apk in holdout_apks:
            baseline_rows.append({"apk": apk, "tool": "rvagent", "cov_method": 40.0, "errors": 5.0})
        _create_summary_csv(baseline_dir / "summary.csv", baseline_rows)

        val_rows = []
        for apk in holdout_apks:
            val_rows.append({"apk": apk, "tool": "rvagent:multimode", "cov_method": 55.0, "errors": 3.0})
        _create_summary_csv(validation_dir / "summary.csv", val_rows)

        result = verify_phase_e(validation_dir, baseline_dir=baseline_dir, expected_rows=10)
        cov_check = next(c for c in result.checks if c.name == "coverage_comparison")
        assert cov_check.passed
        assert "40.00%" in cov_check.detail
        assert "55.00%" in cov_check.detail

    def test_missing_summary(self, tmp_path):
        """Missing summary.csv fails."""
        results_dir = tmp_path / "validation"
        results_dir.mkdir()
        result = verify_phase_e(results_dir)
        row_check = next(c for c in result.checks if c.name == "row_count")
        assert not row_check.passed


# --- VerificationResult Tests ---


class TestVerificationResult:
    def test_all_passed(self):
        result = VerificationResult(phase="X", checks=[
            Check("a", True, "ok"),
            Check("b", True, "ok"),
        ])
        assert result.passed
        assert "2/2" in result.summary

    def test_one_failed(self):
        result = VerificationResult(phase="X", checks=[
            Check("a", True, "ok"),
            Check("b", False, "fail"),
        ])
        assert not result.passed
        assert "1/2" in result.summary

    def test_empty_checks(self):
        result = VerificationResult(phase="X")
        assert result.passed  # vacuously true

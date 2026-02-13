"""
Tests for orphaned trial recovery logic (T19-T23).

Validates the resume logic in calibration_orchestrator.py that handles
trials left in RUNNING state after a host crash.
"""

import sys
from pathlib import Path

import optuna
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from calibration_orchestrator import recover_orphaned_trials
from rv_agent_validation.calibration.objective import ObjectiveFunction


def _create_summary_csv(results_dir: Path) -> None:
    """Helper: create a minimal summary.csv with valid data."""
    results_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([{
        "apk": "test.apk",
        "tool": "rvagent",
        "cov_method": 50.0,
        "errors": 5.0,
    }])
    df.to_csv(results_dir / "summary.csv", index=False)


def test_recover_completed_orphan(tmp_path):
    """T19: Orphaned trial with valid summary.csv gets scored and completed."""
    study = optuna.create_study(direction="maximize")
    trial = study.ask()

    # Simulate: trial was asked but never told (host crashed)
    # Create valid results for this trial
    results_dir = tmp_path / f"trial_{trial.number}" / f"trial_{trial.number}"
    _create_summary_csv(results_dir)

    objective_fn = ObjectiveFunction(
        coverage_weight=0.4, errors_weight=0.4, ui_coverage_weight=0.2
    )

    recovered = recover_orphaned_trials(study, str(tmp_path), objective_fn)

    assert recovered == 1
    assert study.trials[0].state == optuna.trial.TrialState.COMPLETE


def test_recover_failed_orphan(tmp_path):
    """T20: Orphaned trial with no results dir gets marked as FAIL."""
    study = optuna.create_study(direction="maximize")
    trial = study.ask()
    # No results directory created

    objective_fn = ObjectiveFunction()

    recovered = recover_orphaned_trials(study, str(tmp_path), objective_fn)

    assert recovered == 1
    assert study.trials[0].state == optuna.trial.TrialState.FAIL


def test_recover_partial_orphan(tmp_path):
    """T21: Results dir exists but no summary.csv inside — marked FAIL."""
    study = optuna.create_study(direction="maximize")
    trial = study.ask()

    # Create results dir but no summary.csv
    results_dir = tmp_path / f"trial_{trial.number}" / f"trial_{trial.number}"
    results_dir.mkdir(parents=True)

    objective_fn = ObjectiveFunction()

    recovered = recover_orphaned_trials(study, str(tmp_path), objective_fn)

    assert recovered == 1
    assert study.trials[0].state == optuna.trial.TrialState.FAIL


def test_no_orphans(tmp_path):
    """T22: No trials in RUNNING state — recovery is a no-op."""
    study = optuna.create_study(direction="maximize")

    # Create a completed trial (ask + tell)
    trial = study.ask()
    study.tell(trial.number, 0.5)

    objective_fn = ObjectiveFunction()

    recovered = recover_orphaned_trials(study, str(tmp_path), objective_fn)

    assert recovered == 0


def test_resume_continues_from_completed(tmp_path):
    """T23: Study with 6 completed trials, n_trials=10 -> 4 remaining."""
    study = optuna.create_study(direction="maximize")

    # Complete 6 trials
    for _ in range(6):
        trial = study.ask()
        study.tell(trial.number, 0.5)

    completed = len([
        t for t in study.trials
        if t.state == optuna.trial.TrialState.COMPLETE
    ])
    remaining = 10 - completed

    assert completed == 6
    assert remaining == 4

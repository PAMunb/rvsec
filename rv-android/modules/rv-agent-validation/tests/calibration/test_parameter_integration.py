"""
Tests for integration with existing calibration module (T28-T35).

Validates that the orchestrator correctly uses parameter_space.py and
objective.py from the existing calibration module.
"""

from pathlib import Path

import optuna
import pandas as pd

from rv_agent_validation.calibration.parameter_space import (
    CalibrationPhase,
    suggest_params,
    params_to_tool_spec,
)
from rv_agent_validation.calibration.objective import ObjectiveFunction


def test_suggest_params_with_ask_trial():
    """T28: study.ask() trial works with suggest_params() — 8 macro params in range."""
    study = optuna.create_study(direction="maximize")
    trial = study.ask()

    params = suggest_params(trial, CalibrationPhase.MACRO)

    assert len(params) == 8
    assert "mop_direct_score" in params
    assert 200.0 <= params["mop_direct_score"] <= 500.0
    assert "stochastic_probability" in params
    assert 0.1 <= params["stochastic_probability"] <= 0.7


def test_params_to_tool_spec_format():
    """T29: params_to_tool_spec produces correct DSL format."""
    params = {"mop_direct_score": 350.0, "max_re_enables": 8}

    spec = params_to_tool_spec(params)

    assert "mop_direct_score=350.0000" in spec
    assert "max_re_enables=8" in spec
    assert "," in spec


def test_tool_spec_dsl_string():
    """T30: Full DSL string matches expected format."""
    params = {"mop_direct_score": 350.0, "max_re_enables": 8}
    spec = params_to_tool_spec(params)
    full = f"rvagent:pure_algorithm@{spec}"

    assert full.startswith("rvagent:pure_algorithm@")
    assert "mop_direct_score=350.0000" in full
    assert "max_re_enables=8" in full


def test_objective_compute_with_mock_results(tmp_path):
    """T31: ObjectiveFunction.compute() returns expected score from synthetic data."""
    # Create a summary.csv with known values
    df = pd.DataFrame([{
        "apk": "test.apk",
        "tool": "rvagent",
        "cov_method": 50.0,
        "errors": 5.0,
    }])
    df.to_csv(tmp_path / "summary.csv", index=False)

    objective_fn = ObjectiveFunction(
        coverage_weight=0.4,
        errors_weight=0.4,
        ui_coverage_weight=0.2,
    )

    score = objective_fn.compute(str(tmp_path))

    assert score > 0.0
    # 0.4 * 50.0 (cov) + 0.4 * normalized_errors + 0.2 * 0.0 (no metrics files)
    # normalized_errors = min(5.0 * 10, 100) = 50.0 (fallback normalization)
    # expected = 0.4 * 50.0 + 0.4 * 50.0 + 0.2 * 0.0 = 40.0
    assert abs(score - 40.0) < 1.0


def test_objective_missing_summary(tmp_path):
    """T32: ObjectiveFunction.compute() on empty dir returns 0.0."""
    objective_fn = ObjectiveFunction()
    score = objective_fn.compute(str(tmp_path))
    assert score == 0.0


def test_baseline_max_errors_computation(tmp_path):
    """T33: compute_baseline_max_errors with synthetic baseline CSV."""
    # Create summary.csv with multiple tools
    rows = []
    for tool, avg_errors in [("ape", 5.0), ("fastbot", 8.0), ("rvagent", 3.0)]:
        for i in range(3):
            rows.append({
                "apk": f"app_{i}.apk",
                "tool": tool,
                "errors": avg_errors,
            })
    pd.DataFrame(rows).to_csv(tmp_path / "summary.csv", index=False)

    max_errors = ObjectiveFunction.compute_baseline_max_errors(str(tmp_path))

    # Max average errors across tools = 8.0
    assert abs(max_errors - 8.0) < 0.01


def test_macro_phase_suggests_8_params():
    """T34: suggest_params with MACRO phase suggests exactly 8 parameters."""
    study = optuna.create_study(direction="maximize")
    trial = study.ask()

    params = suggest_params(trial, CalibrationPhase.MACRO)

    assert len(params) == 8


def test_micro_phase_suggests_16_params():
    """T35: suggest_params with MICRO phase suggests exactly 16 parameters."""
    study = optuna.create_study(direction="maximize")
    trial = study.ask()

    params = suggest_params(trial, CalibrationPhase.MICRO)

    assert len(params) == 16

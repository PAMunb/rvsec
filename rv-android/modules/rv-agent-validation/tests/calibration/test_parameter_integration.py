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
    """T28: study.ask() trial works with suggest_params() — 11 macro params in range."""
    study = optuna.create_study(direction="maximize")
    trial = study.ask()

    params = suggest_params(trial, CalibrationPhase.MACRO)

    assert len(params) == 11
    assert "mop_direct_score" in params
    assert 300.0 <= params["mop_direct_score"] <= 700.0
    assert "stochastic_probability" in params
    assert 0.05 <= params["stochastic_probability"] <= 0.4
    # Widened ranges (Task 20b)
    assert "coverage_density_weight" in params
    assert 50.0 <= params["coverage_density_weight"] <= 600.0
    assert "visitation_penalty_factor" in params
    assert -40.0 <= params["visitation_penalty_factor"] <= -3.0
    # New gh26/gh18 MACRO params
    assert "backtrack_saturation_threshold" in params
    assert "coverage_density_weight" in params
    assert "error_detection_confidence" in params


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
    import math

    # Create a summary.csv with known values
    df = pd.DataFrame([{
        "apk": "test.apk",
        "tool": "rvagent",
        "cov_method": 50.0,
        "errors": 5.0,
    }])
    df.to_csv(tmp_path / "summary.csv", index=False)

    objective_fn = ObjectiveFunction(
        coverage_weight=0.3,
        errors_weight=0.2,
        ui_coverage_weight=0.5,
    )

    score = objective_fn.compute(str(tmp_path))

    assert score > 0.0
    # 0.3 * 50.0 (cov) + 0.2 * normalized_errors + 0.5 * 0.0 (no metrics files)
    # Log normalization fallback (no baseline): ref=10.0
    # normalized_errors = log(1+5) / log(1+10) * 100 = log(6)/log(11)*100 ≈ 74.76
    expected_errors = math.log(6) / math.log(11) * 100
    expected = 0.3 * 50.0 + 0.2 * expected_errors + 0.5 * 0.0
    assert abs(score - expected) < 1.0


def test_objective_missing_summary(tmp_path):
    """T32: ObjectiveFunction.compute() on empty dir returns 0.0."""
    objective_fn = ObjectiveFunction()
    score = objective_fn.compute(str(tmp_path))
    assert score == 0.0


def test_baseline_max_errors_computation(tmp_path):
    """T33: compute_baseline_max_errors groups by APK, takes max per-APK mean."""
    # Create summary.csv with multiple tools and APKs
    rows = []
    for tool, errors_by_apk in [
        ("ape", [2.0, 10.0, 1.0]),
        ("fastbot", [3.0, 12.0, 2.0]),
        ("rvagent", [1.0, 8.0, 0.5]),
    ]:
        for i, err in enumerate(errors_by_apk):
            rows.append({
                "apk": f"app_{i}.apk",
                "tool": tool,
                "errors": err,
            })
    pd.DataFrame(rows).to_csv(tmp_path / "summary.csv", index=False)

    max_errors = ObjectiveFunction.compute_baseline_max_errors(str(tmp_path))

    # Per-APK means: app_0=(2+3+1)/3=2.0, app_1=(10+12+8)/3=10.0, app_2=(1+2+0.5)/3=1.17
    # Max per-APK mean = 10.0
    assert abs(max_errors - 10.0) < 0.01


def test_macro_phase_suggests_11_params():
    """T34: suggest_params with MACRO phase suggests exactly 11 parameters."""
    study = optuna.create_study(direction="maximize")
    trial = study.ask()

    params = suggest_params(trial, CalibrationPhase.MACRO)

    assert len(params) == 11


def test_micro_phase_suggests_24_params():
    """T35: suggest_params with MICRO phase suggests exactly 24 parameters."""
    study = optuna.create_study(direction="maximize")
    trial = study.ask()

    params = suggest_params(trial, CalibrationPhase.MICRO)

    assert len(params) == 24
    # Dead code params excluded from calibration
    assert "mop_nav_weight" not in params
    assert "llm_max_retries" not in params


def test_full_phase_suggests_35_params():
    """T36: suggest_params with FULL phase suggests all 35 parameters."""
    study = optuna.create_study(direction="maximize")
    trial = study.ask()

    params = suggest_params(trial, CalibrationPhase.FULL)

    assert len(params) == 35


def test_new_micro_params_exist():
    """T37: All new gh26/gh18 MICRO parameters are defined."""
    from rv_agent_validation.calibration.parameter_space import ALL_PARAMETERS

    param_names = {p.name for p in ALL_PARAMETERS}
    new_micro = [
        "mop_max_input_variations", "reward_gamma",
        "reward_score_weight", "error_max_indicator_size",
        "error_max_indicator_count", "spatial_edittext_boost",
        "spatial_spinner_boost", "spatial_min_match_threshold",
        "multi_value_saturation_threshold",
    ]
    for name in new_micro:
        assert name in param_names, f"Missing MICRO param: {name}"

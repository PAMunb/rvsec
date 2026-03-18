"""Parameter space for APE-RV calibration via Optuna.

Defines calibratable parameters in two phases:
- MACRO (13 effective): exploration engine + MOP weights (no LLM)
  - 14 params declared, but fuzzing_rate is conditional on do_fuzzing
- MICRO (4 effective): LLM routing mode + sampling params
  - llm_mode (3 categories) replaces 2 independent booleans to avoid
    the degenerate case where both triggers are off (= no LLM = MACRO)

Parameter names use Python snake_case. The aperv-tool's APERV_PROPERTY_MAPPING
converts them to Java ape.properties camelCase keys (e.g., default_epsilon →
ape.defaultEpsilon). Values pass as strings — Java Config.java parses them.

Post-analysis improvements applied (2026-03-18):
- step=10 for mop_weight_* and graph_stable_restart_threshold (reduce search space)
- log=True for throttle_ms and throttle_for_activity_transition (dense low-end sampling)
- Conditional fuzzing: fuzzing_rate skipped when do_fuzzing=false
- llm_mode categorical (3 options) replaces 2 independent booleans
- llm_temperature range expanded to [0.0, 0.7]

Usage:
    from aperv_parameter_space import CalibrationPhase, suggest_params, params_to_tool_spec
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CalibrationPhase(Enum):
    MACRO = "macro"  # exploration + MOP weights (no LLM)
    MICRO = "micro"  # LLM routing + sampling


@dataclass
class ParameterDef:
    name: str
    param_type: str  # "float", "int", "categorical"
    low: float  # ignored for categorical
    high: float  # ignored for categorical
    default: Any
    choices: Optional[List[str]] = None  # only for categorical
    step: Optional[int] = None  # only for int — reduces effective search space
    log: bool = False  # log-uniform sampling — denser at low end
    description: str = ""


# ---------------------------------------------------------------------------
# MACRO: 14 parameters — exploration engine + MOP weights
# Tool: aperv:sata_mop (no LLM, no SGLang needed)
#
# Note: fuzzing_rate is conditional on do_fuzzing — when do_fuzzing=false,
# fuzzing_rate is fixed at 0.0 (not suggested by Optuna). This reduces
# the effective dimensionality from 14 to 13 for those trials.
# ---------------------------------------------------------------------------

MACRO_PARAMETERS = [
    # Exploration parameters (11)
    ParameterDef(
        name="default_epsilon",
        param_type="float", low=0.01, high=0.20, default=0.05,
        description="Fraction of exploitation (least-visited) vs random actions",
    ),
    ParameterDef(
        name="graph_stable_restart_threshold",
        param_type="int", low=30, high=300, default=100, step=10,
        description="Steps without graph growth before restart",
    ),
    ParameterDef(
        name="state_stable_restart_threshold",
        param_type="int", low=20, high=150, default=50,
        description="Steps in same state before restart",
    ),
    ParameterDef(
        name="do_fuzzing",
        param_type="categorical", low=0, high=0, default="true",
        choices=["true", "false"],
        description="Enable/disable fuzzing entirely",
    ),
    ParameterDef(
        name="fuzzing_rate",
        param_type="float", low=0.0, high=0.10, default=0.02,
        description="Fraction of fuzzing actions per step (conditional on do_fuzzing)",
    ),
    ParameterDef(
        name="throttle_for_activity_transition",
        param_type="int", low=200, high=1000, default=500, log=True,
        description="Delay after activity transition (ms)",
    ),
    ParameterDef(
        name="throttle_ms",
        param_type="int", low=100, high=500, default=200, log=True,
        description="Base delay between actions (ms)",
    ),
    ParameterDef(
        name="max_extra_priority_aliased_actions",
        param_type="int", low=1, high=15, default=5,
        description="Priority boost for multi-target actions",
    ),
    ParameterDef(
        name="max_states_per_activity",
        param_type="int", low=5, high=30, default=10,
        description="Cap on states tracked per activity",
    ),
    ParameterDef(
        name="trivial_activity_rank_threshold",
        param_type="int", low=1, high=8, default=3,
        description="Rank threshold to classify activity as trivial",
    ),
    ParameterDef(
        name="do_back_to_trivial_activity",
        param_type="categorical", low=0, high=0, default="false",
        choices=["true", "false"],
        description="Allow backtracking to trivial activities",
    ),
    # MOP weight parameters (3) — step=10 reduces search space ~10x per param
    ParameterDef(
        name="mop_weight_direct",
        param_type="int", low=100, high=1000, default=500, step=10,
        description="Priority boost for direct MOP-reachable actions",
    ),
    ParameterDef(
        name="mop_weight_transitive",
        param_type="int", low=50, high=600, default=300, step=10,
        description="Priority boost for transitive MOP-reachable actions",
    ),
    ParameterDef(
        name="mop_weight_activity",
        param_type="int", low=10, high=200, default=100, step=10,
        description="Priority boost for MOP-reachable activity-level actions",
    ),
]

# ---------------------------------------------------------------------------
# MICRO: LLM routing and sampling
# Tool: aperv:sata_mop_llm (with LLM, SGLang required)
# MACRO params fixed at optimal values from macro phase
#
# llm_mode replaces 2 independent booleans (llm_on_new_state, llm_on_stagnation)
# to avoid the degenerate case where both=false (= no LLM calls = MACRO).
# The suggest_params function maps llm_mode back to the 2 Java properties.
# ---------------------------------------------------------------------------

MICRO_PARAMETERS = [
    ParameterDef(
        name="llm_mode",
        param_type="categorical", low=0, high=0, default="both",
        choices=["new_state_only", "stagnation_only", "both"],
        description="When to call LLM: on new states, on stagnation, or both",
    ),
    ParameterDef(
        name="llm_temperature",
        param_type="float", low=0.0, high=0.7, default=0.3,
        description="LLM sampling temperature (lower = more deterministic)",
    ),
    ParameterDef(
        name="llm_top_p",
        param_type="float", low=0.3, high=0.95, default=0.6,
        description="Nucleus sampling threshold",
    ),
    ParameterDef(
        name="llm_top_k",
        param_type="int", low=10, high=100, default=50,
        description="Top-K tokens considered for sampling",
    ),
]

# Mapping from llm_mode categorical to the 2 Java boolean properties
_LLM_MODE_MAP = {
    "new_state_only": {"llm_on_new_state": "true", "llm_on_stagnation": "false"},
    "stagnation_only": {"llm_on_new_state": "false", "llm_on_stagnation": "true"},
    "both": {"llm_on_new_state": "true", "llm_on_stagnation": "true"},
}


def get_parameters_for_phase(phase: CalibrationPhase) -> List[ParameterDef]:
    if phase == CalibrationPhase.MACRO:
        return MACRO_PARAMETERS
    elif phase == CalibrationPhase.MICRO:
        return MICRO_PARAMETERS
    raise ValueError(f"Unknown phase: {phase}")


def suggest_params(trial, phase: CalibrationPhase) -> Dict[str, Any]:
    """Suggest parameter values for an Optuna trial.

    Handles two special cases:
    - MACRO conditional fuzzing: fuzzing_rate is only suggested when do_fuzzing=true
    - MICRO llm_mode: maps categorical to llm_on_new_state + llm_on_stagnation
    """
    params = {}

    if phase == CalibrationPhase.MACRO:
        for p in MACRO_PARAMETERS:
            # Conditional fuzzing: skip fuzzing_rate when do_fuzzing=false
            if p.name == "fuzzing_rate":
                if params.get("do_fuzzing") == "false":
                    params["fuzzing_rate"] = 0.0
                    continue
                params[p.name] = trial.suggest_float(p.name, p.low, p.high)
            elif p.param_type == "float":
                params[p.name] = trial.suggest_float(p.name, p.low, p.high, log=p.log)
            elif p.param_type == "int":
                kwargs = {}
                if p.step:
                    kwargs["step"] = p.step
                if p.log:
                    kwargs["log"] = True
                params[p.name] = trial.suggest_int(p.name, int(p.low), int(p.high), **kwargs)
            elif p.param_type == "categorical":
                params[p.name] = trial.suggest_categorical(p.name, p.choices)

    elif phase == CalibrationPhase.MICRO:
        for p in MICRO_PARAMETERS:
            if p.name == "llm_mode":
                # Map llm_mode to the 2 Java boolean properties
                mode = trial.suggest_categorical(p.name, p.choices)
                params.update(_LLM_MODE_MAP[mode])
                continue
            if p.param_type == "float":
                params[p.name] = trial.suggest_float(p.name, p.low, p.high, log=p.log)
            elif p.param_type == "int":
                kwargs = {}
                if p.step:
                    kwargs["step"] = p.step
                if p.log:
                    kwargs["log"] = True
                params[p.name] = trial.suggest_int(p.name, int(p.low), int(p.high), **kwargs)
            elif p.param_type == "categorical":
                params[p.name] = trial.suggest_categorical(p.name, p.choices)

    return params


def get_default_params(phase: CalibrationPhase) -> Dict[str, Any]:
    """Get default parameter values for a phase.

    Returns Java-compatible keys (llm_on_new_state/llm_on_stagnation, not llm_mode).
    """
    if phase == CalibrationPhase.MACRO:
        return {p.name: p.default for p in MACRO_PARAMETERS}
    # MICRO: expand llm_mode default to the 2 Java properties
    params = {}
    for p in MICRO_PARAMETERS:
        if p.name == "llm_mode":
            params.update(_LLM_MODE_MAP[p.default])
        else:
            params[p.name] = p.default
    return params


def params_to_tool_spec(params: Dict[str, Any]) -> str:
    """Convert parameter dict to rv-experiment DSL string.

    Example: "default_epsilon=0.0800,mop_weight_direct=400,do_fuzzing=true"
    """
    parts = []
    for name, value in sorted(params.items()):
        if isinstance(value, float):
            parts.append(f"{name}={value:.6f}")
        else:
            parts.append(f"{name}={value}")
    return ",".join(parts)

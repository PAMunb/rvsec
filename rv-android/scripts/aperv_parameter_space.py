"""Parameter space for APE-RV calibration via Optuna.

Defines 19 calibratable parameters in two phases:
- MACRO (14): exploration engine + MOP weights (no LLM)
- MICRO (5): LLM routing and sampling (with LLM)

Parameter names use Python snake_case. The aperv-tool's APERV_PROPERTY_MAPPING
converts them to Java ape.properties camelCase keys (e.g., default_epsilon →
ape.defaultEpsilon). Values pass as strings — Java Config.java parses them.

Usage:
    from aperv_parameter_space import CalibrationPhase, suggest_params, params_to_tool_spec
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class CalibrationPhase(Enum):
    MACRO = "macro"  # 14 params: exploration + MOP weights (no LLM)
    MICRO = "micro"  # 5 params: LLM routing + sampling


@dataclass
class ParameterDef:
    name: str
    param_type: str  # "float", "int", "categorical"
    low: float  # ignored for categorical
    high: float  # ignored for categorical
    default: Any
    choices: List[str] = None  # only for categorical
    description: str = ""


# ---------------------------------------------------------------------------
# MACRO: 14 parameters — exploration engine + MOP weights
# Tool: aperv:sata_mop (no LLM, no SGLang needed)
# ---------------------------------------------------------------------------

MACRO_PARAMETERS = [
    # Exploration parameters (11)
    ParameterDef(
        name="default_epsilon",
        param_type="float", low=0.01, high=0.20, default=0.05,
        description="Fraction of random actions vs greedy (epsilon-greedy)",
    ),
    ParameterDef(
        name="graph_stable_restart_threshold",
        param_type="int", low=30, high=300, default=100,
        description="Steps without graph growth before restart",
    ),
    ParameterDef(
        name="state_stable_restart_threshold",
        param_type="int", low=20, high=150, default=50,
        description="Steps in same state before restart",
    ),
    ParameterDef(
        name="fuzzing_rate",
        param_type="float", low=0.0, high=0.10, default=0.02,
        description="Fraction of fuzzing actions per step",
    ),
    ParameterDef(
        name="do_fuzzing",
        param_type="categorical", low=0, high=0, default="true",
        choices=["true", "false"],
        description="Enable/disable fuzzing entirely",
    ),
    ParameterDef(
        name="throttle_for_activity_transition",
        param_type="int", low=200, high=1000, default=500,
        description="Delay after activity transition (ms)",
    ),
    ParameterDef(
        name="throttle_ms",
        param_type="int", low=100, high=500, default=200,
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
    # MOP weight parameters (3)
    ParameterDef(
        name="mop_weight_direct",
        param_type="int", low=100, high=1000, default=500,
        description="Priority boost for direct MOP-reachable actions",
    ),
    ParameterDef(
        name="mop_weight_transitive",
        param_type="int", low=50, high=600, default=300,
        description="Priority boost for transitive MOP-reachable actions",
    ),
    ParameterDef(
        name="mop_weight_activity",
        param_type="int", low=10, high=200, default=100,
        description="Priority boost for MOP-reachable activity-level actions",
    ),
]

# ---------------------------------------------------------------------------
# MICRO: 5 parameters — LLM routing and sampling
# Tool: aperv:sata_mop_llm (with LLM, SGLang required)
# MACRO params fixed at optimal values from macro phase
# ---------------------------------------------------------------------------

MICRO_PARAMETERS = [
    ParameterDef(
        name="llm_on_new_state",
        param_type="categorical", low=0, high=0, default="true",
        choices=["true", "false"],
        description="Call LLM on first visit to a new state",
    ),
    ParameterDef(
        name="llm_on_stagnation",
        param_type="categorical", low=0, high=0, default="true",
        choices=["true", "false"],
        description="Call LLM when exploration graph stagnates",
    ),
    ParameterDef(
        name="llm_temperature",
        param_type="float", low=0.01, high=0.5, default=0.3,
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


def get_parameters_for_phase(phase: CalibrationPhase) -> List[ParameterDef]:
    if phase == CalibrationPhase.MACRO:
        return MACRO_PARAMETERS
    elif phase == CalibrationPhase.MICRO:
        return MICRO_PARAMETERS
    raise ValueError(f"Unknown phase: {phase}")


def suggest_params(trial, phase: CalibrationPhase) -> Dict[str, Any]:
    """Suggest parameter values for an Optuna trial."""
    params = {}
    for p in get_parameters_for_phase(phase):
        if p.param_type == "float":
            params[p.name] = trial.suggest_float(p.name, p.low, p.high)
        elif p.param_type == "int":
            params[p.name] = trial.suggest_int(p.name, int(p.low), int(p.high))
        elif p.param_type == "categorical":
            params[p.name] = trial.suggest_categorical(p.name, p.choices)
    return params


def get_default_params(phase: CalibrationPhase) -> Dict[str, Any]:
    """Get default parameter values for a phase."""
    return {p.name: p.default for p in get_parameters_for_phase(phase)}


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

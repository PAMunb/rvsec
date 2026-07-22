"""Parameter space for APE-RV calibration via Optuna.

Defines the calibratable parameters for APE-RV in two sequential phases
(macro then micro), following the convention where macro optimizes the
high-impact exploration parameters first, and micro fine-tunes LLM
integration parameters with the best macro values fixed.

Phases:
    - MACRO (13 effective): exploration engine + MOP weights (no LLM).
      14 params declared, but fuzzing_rate is conditional on do_fuzzing.
    - MICRO (4 effective): LLM routing mode + sampling params.
      llm_mode (3 categories) replaces 2 independent booleans to avoid
      the degenerate case where both triggers are off (= no LLM = MACRO).

Parameter names use Python snake_case. The aperv-tool's APERV_PROPERTY_MAPPING
converts them to Java ape.properties camelCase keys (e.g., default_epsilon ->
ape.defaultEpsilon). Values pass as strings -- Java Config.java parses them.

This module is imported dynamically by ``calibration_orchestrator.py`` when
the ``--tool`` flag starts with ``aperv``.

Key functions:
    - ``suggest_params``: Asks Optuna for parameter values for a trial.
    - ``get_default_params``: Returns default parameter values (for warm-starting).
    - ``params_to_tool_spec``: Converts params dict to rv-experiment DSL string.

Usage:
    from aperv_parameter_space import CalibrationPhase, suggest_params, params_to_tool_spec
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class CalibrationPhase(Enum):
    """Calibration phase controlling which parameters are tuned.

    The two-phase approach reduces dimensionality: MACRO optimizes 13-14
    parameters without LLM overhead, then MICRO fixes those and tunes 4
    LLM-specific parameters.
    """

    MACRO = "macro"  # exploration + MOP weights (no LLM)
    MICRO = "micro"  # LLM routing + sampling


@dataclass
class ParameterDef:
    """Definition of a single calibratable parameter.

    Attributes:
        name: Python snake_case name (mapped to Java camelCase by aperv-tool).
        param_type: One of ``"float"``, ``"int"``, ``"categorical"``.
        low: Lower bound for numeric params (ignored for categorical).
        high: Upper bound for numeric params (ignored for categorical).
        default: Default value used for warm-starting the first Optuna trial.
        choices: Valid options for categorical params (None for numeric).
        step: Step size for int params -- reduces the effective search space
            by restricting Optuna to multiples of this value.
        log: If True, use log-uniform sampling -- produces denser sampling at
            the low end of the range, useful for delay/throttle parameters
            where small values have outsized impact.
        description: Human-readable description of what this parameter controls.
    """

    name: str
    param_type: str
    low: float
    high: float
    default: Any
    choices: Optional[List[str]] = None
    step: Optional[int] = None
    log: bool = False
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
        param_type="float",
        low=0.01,
        high=0.20,
        default=0.05,
        description="Fraction of exploitation (least-visited) vs random actions",
    ),
    ParameterDef(
        name="graph_stable_restart_threshold",
        param_type="int",
        low=30,
        high=300,
        default=100,
        step=10,
        description="Steps without graph growth before restart",
    ),
    ParameterDef(
        name="state_stable_restart_threshold",
        param_type="int",
        low=20,
        high=150,
        default=50,
        description="Steps in same state before restart",
    ),
    ParameterDef(
        name="do_fuzzing",
        param_type="categorical",
        low=0,
        high=0,
        default="true",
        choices=["true", "false"],
        description="Enable/disable fuzzing entirely",
    ),
    ParameterDef(
        name="fuzzing_rate",
        param_type="float",
        low=0.0,
        high=0.10,
        default=0.02,
        description="Fraction of fuzzing actions per step (conditional on do_fuzzing)",
    ),
    ParameterDef(
        name="throttle_for_activity_transition",
        param_type="int",
        low=200,
        high=1000,
        default=500,
        log=True,
        description="Delay after activity transition (ms)",
    ),
    ParameterDef(
        name="throttle_ms",
        param_type="int",
        low=100,
        high=500,
        default=200,
        log=True,
        description="Base delay between actions (ms)",
    ),
    ParameterDef(
        name="max_extra_priority_aliased_actions",
        param_type="int",
        low=1,
        high=15,
        default=5,
        description="Priority boost for multi-target actions",
    ),
    ParameterDef(
        name="max_states_per_activity",
        param_type="int",
        low=5,
        high=30,
        default=10,
        description="Cap on states tracked per activity",
    ),
    ParameterDef(
        name="trivial_activity_rank_threshold",
        param_type="int",
        low=1,
        high=8,
        default=3,
        description="Rank threshold to classify activity as trivial",
    ),
    ParameterDef(
        name="do_back_to_trivial_activity",
        param_type="categorical",
        low=0,
        high=0,
        default="false",
        choices=["true", "false"],
        description="Allow backtracking to trivial activities",
    ),
    # MOP weight parameters (3) — step=10 reduces search space ~10x per param
    ParameterDef(
        name="mop_weight_direct",
        param_type="int",
        low=100,
        high=1000,
        default=500,
        step=10,
        description="Priority boost for direct MOP-reachable actions",
    ),
    ParameterDef(
        name="mop_weight_transitive",
        param_type="int",
        low=50,
        high=600,
        default=300,
        step=10,
        description="Priority boost for transitive MOP-reachable actions",
    ),
    ParameterDef(
        name="mop_weight_activity",
        param_type="int",
        low=10,
        high=200,
        default=100,
        step=10,
        description="Priority boost for MOP-reachable activity-level actions",
    ),
]

# ---------------------------------------------------------------------------
# MACRO V2: 10 parameters — reduced from v1 (14→10)
# Removes low-impact params (fuzzing, aliased actions, states cap, trivial
# activity, back to trivial). Adds mop_weight_wtg and coverage_boost_weight
# (previously missing from the search space). Larger step sizes for faster
# convergence with 80 trials.
# Fixed params in FIXED_PARAMS_V2 are merged by the orchestrator.
# ---------------------------------------------------------------------------

MACRO_PARAMETERS_V2 = [
    # MOP weights (4) — core guidance toward monitored operations
    ParameterDef(
        name="mop_weight_direct",
        param_type="int",
        low=100,
        high=1000,
        default=500,
        step=50,
        description="Priority boost for direct MOP-reachable actions",
    ),
    ParameterDef(
        name="mop_weight_transitive",
        param_type="int",
        low=50,
        high=600,
        default=300,
        step=50,
        description="Priority boost for transitive MOP-reachable actions",
    ),
    ParameterDef(
        name="mop_weight_activity",
        param_type="int",
        low=0,
        high=300,
        default=100,
        step=25,
        description="Priority boost for MOP-reachable activity-level actions",
    ),
    ParameterDef(
        name="mop_weight_wtg",
        param_type="int",
        low=0,
        high=600,
        default=200,
        step=50,
        description="Priority boost for WTG-based MOP reachability",
    ),
    # Exploration (3) — exploration vs exploitation balance
    ParameterDef(
        name="default_epsilon",
        param_type="float",
        low=0.01,
        high=0.20,
        default=0.05,
        description="Fraction of exploitation (least-visited) vs random actions",
    ),
    ParameterDef(
        name="graph_stable_restart_threshold",
        param_type="int",
        low=30,
        high=300,
        default=100,
        step=10,
        description="Steps without graph growth before restart",
    ),
    ParameterDef(
        name="state_stable_restart_threshold",
        param_type="int",
        low=20,
        high=150,
        default=50,
        step=10,
        description="Steps in same state before restart",
    ),
    # Coverage (1)
    ParameterDef(
        name="coverage_boost_weight",
        param_type="int",
        low=0,
        high=500,
        default=100,
        step=25,
        description="Priority boost for untested widgets based on coverage",
    ),
    # Timing (2) — how many actions fit in the timeout
    ParameterDef(
        name="throttle_ms",
        param_type="int",
        low=100,
        high=400,
        default=200,
        step=25,
        description="Base delay between actions (ms)",
    ),
    ParameterDef(
        name="throttle_for_activity_transition",
        param_type="int",
        low=200,
        high=800,
        default=500,
        step=50,
        description="Delay after activity transition (ms)",
    ),
]

# Parameters removed from v2 search space — fixed at empirically-validated values.
# Merged into every v2 trial by the orchestrator.
FIXED_PARAMS_V2: Dict[str, Any] = {
    "max_extra_priority_aliased_actions": 5,
    "max_states_per_activity": 15,
    "do_fuzzing": "false",
    "fuzzing_rate": 0.0,
    "do_back_to_trivial_activity": "false",
    "trivial_activity_rank_threshold": 3,
}


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
        param_type="categorical",
        low=0,
        high=0,
        default="both",
        choices=["new_state_only", "stagnation_only", "both"],
        description="When to call LLM: on new states, on stagnation, or both",
    ),
    ParameterDef(
        name="llm_temperature",
        param_type="float",
        low=0.0,
        high=0.7,
        default=0.3,
        description="LLM sampling temperature (lower = more deterministic)",
    ),
    ParameterDef(
        name="llm_top_p",
        param_type="float",
        low=0.3,
        high=0.95,
        default=0.6,
        description="Nucleus sampling threshold",
    ),
    ParameterDef(
        name="llm_top_k",
        param_type="int",
        low=10,
        high=100,
        default=50,
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
    """Return the parameter definitions for the given calibration phase.

    Args:
        phase: Calibration phase (MACRO or MICRO).

    Returns:
        List of ``ParameterDef`` instances for the requested phase.

    Raises:
        ValueError: If an unknown phase is provided.
    """
    if phase == CalibrationPhase.MACRO:
        return MACRO_PARAMETERS
    elif phase == CalibrationPhase.MICRO:
        return MICRO_PARAMETERS
    raise ValueError(f"Unknown phase: {phase}")


def suggest_params(trial, phase: CalibrationPhase) -> Dict[str, Any]:
    """Suggest parameter values for an Optuna trial.

    Handles two special cases that reduce the effective search space:

    - **MACRO conditional fuzzing**: ``fuzzing_rate`` is only suggested when
      ``do_fuzzing=true``. When fuzzing is disabled, the rate is fixed at 0.0,
      so Optuna doesn't waste trials exploring irrelevant fuzzing rates.

    - **MICRO llm_mode**: A single 3-way categorical replaces two independent
      booleans (``llm_on_new_state``, ``llm_on_stagnation``). This prevents the
      degenerate case where both are ``false`` (= no LLM calls = equivalent to
      MACRO, wasting a trial).

    Args:
        trial: Optuna trial object used to suggest parameter values.
        phase: Calibration phase determining which parameters to suggest.

    Returns:
        Dict mapping parameter names to suggested values. For MICRO phase,
        ``llm_mode`` is expanded into ``llm_on_new_state`` and
        ``llm_on_stagnation`` boolean strings (Java-compatible).
    """
    params = {}

    if phase == CalibrationPhase.MACRO:
        for p in MACRO_PARAMETERS:
            # Conditional: fuzzing_rate is only meaningful when fuzzing is enabled.
            # MACRO_PARAMETERS order guarantees do_fuzzing is suggested before
            # fuzzing_rate, so params["do_fuzzing"] is already set here.
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
                params[p.name] = trial.suggest_int(
                    p.name, int(p.low), int(p.high), **kwargs
                )
            elif p.param_type == "categorical":
                params[p.name] = trial.suggest_categorical(p.name, p.choices)

    elif phase == CalibrationPhase.MICRO:
        for p in MICRO_PARAMETERS:
            if p.name == "llm_mode":
                # Expand the synthetic llm_mode categorical into the 2 Java
                # boolean properties that APE-RV's Config.java expects
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
                params[p.name] = trial.suggest_int(
                    p.name, int(p.low), int(p.high), **kwargs
                )
            elif p.param_type == "categorical":
                params[p.name] = trial.suggest_categorical(p.name, p.choices)

    return params


def get_default_params(phase: CalibrationPhase) -> Dict[str, Any]:
    """Get default parameter values for a phase.

    Used by the orchestrator to warm-start the Optuna study: the first trial
    uses these defaults so the TPE sampler has a known baseline to learn from
    instead of starting with pure random sampling.

    Args:
        phase: Calibration phase (MACRO or MICRO).

    Returns:
        Dict with Java-compatible keys (``llm_on_new_state`` /
        ``llm_on_stagnation``, not ``llm_mode``) and default values.
    """
    if phase == CalibrationPhase.MACRO:
        return {p.name: p.default for p in MACRO_PARAMETERS}
    # MICRO: expand llm_mode default to the 2 Java boolean properties,
    # keeping the output format consistent with suggest_params()
    params = {}
    for p in MICRO_PARAMETERS:
        if p.name == "llm_mode":
            params.update(_LLM_MODE_MAP[p.default])
        else:
            params[p.name] = p.default
    return params


def suggest_params_v2(trial, phase: CalibrationPhase) -> Dict[str, Any]:
    """Suggest parameter values for a v2 Optuna trial.

    Simpler than v1: no conditional parameters (do_fuzzing/fuzzing_rate removed).
    For MICRO phase, delegates to the v1 suggest_params (MICRO is unchanged in v2).

    Args:
        trial: Optuna trial object used to suggest parameter values.
        phase: Calibration phase determining which parameters to suggest.

    Returns:
        Dict mapping parameter names to suggested values.
    """
    if phase == CalibrationPhase.MICRO:
        return suggest_params(trial, phase)

    params = {}
    for p in MACRO_PARAMETERS_V2:
        if p.param_type == "float":
            params[p.name] = trial.suggest_float(p.name, p.low, p.high, log=p.log)
        elif p.param_type == "int":
            kwargs = {}
            if p.step:
                kwargs["step"] = p.step
            params[p.name] = trial.suggest_int(
                p.name, int(p.low), int(p.high), **kwargs
            )
        elif p.param_type == "categorical":
            params[p.name] = trial.suggest_categorical(p.name, p.choices)
    return params


def get_default_params_v2(phase: CalibrationPhase) -> Dict[str, Any]:
    """Get default parameter values for v2.

    For MICRO phase, delegates to the v1 get_default_params (MICRO unchanged).

    Args:
        phase: Calibration phase (MACRO or MICRO).

    Returns:
        Dict with default values for the requested phase.
    """
    if phase == CalibrationPhase.MICRO:
        return get_default_params(phase)
    return {p.name: p.default for p in MACRO_PARAMETERS_V2}


def params_to_tool_spec(params: Dict[str, Any]) -> str:
    """Convert parameter dict to rv-experiment DSL string.

    The DSL string is appended to the tool name with ``@`` in the orchestrator
    (e.g., ``aperv:sata_mop@default_epsilon=0.0800,mop_weight_direct=400``).
    rv-experiment parses this and passes key=value pairs to the tool.

    Args:
        params: Dict mapping parameter names to values.

    Returns:
        Comma-separated ``name=value`` string, sorted by parameter name
        for deterministic output. Floats use 6 decimal places to avoid
        floating-point display artifacts.

    Example:
        >>> params_to_tool_spec({"default_epsilon": 0.08, "do_fuzzing": "true"})
        "default_epsilon=0.080000,do_fuzzing=true"
    """
    parts = []
    # Sorted for deterministic output -- makes trial logs easier to diff
    for name, value in sorted(params.items()):
        if isinstance(value, float):
            parts.append(f"{name}={value:.6f}")
        else:
            parts.append(f"{name}={value}")
    return ",".join(parts)

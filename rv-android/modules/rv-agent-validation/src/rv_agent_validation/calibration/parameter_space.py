"""
Parameter space definition for RVAgent calibration.

Defines all tunable parameters with their ranges for Optuna optimization.
Split into macro (high-impact) and micro (fine-tuning) phases.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class CalibrationPhase(Enum):
    """Calibration phase determines which parameters to tune."""

    MACRO = "macro"  # 11 high-impact parameters
    MICRO = "micro"  # 26 fine-tuning parameters
    FULL = "full"  # All 37 parameters


@dataclass
class ParameterDef:
    """Definition of a tunable parameter."""

    name: str
    param_type: str  # "float", "int"
    low: float
    high: float
    default: float
    description: str
    phase: CalibrationPhase
    importance: int = 3  # 1-5 scale: 5=critical, 4=high, 3=medium, 2=low, 1=minimal


# Macro parameters (Phase 1) - 11 high-impact parameters
MACRO_PARAMETERS: List[ParameterDef] = [
    ParameterDef(
        name="mop_direct_score",
        param_type="float",
        low=300.0,
        high=700.0,
        default=500.0,
        description="Score for actions directly reaching MOP methods",
        phase=CalibrationPhase.MACRO,
        importance=5,  # Primary signal driving agent toward monitored operations
    ),
    ParameterDef(
        name="wtg_guided_score",
        param_type="float",
        low=50.0,
        high=300.0,
        default=150.0,
        description="Score for WTG-guided navigation to unvisited screens",
        phase=CalibrationPhase.MACRO,
        importance=4,  # Important for exploration breadth via WTG graph
    ),
    ParameterDef(
        name="unsaturated_bonus",
        param_type="float",
        low=50.0,
        high=150.0,
        default=100.0,
        description="Bonus score for actions in unsaturated states",
        phase=CalibrationPhase.MACRO,
        importance=4,  # Drives state diversity in exploration
    ),
    ParameterDef(
        name="max_re_enables",
        param_type="int",
        low=3,
        high=15,
        default=6,
        description="Maximum times an action can be re-enabled for successor exploration",
        phase=CalibrationPhase.MACRO,
        importance=5,  # Directly controls DFS depth vs breadth
    ),
    ParameterDef(
        name="ui_coverage_threshold",
        param_type="float",
        low=0.7,
        high=1.0,
        default=0.9,
        description="UI coverage threshold for successor re-enablement",
        phase=CalibrationPhase.MACRO,
        importance=4,  # Controls when successors get re-enabled for deeper exploration
    ),
    ParameterDef(
        name="stochastic_probability",
        param_type="float",
        low=0.05,
        high=0.4,
        default=0.15,
        description="Probability of using Gumbel-max stochastic selection",
        phase=CalibrationPhase.MACRO,
        importance=5,  # Exploration/exploitation balance — small changes dramatically alter behavior
    ),
    ParameterDef(
        name="strength_weight",
        param_type="float",
        low=25.0,
        high=100.0,
        default=50.0,
        description="Weight for action strength (historical success rate)",
        phase=CalibrationPhase.MACRO,
        importance=4,  # Controls exploitation of historically successful actions
    ),
    ParameterDef(
        name="visitation_penalty_factor",
        param_type="float",
        low=-25.0,
        high=-5.0,
        default=-15.0,
        description="Penalty factor for over-visited states (negative value)",
        phase=CalibrationPhase.MACRO,
        importance=5,  # Anti-loop mechanism — wrong value = stuck in loops or premature abandonment
    ),
    # New MACRO parameters from gh26 and gh18
    ParameterDef(
        name="backtrack_saturation_threshold",
        param_type="float",
        low=0.5,
        high=1.0,
        default=0.8,
        description="Threshold for triggering backtrack when state is saturated",
        phase=CalibrationPhase.MACRO,
        importance=4,  # Controls when exploration pivots via backtracking
    ),
    ParameterDef(
        name="coverage_density_weight",
        param_type="float",
        low=50.0,
        high=400.0,
        default=200.0,
        description="Weight for coverage density in successor scoring",
        phase=CalibrationPhase.MACRO,
        importance=3,  # New gh26 scorer — impact not yet validated experimentally
    ),
    ParameterDef(
        name="error_detection_confidence",
        param_type="float",
        low=0.3,
        high=0.95,
        default=0.7,
        description="Confidence threshold for visual error detection",
        phase=CalibrationPhase.MACRO,
        importance=3,  # Controls false positive/negative trade-off — moderate range sensitivity
    ),
]

# Micro parameters (Phase 2) - 26 fine-tuning parameters
MICRO_PARAMETERS: List[ParameterDef] = [
    ParameterDef(
        name="mop_transitive_score",
        param_type="float",
        low=150.0,
        high=450.0,
        default=300.0,
        description="Score for actions transitively reaching MOP methods",
        phase=CalibrationPhase.MICRO,
        importance=4,  # Secondary MOP signal — still significant for coverage
    ),
    ParameterDef(
        name="stochastic_temperature",
        param_type="float",
        low=0.1,
        high=5.0,
        default=1.0,
        description="Temperature for Gumbel-max selection (higher = more random)",
        phase=CalibrationPhase.MICRO,
        importance=3,  # Shapes distribution when stochastic selection is triggered
    ),
    ParameterDef(
        name="scroll_probability",
        param_type="float",
        low=0.05,
        high=0.3,
        default=0.15,
        description="Probability of scroll action for dynamic content discovery",
        phase=CalibrationPhase.MICRO,
        importance=2,  # Narrow scope — only affects dynamic content discovery
    ),
    ParameterDef(
        name="plateau_window",
        param_type="int",
        low=5,
        high=20,
        default=10,
        description="Plateau detection window size",
        phase=CalibrationPhase.MICRO,
        importance=3,  # Affects when algorithm detects stuck state and pivots
    ),
    ParameterDef(
        name="max_input_variations",
        param_type="int",
        low=1,
        high=6,
        default=3,
        description="Maximum test value variations per input field",
        phase=CalibrationPhase.MICRO,
        importance=3,  # Affects testing thoroughness for input fields
    ),
    ParameterDef(
        name="gradual_decay_rate",
        param_type="float",
        low=0.5,
        high=0.9,
        default=0.7,
        description="Decay rate per visit (0.7 = 70% retention)",
        phase=CalibrationPhase.MICRO,
        importance=3,  # Controls how fast action scores decay with visits
    ),
    ParameterDef(
        name="component_high_priority",
        param_type="float",
        low=30.0,
        high=80.0,
        default=50.0,
        description="Score for high-priority components (buttons, inputs)",
        phase=CalibrationPhase.MICRO,
        importance=3,  # Affects prioritization of interactive elements
    ),
    ParameterDef(
        name="component_medium_priority",
        param_type="float",
        low=20.0,
        high=60.0,
        default=40.0,
        description="Score for medium-priority components (toggles, sliders)",
        phase=CalibrationPhase.MICRO,
        importance=2,  # Secondary component scoring, coupled with high_priority
    ),
    ParameterDef(
        name="gradual_decay_base",
        param_type="float",
        low=100.0,
        high=300.0,
        default=200.0,
        description="Base score for GradualDecayScorer",
        phase=CalibrationPhase.MICRO,
        importance=2,  # Base value — less impactful than decay rate
    ),
    ParameterDef(
        name="gradual_decay_min_visits",
        param_type="int",
        low=3,
        high=10,
        default=5,
        description="Visits after which score becomes zero",
        phase=CalibrationPhase.MICRO,
        importance=2,  # Threshold coupled with decay_rate, secondary effect
    ),
    ParameterDef(
        name="llm_probability",
        param_type="float",
        low=0.1,
        high=0.9,
        default=0.7,
        description="LLM probability in multimode",
        phase=CalibrationPhase.MICRO,
        importance=5,  # THE key multimode parameter — LLM vs algorithm ratio
    ),
    ParameterDef(
        name="llm_temperature",
        param_type="float",
        low=0.001,
        high=0.9,
        default=0.01,
        description="LLM temperature for tool calling",
        phase=CalibrationPhase.MICRO,
        importance=4,  # Validated as critical for tool calling accuracy (low = better)
    ),
    ParameterDef(
        name="max_short_term_iterations",
        param_type="int",
        low=5,
        high=20,
        default=10,
        description="Maximum iterations in short-term memory",
        phase=CalibrationPhase.MICRO,
        importance=3,  # Controls LLM context window management
    ),
    ParameterDef(
        name="llm_max_retries",
        param_type="int",
        low=0,
        high=5,
        default=2,
        description="Max consecutive LLM failures before fallback",
        phase=CalibrationPhase.MICRO,
        importance=2,  # Robustness parameter, small effect on objective
    ),
    ParameterDef(
        name="llm_top_p",
        param_type="float",
        low=0.1,
        high=0.99,
        default=0.6,
        description="LLM top-p parameter",
        phase=CalibrationPhase.MICRO,
        importance=2,  # Sampling detail — secondary to temperature
    ),
    ParameterDef(
        name="llm_top_k",
        param_type="int",
        low=10,
        high=100,
        default=50,
        description="LLM top-k parameter",
        phase=CalibrationPhase.MICRO,
        importance=2,  # Sampling detail — secondary to temperature
    ),
    # New MICRO parameters from gh26
    ParameterDef(
        name="mop_nav_weight",
        param_type="float",
        low=0.5,
        high=5.0,
        default=2.0,
        description="Weight for MOP navigation guidance in successor scoring",
        phase=CalibrationPhase.MICRO,
        importance=3,  # Modulates MOP-based navigation priority
    ),
    ParameterDef(
        name="mop_max_input_variations",
        param_type="int",
        low=5,
        high=15,
        default=11,
        description="Maximum input variations for MOP-reaching fields",
        phase=CalibrationPhase.MICRO,
        importance=3,  # Affects testing thoroughness for MOP-specific fields
    ),
    ParameterDef(
        name="reward_gamma",
        param_type="float",
        low=0.5,
        high=0.99,
        default=0.8,
        description="Discount factor for reward propagation",
        phase=CalibrationPhase.MICRO,
        importance=3,  # Controls how rewards propagate through action graph
    ),
    ParameterDef(
        name="reward_score_weight",
        param_type="float",
        low=0.1,
        high=3.0,
        default=1.0,
        description="Weight for reward score in action selection",
        phase=CalibrationPhase.MICRO,
        importance=3,  # Controls reward influence in composite action score
    ),
    # New MICRO parameters from gh18
    ParameterDef(
        name="error_max_indicator_size",
        param_type="int",
        low=30,
        high=200,
        default=80,
        description="Maximum pixel size for error indicator detection",
        phase=CalibrationPhase.MICRO,
        importance=2,  # Visual processing detail for error detection
    ),
    ParameterDef(
        name="error_max_indicator_count",
        param_type="int",
        low=2,
        high=20,
        default=5,
        description="Maximum number of error indicators to consider",
        phase=CalibrationPhase.MICRO,
        importance=2,  # Visual processing detail for error detection
    ),
    ParameterDef(
        name="spatial_edittext_boost",
        param_type="float",
        low=1.0,
        high=2.0,
        default=1.2,
        description="Spatial boost factor for EditText fields near error indicators",
        phase=CalibrationPhase.MICRO,
        importance=1,  # Very narrow range (1.0-2.0), small multiplier effect
    ),
    ParameterDef(
        name="spatial_spinner_boost",
        param_type="float",
        low=1.0,
        high=2.0,
        default=1.1,
        description="Spatial boost factor for Spinner fields near error indicators",
        phase=CalibrationPhase.MICRO,
        importance=1,  # Very narrow range, minimal effect on objective
    ),
    ParameterDef(
        name="spatial_min_match_threshold",
        param_type="float",
        low=0.01,
        high=0.5,
        default=0.1,
        description="Minimum spatial match score threshold for error association",
        phase=CalibrationPhase.MICRO,
        importance=2,  # Association threshold for error detection subsystem
    ),
    ParameterDef(
        name="multi_value_saturation_threshold",
        param_type="int",
        low=2,
        high=8,
        default=4,
        description="Saturation threshold for multi-value widgets (EditText, Spinner, SeekBar)",
        phase=CalibrationPhase.MICRO,
        importance=2,  # Widget saturation detail, narrow range
    ),
]

# All parameters
ALL_PARAMETERS = MACRO_PARAMETERS + MICRO_PARAMETERS


def get_parameters_for_phase(phase: CalibrationPhase) -> List[ParameterDef]:
    """Get parameters for a calibration phase."""
    if phase == CalibrationPhase.MACRO:
        return MACRO_PARAMETERS
    elif phase == CalibrationPhase.MICRO:
        return MICRO_PARAMETERS
    else:
        return ALL_PARAMETERS


def get_parameters_by_importance(min_importance: int) -> List[ParameterDef]:
    """Get all parameters with importance >= min_importance.

    Useful for fast calibration: min_importance=4 gives ~12 critical+high params,
    min_importance=3 gives ~24 params, etc.
    """
    return [p for p in ALL_PARAMETERS if p.importance >= min_importance]


def get_default_params() -> Dict[str, Any]:
    """Get default parameter values."""
    return {p.name: p.default for p in ALL_PARAMETERS}


def suggest_params(trial, phase: CalibrationPhase) -> Dict[str, Any]:
    """
    Suggest parameter values for an Optuna trial.

    Args:
        trial: Optuna trial object
        phase: Calibration phase (determines which params to tune)

    Returns:
        Dictionary of parameter name -> suggested value
    """
    params = {}
    parameters = get_parameters_for_phase(phase)

    for p in parameters:
        if p.param_type == "float":
            params[p.name] = trial.suggest_float(p.name, p.low, p.high)
        elif p.param_type == "int":
            params[p.name] = trial.suggest_int(p.name, int(p.low), int(p.high))

    return params


def params_to_tool_spec(params: Dict[str, Any]) -> str:
    """
    Convert parameters to rv-experiment tool specification DSL.

    Args:
        params: Dictionary of parameter values

    Returns:
        String in format "param1=value1,param2=value2,..."
    """
    parts = []
    for name, value in params.items():
        if isinstance(value, float):
            parts.append(f"{name}={value:.4f}")
        else:
            parts.append(f"{name}={value}")
    return ",".join(parts)

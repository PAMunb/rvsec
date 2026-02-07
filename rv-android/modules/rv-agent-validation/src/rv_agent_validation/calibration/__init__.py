"""
Calibration module for RVAgent parameter optimization.

Provides Optuna-based Bayesian optimization for tuning scorer weights
and exploration parameters to maximize coverage and MOP error detection.
"""

from .parameter_space import (
    CalibrationPhase,
    ParameterDef,
    MACRO_PARAMETERS,
    MICRO_PARAMETERS,
    ALL_PARAMETERS,
    get_parameters_for_phase,
    get_default_params,
    suggest_params,
    params_to_tool_spec,
)
from .objective import ObjectiveFunction
from .optimizer import CalibrationOptimizer
from .runner import CalibrationRunner, create_runner_from_config
from .metrics_collector import CalibrationMetricsCollector, RunMetrics

__all__ = [
    # Parameter space
    "CalibrationPhase",
    "ParameterDef",
    "MACRO_PARAMETERS",
    "MICRO_PARAMETERS",
    "ALL_PARAMETERS",
    "get_parameters_for_phase",
    "get_default_params",
    "suggest_params",
    "params_to_tool_spec",
    # Objective
    "ObjectiveFunction",
    # Optimizer
    "CalibrationOptimizer",
    # Runner
    "CalibrationRunner",
    "create_runner_from_config",
    # Metrics (existing)
    "CalibrationMetricsCollector",
    "RunMetrics",
]

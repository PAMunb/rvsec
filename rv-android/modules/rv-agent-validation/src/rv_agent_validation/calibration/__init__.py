"""
Calibration module for RVAgent parameter optimization.

Provides parameter space definitions, objective function, and CLI commands.
Docker-based orchestration is in scripts/calibration_orchestrator.py and
scripts/baseline_docker.py (host-side, not part of this package).
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
    # Metrics
    "CalibrationMetricsCollector",
    "RunMetrics",
]

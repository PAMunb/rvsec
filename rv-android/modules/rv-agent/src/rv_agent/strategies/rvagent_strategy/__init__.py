"""
RVAgent Strategy Package - Coverage-optimized exploration with successor tracking.

This package implements a systematic DFS strategy that:
- Tracks successor state exploration (solves combobox problem)
- Uses MOP-aware prioritization
- Implements plateau detection for automatic termination
- Generates test value variations for input fields
"""

from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker
from rv_agent.strategies.rvagent_strategy.plateau_detector import PlateauDetector
from rv_agent.strategies.rvagent_strategy.input_value_generator import (
    InputValueGenerator,
)
from rv_agent.strategies.rvagent_strategy.coverage_metrics import CoverageMetrics

__all__ = [
    "RVAgentStrategy",
    "SuccessorTracker",
    "PlateauDetector",
    "InputValueGenerator",
    "CoverageMetrics",
]

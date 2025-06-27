"""
Phase Execution Strategy Module

This module implements the Strategy Pattern for flexible phase execution in the
RV-Android experiment workflow system, enabling independent phase execution,
artifact reuse, and graceful fallback modes.

### Key Components:
- PhaseExecutionStrategy: Abstract base strategy interface
- FullExecutionStrategy: Complete execution without fallbacks
- FallbackExecutionStrategy: Graceful degradation with fallbacks
- PhaseResult: Structured result data for phase execution

### Architecture Benefits:
- Independent phase execution capabilities
- Artifact reuse detection and validation
- Clear fallback mode notifications
- Strategy-based execution patterns
"""

from .base_strategy import PhaseExecutionStrategy
from .full_execution_strategy import FullExecutionStrategy
from .fallback_execution_strategy import FallbackExecutionStrategy
from .phase_result import PhaseResult, PhaseExecutionMode, PhaseExecutionContext

__all__ = [
    'PhaseExecutionStrategy',
    'FullExecutionStrategy', 
    'FallbackExecutionStrategy',
    'PhaseResult',
    'PhaseExecutionMode',
    'PhaseExecutionContext'
]
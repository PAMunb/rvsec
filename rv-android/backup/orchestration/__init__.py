# rvandroid/experiment/orchestration/__init__.py
"""
Advanced experiment orchestration system for RV-Android.

This package provides a flexible and powerful orchestration system for managing
and coordinating complex experiments with support for parallel execution,
event-driven control flow, and robust error recovery mechanisms.
"""

from rvandroid.experiment.orchestration.interfaces import (
    OrchestrationMode,
    TaskPriority,
    ExecutionStrategy,
    IOrchestrator,
    IExecutionTracker
)

from rvandroid.experiment.orchestration.orchestrator import (
    ExperimentOrchestrator,
    OrchestrationConfig
)

from rvandroid.experiment.orchestration.execution import (
    ParallelExecutionStrategy,
    SequentialExecutionStrategy,
    AdaptiveExecutionStrategy,
    PriorityBasedExecutionStrategy
)

from rvandroid.experiment.orchestration.tracker import (
    ExecutionTracker,
    ExecutionStatistics,
    ExecutionCheckpoint
)

__all__ = [
    # Interfaces and enums
    'OrchestrationMode',
    'TaskPriority',
    'ExecutionStrategy',
    'IOrchestrator',
    'IExecutionTracker',
    
    # Orchestrator and configuration
    'ExperimentOrchestrator',
    'OrchestrationConfig',
    
    # Execution strategies
    'ParallelExecutionStrategy',
    'SequentialExecutionStrategy',
    'AdaptiveExecutionStrategy',
    'PriorityBasedExecutionStrategy',
    
    # Execution tracking
    'ExecutionTracker',
    'ExecutionStatistics',
    'ExecutionCheckpoint'
]
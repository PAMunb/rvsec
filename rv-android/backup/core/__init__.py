# rvandroid/experiment/core/__init__.py
"""
Core components for the unified execution framework.

This module provides the fundamental abstractions and implementations for the
execution framework, including workflow, execution, and component lifecycle management.
"""

from rvandroid.experiment.core.conductor import ExperimentConductor
from rvandroid.experiment.core.interfaces import (
    IWorkflow,
    IExecutionContext,
    IPhaseProcessor,
    IWorkflowFactory,
    ExecutionPhase
)
from rvandroid.experiment.core.context import ExecutionContext
from rvandroid.experiment.core.workflow import BaseWorkflow
from rvandroid.experiment.core.factory import WorkflowFactory

# Define the exported API
__all__ = [
    # Core Interfaces
    'IWorkflow',
    'IExecutionContext',
    'IPhaseProcessor',
    'IWorkflowFactory',
    'ExecutionPhase',
    
    # Core Implementations
    'ExperimentConductor',
    'ExecutionContext',
    'BaseWorkflow',
    'WorkflowFactory'
]
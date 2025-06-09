# rvandroid/experiment/workflow/__init__.py
"""
Experiment workflow package for RV-Android.

This package provides a modular, event-driven framework for executing
Android application testing experiments with runtime verification capabilities.
It splits the experiment workflow into specific components with clear responsibilities.
"""

from rv_experiment.experiment.workflow.components import (
    IComponent,
    IWorkflowComponent,
    BaseComponent,
    BaseWorkflowComponent,
    ComponentLifecycle,
    ComponentMetadata,
    ComponentProvider
)
from rv_experiment.experiment.workflow.processors import (
    BasePhaseProcessor,
    SetupProcessor,
    StaticAnalysisProcessor,
    ExecutionProcessor,
    AnalysisProcessor,
    ReportingProcessor,
    CleanupProcessor
)
from rv_experiment.experiment.workflow.registry import ComponentRegistry

__all__ = [
    # Component interfaces and base classes
    'IComponent',
    'IWorkflowComponent',
    'BaseComponent',
    'BaseWorkflowComponent',
    'ComponentLifecycle',
    'ComponentMetadata',
    'ComponentProvider',

    # Registry
    'ComponentRegistry',

    # Processors
    'BasePhaseProcessor',
    'SetupProcessor',
    'StaticAnalysisProcessor',
    'ExecutionProcessor',
    'AnalysisProcessor',
    'ReportingProcessor',
    'CleanupProcessor'
]

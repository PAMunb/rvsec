# rvandroid/experiment/workflow/__init__.py
"""
Experiment workflow package for RV-Android.

This package provides a modular, event-driven framework for executing
Android application testing experiments with runtime verification capabilities.
It splits the experiment workflow into specific components with clear responsibilities.
"""

from rvandroid.experiment.workflow.components import (
    IComponent,
    IWorkflowComponent,
    BaseComponent,
    BaseWorkflowComponent,
    ComponentLifecycle,
    ComponentMetadata,
    ComponentProvider
)

from rvandroid.experiment.workflow.registry import ComponentRegistry
from rvandroid.experiment.workflow.injection import (
    ComponentInjector,
    ComponentDecorator,
    autowired
)
from rvandroid.experiment.workflow.processors import (
    BasePhaseProcessor,
    SetupProcessor,
    StaticAnalysisProcessor,
    ExecutionProcessor,
    AnalysisProcessor,
    ReportingProcessor,
    CleanupProcessor
)
from rvandroid.experiment.workflow.conductor import WorkflowConductor

__all__ = [
    # Component interfaces and base classes
    'IComponent',
    'IWorkflowComponent',
    'BaseComponent',
    'BaseWorkflowComponent',
    'ComponentLifecycle',
    'ComponentMetadata',
    'ComponentProvider',
    
    # Registry and injection
    'ComponentRegistry',
    'ComponentInjector',
    'ComponentDecorator',
    'autowired',
    
    # Processors
    'BasePhaseProcessor',
    'SetupProcessor',
    'StaticAnalysisProcessor',
    'ExecutionProcessor',
    'AnalysisProcessor',
    'ReportingProcessor',
    'CleanupProcessor',
    
    # Conductor
    'WorkflowConductor'
]
# rv_experiment/experiment/workflow/__init__.py
"""
Experiment workflow package for RV-Android.

This package provides a modular, event-driven framework for executing
Android application testing experiments with runtime verification capabilities.
It splits the experiment workflow into specific components with clear responsibilities.
"""

from rv_experiment.experiment.workflow.execution_controller import ExecutionController
from rv_experiment.experiment.workflow.post_processor import PostProcessor

# Import workflow components
from rv_experiment.experiment.workflow.pre_processor import PreProcessor
from rv_experiment.experiment.workflow.result_manager import ResultManager
from rv_experiment.experiment.workflow.workflow_factory import WorkflowFactory

__all__ = [
    "PreProcessor",
    "ExecutionController",
    "PostProcessor",
    "ResultManager",
    "WorkflowFactory",
]

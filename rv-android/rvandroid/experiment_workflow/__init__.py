# rvandroid/experiment_workflow/__init__.py
"""
Experiment workflow package for RV-Android.

This package provides a modular, event-driven framework for executing
Android application testing experiments with runtime verification capabilities.
It splits the experiment workflow into specific components with clear responsibilities.
"""

from rvandroid.experiment_workflow.experiment_controller import ExperimentController

__all__ = ['ExperimentController']

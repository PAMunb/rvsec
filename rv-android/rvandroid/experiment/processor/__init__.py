# rvandroid/experiment/processor/__init__.py
"""
Phase processors for the unified execution framework.

This module provides the phase processor implementations for the execution
framework. Each processor handles a specific phase of experiment execution,
such as preparation, static analysis, execution, analysis, or reporting.
"""

from rvandroid.experiment.processor.preparation import PreparationProcessor
from rvandroid.experiment.processor.static_analysis import StaticAnalysisProcessor
from rvandroid.experiment.processor.execution import ExecutionProcessor
from rvandroid.experiment.processor.analysis import AnalysisProcessor
from rvandroid.experiment.processor.reporting import ReportingProcessor
from rvandroid.experiment.processor.base import BasePhaseProcessor

# Define the exported API
__all__ = [
    'BasePhaseProcessor',
    'PreparationProcessor',
    'StaticAnalysisProcessor',
    'ExecutionProcessor',
    'AnalysisProcessor',
    'ReportingProcessor'
]
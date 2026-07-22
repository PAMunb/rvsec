"""
Offline validation framework for RVAgent.

This module provides tools for validating RVAgent behavior using pre-captured
screenshots and UI dumps, enabling fast iteration without emulator.

Key components:
- SequenceLoader: Load app sequences from dataset
- MockDeviceInterface: File-based device simulation
- ActionValidator: Validate actions against actual UI
- MetricsCollector: Comprehensive metrics collection
- ValidationRunner: Main validation workflow
- ReportGenerator: Generate validation reports
"""

from rv_agent.validation.sequence_loader import SequenceLoader
from rv_agent.validation.mock_device import MockDeviceInterface
from rv_agent.validation.action_validator import ActionValidator
from rv_agent.validation.metrics_collector import MetricsCollector
from rv_agent.validation.validation_runner import ValidationRunner

__all__ = [
    "SequenceLoader",
    "MockDeviceInterface",
    "ActionValidator",
    "MetricsCollector",
    "ValidationRunner",
]

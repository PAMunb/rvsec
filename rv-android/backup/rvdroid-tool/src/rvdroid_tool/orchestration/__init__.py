# rvandroid/rvdroid/orchestration/__init__.py

"""
Orchestration system for RVDroid.

This package provides components for coordinating the operation of RVDroid,
managing execution lifecycle, resource allocation, and error recovery.
"""

from rvdroid_tool.orchestration.lifecycle import LifecycleManager, ExecutionPhase
from rvdroid_tool.orchestration.recovery import RecoveryManager, ErrorSeverity, RecoveryStrategy

__all__ = [
    'LifecycleManager',
    'ExecutionPhase',
    'RecoveryManager',
    'ErrorSeverity',
    'RecoveryStrategy'
]
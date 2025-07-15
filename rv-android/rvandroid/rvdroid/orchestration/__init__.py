# rvandroid/rvdroid/orchestration/__init__.py

"""
Orchestration system for RVDroid.

This package provides components for coordinating the operation of RVDroid,
managing execution lifecycle, resource allocation, and error recovery.
"""

from rvandroid.rvdroid.orchestration.lifecycle import LifecycleManager, ExecutionPhase
from rvandroid.rvdroid.orchestration.recovery import RecoveryManager, ErrorSeverity, RecoveryStrategy

__all__ = [
    'LifecycleManager',
    'ExecutionPhase',
    'RecoveryManager',
    'ErrorSeverity',
    'RecoveryStrategy'
]
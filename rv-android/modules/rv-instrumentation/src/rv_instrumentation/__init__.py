"""
RV-Instrumentation module for Android APK runtime verification instrumentation.

This module provides comprehensive APK instrumentation capabilities for integrating
runtime verification monitors with Android applications. It transforms standard APKs
into monitored operations-enabled artifacts through a sophisticated pipeline that
includes decompilation, monitor weaving, recompilation, and signing.

Key Components:
- RVInstrumentation: Core instrumentation engine for APK transformation
- RVInstrumentationConfig: Configuration management for flexible deployment
"""

from .config import ConfigurationError, RVInstrumentationConfig
from .rvandroid import RVInstrumentation

__all__ = ["RVInstrumentation", "RVInstrumentationConfig", "ConfigurationError"]

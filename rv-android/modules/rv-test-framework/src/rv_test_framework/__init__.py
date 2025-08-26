"""
RV-Android Test Framework for configuration evaluation.

This module provides a specialized framework for evaluating different configurations
of AI-driven Android testing tools within the RV-Android modular ecosystem.

### Key Principles:
- Maximum reuse of existing rv-android infrastructure
- User responsibility for configuration and resource management
- Simple, predictable behavior without complex automation
- Clean integration with existing module interfaces
"""

__version__ = "0.1.0"
__author__ = "RV-Android Team"

from rv_test_framework.core.framework import TestFramework

__all__ = ["TestFramework"]
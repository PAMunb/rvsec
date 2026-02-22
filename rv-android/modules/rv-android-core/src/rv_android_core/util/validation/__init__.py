"""
Validation utilities for RV-Android Core.

This module provides Pydantic-based validation utilities for data models,
configuration objects, and structured data throughout the RV-Android system.
"""

from .base import BaseValidatedModel
from .config import ValidationConfig, get_validation_config
from .decorators import validated_model

__all__ = [
    "ValidationConfig",
    "get_validation_config",
    "validated_model",
    "BaseValidatedModel",
]

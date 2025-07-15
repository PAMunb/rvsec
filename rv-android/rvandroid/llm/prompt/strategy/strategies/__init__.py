"""Specialized prompt generation strategies for the prompt system.

This package contains specialized prompt generation strategies that coordinate
the prompt generation process for different use cases.
"""

from .batch_action_strategy import BatchActionStrategy
from .standard_strategy import StandardStrategy

__all__ = [
    "BatchActionStrategy",
    "StandardStrategy",
]
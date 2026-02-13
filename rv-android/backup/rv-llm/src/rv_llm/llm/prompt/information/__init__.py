"""Information layer for the prompt system.

This package provides the information layer components of the prompt system,
which are responsible for collecting and formatting information from various
sources for use in prompt generation.
"""

from .base_fragment import InformationFragment
from .fragment_manager import InformationManager

__all__ = [
    "InformationFragment",
    "InformationManager"
]

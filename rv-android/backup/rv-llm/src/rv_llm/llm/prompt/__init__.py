"""
Prompt strategies for interacting with LLMs.

This package provides the prompt generation framework including strategies,
templates, and information fragments for creating effective LLM prompts.
"""

# Import base modules for prompt system
from .framework import PromptFramework
from .information.fragment_manager import InformationManager
from .strategy.base_strategy import PromptStrategy as BasePromptStrategy

__all__ = [
    "PromptFramework",
    "InformationManager", 
    "BasePromptStrategy"
]

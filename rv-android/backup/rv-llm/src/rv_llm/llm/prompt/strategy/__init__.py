"""Strategy layer for the prompt system.

This package provides the strategy layer components of the prompt system,
which are responsible for coordinating prompt generation flow.

Note: The StrategyRegistry has been removed. All strategy management is now
handled directly by the ComponentConfigurator class.
"""

from .base_strategy import PromptStrategy

__all__ = [
    "PromptStrategy"
]

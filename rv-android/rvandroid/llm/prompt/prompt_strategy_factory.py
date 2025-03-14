# rvandroid/llm/prompt/prompt_strategy_factory.py
from typing import Optional, Union

from rvandroid.llm.prompt.base_prompt_strategy import BasePromptStrategy
from rvandroid.llm.prompt.composable_prompt_strategy import ComposablePromptStrategy
from rvandroid.llm.prompt.composable_single_action_strategy import ComposableSingleActionStrategy
from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
from rvandroid.llm.prompt.prompt_strategy_dspy import DSPyPromptStrategy
from rvandroid.llm.prompt.prompt_strategy_frontier import FrontierPromptStrategy
from rvandroid.llm.prompt.single_action_prompt_strategy import SingleActionPromptStrategy
from rvandroid.llm.prompt.dspy_single_action_prompt_strategy import DSPySingleActionPromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType, ParserFactory


class PromptStrategyFactory:
    """
    Factory class for creating prompt strategy instances.
    Maps strategy names to their implementations.
    """

    # Mapping of strategy types to their implementation classes
    STRATEGIES = {
        "basic": BasicPromptStrategy001,
        "single_action": SingleActionPromptStrategy,
        "dspy": DSPyPromptStrategy,
        "frontier": FrontierPromptStrategy,
        "dspy_single_action": DSPySingleActionPromptStrategy,
        "composable": ComposablePromptStrategy,
        "composable_single_action": ComposableSingleActionStrategy
    }

    @classmethod
    def create(cls,
               strategy_type: str,
               static_data: Optional[StaticAnalysisData] = None,
               parser: Optional[AbstractScreenParser] = None) -> BasePromptStrategy:
        """
        Create a prompt strategy instance of the specified type.

        Args:
            strategy_type: Type of strategy to create
            static_data: Static analysis data (optional)
            parser: Parser instance (optional)

        Returns:
            BasePromptStrategy instance

        Raises:
            ValueError: If strategy_type is unknown
        """
        # Default to single_action if not specified
        if not strategy_type:
            strategy_type = "single_action"

        # Get parser instance if none provided
        if parser is None:
            parser = ParserFactory.create(ParserType.DROIDBOT)

        # Get strategy class
        strategy_class = cls.STRATEGIES.get(strategy_type.lower())
        if not strategy_class:
            raise ValueError(f"Unknown prompt strategy type: {strategy_type}. Options: {list(cls.STRATEGIES.keys())}")

        # Create and return strategy instance
        return strategy_class(static_data, parser)

    @classmethod
    def available_strategies(cls) -> list:
        """
        Returns a list of available strategy types.

        Returns:
            List of strategy type names
        """
        return list(cls.STRATEGIES.keys())

    @classmethod
    def get_default_strategy(cls) -> str:
        """
        Returns the default strategy type.

        Returns:
            Default strategy type name
        """
        return "composable_single_action"  # Updated default to use the new composable strategy

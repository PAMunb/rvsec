# rvandroid/llm/prompt/prompt_strategy_factory.py
from typing import Optional, Union

from rvandroid.llm.prompt.base_prompt_strategy import BasePromptStrategy
from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001  # Adicione esta linha
from rvandroid.llm.prompt.prompt_strategy_dspy import DSPyPromptStrategy
from rvandroid.llm.prompt.prompt_strategy_frontier import FrontierPromptStrategy
from rvandroid.llm.prompt.single_action_prompt_strategy import SingleActionPromptStrategy
from rvandroid.llm.prompt.dspy_single_action_prompt_strategy import DSPySingleActionPromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType, ParserFactory
from rvandroid.config.component_config import ComponentConfig


class PromptStrategyFactory:
    """
    Factory class for creating prompt strategy instances.
    Maps strategy names to their implementations.
    """

    # Mapping of strategy types to their implementation classes
    STRATEGIES = {
        "basic": BasicPromptStrategy001,  # Adicione esta linha para incluir a estratégia "basic"
        "single_action": SingleActionPromptStrategy,
        "dspy": DSPyPromptStrategy,
        "frontier": FrontierPromptStrategy,
        "dspy_single_action": DSPySingleActionPromptStrategy,
        # Add more strategies as needed
    }

    @classmethod
    def create(cls,
               strategy_type: str,
               static_data: Optional[StaticAnalysisData] = None,
               parser: Union[ParserType, AbstractScreenParser, None] = None,
               component_config: Optional[ComponentConfig] = None) -> BasePromptStrategy:
        """
        Create a prompt strategy instance of the specified type.

        Args:
            strategy_type: Type of strategy to create
            static_data: Static analysis data (optional)
            parser: Parser instance or parser type (optional)
            component_config: Component configuration (optional)

        Returns:
            BasePromptStrategy instance

        Raises:
            ValueError: If strategy_type is unknown
        """
        # Default to single_action if not specified
        if not strategy_type:
            strategy_type = "single_action"

        # Convert parser type to parser instance if needed
        parser_instance = parser
        if isinstance(parser, ParserType) or parser is None:
            parser_type = ParserType.DROIDBOT if parser is None else parser
            parser_instance = ParserFactory.create(parser_type)

        # Get strategy class
        strategy_class = cls.STRATEGIES.get(strategy_type.lower())
        if not strategy_class:
            raise ValueError(f"Unknown prompt strategy type: {strategy_type}")

        # Create and return strategy instance
        return strategy_class(static_data, parser_instance)

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
        return "single_action"
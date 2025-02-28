# rvandroid/llm/prompt_strategy_factory.py (Updated)
import logging
from typing import Dict, Type, Optional, Union

from rvandroid.config.component_config import ComponentConfig
from rvandroid.llm.frontier_prompt_strategy import FrontierPromptStrategy
from rvandroid.llm.prompt_strategy import PromptStrategy
from rvandroid.llm.prompt_strategy_basic import BasicPromptStrategy
from rvandroid.llm.prompt_strategy_dspy import DSPyPromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.abstract_parser import AbstractScreenParser
from rvandroid.parser.parser_factory import ParserType

logger = logging.getLogger(__name__)


class PromptStrategyFactory:
    """
    Factory for creating prompt strategies.
    """

    # Registry of available strategy types
    _STRATEGIES: Dict[str, Type[PromptStrategy]] = {
        "basic": BasicPromptStrategy,
        "dspy": DSPyPromptStrategy,
        "frontier": FrontierPromptStrategy
    }

    @classmethod
    def create(
            cls,
            strategy_type: str,
            static_data: Optional[StaticAnalysisData] = None,
            parser: Union[ParserType, AbstractScreenParser, None] = ParserType.DROIDBOT,
            config: Optional[ComponentConfig] = None
    ) -> PromptStrategy:
        """
        Create a prompt strategy instance.

        Args:
            strategy_type: Type of strategy ('basic', 'dspy', 'frontier', etc.)
            static_data: Static analysis data (optional)
            parser: Parser type or instance to use (optional)
            config: Component configuration for advanced customization (optional)

        Returns:
            PromptStrategy instance

        Raises:
            ValueError: If strategy_type is invalid
        """
        if strategy_type not in cls._STRATEGIES:
            logger.warning(f"Unknown prompt strategy type: {strategy_type}, using 'basic'")
            strategy_type = "basic"

        # If a component config is provided, use it to create the strategy
        if config and config.strategy_class:
            logger.info(f"Creating prompt strategy using custom component configuration")
            return config.create_strategy(static_data)

        # Otherwise use the standard approach
        strategy_class = cls._STRATEGIES[strategy_type]
        return strategy_class(static_data, parser)

    @staticmethod
    def register_strategy(name: str, strategy_class: Type[PromptStrategy]) -> None:
        """
        Register a new prompt strategy.

        Args:
            name: Name of the strategy
            strategy_class: Strategy class

        Raises:
            TypeError: If strategy_class is not a subclass of PromptStrategy
        """
        if not issubclass(strategy_class, PromptStrategy):
            raise TypeError(f"Strategy class must be a subclass of PromptStrategy")

        PromptStrategyFactory._STRATEGIES[name] = strategy_class
        logger.info(f"Registered new prompt strategy: {name}")

    @staticmethod
    def get_available_strategies() -> Dict[str, Type[PromptStrategy]]:
        """
        Get all available strategy types.

        Returns:
            Dictionary of strategy types and their classes
        """
        return PromptStrategyFactory._STRATEGIES.copy()

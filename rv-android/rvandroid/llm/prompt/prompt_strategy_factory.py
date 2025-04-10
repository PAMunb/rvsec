# rvandroid/llm/prompt/prompt_strategy_factory.py
from typing import Optional, Dict, List, Type, Any

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.prompt.base_prompt_strategy import BasePromptStrategy
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType, ParserFactory


class PromptStrategyFactory:
    """
    Factory class for creating prompt strategy instances.
    Integrates with the component registry system for dynamic strategy discovery.
    
    ### Architectural Decisions:
    - Uses the centralized ComponentRegistry for strategy type management
    - Provides factory methods for strategy creation and configuration
    - Supports dynamic strategy type registration and discovery
    - Maintains backward compatibility with legacy code

    ### Role in the System:
    - Acts as the primary factory for prompt strategy creation
    - Provides consistent strategy initialization across the system
    - Handles strategy-specific parameter configuration
    - Enables runtime strategy registration and discovery
    """

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
        # Default to composable_single_action if not specified
        if not strategy_type:
            strategy_type = cls.get_default_strategy()

        # Get parser instance if none provided
        if parser is None:
            parser = ParserFactory.create(ParserType.DROIDBOT)

        # Get strategy class from registry
        strategy_registry = ComponentConfigurator._registries['strategy']
        strategy_class = strategy_registry.get(strategy_type.lower())
        
        if not strategy_class:
            # Try to fall back to legacy strategy mapping
            legacy_strategies = cls._get_legacy_strategies()
            if strategy_type.lower() in legacy_strategies:
                strategy_class = legacy_strategies[strategy_type.lower()]
                # Register for future use
                ComponentConfigurator.register_strategy(
                    strategy_type.lower(), strategy_class)
            else:
                raise ValueError(
                    f"Unknown prompt strategy type: {strategy_type}. "
                    f"Options: {strategy_registry.get_names()}")

        # Create and return strategy instance
        return strategy_class(static_data, parser)

    # TODO remover legado
    @staticmethod
    def _get_legacy_strategies() -> Dict[str, Type[BasePromptStrategy]]:
        """
        Returns a mapping of legacy strategy types.
        This is used for backward compatibility and will be removed in future versions.

        Returns:
            Dictionary of strategy types and their implementation classes
        """
        # Import here to avoid circular imports
        from rvandroid.llm.prompt.composable_prompt_strategy import ComposablePromptStrategy
        from rvandroid.llm.prompt.composable_single_action_strategy import ComposableSingleActionStrategy
        from rvandroid.llm.prompt.dspy_single_action_prompt_strategy import DSPySingleActionPromptStrategy
        from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
        from rvandroid.llm.prompt.prompt_strategy_dspy import DSPyPromptStrategy
        from rvandroid.llm.prompt.prompt_strategy_frontier import FrontierPromptStrategy
        from rvandroid.llm.prompt.single_action_prompt_strategy import SingleActionPromptStrategy
        from rvandroid.llm.prompt.flow_based_batch_action_strategy import FlowBasedBatchActionStrategy
        
        return {
            "basic": BasicPromptStrategy001,
            "single_action": SingleActionPromptStrategy,
            "dspy": DSPyPromptStrategy,
            "frontier": FrontierPromptStrategy,
            "dspy_single_action": DSPySingleActionPromptStrategy,
            "composable": ComposablePromptStrategy,
            "composable_single_action": ComposableSingleActionStrategy,
            "flow_based_batch_action": FlowBasedBatchActionStrategy
        }

    @classmethod
    def register_strategy(cls, name: str, strategy_class: Type[BasePromptStrategy], 
                         metadata: Dict[str, Any] = None) -> None:
        """
        Register a new prompt strategy type.

        Args:
            name: Strategy type name
            strategy_class: Strategy class implementation
            metadata: Additional strategy metadata (optional)

        Raises:
            TypeError: If strategy_class is not a subclass of BasePromptStrategy
        """
        if not issubclass(strategy_class, BasePromptStrategy):
            raise TypeError(f"Strategy class must be a subclass of BasePromptStrategy")

        # Register with component registry
        ComponentConfigurator.register_strategy(name, strategy_class, metadata=metadata)

    @classmethod
    def available_strategies(cls) -> List[str]:
        """
        Returns a list of available strategy types.

        Returns:
            List of strategy type names
        """
        # Get strategies from registry
        registry_strategies = ComponentConfigurator._registries['strategy'].get_names()
        
        # Add any legacy strategies not in registry
        legacy_strategies = set(cls._get_legacy_strategies().keys())
        all_strategies = set(registry_strategies).union(legacy_strategies)
        
        return list(all_strategies)

    @classmethod
    def get_default_strategy(cls) -> str:
        """
        Returns the default strategy type.

        Returns:
            Default strategy type name
        """
        return "composable_single_action"  # Using the new composable strategy as default

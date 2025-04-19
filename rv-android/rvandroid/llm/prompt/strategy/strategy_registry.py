"""Strategy registry for the prompt system.

This module defines the StrategyRegistry class, which is responsible for
registering, managing, and providing access to prompt generation strategies.
"""

from typing import Dict, Optional

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from .base_strategy import PromptStrategy


class StrategyRegistry:
    """Registry for prompt generation strategies.
    
    The StrategyRegistry is responsible for registering, managing, and providing
    access to prompt generation strategies.
    """

    def __init__(self):
        """Initialize the strategy registry."""
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.prompt.strategy.registry",
            {CONTEXT_COMPONENT: "StrategyRegistry"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

        # Initialize strategy registry
        self.strategies: Dict[str, PromptStrategy] = {}
        self.default_strategy: Optional[str] = None

    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the strategy registry with the given configuration.
        
        Args:
            config: The configuration to use.
        """
        self.logger.info("Configuring StrategyRegistry")

        # Configure registered strategies
        for strategy in self.strategies.values():
            strategy.configure(config)

        # Set default strategy if specified in llm_config
        if hasattr(config, 'llm_config') and hasattr(config.llm_config, 'default_strategy'):
            default_strategy = config.llm_config.default_strategy
            if default_strategy and default_strategy in self.strategies:
                self.default_strategy = default_strategy
                self.logger.info(f"Set default strategy to: {default_strategy}")

    def register_strategy(self, strategy: PromptStrategy) -> None:
        """Register a prompt generation strategy.
        
        Args:
            strategy: The strategy to register.
        """
        if strategy.name in self.strategies:
            self.logger.warning(f"Overwriting existing strategy: {strategy.name}")

        self.strategies[strategy.name] = strategy

        # If this is the first strategy, set it as default
        if self.default_strategy is None:
            self.default_strategy = strategy.name

        self.logger.info(f"Registered strategy: {strategy.name}")

    def unregister_strategy(self, name: str) -> None:
        """Unregister a prompt generation strategy.
        
        Args:
            name: The name of the strategy to unregister.
        """
        if name in self.strategies:
            self.logger.info(f"Unregistered strategy: {name}")

            # If this was the default strategy, clear the default
            if self.default_strategy == name:
                self.default_strategy = next(iter(self.strategies.keys())) if self.strategies else None

            del self.strategies[name]
        else:
            self.logger.warning(f"Attempted to unregister non-existent strategy: {name}")

    def get_strategy(self, name: Optional[str] = None) -> Optional[PromptStrategy]:
        """Get a registered strategy by name.
        
        Args:
            name: The name of the strategy to get. If not provided,
                returns the default strategy.
            
        Returns:
            The strategy, or None if not found.
        """
        if name is None:
            if self.default_strategy is None:
                self.logger.warning("No default strategy set")
                return None

            name = self.default_strategy

        strategy = self.strategies.get(name)

        if strategy is None:
            self.logger.warning(f"Strategy not found: {name}")

        return strategy

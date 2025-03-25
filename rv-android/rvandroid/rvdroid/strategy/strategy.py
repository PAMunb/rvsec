"""
Strategy framework for RVDroid.

This module provides the base classes and interfaces for implementing
testing strategies that guide the exploration of Android applications.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class Strategy(ABC):
    """
    Abstract base class for all exploration strategies.

    Defines the interface that all strategies must implement, including
    methods for action generation, feedback processing, and metadata access.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "BaseStrategy"):
        """
        Initialize the strategy.

        Args:
            static_data: Optional static analysis data
            name: Strategy name
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"rvdroid.strategy.{name.lower()}",
            {CONTEXT_COMPONENT: name}
        )

        # Store static data
        self.static_data = static_data
        self.name = name

        self.logger.info(f"Initialized {name} strategy")

    @abstractmethod
    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any],
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate the next action based on the current state and history.

        Args:
            screen: Parsed screen description
            state_data: Raw state data
            history: Optional history of previous states and actions

        Returns:
            ItemAction to execute, or None if no action is available
        """
        pass

    @abstractmethod
    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update strategy based on action execution feedback.

        Args:
            action: Action that was executed
            result: Execution result with success status and state change info
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the strategy for logging and analysis.

        Returns:
            Dictionary with strategy metadata
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__
        }


class StrategyRegistry:
    """
    Registry for available strategies.

    Maintains a collection of registered strategy classes and provides
    methods for strategy discovery and instantiation.
    """

    _strategies: Dict[str, type] = {}

    @classmethod
    def register(cls, strategy_class: type) -> None:
        """
        Register a strategy class.

        Args:
            strategy_class: Strategy class to register
        """
        if not issubclass(strategy_class, Strategy):
            raise TypeError(f"Strategy class must inherit from Strategy base class")

        cls._strategies[strategy_class.__name__] = strategy_class

    @classmethod
    def get_strategy(cls, strategy_name: str) -> Optional[type]:
        """
        Get a strategy class by name.

        Args:
            strategy_name: Name of the strategy class

        Returns:
            Strategy class or None if not found
        """
        return cls._strategies.get(strategy_name)

    @classmethod
    def create_strategy(cls, strategy_name: str, static_data: Optional[StaticAnalysisData] = None,
                        **kwargs) -> Optional[Strategy]:
        """
        Create a strategy instance by name.

        Args:
            strategy_name: Name of the strategy class
            static_data: Optional static analysis data
            **kwargs: Additional arguments for the strategy constructor

        Returns:
            Strategy instance or None if strategy not found
        """
        strategy_class = cls.get_strategy(strategy_name)
        if not strategy_class:
            return None

        return strategy_class(static_data=static_data, **kwargs)

    @classmethod
    def list_strategies(cls) -> List[str]:
        """
        Get a list of available strategy names.

        Returns:
            List of strategy names
        """
        return list(cls._strategies.keys())


class StrategyComposition(Strategy):
    """
    Strategy that composes multiple strategies with configurable weighting.

    Delegates action generation to component strategies based on weights
    and selection criteria, allowing for flexible strategy combinations.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "CompositeStrategy",
                 strategies: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize the composite strategy.

        Args:
            static_data: Optional static analysis data
            name: Strategy name
            strategies: List of strategy configurations with names and weights
        """
        super().__init__(static_data, name)

        # Initialize component strategies
        self.strategies: List[Dict[str, Any]] = []

        if strategies:
            for strategy_config in strategies:
                strategy_name = strategy_config.get("name")
                weight = strategy_config.get("weight", 1.0)

                strategy = StrategyRegistry.create_strategy(strategy_name, static_data)
                if strategy:
                    self.strategies.append({
                        "strategy": strategy,
                        "weight": weight,
                        "last_result": None
                    })

        self.logger.info(f"Initialized composite strategy with {len(self.strategies)} component strategies")

    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any],
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate the next action by delegating to component strategies.

        Args:
            screen: Parsed screen description
            state_data: Raw state data
            history: Optional history of previous states and actions

        Returns:
            ItemAction to execute, or None if no action is available
        """
        if not self.strategies:
            self.logger.warning("No component strategies available")
            return None

        # Select strategy based on weights and previous results
        selected_strategy = self._select_strategy(state_data)
        if not selected_strategy:
            self.logger.warning("Failed to select a component strategy")
            return None

        # Generate action using selected strategy
        strategy = selected_strategy["strategy"]
        self.logger.debug(f"Using '{strategy.name}' strategy for action generation")

        action = strategy.generate_action(screen, state_data, history)

        # Record which strategy generated this action
        if action:
            selected_strategy["last_action"] = action

        return action

    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update component strategies based on action execution feedback.

        Args:
            action: Action that was executed
            result: Execution result with success status and state change info
        """
        # Find which strategy generated this action
        for strategy_info in self.strategies:
            if "last_action" in strategy_info and strategy_info["last_action"] == action:
                # Update the strategy that generated this action
                strategy = strategy_info["strategy"]
                strategy.update_feedback(action, result)

                # Update last result for strategy selection
                strategy_info["last_result"] = result

                # Adjust weights based on results
                if result.get("new_state", False):
                    # Increase weight of strategies that discover new states
                    strategy_info["weight"] *= 1.1

                break

        # Normalize weights
        self._normalize_weights()

    def _select_strategy(self, state_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Select a strategy based on weights and previous results.

        Args:
            state_data: Raw state data

        Returns:
            Selected strategy info or None if no strategies available
        """
        if not self.strategies:
            return None

        # Get total weight
        total_weight = sum(s["weight"] for s in self.strategies)

        # Simple weighted random selection
        import random
        selection = random.uniform(0, total_weight)

        current = 0
        for strategy_info in self.strategies:
            current += strategy_info["weight"]
            if selection <= current:
                return strategy_info

        # Fallback to first strategy
        return self.strategies[0]

    def _normalize_weights(self) -> None:
        """Normalize the weights of component strategies."""
        # Get total weight
        total_weight = sum(s["weight"] for s in self.strategies)

        # Normalize weights
        if total_weight > 0:
            for strategy_info in self.strategies:
                strategy_info["weight"] /= total_weight

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the composite strategy.

        Returns:
            Dictionary with composite strategy metadata
        """
        metadata = super().get_metadata()

        # Add component strategy information
        metadata["component_strategies"] = [
            {
                "name": s["strategy"].name,
                "type": s["strategy"].__class__.__name__,
                "weight": s["weight"]
            }
            for s in self.strategies
        ]

        return metadata
   
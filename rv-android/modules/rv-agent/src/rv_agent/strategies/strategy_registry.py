"""
Strategy registry for graph exploration algorithms.

Provides dynamic discovery and instantiation of exploration strategies
(DFS, BFS, etc.) with dependency injection support.
"""

import logging
from typing import Dict, Type, Optional, Any

from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_agent.strategies.dfs_strategy import DFSStrategy
from rv_agent.strategies.bfs_strategy import BFSStrategy
from rv_agent.strategies.greedy_strategy import GreedyStrategy
from rv_agent.strategies.simulated_annealing_strategy import SimulatedAnnealingStrategy
from rv_agent.strategies.genetic_algorithm_strategy import GeneticAlgorithmStrategy
from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_android_core.domain.static import StaticAnalysisData

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    Registry for exploration strategy discovery and instantiation.

    ### Architectural Decisions:
    - Implements registry pattern for strategy management
    - Provides factory methods for strategy instantiation
    - Supports dependency injection for strategy dependencies
    - Enables runtime strategy switching
    - Uses string-based strategy lookup for configuration

    ### Role in the System:
    - Central registry for available exploration strategies
    - Factory for creating configured strategy instances
    - Enables strategy discovery without hard-coded dependencies
    - Supports future strategy additions without code changes

    ### Integration Points:
    - Used by RVAgent to create strategy instances
    - Used by FallbackManager to access algorithmic strategies
    - Provides interface for strategy enumeration
    - Supports configuration-driven strategy selection
    """

    def __init__(self):
        """Initialize strategy registry with built-in strategies."""
        self._strategies: Dict[str, Type[ExplorationStrategy]] = {}
        self._register_builtin_strategies()

    def _register_builtin_strategies(self):
        """Register built-in exploration strategies."""
        # Classic graph traversal strategies
        self.register("dfs", DFSStrategy)
        self.register("bfs", BFSStrategy)

        # Advanced learning-based strategies
        self.register("greedy", GreedyStrategy)
        self.register("simulated_annealing", SimulatedAnnealingStrategy)
        self.register("genetic_algorithm", GeneticAlgorithmStrategy)

        logger.debug("Registered built-in strategies: dfs, bfs, greedy, simulated_annealing, genetic_algorithm")

    def register(self, name: str, strategy_class: Type[ExplorationStrategy]):
        """
        Register a strategy class with given name.

        Args:
            name: Strategy identifier (e.g., "dfs", "bfs")
            strategy_class: ExplorationStrategy subclass

        Raises:
            ValueError: If strategy class does not implement ExplorationStrategy
        """
        if not issubclass(strategy_class, ExplorationStrategy):
            raise ValueError(
                f"Strategy class {strategy_class.__name__} must inherit from ExplorationStrategy"
            )

        self._strategies[name.lower()] = strategy_class
        logger.debug(f"Registered strategy: {name} -> {strategy_class.__name__}")

    def get_strategy(
        self,
        name: str,
        graph: DynamicStateGraph,
        static_data: Optional[StaticAnalysisData] = None,
        coordinate_converter: Optional[Any] = None
    ) -> ExplorationStrategy:
        """
        Create and return configured strategy instance.

        Args:
            name: Strategy identifier (e.g., "dfs", "bfs")
            graph: Dynamic state graph for history tracking
            static_data: Optional static analysis data for MOP guidance
            coordinate_converter: Optional coordinate converter for space transformations

        Returns:
            Configured ExplorationStrategy instance

        Raises:
            ValueError: If strategy name not registered
        """
        strategy_name = name.lower()

        if strategy_name not in self._strategies:
            available = ", ".join(self._strategies.keys())
            raise ValueError(
                f"Unknown strategy: {name}. Available strategies: {available}"
            )

        strategy_class = self._strategies[strategy_name]

        logger.info(f"Creating strategy instance: {strategy_name} ({strategy_class.__name__})")

        # Instantiate strategy with dependencies
        return strategy_class(
            graph=graph,
            static_data=static_data,
            coordinate_converter=coordinate_converter
        )

    def list_strategies(self) -> list[str]:
        """
        List all registered strategy names.

        Returns:
            List of registered strategy identifiers
        """
        return list(self._strategies.keys())

    def has_strategy(self, name: str) -> bool:
        """
        Check if strategy is registered.

        Args:
            name: Strategy identifier to check

        Returns:
            True if strategy is registered
        """
        return name.lower() in self._strategies

    def unregister(self, name: str):
        """
        Remove strategy from registry.

        Args:
            name: Strategy identifier to remove

        Raises:
            ValueError: If strategy not registered
        """
        strategy_name = name.lower()

        if strategy_name not in self._strategies:
            raise ValueError(f"Strategy not registered: {name}")

        del self._strategies[strategy_name]
        logger.debug(f"Unregistered strategy: {name}")

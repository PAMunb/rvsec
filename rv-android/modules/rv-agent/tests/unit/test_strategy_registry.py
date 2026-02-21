"""
Unit tests for StrategyRegistry.

Tests strategy registration, instantiation, listing, and error handling.
"""

import pytest
from unittest.mock import MagicMock

from rv_agent.strategies.strategy_registry import StrategyRegistry
from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_agent.strategies.dfs_strategy import DFSStrategy
from rv_agent.strategies.bfs_strategy import BFSStrategy
from rv_agent.strategies.greedy_strategy import GreedyStrategy
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.config.agent_config import RVAgentConfig


class TestStrategyRegistryInit:
    """Test strategy registry initialization."""

    def test_builtin_strategies_registered(self):
        """Built-in strategies are registered on init."""
        registry = StrategyRegistry()

        assert registry.has_strategy("dfs")
        assert registry.has_strategy("bfs")
        assert registry.has_strategy("greedy")
        assert registry.has_strategy("rvagent")

    def test_list_strategies(self):
        """List all registered strategies."""
        registry = StrategyRegistry()

        strategies = registry.list_strategies()

        assert "dfs" in strategies
        assert "bfs" in strategies
        assert "greedy" in strategies
        assert "rvagent" in strategies
        assert len(strategies) >= 4


class TestStrategyRegistration:
    """Test strategy registration."""

    def test_register_valid_strategy(self):
        """Register a valid strategy class."""
        registry = StrategyRegistry()

        # Create a custom strategy
        class CustomStrategy(ExplorationStrategy):
            def select_next_action(self, screen_hash, screen_desc):
                return None

            def reset(self):
                pass

        registry.register("custom", CustomStrategy)

        assert registry.has_strategy("custom")

    def test_register_invalid_class_raises(self):
        """Registering non-strategy class raises ValueError."""
        registry = StrategyRegistry()

        class NotAStrategy:
            pass

        with pytest.raises(ValueError) as exc_info:
            registry.register("invalid", NotAStrategy)

        assert "must inherit from ExplorationStrategy" in str(exc_info.value)

    def test_register_case_insensitive(self):
        """Strategy names are case-insensitive."""
        registry = StrategyRegistry()

        assert registry.has_strategy("DFS")
        assert registry.has_strategy("dfs")
        assert registry.has_strategy("Dfs")


class TestStrategyInstantiation:
    """Test strategy instantiation via get_strategy."""

    @pytest.fixture
    def registry(self):
        return StrategyRegistry()

    @pytest.fixture
    def graph(self):
        return DynamicStateGraph()

    @pytest.fixture
    def config(self):
        return RVAgentConfig(package_name="com.test.app")

    def test_get_dfs_strategy(self, registry, graph):
        """Get DFS strategy instance."""
        strategy = registry.get_strategy("dfs", graph=graph)

        assert isinstance(strategy, DFSStrategy)

    def test_get_bfs_strategy(self, registry, graph):
        """Get BFS strategy instance."""
        strategy = registry.get_strategy("bfs", graph=graph)

        assert isinstance(strategy, BFSStrategy)

    def test_get_greedy_strategy(self, registry, graph):
        """Get Greedy strategy instance."""
        strategy = registry.get_strategy("greedy", graph=graph)

        assert isinstance(strategy, GreedyStrategy)

    def test_get_unknown_strategy_raises(self, registry, graph):
        """Getting unknown strategy raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            registry.get_strategy("unknown", graph=graph)

        assert "Unknown strategy" in str(exc_info.value)
        assert "Available strategies" in str(exc_info.value)

    def test_get_rvagent_without_config_raises(self, registry, graph):
        """RVAgent without config raises ValueError."""
        ui_coverage = UICoverageTracker()

        with pytest.raises(ValueError) as exc_info:
            registry.get_strategy("rvagent", graph=graph, ui_coverage=ui_coverage)

        assert "requires config" in str(exc_info.value)

    def test_get_rvagent_without_ui_coverage_raises(self, registry, graph, config):
        """RVAgent without ui_coverage raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            registry.get_strategy("rvagent", graph=graph, config=config)

        assert "requires ui_coverage" in str(exc_info.value)

    def test_get_rvagent_with_required_params(self, registry, graph, config):
        """RVAgent with required parameters succeeds."""
        ui_coverage = UICoverageTracker()

        strategy = registry.get_strategy(
            "rvagent", graph=graph, config=config, ui_coverage=ui_coverage
        )

        assert strategy is not None

    def test_get_rvagent_with_all_params(self, registry, graph, config):
        """RVAgent with all optional parameters."""
        ui_coverage = UICoverageTracker()
        coordinate_converter = MagicMock()
        static_data = MagicMock()

        strategy = registry.get_strategy(
            "rvagent",
            graph=graph,
            config=config,
            ui_coverage=ui_coverage,
            coordinate_converter=coordinate_converter,
            static_data=static_data,
            device_dimensions=(1080, 2400),
        )

        assert strategy is not None

    def test_get_strategy_case_insensitive(self, registry, graph):
        """Strategy names are case-insensitive in get_strategy."""
        strategy1 = registry.get_strategy("DFS", graph=graph)
        strategy2 = registry.get_strategy("dfs", graph=graph)

        assert type(strategy1) == type(strategy2)

    def test_get_strategy_with_static_data(self, registry, graph):
        """Get strategy with static analysis data."""
        static_data = MagicMock()

        strategy = registry.get_strategy("dfs", graph=graph, static_data=static_data)

        assert isinstance(strategy, DFSStrategy)

    def test_get_strategy_with_coordinate_converter(self, registry, graph):
        """Get strategy with coordinate converter."""
        converter = MagicMock()

        strategy = registry.get_strategy(
            "bfs", graph=graph, coordinate_converter=converter
        )

        assert isinstance(strategy, BFSStrategy)


class TestStrategyUnregistration:
    """Test strategy unregistration."""

    def test_unregister_existing_strategy(self):
        """Unregister an existing strategy."""
        registry = StrategyRegistry()

        assert registry.has_strategy("greedy")

        registry.unregister("greedy")

        assert not registry.has_strategy("greedy")

    def test_unregister_nonexistent_raises(self):
        """Unregistering nonexistent strategy raises ValueError."""
        registry = StrategyRegistry()

        with pytest.raises(ValueError) as exc_info:
            registry.unregister("nonexistent")

        assert "not registered" in str(exc_info.value)

    def test_unregister_case_insensitive(self):
        """Unregister is case-insensitive."""
        registry = StrategyRegistry()

        registry.unregister("DFS")

        assert not registry.has_strategy("dfs")


class TestHasStrategy:
    """Test has_strategy method."""

    def test_has_existing_strategy(self):
        """Check existing strategy."""
        registry = StrategyRegistry()

        assert registry.has_strategy("dfs") is True

    def test_has_nonexistent_strategy(self):
        """Check nonexistent strategy."""
        registry = StrategyRegistry()

        assert registry.has_strategy("nonexistent") is False

    def test_has_strategy_case_insensitive(self):
        """has_strategy is case-insensitive."""
        registry = StrategyRegistry()

        assert registry.has_strategy("DFS") is True
        assert registry.has_strategy("Dfs") is True
        assert registry.has_strategy("dfs") is True

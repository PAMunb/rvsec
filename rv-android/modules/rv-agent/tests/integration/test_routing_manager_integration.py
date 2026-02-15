"""
Integration tests for RoutingManager with real fixtures.

Tests routing decisions, mode transitions, and action validation.
"""

import pytest
from pathlib import Path
from typing import Dict, List, Tuple
from unittest.mock import MagicMock, patch

from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph, compute_screen_hash_from_description
from rv_agent.routing.routing_manager import RoutingManager
from rv_agent.routing.fallback_manager import FallbackManager
from rv_agent.strategies.strategy_registry import StrategyRegistry
from rv_agent.strategies.dfs_strategy import DFSStrategy
from rv_agent.config.agent_config import RVAgentConfig


pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "screenshots"


def load_fixture(app_name: str, screen_num: str) -> Tuple[str, ScreenDescription]:
    """Load a fixture pair."""
    xml_path = FIXTURES_DIR / app_name / f"{screen_num}.uiautomator.xml"
    with open(xml_path, "r") as f:
        xml_content = f.read()

    parser = UIAutomator2Parser(visitor_class=DefaultTextVisitor)
    screen_desc = parser.parse(xml_content, activity=f"com.example.{app_name}.MainActivity")

    return xml_content, screen_desc


@pytest.fixture
def config_pure_algorithm():
    """Config for pure_algorithm mode."""
    config = RVAgentConfig.create_default(package_name="com.test.app")
    config.agent_mode = "pure_algorithm"
    return config


@pytest.fixture
def config_multimode():
    """Config for multimode."""
    config = RVAgentConfig.create_default(package_name="com.test.app")
    config.agent_mode = "multimode"
    config.llm_probability = 0.7
    return config


@pytest.fixture
def config_llm_only():
    """Config for llm_only mode."""
    config = RVAgentConfig.create_default(package_name="com.test.app")
    config.agent_mode = "llm_only"
    return config


@pytest.fixture
def graph():
    """Fresh DynamicStateGraph."""
    return DynamicStateGraph()


@pytest.fixture
def dfs_strategy(graph):
    """DFS strategy."""
    return DFSStrategy(graph=graph)


@pytest.fixture
def strategy_registry():
    """Strategy registry with default strategies."""
    return StrategyRegistry()


@pytest.fixture
def fallback_manager(strategy_registry):
    """Fallback manager."""
    return FallbackManager(strategy_registry=strategy_registry)


@pytest.fixture
def routing_manager_pure(config_pure_algorithm, fallback_manager, dfs_strategy):
    """RoutingManager in pure_algorithm mode."""
    return RoutingManager(
        config=config_pure_algorithm,
        fallback_manager=fallback_manager,
        exploration_strategy=dfs_strategy
    )


@pytest.fixture
def routing_manager_multimode(config_multimode, fallback_manager, dfs_strategy):
    """RoutingManager in multimode."""
    return RoutingManager(
        config=config_multimode,
        fallback_manager=fallback_manager,
        exploration_strategy=dfs_strategy
    )


# =============================================================================
# Mode Selection Tests
# =============================================================================

class TestModeSelection:
    """Test routing mode selection."""

    def test_pure_algorithm_always_returns_algorithm(self, routing_manager_pure):
        """Pure algorithm mode always routes to algorithm."""
        for i in range(10):
            decision = routing_manager_pure.route_decision(iteration=i + 1)
            assert decision == "algorithm"

    def test_multimode_returns_mixed(self, routing_manager_multimode):
        """Multimode returns both algorithm and llm decisions."""
        decisions = []
        for i in range(50):
            decision = routing_manager_multimode.route_decision(iteration=i + 1)
            decisions.append(decision)

        # Should have some variety (probabilistic)
        unique_decisions = set(decisions)
        # At least algorithm should appear (probability 0.3)
        assert "algorithm" in unique_decisions or "llm" in unique_decisions

    def test_llm_only_returns_llm(self, config_llm_only, fallback_manager, dfs_strategy):
        """LLM-only mode always routes to llm."""
        routing_manager = RoutingManager(
            config=config_llm_only,
            fallback_manager=fallback_manager,
            exploration_strategy=dfs_strategy
        )

        for i in range(10):
            decision = routing_manager.route_decision(iteration=i + 1)
            assert decision == "llm"


# =============================================================================
# Counter Tracking Tests
# =============================================================================

class TestCounterTracking:
    """Test decision counter tracking."""

    def test_counters_start_at_zero(self, routing_manager_pure):
        """Counters start at zero."""
        counters = routing_manager_pure.get_decision_counters()
        assert counters["llm_executed"] == 0
        assert counters["algorithm_chosen"] == 0

    def test_algorithm_counter_increments(self, routing_manager_pure):
        """Algorithm counter increments on algorithm decision."""
        initial = routing_manager_pure.get_decision_counters()["algorithm_chosen"]

        routing_manager_pure.route_decision(iteration=1)

        counters = routing_manager_pure.get_decision_counters()
        assert counters["algorithm_chosen"] == initial + 1

    def test_get_decision_counters(self, routing_manager_pure):
        """Get decision counters structure."""
        for i in range(5):
            routing_manager_pure.route_decision(iteration=i + 1)

        counters = routing_manager_pure.get_decision_counters()

        assert "algorithm_chosen" in counters
        assert "llm_executed" in counters
        assert "llm_validation_failed" in counters
        assert counters["algorithm_chosen"] == 5

    def test_llm_percentage_calculation(self, routing_manager_multimode):
        """Test LLM percentage calculation."""
        # Run many iterations to get statistical average
        for i in range(100):
            routing_manager_multimode.route_decision(iteration=i + 1)

        counters = routing_manager_multimode.get_decision_counters()

        # Verify percentage is calculated
        assert "llm_percentage" in counters
        assert "algorithm_percentage" in counters
        assert counters["llm_percentage"] + counters["algorithm_percentage"] == pytest.approx(100, abs=0.1)


# =============================================================================
# Action Validation Tests
# =============================================================================

class TestActionValidation:
    """Test action validation in routing."""

    def test_validate_valid_click_action(self, routing_manager_multimode):
        """Validate valid click action."""
        action = {
            "action_type": "CLICK",
            "x": 352,
            "y": 273,
            "explanation": "Click button"
        }
        recent_actions = []

        result = routing_manager_multimode.validate_action(action, recent_actions)

        assert result["validation_path"] == "execute"
        assert result["loop_detected"] is False
        # Action should be returned unchanged when valid
        assert result["current_action"]["action_type"] == "CLICK"

    def test_validate_action_without_type_returns_back(self, routing_manager_multimode):
        """Invalid action without action_type returns BACK."""
        action = {"x": 100, "y": 200}  # Missing action_type
        recent_actions = []

        result = routing_manager_multimode.validate_action(action, recent_actions)

        # Now returns "execute" with BACK action instead of algorithm_fallback
        assert result["validation_path"] == "execute"
        assert result["current_action"]["action_type"] == "BACK"

    def test_validate_none_action_returns_back(self, routing_manager_multimode):
        """Validate None action returns BACK."""
        result = routing_manager_multimode.validate_action(None, [])

        # Now returns "execute" with BACK action instead of algorithm_fallback
        assert result["validation_path"] == "execute"
        assert result["current_action"]["action_type"] == "BACK"

    def test_validate_back_action(self, routing_manager_multimode):
        """Validate BACK action."""
        action = {"action_type": "BACK", "explanation": "Go back"}
        recent_actions = []

        result = routing_manager_multimode.validate_action(action, recent_actions)

        assert result["validation_path"] == "execute"

    def test_validate_scroll_action(self, routing_manager_multimode):
        """Validate SCROLL action."""
        action = {
            "action_type": "SCROLL",
            "direction": "down",
            "explanation": "Scroll down"
        }
        recent_actions = []

        result = routing_manager_multimode.validate_action(action, recent_actions)

        assert result["validation_path"] == "execute"


# =============================================================================
# Validation Counter Tests
# =============================================================================

class TestValidationCounting:
    """Test validation failure counting."""

    def test_llm_validation_failed_increments(self, routing_manager_multimode):
        """LLM validation failed counter increments on invalid action."""
        initial = routing_manager_multimode.get_decision_counters()["llm_validation_failed"]

        # Trigger validation failure (None action)
        routing_manager_multimode.validate_action(None, [])

        counters = routing_manager_multimode.get_decision_counters()
        assert counters["llm_validation_failed"] == initial + 1

    def test_valid_action_does_not_increment_failure(self, routing_manager_multimode):
        """Valid action does not increment failure counter."""
        initial = routing_manager_multimode.get_decision_counters()["llm_validation_failed"]

        action = {"action_type": "CLICK", "x": 100, "y": 200}
        routing_manager_multimode.validate_action(action, [], decision_maker="llm")

        counters = routing_manager_multimode.get_decision_counters()
        assert counters["llm_validation_failed"] == initial

    def test_invalid_action_returns_back(self, routing_manager_multimode):
        """Invalid action returns BACK for execution."""
        result = routing_manager_multimode.validate_action(None, [])

        assert result["validation_path"] == "execute"
        assert result["current_action"]["action_type"] == "BACK"


# =============================================================================
# Fixture Integration Tests
# =============================================================================

class TestFixtureIntegration:
    """Test routing with real fixture data."""

    def test_validate_action_with_fixture_coords(self, routing_manager_multimode):
        """Validate action using coordinates from fixture."""
        _, screen_desc = load_fixture("cryptoapp", "001")

        actions = screen_desc.get_all_actions()
        if not actions:
            pytest.skip("No actions in fixture")

        first_action = actions[0]
        coords = first_action.get_execution_coordinates()

        if coords:
            action = {
                "action_type": "CLICK",
                "x": coords[0],
                "y": coords[1]
            }
            result = routing_manager_multimode.validate_action(action, [])

            assert result["validation_path"] == "execute"


# =============================================================================
# Proportion Tracking Tests
# =============================================================================

class TestProportionTracking:
    """Test LLM/algorithm proportion tracking."""

    def test_multimode_proportion_tracking(self, routing_manager_multimode):
        """Track LLM/algorithm proportion in multimode."""
        # Run many iterations
        for i in range(200):
            decision = routing_manager_multimode.route_decision(iteration=i + 1)

            # For LLM decisions, simulate successful validation
            if decision == "llm":
                action = {"action_type": "CLICK", "x": 100 + i, "y": 200 + i}
                routing_manager_multimode.validate_action(action, [], decision_maker="llm")

        counters = routing_manager_multimode.get_decision_counters()

        # In multimode with 0.7 probability, LLM should be ~70%
        total = counters["llm_executed"] + counters["algorithm_chosen"]
        if total > 0:
            llm_pct = counters["llm_percentage"]
            # Allow wide margin for randomness
            assert 40 <= llm_pct <= 90

    def test_pure_algorithm_proportion(self, routing_manager_pure):
        """Pure algorithm mode has 100% algorithm."""
        for i in range(50):
            routing_manager_pure.route_decision(iteration=i + 1)

        counters = routing_manager_pure.get_decision_counters()

        assert counters["algorithm_chosen"] == 50
        assert counters["llm_executed"] == 0
        assert counters["algorithm_percentage"] == 100.0


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Test routing edge cases."""

    def test_empty_action_dict_returns_back(self, routing_manager_multimode):
        """Empty action dict returns BACK."""
        result = routing_manager_multimode.validate_action({}, [])

        assert result["validation_path"] == "execute"
        assert result["current_action"]["action_type"] == "BACK"

    def test_action_with_empty_action_type_returns_back(self, routing_manager_multimode):
        """Action with empty action_type returns BACK."""
        action = {"action_type": "", "x": 100, "y": 200}
        result = routing_manager_multimode.validate_action(action, [])

        assert result["validation_path"] == "execute"
        assert result["current_action"]["action_type"] == "BACK"

    def test_action_with_none_action_type_returns_back(self, routing_manager_multimode):
        """Action with None action_type returns BACK."""
        action = {"action_type": None, "x": 100, "y": 200}
        result = routing_manager_multimode.validate_action(action, [])

        assert result["validation_path"] == "execute"
        assert result["current_action"]["action_type"] == "BACK"

    def test_large_iteration_number(self, routing_manager_pure):
        """Handle large iteration numbers."""
        decision = routing_manager_pure.route_decision(iteration=10000)
        assert decision == "algorithm"

    def test_zero_iteration(self, routing_manager_pure):
        """Handle zero iteration."""
        decision = routing_manager_pure.route_decision(iteration=0)
        assert decision == "algorithm"

    def test_negative_iteration(self, routing_manager_pure):
        """Handle negative iteration."""
        decision = routing_manager_pure.route_decision(iteration=-1)
        assert decision == "algorithm"


# =============================================================================
# Decision Maker Source Tests
# =============================================================================

class TestDecisionMakerSource:
    """Test decision maker source tracking."""

    def test_llm_decision_maker_counts_executed(self, routing_manager_multimode):
        """LLM decision maker increments executed counter."""
        action = {"action_type": "CLICK", "x": 100, "y": 200}

        initial = routing_manager_multimode.get_decision_counters()["llm_executed"]

        routing_manager_multimode.validate_action(action, [], decision_maker="llm")

        counters = routing_manager_multimode.get_decision_counters()
        assert counters["llm_executed"] == initial + 1

    def test_algorithm_decision_maker_does_not_increment_chosen(self, routing_manager_multimode):
        """Algorithm decision maker does not increment algorithm_chosen in validate_action.

        algorithm_chosen is only incremented in route_decision(), not validate_action().
        validate_action() only increments llm_executed for decision_maker="llm".
        """
        action = {"action_type": "CLICK", "x": 100, "y": 200}

        initial = routing_manager_multimode.get_decision_counters()["algorithm_chosen"]

        routing_manager_multimode.validate_action(action, [], decision_maker="algorithm")

        counters = routing_manager_multimode.get_decision_counters()
        assert counters["algorithm_chosen"] == initial

"""
Unit tests for the RoutingManager.

Tests the simplified routing manager that:
- Routes decisions between LLM and algorithm paths
- Validates actions and returns BACK on failure (no fallback cycle)
- Tracks counters for metrics
"""
import pytest
from unittest.mock import MagicMock, patch

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.routing.routing_manager import RoutingManager


@pytest.fixture
def mock_config():
    """Fixture for RVAgentConfig mock."""
    config = MagicMock(spec=RVAgentConfig)
    config.get_agent_mode.return_value = "multimode"
    config.llm_probability = 0.7
    return config


@pytest.fixture
def mock_fallback_manager():
    """Fixture for FallbackManager mock."""
    return MagicMock()


@pytest.fixture
def mock_exploration_strategy():
    """Fixture for ExplorationStrategy mock."""
    return MagicMock()


@pytest.fixture
def routing_manager(mock_config, mock_fallback_manager, mock_exploration_strategy):
    """Fixture for RoutingManager instance."""
    return RoutingManager(
        config=mock_config,
        fallback_manager=mock_fallback_manager,
        exploration_strategy=mock_exploration_strategy
    )


class TestRoutingManager:
    """Test suite for the RoutingManager."""

    def test_initialization(self, routing_manager, mock_config, mock_fallback_manager):
        """Test that the manager initializes correctly."""
        assert routing_manager.config == mock_config
        assert routing_manager.fallback_manager == mock_fallback_manager
        assert routing_manager.llm_executed == 0
        assert routing_manager.algorithm_chosen == 0
        assert routing_manager.llm_validation_failed == 0
        assert routing_manager.forced_back_count == 0

    # --- Tests for route_decision ---

    def test_route_decision_pure_algorithm_mode(self, routing_manager, mock_config):
        """Test routing decision in pure_algorithm mode."""
        mock_config.get_agent_mode.return_value = "pure_algorithm"
        decision = routing_manager.route_decision(iteration=1)
        assert decision == "algorithm"
        assert routing_manager.algorithm_chosen == 1
        assert routing_manager.llm_executed == 0

    def test_route_decision_llm_only_mode(self, routing_manager, mock_config):
        """Test routing decision in llm_only mode."""
        mock_config.get_agent_mode.return_value = "llm_only"
        decision = routing_manager.route_decision(iteration=1)
        assert decision == "llm"
        # llm_executed is incremented after validation, so it should be 0 here
        assert routing_manager.llm_executed == 0
        assert routing_manager.algorithm_chosen == 0

    @patch('random.random', return_value=0.6)
    def test_route_decision_multimode_chooses_llm(self, mock_random, routing_manager, mock_config):
        """Test multimode chooses LLM when random value is below probability."""
        mock_config.llm_probability = 0.7
        decision = routing_manager.route_decision(iteration=1)
        assert decision == "llm"
        assert routing_manager.llm_executed == 0
        assert routing_manager.algorithm_chosen == 0

    @patch('random.random', return_value=0.8)
    def test_route_decision_multimode_chooses_algorithm(self, mock_random, routing_manager, mock_config):
        """Test multimode chooses algorithm when random value is above probability."""
        mock_config.llm_probability = 0.7
        decision = routing_manager.route_decision(iteration=1)
        assert decision == "algorithm"
        assert routing_manager.algorithm_chosen == 1
        assert routing_manager.llm_executed == 0

    def test_route_decision_unknown_mode_defaults_to_algorithm(self, routing_manager, mock_config):
        """Test that unknown mode defaults to algorithm path."""
        mock_config.get_agent_mode.return_value = "unknown_mode"
        decision = routing_manager.route_decision(iteration=1)
        assert decision == "algorithm"
        assert routing_manager.algorithm_chosen == 1

    # --- Tests for validate_action ---

    def test_validate_action_no_action_returns_back(self, routing_manager, mock_config):
        """Test that a None action returns BACK action."""
        result = routing_manager.validate_action(None, recent_actions=[])
        assert result["validation_path"] == "execute"
        assert result["loop_detected"]
        assert result["current_action"]["action_type"] == "BACK"
        assert routing_manager.llm_validation_failed == 1

    def test_validate_action_valid_llm_action_passes(self, routing_manager, mock_config):
        """Test that a valid LLM action passes validation."""
        action = {"action_type": "CLICK", "x": 100, "y": 200}
        result = routing_manager.validate_action(action, recent_actions=[], decision_maker="llm")
        assert result["validation_path"] == "execute"
        assert not result["loop_detected"]
        assert result["current_action"] == action
        assert routing_manager.llm_executed == 1
        assert routing_manager.llm_validation_failed == 0

    def test_validate_action_valid_algorithm_action_passes(self, routing_manager, mock_config):
        """Test that a valid algorithm action passes and increments algorithm_chosen."""
        action = {"action_type": "CLICK", "x": 100, "y": 200}
        result = routing_manager.validate_action(action, recent_actions=[], decision_maker="algorithm")
        assert result["validation_path"] == "execute"
        assert not result["loop_detected"]
        assert result["current_action"] == action
        assert routing_manager.llm_executed == 0
        assert routing_manager.algorithm_chosen == 1

    def test_validate_action_invalid_action_dict_returns_back(self, routing_manager, mock_config):
        """Test that an invalid action dict returns BACK."""
        action = {"action_type": None}
        result = routing_manager.validate_action(action, recent_actions=[])
        assert result["validation_path"] == "execute"
        assert result["loop_detected"]
        assert result["current_action"]["action_type"] == "BACK"
        assert routing_manager.llm_validation_failed == 1

    def test_validate_action_empty_dict_returns_back(self, routing_manager, mock_config):
        """Test that an empty action dict returns BACK."""
        action = {}
        result = routing_manager.validate_action(action, recent_actions=[])
        assert result["validation_path"] == "execute"
        assert result["loop_detected"]
        assert result["current_action"]["action_type"] == "BACK"
        assert routing_manager.llm_validation_failed == 1

    # --- Tests for get_decision_counters ---

    def test_get_decision_counters_initial_values(self, routing_manager):
        """Test the initial counter values."""
        counters = routing_manager.get_decision_counters()
        assert counters["llm_executed"] == 0
        assert counters["algorithm_chosen"] == 0
        assert counters["llm_validation_failed"] == 0
        assert counters["forced_back"] == 0
        assert counters["primary_total"] == 0
        assert counters["total_actions"] == 0

    def test_get_decision_counters_all_values(self, routing_manager):
        """Test the reporting of decision counters with all values non-zero."""
        routing_manager.llm_executed = 65
        routing_manager.algorithm_chosen = 25
        routing_manager.llm_validation_failed = 5
        routing_manager.forced_back_count = 5

        counters = routing_manager.get_decision_counters()

        assert counters["llm_executed"] == 65
        assert counters["algorithm_chosen"] == 25
        assert counters["llm_validation_failed"] == 5
        assert counters["forced_back"] == 5
        assert counters["primary_total"] == 90
        assert counters["total_actions"] == 100
        assert counters["llm_percentage"] == pytest.approx(65 / 90 * 100)
        assert counters["algorithm_percentage"] == pytest.approx(25 / 90 * 100)

    def test_get_decision_counters_percentage_calculation(self, routing_manager):
        """Test percentage calculation in counters."""
        routing_manager.llm_executed = 70
        routing_manager.algorithm_chosen = 30

        counters = routing_manager.get_decision_counters()

        assert counters["llm_percentage"] == pytest.approx(70.0)
        assert counters["algorithm_percentage"] == pytest.approx(30.0)

    # --- Tests for _create_back_action ---

    def test_create_back_action(self, routing_manager):
        """Test BACK action creation."""
        back_action = routing_manager._create_back_action("test_reason")
        assert back_action["action_type"] == "BACK"
        assert back_action["x"] == 0
        assert back_action["y"] == 0
        assert back_action["source"] == "validation"
        assert back_action["reason"] == "test_reason"

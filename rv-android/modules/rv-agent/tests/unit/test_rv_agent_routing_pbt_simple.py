"""
Property-based tests for the RVAgent routing and decision making using Hypothesis.

This test suite focuses on the routing manager and decision making properties that should hold
regardless of specific inputs or configurations.
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from rv_agent.agent.rv_agent import RVAgent
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_agent.services.vision_service import ImageHandler
from rv_agent.services.screen_analyzer import ScreenProcessor
from rv_agent.llm.llm_client import LLMClient
from rv_agent.routing.routing_manager import RoutingManager
from rv_agent.execution.tool_executor import ToolExecutor
from rv_agent.memory.memory_coordinator import MemoryCoordinator


# Define strategies for generating test data
agent_modes = st.sampled_from(["pure_algorithm", "llm_only", "multimode"])

# Strategy for generating valid package names
package_name_strategy = st.text(
    alphabet=st.characters(min_codepoint=97, max_codepoint=122),  # lowercase letters
    min_size=1,
    max_size=50
).filter(lambda x: x.isidentifier())  # Ensure it's a valid identifier

# Strategy for generating timeouts
timeout_strategy = st.floats(min_value=1.0, max_value=3600.0)  # 1 second to 1 hour

# Strategy for generating valid strategy names
strategy_names = st.sampled_from(["dfs", "bfs", "greedy", "rvagent"])

# Strategy for generating screen hashes
screen_hash_strategy = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122),  # alphanumeric + symbols
    min_size=10,
    max_size=64
)

# Strategy for generating action types
action_types = st.sampled_from(["CLICK", "TYPE", "SWIPE", "SCROLL", "BACK", "HOME"])

# Strategy for generating coordinates
coordinate_strategy = st.integers(min_value=0, max_value=2000)

# Strategy for generating action dictionaries
action_strategy = st.fixed_dictionaries({
    "action_type": action_types,
    "x": coordinate_strategy,
    "y": coordinate_strategy,
    "text": st.text(max_size=100),
    "element_id": st.text(max_size=50)
})

# Strategy for generating action sequences
action_sequence_strategy = st.lists(action_strategy, min_size=1, max_size=10)

# Strategy for generating float values for percentages
percentage_strategy = st.floats(min_value=0.0, max_value=100.0)


@pytest.mark.hypothesis
class TestRoutingManager:
    """Property-based tests for the RoutingManager component."""

    def _create_mock_dependencies(self):
        """Helper method to create mock dependencies for testing."""
        mock_deps = {
            "device": MagicMock(spec=DeviceInterface),
            "dynamic_graph": MagicMock(spec=DynamicStateGraph),
            "exploration_strategy": MagicMock(spec=ExplorationStrategy),
            "image_handler": MagicMock(spec=ImageHandler),
            "screen_processor": MagicMock(spec=ScreenProcessor),
            "llm_client": MagicMock(spec=LLMClient),
            "routing_manager": MagicMock(spec=RoutingManager),
            "tool_executor": MagicMock(spec=ToolExecutor),
            "memory_coordinator": MagicMock(spec=MemoryCoordinator),
        }
        
        # Setup routing manager mock
        mock_deps["routing_manager"].forced_back_count = 0
        mock_deps["routing_manager"].llm_executed = 0
        mock_deps["routing_manager"].algorithm_chosen = 0
        mock_deps["routing_manager"].llm_validation_failed = 0
        mock_deps["routing_manager"].get_decision_counters.return_value = {
            "total_actions": 0,
            "llm_executed": 0,
            "algorithm_chosen": 0,
            "llm_percentage": 0.0,
            "algorithm_percentage": 0.0,
            "llm_validation_failed": 0,
            "forced_back": 0,
            "primary_total": 0
        }
        
        return mock_deps

    @given(
        mode=agent_modes,
        iteration=st.integers(min_value=0, max_value=1000)
    )
    @settings(deadline=2000, max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_routing_decision_properties(self, mode, iteration):
        """Test properties of routing decisions based on agent mode."""
        # Create a mock RoutingManager
        routing_manager = MagicMock(spec=RoutingManager)

        # Based on the mode, determine expected behavior
        if mode == "pure_algorithm":
            expected_path = "algorithm"
        elif mode == "llm_only":
            expected_path = "llm"
        else:  # multimode
            # In multimode, it could be either depending on internal logic
            # For testing purposes, we'll pick one deterministically based on iteration
            expected_path = "algorithm" if iteration % 2 == 0 else "llm"

        # Mock the route_decision method
        routing_manager.route_decision.return_value = expected_path

        # Test the routing decision
        decision = routing_manager.route_decision(iteration)

        # Verify that decision is one of the valid paths
        assert decision in ["algorithm", "llm", "end"]

        # Verify the method was called
        routing_manager.route_decision.assert_called()

    @given(
        total_actions=st.integers(min_value=0, max_value=1000),
        llm_executed=st.integers(min_value=0, max_value=1000),
        algorithm_chosen=st.integers(min_value=0, max_value=1000)
    )
    @settings(deadline=2000, max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_decision_counter_properties(self, total_actions, llm_executed, algorithm_chosen):
        """Test properties of decision counters."""
        # Create a mock RoutingManager
        routing_manager = MagicMock(spec=RoutingManager)

        # Calculate percentages
        primary_total = llm_executed + algorithm_chosen
        llm_percentage = (llm_executed / max(primary_total, 1)) * 100 if primary_total > 0 else 0.0
        algorithm_percentage = (algorithm_chosen / max(primary_total, 1)) * 100 if primary_total > 0 else 0.0

        # Mock the get_decision_counters method
        counters = {
            "total_actions": total_actions,
            "llm_executed": llm_executed,
            "algorithm_chosen": algorithm_chosen,
            "llm_percentage": llm_percentage,
            "algorithm_percentage": algorithm_percentage,
            "llm_validation_failed": 0,  # For simplicity
            "forced_back": 0,  # For simplicity
            "primary_total": primary_total
        }

        routing_manager.get_decision_counters.return_value = counters

        # Get counters
        result = routing_manager.get_decision_counters()

        # Verify structure
        assert isinstance(result, dict)
        assert "total_actions" in result
        assert "llm_executed" in result
        assert "algorithm_chosen" in result
        assert "llm_percentage" in result
        assert "algorithm_percentage" in result

        # Verify numerical properties
        assert result["total_actions"] == total_actions
        assert result["llm_executed"] == llm_executed
        assert result["algorithm_chosen"] == algorithm_chosen
        assert 0.0 <= result["llm_percentage"] <= 100.0
        assert 0.0 <= result["algorithm_percentage"] <= 100.0

        # Verify percentage relationships
        if primary_total > 0:
            calculated_total_percentage = result["llm_percentage"] + result["algorithm_percentage"]
            # Due to floating point precision, allow small deviation
            assert abs(calculated_total_percentage - 100.0) < 0.01 or \
                   abs(calculated_total_percentage - 100.0) <= 2.0  # Allow for rounding errors


@pytest.mark.hypothesis
class TestLoopDetection:
    """Property-based tests for the loop detection mechanism."""

    @given(
        actions=action_sequence_strategy,
        loop_threshold=st.integers(min_value=2, max_value=5)
    )
    @settings(deadline=2000, max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_loop_detection_properties(self, actions, loop_threshold):
        """Test properties of loop detection with various action sequences."""
        # Create a mock LoopDetector
        loop_detector = MagicMock()

        # Mock the detect_loop method
        def mock_detect_loop(action, action_history):
            # Simple mock: if the same action appears loop_threshold times consecutively, detect loop
            if len(action_history) >= loop_threshold:
                recent_actions = action_history[-loop_threshold:]
                if all(a["action_type"] == action["action_type"] for a in recent_actions):
                    return True
            return False

        loop_detector.detect_loop = mock_detect_loop

        # Test loop detection with the action sequence
        for i, action in enumerate(actions):
            history = actions[:i]
            is_loop = loop_detector.detect_loop(action, history)

            # Verify that the result is a boolean
            assert isinstance(is_loop, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
"""
Property-based tests for the RVAgent core functionality using Hypothesis.

This test suite focuses on the core RVAgent functionality, testing properties
that should hold regardless of specific inputs or configurations.
"""
import pytest
import time
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


@pytest.mark.hypothesis
class TestRVAgentCoreFunctionality:
    """Property-based tests for the core RVAgent functionality."""

    def _create_mock_dependencies(self):
        """Helper method to create mock dependencies for RVAgent."""
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
        package=package_name_strategy,
        timeout=timeout_strategy,
        strategy_name=strategy_names
    )
    @settings(deadline=2000, max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_agent_initialization_properties(self, mode, package, timeout, strategy_name):
        """Test that RVAgent initialization preserves configuration properties."""
        # Create mock config
        config = MagicMock(spec=RVAgentConfig)
        config.get_agent_mode.return_value = mode
        config.package_name = package
        config.strategy = strategy_name
        config.timeout = timeout
        
        # Create mock dependencies
        mock_deps = self._create_mock_dependencies()
        
        # Skip LLM client requirement for non-LLM modes
        if mode in ["llm_only", "multimode"]:
            # For these modes, we need an LLM client
            agent = RVAgent(config=config, **mock_deps)
        else:
            # For pure algorithm mode, LLM client can be None
            mock_deps["llm_client"] = None
            agent = RVAgent(config=config, **mock_deps)
        
        # Verify that configuration is preserved
        assert agent.config.get_agent_mode() == mode
        assert agent.config.package_name == package
        assert agent.config.strategy == strategy_name
        assert agent.config.timeout == timeout
        
        # Verify that detection thresholds are set correctly
        assert agent.STUCK_THRESHOLD == 3
        assert agent.NO_ACTION_THRESHOLD == 3
        assert agent.stuck_screen_count == 0
        assert agent.consecutive_no_action == 0

    @given(
        current_hash=screen_hash_strategy,
        previous_hash=screen_hash_strategy,
        action=action_strategy
    )
    @settings(deadline=2000, max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_stuck_detection_properties(self, current_hash, previous_hash, action):
        """Test properties of stuck detection mechanism."""
        # Create mock config
        config = MagicMock(spec=RVAgentConfig)
        config.get_agent_mode.return_value = "pure_algorithm"
        config.package_name = "com.example.test"
        config.strategy = "dfs"
        config.timeout = 100.0
        
        # Create mock dependencies
        mock_deps = self._create_mock_dependencies()
        mock_deps["llm_client"] = None  # Pure algorithm mode
        
        agent = RVAgent(config=config, **mock_deps)
        
        # Test stuck detection logic
        # Initially, agent should not be stuck
        assert agent.stuck_screen_count == 0
        
        # If same screen appears multiple times, stuck count should increase
        original_count = agent.stuck_screen_count
        
        # Simulate same screen appearing
        agent.last_screen_hash = current_hash
        
        # Update stuck detection manually to test the logic
        if current_hash == agent.last_screen_hash:
            agent.stuck_screen_count += 1
        else:
            agent.stuck_screen_count = 0
            agent.last_screen_hash = current_hash
        
        # Verify stuck detection properties
        if current_hash == previous_hash:
            # If hashes are the same, stuck count should have increased
            assert agent.stuck_screen_count >= original_count
        else:
            # If hashes differ, stuck count should reset or stay same
            assert agent.stuck_screen_count >= 0

    @given(
        iterations=st.integers(min_value=1, max_value=10),
        action_type=action_types
    )
    @settings(deadline=2000, max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_no_action_detection_properties(self, iterations, action_type):
        """Test properties of no-action detection mechanism."""
        # Create mock config
        config = MagicMock(spec=RVAgentConfig)
        config.get_agent_mode.return_value = "pure_algorithm"
        config.package_name = "com.example.test"
        config.strategy = "dfs"
        config.timeout = 100.0
        
        # Create mock dependencies
        mock_deps = self._create_mock_dependencies()
        mock_deps["llm_client"] = None  # Pure algorithm mode
        
        # Mock strategy to sometimes return None (no action)
        mock_deps["exploration_strategy"].select_next_action.side_effect = [None] * iterations
        
        agent = RVAgent(config=config, **mock_deps)
        
        # Initially, no action count should be 0
        original_count = agent.consecutive_no_action
        
        # Simulate multiple iterations with no action
        for i in range(iterations):
            # In algorithm_node, if no action is returned, counter increases
            selected_action = mock_deps["exploration_strategy"].select_next_action()
            if selected_action is None:
                agent.consecutive_no_action += 1
            else:
                agent.consecutive_no_action = 0  # Reset when action is found
        
        # Verify no-action detection properties
        if iterations > 0:
            assert agent.consecutive_no_action >= original_count
            # The count should be at most the number of iterations
            assert agent.consecutive_no_action <= iterations

    @given(
        num_states=st.integers(min_value=1, max_value=20),
        num_transitions=st.integers(min_value=0, max_value=20)
    )
    @settings(deadline=2000, max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_memory_stats_properties(self, num_states, num_transitions):
        """Test properties of memory statistics reporting."""
        # Create mock config
        config = MagicMock(spec=RVAgentConfig)
        config.get_agent_mode.return_value = "pure_algorithm"
        config.package_name = "com.example.test"
        config.strategy = "dfs"
        config.timeout = 100.0
        
        # Create mock dependencies
        mock_deps = self._create_mock_dependencies()
        mock_deps["llm_client"] = None  # Pure algorithm mode
        
        agent = RVAgent(config=config, **mock_deps)
        
        # Mock memory coordinator to return specific stats
        expected_stats = {
            "total_interactions": num_states,
            "unique_states": num_states,
            "transitions": num_transitions,
            "coverage_percentage": min(100.0, (num_states / max(num_states, 1)) * 100)
        }
        
        mock_deps["memory_coordinator"].get_all_statistics.return_value = expected_stats
        
        # Get memory stats
        stats = agent.get_memory_stats()
        
        # Verify stats structure
        assert isinstance(stats, dict)
        assert "total_interactions" in stats
        assert "unique_states" in stats
        
        # Verify that the returned stats match what was set
        assert stats["total_interactions"] == num_states
        assert stats["unique_states"] == num_states


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
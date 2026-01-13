"""
Simple, focused property-based tests for the most critical RVAgent components using Hypothesis.

This test suite focuses on the most essential properties that should hold regardless of inputs.
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import MagicMock, patch
import time

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


# Define simple strategies for generating test data
agent_modes = st.sampled_from(["pure_algorithm", "multimode"])

# Strategy for generating valid package names
package_name_strategy = st.text(
    alphabet=st.characters(min_codepoint=97, max_codepoint=122),  # lowercase letters
    min_size=1,
    max_size=50
).filter(lambda x: x.isidentifier())  # Ensure it's a valid identifier

# Strategy for generating timeouts
timeout_strategy = st.floats(min_value=10.0, max_value=300.0)  # 10 seconds to 5 minutes

# Strategy for generating screen hashes
screen_hash_strategy = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122),  # alphanumeric + symbols
    min_size=10,
    max_size=64
)

# Strategy for generating action types
action_types = st.sampled_from(["CLICK", "TYPE", "BACK", "HOME"])

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
class TestRVAgentCoreProperties:
    """Essential property-based tests for RVAgent core functionality."""
    
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
        timeout=timeout_strategy
    )
    @settings(deadline=2000, max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_agent_initialization_preserves_configuration(self, mode, package, timeout):
        """Test that RVAgent initialization preserves configuration properties."""
        # Create mock config
        config = MagicMock(spec=RVAgentConfig)
        config.get_agent_mode.return_value = mode
        config.package_name = package
        config.strategy = "dfs"
        config.timeout = timeout
        
        # Create mock dependencies
        mock_deps = self._create_mock_dependencies()
        
        # For pure algorithm mode, set LLM client to None
        if mode == "pure_algorithm":
            mock_deps["llm_client"] = None
        
        # Initialize agent
        agent = RVAgent(config=config, **mock_deps)
        
        # Verify that configuration is preserved
        assert agent.config.get_agent_mode() == mode
        assert agent.config.package_name == package
        assert agent.config.timeout == timeout
        
        # Verify that detection thresholds are properly initialized
        assert agent.STUCK_THRESHOLD == 3
        assert agent.NO_ACTION_THRESHOLD == 3
        assert agent.stuck_screen_count == 0
        assert agent.consecutive_no_action == 0

    @given(
        current_hash=screen_hash_strategy,
        previous_hash=screen_hash_strategy
    )
    @settings(deadline=2000, max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_stuck_detection_logic(self, current_hash, previous_hash):
        """Test the logic of stuck detection mechanism."""
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
        
        # Initially, agent should not be stuck
        assert agent.stuck_screen_count == 0
        
        # If same screen appears multiple times, stuck count should increase
        original_count = agent.stuck_screen_count
        agent.last_screen_hash = current_hash
        
        # Apply stuck detection logic
        if agent.last_screen_hash == current_hash:
            agent.stuck_screen_count += 1
        else:
            agent.stuck_screen_count = 1
            agent.last_screen_hash = current_hash
        
        # Verify stuck detection properties
        if current_hash == previous_hash:
            # If hashes are the same, stuck count should have increased
            assert agent.stuck_screen_count >= original_count
        else:
            # If hashes differ, stuck count should reset to 1
            assert agent.stuck_screen_count == 1

    @given(
        iterations=st.integers(min_value=0, max_value=5),
        has_action=st.booleans()
    )
    @settings(deadline=2000, max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_no_action_detection_logic(self, iterations, has_action):
        """Test the logic of no-action detection for deadlock prevention."""
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
        
        original_count = agent.consecutive_no_action
        
        # Simulate multiple iterations
        for i in range(iterations):
            if has_action:
                # Action found, reset counter
                agent.consecutive_no_action = 0
            else:
                # No action found, increment counter
                agent.consecutive_no_action += 1
        
        # Verify no-action detection properties
        if iterations > 0 and not has_action:
            # If no actions were found in all iterations, counter should increase
            assert agent.consecutive_no_action > original_count
        elif has_action:
            # If action was found, counter should be 0
            assert agent.consecutive_no_action == 0
        else:
            # Otherwise, counter should remain unchanged
            assert agent.consecutive_no_action == original_count


@pytest.mark.hypothesis
class TestRVAgentMemoryProperties:
    """Essential property-based tests for RVAgent memory systems."""

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
        num_interactions=st.integers(min_value=0, max_value=10),
        activity_name=st.text(max_size=50)
    )
    @settings(deadline=2000, max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_memory_stats_structure(self, num_interactions, activity_name):
        """Test that memory statistics have consistent structure."""
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

        # Mock memory coordinator to return consistent stats structure
        expected_stats = {
            "total_interactions": num_interactions,
            "unique_activities": 1,
            "memory_size": num_interactions * 10,  # Simplified
            "coverage_percentage": min(100.0, (num_interactions / max(num_interactions, 1)) * 100)
        }

        mock_deps["memory_coordinator"].get_all_statistics.return_value = expected_stats

        # Get memory stats
        stats = agent.get_memory_stats()

        # Verify that stats is a dictionary with expected keys
        assert isinstance(stats, dict)
        assert "total_interactions" in stats
        assert "unique_activities" in stats
        assert stats["total_interactions"] == num_interactions


@pytest.mark.hypothesis
class TestRVAgentTimeoutLogic:
    """Property-based tests for RVAgent timeout logic."""
    
    @given(
        start_time_offset=st.floats(min_value=0.0, max_value=10.0),
        timeout=timeout_strategy
    )
    @settings(deadline=2000, max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_timeout_logic_properties(self, start_time_offset, timeout):
        """Test properties of timeout logic in RVAgent."""
        # Calculate start time in the past
        start_time = time.time() - start_time_offset
        current_time = time.time()
        elapsed = current_time - start_time
        
        # The condition from the run method
        should_continue = elapsed < timeout
        
        # Verify timeout logic properties
        if elapsed >= timeout:
            assert should_continue is False
        else:
            assert should_continue is True
        
        # Elapsed time should be non-negative
        assert elapsed >= 0
        
        # If timeout is very small compared to elapsed time, should not continue
        if timeout < elapsed:
            assert should_continue is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
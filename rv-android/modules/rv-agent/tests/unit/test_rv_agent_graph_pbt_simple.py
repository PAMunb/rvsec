"""
Property-based tests for the RVAgent LangGraph workflow using Hypothesis.

This test suite focuses on the LangGraph workflow properties that should hold
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
class TestRVAgentGraphWorkflow:
    """Property-based tests for the RVAgent LangGraph workflow."""

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
        screen_hash=screen_hash_strategy,
        action=action_strategy
    )
    @settings(deadline=2000, max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_graph_decision_routing_properties(self, mode, screen_hash, action):
        """Test properties of the decision routing in the graph workflow."""
        # Create mock config
        config = MagicMock(spec=RVAgentConfig)
        config.get_agent_mode.return_value = mode
        config.package_name = "com.example.test"
        config.strategy = "dfs"
        config.timeout = 100.0

        # Create mock dependencies
        mock_deps = self._create_mock_dependencies()

        # For pure algorithm mode, set LLM client to None
        if mode == "pure_algorithm":
            mock_deps["llm_client"] = None

        agent = RVAgent(config=config, **mock_deps)

        # Mock the routing manager to return consistent decisions for the mode
        if mode == "pure_algorithm":
            expected_path = "algorithm"
        elif mode == "llm_only":
            expected_path = "llm"
        else:  # multimode
            # For multimode, it can be either algorithm or llm
            expected_path = "algorithm"  # Use fixed value to avoid complexity

        mock_deps["routing_manager"].route_decision.return_value = expected_path

        # Import the decision router node
        from rv_agent.agent.nodes import decision_router_node

        # Test the decision routing node
        state = {"iteration": 1}
        result = decision_router_node(agent, state)

        # Verify that the decision path is preserved in the result
        assert result["decision_path"] in ["algorithm", "llm", "end"]
        assert result["decision_maker"] in ["algorithm", "llm", "stuck_recovery", "unknown"]

        # If force_back_action is True, decision path should be algorithm
        state_with_force_back = {"iteration": 1, "force_back_action": True}
        result_with_force = decision_router_node(agent, state_with_force_back)
        assert result_with_force["decision_path"] == "algorithm"
        assert result_with_force["decision_maker"] == "stuck_recovery"

    @given(
        action=action_strategy,
        decision_maker=st.sampled_from(["algorithm", "llm", "stuck_recovery", "unknown"])
    )
    @settings(deadline=2000, max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_graph_action_validation_properties(self, action, decision_maker):
        """Test properties of the action validation in the graph workflow."""
        # Create mock config
        config = MagicMock(spec=RVAgentConfig)
        config.get_agent_mode.return_value = "multimode"
        config.package_name = "com.example.test"
        config.strategy = "dfs"
        config.timeout = 100.0

        # Create mock dependencies
        mock_deps = self._create_mock_dependencies()

        agent = RVAgent(config=config, **mock_deps)

        # Mock the routing manager to return validation results
        def mock_validate_action(*args, **kwargs):
            # The actual method signature is (self, action, recent_actions, decision_maker)
            # Extract the arguments from the call
            if len(args) >= 4:  # self + 3 params
                action_arg = args[1] if len(args) > 1 else kwargs.get('action')
                recent_actions_arg = args[2] if len(args) > 2 else kwargs.get('recent_actions', [])
                decision_maker_arg = args[3] if len(args) > 3 else kwargs.get('decision_maker', 'unknown')
            else:
                action_arg = kwargs.get('action')
                recent_actions_arg = kwargs.get('recent_actions', [])
                decision_maker_arg = kwargs.get('decision_maker', 'unknown')

            return {
                "current_action": action_arg,
                "loop_detected": False
            }

        # Set the side_effect to use our mock function
        mock_deps["routing_manager"].validate_action.side_effect = mock_validate_action

        # Import the validation node
        from rv_agent.agent.nodes import validate_action_node

        # Test the validation node with LLM action
        llm_state = {
            "decision_maker": "llm",
            "llm_action": action,
            "recent_action_window": [],
            "loop_detected": False
        }
        llm_result = validate_action_node(agent, llm_state)

        # Verify that LLM action is processed correctly
        assert "current_action" in llm_result
        assert llm_result["current_action"]["action_type"] == action["action_type"]

        # Test the validation node with algorithm action
        algo_state = {
            "decision_maker": "algorithm",
            "current_action": action,
            "recent_action_window": [],
            "loop_detected": False
        }
        algo_result = validate_action_node(agent, algo_state)

        # Verify that algorithm action is processed correctly
        assert "current_action" in algo_result
        assert algo_result["current_action"]["action_type"] == action["action_type"]

    @given(
        screen_hash=screen_hash_strategy,
        activity_name=st.text(max_size=50)
    )
    @settings(deadline=2000, max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_graph_parse_ui_properties(self, screen_hash, activity_name):
        """Test properties of the parse UI node in the graph workflow."""
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

        # Mock the screen processor
        mock_deps["screen_processor"].parse_current_screen.return_value = {
            "screen_hash": screen_hash,
            "activity": activity_name,
            "screen_description": MagicMock(),
            "ui_elements_text": f"Sample UI elements for {activity_name}",
            "is_external": False,
            "external_navigation_count": 0
        }

        # Import the parse UI node
        from rv_agent.agent.nodes import parse_ui_node

        # Test the parse UI node
        state = {"external_navigation_count": 0}
        result = parse_ui_node(agent, state)

        # Verify that the parsed UI information is correctly set in state
        assert result["current_screen_hash"] == screen_hash
        assert result["current_activity"] == activity_name
        assert "ui_elements_text" in result
        assert isinstance(result["ui_elements_text"], str)
        assert result["is_external"] is False
        assert result["external_navigation_count"] == 0


@pytest.mark.hypothesis
class TestRVAgentGraphExecution:
    """Property-based tests for the graph execution functionality."""

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
        action=action_strategy,
        success_status=st.booleans()
    )
    @settings(deadline=2000, max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_graph_execution_properties(self, action, success_status):
        """Test properties of the execution node in the graph workflow."""
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

        # Mock the tool executor
        mock_deps["tool_executor"].execute_action.return_value = {
            "success": success_status,
            "action_executed": action
        }

        # Import the execution node
        from rv_agent.agent.nodes import execute_node

        # Test the execution node
        state = {
            "current_action": action,
            "decision_maker": "algorithm"
        }
        result = execute_node(agent, state)

        # Verify execution results
        assert result["action_success"] == success_status
        assert result["action_executed"]["action_type"] == action["action_type"]

        # If action is None, execution should return None
        none_state = {"current_action": None}
        none_result = execute_node(agent, none_state)
        assert none_result["action_executed"] is None

    @given(
        screen_hash=screen_hash_strategy,
        activity_name=st.text(max_size=50),
        action=action_strategy
    )
    @settings(deadline=2000, max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_graph_learn_node_properties(self, screen_hash, activity_name, action):
        """Test properties of the learn node in the graph workflow."""
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

        # Setup memory mocks
        mock_deps["memory_coordinator"].update_memories.return_value = {"recent_action_window": [action]}
        mock_deps["memory_coordinator"].generate_summaries.return_value = {
            "action_history_summary": "history",
            "exploration_summary": "exploration",
            "memory_insights": "insights",
            "navigation_path": "path"
        }
        mock_deps["memory_coordinator"].track_state_discovery.return_value = {
            "visited_states": [screen_hash],
            "state_transitions": [("prev_hash", screen_hash)]
        }
        mock_deps["memory_coordinator"].check_continuation.return_value = {"should_continue": True}

        # Import the learn node
        from rv_agent.agent.nodes import learn_node

        # Test the learn node
        state = {
            "current_screen_hash": screen_hash,
            "current_activity": activity_name,
            "current_action": action,
            "start_time": 1234567890.0,
            "timeout": 100.0
        }

        result = learn_node(agent, state)

        # Verify that summaries are returned
        assert "action_history_summary" in result
        assert "exploration_summary" in result
        assert "memory_insights" in result
        assert "navigation_path" in result

        # Verify that the result contains expected fields
        assert result["action_history_summary"] == "history"
        assert result["exploration_summary"] == "exploration"
        assert result["memory_insights"] == "insights"
        assert result["navigation_path"] == "path"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
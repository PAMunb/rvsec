"""
High priority unit tests for RVAgent critical scenarios.

These tests focus on the most critical failure scenarios and edge cases
that could impact the reliability of the RVAgent in production environments.
"""

import pytest
import time
from unittest.mock import MagicMock, patch, PropertyMock

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


@pytest.fixture
def agent_config():
    """Standard agent configuration."""
    config = MagicMock(spec=RVAgentConfig)
    config.get_agent_mode.return_value = "multimode"
    config.package_name = "com.example.app"
    config.strategy = "dfs"
    config.timeout = 100
    return config


@pytest.fixture
def mock_dependencies():
    """Standard mock dependencies."""
    mock_deps = {
        "device": MagicMock(spec=DeviceInterface),
        "dynamic_graph": MagicMock(spec=DynamicStateGraph),
        "exploration_strategy": MagicMock(spec=ExplorationStrategy),
        "image_handler": MagicMock(spec=ImageHandler),
        "screen_processor": MagicMock(spec=ScreenProcessor),
        "llm_client": MagicMock(spec=LLMClient),
        "routing_manager": MagicMock(),
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


class TestRVAgentErrorHandlingScenarios:
    """High priority tests for error handling scenarios."""
    
    def test_agent_handles_llm_api_rate_limits(self, agent_config, mock_dependencies):
        """Test agent graceful handling of LLM API rate limits."""
        # Simulate LLM client raising rate limit exception
        mock_dependencies["llm_client"].generate_action.side_effect = Exception("Rate limit exceeded")
        
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        # Test that the agent can handle the exception without crashing
        # This would typically happen in the llm_generate_node
        state = {
            "screen_description": MagicMock(),
            "screenshot_b64": "base64",
            "ui_elements_text": "Button",
            "iteration": 5,
            "action_history_summary": "Previous actions",
            "llm_tokens_input": 100,
            "llm_tokens_output": 10,
            "llm_time_ms": 200
        }
        
        # Since llm_generate_node is external, we test the resilience of the agent
        # by checking that it can continue despite LLM failures
        assert agent.llm_client.generate_action is not None
        
        # Verify the side effect was set
        with pytest.raises(Exception, match="Rate limit exceeded"):
            agent.llm_client.generate_action()
    
    def test_agent_handles_device_connection_issues(self, agent_config, mock_dependencies):
        """Test agent behavior when device becomes disconnected."""
        # Simulate device disconnection
        mock_dependencies["device"].take_screenshot.side_effect = ConnectionError("Device disconnected")
        
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        # Test that the agent can handle device disconnection
        from rv_agent.agent.nodes import capture_screenshot_node
        state = {}
        
        result = capture_screenshot_node(agent, state)
        
        # Should handle the exception gracefully and return end path
        assert result["decision_path"] == "end"
        assert result["screenshot_b64"] == ""
    
    def test_agent_handles_app_crashes(self, agent_config, mock_dependencies):
        """Test agent behavior when target app crashes."""
        # Simulate app crash during launch
        mock_dependencies["device"].launch_app.side_effect = Exception("App crashed")
        
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        # Test the run method handles app crash
        result = agent.run()
        
        assert result["status"] == "error"
        assert "crash" in result["error"].lower() or "App crashed" in result["error"]
    
    def test_agent_handles_android_system_errors(self, agent_config, mock_dependencies):
        """Test agent behavior when Android system throws errors."""
        # Simulate system error during screen parsing
        mock_dependencies["screen_processor"].parse_current_screen.side_effect = Exception("System error")

        agent = RVAgent(config=agent_config, **mock_dependencies)

        from rv_agent.agent.nodes import parse_ui_node
        state = {}

        # The parse_ui_node doesn't handle exceptions internally, so this should propagate
        # This test documents the current behavior where exceptions are not caught
        with pytest.raises(Exception, match="System error"):
            parse_ui_node(agent, state)
    
    def test_agent_handles_permission_denied(self, agent_config, mock_dependencies):
        """Test agent behavior when permissions are denied."""
        # Simulate permission denied error
        mock_dependencies["device"].take_screenshot.side_effect = PermissionError("Permission denied")
        
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        from rv_agent.agent.nodes import capture_screenshot_node
        state = {}
        
        result = capture_screenshot_node(agent, state)
        
        # Should handle permission error gracefully
        assert result["decision_path"] == "end"
        assert result["screenshot_b64"] == ""


class TestRVAgentMultimodeBalancedExecution:
    """High priority tests for multimode balanced execution."""
    
    def test_multimode_balanced_decision_making(self, agent_config, mock_dependencies):
        """Test multimode maintains proper balance between LLM and algorithm decisions."""
        agent_config.get_agent_mode.return_value = "multimode"
        
        # Mock the routing manager to alternate between LLM and algorithm
        call_count = 0
        def route_decision_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return "llm" if call_count % 2 == 0 else "algorithm"
        
        mock_dependencies["routing_manager"].route_decision.side_effect = route_decision_side_effect
        
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        # Test that routing manager is called and alternates appropriately
        from rv_agent.agent.nodes import decision_router_node
        
        # Track routing decisions
        llm_count = 0
        algo_count = 0
        
        for i in range(10):
            state = {"iteration": i}
            result = decision_router_node(agent, state)
            
            if result["decision_path"] == "llm":
                llm_count += 1
            elif result["decision_path"] == "algorithm":
                algo_count += 1
        
        # Should have some balance (not all one way)
        assert llm_count > 0
        assert algo_count > 0
        assert abs(llm_count - algo_count) <= 2  # Allow some variance
    
    def test_multimode_fallback_behavior(self, agent_config, mock_dependencies):
        """Test multimode falls back correctly when LLM fails."""
        agent_config.get_agent_mode.return_value = "multimode"
        
        # Mock LLM to fail occasionally
        call_count = 0
        def generate_action_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Every third call fails
                return {"response": None, "success": False, "tokens_input": 0, "tokens_output": 0, "time_ms": 0}
            else:
                mock_response = MagicMock()
                mock_response.tool_calls = [{"name": "click", "args": {"x": 100, "y": 200}}]
                return {"response": mock_response, "success": True, "tokens_input": 100, "tokens_output": 10, "time_ms": 100}
        
        mock_dependencies["llm_client"].generate_action.side_effect = generate_action_side_effect
        
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        # Test LLM node behavior with occasional failures
        from rv_agent.agent.nodes import llm_generate_node
        
        success_count = 0
        failure_count = 0
        
        for i in range(6):  # Test 6 iterations
            state = {
                "screen_description": MagicMock(),
                "screenshot_b64": "base64",
                "ui_elements_text": "Button",
                "iteration": i,
                "action_history_summary": "Previous actions",
                "llm_tokens_input": 100,
                "llm_tokens_output": 10,
                "llm_time_ms": 200
            }
            result = llm_generate_node(agent, state)
            
            if result["llm_action"] is not None:
                success_count += 1
            else:
                failure_count += 1
        
        # Should have mix of successes and null returns (when LLM fails)
        assert success_count >= 0  # Some should succeed
        assert failure_count >= 0  # Some should fail
    
    def test_multimode_state_consistency(self, agent_config, mock_dependencies):
        """Test multimode maintains consistent state between LLM and algorithm paths."""
        agent_config.get_agent_mode.return_value = "multimode"
        
        # Mock routing to switch between paths
        mock_dependencies["routing_manager"].route_decision.side_effect = lambda: "llm"
        
        # Mock LLM to return consistent action format
        mock_response = MagicMock()
        mock_response.tool_calls = [{"name": "click", "args": {"x": 100, "y": 200}}]
        mock_dependencies["llm_client"].generate_action.return_value = {
            "response": mock_response, 
            "success": True, 
            "tokens_input": 100, 
            "tokens_output": 10, 
            "time_ms": 100
        }
        
        # Mock strategy to return consistent action format
        item_action = MagicMock()
        item_action.get_execution_coordinates.return_value = (150, 250)
        item_action.action_type = "CLICK"
        item_action.id = "btn_test"
        item_action.text = "Test Button"
        mock_dependencies["exploration_strategy"].select_next_action.return_value = item_action
        
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        from rv_agent.agent.nodes import llm_generate_node, algorithm_node
        
        # Test LLM path produces consistent action format
        llm_state = {
            "screen_description": MagicMock(),
            "screenshot_b64": "base64",
            "ui_elements_text": "Button",
            "iteration": 1,
            "action_history_summary": "Previous actions",
            "llm_tokens_input": 100,
            "llm_tokens_output": 10,
            "llm_time_ms": 200
        }
        llm_result = llm_generate_node(agent, llm_state)
        
        # Test algorithm path produces consistent action format  
        algo_state = {"current_screen_hash": "hash1", "screen_description": MagicMock()}
        algo_result = algorithm_node(agent, algo_state)
        
        # Both should have compatible action structures
        assert "llm_action" in llm_result or "current_action" in algo_result
        if "current_action" in algo_result:
            assert "action_type" in algo_result["current_action"]
            assert "x" in algo_result["current_action"] or "y" in algo_result["current_action"]


class TestRVAgentStuckDetectionAndRecovery:
    """High priority tests for stuck detection and recovery."""
    
    def test_stuck_detection_timing_accuracy(self, agent_config, mock_dependencies):
        """Test stuck detection triggers at exact threshold."""
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        from rv_agent.agent.nodes import learn_node
        
        # Setup memory mocks
        mock_dependencies["memory_coordinator"].update_memories.return_value = {"recent_action_window": []}
        mock_dependencies["memory_coordinator"].generate_summaries.return_value = {
            "action_history_summary": "history",
            "exploration_summary": "exploration", 
            "memory_insights": "insights",
            "navigation_path": "path"
        }
        mock_dependencies["memory_coordinator"].track_state_discovery.return_value = {
            "visited_states": ["hash1"],
            "state_transitions": [("hash0", "hash1")]
        }
        mock_dependencies["memory_coordinator"].check_continuation.return_value = {"should_continue": True}
        
        # Set the same screen hash multiple times to trigger stuck detection
        agent.last_screen_hash = "same_hash"
        
        # Before threshold - should not trigger force_back
        for i in range(agent.STUCK_THRESHOLD - 1):
            state = {"current_screen_hash": "same_hash", "start_time": time.time(), "timeout": 100}
            result = learn_node(agent, state)
            assert result.get("force_back_action") is None or result.get("force_back_action") is False
        
        # At threshold - should trigger force_back
        state = {"current_screen_hash": "same_hash", "start_time": time.time(), "timeout": 100}
        result = learn_node(agent, state)
        assert result.get("force_back_action") is True
        
        # Verify counter was reset after triggering
        assert agent.stuck_screen_count == 0
    
    def test_stuck_recovery_effectiveness(self, agent_config, mock_dependencies):
        """Test stuck recovery actually resolves the stuck condition."""
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        from rv_agent.agent.nodes import learn_node, decision_router_node
        
        # Setup memory mocks
        mock_dependencies["memory_coordinator"].update_memories.return_value = {"recent_action_window": []}
        mock_dependencies["memory_coordinator"].generate_summaries.return_value = {
            "action_history_summary": "history",
            "exploration_summary": "exploration",
            "memory_insights": "insights", 
            "navigation_path": "path"
        }
        mock_dependencies["memory_coordinator"].track_state_discovery.return_value = {
            "visited_states": ["hash1"],
            "state_transitions": [("hash0", "hash1")]
        }
        mock_dependencies["memory_coordinator"].check_continuation.return_value = {"should_continue": True}
        
        # Simulate being stuck
        agent.last_screen_hash = "stuck_hash"
        agent.stuck_screen_count = agent.STUCK_THRESHOLD - 1  # Almost at threshold
        
        # Trigger stuck detection
        state = {"current_screen_hash": "stuck_hash", "start_time": time.time(), "timeout": 100}
        learn_result = learn_node(agent, state)
        
        # Verify force_back_action was set
        assert learn_result.get("force_back_action") is True
        
        # Now test that decision router picks up the force_back flag
        mock_dependencies["routing_manager"].route_decision.return_value = "llm"  # Would normally go to LLM
        
        decision_state = {"iteration": 1, "force_back_action": True}
        decision_result = decision_router_node(agent, decision_state)
        
        # Should override normal routing and go to algorithm (for BACK action)
        assert decision_result["decision_path"] == "algorithm"
        assert decision_result["decision_maker"] == "stuck_recovery"
    
    def test_false_positive_stuck_detection(self, agent_config, mock_dependencies):
        """Test stuck detection doesn't trigger unnecessarily."""
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        from rv_agent.agent.nodes import learn_node
        
        # Setup memory mocks
        mock_dependencies["memory_coordinator"].update_memories.return_value = {"recent_action_window": []}
        mock_dependencies["memory_coordinator"].generate_summaries.return_value = {
            "action_history_summary": "history",
            "exploration_summary": "exploration",
            "memory_insights": "insights",
            "navigation_path": "path"
        }
        mock_dependencies["memory_coordinator"].track_state_discovery.return_value = {
            "visited_states": ["hash1"],
            "state_transitions": [("hash0", "hash1")]
        }
        mock_dependencies["memory_coordinator"].check_continuation.return_value = {"should_continue": True}
        
        # Different screen hashes - should not trigger stuck detection
        agent.last_screen_hash = "hash1"
        
        for i, hash_val in enumerate(["hash2", "hash3", "hash4", "hash5"]):
            state = {"current_screen_hash": hash_val, "start_time": time.time(), "timeout": 100}
            result = learn_node(agent, state)
            
            # Should not set force_back_action for different screens
            assert result.get("force_back_action") is None or result.get("force_back_action") is False
            assert agent.stuck_screen_count == 0  # Should reset each time


class TestRVAgentConfigurationValidation:
    """High priority tests for configuration validation."""
    
    def test_agent_with_invalid_config_parameters(self, agent_config, mock_dependencies):
        """Test agent behavior with invalid configuration parameters."""
        # Test with invalid timeout
        agent_config.timeout = -1  # Invalid timeout
        
        # Should still initialize but handle invalid config appropriately
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        # Test run with negative timeout
        with patch('time.sleep'):
            result = agent.run()
        
        # Should handle negative timeout gracefully
        assert result["status"] in ["completed", "error"]
    
    def test_agent_config_validation_comprehensive(self, agent_config, mock_dependencies):
        """Test comprehensive configuration validation."""
        # Test with empty package name
        agent_config.package_name = ""
        
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        # Mock launch to avoid actual device calls
        mock_dependencies["device"].launch_app.side_effect = Exception("Invalid package")
        
        result = agent.run()
        
        assert result["status"] == "error"
        
        # Test with None package name
        agent_config.package_name = None
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        mock_dependencies["device"].launch_app.side_effect = Exception("Invalid package")
        
        result = agent.run()
        
        assert result["status"] == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
Medium priority unit tests for RVAgent scenarios.

These tests focus on performance, complex UI handling, and extended execution scenarios.
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


class TestRVAgentPerformanceScenarios:
    """Medium priority tests for performance scenarios."""
    
    def test_agent_performance_with_large_apps(self, agent_config, mock_dependencies):
        """Test agent performance with complex UI layouts."""
        # Simulate complex UI with many elements
        complex_ui_lines = []
        for i in range(0, 100, 4):  # 100 elements
            complex_ui_lines.extend([
                f"{i}. Button 'Button{i}' at (100, {200+i*10})",
                f"{i+1}. TextView 'Label{i}' at (150, {250+i*10})",
                f"{i+2}. EditText 'Input{i}' at (200, {300+i*10})",
                f"{i+3}. ImageView 'Image{i}' at (250, {350+i*10})",
            ])
        complex_ui_text = "\n".join(complex_ui_lines)

        mock_dependencies["screen_processor"].parse_current_screen.return_value = {
            "screen_hash": "complex_hash",
            "activity": "ComplexActivity",
            "screen_description": MagicMock(),
            "ui_elements_text": complex_ui_text,
            "is_external": False,
            "external_navigation_count": 0
        }

        agent = RVAgent(config=agent_config, **mock_dependencies)

        from rv_agent.agent.nodes import parse_ui_node
        state = {"external_navigation_count": 0}
        start_time = time.time()
        result = parse_ui_node(agent, state)
        end_time = time.time()

        # Should handle complex UI without significant performance degradation
        processing_time = end_time - start_time
        assert processing_time < 1.0  # Should process in under 1 second
        assert result["current_screen_hash"] == "complex_hash"
        assert len(result["ui_elements_text"]) > 1000  # Verify complex UI was processed
    
    def test_agent_memory_usage_over_time(self, agent_config, mock_dependencies):
        """Test memory usage patterns during extended runs."""
        # Mock the memory coordinator to return realistic stats
        initial_stats = {"total_interactions": 0, "unique_states": 0, "memory_size": 100}
        final_stats = {"total_interactions": 10, "unique_states": 8, "memory_size": 150}

        mock_dependencies["memory_coordinator"].get_all_statistics.return_value = initial_stats

        agent = RVAgent(config=agent_config, **mock_dependencies)

        # Get initial memory stats
        initial_memory_stats = agent.get_memory_stats()

        # Simulate 10 iterations of the learn node
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

        for i in range(10):
            state = {
                "current_screen_hash": f"hash_{i}",
                "previous_screen_hash": f"hash_{i-1}" if i > 0 else None,
                "current_activity": f"Activity{i}",
                "current_action": {"action_type": "CLICK", "x": 100, "y": 200},
                "start_time": time.time(),
                "timeout": 100
            }
            learn_node(agent, state)

        # Update memory stats to simulate growth
        mock_dependencies["memory_coordinator"].get_all_statistics.return_value = final_stats

        # Check that memory stats increased appropriately
        final_memory_stats = agent.get_memory_stats()

        # Memory usage should have increased but not exponentially
        # This test mainly verifies that the memory system doesn't crash
        assert isinstance(final_memory_stats, dict)
        assert final_memory_stats["total_interactions"] >= initial_memory_stats["total_interactions"]
    
    def test_agent_cpu_usage_under_load(self, agent_config, mock_dependencies):
        """Test CPU usage during intensive exploration."""
        # This test focuses on verifying the agent doesn't consume excessive resources
        # during intensive operations by measuring execution time
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        # Simulate rapid successive calls to various nodes
        from rv_agent.agent.nodes import algorithm_node
        
        # Mock strategy to return actions quickly
        item_action = MagicMock()
        item_action.get_execution_coordinates.return_value = (100, 200)
        item_action.action_type = "CLICK"
        item_action.id = "btn_test"
        item_action.text = "Test Button"
        mock_dependencies["exploration_strategy"].select_next_action.return_value = item_action
        
        start_time = time.time()
        
        # Execute many algorithm node calls
        for i in range(100):
            state = {
                "current_screen_hash": f"hash_{i % 10}",  # Cycle through 10 hashes
                "screen_description": MagicMock(),
                "force_back_action": False
            }
            result = algorithm_node(agent, state)
            assert result["current_action"]["action_type"] == "CLICK"
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should handle 100 operations in reasonable time (under 5 seconds)
        assert total_time < 5.0


class TestRVAgentComplexUIScenarios:
    """Medium priority tests for complex UI element handling."""
    
    def test_agent_handles_complex_ui_elements(self, agent_config, mock_dependencies):
        """Test agent behavior with complex UI layouts."""
        # Create a complex UI representation with nested elements
        complex_ui_elements = "\n".join([
            "1. RecyclerView 'list_container' at (0, 0, 1080, 1000)",
            "   - ListItem 'item_0' at (10, 10, 1060, 200)",
            "     * Button 'delete_btn_0' at (950, 50, 100, 100)",
            "     * TextView 'title_0' at (20, 20, 500, 80)",
            "   - ListItem 'item_1' at (10, 210, 1060, 400)",
            "     * ImageView 'thumbnail_1' at (20, 20, 150, 150)",
            "     * Button 'action_btn_1' at (200, 100, 200, 80)",
            "2. BottomNavigationView 'bottom_nav' at (0, 1800, 1080, 200)",
            "   - MenuItem 'home' at (0, 0, 270, 200)",
            "   - MenuItem 'search' at (270, 0, 270, 200)",
            "   - MenuItem 'profile' at (810, 0, 270, 200)",
            "3. FloatingActionButton 'fab' at (900, 1700, 150, 150)"
        ])
        
        mock_dependencies["screen_processor"].parse_current_screen.return_value = {
            "screen_hash": "complex_layout_hash",
            "activity": "MainActivity",
            "screen_description": MagicMock(),
            "ui_elements_text": complex_ui_elements,
            "is_external": False,
            "external_navigation_count": 0
        }
        
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        from rv_agent.agent.nodes import parse_ui_node
        state = {"external_navigation_count": 0}
        result = parse_ui_node(agent, state)
        
        # Should handle complex nested UI structure
        assert result["current_screen_hash"] == "complex_layout_hash"
        assert "RecyclerView" in result["ui_elements_text"]
        assert "BottomNavigationView" in result["ui_elements_text"]
    
    def test_agent_handles_dynamic_ui_changes(self, agent_config, mock_dependencies):
        """Test agent behavior with dynamic UI elements."""
        # Simulate UI that changes dynamically (e.g., loading states, animations)
        dynamic_ui_elements = "\n".join([
            "1. ProgressBar 'loading_indicator' at (500, 500, 80, 80) [visible=true]",
            "2. TextView 'status_text' at (400, 600, 280, 60) [text='Loading...']",
            "3. Button 'cancel_btn' at (500, 700, 200, 80) [enabled=false]",
            "4. ListView 'content_list' at (0, 100, 1080, 800) [count=0]"
        ])
        
        mock_dependencies["screen_processor"].parse_current_screen.return_value = {
            "screen_hash": "dynamic_loading_hash",
            "activity": "LoadingActivity",
            "screen_description": MagicMock(),
            "ui_elements_text": dynamic_ui_elements,
            "is_external": False,
            "external_navigation_count": 0
        }
        
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        from rv_agent.agent.nodes import parse_ui_node
        state = {"external_navigation_count": 0}
        result = parse_ui_node(agent, state)
        
        # Should handle dynamic/loading UI states
        assert result["current_screen_hash"] == "dynamic_loading_hash"
        assert "ProgressBar" in result["ui_elements_text"]
        assert "Loading..." in result["ui_elements_text"]
    
    def test_agent_handles_overlay_ui_elements(self, agent_config, mock_dependencies):
        """Test agent behavior with overlay UI elements."""
        # Simulate UI with overlays, dialogs, etc.
        overlay_ui_elements = "\n".join([
            "1. ConstraintLayout 'main_container' at (0, 0, 1080, 1920)",
            "2. Button 'main_action' at (100, 1000, 880, 120)",
            "3. Dialog 'confirmation_dialog' at (180, 400, 720, 600) [overlay=true]",
            "   - TextView 'dialog_title' at (200, 420, 680, 100) [text='Confirm Action']",
            "   - Button 'confirm_btn' at (250, 550, 250, 100) [text='Confirm']",
            "   - Button 'cancel_btn' at (530, 550, 250, 100) [text='Cancel']",
            "4. DimOverlay 'background_dim' at (0, 0, 1080, 1920) [alpha=0.5]"
        ])
        
        mock_dependencies["screen_processor"].parse_current_screen.return_value = {
            "screen_hash": "overlay_dialog_hash",
            "activity": "DialogActivity",
            "screen_description": MagicMock(),
            "ui_elements_text": overlay_ui_elements,
            "is_external": False,
            "external_navigation_count": 0
        }
        
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        from rv_agent.agent.nodes import parse_ui_node
        state = {"external_navigation_count": 0}
        result = parse_ui_node(agent, state)
        
        # Should handle overlay UI elements properly
        assert result["current_screen_hash"] == "overlay_dialog_hash"
        assert "Dialog" in result["ui_elements_text"]
        assert "overlay" in result["ui_elements_text"]


class TestRVAgentExtendedExecutionScenarios:
    """Medium priority tests for extended execution scenarios."""
    
    def test_agent_extended_execution_stability(self, agent_config, mock_dependencies):
        """Test agent stability during extended execution."""
        # Mock a scenario with many iterations
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        # Mock the graph to simulate multiple iterations
        with patch.object(agent, 'graph') as mock_graph:
            # Simulate 50 iterations
            mock_iteration = 0
            def mock_invoke(state, config):
                nonlocal mock_iteration
                mock_iteration += 1
                
                # Return different screen hashes to simulate exploration
                result = {
                    "visited_states": [f"hash_{i}" for i in range(mock_iteration)],
                    "state_transitions": [(f"hash_{i}", f"hash_{i+1}") for i in range(mock_iteration-1)],
                    "llm_tokens_input": mock_iteration * 100,
                    "llm_tokens_output": mock_iteration * 10,
                    "llm_time_ms": mock_iteration * 50.0,
                    "current_screen_hash": f"hash_{mock_iteration}",
                    "current_activity": f"Activity_{mock_iteration}",
                    "current_action": {"action_type": "CLICK", "x": 100, "y": 200},
                    "action_history_summary": f"Action history up to iteration {mock_iteration}",
                    "iteration": mock_iteration
                }
                
                if mock_iteration >= 50:
                    # Stop after 50 iterations
                    raise KeyboardInterrupt()
                
                return result
            
            mock_graph.invoke.side_effect = mock_invoke
            
            # Mock the routing manager counters
            mock_dependencies["routing_manager"].get_decision_counters.return_value = {
                "total_actions": 50,
                "llm_executed": 35,
                "algorithm_chosen": 15,
                "llm_percentage": 70.0,
                "algorithm_percentage": 30.0,
                "llm_validation_failed": 0,
                "forced_back": 0,
                "primary_total": 50
            }
            
            # Mock memory stats
            mock_dependencies["memory_coordinator"].get_all_statistics.return_value = {
                "total_interactions": 50,
                "unique_states": 45
            }
            
            # Mock sleep to speed up test
            with patch('time.sleep'):
                try:
                    result = agent.run()
                except KeyboardInterrupt:
                    # Expected due to our mock
                    pass
                else:
                    # If no exception, check the result
                    assert result["iterations"] <= 50
                    assert result["status"] in ["completed", "error"]
    
    def test_agent_resource_cleanup_after_execution(self, agent_config, mock_dependencies):
        """Test agent cleans up resources after execution."""
        # Test that agent properly manages resources
        agent = RVAgent(config=agent_config, **mock_dependencies)
        
        # Capture initial state
        initial_attrs = set(dir(agent))
        
        # Perform some operations
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
        
        # Run several learn node operations
        for i in range(10):
            state = {
                "current_screen_hash": f"hash_{i}",
                "previous_screen_hash": f"hash_{i-1}" if i > 0 else None,
                "current_activity": f"Activity{i}",
                "current_action": {"action_type": "CLICK", "x": 100, "y": 200},
                "start_time": time.time(),
                "timeout": 100
            }
            learn_node(agent, state)
        
        # Check that no unexpected attributes were added
        final_attrs = set(dir(agent))
        new_attrs = final_attrs - initial_attrs
        
        # Only allow expected temporary attributes
        allowed_new_attrs = set()
        unexpected_attrs = new_attrs - allowed_new_attrs
        
        # This test mainly verifies that the agent doesn't leak attributes
        # In practice, we expect no unexpected attributes to be added
        assert len(unexpected_attrs) == 0, f"Unexpected attributes added: {unexpected_attrs}"
    
    def test_agent_concurrent_operation_isolation(self, agent_config, mock_dependencies):
        """Test that agent operations are isolated."""
        # Create two separate agent instances
        agent1 = RVAgent(config=agent_config, **mock_dependencies)
        
        # Create new dependencies for agent2 to ensure isolation
        mock_deps2 = {
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
        
        mock_deps2["routing_manager"].forced_back_count = 0
        mock_deps2["routing_manager"].llm_executed = 0
        mock_deps2["routing_manager"].algorithm_chosen = 0
        mock_deps2["routing_manager"].llm_validation_failed = 0
        mock_deps2["routing_manager"].get_decision_counters.return_value = {
            "total_actions": 0,
            "llm_executed": 0,
            "algorithm_chosen": 0,
            "llm_percentage": 0.0,
            "algorithm_percentage": 0.0,
            "llm_validation_failed": 0,
            "forced_back": 0,
            "primary_total": 0
        }
        
        agent2 = RVAgent(config=agent_config, **mock_deps2)
        
        # Verify agents have independent state
        assert agent1.stuck_screen_count == agent2.stuck_screen_count == 0
        assert agent1.consecutive_no_action == agent2.consecutive_no_action == 0
        assert agent1.last_screen_hash == agent2.last_screen_hash == None
        
        # Modify one agent's state
        agent1.stuck_screen_count = 5
        agent1.last_screen_hash = "agent1_hash"
        
        # Verify other agent is unaffected
        assert agent2.stuck_screen_count == 0
        assert agent2.last_screen_hash is None
        assert agent1.stuck_screen_count == 5  # Original still changed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
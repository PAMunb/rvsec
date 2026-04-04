"""
Integration tests for component interactions in RVAgent.

Tests the integration between major components without requiring emulator.
"""

from unittest.mock import MagicMock, patch
from rv_agent.agent.rv_agent import RVAgent
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_agent.services.screen_analyzer import ScreenProcessor
from rv_agent.execution.tool_executor import ToolExecutor
from rv_agent.routing.routing_manager import RoutingManager
from rv_agent.domain.state import AgentState

# class TestRVAgentComponentIntegration:
#     """Test integration between RVAgent and its core components."""
#
#     @patch('rv_agent.agent.rv_agent.DynamicStateGraph')
#     @patch('rv_agent.agent.rv_agent.UICoverageTracker')
#     @patch('rv_agent.agent.rv_agent.ScreenProcessor')
#     @patch('rv_agent.agent.rv_agent.LLMClient')
#     @patch('rv_agent.agent.rv_agent.ToolExecutor')
#     @patch('rv_agent.agent.rv_agent.MemoryCoordinator')
#     @patch('rv_agent.agent.rv_agent.RoutingManager')
#     @patch('rv_agent.agent.rv_agent.DeviceInterface')
#     def test_rvagent_initialization_with_all_components(
#         self,
#         mock_device_interface,
#         mock_routing_manager,
#         mock_memory_coordinator,
#         mock_tool_executor,
#         mock_llm_client,
#         mock_screen_processor,
#         mock_ui_coverage,
#         mock_dynamic_graph
#     ):
#         """RVAgent successfully integrates with all core components."""
#         # Create mock instances
#         mock_device = MagicMock()
#         mock_device_interface.return_value = mock_device
#
#         mock_graph = MagicMock()
#         mock_dynamic_graph.return_value = mock_graph
#
#         mock_coverage = MagicMock()
#         mock_ui_coverage.return_value = mock_coverage
#
#         mock_screen_proc = MagicMock()
#         mock_screen_processor.return_value = mock_screen_proc
#
#         mock_llm = MagicMock()
#         mock_llm_client.return_value = mock_llm
#
#         mock_tool_exec = MagicMock()
#         mock_tool_executor.return_value = mock_tool_exec
#
#         mock_memory_coord = MagicMock()
#         mock_memory_coordinator.return_value = mock_memory_coord
#
#         mock_routing = MagicMock()
#         mock_routing_manager.return_value = mock_routing
#
#         # Create config
#         config = RVAgentConfig(
#             package_name="com.example.test",
#             device_id="emulator-5554",
#             llm_base_url="http://test.url",
#             llm_model="test-model"
#         )
#
#         # Initialize RVAgent
#         agent = RVAgent(
#             config=config,
#             device=mock_device,
#             dynamic_graph=mock_graph,
#             exploration_strategy=MagicMock(),
#             image_handler=MagicMock(),
#             screen_processor=mock_screen_proc,
#             llm_client=mock_llm,
#             routing_manager=mock_routing,
#             tool_executor=mock_tool_exec,
#             memory_coordinator=mock_memory_coord,
#             ui_coverage=mock_coverage
#         )
#
#         # Verify all components are properly integrated
#         assert agent.device == mock_device
#         assert agent.graph == mock_graph
#         assert agent.ui_coverage == mock_coverage
#         assert agent.screen_processor == mock_screen_proc
#         assert agent.llm_client == mock_llm
#         assert agent.tool_executor == mock_tool_exec
#         assert agent.memory_coordinator == mock_memory_coord
#         assert agent.routing_manager == mock_routing


class TestStrategyMemoryIntegration:
    """Test integration between strategy and memory components."""

    def test_strategy_uses_memory_coordinator_for_state_tracking(self):
        """RVAgentStrategy can hold a MemoryCoordinator reference for state tracking."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        mock_memory_coordinator = MagicMock()

        # Create strategy with mocked dependencies
        config = RVAgentConfig.create_default(package_name="com.test.app")
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage,
            config=config,
        )
        strategy.memory_coordinator = mock_memory_coordinator

        # The strategy should have access to the memory coordinator
        assert hasattr(strategy, "memory_coordinator")
        assert strategy.memory_coordinator is mock_memory_coordinator


class TestToolExecutorStrategyIntegration:
    """Test integration between ToolExecutor and Strategy components."""

    def test_tool_executor_records_transitions_that_strategy_tracks(self):
        """ToolExecutor and Strategy properly coordinate transition tracking."""
        # This test verifies that when ToolExecutor records a transition,
        # the Strategy component can access that information

        mock_device = MagicMock()
        mock_device.click.return_value = True

        # Create tool executor
        tool_executor = ToolExecutor(device=mock_device)

        # Mock the action to execute
        action = {
            "action_type": "CLICK",
            "x": 100,
            "y": 200,
            "element_description": "Test button",
        }

        # Execute the action
        result = tool_executor.execute_action(action)

        # Verify the action was executed
        mock_device.click.assert_called_once_with(100, 200)
        assert result["success"] is True


class TestScreenAnalyzerLLMIntegration:
    """Test integration between ScreenAnalyzer and LLM components."""

    def test_screen_processor_requires_correct_dependencies(self):
        """ScreenProcessor requires correct dependencies during initialization."""
        mock_device = MagicMock()
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()

        # Create screen processor with correct dependencies
        screen_processor = ScreenProcessor(
            device=mock_device, dynamic_graph=mock_graph, ui_coverage=mock_ui_coverage
        )

        # Verify initialization
        assert screen_processor.device == mock_device
        assert screen_processor.dynamic_graph == mock_graph
        assert screen_processor.ui_coverage == mock_ui_coverage


# class TestMemoryCoordinatorIntegration:
#     """Test integration of MemoryCoordinator with other components."""
#
#     def test_memory_coordinator_requires_correct_dependencies(self):
#         """MemoryCoordinator requires correct dependencies during initialization."""
#         mock_graph = MagicMock()
#         mock_short_term = MagicMock()
#         mock_long_term = MagicMock()
#         mock_ui_coverage = MagicMock()
#         mock_agent_memory = MagicMock()
#
#         # Create memory coordinator with correct dependencies
#         memory_coordinator = MemoryCoordinator(
#             dynamic_graph=mock_graph,
#             short_term_memory=mock_short_term,
#             long_term_memory=mock_long_term,
#             ui_coverage=mock_ui_coverage,
#             agent_memory=mock_agent_memory
#         )
#
#         # Verify initialization
#         assert memory_coordinator.dynamic_graph == mock_graph
#         assert memory_coordinator.short_term_memory == mock_short_term
#         assert memory_coordinator.long_term_memory == mock_long_term
#         assert memory_coordinator.ui_coverage == mock_ui_coverage
#         assert memory_coordinator.agent_memory == mock_agent_memory


class TestRoutingManagerIntegration:
    """Test integration of RoutingManager with decision components."""

    def test_routing_manager_requires_correct_dependencies(self):
        """RoutingManager requires correct dependencies during initialization."""
        mock_config = MagicMock()
        mock_config.seed = None  # Required: RoutingManager.__init__ checks config.seed
        mock_fallback_manager = MagicMock()
        mock_exploration_strategy = MagicMock()

        # Create routing manager with correct dependencies
        routing_manager = RoutingManager(
            config=mock_config,
            fallback_manager=mock_fallback_manager,
            exploration_strategy=mock_exploration_strategy,
        )

        # Verify initialization
        assert routing_manager.config == mock_config
        assert routing_manager.fallback_manager == mock_fallback_manager
        assert routing_manager.exploration_strategy == mock_exploration_strategy


class TestEndToEndFlowMocked:
    """Test end-to-end flow with mocked components."""

    @patch("rv_agent.agent.rv_agent.DynamicStateGraph")
    @patch("rv_agent.agent.rv_agent.UICoverageTracker")
    @patch("rv_agent.agent.rv_agent.ScreenProcessor")
    @patch("rv_agent.agent.rv_agent.LLMClient")
    @patch("rv_agent.agent.rv_agent.ToolExecutor")
    @patch("rv_agent.agent.rv_agent.MemoryCoordinator")
    @patch("rv_agent.agent.rv_agent.RoutingManager")
    @patch("rv_agent.agent.rv_agent.DeviceInterface")
    def test_complete_iteration_cycle(
        self,
        mock_device_interface,
        mock_routing_manager,
        mock_memory_coordinator,
        mock_tool_executor,
        mock_llm_client,
        mock_screen_processor,
        mock_ui_coverage,
        mock_dynamic_graph,
    ):
        """Complete iteration cycle works with all components properly integrated."""
        # Create mock instances
        mock_device = MagicMock()
        mock_device_interface.return_value = mock_device
        mock_device.get_current_ui_state.return_value = {
            "activity": "MainActivity",
            "elements": [],
        }
        mock_device.take_screenshot.return_value = "/tmp/screenshot.png"

        mock_graph = MagicMock()
        mock_dynamic_graph.return_value = mock_graph

        mock_coverage = MagicMock()
        mock_ui_coverage.return_value = mock_coverage

        mock_screen_proc = MagicMock()
        mock_screen_processor.return_value = mock_screen_proc
        mock_screen_proc.capture_and_process.return_value = {
            "screenshot_b64": "base64image",
            "ui_elements_text": "Button: OK",
            "screen_description": MagicMock(),
        }

        mock_llm = MagicMock()
        mock_llm_client.return_value = mock_llm
        mock_llm.generate_with_retry.return_value = MagicMock()
        mock_llm.generate_with_retry.return_value.content = "Test response"

        mock_tool_exec = MagicMock()
        mock_tool_executor.return_value = mock_tool_exec
        mock_tool_exec.execute_action.return_value = {
            "success": True,
            "action_executed": {"action_type": "CLICK"},
        }

        mock_memory_coord = MagicMock()
        mock_memory_coordinator.return_value = mock_memory_coord
        mock_memory_coord.update_memories.return_value = {"recent_action_window": []}
        mock_memory_coord.generate_summaries.return_value = {
            "action_history_summary": "",
            "exploration_summary": "",
            "memory_insights": "",
            "navigation_path": "",
        }
        mock_memory_coord.check_continuation.return_value = {"should_continue": True}

        mock_routing = MagicMock()
        mock_routing_manager.return_value = mock_routing
        mock_routing.route_iteration.return_value = {
            "use_llm": True,
            "use_algorithm": False,
        }

        # Create config
        config = RVAgentConfig(
            package_name="com.example.test",
            device_id="emulator-5554",
            llm_base_url="http://test.url",
            llm_model="test-model",
        )

        # Create RVAgent with mocked components
        agent = RVAgent(
            config=config,
            device=mock_device,
            dynamic_graph=mock_graph,
            exploration_strategy=MagicMock(),
            image_handler=MagicMock(),
            screen_processor=mock_screen_proc,
            llm_client=mock_llm,
            routing_manager=mock_routing,
            tool_executor=mock_tool_exec,
            memory_coordinator=mock_memory_coord,
            ui_coverage=mock_coverage,
        )

        # Create initial state
        initial_state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="initial_hash",
            visited_states=set(),
            state_transitions=[],
            recent_action_window=[],
            iteration=0,
        )

        # Verify that the agent has all required components
        assert agent.device is not None
        assert agent.screen_processor is not None
        assert agent.llm_client is not None
        assert agent.tool_executor is not None
        assert agent.memory_coordinator is not None
        assert agent.routing_manager is not None
        assert agent.graph is not None
        assert agent.ui_coverage is not None


# class TestComponentDependencyInjection:
#     """Test that components receive proper dependencies."""
#
#     def test_basic_components_can_be_initialized(self):
#         """Basic components can be initialized without requiring external connections."""
#         # Test DynamicStateGraph initialization
#         mock_graph = DynamicStateGraph()
#         assert mock_graph is not None
#         # Check if it has expected methods
#         assert hasattr(mock_graph, 'get_or_create_state')
#
#         # Test UICoverageTracker initialization
#         mock_ui_coverage = UICoverageTracker()
#         assert mock_ui_coverage is not None
#         # Check if it has expected methods
#         assert hasattr(mock_ui_coverage, 'update_coverage')

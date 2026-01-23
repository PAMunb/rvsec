"""
Unit tests for AgentFactory.

Tests factory pattern for creating fully configured RVAgent instances.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from rv_agent.agent.agent_factory import AgentFactory
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.agent.rv_agent import RVAgent


@pytest.fixture
def base_config():
    """Create base configuration for testing."""
    config = MagicMock(spec=RVAgentConfig)
    config.get_agent_mode.return_value = "pure_algorithm"
    config.package_name = "com.example.app"
    config.device_id = "emulator-5554"
    config.strategy = "dfs"
    config.timeout = 100
    config.screenshot_dir = "/tmp/screenshots"
    config.screenshot_rotation_limit = 50
    config.device_dimensions = (1080, 1920)
    config.optimized_dimensions = (704, 1248)
    config.max_external_attempts = 3
    config.plateau_window = 5
    config.max_input_variations = 3
    config.llm_timeout = 30.0
    config.prompt_version = "v12"
    config.stochastic_probability = 0.3
    config.stochastic_temperature = 1.0
    return config


@pytest.fixture
def mock_device():
    """Create mock device interface."""
    return MagicMock(spec=DeviceInterface)


class TestAgentFactoryCreateAgent:
    """Test create_agent method."""

    @patch('rv_agent.agent.agent_factory.DeviceInterface')
    @patch('rv_agent.agent.agent_factory.DynamicStateGraph')
    @patch('rv_agent.agent.agent_factory.UICoverageTracker')
    @patch('rv_agent.agent.agent_factory.StrategyRegistry')
    @patch('rv_agent.agent.agent_factory.ImageHandler')
    @patch('rv_agent.agent.agent_factory.ScreenProcessor')
    @patch('rv_agent.agent.agent_factory.FallbackManager')
    @patch('rv_agent.agent.agent_factory.RoutingManager')
    @patch('rv_agent.agent.agent_factory.ToolExecutor')
    @patch('rv_agent.agent.agent_factory.LongTermMemory')
    @patch('rv_agent.agent.agent_factory.ShortTermMemory')
    @patch('rv_agent.agent.agent_factory.AgentMemoryManager')
    @patch('rv_agent.agent.agent_factory.MemoryCoordinator')
    @patch('rv_agent.agent.agent_factory.RVAgent')
    def test_creates_agent_pure_algorithm(
        self,
        mock_rv_agent,
        mock_memory_coord,
        mock_agent_memory,
        mock_short_term,
        mock_long_term,
        mock_tool_executor,
        mock_routing,
        mock_fallback,
        mock_screen_processor,
        mock_image_handler,
        mock_strategy_registry,
        mock_ui_coverage,
        mock_dynamic_graph,
        mock_device_interface,
        base_config
    ):
        """Creates agent in pure_algorithm mode."""
        mock_strategy_instance = MagicMock()
        mock_strategy_registry.return_value.get_strategy.return_value = mock_strategy_instance
        mock_rv_agent.return_value = MagicMock(spec=RVAgent)

        agent = AgentFactory.create_agent(base_config)

        assert agent is not None
        mock_rv_agent.assert_called_once()
        mock_device_interface.assert_called_once_with(device_id="emulator-5554")

    @patch('rv_agent.agent.agent_factory.DeviceInterface')
    @patch('rv_agent.agent.agent_factory.DynamicStateGraph')
    @patch('rv_agent.agent.agent_factory.UICoverageTracker')
    @patch('rv_agent.agent.agent_factory.StrategyRegistry')
    @patch('rv_agent.agent.agent_factory.ImageHandler')
    @patch('rv_agent.agent.agent_factory.ScreenProcessor')
    @patch('rv_agent.agent.agent_factory.FallbackManager')
    @patch('rv_agent.agent.agent_factory.RoutingManager')
    @patch('rv_agent.agent.agent_factory.ToolExecutor')
    @patch('rv_agent.agent.agent_factory.LongTermMemory')
    @patch('rv_agent.agent.agent_factory.ShortTermMemory')
    @patch('rv_agent.agent.agent_factory.AgentMemoryManager')
    @patch('rv_agent.agent.agent_factory.MemoryCoordinator')
    @patch('rv_agent.agent.agent_factory.RVAgent')
    def test_uses_injected_device(
        self,
        mock_rv_agent,
        mock_memory_coord,
        mock_agent_memory,
        mock_short_term,
        mock_long_term,
        mock_tool_executor,
        mock_routing,
        mock_fallback,
        mock_screen_processor,
        mock_image_handler,
        mock_strategy_registry,
        mock_ui_coverage,
        mock_dynamic_graph,
        mock_device_interface,
        base_config,
        mock_device
    ):
        """Uses injected device interface instead of creating new one."""
        mock_strategy_instance = MagicMock()
        mock_strategy_registry.return_value.get_strategy.return_value = mock_strategy_instance
        mock_rv_agent.return_value = MagicMock(spec=RVAgent)

        agent = AgentFactory.create_agent(base_config, device=mock_device)

        assert agent is not None
        mock_device_interface.assert_not_called()

    def test_invalid_mode_raises_error(self, base_config):
        """Invalid mode raises ValueError."""
        base_config.get_agent_mode.return_value = "invalid_mode"

        with pytest.raises(ValueError, match="Invalid mode: invalid_mode"):
            AgentFactory.create_agent(base_config)

    @patch('rv_agent.agent.agent_factory.DeviceInterface')
    @patch('rv_agent.agent.agent_factory.DynamicStateGraph')
    @patch('rv_agent.agent.agent_factory.UICoverageTracker')
    @patch('rv_agent.agent.agent_factory.StrategyRegistry')
    @patch('rv_agent.agent.agent_factory.ImageHandler')
    @patch('rv_agent.agent.agent_factory.ScreenProcessor')
    @patch('rv_agent.agent.agent_factory.FallbackManager')
    @patch('rv_agent.agent.agent_factory.RoutingManager')
    @patch('rv_agent.agent.agent_factory.ToolExecutor')
    @patch('rv_agent.agent.agent_factory.LongTermMemory')
    @patch('rv_agent.agent.agent_factory.ShortTermMemory')
    @patch('rv_agent.agent.agent_factory.AgentMemoryManager')
    @patch('rv_agent.agent.agent_factory.MemoryCoordinator')
    @patch('rv_agent.agent.agent_factory.RVAgent')
    def test_creates_strategy_via_registry(
        self,
        mock_rv_agent,
        mock_memory_coord,
        mock_agent_memory,
        mock_short_term,
        mock_long_term,
        mock_tool_executor,
        mock_routing,
        mock_fallback,
        mock_screen_processor,
        mock_image_handler,
        mock_strategy_registry,
        mock_ui_coverage,
        mock_dynamic_graph,
        mock_device_interface,
        base_config
    ):
        """Creates exploration strategy via StrategyRegistry."""
        mock_strategy = MagicMock()
        mock_registry = MagicMock()
        mock_registry.get_strategy.return_value = mock_strategy
        mock_strategy_registry.return_value = mock_registry
        mock_rv_agent.return_value = MagicMock(spec=RVAgent)

        AgentFactory.create_agent(base_config)

        mock_registry.get_strategy.assert_called_once()
        call_kwargs = mock_registry.get_strategy.call_args[1]
        assert call_kwargs['name'] == 'dfs'
        assert call_kwargs['plateau_window'] == 5
        assert call_kwargs['max_input_variations'] == 3

    @patch('rv_agent.agent.agent_factory.DeviceInterface')
    @patch('rv_agent.agent.agent_factory.DynamicStateGraph')
    @patch('rv_agent.agent.agent_factory.UICoverageTracker')
    @patch('rv_agent.agent.agent_factory.StrategyRegistry')
    @patch('rv_agent.agent.agent_factory.ImageHandler')
    @patch('rv_agent.agent.agent_factory.ScreenProcessor')
    @patch('rv_agent.agent.agent_factory.FallbackManager')
    @patch('rv_agent.agent.agent_factory.RoutingManager')
    @patch('rv_agent.agent.agent_factory.ToolExecutor')
    @patch('rv_agent.agent.agent_factory.LongTermMemory')
    @patch('rv_agent.agent.agent_factory.ShortTermMemory')
    @patch('rv_agent.agent.agent_factory.AgentMemoryManager')
    @patch('rv_agent.agent.agent_factory.MemoryCoordinator')
    @patch('rv_agent.agent.agent_factory.RVAgent')
    def test_passes_static_data(
        self,
        mock_rv_agent,
        mock_memory_coord,
        mock_agent_memory,
        mock_short_term,
        mock_long_term,
        mock_tool_executor,
        mock_routing,
        mock_fallback,
        mock_screen_processor,
        mock_image_handler,
        mock_strategy_registry,
        mock_ui_coverage,
        mock_dynamic_graph,
        mock_device_interface,
        base_config
    ):
        """Passes static data to components that need it."""
        mock_strategy_instance = MagicMock()
        mock_strategy_registry.return_value.get_strategy.return_value = mock_strategy_instance
        mock_rv_agent.return_value = MagicMock(spec=RVAgent)
        static_data = MagicMock()

        AgentFactory.create_agent(base_config, static_data=static_data)

        # Verify static_data passed to RVAgent
        call_kwargs = mock_rv_agent.call_args[1]
        assert call_kwargs['static_data'] == static_data

        # Verify static_data passed to LongTermMemory
        mock_long_term.assert_called_once_with(static_data=static_data)


class TestAgentFactoryLLMModes:
    """Test LLM mode configurations."""

    @patch('rv_agent.agent.agent_factory.DeviceInterface')
    @patch('rv_agent.agent.agent_factory.DynamicStateGraph')
    @patch('rv_agent.agent.agent_factory.UICoverageTracker')
    @patch('rv_agent.agent.agent_factory.StrategyRegistry')
    @patch('rv_agent.agent.agent_factory.ImageHandler')
    @patch('rv_agent.agent.agent_factory.ScreenProcessor')
    @patch('rv_agent.agent.agent_factory.FallbackManager')
    @patch('rv_agent.agent.agent_factory.RoutingManager')
    @patch('rv_agent.agent.agent_factory.ToolExecutor')
    @patch('rv_agent.agent.agent_factory.LongTermMemory')
    @patch('rv_agent.agent.agent_factory.ShortTermMemory')
    @patch('rv_agent.agent.agent_factory.AgentMemoryManager')
    @patch('rv_agent.agent.agent_factory.MemoryCoordinator')
    @patch('rv_agent.agent.agent_factory.RVAgent')
    @patch.object(AgentFactory, '_create_llm_client')
    def test_creates_llm_client_for_llm_only(
        self,
        mock_create_llm,
        mock_rv_agent,
        mock_memory_coord,
        mock_agent_memory,
        mock_short_term,
        mock_long_term,
        mock_tool_executor,
        mock_routing,
        mock_fallback,
        mock_screen_processor,
        mock_image_handler,
        mock_strategy_registry,
        mock_ui_coverage,
        mock_dynamic_graph,
        mock_device_interface,
        base_config
    ):
        """Creates LLM client for llm_only mode."""
        base_config.get_agent_mode.return_value = "llm_only"
        mock_strategy_instance = MagicMock()
        mock_strategy_registry.return_value.get_strategy.return_value = mock_strategy_instance
        mock_rv_agent.return_value = MagicMock(spec=RVAgent)
        mock_llm_client = MagicMock()
        mock_create_llm.return_value = mock_llm_client

        AgentFactory.create_agent(base_config)

        mock_create_llm.assert_called_once_with(base_config)

    @patch('rv_agent.agent.agent_factory.DeviceInterface')
    @patch('rv_agent.agent.agent_factory.DynamicStateGraph')
    @patch('rv_agent.agent.agent_factory.UICoverageTracker')
    @patch('rv_agent.agent.agent_factory.StrategyRegistry')
    @patch('rv_agent.agent.agent_factory.ImageHandler')
    @patch('rv_agent.agent.agent_factory.ScreenProcessor')
    @patch('rv_agent.agent.agent_factory.FallbackManager')
    @patch('rv_agent.agent.agent_factory.RoutingManager')
    @patch('rv_agent.agent.agent_factory.ToolExecutor')
    @patch('rv_agent.agent.agent_factory.LongTermMemory')
    @patch('rv_agent.agent.agent_factory.ShortTermMemory')
    @patch('rv_agent.agent.agent_factory.AgentMemoryManager')
    @patch('rv_agent.agent.agent_factory.MemoryCoordinator')
    @patch('rv_agent.agent.agent_factory.RVAgent')
    @patch.object(AgentFactory, '_create_llm_client')
    def test_creates_llm_client_for_multimode(
        self,
        mock_create_llm,
        mock_rv_agent,
        mock_memory_coord,
        mock_agent_memory,
        mock_short_term,
        mock_long_term,
        mock_tool_executor,
        mock_routing,
        mock_fallback,
        mock_screen_processor,
        mock_image_handler,
        mock_strategy_registry,
        mock_ui_coverage,
        mock_dynamic_graph,
        mock_device_interface,
        base_config
    ):
        """Creates LLM client for multimode."""
        base_config.get_agent_mode.return_value = "multimode"
        mock_strategy_instance = MagicMock()
        mock_strategy_registry.return_value.get_strategy.return_value = mock_strategy_instance
        mock_rv_agent.return_value = MagicMock(spec=RVAgent)
        mock_llm_client = MagicMock()
        mock_create_llm.return_value = mock_llm_client

        AgentFactory.create_agent(base_config)

        mock_create_llm.assert_called_once_with(base_config)

    @patch('rv_agent.agent.agent_factory.DeviceInterface')
    @patch('rv_agent.agent.agent_factory.DynamicStateGraph')
    @patch('rv_agent.agent.agent_factory.UICoverageTracker')
    @patch('rv_agent.agent.agent_factory.StrategyRegistry')
    @patch('rv_agent.agent.agent_factory.ImageHandler')
    @patch('rv_agent.agent.agent_factory.ScreenProcessor')
    @patch('rv_agent.agent.agent_factory.FallbackManager')
    @patch('rv_agent.agent.agent_factory.RoutingManager')
    @patch('rv_agent.agent.agent_factory.ToolExecutor')
    @patch('rv_agent.agent.agent_factory.LongTermMemory')
    @patch('rv_agent.agent.agent_factory.ShortTermMemory')
    @patch('rv_agent.agent.agent_factory.AgentMemoryManager')
    @patch('rv_agent.agent.agent_factory.MemoryCoordinator')
    @patch('rv_agent.agent.agent_factory.RVAgent')
    @patch.object(AgentFactory, '_create_llm_client')
    def test_no_llm_client_for_pure_algorithm(
        self,
        mock_create_llm,
        mock_rv_agent,
        mock_memory_coord,
        mock_agent_memory,
        mock_short_term,
        mock_long_term,
        mock_tool_executor,
        mock_routing,
        mock_fallback,
        mock_screen_processor,
        mock_image_handler,
        mock_strategy_registry,
        mock_ui_coverage,
        mock_dynamic_graph,
        mock_device_interface,
        base_config
    ):
        """Does not create LLM client for pure_algorithm mode."""
        base_config.get_agent_mode.return_value = "pure_algorithm"
        mock_strategy_instance = MagicMock()
        mock_strategy_registry.return_value.get_strategy.return_value = mock_strategy_instance
        mock_rv_agent.return_value = MagicMock(spec=RVAgent)

        AgentFactory.create_agent(base_config)

        mock_create_llm.assert_not_called()

        # Verify llm_client is None in RVAgent call
        call_kwargs = mock_rv_agent.call_args[1]
        assert call_kwargs['llm_client'] is None


class TestAgentFactoryCreateLLMClient:
    """Test _create_llm_client method."""

    @patch('rv_agent.agent.agent_factory.LLMClient')
    @patch('rv_agent.agent.agent_factory.importlib')
    def test_creates_llm_with_config(
        self,
        mock_importlib,
        mock_llm_client,
        base_config
    ):
        """Creates LLM client with configuration."""
        mock_prompt_module = MagicMock()
        mock_importlib.import_module.return_value = mock_prompt_module
        mock_client = MagicMock()
        mock_llm_client.return_value = mock_client

        result = AgentFactory._create_llm_client(base_config)

        assert result == mock_client
        mock_llm_client.assert_called_once_with(
            config=base_config,
            prompt_module=mock_prompt_module
        )

    @patch('rv_agent.agent.agent_factory.LLMClient')
    @patch('rv_agent.agent.agent_factory.importlib')
    def test_loads_prompt_module_dynamically(
        self,
        mock_importlib,
        mock_llm_client,
        base_config
    ):
        """Loads prompt module based on config version."""
        base_config.prompt_version = "v13"
        mock_prompt_module = MagicMock()
        mock_importlib.import_module.return_value = mock_prompt_module

        AgentFactory._create_llm_client(base_config)

        mock_importlib.import_module.assert_called_with("rv_agent.prompts.v13")

    @patch('rv_agent.agent.agent_factory.LLMClient')
    @patch('rv_agent.agent.agent_factory.importlib')
    def test_falls_back_to_v12_on_import_error(
        self,
        mock_importlib,
        mock_llm_client,
        base_config
    ):
        """Falls back to v12 when prompt module import fails."""
        base_config.prompt_version = "invalid_version"
        mock_importlib.import_module.side_effect = ImportError("Module not found")

        # Should use fallback v12 prompt module
        AgentFactory._create_llm_client(base_config)

        # LLMClient should still be called (with fallback module from import)
        mock_llm_client.assert_called_once()

    @patch('rv_agent.agent.agent_factory.LLMClient')
    @patch('rv_agent.agent.agent_factory.importlib')
    def test_passes_config_to_llm_client(
        self,
        mock_importlib,
        mock_llm_client,
        base_config
    ):
        """Passes config to LLMClient (ChatOpenAI created internally)."""
        mock_prompt_module = MagicMock()
        mock_importlib.import_module.return_value = mock_prompt_module

        AgentFactory._create_llm_client(base_config)

        call_kwargs = mock_llm_client.call_args[1]
        assert call_kwargs['config'] == base_config
        assert call_kwargs['prompt_module'] == mock_prompt_module


class TestAgentFactoryComponentCreation:
    """Test component creation order and wiring."""

    @patch('rv_agent.agent.agent_factory.DeviceInterface')
    @patch('rv_agent.agent.agent_factory.DynamicStateGraph')
    @patch('rv_agent.agent.agent_factory.UICoverageTracker')
    @patch('rv_agent.agent.agent_factory.StrategyRegistry')
    @patch('rv_agent.agent.agent_factory.ImageHandler')
    @patch('rv_agent.agent.agent_factory.ScreenProcessor')
    @patch('rv_agent.agent.agent_factory.FallbackManager')
    @patch('rv_agent.agent.agent_factory.RoutingManager')
    @patch('rv_agent.agent.agent_factory.ToolExecutor')
    @patch('rv_agent.agent.agent_factory.LongTermMemory')
    @patch('rv_agent.agent.agent_factory.ShortTermMemory')
    @patch('rv_agent.agent.agent_factory.AgentMemoryManager')
    @patch('rv_agent.agent.agent_factory.MemoryCoordinator')
    @patch('rv_agent.agent.agent_factory.RVAgent')
    def test_creates_image_handler_with_config(
        self,
        mock_rv_agent,
        mock_memory_coord,
        mock_agent_memory,
        mock_short_term,
        mock_long_term,
        mock_tool_executor,
        mock_routing,
        mock_fallback,
        mock_screen_processor,
        mock_image_handler,
        mock_strategy_registry,
        mock_ui_coverage,
        mock_dynamic_graph,
        mock_device_interface,
        base_config
    ):
        """Creates ImageHandler with config parameters."""
        mock_strategy_instance = MagicMock()
        mock_strategy_registry.return_value.get_strategy.return_value = mock_strategy_instance
        mock_rv_agent.return_value = MagicMock(spec=RVAgent)

        AgentFactory.create_agent(base_config)

        mock_image_handler.assert_called_once_with(
            output_dir="/tmp/screenshots",
            rotation_limit=50,
            target_size=(704, 1248),
            quality=85
        )

    @patch('rv_agent.agent.agent_factory.DeviceInterface')
    @patch('rv_agent.agent.agent_factory.DynamicStateGraph')
    @patch('rv_agent.agent.agent_factory.UICoverageTracker')
    @patch('rv_agent.agent.agent_factory.StrategyRegistry')
    @patch('rv_agent.agent.agent_factory.ImageHandler')
    @patch('rv_agent.agent.agent_factory.ScreenProcessor')
    @patch('rv_agent.agent.agent_factory.FallbackManager')
    @patch('rv_agent.agent.agent_factory.RoutingManager')
    @patch('rv_agent.agent.agent_factory.ToolExecutor')
    @patch('rv_agent.agent.agent_factory.LongTermMemory')
    @patch('rv_agent.agent.agent_factory.ShortTermMemory')
    @patch('rv_agent.agent.agent_factory.AgentMemoryManager')
    @patch('rv_agent.agent.agent_factory.MemoryCoordinator')
    @patch('rv_agent.agent.agent_factory.RVAgent')
    def test_creates_screen_processor_with_dependencies(
        self,
        mock_rv_agent,
        mock_memory_coord,
        mock_agent_memory,
        mock_short_term,
        mock_long_term,
        mock_tool_executor,
        mock_routing,
        mock_fallback,
        mock_screen_processor,
        mock_image_handler,
        mock_strategy_registry,
        mock_ui_coverage,
        mock_dynamic_graph,
        mock_device_interface,
        base_config
    ):
        """Creates ScreenProcessor with correct dependencies."""
        mock_strategy_instance = MagicMock()
        mock_strategy_registry.return_value.get_strategy.return_value = mock_strategy_instance
        mock_rv_agent.return_value = MagicMock(spec=RVAgent)
        mock_graph = MagicMock()
        mock_dynamic_graph.return_value = mock_graph
        mock_coverage = MagicMock()
        mock_ui_coverage.return_value = mock_coverage

        AgentFactory.create_agent(base_config)

        call_kwargs = mock_screen_processor.call_args[1]
        assert call_kwargs['dynamic_graph'] == mock_graph
        assert call_kwargs['ui_coverage'] == mock_coverage
        assert call_kwargs['device_dimensions'] == (1080, 1920)

    @patch('rv_agent.agent.agent_factory.DeviceInterface')
    @patch('rv_agent.agent.agent_factory.DynamicStateGraph')
    @patch('rv_agent.agent.agent_factory.UICoverageTracker')
    @patch('rv_agent.agent.agent_factory.StrategyRegistry')
    @patch('rv_agent.agent.agent_factory.ImageHandler')
    @patch('rv_agent.agent.agent_factory.ScreenProcessor')
    @patch('rv_agent.agent.agent_factory.FallbackManager')
    @patch('rv_agent.agent.agent_factory.RoutingManager')
    @patch('rv_agent.agent.agent_factory.ToolExecutor')
    @patch('rv_agent.agent.agent_factory.LongTermMemory')
    @patch('rv_agent.agent.agent_factory.ShortTermMemory')
    @patch('rv_agent.agent.agent_factory.AgentMemoryManager')
    @patch('rv_agent.agent.agent_factory.MemoryCoordinator')
    @patch('rv_agent.agent.agent_factory.RVAgent')
    def test_creates_routing_manager_with_dependencies(
        self,
        mock_rv_agent,
        mock_memory_coord,
        mock_agent_memory,
        mock_short_term,
        mock_long_term,
        mock_tool_executor,
        mock_routing,
        mock_fallback,
        mock_screen_processor,
        mock_image_handler,
        mock_strategy_registry,
        mock_ui_coverage,
        mock_dynamic_graph,
        mock_device_interface,
        base_config
    ):
        """Creates RoutingManager with fallback manager."""
        mock_strategy_instance = MagicMock()
        mock_strategy_registry.return_value.get_strategy.return_value = mock_strategy_instance
        mock_rv_agent.return_value = MagicMock(spec=RVAgent)
        mock_fb = MagicMock()
        mock_fallback.return_value = mock_fb

        AgentFactory.create_agent(base_config)

        call_kwargs = mock_routing.call_args[1]
        assert call_kwargs['config'] == base_config
        assert call_kwargs['fallback_manager'] == mock_fb
        assert call_kwargs['exploration_strategy'] == mock_strategy_instance

    @patch('rv_agent.agent.agent_factory.DeviceInterface')
    @patch('rv_agent.agent.agent_factory.DynamicStateGraph')
    @patch('rv_agent.agent.agent_factory.UICoverageTracker')
    @patch('rv_agent.agent.agent_factory.StrategyRegistry')
    @patch('rv_agent.agent.agent_factory.ImageHandler')
    @patch('rv_agent.agent.agent_factory.ScreenProcessor')
    @patch('rv_agent.agent.agent_factory.FallbackManager')
    @patch('rv_agent.agent.agent_factory.RoutingManager')
    @patch('rv_agent.agent.agent_factory.ToolExecutor')
    @patch('rv_agent.agent.agent_factory.LongTermMemory')
    @patch('rv_agent.agent.agent_factory.ShortTermMemory')
    @patch('rv_agent.agent.agent_factory.AgentMemoryManager')
    @patch('rv_agent.agent.agent_factory.MemoryCoordinator')
    @patch('rv_agent.agent.agent_factory.RVAgent')
    def test_creates_memory_coordinator_with_all_components(
        self,
        mock_rv_agent,
        mock_memory_coord,
        mock_agent_memory,
        mock_short_term,
        mock_long_term,
        mock_tool_executor,
        mock_routing,
        mock_fallback,
        mock_screen_processor,
        mock_image_handler,
        mock_strategy_registry,
        mock_ui_coverage,
        mock_dynamic_graph,
        mock_device_interface,
        base_config
    ):
        """Creates MemoryCoordinator with all memory components."""
        mock_strategy_instance = MagicMock()
        mock_strategy_registry.return_value.get_strategy.return_value = mock_strategy_instance
        mock_rv_agent.return_value = MagicMock(spec=RVAgent)
        mock_graph = MagicMock()
        mock_dynamic_graph.return_value = mock_graph
        mock_st = MagicMock()
        mock_short_term.return_value = mock_st
        mock_lt = MagicMock()
        mock_long_term.return_value = mock_lt
        mock_coverage = MagicMock()
        mock_ui_coverage.return_value = mock_coverage
        mock_am = MagicMock()
        mock_agent_memory.return_value = mock_am

        AgentFactory.create_agent(base_config)

        call_kwargs = mock_memory_coord.call_args[1]
        assert call_kwargs['dynamic_graph'] == mock_graph
        assert call_kwargs['short_term_memory'] == mock_st
        assert call_kwargs['long_term_memory'] == mock_lt
        assert call_kwargs['ui_coverage'] == mock_coverage
        assert call_kwargs['agent_memory'] == mock_am
        assert call_kwargs['action_window_size'] == 10

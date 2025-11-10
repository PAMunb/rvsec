"""
Agent factory for simplified RVAgent instantiation.

Provides centralized component creation with proper dependency injection
to simplify agent instantiation and testing.
"""

import logging
from typing import Optional

from langchain_ollama import ChatOllama

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.prompts import v12 as current_prompt
from rv_agent.core.rv_agent import RVAgent
from rv_agent.core.device_interface import DeviceInterface
from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_agent.strategies.dfs_strategy import DFSStrategy
from rv_agent.strategies.strategy_registry import StrategyRegistry
from rv_agent.vision.image_handler import ImageHandler
from rv_agent.ui.screen_processor import ScreenProcessor
from rv_agent.llm.llm_client import LLMClient
from rv_agent.routing.routing_manager import RoutingManager
from rv_agent.routing.loop_detector import LoopDetector
from rv_agent.routing.fallback_manager import FallbackManager
from rv_agent.execution.tool_executor import ToolExecutor
from rv_agent.memory.memory_coordinator import MemoryCoordinator
from rv_agent.memory.agent_memory import AgentMemoryManager
from rv_agent.memory.long_term import LongTermMemory
from rv_agent.memory.short_term import ShortTermMemory
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_android_core.domain.static import StaticAnalysisData

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Factory for creating fully configured RVAgent instances.

    ### Architectural Decisions:
    - Centralizes component instantiation logic
    - Handles dependency injection wiring
    - Provides simple interface for agent creation
    - Supports optional device injection for testing
    - Creates components in correct dependency order
    - Validates configuration before instantiation

    ### Role in the System:
    - Simplifies RVAgent creation for users
    - Provides consistent component configuration
    - Enables easy testing with mock components
    - Reduces boilerplate in agent usage code
    - Centralizes component dependency management

    ### Integration Points:
    - Used by tests and application code to create agents
    - Accepts RVAgentConfig for configuration
    - Creates all required component instances
    - Returns fully configured RVAgent
    - Supports optional device and static data injection
    """

    @staticmethod
    def create_agent(
        config: RVAgentConfig,
        static_data: Optional[StaticAnalysisData] = None,
        device: Optional[DeviceInterface] = None
    ) -> RVAgent:
        """
        Create fully configured RVAgent instance.

        Args:
            config: Agent configuration
            static_data: Optional static analysis data
            device: Optional device interface (for testing)

        Returns:
            Configured RVAgent instance

        Raises:
            ValueError: If configuration is invalid
        """
        logger.info("AgentFactory: Creating RVAgent instance")

        # Validate configuration
        mode = config.get_agent_mode()
        if mode not in ["pure_algorithm", "llm_only", "multimode"]:
            raise ValueError(f"Invalid mode: {mode}")

        logger.info(f"Mode: {mode}, Strategy: {config.strategy}")

        # Create device interface
        if device is None:
            device = DeviceInterface(device_id=config.device_id)
            logger.info(f"Created DeviceInterface: {config.device_id}")
        else:
            logger.info("Using injected device interface")

        # Create dynamic state graph
        dynamic_graph = DynamicStateGraph()
        logger.info("Created DynamicStateGraph")

        # Create exploration strategy
        strategy_registry = StrategyRegistry()
        exploration_strategy = strategy_registry.get_strategy(
            name=config.strategy,
            graph=dynamic_graph,
            static_data=static_data,
            coordinate_converter=None  # Will use coordinate_utils directly
        )
        logger.info(f"Created ExplorationStrategy: {config.strategy}")

        # Create image handler
        image_handler = ImageHandler(
            output_dir=config.screenshot_dir,
            rotation_limit=config.screenshot_rotation_limit,
            target_size=config.optimized_dimensions,
            quality=85
        )
        logger.info(f"Created ImageHandler: {config.screenshot_dir}")

        # Create screen processor
        screen_processor = ScreenProcessor(
            device=device,
            dynamic_graph=dynamic_graph,
            static_data=static_data,
            device_dimensions=config.device_dimensions,
            optimized_dimensions=config.optimized_dimensions,
            max_external_attempts=config.max_external_attempts
        )
        logger.info("Created ScreenProcessor")

        # Create LLM client (if needed)
        llm_client = None
        if mode in ["llm_only", "multimode"]:
            llm_client = AgentFactory._create_llm_client(config)
            logger.info("Created LLMClient")

        # Create loop detector
        loop_detector = LoopDetector(config=config)
        logger.info("Created LoopDetector")

        # Create fallback manager
        fallback_manager = FallbackManager(strategy_registry=strategy_registry)
        logger.info("Created FallbackManager")

        # Create routing manager
        routing_manager = RoutingManager(
            config=config,
            loop_detector=loop_detector,
            fallback_manager=fallback_manager,
            exploration_strategy=exploration_strategy
        )
        logger.info("Created RoutingManager")

        # Create tool executor
        tool_executor = ToolExecutor(
            device=device,
            image_handler=image_handler
        )
        logger.info("Created ToolExecutor")

        # Create memory components
        long_term_memory = LongTermMemory(static_data=static_data)
        short_term_memory = ShortTermMemory()
        ui_coverage = UICoverageTracker()
        agent_memory = AgentMemoryManager(
            max_action_history=5,
            max_navigation_path=5
        )
        logger.info("Created memory components")

        # Create memory coordinator
        memory_coordinator = MemoryCoordinator(
            dynamic_graph=dynamic_graph,
            short_term_memory=short_term_memory,
            long_term_memory=long_term_memory,
            ui_coverage=ui_coverage,
            agent_memory=agent_memory,
            action_window_size=10
        )
        logger.info("Created MemoryCoordinator")

        # Create RVAgent
        agent = RVAgent(
            config=config,
            device=device,
            dynamic_graph=dynamic_graph,
            exploration_strategy=exploration_strategy,
            image_handler=image_handler,
            screen_processor=screen_processor,
            llm_client=llm_client,
            routing_manager=routing_manager,
            tool_executor=tool_executor,
            memory_coordinator=memory_coordinator,
            static_data=static_data
        )

        logger.info("AgentFactory: RVAgent created successfully")
        return agent

    @staticmethod
    def _create_llm_client(config: RVAgentConfig) -> LLMClient:
        """
        Create LLM client with tool calling support.

        Args:
            config: Agent configuration

        Returns:
            Configured LLMClient instance
        """
        # Get LLM configuration
        llm_config = config.get_langchain_config()

        # Create base LLM
        llm_base = ChatOllama(
            model=llm_config['model'],
            temperature=llm_config['temperature'],
            top_p=llm_config.get('top_p', 0.8),
            top_k=llm_config.get('top_k', 50),
            base_url=llm_config.get('base_url', 'http://localhost:11434'),
            timeout=60.0,
            request_timeout=60.0
        )

        # Import and create Android tools
        from rv_agent.llm.tools.android_tools import (
            create_android_tools,
            set_device_interface,
            set_coordinate_converter
        )

        tools = create_android_tools()
        logger.info(f"Created {len(tools)} Android tools")

        # Bind tools to LLM
        llm_with_tools = llm_base.bind_tools(tools)

        # Create LLM client
        return LLMClient(
            config=config,
            llm=llm_with_tools,
            prompt_module=current_prompt
        )

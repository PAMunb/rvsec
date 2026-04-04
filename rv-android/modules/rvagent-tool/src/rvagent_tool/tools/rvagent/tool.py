"""
RVAgent Tool for rv-platform integration.

Wraps rv-agent as an AbstractTool for execution within the rv-platform
task execution framework.
"""

from typing import Any, Dict

from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rvagent_tool.tools.rvagent.config import build_agent_config_dict, get_static_data

# Tool constants
RVAGENT_TOOL_NAME = "rvagent"
RVAGENT_DESCRIPTION = "LLM-driven Android testing with multimodal exploration"


class RVAgentTool(AbstractTool):
    """
    RV-Agent tool for rv-platform integration.

    Wraps rv-agent AgentFactory and RVAgent for execution within
    the rv-platform task execution framework. Supports three
    exploration modes: pure_algorithm, llm_only, multimode.

    ### Architectural Role:
    - Implements AbstractTool interface for platform integration
    - Delegates to rv-agent AgentFactory for agent creation
    - Maps platform Task/ToolConfig to RVAgentConfig
    - Supports static analysis data from platform context

    ### Integration Points:
    - Registered via rv-platform on import
    - Uses rv-android-core error handling and logging
    - Connects with rv-agent for LLM-driven testing
    - Receives static_data from platform StaticAnalysisComponent

    ### Tool Execution Flow:
    1. configure() stores variant configuration
    2. execute_tool_specific_logic() builds RVAgentConfig from task/app
    3. AgentFactory creates configured RVAgent with static data
    4. RVAgent executes exploration until timeout
    """

    # process_pattern is used by kill_related_processes() to terminate
    # tool-related processes on the device after execution.
    # rv-agent doesn't spawn persistent processes on the device
    # (it uses UIAutomator2 which manages its own cleanup).
    TOOL_SPEC = ToolSpec(
        name=RVAGENT_TOOL_NAME,
        description=RVAGENT_DESCRIPTION,
        url="https://github.com/PAMunb/rvsec",
        version="1.0.0",
        process_pattern="",
    )

    def __init__(self):
        """
        Initialize RVAgent tool.

        Sets up logging and prepares for configuration-based setup.
        """
        tool_spec = self.get_tool_spec()
        super().__init__(
            name=tool_spec.name,
            description=tool_spec.description,
            process_pattern=tool_spec.process_pattern,
        )

        # Initialize component logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvagent_tool.tools.rvagent", {CONTEXT_COMPONENT: "RVAgentTool"}
        )

        # Configuration stored from configure() method
        self._tool_config: Dict[str, Any] = {}

        self.logger.info("RVAgent tool initialized")

    @classmethod
    def get_tool_spec(cls) -> ToolSpec:
        """
        Get tool specification for registration.

        Returns:
            ToolSpec instance with tool metadata
        """
        return cls.TOOL_SPEC

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get available RVAgent variants.

        Variants map to rv-agent execution modes with predefined
        configurations for different testing scenarios.

        NOTE: timeout is ALWAYS controlled by Task.config, not by variants.
        The platform manages execution timeout uniformly across all tools.

        Returns:
            Dictionary mapping variant names to configuration parameters
        """
        return {
            "default": {
                "agent_mode": "multimode",
                "llm_probability": 0.7,
                "strategy": "rvagent",
            },
            "multimode": {
                "agent_mode": "multimode",
                "llm_probability": 0.7,
                "strategy": "rvagent",
            },
            "pure_algorithm": {"agent_mode": "pure_algorithm", "strategy": "rvagent"},
            "llm_only": {"agent_mode": "llm_only", "strategy": "rvagent"},
            "thorough": {
                "agent_mode": "multimode",
                "llm_probability": 0.8,
                "strategy": "rvagent",
                "plateau_window": 15,
            },
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure tool with resolved variant parameters.

        Called by ToolFactory after resolving variant configuration.
        Stores configuration for use in execute_tool_specific_logic.

        Args:
            config: Configuration dictionary with tool-specific parameters
        """
        self._tool_config = config.copy() if config else {}
        self.logger.info(
            f"RVAgent tool configured: mode={self._tool_config.get('agent_mode', 'default')}"
        )

    @ErrorHandler.handle_errors(
        component="RVAgentTool", phase="execute_tool_specific_logic", reraise=True
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute RV-Agent testing.

        Creates RVAgentConfig from task context, uses AgentFactory
        to create agent with static data, and runs exploration.

        Args:
            task: Task configuration with device, timeout, static data
            app: Application under test
        """
        # Import here to avoid circular dependencies
        from rv_agent.agent.agent_factory import AgentFactory
        from rv_agent.config.agent_config import RVAgentConfig

        self.logger.info(f"Executing RVAgent for {app.package_name}")

        # Build agent configuration from task context
        config_dict = build_agent_config_dict(task, app, self._tool_config)
        self.logger.debug(f"Agent config: {config_dict}")

        # Create RVAgentConfig
        agent_config = RVAgentConfig(**config_dict)

        # Validate configuration
        is_valid, error = agent_config.validate()
        if not is_valid:
            raise ValueError(f"Invalid agent configuration: {error}")

        # Get static analysis data from task (loaded by platform)
        static_data = get_static_data(task)
        if static_data:
            self.logger.info("Using static analysis data from platform")
        else:
            self.logger.info("No static analysis data available")

        # Create agent via factory
        self.logger.info("Creating RVAgent via AgentFactory")
        agent = AgentFactory.create_agent(config=agent_config, static_data=static_data)

        # Run agent exploration
        self.logger.info(
            f"Starting RVAgent exploration (timeout={agent_config.timeout}s)"
        )
        results = agent.run()

        # Log results summary
        iterations = results.get("iterations", 0)
        unique_states = results.get("unique_states", 0)
        self.logger.info(
            f"RVAgent completed: {iterations} iterations, {unique_states} states"
        )

    def get_tool_info(self) -> dict:
        """
        Get comprehensive tool information.

        Returns:
            Dictionary with tool information and current configuration
        """
        info = super().get_tool_info()
        info.update(
            {
                "tool_spec": (
                    self.TOOL_SPEC.to_dict()
                    if hasattr(self.TOOL_SPEC, "to_dict")
                    else str(self.TOOL_SPEC)
                ),
                "current_config": self._tool_config,
                "version": self.TOOL_SPEC.version,
                "url": self.TOOL_SPEC.url,
            }
        )
        return info

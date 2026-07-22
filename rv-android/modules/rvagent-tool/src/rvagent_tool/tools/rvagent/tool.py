"""
RVAgent Tool for rv-platform integration.

Wrap rv-agent as an AbstractTool for execution within the rv-platform
task execution framework. Maps platform Task/App context to RVAgentConfig
and delegates to AgentFactory for LLM-driven Android UI exploration.
"""

from typing import Any, Dict

from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rvagent_tool.tools.rvagent.config import (
    RV_STEERING_OFF,
    build_agent_config_dict,
    get_static_data,
)

# Tool constants
RVAGENT_TOOL_NAME = "rvagent"
RVAGENT_DESCRIPTION = "LLM-driven Android testing with multimodal exploration"


class RVAgentTool(AbstractTool):
    """
    RV-Agent tool for rv-platform integration.

    Wrap rv-agent AgentFactory and RVAgent for execution within
    the rv-platform task execution framework. Supports three
    exploration modes: pure_algorithm, llm_only, multimode.

    ### Role in the System:
    - Implements AbstractTool interface so rv-platform can dispatch
      RV-Agent as a first-class exploration tool
    - Delegates to rv-agent AgentFactory for agent creation
    - Maps platform Task/ToolConfig to RVAgentConfig parameters

    ### Architectural Decisions:
    - Lazy import of rv-agent modules in execute_tool_specific_logic()
      to avoid circular dependencies at registration time
    - Timeout is controlled by Task.config, not by tool variants,
      keeping execution timeout uniform across all tools
    - Static analysis data is injected from the platform context
      rather than loaded independently

    ### Key Features:
    - Five named variants: default, multimode, pure_algorithm, llm_only, thorough
    - Configuration mapping from platform Task to RVAgentConfig via config module
    - Static analysis data passthrough from platform StaticAnalysisComponent

    ### Integration Points:
    - Input: Task (device_id, timeout, static_data), App (package_name)
    - Output: exploration results logged; coverage via logcat
    - Upstream: rv-platform registers tool on import; ToolFactory resolves variants
    - Downstream: rv-agent AgentFactory creates and runs the configured agent
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

        Set up logging and prepare for configuration-based setup via
        the AbstractTool interface.

        State:
            self.logger: Context-aware logger tagged with component "RVAgentTool".
            self._tool_config: Stores resolved variant config from configure().
                Empty until configure() is called.
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
        Get available RVAgent variants (frozen experimental arms).

        A variant is an experimental arm, and arms MUST NOT inherit defaults
        (INV-RVA-01): every frozen variant sets ALL arm-defining keys explicitly.
        This is enforced by spreading ``RV_STEERING_OFF`` — the pinned copy of the
        agent kill-switch registry (every arm-defining key at its off/0 value) —
        into every variant, so no arm-defining behavior can fall back to an
        ``RVAgentConfig`` default. The guard pytest fails if any variant omits a
        key or if ``RV_STEERING_OFF`` drifts from the agent registry.

        Two arm families (FR20):
        - Steering family: ``pure_algorithm`` sets ``pure_mode=True`` (INV-RVA-03),
          the kill-switch that additionally forces every registered flag off at
          assembly time, so the pure arm is auditably free of MOP steering.
        - LLM family (``multimode``/``llm_only``, plus the ``default`` alias and the
          ``thorough`` tuning): every gh77 steering flag is explicitly off
          (INV-RVA-04) so LLM latency never contaminates a steering measurement;
          a MOP+LLM combination would be frozen only under its own named arm.

        L2 pattern: defaults live here in the variant dicts; ``configure()`` reads
        the merged dict; no ``os.environ`` access at the tool layer. Timeout is
        ALWAYS controlled by ``Task.config``, never by a variant.

        Returns:
            Dictionary mapping variant names to configuration parameters
        """
        # Every arm-defining key at its off value, spread into each variant so the
        # explicitness guard (INV-RVA-01) holds by construction.
        steering_off = dict(RV_STEERING_OFF)
        return {
            "default": {
                **steering_off,
                "pure_mode": False,
                "agent_mode": "multimode",
                "llm_probability": 0.7,
                "strategy": "rvagent",
            },
            "multimode": {
                **steering_off,
                "pure_mode": False,
                "agent_mode": "multimode",
                "llm_probability": 0.7,
                "strategy": "rvagent",
            },
            "pure_algorithm": {
                **steering_off,
                "pure_mode": True,
                "agent_mode": "pure_algorithm",
                "strategy": "rvagent",
            },
            # Steering arm frozen from the 7.7 calibration smoke (cryptoapp,
            # 2026-07-13): the MOP frontier boost on top of the generic WTG
            # frontier. Algorithmic (no LLM), all other steering off. The two
            # weights (mop_frontier_weight over wtg_guided_score) interact
            # additively — on an unvisited MOP-reaching activity both scorers
            # fire (200 + 150 = 350) vs 150 for a generic unvisited activity, the
            # intended MOP-over-generic frontier separation. See
            # docs/20260713_calibracao_frontier_gh77.md.
            "mop_frontier": {
                **steering_off,
                "pure_mode": False,
                "mop_frontier_weight": 200.0,
                "wtg_guided_score": 150.0,
                "agent_mode": "pure_algorithm",
                "strategy": "rvagent",
            },
            "llm_only": {
                **steering_off,
                "pure_mode": False,
                "agent_mode": "llm_only",
                "strategy": "rvagent",
            },
            "thorough": {
                **steering_off,
                "pure_mode": False,
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
        from rv_agent.services.transition_manager import validate_static_data

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

        # Static-data fail-fast at the plugin boundary (INV-RVA static-data
        # fail-fast; mirrors agent-side INV-AGT-49). A present-but-invalid
        # StaticAnalysisData aborts the task here — BEFORE any device/emulator
        # time is spent — with an error naming the offending field. Absent static
        # data is a supported degraded mode (WTG guidance disabled) and passes
        # through. This guard runs ahead of AgentFactory (which creates the
        # DeviceInterface), so a misconfigured pre-processing pipeline never
        # reaches the emulator.
        validate_static_data(static_data)
        if static_data:
            self.logger.info("Using static analysis data from platform")
        else:
            self.logger.info("No static analysis data available")

        # Create agent via factory
        self.logger.info("Creating RVAgent via AgentFactory")
        agent = AgentFactory.create_agent(config=agent_config, static_data=static_data)

        # Teardown ALWAYS runs (INV-RVA-05): the agent session is stopped and the
        # device client released on success, on timeout, and on any exception, so
        # a crashed exploration never leaves the app running on the shared
        # emulator. The trace/metric artifacts are flushed by RVAgent.run() itself
        # (its exploration loop swallows per-iteration errors and always reaches
        # the flush); this finally covers the device-side session.
        try:
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
        finally:
            self._teardown_agent(agent, app)

    def _teardown_agent(self, agent: Any, app: App) -> None:
        """
        Release the device session for a finished/failed RVAgent run (INV-RVA-05).

        Stops the app under test on the platform-managed emulator so no session
        outlives the task. Idempotent and defensive: it never raises (teardown
        must not mask the original exception in the caller's ``finally``), and it
        tolerates a partially built agent whose device is absent.

        Args:
            agent: The RVAgent instance (or None if creation failed before this
                point). Its ``device`` is a UIAutomator2 DeviceInterface.
            app: Application under test (supplies the package to stop).
        """
        device = getattr(agent, "device", None)
        if device is None:
            return
        try:
            device.stop_app(app.package_name)
            self.logger.info(f"RVAgent teardown: stopped {app.package_name}")
        except Exception as exc:  # teardown must never mask the caller's error
            self.logger.warning(f"RVAgent teardown: stop_app failed: {exc}")

    def get_tool_info(self) -> dict:
        """
        Get comprehensive tool information including current configuration.

        Returns:
            Dictionary with tool metadata, spec, version, URL, and active
            variant configuration from configure()
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

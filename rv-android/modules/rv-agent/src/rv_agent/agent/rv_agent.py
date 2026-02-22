"""
Autonomous Android testing agent with modular architecture.

Implements an LLM-guided or algorithm-based agent that explores Android
applications using a modular component-based design with dependency injection.

### Architectural Decisions:
- **Component-Based**: Specialized components handle distinct concerns
- **Dependency Injection**: All dependencies passed via constructor
- **Stateless LLM Context**: Fresh messages built from summaries each iteration
- **Multi-Mode Operation**: pure_algorithm, llm_only, multimode execution
- **Pluggable Strategies**: Swappable exploration algorithms (DFS, BFS, etc.)
- **Centralized Routing**: Decision routing between LLM and algorithm paths

### Key Features:
- **RoutingManager**: Decision routing between exploration modes
- **ScreenProcessor**: UI parsing and element formatting
- **LLMClient**: LLM interaction and tool call handling
- **ToolExecutor**: Action execution on device
- **MemoryCoordinator**: Memory system coordination
- **ExplorationStrategy**: Algorithmic exploration (DFS, BFS)
- **ImageHandler**: Screenshot capture and optimization
"""

import logging
import time
from typing import Any, Dict, Optional

from langgraph.graph import END, StateGraph
from rv_android_core.domain.static import StaticAnalysisData

from rv_agent import tracking as track
from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.agent.nodes import (
    algorithm_node,
    capture_screenshot_node,
    decision_router_node,
    execute_node,
    learn_node,
    llm_generate_node,
    parse_ui_node,
    validate_action_node,
)
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.domain.action import ActionNormalizer
from rv_agent.domain.state import AgentState
from rv_agent.execution.tool_executor import ToolExecutor
from rv_agent.llm.llm_client import LLMClient
from rv_agent.memory.memory_coordinator import MemoryCoordinator
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.routing.routing_manager import RoutingManager
from rv_agent.routing.stuck_recovery import StuckRecovery
from rv_agent.services.navigation_guidance import NavigationGuidance
from rv_agent.services.screen_analyzer import ScreenProcessor
from rv_agent.services.vision_service import ImageHandler
from rv_agent.strategies.base_strategy import ExplorationStrategy

logger = logging.getLogger(__name__)

# Maximum total errors (never resets) before the agent gives up.
# When reached, the agent has clearly lost the ability to interact with
# the app and should not waste the remaining timeout in error loops.
MAX_TOTAL_ERRORS = 30


class RVAgent:
    """
    Modular autonomous Android exploration agent.

    ### Architectural Decisions:
    - Uses dependency injection for all components
    - Delegates node logic to specialized components
    - Maintains stateless LLM context (~2500 tokens/iteration)
    - Supports three execution modes via RoutingManager
    - Uses LangGraph for workflow orchestration
    - Keeps minimal orchestration logic in nodes

    ### Role in the System:
    - Orchestrates exploration workflow via LangGraph
    - Coordinates component interactions through nodes
    - Manages external execution loop with timeout
    - Provides entry point for Android app exploration
    - Reports exploration metrics and results

    ### Integration Points:
    - Accepts configuration via RVAgentConfig
    - Uses DeviceInterface for device interactions
    - Delegates to RoutingManager for path decisions
    - Uses ScreenProcessor for UI parsing
    - Uses LLMClient for LLM interactions
    - Uses ToolExecutor for action execution
    - Uses MemoryCoordinator for memory updates
    - Reports results to caller
    """

    def __init__(
        self,
        config: RVAgentConfig,
        device: DeviceInterface,
        dynamic_graph: DynamicStateGraph,
        exploration_strategy: ExplorationStrategy,
        image_handler: ImageHandler,
        screen_processor: ScreenProcessor,
        llm_client: Optional[LLMClient],
        routing_manager: RoutingManager,
        tool_executor: ToolExecutor,
        memory_coordinator: MemoryCoordinator,
        navigation_guidance: Optional[NavigationGuidance] = None,
        action_normalizer: Optional[ActionNormalizer] = None,
        static_data: Optional[StaticAnalysisData] = None,
        ui_coverage: Optional["UICoverageTracker"] = None,
    ):
        """
        Initialize RVAgent with injected dependencies.

        Args:
            config: Agent configuration
            device: Device interface for Android interactions
            dynamic_graph: State graph for exploration tracking
            exploration_strategy: Algorithm strategy (DFS, BFS, etc.)
            image_handler: Screenshot capture and optimization
            screen_processor: UI parsing and formatting
            llm_client: LLM client (required for llm_only/multimode)
            routing_manager: Decision routing manager
            tool_executor: Action execution manager
            memory_coordinator: Memory coordination manager
            navigation_guidance: Optional navigation guidance for WTG integration
            action_normalizer: Action format normalizer for unified format
            static_data: Optional static analysis data

        State:
            self.strategy: Assigned from exploration_strategy.
            self.last_screen_hash: Track Level 1 stuck detection, initially None.
            self.stuck_screen_count: Increment when screen hash unchanged, reset on change.
            self.stuck_recovery: StuckRecovery for Level 2 stuck detection (backtrack BFS).
            self.consecutive_no_action: Track iterations without action for deadlock detection.
            self.graph: Compiled LangGraph workflow, built in __init__.
        """
        self.config = config
        self.device = device
        self.dynamic_graph = dynamic_graph
        self.strategy = exploration_strategy
        self.image_handler = image_handler
        self.screen_processor = screen_processor
        self.llm_client = llm_client
        self.routing_manager = routing_manager
        self.tool_executor = tool_executor
        self.memory_coordinator = memory_coordinator
        self.navigation_guidance = navigation_guidance
        self.action_normalizer = action_normalizer
        self.static_data = static_data
        self.ui_coverage = ui_coverage

        # Validate LLM client for modes that need it
        mode = config.get_agent_mode()
        if mode in ["llm_only", "multimode"] and llm_client is None:
            raise ValueError(f"LLM client required for mode: {mode}")

        # Level 1 stuck detection (screen unchanged)
        # Dynamic threshold based on screen complexity (number of elements)
        self.last_screen_hash = None
        self.stuck_screen_count = 0
        self.error_recovery_count = 0
        self.BASE_STUCK_THRESHOLD = 8  # Minimum threshold for simple screens
        self.STUCK_THRESHOLD_FACTOR = (
            1.5  # Multiplier: threshold = max(base, elements * factor)
        )

        # Level 2 stuck detection (persistent same state)
        # Uses Backtrack BFS to find unsaturated ancestors, then RESTART if none found
        self.stuck_recovery = StuckRecovery(max_blocks=10)

        # Screen description cache: reuse when screen_hash is unchanged
        self._cached_screen_desc = None

        # Deadlock detection (no action available)
        self.consecutive_no_action = 0
        self.NO_ACTION_THRESHOLD = 3  # Force BACK after 3 iterations without action

        logger.info("RVAgent initialized with modular architecture")
        logger.info(f"Mode: {mode}")
        logger.info(f"Strategy: {config.strategy}")
        logger.info(f"Package: {config.package_name}")

        # Build LangGraph workflow
        self.graph = self._build_agent_graph()

        logger.info("RVAgent initialization complete")

    def _build_agent_graph(self):
        """
        Build unified LangGraph workflow for all modes.

        Workflow structure:
                      start
                        ↓
                    parse_ui
                        ↓
                 decision_router
                ↙      ↓      ↘
           algorithm   llm    end
                ↓        ↓
                ↓   capture_screenshot
                ↓        ↓
                ↓   llm_generate
                ↓        ↓
                └──→ validate_action
                           ↓
                        execute
                           ↓
                         learn
                           ↓
                          END

        Notes:
        - validate_action always proceeds to execute (no fallback cycle)
        - If action is invalid or loop detected, BACK action is substituted
        - Stuck detection handled in learn_node, forces algorithm path with BACK

        Returns:
            Compiled LangGraph workflow
        """
        mode = self.config.get_agent_mode()
        logger.info(f"Building workflow (mode={mode})")

        workflow = StateGraph(AgentState)

        # Add nodes (externalized in agent/nodes/)
        workflow.add_node("parse_ui", lambda s: parse_ui_node(self, s))
        workflow.add_node("decision_router", lambda s: decision_router_node(self, s))
        workflow.add_node("algorithm_node", lambda s: algorithm_node(self, s))
        workflow.add_node(
            "capture_screenshot", lambda s: capture_screenshot_node(self, s)
        )
        workflow.add_node("llm_generate", lambda s: llm_generate_node(self, s))
        workflow.add_node("validate_action", lambda s: validate_action_node(self, s))
        workflow.add_node("execute", lambda s: execute_node(self, s))
        workflow.add_node("learn", lambda s: learn_node(self, s))

        # Entry point
        workflow.set_entry_point("parse_ui")
        workflow.add_edge("parse_ui", "decision_router")

        # Decision routing
        workflow.add_conditional_edges(
            "decision_router",
            lambda s: s.get("decision_path", "end"),
            {"llm": "capture_screenshot", "algorithm": "algorithm_node", "end": END},
        )

        # LLM path
        workflow.add_edge("capture_screenshot", "llm_generate")
        workflow.add_edge("llm_generate", "validate_action")

        # Algorithm path also goes through validation
        workflow.add_edge("algorithm_node", "validate_action")

        # Validation always goes to execute (no fallback cycle)
        workflow.add_edge("validate_action", "execute")

        # Common path
        workflow.add_edge("execute", "learn")
        workflow.add_edge("learn", END)

        logger.info("Workflow compiled successfully")
        return workflow.compile()

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics from all memory systems.

        Delegates to MemoryCoordinator's facade method to collect statistics
        from ui_coverage, short_term, long_term, and dynamic_graph.

        Returns:
            Dictionary with memory statistics from all systems
        """
        return self.memory_coordinator.get_all_statistics()

    def run(self) -> Dict[str, Any]:
        """
        Execute agent exploration with external timeout loop.

        Returns:
            Dictionary with keys:
            - "status" (str): Completion status ("completed" or "error").
            - "iterations" (int): Total exploration iterations executed.
            - "execution_time_s" (float): Wall clock execution time in seconds.
            - "unique_states" (int): Number of unique UI states discovered.
            - "total_transitions" (int): Number of state transitions recorded.
            - "llm_tokens_input" (int): Total LLM input tokens consumed.
            - "llm_tokens_output" (int): Total LLM output tokens generated.
            - "llm_time_ms" (float): Total LLM inference time in milliseconds.
            - "total_actions" (int): Total actions across all paths.
            - "llm_executed" (int): Actions generated by LLM.
            - "algorithm_chosen" (int): Actions chosen by algorithm.
            - "llm_percentage" (float): LLM action percentage.
            - "algorithm_percentage" (float): Algorithm action percentage.
            - "llm_validation_failed" (int): LLM actions that failed validation.
            - "forced_back" (int): BACK actions from stuck detection.
            - "memory_stats" (dict): Memory system statistics.
            - "ui_coverage" (dict): UI element coverage metrics.
        """
        logger.info("Starting RVAgent execution")

        start_time = time.time()
        iteration = 0

        # Launch app
        try:
            logger.info(f"Launching application: {self.config.package_name}")
            self.device.launch_app(self.config.package_name)
            time.sleep(2)
        except Exception as e:
            logger.error(f"Failed to launch app: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

        # Set up .trace file handler for RVTRACK log persistence
        trace_handler = None
        if self.config.metrics_output_dir:
            try:
                from pathlib import Path

                from rv_agent.metrics import MetricsExporter

                trace_filename = MetricsExporter.build_filename(
                    self.config.package_name,
                    self.config.agent_mode,
                    self.config.timeout,
                ).replace(".rvagent_metrics.json", ".trace")
                trace_path = Path(self.config.metrics_output_dir) / trace_filename
                trace_path.parent.mkdir(parents=True, exist_ok=True)
                trace_handler = logging.FileHandler(str(trace_path), encoding="utf-8")
                trace_handler.setLevel(logging.DEBUG)
                logging.getLogger("rv_agent").addHandler(trace_handler)
                logger.info(f"RVTRACK trace file: {trace_path}")
            except Exception as e:
                logger.warning(f"Failed to set up trace file: {e}")

        # Initialize state
        state = {
            "iteration": 0,
            "start_time": start_time,
            "timeout": self.config.timeout,
            "visited_states": [],
            "state_transitions": [],
            "previous_screen_hash": None,
            "previous_action_signature": None,
            "previous_activity": None,
            "external_navigation_count": 0,
            "recent_action_window": [],
            "llm_tokens_input": 0,
            "llm_tokens_output": 0,
            "llm_time_ms": 0.0,
            "action_history_summary": "No previous actions.",
            "exploration_summary": "Starting exploration.",
            "memory_insights": "No insights yet.",
            "navigation_path": "Starting navigation.",
            "decision_path": "algorithm",
            "decision_maker": "unknown",
            "loop_detected": False,
            "used_fallback": False,
            "force_back_action": False,  # Stuck state detection flag
            # LLM action validation fields (multimode)
            "llm_action": None,
            "has_tool_calls": False,
            "llm_reasoning": "",
            "validation_path": "",
            "ui_xml": "",
            # Error detection fields
            "force_fill_input": False,
            "error_detection_screenshot": None,
            "error_indicators": None,
        }

        # External execution loop
        consecutive_errors = 0
        max_consecutive_errors = 10
        total_errors = 0

        while True:
            try:
                elapsed = time.time() - start_time

                if elapsed >= self.config.timeout:
                    logger.info(f"🏁 Timeout reached ({elapsed:.1f}s)")
                    break

                logger.info(f"⏱️  Iteration {iteration} (elapsed: {elapsed:.1f}s)")

                state["iteration"] = iteration

                # Invoke graph for one iteration
                # Set recursion_limit to prevent infinite loops in validation routing
                result = self.graph.invoke(state, {"recursion_limit": 100})

                # Update state with results
                state.update(result)

                iteration += 1
                consecutive_errors = 0  # Reset on success
                time.sleep(0.5)

            except KeyboardInterrupt:
                logger.info("⚠️  Interrupted by user")
                break
            except Exception as e:
                consecutive_errors += 1
                total_errors += 1
                logger.error(
                    f"Iteration {iteration} error "
                    f"({consecutive_errors}/{max_consecutive_errors} consecutive, "
                    f"{total_errors}/{MAX_TOTAL_ERRORS} total): {e}"
                )

                # Total error limit: agent has lost the ability to interact
                if total_errors >= MAX_TOTAL_ERRORS:
                    logger.critical(
                        f"Total error limit reached ({MAX_TOTAL_ERRORS}), "
                        "agent cannot recover — stopping execution"
                    )
                    break

                if consecutive_errors >= max_consecutive_errors:
                    logger.error(
                        f"Too many consecutive errors ({max_consecutive_errors}), "
                        "resetting counter but continuing until timeout or total limit"
                    )
                    consecutive_errors = 0  # Reset to allow more attempts

                time.sleep(1)  # Brief pause before retry

        # Compute final metrics
        execution_time = time.time() - start_time

        # Get decision counters
        counters = self.routing_manager.get_decision_counters()

        # Collect memory statistics
        memory_stats = self.get_memory_stats()

        # Collect UI coverage metrics
        ui_coverage_metrics = {}
        if hasattr(self, "ui_coverage"):
            try:
                ui_coverage_metrics = self.ui_coverage.get_comprehensive_metrics()
            except Exception as e:
                logger.warning(f"Failed to get UI coverage metrics: {e}")

        results = {
            "status": "completed",
            "iterations": iteration,
            "execution_time_s": execution_time,
            "unique_states": len(state["visited_states"]),
            "total_transitions": len(state["state_transitions"]),
            "llm_tokens_input": state["llm_tokens_input"],
            "llm_tokens_output": state["llm_tokens_output"],
            "llm_time_ms": state["llm_time_ms"],
            "total_actions": counters["total_actions"],
            "llm_executed": counters["llm_executed"],
            "algorithm_chosen": counters["algorithm_chosen"],
            "llm_percentage": counters["llm_percentage"],
            "algorithm_percentage": counters["algorithm_percentage"],
            "llm_validation_failed": counters["llm_validation_failed"],
            "forced_back": counters["forced_back"],
            "memory_stats": memory_stats,
            "ui_coverage": ui_coverage_metrics,
            "tracking_counters": track.get_aggregate_counters(),
        }

        # Save metrics to file if output directory is configured
        if self.config.metrics_output_dir:
            from rv_agent.metrics import MetricsExporter

            MetricsExporter.export(
                results=results,
                output_dir=self.config.metrics_output_dir,
                package_name=self.config.package_name,
                agent_mode=self.config.agent_mode,
                timeout=self.config.timeout,
            )

        # Clean up trace file handler
        if trace_handler:
            logging.getLogger("rv_agent").removeHandler(trace_handler)
            trace_handler.close()

        return results

"""
Autonomous Android testing agent with modular architecture.

Implements an LLM-guided or algorithm-based agent that explores Android
applications using a modular component-based design with dependency injection.

### Architectural Principles:
- **Component-Based**: Specialized components handle distinct concerns
- **Dependency Injection**: All dependencies passed via constructor
- **Stateless LLM Context**: Fresh messages built from summaries each iteration
- **Multi-Mode Operation**: pure_algorithm, llm_only, multimode execution
- **Pluggable Strategies**: Swappable exploration algorithms (DFS, BFS, etc.)
- **Centralized Routing**: Decision routing between LLM and algorithm paths

### System Components:
- **RoutingManager**: Decision routing between exploration modes
- **ScreenProcessor**: UI parsing and element formatting
- **LLMClient**: LLM interaction and tool call handling
- **ToolExecutor**: Action execution on device
- **MemoryCoordinator**: Memory system coordination
- **ExplorationStrategy**: Algorithmic exploration (DFS, BFS)
- **ImageHandler**: Screenshot capture and optimization
"""

import time
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from langgraph.graph import StateGraph, END

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.domain.state import AgentState
from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_agent.strategies.strategy_registry import StrategyRegistry
from rv_agent.services.vision_service import ImageHandler
from rv_agent.services.screen_analyzer import ScreenProcessor
from rv_agent.llm.llm_client import LLMClient
from rv_agent.routing.routing_manager import RoutingManager
from rv_agent.routing.loop_detector import LoopDetector
from rv_agent.routing.fallback_manager import FallbackManager
from rv_agent.routing.stuck_recovery import StuckRecovery
from rv_agent.execution.tool_executor import ToolExecutor
from rv_agent.memory.memory_coordinator import MemoryCoordinator
from rv_agent.memory.agent_memory import AgentMemoryManager
from rv_agent.memory.long_term import LongTermMemory
from rv_agent.memory.short_term import ShortTermMemory
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.services.navigation_guidance import NavigationGuidance
from rv_agent.domain.action import ActionNormalizer
from rv_android_core.domain.static import StaticAnalysisData

# INSTRUMENTATION: Optional metrics collector for validation experiments
# This import and usage can be removed for production
try:
    from validation.multimodal.collector import MultimodalMetricsCollector
except ImportError:
    MultimodalMetricsCollector = None  # Not available outside validation context
from rv_agent.agent.nodes import (
    parse_ui_node,
    decision_router_node,
    algorithm_node,
    capture_screenshot_node,
    llm_generate_node,
    validate_action_node,
    execute_node,
    learn_node,
)

logger = logging.getLogger(__name__)


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
        # INSTRUMENTATION: Optional metrics collector for validation
        metrics_collector: Optional[Any] = None
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
            metrics_collector: INSTRUMENTATION - Optional collector for validation metrics
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

        # INSTRUMENTATION: Store metrics collector for validation
        # Can be removed for production
        self.metrics_collector = metrics_collector
        if metrics_collector:
            logger.info("INSTRUMENTATION: Metrics collector attached for validation")

        # Validate LLM client for modes that need it
        mode = config.get_agent_mode()
        if mode in ["llm_only", "multimode"] and llm_client is None:
            raise ValueError(f"LLM client required for mode: {mode}")

        # Level 1 stuck detection (screen unchanged)
        self.last_screen_hash = None
        self.stuck_screen_count = 0
        self.STUCK_THRESHOLD = 8  # Force BACK after 8 unchanged screens

        # Level 2 stuck detection (persistent same state)
        # Uses Backtrack BFS to find unsaturated ancestors, then RESTART if none found
        self.stuck_recovery = StuckRecovery(max_blocks=10)

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
        workflow.add_node("capture_screenshot", lambda s: capture_screenshot_node(self, s))
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
            {
                "llm": "capture_screenshot",
                "algorithm": "algorithm_node",
                "end": END
            }
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
            Metrics dictionary with exploration results
        """
        logger.info("Starting RVAgent execution")
        logger.info(f"DEBUG_TRACE: run() called, timeout={self.config.timeout}")

        start_time = time.time()
        iteration = 0

        # Launch app
        try:
            logger.info(f"Launching application: {self.config.package_name}")
            self.device.launch_app(self.config.package_name)
            time.sleep(2)
            logger.info("DEBUG_TRACE: App launched successfully")
        except Exception as e:
            logger.error(f"Failed to launch app: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

        # Initialize state
        state = {
            "iteration": 0,
            "start_time": start_time,
            "timeout": self.config.timeout,
            "visited_states": [],
            "state_transitions": [],
            "previous_screen_hash": None,
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
            # INSTRUMENTATION: Raw XML for hit classification
            "ui_xml": ""
        }

        # External execution loop
        logger.info(f"DEBUG_TRACE: Starting loop, timeout={self.config.timeout}")
        consecutive_errors = 0
        max_consecutive_errors = 10

        while True:
            try:
                elapsed = time.time() - start_time
                logger.info(f"DEBUG_TRACE: Loop check, elapsed={elapsed:.1f}, timeout={self.config.timeout}")

                if elapsed >= self.config.timeout:
                    logger.info(f"🏁 Timeout reached ({elapsed:.1f}s)")
                    break

                logger.info(f"⏱️  Iteration {iteration} (elapsed: {elapsed:.1f}s)")

                state["iteration"] = iteration

                # Invoke graph for one iteration
                # Set recursion_limit to prevent infinite loops in validation routing
                logger.info(f"DEBUG_TRACE: Before graph.invoke(), iteration={iteration}")
                result = self.graph.invoke(state, {"recursion_limit": 100})
                logger.info(f"DEBUG_TRACE: After graph.invoke(), result keys={list(result.keys()) if result else 'None'}")

                # Update state with results
                state.update(result)

                iteration += 1
                consecutive_errors = 0  # Reset on success
                logger.info(f"DEBUG_TRACE: Iteration incremented to {iteration}")
                time.sleep(0.5)

            except KeyboardInterrupt:
                logger.info("⚠️  Interrupted by user")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"DEBUG_TRACE: Exception in iteration {iteration}: {type(e).__name__}: {e}")
                logger.error(f"❌ Iteration error (attempt {consecutive_errors}/{max_consecutive_errors}): {e}")

                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"❌ Too many consecutive errors ({max_consecutive_errors}), but continuing until timeout")
                    consecutive_errors = 0  # Reset to allow more attempts

                time.sleep(1)  # Brief pause before retry

        # Compute final metrics
        execution_time = time.time() - start_time

        # INSTRUMENTATION: Finalize metrics collection
        # This block can be removed for production
        if self.metrics_collector:
            try:
                self.metrics_collector.finalize()
                logger.info("INSTRUMENTATION: Metrics collection finalized")
            except Exception as e:
                logger.warning(f"INSTRUMENTATION: Failed to finalize metrics: {e}")
        # END INSTRUMENTATION

        # Get decision counters (detailed breakdown)
        counters = self.routing_manager.get_decision_counters()

        # Collect memory statistics
        memory_stats = self.get_memory_stats()

        # Collect UI coverage metrics (core functionality)
        ui_coverage_metrics = {}
        if hasattr(self, 'ui_coverage'):
            try:
                ui_coverage_metrics = self.ui_coverage.get_comprehensive_metrics()
            except Exception as e:
                logger.warning(f"Failed to get UI coverage metrics: {e}")

        return {
            "status": "completed",
            "iterations": iteration,
            "execution_time_s": execution_time,
            "unique_states": len(state["visited_states"]),
            "total_transitions": len(state["state_transitions"]),
            "llm_tokens_input": state["llm_tokens_input"],
            "llm_tokens_output": state["llm_tokens_output"],
            "llm_time_ms": state["llm_time_ms"],

            # Decision counters
            "total_actions": counters["total_actions"],

            # Primary counters (validate 70/30 proportion)
            "llm_executed": counters["llm_executed"],
            "algorithm_chosen": counters["algorithm_chosen"],
            "llm_percentage": counters["llm_percentage"],
            "algorithm_percentage": counters["algorithm_percentage"],

            # Event counters
            "llm_validation_failed": counters["llm_validation_failed"],
            "forced_back": counters["forced_back"],

            "memory_stats": memory_stats,
            "ui_coverage": ui_coverage_metrics
        }

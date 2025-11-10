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
from typing import Optional, Dict, Any

from langgraph.graph import StateGraph, END

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.llm.graph.state import AgentState
from rv_agent.core.device_interface import DeviceInterface
from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_agent.strategies.base_strategy import ExplorationStrategy
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
from rv_android_core.domain.static import StaticAnalysisData

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
        static_data: Optional[StaticAnalysisData] = None
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
            static_data: Optional static analysis data
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
        self.static_data = static_data

        # Validate LLM client for modes that need it
        mode = config.get_agent_mode()
        if mode in ["llm_only", "multimode"] and llm_client is None:
            raise ValueError(f"LLM client required for mode: {mode}")

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
          algorithm  llm   end
             ↓        ↓
        algorithm_node  capture_screenshot
             ↓        ↓
             │     llm_generate
             │        ↓
             │    validation_router
             │     ↙       ↘
             │  execute  algorithm_node
             │     ↓         ↓
             └─→ execute ←───┘
                   ↓
                 learn
                   ↓
                  END

        Returns:
            Compiled LangGraph workflow
        """
        mode = self.config.get_agent_mode()
        logger.info(f"Building workflow (mode={mode})")

        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("parse_ui", self._parse_ui_node)
        workflow.add_node("decision_router", self._decision_router_node)
        workflow.add_node("algorithm_node", self._algorithm_node)
        workflow.add_node("capture_screenshot", self._capture_screenshot_node)
        workflow.add_node("llm_generate", self._llm_generate_node)
        workflow.add_node("validation_router", self._validation_router_node)
        workflow.add_node("execute", self._execute_node)
        workflow.add_node("learn", self._learn_node)

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
        workflow.add_edge("llm_generate", "validation_router")

        # Validation routing
        workflow.add_conditional_edges(
            "validation_router",
            lambda s: s.get("validation_path", "execute"),
            {
                "execute": "execute",
                "algorithm_fallback": "algorithm_node"
            }
        )

        # Algorithm path
        workflow.add_edge("algorithm_node", "execute")

        # Common path
        workflow.add_edge("execute", "learn")
        workflow.add_edge("learn", END)

        logger.info("Workflow compiled successfully")
        return workflow.compile()

    def _parse_ui_node(self, state: AgentState) -> AgentState:
        """Parse current screen UI and update state."""
        logger.info("📱 PARSE_UI: Parsing screen")

        result = self.screen_processor.parse_current_screen(
            target_package=self.config.package_name,
            external_navigation_count=state.get("external_navigation_count", 0)
        )

        return {
            "current_screen_hash": result["screen_hash"],
            "current_activity": result["activity"],
            "screen_description": result["screen_description"],
            "ui_elements_text": result["ui_elements_text"],
            "is_external": result["is_external"],
            "external_navigation_count": result["external_navigation_count"]
        }

    def _decision_router_node(self, state: AgentState) -> AgentState:
        """Route decision between LLM and algorithm."""
        logger.info("🔀 DECISION_ROUTER: Routing decision")

        iteration = state.get("iteration", 0)
        decision_path = self.routing_manager.route_decision(iteration)

        return {
            "decision_path": decision_path,
            "decision_maker": decision_path  # Track for metrics
        }

    def _algorithm_node(self, state: AgentState) -> AgentState:
        """Generate action using algorithmic strategy."""
        logger.info("🤖 ALGORITHM: Generating action")

        screen_hash = state.get("current_screen_hash")
        screen_desc = state.get("screen_description")

        item_action = self.strategy.select_next_action(screen_hash, screen_desc)

        if not item_action:
            logger.warning("No action available from strategy")
            return {
                "current_action": None,
                "decision_path": "end"
            }

        # Get coordinates from ItemAction
        coords = item_action.get_execution_coordinates()
        if not coords:
            logger.error("Failed to get coordinates from ItemAction")
            return {
                "current_action": None,
                "decision_path": "end"
            }

        x, y = coords

        # Convert ItemAction to action dict
        action = {
            "action_type": item_action.action_type.upper(),
            "x": x,
            "y": y,
            "id": item_action.id,
            "text": item_action.text or ""
        }

        logger.info(f"Algorithm selected: {action['action_type']} at ({x}, {y})")

        return {
            "current_action": action,
            "current_item_action": item_action,  # Store for transition recording
            "decision_maker": "algorithm"  # Track that action came from algorithm
        }

    def _capture_screenshot_node(self, state: AgentState) -> AgentState:
        """Capture and optimize screenshot for LLM."""
        logger.info("📸 CAPTURE_SCREENSHOT: Capturing screen")

        try:
            # Capture screenshot (returns file path)
            screenshot_path = self.device.take_screenshot()

            # Optimize screenshot to base64 (same as old code)
            screenshot_b64 = self.image_handler.optimize(
                image_path=screenshot_path,
                quality=90
            )

            if not screenshot_b64:
                logger.error("Screenshot optimization failed")
                return {
                    "screenshot_b64": "",
                    "decision_path": "end"
                }

            logger.info(f"Screenshot captured and optimized")

            return {"screenshot_b64": screenshot_b64}

        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}", exc_info=True)
            return {
                "screenshot_b64": "",
                "decision_path": "end"
            }

    def _llm_generate_node(self, state: AgentState) -> AgentState:
        """Generate action using LLM."""
        logger.info("🤖 LLM_GENERATE: Calling LLM")

        if not self.llm_client:
            logger.error("LLM client not available")
            return {
                "llm_action": None,
                "has_tool_calls": False,
                "validation_path": "algorithm_fallback"
            }

        result = self.llm_client.generate_action(
            screen_description=state.get("screen_description"),
            screenshot_b64=state.get("screenshot_b64", ""),
            ui_elements_text=state.get("ui_elements_text", ""),
            iteration=state.get("iteration", 0),
            last_action_summary=state.get("action_history_summary")
        )

        return {
            "llm_action": result.get("action"),
            "has_tool_calls": result.get("has_tool_calls", False),
            "llm_reasoning": result.get("reasoning", ""),
            "llm_tokens_input": state.get("llm_tokens_input", 0) + result.get("tokens_input", 0),
            "llm_tokens_output": state.get("llm_tokens_output", 0) + result.get("tokens_output", 0),
            "llm_time_ms": state.get("llm_time_ms", 0) + result.get("time_ms", 0),
            "decision_maker": "llm"  # Track that action came from LLM
        }

    def _validation_router_node(self, state: AgentState) -> AgentState:
        """Validate LLM action and route to execution or fallback."""
        logger.info("✅ VALIDATION_ROUTER: Validating LLM action")

        llm_action = state.get("llm_action")
        has_tool_calls = state.get("has_tool_calls", False)
        recent_actions = state.get("recent_action_window", [])

        # DEBUG: Log what we received from state
        logger.warning(f"🔍 VALIDATION_ROUTER DEBUG:")
        logger.warning(f"   llm_action: {llm_action}")
        logger.warning(f"   has_tool_calls from state: {has_tool_calls}")
        logger.warning(f"   state keys: {list(state.keys())}")

        validation_result = self.routing_manager.validate_llm_action(
            llm_action=llm_action,
            recent_actions=recent_actions,
            has_tool_calls=has_tool_calls
        )

        # Update current_action if validation passed
        if validation_result.get("current_action"):
            return {
                "current_action": validation_result["current_action"],
                "validation_path": validation_result["validation_path"],
                "loop_detected": validation_result["loop_detected"],
                "used_fallback": validation_result["used_fallback"],
                "decision_maker": "llm"  # Preserve LLM source for validated actions
            }
        else:
            return {
                "validation_path": validation_result["validation_path"],
                "loop_detected": validation_result["loop_detected"],
                "used_fallback": validation_result["used_fallback"]
            }

    def _execute_node(self, state: AgentState) -> AgentState:
        """Execute action on device."""
        logger.info("⚙️ EXECUTE: Executing action")

        action = state.get("current_action")

        if not action:
            logger.warning("No action to execute")
            return {"action_executed": None}

        # Determine if coordinate conversion is needed based on action source
        # LLM actions use optimized image space (704x1248) and need conversion
        # Algorithm actions already use device space (1080x1920) and don't need conversion
        decision_maker = state.get("decision_maker", "unknown")
        convert_coords = (decision_maker == "llm")

        logger.debug(f"Executing action from {decision_maker}, convert_coords={convert_coords}")

        result = self.tool_executor.execute_action(action, convert_coordinates=convert_coords)

        # Record transition if action succeeded
        if result.get("success"):
            prev_hash = state.get("previous_screen_hash")
            current_hash = state.get("current_screen_hash", "")
            item_action = state.get("current_item_action")  # Get stored ItemAction

            if prev_hash and item_action:
                # Record transition in strategy using the original ItemAction
                self.strategy.record_transition(prev_hash, current_hash, item_action)
                logger.debug(f"Recorded transition: {prev_hash[:8]} → {current_hash[:8]}")

        # Update current_action with normalized format for proper memory recording
        # This ensures LLM actions (which start in tool_name/tool_args format)
        # are properly normalized before being passed to memory_coordinator
        normalized_action = result.get("action_executed")

        return {
            "current_action": normalized_action,  # Update with normalized action
            "action_executed": normalized_action,
            "action_success": result.get("success", False)
        }

    def _learn_node(self, state: AgentState) -> AgentState:
        """Update memory systems and prepare for next iteration."""
        logger.info("📚 LEARN: Updating memories")

        # Update memories
        memory_result = self.memory_coordinator.update_memories(
            current_screen_hash=state.get("current_screen_hash", "unknown"),
            current_activity=state.get("current_activity", "unknown"),
            screen_description=state.get("screen_description"),
            action=state.get("current_action"),
            llm_reasoning=state.get("llm_reasoning", ""),
            iteration=state.get("iteration", 0),
            recent_action_window=state.get("recent_action_window", [])
        )

        # Generate summaries
        summaries = self.memory_coordinator.generate_summaries(
            action=state.get("current_action"),
            current_activity=state.get("current_activity", "unknown"),
            visited_states=state.get("visited_states", []),
            state_transitions=state.get("state_transitions", [])
        )

        # Track state discovery
        tracking = self.memory_coordinator.track_state_discovery(
            current_hash=state.get("current_screen_hash"),
            previous_hash=state.get("previous_screen_hash"),
            visited_states=state.get("visited_states", []),
            state_transitions=state.get("state_transitions", [])
        )

        # Check continuation
        continuation = self.memory_coordinator.check_continuation(
            start_time=state.get("start_time"),
            timeout=state.get("timeout")
        )

        # Update state
        return {
            "recent_action_window": memory_result["recent_action_window"],
            "action_history_summary": summaries["action_history_summary"],
            "exploration_summary": summaries["exploration_summary"],
            "memory_insights": summaries["memory_insights"],
            "navigation_path": summaries["navigation_path"],
            "visited_states": tracking["visited_states"],
            "state_transitions": tracking["state_transitions"],
            "previous_screen_hash": state.get("current_screen_hash"),
            "should_continue": continuation["should_continue"],
            "loop_detected": False  # Reset for next iteration
        }

    def run(self) -> Dict[str, Any]:
        """
        Execute agent exploration with external timeout loop.

        Returns:
            Metrics dictionary with exploration results
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
            # LLM action validation fields (multimode)
            "llm_action": None,
            "has_tool_calls": False,
            "llm_reasoning": "",
            "validation_path": ""
        }

        # External execution loop
        try:
            while True:
                elapsed = time.time() - start_time

                if elapsed >= self.config.timeout:
                    logger.info(f"🏁 Timeout reached ({elapsed:.1f}s)")
                    break

                logger.info(f"⏱️  Iteration {iteration} (elapsed: {elapsed:.1f}s)")

                state["iteration"] = iteration

                # Invoke graph for one iteration
                result = self.graph.invoke(state)

                # Update state with results
                state.update(result)

                iteration += 1
                time.sleep(0.5)

        except KeyboardInterrupt:
            logger.info("⚠️  Interrupted by user")
        except Exception as e:
            logger.error(f"❌ Execution error: {e}", exc_info=True)

        # Compute final metrics
        execution_time = time.time() - start_time

        # Get decision counters
        counters = self.routing_manager.get_decision_counters()

        return {
            "status": "completed",
            "iterations": iteration,
            "execution_time_s": execution_time,
            "unique_states": len(state["visited_states"]),
            "total_transitions": len(state["state_transitions"]),
            "llm_tokens_input": state["llm_tokens_input"],
            "llm_tokens_output": state["llm_tokens_output"],
            "llm_time_ms": state["llm_time_ms"],
            "llm_decisions": counters["llm_decisions"],
            "algorithm_decisions": counters["algorithm_decisions"]
        }

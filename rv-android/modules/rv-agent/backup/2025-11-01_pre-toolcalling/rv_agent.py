"""
Autonomous Android testing agent with stateless context architecture.

Implements an LLM-based agent that explores Android applications using
multimodal understanding with CONSTANT token usage per iteration (no history accumulation).

### Stateless Architecture:
- NO MESSAGE HISTORY: Each LLM call receives fresh message built from summaries
- AgentMemoryManager: Generates pre-formatted summary strings
- Constant ~2500 tokens/iteration vs exponential growth
- Prevents context window overflow (32K limit)
"""

import os
import time
import base64
import logging
from typing import Optional, Dict, Any, Set
from pathlib import Path

from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.llm.graph.state import AgentState
from rv_agent.core.device_interface import DeviceInterface
from rv_agent.core.screenshot_optimizer import ScreenshotOptimizer
from rv_agent.core.dynamic_state_graph import DynamicStateGraph, compute_screen_hash
from rv_agent.core.coordinate_converter import CoordinateConverter
from rv_agent.strategies import DFSStrategy, BFSStrategy
from rv_agent.memory import AgentMemoryManager
from rv_agent.memory.long_term import LongTermMemory
from rv_agent.memory.short_term import ShortTermMemory
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_android_core.domain.static import StaticAnalysisData

# Import versioned prompts - CHANGE HERE TO SWITCH VERSIONS
from rv_agent.prompts import v4 as current_prompt  # v1 = baseline, v2 = diversity-focused, v3 = enforced (broken), v4 = balanced

logger = logging.getLogger(__name__)


class RVAgent:
    """
    Autonomous Android exploration agent with stateless LLM context.

    ### Key Architectural Changes:
    - **Stateless Messaging**: No message history accumulation
    - **AgentMemoryManager**: Generates pre-formatted summary strings
    - **Constant Token Usage**: ~2500 tokens per iteration (vs exponential)
    - **Fresh Messages**: Each LLM call constructs new message from summaries

    ### Integration Pattern (from rvsmart-tool):
    - Memory provides PRE-FORMATTED STRINGS (not objects)
    - Summaries limited to last N actions (default 5)
    - Exploration state tracked separately from LLM context
    - Each iteration builds fresh HumanMessage with all context embedded

    ### Benefits:
    - No context window overflow (stays under 32K)
    - Predictable token usage for cost/performance planning
    - Can run unlimited iterations without memory growth
    - GPU RAM stays constant (no 14GB spikes)
    """

    def __init__(
        self,
        config: RVAgentConfig,
        static_data: Optional[StaticAnalysisData] = None,
        device: Optional[Any] = None
    ):
        """
        Initialize RVAgent with stateless context architecture.

        Args:
            config: Agent configuration
            static_data: Optional static analysis data for MOP guidance
            device: Optional device interface (for testing/validation)
        """
        self.config = config
        self.static_data = static_data

        logger.info("Initializing RVAgent (STATELESS architecture)")
        logger.info(f"Strategy: {config.strategy}")
        logger.info(f"Device: {config.device_id}")
        logger.info(f"Package: {config.package_name}")
        logger.info(f"Static analysis: {'enabled' if static_data else 'disabled'}")

        # Device interaction (use injected device or create new one)
        if device is not None:
            self.device = device
            logger.info("Using injected device interface (validation mode)")
        else:
            self.device = DeviceInterface(device_id=config.device_id)
        self.screenshot_optimizer = ScreenshotOptimizer()

        # UI parsing
        self.parser = UIAutomator2Parser(DefaultTextVisitor)

        # STATELESS Memory Manager (generates summaries)
        self.memory_manager = AgentMemoryManager(
            max_action_history=5,  # Limit to last 5 actions
            max_navigation_path=5   # Last 5 activities
        )
        logger.info("AgentMemoryManager initialized for stateless context")

        # Legacy memory systems (still used for exploration tracking)
        self.long_term = LongTermMemory(static_data)
        self.short_term = ShortTermMemory()
        self.ui_coverage = UICoverageTracker()

        # Dynamic exploration graph (structural hash)
        self.dynamic_graph = DynamicStateGraph()

        # Pluggable strategy (DFS or BFS)
        if config.strategy == "dfs":
            self.strategy = DFSStrategy(self.dynamic_graph, static_data)
            logger.info("Using DFS strategy")
        elif config.strategy == "bfs":
            self.strategy = BFSStrategy(self.dynamic_graph, static_data)
            logger.info("Using BFS strategy")
        else:
            raise ValueError(f"Unknown strategy: {config.strategy}")

        # Coordinate converter
        self.converter = CoordinateConverter(
            device_dimensions=config.device_dimensions,
            optimized_dimensions=config.optimized_dimensions
        )

        logger.info(
            f"Coordinate converter: {config.device_dimensions} → {config.optimized_dimensions}"
        )

        # Create LLM instance (NO TOOLS - stateless pattern uses parsing)
        llm_config = config.get_langchain_config()
        self.llm = ChatOllama(
            model="qwen-vision-tools-v1",
            temperature=llm_config['temperature'],
            top_p=llm_config.get('top_p', 0.8),
            top_k=llm_config.get('top_k', 50),
            base_url=llm_config.get('base_url', 'http://localhost:11434'),
            timeout=60.0,
            request_timeout=60.0
        )

        logger.info("LLM configured: qwen-vision-tools-v1 (stateless mode)")

        # LangGraph workflow (simplified for stateless)
        self.graph = self._build_agent_graph()

        # External loop state (persisted between graph invocations)
        self.external_navigation_count = 0

        logger.info("RVAgent initialized successfully (STATELESS)")

    def _build_agent_graph(self):
        """
        Build simplified LangGraph workflow for stateless processing.

        ### Stateless Simplifications:
        - No ToolNode (actions embedded in response parsing)
        - Linear flow: observe → assistant → act → learn → END
        - Each iteration is independent (no accumulated context)

        Returns:
            Compiled LangGraph workflow
        """
        logger.info("Building LangGraph workflow (stateless mode)")

        workflow = StateGraph(AgentState)

        # Add stateless nodes
        workflow.add_node("observe", self._observe_node)
        workflow.add_node("assistant", self._assistant_node)
        workflow.add_node("act", self._act_node)
        workflow.add_node("learn", self._learn_node)

        # Simple linear flow (no conditionals needed)
        workflow.set_entry_point("observe")
        workflow.add_edge("observe", "assistant")
        workflow.add_edge("assistant", "act")
        workflow.add_edge("act", "learn")
        workflow.add_edge("learn", END)

        logger.info("LangGraph workflow compiled (stateless mode)")
        return workflow.compile()

    def _observe_node(self, state: AgentState) -> AgentState:
        """
        Observe current screen state - NO message construction.

        ### Stateless Pattern:
        - Captures current UI state and screenshot
        - NO message creation (done in assistant node)
        - Returns raw observation data

        Returns:
            Updated state with current observations
        """
        logger.info("🔍 OBSERVE: Capturing current screen state")

        try:
            # Get current UI state
            ui_state = self.device.get_current_ui_state()

            # Take and optimize screenshot
            screenshot_path = self.device.take_screenshot()
            screenshot_b64 = self._load_and_optimize_screenshot(screenshot_path)

            # Parse screen
            screen_description = self.parser.parse(
                ui_state['xml'],
                static_data=self.static_data
            )

            # Compute screen hash
            screen_hash = compute_screen_hash(ui_state['xml'])

            logger.info(f"   Activity: {ui_state['current_activity']}")
            logger.info(f"   Screen hash: {screen_hash[:12]}...")
            logger.info(f"   UI elements: {len(screen_description.items)}")

            return {
                "screenshot_b64": screenshot_b64,
                "current_screen_hash": screen_hash,
                "current_activity": ui_state['current_activity'],
                "screen_description": screen_description
            }

        except Exception as e:
            logger.error(f"❌ Observation failed: {e}", exc_info=True)
            raise

    def _assistant_node(self, state: AgentState) -> AgentState:
        """
        Generate action using stateless LLM call with fresh message.

        ### Stateless Pattern:
        - Builds FRESH HumanMessage from state summaries
        - NO message history (completely independent call)
        - Includes screenshot in multimodal message
        - Parses action from response content

        Returns:
            Updated state with action and token metrics
        """
        logger.info("🤖 ASSISTANT: Generating action with stateless context")

        start_time = time.time()

        try:
            # Build fresh message from summaries
            message = self._build_stateless_message(state)

            # Log token estimate
            logger.info(f"   Message constructed (estimated ~2500 tokens)")

            # Single LLM call with fresh message
            response = self.llm.invoke([message])

            llm_time_ms = (time.time() - start_time) * 1000

            # Extract tokens
            llm_tokens_input = 0
            llm_tokens_output = 0

            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                llm_tokens_input = response.usage_metadata.get('input_tokens', 0)
                llm_tokens_output = response.usage_metadata.get('output_tokens', 0)
            elif hasattr(response, 'response_metadata') and response.response_metadata:
                metadata = response.response_metadata
                llm_tokens_input = metadata.get('prompt_eval_count', 0)
                llm_tokens_output = metadata.get('eval_count', 0)

            logger.info(f"   LLM Response: {llm_time_ms:.1f}ms, "
                       f"tokens: {llm_tokens_input} in / {llm_tokens_output} out")

            # Parse action from response
            action = self._parse_action(response.content, state)

            return {
                "llm_tokens_input": llm_tokens_input,
                "llm_tokens_output": llm_tokens_output,
                "llm_time_ms": llm_time_ms,
                "current_action": action
            }

        except Exception as e:
            logger.error(f"❌ Assistant failed: {e}", exc_info=True)
            # Return fallback action
            return {
                "llm_tokens_input": 0,
                "llm_tokens_output": 0,
                "llm_time_ms": (time.time() - start_time) * 1000,
                "current_action": {"action_type": "BACK", "explanation": "Fallback due to error"}
            }

    def _build_stateless_message(self, state: AgentState) -> HumanMessage:
        """
        Build fresh HumanMessage from state summaries (NO HISTORY).

        ### Message Structure:
        - System prompt with agent goals
        - Current screen context (activity, UI elements)
        - Action history summary (last 5 actions)
        - Exploration summary (states/transitions)
        - Memory insights (visit patterns)
        - Navigation path (activity flow)
        - Screenshot (multimodal)

        Returns:
            Fresh HumanMessage with all context embedded
        """
        # Get system prompt from versioned module
        system_text = current_prompt.get_system_prompt()

        # Format UI elements
        ui_elements_text = self._format_ui_elements(state['screen_description'])

        # Build context from summaries
        context_parts = [
            "# Current Screen",
            f"Activity: {state['current_activity']}",
            f"Screen ID: {state['current_screen_hash'][:12]}...",
            "",
            "# UI Elements",
            ui_elements_text,
            "",
            "# Action History",
            state.get('action_history_summary', 'No previous actions.'),
            "",
            "# Exploration Status",
            state.get('exploration_summary', 'Starting exploration.'),
            "",
            "# Memory Insights",
            state.get('memory_insights', 'No insights yet.'),
            "",
            "# Navigation Path",
            state.get('navigation_path', 'Starting navigation.'),
            "",
            "Generate the next action (JSON format):"
        ]

        user_text = "\n".join(context_parts)

        # Build multimodal message
        return HumanMessage(content=[
            {"type": "text", "text": f"{system_text}\n\n{user_text}"},
            {"type": "image_url", "image_url": {
                "url": f"data:image/png;base64,{state['screenshot_b64']}"
            }}
        ])

    def _format_ui_elements(self, screen_description) -> str:
        """Format UI elements as text list."""
        if not screen_description or not screen_description.items:
            return "No interactive elements found."

        lines = []
        for i, item in enumerate(screen_description.items[:15], 1):  # Limit to 15
            elem_type = item.view.get('class', 'View').split('.')[-1]
            text = item.view.get('text', '')
            resource_id = item.view.get('resource_id', '').split('/')[-1]

            desc = f"{i}. {elem_type}"
            if text:
                desc += f" '{text}'"
            if resource_id:
                desc += f" ({resource_id})"

            # Add MOP markers if available
            if hasattr(item, 'actions') and item.actions:
                action = item.actions[0]
                if action.directly_reaches_mop:
                    desc += " [DM]"
                elif action.reaches_mop:
                    desc += " [M]"

            lines.append(desc)

        ui_text = "\n".join(lines)

        # 🐛 DEBUG: Log UI description with EditText detection
        logger.debug(f"🐛 UI DESCRIPTION ({len(screen_description.items)} elements, showing {min(15, len(screen_description.items))}):\n{ui_text}")
        edittext_count = sum(1 for item in screen_description.items if 'EditText' in item.view.get('class', ''))
        if edittext_count > 0:
            logger.warning(f"🐛 EDITTEXT DETECTED: {edittext_count} EditText elements in UI!")

        return ui_text

    def _parse_action(self, response_content: str, state: AgentState) -> Dict:
        """Parse action from LLM response (JSON or text) - IMPROVED."""
        import json
        import re

        logger.debug(f"Parsing action from response: {response_content[:200]}...")

        # 🐛 DEBUG: Log full LLM response
        logger.debug(f"🐛 FULL LLM RESPONSE:\n{response_content}")

        # Try multiple JSON extraction patterns
        json_patterns = [
            r'\{[^{}]*"action_type"[^{}]*\}',  # Simple JSON
            r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}',  # Nested JSON
            r'```json\s*(\{.*?\})\s*```',      # Markdown code block
            r'```\s*(\{.*?\})\s*```',          # Generic code block
        ]

        for pattern in json_patterns:
            try:
                json_match = re.search(pattern, response_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1) if json_match.lastindex else json_match.group()
                    action = json.loads(json_str)
                    if "action_type" in action:
                        logger.info(f"✅ Parsed action: {action['action_type']}")
                        logger.debug(f"🐛 PARSED ACTION FULL: {action}")
                        return action
            except Exception as e:
                logger.debug(f"Pattern {pattern} failed: {e}")
                continue

        # Fallback: extract action_type from text
        logger.warning("JSON parsing failed, using text fallback")
        logger.error(f"🐛 PARSING FAILED - Full response:\n{response_content}")
        action_type = "BACK"
        target = None
        text = None

        content_upper = response_content.upper()
        if "CLICK" in content_upper:
            action_type = "CLICK"
            # Try to extract target
            target_match = re.search(r'(?:element|button|item)\s*(\d+)', response_content, re.IGNORECASE)
            if target_match:
                target = target_match.group(1)
        elif "TYPE" in content_upper or "TEXT" in content_upper:
            action_type = "TYPE_TEXT"
            # Try to extract text
            text_match = re.search(r'["\']([^"\']+)["\']', response_content)
            if text_match:
                text = text_match.group(1)
        elif "LONG" in content_upper:
            action_type = "LONG_CLICK"
        elif "HOME" in content_upper:
            action_type = "HOME"

        action = {
            "action_type": action_type,
            "explanation": "Parsed from text response (fallback)"
        }
        if target:
            action["target"] = target
        if text:
            action["text"] = text

        logger.info(f"⚠️ Fallback action: {action_type}")
        return action

    def _act_node(self, state: AgentState) -> AgentState:
        """
        Execute action and update memory summaries.

        ### Stateless Pattern:
        - Executes parsed action
        - Records in AgentMemoryManager
        - Generates NEW summaries (replaces old ones)
        - Updates exploration state

        Returns:
            Updated state with new summaries
        """
        logger.info("⚡ ACT: Executing action and updating memory")

        action = state["current_action"]
        activity = state["current_activity"]

        # Execute action
        success = self._execute_action(action, state)

        # Record in memory manager
        self.memory_manager.record_action(action, activity, success)

        # Update exploration tracking
        screen_hash = state["current_screen_hash"]
        state["visited_states"].add(screen_hash)

        # Generate NEW summaries (stateless)
        action_history_summary = self.memory_manager.get_action_history_summary()
        exploration_summary = self.memory_manager.get_exploration_summary(
            state["visited_states"],
            state["state_transitions"]
        )
        memory_insights = self.memory_manager.get_memory_insights(activity)
        navigation_path = self.memory_manager.get_navigation_path()

        logger.info(f"   Action: {action['action_type']}")
        logger.info(f"   Success: {success}")
        logger.info(f"   States visited: {len(state['visited_states'])}")

        return {
            "action_history_summary": action_history_summary,
            "exploration_summary": exploration_summary,
            "memory_insights": memory_insights,
            "navigation_path": navigation_path
        }

    def _execute_action(self, action: Dict, state: AgentState) -> bool:
        """
        Execute action on device using injected device interface.

        Uses state["_device"] instead of self.device to support MockDeviceInterface
        during validation and real DeviceInterface during execution.
        """
        action_type = action.get("action_type", "BACK")
        device = state.get("_device")

        if not device:
            logger.error("No device interface in state!")
            return False

        try:
            if action_type == "CLICK":
                # Find element and click - HYBRID: supports both numeric index and element IDs
                target_id = action.get("target", "1")
                screen_desc = state.get("screen_description")

                if not screen_desc or not screen_desc.items:
                    logger.warning("   No screen_description available")
                    return False

                # Try numeric index first
                if target_id.isdigit():
                    idx = int(target_id) - 1
                    if 0 <= idx < len(screen_desc.items):
                        item = screen_desc.items[idx]
                        bounds = item.view.get("bounds")
                        if bounds:
                            x = (bounds[0][0] + bounds[1][0]) // 2
                            y = (bounds[0][1] + bounds[1][1]) // 2
                            device.click(x, y)
                            logger.info(f"   Executed CLICK at ({x}, {y}) on element {idx+1}")
                            return True
                    else:
                        logger.warning(f"   Invalid target index: {idx}")
                        return False

                # Fallback: try matching by element ID (resource_id)
                else:
                    logger.info(f"   Target is element ID, searching: {target_id}")
                    logger.info(f"   Total items in screen_desc: {len(screen_desc.items)}")

                    for idx, item in enumerate(screen_desc.items):
                        # IMPORTANT: Parser stores as "resource_id" (underscore), not "resource-id" (hyphen)
                        resource_id = item.view.get("resource_id", "")
                        logger.info(f"   Item {idx}: resource_id='{resource_id}', class={item.view.get('class', 'unknown')}")

                        # Match by resource_id (e.g., "br.unb.cic.cryptoapp:id/buttonMessageDigest")
                        if resource_id and target_id in resource_id:
                            bounds = item.view.get("bounds")
                            if bounds:
                                x = (bounds[0][0] + bounds[1][0]) // 2
                                y = (bounds[0][1] + bounds[1][1]) // 2
                                device.click(x, y)
                                logger.info(f"   ✅ Executed CLICK at ({x}, {y}) on element with ID: {target_id}")
                                return True

                    logger.warning(f"   ❌ Element ID not found: {target_id}")
                    logger.warning(f"   Searched through {len(screen_desc.items)} items, no match for '{target_id}'")
                    return False

            elif action_type == "TYPE_TEXT":
                text = action.get("text", "test")
                device.input_text(text)
                logger.info(f"   Executed TYPE_TEXT: '{text}'")
                return True

            elif action_type == "LONG_CLICK":
                # Similar to CLICK but long press
                target_id = action.get("target", "1")
                if target_id.isdigit():
                    idx = int(target_id) - 1
                    screen_desc = state.get("screen_description")
                    if screen_desc and 0 <= idx < len(screen_desc.items):
                        item = screen_desc.items[idx]
                        bounds = item.view.get("bounds")
                        if bounds:
                            x = (bounds[0][0] + bounds[1][0]) // 2
                            y = (bounds[0][1] + bounds[1][1]) // 2
                            device.long_click(x, y)
                            logger.info(f"   Executed LONG_CLICK at ({x}, {y})")
                            return True
                return False

            elif action_type == "BACK":
                device.back()
                logger.info(f"   Executed BACK")
                return True

            elif action_type == "HOME":
                device.home()
                logger.info(f"   Executed HOME")
                return True

            else:
                logger.warning(f"   Unknown action type: {action_type}")
                return False

        except Exception as e:
            logger.error(f"Action execution failed: {e}", exc_info=True)
            return False

    def _learn_node(self, state: AgentState) -> AgentState:
        """
        Update memory systems after action execution.

        Updates:
        - DynamicStateGraph: Records state transition
        - ShortTermMemory: Adds iteration record
        - UICoverageTracker: Updates element coverage
        - LongTermMemory: Updates activity visits (if applicable)

        Returns:
            Updated state with should_continue flag
        """
        logger.info("📚 LEARN: Updating memory systems")

        # Extract state variables
        current_screen = state.get("current_screen_hash", "unknown")
        current_activity = state.get("current_activity", "unknown")
        action = state.get("current_action", {})
        screen_desc = state.get("screen_description")

        # Get injected memory systems
        dynamic_graph = state.get("_graph")
        short_term = state.get("_short_term")
        ui_coverage = state.get("_ui_coverage")
        long_term = state.get("_long_term")

        try:
            # Update DynamicStateGraph - CORRECTED API
            if dynamic_graph and screen_desc:
                # Create or update state node (CORRECT: use get_or_create_state)
                node = dynamic_graph.get_or_create_state(
                    screen_hash=current_screen,
                    activity=current_activity,
                    screen_desc=screen_desc
                )
                logger.debug(f"   Updated DynamicGraph state: {current_screen[:8]} (visits: {node.visit_count})")

                # Record action execution (CORRECT: use record_action)
                # Extract action_id from action (use element index or hash)
                action_id = hash(str(action))  # Simple hash for now
                dynamic_graph.record_action(
                    screen_hash=current_screen,
                    action_id=action_id,
                    next_hash=None,  # Will be known on next iteration
                    timestamp=time.time()
                )
                logger.debug(f"   Recorded action in DynamicGraph")

            # Update ShortTermMemory - CORRECTED API
            if short_term:
                # CORRECT: use record_iteration with proper parameters
                state_dict = {
                    "screen_hash": current_screen,
                    "activity": current_activity
                }
                actions_list = [action] if action else []
                llm_reasoning = state.get("llm_reasoning", "")

                short_term.record_iteration(
                    state=state_dict,
                    actions=actions_list,
                    llm_reasoning=llm_reasoning
                )
                logger.debug(f"   Updated ShortTermMemory: iteration {state.get('iteration', 0)}")

            # Update UICoverageTracker - CORRECTED API
            if ui_coverage and screen_desc:
                for item in screen_desc.items:
                    # Create element_id from resource_id or class
                    resource_id = item.view.get("resource_id", "")
                    element_class = item.view.get("class", "unknown")
                    element_id = resource_id if resource_id else f"class:{element_class}"

                    # CORRECT: use record_interaction (not record_element_seen)
                    ui_coverage.record_interaction(
                        element_id=element_id,
                        action_type="view",  # Just viewing the element
                        screen_hash=current_screen,
                        success=True
                    )
                logger.debug(f"   Updated UI coverage: {len(screen_desc.items)} elements")

            # Update LongTermMemory - CORRECTED API
            if long_term and screen_desc:
                # CORRECT: use record_state to track state visits
                long_term.record_state(
                    state_hash=current_screen,
                    activity=current_activity,
                    interactive_elements_count=len(screen_desc.items)
                )
                logger.debug(f"   Updated LongTermMemory: state {current_screen[:8]}")

        except Exception as e:
            logger.error(f"Memory update failed: {e}", exc_info=True)

        # Check if should continue (timeout checked in external loop)
        elapsed = time.time() - state["start_time"]
        should_continue = elapsed < state["timeout"]

        logger.info(f"   Memory systems updated, should_continue={should_continue}")

        return {"should_continue": should_continue}

    def _load_and_optimize_screenshot(self, screenshot_path: str) -> str:
        """Load and optimize screenshot to base64."""
        # Check if screenshot_path is already a base64 string (mock mode)
        # MockDeviceInterface returns base64 directly, not a file path
        if not os.path.exists(screenshot_path):
            # Already base64, return as-is
            logger.debug(f"Screenshot path is base64 string (mock mode), returning as-is")
            return screenshot_path

        try:
            # Try to optimize (real device mode with actual file path)
            optimized_path = self.screenshot_optimizer.optimize(
                image_path=screenshot_path,
                target_size=self.config.optimized_dimensions,
                quality=90
            )

            # Read optimized file
            with open(optimized_path, 'rb') as f:
                img_data = f.read()

            return base64.b64encode(img_data).decode('utf-8')

        except Exception as e:
            # Fallback: read original file
            logger.warning(f"Optimization failed: {e}, using original screenshot")
            with open(screenshot_path, 'rb') as f:
                img_data = f.read()

            return base64.b64encode(img_data).decode('utf-8')

    def run(self) -> Dict[str, Any]:
        """
        Execute agent with external timeout loop.

        Returns:
            Metrics dictionary with exploration results
        """
        logger.info("Starting RVAgent execution (STATELESS)")

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

        # Initialize state with EMPTY summaries
        state = {
            "action_history_summary": "No previous actions.",
            "exploration_summary": "Starting exploration.",
            "memory_insights": "No insights yet.",
            "navigation_path": "Starting navigation.",
            "iteration": 0,
            "should_continue": True,
            "start_time": start_time,
            "timeout": self.config.timeout,
            "strategy_name": self.config.strategy,
            "visited_states": set(),
            "state_transitions": {},
            "device_dimensions": self.config.device_dimensions,
            "optimized_dimensions": self.config.optimized_dimensions,
            "external_navigation_count": 0,
            "is_external": False,
            "llm_tokens_input": 0,
            "llm_tokens_output": 0,
            "llm_time_ms": 0.0,
            # Injected dependencies
            "_device": self.device,
            "_parser": self.parser,
            "_static_data": self.static_data,
            "_strategy": self.strategy,
            "_long_term": self.long_term,
            "_short_term": self.short_term,
            "_ui_coverage": self.ui_coverage,
            "_graph": self.dynamic_graph,
            "_converter": self.converter,
            "_package_name": self.config.package_name
        }

        # External loop
        try:
            while True:
                elapsed = time.time() - start_time

                if elapsed >= self.config.timeout:
                    logger.info(f"🏁 Timeout reached ({elapsed:.1f}s)")
                    break

                logger.info(f"⏱️  Iteration {iteration} (elapsed: {elapsed:.1f}s)")

                state["iteration"] = iteration

                # Invoke graph for ONE iteration
                result = self.graph.invoke(state)

                # Update state with results
                state.update(result)

                iteration += 1
                time.sleep(0.5)  # Brief pause between iterations

        except KeyboardInterrupt:
            logger.info("⚠️  Interrupted by user")
        except Exception as e:
            logger.error(f"❌ Execution error: {e}", exc_info=True)

        # Return metrics
        execution_time = time.time() - start_time

        return {
            "status": "completed",
            "iterations": iteration,
            "execution_time_s": execution_time,
            "unique_states": len(state["visited_states"]),
            "total_transitions": len(state["state_transitions"])
        }

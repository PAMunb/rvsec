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
from langgraph.prebuilt import tools_condition
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

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
from rv_agent.llm.tools import json_parser  # JSON parser for vision+tools responses

# Import versioned prompts - CHANGE HERE TO SWITCH VERSIONS
from rv_agent.prompts import v10 as current_prompt  # v10 = simplified for smaller vision models (qwen3-vl:4b)

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

        # Import and create Android tools
        from rv_agent.llm.tools.android_tools import (
            create_android_tools,
            set_device_interface,
            set_coordinate_converter
        )

        self.tools = create_android_tools()
        logger.info(f"Android tools created: {len(self.tools)} tools")

        # Initialize tools with device and converter
        set_device_interface(self.device)
        set_coordinate_converter(self.converter)
        logger.info("Tools initialized with device interface and coordinate converter")

        # Create LLM instance with tool calling
        llm_config = config.get_langchain_config()
        llm_base = ChatOllama(
            model=llm_config['model'],  # Use model from config
            temperature=llm_config['temperature'],
            top_p=llm_config.get('top_p', 0.8),
            top_k=llm_config.get('top_k', 50),
            base_url=llm_config.get('base_url', 'http://localhost:11434'),
            timeout=60.0,
            request_timeout=60.0
        )

        # Bind tools to LLM
        self.llm = llm_base.bind_tools(self.tools)

        logger.info("LLM configured with tool calling support")

        # LangGraph workflow (simplified for stateless)
        self.graph = self._build_agent_graph()

        # External loop state (persisted between graph invocations)
        self.external_navigation_count = 0

        logger.info("RVAgent initialized successfully (STATELESS)")

    def _build_agent_graph(self):
        """
        Build LangGraph workflow with retry logic.

        Flow:
        observe → assistant → [tools_condition]
                            ↓                ↓
                         tools              learn (no tools)
                            ↓
                      validate_action
                            ↓
                     [retry_decision]
                ↓           ↓            ↓
          update_params  update_mem  max_retries
               ↓             ↓            ↓
           assistant       learn        learn

        Workflow:
        - Uses builtin tools_condition from langgraph.prebuilt
        - Adds retry loop with progressive sampling (temperature, top_p, top_k)
        - validate_action node checks if tools were executed
        - retry_decision routes based on success/failure
        - update_sampling_params increases creativity on retry

        Returns:
            Compiled LangGraph workflow
        """
        logger.info("Building LangGraph workflow with retry logic")

        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("observe", self._observe_node)
        workflow.add_node("assistant", self._assistant_node)
        workflow.add_node("tools", self._execute_tools_node)  # Custom tool executor
        workflow.add_node("validate_action", self._validate_action_node)  # V7
        workflow.add_node("update_sampling", self._update_sampling_params_node)  # V7
        workflow.add_node("update_memories", self._update_memories_node)
        workflow.add_node("learn", self._learn_node)
        workflow.add_node("handle_max_retries", self._handle_max_retries_node)  # V7

        # Flow
        workflow.set_entry_point("observe")
        workflow.add_edge("observe", "assistant")

        # Use builtin tools_condition 
        workflow.add_conditional_edges(
            "assistant",
            tools_condition,  # Builtin from langgraph.prebuilt
        )

        # Validate action after tool execution 
        workflow.add_edge("tools", "validate_action")

        # Retry decision based on validation 
        workflow.add_conditional_edges(
            "validate_action",
            self._retry_decision,
            {
                "success": "update_memories",      # Success → continue
                "retry": "update_sampling",         # Retry with higher creativity
                "max_retries": "handle_max_retries"  # Give up → fallback
            }
        )

        # Retry loop: update_sampling → assistant (try again)
        workflow.add_edge("update_sampling", "assistant")

        # Normal continuation
        workflow.add_edge("update_memories", "learn")
        workflow.add_edge("handle_max_retries", "learn")
        workflow.add_edge("learn", END)

        logger.info("LangGraph workflow compiled with retry logic")
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

            # Don't clear messages - let them flow naturally for tool calling
            # Messages accumulate within a single graph invocation
            # External loop creates fresh state for each iteration
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
        Generate action using LLM with tool calling (Current: progressive sampling).

        LLM analyzes current screen and decides which tool to call.
        Uses sampling parameters from state for progressive creativity across retries.

        Returns:
            Updated state with messages and token metrics
        """
        # Get sampling parameters from state (retry logic)
        temperature = state.get("sampling_temperature", 0.1)
        top_p = state.get("sampling_top_p", 0.9)
        top_k = state.get("sampling_top_k", 40)
        retry_count = state.get("retry_count", 0)

        logger.info(f"🤖 ASSISTANT: Generating action (retry={retry_count}, temp={temperature}, top_p={top_p}, top_k={top_k})")

        start_time = time.time()

        try:
            # Build fresh messages from summaries ( separate roles)
            messages = self._build_stateless_message(state)

            logger.info("   Messages constructed with screenshot + UI coordinates")
            logger.info(f"   Using {len(messages)} messages (SystemMessage + HumanMessage)")

            # Get existing messages from state (for ToolNode compatibility)
            existing_messages = state.get("messages", [])

            # LLM invocation with dynamic sampling parameters 
            # Pass parameters directly to invoke() (Ollama-specific approach)
            response = self.llm.invoke(
                messages,  #  Use list of messages directly
                config={
                    "configurable": {
                        "temperature": temperature,
                        "top_p": top_p,
                        "top_k": top_k
                    }
                }
            )

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

            # Log tool calls (native or parsed from JSON/XML)
            if hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info(f"   ✅ Native tool calls: {len(response.tool_calls)}")
                for tc in response.tool_calls:
                    logger.info(f"     - {tc['name']} with args: {tc['args']}")
            else:
                logger.warning("   ⚠️  No native tool calls - attempting JSON/XML parsing...")
                # Parse tool calls from text response (qwen-vision-tools-v2 returns XML)
                parsed_calls = json_parser.parse_tool_calls_from_text(response.content)
                if parsed_calls:
                    logger.info(f"   ✅ Parsed {len(parsed_calls)} tool calls from text")
                    # Convert parsed calls to LangChain format and inject into response
                    response.tool_calls = [
                        {
                            'name': tc['name'],
                            'args': tc['args'],
                            'id': f"call_{i}",
                            'type': 'tool_call'
                        }
                        for i, tc in enumerate(parsed_calls)
                    ]
                    for tc in response.tool_calls:
                        logger.info(f"     - {tc['name']} with args: {tc['args']}")
                else:
                    logger.warning("   ❌ No tool calls found in text either")

            logger.info(f"   LLM Response: {llm_time_ms:.1f}ms, "
                       f"tokens: {llm_tokens_input} in / {llm_tokens_output} out")

            # Log complete response content for debugging (first 500 chars)
            response_preview = response.content[:500] if response.content else "<empty>"
            logger.debug(f"📤 LLM Response Content (first 500 chars):\n{response_preview}")
            if len(response.content) > 500:
                logger.debug(f"   ... (total {len(response.content)} chars)")

            # Accumulate messages (system + user + AI response) for ToolNode compatibility
            # Messages will be cleared on next observe_node iteration
            #  messages is already a list [SystemMessage, HumanMessage]
            updated_messages = existing_messages + messages + [response]

            logger.info(f"🔧 ASSISTANT RETURN: Returning {len(updated_messages)} messages to state")
            logger.info(f"   - existing: {len(existing_messages)}, adding: {len(messages) + 1} (system + user + AI)")

            return {
                "messages": updated_messages,
                "llm_tokens_input": llm_tokens_input,
                "llm_tokens_output": llm_tokens_output,
                "llm_time_ms": llm_time_ms
            }

        except Exception as e:
            logger.error(f"❌ Assistant failed: {e}", exc_info=True)
            # Return empty response (will trigger fallback in update_memories)
            return {
                "messages": [],
                "llm_tokens_input": 0,
                "llm_tokens_output": 0,
                "llm_time_ms": (time.time() - start_time) * 1000
            }

    def _build_stateless_message(self, state: AgentState) -> list:
        """
        Build fresh messages with SIMPLIFIED V10 prompt and SEPARATE ROLES.

        V10 minimal context approach:
        - Simple system prompt (no complex instructions)
        - Only UI elements formatted by _format_ui_elements
        - Minimal action history (last action only)
        - NO exploration metrics, memory insights, or navigation paths
        - SEPARATED ROLES: SystemMessage + HumanMessage (like working test)

        This reduces prompt complexity to prevent overloading smaller vision models.

        Returns:
            List of [SystemMessage, HumanMessage] with simplified context
        """
        # Get simple system prompt from V10
        system_text = current_prompt.SYSTEM_PROMPT

        # Format UI elements using existing method
        ui_elements_text = self._format_ui_elements(state['screen_description'])

        # Build minimal user message from V10 - only iteration, last action, and UI elements
        state_info = {
            'ui_elements': [ui_elements_text],  # Wrap in list as expected by v10.build_user_message
            'last_action': state.get('last_action_summary', None),
            'iteration': state.get('iteration', 0)
        }
        user_text = current_prompt.build_user_message(state_info)

        # DEBUG: Log full prompt on iteration 2
        iteration = state.get("iteration", 0)
        if iteration == 1:  # iteration 2 (0-indexed)
            full_prompt = f"{system_text}\n\n{user_text}"
            logger.info(f"\n{'='*80}\nFULL PROMPT (Iteration 2):\n{'='*80}\n{full_prompt}\n{'='*80}")

        #  Separate roles like successful test
        system_message = SystemMessage(content=system_text)

        # Build multimodal human message
        human_message = HumanMessage(content=[
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {
                "url": f"data:image/png;base64,{state['screenshot_b64']}"
            }}
        ])

        return [system_message, human_message]

    def _format_ui_elements(self, screen_description) -> str:
        """
        Format UI elements with explicit coordinates for vision model.

        V8.1: Separates elements into three categories to guide tool selection:
        1. Text Input Fields (EditText) - MUST use android_type_text
        2. Dropdown Selectors (Spinner) - use android_click to open, then select
        3. Clickable Elements (Buttons, Images, etc) - use android_click

        CRITICAL: All coordinates are transformed to optimized space before
        being shown to the LLM, so LLM generates coordinates that android_tools can validate.
        """
        if not screen_description or not screen_description.items:
            return "No interactive elements found."

        # V8.1: Separate elements by category
        text_inputs = []  # EditText - MUST type
        spinners = []  # Spinner - click to open dropdown
        clickable_items = []  # Everything else - click normally

        for item in screen_description.items:
            if not item.view.get('clickable', False):
                continue  # Skip non-clickable

            elem_class = item.view.get('class', '')
            if 'EditText' in elem_class or 'AutoCompleteTextView' in elem_class:
                text_inputs.append(item)
            elif 'Spinner' in elem_class:
                spinners.append(item)
            else:
                clickable_items.append(item)

        # Check if we have any elements
        if not text_inputs and not spinners and not clickable_items:
            return "No interactive elements found."

        lines = []

        # SECTION 1: Text Input Fields (highest priority for forms)
        if text_inputs:
            lines.extend([
                "=== TEXT INPUT FIELDS ===",
                "⚠️ IMPORTANT: Use android_type_text() tool for these elements, NOT android_click()!",
                ""
            ])
            for i, item in enumerate(text_inputs[:5], 1):  # Limit to 5
                desc = self._format_element_desc(i, item, "TEXT INPUT")
                if desc:
                    lines.append(desc)
            lines.append("")

        # SECTION 2: Dropdown Selectors
        if spinners:
            lines.extend([
                "=== DROPDOWN SELECTORS ===",
                "ℹ️ Use android_click() to open dropdown, then select option in next iteration",
                ""
            ])
            for i, item in enumerate(spinners[:5], 1):  # Limit to 5
                desc = self._format_element_desc(i, item, "DROPDOWN")
                if desc:
                    lines.append(desc)
            lines.append("")

        # SECTION 3: Clickable Elements
        if clickable_items:
            lines.extend([
                "=== CLICKABLE ELEMENTS ===",
                "Use android_click() for buttons, images, checkboxes, switches, icons",
                ""
            ])
            for i, item in enumerate(clickable_items[:10], 1):  # Limit to 10
                desc = self._format_element_desc(i, item, None)
                if desc:
                    lines.append(desc)
            lines.append("")

        # Show optimized dimensions
        opt_width = self.converter.optimized_width
        opt_height = self.converter.optimized_height
        lines.extend([
            f"Screen resolution: {opt_width}x{opt_height} pixels",
            "Use EXACT coordinates from 'at position (x, y)' for tool calls"
        ])

        ui_text = "\n".join(lines)

        # V8.1: Enhanced logging
        total_count = len(screen_description.items)
        logger.debug(
            f"UI description: {total_count} total, "
            f"{len(text_inputs)} text inputs, "
            f"{len(spinners)} spinners, "
            f"{len(clickable_items)} clickable"
        )

        if text_inputs:
            logger.info(f"✏️ {len(text_inputs)} text input field(s) detected - must use android_type_text")
        if spinners:
            logger.info(f"🔽 {len(spinners)} spinner(s) detected - click to open dropdown")

        return ui_text

    def _format_element_desc(self, index: int, item, category_label: str = None) -> str:
        """
        Format single element description with optimized coordinates.

        Args:
            index: Element index in list
            item: ScreenItem to format
            category_label: Optional label to prepend (e.g., "TEXT INPUT", "DROPDOWN")

        Returns:
            Formatted element description or empty string if invalid bounds
        """
        elem_type = item.view.get('class', 'View').split('.')[-1]
        text = item.view.get('text', '')
        resource_id = item.view.get('resource_id', '').split('/')[-1]
        bounds = item.view.get('bounds')

        # Calculate center coordinates IN DEVICE SPACE
        if not (bounds and len(bounds) == 2 and len(bounds[0]) == 2 and len(bounds[1]) == 2):
            logger.debug(f"Element {index} has invalid bounds: {bounds}")
            return ""

        device_center_x = (bounds[0][0] + bounds[1][0]) // 2
        device_center_y = (bounds[0][1] + bounds[1][1]) // 2

        # CRITICAL: Transform to optimized space for LLM
        optimized_center_x, optimized_center_y = self.converter.device_to_optimized(
            device_center_x, device_center_y
        )

        # Transform bounds to optimized space
        opt_x1, opt_y1 = self.converter.device_to_optimized(bounds[0][0], bounds[0][1])
        opt_x2, opt_y2 = self.converter.device_to_optimized(bounds[1][0], bounds[1][1])
        optimized_bounds = [[opt_x1, opt_y1], [opt_x2, opt_y2]]

        # Build description
        desc_parts = [f"{index}."]
        if category_label:
            desc_parts.append(f"[{category_label}]")
        desc_parts.append(elem_type)

        if text:
            desc_parts.append(f"'{text}'")
        if resource_id:
            desc_parts.append(f"({resource_id})")

        desc = " ".join(desc_parts)
        desc += f" at position ({optimized_center_x}, {optimized_center_y}) - bounds{optimized_bounds}"

        # Add available actions and MOP markers
        if hasattr(item, 'actions') and item.actions:
            actions_text = ", ".join(action.text for action in item.actions if hasattr(action, 'text'))
            if actions_text:
                desc += f". Actions: {actions_text}"

            action = item.actions[0]
            if action.directly_reaches_mop:
                desc += " [DM]"
            elif action.reaches_mop:
                desc += " [M]"

        return desc

    def _find_item_by_coords(self, coords: tuple, screen_desc, tolerance: int = 20):
        """
        Map coordinates to ScreenItem with fuzzy bounds matching.

        Supports hybrid validation:
        - DOM elements: Match via bounds intersection
        - Non-DOM elements (canvas, games): Return None but coords still valid

        Args:
            coords: (x, y) tuple in device space
            screen_desc: ScreenDescription object
            tolerance: Pixel tolerance for bounds matching

        Returns:
            ScreenItem if DOM element found, None otherwise

        Note: None result does NOT mean invalid action. Vision model can
        identify interactive elements not present in DOM (games, canvas, etc).
        """
        x, y = coords

        for item in screen_desc.items:
            bounds = item.view.get('bounds')
            if not bounds or len(bounds) != 2:
                continue

            [[x1, y1], [x2, y2]] = bounds

            # Check if coords within bounds (with tolerance)
            if (x1 - tolerance <= x <= x2 + tolerance) and \
               (y1 - tolerance <= y <= y2 + tolerance):
                return item

        return None  # Not DOM element (possibly canvas/game element)

    # =============================================================================
    # V7 RETRY LOGIC NODES - Progressive Creativity
    # =============================================================================

    def _validate_action_node(self, state: AgentState) -> AgentState:
        """
        Validate if tools were executed (V7 retry mechanism).

        Decision node that checks if tool execution occurred.
        This allows retry logic to detect when NO tools were called.

        Returns:
            Updated state with validation status
        """
        from langchain_core.messages import ToolMessage

        logger.info("🔍 VALIDATE_ACTION: Checking tool execution")

        messages = state.get("messages", [])
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]

        if not tool_messages:
            logger.warning("   ❌ No tool messages found - NO ACTION EXECUTED")
            return {
                "last_action_success": False,
                "retry_reason": "no_tool_executed"
            }

        # Tool was executed - check if successful
        last_tool = tool_messages[-1]
        success = "success" in str(last_tool.content).lower()

        if success:
            logger.info("   ✅ Tool executed successfully")
            return {
                "last_action_success": True,
                "retry_reason": "",
                "retry_count": 0  # Reset retry count on success
            }
        else:
            logger.warning("   ⚠️  Tool executed but failed")
            return {
                "last_action_success": False,
                "retry_reason": "tool_execution_failed"
            }

    def _retry_decision(self, state: AgentState) -> str:
        """
        Routing function for retry logic .

        Decides whether to retry with higher creativity or proceed.

        Returns:
            "success" - Continue to update_memories
            "retry" - Retry with increased sampling params
            "max_retries" - Give up, use fallback
        """
        logger.info("🔀 RETRY_DECISION: Evaluating retry strategy")

        success = state.get("last_action_success", False)
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)

        if success:
            logger.info("   ✅ Action successful → continue")
            return "success"

        if retry_count >= max_retries:
            logger.warning(f"   🛑 Max retries ({max_retries}) reached → fallback")
            return "max_retries"

        logger.info(f"   🔄 Retry {retry_count + 1}/{max_retries} with higher creativity")
        return "retry"

    def _update_sampling_params_node(self, state: AgentState) -> AgentState:
        """
        Update sampling parameters for progressive creativity .

        Increases temperature, top_p, top_k progressively across retries.

        Returns:
            Updated state with increased sampling parameters
        """
        retry_count = state.get("retry_count", 0) + 1

        # Progressive temperature: 0.1 → 0.5 → 0.9
        temperature_levels = [0.1, 0.5, 0.9]
        # Progressive top_p: 0.9 → 0.95 → 0.99
        top_p_levels = [0.9, 0.95, 0.99]
        # Progressive top_k: 40 → 50 → 60
        top_k_levels = [40, 50, 60]

        idx = min(retry_count, len(temperature_levels) - 1)

        new_temperature = temperature_levels[idx]
        new_top_p = top_p_levels[idx]
        new_top_k = top_k_levels[idx]

        logger.info(f"📈 UPDATE_SAMPLING: Retry {retry_count}")
        logger.info(f"   Temperature: {new_temperature}")
        logger.info(f"   Top-p: {new_top_p}")
        logger.info(f"   Top-k: {new_top_k}")

        return {
            "retry_count": retry_count,
            "sampling_temperature": new_temperature,
            "sampling_top_p": new_top_p,
            "sampling_top_k": new_top_k,
            "messages": []  # Clear messages for clean retry
        }

    def _handle_max_retries_node(self, state: AgentState) -> AgentState:
        """
        Handle max retries reached - fallback behavior .

        Creates fallback BACK action when all retries exhausted.

        Returns:
            Updated state with fallback action
        """
        logger.warning("⚠️  HANDLE_MAX_RETRIES: Fallback behavior triggered")

        retry_reason = state.get("retry_reason", "unknown")
        retry_count = state.get("retry_count", 0)

        logger.warning(f"   Reason: {retry_reason}")
        logger.warning(f"   Retries attempted: {retry_count}")

        # Fallback: create BACK action
        fallback_action = {
            "action_type": "BACK",
            "explanation": f"Max retries ({retry_count}) reached: {retry_reason}"
        }

        # Record in memory (will be processed in update_memories)
        # This ensures fallback action is tracked like any other action

        return {
            "current_action": fallback_action,
            "retry_count": 0,  # Reset for next iteration
            "last_action_success": True  # Prevent further retries
        }

    # =============================================================================
    # END V7 RETRY LOGIC NODES
    # =============================================================================

    def _execute_tools_node(self, state: AgentState) -> AgentState:
        """
        Custom tool executor for stateless architecture.

        Extracts tool calls from last message and executes them directly,
        without relying on LangGraph's ToolNode which expects message accumulation.

        Args:
            state: Current agent state with messages

        Returns:
            Updated state with tool execution results and action coordinates
        """
        from langchain_core.messages import ToolMessage

        logger.info("🔧 TOOLS: Executing tool calls")

        messages = state.get("messages", [])
        if not messages:
            logger.warning("   No messages in state for tool execution")
            return state

        last_message = messages[-1]

        # Extract tool calls from AI message
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            logger.warning("   No tool calls found in last message")
            return state

        tool_calls = last_message.tool_calls
        logger.info(f"   Executing {len(tool_calls)} tool call(s)")

        # Execute each tool call
        tool_results = []
        executed_action = None  # Track action for state update

        for tool_call in tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            tool_id = tool_call['id']

            logger.info(f"   - Tool: {tool_name}")
            logger.info(f"     Args: {tool_args}")

            # Find tool by name
            tool = next((t for t in self.tools if t.name == tool_name), None)

            if not tool:
                error_msg = f"Tool '{tool_name}' not found"
                logger.error(f"     ERROR: {error_msg}")
                tool_results.append(ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_id
                ))
                continue

            # Execute tool
            try:
                result = tool.invoke(tool_args)
                logger.info(f"     Result: {result}")

                # Create ToolMessage with result
                tool_results.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id
                ))

                # Extract action coordinates for state
                # Action tools (android_click, android_type_text, etc.) return success/error strings
                # We need to extract x, y from tool_args for memory updates
                if tool_name.startswith('android_') and 'x' in tool_args and 'y' in tool_args:
                    executed_action = {
                        'tool_name': tool_name,
                        'x': tool_args['x'],
                        'y': tool_args['y'],
                        'element_description': tool_args.get('element_description', ''),
                        'text': tool_args.get('text', None)  # For android_type_text
                    }

            except Exception as e:
                error_msg = f"Tool execution failed: {str(e)}"
                logger.error(f"     ERROR: {error_msg}", exc_info=True)
                tool_results.append(ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_id
                ))

        # Update state with tool results
        updated_messages = messages + tool_results

        # Update current_action for memory systems
        result = {
            "messages": updated_messages
        }

        if executed_action:
            result["current_action"] = executed_action
            logger.info(f"   Action executed: {executed_action['tool_name']} at ({executed_action['x']}, {executed_action['y']})")

        return result

    def _update_memories_node(self, state: AgentState) -> AgentState:
        """
        Process tool execution results and update memory systems.

        Extracts tool results from ToolMessages created by ToolNode,
        maps coordinates to screen items when possible, and updates
        all memory systems with the executed action.

        Supports hybrid action validation:
        - DOM elements: Validate via screen_desc matching
        - Non-DOM elements: Accept coordinates as-is (vision model decision)

        Returns:
            Updated state with memory summaries
        """
        logger.info("🔄 UPDATE_MEMORIES: Processing tool results")

        messages = state.get("messages", [])
        from langchain_core.messages import ToolMessage

        # Extract tool messages (results from ToolNode execution)
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]

        if not tool_messages:
            logger.warning("   No tool messages found, using fallback BACK action")
            # Fallback: create BACK action
            action = {"action_type": "BACK", "explanation": "No tool calls"}
            self.memory_manager.record_action(action, state["current_activity"], False)
        else:
            for tool_msg in tool_messages:
                logger.info(f"   Processing tool result: {tool_msg.name}")

                # Extract tool call info from state messages
                # ToolNode creates ToolMessage with tool_call_id linking back to original call
                ai_messages = [m for m in messages if hasattr(m, 'tool_calls')]

                if ai_messages and ai_messages[-1].tool_calls:
                    for tool_call in ai_messages[-1].tool_calls:
                        tool_name = tool_call['name']
                        tool_args = tool_call['args']

                        logger.info(f"   Tool: {tool_name}, Args: {tool_args}")

                        # Map coordinates to ScreenItem (optional, for logging)
                        coords = (tool_args.get('x', 0), tool_args.get('y', 0))
                        screen_item = self._find_item_by_coords(
                            coords,
                            state['screen_description']
                        )

                        if screen_item:
                            logger.info(f"   DOM element matched: {screen_item.view.get('resource_id', 'unknown')}")
                        else:
                            logger.info(f"   Non-DOM element (visual): coords {coords}")

                        # Create action record for memory
                        action = {
                            "action_type": tool_name.replace('android_', '').upper(),
                            "coords": coords,
                            "element_description": tool_args.get('element_description', ''),
                            "text": tool_args.get('text', ''),
                            "explanation": f"Tool call: {tool_name}"
                        }

                        # Record in memory manager
                        success = "success" in str(tool_msg.content).lower() and "true" in str(tool_msg.content).lower()
                        self.memory_manager.record_action(
                            action,
                            state["current_activity"],
                            success
                        )

                        logger.info(f"   Action recorded: {action['action_type']}, success={success}")

        # Generate NEW summaries
        action_history_summary = self.memory_manager.get_action_history_summary()
        exploration_summary = self.memory_manager.get_exploration_summary(
            state["visited_states"],
            state["state_transitions"]
        )
        memory_insights = self.memory_manager.get_memory_insights(state["current_activity"])
        navigation_path = self.memory_manager.get_navigation_path()

        return {
            "action_history_summary": action_history_summary,
            "exploration_summary": exploration_summary,
            "memory_insights": memory_insights,
            "navigation_path": navigation_path
        }

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

        # Generate memory summaries for next iteration (stateless context)
        try:
            # Record action in memory_manager
            if action:
                self.memory_manager.record_action(
                    action=action,
                    activity=current_activity,
                    success=True  # TODO: Track action success from validation
                )
                logger.debug(f"   Recorded action in AgentMemoryManager")

            # Generate all summaries
            action_history_summary = self.memory_manager.get_action_history_summary()
            exploration_summary = self.memory_manager.get_exploration_summary(
                visited_states=state.get("visited_states", []),
                state_transitions=state.get("state_transitions", [])
            )
            memory_insights = self.memory_manager.get_memory_insights(current_activity)
            navigation_path = self.memory_manager.get_navigation_path()

            logger.info(f"   Memory summaries generated for next iteration")

        except Exception as e:
            logger.error(f"Summary generation failed: {e}", exc_info=True)
            # Fallback to default summaries
            action_history_summary = "No previous actions."
            exploration_summary = "Starting exploration."
            memory_insights = "No insights yet."
            navigation_path = "Starting navigation."

        # Track state discovery and transitions
        current_hash = state.get("current_screen_hash")
        prev_hash = state.get("previous_screen_hash")
        visited = state.get("visited_states", [])
        transitions = state.get("state_transitions", [])

        # Add current state to visited if not already present
        if current_hash and current_hash not in visited:
            visited.append(current_hash)
            logger.debug(f"   New state discovered: {current_hash[:12]}...")

        # Record transition if state changed
        logger.debug(f"   TRANSITION CHECK: prev={prev_hash[:12] if prev_hash else None}, current={current_hash[:12] if current_hash else None}, different={prev_hash != current_hash if (prev_hash and current_hash) else 'N/A'}")
        if prev_hash and current_hash and prev_hash != current_hash:
            transition = (prev_hash, current_hash)
            if transition not in transitions:
                transitions.append(transition)
                logger.debug(f"   New transition: {prev_hash[:8]}... → {current_hash[:8]}...")

        # Check if should continue (timeout checked in external loop)
        elapsed = time.time() - state["start_time"]
        should_continue = elapsed < state["timeout"]

        logger.info(f"   Memory systems updated, should_continue={should_continue}")
        logger.info(f"   States discovered: {len(visited)}, Transitions: {len(transitions)}")

        # Return summaries and tracking data for next iteration
        return {
            "should_continue": should_continue,
            "action_history_summary": action_history_summary,
            "exploration_summary": exploration_summary,
            "memory_insights": memory_insights,
            "navigation_path": navigation_path,
            "visited_states": visited,
            "state_transitions": transitions,
            "previous_screen_hash": current_hash
        }

    def _load_and_optimize_screenshot(self, screenshot_path: str) -> str:
        """Load and optimize screenshot to base64."""
        # Check if screenshot_path is already a base64 string (mock mode)
        # MockDeviceInterface returns base64 directly, not a file path
        if not os.path.exists(screenshot_path):
            # Already base64, return as-is
            logger.debug(f"Screenshot path is base64 string (mock mode), returning as-is")
            return screenshot_path

        try:
            # FIX: screenshot_optimizer.optimize() returns base64 string directly, not a file path
            # Previously this was incorrectly treated as a file path and tried to open() it
            # causing "[Errno 36] File name too long" error
            optimized_b64 = self.screenshot_optimizer.optimize(
                image_path=screenshot_path,
                target_size=self.config.optimized_dimensions,
                quality=90
            )

            # optimize() can return None if it fails
            if optimized_b64:
                logger.debug(f"Screenshot optimized successfully (base64 length: {len(optimized_b64)})")
                return optimized_b64

            # If optimize returned None, fall through to exception handler
            raise Exception("Optimization returned None")

        except Exception as e:
            # Fallback: read original file and encode to base64
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

        # Initialize state with empty summaries and tracking structures
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
            "visited_states": [],
            "state_transitions": [],
            "previous_screen_hash": None,
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
            "_package_name": self.config.package_name,
            # Retry mechanism
            "retry_count": 0,
            "max_retries": 2,
            "last_action_success": True,
            "retry_reason": "",
            # Sampling parameters
            "sampling_temperature": 0.1,
            "sampling_top_p": 0.9,
            "sampling_top_k": 40,
            # Messages for tool calling
            "messages": []
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

                # Reset retry mechanism for new iteration 
                state["retry_count"] = 0
                state["last_action_success"] = True
                state["retry_reason"] = ""
                state["sampling_temperature"] = 0.1
                state["sampling_top_p"] = 0.9
                state["sampling_top_k"] = 40
                state["messages"] = []  # Clear messages for stateless context

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

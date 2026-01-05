"""
LangChain Service for RVAgent - Native tool-calling implementation.

EXACT implementation following the plan with LangChain AgentExecutor + ReAct pattern.
Uses native tool-calling instead of prompt engineering + JSON parsing.
"""

import time
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional

from langchain_ollama import ChatOllama
from langchain.agents import create_tool_calling_agent, AgentExecutor

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler

from ..constants import RVAgentConstants
from .simple_tools import create_android_tools


def encode_image_to_base64(image_path: str) -> Optional[str]:
    """
    Encode image file to base64 string for vision model input.

    Args:
        image_path: Path to image file

    Returns:
        Base64 encoded string or None if failed
    """
    try:
        if not Path(image_path).exists():
            return None

        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            return encoded_string

    except Exception as e:
        print(f"[TEST_LOG_VISION] ❌ Image encoding failed: {e}")
        return None


class LangChainService:
    """
    LangChain service for RVAgent with native tool-calling.

    SUBPROCESS ISOLATED PROCESS:
    - LoggingManager.get_instance() with own subprocess instance
    - ErrorHandler.get_instance() with own subprocess instance
    - LangChain AgentExecutor with ReAct pattern
    - Native tool-calling (no JSON parsing)
    - Phase 0 parameters: temp=0.25, top_p=0.8, top_k=50

    DIFFERENTIATOR: Uses LangChain native tool-calling vs prompt engineering
    """

    def __init__(self, device_adapter, model_name: str = RVAgentConstants.DEFAULT_MODEL):
        """Initialize LangChain service with tool-calling agent."""

        # Process isolation - LoggingManager with own instance
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.llm.langchain_service",
            {"component": "LangChainService"}
        )

        # ErrorHandler decorators available in subprocess
        self.error_handler = ErrorHandler.get_instance()

        self.model_name = model_name
        self.device_adapter = device_adapter

        # Initialize LangChain tools using simple approach
        self.tools = create_android_tools(device_adapter)

        # Initialize LLM and agent
        self.llm = None
        self.agent_executor = None
        self._initialize_llm()
        self._initialize_agent()

        self.logger.info(f"[RVAGENT_DEBUG] LangChainService initialized with tool-calling: {model_name}")

    def _initialize_llm(self) -> None:
        """Initialize LLM with Phase 0 validated parameters."""
        try:
            self.logger.info(f"[RVAGENT_DEBUG] Initializing LLM with {self.model_name}...")
            print(f"[TEST_LOG_MODEL] 🧠 Starting LLM initialization: {self.model_name}")

            if self.model_name.startswith("claude"):
                # Claude configuration (ready for future tests)
                print(f"[TEST_LOG_MODEL] 🔧 Using Claude configuration")
                if not ANTHROPIC_AVAILABLE:
                    raise ImportError("langchain-anthropic not installed. Install with: pip install langchain-anthropic")

                self.llm = ChatAnthropic(
                    model=self.model_name,
                    temperature=RVAgentConstants.DEFAULT_TEMPERATURE,
                    max_tokens=RVAgentConstants.DEFAULT_MAX_TOKENS,
                    # top_p=RVAgentConstants.DEFAULT_TOP_P,  # Claude uses different params
                )
                self.logger.info("[RVAGENT_DEBUG] ✅ Claude LLM initialized")
                print(f"[TEST_LOG_MODEL] ✅ Claude LLM object created: {type(self.llm)}")
            else:
                # Ollama configuration (main focus)
                print(f"[TEST_LOG_MODEL] 🔧 Using Ollama configuration")
                print(f"[TEST_LOG_MODEL] Parameters: temp={RVAgentConstants.DEFAULT_TEMPERATURE}, top_p={RVAgentConstants.DEFAULT_TOP_P}, top_k={RVAgentConstants.DEFAULT_TOP_K}")

                self.llm = ChatOllama(
                    model=self.model_name,
                    temperature=RVAgentConstants.DEFAULT_TEMPERATURE,  # 0.25
                    top_p=RVAgentConstants.DEFAULT_TOP_P,              # 0.8
                    top_k=RVAgentConstants.DEFAULT_TOP_K,              # 50
                    num_predict=RVAgentConstants.DEFAULT_MAX_TOKENS,   # 800
                    base_url="http://localhost:11434"
                )
                self.logger.info("[RVAGENT_DEBUG] ✅ Ollama LLM initialized")
                print(f"[TEST_LOG_MODEL] ✅ Ollama LLM object created: {type(self.llm)}")
                print(f"[TEST_LOG_MODEL] 🌐 Base URL: http://localhost:11434")

            # Test LLM connection immediately
            print(f"[TEST_LOG_MODEL] 🔍 Testing LLM connection...")
            test_response = self.llm.invoke("Test connection. Respond with: Hello from RVAgent")
            print(f"[TEST_LOG_MODEL] ✅ LLM connection test response: {test_response}")

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] LLM initialization failed: {e}")
            print(f"[TEST_LOG_MODEL] ❌ LLM initialization failed: {e}")
            raise

    def _initialize_agent(self) -> None:
        """Initialize tool-calling agent (simplified approach)."""
        try:
            print(f"[TEST_LOG_AGENT] 🔧 Starting agent initialization...")
            print(f"[TEST_LOG_AGENT] Tools available: {len(self.tools)}")
            for i, tool in enumerate(self.tools):
                print(f"[TEST_LOG_AGENT]   Tool {i+1}: {tool.name} - {tool.description[:50]}...")

            # Create simple tool-calling prompt
            print(f"[TEST_LOG_AGENT] 📝 Creating tool-calling prompt template...")
            from langchain.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an autonomous Android testing agent.

GOAL: Test the Android application systematically using available tools to interact with the device.

COORDINATE ENHANCEMENT (Phase 0 validated - 100% vs 30% success):
- Always use explicit coordinates when available from UI descriptions
- Format: "at position (x, y)" is CRITICAL for success

Available tools: android_click, android_input, android_scroll, android_back, android_screenshot

TESTING STRATEGY:
1. ANALYZE current screen elements
2. REASON about what to test based on UI elements
3. ACT by calling appropriate tools for device interaction
4. Focus on systematic exploration

Choose the best tool to start testing the application."""),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}")
            ])
            print(f"[TEST_LOG_AGENT] ✅ Prompt template created")

            # Create tool-calling agent
            print(f"[TEST_LOG_AGENT] 🤖 Creating tool-calling agent...")
            from langchain.agents import create_tool_calling_agent
            agent = create_tool_calling_agent(self.llm, self.tools, prompt)
            print(f"[TEST_LOG_AGENT] ✅ Tool-calling agent created: {type(agent)}")

            # Create agent executor
            print(f"[TEST_LOG_AGENT] ⚡ Creating AgentExecutor...")
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=5,  # Prevent infinite loops
                return_intermediate_steps=True
            )
            print(f"[TEST_LOG_AGENT] ✅ AgentExecutor created: {type(self.agent_executor)}")

            self.logger.info(f"[RVAGENT_DEBUG] ✅ Tool-calling agent initialized with {len(self.tools)} tools")
            print(f"[TEST_LOG_AGENT] 🎉 Agent initialization complete!")

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Agent initialization failed: {e}")
            print(f"[TEST_LOG_AGENT] ❌ Agent initialization failed: {e}")
            raise

    def _create_react_prompt(self) -> ChatPromptTemplate:
        """Create ReAct prompt template optimized for tool-calling."""
        return ChatPromptTemplate.from_messages([
            ("system", """You are an autonomous Android testing agent using ReAct pattern with tool-calling.

GOAL: Test the Android application systematically using available tools to interact with the device.

COORDINATE ENHANCEMENT (Phase 0 validated - 100% vs 30% success):
- Always use explicit coordinates when available from UI descriptions
- Format: "at position (x, y)" is CRITICAL for success

TOOLS AVAILABLE:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

TESTING STRATEGY:
1. ANALYZE current screen with [UNTESTED] priority (highest priority)
2. REASON about what to test based on coverage annotations
3. ACT by calling appropriate tools for device interaction
4. Focus on systematic exploration with UI coverage guidance
5. Balance tool usage for comprehensive testing

PRIORITIZE [UNTESTED] elements for systematic coverage."""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

    def generate_react_decision(self, ui_state: Dict[str, Any],
                              memory_context: str,
                              coverage_stats: Dict[str, Any],
                              exploration_suggestions: List[Dict[str, Any]],
                              screenshot_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Generate ReAct decision using native tool-calling agent.

        Args:
            ui_state: Current UI state from DeviceInterface
            memory_context: Formatted memory context
            coverage_stats: UI coverage statistics
            exploration_suggestions: Suggested exploration actions

        Returns:
            Agent execution result with tool calls or None if failed
        """
        try:
            start_time = time.time()
            self.logger.debug("[RVAGENT_DEBUG] Starting tool-calling ReAct decision...")
            print(f"[TEST_LOG_EXECUTION] 🚀 Starting ReAct execution...")

            # Build context with UI state and memory
            context = self._build_context(ui_state, memory_context, coverage_stats, exploration_suggestions)

            self.logger.debug(f"[RVAGENT_DEBUG] Agent context built: {len(context)} characters")
            print(f"[TEST_LOG_EXECUTION] 📝 Context built: {len(context)} characters")
            print(f"[TEST_LOG_EXECUTION] 📄 Full context:")
            print(f"[TEST_LOG_EXECUTION] " + "="*60)
            print(context)
            print(f"[TEST_LOG_EXECUTION] " + "="*60)

            # Execute ReAct cycle with tool-calling
            print(f"[TEST_LOG_EXECUTION] ⚡ Invoking AgentExecutor...")
            print(f"[TEST_LOG_EXECUTION] Model: {self.model_name}")
            print(f"[TEST_LOG_EXECUTION] Tools: {[tool.name for tool in self.tools]}")

            # Check if we have a screenshot to include
            agent_input = {"input": context}

            if screenshot_path:
                print(f"[TEST_LOG_VISION] 📸 Including screenshot: {screenshot_path}")

                # Encode screenshot to base64
                screenshot_b64 = encode_image_to_base64(screenshot_path)

                if screenshot_b64:
                    print(f"[TEST_LOG_VISION] ✅ Screenshot encoded: {len(screenshot_b64)} characters")

                    # Create multimodal message for vision model
                    multimodal_content = [
                        {"type": "text", "text": context},
                        {
                            "type": "image",
                            "source_type": "base64",
                            "data": screenshot_b64,
                            "mime_type": "image/png"
                        }
                    ]

                    # Create HumanMessage with multimodal content for vision models
                    # Note: This approach may need adjustment based on LangChain version
                    agent_input["input"] = context  # Keep text context
                    agent_input["screenshot_data"] = screenshot_b64  # Add screenshot separately

                    print(f"[TEST_LOG_VISION] 🎨 Multimodal input prepared for vision model")
                else:
                    print(f"[TEST_LOG_VISION] ❌ Screenshot encoding failed")

            result = self.agent_executor.invoke(agent_input)
            execution_time = time.time() - start_time

            print(f"[TEST_LOG_EXECUTION] ✅ AgentExecutor completed in {execution_time:.2f}s")
            print(f"[TEST_LOG_EXECUTION] 📊 Raw result keys: {list(result.keys())}")
            print(f"[TEST_LOG_EXECUTION] 📄 Full result:")
            print(f"[TEST_LOG_EXECUTION] " + "="*60)
            for key, value in result.items():
                print(f"[TEST_LOG_EXECUTION] {key}: {str(value)[:200]}...")
            print(f"[TEST_LOG_EXECUTION] " + "="*60)

            # Extract tool calls and results
            tool_calls = self._extract_tool_calls(result)
            print(f"[TEST_LOG_EXECUTION] 🔧 Tool calls extracted: {len(tool_calls)}")

            for i, tool_call in enumerate(tool_calls):
                print(f"[TEST_LOG_EXECUTION] Tool {i+1}: {tool_call.get('tool', 'unknown')}")
                print(f"[TEST_LOG_EXECUTION]   Input: {tool_call.get('tool_input', {})}")
                print(f"[TEST_LOG_EXECUTION]   Result: {str(tool_call.get('result', ''))[:100]}...")

            self.logger.info(f"[RVAGENT_DEBUG] ✅ Tool-calling ReAct completed in {execution_time:.2f}s")
            self.logger.info(f"[RVAGENT_DEBUG] Tools executed: {len(tool_calls)}")

            # Convert to format expected by ReactEngine
            actions = self._convert_tool_calls_to_actions(tool_calls)
            print(f"[TEST_LOG_EXECUTION] 🎯 Actions converted: {len(actions)}")

            return {
                "actions": actions,
                "execution_time": execution_time,
                "final_output": result.get("output", ""),
                "tool_calls": tool_calls
            }

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Tool-calling ReAct decision failed: {e}")
            print(f"[TEST_LOG_EXECUTION] ❌ Execution failed: {e}")
            print(f"[TEST_LOG_EXECUTION] 📊 Exception type: {type(e)}")
            import traceback
            print(f"[TEST_LOG_EXECUTION] 📄 Full traceback:")
            traceback.print_exc()
            return None

    def _build_context(self, ui_state: Dict[str, Any], memory_context: str,
                      coverage_stats: Dict[str, Any], exploration_suggestions: List[Dict[str, Any]]) -> str:
        """Build context string for ReAct agent."""
        context_parts = []

        # Current UI state
        activity = ui_state.get('activity', 'unknown')
        element_count = ui_state.get('element_count', 0)

        context_parts.append(f"CURRENT SCREEN: {activity} ({element_count} elements)")

        # UI elements with coordinate enhancement
        if 'formatted_elements' in ui_state:
            context_parts.append("UI ELEMENTS:")
            context_parts.append(ui_state['formatted_elements'])

        # Memory context
        if memory_context:
            context_parts.append("RECENT ACTIONS:")
            context_parts.append(memory_context)

        # Coverage information
        tested = coverage_stats.get("tested_elements", 0)
        untested = coverage_stats.get("untested_elements", 0)
        coverage_pct = coverage_stats.get("coverage_percentage", 0.0)

        context_parts.append(f"COVERAGE STATUS: {tested} tested, {untested} untested ({coverage_pct:.1f}%)")

        # Exploration suggestions
        if exploration_suggestions:
            suggestions_text = []
            for i, suggestion in enumerate(exploration_suggestions[:3], 1):
                suggestion_type = suggestion.get("suggestion", "unknown")
                reason = suggestion.get("reason", "no reason")
                suggestions_text.append(f"{i}. {suggestion_type}: {reason}")

            context_parts.append("PRIORITY SUGGESTIONS:")
            context_parts.extend(suggestions_text)

        return "\n\n".join(context_parts)

    def _extract_tool_calls(self, agent_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool calls from agent execution result."""
        tool_calls = []

        try:
            # Get intermediate steps which contain tool calls
            intermediate_steps = agent_result.get("intermediate_steps", [])

            for step in intermediate_steps:
                if len(step) >= 2:  # (AgentAction, result)
                    agent_action, result = step[0], step[1]

                    tool_call = {
                        "tool": agent_action.tool,
                        "tool_input": agent_action.tool_input,
                        "result": result,
                        "log": agent_action.log
                    }
                    tool_calls.append(tool_call)

            return tool_calls

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Error extracting tool calls: {e}")
            return []

    def _convert_tool_calls_to_actions(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tool calls to ReactAction format for compatibility."""
        actions = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("tool", "")
            tool_input = tool_call.get("tool_input", {})
            result = tool_call.get("result", "")

            # Extract reasoning from log or use tool result
            reasoning = tool_call.get("log", result)

            # Convert tool call to action format
            action = {
                "reasoning": reasoning,
                "action_type": self._map_tool_to_action_type(tool_name),
                "element_id": tool_input.get("element_description", ""),
                "coordinates": self._parse_coordinates(tool_input.get("coordinates", "")),
                "input_text": tool_input.get("text", ""),
                "confidence": 0.8,  # Tool-calling has higher confidence
                "success": "SUCCESS" in result
            }
            actions.append(action)

        return actions

    def _map_tool_to_action_type(self, tool_name: str) -> str:
        """Map tool name to action type."""
        mapping = {
            "android_click": "click",
            "android_input": "input",
            "android_scroll": "scroll",
            "android_back": "back",
            "android_screenshot": "screenshot"
        }
        return mapping.get(tool_name, "unknown")

    def _parse_coordinates(self, coordinates_str: str) -> List[int]:
        """Parse coordinates string to list of integers."""
        try:
            if coordinates_str and "," in coordinates_str:
                x, y = map(int, coordinates_str.split(","))
                return [x, y]
            return []
        except:
            return []

    def test_llm_connection(self) -> bool:
        """Test LLM connection and tool-calling functionality."""
        try:
            self.logger.info("[RVAGENT_DEBUG] Testing tool-calling connection...")

            test_context = """Test the tool-calling system:

CURRENT SCREEN: TestActivity (3 elements)

UI ELEMENTS:
1. "Submit" Button at position (100, 200)
2. "Cancel" Button at position (200, 200)
3. "Help" Button at position (300, 200)

COVERAGE STATUS: 0 tested, 3 untested (0.0%)

Choose one element to test with android_click tool."""

            result = self.agent_executor.invoke({"input": test_context})

            self.logger.info(f"[RVAGENT_DEBUG] Test result: {result.get('output', '')[:150]}...")

            # Check if tools were called
            tool_calls = self._extract_tool_calls(result)
            if tool_calls:
                self.logger.info(f"[RVAGENT_DEBUG] ✅ Tool-calling test successful: {len(tool_calls)} tools called")
                return True
            else:
                self.logger.warning("[RVAGENT_DEBUG] ⚠️ No tools called in test")
                return False

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Tool-calling connection test failed: {e}")
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """Get tool-calling performance metrics."""
        return {
            "model_name": self.model_name,
            "tools_available": [tool.name for tool in self.tools],
            "parameters": {
                "temperature": RVAgentConstants.DEFAULT_TEMPERATURE,
                "top_p": RVAgentConstants.DEFAULT_TOP_P,
                "top_k": RVAgentConstants.DEFAULT_TOP_K,
                "max_tokens": RVAgentConstants.DEFAULT_MAX_TOKENS
            },
            "agent_type": "ReAct with native tool-calling"
        }
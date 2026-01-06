"""
LangGraph Agent for RV-Agent.

Autonomous Android testing agent using LangGraph prebuilt components with vision capabilities.
Implements clean agent architecture without manual routing or complex state management.

### Architectural Decisions:
- Uses LangGraph prebuilt components (tools_condition, ToolNode, MessagesState)
- Direct integration with android_tools for device interaction
- SqliteSaver checkpointer for memory persistence across sessions
- Screenshot optimization for efficient vision model input
- LangSmith observability for debugging and monitoring
- No simulation fallback - enforces real emulator usage

### Role in the System:
- Provides autonomous Android testing capabilities
- Coordinates screenshot capture, UI analysis, and action execution
- Maintains conversation history through checkpointing
- Integrates vision model with Android device actions
- Enables multi-turn reasoning with memory

### Agent Flow:
1. Agent receives initial task/prompt
2. Agent decides which tools to call (or END)
3. tools_condition routes: if tool_calls → "tools", else → END
4. Tools execute and return results
5. Loop back to agent with updated messages
6. Agent continues until task complete or max iterations

**That's it!** No manual routing, no complex state management.
"""

import os
import time
import sqlite3
from typing import Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
from pathlib import Path

from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT

from ..tools import get_android_tools, initialize_tools
from ..core.screenshot_optimizer import ScreenshotOptimizer
from ..constants import RVAgentConstants


# Load environment variables
load_dotenv()


class AgentState(TypedDict):
    """
    Agent state using MessagesState pattern.

    Messages automatically managed by add_messages reducer.
    No need for custom state tracking - LangGraph handles it.
    """
    messages: Annotated[list, add_messages]


class RVAgent:
    """
    Autonomous Android testing agent using LangGraph.

    ### Execution Pattern:
    The agent operates in a simple loop coordinated by LangGraph:
    - Agent receives messages and decides next action
    - tools_condition automatically routes based on tool_calls presence
    - ToolNode executes tools and appends results to messages
    - Loop continues until agent decides to stop (no more tool_calls)

    ### Memory System:
    - SqliteSaver checkpointer preserves conversation history
    - Each session identified by unique thread_id
    - Agent can resume previous sessions with full context
    - Memory stored in-memory (configurable for persistence)

    ### Vision Integration:
    - Screenshots optimized to 728×1288 (Qwen2.5-VL requirement)
    - Base64 encoding for multimodal message content
    - Automatic compression to JPEG at 85% quality
    - ~1,196 tokens per image (optimal range 256-1280)
    """

    def __init__(self, device_id: str = RVAgentConstants.DEFAULT_DEVICE_ID):
        """
        Initialize RV-Agent with device connection.

        Args:
            device_id: Emulator device identifier

        Raises:
            ValueError: If device_id is not an emulator
            RuntimeError: If device connection or initialization fails
        """
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.core.langgraph_agent",
            {CONTEXT_COMPONENT: "RVAgent"}
        )

        self.logger.info(f"Initializing RV-Agent for device: {device_id}")

        # Load configuration from environment
        self.model_name = os.getenv("OLLAMA_MODEL", RVAgentConstants.DEFAULT_MODEL)
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.device_id = device_id

        # Initialize Android tools (raises on failure)
        try:
            initialize_tools(device_id)
            self.tools = get_android_tools()
            self.logger.info(f"Initialized {len(self.tools)} Android tools")
        except Exception as e:
            self.logger.error(f"Tool initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize Android tools: {e}")

        # Initialize screenshot optimizer
        self.screenshot_optimizer = ScreenshotOptimizer()

        # Create LLM with tool binding
        try:
            self.llm = ChatOllama(
                model=self.model_name,
                base_url=self.ollama_host,
                temperature=RVAgentConstants.DEFAULT_TEMPERATURE,
                top_p=RVAgentConstants.DEFAULT_TOP_P,
                top_k=RVAgentConstants.DEFAULT_TOP_K,
                num_predict=RVAgentConstants.DEFAULT_MAX_TOKENS
            )
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            self.logger.info(f"LLM initialized: {self.model_name}")
        except Exception as e:
            self.logger.error(f"LLM initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize LLM: {e}")

        # Create memory checkpointer
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.memory = SqliteSaver(conn)
        self.logger.debug("Memory checkpointer initialized (in-memory)")

        # Build builder
        self.graph = self._build_graph()
        self.logger.info("LangGraph agent initialized successfully")

    def _build_graph(self):
        """
        Build LangGraph using prebuilt components.

        Graph structure:
        - agent: LLM with tools that generates responses/tool_calls
        - tools: ToolNode that executes tool_calls automatically
        - tools_condition: Prebuilt routing (tool_calls → "tools", else → END)

        Returns:
            Compiled builder with checkpointer
        """
        graph = StateGraph(AgentState)

        # Agent node: LLM decides next action
        def agent_node(state: AgentState) -> Dict[str, Any]:
            """
            Agent node invokes LLM with tools.

            LLM receives full message history and decides:
            - Generate tool_calls to execute actions
            - Generate final response (no tool_calls) to end

            Returns:
                Updated state with LLM response
            """
            try:
                messages = state["messages"]
                self.logger.debug(f"Agent node: processing {len(messages)} messages")

                # Invoke LLM with tools
                response = self.llm_with_tools.invoke(messages)

                # Check if LLM called tools
                has_tool_calls = hasattr(response, 'tool_calls') and response.tool_calls
                self.logger.debug(f"Agent response: tool_calls={has_tool_calls}")

                return {"messages": [response]}

            except Exception as e:
                self.logger.error(f"Agent node failed: {e}", exc_info=True)
                raise

        # Add nodes using prebuilt components
        graph.add_node("agent", agent_node)
        graph.add_node("tools", ToolNode(self.tools))

        # Set entry point
        graph.set_entry_point("agent")

        # Add edges using prebuilt tools_condition
        # tools_condition automatically routes:
        #   - If last message has tool_calls → "tools"
        #   - Otherwise → END
        graph.add_conditional_edges("agent", tools_condition)

        # After tools execute, return to agent
        graph.add_edge("tools", "agent")

        # Compile with checkpointer for memory
        compiled_graph = graph.compile(checkpointer=self.memory)

        self.logger.debug("LangGraph compiled with prebuilt components")
        return compiled_graph

    def run_session(
        self,
        task: str,
        screenshot_path: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run autonomous testing session.

        Creates initial message with task and optional screenshot, then
        lets the agent autonomously explore the application using available tools.

        The session runs until the agent decides to stop (no more tool calls).
        External timeout control should be handled by the caller.

        Args:
            task: Testing objective/instructions
            screenshot_path: Optional initial screenshot path
            thread_id: Optional session identifier for memory (default: timestamp)

        Returns:
            Session results with execution metrics

        Example:
            results = agent.run_session(
                task="Test the login functionality",
                screenshot_path="/tmp/screenshot.png",
                thread_id="session_001"
            )
        """
        try:
            # Generate thread_id if not provided
            if thread_id is None:
                thread_id = f"session_{int(time.time())}"

            self.logger.info(f"Starting session: {thread_id}")
            self.logger.info(f"Task: {task}")

            # Build initial message
            message_content = [{"type": "text", "text": task}]

            # Add screenshot if provided
            if screenshot_path and Path(screenshot_path).exists():
                self.logger.info(f"Including screenshot: {screenshot_path}")

                # Optimize screenshot for vision model
                optimized_b64 = self.screenshot_optimizer.optimize(screenshot_path)

                if optimized_b64:
                    message_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{optimized_b64}"}
                    })
                else:
                    self.logger.warning("Screenshot optimization failed, proceeding without image")

            # Create initial state
            initial_state = {
                "messages": [HumanMessage(content=message_content)]
            }

            # Execution configuration
            config = {
                "configurable": {"thread_id": thread_id}
            }

            # Execute builder
            self.logger.info("Executing LangGraph session...")
            start_time = time.time()

            final_state = self.graph.invoke(initial_state, config=config)

            execution_time = time.time() - start_time
            self.logger.info(f"Session completed in {execution_time:.2f}s")

            # Generate results
            return self._generate_results(final_state, thread_id, execution_time)

        except Exception as e:
            self.logger.error(f"Session execution failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "thread_id": thread_id
            }

    def _generate_results(
        self,
        final_state: Dict[str, Any],
        thread_id: str,
        execution_time: float
    ) -> Dict[str, Any]:
        """
        Generate session results summary.

        Analyzes final state to extract metrics and execution details.

        Args:
            final_state: Final builder state
            thread_id: Session identifier
            execution_time: Total execution time

        Returns:
            Results dictionary with metrics
        """
        try:
            messages = final_state.get("messages", [])

            # Count tool executions by type
            tool_counts = {
                "capture_screenshot": 0,
                "android_click": 0,
                "android_input": 0,
                "android_scroll": 0,
                "android_back": 0
            }

            for msg in messages:
                if hasattr(msg, 'name') and msg.name in tool_counts:
                    tool_counts[msg.name] += 1

            total_actions = sum(tool_counts.values())

            results = {
                "status": "completed",
                "thread_id": thread_id,
                "execution_time": execution_time,
                "metrics": {
                    "total_messages": len(messages),
                    "total_tool_calls": total_actions,
                    "tool_breakdown": tool_counts
                },
                "model": self.model_name,
                "device": self.device_id
            }

            self.logger.info(f"Session results: {total_actions} actions in {len(messages)} messages")
            return results

        except Exception as e:
            self.logger.error(f"Results generation failed: {e}", exc_info=True)
            return {
                "status": "partial",
                "error": str(e),
                "thread_id": thread_id
            }

    def get_session_history(self, thread_id: str) -> list:
        """
        Retrieve message history for a session.

        Uses checkpointer to load full conversation history
        for a given thread_id.

        Args:
            thread_id: Session identifier

        Returns:
            List of messages in session

        Example:
            history = agent.get_session_history("session_001")
            for msg in history:
                print(msg)
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}

            # Get checkpoint state
            checkpoint = self.memory.get(config)

            if checkpoint and "messages" in checkpoint:
                return checkpoint["messages"]

            self.logger.warning(f"No history found for thread: {thread_id}")
            return []

        except Exception as e:
            self.logger.error(f"History retrieval failed: {e}", exc_info=True)
            return []

    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status and configuration.

        Returns:
            Agent status dictionary
        """
        return {
            "model": self.model_name,
            "device": self.device_id,
            "tools_available": len(self.tools),
            "memory": "SqliteSaver (in-memory)",
            "observability": "LangSmith" if os.getenv("LANGCHAIN_TRACING_V2") else "disabled",
            "architecture": "LangGraph with prebuilt components"
        }

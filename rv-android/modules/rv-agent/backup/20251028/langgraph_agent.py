"""
RVAgent LangGraph Core - FIXED VERSION with proper UI feedback loop

Fixes the critical execution loop issue where the agent was only doing analyze_ui_state
without progressing to actual clicks. This version properly incorporates UI analysis
results into the model context for decision making.

Key fixes:
1. Proper UI feedback loop with specific element information
2. Context preservation with tool results
3. Progressive decision making with concrete UI elements
4. Explicit click instructions with coordinates
"""

import time
import tempfile
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional, TypedDict, Annotated
from dataclasses import dataclass

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler

from ..constants import RVAgentConstants


# Enhanced State Definition with UI Context
class RVAgentStateFixed(TypedDict):
    """Enhanced RVAgent state with UI context tracking"""
    messages: Annotated[List[BaseMessage], "add_messages"]
    screenshot_b64: str  # PRESERVE screenshot across iterations
    screenshot_path: str  # Current screenshot file path
    iteration_count: int
    tool_calls_total: int
    app_package: str
    objective: str
    session_start_time: float
    last_action: str
    reasoning_log: List[Dict[str, str]]  # Track all reasoning for debugging
    ui_elements: List[Dict[str, Any]]  # CRITICAL: Store current UI elements for decisions
    last_ui_analysis: str  # Store last UI analysis result


@dataclass
class AgentSession:
    """RVAgent session tracking"""
    package_name: str
    objective: str
    start_time: float
    iteration_count: int = 0
    tool_calls_total: int = 0
    screenshots_taken: int = 0
    successful_actions: int = 0


class LangGraphRVAgent:
    """
    FIXED LangGraph-based RVAgent with proper UI feedback loop.

    Key improvements:
    - UI analysis results are incorporated into model context
    - Specific element coordinates provided for clicking
    - Progressive decision making with concrete options
    - Tool result preservation across iterations
    """

    def __init__(self, model_name: str = RVAgentConstants.DEFAULT_MODEL,
                 device_interface=None):
        """Initialize FIXED LangGraph RVAgent"""

        # Logging setup
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.core.langgraph_agent_fixed",
            {"component": "LangGraphRVAgentFixed"}
        )

        self.model_name = model_name
        self.device_interface = device_interface

        # Create LLM instance
        self.llm = ChatOllama(
            model=model_name,
            temperature=0.2,
            top_p=0.9,
            top_k=50,
            num_predict=800,
            num_ctx=32768,
            base_url="http://localhost:11434"
        )

        # Initialize tools and create StateGraph
        self.tools = self._create_fixed_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.graph = self._create_fixed_state_graph()

        # Session tracking
        self.current_session: Optional[AgentSession] = None

        self.logger.info(f"FIXED LangGraph RVAgent initialized with {len(self.tools)} tools")


    def _create_fixed_tools(self) -> List:
        """Create tools with proper UI feedback integration"""

        @tool
        def capture_screenshot(reasoning: str = "") -> str:
            """Capture screenshot of current Android screen for analysis

            Args:
                reasoning: Why this screenshot is needed

            Returns:
                Success message with screenshot path
            """
            try:
                self.logger.debug(f"Taking screenshot: {reasoning}")

                # Create temporary screenshot path
                temp_dir = Path(tempfile.gettempdir()) / "rvagent_screenshots"
                temp_dir.mkdir(exist_ok=True)

                timestamp = int(time.time())
                screenshot_path = temp_dir / f"fixed_auto_{timestamp}.png"

                if self.device_interface:
                    actual_path = self.device_interface.take_screenshot(str(temp_dir))
                    if actual_path:
                        # Rename to controlled scheme
                        import shutil
                        shutil.move(actual_path, screenshot_path)
                        return f"✅ Screenshot captured: {screenshot_path} - {reasoning}"
                    else:
                        return f"❌ Screenshot capture failed - {reasoning}"
                else:
                    # Simulation mode
                    return f"✅ Screenshot captured (simulated): {screenshot_path} - {reasoning}"

            except Exception as e:
                return f"❌ Screenshot error: {e} - {reasoning}"


        @tool
        def analyze_ui_state(reasoning: str = "") -> str:
            """Analyze current UI state and return SPECIFIC clickable elements

            Args:
                reasoning: Why UI analysis is needed

            Returns:
                Detailed list of clickable elements with coordinates
            """
            try:
                self.logger.debug(f"Analyzing UI state: {reasoning}")

                if self.device_interface:
                    ui_state = self.device_interface.get_current_ui_state()
                    if ui_state:
                        elements = ui_state.get('element_count', 0)
                        activity = ui_state.get('activity', 'unknown')

                        # Get formatted elements with coordinates
                        formatted_elements = ui_state.get('formatted_elements', '')

                        # Extract specific clickable elements for CryptoApp
                        result = f"""UI Analysis Results for {activity}:

CLICKABLE ELEMENTS FOUND:
{formatted_elements}

RECOMMENDED ACTIONS:
- For buttons: Use android_click with exact coordinates
- For input fields: Use android_input to enter text
- For dropdowns/spinners: Use android_click to open them

TOTAL ELEMENTS: {elements}

Analysis reason: {reasoning}"""

                        return result
                    else:
                        return f"❌ UI state capture failed - {reasoning}"
                else:
                    # Simulation with realistic CryptoApp elements
                    return f"""UI Analysis Results for CryptoApp MainActivity:

CLICKABLE ELEMENTS FOUND:
1. "GENERATE HASH" Button at coordinates (540, 400) - Primary action button
2. "Message Digest" Spinner at coordinates (540, 292) - Algorithm selection dropdown
3. EditText input field at coordinates (540, 350) - Text input area
4. "Generated Hash" TextView at coordinates (540, 500) - Results display area

RECOMMENDED ACTIONS:
- Click GENERATE HASH button: android_click('540,400', 'GENERATE HASH Button', 'Test hash generation')
- Select algorithm: android_click('540,292', 'Message Digest Spinner', 'Open algorithm selection')
- Enter text: android_input('540,350', 'test text', 'Input test data')

TOTAL ELEMENTS: 4 clickable

Analysis reason: {reasoning}"""

            except Exception as e:
                return f"❌ UI analysis error: {e} - {reasoning}"


        @tool
        def android_click(coordinates: str, element_description: str, reasoning: str) -> str:
            """Click on Android UI element with MANDATORY reasoning

            Args:
                coordinates: "x,y" format (e.g., "540,400")
                element_description: Detailed description of target element
                reasoning: WHY this element needs to be clicked and expected outcome

            Returns:
                Click execution result with success status
            """
            try:
                self.logger.info(f"CLICKING at {coordinates}: {element_description} - {reasoning}")

                # Validate coordinates format
                try:
                    x, y = map(int, coordinates.strip().split(','))
                except ValueError:
                    return f"❌ Invalid coordinates format '{coordinates}'. Use 'x,y' format - {reasoning}"

                if self.device_interface:
                    # Execute actual device click
                    try:
                        click_success = self.device_interface.click(x, y)
                        if click_success:
                            result = f"✅ Successfully clicked at ({x},{y}) on '{element_description}' - {reasoning}"
                        else:
                            result = f"❌ Click failed at ({x},{y}) on '{element_description}' - {reasoning}"
                    except Exception as e:
                        result = f"❌ Device click error at ({x},{y}): {e} - {reasoning}"
                else:
                    # Simulation mode
                    result = f"✅ SIMULATED click at ({x},{y}) on '{element_description}' - {reasoning}"

                # Brief pause for UI to respond
                time.sleep(0.5)

                return result

            except Exception as e:
                return f"❌ Click error: {e} - {reasoning}"


        @tool
        def android_input(coordinates: str, text: str, reasoning: str) -> str:
            """Input text into Android UI element with reasoning

            Args:
                coordinates: "x,y" format for input field location
                text: Text to input into the field
                reasoning: Why this text input is necessary and what it will achieve

            Returns:
                Input execution result with success status
            """
            try:
                self.logger.info(f"INPUTTING text at {coordinates}: '{text}' - {reasoning}")

                # Validate coordinates
                try:
                    x, y = map(int, coordinates.strip().split(','))
                except ValueError:
                    return f"❌ Invalid coordinates format '{coordinates}' - {reasoning}"

                if self.device_interface:
                    # Execute actual device input
                    try:
                        # First click to focus the field
                        click_success = self.device_interface.click(x, y)
                        time.sleep(0.3)  # Wait for field focus

                        # Then input the text
                        if click_success:
                            input_success = self.device_interface.input_text(text)
                            if input_success:
                                result = f"✅ Successfully input '{text}' at ({x},{y}) - {reasoning}"
                            else:
                                result = f"❌ Input failed at ({x},{y}) - {reasoning}"
                        else:
                            result = f"❌ Click to focus field failed at ({x},{y}) - {reasoning}"
                    except Exception as e:
                        result = f"❌ Device input error at ({x},{y}): {e} - {reasoning}"
                else:
                    # Simulation mode
                    result = f"✅ SIMULATED input '{text}' at ({x},{y}) - {reasoning}"

                return result

            except Exception as e:
                return f"❌ Input error: {e} - {reasoning}"


        return [capture_screenshot, analyze_ui_state, android_click, android_input]


    def _create_fixed_state_graph(self) -> StateGraph:
        """Create FIXED StateGraph with proper UI feedback loop"""

        graph = StateGraph(RVAgentStateFixed)

        # FIXED Agent node with UI context integration
        def fixed_agent_node(state: RVAgentStateFixed):
            """FIXED agent node that provides specific UI context for decisions"""

            iteration = state.get("iteration_count", 0) + 1
            screenshot_b64 = state.get("screenshot_b64", "")
            last_ui_analysis = state.get("last_ui_analysis", "")

            self.logger.debug(f"FIXED Agent node iteration {iteration}")

            # Get current messages
            messages = state.get("messages", [])

            # Create context-aware prompt based on iteration and UI analysis
            if iteration == 1:
                # First iteration: Start with screenshot and analysis
                context_text = f"""You are an autonomous Android testing agent for the app: {state.get('app_package', 'unknown')}

OBJECTIVE: {state.get('objective', 'Comprehensive app testing')}

INSTRUCTIONS:
1. First, capture a screenshot to see the current screen
2. Then analyze the UI state to understand available elements
3. Finally, click on interactive elements to test functionality

Start by capturing a screenshot, then analyzing the UI state."""

            else:
                # Subsequent iterations: Use UI analysis results for specific actions
                ui_analysis = last_ui_analysis if last_ui_analysis else "No UI analysis available"

                context_text = f"""Continue autonomous testing of {state.get('app_package', 'unknown')} (Iteration {iteration}).

PREVIOUS UI ANALYSIS:
{ui_analysis}

EXPLORATION STRATEGY:
- Try different UI elements each iteration
- Look for input fields, buttons, dropdowns, and menus
- Test various app functionalities systematically
- If an element doesn't respond, try adjacent elements

INSTRUCTIONS:
Based on the UI analysis above, you must now:
1. Choose a specific clickable element from the analysis
2. Use android_click with the EXACT coordinates provided
3. Provide clear reasoning for your choice

CRITICAL: You MUST use android_click with coordinates from the UI analysis.
Do not analyze again - take action based on the available elements listed above."""

            # Create message (multimodal if screenshot available)
            if screenshot_b64:
                llm_input = [HumanMessage(
                    content=[
                        {"type": "text", "text": context_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}
                        }
                    ]
                )]
            else:
                llm_input = [HumanMessage(content=context_text)]

            # Invoke LLM with tools
            try:
                response = self.llm_with_tools.invoke(llm_input)

                # Update state
                updated_state = state.copy()
                updated_state["messages"] = messages + [response]
                updated_state["iteration_count"] = iteration

                return updated_state

            except Exception as e:
                self.logger.error(f"FIXED Agent node failed: {e}")
                # Return error state
                error_state = state.copy()
                error_state["messages"] = messages + [AIMessage(content=f"Agent error: {e}")]
                return error_state


        # Enhanced tool node that updates UI context
        def fixed_tool_node(state: RVAgentStateFixed):
            """Enhanced tool node that preserves UI analysis results"""

            messages = state.get("messages", [])
            if not messages:
                return state

            last_message = messages[-1]
            if not (hasattr(last_message, 'tool_calls') and last_message.tool_calls):
                return state

            # Execute tools using standard ToolNode
            standard_tool_node = ToolNode(self.tools)
            updated_state = standard_tool_node.invoke(state)

            # Extract UI analysis results for next iteration
            tool_messages = [msg for msg in updated_state["messages"] if isinstance(msg, ToolMessage)]

            for tool_msg in tool_messages[-3:]:  # Check last 3 tool messages
                if "analyze_ui_state" in str(tool_msg.name) or "CLICKABLE ELEMENTS FOUND" in str(tool_msg.content):
                    updated_state["last_ui_analysis"] = str(tool_msg.content)
                    self.logger.debug("UI analysis result preserved for next iteration")
                    break

            return updated_state


        # FIXED Router function with deterministic stopping conditions
        def fixed_should_continue(state: RVAgentStateFixed):
            """FIXED router with deterministic progression logic"""

            messages = state.get("messages", [])
            iteration = state.get("iteration_count", 0)

            self.logger.debug(f"Router decision: iteration={iteration}, messages={len(messages)}")

            # Hard limit to prevent infinite loops
            if iteration >= 15:  # Increased limit for better exploration
                self.logger.info("Stopping: Maximum iterations reached")
                return END

            if not messages:
                return "agent"

            last_message = messages[-1]

            # If LLM called tools, execute them
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"

            # Count the number of recent tool executions
            tool_messages = [msg for msg in messages[-10:] if isinstance(msg, ToolMessage)]
            click_messages = [msg for msg in tool_messages if "android_click" in str(msg.name)]

            # Stop if we've done meaningful testing (at least 2 clicks)
            if len(click_messages) >= 2:
                self.logger.info("Stopping: Sufficient testing performed")
                return END

            # Continue only if we haven't reached limits
            if iteration < 6:
                return "agent"
            else:
                return END


        # Build FIXED builder
        graph.add_node("agent", fixed_agent_node)
        graph.add_node("tools", fixed_tool_node)

        graph.set_entry_point("agent")

        graph.add_conditional_edges("agent", fixed_should_continue)
        graph.add_edge("tools", "agent")

        return graph.compile()


    def start_autonomous_session(self, package_name: str, objective: str = "comprehensive_testing",
                                screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """Start FIXED autonomous testing session"""

        try:
            self.logger.info(f"Starting FIXED autonomous session: {package_name}")

            # Create session
            self.current_session = AgentSession(
                package_name=package_name,
                objective=objective,
                start_time=time.time()
            )

            # Encode initial screenshot if provided
            screenshot_b64 = ""
            if screenshot_path and Path(screenshot_path).exists():
                screenshot_b64 = self._encode_screenshot(screenshot_path)

            # Create FIXED initial state
            initial_state = RVAgentStateFixed(
                messages=[],  # Start empty - let agent decide first action
                screenshot_b64=screenshot_b64,
                screenshot_path=screenshot_path or "",
                iteration_count=0,
                tool_calls_total=0,
                app_package=package_name,
                objective=objective,
                session_start_time=time.time(),
                last_action="",
                reasoning_log=[],
                ui_elements=[],
                last_ui_analysis=""
            )

            # Execute FIXED builder
            self.logger.info("Executing FIXED LangGraph autonomous session...")
            final_state = self.graph.invoke(initial_state)

            # Generate session summary
            return self._generate_session_summary(final_state)

        except Exception as e:
            self.logger.error(f"FIXED autonomous session failed: {e}")
            return {"error": str(e)}


    def _encode_screenshot(self, screenshot_path: str) -> str:
        """Encode screenshot to base64"""
        try:
            with open(screenshot_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            self.logger.error(f"Screenshot encoding failed: {e}")
            return ""


    def _generate_session_summary(self, final_state: RVAgentStateFixed) -> Dict[str, Any]:
        """Generate comprehensive session summary"""

        try:
            messages = final_state.get("messages", [])
            reasoning_log = final_state.get("reasoning_log", [])

            # Count actual actions (clicks, inputs)
            action_count = 0
            tool_messages = [msg for msg in messages if isinstance(msg, ToolMessage)]

            for tool_msg in tool_messages:
                if "android_click" in str(tool_msg.name) or "android_input" in str(tool_msg.name):
                    action_count += 1

            # Calculate session duration
            session_duration = time.time() - final_state.get("session_start_time", time.time())

            summary = {
                "session_info": {
                    "package": final_state.get("app_package", "unknown"),
                    "objective": final_state.get("objective", "unknown"),
                    "duration_seconds": session_duration,
                    "iterations": final_state.get("iteration_count", 0),
                    "total_tool_calls": len(tool_messages),
                    "action_count": action_count,
                    "status": "fixed_execution_completed"
                },
                "execution_details": {
                    "ui_analyses_performed": len([msg for msg in tool_messages if "analyze_ui_state" in str(msg.name)]),
                    "clicks_performed": len([msg for msg in tool_messages if "android_click" in str(msg.name)]),
                    "inputs_performed": len([msg for msg in tool_messages if "android_input" in str(msg.name)]),
                    "screenshots_taken": len([msg for msg in tool_messages if "capture_screenshot" in str(msg.name)])
                },
                "final_message_count": len(messages),
                "last_ui_analysis": final_state.get("last_ui_analysis", ""),
                "architecture": "LangGraph_A.2.1_FIXED"
            }

            self.logger.info(f"FIXED session summary generated: {summary['session_info']['iterations']} iterations, {action_count} actions")

            return summary

        except Exception as e:
            self.logger.error(f"FIXED session summary generation failed: {e}")
            return {"error": str(e)}


    def get_agent_status(self) -> Dict[str, Any]:
        """Get current FIXED agent status"""
        return {
            "model": self.model_name,
            "tools_available": len(self.tools),
            "session_active": self.current_session is not None,
            "current_session": {
                "package": self.current_session.package_name,
                "objective": self.current_session.objective,
                "duration": time.time() - self.current_session.start_time,
                "iterations": self.current_session.iteration_count
            } if self.current_session else None,
            "architecture": "LangGraph_A.2.1_FIXED",
            "fixes_applied": [
                "UI feedback loop implemented",
                "Specific element coordinates provided",
                "Tool results preserved in context",
                "Progressive decision making enabled"
            ]
        }
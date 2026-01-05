"""
RVAgent LLM Service - Direct LLM+Tools implementation.

Implements coordinate validation discoveries: uses LLM with bind_tools() directly
instead of LangChain Agent framework, which breaks multimodal input.
Based on successful validation results with 100% hit rates.
"""

import time
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler

from ..constants import RVAgentConstants


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
        print(f"[LANGCHAIN_SERVICE] ❌ Image encoding failed: {e}")
        return None


# Redundant tool implementations removed - using existing simple_tools.py


class LangChainService:
    """
    LangChain service for RVAgent using direct LLM+Tools approach.

    Uses LLM with bind_tools() instead of Agent framework to support multimodal input.
    Based on coordinate validation discoveries with 100% hit rates.
    """

    def __init__(self, device_adapter, model_name: str = RVAgentConstants.DEFAULT_MODEL):
        """Initialize LangChain service with direct LLM+Tools."""

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

        # Initialize tools using existing simple_tools with device connection
        from .simple_tools import create_android_tools
        self.tools = create_android_tools(self.device_adapter)

        # Initialize LLM and bind tools
        self.llm = None
        self.llm_with_tools = None
        self._initialize_llm()

        # Track if we need to reinitialize (for debugging)
        self.call_count = 0

        self.logger.info(f"[RVAGENT_DEBUG] LangChainService initialized with LLM+Tools: {model_name}")

    def _initialize_llm(self) -> None:
        """Initialize LLM with tools binding."""
        try:
            self.logger.info(f"[RVAGENT_DEBUG] Initializing LLM with {self.model_name}...")
            print(f"[LLM_SERVICE] 🧠 Starting LLM initialization: {self.model_name}")

            if self.model_name.startswith("claude"):
                # Claude configuration
                print(f"[LLM_SERVICE] 🔧 Using Claude configuration")
                if not ANTHROPIC_AVAILABLE:
                    raise ImportError("langchain-anthropic not installed. Install with: pip install langchain-anthropic")

                self.llm = ChatAnthropic(
                    model=self.model_name,
                    temperature=RVAgentConstants.DEFAULT_TEMPERATURE,
                    max_tokens=RVAgentConstants.DEFAULT_MAX_TOKENS,
                )
                self.logger.info("[RVAGENT_DEBUG] ✅ Claude LLM initialized")
                print(f"[LLM_SERVICE] ✅ Claude LLM object created: {type(self.llm)}")
            else:
                # Ollama configuration
                print(f"[LLM_SERVICE] 🔧 Using Ollama configuration")
                print(f"[LLM_SERVICE] Parameters: temp={RVAgentConstants.DEFAULT_TEMPERATURE}, top_p={RVAgentConstants.DEFAULT_TOP_P}, top_k={RVAgentConstants.DEFAULT_TOP_K}")

                self.llm = ChatOllama(
                    model=self.model_name,
                    temperature=0.2,              # Validated parameters from coordinate test
                    top_p=0.9,                    # Validated parameters from coordinate test
                    top_k=50,                     # Same as validated
                    num_predict=RVAgentConstants.DEFAULT_MAX_TOKENS,   # 800
                    num_ctx=32768,                # Context size from validation
                    base_url="http://localhost:11434"
                )
                self.logger.info("[RVAGENT_DEBUG] ✅ Ollama LLM initialized")
                print(f"[LLM_SERVICE] ✅ Ollama LLM object created: {type(self.llm)}")

            # Bind tools to LLM (direct approach that works with multimodal)
            print(f"[LLM_SERVICE] 🔧 Binding {len(self.tools)} tools to LLM...")
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            print(f"[LLM_SERVICE] ✅ Tools bound successfully: {[tool.name for tool in self.tools]}")

            # Test LLM connection
            print(f"[LLM_SERVICE] 🔍 Testing LLM connection...")
            test_response = self.llm.invoke("Test connection. Respond with: Hello from RVAgent")
            print(f"[LLM_SERVICE] ✅ LLM connection test response: {test_response}")

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] LLM initialization failed: {e}")
            print(f"[LLM_SERVICE] ❌ LLM initialization failed: {e}")
            raise

    def generate_react_decision(self, ui_state: Dict[str, Any],
                              memory_context: str,
                              coverage_stats: Dict[str, Any],
                              exploration_suggestions: List[Dict[str, Any]],
                              screenshot_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Generate ReAct decision using direct LLM+Tools approach.

        Args:
            ui_state: Current UI state from DeviceInterface
            memory_context: Formatted memory context
            coverage_stats: UI coverage statistics
            exploration_suggestions: Suggested exploration actions
            screenshot_path: Path to screenshot for vision models

        Returns:
            LLM execution result with tool calls or None if failed
        """
        try:
            start_time = time.time()
            self.call_count += 1
            self.logger.debug("[RVAGENT_DEBUG] Starting LLM+Tools decision...")
            print(f"[LLM_SERVICE] 🚀 Starting LLM+Tools execution (call #{self.call_count})...")

            # REMOVED: Don't reinitialize - need memory between calls for exploration
            # if self.call_count > 1:
            #     print(f"[LLM_SERVICE] 🔄 Reinitializing LLM+Tools for fresh state...")
            #     self._initialize_llm()

            # Build context
            context = self._build_context(ui_state, memory_context, coverage_stats, exploration_suggestions)
            print(f"[LLM_SERVICE] 📝 Context built: {len(context)} characters")

            # FASE 1 Debug Logging - Memory and Coverage Analysis
            print(f"[RVAGENT_DEBUG] Memory Context: {memory_context[:200]}..." if memory_context and len(memory_context) > 200 else f"[RVAGENT_DEBUG] Memory Context: {memory_context}")
            print(f"[RVAGENT_DEBUG] Coverage Stats: {coverage_stats}")
            print(f"[RVAGENT_DEBUG] Exploration Suggestions: {len(exploration_suggestions)} suggestions")
            if exploration_suggestions:
                for i, suggestion in enumerate(exploration_suggestions[:3]):
                    print(f"[RVAGENT_DEBUG]   {i+1}. {suggestion.get('suggestion', 'N/A')}: {suggestion.get('reason', 'No reason')}")
            print(f"[RVAGENT_DEBUG] Full Context Preview (first 500 chars): {context[:500]}...")

            # Create message with multimodal support - EXACT format from validation
            if screenshot_path:
                print(f"[LLM_SERVICE] 📸 Including screenshot: {screenshot_path}")

                # Encode screenshot
                screenshot_b64 = encode_image_to_base64(screenshot_path)

                if screenshot_b64:
                    print(f"[LLM_SERVICE] ✅ Screenshot encoded: {len(screenshot_b64)} characters")

                    # Create multimodal HumanMessage - EXACT format from validation success
                    message = HumanMessage(
                        content=[
                            {
                                "type": "text",
                                "text": f"""Look at this Android app screenshot and interact with an important UI element.

{context}

Choose one element and use the appropriate tool with exact coordinates and reasoning."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot_b64}"
                                }
                            }
                        ]
                    )
                    print(f"[LLM_SERVICE] 🎨 Multimodal message created using validated format")
                else:
                    print(f"[LLM_SERVICE] ❌ Screenshot encoding failed, using text only")
                    message = HumanMessage(content=context)
            else:
                message = HumanMessage(content=context)

            # Execute LLM with tools
            print(f"[LLM_SERVICE] ⚡ Invoking LLM with tools...")
            print(f"[LLM_SERVICE] 🔧 Available tools: {[tool.name for tool in self.tools]}")

            result = self.llm_with_tools.invoke([message])
            execution_time = time.time() - start_time

            print(f"[LLM_SERVICE] ✅ LLM+Tools completed in {execution_time:.2f}s")
            print(f"[LLM_SERVICE] 📊 Result type: {type(result)}")
            print(f"[LLM_SERVICE] 📄 FULL LLM RESPONSE:")
            print(f"[LLM_SERVICE] 📝 Content: {str(result.content)}")
            print(f"[LLM_SERVICE] 📝 Content length: {len(str(result.content))} characters")

            # Check for multiple tool calls in content
            content_str = str(result.content)
            tool_call_count_in_content = content_str.count('tool_call')
            android_click_count = content_str.count('android_click')
            print(f"[LLM_SERVICE] 📊 'tool_call' mentions in content: {tool_call_count_in_content}")
            print(f"[LLM_SERVICE] 📊 'android_click' mentions in content: {android_click_count}")

            print(f"[LLM_SERVICE] 🔍 Has tool_calls attr: {hasattr(result, 'tool_calls')}")
            if hasattr(result, 'tool_calls'):
                print(f"[LLM_SERVICE] 🔧 Tool calls ({len(result.tool_calls)}):")
                for i, tc in enumerate(result.tool_calls):
                    print(f"[LLM_SERVICE]   {i+1}. {tc.get('name', 'unknown')}: {tc.get('args', {})}")
            else:
                print(f"[LLM_SERVICE] ❌ NO TOOL CALLS FOUND")
            print(f"[LLM_SERVICE] 📋 Additional kwargs: {result.additional_kwargs}")
            print(f"[LLM_SERVICE] 📋 Response metadata keys: {list(result.response_metadata.keys())}")

            # Extract tool calls - Manual parsing for gemma3-tools compatibility
            tool_calls = []

            # Try automatic tool_calls first
            if hasattr(result, 'tool_calls') and result.tool_calls:
                print(f"[LLM_SERVICE] 🔧 Automatic tool calls detected: {len(result.tool_calls)}")
                print(f"[LLM_SERVICE] 🔍 Tool calls raw structure: {result.tool_calls}")

                for i, tool_call in enumerate(result.tool_calls):
                    print(f"[LLM_SERVICE] Tool {i+1}: {tool_call.get('name', 'unknown')}")
                    print(f"[LLM_SERVICE]   Args: {tool_call.get('args', {})}")
                    print(f"[LLM_SERVICE]   Full tool_call object: {tool_call}")

                    # Execute tool
                    tool_name = tool_call.get('name', '')
                    tool_args = tool_call.get('args', {})

                    # COORDINATE VALIDATION - Block forbidden coordinates
                    # COORDINATE VALIDATION - Block repeated coordinates and dangerous system elements
                    if tool_name == 'android_click':
                        coordinates = tool_args.get('coordinates', '')
                        element_desc = tool_args.get('element_description', '')

                        # Extract blocked coords from memory
                        blocked_coords = []
                        if memory_context:
                            import re
                            coord_matches = re.findall(r'at \((\d+), (\d+)\)', memory_context)
                            blocked_coords = [f"{x},{y}" for x, y in coord_matches]

                        # Check for repeated coordinates
                        if coordinates in blocked_coords:
                            print(f"[LLM_SERVICE] 🚫 BLOCKED: Coordinate {coordinates} is forbidden!")
                            print(f"[LLM_SERVICE] 🚫 Blocked coordinates: {blocked_coords}")
                            tool_result = f"BLOCKED: Coordinate {coordinates} was already used successfully. Choose different element."
                            tool_calls.append({
                                "tool": tool_name,
                                "tool_input": tool_args,
                                "result": tool_result
                            })
                            continue

                        # Check for dangerous system navigation elements
                        dangerous_elements = ['Overview', 'recent_apps', 'Home', 'home_button']
                        if any(danger in element_desc for danger in dangerous_elements):
                            print(f"[LLM_SERVICE] 🚫 BLOCKED: Dangerous system element '{element_desc}'!")
                            tool_result = f"BLOCKED: '{element_desc}' is a system navigation element that can exit the app. Choose app-specific elements only."
                            tool_calls.append({
                                "tool": tool_name,
                                "tool_input": tool_args,
                                "result": tool_result
                            })
                            continue

                        # Check for coordinates in dangerous system areas (bottom navigation bar)
                        if coordinates:
                            try:
                                x, y = map(int, coordinates.replace(' ', '').split(','))
                                if y > 1800:  # Bottom system navigation area
                                    print(f"[LLM_SERVICE] 🚫 BLOCKED: System navigation area at y={y}!")
                                    tool_result = f"BLOCKED: Coordinate ({x}, {y}) is in system navigation area. Choose app content elements only."
                                    tool_calls.append({
                                        "tool": tool_name,
                                        "tool_input": tool_args,
                                        "result": tool_result
                                    })
                                    continue
                            except:
                                pass  # Invalid coordinate format, let it proceed

                    # Find and execute the tool
                    tool_result = self._execute_tool(tool_name, tool_args)

                    tool_calls.append({
                        "tool": tool_name,
                        "tool_input": tool_args,
                        "result": tool_result
                    })
            else:
                print(f"[LLM_SERVICE] ⚠️ No automatic tool calls detected, trying manual parsing...")

                # Manual parsing for gemma3-tools format
                content = str(result.content)
                print(f"[LLM_SERVICE] 🔍 Parsing content for tool calls...")

                import json
                import re

                # Look for JSON tool calls in content
                json_pattern = r'\{"name":\s*"([^"]+)"[^}]*"parameters":\s*\{([^}]*)\}'
                matches = re.findall(json_pattern, content)

                if matches:
                    print(f"[LLM_SERVICE] 🎯 Found {len(matches)} tool calls via manual parsing")

                    for i, (tool_name, params_str) in enumerate(matches):
                        try:
                            # Parse parameters
                            params_json = "{" + params_str + "}"
                            tool_args = json.loads(params_json)

                            print(f"[LLM_SERVICE] Manual Tool {i+1}: {tool_name}")
                            print(f"[LLM_SERVICE]   Args: {tool_args}")

                            # Execute tool
                            tool_result = self._execute_tool(tool_name, tool_args)

                            tool_calls.append({
                                "tool": tool_name,
                                "tool_input": tool_args,
                                "result": tool_result
                            })
                        except Exception as e:
                            print(f"[LLM_SERVICE] ❌ Failed to parse tool call {i+1}: {e}")
                else:
                    print(f"[LLM_SERVICE] ❌ No tool calls found via manual parsing either")

            self.logger.info(f"[RVAGENT_DEBUG] ✅ LLM+Tools completed in {execution_time:.2f}s")
            self.logger.info(f"[RVAGENT_DEBUG] Tools executed: {len(tool_calls)}")

            # Convert to format expected by ReactEngine
            actions = self._convert_tool_calls_to_actions(tool_calls, result.content)

            return {
                "actions": actions,
                "execution_time": execution_time,
                "final_output": result.content,
                "tool_calls": tool_calls
            }

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] LLM+Tools decision failed: {e}")
            print(f"[LLM_SERVICE] ❌ Execution failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Execute tool by name with arguments."""
        try:
            for tool in self.tools:
                if tool.name == tool_name:
                    return tool.invoke(tool_args)
            return f"Tool '{tool_name}' not found"
        except Exception as e:
            return f"Tool execution failed: {e}"

    def _build_context(self, ui_state: Dict[str, Any], memory_context: str,
                      coverage_stats: Dict[str, Any], exploration_suggestions: List[Dict[str, Any]]) -> str:
        """Build context string for LLM using validated coordinate testing approach with memory and coverage."""

        # BUILD MEMORY SECTION - Key for preventing infinite loops
        memory_section = ""
        blocked_elements = []

        if memory_context and memory_context.strip() and memory_context != "This is a new screen - no previous actions attempted.":
            # Extract blocked elements from memory
            lines = memory_context.split('\n')
            for line in lines:
                if '✅' in line and 'at (' in line:
                    # Extract coordinates from successful actions
                    import re
                    coord_match = re.search(r'at \((\d+), (\d+)\)', line)
                    if coord_match:
                        coords = f"{coord_match.group(1)},{coord_match.group(2)}"
                        blocked_elements.append(coords)

            memory_section = f"""
🚫 BLOCKED ACTIONS - DO NOT REPEAT:
{memory_context}

❌ FORBIDDEN COORDINATES: {', '.join(blocked_elements)}
⚠️ ABSOLUTE RULE: You MUST NOT click on these coordinates again!
✅ REQUIREMENT: Choose completely different UI elements that you haven't tested yet."""
        elif memory_context and "new screen" in memory_context:
            memory_section = f"""
MEMORY: {memory_context}"""

        # BUILD COVERAGE SECTION - Guide exploration priorities
        coverage_section = ""
        if coverage_stats:
            tested = coverage_stats.get('tested_elements', 0)
            untested = coverage_stats.get('untested_elements', 0)
            total = tested + untested
            percentage = coverage_stats.get('coverage_percentage', 0.0)

            if total > 0:
                coverage_section = f"""
COVERAGE STATUS: {tested} tested, {untested} untested ({percentage:.1f}%)
PRIORITY: Focus on UNTESTED elements to maximize coverage and avoid redundant actions."""

        # BUILD EXPLORATION SUGGESTIONS - Strategic guidance
        exploration_section = ""
        if exploration_suggestions:
            suggestions = []
            for suggestion in exploration_suggestions[:3]:  # Top 3 suggestions
                if suggestion.get('suggestion'):
                    suggestions.append(f"- {suggestion['suggestion']}: {suggestion.get('reason', 'No reason provided')}")

            if suggestions:
                exploration_section = f"""
EXPLORATION SUGGESTIONS:
{chr(10).join(suggestions)}"""

        # FILTER UI ELEMENTS - Remove blocked and dangerous elements
        filtered_elements = self._filter_safe_elements(ui_state.get('formatted_elements', 'No elements found'), blocked_elements)

        # COMPREHENSIVE PROMPT - Validation approach + Memory guidance + Coverage strategy
        context = f"""You are testing an Android application systematically. Look at the UI elements and create a comprehensive testing sequence.

AVAILABLE SAFE UI ELEMENTS (filtered to exclude blocked and dangerous elements):
{filtered_elements}{memory_section}{coverage_section}{exploration_section}

IMPORTANT:
1. Use EXACT coordinates from "at position (x, y)" format. Never estimate coordinates.
2. **USE MULTIPLE TOOLS PER RESPONSE** - You should execute 2-3 tools in sequence for comprehensive testing:
   - android_click: Click buttons, tabs, images, checkboxes, spinners
   - android_input: Type text into input fields (use coordinates first, then text)
   - android_scroll: Scroll to see more content (up, down, left, right)
   - android_back: Navigate back or close dialogs
3. **TOOL SEQUENCES** - Execute logical sequences:
   - For EditText: android_click coordinates → android_input "test text"
   - For Spinners: android_click to open → android_click to select option
   - For exploration: android_click button → android_click another element
4. Always provide 'reasoning' parameter for each action
5. **MAXIMIZE TESTING**: Use 2-3 tools per response when possible

TESTING STRATEGY:
1. 🚫 FIRST RULE: Check forbidden coordinates list - NEVER use blocked coordinates
2. ✅ SECOND RULE: Only choose elements with coordinates NOT in the forbidden list
3. 🎯 THIRD RULE: Prioritize APP-SPECIFIC elements (buttons, inputs, content within the app)
4. 🚫 FOURTH RULE: Avoid dangerous system elements (Home, Overview at bottom y > 1800)
5. 🔄 FIFTH RULE: If stuck/no app elements, use android_back or android_scroll to navigate

DANGEROUS ELEMENTS (avoid unless stuck):
- "Home", "Overview" - can exit the app to system
- System navigation bar at very bottom of screen (y > 1800)

NAVIGATION ELEMENTS (use carefully):
- "Back", "Navigate up" - use only if stuck or need to go back
- Use android_back tool instead of clicking Back button when possible

SAFE ELEMENTS TO PRIORITIZE:
- App buttons (like "GENERATE HASH", "MESSAGE DIGEST")
- Input fields within the app content
- Spinners and dropdowns in app content
- Content areas and app-specific UI

⚠️ CRITICAL VALIDATION: Choose elements that are clearly part of the target app content, not system navigation!

Task: Choose ONE action from UNBLOCKED elements only. Focus on elements that haven't been tested yet.
PRIORITY SEQUENCES (choose the most appropriate):
1. For EditText fields: Use android_input tool with coordinates AND text
2. For Spinners: Use android_click to open dropdown options
3. For new buttons: Use android_click to test functionality
4. For navigation: Use android_back or android_scroll when stuck

CRITICAL: If you see Spinner at (540, 292) - this is the ONLY safe untested element!"""

        return context

    def _filter_safe_elements(self, elements_text: str, blocked_coords: List[str]) -> str:
        """Filter UI elements to remove blocked coordinates and dangerous system elements."""
        if not elements_text or elements_text == 'No elements found':
            return elements_text

        lines = elements_text.split('\n')
        safe_lines = []

        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue

            # Extract coordinates from line
            import re
            coord_match = re.search(r'at position \((\d+), (\d+)\)', line)
            if coord_match:
                x, y = coord_match.groups()
                coordinates = f"{x},{y}"

                # Skip if coordinates are blocked
                if coordinates in blocked_coords:
                    continue

                # Skip if in system navigation area (bottom y > 1800)
                if int(y) > 1800:
                    continue

                # Skip dangerous system elements
                dangerous_keywords = ['Overview', 'recent_apps', 'Home', 'home_button', 'Navigate up']
                if any(keyword in line for keyword in dangerous_keywords):
                    continue

            safe_lines.append(line)

        if not safe_lines:
            return "No safe elements available. Use android_scroll to explore or android_back to navigate."

        return '\n'.join(safe_lines)

    def _convert_tool_calls_to_actions(self, tool_calls: List[Dict[str, Any]], llm_content: str) -> List[Dict[str, Any]]:
        """Convert tool calls to ReactAction format for compatibility."""
        actions = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("tool", "")
            tool_input = tool_call.get("tool_input", {})
            result = tool_call.get("result", "")

            # Extract reasoning from reasoning parameter (simple_tools format) or LLM content
            reasoning = tool_input.get("reasoning", tool_input.get("explanation", llm_content))

            # Convert tool call to action format
            action = {
                "reasoning": reasoning,
                "action_type": self._map_tool_to_action_type(tool_name),
                "element_id": tool_input.get("element_description", ""),
                "coordinates": self._parse_coordinates(tool_input.get("coordinates", "")),
                "input_text": tool_input.get("text", ""),
                "confidence": 0.9,  # LLM+Tools has high confidence
                "already_executed": True,  # Tools were already executed
                "success": "successfully" in result.lower()
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
            "android_analyze_spinner": "analyze"
        }
        return mapping.get(tool_name, "unknown")

    def _parse_coordinates(self, coordinates_str: str) -> Optional[List[int]]:
        """Parse coordinates string to list of integers."""
        try:
            if coordinates_str and "," in coordinates_str:
                x, y = map(int, coordinates_str.split(","))
                return [x, y]
            return None
        except:
            return None

    def test_llm_connection(self) -> bool:
        """Test LLM connection and tool-calling functionality."""
        try:
            self.logger.info("[RVAGENT_DEBUG] Testing LLM+Tools connection...")

            test_context = """Test the tool-calling system:

CURRENT SCREEN: TestActivity (3 elements)

UI ELEMENTS:
1. "Submit" Button at position (100, 200)
2. "Cancel" Button at position (200, 200)
3. "Help" Button at position (300, 200)

COVERAGE STATUS: 0 tested, 3 untested (0.0%)

Choose one element to test with android_click tool."""

            message = HumanMessage(content=test_context)
            result = self.llm_with_tools.invoke([message])

            self.logger.info(f"[RVAGENT_DEBUG] Test result: {str(result.content)[:150]}...")

            # Check if tools were called
            tool_calls_detected = hasattr(result, 'tool_calls') and result.tool_calls
            if tool_calls_detected:
                self.logger.info(f"[RVAGENT_DEBUG] ✅ LLM+Tools test successful: {len(result.tool_calls)} tools called")
                return True
            else:
                self.logger.warning("[RVAGENT_DEBUG] ⚠️ No tools called in test")
                return False

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] LLM+Tools connection test failed: {e}")
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """Get LLM+Tools performance metrics."""
        return {
            "model_name": self.model_name,
            "tools_available": [tool.name for tool in self.tools],
            "parameters": {
                "temperature": RVAgentConstants.DEFAULT_TEMPERATURE,
                "top_p": RVAgentConstants.DEFAULT_TOP_P,
                "top_k": RVAgentConstants.DEFAULT_TOP_K,
                "max_tokens": RVAgentConstants.DEFAULT_MAX_TOKENS
            },
            "implementation": "Direct LLM+Tools with multimodal support"
        }
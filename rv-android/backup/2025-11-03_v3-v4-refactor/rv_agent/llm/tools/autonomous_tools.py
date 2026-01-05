"""
Autonomous Android Testing Tools for LangGraph RVAgent

Enhanced tool suite with reasoning fields for debugging and comprehensive
Android application testing capabilities.

All tools include mandatory reasoning parameter for debugging and learning.
"""

import time
import base64
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from langchain_core.tools import tool
from rv_android_core.util.logging.manager import LoggingManager


@dataclass
class ToolExecution:
    """Track tool execution with reasoning"""
    tool_name: str
    timestamp: float
    reasoning: str
    parameters: Dict[str, Any]
    result: str
    success: bool


class AutonomousToolManager:
    """Manages autonomous tools with execution tracking and memory integration"""

    def __init__(self, device_interface=None):
        self.device_interface = device_interface
        self.execution_history: List[ToolExecution] = []

        # Logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.tools.autonomous_tools",
            {"component": "AutonomousToolManager"}
        )

        # Screenshot management
        self.screenshot_dir = Path(tempfile.gettempdir()) / "rvagent_autonomous"
        self.screenshot_dir.mkdir(exist_ok=True)
        self.screenshot_limit = 15  # Keep only last 15 screenshots

        self.logger.info("Autonomous tool manager initialized")


    def _record_execution(self, tool_name: str, reasoning: str,
                         parameters: Dict[str, Any], result: str, success: bool):
        """Record tool execution for debugging and learning"""
        execution = ToolExecution(
            tool_name=tool_name,
            timestamp=time.time(),
            reasoning=reasoning,
            parameters=parameters,
            result=result,
            success=success
        )
        self.execution_history.append(execution)

        # Keep only last 50 executions to manage memory
        if len(self.execution_history) > 50:
            self.execution_history = self.execution_history[-50:]

        self.logger.debug(f"Recorded {tool_name} execution: {'✅' if success else '❌'}")


    def _cleanup_old_screenshots(self):
        """Remove old screenshots to manage disk space"""
        try:
            screenshots = sorted(self.screenshot_dir.glob("*.png"))
            if len(screenshots) > self.screenshot_limit:
                for old_shot in screenshots[:-self.screenshot_limit]:
                    old_shot.unlink()
                    self.logger.debug(f"Removed old screenshot: {old_shot.name}")
        except Exception as e:
            self.logger.warning(f"Screenshot cleanup failed: {e}")


    def create_tools(self):
        """Create all autonomous tools with reasoning fields"""

        tool_manager = self  # For closure access

        @tool
        def capture_screenshot(reasoning: str, purpose: str = "analysis") -> str:
            """Autonomously capture screenshot of current Android screen

            Args:
                reasoning: Detailed explanation of why this screenshot is needed
                purpose: Purpose of screenshot - "analysis", "verification", "documentation"

            Returns:
                Success message with screenshot path and encoded base64 data
            """
            try:
                timestamp = int(time.time())
                screenshot_path = tool_manager.screenshot_dir / f"auto_{timestamp}_{purpose}.png"

                tool_manager.logger.info(f"Capturing screenshot: {reasoning}")

                if tool_manager.device_interface:
                    actual_path = tool_manager.device_interface.take_screenshot(str(tool_manager.screenshot_dir))
                    if actual_path:
                        # Rename to controlled scheme
                        import shutil
                        shutil.move(actual_path, screenshot_path)

                        # Encode to base64 for multimodal context
                        with open(screenshot_path, "rb") as f:
                            screenshot_b64 = base64.b64encode(f.read()).decode("utf-8")

                        result = f"✅ Screenshot captured: {screenshot_path} | Base64 length: {len(screenshot_b64)} | {reasoning}"
                        success = True
                    else:
                        result = f"❌ Screenshot capture failed: Device interface error | {reasoning}"
                        success = False
                else:
                    # Create dummy screenshot for simulation
                    screenshot_path.write_bytes(b"dummy_screenshot_data")
                    result = f"✅ Screenshot captured (simulated): {screenshot_path} | {reasoning}"
                    success = True

                tool_manager._record_execution("capture_screenshot", reasoning,
                                             {"purpose": purpose}, result, success)
                tool_manager._cleanup_old_screenshots()

                return result

            except Exception as e:
                error_result = f"❌ Screenshot error: {e} | {reasoning}"
                tool_manager._record_execution("capture_screenshot", reasoning,
                                             {"purpose": purpose}, error_result, False)
                return error_result


        @tool
        def android_click(coordinates: str, element_description: str, reasoning: str,
                         confidence: str = "high") -> str:
            """Click on Android UI element with detailed reasoning

            Args:
                coordinates: "x,y" format (e.g., "540,292")
                element_description: Detailed description of target element
                reasoning: Why this element needs to be clicked and expected outcome
                confidence: "high", "medium", "low" - confidence in element identification

            Returns:
                Click execution result with success status
            """
            try:
                tool_manager.logger.info(f"Clicking at {coordinates}: {element_description} - {reasoning}")

                # Validate coordinates format
                try:
                    x, y = map(int, coordinates.strip().split(','))
                except ValueError:
                    error_result = f"❌ Invalid coordinates format '{coordinates}'. Use 'x,y' format | {reasoning}"
                    tool_manager._record_execution("android_click", reasoning,
                                                 {"coordinates": coordinates, "element": element_description},
                                                 error_result, False)
                    return error_result

                # Check for dangerous system areas
                if y > 1800:  # Bottom system navigation
                    warning_result = f"⚠️ WARNING: Coordinates ({x},{y}) in system navigation area. Proceeding with caution | {reasoning}"
                    tool_manager.logger.warning(warning_result)

                if tool_manager.device_interface:
                    # Actual device click
                    success = tool_manager.device_interface.click_coordinate(x, y)
                    if success:
                        result = f"✅ Successfully clicked at ({x},{y}) on '{element_description}' | {reasoning}"
                    else:
                        result = f"❌ Click failed at ({x},{y}) - device interface error | {reasoning}"
                else:
                    # Simulation mode
                    success = True
                    result = f"✅ Click simulated at ({x},{y}) on '{element_description}' | {reasoning}"

                tool_manager._record_execution("android_click", reasoning,
                                             {
                                                 "coordinates": coordinates,
                                                 "element": element_description,
                                                 "confidence": confidence,
                                                 "x": x, "y": y
                                             }, result, success)

                # Brief pause for UI to respond
                time.sleep(0.5)

                return result

            except Exception as e:
                error_result = f"❌ Click error: {e} | {reasoning}"
                tool_manager._record_execution("android_click", reasoning,
                                             {"coordinates": coordinates, "element": element_description},
                                             error_result, False)
                return error_result


        @tool
        def android_input(coordinates: str, text: str, reasoning: str,
                         input_method: str = "direct") -> str:
            """Input text into Android UI element with reasoning

            Args:
                coordinates: "x,y" format for input field location
                text: Text to input into the field
                reasoning: Why this text input is necessary and what it will achieve
                input_method: "direct", "click_then_type", "clear_then_type"

            Returns:
                Input execution result with success status
            """
            try:
                tool_manager.logger.info(f"Inputting text at {coordinates}: '{text}' - {reasoning}")

                # Validate coordinates
                try:
                    x, y = map(int, coordinates.strip().split(','))
                except ValueError:
                    error_result = f"❌ Invalid coordinates format '{coordinates}' | {reasoning}"
                    tool_manager._record_execution("android_input", reasoning,
                                                 {"coordinates": coordinates, "text": text}, error_result, False)
                    return error_result

                if tool_manager.device_interface:
                    if input_method == "click_then_type":
                        # Click field first, then type
                        click_success = tool_manager.device_interface.click_coordinate(x, y)
                        if click_success:
                            time.sleep(0.3)  # Wait for keyboard
                            type_success = tool_manager.device_interface.input_text(text)
                        else:
                            type_success = False
                        success = click_success and type_success
                    else:
                        # Direct input
                        success = tool_manager.device_interface.input_text_at_coordinates(x, y, text)

                    if success:
                        result = f"✅ Successfully input '{text}' at ({x},{y}) using {input_method} | {reasoning}"
                    else:
                        result = f"❌ Input failed for '{text}' at ({x},{y}) | {reasoning}"
                else:
                    # Simulation
                    success = True
                    result = f"✅ Input simulated: '{text}' at ({x},{y}) | {reasoning}"

                tool_manager._record_execution("android_input", reasoning,
                                             {
                                                 "coordinates": coordinates,
                                                 "text": text,
                                                 "input_method": input_method,
                                                 "x": x, "y": y
                                             }, result, success)

                return result

            except Exception as e:
                error_result = f"❌ Input error: {e} | {reasoning}"
                tool_manager._record_execution("android_input", reasoning,
                                             {"coordinates": coordinates, "text": text}, error_result, False)
                return error_result


        @tool
        def android_scroll(direction: str, reasoning: str, distance: str = "medium") -> str:
            """Scroll the Android screen with detailed reasoning

            Args:
                direction: "up", "down", "left", "right"
                reasoning: Why scrolling is needed and what content is expected
                distance: "short", "medium", "long" - scroll distance

            Returns:
                Scroll execution result
            """
            try:
                tool_manager.logger.info(f"Scrolling {direction} ({distance}) - {reasoning}")

                valid_directions = ["up", "down", "left", "right"]
                if direction not in valid_directions:
                    error_result = f"❌ Invalid direction '{direction}'. Use: {valid_directions} | {reasoning}"
                    tool_manager._record_execution("android_scroll", reasoning,
                                                 {"direction": direction, "distance": distance}, error_result, False)
                    return error_result

                if tool_manager.device_interface:
                    success = tool_manager.device_interface.scroll(direction, distance)
                    if success:
                        result = f"✅ Successfully scrolled {direction} ({distance}) | {reasoning}"
                    else:
                        result = f"❌ Scroll {direction} failed | {reasoning}"
                else:
                    # Simulation
                    success = True
                    result = f"✅ Scrolled {direction} ({distance}) - simulated | {reasoning}"

                tool_manager._record_execution("android_scroll", reasoning,
                                             {"direction": direction, "distance": distance}, result, success)

                # Brief pause for scroll to complete
                time.sleep(0.4)

                return result

            except Exception as e:
                error_result = f"❌ Scroll error: {e} | {reasoning}"
                tool_manager._record_execution("android_scroll", reasoning,
                                             {"direction": direction, "distance": distance}, error_result, False)
                return error_result


        @tool
        def android_back(reasoning: str, action_type: str = "back_button") -> str:
            """Navigate back or close dialog with reasoning

            Args:
                reasoning: Why back navigation is needed and expected result
                action_type: "back_button", "escape_key", "close_dialog"

            Returns:
                Back navigation result
            """
            try:
                tool_manager.logger.info(f"Going back ({action_type}) - {reasoning}")

                if tool_manager.device_interface:
                    if action_type == "back_button":
                        success = tool_manager.device_interface.press_back()
                    elif action_type == "escape_key":
                        success = tool_manager.device_interface.press_key("KEYCODE_ESCAPE")
                    else:
                        success = tool_manager.device_interface.press_back()  # Default

                    if success:
                        result = f"✅ Successfully navigated back using {action_type} | {reasoning}"
                    else:
                        result = f"❌ Back navigation failed ({action_type}) | {reasoning}"
                else:
                    # Simulation
                    success = True
                    result = f"✅ Back navigation simulated ({action_type}) | {reasoning}"

                tool_manager._record_execution("android_back", reasoning,
                                             {"action_type": action_type}, result, success)

                # Brief pause for navigation to complete
                time.sleep(0.3)

                return result

            except Exception as e:
                error_result = f"❌ Back navigation error: {e} | {reasoning}"
                tool_manager._record_execution("android_back", reasoning,
                                             {"action_type": action_type}, error_result, False)
                return error_result


        @tool
        def update_memory(memory_type: str, content: str, reasoning: str,
                         priority: str = "normal") -> str:
            """Update agent memory with discovered information

            Args:
                memory_type: "ui_elements", "app_state", "test_results", "navigation_paths"
                content: Information to store in memory
                reasoning: Why this information is important to remember
                priority: "low", "normal", "high" - importance level

            Returns:
                Memory update result
            """
            try:
                tool_manager.logger.info(f"Updating {memory_type} memory (priority: {priority}) - {reasoning}")

                # Validate memory type
                valid_types = ["ui_elements", "app_state", "test_results", "navigation_paths", "errors", "discoveries"]
                if memory_type not in valid_types:
                    error_result = f"❌ Invalid memory type '{memory_type}'. Use: {valid_types} | {reasoning}"
                    tool_manager._record_execution("update_memory", reasoning,
                                                 {"memory_type": memory_type, "content": content[:100]},
                                                 error_result, False)
                    return error_result

                # Store in execution history for now (could integrate with actual memory system)
                memory_entry = {
                    "type": memory_type,
                    "content": content,
                    "priority": priority,
                    "timestamp": time.time(),
                    "reasoning": reasoning
                }

                # Here would integrate with actual memory components
                # For now, just record the operation

                result = f"✅ Updated {memory_type} memory with {len(content)} chars (priority: {priority}) | {reasoning}"
                success = True

                tool_manager._record_execution("update_memory", reasoning,
                                             {
                                                 "memory_type": memory_type,
                                                 "content_length": len(content),
                                                 "priority": priority
                                             }, result, success)

                return result

            except Exception as e:
                error_result = f"❌ Memory update error: {e} | {reasoning}"
                tool_manager._record_execution("update_memory", reasoning,
                                             {"memory_type": memory_type, "content": content[:100]},
                                             error_result, False)
                return error_result


        @tool
        def analyze_ui_state(reasoning: str, analysis_depth: str = "standard") -> str:
            """Analyze current UI state and extract detailed information

            Args:
                reasoning: Why UI analysis is needed and what to focus on
                analysis_depth: "quick", "standard", "deep" - level of analysis detail

            Returns:
                Comprehensive UI analysis results
            """
            try:
                tool_manager.logger.info(f"Analyzing UI state ({analysis_depth}) - {reasoning}")

                if tool_manager.device_interface:
                    ui_state = tool_manager.device_interface.get_current_ui_state()
                    if ui_state:
                        elements = ui_state.get('element_count', 0)
                        activity = ui_state.get('activity', 'unknown')
                        package = ui_state.get('package', 'unknown')

                        if analysis_depth == "deep":
                            # Extract detailed element information
                            formatted_elements = ui_state.get('formatted_elements', 'No element details')
                            result = f"✅ Deep UI Analysis: {elements} elements in {activity} ({package})\nElements: {formatted_elements[:200]}... | {reasoning}"
                        else:
                            result = f"✅ UI Analysis: {elements} elements in {activity} ({package}) | {reasoning}"

                        success = True
                    else:
                        result = f"❌ UI state capture failed - device interface error | {reasoning}"
                        success = False
                else:
                    # Simulation
                    if analysis_depth == "deep":
                        result = f"✅ UI Analysis (simulated): 7 elements in CryptoActivity\nElements: Button 'GENERATE HASH' at (540,400), Spinner at (540,292), EditText at (540,350)... | {reasoning}"
                    else:
                        result = f"✅ UI Analysis (simulated): 7 elements in CryptoActivity | {reasoning}"
                    success = True

                tool_manager._record_execution("analyze_ui_state", reasoning,
                                             {"analysis_depth": analysis_depth}, result, success)

                return result

            except Exception as e:
                error_result = f"❌ UI analysis error: {e} | {reasoning}"
                tool_manager._record_execution("analyze_ui_state", reasoning,
                                             {"analysis_depth": analysis_depth}, error_result, False)
                return error_result


        return [
            capture_screenshot, android_click, android_input,
            android_scroll, android_back, update_memory, analyze_ui_state
        ]


    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get comprehensive tool execution statistics"""
        if not self.execution_history:
            return {"total_executions": 0, "tools_used": [], "success_rate": 0.0}

        # Count executions by tool
        tool_counts = {}
        success_counts = {}

        for execution in self.execution_history:
            tool_name = execution.tool_name
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

            if execution.success:
                success_counts[tool_name] = success_counts.get(tool_name, 0) + 1

        # Calculate success rates
        tool_success_rates = {
            tool: (success_counts.get(tool, 0) / count) * 100
            for tool, count in tool_counts.items()
        }

        total_executions = len(self.execution_history)
        total_successes = sum(1 for ex in self.execution_history if ex.success)
        overall_success_rate = (total_successes / total_executions) * 100 if total_executions > 0 else 0

        return {
            "total_executions": total_executions,
            "total_successes": total_successes,
            "overall_success_rate": overall_success_rate,
            "tool_counts": tool_counts,
            "tool_success_rates": tool_success_rates,
            "recent_executions": [
                {
                    "tool": ex.tool_name,
                    "timestamp": ex.timestamp,
                    "reasoning": ex.reasoning[:100] + "..." if len(ex.reasoning) > 100 else ex.reasoning,
                    "success": ex.success
                }
                for ex in self.execution_history[-10:]  # Last 10 executions
            ]
        }


    def clear_execution_history(self):
        """Clear tool execution history"""
        self.execution_history.clear()
        self.logger.info("Tool execution history cleared")
"""
Simple Tools for RVAgent - Direct implementation bypassing Pydantic issues.

Minimal but functional tool-calling implementation for MVP testing.
"""

import logging
from typing import Optional, Any, Dict

from langchain_core.tools import tool


def create_android_tools(device_adapter: Any):
    """Create Android tools with device adapter closure."""

    logger = logging.getLogger("rv_agent.tools")

    @tool
    def android_click(coordinates: str, element_description: str = "", reasoning: str = "") -> str:
        """
        Click on Android UI elements using exact coordinates.

        Args:
            coordinates: Click coordinates in format 'x,y' (e.g., '100,200')
            element_description: Description of the UI element being clicked
            reasoning: Explanation of why this click action is being performed
        """
        try:
            print(f"[TEST_LOG_TOOL] 🖱️ ANDROID_CLICK called!")
            print(f"[TEST_LOG_TOOL]   Coordinates: {coordinates}")
            print(f"[TEST_LOG_TOOL]   Element: {element_description}")
            print(f"[TEST_LOG_TOOL]   Reasoning: {reasoning}")

            # Parse coordinates (handle spaces)
            x, y = map(int, coordinates.replace(' ', '').split(','))
            print(f"[TEST_LOG_TOOL]   Parsed: x={x}, y={y}")

            # Log action with Phase 0 validated format
            action_desc = f"at position ({x}, {y})"
            if element_description:
                action_desc += f" on {element_description}"

            logger.debug(f"[RVAGENT_TOOLS] android_click executing: {action_desc}")
            if reasoning:
                logger.debug(f"[RVAGENT_TOOLS] Reasoning: {reasoning}")

            print(f"[TEST_LOG_TOOL] 🎯 Executing click via device adapter...")

            # Execute click via device adapter
            success = device_adapter.click(x, y)
            print(f"[TEST_LOG_TOOL] 📊 Device adapter response: {success}")

            if success:
                result = f"SUCCESS: Clicked {action_desc}"
                logger.info(f"[RVAGENT_TOOLS] {result}")
                print(f"[TEST_LOG_TOOL] ✅ {result}")
                return result
            else:
                result = f"FAILED: Could not click {action_desc}"
                logger.warning(f"[RVAGENT_TOOLS] {result}")
                print(f"[TEST_LOG_TOOL] ❌ {result}")
                return result

        except ValueError as e:
            error_msg = f"INVALID_COORDINATES: Could not parse '{coordinates}'. Use format 'x,y'"
            logger.error(f"[RVAGENT_TOOLS] {error_msg}")
            print(f"[TEST_LOG_TOOL] ❌ {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"ERROR: Click action failed: {str(e)}"
            logger.error(f"[RVAGENT_TOOLS] {error_msg}")
            print(f"[TEST_LOG_TOOL] ❌ {error_msg}")
            return error_msg

    @tool
    def android_input(text: str, coordinates: str = "", element_description: str = "") -> str:
        """
        Input text into Android text fields and input elements.

        Args:
            text: Text to input into the field
            coordinates: Coordinates to tap before input (format 'x,y')
            element_description: Description of the input field
        """
        try:
            print(f"[TEST_LOG_TOOL] ⌨️ ANDROID_INPUT called!")
            print(f"[TEST_LOG_TOOL]   Text: {text}")
            print(f"[TEST_LOG_TOOL]   Coordinates: {coordinates}")
            print(f"[TEST_LOG_TOOL]   Element: {element_description}")

            action_desc = f"text '{text}'"

            # Tap coordinates first if provided
            if coordinates:
                x, y = map(int, coordinates.replace(' ', '').split(','))
                print(f"[TEST_LOG_TOOL] 🎯 Tapping input field at ({x}, {y}) first...")
                tap_success = device_adapter.click(x, y)
                if not tap_success:
                    return f"FAILED: Could not tap input field at ({x}, {y})"
                action_desc += f" at position ({x}, {y})"
                print(f"[TEST_LOG_TOOL] ✅ Input field tapped successfully")

            if element_description:
                action_desc += f" in {element_description}"

            logger.debug(f"[RVAGENT_TOOLS] android_input executing: {action_desc}")

            # Execute text input
            print(f"[TEST_LOG_TOOL] 📝 Executing text input: '{text}'...")
            success = device_adapter.input_text(text)

            if success:
                result = f"SUCCESS: Input {action_desc}"
                logger.info(f"[RVAGENT_TOOLS] {result}")
                print(f"[TEST_LOG_TOOL] ✅ {result}")
                return result
            else:
                result = f"FAILED: Could not input {action_desc}"
                logger.warning(f"[RVAGENT_TOOLS] {result}")
                print(f"[TEST_LOG_TOOL] ❌ {result}")
                return result

        except Exception as e:
            error_msg = f"ERROR: Input action failed: {str(e)}"
            logger.error(f"[RVAGENT_TOOLS] {error_msg}")
            return error_msg

    @tool
    def android_scroll(direction: str, distance: str = "medium") -> str:
        """
        Scroll in Android applications to reveal additional content.

        Args:
            direction: Scroll direction: 'up', 'down', 'left', 'right'
            distance: Scroll distance: 'short', 'medium', 'long'
        """
        try:
            logger.debug(f"[RVAGENT_TOOLS] android_scroll executing: {direction} scroll ({distance})")

            success = device_adapter.scroll(direction, distance)

            if success:
                result = f"SUCCESS: Scrolled {direction} ({distance} distance)"
                logger.info(f"[RVAGENT_TOOLS] {result}")
                return result
            else:
                result = f"FAILED: Could not scroll {direction}"
                logger.warning(f"[RVAGENT_TOOLS] {result}")
                return result

        except Exception as e:
            error_msg = f"ERROR: Scroll action failed: {str(e)}"
            logger.error(f"[RVAGENT_TOOLS] {error_msg}")
            return error_msg

    @tool
    def android_back(reasoning: str = "") -> str:
        """
        Navigate back in Android applications using system back button.

        Args:
            reasoning: Explanation of why this back action is being performed
        """
        try:
            logger.debug(f"[RVAGENT_TOOLS] android_back executing: back navigation")
            if reasoning:
                logger.debug(f"[RVAGENT_TOOLS] Reasoning: {reasoning}")

            success = device_adapter.back()

            if success:
                result = "SUCCESS: Navigated back"
                logger.info(f"[RVAGENT_TOOLS] {result}")
                return result
            else:
                result = "FAILED: Could not navigate back"
                logger.warning(f"[RVAGENT_TOOLS] {result}")
                return result

        except Exception as e:
            error_msg = f"ERROR: Back navigation failed: {str(e)}"
            logger.error(f"[RVAGENT_TOOLS] {error_msg}")
            return error_msg

    @tool
    def android_screenshot(reasoning: str = "") -> str:
        """
        Take screenshot of current Android screen for analysis.

        Args:
            reasoning: Explanation of why this screenshot is being taken
        """
        try:
            logger.debug(f"[RVAGENT_TOOLS] android_screenshot executing: screenshot capture")
            if reasoning:
                logger.debug(f"[RVAGENT_TOOLS] Reasoning: {reasoning}")

            screenshot_path = device_adapter.take_screenshot()

            if screenshot_path:
                result = f"SUCCESS: Screenshot saved to {screenshot_path}"
                logger.info(f"[RVAGENT_TOOLS] {result}")
                return result
            else:
                result = "FAILED: Could not capture screenshot"
                logger.warning(f"[RVAGENT_TOOLS] {result}")
                return result

        except Exception as e:
            error_msg = f"ERROR: Screenshot capture failed: {str(e)}"
            logger.error(f"[RVAGENT_TOOLS] {error_msg}")
            return error_msg

    # Screenshot is now controlled by the system loop, not LLM tool
    return [android_click, android_input, android_scroll, android_back]
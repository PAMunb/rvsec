"""
Simple Tools with Explanation for validation - Enhanced version with reasoning capture.

This version includes an 'explanation' parameter to understand LLM decision-making.
"""

import logging
from typing import Optional, Any, Dict
from langchain_core.tools import tool


def create_android_tools(device_adapter: Any):
    """Create Android tools with device adapter closure and explanation support."""

    logger = logging.getLogger("rv_agent.validation.tools")

    @tool
    def android_click(coordinates: str, element_description: str = "", explanation: str = "") -> str:
        """
        Click on Android UI elements using exact coordinates.

        Args:
            coordinates: Click coordinates in format 'x,y' (e.g., '540,273')
            element_description: Description of the UI element being clicked (e.g., 'MESSAGE DIGEST button')
            explanation: Detailed explanation of why this element was chosen and these coordinates were selected
        """
        try:
            print(f"\n[TOOL_CALL] 🖱️ ANDROID_CLICK")
            print(f"  📍 Coordinates: {coordinates}")
            print(f"  🎯 Element: {element_description}")
            print(f"  💭 Explanation: {explanation}")

            # Parse coordinates
            x, y = map(int, coordinates.split(','))
            print(f"  📐 Parsed: x={x}, y={y}")

            # Log the reasoning for analysis
            logger.info(f"[REASONING] Click at ({x},{y}): {explanation}")

            # Execute click via device adapter
            success = device_adapter.click(x, y)

            if success:
                return f"Successfully clicked at ({x}, {y}) on {element_description}. Action was executed."
            else:
                return f"Click at ({x}, {y}) was registered but may have missed the target."

        except ValueError as e:
            error_msg = f"Invalid coordinate format: {coordinates}. Use 'x,y' format (e.g., '540,273')"
            print(f"  ❌ Error: {error_msg}")
            logger.error(f"[ERROR] {error_msg}")
            return error_msg

        except Exception as e:
            error_msg = f"Click failed: {str(e)}"
            print(f"  ❌ Error: {error_msg}")
            logger.error(f"[ERROR] {error_msg}")
            return error_msg

    @tool
    def android_input(text: str, element_description: str = "", explanation: str = "") -> str:
        """
        Input text into Android UI text fields.

        Args:
            text: Text to input into the field
            element_description: Description of the text field (e.g., 'password input field')
            explanation: Reasoning for choosing this input field and the text being entered
        """
        try:
            print(f"\n[TOOL_CALL] ⌨️ ANDROID_INPUT")
            print(f"  📝 Text: '{text}'")
            print(f"  🎯 Element: {element_description}")
            print(f"  💭 Explanation: {explanation}")

            logger.info(f"[REASONING] Input '{text}' to {element_description}: {explanation}")

            # Execute input via device adapter
            success = device_adapter.input_text(text, element_description)

            if success:
                return f"Successfully input '{text}' to {element_description}"
            else:
                return f"Failed to input text to {element_description}"

        except Exception as e:
            error_msg = f"Input failed: {str(e)}"
            print(f"  ❌ Error: {error_msg}")
            logger.error(f"[ERROR] {error_msg}")
            return error_msg

    @tool
    def android_scroll(direction: str, start_coords: str = "540,1000", end_coords: str = "540,500",
                      explanation: str = "") -> str:
        """
        Scroll the Android screen in a specified direction.

        Args:
            direction: Scroll direction ('up', 'down', 'left', 'right')
            start_coords: Starting coordinates for scroll in format 'x,y' (default: '540,1000')
            end_coords: Ending coordinates for scroll in format 'x,y' (default: '540,500')
            explanation: Reasoning for scrolling and why this direction was chosen
        """
        try:
            print(f"\n[TOOL_CALL] 📜 ANDROID_SCROLL")
            print(f"  ↕️ Direction: {direction}")
            print(f"  📍 Start: {start_coords}")
            print(f"  📍 End: {end_coords}")
            print(f"  💭 Explanation: {explanation}")

            logger.info(f"[REASONING] Scroll {direction}: {explanation}")

            # Parse coordinates
            start_x, start_y = map(int, start_coords.split(','))
            end_x, end_y = map(int, end_coords.split(','))

            # Execute scroll via device adapter
            success = device_adapter.scroll(direction, start_x, start_y, end_x, end_y)

            if success:
                return f"Successfully scrolled {direction} from ({start_x},{start_y}) to ({end_x},{end_y})"
            else:
                return f"Scroll {direction} failed"

        except ValueError as e:
            error_msg = f"Invalid coordinate format. Use 'x,y' format"
            print(f"  ❌ Error: {error_msg}")
            return error_msg

        except Exception as e:
            error_msg = f"Scroll failed: {str(e)}"
            print(f"  ❌ Error: {error_msg}")
            return error_msg

    @tool
    def android_back(explanation: str = "") -> str:
        """
        Press the Android back button.

        Args:
            explanation: Reasoning for pressing back button (e.g., 'returning to main menu', 'exiting dialog')
        """
        try:
            print(f"\n[TOOL_CALL] ⬅️ ANDROID_BACK")
            print(f"  💭 Explanation: {explanation}")

            logger.info(f"[REASONING] Back button: {explanation}")

            # Execute back via device adapter
            success = device_adapter.back()

            if success:
                return "Successfully pressed back button"
            else:
                return "Back button press failed"

        except Exception as e:
            error_msg = f"Back button failed: {str(e)}"
            print(f"  ❌ Error: {error_msg}")
            return error_msg

    @tool
    def android_analyze_spinner(element_description: str = "", coordinates: str = "",
                               explanation: str = "") -> str:
        """
        Special tool for analyzing and interacting with Spinner/Dropdown elements.

        Args:
            element_description: Description of the spinner element
            coordinates: Coordinates of the spinner in format 'x,y'
            explanation: Analysis of why this might be a spinner and how to interact with it
        """
        try:
            print(f"\n[TOOL_CALL] 📋 ANDROID_ANALYZE_SPINNER")
            print(f"  🎯 Element: {element_description}")
            print(f"  📍 Coordinates: {coordinates}")
            print(f"  💭 Explanation: {explanation}")

            logger.info(f"[REASONING] Spinner analysis at {coordinates}: {explanation}")

            # This is a special analysis tool to help identify spinner interactions
            if coordinates:
                x, y = map(int, coordinates.split(','))
                # Try clicking on the spinner
                success = device_adapter.click(x, y)
                if success:
                    return f"Spinner/Dropdown at ({x},{y}) was clicked. It should now show options."
                else:
                    return f"Failed to interact with spinner at ({x},{y})"
            else:
                return "Please provide coordinates for the spinner element"

        except Exception as e:
            error_msg = f"Spinner analysis failed: {str(e)}"
            print(f"  ❌ Error: {error_msg}")
            return error_msg

    # Return all tools
    return [
        android_click,
        android_input,
        android_scroll,
        android_back,
        android_analyze_spinner
    ]


def create_validation_tools(device_adapter: Any):
    """
    Create enhanced validation tools with detailed reasoning capture.

    This version is specifically for validation and testing, with extra
    logging and analysis capabilities.
    """
    tools = create_android_tools(device_adapter)

    # Add metadata for validation
    for tool in tools:
        tool.metadata = {
            "requires_coordinates": tool.name in ["android_click", "android_scroll", "android_analyze_spinner"],
            "captures_reasoning": True,
            "validation_enabled": True
        }

    return tools
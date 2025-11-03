"""
Simplified Android Tools for RVAgent Tool-Calling Validation.

Using simpler approach without complex Pydantic schemas to test tool-calling flow.
"""
import time
import logging
from typing import Optional, Any
from langchain_core.tools import tool


@tool
def android_click(coordinates: str, element_description: str = "", reasoning: str = "") -> str:
    """
    Click on Android UI elements using exact coordinates.

    Args:
        coordinates: Click coordinates in format 'x,y' (e.g., '100,200')
        element_description: Description of the UI element being clicked
        reasoning: Explanation of why this click is being performed

    Returns:
        Result message indicating success or failure

    Examples:
        android_click("245,678", "login button", "tap to login")
    """
    logger = logging.getLogger("rv_agent.tools.android_click")

    try:
        # Parse coordinates
        x, y = map(int, coordinates.split(','))

        # Log action with Phase 0 validated format
        action_desc = f"at position ({x}, {y})"
        if element_description:
            action_desc += f" on {element_description}"

        logger.info(f"[MOCK_TOOLS] AndroidClick executing: {action_desc}")
        if reasoning:
            logger.info(f"[MOCK_TOOLS] Reasoning: {reasoning}")

        # Simulate processing delay
        time.sleep(0.1)

        # Simulate success/failure based on coordinates (for testing)
        if x < 0 or y < 0 or x > 1000 or y > 2000:
            result = f"FAILED: Invalid coordinates {action_desc} (out of screen bounds)"
            logger.warning(f"[MOCK_TOOLS] {result}")
            return result

        result = f"SUCCESS: Clicked {action_desc}"
        logger.info(f"[MOCK_TOOLS] {result}")
        return result

    except ValueError as e:
        error_msg = f"INVALID_COORDINATES: Could not parse '{coordinates}'. Use format 'x,y'"
        logger.error(f"[MOCK_TOOLS] {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"ERROR: Click action failed: {str(e)}"
        logger.error(f"[MOCK_TOOLS] {error_msg}")
        return error_msg


@tool
def android_input(text: str, coordinates: str = "", element_description: str = "") -> str:
    """
    Input text into Android text fields and editable elements.

    Args:
        text: Text to input into the field
        coordinates: Optional coordinates to tap before input (format 'x,y')
        element_description: Description of the input field

    Returns:
        Result message indicating success or failure

    Examples:
        android_input("user@example.com", "200,400", "username field")
    """
    logger = logging.getLogger("rv_agent.tools.android_input")

    try:
        action_desc = f"text '{text}'"

        # Simulate tapping coordinates first if provided
        if coordinates:
            x, y = map(int, coordinates.split(','))
            if x < 0 or y < 0 or x > 1000 or y > 2000:
                return f"FAILED: Could not tap input field at ({x}, {y}) - invalid coordinates"
            action_desc += f" at position ({x}, {y})"

        if element_description:
            action_desc += f" in {element_description}"

        logger.info(f"[MOCK_TOOLS] AndroidInput executing: {action_desc}")

        # Simulate processing delay
        time.sleep(0.1)

        # Simulate validation (reject very long text)
        if len(text) > 100:
            result = f"FAILED: Text too long ({len(text)} chars) for input field"
            logger.warning(f"[MOCK_TOOLS] {result}")
            return result

        result = f"SUCCESS: Input {action_desc}"
        logger.info(f"[MOCK_TOOLS] {result}")
        return result

    except Exception as e:
        error_msg = f"ERROR: Input action failed: {str(e)}"
        logger.error(f"[MOCK_TOOLS] {error_msg}")
        return error_msg


@tool
def android_scroll(direction: str, distance: str = "medium") -> str:
    """
    Scroll in Android applications to reveal additional content.

    Args:
        direction: Scroll direction - 'up', 'down', 'left', 'right'
        distance: Scroll distance - 'short', 'medium', 'long'

    Returns:
        Result message indicating success or failure

    Examples:
        android_scroll("down", "medium")
    """
    logger = logging.getLogger("rv_agent.tools.android_scroll")

    try:
        # Validate direction
        valid_directions = ['up', 'down', 'left', 'right']
        if direction not in valid_directions:
            return f"FAILED: Invalid direction '{direction}'. Use: {', '.join(valid_directions)}"

        # Validate distance
        valid_distances = ['short', 'medium', 'long']
        if distance not in valid_distances:
            return f"FAILED: Invalid distance '{distance}'. Use: {', '.join(valid_distances)}"

        logger.info(f"[MOCK_TOOLS] AndroidScroll executing: {direction} scroll ({distance})")

        # Simulate processing delay
        time.sleep(0.1)

        result = f"SUCCESS: Scrolled {direction} ({distance} distance)"
        logger.info(f"[MOCK_TOOLS] {result}")
        return result

    except Exception as e:
        error_msg = f"ERROR: Scroll action failed: {str(e)}"
        logger.error(f"[MOCK_TOOLS] {error_msg}")
        return error_msg


@tool
def android_back(reasoning: str = "") -> str:
    """
    Navigate back in Android applications using system back button.

    Args:
        reasoning: Optional explanation for the back navigation

    Returns:
        Result message indicating success or failure

    Examples:
        android_back("close dialog and return to main screen")
    """
    logger = logging.getLogger("rv_agent.tools.android_back")

    try:
        logger.info(f"[MOCK_TOOLS] AndroidBack executing: back navigation")
        if reasoning:
            logger.info(f"[MOCK_TOOLS] Reasoning: {reasoning}")

        # Simulate processing delay
        time.sleep(0.1)

        result = "SUCCESS: Navigated back"
        logger.info(f"[MOCK_TOOLS] {result}")
        return result

    except Exception as e:
        error_msg = f"ERROR: Back navigation failed: {str(e)}"
        logger.error(f"[MOCK_TOOLS] {error_msg}")
        return error_msg


def get_simple_tools():
    """Get list of simple tools for testing."""
    return [android_click, android_input, android_scroll, android_back]


# Mock UI state for testing
MOCK_UI_STATE = """
CURRENT SCREEN: MainActivity (8 elements)

UI ELEMENTS:
1. [UNTESTED] Button "LOGIN" at position (245, 678) - clickable
2. [TESTED] TextView "Welcome" at position (400, 200) - not clickable
3. [UNTESTED] EditText "Username" at position (300, 450) - input field
4. [UNTESTED] EditText "Password" at position (300, 520) - input field
5. [UNTESTED] Button "REGISTER" at position (450, 678) - clickable
6. [UNTESTED] ImageView "Logo" at position (400, 100) - clickable
7. [TESTED] TextView "Version 1.0" at position (400, 800) - not clickable
8. [UNTESTED] Button "SETTINGS" at position (50, 50) - clickable

PRIORITY SUGGESTIONS: LOGIN button, Username field, Password field
"""


def get_mock_ui_state():
    """Get mock UI state for testing."""
    return MOCK_UI_STATE
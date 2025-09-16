"""
Mock Android Tools for RVAgent Tool-Calling Validation Prototype.

Simple tools implementation to validate tool-calling architecture without
device dependencies. These tools simulate Android interactions for testing.
"""
import time
import logging
from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class AndroidClickInput(BaseModel):
    """Input schema for AndroidClickTool."""
    coordinates: str = Field(
        description="Click coordinates in format 'x,y' (e.g., '100,200')",
        examples=["245,678", "400,300"]
    )
    element_description: Optional[str] = Field(
        default=None,
        description="Description of the UI element being clicked"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation of why this click is being performed"
    )


class MockAndroidClickTool(BaseTool):
    """
    Mock Android click tool for validation testing.

    Simulates clicking on Android UI elements with coordinate validation
    and success/failure scenarios for testing tool-calling flow.
    """
    name: str = "android_click"
    description: str = """
    Click on Android UI elements using exact coordinates.

    Use this tool to tap buttons, links, icons, or any clickable element.
    Provide coordinates from the UI description in format 'x,y'.

    Examples:
    - android_click(coordinates="245,678", reasoning="tap login button")
    - android_click(coordinates="400,300", element_description="submit button")
    """
    args_schema = AndroidClickInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger("rv_agent.tools.mock_click")
        self.click_count = 0

    def _run(self, coordinates: str, element_description: Optional[str] = None,
             reasoning: Optional[str] = None) -> str:
        """Execute mock click action."""
        try:
            # Parse coordinates
            x, y = map(int, coordinates.split(','))
            self.click_count += 1

            # Log action with Phase 0 validated format
            action_desc = f"at position ({x}, {y})"
            if element_description:
                action_desc += f" on {element_description}"

            self.logger.info(f"[MOCK_TOOLS] MockAndroidClickTool executing: {action_desc}")
            if reasoning:
                self.logger.info(f"[MOCK_TOOLS] Reasoning: {reasoning}")

            # Simulate processing delay
            time.sleep(0.1)

            # Simulate success/failure based on coordinates (for testing)
            if x < 0 or y < 0 or x > 1000 or y > 2000:
                result = f"FAILED: Invalid coordinates {action_desc} (out of screen bounds)"
                self.logger.warning(f"[MOCK_TOOLS] {result}")
                return result

            result = f"SUCCESS: Clicked {action_desc} (click #{self.click_count})"
            self.logger.info(f"[MOCK_TOOLS] {result}")
            return result

        except ValueError as e:
            error_msg = f"INVALID_COORDINATES: Could not parse '{coordinates}'. Use format 'x,y'"
            self.logger.error(f"[MOCK_TOOLS] {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"ERROR: Click action failed: {str(e)}"
            self.logger.error(f"[MOCK_TOOLS] {error_msg}")
            return error_msg

    async def _arun(self, *args, **kwargs) -> str:
        """Async version - delegate to sync implementation."""
        return self._run(*args, **kwargs)


class AndroidInputInput(BaseModel):
    """Input schema for AndroidInputTool."""
    text: str = Field(description="Text to input into the field")
    coordinates: Optional[str] = Field(
        default=None,
        description="Coordinates to tap before input (format 'x,y')"
    )
    element_description: Optional[str] = Field(
        default=None,
        description="Description of the input field"
    )


class MockAndroidInputTool(BaseTool):
    """Mock Android input tool for validation testing."""
    name: str = "android_input"
    description: str = """
    Input text into Android text fields, search boxes, and editable elements.

    Use this tool to type text, enter search queries, fill forms.
    Optionally provide coordinates to tap the field first.

    Examples:
    - android_input(text="user@example.com", coordinates="200,400")
    - android_input(text="search query", element_description="search box")
    """
    args_schema = AndroidInputInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger("rv_agent.tools.mock_input")
        self.input_count = 0

    def _run(self, text: str, coordinates: Optional[str] = None,
             element_description: Optional[str] = None) -> str:
        """Execute mock text input."""
        try:
            self.input_count += 1
            action_desc = f"text '{text}'"

            # Simulate tapping coordinates first if provided
            if coordinates:
                x, y = map(int, coordinates.split(','))
                if x < 0 or y < 0 or x > 1000 or y > 2000:
                    return f"FAILED: Could not tap input field at ({x}, {y}) - invalid coordinates"
                action_desc += f" at position ({x}, {y})"

            if element_description:
                action_desc += f" in {element_description}"

            self.logger.info(f"[MOCK_TOOLS] MockAndroidInputTool executing: {action_desc}")

            # Simulate processing delay
            time.sleep(0.1)

            # Simulate validation (reject very long text)
            if len(text) > 100:
                result = f"FAILED: Text too long ({len(text)} chars) for input field"
                self.logger.warning(f"[MOCK_TOOLS] {result}")
                return result

            result = f"SUCCESS: Input {action_desc} (input #{self.input_count})"
            self.logger.info(f"[MOCK_TOOLS] {result}")
            return result

        except Exception as e:
            error_msg = f"ERROR: Input action failed: {str(e)}"
            self.logger.error(f"[MOCK_TOOLS] {error_msg}")
            return error_msg

    async def _arun(self, *args, **kwargs) -> str:
        return self._run(*args, **kwargs)


class AndroidScrollInput(BaseModel):
    """Input schema for AndroidScrollTool."""
    direction: str = Field(
        description="Scroll direction: 'up', 'down', 'left', 'right'",
        pattern="^(up|down|left|right)$"
    )
    distance: str = Field(
        default="medium",
        description="Scroll distance: 'short', 'medium', 'long'",
        pattern="^(short|medium|long)$"
    )


class MockAndroidScrollTool(BaseTool):
    """Mock Android scroll tool for validation testing."""
    name: str = "android_scroll"
    description: str = """
    Scroll in Android applications to reveal additional content.

    Use this tool when content extends beyond screen boundaries.
    Supports vertical and horizontal scrolling.

    Examples:
    - android_scroll(direction="down", distance="medium")
    - android_scroll(direction="up", distance="short")
    """
    args_schema = AndroidScrollInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger("rv_agent.tools.mock_scroll")
        self.scroll_count = 0

    def _run(self, direction: str, distance: str = "medium") -> str:
        """Execute mock scroll action."""
        try:
            self.scroll_count += 1

            self.logger.info(f"[MOCK_TOOLS] MockAndroidScrollTool executing: {direction} scroll ({distance})")

            # Simulate processing delay
            time.sleep(0.1)

            result = f"SUCCESS: Scrolled {direction} ({distance} distance) - scroll #{self.scroll_count}"
            self.logger.info(f"[MOCK_TOOLS] {result}")
            return result

        except Exception as e:
            error_msg = f"ERROR: Scroll action failed: {str(e)}"
            self.logger.error(f"[MOCK_TOOLS] {error_msg}")
            return error_msg

    async def _arun(self, *args, **kwargs) -> str:
        return self._run(*args, **kwargs)


class MockAndroidBackTool(BaseTool):
    """Mock Android back navigation tool for validation testing."""
    name: str = "android_back"
    description: str = """
    Navigate back in Android applications using system back button.

    Use this tool to go back to previous screens, close dialogs,
    or navigate up in app hierarchy.

    Examples:
    - android_back() - simple back navigation
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger("rv_agent.tools.mock_back")
        self.back_count = 0

    def _run(self, reasoning: Optional[str] = None) -> str:
        """Execute mock back navigation."""
        try:
            self.back_count += 1

            self.logger.info(f"[MOCK_TOOLS] MockAndroidBackTool executing: back navigation")
            if reasoning:
                self.logger.info(f"[MOCK_TOOLS] Reasoning: {reasoning}")

            # Simulate processing delay
            time.sleep(0.1)

            result = f"SUCCESS: Navigated back - back #{self.back_count}"
            self.logger.info(f"[MOCK_TOOLS] {result}")
            return result

        except Exception as e:
            error_msg = f"ERROR: Back navigation failed: {str(e)}"
            self.logger.error(f"[MOCK_TOOLS] {error_msg}")
            return error_msg

    async def _arun(self, reasoning: Optional[str] = None) -> str:
        return self._run(reasoning=reasoning)


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


def get_mock_tools():
    """Get list of mock tools for testing."""
    return [
        MockAndroidClickTool(),
        MockAndroidInputTool(),
        MockAndroidScrollTool(),
        MockAndroidBackTool()
    ]


def get_mock_ui_state():
    """Get mock UI state for testing."""
    return MOCK_UI_STATE
"""
Android tools for LangChain tool calling with SGLang/Qwen3-VL.

These are declarative tool definitions bound to the LLM for structured output.
The LLM outputs tool calls which are then executed by the ToolExecutor.

Coordinate System:
- Qwen3-VL outputs normalized coordinates [0, 1000)
- Converted to optimized image space: x=[0, 704], y=[0, 1248]
- Then converted to device space: x=[0, 1080], y=[0, 1920]

Based on validation from rvsec-vision-llm benchmark (2,847 tests):
- Model: Qwen/Qwen3-VL-4B-Instruct
- Server: SGLang with --tool-call-parser qwen
- Hit rate: 57.7%
- Tool call rate: 90.3%
- Average latency: ~1.8s per inference
"""

from typing import List

from langchain_core.tools import tool


@tool
def android_click(x: int, y: int, element_description: str = "") -> dict:
    """Click on a UI element at coordinates (x, y).

    The LLM should output coordinates in the optimized image space.
    Coordinates are converted to device space before execution.

    Args:
        x: X coordinate in optimized image space (0-704).
        y: Y coordinate in optimized image space (0-1248).
        element_description: Description of element being clicked.

    Returns:
        Success status with coordinates.
    """
    return {"success": True, "x": x, "y": y, "element_description": element_description}


@tool
def android_type_text(x: int, y: int, text: str, element_description: str = "") -> dict:
    """Type text into a text field at coordinates (x, y).

    First clicks on the text field, then types the text.

    Args:
        x: X coordinate of text field in optimized image space (0-704).
        y: Y coordinate of text field in optimized image space (0-1248).
        text: Text to type into the field.
        element_description: Description of the text field.

    Returns:
        Success status with coordinates and text.
    """
    return {
        "success": True,
        "x": x,
        "y": y,
        "text": text,
        "element_description": element_description,
    }


@tool
def android_long_click(x: int, y: int, element_description: str = "") -> dict:
    """Long press on element at coordinates (x, y).

    Useful for context menus, drag operations, or special interactions.

    Args:
        x: X coordinate in optimized image space (0-704).
        y: Y coordinate in optimized image space (0-1248).
        element_description: Description of element.

    Returns:
        Success status with coordinates.
    """
    return {"success": True, "x": x, "y": y, "element_description": element_description}


@tool
def android_swipe(direction: str, distance: str = "medium") -> dict:
    """Swipe in a direction to scroll or navigate.

    Args:
        direction: Swipe direction. One of: 'up', 'down', 'left', 'right'.
        distance: Swipe distance. One of: 'short', 'medium', 'long'.
            Defaults to 'medium'.

    Returns:
        Success status with swipe parameters.
    """
    return {"success": True, "direction": direction, "distance": distance}


@tool
def android_scroll(direction: str) -> dict:
    """Scroll the screen in a direction.

    Simpler alternative to swipe for basic scrolling.

    Args:
        direction: Scroll direction. One of: 'up', 'down'.

    Returns:
        Success status with direction.
    """
    return {"success": True, "direction": direction}


@tool
def android_back() -> dict:
    """Press the Android back button.

    Navigates to the previous screen or closes dialogs.

    Returns:
        Success status.
    """
    return {"success": True, "action": "back"}


@tool
def android_home() -> dict:
    """Press the Android home button.

    Returns to the home screen.

    Returns:
        Success status.
    """
    return {"success": True, "action": "home"}


def get_android_tools() -> List:
    """Get list of Android tools for LangChain tool binding.

    These tools are bound to the LLM using bind_tools() for structured output.
    The LLM will output tool calls which are then executed by ToolExecutor.

    Returns:
        List of tool objects ready for bind_tools().
    """
    return [
        android_click,
        android_type_text,
        android_long_click,
        android_swipe,
        android_scroll,
        android_back,
        android_home,
    ]

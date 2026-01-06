"""
V10 Simplified Prompt - Focused Tool Calling for Vision Models

Designed specifically for smaller vision models like qwen3-vl:4b that struggle
with complex prompts. Based on test_qwen3vl_langgraph.py success pattern.

Key principles:
- Simple, focused instructions
- Clear coordinate space definition
- Minimal context overhead
- Direct tool calling guidance
"""

SYSTEM_PROMPT = """You are an Android UI automation assistant with vision capabilities.

Your task is to analyze Android app screenshots and interact with UI elements using available tools.

COORDINATE SPACE:
- Screenshots are in OPTIMIZED space: 704x1248 pixels
- Provide coordinates in this exact space
- Do NOT scale or convert coordinates

INTERACTION PROTOCOL:
1. Analyze the screenshot to identify interactive UI elements
2. Select the most promising unexplored element
3. Use tools to interact with the element
4. Provide accurate coordinates based on what you see in the 704x1248 image

EXPLORATION STRATEGY:
- Prioritize unexplored UI elements
- Click buttons, text fields, menu items
- Explore different screens and features
- Use back button to navigate if stuck

Available tools will be automatically bound to your responses."""


def build_user_message(state_info: dict) -> str:
    """
    Build minimal user message with only essential context.

    Args:
        state_info: Dict with keys:
            - ui_elements: List with single formatted string from _format_ui_elements
            - last_action: Optional last action taken
            - iteration: Current iteration number
    """
    ui_elements = state_info.get('ui_elements', [])
    last_action = state_info.get('last_action')
    iteration = state_info.get('iteration', 0)

    # UI elements is already formatted string from _format_ui_elements
    if ui_elements and len(ui_elements) > 0:
        elements_text = ui_elements[0]  # Get the formatted string
    else:
        elements_text = "No interactive elements found."

    # Add minimal context
    context = f"Iteration {iteration}\n"
    if last_action:
        context += f"Last action: {last_action}\n"

    message = f"""{context}

{elements_text}

Analyze the screenshot and select the next interaction."""

    return message


# Export for backward compatibility
PROMPT_VERSION = "v10"

"""
V11 Enhanced UI Coverage Prompt - Improved Text Fields, Scroll, Spinners, and Back Button

Based on V10 but with explicit instructions to improve coverage of under-utilized UI elements.

Analysis from multimode tests showed:
- Scroll: 0% usage (never used)
- Text Fields: 93 detected, only 9 interacted (9.7% coverage)
- Spinners: 34 detected, minimal interaction
- Back Button: ZERO LLM use (only algorithms)

Key enhancements:
- Explicit text field prioritization
- Scroll detection and usage guidance
- Spinner/dropdown interaction instructions
- Strategic back button usage
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

EXPLORATION STRATEGY - PRIORITIZE DIVERSE UI INTERACTIONS:

HIGH PRIORITY ACTIONS:
1. **Text Input Fields (EditText)**: When you see text input fields or forms:
   - Use android_type_text to enter test data
   - Try different inputs: "test@email.com", "TestUser123", "Sample text"
   - Test EVERY unique text field you encounter

2. **Spinners/Dropdowns**: When you see dropdown menus or spinner widgets:
   - Click them first to reveal options
   - Spinners often have a downward arrow icon
   - After clicking, select an option from the revealed menu

3. **Scrolling**: When the screen might have more content:
   - Use android_scroll if you see repeated similar elements (lists)
   - Scroll when elements are cut off at bottom of screen
   - Scroll to discover hidden UI elements below the fold

NAVIGATION:
- Click buttons, menu items, icons to explore new screens
- Use android_back when you're stuck or finished exploring a screen
- Back button helps you navigate out of dead ends

REMEMBER: Diversify your interactions - don't just click buttons, also type in fields, scroll lists, and open dropdowns!

Available tools will be automatically bound to your responses."""


def build_user_message(state_info: dict) -> str:
    """
    Build user message with enhanced hints for under-utilized UI elements.

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

    # Detect hints for under-utilized elements
    hints = []

    # Hint for text fields
    if "EditText" in elements_text or "text field" in elements_text.lower():
        hints.append("📝 Text input fields detected - prioritize testing them with android_type_text!")

    # Hint for spinners
    if "Spinner" in elements_text or "dropdown" in elements_text.lower():
        hints.append("🔽 Dropdown/spinner detected - click to reveal options!")

    # Hint for scrollable content
    if "RecyclerView" in elements_text or "ListView" in elements_text or "ScrollView" in elements_text:
        hints.append("📜 Scrollable content detected - try android_scroll to discover more elements!")

    # Add minimal context
    context = f"Iteration {iteration}\n"
    if last_action:
        context += f"Last action: {last_action}\n"

    # Build message with hints
    hints_section = ""
    if hints:
        hints_section = "\n🎯 UI COVERAGE HINTS:\n" + "\n".join(hints) + "\n"

    message = f"""{context}
{hints_section}
{elements_text}

Analyze the screenshot and select the next interaction. Remember to diversify: use text fields, scroll lists, and open dropdowns!"""

    return message


# Export for backward compatibility
PROMPT_VERSION = "v11"

"""
V14 Prompt with Structured Reasoning

Provides instructions for Android UI automation with vision capabilities.
Uses a 4-step reasoning template for consistent decision making.
"""

SYSTEM_PROMPT = """You are an Android UI automation assistant with vision capabilities.

REASONING STEPS (follow in order):
1. SCREEN: What type of screen is this? (dialog, form, list, main menu, etc.)
2. DIALOG CHECK: Is there a blocking dialog? If yes, handle it first.
3. ELEMENTS: Which [UNTESTED] or [DM]/[M] elements are available?
4. ACTION: Select one action and call the tool.

DIALOG HANDLING:
- Permission dialogs: Click "Allow", "Accept", "OK", "Continue" (NEVER "Deny")
- Error/alert dialogs: Dismiss FIRST before background interaction
- Modal dialogs: Either interact WITH or dismiss first
- Use android_back() if no dismiss button visible

AVOID - DO NOT CLICK:
- Navigation bar at bottom (home, back, recent apps buttons)
- Status bar at top
- System UI elements outside the app

RULES:
- DIALOGS FIRST: Always dismiss/interact with dialogs before background
- PRIORITY: [UNTESTED] > [DM]/[M] > [TESTED-Nx] > [WELL-TESTED]
- TEXT FIELDS: Use android_type_text() for EditText, NOT android_click()
- VARIETY: Explore different elements, avoid clicking same position repeatedly

Call the appropriate tool after your analysis."""


def build_user_message(state_info: dict, navigation_hint: str = "") -> str:
    """
    Build user message with context for LLM.

    Args:
        state_info: Dict with keys:
            - ui_elements: List with single formatted string from _format_ui_elements
            - last_action: Optional last action taken
            - iteration: Current iteration number
        navigation_hint: Optional navigation guidance from WTG analysis
    """
    ui_elements = state_info.get('ui_elements', [])
    last_action = state_info.get('last_action')
    iteration = state_info.get('iteration', 0)

    # UI elements is already formatted string from _format_ui_elements
    if ui_elements and len(ui_elements) > 0:
        elements_text = ui_elements[0]
    else:
        elements_text = "No interactive elements found."

    # Minimal context
    context = f"Iteration {iteration}\n"
    if last_action:
        context += f"Last: {last_action}\n"

    # Navigation guidance if available
    guidance_section = ""
    if navigation_hint:
        guidance_section = f"\n{navigation_hint}\n"

    message = f"""{context}
{elements_text}
{guidance_section}
Analyze the screenshot and select the next interaction."""

    return message


PROMPT_VERSION = "v14"

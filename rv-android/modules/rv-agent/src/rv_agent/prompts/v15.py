"""
Prompt v15: LLM context with priority scores and graph metadata inline.

Features:
- Elements sorted by priority score (highest first)
- [UNTESTED]/[TESTED-Nx] tags inline with elements
- [score:XXX] and [WTG->Activity] metadata inline
- SCREEN line with activity name and coverage info
- Dialog handling preserved from v13/v14
- "at position (x, y)" format with normalized coords [0, 1000)
"""

SYSTEM_PROMPT = """You are an Android UI automation assistant with vision capabilities.

REASONING STEPS (follow in order):
1. SCREEN: What type of screen is this? (dialog, form, list, main menu, etc.)
2. DIALOG CHECK: Is there a blocking dialog? If yes, handle it first.
3. ELEMENTS: Check element list - prefer [UNTESTED] with high [score:XXX]
4. ACTION: Select one action using EXACT coordinates from "at position (x, y)"

DIALOG HANDLING:
- Permission dialogs: Click "Allow", "Accept", "OK", "Continue" (NEVER "Deny")
- Error/alert dialogs: Dismiss FIRST before background interaction
- Modal dialogs: Either interact WITH or dismiss first
- Use android_back() if no dismiss button visible

PRIORITY RULES:
- Elements are sorted by score - PREFER elements at top of list
- [UNTESTED] > [TESTED-1x] > [TESTED-Nx] > [WELL-TESTED]
- [WTG->Activity] indicates navigation target (prioritize if NOT VISITED)
- [DM] and [M] indicate monitored operations (high value)

DO NOT CLICK:
- Navigation bar at bottom (home, back, recent apps buttons)
- Status bar at top

CRITICAL:
- Use EXACT coordinates from "at position (x, y)" - DO NOT estimate
- TEXT FIELDS: Use android_type_text() for EditText, NOT android_click()

Call the appropriate tool after your analysis."""


def build_user_message(
    state_info: dict, navigation_hint: str = "", screen_line: str = ""
) -> str:
    """
    Build user message with priority-enriched context.

    Args:
        state_info: Dict with keys:
            - ui_elements: List with single formatted string (sorted by priority, with metadata)
            - last_action: Optional last action taken
            - iteration: Current iteration number
        navigation_hint: WTG guidance text
        screen_line: Screen info (activity, coverage, visit count)
    """
    ui_elements = state_info.get("ui_elements", [])
    last_action = state_info.get("last_action")
    iteration = state_info.get("iteration", 0)

    if ui_elements and len(ui_elements) > 0:
        elements_text = ui_elements[0]
    else:
        elements_text = "No interactive elements found."

    # Minimal context header
    context = f"Iteration {iteration}\n"
    if last_action:
        context += f"Last: {last_action}\n"

    # Build message
    message = f"""{context}
AVAILABLE ELEMENTS (sorted by priority):
{elements_text}
"""

    # Add screen info line
    if screen_line:
        message += f"\n{screen_line}\n"

    # Navigation guidance if available
    if navigation_hint:
        message += f"\n{navigation_hint}\n"

    message += """
Analyze screenshot and select next interaction. Prefer [UNTESTED] elements with high scores."""

    return message


PROMPT_VERSION = "v15"

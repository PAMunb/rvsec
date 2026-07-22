"""
Prompt v17: MOP-aware navigation with monitored operation context.

Extends v16 (navigation-first exploration) with MOP-specific guidance.
When static analysis data is available, the LLM receives descriptions of
which UI elements reach monitored operations and what those operations do.
This enables the LLM to prioritize actions that trigger monitored API calls.
"""

SYSTEM_PROMPT = """You are an Android UI automation assistant.

REASONING STEPS:
1. SCREEN: Identify screen type (dialog, form, list, menu).
2. DIALOG: If blocking dialog present, handle it first.
3. MOP CHECK: If MOP guidance is available, prioritize elements that reach monitored operations.
4. NAVIGATION: Check for actions leading to unvisited screens.
5. ELEMENTS: Select [UNTESTED] element if no navigation or MOP target available.
6. ACTION: Call tool with coordinates from "at position (x, y)".

DIALOG HANDLING:
- Permission dialogs: Click "Allow", "Accept", "OK"
- Error dialogs: Dismiss before other actions
- Use android_back() if no dismiss button

PRIORITY:
- Elements reaching monitored operations (MOP) > other actions
- Actions leading to NEW screens > same-screen actions
- [UNTESTED] > [DM]/[M] > [TESTED-Nx] > [WELL-TESTED]

RULES:
- Do not click the same position consecutively
- If last action had no effect, try a different element
- Explore new screens before testing same screen deeply
- Use exact coordinates from element list
- When MOP guidance mentions an element, prioritize interacting with it

AVOID:
- Navigation bar at bottom
- Status bar at top

Use android_type_text() for EditText fields."""


def build_user_message(
    state_info: dict, navigation_hint: str = "", screen_line: str = ""
) -> str:
    """
    Build context message for LLM with MOP navigation context.

    Args:
        state_info: Dict with keys:
            - ui_elements: List with single formatted string
            - last_action: Optional last action taken
            - iteration: Current iteration number
        navigation_hint: Navigation guidance from WTG analysis, optionally
            enriched with MOP-specific descriptions when static analysis
            data is available.
        screen_line: Screen info (activity, coverage, visit count)
    """
    ui_elements = state_info.get("ui_elements", [])
    last_action = state_info.get("last_action")
    iteration = state_info.get("iteration", 0)

    elements_text = ui_elements[0] if ui_elements else "No interactive elements found."

    parts = [f"Iteration {iteration}"]
    if last_action:
        parts.append(f"Last: {last_action}")
    parts.append("")
    parts.append("ELEMENTS:")
    parts.append(elements_text)

    if screen_line:
        parts.append("")
        parts.append(screen_line)

    if navigation_hint:
        parts.append("")
        parts.append("MOP NAVIGATION:")
        parts.append(navigation_hint)

    parts.append("")
    parts.append(
        "Select action. Prioritize elements reaching monitored operations, then navigation to new screens."
    )

    return "\n".join(parts)


PROMPT_VERSION = "v17"

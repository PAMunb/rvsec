"""Prompt construction for APE-RV LLM validation pipeline.

Replicates the prompt building logic from Java's ApePromptBuilder (commit b2852dd).
Produces OpenAI-format messages and tool schemas for the SGLang inference server.
"""

from __future__ import annotations

from aperv_llm_validation.constants import QWEN_COORD_RANGE
from aperv_llm_validation.data.models import PromptConfig, Widget


def _simple_class_name(full_name: str) -> str:
    """Extract simple class name: 'android.widget.Button' -> 'Button'."""
    if not full_name:
        return "View"
    dot = full_name.rfind(".")
    return full_name[dot + 1 :] if dot >= 0 else full_name


def _truncate(s: str, max_len: int) -> str:
    """Truncate string to max_len, appending ellipsis if truncated."""
    if not s:
        return ""
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "\u2026"


MAX_TEXT_LEN = 50


def build_widget_list(widgets: list[Widget], device_w: int, device_h: int) -> str:
    """Format widgets as APE-style indexed list.

    Format: [i] ClassName "text" @(normX,normY) (v:0)
    Where normX = int((centerX / device_w) * 1000), clamped to [0, 999].
    v:0 always (offline, no visit history).
    """
    lines: list[str] = []
    for i, w in enumerate(widgets):
        class_simple = _simple_class_name(w.class_name)
        cx, cy = w.center

        norm_x = int((cx / device_w) * QWEN_COORD_RANGE)
        norm_y = int((cy / device_h) * QWEN_COORD_RANGE)
        norm_x = max(0, min(norm_x, QWEN_COORD_RANGE - 1))
        norm_y = max(0, min(norm_y, QWEN_COORD_RANGE - 1))

        # Display text: prefer text, fallback to content_desc
        display_text = w.text if w.text else w.content_desc
        truncated = _truncate(display_text, MAX_TEXT_LEN)

        lines.append(f'[{i}] {class_simple} "{truncated}" @({norm_x},{norm_y}) (v:0)')

    return "\n".join(lines)


def build_system_message(include_type_text: bool, include_reasoning: bool = False) -> str:
    """Build the system message — exact replica of Java's ApePromptBuilder.buildSystemMessage().

    The include_reasoning parameter is accepted for API compatibility but does not
    affect the system message text (reasoning is handled in the tool schema only).
    """
    parts: list[str] = []
    parts.append("You are an Android UI testing agent exploring an app.\n")
    parts.append("DIALOG: If permission/error dialog visible, dismiss it first (click Allow/OK).\n")
    parts.append("PRIORITY: [DM]/[M] elements > unvisited (v:0) > visited.\n")
    parts.append("AVOID: status bar (top), navigation bar (bottom).\n")
    parts.append("RULES: Don't click same position twice. ")
    parts.append("Use type_text for input fields with valid data ")
    parts.append("(email: user@example.com, password: Test1234!, domain: example.com, search: relevant term).\n")
    parts.append("Tools (coordinates in [0,1000) normalized space):\n")
    parts.append("  click(x, y) \u2014 tap element\n")
    parts.append("  long_click(x, y) \u2014 long press element\n")
    if include_type_text:
        parts.append("  type_text(x, y, text) \u2014 type into field\n")
    parts.append("  back() \u2014 press back\n")
    parts.append('Respond with one JSON: {"name": "<action>", "arguments": {<args>}}')
    return "".join(parts)


def build_user_text(
    activity: str,
    widgets: list[Widget],
    device_w: int,
    device_h: int,
) -> str:
    """Build the user text part: screen header + widget list."""
    # Simple activity name
    if not activity:
        activity_simple = "Unknown"
    else:
        dot = activity.rfind(".")
        activity_simple = activity[dot + 1 :] if dot >= 0 else activity

    parts: list[str] = []
    parts.append(f'Screen "{activity_simple}":')
    widget_list = build_widget_list(widgets, device_w, device_h)
    if widget_list:
        parts.append(widget_list)

    return "\n".join(parts)


def build_messages(
    screenshot_b64: str,
    widgets: list[Widget],
    activity: str,
    device_w: int,
    device_h: int,
    prompt_config: PromptConfig | None = None,
) -> list[dict]:
    """Build the 2-message prompt array: [system, user].

    User message has 2 content parts: [image_url, text].
    image_url format: data:image/jpeg;base64,{b64}
    """
    # Determine if input fields present
    has_input = any(w.editable for w in widgets)

    # System message
    system_text = build_system_message(include_type_text=has_input)

    # User text
    user_text = build_user_text(activity, widgets, device_w, device_h)

    # Image URL
    image_url = f"data:image/jpeg;base64,{screenshot_b64 or ''}"

    return [
        {"role": "system", "content": system_text},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": user_text},
            ],
        },
    ]


def build_tool_schema(include_type_text: bool, include_reasoning: bool = False) -> list[dict]:
    """Build OpenAI tools array with click, long_click, back, and conditionally type_text.

    If include_reasoning is True, each tool gets an optional 'reasoning' string parameter.
    """

    def _coord_params(include_reasoning: bool) -> dict:
        props = {
            "x": {"type": "integer", "description": "Normalized x coordinate [0, 1000)"},
            "y": {"type": "integer", "description": "Normalized y coordinate [0, 1000)"},
        }
        required = ["x", "y"]
        if include_reasoning:
            props["reasoning"] = {"type": "string", "description": "Reasoning for this action"}
        return {"type": "object", "properties": props, "required": required}

    tools = [
        {
            "type": "function",
            "function": {
                "name": "click",
                "description": "Tap element at coordinates",
                "parameters": _coord_params(include_reasoning),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "long_click",
                "description": "Long press element at coordinates",
                "parameters": _coord_params(include_reasoning),
            },
        },
    ]

    if include_type_text:
        type_text_props = {
            "x": {"type": "integer", "description": "Normalized x coordinate [0, 1000)"},
            "y": {"type": "integer", "description": "Normalized y coordinate [0, 1000)"},
            "text": {"type": "string", "description": "Text to type into the field"},
        }
        required = ["x", "y", "text"]
        if include_reasoning:
            type_text_props["reasoning"] = {"type": "string", "description": "Reasoning for this action"}
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "type_text",
                    "description": "Type text into input field at coordinates",
                    "parameters": {"type": "object", "properties": type_text_props, "required": required},
                },
            }
        )

    back_props: dict = {}
    back_required: list[str] = []
    if include_reasoning:
        back_props["reasoning"] = {"type": "string", "description": "Reasoning for this action"}
    tools.append(
        {
            "type": "function",
            "function": {
                "name": "back",
                "description": "Press back button",
                "parameters": {"type": "object", "properties": back_props, "required": back_required},
            },
        }
    )

    return tools

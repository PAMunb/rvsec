"""3-level fallback tool call parser — Python replica of ToolCallParser.java (commit b2852dd).

Parses tool calls from LLM responses using native -> XML tag -> inline JSON fallback.
Handles Qwen3-VL malformed JSON coordinates via fix_malformed_json().
"""

from __future__ import annotations

import json
import re

from aperv_llm_validation.data.models import ParsedAction

# Matches <tool_call>...</tool_call> or <function_call>...</function_call>
_XML_TAG_PATTERN = re.compile(
    r"<(?:tool_call|function_call)>(.*?)</(?:tool_call|function_call)>",
    re.DOTALL,
)

# Malformed JSON fixes (ported from Java ToolCallParser / RVAgent tool_call_parser.py)
# Pattern 1: "x": 352, 782  ->  "x": 352, "y": 782
_FIX_MISSING_Y_KEY = re.compile(r'"x":\s*(\d+),\s*(\d+)')
# Pattern 2: "x": [352, 782]  ->  "x": 352, "y": 782
_FIX_ARRAY_COORDS = re.compile(r'"x":\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]')
# Pattern 3: ": .91  ->  ": 0.91
_FIX_LEADING_ZERO = re.compile(r":\s*\.(\d+)")


def fix_malformed_json(s: str) -> str:
    """Fix common Qwen3-VL JSON malformations before parsing.

    Handles:
    - Missing "y" key: ``"x": 352, 782`` -> ``"x": 352, "y": 782``
    - Array coordinates: ``"x": [352, 782]`` -> ``"x": 352, "y": 782``
    - Missing leading zero: ``: .91`` -> ``: 0.91``
    - Truncated JSON: auto-close unbalanced braces
    """
    # Fix missing leading zero
    result = _FIX_LEADING_ZERO.sub(r": 0.\1", s)
    # Fix array coords
    result = _FIX_ARRAY_COORDS.sub(r'"x": \1, "y": \2', result)
    # Fix missing "y" key
    result = _FIX_MISSING_Y_KEY.sub(r'"x": \1, "y": \2', result)
    # Auto-close truncated JSON
    open_count = 0
    for c in result:
        if c == "{":
            open_count += 1
        elif c == "}":
            open_count -= 1
    if open_count > 0:
        result += "}" * open_count
    return result


def parse(response: dict) -> ParsedAction | None:
    """Parse a tool call from an OpenAI-format response dict.

    Uses 3-level fallback:
    1. Native tool_calls array in response["choices"][0]["message"]["tool_calls"]
    2. XML tags (<tool_call>/<function_call>) in content text
    3. Inline JSON with "name" + "arguments" keys in content text

    Returns None if no recognizable tool call was found.
    """
    if response is None:
        return None

    try:
        message = response["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return None

    # Level 1: native tool_calls
    tool_calls = message.get("tool_calls")
    if tool_calls and len(tool_calls) > 0:
        tc = tool_calls[0]
        try:
            name = tc["function"]["name"]
            args_raw = tc["function"].get("arguments", "{}")
            if isinstance(args_raw, str):
                args = json.loads(args_raw)
            else:
                args = args_raw if isinstance(args_raw, dict) else {}
            reasoning = _extract_reasoning(message)
            return _build_parsed_action(name, args, "native", reasoning)
        except (KeyError, json.JSONDecodeError, TypeError):
            pass

    # Level 2 & 3: parse from content text
    content = message.get("content", "")
    if not content:
        return None

    reasoning = _extract_reasoning(message)

    # Level 2: XML tag
    action = _parse_xml(content, reasoning)
    if action is not None:
        return action

    # Level 3: inline JSON
    return _parse_json_inline(content, reasoning)


def _extract_reasoning(message: dict) -> str | None:
    """Extract reasoning field from message if present."""
    # Some models include reasoning in a dedicated field
    reasoning = message.get("reasoning")
    if reasoning:
        return reasoning
    # Check reasoning_content (used by some providers)
    reasoning = message.get("reasoning_content")
    if reasoning:
        return reasoning
    return None


def _parse_xml(content: str, reasoning: str | None) -> ParsedAction | None:
    """Parse <tool_call>JSON</tool_call> or <function_call>JSON</function_call>."""
    m = _XML_TAG_PATTERN.search(content)
    if not m:
        return None
    inner = m.group(1).strip()
    return _parse_json_string(inner, "xml_tag", reasoning)


def _parse_json_inline(content: str, reasoning: str | None) -> ParsedAction | None:
    """Find and parse the first inline JSON object with 'name' + 'arguments' keys."""
    start = content.find("{")
    while 0 <= start < len(content):
        end = _find_matching_brace(content, start)
        if end < 0:
            # Truncated JSON — try the rest of the string; fix_malformed_json will
            # auto-close braces
            candidate = content[start:]
            action = _parse_json_string(candidate, "inline_json", reasoning)
            if action is not None:
                return action
            break
        candidate = content[start : end + 1]
        action = _parse_json_string(candidate, "inline_json", reasoning)
        if action is not None:
            return action
        start = content.find("{", start + 1)
    return None


def _find_matching_brace(s: str, start: int) -> int:
    """Find the closing brace matching the opening brace at position start."""
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _parse_json_string(
    json_str: str, parse_level: str, reasoning: str | None
) -> ParsedAction | None:
    """Parse a JSON string into a ParsedAction if it contains 'name' and 'arguments'.

    Applies malformed-JSON fixes before parsing.
    """
    try:
        fixed = fix_malformed_json(json_str)
        obj = json.loads(fixed)
        if not isinstance(obj, dict) or "name" not in obj:
            return None

        name = obj["name"]
        args = {}
        if "arguments" in obj:
            args_raw = obj["arguments"]
            if isinstance(args_raw, str):
                args = json.loads(args_raw)
            elif isinstance(args_raw, dict):
                args = args_raw
        return _build_parsed_action(name, args, parse_level, reasoning)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _build_parsed_action(
    name: str, args: dict, parse_level: str, reasoning: str | None
) -> ParsedAction | None:
    """Build a ParsedAction from a parsed action name and its arguments."""
    if name is None:
        return None

    action_type = name.lower().replace("-", "_")
    x = _get_int_arg(args, "x", 0)
    y = _get_int_arg(args, "y", 0)
    text = args.get("text")
    if text is not None:
        text = str(text)

    return ParsedAction(
        action_type=action_type,
        x=x,
        y=y,
        text=text,
        reasoning=reasoning,
        parse_level=parse_level,
    )


def _get_int_arg(args: dict, key: str, default: int = 0) -> int:
    """Extract an integer argument, handling float and string values."""
    if args is None or key not in args:
        return default
    val = args[key]
    if isinstance(val, (int, float)):
        return int(val)
    try:
        return int(str(val))
    except (ValueError, TypeError):
        return default

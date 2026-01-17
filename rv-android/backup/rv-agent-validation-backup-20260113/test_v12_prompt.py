#!/usr/bin/env python3
"""Test with actual v12 prompt to see native vs xml behavior."""

import base64
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

# Import actual prompt
import sys
sys.path.insert(0, "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent/src")
from rv_agent.prompts.v12 import SYSTEM_PROMPT, build_user_message


@tool
def android_click(x: int, y: int, element_description: str = "") -> dict:
    """Click on a UI element at coordinates (x, y).

    Args:
        x: X coordinate.
        y: Y coordinate.
        element_description: Description of element being clicked.
    """
    return {"success": True, "x": x, "y": y}


@tool
def android_back() -> dict:
    """Press the Android back button."""
    return {"success": True, "action": "back"}


def test_v12_prompt():
    """Test with v12 prompt."""

    llm = ChatOpenAI(
        base_url="http://192.168.0.21:30000/v1",
        model="Qwen/Qwen3-VL-4B-Instruct",
        temperature=0.1,
        max_tokens=256,
        api_key="not-needed",
    )

    tools = [android_click, android_back]
    llm_with_tools = llm.bind_tools(tools)

    # Load screenshot
    screenshot_path = Path("/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent/tests/fixtures/screenshots/cryptoapp/001.png")
    with open(screenshot_path, "rb") as f:
        screenshot_b64 = base64.b64encode(f.read()).decode()

    # Simulated UI elements text (like rv-agent provides)
    ui_elements_text = """
=== CLICKABLE ELEMENTS ===
Button 'MESSAGE DIGEST' at position (540, 350) - Actions: [CLICK]
Button 'CIPHER' at position (540, 500) - Actions: [CLICK]
Button 'MAC' at position (540, 650) - Actions: [CLICK]
Button 'SIGNATURE' at position (540, 800) - Actions: [CLICK]
Button 'KEY GENERATOR' at position (540, 950) - Actions: [CLICK]

Coordinates are in absolute pixels. Use these values directly with android_click.
"""

    print("=" * 70)
    print("Testing with V12 prompt")
    print("=" * 70)

    native_count = 0
    xml_count = 0

    for i in range(10):
        state_info = {
            "ui_elements": [ui_elements_text],
            "last_action": "Started app" if i == 0 else f"Clicked button {i}",
            "iteration": i
        }
        user_text = build_user_message(state_info)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=[
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
            ])
        ]

        response = llm_with_tools.invoke(messages)

        has_native = bool(response.tool_calls)
        has_xml_in_content = response.content and "<tool_call>" in response.content

        if has_native:
            native_count += 1
            strategy = "NATIVE"
        elif has_xml_in_content:
            xml_count += 1
            strategy = "XML"
        else:
            strategy = "NONE"

        # Get token info
        usage = {}
        if hasattr(response, 'response_metadata'):
            meta = response.response_metadata
            usage = meta.get('token_usage', meta.get('usage', {}))

        output_tokens = usage.get('completion_tokens', '?')

        print(f"Test {i+1}: {strategy:6} | output_tokens={output_tokens:3} | content_len={len(response.content) if response.content else 0}")

        if has_native:
            print(f"         tool_calls: {response.tool_calls}")
        if response.content:
            print(f"         content: {response.content[:200]}...")

    print("\n" + "=" * 70)
    print(f"SUMMARY: native={native_count}, xml={xml_count}")
    print("=" * 70)


if __name__ == "__main__":
    test_v12_prompt()

#!/usr/bin/env python3
"""Investigate native vs xml tool calling behavior."""

import base64
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool


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


def test_native_vs_xml():
    """Investigate when native vs xml is used."""

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

    print("=" * 70)
    print("Investigating native vs xml tool calling")
    print("=" * 70)

    native_count = 0
    xml_count = 0

    for i in range(10):
        messages = [
            SystemMessage(content="You are an Android UI assistant. Use the available tools to interact."),
            HumanMessage(content=[
                {"type": "text", "text": "Click on the first button you see."},
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

        print(f"\n--- Test {i+1}: {strategy} ---")
        print(f"tool_calls: {response.tool_calls}")
        print(f"content ({len(response.content) if response.content else 0} chars): {response.content[:500] if response.content else 'empty'}")

        # Check response metadata for token info
        if hasattr(response, 'response_metadata'):
            meta = response.response_metadata
            usage = meta.get('token_usage', meta.get('usage', {}))
            print(f"tokens: input={usage.get('prompt_tokens', '?')}, output={usage.get('completion_tokens', '?')}")

    print("\n" + "=" * 70)
    print(f"SUMMARY: native={native_count}, xml={xml_count}, total={native_count + xml_count}")
    print("=" * 70)


if __name__ == "__main__":
    test_native_vs_xml()

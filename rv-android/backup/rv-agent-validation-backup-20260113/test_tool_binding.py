#!/usr/bin/env python3
"""Test tool binding behavior with Qwen3-VL."""

import json
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


def test_tool_binding():
    """Test tool binding with Qwen3-VL."""
    import base64
    from pathlib import Path

    # Initialize LLM
    llm = ChatOpenAI(
        base_url="http://192.168.0.21:30000/v1",
        model="Qwen/Qwen3-VL-4B-Instruct",
        temperature=0.1,
        max_tokens=256,
        api_key="not-needed",
    )

    # Bind tools
    tools = [android_click, android_back]
    llm_with_tools = llm.bind_tools(tools)

    # Find a test screenshot
    screenshot_path = Path("../tests/fixtures/screenshots/cryptoapp/001.png")
    if not screenshot_path.exists():
        screenshot_path = Path("/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent/tests/fixtures/screenshots/cryptoapp/001.png")

    if screenshot_path.exists():
        with open(screenshot_path, "rb") as f:
            screenshot_b64 = base64.b64encode(f.read()).decode()
        print(f"Using screenshot: {screenshot_path}")
    else:
        print("No screenshot found, using text-only test")
        screenshot_b64 = None

    print("=" * 60)
    print("Testing tool binding with Qwen3-VL (MULTIMODAL)")
    print("=" * 60)

    for i in range(5):
        print(f"\n--- Test {i+1} ---")

        if screenshot_b64:
            # Multimodal message with image
            messages = [
                SystemMessage(content="You are an Android UI assistant. Use the available tools to interact."),
                HumanMessage(content=[
                    {"type": "text", "text": "Analyze this screenshot and click on the first button you see."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
                ])
            ]
        else:
            messages = [
                SystemMessage(content="You are an Android UI assistant. Use the available tools to interact."),
                HumanMessage(content="Click on the button at coordinates (500, 300).")
            ]

        response = llm_with_tools.invoke(messages)

        print(f"Response type: {type(response).__name__}")
        print(f"Has tool_calls attr: {hasattr(response, 'tool_calls')}")
        print(f"tool_calls value: {response.tool_calls if hasattr(response, 'tool_calls') else 'N/A'}")
        print(f"Content length: {len(response.content) if response.content else 0}")
        print(f"Content (first 300): {response.content[:300] if response.content else 'empty'}")

        if response.tool_calls:
            print(f"✅ NATIVE tool calls: {len(response.tool_calls)}")
            for tc in response.tool_calls:
                print(f"   - {tc}")
        elif response.content and ("<tool_call>" in response.content or "android_" in response.content):
            print(f"⚠️  FALLBACK needed - tool call in content")
        else:
            print(f"❌ NO tool calls detected")


if __name__ == "__main__":
    test_tool_binding()

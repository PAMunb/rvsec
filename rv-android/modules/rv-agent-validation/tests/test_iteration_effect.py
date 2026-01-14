#!/usr/bin/env python3
"""Test if iteration number affects native vs xml."""

import base64
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

import sys
sys.path.insert(0, "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent/src")
from rv_agent.prompts.v12 import SYSTEM_PROMPT, build_user_message


@tool
def android_click(x: int, y: int, element_description: str = "") -> dict:
    """Click on a UI element at coordinates (x, y)."""
    return {"success": True, "x": x, "y": y}


@tool
def android_back() -> dict:
    """Press the Android back button."""
    return {"success": True, "action": "back"}


def test_iteration_effect():
    """Test with fixed iteration to see if it affects behavior."""

    llm = ChatOpenAI(
        base_url="http://192.168.0.21:30000/v1",
        model="Qwen/Qwen3-VL-4B-Instruct",
        temperature=0.1,
        max_tokens=256,
        api_key="not-needed",
    )

    tools = [android_click, android_back]
    llm_with_tools = llm.bind_tools(tools)

    screenshot_path = Path("/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent/tests/fixtures/screenshots/cryptoapp/001.png")
    with open(screenshot_path, "rb") as f:
        screenshot_b64 = base64.b64encode(f.read()).decode()

    ui_elements_text = """
=== CLICKABLE ELEMENTS ===
Button 'MESSAGE DIGEST' at position (540, 350) - Actions: [CLICK]
Button 'CIPHER' at position (540, 500) - Actions: [CLICK]
"""

    print("=" * 70)
    print("Testing iteration effect on native vs xml")
    print("=" * 70)

    # Test with iteration=0 (5 times)
    print("\n--- ITERATION 0 (5 tests) ---")
    for i in range(5):
        state_info = {
            "ui_elements": [ui_elements_text],
            "last_action": "Started app",
            "iteration": 0  # FIXED at 0
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
        strategy = "NATIVE" if response.tool_calls else ("XML" if "<tool_call>" in (response.content or "") else "NONE")
        print(f"  Test {i+1}: {strategy}")

    # Test with iteration=5 (5 times)
    print("\n--- ITERATION 5 (5 tests) ---")
    for i in range(5):
        state_info = {
            "ui_elements": [ui_elements_text],
            "last_action": "Clicked button 5",
            "iteration": 5  # FIXED at 5
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
        strategy = "NATIVE" if response.tool_calls else ("XML" if "<tool_call>" in (response.content or "") else "NONE")
        print(f"  Test {i+1}: {strategy}")

    # Test with iteration=10 (5 times)
    print("\n--- ITERATION 10 (5 tests) ---")
    for i in range(5):
        state_info = {
            "ui_elements": [ui_elements_text],
            "last_action": "Clicked button 10",
            "iteration": 10  # FIXED at 10
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
        strategy = "NATIVE" if response.tool_calls else ("XML" if "<tool_call>" in (response.content or "") else "NONE")
        print(f"  Test {i+1}: {strategy}")


if __name__ == "__main__":
    test_iteration_effect()

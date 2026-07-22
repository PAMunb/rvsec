#!/usr/bin/env python3
"""
Test base qwen2.5vl:7b model with vision + tools (no custom template).
"""

import base64
from pathlib import Path
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama


def android_click(element_description: str, x: int, y: int) -> str:
    """Click on a UI element at given coordinates."""
    print(f"   🖱️  MOCK CLICK: {element_description} at ({x}, {y})")
    return f"Clicked {element_description} at ({x}, {y})"


def android_type_text(element_description: str, x: int, y: int, text: str) -> str:
    """Type text into input field at given coordinates."""
    print(f"   ⌨️  MOCK TYPE_TEXT: '{text}' into {element_description} at ({x}, {y})")
    return f"Typed '{text}' into {element_description} at ({x}, {y})"


def test_base_model_with_vision_and_tools():
    """Test base qwen2.5vl:7b with vision + tools."""

    print("=" * 80)
    print("🧪 TEST BASE MODEL (qwen2.5vl:7b) - Vision + Tools")
    print("=" * 80)
    print()

    # Find screenshot
    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    cryptoapp_dir = dataset_dir / "cryptoapp.apk"
    screenshot_files = list(cryptoapp_dir.glob("*.png")) if cryptoapp_dir.exists() else []

    if not screenshot_files:
        print("❌ No screenshot found!")
        return False

    screenshot_path = screenshot_files[0]
    print(f"📷 Screenshot: {screenshot_path.name}")

    # Load image
    with open(screenshot_path, 'rb') as f:
        image_base64 = base64.b64encode(f.read()).decode('utf-8')

    print(f"✅ Image loaded: {len(image_base64)} bytes")
    print()

    # Create model (llama32-vision-tools-v1 - native vision + tools)
    llm = ChatOllama(
        model="llama32-vision-tools-v1",  # VISION + TOOLS NATIVE
        temperature=0.00001,
    )
    print("📋 Using model: llama32-vision-tools-v1 (VISION + TOOLS NATIVE)")
    print()

    # Bind tools
    android_tools = [android_click, android_type_text]
    llm_with_tools = llm.bind_tools(android_tools)

    print(f"🔧 Tools bound: {[t.__name__ for t in android_tools]}")
    print()

    # Create prompt
    prompt = """You are analyzing an Android CryptoApp screen.

Look at the screenshot and identify what actions should be taken.

IMPORTANT RULES:
- For text input fields (EditText), use android_type_text (NOT android_click)
- For buttons, use android_click
- Provide realistic coordinates based on the image

What actions should be taken with this screen?"""

    # Send message with image
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": f"data:image/png;base64,{image_base64}"}
        ]
    )

    print("📤 Sending message to model...")
    print()

    response = llm_with_tools.invoke([message])

    print("=" * 80)
    print("📥 RESPOSTA:")
    print("=" * 80)
    print()

    # Check for tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"✅ SUCCESS! Model generated {len(response.tool_calls)} NATIVE tool call(s)")
        print()

        for i, tool_call in enumerate(response.tool_calls, 1):
            print(f"Tool Call #{i}:")
            print(f"   Name: {tool_call.get('name', 'unknown')}")
            print(f"   Args: {tool_call.get('args', {})}")

            # Execute mock tool
            tool_name = tool_call.get('name')
            tool_args = tool_call.get('args', {})

            if tool_name == 'android_click':
                android_click(**tool_args)
            elif tool_name == 'android_type_text':
                android_type_text(**tool_args)

            print()

        return True

    else:
        print("❌ FAILURE! No NATIVE tool calls generated")
        print(f"Response content: {response.content if hasattr(response, 'content') else 'N/A'}")
        print()
        print(f"Full response: {response}")
        return False


if __name__ == "__main__":
    success = test_base_model_with_vision_and_tools()

    print("=" * 80)
    if success:
        print("✅ BASE MODEL TEST PASSED - NATIVE TOOL CALLS WORK!")
    else:
        print("❌ BASE MODEL TEST FAILED - NO NATIVE TOOL CALLS")
    print("=" * 80)

    exit(0 if success else 1)

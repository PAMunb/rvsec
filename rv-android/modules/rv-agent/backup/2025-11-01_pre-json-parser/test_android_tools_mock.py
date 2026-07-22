#!/usr/bin/env python3
"""
Test com Android tools mock (fake) para verificar tool calling.
Baseado no script simples que funcionou.
"""

import base64
from pathlib import Path
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama


# Android tools MOCK - só print, sem ação real
def android_click(element_description: str, x: int, y: int) -> str:
    """
    Click on buttons, images, checkboxes, switches, and other clickable UI elements.

    USE FOR: Button, ImageButton, ImageView, CheckBox, Switch, RadioButton
    DO NOT USE FOR: EditText (use android_type_text instead)

    Args:
        element_description: Human-readable element description
        x: X coordinate in image space
        y: Y coordinate in image space

    Returns:
        Success message
    """
    print(f"   🖱️  MOCK CLICK: {element_description} at ({x}, {y})")
    return f"Clicked {element_description} at ({x}, {y})"


def android_type_text(element_description: str, x: int, y: int, text: str) -> str:
    """
    Type text into text input fields. ALWAYS use this for EditText elements.

    USE FOR: EditText, AutoCompleteTextView, any text input field
    DO NOT USE: android_click on EditText - use this tool instead

    Args:
        element_description: Human-readable element description
        x: X coordinate in image space
        y: Y coordinate in image space
        text: Text to type

    Returns:
        Success message
    """
    print(f"   ⌨️  MOCK TYPE_TEXT: '{text}' into {element_description} at ({x}, {y})")
    return f"Typed '{text}' into {element_description} at ({x}, {y})"


def android_swipe(direction: str, distance: str = "medium") -> str:
    """
    Swipe/scroll screen in specified direction.

    USE FOR: Scrolling lists, revealing hidden content

    Args:
        direction: Swipe direction - "up", "down", "left", "right"
        distance: Swipe distance - "short", "medium", "long"

    Returns:
        Success message
    """
    print(f"   ↔️  MOCK SWIPE: {direction} ({distance})")
    return f"Swiped {direction} with {distance} distance"


def test_with_screenshot():
    """Test Android tools com screenshot do CryptoApp."""

    print("=" * 80)
    print("🧪 TESTE ANDROID TOOLS MOCK - Com Screenshot CryptoApp (V2)")
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

    # Create model V2 (with vision+tools template)
    llm = ChatOllama(
        model="qwen-vision-tools-v2",
        temperature=0.00001,
    )
    print("📋 Using model: qwen-vision-tools-v2 (vision+tools template)")
    print()

    # Bind Android tools
    android_tools = [android_click, android_type_text, android_swipe]
    llm_with_tools = llm.bind_tools(android_tools)

    print(f"🔧 Tools bound: {[t.__name__ for t in android_tools]}")
    print()

    # Create prompt
    prompt = """You are analyzing an Android CryptoApp screen for generating cryptographic hashes.

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
        print(f"✅ SUCCESS! Model generated {len(response.tool_calls)} tool call(s)")
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
            elif tool_name == 'android_swipe':
                android_swipe(**tool_args)

            print()

        return True

    else:
        print("❌ FAILURE! No tool calls generated")
        print(f"Response content: {response.content if hasattr(response, 'content') else 'N/A'}")
        return False


def test_without_screenshot():
    """Test Android tools SEM screenshot (só texto)."""

    print("=" * 80)
    print("🧪 TESTE ANDROID TOOLS MOCK - Sem Screenshot (só texto)")
    print("=" * 80)
    print()

    llm = ChatOllama(
        model="qwen-vision-tools-v1:latest",
        temperature=0.00001,
    )

    android_tools = [android_click, android_type_text, android_swipe]
    llm_with_tools = llm.bind_tools(android_tools)

    print(f"🔧 Tools bound: {[t.__name__ for t in android_tools]}")
    print()

    prompt = """You see an Android login screen with:
1. EditText 'Email' at position (540, 400)
2. EditText 'Password' at position (540, 600)
3. Button 'Login' at position (540, 900)

What actions should you take to login?"""

    print("📤 Sending message to model...")
    print(f"Prompt: {prompt[:100]}...")
    print()

    response = llm_with_tools.invoke([HumanMessage(content=prompt)])

    print("=" * 80)
    print("📥 RESPOSTA:")
    print("=" * 80)
    print()

    # Check for tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"✅ SUCCESS! Model generated {len(response.tool_calls)} tool call(s)")
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
            elif tool_name == 'android_swipe':
                android_swipe(**tool_args)

            print()

        return True

    else:
        print("❌ FAILURE! No tool calls generated")
        print(f"Response content: {response.content if hasattr(response, 'content') else 'N/A'}")
        return False


if __name__ == "__main__":
    # Test 1: Without screenshot (simpler)
    print("\n\n")
    success1 = test_without_screenshot()

    print("\n\n")

    # Test 2: With screenshot (more realistic)
    success2 = test_with_screenshot()

    print("\n\n")
    print("=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(f"Test without screenshot: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"Test with screenshot:    {'✅ PASSED' if success2 else '❌ FAILED'}")
    print("=" * 80)

    exit(0 if (success1 and success2) else 1)

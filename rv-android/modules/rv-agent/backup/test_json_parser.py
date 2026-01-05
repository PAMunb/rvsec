#!/usr/bin/env python3
"""
Test JSON parser with CryptoApp screenshot.
Validates that json_parser can extract and execute tool calls from text responses.
"""

import base64
from pathlib import Path
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from rv_agent.llm.tools import json_parser
from rv_agent.llm.tools.android_tools import create_android_tools, set_device_interface, set_coordinate_converter
from rv_agent.core.device_interface import DeviceInterface
from rv_agent.core.coordinate_converter import CoordinateConverter


# Mock device for testing
class MockDevice:
    def click(self, x, y):
        print(f"   📱 MOCK DEVICE CLICK: ({x}, {y})")
        return True

    def input_text(self, text):
        print(f"   ⌨️  MOCK DEVICE INPUT_TEXT: '{text}'")
        return True

    def long_click(self, x, y):
        print(f"   📱 MOCK DEVICE LONG_CLICK: ({x}, {y})")
        return True

    def swipe(self, direction, distance):
        print(f"   📱 MOCK DEVICE SWIPE: {direction} ({distance})")
        return True

    def back(self):
        print(f"   📱 MOCK DEVICE BACK")
        return True

    def home(self):
        print(f"   📱 MOCK DEVICE HOME")
        return True


def test_json_parser_with_screenshot():
    """Test JSON parser with CryptoApp screenshot."""

    print("=" * 80)
    print("🧪 TEST JSON PARSER - Com Screenshot CryptoApp")
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

    # Create model v2 (with vision+tools template)
    llm = ChatOllama(
        model="qwen-vision-tools-v2",
        temperature=0.00001,
    )
    print("📋 Using model: qwen-vision-tools-v2 (vision+tools template)")

    # Bind Android tools (for schema injection)
    android_tools = create_android_tools()
    llm_with_tools = llm.bind_tools(android_tools)

    print(f"🔧 Tools bound (for schema injection)")
    print()

    # Create prompt
    prompt = """You are analyzing an Android CryptoApp screen for generating cryptographic hashes.

Look at the screenshot and identify what actions should be taken.

IMPORTANT RULES:
- For text input fields (EditText), use android_type_text (NOT android_click)
- For buttons, use android_click
- Provide realistic coordinates based on the image dimensions (728x1288)

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
    print("📥 RESPOSTA RECEBIDA:")
    print("=" * 80)
    print()

    # Check for native tool_calls first
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"✅ Native tool_calls found: {len(response.tool_calls)}")
        print()
        return True

    # Parse from JSON text
    print("⚠️ No native tool_calls, parsing from JSON text...")
    print()

    tool_calls = json_parser.parse_tool_calls_from_text(response.content)

    if not tool_calls:
        print("❌ FAILED: No tool calls found in JSON text either")
        print(f"Response content: {response.content[:500]}...")
        return False

    print(f"✅ SUCCESS! Parsed {len(tool_calls)} tool calls from JSON")
    print()

    # Setup mock device and converter
    device = MockDevice()
    converter = CoordinateConverter(
        device_dimensions=(1080, 1920),
        optimized_dimensions=(728, 1288)
    )

    # Execute parsed tool calls
    print("🔧 EXECUTING PARSED TOOL CALLS:")
    print()

    for i, tool_call in enumerate(tool_calls, 1):
        print(f"Tool Call #{i}:")
        print(f"   Name: {tool_call.get('name')}")
        print(f"   Args: {tool_call.get('args')}")

        result = json_parser.execute_tool_call(tool_call, device, converter)

        print(f"   Result: {result.get('action_type')} - {'✅ success' if result.get('success') else '❌ failed'}")
        print()

    return True


if __name__ == "__main__":
    success = test_json_parser_with_screenshot()

    print("=" * 80)
    if success:
        print("✅ JSON PARSER TEST PASSED")
    else:
        print("❌ JSON PARSER TEST FAILED")
    print("=" * 80)

    exit(0 if success else 1)

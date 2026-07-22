#!/usr/bin/env python3
"""
Debug Model Response - Analyze what the model is returning

Check if the model is making tool calls correctly and why it's only calling analyze_ui_state
"""

import sys
from pathlib import Path

# Add rv-agent to path
rv_agent_path = str(Path(__file__).parent / "src")
sys.path.insert(0, rv_agent_path)

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
import base64
import time

@tool
def android_click(coordinates: str, element_description: str = "", reasoning: str = "") -> str:
    """Click on Android UI element at specified coordinates"""
    print(f"🔧 TOOL EXECUTED: android_click({coordinates}, '{element_description}', '{reasoning}')")
    return f"✅ Clicked at coordinates: {coordinates} on element: {element_description}"

@tool
def analyze_ui_state(reasoning: str = "") -> str:
    """Analyze current UI state and extract available elements"""
    print(f"🔧 TOOL EXECUTED: analyze_ui_state('{reasoning}')")
    return f"✅ UI Analysis completed: 8 elements found in CryptoApp MainActivity - {reasoning}"

def test_model_tool_calling():
    """Test what the model is actually responding with"""

    print("🔬 DEBUGGING MODEL TOOL CALLING BEHAVIOR")
    print("=" * 60)

    # Initialize model
    llm = ChatOllama(
        model="PetrosStav/gemma3-tools:4b",
        temperature=0.2,
        top_p=0.9,
        top_k=50,
        num_predict=800,
        num_ctx=32768,
        base_url="http://localhost:11434"
    )

    # Bind tools
    tools = [android_click, analyze_ui_state]
    llm_with_tools = llm.bind_tools(tools)

    # Create test prompt focused on clicking action
    test_prompt = """You are testing a CryptoApp. The app is currently showing the main screen with the following UI elements:

AVAILABLE UI ELEMENTS:
1. "GENERATE HASH" Button at coordinates (540, 400)
2. "Message Digest" Spinner at coordinates (540, 292)
3. EditText input field at coordinates (540, 350)

CRITICAL INSTRUCTION: You MUST click on the "GENERATE HASH" button to test the app functionality.

Use the android_click tool with these exact coordinates: 540,400

Your task: Click the GENERATE HASH button and provide reasoning for why you're clicking it."""

    message = HumanMessage(content=test_prompt)

    print("📝 Sending prompt to model...")
    print(f"Prompt: {test_prompt[:200]}...")

    start_time = time.time()
    response = llm_with_tools.invoke([message])
    execution_time = time.time() - start_time

    print(f"\n🤖 MODEL RESPONSE (took {execution_time:.2f}s):")
    print(f"Response type: {type(response)}")
    print(f"Content: {response.content}")

    print(f"\n🔧 TOOL CALLS CHECK:")
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"✅ Tool calls found: {len(response.tool_calls)}")
        for i, tool_call in enumerate(response.tool_calls):
            print(f"  {i+1}. Tool: {tool_call.get('name', 'unknown')}")
            print(f"     Args: {tool_call.get('args', {})}")
    else:
        print("❌ No tool calls detected!")
        print("This explains why the agent only loops without taking actions")

    print(f"\n📊 RESPONSE ATTRIBUTES:")
    for attr in dir(response):
        if not attr.startswith('_'):
            try:
                value = getattr(response, attr)
                if not callable(value):
                    print(f"  {attr}: {value}")
            except:
                pass

    # Try manual parsing
    print(f"\n🔍 MANUAL PARSING ATTEMPT:")
    content_str = str(response.content)
    print(f"Content length: {len(content_str)}")
    print(f"Contains 'android_click': {'android_click' in content_str}")
    print(f"Contains 'analyze_ui_state': {'analyze_ui_state' in content_str}")
    print(f"Contains coordinates: {'540,400' in content_str}")

    return response

if __name__ == "__main__":
    try:
        response = test_model_tool_calling()
        print("\n✅ Debug test completed")
    except Exception as e:
        print(f"❌ Debug test failed: {e}")
        import traceback
        traceback.print_exc()
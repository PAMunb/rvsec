#!/usr/bin/env python3
"""
Simplified Autonomous Test - Direct approach with UI information

Based on the debug findings, create a working version that provides
specific UI element information to the model for decision making.
"""

import sys
import time
from pathlib import Path

# Add rv-agent to path
rv_agent_path = str(Path(__file__).parent / "src")
sys.path.insert(0, rv_agent_path)

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
import base64

@tool
def android_click(coordinates: str, element_description: str = "", reasoning: str = "") -> str:
    """Click on Android UI element at specified coordinates"""
    print(f"🎯 CLICKING: {coordinates} on '{element_description}' - {reasoning}")
    return f"✅ Clicked at {coordinates} on '{element_description}' - {reasoning}"

@tool
def capture_screenshot(reasoning: str = "") -> str:
    """Capture screenshot of current Android screen"""
    print(f"📸 SCREENSHOT: {reasoning}")
    return f"✅ Screenshot captured - {reasoning}"

@tool
def analyze_ui_state(reasoning: str = "") -> str:
    """Analyze current UI state and extract available elements"""
    print(f"🔍 ANALYZING: {reasoning}")
    # Simulated CryptoApp UI elements
    ui_elements = """Current CryptoApp screen shows:
1. "GENERATE HASH" Button at coordinates (540, 400) - main action button
2. "Message Digest" Spinner at coordinates (540, 292) - algorithm selection
3. EditText input field at coordinates (540, 350) - for text input
4. "Generated Hash" TextView at coordinates (540, 500) - shows results"""
    return f"✅ UI Analysis: {ui_elements}"

def run_simplified_autonomous():
    """Run simplified autonomous test with proper UI feedback"""

    print("🚀 SIMPLIFIED AUTONOMOUS TEST - Direct UI Approach")
    print("=" * 60)

    # Initialize model
    llm = ChatOllama(
        model="PetrosStav/gemma3-tools:4b",
        temperature=0.2,
        top_p=0.9,
        top_k=50
    )

    # Bind tools
    tools = [android_click, capture_screenshot, analyze_ui_state]
    llm_with_tools = llm.bind_tools(tools)

    # Simulate autonomous session
    iteration = 0
    max_iterations = 5

    while iteration < max_iterations:
        iteration += 1
        print(f"\n=== ITERATION {iteration} ===")

        # Create context-aware prompt
        if iteration == 1:
            prompt = """You are autonomously testing a CryptoApp. Your goal is to systematically test the application functionality.

CURRENT SCREEN: CryptoApp MainActivity

INSTRUCTIONS:
1. First, capture a screenshot to see what's available
2. Then analyze the UI state to understand the elements
3. Finally, click on interactive elements to test functionality

Start by capturing a screenshot and analyzing the UI to understand what's available."""
        else:
            prompt = f"""Continue testing the CryptoApp autonomously (iteration {iteration}).

You have already done some actions. Now you should:
1. Analyze the current UI state to see what elements are available
2. Choose an element to interact with based on your testing strategy
3. Click on elements to test different functionality

Focus on testing the core functionality like GENERATE HASH button, input fields, and dropdown selections."""

        message = HumanMessage(content=prompt)

        print(f"📤 Sending prompt to model...")
        start_time = time.time()

        try:
            response = llm_with_tools.invoke([message])
            execution_time = time.time() - start_time

            print(f"⏱️  Model response time: {execution_time:.2f}s")

            # Check for tool calls
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"🔧 Tool calls found: {len(response.tool_calls)}")

                for i, tool_call in enumerate(response.tool_calls):
                    tool_name = tool_call.get('name', 'unknown')
                    tool_args = tool_call.get('args', {})

                    print(f"\n  {i+1}. Executing: {tool_name}")
                    print(f"     Args: {tool_args}")

                    # Execute the tool
                    for tool in tools:
                        if tool.name == tool_name:
                            result = tool.invoke(tool_args)
                            print(f"     Result: {result}")
                            break

                print(f"✅ Iteration {iteration} completed with {len(response.tool_calls)} actions")

            else:
                print("❌ No tool calls - model only provided text response")
                print(f"Response: {response.content}")

            # Brief pause between iterations
            time.sleep(1)

        except Exception as e:
            print(f"❌ Error in iteration {iteration}: {e}")
            break

    print(f"\n✅ Simplified autonomous test completed - {iteration} iterations")

if __name__ == "__main__":
    run_simplified_autonomous()
"""
Teste para verificar como passar imagem corretamente para o agent.
"""

import base64
import sys
from pathlib import Path

# Add rv-agent to path
rv_agent_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, rv_agent_path)

from langchain_ollama import ChatOllama
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage

from mock_device_adapter import MockDeviceAdapter
from simple_tools_with_explanation import create_validation_tools


def encode_image_to_base64(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string


def test_agent_with_direct_multimodal():
    """Test using agent with direct multimodal input like the working test."""

    print("🧪 Testing Agent with Direct Multimodal Input")
    print("=" * 60)

    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"
    xml_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.uiautomator"

    # Setup mock device
    mock_device = MockDeviceAdapter(xml_path)
    tools = create_validation_tools(mock_device)

    # Get element descriptions
    elements_desc = mock_device.get_element_list_for_prompt()
    print(f"📋 Elements found: {len(mock_device.clickable_elements)}")
    print(f"🔍 Element descriptions:\n{elements_desc}")

    # Setup LLM and agent
    llm = ChatOllama(
        model="PetrosStav/gemma3-tools:4b",
        temperature=0.2
    )

    # Create simple prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are testing an Android application. You can see UI elements and should use tools to interact with them.

Available tools:
- android_click: Click on UI elements using coordinates
- android_input: Input text into fields
- android_scroll: Scroll the screen
- android_back: Press back button
- android_analyze_spinner: Special tool for spinners/dropdowns

IMPORTANT: Always provide an 'explanation' parameter describing your reasoning."""),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    # Create agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=3,
        handle_parsing_errors=True
    )

    # Encode image
    image_base64 = encode_image_to_base64(screenshot_path)
    print(f"📸 Image encoded: {len(image_base64)} chars")

    # Test 1: Direct multimodal input (like what worked)
    print("\n🔬 TEST 1: Direct multimodal with HumanMessage")
    print("-" * 40)

    try:
        # Create the exact same format that worked
        message_content = [
            {
                "type": "text",
                "text": f"""Describe this Android app screenshot and interact with a UI element.

Available UI elements:
{elements_desc}

Choose one element and use android_click with exact coordinates. Always include an explanation."""
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"}
            }
        ]

        # Try invoking the LLM directly first
        direct_response = llm.invoke([HumanMessage(content=message_content)])
        print("📝 Direct LLM Response:")
        print(direct_response.content[:300] + "...")

    except Exception as e:
        print(f"❌ Direct LLM test failed: {e}")

    # Test 2: Agent with multimodal input
    print("\n🔬 TEST 2: Agent with multimodal input")
    print("-" * 40)

    try:
        # Try to pass the multimodal content to agent
        result = agent_executor.invoke({
            "input": message_content
        })

        print("📝 Agent Response:")
        print(result.get("output", "No output")[:300] + "...")

        # Check if any tools were called
        metrics = mock_device.get_validation_metrics()
        print(f"🖱️ Tool calls made: {metrics['total_clicks']}")

    except Exception as e:
        print(f"❌ Agent test failed: {e}")

    # Test 3: Agent with text-only input (fallback)
    print("\n🔬 TEST 3: Agent with text-only input")
    print("-" * 40)

    try:
        text_input = f"""Look at this Android app screenshot and interact with a UI element.

Available UI elements:
{elements_desc}

Choose one element and use android_click with exact coordinates. Always include an explanation.

Note: This is a Crypto App with MESSAGE DIGEST, CIPHER, and GENERATED buttons."""

        result = agent_executor.invoke({"input": text_input})

        print("📝 Agent Response:")
        print(result.get("output", "No output")[:300] + "...")

        # Check if any tools were called
        metrics = mock_device.get_validation_metrics()
        print(f"🖱️ Tool calls made: {metrics['total_clicks']}")

    except Exception as e:
        print(f"❌ Text-only agent test failed: {e}")

    print("\n📊 Final Tool Usage Metrics:")
    final_metrics = mock_device.get_validation_metrics()
    print(f"  Total clicks: {final_metrics['total_clicks']}")
    print(f"  Hit rate: {final_metrics['hit_rate']:.1f}%")
    print(f"  Avg distance: {final_metrics['avg_distance']:.1f}px")


if __name__ == "__main__":
    test_agent_with_direct_multimodal()
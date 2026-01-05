"""
Teste correto de multimodal com LangChain baseado na documentação oficial.
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
from langchain_core.tools import tool

from mock_device_adapter import MockDeviceAdapter


def encode_image_to_base64(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string


@tool
def android_click(coordinates: str, element_description: str = "", explanation: str = "") -> str:
    """Click on Android UI elements using exact coordinates."""
    print(f"\n[TOOL_CALL] 🖱️ ANDROID_CLICK")
    print(f"  📍 Coordinates: {coordinates}")
    print(f"  🎯 Element: {element_description}")
    print(f"  💭 Explanation: {explanation}")
    return f"Clicked at {coordinates} on {element_description}"


def test_1_direct_llm_multimodal():
    """Test 1: Direct LLM with multimodal (this should work)."""

    print("\n🧪 TEST 1: Direct LLM Multimodal")
    print("=" * 50)

    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"
    image_base64 = encode_image_to_base64(screenshot_path)

    llm = ChatOllama(model="PetrosStav/gemma3-tools:4b", temperature=0.1)

    # Official LangChain multimodal format
    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": "Describe this Android app screenshot. What buttons do you see?"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_base64}"
                }
            }
        ]
    )

    try:
        response = llm.invoke([message])
        print("✅ Direct LLM Response:")
        print(response.content[:200] + "...")

        # Check if it sees crypto app content
        if "crypto" in response.content.lower() or "message digest" in response.content.lower():
            print("✅ Correctly recognizes Crypto App content")
        else:
            print("❌ Does not recognize Crypto App content")

    except Exception as e:
        print(f"❌ Direct LLM failed: {e}")


def test_2_llm_with_tools_multimodal():
    """Test 2: LLM with tools bound + multimodal."""

    print("\n🧪 TEST 2: LLM with Tools + Multimodal")
    print("=" * 50)

    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"
    image_base64 = encode_image_to_base64(screenshot_path)

    llm = ChatOllama(model="PetrosStav/gemma3-tools:4b", temperature=0.1)

    # Bind tools to LLM
    tools = [android_click]
    llm_with_tools = llm.bind_tools(tools)

    # Create multimodal message
    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": """Look at this Android app screenshot. Choose a button and use the android_click tool.

Available options:
- MESSAGE DIGEST button at (540, 273)
- CIPHER button at (540, 399)
- GENERATED button at (540, 525)

Use android_click with exact coordinates and provide explanation."""
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_base64}"
                }
            }
        ]
    )

    try:
        response = llm_with_tools.invoke([message])
        print("✅ LLM with Tools Response:")
        print(f"Content: {response.content[:200]}...")

        # Check for tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"✅ Tool calls detected: {len(response.tool_calls)}")
            for call in response.tool_calls:
                print(f"  Tool: {call['name']}")
                print(f"  Args: {call['args']}")
        else:
            print("❌ No tool calls detected")

    except Exception as e:
        print(f"❌ LLM with tools failed: {e}")


def test_3_agent_with_multimodal_proper():
    """Test 3: Agent with proper multimodal input."""

    print("\n🧪 TEST 3: Agent with Proper Multimodal")
    print("=" * 50)

    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"
    image_base64 = encode_image_to_base64(screenshot_path)

    llm = ChatOllama(model="PetrosStav/gemma3-tools:4b", temperature=0.1)
    tools = [android_click]

    # Create prompt template that supports multimodal
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an Android testing assistant. You can see screenshots and use tools to interact with UI elements."),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    # Create agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=2
    )

    try:
        # Test A: Pass multimodal content directly
        print("\n--- Test 3A: Multimodal content in input ---")

        multimodal_content = [
            {
                "type": "text",
                "text": """Look at this Android app screenshot and click on the MESSAGE DIGEST button.

Use android_click tool with coordinates (540, 273) and provide explanation."""
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_base64}"
                }
            }
        ]

        result = agent_executor.invoke({"input": multimodal_content})
        print("✅ Agent Result:")
        print(result.get("output", "No output")[:200] + "...")

    except Exception as e:
        print(f"❌ Agent multimodal test failed: {e}")

        # Test B: Text-only fallback
        print("\n--- Test 3B: Text-only fallback ---")
        try:
            text_input = """You are looking at a Crypto App screenshot with these buttons:
- MESSAGE DIGEST button at coordinates (540, 273)
- CIPHER button at coordinates (540, 399)
- GENERATED button at coordinates (540, 525)

Click on MESSAGE DIGEST using android_click tool with exact coordinates."""

            result = agent_executor.invoke({"input": text_input})
            print("✅ Text-only Agent Result:")
            print(result.get("output", "No output")[:200] + "...")

        except Exception as e:
            print(f"❌ Text-only agent also failed: {e}")


def main():
    """Run all multimodal tests in correct LangChain way."""

    print("🔬 LangChain Multimodal Tests - Following Official Docs")
    print("=" * 60)

    # Test progression from simple to complex
    test_1_direct_llm_multimodal()
    test_2_llm_with_tools_multimodal()
    test_3_agent_with_multimodal_proper()

    print("\n📊 SUMMARY:")
    print("- Test 1: Direct LLM should work")
    print("- Test 2: LLM + tools should work")
    print("- Test 3: Agent is the challenging part")
    print("\nIf Agent fails but LLM+tools works, we know it's Agent framework issue.")


if __name__ == "__main__":
    main()
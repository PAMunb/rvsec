"""
Test Qwen3-VL with LangGraph ToolNode

This script tests qwen3-vl:4b using LangGraph's native ToolNode
for vision-based tool calling with Android UI screenshots.

Focus: Make tool calling work WITH images using LangGraph
"""

import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# TOOLS
# ============================================================================

@tool
def get_current_datetime() -> dict:
    """
    Get current date and time.

    Returns:
        Dict with date, time, day_of_week, timestamp
    """
    now = datetime.now()
    result = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "timestamp": now.isoformat()
    }
    logger.info(f"📅 get_current_datetime() → {result}")
    return result


@tool
def android_click(element_description: str, x: int, y: int) -> dict:
    """
    Click on an Android UI element at specified coordinates.

    Args:
        element_description: Description of the UI element to click
        x: X coordinate (in optimized image space 728x1288)
        y: Y coordinate (in optimized image space 728x1288)

    Returns:
        Success status with click details
    """
    logger.info(f"🖱️  android_click('{element_description}', x={x}, y={y})")

    result = {
        "success": True,
        "element": element_description,
        "coordinates": {"x": x, "y": y},
        "message": f"Clicked '{element_description}' at ({x}, {y})"
    }

    # Validate coordinates for MESSAGE DIGEST button (expected ~364, 183 in optimized)
    expected_x, expected_y = 364, 183
    tolerance = 80
    x_diff = abs(x - expected_x)
    y_diff = abs(y - expected_y)

    if x_diff <= tolerance and y_diff <= tolerance:
        logger.info(f"✅ Coordinates ACCURATE! Diff: ({x_diff}px, {y_diff}px)")
        result["accuracy"] = "accurate"
    else:
        logger.warning(f"⚠️  Coordinates may be off. Expected: ({expected_x}, {expected_y}), Got: ({x}, {y})")
        result["accuracy"] = "uncertain"

    return result


# ============================================================================
# AGENT STATE
# ============================================================================

class AgentState(MessagesState):
    """State for the agent graph with message history"""
    pass


# ============================================================================
# AGENT NODES
# ============================================================================

def agent_node(state: AgentState) -> dict:
    """
    Main agent node that calls the LLM with tools
    """
    logger.info(f"🤖 Agent node called with {len(state['messages'])} messages")

    # Create LLM with tool binding
    llm = ChatOllama(
        model="qwen3-vl:4b",
        temperature=0.0,
    )

    # Bind tools to LLM
    tools = [get_current_datetime, android_click]
    llm_with_tools = llm.bind_tools(tools)

    # Get response
    response = llm_with_tools.invoke(state["messages"])

    # Log response details
    logger.info(f"📨 Response type: {type(response)}")
    logger.info(f"📨 Response content: {response.content[:200] if response.content else '[empty]'}")

    if hasattr(response, 'tool_calls') and response.tool_calls:
        logger.info(f"🔧 Tool calls found: {len(response.tool_calls)}")
        for i, tc in enumerate(response.tool_calls):
            logger.info(f"   Tool #{i+1}: {tc['name']} with args {tc['args']}")
    else:
        logger.info(f"⚠️  No tool_calls attribute or empty")
        # Check if tool call is in content as JSON
        if response.content and '{' in response.content:
            logger.info(f"💡 Tool call may be in content as JSON")

    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    Determine if we should continue to tools or end
    """
    messages = state["messages"]
    last_message = messages[-1]

    # Check if there are tool calls
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info(f"➡️  Routing to tools ({len(last_message.tool_calls)} calls)")
        return "tools"

    logger.info(f"🏁 Routing to end (no tool calls)")
    return "end"


# ============================================================================
# BUILD GRAPH
# ============================================================================

def build_agent_graph():
    """
    Build the LangGraph agent with ToolNode
    """
    # Define tools
    tools = [get_current_datetime, android_click]
    tool_node = ToolNode(tools)

    # Build graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # Set entry point
    workflow.add_edge(START, "agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )

    # After tools, go back to agent
    workflow.add_edge("tools", "agent")

    # Compile graph
    graph = workflow.compile()

    return graph


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_image_base64(image_path: str) -> str:
    """Load image and convert to base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def create_vision_message(prompt: str, image_b64: str) -> HumanMessage:
    """
    Create a HumanMessage with vision content

    LangChain format for multimodal messages:
    https://python.langchain.com/docs/how_to/multimodal_inputs/
    """
    return HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": f"data:image/png;base64,{image_b64}"
            }
        ]
    )


# ============================================================================
# TESTS
# ============================================================================

def test_with_vision(graph, image_path: str):
    """
    Test: Vision-based tool calling with Android screenshot

    Image: CryptoApp with MESSAGE DIGEST button at ~(364, 183) in optimized space
    Task: Click on MESSAGE DIGEST button using android_click tool
    """
    logger.info("=" * 80)
    logger.info("🧪 TEST: Vision-based Tool Calling with LangGraph")
    logger.info("=" * 80)

    # Load image
    logger.info(f"📷 Loading image: {image_path}")
    image_b64 = load_image_base64(image_path)
    logger.info(f"   Image size (base64): {len(image_b64)} chars")

    # Create system message
    system_msg = SystemMessage(
        content="""You are an Android UI automation assistant with vision capabilities.

Your task is to analyze Android app screenshots and interact with UI elements using tools.

IMPORTANT COORDINATE SPACE:
- The screenshot you see is in OPTIMIZED space: 728x1288 pixels
- You MUST provide coordinates in this OPTIMIZED space
- Do NOT scale or convert coordinates

When you see a UI element you need to click:
1. Identify the element's center position in the 728x1288 image
2. Use the android_click tool with those exact coordinates
3. Provide accurate x,y values based on what you see

Available tools:
- android_click(element_description, x, y): Click on UI element at coordinates"""
    )

    # Create vision message
    user_msg = create_vision_message(
        prompt="Analyze this Android app screenshot. Click on the 'MESSAGE DIGEST' button using the android_click tool. Provide the coordinates where you see this button in the image.",
        image_b64=image_b64
    )

    # Initial state
    initial_state = {
        "messages": [system_msg, user_msg]
    }

    # Run graph
    logger.info("🚀 Invoking graph...")
    try:
        result = graph.invoke(initial_state)

        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("📊 RESULTS")
        logger.info("=" * 80)

        for i, msg in enumerate(result["messages"]):
            logger.info(f"\nMessage {i+1}: {type(msg).__name__}")

            if isinstance(msg, AIMessage):
                logger.info(f"  Content: {msg.content[:200] if msg.content else '[empty]'}")
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    logger.info(f"  Tool calls: {len(msg.tool_calls)}")
                    for tc in msg.tool_calls:
                        logger.info(f"    - {tc['name']}: {tc['args']}")

            elif isinstance(msg, ToolMessage):
                logger.info(f"  Tool: {msg.name}")
                logger.info(f"  Result: {msg.content}")

        logger.info("\n✅ Test completed successfully!")
        return result

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return None


def test_without_vision(graph):
    """
    Test: Simple tool calling without vision (baseline)

    Task: Get current date/time using get_current_datetime tool
    """
    logger.info("=" * 80)
    logger.info("🧪 TEST: Simple Tool Calling (No Vision)")
    logger.info("=" * 80)

    # Create messages
    system_msg = SystemMessage(
        content="You are a helpful assistant with access to tools."
    )

    user_msg = HumanMessage(
        content="What day is today? Use the get_current_datetime tool to find out."
    )

    # Initial state
    initial_state = {
        "messages": [system_msg, user_msg]
    }

    # Run graph
    logger.info("🚀 Invoking graph...")
    try:
        result = graph.invoke(initial_state)

        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("📊 RESULTS")
        logger.info("=" * 80)

        for i, msg in enumerate(result["messages"]):
            logger.info(f"\nMessage {i+1}: {type(msg).__name__}")

            if isinstance(msg, AIMessage):
                logger.info(f"  Content: {msg.content}")
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    logger.info(f"  Tool calls: {len(msg.tool_calls)}")

            elif isinstance(msg, ToolMessage):
                logger.info(f"  Tool: {msg.name}")
                logger.info(f"  Result: {msg.content}")

        logger.info("\n✅ Test completed successfully!")
        return result

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return None


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run LangGraph tests with qwen3-vl"""

    print("\n" + "=" * 80)
    print("  QWEN3-VL + LANGGRAPH TOOLNODE TEST")
    print("=" * 80)
    print("\nModel: qwen3-vl:4b")
    print("Framework: LangGraph with native ToolNode")
    print("Focus: Vision-based tool calling with Android screenshots")

    # Image configuration
    image_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"

    if not Path(image_path).exists():
        logger.error(f"❌ Image not found: {image_path}")
        return

    logger.info(f"\n📷 Test image: {Path(image_path).name}")
    logger.info(f"   Expected button: MESSAGE DIGEST at ~(364, 183) in 728x1288 space")

    # Build graph
    logger.info("\n🔧 Building LangGraph agent...")
    graph = build_agent_graph()
    logger.info("✅ Graph built successfully!")

    # Run tests
    results = {}

    # Test 1: Without vision (baseline)
    logger.info("\n" + "🔵" * 40)
    results['no_vision'] = test_without_vision(graph)

    # Test 2: With vision (main test)
    logger.info("\n" + "🔵" * 40)
    results['with_vision'] = test_with_vision(graph, image_path)

    # Summary
    print("\n" + "=" * 80)
    print("  SUMMARY")
    print("=" * 80)

    if results['no_vision']:
        print("\n✅ Test 1 (No Vision): Passed")
    else:
        print("\n❌ Test 1 (No Vision): Failed")

    if results['with_vision']:
        print("✅ Test 2 (With Vision): Passed")
    else:
        print("❌ Test 2 (With Vision): Failed")

    print("\n" + "=" * 80)
    print("  NEXT STEPS")
    print("=" * 80)
    print("\n💡 If tool calling doesn't work with vision:")
    print("   1. Check if qwen3-vl returns tools in content instead of tool_calls")
    print("   2. May need custom parser for JSON-in-content format")
    print("   3. Consider using Qwen-Agent framework for vision + tools")
    print("\n📚 References:")
    print("   - LangGraph ToolNode: https://langchain-ai.github.io/langgraph/")
    print("   - Qwen-Agent: https://github.com/QwenLM/Qwen-Agent")
    print("   - Multimodal inputs: https://python.langchain.com/docs/how_to/multimodal_inputs/")


if __name__ == "__main__":
    main()

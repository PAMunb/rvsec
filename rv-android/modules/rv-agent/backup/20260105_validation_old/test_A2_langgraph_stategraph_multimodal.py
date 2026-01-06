#!/usr/bin/env python3
"""
FASE A.2: LangGraph StateGraph Multimodal Test

Objetivo: Testar LangGraph StateGraph com input multimodal preservado
Modelo: PetrosStav/gemma3-tools:4b (mesmo modelo do A.1 para comparação)
Expected: ✅ Preserva estrutura multimodal, permite tool calling
"""

import sys
import time
from pathlib import Path
from typing import List, TypedDict, Annotated

# Add rv-agent to path
rv_agent_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, rv_agent_path)

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from shared_validation_utils import (
    ValidationMetrics, setup_phase_logging, encode_image_to_base64,
    load_cryptoapp_screenshots, save_test_results, print_test_summary,
    create_cryptoapp_prompts, parse_tool_calls_from_response
)


@tool
def android_click_tool(coordinates: str, element_description: str = "") -> str:
    """Click on Android UI element at specified coordinates"""
    print(f"🔧 TOOL EXECUTED: android_click({coordinates}, '{element_description}')")
    return f"✅ Clicked at coordinates: {coordinates} on element: {element_description}"


@tool
def android_analyze_tool(screen_description: str) -> str:
    """Analyze Android screen content"""
    print(f"🔧 TOOL EXECUTED: android_analyze('{screen_description[:50]}...')")
    return f"✅ Screen analysis completed: {screen_description}"


# State definition for LangGraph
class AndroidAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "add_messages"]
    current_screenshot: str
    tool_calls_detected: bool
    multimodal_preserved: bool


def create_langgraph_android_agent():
    """Create LangGraph-based agent with multimodal support"""

    # Initialize LLM with tools
    llm = ChatOllama(
        model="PetrosStav/gemma3-tools:4b",
        temperature=0.2,
        top_p=0.9,
        top_k=50
    )

    # Tools
    tools = [android_click_tool, android_analyze_tool]
    llm_with_tools = llm.bind_tools(tools)

    # Agent node: processes messages and decides on actions
    def agent_node(state: AndroidAgentState):
        print("🤖 AGENT NODE: Processing multimodal state...")

        messages = state["messages"]
        print(f"📨 Received {len(messages)} messages")

        # Check if multimodal content is preserved
        has_multimodal = any(
            isinstance(msg, HumanMessage) and
            isinstance(msg.content, list) and
            any(item.get("type") == "image_url" for item in msg.content if isinstance(item, dict))
            for msg in messages
        )

        print(f"📸 Multimodal content preserved: {'✅' if has_multimodal else '❌'}")

        # Update state to track multimodal preservation
        state["multimodal_preserved"] = has_multimodal

        # Invoke LLM with tools
        try:
            print("🧠 Invoking LLM with multimodal messages...")
            response = llm_with_tools.invoke(messages)

            # Check for tool calls
            has_tool_calls = hasattr(response, 'tool_calls') and response.tool_calls
            print(f"🛠️ Tool calls detected: {'✅' if has_tool_calls else '❌'}")

            if has_tool_calls:
                print(f"🔧 Found {len(response.tool_calls)} tool calls:")
                for i, tool_call in enumerate(response.tool_calls):
                    print(f"  {i+1}. {tool_call['name']} - {tool_call['args']}")

            state["tool_calls_detected"] = has_tool_calls

            return {"messages": [response]}

        except Exception as e:
            print(f"❌ LLM invocation failed: {e}")
            error_msg = AIMessage(content=f"Error: {e}")
            return {"messages": [error_msg]}

    # Tool node: executes tools
    tool_node = ToolNode(tools)

    # Router function: decides next step
    def should_continue(state):
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        return END

    # Create builder
    workflow = StateGraph(AndroidAgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        END: END
    })

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Compile builder
    return workflow.compile()


def test_langgraph_with_multimodal():
    """Test LangGraph with multimodal input (should work)"""

    # Setup
    test_id = "A2_langgraph_stategraph_multimodal"
    logger = setup_phase_logging("a_langchain", test_id)
    metrics = ValidationMetrics()
    metrics.test_id = test_id
    metrics.phase = "A_LangChain_Architecture"
    metrics.model_name = "PetrosStav/gemma3-tools:4b"

    logger.info("="*60)
    logger.info(f"🧪 STARTING: {test_id}")
    logger.info("="*60)

    try:
        # Load screenshots
        screenshots = load_cryptoapp_screenshots()
        if not screenshots:
            raise Exception("No CryptoApp screenshots found")

        screenshot_data = screenshots[0]  # Use first screenshot
        logger.info(f"📸 Using screenshot: {screenshot_data['name']}")

        # Encode image
        screenshot_b64 = encode_image_to_base64(screenshot_data["screenshot"])
        if not screenshot_b64:
            raise Exception("Failed to encode screenshot")

        logger.info("✅ Image encoded successfully")

        # Create LangGraph agent
        logger.info("🏗️ Creating LangGraph StateGraph agent...")
        graph_agent = create_langgraph_android_agent()
        logger.info("✅ LangGraph agent created successfully")

        # Create multimodal message
        logger.info("📸 Creating multimodal HumanMessage...")
        multimodal_message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Look at this CryptoApp screenshot. I want to click on the 'Message Digest' button. Use the android_click tool with the exact coordinates."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot_b64}"
                    }
                }
            ]
        )

        logger.info("✅ Multimodal message created")

        # Initial state
        initial_state = {
            "messages": [multimodal_message],
            "current_screenshot": screenshot_data["name"],
            "tool_calls_detected": False,
            "multimodal_preserved": False
        }

        # CRITICAL TEST: Execute LangGraph with multimodal input
        logger.info("🔥 CRITICAL TEST: LangGraph execution with multimodal message")

        start_time = time.time()

        try:
            # Execute builder
            result = graph_agent.invoke(initial_state)

            response_time = time.time() - start_time
            metrics.response_time = response_time

            logger.info(f"⚡ Response time: {response_time:.2f}s")
            logger.info("🔍 LangGraph execution analysis...")

            # Analyze results
            messages = result.get("messages", [])
            multimodal_preserved = result.get("multimodal_preserved", False)
            tool_calls_detected = result.get("tool_calls_detected", False)

            logger.info(f"📨 Total messages in result: {len(messages)}")
            logger.info(f"📸 Multimodal preserved: {'✅' if multimodal_preserved else '❌'}")
            logger.info(f"🛠️ Tool calls detected: {'✅' if tool_calls_detected else '❌'}")

            # Update metrics
            metrics.multimodal_support = multimodal_preserved
            metrics.tool_calling_detected = tool_calls_detected

            # Analyze final response
            if messages:
                final_message = messages[-1]
                if hasattr(final_message, 'content'):
                    final_content = final_message.content
                else:
                    final_content = str(final_message)

                metrics.raw_response = final_content[:500]
                logger.info(f"📝 Final response (truncated): {final_content[:200]}...")

                # Check for CryptoApp understanding
                crypto_indicators = ["crypto", "message digest", "cipher", "hash", "button"]
                has_crypto_context = any(indicator in final_content.lower() for indicator in crypto_indicators)

                if has_crypto_context:
                    logger.info("✅ Response shows CryptoApp understanding")

                # Parse tool calls from content if not already detected
                if not tool_calls_detected:
                    parsed_tools = parse_tool_calls_from_response(final_content)
                    if parsed_tools:
                        metrics.tool_calling_detected = True
                        metrics.parsed_tools = parsed_tools
                        logger.info(f"🔧 Found tool calls in text: {len(parsed_tools)}")

            # Overall assessment
            if metrics.multimodal_support and metrics.tool_calling_detected:
                logger.info("🎉 SUCCESS: LangGraph handled multimodal + tools perfectly!")
                metrics.success_rate = 1.0
            elif metrics.multimodal_support:
                logger.info("⚡ PARTIAL: LangGraph preserved multimodal but no tools")
                metrics.success_rate = 0.6
            elif metrics.tool_calling_detected:
                logger.info("⚡ PARTIAL: LangGraph called tools but lost multimodal")
                metrics.success_rate = 0.4
            else:
                logger.warning("❌ FAILURE: LangGraph lost both multimodal and tools")
                metrics.success_rate = 0.0

        except Exception as e:
            response_time = time.time() - start_time
            metrics.response_time = response_time

            logger.error(f"❌ LangGraph execution failed: {e}")
            metrics.error_messages.append(f"LangGraph execution failed: {e}")
            metrics.success_rate = 0.0

    except Exception as e:
        logger.error(f"❌ Test setup failed: {e}")
        metrics.error_messages.append(f"Test setup failed: {e}")
        metrics.success_rate = 0.0

    # Finalize metrics
    metrics.coordinate_accuracy = float('inf')  # No coordinate validation in this test
    metrics.hit_rate = 0.0  # No actual clicks performed
    metrics.memory_usage_mb = 0  # Not measured

    # Save results
    save_test_results(metrics, "a_langchain")
    print_test_summary(metrics)

    logger.info("="*60)
    logger.info(f"📊 TEST COMPLETED: {test_id}")
    logger.info(f"Success Rate: {metrics.success_rate:.1%}")
    logger.info(f"Multimodal Support: {'✅' if metrics.multimodal_support else '❌'}")
    logger.info(f"Tool Calling: {'✅' if metrics.tool_calling_detected else '❌'}")
    logger.info("="*60)

    return metrics


def main():
    """Main test execution"""
    print("🚀 Starting FASE A.2 - LangGraph StateGraph Multimodal Test")
    print("🎯 Expected: LangGraph should PRESERVE multimodal and ENABLE tools")

    result = test_langgraph_with_multimodal()

    print(f"\n🏁 Test completed!")
    print(f"Results saved to: validation/results/fase_a_langchain/")
    print(f"Logs saved to: validation/logs/fase_a_langchain/")

    return result


if __name__ == "__main__":
    main()
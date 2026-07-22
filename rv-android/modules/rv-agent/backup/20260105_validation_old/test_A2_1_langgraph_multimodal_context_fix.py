#!/usr/bin/env python3
"""
FASE A.2.1: LangGraph Multimodal Context Fix

Objetivo: Resolver problema do A.2 - LangGraph perde contexto multimodal após first tool call
Solução: Preservar screenshot em state e recriar multimodal message em cada iteração
Expected: ✅ LangGraph mantém multimodal context em múltiplas iterações
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


# ENHANCED State definition with screenshot preservation
class AndroidAgentStateFixed(TypedDict):
    messages: Annotated[List[BaseMessage], "add_messages"]
    screenshot_b64: str  # PRESERVE screenshot across iterations
    screenshot_name: str
    iteration_count: int
    tool_calls_total: int
    multimodal_preserved_history: List[bool]
    last_action: str


def create_langgraph_android_agent_fixed():
    """Create FIXED LangGraph agent that preserves multimodal context"""

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

    # FIXED Agent node: always recreates multimodal message
    def agent_node_fixed(state: AndroidAgentStateFixed):
        iteration = state.get("iteration_count", 0) + 1
        print(f"🤖 AGENT NODE (Iteration {iteration}): Processing multimodal state...")

        # Get current messages and screenshot
        messages = state["messages"]
        screenshot_b64 = state["screenshot_b64"]
        screenshot_name = state["screenshot_name"]

        print(f"📨 Input messages: {len(messages)}")
        print(f"📸 Screenshot preserved: {bool(screenshot_b64)}")

        # CRITICAL FIX: Always recreate multimodal message for LLM
        if iteration == 1:
            # First iteration: use original messages
            llm_input = messages
        else:
            # Subsequent iterations: recreate multimodal context
            print("🔧 FIXING: Recreating multimodal message for iteration > 1")

            # Get last AI response for context
            last_ai_message = None
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    last_ai_message = msg
                    break

            # Create fresh multimodal message with history
            context_text = f"""Continue working with this CryptoApp screenshot.

Previous actions in this session:
{f"- Last action: {state.get('last_action', 'None')}" if state.get('last_action') else "- This is the first action"}
{f"- Tools used so far: {state.get('tool_calls_total', 0)}" if state.get('tool_calls_total', 0) > 0 else ""}

Current task: Click on the 'Message Digest' button if not done yet, or explore other options.
Use android_click tool with exact coordinates."""

            fresh_multimodal_message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": context_text
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_b64}"
                        }
                    }
                ]
            )

            # Use fresh message + last AI response
            if last_ai_message:
                llm_input = [fresh_multimodal_message, last_ai_message]
            else:
                llm_input = [fresh_multimodal_message]

        # Check if multimodal content is preserved
        has_multimodal = any(
            isinstance(msg, HumanMessage) and
            isinstance(msg.content, list) and
            any(item.get("type") == "image_url" for item in msg.content if isinstance(item, dict))
            for msg in llm_input
        )

        print(f"📸 Multimodal content in LLM input: {'✅' if has_multimodal else '❌'}")

        # Track multimodal preservation
        multimodal_history = state.get("multimodal_preserved_history", [])
        multimodal_history.append(has_multimodal)

        # Invoke LLM with tools
        try:
            print(f"🧠 Invoking LLM (iteration {iteration}) with multimodal messages...")
            response = llm_with_tools.invoke(llm_input)

            # Check for tool calls
            has_tool_calls = hasattr(response, 'tool_calls') and response.tool_calls
            print(f"🛠️ Tool calls detected: {'✅' if has_tool_calls else '❌'}")

            if has_tool_calls:
                print(f"🔧 Found {len(response.tool_calls)} tool calls:")
                for i, tool_call in enumerate(response.tool_calls):
                    print(f"  {i+1}. {tool_call['name']} - {tool_call['args']}")

            # Update state
            updated_state = {
                "messages": [response],
                "iteration_count": iteration,
                "tool_calls_total": state.get("tool_calls_total", 0) + (len(response.tool_calls) if has_tool_calls else 0),
                "multimodal_preserved_history": multimodal_history,
                "last_action": f"Iteration {iteration}: {'Called tools' if has_tool_calls else 'No tools'}"
            }

            return updated_state

        except Exception as e:
            print(f"❌ LLM invocation failed: {e}")
            error_msg = AIMessage(content=f"Error: {e}")
            return {
                "messages": [error_msg],
                "iteration_count": iteration,
                "multimodal_preserved_history": multimodal_history + [False]
            }

    # Tool node: executes tools
    tool_node = ToolNode(tools)

    # Router function: decides next step (limit iterations)
    def should_continue_fixed(state):
        messages = state["messages"]
        iteration = state.get("iteration_count", 0)

        # Limit to 3 iterations to prevent infinite loops
        if iteration >= 3:
            print(f"🛑 Stopping after {iteration} iterations")
            return END

        last_message = messages[-1]

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        return END

    # Create builder
    workflow = StateGraph(AndroidAgentStateFixed)

    # Add nodes
    workflow.add_node("agent", agent_node_fixed)
    workflow.add_node("tools", tool_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges("agent", should_continue_fixed, {
        "tools": "tools",
        END: END
    })

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Compile builder
    return workflow.compile()


def test_langgraph_multimodal_context_fixed():
    """Test FIXED LangGraph that preserves multimodal context across iterations"""

    # Setup
    test_id = "A2_1_langgraph_multimodal_context_fix"
    logger = setup_phase_logging("a_langchain", test_id)
    metrics = ValidationMetrics()
    metrics.test_id = test_id
    metrics.phase = "A_LangChain_Architecture_Fix"
    metrics.model_name = "PetrosStav/gemma3-tools:4b"

    logger.info("="*60)
    logger.info(f"🧪 STARTING: {test_id}")
    logger.info("🎯 FIX: Preserve multimodal context across LangGraph iterations")
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

        # Create FIXED LangGraph agent
        logger.info("🏗️ Creating FIXED LangGraph StateGraph agent...")
        graph_agent = create_langgraph_android_agent_fixed()
        logger.info("✅ Fixed LangGraph agent created successfully")

        # Create initial multimodal message
        logger.info("📸 Creating initial multimodal HumanMessage...")
        initial_multimodal_message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Look at this CryptoApp screenshot. I want to test multiple interactions. Start by clicking on the 'Message Digest' button, then analyze the result. Use android_click tool with exact coordinates."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot_b64}"
                    }
                }
            ]
        )

        logger.info("✅ Initial multimodal message created")

        # Initial state with screenshot preservation
        initial_state = {
            "messages": [initial_multimodal_message],
            "screenshot_b64": screenshot_b64,  # PRESERVE this!
            "screenshot_name": screenshot_data["name"],
            "iteration_count": 0,
            "tool_calls_total": 0,
            "multimodal_preserved_history": [],
            "last_action": ""
        }

        # CRITICAL TEST: Execute FIXED LangGraph with multimodal preservation
        logger.info("🔥 CRITICAL TEST: Fixed LangGraph execution with preserved multimodal context")

        start_time = time.time()

        try:
            # Execute builder
            result = graph_agent.invoke(initial_state)

            response_time = time.time() - start_time
            metrics.response_time = response_time

            logger.info(f"⚡ Total response time: {response_time:.2f}s")
            logger.info("🔍 Fixed LangGraph execution analysis...")

            # Analyze results
            messages = result.get("messages", [])
            multimodal_history = result.get("multimodal_preserved_history", [])
            total_iterations = result.get("iteration_count", 0)
            total_tool_calls = result.get("tool_calls_total", 0)

            logger.info(f"📨 Total messages in result: {len(messages)}")
            logger.info(f"🔄 Total iterations: {total_iterations}")
            logger.info(f"🛠️ Total tool calls: {total_tool_calls}")
            logger.info(f"📸 Multimodal history: {multimodal_history}")

            # Calculate success metrics
            multimodal_success_rate = sum(multimodal_history) / len(multimodal_history) if multimodal_history else 0.0
            has_multiple_iterations = total_iterations > 1
            has_tool_calls = total_tool_calls > 0

            logger.info(f"📊 Multimodal preservation rate: {multimodal_success_rate:.1%}")

            # Update metrics
            metrics.multimodal_support = multimodal_success_rate >= 0.8  # 80%+ preservation
            metrics.tool_calling_detected = has_tool_calls

            # Analyze final response for coordinate extraction
            if messages:
                final_message = messages[-1]
                if hasattr(final_message, 'content'):
                    final_content = final_message.content
                else:
                    final_content = str(final_message)

                metrics.raw_response = final_content[:500]
                logger.info(f"📝 Final response (truncated): {final_content[:200]}...")

            # Overall assessment
            if metrics.multimodal_support and has_multiple_iterations and has_tool_calls:
                logger.info("🎉 SUCCESS: Fixed LangGraph preserves multimodal across iterations!")
                metrics.success_rate = 1.0
            elif metrics.multimodal_support and has_tool_calls:
                logger.info("⚡ PARTIAL SUCCESS: Fixed LangGraph works but limited iterations")
                metrics.success_rate = 0.8
            elif has_tool_calls:
                logger.info("🔧 TOOL SUCCESS: Tools work but multimodal issues remain")
                metrics.success_rate = 0.6
            else:
                logger.warning("❌ FAILURE: Fix didn't resolve the issues")
                metrics.success_rate = 0.0

        except Exception as e:
            response_time = time.time() - start_time
            metrics.response_time = response_time

            logger.error(f"❌ Fixed LangGraph execution failed: {e}")
            metrics.error_messages.append(f"Fixed LangGraph execution failed: {e}")
            metrics.success_rate = 0.0

    except Exception as e:
        logger.error(f"❌ Test setup failed: {e}")
        metrics.error_messages.append(f"Test setup failed: {e}")
        metrics.success_rate = 0.0

    # Finalize metrics
    metrics.coordinate_accuracy = float('inf')  # No coordinate validation in this test
    metrics.hit_rate = 0.0  # No actual UI validation
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
    print("🚀 Starting FASE A.2.1 - LangGraph Multimodal Context Fix")
    print("🎯 Expected: FIXED LangGraph should PRESERVE multimodal across ALL iterations")

    result = test_langgraph_multimodal_context_fixed()

    print(f"\n🏁 Test completed!")
    print(f"Results saved to: validation/results/fase_a_langchain/")
    print(f"Logs saved to: validation/logs/fase_a_langchain/")

    return result


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
FASE A.1: AgentExecutor Multimodal Failure Test

Objetivo: Reproduzir e confirmar falha do AgentExecutor com input multimodal
Modelo: PetrosStav/gemma3-tools:4b (atual RVAgent)
Expected: ❌ Falha multimodal - imagem não chega ao LLM
"""

import sys
import time
from pathlib import Path

# Add rv-agent to path
rv_agent_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, rv_agent_path)

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub

from shared_validation_utils import (
    ValidationMetrics, setup_phase_logging, encode_image_to_base64,
    load_cryptoapp_screenshots, save_test_results, print_test_summary,
    create_cryptoapp_prompts, parse_tool_calls_from_response
)


@tool
def android_click_tool(coordinates: str, element_description: str = "") -> str:
    """Click on Android UI element at specified coordinates"""
    print(f"🔧 TOOL CALLED: android_click({coordinates}, '{element_description}')")
    return f"Clicked at coordinates: {coordinates} on element: {element_description}"


@tool
def android_analyze_tool(screen_description: str) -> str:
    """Analyze Android screen content"""
    print(f"🔧 TOOL CALLED: android_analyze('{screen_description[:50]}...')")
    return f"Screen analysis: {screen_description}"


def test_agentexecutor_with_multimodal():
    """Test AgentExecutor with multimodal input (should fail)"""

    # Setup
    test_id = "A1_agentexecutor_multimodal_failure"
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

        metrics.multimodal_support = True  # We have image data
        logger.info("✅ Image encoded successfully")

        # Initialize LLM
        logger.info("🧠 Initializing Ollama ChatOllama...")
        llm = ChatOllama(
            model="PetrosStav/gemma3-tools:4b",
            temperature=0.2,
            top_p=0.9,
            top_k=50
        )

        # Create tools
        tools = [android_click_tool, android_analyze_tool]
        logger.info(f"🛠️ Created {len(tools)} tools")

        # Try to create ReactAgent (this is where it should break)
        logger.info("🤖 Creating ReAct agent with AgentExecutor...")

        try:
            # Get ReAct prompt template
            prompt = hub.pull("hwchase17/react")
            logger.info("✅ ReAct prompt template loaded")

            # Create agent
            agent = create_react_agent(llm, tools, prompt)
            logger.info("✅ ReAct agent created")

            # Create AgentExecutor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=3
            )
            logger.info("✅ AgentExecutor created")

        except Exception as e:
            logger.error(f"❌ Agent creation failed: {e}")
            metrics.error_messages.append(f"Agent creation failed: {e}")
            metrics.success_rate = 0.0
            return metrics

        # Create multimodal message
        logger.info("📸 Creating multimodal HumanMessage...")
        multimodal_message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Look at this CryptoApp screenshot. Use the android_click tool to click on the 'Message Digest' button. Provide exact coordinates."
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

        # CRITICAL TEST: Try to execute with multimodal input
        logger.info("🔥 CRITICAL TEST: AgentExecutor.invoke() with multimodal message")

        start_time = time.time()

        try:
            # This should FAIL because AgentExecutor doesn't handle multimodal properly
            result = agent_executor.invoke({"input": multimodal_message})

            response_time = time.time() - start_time
            metrics.response_time = response_time

            logger.info(f"⚡ Response time: {response_time:.2f}s")
            logger.info("🔍 AgentExecutor response analysis...")

            # Analyze response
            if isinstance(result, dict):
                output = result.get("output", str(result))
            else:
                output = str(result)

            metrics.raw_response = output[:500]
            logger.info(f"📝 Response (truncated): {output[:200]}...")

            # Check if image was processed
            image_indicators = ["image", "screenshot", "visual", "see", "picture", "photo"]
            has_image_reference = any(indicator in output.lower() for indicator in image_indicators)

            if has_image_reference:
                logger.info("✅ Response mentions visual content - image may have been processed")
                metrics.multimodal_support = True
            else:
                logger.warning("⚠️ Response doesn't mention visual content - image likely ignored")
                metrics.multimodal_support = False

            # Check for tool calls
            tool_calls = parse_tool_calls_from_response(output)
            if tool_calls:
                logger.info(f"✅ Tool calls detected: {len(tool_calls)}")
                metrics.tool_calling_detected = True
                metrics.parsed_tools = tool_calls
            else:
                logger.warning("⚠️ No tool calls detected in response")
                metrics.tool_calling_detected = False

            # Check if response makes sense for CryptoApp
            crypto_indicators = ["crypto", "message digest", "cipher", "hash", "button"]
            has_crypto_context = any(indicator in output.lower() for indicator in crypto_indicators)

            if has_crypto_context:
                logger.info("✅ Response shows CryptoApp understanding")
                metrics.success_rate = 0.7
            else:
                logger.warning("⚠️ Response doesn't show CryptoApp understanding")
                metrics.success_rate = 0.3

            # Final assessment
            if metrics.multimodal_support and metrics.tool_calling_detected:
                logger.info("🎉 UNEXPECTED: AgentExecutor handled multimodal + tools!")
                metrics.success_rate = 1.0
            else:
                logger.warning("⚠️ EXPECTED: AgentExecutor failed with multimodal input")
                metrics.success_rate = 0.0

        except Exception as e:
            response_time = time.time() - start_time
            metrics.response_time = response_time

            logger.error(f"❌ AgentExecutor.invoke() failed: {e}")
            metrics.error_messages.append(f"AgentExecutor invoke failed: {e}")
            metrics.success_rate = 0.0

            # Check specific error types
            error_str = str(e).lower()
            if "image" in error_str or "multimodal" in error_str:
                logger.info("✅ EXPECTED: Multimodal-specific error confirmed")
                metrics.multimodal_support = False
            elif "tool" in error_str:
                logger.info("ℹ️ Tool-related error")
                metrics.tool_calling_detected = False

    except Exception as e:
        logger.error(f"❌ Test setup failed: {e}")
        metrics.error_messages.append(f"Test setup failed: {e}")
        metrics.success_rate = 0.0

    # Finalize metrics
    metrics.coordinate_accuracy = float('inf')  # No coordinates extracted
    metrics.hit_rate = 0.0  # No successful clicks
    metrics.memory_usage_mb = 0  # Not measured in this test

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
    print("🚀 Starting FASE A.1 - AgentExecutor Multimodal Failure Test")
    print("🎯 Expected: AgentExecutor should FAIL with multimodal input")

    result = test_agentexecutor_with_multimodal()

    print(f"\n🏁 Test completed!")
    print(f"Results saved to: validation/results/fase_a_langchain/")
    print(f"Logs saved to: validation/logs/fase_a_langchain/")

    return result


if __name__ == "__main__":
    main()
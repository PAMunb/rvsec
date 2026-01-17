#!/usr/bin/env python3
"""
Quick test to verify LLM integration fix.
Tests that llm_node correctly extracts actions from llm_client response.
"""

import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable verbose logging from libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def test_llm_extraction():
    """Test that LLM action extraction works correctly."""
    from rv_agent.config.agent_config import RVAgentConfig
    from rv_agent.llm.llm_client import LLMClient
    from rv_agent.prompts import v12 as prompt_module

    logger.info("=" * 60)
    logger.info("Testing LLM action extraction fix")
    logger.info("=" * 60)

    # Create config for multimode
    config = RVAgentConfig(
        package_name="test.package",
        agent_mode="multimode",
        llm_base_url="http://192.168.0.21:30000/v1"
    )

    # Initialize LLM client
    client = LLMClient(config, prompt_module)

    # Create mock screen description and screenshot
    from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
    screen_desc = ScreenDescription(
        activity="com.test.MainActivity",
        items=[]
    )

    # Use a simple base64 placeholder (1x1 pixel PNG)
    screenshot_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    ui_text = """
    UI Elements:
    1. [Button] "Login" at (350, 500)
    2. [EditText] "Username" at (350, 300)
    3. [EditText] "Password" at (350, 400)
    """

    logger.info("Calling LLM client...")
    start = time.perf_counter()

    result = client.generate_action(
        screen_description=screen_desc,
        screenshot_b64=screenshot_b64,
        ui_elements_text=ui_text,
        iteration=1,
        last_action_summary="Started app"
    )

    elapsed = time.perf_counter() - start
    logger.info(f"LLM response in {elapsed:.2f}s")

    # Check result structure
    logger.info(f"Result keys: {list(result.keys())}")
    logger.info(f"Success: {result.get('success')}")
    logger.info(f"Response type: {type(result.get('response'))}")

    response = result.get("response")
    if response:
        logger.info(f"Response content: {response.content[:200] if response.content else 'None'}...")
        tool_calls = getattr(response, "tool_calls", []) or []
        logger.info(f"Tool calls: {len(tool_calls)}")

        if tool_calls:
            for i, tc in enumerate(tool_calls):
                logger.info(f"  Tool {i}: name={tc.get('name')}, args={tc.get('args')}")

            # Test conversion to action format
            first_tool = tool_calls[0]
            llm_action = {
                "tool_name": first_tool.get("name", ""),
                "tool_args": first_tool.get("args", {})
            }
            logger.info(f"Converted action: {llm_action}")
            return True
        else:
            logger.warning("No tool calls in response!")
            return False
    else:
        logger.error("No response from LLM!")
        return False


def test_full_iteration():
    """Test a full iteration with multimode."""
    import subprocess

    logger.info("\n" + "=" * 60)
    logger.info("Testing full iteration with multimode")
    logger.info("=" * 60)

    # Run a single iteration test
    cmd = [
        "poetry", "run", "python", "-c",
        """
import logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

from rv_agent.agent.agent_factory import AgentFactory
from rv_agent.config.agent_config import RVAgentConfig

config = RVAgentConfig(
    package_name="br.unb.cic.cryptoapp",
    device_serial="emulator-5554",
    agent_mode="multimode",
    timeout_seconds=30,
    sglang_server_url="http://192.168.0.21:30000/v1"
)

print("Creating agent...")
agent = AgentFactory.create_agent(config)
print(f"Agent mode: {agent.config.agent_mode}")
print(f"LLM client: {agent.llm_client is not None}")

# Run single iteration
print("Running single iteration...")
result = agent.run_single_iteration()
print(f"Result: {result}")

agent.cleanup()
print("Done!")
"""
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[:500])

    return result.returncode == 0


if __name__ == "__main__":
    # Test 1: LLM extraction
    try:
        success1 = test_llm_extraction()
        logger.info(f"Test 1 (LLM extraction): {'PASS' if success1 else 'FAIL'}")
    except Exception as e:
        logger.error(f"Test 1 failed with exception: {e}")
        success1 = False

    # Test 2: Full iteration (optional, requires device)
    # try:
    #     success2 = test_full_iteration()
    #     logger.info(f"Test 2 (Full iteration): {'PASS' if success2 else 'FAIL'}")
    # except Exception as e:
    #     logger.error(f"Test 2 failed: {e}")
    #     success2 = False

    sys.exit(0 if success1 else 1)

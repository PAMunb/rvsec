#!/usr/bin/env python3
"""
Test V11 Enhanced UI Coverage Prompts

Compares v11 (enhanced) with v10 (baseline) metrics:
- android_scroll usage
- Text field interactions
- Spinner interactions
- android_back usage

Test parameters:
- Strategy: Greedy (most iterations in previous tests)
- Timeout: 120 seconds (2 minutes)
- Mode: Multimode (70% LLM, 30% algorithm)
"""

import sys
import logging
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_v11_ui_coverage():
    """Test V11 enhanced UI coverage prompt."""

    package = "br.unb.cic.cryptoapp"
    timeout_seconds = 120

    logger.info("="*80)
    logger.info("TESTING V11 ENHANCED UI COVERAGE")
    logger.info("="*80)
    logger.info(f"Package: {package}")
    logger.info(f"Strategy: GREEDY")
    logger.info(f"Timeout: {timeout_seconds}s")
    logger.info(f"Mode: Multimode (70% LLM, 30% Algorithm)")
    logger.info(f"Prompt Version: V11 (Enhanced)")
    logger.info("="*80)

    # Create configuration
    config = RVAgentConfig(
        package_name=package,
        device_id="emulator-5554",
        agent_mode="multimode",
        strategy="greedy",
        llm_probability=0.7,
        llm_model="qwen3-vl-4b-8k:latest",
        timeout=timeout_seconds,
        max_iterations=200,
        screenshot_dir="/tmp/rvagent_screenshots_v11",
        screenshot_rotation_limit=50,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248)
    )

    # Create agent
    logger.info("\nCreating agent with V11 prompts...")
    agent = AgentFactory.create_agent(config)

    # Run test
    logger.info("\nStarting exploration...\n")

    try:
        result = agent.run()

        logger.info("\n" + "="*80)
        logger.info("TEST COMPLETED")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(test_v11_ui_coverage())

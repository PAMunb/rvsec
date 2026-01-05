#!/usr/bin/env python3
"""
Test V13 Routing Fix - Verify double-counting bug is fixed.

Expected: With 70% LLM probability, should get ~70% LLM decisions
(not 30-38% like before the fix).
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_routing_fix():
    """Test with cryptoapp for 3 minutes to verify routing fix."""

    logger.info("="*80)
    logger.info("V13 ROUTING FIX VALIDATION")
    logger.info("="*80)
    logger.info("Testing cryptoapp for 180s to verify LLM percentage fix")
    logger.info("")

    # Test configuration
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        device_id="emulator-5554",
        timeout=180,  # 3 minutes
        agent_mode="multimode",
        strategy="greedy",
        llm_model="qwen3-vl-4b-8k:latest",
        llm_probability=0.7,  # 70% LLM
        prompt_version="v13",
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248),
        screenshot_dir="/tmp/v13_routing_fix_test",
        screenshot_rotation_limit=50
    )

    # Run test
    logger.info("Creating agent...")
    agent = AgentFactory.create_agent(config=config)

    logger.info("Running test...")
    results = agent.run()

    # Extract metrics
    total_actions = results.get("total_actions", 0)
    llm_decisions = results.get("llm_decisions", 0)
    algorithm_decisions = results.get("algorithm_decisions", 0)

    llm_percentage = (llm_decisions / total_actions * 100) if total_actions > 0 else 0
    algorithm_percentage = (algorithm_decisions / total_actions * 100) if total_actions > 0 else 0

    # Validation
    logger.info("")
    logger.info("="*80)
    logger.info("RESULTS:")
    logger.info("="*80)
    logger.info(f"Total actions: {total_actions}")
    logger.info(f"LLM decisions: {llm_decisions} ({llm_percentage:.1f}%)")
    logger.info(f"Algorithm decisions: {algorithm_decisions} ({algorithm_percentage:.1f}%)")
    logger.info("")

    # Expected: ~70% LLM (configured probability)
    # Tolerance: ±20% (50-90% acceptable for small sample)
    expected_llm_min = 50.0
    expected_llm_max = 90.0

    if expected_llm_min <= llm_percentage <= expected_llm_max:
        logger.info(f"✅ PASS: LLM percentage {llm_percentage:.1f}% within expected range ({expected_llm_min}-{expected_llm_max}%)")
        logger.info("✅ Routing fix successful!")
        status = "PASS"
    else:
        logger.error(f"❌ FAIL: LLM percentage {llm_percentage:.1f}% outside expected range ({expected_llm_min}-{expected_llm_max}%)")
        logger.error("❌ Routing still broken!")
        status = "FAIL"

    # Save results
    result_data = {
        "test_date": datetime.now().isoformat(),
        "app_package": "br.unb.cic.cryptoapp",
        "duration_s": 180,
        "total_actions": total_actions,
        "llm_decisions": llm_decisions,
        "algorithm_decisions": algorithm_decisions,
        "llm_percentage": llm_percentage,
        "algorithm_percentage": algorithm_percentage,
        "configured_llm_probability": 0.7,
        "validation": {
            "llm_percentage_ok": expected_llm_min <= llm_percentage <= expected_llm_max,
            "status": status
        }
    }

    output_file = Path("v13_routing_fix_test_result.json")
    with open(output_file, 'w') as f:
        json.dump(result_data, f, indent=2)

    logger.info(f"\nResults saved to: {output_file}")
    logger.info("="*80)

    return result_data


if __name__ == "__main__":
    test_routing_fix()

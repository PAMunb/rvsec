#!/usr/bin/env python3
"""
Test Detailed Counters - Validate new counter semantics.

Tests the separation of:
- Primary counters (llm_executed, algorithm_chosen) → 70/30 validation
- Auxiliary counters (llm_fallback, forced_back, recovery_actions) → special cases
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_detailed_counters():
    """Test with cryptoapp for 3 minutes to verify detailed counters."""

    logger.info("="*80)
    logger.info("DETAILED COUNTERS VALIDATION")
    logger.info("="*80)
    logger.info("Testing cryptoapp for 180s with new counter semantics")
    logger.info("")

    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        device_id="emulator-5554",
        timeout=180,
        agent_mode="multimode",
        strategy="greedy",
        llm_model="qwen3-vl-4b-8k:latest",
        llm_probability=0.7,
        prompt_version="v13",
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248),
        screenshot_dir="/tmp/detailed_counters_test",
        screenshot_rotation_limit=50
    )

    logger.info("Creating agent...")
    agent = AgentFactory.create_agent(config=config)

    logger.info("Running test...")
    results = agent.run()

    # Extract new metrics
    total_actions = results.get("total_actions", 0)
    llm_executed = results.get("llm_executed", 0)
    algorithm_chosen = results.get("algorithm_chosen", 0)
    llm_fallback = results.get("llm_fallback", 0)
    forced_back = results.get("forced_back", 0)
    recovery_actions = results.get("recovery_actions", 0)
    llm_percentage = results.get("llm_percentage", 0)

    # Display results
    logger.info("")
    logger.info("="*80)
    logger.info("RESULTS:")
    logger.info("="*80)
    logger.info("")
    logger.info("PRIMARY COUNTERS (validate 70/30):")
    logger.info(f"  llm_executed: {llm_executed}")
    logger.info(f"  algorithm_chosen: {algorithm_chosen}")
    logger.info(f"  Primary total: {llm_executed + algorithm_chosen}")
    logger.info(f"  LLM percentage: {llm_percentage:.1f}%")
    logger.info("")
    logger.info("AUXILIARY COUNTERS (special cases):")
    logger.info(f"  llm_fallback: {llm_fallback}")
    logger.info(f"  forced_back: {forced_back}")
    logger.info(f"  recovery_actions: {recovery_actions}")
    logger.info("")
    logger.info("TOTALS:")
    logger.info(f"  Total actions (all): {total_actions}")
    logger.info(f"  Breakdown: {llm_executed} + {algorithm_chosen} + {llm_fallback} + {forced_back} + {recovery_actions} = {total_actions}")
    logger.info("")

    # Validation
    expected_llm_min = 50.0
    expected_llm_max = 90.0

    if expected_llm_min <= llm_percentage <= expected_llm_max:
        logger.info(f"✅ PASS: LLM percentage {llm_percentage:.1f}% within expected range")
        status = "PASS"
    else:
        logger.error(f"❌ FAIL: LLM percentage {llm_percentage:.1f}% outside expected range")
        status = "FAIL"

    # Verify sum
    calculated_total = llm_executed + algorithm_chosen + llm_fallback + forced_back + recovery_actions
    if calculated_total == total_actions:
        logger.info(f"✅ Counter sum correct: {calculated_total} = {total_actions}")
    else:
        logger.error(f"❌ Counter sum mismatch: {calculated_total} ≠ {total_actions}")

    # Save results
    result_data = {
        "test_date": datetime.now().isoformat(),
        "app_package": "br.unb.cic.cryptoapp",
        "duration_s": 180,
        "primary_counters": {
            "llm_executed": llm_executed,
            "algorithm_chosen": algorithm_chosen,
            "llm_percentage": llm_percentage,
            "algorithm_percentage": 100 - llm_percentage
        },
        "auxiliary_counters": {
            "llm_fallback": llm_fallback,
            "forced_back": forced_back,
            "recovery_actions": recovery_actions
        },
        "totals": {
            "total_actions": total_actions,
            "primary_total": llm_executed + algorithm_chosen,
            "auxiliary_total": llm_fallback + forced_back + recovery_actions
        },
        "validation": {
            "llm_percentage_ok": expected_llm_min <= llm_percentage <= expected_llm_max,
            "sum_correct": calculated_total == total_actions,
            "status": status
        }
    }

    output_file = Path("detailed_counters_test_result.json")
    with open(output_file, 'w') as f:
        json.dump(result_data, f, indent=2)

    logger.info(f"\nResults saved to: {output_file}")
    logger.info("="*80)

    return result_data


if __name__ == "__main__":
    test_detailed_counters()

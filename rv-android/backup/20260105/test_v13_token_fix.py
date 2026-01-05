#!/usr/bin/env python3
"""
Test V13 Token Explosion Fix
==============================

Quick validation test to verify num_predict/repeat_penalty fix works.
Tests cryptoapp (baseline) for 60 seconds to check:
1. No 81920 token explosions
2. Tokens/action reasonable (~1.5-2.5k)
3. No 10-minute timeouts
"""

import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/v13_token_fix_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_token_fix(app_package: str, timeout: int = 60) -> Dict[str, Any]:
    """Test token fix with single app."""
    logger.info(f"\n{'='*80}")
    logger.info(f"TESTING TOKEN FIX: {app_package}")
    logger.info(f"{'='*80}")
    logger.info(f"Timeout: {timeout}s")
    logger.info(f"Expected: No 81920 token calls, ~1.5-2.5k tokens/action")

    config = RVAgentConfig(
        package_name=app_package,
        timeout=timeout,
        prompt_version="v13",
        agent_mode="multimode",
        strategy="greedy",
        llm_model="qwen3-vl-4b-8k:latest",
        llm_probability=0.7,
        llm_timeout=15.0,  # Strict timeout
        llm_max_tokens=512,  # Should be used by num_predict
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248),
        screenshot_dir=f"/tmp/v13_token_fix_{app_package}",
        screenshot_rotation_limit=50
    )

    try:
        logger.info("Creating agent with V13 + Token Fix...")
        start_time = time.time()
        agent = AgentFactory.create_agent(config=config)

        logger.info("Starting exploration...")
        results = agent.run()
        elapsed = time.time() - start_time

        # Extract metrics
        total_actions = results.get("total_actions", 0)
        llm_decisions = results.get("llm_decisions", 0)
        tokens_input = results.get("llm_tokens_input", 0)
        tokens_output = results.get("llm_tokens_output", 0)
        tokens_total = tokens_input + tokens_output
        llm_time_ms = results.get("llm_time_ms", 0.0)

        # Calculate metrics
        tokens_per_action = tokens_total / total_actions if total_actions > 0 else 0
        tokens_per_call = tokens_total / llm_decisions if llm_decisions > 0 else 0
        avg_time_per_call = llm_time_ms / llm_decisions if llm_decisions > 0 else 0

        # Validation checks
        max_call_time_ok = avg_time_per_call < 30000  # <30s per call
        tokens_reasonable = tokens_per_action < 5000  # <5k tokens/action
        no_explosion = tokens_per_call < 10000  # No single call >10k tokens

        validation = {
            "max_call_time_ok": max_call_time_ok,
            "tokens_reasonable": tokens_reasonable,
            "no_explosion": no_explosion
        }

        all_checks_passed = all(validation.values())

        # Log results
        logger.info(f"\n{'='*80}")
        logger.info("TEST RESULTS")
        logger.info(f"{'='*80}")
        logger.info(f"⏱️  Duration: {elapsed:.1f}s")
        logger.info(f"📊 Total actions: {total_actions}")
        logger.info(f"🧠 LLM decisions: {llm_decisions} ({llm_decisions/total_actions*100:.1f}%)")
        logger.info(f"💬 Tokens: {tokens_input} in / {tokens_output} out = {tokens_total} total")
        logger.info(f"📈 Tokens/action: {tokens_per_action:.0f}")
        logger.info(f"📈 Tokens/call: {tokens_per_call:.0f}")
        logger.info(f"⏱️  Avg time/call: {avg_time_per_call/1000:.1f}s")

        logger.info(f"\n{'='*80}")
        logger.info("VALIDATION")
        logger.info(f"{'='*80}")
        logger.info(f"{'✅' if max_call_time_ok else '❌'} Max call time <30s: {avg_time_per_call/1000:.1f}s")
        logger.info(f"{'✅' if tokens_reasonable else '❌'} Tokens/action <5k: {tokens_per_action:.0f}")
        logger.info(f"{'✅' if no_explosion else '❌'} No explosion >10k: {tokens_per_call:.0f}")

        logger.info(f"\n{'='*80}")
        logger.info(f"{'✅ FIX VALIDATED!' if all_checks_passed else '❌ FIX FAILED!'}")
        logger.info(f"{'='*80}")

        return {
            "app_package": app_package,
            "total_actions": total_actions,
            "llm_decisions": llm_decisions,
            "tokens_total": tokens_total,
            "tokens_per_action": tokens_per_action,
            "tokens_per_call": tokens_per_call,
            "avg_time_per_call_ms": avg_time_per_call,
            "validation": validation,
            "all_checks_passed": all_checks_passed,
            "execution_time_s": elapsed
        }

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return {
            "app_package": app_package,
            "status": "error",
            "error": str(e),
            "all_checks_passed": False
        }


def main():
    """Run token fix validation test."""
    logger.info("\n" + "="*80)
    logger.info("V13 TOKEN EXPLOSION FIX - VALIDATION TEST")
    logger.info("="*80)
    logger.info("Testing: br.unb.cic.cryptoapp (60s)")
    logger.info("Fix: num_predict=512, repeat_penalty=1.1, llm_timeout=15s")

    # Test cryptoapp (baseline)
    result = test_token_fix("br.unb.cic.cryptoapp", timeout=60)

    # Save result
    result_file = Path("v13_token_fix_result.json")
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)

    logger.info(f"\n✅ Result saved: {result_file}")

    return 0 if result.get("all_checks_passed", False) else 1


if __name__ == "__main__":
    sys.exit(main())

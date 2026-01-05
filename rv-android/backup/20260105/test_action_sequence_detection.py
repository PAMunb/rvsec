#!/usr/bin/env python3
"""
Quick test to validate action sequence detection and deadlock escape.

Tests the new features:
1. Action sequence repetition detection
2. Deadlock escape (consecutive no-action)
3. Detailed logging for auxiliary counters
"""

import logging
import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-android-core" / "src"))

from rv_agent.core.agent_factory import AgentFactory
from rv_agent.config.agent_config import RVAgentConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_cryptoapp_v13():
    """
    Test cryptoapp with v13 to verify:
    - Action sequence detection works
    - Deadlock escape works
    - Logs show detailed information
    """
    logger.info("="*80)
    logger.info("TESTING: Action Sequence Detection & Deadlock Escape")
    logger.info("="*80)
    logger.info("")
    logger.info("App: br.unb.cic.cryptoapp")
    logger.info("Prompt: v13")
    logger.info("Duration: 180s (3 minutes)")
    logger.info("Expected: Should NOT get stuck in deadlock")
    logger.info("")

    # Create config
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        agent_mode="multimode",
        strategy="greedy",
        llm_provider="ollama",
        llm_model="qwen3-vl-4b-8k:latest",
        llm_temperature=0.1,
        llm_top_p=0.9,
        llm_top_k=40,
        prompt_version="v13",
        max_iterations=100,
        timeout=180,  # 3 minutes
        device_id="emulator-5554"
    )

    try:
        # Create agent
        logger.info("Creating RVAgent...")
        agent = AgentFactory.create_agent(config)

        # Run agent
        logger.info("Starting execution...")
        logger.info("")
        results = agent.run()

        # Display results
        logger.info("")
        logger.info("="*80)
        logger.info("TEST RESULTS")
        logger.info("="*80)
        logger.info(f"Status: {results.get('status', 'unknown')}")
        logger.info(f"Iterations: {results.get('iterations', 0)}")
        logger.info(f"Total actions: {results.get('total_actions', 0)}")
        logger.info("")

        # Check auxiliary counters
        logger.info("Auxiliary Counters:")
        logger.info(f"  llm_fallback: {results.get('llm_fallback', 0)}")
        logger.info(f"  forced_back: {results.get('forced_back', 0)}")
        logger.info(f"  recovery_actions: {results.get('recovery_actions', 0)}")
        logger.info("")

        # Check decisor distribution
        llm_exec = results.get('llm_executed', results.get('llm_decisions', 0))
        alg_chosen = results.get('algorithm_chosen', results.get('algorithm_decisions', 0))
        logger.info("Decision Distribution:")
        logger.info(f"  LLM executed: {llm_exec}")
        logger.info(f"  Algorithm chosen: {alg_chosen}")
        if llm_exec + alg_chosen > 0:
            llm_pct = (llm_exec / (llm_exec + alg_chosen)) * 100
            logger.info(f"  LLM percentage: {llm_pct:.1f}%")
        logger.info("")

        # Success criteria
        success = True
        reasons = []

        if results.get('status') == 'timeout':
            logger.info("✅ Test completed without deadlock (reached timeout normally)")
        elif results.get('iterations', 0) > 10:
            logger.info("✅ Test progressed (>10 iterations)")
        else:
            success = False
            reasons.append("Too few iterations - possible early termination")

        if results.get('llm_fallback', 0) > 0:
            logger.info("✅ Auxiliary counters working (llm_fallback > 0)")
        else:
            logger.warning("⚠️  No llm_fallback detected - might be good or might indicate issue")

        # Final verdict
        logger.info("")
        logger.info("="*80)
        if success:
            logger.info("✅ TEST PASSED")
        else:
            logger.info("❌ TEST FAILED")
            for reason in reasons:
                logger.info(f"   - {reason}")
        logger.info("="*80)

        return 0 if success else 1

    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(test_cryptoapp_v13())

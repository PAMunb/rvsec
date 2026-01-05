"""
Test refactored RVAgent in multimode (LLM + Algorithm fallback).

Tests the AgentFactory pattern with multimode execution:
- LLM decides first (primary path)
- Algorithm fallback (DFS) when LLM fails
- Proper component dependency injection
"""

import json
import logging
import time

from rv_agent.core.agent_factory import AgentFactory
from rv_agent.config.agent_config import RVAgentConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_multimode():
    """Test refactored architecture with multimode (LLM + Algorithm)."""

    logger.info("=" * 80)
    logger.info("TEST: Multimode (LLM + Algorithm Fallback) - Refactored Architecture")
    logger.info("=" * 80)

    # Configuration for multimode
    config = RVAgentConfig(
        device_id="emulator-5554",
        package_name="br.unb.cic.cryptoapp",
        agent_mode="multimode",  # LLM + Algorithm fallback
        strategy="dfs",
        timeout=60,
        llm_provider="ollama",
        llm_model="qwen2.5:7b",
        llm_max_retries=2,
        screenshot_dir="/tmp/rvagent_screenshots",
        screenshot_rotation_limit=50
    )

    logger.info("Configuration:")
    logger.info(f"  Mode: {config.agent_mode}")
    logger.info(f"  LLM: {config.llm_provider}/{config.llm_model}")
    logger.info(f"  Strategy: {config.strategy}")
    logger.info(f"  Timeout: {config.timeout}s")

    # Create agent using factory
    logger.info("Creating agent using AgentFactory...")

    try:
        agent = AgentFactory.create_agent(
            config=config,
            static_data=None,
            device=None  # Will create DeviceInterface automatically
        )

        logger.info("✅ Agent created successfully")

        # Run exploration
        logger.info("Starting exploration...")
        results = agent.run()

        # Display results
        logger.info("=" * 80)
        logger.info("RESULTS")
        logger.info("=" * 80)
        logger.info(f"Status: {results['status']}")
        logger.info(f"Iterations: {results['iterations']}")
        logger.info(f"Execution time: {results['execution_time_s']:.1f}s")
        logger.info(f"Unique states: {results['unique_states']}")
        logger.info(f"Total transitions: {results['total_transitions']}")
        logger.info(f"LLM tokens (input): {results.get('llm_tokens_input', 0)}")
        logger.info(f"LLM tokens (output): {results.get('llm_tokens_output', 0)}")
        logger.info(f"LLM time: {results.get('llm_time_ms', 0):.1f}ms")
        logger.info(f"LLM decisions: {results.get('llm_decisions', 0)}")
        logger.info(f"Algorithm decisions: {results.get('algorithm_decisions', 0)}")

        # Save results
        output_file = "/tmp/test_refactored_multimode_results.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to: {output_file}")

        # Validation
        logger.info("=" * 80)
        logger.info("VALIDATION")
        logger.info("=" * 80)

        validation_passed = True

        # Check that we have some decisions
        total_decisions = results.get('llm_decisions', 0) + results.get('algorithm_decisions', 0)
        if total_decisions > 0:
            logger.info(f"✅ Total decisions: {total_decisions}")
        else:
            logger.error("❌ No decisions made")
            validation_passed = False

        # Check that we discovered states
        if results['unique_states'] > 0:
            logger.info(f"✅ States discovered: {results['unique_states']}")
        else:
            logger.error("❌ No states discovered")
            validation_passed = False

        # Check LLM decisions (should have at least tried)
        llm_decisions = results.get('llm_decisions', 0)
        if llm_decisions > 0:
            logger.info(f"✅ LLM decisions: {llm_decisions}")
        else:
            logger.warning(f"⚠️  No LLM decisions (fallback only): {results.get('algorithm_decisions', 0)} algorithm decisions")

        # Check algorithm decisions (fallback)
        algorithm_decisions = results.get('algorithm_decisions', 0)
        if algorithm_decisions > 0:
            logger.info(f"✅ Algorithm fallback used: {algorithm_decisions} decisions")
        else:
            logger.info(f"ℹ️  No algorithm fallback needed (LLM only)")

        logger.info("=" * 80)
        if validation_passed:
            logger.info("✅ TEST PASSED - Multimode working correctly!")
        else:
            logger.error("❌ TEST FAILED")
        logger.info("=" * 80)

        return validation_passed

    except Exception as e:
        logger.error(f"❌ Failed to create agent: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_multimode()
    exit(0 if success else 1)

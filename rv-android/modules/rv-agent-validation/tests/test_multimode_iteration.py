#!/usr/bin/env python3
"""
Test multimode iteration with LLM integration.
Verifies that LangGraph executes LLM actions correctly.
"""

import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce verbosity of some loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uiautomator2").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def test_multimode_iteration():
    """Test a full multimode execution with short timeout."""
    from rv_agent.agent.agent_factory import AgentFactory
    from rv_agent.config.agent_config import RVAgentConfig

    logger.info("=" * 60)
    logger.info("Testing multimode execution with LLM")
    logger.info("=" * 60)

    # Create config for multimode with short timeout
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        device_id="emulator-5554",
        agent_mode="multimode",
        timeout=60,  # Short timeout for testing (60 seconds min)
        llm_base_url="http://192.168.0.21:30000/v1",
        debug_mode=True
    )

    logger.info(f"Config: agent_mode={config.agent_mode}")
    logger.info(f"Config: llm_base_url={config.llm_base_url}")
    logger.info(f"Config: timeout={config.timeout}s")

    # Create agent
    logger.info("Creating agent...")
    agent = AgentFactory.create_agent(config)

    logger.info(f"Agent mode: {agent.config.agent_mode}")
    logger.info(f"LLM client available: {agent.llm_client is not None}")
    logger.info(f"Navigation guidance enabled: {agent.navigation_guidance.is_enabled if agent.navigation_guidance else False}")

    # Run agent (has internal timeout loop)
    logger.info("\nRunning agent for 60 seconds...")
    result = agent.run()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("EXECUTION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Total iterations: {result.get('iterations', 0)}")
    logger.info(f"Execution time: {result.get('execution_time_s', 0):.1f}s")
    logger.info(f"Unique states: {result.get('unique_states', 0)}")
    logger.info(f"Total transitions: {result.get('total_transitions', 0)}")

    # LLM metrics
    logger.info("\n--- LLM Metrics ---")
    logger.info(f"LLM tokens input: {result.get('llm_tokens_input', 0)}")
    logger.info(f"LLM tokens output: {result.get('llm_tokens_output', 0)}")
    logger.info(f"LLM time: {result.get('llm_time_ms', 0):.0f}ms")

    # Decision breakdown
    counters = result.get("decision_counters", {})
    logger.info("\n--- Decision Breakdown ---")
    logger.info(f"LLM decisions: {counters.get('llm_decisions', 0)}")
    logger.info(f"Algorithm decisions: {counters.get('algorithm_decisions', 0)}")
    logger.info(f"LLM executions: {counters.get('llm_executions', 0)}")
    logger.info(f"Algorithm executions: {counters.get('algorithm_executions', 0)}")

    # Check LLM stats from client
    if agent.llm_client:
        stats = agent.llm_client.get_stats()
        logger.info("\n--- LLM Client Stats ---")
        logger.info(f"Total LLM calls: {stats.get('total_calls', 0)}")
        logger.info(f"Total tokens: {stats.get('total_tokens', 0)}")
        logger.info(f"Avg latency: {stats.get('avg_latency_ms', 0):.0f}ms")
        parser_stats = stats.get('parser_stats', {})
        logger.info(f"Parser success rate: {parser_stats.get('success_rate', 0):.1%}")

    # Success criteria: agent ran and completed at least some iterations
    iterations = result.get('iterations', 0)
    llm_calls = agent.llm_client.get_stats().get('total_calls', 0) if agent.llm_client else 0
    success = iterations > 0 and llm_calls > 0

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Test {'PASSED' if success else 'FAILED'}")
    logger.info(f"  - Iterations executed: {iterations}")
    logger.info(f"  - LLM calls made: {llm_calls}")
    return success


if __name__ == "__main__":
    try:
        success = test_multimode_iteration()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        sys.exit(1)

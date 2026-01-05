#!/usr/bin/env python3
"""
Memory Sync Validation Test
============================

Validates that memory statistics are properly collected via the facade pattern.

Success criteria:
- ui_coverage.total_unique_elements > 0
- short_term.iteration_count > 0
- long_term.total_states > 0
- dynamic_graph.total_states > 0
"""

import sys
import logging
from pathlib import Path

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_memory_sync():
    """
    Test memory sync with cryptoapp.

    Runs a 60-second test and validates that all memory statistics
    are properly collected.
    """
    logger.info("="*80)
    logger.info("MEMORY SYNC VALIDATION TEST")
    logger.info("="*80)

    # Configure test
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        timeout=60,  # 1 minute test
        prompt_version="v10",  # Use baseline prompt
        agent_mode="multimode",
        strategy="greedy",
        llm_model="qwen3-vl-4b-8k:latest",
        llm_probability=0.7,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248),
        screenshot_dir="/tmp/memory_sync_test",
        screenshot_rotation_limit=50
    )

    logger.info(f"Testing with: {config.package_name}")
    logger.info(f"Timeout: {config.timeout}s")
    logger.info(f"Prompt: {config.prompt_version}")

    try:
        # Create and run agent
        agent = AgentFactory.create_agent(config=config)
        results = agent.run()

        logger.info("\n" + "-"*80)
        logger.info("EXECUTION RESULTS")
        logger.info("-"*80)
        logger.info(f"Status: {results.get('status')}")
        logger.info(f"Iterations: {results.get('iterations')}")
        logger.info(f"Total actions: {results.get('total_actions')}")
        logger.info(f"Execution time: {results.get('execution_time_s'):.1f}s")

        # Extract memory stats
        memory_stats = results.get("memory_stats", {})

        if not memory_stats:
            logger.error("❌ FAILED: memory_stats not found in results")
            return False

        logger.info("\n" + "-"*80)
        logger.info("MEMORY STATISTICS VALIDATION")
        logger.info("-"*80)

        # Validate UI Coverage
        ui_coverage = memory_stats.get("ui_coverage", {})
        ui_elements = ui_coverage.get("total_unique_elements", 0)
        logger.info(f"UI Coverage - Total unique elements: {ui_elements}")

        # Validate Short Term Memory
        short_term = memory_stats.get("short_term", {})
        st_iterations = short_term.get("iteration_count", 0)
        logger.info(f"Short Term Memory - Iteration count: {st_iterations}")

        # Validate Long Term Memory
        long_term = memory_stats.get("long_term", {})
        lt_states = long_term.get("total_states", 0)
        logger.info(f"Long Term Memory - Total states: {lt_states}")

        # Validate Dynamic Graph
        dynamic_graph = memory_stats.get("dynamic_graph", {})
        graph_states = dynamic_graph.get("total_states", 0)
        graph_transitions = dynamic_graph.get("total_transitions", 0)
        logger.info(f"Dynamic Graph - States: {graph_states}, Transitions: {graph_transitions}")

        # Check success criteria
        logger.info("\n" + "-"*80)
        logger.info("VALIDATION RESULTS")
        logger.info("-"*80)

        success = True

        if ui_elements > 0:
            logger.info("✅ UI Coverage: total_unique_elements > 0")
        else:
            logger.error("❌ UI Coverage: total_unique_elements = 0")
            success = False

        if st_iterations > 0:
            logger.info("✅ Short Term Memory: iteration_count > 0")
        else:
            logger.error("❌ Short Term Memory: iteration_count = 0")
            success = False

        if lt_states > 0:
            logger.info("✅ Long Term Memory: total_states > 0")
        else:
            logger.error("❌ Long Term Memory: total_states = 0")
            success = False

        if graph_states > 0:
            logger.info("✅ Dynamic Graph: total_states > 0")
        else:
            logger.error("❌ Dynamic Graph: total_states = 0")
            success = False

        # Overall result
        logger.info("\n" + "="*80)
        if success:
            logger.info("✅ MEMORY SYNC VALIDATION: PASSED")
            logger.info("All memory statistics are properly collected!")
        else:
            logger.error("❌ MEMORY SYNC VALIDATION: FAILED")
            logger.error("Some memory statistics are not being collected")
        logger.info("="*80)

        return success

    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = validate_memory_sync()
    sys.exit(0 if success else 1)

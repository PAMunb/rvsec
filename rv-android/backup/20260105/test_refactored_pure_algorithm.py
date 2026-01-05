"""
Test refactored RVAgent with pure_algorithm mode using AgentFactory.
"""

import logging
import json
from pathlib import Path

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_pure_algorithm():
    """Test pure algorithm mode (no LLM)."""
    logger.info("=" * 80)
    logger.info("TEST: Pure Algorithm Mode (DFS) - Refactored Architecture")
    logger.info("=" * 80)

    # Configuration
    config = RVAgentConfig(
        device_id="emulator-5554",
        package_name="br.unb.cic.cryptoapp",
        agent_mode="pure_algorithm",  # No LLM (corrected field name)
        timeout=60  # 1 minute for quick test
    )

    logger.info(f"Configuration:")
    logger.info(f"  Mode: {config.agent_mode}")
    logger.info(f"  Package: {config.package_name}")
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
    except Exception as e:
        logger.error(f"❌ Failed to create agent: {e}", exc_info=True)
        return

    # Run exploration
    logger.info("Starting exploration...")
    try:
        results = agent.run()

        # Log results
        logger.info("=" * 80)
        logger.info("EXPLORATION RESULTS")
        logger.info("=" * 80)
        logger.info(f"Status: {results['status']}")
        logger.info(f"Iterations: {results['iterations']}")
        logger.info(f"Execution time: {results['execution_time_s']:.1f}s")
        logger.info(f"Unique states: {results['unique_states']}")
        logger.info(f"Total transitions: {results['total_transitions']}")
        logger.info(f"Algorithm decisions: {results['algorithm_decisions']}")
        logger.info(f"LLM decisions: {results['llm_decisions']}")

        # Save results
        output_file = Path("/tmp/test_refactored_pure_algorithm_results.json")
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to: {output_file}")

        # Validate results
        logger.info("=" * 80)
        logger.info("VALIDATION")
        logger.info("=" * 80)

        validations = []

        # Check that only algorithm was used
        if results['llm_decisions'] == 0:
            logger.info("✅ No LLM decisions (pure_algorithm mode working)")
            validations.append(True)
        else:
            logger.error(f"❌ LLM decisions found: {results['llm_decisions']} (should be 0)")
            validations.append(False)

        # Check that algorithm was used
        if results['algorithm_decisions'] > 0:
            logger.info(f"✅ Algorithm decisions: {results['algorithm_decisions']}")
            validations.append(True)
        else:
            logger.error("❌ No algorithm decisions (should have at least 1)")
            validations.append(False)

        # Check states discovered
        if results['unique_states'] > 0:
            logger.info(f"✅ States discovered: {results['unique_states']}")
            validations.append(True)
        else:
            logger.error("❌ No states discovered")
            validations.append(False)

        # Overall result
        if all(validations):
            logger.info("=" * 80)
            logger.info("✅ TEST PASSED - Pure algorithm mode working correctly!")
            logger.info("=" * 80)
        else:
            logger.error("=" * 80)
            logger.error("❌ TEST FAILED - Some validations failed")
            logger.error("=" * 80)

    except Exception as e:
        logger.error(f"❌ Exploration failed: {e}", exc_info=True)


if __name__ == "__main__":
    test_pure_algorithm()

"""
Quick test to validate multimode fixes.
"""
import sys
import json
import logging
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.rv_agent import RVAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run quick multimode validation test."""
    logger.info("=" * 80)
    logger.info("MULTIMODE FIX VALIDATION - 60s test")
    logger.info("=" * 80)

    # Configuration
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        device_id="emulator-5554",
        timeout=60,  # Minimum allowed
        agent_mode="multimode",
        llm_probability=0.7,
        llm_model="qwen3-vl:4b",
        llm_temperature=0.25
    )

    # Create and run agent
    try:
        agent = RVAgent(config)
        logger.info("Agent initialized successfully")

        logger.info("Starting quick multimode test...")
        results = agent.run()

        logger.info("=" * 80)
        logger.info("RESULTS")
        logger.info("=" * 80)
        logger.info(f"Status: {results.get('status')}")
        logger.info(f"Iterations: {results.get('iterations')}")
        logger.info(f"Time: {results.get('execution_time_s', 0):.1f}s")
        logger.info(f"Unique states: {results.get('unique_states', 0)}")
        logger.info(f"Transitions: {results.get('total_transitions', 0)}")

        # Check decision counters
        llm_decisions = results.get('llm_decisions', -1)
        dfs_decisions = results.get('dfs_decisions', -1)
        total_decisions = llm_decisions + dfs_decisions

        logger.info("")
        logger.info("DECISION COUNTERS (should NOT be -1/-1)")
        logger.info("-" * 80)
        logger.info(f"LLM decisions: {llm_decisions}")
        logger.info(f"DFS decisions: {dfs_decisions}")
        logger.info(f"Total decisions: {total_decisions}")

        if llm_decisions >= 0 and dfs_decisions >= 0:
            logger.info("✅ Decision counters are correctly persisted!")
        else:
            logger.error("❌ Decision counters NOT persisted (still -1/-1)")

        # Get transition graph report
        if hasattr(agent, 'dynamic_graph'):
            report = agent.dynamic_graph.get_transition_graph_report()

            logger.info("")
            logger.info("TRANSITION GRAPH REPORT")
            logger.info("-" * 80)
            logger.info(f"Total states: {report['total_states']}")
            logger.info(f"Total transitions: {report['total_transitions']}")

            # Try to display transitions (should not crash)
            logger.info("")
            logger.info("TRANSITIONS (testing fixed keys):")
            try:
                for trans in report['transitions'][:5]:
                    logger.info(f"  {trans['from'][:8]} → {trans['to'][:8]}: {trans['action_count']} actions")
                logger.info("✅ Transition reporting works correctly!")
            except KeyError as e:
                logger.error(f"❌ Transition reporting still broken: {e}")

        # Save results
        output_file = "multimode_fix_validation_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info("")
        logger.info(f"Report saved to: {output_file}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

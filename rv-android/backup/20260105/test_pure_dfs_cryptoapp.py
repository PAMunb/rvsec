"""
Test PURE_DFS mode (no LLM dependency).

Tests the DFS standalone algorithm without LLM.
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
    """Run DFS test with CryptoApp."""
    logger.info("=" * 80)
    logger.info("PURE DFS Test - CryptoApp (NO LLM)")
    logger.info("=" * 80)

    # Configuration - PURE_DFS mode
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        device_id="emulator-5554",
        timeout=120,  # 2 minutes - only stops by timeout
        agent_mode="pure_dfs"  # Pure DFS - NO LLM
    )

    logger.info(f"Mode: {config.get_agent_mode()}")
    logger.info(f"Package: {config.package_name}")
    logger.info(f"Timeout: {config.timeout}s")
    logger.info("⚡ DFS mode: Zero LLM cost, ~0.1s per iteration")

    # Create and run agent
    try:
        agent = RVAgent(config)
        logger.info("Agent initialized successfully")

        logger.info("Starting DFS exploration...")
        results = agent.run()

        logger.info("=" * 80)
        logger.info("EXECUTION COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Status: {results.get('status')}")
        logger.info(f"Iterations: {results.get('iterations')}")
        logger.info(f"Time: {results.get('execution_time_s', 0):.1f}s")
        logger.info(f"Unique states: {results.get('unique_states', 0)}")
        logger.info(f"Transitions: {results.get('total_transitions', 0)}")

        # Get transition graph report
        if hasattr(agent, 'dynamic_graph'):
            report = agent.dynamic_graph.get_transition_graph_report()

            logger.info("")
            logger.info("TRANSITION GRAPH REPORT")
            logger.info("-" * 80)
            logger.info(f"Total states: {report['total_states']}")
            logger.info(f"Total transitions: {report['total_transitions']}")
            logger.info(f"Average coverage: {report['avg_coverage']:.1f}%")

            logger.info("")
            logger.info("STATES:")
            for state in report['states'][:10]:  # Show first 10
                logger.info(f"  {state['screen_hash'][:8]}: "
                           f"{state['activity']}, "
                           f"visits={state['visit_count']}, "
                           f"coverage={state['coverage']:.1f}%")

            logger.info("")
            logger.info("TRANSITIONS (first 10):")
            for t in report['transitions'][:10]:
                logger.info(f"  {t['from'][:8]} → {t['to'][:8]}: "
                           f"{t['action_count']} actions")

            # Save report to file
            output_file = Path("pure_dfs_test_results.json")
            with open(output_file, 'w') as f:
                json.dump({
                    "results": results,
                    "transition_graph": report
                }, f, indent=2, default=str)
            logger.info(f"\nReport saved to: {output_file}")

        return results

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    main()

"""
Test HYBRID mode (LLM + DFS fallback).

Tests the hybrid strategy with LLM-guided exploration and automatic DFS fallback.
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
    """Run hybrid test with CryptoApp."""
    logger.info("=" * 80)
    logger.info("HYBRID Mode Test - CryptoApp (LLM + DFS Fallback)")
    logger.info("=" * 80)

    # Configuration - HYBRID mode
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        device_id="emulator-5554",
        timeout=120,  # 2 minutes
        agent_mode="hybrid",  # Hybrid: LLM with DFS fallback
        llm_model="qwen3-vl:4b",  # Using Qwen3-VL 4B
        llm_temperature=0.25,
        llm_max_retries=2  # Fallback to DFS after 2 LLM failures
    )

    logger.info(f"Mode: {config.get_agent_mode()}")
    logger.info(f"Package: {config.package_name}")
    logger.info(f"Timeout: {config.timeout}s")
    logger.info(f"LLM Model: {config.llm_model}")
    logger.info(f"LLM Temperature: {config.llm_temperature}")
    logger.info(f"Max LLM Retries: {config.llm_max_retries}")
    logger.info("🔀 Hybrid mode: LLM guidance with automatic DFS fallback on failures/loops")

    # Create and run agent
    try:
        agent = RVAgent(config)
        logger.info("Agent initialized successfully")

        logger.info("Starting hybrid exploration...")
        results = agent.run()

        logger.info("=" * 80)
        logger.info("EXECUTION COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Status: {results.get('status')}")
        logger.info(f"Iterations: {results.get('iterations')}")
        logger.info(f"Time: {results.get('execution_time_s', 0):.1f}s")
        logger.info(f"Unique states: {results.get('unique_states', 0)}")
        logger.info(f"Transitions: {results.get('total_transitions', 0)}")

        # Decision statistics
        llm_decisions = results.get('llm_decisions', 0)
        dfs_decisions = results.get('dfs_decisions', 0)
        total_decisions = llm_decisions + dfs_decisions

        logger.info("")
        logger.info("DECISION DISTRIBUTION")
        logger.info("-" * 80)
        logger.info(f"LLM decisions: {llm_decisions} ({100*llm_decisions/total_decisions if total_decisions > 0 else 0:.1f}%)")
        logger.info(f"DFS decisions: {dfs_decisions} ({100*dfs_decisions/total_decisions if total_decisions > 0 else 0:.1f}%)")
        logger.info(f"Total decisions: {total_decisions}")

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
            for trans in report['transitions'][:10]:
                logger.info(f"  {trans['from_hash'][:8]} → {trans['to_hash'][:8]}: {trans['count']} actions")

        # Save results
        output_file = "hybrid_test_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info("")
        logger.info(f"Report saved to: {output_file}")

    except KeyboardInterrupt:
        logger.info("\n⚠️  Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test all 3 exploration strategies in multimode (hybrid LLM + Algorithm).

Tests:
1. Greedy + LLM (60 seconds)
2. SimulatedAnnealing + LLM (60 seconds)
3. GeneticAlgorithm + LLM (60 seconds)

Expected behavior:
- ~70% decisions from LLM
- ~30% decisions from algorithm
- All strategies sharing DynamicStateGraph
- No "Unknown action type" warnings
"""

import sys
import logging
from pathlib import Path

# Add modules to path
modules_path = Path(__file__).parent / "modules"
sys.path.insert(0, str(modules_path / "rv-agent/src"))
sys.path.insert(0, str(modules_path / "rv-android-core/src"))
sys.path.insert(0, str(modules_path / "rv-screen-parser/src"))
sys.path.insert(0, str(modules_path / "rv-llm/src"))
sys.path.insert(0, str(modules_path / "rv-uiautomator/src"))

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory
from rv_agent.core.device_interface import DeviceInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_strategy(strategy_name: str, timeout_seconds: int = 60):
    """
    Test single strategy in multimode.

    Args:
        strategy_name: Strategy to test (greedy, simulated_annealing, genetic_algorithm)
        timeout_seconds: Test duration in seconds
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing Strategy: {strategy_name.upper()} in MULTIMODE")
    logger.info(f"{'='*60}\n")

    try:
        # Step 1: Initialize device
        logger.info("Step 1: Initializing device and restarting app")
        device = DeviceInterface()  # Auto-connects in __init__

        # Restart app
        package = "br.unb.cic.cryptoapp"
        logger.info(f"Stopping {package}")
        device.stop_app(package)

        import time
        time.sleep(1)

        logger.info(f"Launching {package} from launcher")
        device.start_app(package)
        time.sleep(5)

        logger.info("App restarted successfully")

        # Step 2: Create multimode config
        logger.info(f"Step 2: Creating multimode config (strategy={strategy_name}, llm_prob=0.7)")
        config = RVAgentConfig(
            package_name=package,
            device_id="emulator-5554",
            agent_mode="multimode",
            strategy=strategy_name,
            llm_probability=0.7,  # 70% LLM, 30% algorithm
            llm_model="qwen3-vl-4b-8k:latest",  # Custom 8k context model
            timeout=timeout_seconds,
            max_iterations=200,
            screenshot_dir="/tmp/rvagent_screenshots",
            screenshot_rotation_limit=50,
            device_dimensions=(1080, 1920),
            optimized_dimensions=(704, 1248)
        )

        # Step 3: Create RVAgent
        logger.info("Step 3: Creating RVAgent with device and LLM integration")
        agent = AgentFactory.create_agent(
            config=config,
            static_data=None,
            device=device
        )

        # Step 4: Run exploration
        logger.info(f"Step 4: Starting multimode exploration with {strategy_name} + LLM")
        logger.info(f"Timeout: {timeout_seconds} seconds")

        result = agent.run()  # Timeout configured in RVAgentConfig

        # Step 5: Analyze results
        logger.info("\n" + "="*60)
        logger.info(f"RESULTS: {strategy_name.upper()}")
        logger.info("="*60)

        # Get routing statistics
        routing_counters = agent.routing_manager.get_decision_counters()
        llm_decisions = routing_counters["llm_decisions"]
        alg_decisions = routing_counters["algorithm_decisions"]
        total_decisions = llm_decisions + alg_decisions

        if total_decisions > 0:
            llm_pct = (llm_decisions / total_decisions) * 100
            alg_pct = (alg_decisions / total_decisions) * 100
        else:
            llm_pct = alg_pct = 0

        logger.info(f"Iterations: {result['iteration']}")
        logger.info(f"Unique states: {len(result['visited_states'])}")
        logger.info(f"LLM decisions: {llm_decisions} ({llm_pct:.1f}%)")
        logger.info(f"Algorithm decisions: {alg_decisions} ({alg_pct:.1f}%)")
        logger.info(f"Total decisions: {total_decisions}")

        # Tokens
        logger.info(f"LLM tokens in: {result.get('llm_tokens_input', 0)}")
        logger.info(f"LLM tokens out: {result.get('llm_tokens_output', 0)}")
        logger.info(f"LLM time (ms): {result.get('llm_time_ms', 0):.0f}")

        # Check distribution
        logger.info("\n" + "-"*60)
        if 60 <= llm_pct <= 80:
            logger.info("✅ LLM percentage within expected range (60-80%)")
        else:
            logger.warning(f"⚠️  LLM percentage outside expected range: {llm_pct:.1f}%")

        if 20 <= alg_pct <= 40:
            logger.info("✅ Algorithm percentage within expected range (20-40%)")
        else:
            logger.warning(f"⚠️  Algorithm percentage outside expected range: {alg_pct:.1f}%")

        logger.info(f"✅ {strategy_name.upper()} test completed successfully\n")

        return {
            "strategy": strategy_name,
            "success": True,
            "iterations": result['iteration'],
            "unique_states": len(result['visited_states']),
            "llm_decisions": llm_decisions,
            "algorithm_decisions": alg_decisions,
            "llm_percentage": llm_pct,
            "algorithm_percentage": alg_pct
        }

    except Exception as e:
        logger.error(f"❌ {strategy_name.upper()} test failed: {e}", exc_info=True)
        return {
            "strategy": strategy_name,
            "success": False,
            "error": str(e)
        }


def main():
    """Test all 3 strategies in sequence."""
    strategies = [
        "greedy",
        "simulated_annealing",
        "genetic_algorithm"
    ]

    results = []

    logger.info("\n" + "="*80)
    logger.info("MULTIMODE STRATEGY TEST SUITE")
    logger.info("Testing Greedy, SimulatedAnnealing, and GeneticAlgorithm")
    logger.info("Mode: Multimode (70% LLM, 30% Algorithm)")
    logger.info("="*80 + "\n")

    for strategy in strategies:
        result = test_strategy(strategy, timeout_seconds=300)
        results.append(result)

        # Pause between tests
        if strategy != strategies[-1]:
            logger.info("Pausing 5 seconds before next test...")
            import time
            time.sleep(5)

    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY: ALL STRATEGIES")
    logger.info("="*80)

    for result in results:
        if result["success"]:
            logger.info(f"\n{result['strategy'].upper()}: ✅ SUCCESS")
            logger.info(f"  Iterations: {result['iterations']}")
            logger.info(f"  Unique states: {result['unique_states']}")
            logger.info(f"  LLM: {result['llm_decisions']} ({result['llm_percentage']:.1f}%)")
            logger.info(f"  Algorithm: {result['algorithm_decisions']} ({result['algorithm_percentage']:.1f}%)")
        else:
            logger.info(f"\n{result['strategy'].upper()}: ❌ FAILED")
            logger.info(f"  Error: {result.get('error', 'Unknown')}")

    # Check if all passed
    all_passed = all(r["success"] for r in results)

    logger.info("\n" + "="*80)
    if all_passed:
        logger.info("✅ ALL TESTS PASSED")
    else:
        logger.error("❌ SOME TESTS FAILED")
    logger.info("="*80 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

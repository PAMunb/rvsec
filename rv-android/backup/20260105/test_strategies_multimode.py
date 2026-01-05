#!/usr/bin/env python3
"""
Test script for new exploration strategies with multimode (LLM + algorithm hybrid).

Tests each strategy with:
- Clean app restart before test
- Multimode with 70% LLM / 30% algorithm
- Full RVAgent lifecycle
- Detailed logging for analysis
"""

import sys
import logging
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-uiautomator" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-screen-parser" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-llm" / "src"))

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory
from rv_agent.core.device_interface import DeviceInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_multimode_strategy(strategy_name: str, timeout: int = 120, llm_probability: float = 0.70):
    """
    Test a single strategy in multimode with LLM integration.

    Args:
        strategy_name: Strategy to test (greedy, simulated_annealing, genetic_algorithm)
        timeout: Test timeout in seconds
        llm_probability: Probability of using LLM (0.0-1.0)
    """
    package_name = "br.unb.cic.cryptoapp"
    device_id = "emulator-5554"

    print("\n" + "="*80)
    print(f"TESTING MULTIMODE: {strategy_name.upper()} + LLM")
    print("="*80)
    print(f"Package: {package_name}")
    print(f"Timeout: {timeout}s")
    print(f"Device: {device_id}")
    print(f"LLM Probability: {llm_probability:.0%}")
    print(f"Algorithm Probability: {1-llm_probability:.0%}")
    print(f"LLM Model: qwen3-vl-4b-8k")
    print("="*80 + "\n")

    # Step 1: Create device interface and force restart app
    logger.info("Step 1: Initializing device and restarting app")
    device = DeviceInterface(device_id=device_id)

    # Force stop and restart app
    logger.info(f"Stopping {package_name}")
    device.stop_app(package_name)

    # Start app fresh
    logger.info(f"Launching {package_name} from launcher")
    device.launch_app(package_name)

    # Wait for app to stabilize
    import time
    time.sleep(3)

    logger.info("App restarted successfully")

    # Step 2: Create RVAgent config for multimode
    logger.info(f"Step 2: Creating multimode config (strategy={strategy_name}, llm_prob={llm_probability})")
    config = RVAgentConfig(
        package_name=package_name,
        device_id=device_id,
        agent_mode="multimode",
        strategy=strategy_name,
        llm_probability=llm_probability,
        llm_model="qwen3-vl-4b-8k",  # 8k context window
        timeout=timeout,
        max_iterations=200,
        screenshot_dir="/tmp/rvagent_screenshots",
        screenshot_rotation_limit=50,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248)
    )

    # Step 3: Create agent with device (full integration)
    logger.info("Step 3: Creating RVAgent with device and LLM integration")
    agent = AgentFactory.create_agent(
        config=config,
        static_data=None,
        device=device  # Pass device for full integration
    )

    # Step 4: Run exploration
    logger.info(f"Step 4: Starting multimode exploration with {strategy_name} + LLM")
    print(f"\n▶️  Starting {strategy_name} + LLM multimode exploration...\n")

    try:
        results = agent.run()

        # Calculate actual decision ratio
        total_decisions = results.get('llm_decisions', 0) + results.get('algorithm_decisions', 0)
        actual_llm_ratio = results.get('llm_decisions', 0) / total_decisions if total_decisions > 0 else 0

        # Display results
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)
        print(f"Strategy: {strategy_name} + LLM")
        print(f"Status: {results.get('status', 'unknown')}")
        print(f"Iterations: {results.get('iterations', 0)}")
        print(f"Unique States: {results.get('unique_states', 0)}")
        print(f"Transitions: {results.get('transitions', 0)}")
        print(f"LLM Decisions: {results.get('llm_decisions', 0)}")
        print(f"Algorithm Decisions: {results.get('algorithm_decisions', 0)}")
        print(f"Actual LLM Ratio: {actual_llm_ratio:.1%} (expected {llm_probability:.0%})")
        print(f"LLM Time: {results.get('llm_time_ms', 0)/1000:.1f}s")
        print(f"Execution Time: {results.get('execution_time', 0):.1f}s")
        print("="*80 + "\n")

        return results

    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

    finally:
        # Cleanup
        logger.info("Cleaning up...")
        device.stop_app(package_name)


def main():
    """Run multimode tests for all strategies."""
    import argparse

    parser = argparse.ArgumentParser(description="Test exploration strategies in multimode")
    parser.add_argument(
        "--strategy",
        choices=["greedy", "simulated_annealing", "genetic_algorithm", "all"],
        default="all",
        help="Strategy to test (default: all)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Test timeout in seconds (default: 120)"
    )
    parser.add_argument(
        "--llm-prob",
        type=float,
        default=0.70,
        help="LLM probability (default: 0.70)"
    )

    args = parser.parse_args()

    if args.strategy == "all":
        strategies = ["greedy", "simulated_annealing", "genetic_algorithm"]
    else:
        strategies = [args.strategy]

    results = {}
    for strategy in strategies:
        try:
            result = test_multimode_strategy(strategy, timeout=args.timeout, llm_probability=args.llm_prob)
            results[strategy] = result
        except KeyboardInterrupt:
            logger.warning(f"Test interrupted for {strategy}")
            break
        except Exception as e:
            logger.error(f"Fatal error testing {strategy}: {e}")
            results[strategy] = {"status": "fatal_error", "error": str(e)}

    # Summary
    print("\n" + "="*80)
    print("MULTIMODE TEST SUMMARY")
    print("="*80)
    for strategy, result in results.items():
        status = result.get('status', 'unknown')
        iterations = result.get('iterations', 0)
        states = result.get('unique_states', 0)
        llm_decisions = result.get('llm_decisions', 0)
        algo_decisions = result.get('algorithm_decisions', 0)
        print(f"{strategy:25} | Status: {status:10} | Iter: {iterations:3} | States: {states:3} | LLM: {llm_decisions:3} | Algo: {algo_decisions:3}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

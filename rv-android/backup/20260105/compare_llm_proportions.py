"""
Compare LLM vs Algorithm Proportions in Multimode.

Tests different LLM probabilities to find optimal balance between:
- State discovery (LLM strength)
- Execution speed (algorithm strength)

LLM is always the star (>50% probability).
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, List
import sys

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_test(
    llm_probability: float,
    timeout: int = 180,
    package_name: str = "br.unb.cic.cryptoapp"
) -> Dict[str, Any]:
    """
    Run single test with specific LLM probability.

    Args:
        llm_probability: Probability of using LLM (0.0 to 1.0)
        timeout: Test timeout in seconds
        package_name: Target app package

    Returns:
        Test results dictionary
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing LLM probability: {llm_probability:.0%}")
    logger.info(f"{'='*80}")

    # Create configuration
    config = RVAgentConfig(
        package_name=package_name,
        device_id="emulator-5554",
        agent_mode="multimode",
        llm_probability=llm_probability,
        llm_model="qwen3-vl-4b-8k",  # 8k context to avoid truncation
        strategy="dfs",
        timeout=timeout,
        max_iterations=200,
        screenshot_dir="/tmp/rvagent_screenshots",
        screenshot_rotation_limit=50,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248)
    )

    try:
        # Create agent
        logger.info("Creating agent...")
        agent = AgentFactory.create_agent(
            config=config,
            static_data=None,
            device=None
        )

        # Run exploration
        logger.info("Starting exploration...")
        start_time = time.time()
        results = agent.run()
        elapsed_time = time.time() - start_time

        # Extract metrics
        iterations = results.get('iterations', 0)
        states = results.get('unique_states', 0)
        transitions = results.get('transitions', 0)
        llm_decisions = results.get('llm_decisions', 0)
        algorithm_decisions = results.get('algorithm_decisions', 0)
        llm_time = results.get('llm_time_ms', 0)

        # Calculate derived metrics
        total_decisions = llm_decisions + algorithm_decisions
        actual_llm_ratio = llm_decisions / total_decisions if total_decisions > 0 else 0
        states_per_second = states / elapsed_time if elapsed_time > 0 else 0
        iterations_per_second = iterations / elapsed_time if elapsed_time > 0 else 0
        avg_llm_time = llm_time / llm_decisions if llm_decisions > 0 else 0

        result = {
            "llm_probability": llm_probability,
            "iterations": iterations,
            "states": states,
            "transitions": transitions,
            "llm_decisions": llm_decisions,
            "algorithm_decisions": algorithm_decisions,
            "total_decisions": total_decisions,
            "actual_llm_ratio": actual_llm_ratio,
            "execution_time": elapsed_time,
            "llm_time_total_ms": llm_time,
            "avg_llm_time_ms": avg_llm_time,
            "states_per_second": states_per_second,
            "iterations_per_second": iterations_per_second,
            "efficiency_score": states / elapsed_time if elapsed_time > 0 else 0,
            "status": "success"
        }

        logger.info(f"✅ Test completed successfully")
        logger.info(f"   States: {states}, Time: {elapsed_time:.1f}s")
        logger.info(f"   LLM decisions: {llm_decisions}/{total_decisions} ({actual_llm_ratio:.1%})")
        logger.info(f"   Efficiency: {states_per_second:.2f} states/sec")

        return result

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return {
            "llm_probability": llm_probability,
            "status": "failed",
            "error": str(e)
        }


def compare_proportions(
    probabilities: List[float],
    timeout: int = 180,
    output_dir: str = "./comparison_results"
) -> Dict[str, Any]:
    """
    Compare different LLM probabilities.

    Args:
        probabilities: List of LLM probabilities to test
        timeout: Timeout per test in seconds (default: 180s = 3 minutes for significance)
        output_dir: Output directory for results

    Returns:
        Comparison results
    """
    logger.info("="*80)
    logger.info("LLM PROPORTION COMPARISON")
    logger.info("="*80)
    logger.info(f"Testing probabilities: {[f'{p:.0%}' for p in probabilities]}")
    logger.info(f"Timeout per test: {timeout}s ({timeout/60:.1f} minutes)")
    logger.info(f"Estimated total time: {timeout*len(probabilities)/60:.1f} minutes")
    logger.info("="*80)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Run tests
    results = []
    for prob in probabilities:
        result = run_test(
            llm_probability=prob,
            timeout=timeout
        )
        results.append(result)

        # Small delay between tests
        time.sleep(2)

    # Analyze results
    successful_results = [r for r in results if r.get("status") == "success"]

    if not successful_results:
        logger.error("❌ No successful tests!")
        return {"status": "failed", "results": results}

    # Find best configurations
    best_states = max(successful_results, key=lambda x: x.get("states", 0))
    best_efficiency = max(successful_results, key=lambda x: x.get("efficiency_score", 0))
    best_speed = max(successful_results, key=lambda x: x.get("iterations_per_second", 0))

    # Generate summary
    summary = {
        "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "timeout_per_test": timeout,
        "probabilities_tested": probabilities,
        "total_tests": len(results),
        "successful_tests": len(successful_results),
        "failed_tests": len(results) - len(successful_results),

        "best_for_states": {
            "llm_probability": best_states["llm_probability"],
            "states": best_states["states"],
            "time": best_states["execution_time"],
            "efficiency": best_states["efficiency_score"]
        },

        "best_for_efficiency": {
            "llm_probability": best_efficiency["llm_probability"],
            "states": best_efficiency["states"],
            "time": best_efficiency["execution_time"],
            "efficiency": best_efficiency["efficiency_score"]
        },

        "best_for_speed": {
            "llm_probability": best_speed["llm_probability"],
            "iterations_per_second": best_speed["iterations_per_second"],
            "states": best_speed["states"]
        },

        "all_results": results
    }

    # Save detailed results
    results_file = output_path / "proportion_comparison.json"
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info("\n" + "="*80)
    logger.info("COMPARISON SUMMARY")
    logger.info("="*80)

    logger.info("\n📊 BEST CONFIGURATION FOR STATE DISCOVERY:")
    logger.info(f"   LLM Probability: {best_states['llm_probability']:.0%}")
    logger.info(f"   States: {best_states['states']}")
    logger.info(f"   Time: {best_states['execution_time']:.1f}s")
    logger.info(f"   Efficiency: {best_states['efficiency_score']:.2f} states/sec")

    logger.info("\n⚡ BEST CONFIGURATION FOR EFFICIENCY:")
    logger.info(f"   LLM Probability: {best_efficiency['llm_probability']:.0%}")
    logger.info(f"   States: {best_efficiency['states']}")
    logger.info(f"   Efficiency: {best_efficiency['efficiency_score']:.2f} states/sec")

    logger.info("\n🚀 BEST CONFIGURATION FOR SPEED:")
    logger.info(f"   LLM Probability: {best_speed['llm_probability']:.0%}")
    logger.info(f"   Speed: {best_speed['iterations_per_second']:.2f} iter/sec")
    logger.info(f"   States: {best_speed['states']}")

    logger.info("\n📈 ALL RESULTS:")
    logger.info(f"{'LLM%':>6} | {'States':>6} | {'Time':>7} | {'LLM Dec':>8} | {'Alg Dec':>8} | {'Efficiency':>10}")
    logger.info("-" * 80)
    for r in successful_results:
        logger.info(
            f"{r['llm_probability']*100:>5.0f}% | "
            f"{r['states']:>6} | "
            f"{r['execution_time']:>6.1f}s | "
            f"{r['llm_decisions']:>8} | "
            f"{r['algorithm_decisions']:>8} | "
            f"{r['efficiency_score']:>9.2f}"
        )

    logger.info("\n" + "="*80)
    logger.info(f"Results saved to: {results_file}")
    logger.info("="*80)

    return summary


def main():
    """Main execution."""

    # Test probabilities (LLM is always the star > 50%)
    probabilities = [
        0.55,  # 55% LLM, 45% algorithm (close to balanced)
        0.60,  # 60% LLM, 40% algorithm (balanced)
        0.65,  # 65% LLM, 35% algorithm
        0.70,  # 70% LLM, 30% algorithm (current default)
        0.75,  # 75% LLM, 25% algorithm
        0.80,  # 80% LLM, 20% algorithm (LLM dominant)
    ]

    # Run comparison
    results = compare_proportions(
        probabilities=probabilities,
        timeout=60,
        output_dir="./proportion_comparison_results"
    )

    if results.get("status") != "failed":
        logger.info("\n✅ Comparison completed successfully!")

        # Recommendation
        best = results["best_for_efficiency"]
        logger.info("\n💡 RECOMMENDATION:")
        logger.info(f"   Use LLM probability: {best['llm_probability']:.0%}")
        logger.info(f"   Expected: {best['states']} states in {best['time']:.1f}s")
        logger.info(f"   Efficiency: {best['efficiency']:.2f} states/sec")
    else:
        logger.error("\n❌ Comparison failed!")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
vLLM Real Execution Test - CryptoApp (180s)

Validates vLLM integration with real emulator execution:
- Zero loop rate (vs 50% with Ollama)
- LLM decision quality
- Complete metrics collection
- Comparison with Ollama baseline
"""

import sys
import os
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def prepare_device():
    """Prepare Android device for testing."""
    logger.info("Preparing device...")

    # Check device
    result = subprocess.run(
        ["adb", "devices"],
        capture_output=True,
        text=True,
        timeout=10
    )

    if "emulator-5554" not in result.stdout:
        logger.error("❌ Emulator not found")
        return False

    # Uninstall previous version
    logger.info("Uninstalling previous CryptoApp...")
    subprocess.run(
        ["adb", "uninstall", "br.unb.cic.cryptoapp"],
        capture_output=True,
        timeout=30
    )

    # Install APK
    apk_path = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk"

    logger.info(f"Installing {apk_path}...")
    result = subprocess.run(
        ["adb", "install", "-r", "-g", apk_path],
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode != 0:
        logger.error(f"❌ Failed to install: {result.stderr}")
        return False

    logger.info("✅ CryptoApp installed successfully")
    return True


def run_vllm_test(timeout: int = 180) -> dict:
    """Run RVAgent test with vLLM backend."""

    logger.info("="*80)
    logger.info("vLLM REAL EXECUTION TEST - CRYPTOAPP")
    logger.info("="*80)

    # Configuration with vLLM
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        device_id="emulator-5554",
        timeout=timeout,
        agent_mode="llm_only",  # Use only LLM to test vLLM thoroughly
        strategy="greedy",
        llm_model="./models/qwen3-vl-4b-fp8",  # vLLM model
        max_iterations=200,
        screenshot_dir="/tmp/vllm_real_test_cryptoapp",
        screenshot_rotation_limit=50,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248),
        prompt_version="v13"
    )

    logger.info(f"\n📱 App: {config.package_name}")
    logger.info(f"⏱️  Timeout: {config.timeout}s")
    logger.info(f"🎯 Mode: {config.agent_mode}")
    logger.info(f"📊 Strategy: {config.strategy}")
    logger.info(f"🤖 Model: {config.llm_model}")
    logger.info(f"🌐 Backend: vLLM (http://localhost:8000/v1)")
    logger.info(f"📝 Prompt: {config.prompt_version}")

    # Create agent
    logger.info("\nCreating agent with vLLM backend...")
    try:
        agent = AgentFactory.create_agent(config=config)
        logger.info("✅ Agent created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create agent: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Run test
    logger.info("\n🚀 Starting exploration...")
    logger.info("="*80)

    start_time = time.time()

    try:
        results = agent.run()
        elapsed = time.time() - start_time

        logger.info("="*80)
        logger.info("✅ TEST COMPLETED SUCCESSFULLY")
        logger.info("="*80)

        # Add elapsed time to results
        results["elapsed_time"] = elapsed

        return results

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"\n❌ Test failed after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_results(results: dict):
    """Analyze and print detailed results."""

    if not results:
        logger.error("No results to analyze")
        return

    logger.info("\n" + "="*80)
    logger.info("DETAILED RESULTS ANALYSIS")
    logger.info("="*80)

    # Basic metrics
    elapsed = results.get("elapsed_time", 0)
    total_actions = results.get("total_actions", 0)
    states_explored = results.get("states_explored", 0)
    ui_elements = results.get("ui_elements_discovered", 0)

    logger.info(f"\n⏱️  Duration: {elapsed:.1f}s / 180s")
    logger.info(f"📊 Total actions: {total_actions}")
    logger.info(f"🗺️  States explored: {states_explored}")
    logger.info(f"🎨 UI elements discovered: {ui_elements}")

    # LLM metrics (CRITICAL for loop detection)
    llm_stats = results.get("llm_stats", {})
    if llm_stats:
        total_calls = llm_stats.get("total_calls", 0)
        successful_calls = llm_stats.get("successful_calls", 0)
        failed_calls = llm_stats.get("failed_calls", 0)
        timeout_calls = llm_stats.get("timeout_calls", 0)
        loop_calls = llm_stats.get("loop_calls", 0)  # finish_reason='length'

        logger.info(f"\n🧠 LLM Statistics:")
        logger.info(f"  Total calls: {total_calls}")
        logger.info(f"  Successful: {successful_calls}")
        logger.info(f"  Failed: {failed_calls}")
        logger.info(f"  Timeouts: {timeout_calls}")
        logger.info(f"  Loops (finish='length'): {loop_calls}")

        if total_calls > 0:
            success_rate = (successful_calls / total_calls) * 100
            loop_rate = (loop_calls / total_calls) * 100

            logger.info(f"\n📈 LLM Performance:")
            logger.info(f"  Success rate: {success_rate:.1f}%")
            logger.info(f"  Loop rate: {loop_rate:.1f}%")

            # Average response times
            avg_response_time = llm_stats.get("avg_response_time", 0)
            if avg_response_time > 0:
                logger.info(f"  Avg response time: {avg_response_time:.2f}s")

    # Action distribution
    action_dist = results.get("action_type_distribution", {})
    if action_dist:
        logger.info(f"\n🎯 Action Distribution:")
        for action_type, count in sorted(action_dist.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_actions * 100) if total_actions > 0 else 0
            logger.info(f"  {action_type}: {count} ({percentage:.1f}%)")

    # Coverage metrics
    ui_coverage = results.get("ui_coverage", 0)
    if ui_coverage > 0:
        logger.info(f"\n📊 Coverage:")
        logger.info(f"  UI coverage: {ui_coverage:.1f}%")

    # VALIDATION
    logger.info("\n" + "="*80)
    logger.info("VALIDATION - vLLM vs Ollama Baseline")
    logger.info("="*80)

    validation_passed = True

    if llm_stats:
        loop_rate = (llm_stats.get("loop_calls", 0) / llm_stats.get("total_calls", 1)) * 100
        success_rate = (llm_stats.get("successful_calls", 0) / llm_stats.get("total_calls", 1)) * 100

        # Loop rate check (CRITICAL)
        logger.info(f"\n🔄 Loop Rate Check:")
        logger.info(f"  vLLM (current): {loop_rate:.1f}%")
        logger.info(f"  Ollama (baseline): 50.0%")

        if loop_rate == 0.0:
            logger.info(f"  ✅ PASS: Zero loop rate achieved!")
        elif loop_rate < 10.0:
            logger.info(f"  ⚠️  WARNING: Loop rate {loop_rate:.1f}% < 10% (acceptable)")
        else:
            logger.info(f"  ❌ FAIL: Loop rate {loop_rate:.1f}% >= 10%")
            validation_passed = False

        # Success rate check
        logger.info(f"\n✨ Success Rate Check:")
        logger.info(f"  Current: {success_rate:.1f}%")
        logger.info(f"  Expected: >= 85%")

        if success_rate >= 85.0:
            logger.info(f"  ✅ PASS: Success rate meets threshold")
        else:
            logger.info(f"  ⚠️  WARNING: Success rate below 85%")

    # Actions check
    logger.info(f"\n🎯 Exploration Check:")
    logger.info(f"  Total actions: {total_actions}")
    logger.info(f"  States explored: {states_explored}")

    if total_actions >= 10:
        logger.info(f"  ✅ PASS: Sufficient exploration")
    else:
        logger.info(f"  ⚠️  WARNING: Limited exploration (< 10 actions)")

    # Overall result
    logger.info("\n" + "="*80)
    if validation_passed and total_actions >= 10:
        logger.info("🎉 OVERALL: TEST PASSED")
    else:
        logger.info("⚠️  OVERALL: TEST COMPLETED WITH WARNINGS")
    logger.info("="*80)

    return validation_passed


def main():
    """Main test execution."""

    print("\n" + "="*80)
    print("vLLM REAL EXECUTION VALIDATION TEST")
    print("="*80)
    print("\nObjective: Validate vLLM eliminates token repetition loops")
    print("Expected: 0% loop rate (vs 50% Ollama baseline)")
    print("Duration: 180 seconds")
    print()

    # Prepare device
    if not prepare_device():
        logger.error("Failed to prepare device")
        return 1

    # Run test
    results = run_vllm_test(timeout=180)

    if not results:
        logger.error("Test execution failed")
        return 1

    # Analyze results
    validation_passed = analyze_results(results)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path(__file__).parent / f"vllm_real_cryptoapp_results_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\n💾 Results saved to: {output_file}")

    return 0 if validation_passed else 1


if __name__ == "__main__":
    sys.exit(main())

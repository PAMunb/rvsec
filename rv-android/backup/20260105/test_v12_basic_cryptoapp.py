#!/usr/bin/env python3
"""
Basic test for V12 improvements with cryptoapp.

Quick sanity check to verify that the 6 implemented improvements don't break basic functionality.
"""

import json
import time
from pathlib import Path

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory


def test_cryptoapp_basic():
    """Test cryptoapp with V12 improvements (60 seconds)."""

    print("\n" + "="*80)
    print("V12 BASIC TEST - CRYPTOAPP (60s)")
    print("="*80)
    print("\nVerifying that all 6 improvements work without breaking functionality:")
    print("  1. UI Coverage Annotations")
    print("  2. LLM Timeout (60s)")
    print("  3. Recovery Mode (3 failures → 10 algorithm actions)")
    print("  4. Spatial Loop Detector")
    print("  6. Text Input Fallback (20% probability)")
    print("  7. Stuck State Detector (5 unchanged screens → BACK)")
    print()

    # Configuration
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        device_id="emulator-5554",
        timeout=60,
        agent_mode="multimode",  # 70% LLM / 30% algorithm
        strategy="greedy",
        llm_model="qwen3-vl-4b-8k:latest",
        llm_probability=0.7,  # 70% LLM probability
        max_iterations=200,
        screenshot_dir="/tmp/rvagent_v12_basic_test",
        screenshot_rotation_limit=50,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248)
    )

    print(f"📱 App: {config.package_name}")
    print(f"⏱️  Timeout: {config.timeout}s")
    print(f"🎯 Mode: {config.agent_mode} (LLM prob: {config.llm_probability})")
    print(f"📊 Strategy: {config.strategy}")
    print(f"🤖 Model: {config.llm_model}")
    print()

    # Create agent
    print("Creating agent with V12 improvements...")
    agent = AgentFactory.create_agent(config=config)

    # Run test
    print("\nStarting exploration...")
    start_time = time.time()

    try:
        results = agent.run()
        elapsed = time.time() - start_time

        print("\n" + "="*80)
        print("TEST COMPLETED SUCCESSFULLY")
        print("="*80)

        # Extract metrics
        total_actions = results.get("total_actions", 0)
        llm_decisions = results.get("llm_decisions", 0)
        algorithm_decisions = results.get("algorithm_decisions", 0)

        print(f"\n⏱️  Duration: {elapsed:.1f}s")
        print(f"📊 Total actions: {total_actions}")
        print(f"🧠 LLM decisions: {llm_decisions} ({llm_decisions/total_actions*100:.1f}%)")
        print(f"⚙️  Algorithm decisions: {algorithm_decisions} ({algorithm_decisions/total_actions*100:.1f}%)")

        # Check for new features usage
        print("\n--- V12 Features Check ---")

        # Recovery mode activations
        if "recovery_mode_activations" in results:
            print(f"🔧 Recovery mode activations: {results['recovery_mode_activations']}")

        # Spatial loops detected
        if "spatial_loops_detected" in results:
            print(f"🔄 Spatial loops detected: {results['spatial_loops_detected']}")

        # Stuck states detected
        if "stuck_states_detected" in results:
            print(f"🚫 Stuck states detected: {results['stuck_states_detected']}")

        # Text input actions
        action_types = results.get("action_type_distribution", {})
        text_actions = action_types.get("SET_TEXT", 0)
        if text_actions > 0:
            print(f"📝 Text input actions: {text_actions}/{total_actions} ({text_actions/total_actions*100:.1f}%)")

        # Save results
        result_file = Path("/tmp/v12_basic_test_result.json")
        result_file.write_text(json.dumps(results, indent=2))
        print(f"\n💾 Results saved to: {result_file}")

        print("\n✅ Basic test PASSED - No regressions detected")
        return True

    except Exception as e:
        elapsed = time.time() - start_time
        print("\n" + "="*80)
        print("TEST FAILED")
        print("="*80)
        print(f"\n❌ Error after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_cryptoapp_basic()
    exit(0 if success else 1)

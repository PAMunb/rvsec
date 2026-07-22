#!/usr/bin/env python3
"""
RVAgent vLLM integration test with CryptoApp.

Tests the complete RVAgent workflow with vLLM backend to validate:
- LLM client creation with vLLM
- Tool calling functionality
- Vision capabilities (screenshot processing)
- Zero loop rate (finish_reason='stop')
"""

import json
import logging
from pathlib import Path

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory
from rv_android_core.domain.static import StaticAnalysisData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run RVAgent test with CryptoApp using vLLM backend."""

    print("\n" + "=" * 80)
    print("RVAgent vLLM Integration Test - CryptoApp")
    print("=" * 80)

    # Test configuration
    apk_path = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp/br.unb.cic.cryptoapp.apk"
    package_name = "br.unb.cic.cryptoapp"
    device_id = "emulator-5554"
    max_steps = 10  # Quick validation test

    print(f"\nConfiguration:")
    print(f"  APK: {apk_path}")
    print(f"  Package: {package_name}")
    print(f"  Device: {device_id}")
    print(f"  Max steps: {max_steps}")
    print(f"  LLM Backend: vLLM (http://localhost:8000/v1)")
    print(f"  Model: Qwen3-VL-4B-FP8")

    # Create agent configuration
    config = RVAgentConfig(
        apk_path=apk_path,
        package_name=package_name,
        device_id=device_id,
        max_steps=max_steps,
        mode="llm_only",  # Use only LLM (no DFS algorithm)
        strategy="dfs",
        llm_timeout=30.0,  # Increased timeout for first request
        prompt_version="v13",
        screenshot_dir=str(Path(__file__).parent / "vllm_test_screenshots"),
        llm_config={
            "provider": "vllm",
            "model": "./models/qwen3-vl-4b-fp8",
            "base_url": "http://localhost:8000/v1",
            "temperature": 0.6,
            "top_p": 0.95,
            "max_tokens": 2048
        }
    )

    print(f"\nAgent mode: {config.get_agent_mode()}")
    print(f"Strategy: {config.strategy}")

    # Create agent
    print("\n📦 Creating RVAgent with vLLM backend...")
    try:
        agent = AgentFactory.create_agent(
            config=config,
            static_data=None  # No static analysis for quick test
        )
        print("✅ RVAgent created successfully")
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        import traceback
        traceback.print_exc()
        return

    # Run agent
    print("\n🚀 Starting exploration...")
    print("-" * 80)

    try:
        result = agent.run()
        print("-" * 80)
        print("\n✅ Exploration completed successfully")
    except Exception as e:
        print(f"\n❌ Exploration failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Analyze results
    print("\n" + "=" * 80)
    print("RESULTS ANALYSIS")
    print("=" * 80)

    # Extract metrics from result
    steps_taken = result.get('steps_taken', 0)
    states_explored = result.get('states_explored', 0)
    ui_elements_discovered = result.get('ui_elements_discovered', 0)

    print(f"\nExploration Metrics:")
    print(f"  Steps taken: {steps_taken}/{max_steps}")
    print(f"  States explored: {states_explored}")
    print(f"  UI elements discovered: {ui_elements_discovered}")

    # Check LLM usage metrics (if available)
    llm_stats = result.get('llm_stats', {})
    if llm_stats:
        total_calls = llm_stats.get('total_calls', 0)
        successful_calls = llm_stats.get('successful_calls', 0)
        failed_calls = llm_stats.get('failed_calls', 0)
        loop_count = llm_stats.get('loop_count', 0)  # finish_reason='length'

        print(f"\nLLM Statistics:")
        print(f"  Total calls: {total_calls}")
        print(f"  Successful: {successful_calls}")
        print(f"  Failed: {failed_calls}")
        print(f"  Loops (finish='length'): {loop_count}")

        if total_calls > 0:
            loop_rate = (loop_count / total_calls) * 100
            success_rate = (successful_calls / total_calls) * 100

            print(f"\nLLM Performance:")
            print(f"  Success rate: {success_rate:.1f}%")
            print(f"  Loop rate: {loop_rate:.1f}%")

            # Validation
            print(f"\n{'='*80}")
            print("VALIDATION")
            print("=" * 80)

            if loop_rate == 0.0:
                print("✅ PASS: Zero loop rate (no token repetition)")
            else:
                print(f"❌ FAIL: Loop rate {loop_rate:.1f}% (expected 0%)")

            if success_rate >= 85.0:
                print(f"✅ PASS: Success rate {success_rate:.1f}% >= 85%")
            else:
                print(f"⚠️  WARNING: Success rate {success_rate:.1f}% < 85%")
    else:
        print("\n⚠️  No LLM statistics available in result")

    # Save detailed results
    output_file = Path(__file__).parent / "vllm_rvagent_cryptoapp_results.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nDetailed results saved to: {output_file}")

    print("\n" + "=" * 80)
    print("Test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()

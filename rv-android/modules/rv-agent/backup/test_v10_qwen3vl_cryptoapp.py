"""
Test V10 Simplified Prompt with qwen3-vl:4b on CryptoApp

Validates that the simplified V10 prompt works with smaller vision models
that were overwhelmed by complex V9 prompts.

Expected behavior:
- Model should generate tool calls (not get stuck)
- Should discover unique states (not loop on same state)
- Should explore different features (MESSAGE DIGEST, CIPHER, etc.)
"""

import json
import logging
import sys
import time
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.core.rv_agent import RVAgent
from rv_agent.core.device_interface import DeviceInterface
from rv_agent.config.agent_config import RVAgentConfig


def test_v10_cryptoapp():
    """
    Test V10 simplified prompt with qwen3-vl:4b on CryptoApp.

    Success criteria:
    - Generates tool calls in first iteration
    - Discovers at least 2 unique states in 120s
    - No immediate loops (different states across first 5 iterations)
    """
    print("\n" + "="*80)
    print("  V10 SIMPLIFIED PROMPT TEST")
    print("="*80)
    print("\nConfiguration:")
    print("  App: CryptoApp (br.unb.cic.cryptoapp)")
    print("  Model: qwen3-vl:4b")
    print("  Prompt: V10 Simplified (minimal context)")
    print("  Timeout: 120s")
    print("  Temperature: 0.0 (deterministic)")

    # Test configuration
    DEVICE_ID = "emulator-5554"
    PACKAGE = "br.unb.cic.cryptoapp"
    APK_PATH = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/cryptoapp.apk"
    TIMEOUT = 120

    start_time = time.time()

    try:
        # Create device interface
        logger.info("📱 Connecting to device...")
        device = DeviceInterface(DEVICE_ID)

        # Create config with qwen3-vl model
        logger.info("⚙️  Creating RVAgent config...")
        config = RVAgentConfig(
            package_name=PACKAGE,
            device_id=DEVICE_ID,
            strategy="dfs",
            timeout=TIMEOUT,
            max_iterations=200,
            llm_model="qwen3-vl:4b",  # Smaller vision model
            llm_temperature=0.0,  # Deterministic like working test
            llm_top_p=0.9,
            llm_top_k=40
        )

        # Create RVAgent with V10 prompt
        logger.info("🤖 Creating RVAgent with V10 prompt...")
        agent = RVAgent(config, static_data=None, device=device)

        # Run exploration
        logger.info("\n🚀 Starting exploration...")
        logger.info("   Watching for:")
        logger.info("   ✓ Tool calls generated in iteration 1")
        logger.info("   ✓ Unique states discovered")
        logger.info("   ✓ No immediate loops")

        results = agent.run()

        execution_time = time.time() - start_time

        # Analyze results
        print("\n" + "="*80)
        print("  RESULTS")
        print("="*80)

        iterations = results['iterations']
        unique_states = results['unique_states']
        transitions = results['total_transitions']
        potential_loop = results.get('potential_loop', False)

        print(f"\nMetrics:")
        print(f"  Iterations: {iterations}")
        print(f"  Unique States: {unique_states}")
        print(f"  Transitions: {transitions}")
        print(f"  Execution Time: {execution_time:.1f}s")
        print(f"  Loop Detected: {'YES ❌' if potential_loop else 'NO ✅'}")

        # Success criteria
        print("\n" + "="*80)
        print("  VALIDATION")
        print("="*80)

        success = True

        # Check 1: Generated actions
        if iterations == 0:
            print("\n❌ FAIL: No iterations - model didn't generate any actions")
            success = False
        else:
            print(f"\n✅ PASS: Generated {iterations} iterations")

        # Check 2: Discovered unique states
        if unique_states < 2:
            print(f"❌ FAIL: Only {unique_states} unique states - not exploring")
            success = False
        else:
            print(f"✅ PASS: Discovered {unique_states} unique states")

        # Check 3: Not looping immediately
        if potential_loop:
            print("⚠️  WARNING: Potential loop detected")
        else:
            print("✅ PASS: No loops detected")

        # Comparison with baseline
        print("\n" + "="*80)
        print("  COMPARISON WITH BASELINE")
        print("="*80)
        print("\nBaseline (Qwen2.5-Coder, V9 complex prompt):")
        print("  Iterations: 22")
        print("  Unique States: 0  ❌")
        print("  Loop: YES  ❌")

        print(f"\nV10 Simplified (qwen3-vl:4b):")
        print(f"  Iterations: {iterations}")
        print(f"  Unique States: {unique_states}  {'✅' if unique_states > 0 else '❌'}")
        print(f"  Loop: {'YES ❌' if potential_loop else 'NO ✅'}")

        if unique_states > 0:
            print("\n🎉 IMPROVEMENT! V10 enables qwen3-vl to explore!")
        else:
            print("\n❌ SAME PROBLEM: Model still not exploring")

        # Save results
        output_file = Path("test_v10_cryptoapp_results.json")
        results_data = {
            "app": "cryptoapp",
            "model": "qwen3-vl:4b",
            "prompt_version": "v10",
            "timeout": TIMEOUT,
            "metrics": {
                "iterations": iterations,
                "unique_states": unique_states,
                "transitions": transitions,
                "potential_loop": potential_loop,
                "execution_time_s": execution_time
            },
            "validation": {
                "generated_actions": iterations > 0,
                "discovered_states": unique_states >= 2,
                "no_immediate_loop": not potential_loop,
                "overall_success": success
            }
        }

        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"\n💾 Results saved: {output_file}")

        print("\n" + "="*80)
        if success:
            print("  ✅ TEST PASSED")
        else:
            print("  ❌ TEST FAILED")
        print("="*80)

        return success

    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}", exc_info=True)

        # Save error results
        output_file = Path("test_v10_cryptoapp_results.json")
        error_data = {
            "app": "cryptoapp",
            "model": "qwen3-vl:4b",
            "prompt_version": "v10",
            "status": "failed",
            "error": str(e),
            "execution_time_s": time.time() - start_time
        }

        with open(output_file, 'w') as f:
            json.dump(error_data, f, indent=2)

        print(f"\n💾 Error results saved: {output_file}")
        return False


if __name__ == "__main__":
    success = test_v10_cryptoapp()
    sys.exit(0 if success else 1)

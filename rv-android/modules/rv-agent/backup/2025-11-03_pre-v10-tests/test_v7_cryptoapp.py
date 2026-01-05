"""
Test V7 Retry Logic with cryptoapp.apk

Goal: Validate that retry mechanism with progressive sampling reduces UNKNOWN rate.

Expected Behavior:
- When LLM doesn't generate tool calls (UNKNOWN), retry with increased creativity
- Progressive sampling: temp 0.1 → 0.5 → 0.9
- Max 2 retries before fallback to BACK action
- Log retry attempts and sampling parameters

Success Criteria:
- Fewer UNKNOWN actions compared to V5 (46.4% UNKNOWN)
- Evidence of retry mechanism in logs
- Sampling parameters increase across retries
"""

import json
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.validation.validation_runner import ValidationRunner


def test_v7_cryptoapp():
    """Test V7 retry logic with cryptoapp.apk"""

    print("=" * 80)
    print("V7 RETRY LOGIC TEST - cryptoapp.apk")
    print("=" * 80)

    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    output_dir = Path("v7_cryptoapp_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Single app test
    apps_to_test = ["cryptoapp.apk"]

    logger.info(f"\n📱 Testing V7 with {apps_to_test[0]}")
    logger.info(f"   Dataset: {dataset_dir}")
    logger.info(f"   Prompt: V5 (with V7 retry logic)")
    logger.info(f"   Max retries: 2")
    logger.info(f"   Sampling progression: 0.1 → 0.5 → 0.9 (temp)\n")

    # Create validation runner
    runner = ValidationRunner(
        dataset_dir=dataset_dir,
        max_iterations=10,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(728, 1288)
    )

    # Run validation for single app
    app_name = apps_to_test[0]
    output_file = output_dir / f"{app_name}.json"

    try:
        metrics = runner.validate_app(
            app_name=app_name,
            strategy="dfs",
            output_path=output_file
        )
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return None

    # Analyze results (using correct V5 metrics structure)
    print("\n" + "=" * 80)
    print("V7 TEST RESULTS")
    print("=" * 80)

    if not metrics:
        print("❌ No metrics generated")
        return None

    # Access metrics using V5 structure
    total_iterations = metrics.get('total_iterations', 0)
    total_device_actions = metrics['device_actions']['total_actions']
    action_types = metrics['device_actions']['action_types']

    print(f"\n📊 Action Statistics:")
    print(f"   Total iterations: {total_iterations}")
    print(f"   Total device actions: {total_device_actions}")

    print(f"\n   Action Type Distribution:")
    for action_type, count in sorted(action_types.items()):
        percentage = (count / total_device_actions * 100) if total_device_actions > 0 else 0
        print(f"      {action_type}: {count} ({percentage:.1f}%)")

    # Calculate UNKNOWN rate (from actions.by_type)
    unknown_count = metrics['actions']['by_type'].get('UNKNOWN', 0)
    unknown_rate = (unknown_count / total_iterations * 100) if total_iterations > 0 else 0

    print(f"\n   ⚠️  UNKNOWN Rate: {unknown_rate:.1f}% ({unknown_count}/{total_iterations} iterations)")
    print(f"   🎯 Target: < 46.4% (V5 baseline)")

    # Exploration metrics
    print(f"\n🗺️  Exploration Metrics:")
    print(f"   Unique screens: {metrics.get('unique_screens', 0)}")
    print(f"   Activities: {metrics.get('unique_activities', 0)}")

    # Save consolidated result
    output = {
        "app": "cryptoapp.apk",
        "version": "v7",
        "prompt": "v5",
        "total_iterations": total_iterations,
        "device_actions": {
            "total_actions": total_device_actions,
            "action_types": action_types
        },
        "actions": {
            "by_type": metrics['actions']['by_type']
        },
        "unknown_rate": unknown_rate,
        "unique_screens": metrics.get("unique_screens", 0),
        "unique_activities": metrics.get("unique_activities", 0),
        "has_static_analysis": metrics.get("has_static_analysis", False)
    }

    output_file = output_dir / "cryptoapp_test.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")

    # Success evaluation
    print("\n" + "=" * 80)
    if unknown_rate < 46.4:
        print("✅ SUCCESS: V7 UNKNOWN rate is LOWER than V5 baseline!")
        print(f"   V5: 46.4% → V7: {unknown_rate:.1f}% (improvement: {46.4 - unknown_rate:.1f}%)")
    else:
        print("⚠️  PARTIAL: V7 UNKNOWN rate still needs improvement")
        print(f"   V5: 46.4% → V7: {unknown_rate:.1f}% (change: {unknown_rate - 46.4:+.1f}%)")
    print("=" * 80)

    return output


if __name__ == "__main__":
    result = test_v7_cryptoapp()

    if result:
        # Exit code based on success
        unknown_rate = result["unknown_rate"]
        sys.exit(0 if unknown_rate < 46.4 else 1)
    else:
        sys.exit(1)

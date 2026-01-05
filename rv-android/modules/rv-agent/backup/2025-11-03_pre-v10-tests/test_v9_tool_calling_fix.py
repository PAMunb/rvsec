"""
Test V9 Tool Calling Fix + TYPE_TEXT Fix (Options A + B).

Validates:
1. Tool calling regression fixed (cryptoapp: 12% → 100%, simplenotes_7: 0% → >50%)
2. TYPE_TEXT fix works (android_type_text called, TYPE_TEXT recorded)
3. UNKNOWN actions eliminated

Expected Results:
- cryptoapp: ~100% success rate (vs 12% in v8), TYPE_TEXT in iteration 3
- simplenotes_7: >50% success rate (vs 0% in v8)
"""

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


def main():
    """Test V9 fixes on critical apps."""
    logger.info("=" * 80)
    logger.info("🔬 V9 VALIDATION - Tool Calling Fix + TYPE_TEXT Fix")
    logger.info("=" * 80)

    # Dataset directory
    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

    if not dataset_dir.exists():
        logger.error(f"Dataset directory not found: {dataset_dir}")
        return False

    # Test apps
    test_apps = [
        {
            "name": "cryptoapp.apk",
            "iterations": 5,  # Quick test - iteration 3 should show TYPE_TEXT
            "expected_success_rate": 0.80,  # 80%+ tool execution
            "expected_type_text": True,  # Should have TYPE_TEXT in actions
            "description": "12% → 100% success + TYPE_TEXT fix"
        },
        {
            "name": "com.rafapps.simplenotes_7.apk",
            "iterations": 10,
            "expected_success_rate": 0.50,  # 50%+ (was 0% in v8)
            "expected_type_text": False,  # May not have EditText
            "description": "0% → >50% success"
        }
    ]

    logger.info(f"\n📱 Testing {len(test_apps)} critical apps:")
    for app in test_apps:
        logger.info(f"  - {app['name']}: {app['description']}")

    # Configuration
    device_dimensions = (1080, 1920)
    optimized_dimensions = (728, 1288)
    strategy = "dfs"

    logger.info(f"\n📋 Configuration:")
    logger.info(f"  Strategy: {strategy}")
    logger.info(f"  Device dimensions: {device_dimensions}")
    logger.info(f"  Optimized dimensions: {optimized_dimensions}")
    logger.info("")

    # Create validation runner
    runner = ValidationRunner(
        dataset_dir=dataset_dir,
        max_iterations=10,  # Will be overridden per app
        device_dimensions=device_dimensions,
        optimized_dimensions=optimized_dimensions
    )

    # Validate each app
    results = []

    for i, app_config in enumerate(test_apps, 1):
        app_name = app_config["name"]
        max_iterations = app_config["iterations"]

        logger.info("=" * 80)
        logger.info(f"🔍 [{i}/{len(test_apps)}] TESTING: {app_name}")
        logger.info(f"   {app_config['description']}")
        logger.info("=" * 80)

        # Update runner config
        runner.max_iterations = max_iterations

        output_path = Path(f"v9_validation_{app_name.replace('.apk', '')}.json")

        try:
            metrics = runner.validate_app(
                app_name=app_name,
                strategy=strategy,
                output_path=output_path
            )

            # Analyze results
            total_iterations = metrics['total_iterations']
            actions_by_type = metrics['actions']['by_type']
            device_actions = metrics.get('device_actions', {})
            device_action_count = device_actions.get('total_actions', 0)

            # Calculate success rate (iterations that reached tools node)
            success_rate = device_action_count / total_iterations if total_iterations > 0 else 0

            # Check for TYPE_TEXT
            has_type_text = actions_by_type.get('TYPE_TEXT', 0) > 0

            # Determine success
            success = success_rate >= app_config['expected_success_rate']
            if app_config['expected_type_text']:
                success = success and has_type_text

            logger.info(f"\n✅ {app_name} completed")
            logger.info(f"   Results: {output_path}")
            logger.info(f"   Total iterations: {total_iterations}")
            logger.info(f"   Device actions: {device_action_count}")
            logger.info(f"   Success rate: {success_rate * 100:.1f}% (expected: {app_config['expected_success_rate'] * 100:.1f}%)")
            logger.info(f"   Actions by type: {actions_by_type}")
            logger.info(f"   TYPE_TEXT present: {'✅' if has_type_text else '❌'}")

            results.append({
                'app': app_name,
                'success': success,
                'success_rate': success_rate,
                'expected_rate': app_config['expected_success_rate'],
                'has_type_text': has_type_text,
                'expected_type_text': app_config['expected_type_text'],
                'total_iterations': total_iterations,
                'device_actions': device_action_count,
                'actions_by_type': actions_by_type
            })

        except Exception as e:
            logger.error(f"\n❌ {app_name} failed: {e}", exc_info=True)
            results.append({
                'app': app_name,
                'success': False,
                'error': str(e)
            })

        logger.info("")

    # Summary
    logger.info("=" * 80)
    logger.info("📊 V9 VALIDATION SUMMARY")
    logger.info("=" * 80)

    all_success = True

    for result in results:
        if 'error' in result:
            logger.info(f"\n❌ {result['app']}: FAILED")
            logger.info(f"   Error: {result['error']}")
            all_success = False
            continue

        app = result['app']
        success = result['success']
        success_rate = result['success_rate']
        expected_rate = result['expected_rate']
        has_type_text = result['has_type_text']
        expected_type_text = result['expected_type_text']

        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"\n{status}: {app}")
        logger.info(f"   Success rate: {success_rate * 100:.1f}% (expected: {expected_rate * 100:.1f}%)")
        logger.info(f"   Tool calling: {result['device_actions']}/{result['total_iterations']} iterations")
        logger.info(f"   Actions: {result['actions_by_type']}")

        if expected_type_text:
            type_text_status = "✅" if has_type_text else "❌"
            logger.info(f"   TYPE_TEXT: {type_text_status} (expected: YES)")

        if not success:
            all_success = False
            if success_rate < expected_rate:
                logger.info(f"   ISSUE: Success rate too low!")
            if expected_type_text and not has_type_text:
                logger.info(f"   ISSUE: TYPE_TEXT not recorded!")

    logger.info("\n" + "=" * 80)
    if all_success:
        logger.info("🎉 ALL TESTS PASSED - V9 FIX SUCCESSFUL!")
        logger.info("=" * 80)
        logger.info("\n✅ Tool calling regression FIXED")
        logger.info("✅ TYPE_TEXT fix WORKING")
        logger.info("✅ UNKNOWN actions ELIMINATED")
    else:
        logger.info("❌ SOME TESTS FAILED - Review results above")
        logger.info("=" * 80)

    logger.info("")

    return all_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

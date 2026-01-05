"""
Quick test to verify TYPE_TEXT fix.

Tests that android_type_text now correctly uses MockDevice.type_text()
and records TYPE_TEXT action instead of CLICK.
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
    """Test TYPE_TEXT fix on cryptoapp (first 5 iterations only)."""
    logger.info("=" * 80)
    logger.info("🔬 TYPE_TEXT FIX VERIFICATION TEST")
    logger.info("=" * 80)

    # Dataset directory
    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

    if not dataset_dir.exists():
        logger.error(f"Dataset directory not found: {dataset_dir}")
        return False

    # Test cryptoapp (only 5 iterations - iteration 3 should be TYPE_TEXT)
    app_name = "cryptoapp.apk"
    max_iterations = 5
    device_dimensions = (1080, 1920)
    optimized_dimensions = (728, 1288)
    strategy = "dfs"

    logger.info(f"\n📱 Testing: {app_name}")
    logger.info(f"   Iterations: {max_iterations} (expect TYPE_TEXT in iteration 3)")
    logger.info("")

    # Create validation runner
    runner = ValidationRunner(
        dataset_dir=dataset_dir,
        max_iterations=max_iterations,
        device_dimensions=device_dimensions,
        optimized_dimensions=optimized_dimensions
    )

    # Validate
    output_path = Path(f"test_type_text_fix_result.json")

    try:
        metrics = runner.validate_app(
            app_name=app_name,
            strategy=strategy,
            output_path=output_path
        )

        # Check results
        logger.info("\n" + "=" * 80)
        logger.info("📊 RESULTS")
        logger.info("=" * 80)

        total_iterations = metrics['total_iterations']
        actions_by_type = metrics['actions']['by_type']
        device_actions = metrics.get('device_actions', {})

        logger.info(f"\nTotal iterations: {total_iterations}")
        logger.info(f"Actions by type: {actions_by_type}")
        logger.info(f"Device actions count: {device_actions.get('total_actions', 0)}")

        # Check if TYPE_TEXT is present
        type_text_count = actions_by_type.get('TYPE_TEXT', 0)

        logger.info("\n" + "=" * 80)
        if type_text_count > 0:
            logger.info("✅ SUCCESS: TYPE_TEXT action recorded!")
            logger.info(f"   TYPE_TEXT count: {type_text_count}")
            logger.info("   Fix is working correctly!")
        else:
            logger.info("❌ FAILURE: No TYPE_TEXT actions found")
            logger.info("   Expected TYPE_TEXT in iteration 3")
            logger.info("   Fix may not be working")

        logger.info("=" * 80)

        # Show device actions details
        if device_actions.get('actions'):
            logger.info("\n📋 Device Actions Details:")
            for action in device_actions['actions']:
                logger.info(f"   Step {action['step']}: {action['action_type']} - {action.get('element', 'N/A')}")

        logger.info(f"\n📁 Full results saved to: {output_path}")

        return type_text_count > 0

    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

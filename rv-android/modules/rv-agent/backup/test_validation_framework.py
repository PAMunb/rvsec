"""
Test the offline validation framework with cryptoapp sequence.

This script tests the validation framework by running RVAgent on pre-captured
screenshots and UI dumps, validating action correctness, and collecting metrics.
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


def test_cryptoapp_validation():
    """
    Test validation framework with cryptoapp sequence.
    """
    logger.info("=" * 80)
    logger.info("Testing Offline Validation Framework")
    logger.info("=" * 80)

    # Dataset directory
    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

    if not dataset_dir.exists():
        logger.error(f"Dataset directory not found: {dataset_dir}")
        return False

    try:
        # Create validation runner
        runner = ValidationRunner(
            dataset_dir=dataset_dir,
            max_iterations=10,  # Test with 10 iterations
            device_dimensions=(1080, 1920),
            optimized_dimensions=(728, 1288)
        )

        # Run validation on cryptoapp
        output_path = Path("validation_results") / "cryptoapp_validation.json"
        metrics = runner.validate_app(
            app_name="cryptoapp.apk",
            strategy="dfs",
            output_path=output_path
        )

        logger.info("\n✅ Validation completed successfully!")
        logger.info(f"📄 Results saved to: {output_path}")

        # Print key metrics
        logger.info("\n📊 Key Metrics:")
        logger.info(f"  Total iterations: {metrics['total_iterations']}")
        logger.info(f"  Valid actions: {metrics['actions']['valid']}")
        logger.info(f"  Invalid actions: {metrics['actions']['invalid']}")
        logger.info(f"  Unique screens: {metrics['exploration']['unique_screens']}")
        logger.info(f"  Element types: {len(metrics['element_coverage']['types_seen'])}")

        return True

    except Exception as e:
        logger.error(f"❌ Validation failed: {e}", exc_info=True)
        return False


def test_sequence_loader():
    """
    Test SequenceLoader to verify dataset reading.
    """
    logger.info("\n" + "=" * 80)
    logger.info("Testing SequenceLoader")
    logger.info("=" * 80)

    from rv_agent.validation.sequence_loader import SequenceLoader

    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

    try:
        loader = SequenceLoader(dataset_dir)

        # List apps
        apps = loader.list_apps()
        logger.info(f"Found {len(apps)} apps: {apps[:5]}...")

        # Load cryptoapp sequence
        sequence = loader.load_app_sequence("cryptoapp.apk")
        logger.info(f"\nLoaded sequence: {sequence}")
        logger.info(f"  Package: {sequence.package_name}")
        logger.info(f"  Screens: {len(sequence.screens)}")
        logger.info(f"  First screen: {sequence.screens[0]}")
        logger.info(f"  Static analysis files: reach={sequence.reach_path is not None}")

        return True

    except Exception as e:
        logger.error(f"❌ SequenceLoader test failed: {e}", exc_info=True)
        return False


def test_action_validator():
    """
    Test ActionValidator with sample UI dump.
    """
    logger.info("\n" + "=" * 80)
    logger.info("Testing ActionValidator")
    logger.info("=" * 80)

    from rv_agent.validation.action_validator import ActionValidator

    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    uiautomator_path = dataset_dir / "cryptoapp.apk" / "001.uiautomator"

    try:
        validator = ActionValidator()

        # Load UI elements
        element_count = validator.load_ui_elements(uiautomator_path)
        logger.info(f"Loaded {element_count} UI elements")

        # Test click validation on "MESSAGE DIGEST" button
        # From the .state file, we know this button is at bounds [0,210][1080,336]
        # Center point: (540, 273)
        result = validator.validate_click(540, 273)
        logger.info(f"\nClick validation (540, 273): {result.valid}")
        logger.info(f"  Reason: {result.reason}")
        logger.info(f"  Element: {result.element}")

        # Test invalid click (off-screen)
        result = validator.validate_click(2000, 2000)
        logger.info(f"\nClick validation (2000, 2000): {result.valid}")
        logger.info(f"  Reason: {result.reason}")

        # Get element distribution
        distribution = validator.get_element_type_distribution()
        logger.info(f"\nElement distribution: {distribution}")

        return True

    except Exception as e:
        logger.error(f"❌ ActionValidator test failed: {e}", exc_info=True)
        return False


def test_mock_device():
    """
    Test MockDeviceInterface with sequence.
    """
    logger.info("\n" + "=" * 80)
    logger.info("Testing MockDeviceInterface")
    logger.info("=" * 80)

    from rv_agent.validation.sequence_loader import SequenceLoader
    from rv_agent.validation.mock_device import MockDeviceInterface

    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

    try:
        loader = SequenceLoader(dataset_dir)
        sequence = loader.load_app_sequence("cryptoapp.apk")

        # Create mock device
        mock_device = MockDeviceInterface(sequence)
        logger.info(f"Created mock device for: {sequence.app_name}")

        # Test getting UI state
        ui_state = mock_device.get_current_ui_state()
        logger.info(f"\nCurrent activity: {ui_state['current_activity']}")
        logger.info(f"XML length: {len(ui_state['xml'])} bytes")

        # Test screenshot
        screenshot = mock_device.get_screenshot()
        logger.info(f"Screenshot size: {len(screenshot) if screenshot else 0} bytes")

        # Test click (should advance sequence)
        logger.info(f"\nStep before click: {mock_device.get_current_step()}/{mock_device.get_sequence_length()}")
        mock_device.click(540, 273)
        logger.info(f"Step after click: {mock_device.get_current_step()}/{mock_device.get_sequence_length()}")

        # Get action summary
        summary = mock_device.get_action_summary()
        logger.info(f"\nAction summary: {summary['total_actions']} actions, {summary['valid_actions']} valid")

        return True

    except Exception as e:
        logger.error(f"❌ MockDeviceInterface test failed: {e}", exc_info=True)
        return False


def main():
    """Run all tests."""
    logger.info("🚀 Starting offline validation framework tests\n")

    tests = [
        ("SequenceLoader", test_sequence_loader),
        ("ActionValidator", test_action_validator),
        ("MockDeviceInterface", test_mock_device),
        ("Full Validation", test_cryptoapp_validation)
    ]

    results = {}
    for name, test_func in tests:
        try:
            success = test_func()
            results[name] = "✅ PASS" if success else "❌ FAIL"
        except Exception as e:
            logger.error(f"Test {name} crashed: {e}", exc_info=True)
            results[name] = "❌ CRASH"

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    for name, result in results.items():
        logger.info(f"  {result} {name}")

    all_passed = all("PASS" in r for r in results.values())
    if all_passed:
        logger.info("\n🎉 All tests passed!")
    else:
        logger.info("\n⚠️  Some tests failed")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

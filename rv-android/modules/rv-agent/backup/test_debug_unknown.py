"""
Debug test to investigate UNKNOWN actions and EditText detection.

Runs with detailed logging to capture:
- Full LLM responses
- Parsing results
- UI descriptions
- Action execution flow
"""

import json
import logging
import sys
from pathlib import Path

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.validation.validation_runner import ValidationRunner


def test_unknown_debug():
    """
    Debug test focusing on apps with high UNKNOWN rate.

    Apps to test:
    - com.hwloc.lstopo_271.apk (77.8% UNKNOWN)
    - org.pulpdust.lesserpad_42.apk (47.1% UNKNOWN)
    - cryptoapp.apk (to check EditText detection)
    """

    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    output_dir = Path("debug_unknown_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Apps with high UNKNOWN rate + cryptoapp for EditText
    test_apps = [
        "com.hwloc.lstopo_271.apk",  # 77.8% UNKNOWN
        "org.pulpdust.lesserpad_42.apk",  # 47.1% UNKNOWN
        "cryptoapp.apk",  # Check EditText detection
    ]

    logger.info("=" * 80)
    logger.info("🐛 DEBUG TEST: UNKNOWN Actions and EditText Detection")
    logger.info("=" * 80)
    logger.info(f"Apps: {test_apps}")
    logger.info(f"Output: {output_dir}")
    logger.info("")

    # Create runner
    runner = ValidationRunner(
        dataset_dir=dataset_dir,
        max_iterations=10,  # Limit to 10 for quick debugging
        device_dimensions=(1080, 1920),
        optimized_dimensions=(728, 1288)
    )

    results = {}

    for idx, app_name in enumerate(test_apps, 1):
        logger.info("\n" + "=" * 80)
        logger.info(f"📱 APP {idx}/{len(test_apps)}: {app_name}")
        logger.info("=" * 80)

        try:
            # Run validation with DEBUG logging
            metrics = runner.validate_app(
                app_name=app_name,
                strategy="dfs",
                output_path=output_dir / f"{app_name}_debug.json"
            )

            results[app_name] = metrics

            # Print summary
            logger.info("\n" + "-" * 60)
            logger.info(f"📊 SUMMARY: {app_name}")
            logger.info("-" * 60)
            logger.info(f"Total iterations: {metrics['total_iterations']}")
            logger.info(f"Actions by type: {metrics['actions']['by_type']}")
            logger.info(f"Valid actions: {metrics['actions']['valid']}")
            logger.info(f"Invalid actions: {metrics['actions']['invalid']}")
            logger.info(f"Device actions total: {metrics['device_actions']['total_actions']}")
            logger.info(f"Device actions valid: {metrics['device_actions']['valid_actions']}")
            logger.info(f"Device action types: {metrics['device_actions']['action_types']}")

            # Check for EditText in UI (if cryptoapp)
            if app_name == "cryptoapp.apk":
                logger.info("\n🔍 EditText Detection Check:")
                logger.info(f"Element types seen: {metrics['element_coverage']['types_seen']}")
                has_edittext = 'EditText' in metrics['element_coverage']['types_seen']
                logger.info(f"EditText present: {has_edittext}")
                if has_edittext:
                    edittext_count = metrics['element_coverage']['type_counts'].get('EditText', 0)
                    logger.info(f"EditText count: {edittext_count}")
                    type_text_count = metrics['device_actions']['action_types'].get('TYPE_TEXT', 0)
                    logger.info(f"TYPE_TEXT actions: {type_text_count}")
                    if type_text_count == 0:
                        logger.error("❌ EditText present but NO TYPE_TEXT actions!")

        except Exception as e:
            logger.error(f"❌ Failed to validate {app_name}: {e}", exc_info=True)
            results[app_name] = {"error": str(e)}

    # Save comprehensive results
    summary_path = output_dir / "debug_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\n💾 Debug results saved to: {output_dir}")
    logger.info(f"   Summary: {summary_path}")

    # Analysis
    logger.info("\n" + "=" * 80)
    logger.info("📊 UNKNOWN ANALYSIS")
    logger.info("=" * 80)

    for app_name, metrics in results.items():
        if "error" in metrics:
            continue

        total_iter = metrics['total_iterations']
        actions_by_type = metrics['actions']['by_type']
        unknown_count = actions_by_type.get('UNKNOWN', 0)
        unknown_pct = (unknown_count / total_iter * 100) if total_iter > 0 else 0

        device_total = metrics['device_actions']['total_actions']
        device_valid = metrics['device_actions']['valid_actions']

        logger.info(f"\n{app_name}:")
        logger.info(f"  LLM iterations: {total_iter}")
        logger.info(f"  UNKNOWN: {unknown_count} ({unknown_pct:.1f}%)")
        logger.info(f"  Device actions: {device_valid}/{device_total}")
        logger.info(f"  LLM/Device ratio: {device_valid/total_iter:.2f}" if total_iter > 0 else "  LLM/Device ratio: N/A")
        logger.info(f"  Actions distribution: {actions_by_type}")

    return results


if __name__ == "__main__":
    results = test_unknown_debug()
    sys.exit(0)

"""
V5 Tool Calling - Full Validation with 29 Apps

Tests V5 with all 29 apps in the expanded dataset, including apps
with and without static analysis data.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime

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


def test_v5_all_apps():
    """
    Test V5 with all 29 apps in the dataset.

    This tests:
    - V5 tool calling with apps that have static analysis
    - V5 tool calling with apps that DON'T have static analysis
    - Overall V5 performance across diverse app set
    """

    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    output_dir = Path("v5_all_29_apps_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all apps from dataset
    all_apps = sorted([f.name for f in dataset_dir.iterdir() if f.name.endswith('.apk')])

    logger.info("=" * 80)
    logger.info("🚀 V5 VALIDATION: All 29 Apps")
    logger.info("=" * 80)
    logger.info(f"Dataset: {dataset_dir}")
    logger.info(f"Total apps: {len(all_apps)}")
    logger.info(f"Output: {output_dir}")
    logger.info("")

    # Create runner
    runner = ValidationRunner(
        dataset_dir=dataset_dir,
        max_iterations=10,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(728, 1288)
    )

    results = {}
    start_time = datetime.now()

    for idx, app_name in enumerate(all_apps, 1):
        logger.info("\n" + "=" * 80)
        logger.info(f"📱 APP {idx}/{len(all_apps)}: {app_name}")
        logger.info("=" * 80)

        try:
            # Run validation
            metrics = runner.validate_app(
                app_name=app_name,
                strategy="dfs",
                output_path=output_dir / f"{app_name}.json"
            )

            results[app_name] = metrics

            # Print quick summary
            logger.info(f"\n✅ {app_name} completed:")
            logger.info(f"   Iterations: {metrics['total_iterations']}")
            logger.info(f"   Device actions: {metrics['device_actions']['total_actions']}")
            logger.info(f"   UNKNOWN: {metrics['actions']['by_type'].get('UNKNOWN', 0)}")
            logger.info(f"   Has static analysis: {metrics.get('has_static_analysis', False)}")

        except Exception as e:
            logger.error(f"❌ Failed to validate {app_name}: {e}", exc_info=True)
            results[app_name] = {"error": str(e)}

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Save comprehensive results
    summary_path = output_dir / "v5_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Generate analysis
    logger.info("\n" + "=" * 80)
    logger.info("📊 V5 OVERALL ANALYSIS")
    logger.info("=" * 80)

    total_apps = len(all_apps)
    successful_apps = sum(1 for r in results.values() if "error" not in r)
    failed_apps = total_apps - successful_apps

    # Aggregate metrics
    total_iterations = 0
    total_device_actions = 0
    total_unknown = 0
    apps_with_static = 0
    apps_without_static = 0

    action_type_totals = {}

    for app_name, metrics in results.items():
        if "error" in metrics:
            continue

        total_iterations += metrics['total_iterations']
        total_device_actions += metrics['device_actions']['total_actions']
        total_unknown += metrics['actions']['by_type'].get('UNKNOWN', 0)

        if metrics.get('has_static_analysis', False):
            apps_with_static += 1
        else:
            apps_without_static += 1

        # Aggregate action types
        for action_type, count in metrics['device_actions']['action_types'].items():
            action_type_totals[action_type] = action_type_totals.get(action_type, 0) + count

    logger.info(f"\n📈 Execution Summary:")
    logger.info(f"   Total apps: {total_apps}")
    logger.info(f"   Successful: {successful_apps}")
    logger.info(f"   Failed: {failed_apps}")
    logger.info(f"   Duration: {duration:.1f}s ({duration/60:.1f} min)")

    logger.info(f"\n📊 Static Analysis:")
    logger.info(f"   Apps with static data: {apps_with_static}")
    logger.info(f"   Apps without static data: {apps_without_static}")

    logger.info(f"\n🎯 V5 Metrics:")
    logger.info(f"   Total iterations: {total_iterations}")
    logger.info(f"   Total device actions: {total_device_actions}")
    logger.info(f"   Device/Iteration ratio: {total_device_actions/total_iterations:.2f}" if total_iterations > 0 else "   Device/Iteration ratio: N/A")
    logger.info(f"   UNKNOWN actions: {total_unknown} ({100*total_unknown/total_iterations:.1f}%)" if total_iterations > 0 else "   UNKNOWN actions: 0")

    logger.info(f"\n📋 Action Type Distribution:")
    for action_type in sorted(action_type_totals.keys()):
        count = action_type_totals[action_type]
        pct = 100 * count / total_device_actions if total_device_actions > 0 else 0
        logger.info(f"   {action_type}: {count} ({pct:.1f}%)")

    # Per-app detailed table
    logger.info(f"\n📱 Per-App Results:")
    logger.info(f"   {'App':<40} {'Iter':>5} {'DevAct':>7} {'UNK':>5} {'Static':>7}")
    logger.info(f"   {'-'*40} {'-'*5} {'-'*7} {'-'*5} {'-'*7}")

    for app_name in sorted(results.keys()):
        metrics = results[app_name]
        if "error" in metrics:
            logger.info(f"   {app_name:<40} {'ERROR':>5}")
            continue

        iters = metrics['total_iterations']
        dev_actions = metrics['device_actions']['total_actions']
        unknown = metrics['actions']['by_type'].get('UNKNOWN', 0)
        has_static = "Yes" if metrics.get('has_static_analysis', False) else "No"

        logger.info(f"   {app_name:<40} {iters:>5} {dev_actions:>7} {unknown:>5} {has_static:>7}")

    logger.info(f"\n💾 Results saved to: {output_dir}")
    logger.info(f"   Summary: {summary_path}")

    return results


if __name__ == "__main__":
    results = test_v5_all_apps()
    sys.exit(0)

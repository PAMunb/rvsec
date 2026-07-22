"""
V7 Retry Logic with Coordinate Transformation - Full Validation with 29 Apps

Tests V7 (retry logic + coordinate transformation) with all 29 apps in the
expanded dataset, including apps with and without static analysis data.

Changes from V5:
- V7 retry logic with progressive sampling (temp 0.1 → 0.5 → 0.9)
- Coordinate transformation: UI elements shown in optimized space (728x1288)
- Max 2 retries before fallback to BACK action

Expected Improvements:
- Lower UNKNOWN rate compared to V5 (46.4%) and V6 (56.7%)
- Better action generation reliability
- Consistent performance across all apps
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


def test_v7_all_apps():
    """
    Test V7 with all 29 apps in the dataset.

    This tests:
    - V7 retry logic with progressive sampling
    - Coordinate transformation in UI prompts
    - V7 performance with apps that have static analysis
    - V7 performance with apps that DON'T have static analysis
    - Overall V7 performance across diverse app set
    """

    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    output_dir = Path("v7_all_29_apps_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all apps from dataset
    all_apps = sorted([f.name for f in dataset_dir.iterdir() if f.name.endswith('.apk')])

    logger.info("=" * 80)
    logger.info("🚀 V7 VALIDATION: All 29 Apps")
    logger.info("=" * 80)
    logger.info(f"Dataset: {dataset_dir}")
    logger.info(f"Total apps: {len(all_apps)}")
    logger.info(f"Output: {output_dir}")
    logger.info(f"V7 Features:")
    logger.info(f"  - Retry logic with progressive sampling (temp 0.1 → 0.5 → 0.9)")
    logger.info(f"  - Coordinate transformation (UI shown in 728x1288)")
    logger.info(f"  - Max 2 retries before fallback to BACK")
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
            unknown_count = metrics['actions']['by_type'].get('UNKNOWN', 0)
            total_iters = metrics['total_iterations']
            unknown_rate = (unknown_count / total_iters * 100) if total_iters > 0 else 0
            logger.info(f"   UNKNOWN: {unknown_count} ({unknown_rate:.1f}%)")
            logger.info(f"   Has static analysis: {metrics.get('has_static_analysis', False)}")

        except Exception as e:
            logger.error(f"❌ Failed to validate {app_name}: {e}", exc_info=True)
            results[app_name] = {"error": str(e)}

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Save comprehensive results
    summary_path = output_dir / "v7_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Generate analysis
    logger.info("\n" + "=" * 80)
    logger.info("📊 V7 COMPREHENSIVE ANALYSIS")
    logger.info("=" * 80)

    successful_apps = [k for k, v in results.items() if 'error' not in v]
    failed_apps = [k for k, v in results.items() if 'error' in v]

    logger.info(f"\n🎯 Overall Results:")
    logger.info(f"   Successful: {len(successful_apps)}/{len(all_apps)}")
    logger.info(f"   Failed: {len(failed_apps)}/{len(all_apps)}")
    logger.info(f"   Duration: {duration:.1f}s")

    if failed_apps:
        logger.info(f"\n❌ Failed apps:")
        for app in failed_apps:
            logger.info(f"   - {app}: {results[app]['error']}")

    # Calculate aggregate metrics
    if successful_apps:
        total_iters = sum(r['total_iterations'] for k, r in results.items() if k in successful_apps)
        total_actions = sum(r['device_actions']['total_actions'] for k, r in results.items() if k in successful_apps)
        total_unknown = sum(r['actions']['by_type'].get('UNKNOWN', 0) for k, r in results.items() if k in successful_apps)

        unknown_rate = (total_unknown / total_iters * 100) if total_iters > 0 else 0

        logger.info(f"\n📈 Aggregate Metrics:")
        logger.info(f"   Total iterations: {total_iters}")
        logger.info(f"   Total device actions: {total_actions}")
        logger.info(f"   UNKNOWN actions: {total_unknown} ({unknown_rate:.1f}%)")
        logger.info(f"   V5 baseline: 46.4% UNKNOWN")
        logger.info(f"   V6 baseline: 56.7% UNKNOWN")

        if unknown_rate < 46.4:
            improvement_v5 = 46.4 - unknown_rate
            improvement_v6 = 56.7 - unknown_rate
            logger.info(f"\n✅ SUCCESS: V7 outperforms both V5 and V6!")
            logger.info(f"   Improvement over V5: {improvement_v5:.1f}%")
            logger.info(f"   Improvement over V6: {improvement_v6:.1f}%")
        elif unknown_rate < 56.7:
            improvement_v6 = 56.7 - unknown_rate
            logger.info(f"\n⚠️  PARTIAL: V7 better than V6 but not V5")
            logger.info(f"   Improvement over V6: {improvement_v6:.1f}%")
            logger.info(f"   Still {unknown_rate - 46.4:.1f}% worse than V5")
        else:
            logger.info(f"\n❌ REGRESSION: V7 worse than both V5 and V6")
            logger.info(f"   Worse than V5 by: {unknown_rate - 46.4:.1f}%")
            logger.info(f"   Worse than V6 by: {unknown_rate - 56.7:.1f}%")

        # App-specific breakdown
        logger.info(f"\n📊 Per-App UNKNOWN Rates:")
        app_stats = []
        for app in successful_apps:
            r = results[app]
            total = r['total_iterations']
            unknown = r['actions']['by_type'].get('UNKNOWN', 0)
            rate = (unknown / total * 100) if total > 0 else 0
            app_stats.append((app, rate))

        # Sort by UNKNOWN rate (worst first)
        app_stats.sort(key=lambda x: x[1], reverse=True)

        logger.info("   Worst 10 apps:")
        for app, rate in app_stats[:10]:
            logger.info(f"      {app}: {rate:.1f}%")

        logger.info("\n   Best 10 apps:")
        for app, rate in app_stats[-10:]:
            logger.info(f"      {app}: {rate:.1f}%")

    logger.info("\n💾 Results saved to:")
    logger.info(f"   Summary: {summary_path}")
    logger.info(f"   Individual: {output_dir}/*.json")
    logger.info("=" * 80)

    return results, unknown_rate if successful_apps else None


if __name__ == "__main__":
    results, unknown_rate = test_v7_all_apps()

    # Exit code based on success
    if unknown_rate is not None:
        sys.exit(0 if unknown_rate < 46.4 else 1)
    else:
        sys.exit(1)

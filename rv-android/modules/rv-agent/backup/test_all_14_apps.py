"""
Complete validation test for all 14 apps in dataset.

Tests the stateless RVAgent refactoring across all apps to verify:
- Constant token usage (~1600-2500 tokens/iteration)
- No context overflow across different app complexities
- All memory system APIs working correctly
- Action execution success rates
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

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
    """Run validation on all 14 apps."""
    logger.info("=" * 80)
    logger.info("🧪 COMPLETE VALIDATION: All 14 Apps")
    logger.info("=" * 80)

    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    output_dir = Path("validation_results_all_apps")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Expected apps (14 total)
    expected_apps = [
        "byrne.utilities.hashpass_2.apk",
        "ca.farrelltonsolar.classic_314.apk",
        "com.gianlu.dnshero_40.apk",
        "com.github.axet.hourlyreminder_476.apk",
        "com.hwloc.lstopo_271.apk",
        "com.sam.hex_16.apk",
        "cryptoapp.apk",
        "info.zamojski.soft.towercollector_2140302.apk",
        "livio.rssreader_101.apk",
        "org.emunix.insteadlauncher_80601.apk",
        "org.pulpdust.lesserpad_42.apk",
        "org.secuso.privacyfriendlydicer_8.apk",
        "org.secuso.privacyfriendlyludo_5.apk",
        "t20kdc.offlinepuzzlesolver_4.apk"
    ]

    logger.info(f"\n📱 Apps to test: {len(expected_apps)}")
    logger.info(f"   Iterations per app: 25 (default)")
    logger.info(f"   Strategy: DFS")
    logger.info(f"   Output: {output_dir}")
    logger.info("")

    # Create runner
    runner = ValidationRunner(
        dataset_dir=dataset_dir,
        max_iterations=25,  # Full test
        device_dimensions=(1080, 1920),
        optimized_dimensions=(728, 1288)
    )

    # Results collection
    all_results = {}
    successful = 0
    failed = 0

    # Test each app
    for idx, app_name in enumerate(expected_apps, 1):
        logger.info("\n" + "=" * 80)
        logger.info(f"📱 APP {idx}/{len(expected_apps)}: {app_name}")
        logger.info("=" * 80)

        output_path = output_dir / f"{app_name}_validation.json"

        try:
            metrics = runner.validate_app(
                app_name=app_name,
                strategy="dfs",
                output_path=output_path
            )

            all_results[app_name] = {
                "status": "success",
                "metrics": metrics
            }
            successful += 1

            logger.info(f"✅ {app_name} completed successfully")

        except Exception as e:
            logger.error(f"❌ {app_name} failed: {e}", exc_info=True)
            all_results[app_name] = {
                "status": "error",
                "error": str(e)
            }
            failed += 1

    # Save summary
    summary_path = output_dir / "validation_summary.json"
    with open(summary_path, 'w') as f:
        json.dump({
            "total_apps": len(expected_apps),
            "successful": successful,
            "failed": failed,
            "results": all_results
        }, f, indent=2)

    # Print final summary
    logger.info("\n" + "=" * 80)
    logger.info("🏁 VALIDATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"\n📊 Overall Results:")
    logger.info(f"   Total apps: {len(expected_apps)}")
    logger.info(f"   Successful: {successful}")
    logger.info(f"   Failed: {failed}")
    logger.info(f"   Success rate: {successful/len(expected_apps)*100:.1f}%")

    # Token usage analysis
    logger.info(f"\n🎯 Token Usage Analysis:")
    token_stats = []
    for app_name, result in all_results.items():
        if result["status"] == "success":
            metrics = result["metrics"]
            avg_tokens = metrics.get("llm", {}).get("avg_tokens_per_iteration", 0)
            token_stats.append((app_name, avg_tokens))

    if token_stats:
        token_stats.sort(key=lambda x: x[1])
        min_app, min_tokens = token_stats[0]
        max_app, max_tokens = token_stats[-1]
        avg_all = sum(t for _, t in token_stats) / len(token_stats)

        logger.info(f"   Min: {min_tokens:.0f} tokens/iter ({min_app})")
        logger.info(f"   Max: {max_tokens:.0f} tokens/iter ({max_app})")
        logger.info(f"   Avg: {avg_all:.0f} tokens/iter (across all apps)")
        logger.info(f"   Target: < 3500 tokens/iter")

        if max_tokens < 3500:
            logger.info(f"   ✅ All apps under token limit!")
        else:
            logger.info(f"   ⚠️  Some apps exceed token limit")

    # Action success analysis
    logger.info(f"\n⚡ Action Success Analysis:")
    action_stats = []
    for app_name, result in all_results.items():
        if result["status"] == "success":
            metrics = result["metrics"]
            valid_rate = metrics.get("actions", {}).get("valid_rate", 0)
            action_stats.append((app_name, valid_rate))

    if action_stats:
        action_stats.sort(key=lambda x: x[1], reverse=True)
        perfect = sum(1 for _, rate in action_stats if rate == 1.0)
        avg_rate = sum(rate for _, rate in action_stats) / len(action_stats)

        logger.info(f"   Apps with 100% valid actions: {perfect}/{len(action_stats)}")
        logger.info(f"   Average valid action rate: {avg_rate*100:.1f}%")

    logger.info(f"\n💾 Results saved to: {output_dir}")
    logger.info(f"   Summary: {summary_path}")
    logger.info("=" * 80 + "\n")

    return successful == len(expected_apps)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

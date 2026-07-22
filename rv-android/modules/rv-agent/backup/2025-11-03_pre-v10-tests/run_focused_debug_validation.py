"""
Run DEBUG validation on critical apps only.

Focuses on:
1. cryptoapp - understand the 22 "missing" actions
2. simplenotes_7 - 100% UNKNOWN actions
3. ca.farrelltonsolar.classic_314 - best performer (for comparison)

This allows quick debugging (<5 min) with full DEBUG logs.
"""

import logging
import sys
from pathlib import Path
import time

# Setup DEBUG logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.validation.validation_runner import ValidationRunner


def main():
    """Run focused DEBUG validation on critical apps."""
    logger.info("=" * 80)
    logger.info("🔬 FOCUSED DEBUG VALIDATION - Critical Apps Only")
    logger.info("=" * 80)

    # Dataset directory
    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

    if not dataset_dir.exists():
        logger.error(f"Dataset directory not found: {dataset_dir}")
        return False

    # Critical apps to debug
    critical_apps = [
        "cryptoapp.apk",                           # 22 "missing" actions
        "com.rafapps.simplenotes_7.apk",           # 100% UNKNOWN
        "ca.farrelltonsolar.classic_314.apk"       # Best performer (comparison)
    ]

    logger.info(f"\n📱 Critical apps for debugging:")
    for app in critical_apps:
        logger.info(f"  - {app}")

    # Create results directory
    results_dir = Path("validation_results_debug")
    results_dir.mkdir(exist_ok=True)

    # Configuration
    max_iterations = 25
    device_dimensions = (1080, 1920)
    optimized_dimensions = (728, 1288)
    strategy = "dfs"

    logger.info(f"\n📋 Configuration:")
    logger.info(f"  Iterations per app: {max_iterations}")
    logger.info(f"  Strategy: {strategy}")
    logger.info(f"  Results dir: {results_dir}")
    logger.info(f"  Log level: DEBUG (full visibility)")
    logger.info("")

    # Create validation runner
    runner = ValidationRunner(
        dataset_dir=dataset_dir,
        max_iterations=max_iterations,
        device_dimensions=device_dimensions,
        optimized_dimensions=optimized_dimensions
    )

    # Validate each critical app
    results = {}
    start_time = time.time()

    for i, app_name in enumerate(critical_apps, 1):
        logger.info("=" * 80)
        logger.info(f"🔍 [{i}/{len(critical_apps)}] DEBUG VALIDATION: {app_name}")
        logger.info("=" * 80)

        output_path = results_dir / f"{app_name.replace('.apk', '')}_debug_validation.json"

        try:
            app_start = time.time()

            metrics = runner.validate_app(
                app_name=app_name,
                strategy=strategy,
                output_path=output_path
            )

            app_duration = time.time() - app_start

            logger.info(f"\n✅ {app_name} completed in {app_duration:.1f}s")
            logger.info(f"   Results: {output_path}")
            logger.info(f"   Unique screens: {metrics['exploration']['unique_screens']}")
            logger.info(f"   Valid actions: {metrics['actions']['valid']}/{metrics['actions']['valid'] + metrics['actions']['invalid']}")

            results[app_name] = {
                'success': True,
                'metrics': metrics,
                'duration': app_duration
            }

        except Exception as e:
            logger.error(f"\n❌ {app_name} failed: {e}", exc_info=True)
            results[app_name] = {
                'success': False,
                'error': str(e)
            }

        logger.info("")

    total_duration = time.time() - start_time

    # Summary
    logger.info("=" * 80)
    logger.info("📊 DEBUG VALIDATION SUMMARY")
    logger.info("=" * 80)

    for app_name, result in results.items():
        if result['success']:
            logger.info(f"\n✅ {app_name}:")
            metrics = result['metrics']
            logger.info(f"   Duration: {result['duration']:.1f}s")
            logger.info(f"   Iterations: {metrics['total_iterations']}")
            logger.info(f"   Actions: {metrics['actions']['by_type']}")
            logger.info(f"   Valid rate: {metrics['actions']['valid_rate'] * 100:.1f}%")
            logger.info(f"   Unique screens: {metrics['exploration']['unique_screens']}")

            # Highlight critical metrics
            if app_name == "cryptoapp.apk":
                device_actions = metrics.get('device_actions', {})
                logger.info(f"\n   🔍 CRYPTOAPP ANALYSIS:")
                logger.info(f"      Total iterations: {metrics['total_iterations']}")
                logger.info(f"      MockDevice actions: {device_actions.get('total_actions', 0)}")
                logger.info(f"      Discrepancy: {metrics['total_iterations'] - device_actions.get('total_actions', 0)}")

            elif app_name == "com.rafapps.simplenotes_7.apk":
                logger.info(f"\n   🔍 SIMPLENOTES ANALYSIS:")
                logger.info(f"      UNKNOWN count: {metrics['actions']['by_type'].get('UNKNOWN', 0)}")
                logger.info(f"      LLM avg tokens: {metrics['llm']['avg_tokens_per_iteration']:.1f}")
        else:
            logger.info(f"\n❌ {app_name}: {result['error']}")

    logger.info(f"\n⏱️  Total duration: {total_duration:.1f}s ({total_duration/60:.1f}min)")
    logger.info(f"   Results saved to: {results_dir}")

    logger.info("\n" + "=" * 80)
    logger.info("🎯 Next Steps:")
    logger.info("=" * 80)
    logger.info("1. Analyze DEBUG logs for:")
    logger.info("   - LLM response content (📤 LLM Response Content)")
    logger.info("   - MockDevice state changes (🔍 BEFORE/AFTER graph invocation)")
    logger.info("   - Action type determination (🎯 ACTION_TYPE DETERMINATION)")
    logger.info("")
    logger.info("2. Extract patterns:")
    logger.info("   grep '📤 LLM Response Content' focused_debug_validation.log")
    logger.info("   grep '🔍 BEFORE\\|🔍 AFTER' focused_debug_validation.log")
    logger.info("   grep '🎯 ACTION_TYPE' focused_debug_validation.log")
    logger.info("=" * 80)

    return all(r['success'] for r in results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

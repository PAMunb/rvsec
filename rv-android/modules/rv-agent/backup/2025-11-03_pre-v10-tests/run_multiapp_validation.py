"""
Run validation on all apps in the dataset.

Discovers all apps in the dataset directory and runs offline validation
on each, generating individual results and a comparative report.
"""

import logging
import sys
from pathlib import Path
import time

# Setup logging (DEBUG level to capture detailed logs)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.validation.validation_runner import ValidationRunner
from rv_agent.validation.comparative_report import ComparativeReportGenerator


def discover_apps(dataset_dir: Path) -> list[str]:
    """
    Discover all app directories in dataset.

    Args:
        dataset_dir: Dataset root directory

    Returns:
        List of app names (directory names ending with .apk)
    """
    app_dirs = [d for d in dataset_dir.iterdir()
               if d.is_dir() and d.name.endswith('.apk')]

    app_names = [d.name for d in sorted(app_dirs)]

    logger.info(f"Found {len(app_names)} apps in dataset:")
    for app_name in app_names:
        logger.info(f"  - {app_name}")

    return app_names


def main():
    """Run multi-app validation."""
    logger.info("=" * 80)
    logger.info("🧪 Multi-App Validation Framework")
    logger.info("=" * 80)

    # Dataset directory
    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

    if not dataset_dir.exists():
        logger.error(f"Dataset directory not found: {dataset_dir}")
        return False

    # Discover apps
    app_names = discover_apps(dataset_dir)

    if not app_names:
        logger.error("No apps found in dataset")
        return False

    # Create results directory
    results_dir = Path("validation_results")
    results_dir.mkdir(exist_ok=True)

    # Configuration
    max_iterations = 25  # Iterations per app
    device_dimensions = (1080, 1920)
    optimized_dimensions = (728, 1288)
    strategy = "dfs"

    logger.info(f"\n📋 Configuration:")
    logger.info(f"  Total apps: {len(app_names)}")
    logger.info(f"  Iterations per app: {max_iterations}")
    logger.info(f"  Strategy: {strategy}")
    logger.info(f"  Results dir: {results_dir}")
    logger.info("")

    # Create validation runner (reuse for all apps)
    runner = ValidationRunner(
        dataset_dir=dataset_dir,
        max_iterations=max_iterations,
        device_dimensions=device_dimensions,
        optimized_dimensions=optimized_dimensions
    )

    # Validate each app
    successful_apps = []
    failed_apps = []

    start_time = time.time()

    for i, app_name in enumerate(app_names, 1):
        logger.info("=" * 80)
        logger.info(f"📱 [{i}/{len(app_names)}] Validating: {app_name}")
        logger.info("=" * 80)

        output_path = results_dir / f"{app_name.replace('.apk', '')}_validation.json"

        try:
            # Run validation
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

            successful_apps.append(app_name)

        except Exception as e:
            logger.error(f"\n❌ {app_name} failed: {e}", exc_info=True)
            failed_apps.append(app_name)

        logger.info("")

    total_duration = time.time() - start_time

    # Summary
    logger.info("=" * 80)
    logger.info("📊 VALIDATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"\n✅ Successful: {len(successful_apps)}/{len(app_names)}")
    for app in successful_apps:
        logger.info(f"  - {app}")

    if failed_apps:
        logger.info(f"\n❌ Failed: {len(failed_apps)}/{len(app_names)}")
        for app in failed_apps:
            logger.info(f"  - {app}")

    logger.info(f"\n⏱️  Total duration: {total_duration:.1f}s ({total_duration/60:.1f}min)")
    logger.info(f"   Avg per app: {total_duration/len(app_names):.1f}s")

    # Generate comparative report
    if successful_apps:
        logger.info("\n" + "=" * 80)
        logger.info("📈 Generating Comparative Report")
        logger.info("=" * 80)

        try:
            report_gen = ComparativeReportGenerator(results_dir)

            # Load all results
            num_loaded = report_gen.load_results()
            logger.info(f"Loaded {num_loaded} results")

            # Aggregate metrics
            metrics = report_gen.aggregate_metrics()

            # Generate reports
            markdown_path = results_dir / "COMPARATIVE_REPORT.md"
            csv_path = results_dir / "comparative_metrics.csv"

            report_gen.generate_markdown_report(markdown_path, metrics)
            report_gen.generate_csv_report(csv_path)

            logger.info(f"\n✅ Reports generated:")
            logger.info(f"   Markdown: {markdown_path}")
            logger.info(f"   CSV: {csv_path}")

        except Exception as e:
            logger.error(f"❌ Failed to generate comparative report: {e}", exc_info=True)

    logger.info("\n" + "=" * 80)
    logger.info("🎉 Multi-App Validation Complete!")
    logger.info("=" * 80)

    return len(failed_apps) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

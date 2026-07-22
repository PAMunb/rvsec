"""
Run full validation on cryptoapp with all 25 screens.
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
    """Run full cryptoapp validation."""
    logger.info("=" * 80)
    logger.info("🧪 Full CryptoApp Validation (25 iterations)")
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
            max_iterations=25,  # All 25 screens
            device_dimensions=(1080, 1920),
            optimized_dimensions=(728, 1288)
        )

        # Run validation on cryptoapp
        output_path = Path("validation_results") / "cryptoapp_full_validation.json"
        metrics = runner.validate_app(
            app_name="cryptoapp.apk",
            strategy="dfs",
            output_path=output_path
        )

        logger.info("\n✅ Validation completed successfully!")
        logger.info(f"📄 Results saved to: {output_path}")

        # Print detailed analysis
        logger.info("\n" + "=" * 80)
        logger.info("📊 DETAILED ANALYSIS")
        logger.info("=" * 80)

        # Action distribution
        logger.info("\n📈 Action Distribution:")
        total_actions = sum(metrics['actions']['by_type'].values())
        for action_type, count in sorted(metrics['actions']['by_type'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_actions * 100) if total_actions > 0 else 0
            logger.info(f"  {action_type}: {count} ({percentage:.1f}%)")

        # Element coverage
        logger.info("\n🎨 Element Types Discovered:")
        for elem_type in sorted(metrics['element_coverage']['types_seen']):
            count = metrics['element_coverage']['type_counts'].get(elem_type, 0)
            logger.info(f"  {elem_type}: {count} occurrences")

        # Screen exploration
        logger.info("\n🗺️  Screen Exploration:")
        logger.info(f"  Unique screens: {metrics['exploration']['unique_screens']}")
        logger.info(f"  Total visits: {sum(metrics['exploration']['screen_visits'].values())}")
        logger.info(f"  Revisit rate: {metrics['exploration']['revisit_rate'] * 100:.1f}%")
        logger.info(f"  Activities discovered: {len(metrics['exploration']['activities'])}")
        for activity in sorted(metrics['exploration']['activities']):
            logger.info(f"    - {activity}")

        # Device actions summary
        if 'device_actions' in metrics:
            device_summary = metrics['device_actions']
            logger.info("\n⚙️  Device Action Summary:")
            logger.info(f"  Total actions: {device_summary['total_actions']}")
            logger.info(f"  Valid actions: {device_summary['valid_actions']} ({device_summary['valid_rate']*100:.1f}%)")
            logger.info(f"  Invalid actions: {device_summary['invalid_actions']}")

        # Memory/Graph
        logger.info("\n🧠 Memory & Graph State:")
        logger.info(f"  Graph states: {metrics['memory_graph']['graph_states']}")
        logger.info(f"  Graph transitions: {metrics['memory_graph']['graph_transitions']}")
        logger.info(f"  Short-term iterations: {metrics['memory_graph']['short_term_iterations']}")

        logger.info("\n" + "=" * 80)
        logger.info("🎉 Validation Complete!")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"❌ Validation failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

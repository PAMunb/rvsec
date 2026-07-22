"""
Quick test for stateless RVAgent refactoring on cryptoapp.

Tests the refactored stateless architecture with a single app
to verify no context overflow occurs.
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
    """Test stateless refactoring with cryptoapp."""
    logger.info("=" * 80)
    logger.info("🧪 Testing Stateless RVAgent Refactoring")
    logger.info("=" * 80)

    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    output_path = Path("test_stateless_cryptoapp.json")

    logger.info(f"\n📱 App: cryptoapp.apk")
    logger.info(f"   Iterations: 10 (quick test)")
    logger.info(f"   Expected: Constant ~2500 tokens/iteration")
    logger.info(f"   Expected: NO context overflow")
    logger.info("")

    # Create runner
    runner = ValidationRunner(
        dataset_dir=dataset_dir,
        max_iterations=10,  # Quick test
        device_dimensions=(1080, 1920),
        optimized_dimensions=(728, 1288)
    )

    # Run validation
    try:
        metrics = runner.validate_app(
            app_name="cryptoapp.apk",
            strategy="dfs",
            output_path=output_path
        )

        logger.info("\n" + "=" * 80)
        logger.info("✅ STATELESS TEST RESULTS")
        logger.info("=" * 80)
        logger.info(f"\n📊 Metrics:")
        logger.info(f"   Iterations: {metrics['iterations']}")
        logger.info(f"   Unique screens: {metrics['exploration']['unique_screens']}")
        logger.info(f"   Valid actions: {metrics['actions']['valid']}")
        logger.info(f"   LLM avg tokens: {metrics['llm']['avg_tokens_input']:.0f} in / {metrics['llm']['avg_tokens_output']:.0f} out")
        logger.info(f"\n🎯 Token Analysis:")
        logger.info(f"   Min input tokens: {metrics['llm']['min_tokens_input']}")
        logger.info(f"   Max input tokens: {metrics['llm']['max_tokens_input']}")
        logger.info(f"   Token variance: {metrics['llm']['max_tokens_input'] - metrics['llm']['min_tokens_input']}")

        # Check expectations
        avg_input = metrics['llm']['avg_tokens_input']
        max_input = metrics['llm']['max_tokens_input']

        logger.info(f"\n🔍 Validation:")
        if avg_input < 3500:
            logger.info(f"   ✅ Average tokens ({avg_input:.0f}) < 3500 (GOOD)")
        else:
            logger.info(f"   ❌ Average tokens ({avg_input:.0f}) >= 3500 (TOO HIGH)")

        if max_input < 32000:
            logger.info(f"   ✅ Max tokens ({max_input}) < 32K limit (NO OVERFLOW)")
        else:
            logger.info(f"   ❌ Max tokens ({max_input}) >= 32K (OVERFLOW!)")

        logger.info(f"\n💾 Results saved: {output_path}")

        return True

    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

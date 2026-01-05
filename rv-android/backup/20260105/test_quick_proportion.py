"""
Quick test to validate proportion comparison setup.

Tests 3 configurations quickly (30s each) to validate before full run.
"""

import logging
import sys

from compare_llm_proportions import compare_proportions

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run quick validation test."""

    logger.info("Quick Proportion Test - 3 configurations @ 2min each")
    logger.info("Estimated time: 6 minutes total")
    logger.info("="*80)

    # Test 3 key proportions quickly
    probabilities = [
        0.60,  # Balanced (60-40)
        0.70,  # Current default (70-30)
        0.80,  # LLM dominant (80-20)
    ]

    results = compare_proportions(
        probabilities=probabilities,
        timeout=120,  # 2 minutes for quick validation
        output_dir="./quick_proportion_test"
    )

    if results.get("status") != "failed":
        logger.info("\n✅ Quick test completed!")
        logger.info("Ready for full comparison with 3min timeout")
    else:
        logger.error("\n❌ Quick test failed!")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

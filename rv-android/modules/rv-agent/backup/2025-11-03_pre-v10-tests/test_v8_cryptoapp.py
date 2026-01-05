"""
V8 Validation Test - Form Intelligence + Spinner Guidance

Tests V8 improvements with cryptoapp.apk:
- Prompt V8 (form intelligence + spinner guidance + pre-submit validation)
- V7 retry logic (progressive sampling: temp 0.1 → 0.5 → 0.9)
- Clickable element filtering (reduces invalid actions from 20% to ~0%)
- Coordinate transformation (UI shown in 728x1288)

Expected Improvements over V7:
- Invalid actions: 20% → <5% (clickable filtering)
- TYPE_TEXT usage: 0% → 30-40% (EditText priority + pre-submit validation)
- Spinner interactions: 0 → detectable (Spinner-specific guidance)
- Repetition: 40% (4/10) → <20% (pre-submit validation + repetition detection)
"""

import json
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


def test_v8_cryptoapp():
    """
    Test V8 with cryptoapp.apk (10 iterations).

    V8 Changes:
    1. Prompt V8: Form intelligence + Spinner guidance + pre-submit validation
    2. Clickable filtering: Only show clickable=true elements to LLM
    3. V7 retry logic: Progressive sampling (temp 0.1 → 0.5 → 0.9)
    4. Coordinate transformation: UI coordinates in optimized space (728x1288)

    Comparison Metrics:
    - Invalid actions: V7 20% → V8 target <5%
    - TYPE_TEXT usage: V7 0% → V8 target 30-40%
    - Spinner interactions: V7 0 → V8 target >0
    - Repetition rate: V7 40% → V8 target <20%
    """

    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    output_dir = Path("v8_cryptoapp_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("🚀 V8 VALIDATION: CryptoApp Test")
    logger.info("=" * 80)
    logger.info(f"Dataset: {dataset_dir}")
    logger.info(f"Output: {output_dir}")
    logger.info(f"V8 Features:")
    logger.info(f"  - Prompt V8 (form intelligence + Spinner guidance)")
    logger.info(f"  - Clickable element filtering (only clickable=true shown to LLM)")
    logger.info(f"  - Pre-submit validation (check EditText/Spinner before Submit)")
    logger.info(f"  - Repetition detection guidance")
    logger.info(f"  - V7 retry logic (temp 0.1 → 0.5 → 0.9, max 2 retries)")
    logger.info(f"  - Coordinate transformation (UI shown in 728x1288)")
    logger.info("")

    # Create runner
    runner = ValidationRunner(
        dataset_dir=dataset_dir,
        max_iterations=10,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(728, 1288)
    )

    logger.info("📱 Testing: cryptoapp.apk")
    logger.info("=" * 80)

    try:
        # Run validation
        metrics = runner.validate_app(
            app_name="cryptoapp.apk",
            strategy="dfs",
            output_path=output_dir / "cryptoapp.apk.json"
        )

        # Extract detailed metrics
        total_iterations = metrics['total_iterations']
        device_actions = metrics['device_actions']
        total_actions = device_actions['total_actions']
        valid_actions = device_actions['valid_actions']
        invalid_actions = device_actions['invalid_actions']

        action_types = metrics['actions']['by_type']
        click_count = action_types.get('CLICK', 0)
        type_text_count = action_types.get('TYPE_TEXT', 0)

        # Calculate metrics
        invalid_rate = (invalid_actions / total_actions * 100) if total_actions > 0 else 0
        type_text_rate = (type_text_count / total_iterations * 100) if total_iterations > 0 else 0

        # Count repetitions (same action 2+ times in a row)
        actions_list = device_actions['actions']
        repetition_count = 0
        prev_element = None
        for action in actions_list:
            current_element = action.get('element', '')
            if prev_element and current_element == prev_element:
                repetition_count += 1
            prev_element = current_element

        repetition_rate = (repetition_count / total_actions * 100) if total_actions > 0 else 0

        # Print results
        logger.info(f"\n✅ V8 cryptoapp completed!")
        logger.info(f"\n📊 V8 Results:")
        logger.info(f"   Iterations: {total_iterations}")
        logger.info(f"   Device actions: {total_actions}")
        logger.info(f"   Valid actions: {valid_actions}")
        logger.info(f"   Invalid actions: {invalid_actions} ({invalid_rate:.1f}%)")
        logger.info(f"\n📊 Tool Distribution:")
        logger.info(f"   CLICK: {click_count} ({click_count/total_iterations*100:.1f}%)")
        logger.info(f"   TYPE_TEXT: {type_text_count} ({type_text_rate:.1f}%)")
        logger.info(f"   Repetitions: {repetition_count} ({repetition_rate:.1f}%)")

        # Compare with V7 baseline
        logger.info(f"\n📈 Comparison with V7 Baseline:")
        logger.info(f"   Invalid actions: V7 20.0% → V8 {invalid_rate:.1f}% (target <5%)")
        logger.info(f"   TYPE_TEXT usage: V7 0.0% → V8 {type_text_rate:.1f}% (target 30-40%)")
        logger.info(f"   Repetition: V7 40.0% → V8 {repetition_rate:.1f}% (target <20%)")

        # Element coverage
        logger.info(f"\n📊 Element Coverage:")
        logger.info(f"   Types seen: {len(metrics['element_coverage']['types_seen'])}")
        logger.info(f"   Unique screens: {metrics['exploration']['unique_screens']}")
        logger.info(f"   Activities: {len(metrics['exploration']['activities'])}")

        # Success check
        improvements = []
        if invalid_rate < 20.0:
            improvements.append("Invalid actions reduced")
        if type_text_rate > 0.0:
            improvements.append("TYPE_TEXT now used")
        if repetition_rate < 40.0:
            improvements.append("Repetition reduced")

        if improvements:
            logger.info(f"\n✅ SUCCESS: V8 shows improvements!")
            for improvement in improvements:
                logger.info(f"   ✓ {improvement}")
        else:
            logger.info(f"\n⚠️  WARNING: V8 may not be improving all metrics")

        logger.info(f"\n💾 Results saved to: {output_dir}/cryptoapp.apk.json")
        logger.info("=" * 80)

        return metrics, invalid_rate, type_text_rate, repetition_rate

    except Exception as e:
        logger.error(f"❌ Failed to validate cryptoapp.apk: {e}", exc_info=True)
        return None, None, None, None


if __name__ == "__main__":
    metrics, invalid_rate, type_text_rate, repetition_rate = test_v8_cryptoapp()

    # Exit code based on success
    if metrics is not None:
        # Success if at least 2 out of 3 metrics improved
        improvements = 0
        if invalid_rate < 20.0:
            improvements += 1
        if type_text_rate > 0.0:
            improvements += 1
        if repetition_rate < 40.0:
            improvements += 1

        sys.exit(0 if improvements >= 2 else 1)
    else:
        sys.exit(1)

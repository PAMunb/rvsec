"""
Quick Test Script for Coordinate Validation

Tests the validation pipeline with a single screenshot to verify everything is working.
"""

import sys
from pathlib import Path

# Add the validation directory to Python path
sys.path.append(str(Path(__file__).parent))

from coordinate_validator import CoordinateValidator


def quick_test():
    """Run a quick test with a single screenshot."""
    print("🚀 Quick Coordinate Validation Test")
    print("=" * 50)

    # Initialize validator
    validator = CoordinateValidator(model_name="PetrosStav/gemma3-tools:4b")

    # Test with cryptoapp - should be simple and reliable
    dataset_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    app_path = Path(dataset_path) / "cryptoapp.apk"

    # Find first screenshot and XML
    screenshots = sorted(app_path.glob("*.png"))
    if not screenshots:
        print(f"❌ No screenshots found in {app_path}")
        return

    screenshot = screenshots[0]
    xml_path = screenshot.with_suffix(".uiautomator")

    if not xml_path.exists():
        print(f"❌ XML not found: {xml_path}")
        return

    print(f"📸 Testing: {screenshot.name}")
    print(f"📄 XML: {xml_path.name}")

    # Test baseline strategy first
    result = validator.validate_single_screenshot(
        str(screenshot),
        str(xml_path),
        strategy="baseline"
    )

    # Print results
    print("\n" + "="*50)
    print("📊 QUICK TEST RESULTS")
    print("="*50)

    if result.get("success", False):
        metrics = result.get("metrics", {})
        print(f"✅ Test successful!")
        print(f"📊 Clicks: {metrics.get('total_clicks', 0)}")
        print(f"🎯 Hits: {metrics.get('hits', 0)}")
        print(f"📈 Hit Rate: {metrics.get('hit_rate', 0):.1f}%")
        print(f"📏 Avg Distance: {metrics.get('avg_distance', 0):.1f}px")
        print(f"⏱️ Response Time: {result.get('response_time', 0):.2f}s")

        # Show click history for analysis
        click_history = metrics.get('click_history', [])
        if click_history:
            print(f"\n🖱️ Click Details:")
            for i, (x, y, element, distance) in enumerate(click_history, 1):
                status = "✅ HIT" if distance < 50 else "❌ MISS"
                print(f"  {i}. ({x},{y}) -> {element} ({distance:.1f}px) {status}")

        # Show agent output snippet
        agent_output = result.get("agent_output", "")
        if agent_output:
            print(f"\n🤖 Agent Output (snippet):")
            print(f"   {agent_output[:200]}...")

    else:
        print(f"❌ Test failed: {result.get('error', 'Unknown error')}")

    return result


def test_all_strategies():
    """Test all strategies with a single screenshot."""
    print("\n🔬 Testing All Strategies")
    print("=" * 50)

    validator = CoordinateValidator(model_name="PetrosStav/gemma3-tools:4b")

    # Same setup as quick_test
    dataset_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    app_path = Path(dataset_path) / "cryptoapp.apk"
    screenshots = sorted(app_path.glob("*.png"))
    screenshot = screenshots[0]
    xml_path = screenshot.with_suffix(".uiautomator")

    strategies = ["baseline", "coordinate_validation", "spinner_focused"]

    results = {}
    for strategy in strategies:
        print(f"\n🧪 Testing strategy: {strategy}")
        result = validator.validate_single_screenshot(
            str(screenshot),
            str(xml_path),
            strategy=strategy
        )
        results[strategy] = result

        if result.get("success", False):
            metrics = result.get("metrics", {})
            print(f"  Hit Rate: {metrics.get('hit_rate', 0):.1f}%")
            print(f"  Distance: {metrics.get('avg_distance', 0):.1f}px")
        else:
            print(f"  ❌ Failed: {result.get('error', 'Unknown')}")

    # Summary
    print(f"\n📊 Strategy Comparison:")
    for strategy, result in results.items():
        if result.get("success", False):
            hit_rate = result["metrics"].get("hit_rate", 0)
            print(f"  {strategy}: {hit_rate:.1f}%")
        else:
            print(f"  {strategy}: FAILED")

    return results


if __name__ == "__main__":
    # Run quick test first
    quick_result = quick_test()

    # If quick test passes, test all strategies
    if quick_result and quick_result.get("success", False):
        strategy_results = test_all_strategies()
    else:
        print("\n⚠️ Quick test failed, skipping strategy comparison")
        print("Check model availability and file paths")
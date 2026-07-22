"""
Expanded Test Runner with detailed logging for 4 diverse apps.
"""

import sys
from pathlib import Path

# Add rv-agent to path
rv_agent_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, rv_agent_path)

from coordinate_validator_fixed import CoordinateValidatorFixed
import json
from datetime import datetime


def main():
    """Run expanded test with detailed logging."""

    print("🚀 EXPANDED COORDINATE VALIDATION TEST")
    print("=" * 60)
    print("Testing 4 diverse apps with Gemma3-tools")
    print("Apps: cryptoapp, hashpass, lstopo, ludo")
    print("=" * 60)

    # Initialize validator
    validator = CoordinateValidatorFixed(model_name="PetrosStav/gemma3-tools:4b")

    # Define test configuration
    dataset_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"

    test_apps = [
        "cryptoapp.apk",                           # Simple: 3 buttons
        "byrne.utilities.hashpass_2.apk",          # Simple + Spinners
        "com.hwloc.lstopo_271.apk",                # Complex: many elements
        "org.secuso.privacyfriendlyludo_5.apk"     # Extreme: 121+ elements (Paradox test)
    ]

    strategies = [
        "baseline",
        "coordinate_validation",
        "spinner_focused"
    ]

    # Special test selection per app
    special_screenshots = {
        "cryptoapp.apk": ["001.png"],                    # Our reliable test
        "byrne.utilities.hashpass_2.apk": ["001.png"],   # Dialog + Spinners
        "com.hwloc.lstopo_271.apk": ["001.png"],         # Complex elements
        "org.secuso.privacyfriendlyludo_5.apk": ["009.png"]  # 121 elements test!
    }

    print(f"📸 Special screenshots selected:")
    for app, screenshots in special_screenshots.items():
        print(f"  {app}: {screenshots}")

    # Run validation with specific screenshots
    print(f"\n🧪 Starting comprehensive validation...")

    # Custom validation run
    all_results = []

    for app in test_apps:
        app_path = Path(dataset_path) / app

        if not app_path.exists():
            print(f"⚠️ App directory not found: {app}")
            continue

        print(f"\n📱 Testing app: {app}")
        print("-" * 40)

        # Use special screenshots if defined, otherwise first available
        if app in special_screenshots:
            screenshot_names = special_screenshots[app]
        else:
            screenshot_names = [sorted(app_path.glob("*.png"))[0].name]

        for screenshot_name in screenshot_names:
            screenshot_path = app_path / screenshot_name
            xml_path = app_path / screenshot_name.replace(".png", ".uiautomator")

            if not screenshot_path.exists() or not xml_path.exists():
                print(f"⚠️ Missing files for {screenshot_name}")
                continue

            print(f"\n📸 Testing screenshot: {screenshot_name}")

            # Test each strategy
            for strategy in strategies:
                print(f"  🧪 Strategy: {strategy}")

                result = validator.validate_single_screenshot(
                    str(screenshot_path),
                    str(xml_path),
                    strategy
                )
                result["app"] = app
                result["screenshot_file"] = screenshot_name
                all_results.append(result)

                # Log key metrics immediately
                if result.get("success", False):
                    metrics = result["metrics"]
                    print(f"    ✅ Hit rate: {metrics['hit_rate']:.1f}% | Distance: {metrics['avg_distance']:.1f}px | Time: {result['response_time']:.2f}s")
                else:
                    print(f"    ❌ Failed: {result.get('error', 'Unknown error')}")

    # Aggregate and save results
    final_results = validator.aggregate_results(all_results)

    # Add special analysis for Ludo (Paradox test)
    ludo_results = [r for r in all_results if "ludo" in r.get("app", "")]
    if ludo_results:
        ludo_analysis = {
            "paradox_test": True,
            "elements_count": "121+ (extreme complexity)",
            "app": "org.secuso.privacyfriendlyludo_5.apk",
            "results": ludo_results
        }
        final_results["ludo_paradox_analysis"] = ludo_analysis

    # Save results with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"expanded_validation_results_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(final_results, f, indent=2)

    # Print comprehensive summary
    print("\n" + "="*60)
    print("📊 EXPANDED VALIDATION RESULTS")
    print("="*60)

    print(f"📈 Overall Statistics:")
    print(f"  Total tests: {final_results.get('total_tests', 0)}")
    print(f"  Successful: {final_results.get('successful_tests', 0)}")

    if "strategy_stats" in final_results:
        print(f"\n🎯 Strategy Performance:")
        for strategy, stats in final_results["strategy_stats"].items():
            print(f"  {strategy}:")
            print(f"    Hit Rate: {stats['hit_rate']:.1f}%")
            print(f"    Avg Distance: {stats['avg_distance']:.1f}px")
            print(f"    Response Time: {stats['avg_response_time']:.2f}s")
            print(f"    Tool Calls: {stats['total_tool_calls']}")

        print(f"\n🏆 Best Strategy: {final_results['best_strategy']['name']} "
              f"({final_results['best_strategy']['hit_rate']:.1f}% hit rate)")

    # Per-app analysis
    print(f"\n📱 Per-App Analysis:")
    apps_performance = {}
    for result in all_results:
        if result.get("success", False):
            app = result["app"]
            if app not in apps_performance:
                apps_performance[app] = []
            apps_performance[app].append(result["metrics"]["hit_rate"])

    for app, hit_rates in apps_performance.items():
        avg_hit_rate = sum(hit_rates) / len(hit_rates)
        app_short = app.split(".")[0] if "." in app else app[:15]
        print(f"  {app_short}: {avg_hit_rate:.1f}% avg hit rate ({len(hit_rates)} tests)")

    # Special Paradox Analysis for Ludo
    if "ludo_paradox_analysis" in final_results:
        print(f"\n🎲 LUDO PARADOX TEST (121+ elements):")
        ludo_stats = final_results["ludo_paradox_analysis"]["results"]
        ludo_hit_rates = [r["metrics"]["hit_rate"] for r in ludo_stats if r.get("success")]
        if ludo_hit_rates:
            avg_ludo = sum(ludo_hit_rates) / len(ludo_hit_rates)
            print(f"  Ludo hit rate: {avg_ludo:.1f}%")
            print(f"  Phase 0 prediction: Complex apps (20+ elements) = 100% success")
            if avg_ludo >= 80:
                print(f"  ✅ PARADOX CONFIRMED: High complexity improves performance!")
            else:
                print(f"  ❓ PARADOX UNCLEAR: Results below expectation")

    print(f"\n💾 Detailed results saved to: {output_file}")
    print(f"📋 Use this for analysis:")
    print(f"  cat {output_file} | jq '.strategy_stats'")
    print(f"  grep -A5 -B5 'explanation' {output_file}")


if __name__ == "__main__":
    main()
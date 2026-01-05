"""
Incremental Coordinate Validation Test

Starts with very few screenshots and gradually increases to test the complete pipeline.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add the validation directory to Python path
sys.path.append(str(Path(__file__).parent))

from coordinate_validator import CoordinateValidator


class IncrementalValidator:
    """Manages incremental testing from small to large datasets."""

    def __init__(self, model_name: str = "PetrosStav/gemma3-tools:4b"):
        """Initialize incremental validator."""
        self.validator = CoordinateValidator(model_name)
        self.dataset_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"

    def get_test_configurations(self) -> List[Dict[str, Any]]:
        """
        Define incremental test configurations from small to large.

        Returns:
            List of test configurations with increasing complexity
        """
        configs = [
            {
                "name": "minimal_test",
                "description": "1 app, 1 screenshot, 1 strategy",
                "apps": ["cryptoapp.apk"],
                "strategies": ["baseline"],
                "samples_per_app": 1
            },
            {
                "name": "single_app_basic",
                "description": "1 app, 2 screenshots, 2 strategies",
                "apps": ["cryptoapp.apk"],
                "strategies": ["baseline", "coordinate_validation"],
                "samples_per_app": 2
            },
            {
                "name": "single_app_full",
                "description": "1 app, 3 screenshots, all strategies",
                "apps": ["cryptoapp.apk"],
                "strategies": ["baseline", "coordinate_validation", "enhanced_description",
                              "element_priority", "spinner_focused"],
                "samples_per_app": 3
            },
            {
                "name": "two_apps_test",
                "description": "2 apps, 3 screenshots each, key strategies",
                "apps": ["cryptoapp.apk", "byrne.utilities.hashpass_2.apk"],
                "strategies": ["baseline", "coordinate_validation", "spinner_focused"],
                "samples_per_app": 3
            },
            {
                "name": "multi_app_comprehensive",
                "description": "4 apps, 5 screenshots each, all strategies",
                "apps": [
                    "cryptoapp.apk",
                    "byrne.utilities.hashpass_2.apk",
                    "com.hwloc.lstopo_271.apk",
                    "org.secuso.privacyfriendlyludo_5.apk"
                ],
                "strategies": ["baseline", "coordinate_validation", "enhanced_description",
                              "element_priority", "spinner_focused"],
                "samples_per_app": 5
            }
        ]
        return configs

    def run_incremental_test(self, start_level: int = 0, stop_at_failure: bool = True) -> Dict[str, Any]:
        """
        Run incremental validation tests.

        Args:
            start_level: Which test level to start from (0-based)
            stop_at_failure: Whether to stop if a test level fails

        Returns:
            Results from all test levels
        """
        configs = self.get_test_configurations()
        all_results = {}

        print("\n🚀 Starting Incremental Validation")
        print("=" * 60)

        for i, config in enumerate(configs[start_level:], start_level):
            level_name = f"Level_{i}_{config['name']}"

            print(f"\n📊 LEVEL {i}: {config['description']}")
            print("-" * 40)

            try:
                # Run validation for this level
                results = self.validator.validate_dataset(
                    dataset_path=self.dataset_path,
                    apps=config["apps"],
                    strategies=config["strategies"],
                    samples_per_app=config["samples_per_app"]
                )

                # Add configuration info to results
                results["config"] = config
                results["level"] = i
                all_results[level_name] = results

                # Print level summary
                self.print_level_summary(i, config, results)

                # Save intermediate results
                self.save_level_results(level_name, results)

                # Check if we should continue
                if self.should_stop(results) and stop_at_failure:
                    print(f"\n⚠️ Stopping at level {i} due to poor results")
                    break

            except Exception as e:
                print(f"\n❌ Level {i} failed with error: {e}")
                all_results[level_name] = {
                    "config": config,
                    "level": i,
                    "error": str(e),
                    "success": False
                }

                if stop_at_failure:
                    print(f"⚠️ Stopping due to failure at level {i}")
                    break

        return all_results

    def print_level_summary(self, level: int, config: Dict[str, Any], results: Dict[str, Any]):
        """Print summary for a test level."""
        print(f"\n📈 Level {level} Results:")

        if "strategy_stats" in results:
            for strategy, stats in results["strategy_stats"].items():
                print(f"  {strategy}: {stats['hit_rate']:.1f}% hit rate, "
                      f"{stats['avg_distance']:.1f}px avg distance")

            if "best_strategy" in results:
                print(f"  🏆 Best: {results['best_strategy']['name']} "
                      f"({results['best_strategy']['hit_rate']:.1f}%)")
        else:
            print("  ❌ No strategy statistics available")

        # Show test counts
        total_tests = results.get("total_tests", 0)
        successful_tests = results.get("successful_tests", 0)
        print(f"  📊 Tests: {successful_tests}/{total_tests} successful")

    def should_stop(self, results: Dict[str, Any]) -> bool:
        """
        Determine if testing should stop based on results quality.

        Args:
            results: Results from current level

        Returns:
            True if results are too poor to continue
        """
        # Stop if no successful tests
        if results.get("successful_tests", 0) == 0:
            return True

        # Stop if best strategy has very low hit rate
        if "best_strategy" in results:
            best_hit_rate = results["best_strategy"]["hit_rate"]
            if best_hit_rate < 20:  # Less than 20% hit rate
                return True

        return False

    def save_level_results(self, level_name: str, results: Dict[str, Any]):
        """Save results for a specific level."""
        output_file = f"incremental_{level_name}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"  💾 Level results saved to: {output_file}")

    def analyze_progression(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze how performance changes across test levels.

        Args:
            all_results: Results from all levels

        Returns:
            Analysis of performance progression
        """
        progression = []

        for level_name, results in all_results.items():
            if "strategy_stats" in results and "best_strategy" in results:
                level_data = {
                    "level": results.get("level", -1),
                    "config_name": results["config"]["name"],
                    "total_tests": results.get("total_tests", 0),
                    "successful_tests": results.get("successful_tests", 0),
                    "best_hit_rate": results["best_strategy"]["hit_rate"],
                    "best_strategy_name": results["best_strategy"]["name"]
                }
                progression.append(level_data)

        # Sort by level
        progression.sort(key=lambda x: x["level"])

        return {
            "progression": progression,
            "trend_analysis": self.analyze_trends(progression)
        }

    def analyze_trends(self, progression: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in the progression data."""
        if len(progression) < 2:
            return {"message": "Not enough data points for trend analysis"}

        # Analyze hit rate trend
        hit_rates = [p["best_hit_rate"] for p in progression]

        # Simple trend analysis
        improving = sum(1 for i in range(1, len(hit_rates)) if hit_rates[i] > hit_rates[i-1])
        declining = sum(1 for i in range(1, len(hit_rates)) if hit_rates[i] < hit_rates[i-1])

        trend = "stable"
        if improving > declining:
            trend = "improving"
        elif declining > improving:
            trend = "declining"

        return {
            "hit_rate_trend": trend,
            "best_hit_rate": max(hit_rates),
            "worst_hit_rate": min(hit_rates),
            "average_hit_rate": sum(hit_rates) / len(hit_rates),
            "total_levels_tested": len(progression)
        }


def main():
    """Run incremental validation tests."""
    print("🧪 Incremental Coordinate Validation for Gemma3-tools")
    print("=" * 60)

    # Initialize validator
    validator = IncrementalValidator()

    # Run incremental tests
    all_results = validator.run_incremental_test(
        start_level=0,  # Start from minimal test
        stop_at_failure=False  # Continue even if some levels fail
    )

    # Analyze progression
    progression_analysis = validator.analyze_progression(all_results)

    # Save final results
    final_results = {
        "all_levels": all_results,
        "progression_analysis": progression_analysis
    }

    output_file = "incremental_validation_complete.json"
    with open(output_file, 'w') as f:
        json.dump(final_results, f, indent=2)

    # Print final summary
    print("\n" + "=" * 60)
    print("🏁 INCREMENTAL VALIDATION COMPLETE")
    print("=" * 60)

    if "trend_analysis" in progression_analysis:
        trends = progression_analysis["trend_analysis"]
        print(f"📊 Performance Trend: {trends.get('hit_rate_trend', 'unknown')}")
        print(f"🎯 Best Hit Rate: {trends.get('best_hit_rate', 0):.1f}%")
        print(f"📉 Worst Hit Rate: {trends.get('worst_hit_rate', 0):.1f}%")
        print(f"📊 Average Hit Rate: {trends.get('average_hit_rate', 0):.1f}%")
        print(f"🧪 Levels Tested: {trends.get('total_levels_tested', 0)}")

    print(f"\n💾 Complete results saved to: {output_file}")

    return final_results


if __name__ == "__main__":
    main()
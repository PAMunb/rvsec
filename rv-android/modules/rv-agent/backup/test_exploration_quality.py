"""
Comprehensive Exploration Quality Validator.

Tests agent exploration quality using offline validation with detailed metrics:
- Action distribution and diversity
- Element interaction patterns
- Stuck/loop detection
- Screen navigation analysis
- Token usage consistency
"""

import json
import logging
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

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


class ExplorationQualityAnalyzer:
    """
    Analyzes exploration quality beyond basic metrics.

    Detects:
    - Stuck patterns (same action/element/screen repeatedly)
    - Low diversity (narrow action distribution)
    - Poor coverage (few elements explored)
    - Loop detection (circular navigation)
    """

    def __init__(self, metrics: dict, device_actions: List[dict]):
        self.metrics = metrics
        self.device_actions = device_actions
        self.issues = []
        self.warnings = []

    def analyze(self) -> dict:
        """Run complete quality analysis."""

        results = {
            "diversity_score": self._calculate_diversity_score(),
            "stuck_detection": self._detect_stuck_patterns(),
            "element_interaction": self._analyze_element_interactions(),
            "screen_navigation": self._analyze_screen_navigation(),
            "action_streaks": self._detect_action_streaks(),
            "quality_grade": None,  # Will be calculated
            "issues": self.issues,
            "warnings": self.warnings
        }

        # Calculate overall quality grade
        results["quality_grade"] = self._calculate_quality_grade(results)

        return results

    def _calculate_diversity_score(self) -> dict:
        """
        Calculate Shannon entropy for action distribution.

        Higher entropy = better diversity
        """
        actions_by_type = self.metrics.get("actions", {}).get("by_type", {})

        if not actions_by_type:
            return {"entropy": 0.0, "normalized": 0.0, "rating": "NONE"}

        total = sum(actions_by_type.values())
        if total == 0:
            return {"entropy": 0.0, "normalized": 0.0, "rating": "NONE"}

        # Shannon entropy
        entropy = 0.0
        for count in actions_by_type.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        # Normalize to 0-1 (max entropy = log2(n) where n = number of action types)
        max_entropy = math.log2(len(actions_by_type)) if len(actions_by_type) > 1 else 1.0
        normalized = entropy / max_entropy if max_entropy > 0 else 0.0

        # Rating
        if normalized > 0.7:
            rating = "EXCELLENT"
        elif normalized > 0.5:
            rating = "GOOD"
        elif normalized > 0.3:
            rating = "FAIR"
        else:
            rating = "POOR"
            self.warnings.append(f"Low action diversity (entropy={normalized:.2f})")

        return {
            "entropy": round(entropy, 3),
            "normalized": round(normalized, 3),
            "max_possible": round(max_entropy, 3),
            "rating": rating,
            "distribution": {
                action: f"{(count/total)*100:.1f}%"
                for action, count in actions_by_type.items()
            }
        }

    def _detect_stuck_patterns(self) -> dict:
        """
        Detect if agent is stuck in repetitive patterns.
        """
        stuck_patterns = {
            "same_action_streak": 0,
            "same_element_streak": 0,
            "same_screen_revisits": 0,
            "is_stuck": False
        }

        if not self.device_actions:
            return stuck_patterns

        # Same action streak
        max_streak = 1
        current_streak = 1
        for i in range(1, len(self.device_actions)):
            if (self.device_actions[i]['action_type'] ==
                self.device_actions[i-1]['action_type']):
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1

        stuck_patterns["same_action_streak"] = max_streak

        # Same element streak
        max_elem_streak = 1
        current_elem_streak = 1
        for i in range(1, len(self.device_actions)):
            elem1 = self.device_actions[i].get('element')
            elem0 = self.device_actions[i-1].get('element')
            if elem1 and elem0 and elem1 == elem0:
                current_elem_streak += 1
                max_elem_streak = max(max_elem_streak, current_elem_streak)
            else:
                current_elem_streak = 1

        stuck_patterns["same_element_streak"] = max_elem_streak

        # Screen revisit analysis
        screen_visits = self.metrics.get("exploration", {}).get("screen_visits", {})
        if screen_visits:
            max_revisits = max(screen_visits.values())
            stuck_patterns["same_screen_revisits"] = max_revisits

        # Determine if stuck
        if (max_streak >= 5 or max_elem_streak >= 3 or
            stuck_patterns["same_screen_revisits"] >= 10):
            stuck_patterns["is_stuck"] = True
            self.issues.append(
                f"Agent appears stuck: {max_streak} action streak, "
                f"{max_elem_streak} element streak, "
                f"{stuck_patterns['same_screen_revisits']} max screen revisits"
            )

        return stuck_patterns

    def _analyze_element_interactions(self) -> dict:
        """
        Analyze which types of elements are being interacted with.
        """
        element_interactions = defaultdict(int)
        unique_elements = set()

        for action in self.device_actions:
            if action.get('valid') and action.get('element'):
                elem_str = action['element']
                unique_elements.add(elem_str)

                # Extract element type from string like "android.widget.Button[...]"
                if 'android.widget.' in elem_str:
                    elem_type = elem_str.split('android.widget.')[1].split('[')[0]
                    element_interactions[elem_type] += 1

        total_interactions = sum(element_interactions.values())

        # Check if too concentrated on one element type
        if element_interactions and total_interactions > 0:
            max_type, max_count = max(element_interactions.items(), key=lambda x: x[1])
            concentration = (max_count / total_interactions) * 100

            if concentration > 80:
                self.warnings.append(
                    f"High concentration on {max_type}: {concentration:.1f}% of interactions"
                )

        return {
            "unique_elements_clicked": len(unique_elements),
            "element_type_distribution": dict(element_interactions),
            "total_valid_interactions": total_interactions
        }

    def _analyze_screen_navigation(self) -> dict:
        """
        Analyze screen navigation patterns.
        """
        exploration = self.metrics.get("exploration", {})
        unique_screens = exploration.get("unique_screens", 0)
        screen_visits = exploration.get("screen_visits", {})
        total_visits = sum(screen_visits.values())

        revisit_rate = exploration.get("revisit_rate", 0.0)

        # Calculate exploration efficiency
        efficiency = (unique_screens / total_visits * 100) if total_visits > 0 else 0.0

        # Rating
        if efficiency > 60:
            rating = "EXCELLENT"
        elif efficiency > 40:
            rating = "GOOD"
        elif efficiency > 20:
            rating = "FAIR"
        else:
            rating = "POOR"
            if unique_screens <= 2 and total_visits > 10:
                self.issues.append(
                    f"Poor exploration: only {unique_screens} unique screens "
                    f"in {total_visits} visits"
                )

        return {
            "unique_screens": unique_screens,
            "total_visits": total_visits,
            "revisit_rate": round(revisit_rate * 100, 1),
            "exploration_efficiency": round(efficiency, 1),
            "rating": rating
        }

    def _detect_action_streaks(self) -> dict:
        """
        Detect consecutive sequences of same actions.
        """
        if not self.device_actions:
            return {"max_streak": 0, "streaks": []}

        streaks = []
        current_action = None
        current_streak_start = 0
        current_streak_count = 0

        for i, action in enumerate(self.device_actions):
            action_type = action['action_type']

            if action_type == current_action:
                current_streak_count += 1
            else:
                # Save previous streak if it was significant
                if current_streak_count >= 3:
                    streaks.append({
                        "action": current_action,
                        "count": current_streak_count,
                        "start_idx": current_streak_start,
                        "end_idx": i - 1
                    })

                current_action = action_type
                current_streak_start = i
                current_streak_count = 1

        # Don't forget last streak
        if current_streak_count >= 3:
            streaks.append({
                "action": current_action,
                "count": current_streak_count,
                "start_idx": current_streak_start,
                "end_idx": len(self.device_actions) - 1
            })

        max_streak = max([s['count'] for s in streaks]) if streaks else 0

        return {
            "max_streak": max_streak,
            "streaks": streaks
        }

    def _calculate_quality_grade(self, results: dict) -> str:
        """
        Calculate overall quality grade (A-F).
        """
        score = 0.0

        # Diversity (30%)
        diversity_normalized = results["diversity_score"]["normalized"]
        score += diversity_normalized * 30

        # Navigation efficiency (30%)
        nav_rating = results["screen_navigation"]["rating"]
        nav_score = {
            "EXCELLENT": 1.0,
            "GOOD": 0.75,
            "FAIR": 0.5,
            "POOR": 0.25,
            "NONE": 0.0
        }.get(nav_rating, 0.0)
        score += nav_score * 30

        # Not stuck (20%)
        if not results["stuck_detection"]["is_stuck"]:
            score += 20

        # Element diversity (20%)
        elem_interactions = results["element_interaction"]["unique_elements_clicked"]
        elem_score = min(elem_interactions / 10.0, 1.0)  # Normalize to max 10 elements
        score += elem_score * 20

        # Convert to grade
        if score >= 90:
            return "A (Excellent)"
        elif score >= 80:
            return "B (Good)"
        elif score >= 70:
            return "C (Fair)"
        elif score >= 60:
            return "D (Poor)"
        else:
            return "F (Failing)"


def run_comprehensive_validation(
    dataset_dir: Path,
    apps: List[str],
    max_iterations: int = 30,
    output_dir: Path = Path("exploration_quality_results")
) -> dict:
    """
    Run comprehensive validation across multiple apps.
    """
    logger.info("=" * 80)
    logger.info("🧪 COMPREHENSIVE EXPLORATION QUALITY TEST")
    logger.info("=" * 80)
    logger.info(f"Apps: {len(apps)}")
    logger.info(f"Max iterations: {max_iterations}")
    logger.info(f"Output: {output_dir}")
    logger.info("")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Create runner
    runner = ValidationRunner(
        dataset_dir=dataset_dir,
        max_iterations=max_iterations,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(728, 1288)
    )

    all_results = {}

    for idx, app_name in enumerate(apps, 1):
        logger.info("\n" + "=" * 80)
        logger.info(f"📱 APP {idx}/{len(apps)}: {app_name}")
        logger.info("=" * 80)

        try:
            # Run validation
            metrics = runner.validate_app(
                app_name=app_name,
                strategy="dfs",
                output_path=output_dir / f"{app_name}_metrics.json"
            )

            # Get device actions
            device_actions = metrics.get('device_actions', {}).get('actions', [])

            # Analyze quality
            analyzer = ExplorationQualityAnalyzer(metrics, device_actions)
            quality_analysis = analyzer.analyze()

            # Combine results
            all_results[app_name] = {
                "basic_metrics": metrics,
                "quality_analysis": quality_analysis
            }

            # Print quality summary
            logger.info("\n" + "-" * 60)
            logger.info(f"📊 QUALITY ANALYSIS: {app_name}")
            logger.info("-" * 60)
            logger.info(f"Overall Grade: {quality_analysis['quality_grade']}")
            logger.info(f"Diversity Score: {quality_analysis['diversity_score']['rating']} "
                       f"(entropy={quality_analysis['diversity_score']['normalized']})")
            logger.info(f"Navigation: {quality_analysis['screen_navigation']['rating']} "
                       f"({quality_analysis['screen_navigation']['unique_screens']} screens, "
                       f"{quality_analysis['screen_navigation']['exploration_efficiency']}% efficiency)")
            logger.info(f"Stuck: {'YES ⚠️' if quality_analysis['stuck_detection']['is_stuck'] else 'NO ✅'}")
            logger.info(f"Unique Elements: {quality_analysis['element_interaction']['unique_elements_clicked']}")

            if quality_analysis['issues']:
                logger.warning(f"\n🚨 ISSUES ({len(quality_analysis['issues'])}):")
                for issue in quality_analysis['issues']:
                    logger.warning(f"  - {issue}")

            if quality_analysis['warnings']:
                logger.warning(f"\n⚠️  WARNINGS ({len(quality_analysis['warnings'])}):")
                for warning in quality_analysis['warnings']:
                    logger.warning(f"  - {warning}")

        except Exception as e:
            logger.error(f"❌ Failed to validate {app_name}: {e}", exc_info=True)
            all_results[app_name] = {"error": str(e)}

    # Save comprehensive summary
    summary_path = output_dir / "comprehensive_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    # Print aggregate statistics
    print_aggregate_stats(all_results)

    logger.info(f"\n💾 Results saved to: {output_dir}")
    logger.info(f"   Summary: {summary_path}")

    return all_results


def print_aggregate_stats(results: dict):
    """Print aggregate statistics across all apps."""
    logger.info("\n" + "=" * 80)
    logger.info("📈 AGGREGATE STATISTICS")
    logger.info("=" * 80)

    successful = [r for r in results.values() if "quality_analysis" in r]

    if not successful:
        logger.warning("No successful validations to analyze")
        return

    # Grade distribution
    grades = [r["quality_analysis"]["quality_grade"] for r in successful]
    grade_counts = Counter(grades)

    logger.info(f"\n🎓 Grade Distribution:")
    for grade in sorted(grade_counts.keys()):
        count = grade_counts[grade]
        percentage = (count / len(successful)) * 100
        logger.info(f"  {grade}: {count} apps ({percentage:.1f}%)")

    # Stuck detection
    stuck_count = sum(1 for r in successful
                     if r["quality_analysis"]["stuck_detection"]["is_stuck"])
    logger.info(f"\n🔒 Stuck Detection:")
    logger.info(f"  Stuck apps: {stuck_count}/{len(successful)} "
               f"({stuck_count/len(successful)*100:.1f}%)")

    # Average diversity
    avg_diversity = sum(r["quality_analysis"]["diversity_score"]["normalized"]
                       for r in successful) / len(successful)
    logger.info(f"\n🎨 Average Diversity Score: {avg_diversity:.3f}")

    # Token usage consistency
    avg_tokens = [r["basic_metrics"]["llm"]["avg_tokens_per_iteration"]
                  for r in successful]
    min_tokens = min(avg_tokens)
    max_tokens = max(avg_tokens)
    mean_tokens = sum(avg_tokens) / len(avg_tokens)

    logger.info(f"\n🎯 Token Usage:")
    logger.info(f"  Min: {min_tokens:.0f} tokens/iter")
    logger.info(f"  Max: {max_tokens:.0f} tokens/iter")
    logger.info(f"  Mean: {mean_tokens:.0f} tokens/iter")
    logger.info(f"  All under 3500: {'YES ✅' if max_tokens < 3500 else 'NO ❌'}")


def discover_all_apps(dataset_dir: Path) -> List[str]:
    """
    Auto-discover all available apps in the dataset.

    Returns list of app directories (*.apk format).
    """
    apps = []
    for item in dataset_dir.iterdir():
        if item.is_dir() and item.name.endswith('.apk'):
            apps.append(item.name)
    return sorted(apps)


def main():
    """Main test function."""
    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

    # Auto-discover ALL available apps in dataset
    test_apps = discover_all_apps(dataset_dir)

    logger.info(f"Auto-discovered {len(test_apps)} apps in dataset:")
    for app in test_apps:
        logger.info(f"  - {app}")
    logger.info("")

    results = run_comprehensive_validation(
        dataset_dir=dataset_dir,
        apps=test_apps,
        max_iterations=30
    )

    # Determine success
    successful = sum(1 for r in results.values() if "quality_analysis" in r)
    return successful == len(test_apps)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

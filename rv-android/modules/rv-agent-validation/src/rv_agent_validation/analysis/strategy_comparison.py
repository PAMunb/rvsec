#!/usr/bin/env python3
"""
Strategy comparison analysis for validation experiments.

Provides comprehensive analysis including:
- Composite score rankings
- Descriptive statistics by strategy
- Statistical significance tests (Kruskal-Wallis, Wilcoxon)
- Effect size calculations (Cliff's Delta)
- Per-app breakdown
- Strategy recommendation

Usage:
    python strategy_comparison.py --experiment-dir results/experiment_20260106/
    python strategy_comparison.py --results-file results.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from statistics import CompositeScorer, DescriptiveStats, EffectSize, SignificanceTests

# Key metrics for analysis
KEY_METRICS = [
    "states_discovered",
    "ui_coverage_percentage",
    "mop_methods_reached",
    "states_per_action",
    "action_validity_rate",
    "total_actions",
]

DEFAULT_STRATEGIES = ["rvagent", "dfs", "bfs", "greedy"]


class StrategyComparison:
    """
    Comprehensive strategy comparison analysis.

    Combines composite scoring, statistical tests, and effect sizes
    to provide actionable strategy recommendations.
    """

    def __init__(
        self, results: List[Dict[str, Any]], strategies: Optional[List[str]] = None
    ):
        """
        Initialize comparison analysis.

        Args:
            results: List of run results.
            strategies: List of strategy names to compare.
        """
        self.results = [r for r in results if r.get("status") == "completed"]
        self.strategies = strategies or self._detect_strategies()
        self.scorer = CompositeScorer()

    def _detect_strategies(self) -> List[str]:
        """Detect strategies present in results."""
        strategies = set()
        for r in self.results:
            if "strategy" in r:
                strategies.add(r["strategy"])
        return sorted(strategies)

    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Run complete analysis.

        Returns:
            Dictionary with all analysis results.
        """
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "n_results": len(self.results),
            "n_strategies": len(self.strategies),
            "strategies": self.strategies,
        }

        # 1. Composite score rankings
        analysis["composite_rankings"] = self._analyze_composite_scores()

        # 2. Descriptive statistics
        analysis["descriptive_stats"] = self._analyze_descriptive_stats()

        # 3. Statistical significance
        analysis["significance"] = self._analyze_significance()

        # 4. Effect sizes
        analysis["effect_sizes"] = self._analyze_effect_sizes()

        # 5. Per-app breakdown
        analysis["per_app"] = self._analyze_per_app()

        # 6. Recommendation
        analysis["recommendation"] = self.scorer.recommend_best_strategy(self.results)

        return analysis

    def _analyze_composite_scores(self) -> Dict[str, Any]:
        """Analyze composite scores."""
        rankings = self.scorer.rank_strategies(self.results)
        summary = self.scorer.get_strategy_summary(self.results)

        return {
            "rankings": [
                {
                    "rank": i + 1,
                    "strategy": strategy,
                    "composite_score": score,
                    "components": components,
                }
                for i, (strategy, score, components) in enumerate(rankings)
            ],
            "summary": summary,
        }

    def _analyze_descriptive_stats(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Analyze descriptive statistics for key metrics."""
        return DescriptiveStats.summary_table(self.results, KEY_METRICS)

    def _analyze_significance(self) -> Dict[str, Any]:
        """Analyze statistical significance."""
        significance = {}

        for metric in KEY_METRICS:
            significance[metric] = SignificanceTests.full_analysis(
                self.results, metric, self.strategies
            )

        return significance

    def _analyze_effect_sizes(self) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze effect sizes."""
        effect_sizes = {}

        for metric in KEY_METRICS:
            effect_sizes[metric] = EffectSize.all_pairwise(
                self.results, metric, self.strategies
            )

        return effect_sizes

    def _analyze_per_app(self) -> Dict[str, Dict[str, Any]]:
        """Analyze results per app."""
        by_app: Dict[str, List[Dict[str, Any]]] = {}

        for result in self.results:
            # Support both "app" and "package_name" fields
            app = result.get("app") or result.get("package_name", "unknown")
            if app not in by_app:
                by_app[app] = []
            by_app[app].append(result)

        analysis = {}
        for app, app_results in by_app.items():
            # Best strategy per app
            rankings = self.scorer.rank_strategies(app_results)
            best = rankings[0] if rankings else None

            # Stats per strategy
            strategy_stats = {}
            for strategy in self.strategies:
                strat_results = [
                    r for r in app_results if r.get("strategy") == strategy
                ]
                if strat_results:
                    scores = [self.scorer.calculate_score(r) for r in strat_results]
                    strategy_stats[strategy] = {
                        "n_runs": len(strat_results),
                        "mean_score": round(sum(scores) / len(scores), 2),
                        "scores": scores,
                    }

            analysis[app] = {
                "n_runs": len(app_results),
                "best_strategy": best[0] if best else None,
                "best_score": best[1] if best else None,
                "by_strategy": strategy_stats,
            }

        return analysis

    def print_report(self):
        """Print formatted analysis report."""
        analysis = self.run_full_analysis()

        print("\n" + "=" * 80)
        print("STRATEGY COMPARISON REPORT")
        print("=" * 80)
        print(f"Generated: {analysis['timestamp']}")
        print(f"Total runs: {analysis['n_results']}")
        print(f"Strategies: {', '.join(analysis['strategies'])}")

        # 1. Composite Score Rankings
        print("\n" + "-" * 80)
        print("1. COMPOSITE SCORE RANKINGS")
        print("-" * 80)
        print(
            f"{'Rank':<6}{'Strategy':<15}{'Score':<10}{'Coverage':<12}{'MOP':<10}{'Efficiency':<12}{'Robust':<10}"
        )
        print("-" * 80)
        for entry in analysis["composite_rankings"]["rankings"]:
            comp = entry["components"]
            print(
                f"{entry['rank']:<6}"
                f"{entry['strategy']:<15}"
                f"{entry['composite_score']:<10.2f}"
                f"{comp['coverage_score']:<12.2f}"
                f"{comp['mop_score']:<10.2f}"
                f"{comp['efficiency_score']:<12.2f}"
                f"{comp['robustness_score']:<10.2f}"
            )

        # 2. Descriptive Statistics
        print("\n" + "-" * 80)
        print("2. DESCRIPTIVE STATISTICS (Mean +/- Std)")
        print("-" * 80)

        for metric in KEY_METRICS:
            print(f"\n  {metric}:")
            stats = analysis["descriptive_stats"].get(metric, {})
            for strategy in self.strategies:
                if strategy in stats:
                    s = stats[strategy]
                    print(
                        f"    {strategy:<12}: {s['mean']:>8.2f} +/- {s['std']:<8.2f} (n={s['n']})"
                    )

        # 3. Statistical Significance
        print("\n" + "-" * 80)
        print("3. STATISTICAL SIGNIFICANCE")
        print("-" * 80)

        for metric in [
            "states_discovered",
            "ui_coverage_percentage",
            "mop_methods_reached",
        ]:
            sig = analysis["significance"].get(metric, {})
            kw = sig.get("kruskal_wallis", {})
            print(f"\n  {metric}:")
            if "error" not in kw:
                sig_marker = "*" if kw.get("significant") else ""
                print(
                    f"    Kruskal-Wallis: H={kw.get('H_statistic', 'N/A')}, p={kw.get('p_value', 'N/A')}{sig_marker}"
                )

            pairwise = sig.get("pairwise_wilcoxon", [])
            significant_pairs = [p for p in pairwise if p.get("significant_bonferroni")]
            if significant_pairs:
                print("    Significant pairs (Bonferroni):")
                for pair in significant_pairs:
                    print(f"      - {pair['comparison']}: p={pair['p_value']}")

        # 4. Effect Sizes
        print("\n" + "-" * 80)
        print("4. EFFECT SIZES (Cliff's Delta)")
        print("-" * 80)

        metric = "states_discovered"
        effects = analysis["effect_sizes"].get(metric, [])
        print(f"\n  {metric}:")
        for effect in effects:
            delta = effect.get("cliff_delta", 0)
            interp = effect.get("cliff_interpretation", "?")
            direction = ">" if delta > 0 else "<" if delta < 0 else "="
            print(
                f"    {effect['comparison']}: delta={delta:.3f} ({interp}) [{direction}]"
            )

        # 5. Per-App Best Strategy
        print("\n" + "-" * 80)
        print("5. PER-APP ANALYSIS")
        print("-" * 80)
        print(f"{'App':<50}{'Best Strategy':<15}{'Score':<10}")
        print("-" * 80)
        for app, app_data in analysis["per_app"].items():
            app_short = app[:48] + ".." if len(app) > 50 else app
            print(
                f"{app_short:<50}"
                f"{app_data['best_strategy'] or 'N/A':<15}"
                f"{app_data['best_score'] or 0:.2f}"
            )

        # Strategy wins count
        wins = {}
        for app_data in analysis["per_app"].values():
            best = app_data.get("best_strategy")
            if best:
                wins[best] = wins.get(best, 0) + 1

        print("\n  Strategy Win Counts:")
        for strategy, count in sorted(wins.items(), key=lambda x: -x[1]):
            print(f"    {strategy}: {count} apps")

        # 6. Recommendation
        print("\n" + "-" * 80)
        print("6. RECOMMENDATION")
        print("-" * 80)
        rec = analysis["recommendation"]
        if rec.get("recommendation"):
            print(f"\n  BEST STRATEGY: {rec['recommendation']}")
            print(f"  Composite Score: {rec['composite_score']:.2f}")
            print(f"  Confidence: {rec.get('confidence', 'N/A')}")
            if rec.get("second_place"):
                print(
                    f"  Second Place: {rec['second_place']} (gap: {rec.get('gap_to_second', 0):.2f})"
                )
        else:
            print(f"\n  {rec.get('reason', 'No recommendation available')}")

        print("\n" + "=" * 80)

        return analysis

    def save_results(self, output_path: Path):
        """
        Save analysis results to JSON file.

        Args:
            output_path: Path for output file.
        """
        analysis = self.run_full_analysis()
        with open(output_path, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"\nResults saved to: {output_path}")


def load_results(experiment_dir: Path) -> List[Dict[str, Any]]:
    """
    Load results from experiment directory.

    Args:
        experiment_dir: Path to experiment directory.

    Returns:
        List of run results.
    """
    results = []

    # Look for results.json or individual run files
    results_file = experiment_dir / "results.json"
    if results_file.exists():
        with open(results_file) as f:
            data = json.load(f)
            if isinstance(data, list):
                results = data
            elif isinstance(data, dict) and "results" in data:
                results = data["results"]

    # Also check for individual run files in runs/ subdirectory
    runs_dir = experiment_dir / "runs"
    if runs_dir.exists():
        for run_file in runs_dir.glob("*.json"):
            try:
                with open(run_file) as f:
                    result = json.load(f)
                    # Check if already in results
                    run_id = result.get("run_id", "")
                    if not any(r.get("run_id") == run_id for r in results):
                        results.append(result)
            except Exception:
                continue

    # Also check for run_*.json files in experiment directory (legacy format)
    for run_file in experiment_dir.glob("run_*.json"):
        try:
            with open(run_file) as f:
                result = json.load(f)
                # Check if already in results
                run_id = result.get("run_id", "")
                if not any(r.get("run_id") == run_id for r in results):
                    results.append(result)
        except Exception:
            continue

    return results


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze strategy validation experiment results"
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--experiment-dir", type=str, help="Path to experiment results directory"
    )
    source_group.add_argument(
        "--results-file", type=str, help="Path to results JSON file"
    )

    parser.add_argument(
        "--strategies", type=str, help="Comma-separated list of strategies to compare"
    )
    parser.add_argument(
        "--output", "-o", type=str, help="Output file for analysis results (JSON)"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress printed output"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Load results
    if args.experiment_dir:
        experiment_dir = Path(args.experiment_dir)
        if not experiment_dir.exists():
            print(f"Error: Directory not found: {experiment_dir}")
            sys.exit(1)
        results = load_results(experiment_dir)
    else:
        results_file = Path(args.results_file)
        if not results_file.exists():
            print(f"Error: File not found: {results_file}")
            sys.exit(1)
        with open(results_file) as f:
            data = json.load(f)
            results = data if isinstance(data, list) else data.get("results", [])

    if not results:
        print("Error: No results found")
        sys.exit(1)

    print(f"Loaded {len(results)} results")

    # Parse strategies
    strategies = None
    if args.strategies:
        strategies = [s.strip() for s in args.strategies.split(",")]

    # Run analysis
    comparison = StrategyComparison(results, strategies)

    if not args.quiet:
        analysis = comparison.print_report()
    else:
        analysis = comparison.run_full_analysis()

    # Save if output specified
    if args.output:
        comparison.save_results(Path(args.output))
    elif args.experiment_dir:
        # Default output in experiment dir
        output_path = Path(args.experiment_dir) / "analysis_results.json"
        comparison.save_results(output_path)

    return analysis


if __name__ == "__main__":
    main()

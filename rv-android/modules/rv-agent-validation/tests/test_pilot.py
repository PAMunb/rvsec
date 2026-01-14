#!/usr/bin/env python3
"""
Pilot test for validation framework.

Tests statistics and reports modules with synthetic data
before running the full experiment.
"""

import sys
import json
import random
import tempfile
from pathlib import Path

# Add validation modules to path
sys.path.insert(0, str(Path(__file__).parent))

from statistics import DescriptiveStats, SignificanceTests, EffectSize
from reports import JSONExporter, CSVExporter, LaTeXExporter


def generate_synthetic_results(n_apps: int = 5, n_strategies: int = 4, n_reps: int = 3):
    """Generate synthetic results for testing."""
    strategies = ["rvagent", "dfs", "bfs", "greedy"][:n_strategies]
    apps = [f"app_{i}" for i in range(n_apps)]

    results = []

    # RVAgent should perform better on average
    strategy_baselines = {
        "rvagent": {"coverage": 75, "states": 50, "actions": 200},
        "dfs": {"coverage": 60, "states": 40, "actions": 180},
        "bfs": {"coverage": 55, "states": 35, "actions": 170},
        "greedy": {"coverage": 65, "states": 45, "actions": 190},
    }

    for app in apps:
        for strategy in strategies:
            baseline = strategy_baselines[strategy]
            for rep in range(n_reps):
                result = {
                    "run_id": f"{app}_{strategy}_{rep}",
                    "app": app,
                    "strategy": strategy,
                    "repetition": rep,
                    "seed": 1000 + rep,
                    "status": "completed",
                    "coverage": baseline["coverage"] + random.gauss(0, 10),
                    "states_explored": int(baseline["states"] + random.gauss(0, 8)),
                    "actions_executed": int(baseline["actions"] + random.gauss(0, 20)),
                    "mop_events": random.randint(5, 50),
                    "app_crashes": random.randint(0, 3),
                }
                results.append(result)

    return results, strategies


def test_descriptive_stats():
    """Test descriptive statistics."""
    print("\n=== Testing Descriptive Statistics ===")

    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    stats = DescriptiveStats.calculate(values)

    print(f"Values: {values}")
    print(f"Mean: {stats['mean']}")
    print(f"Std: {stats['std']}")
    print(f"Median: {stats['median']}")
    print(f"Min: {stats['min']}")
    print(f"Max: {stats['max']}")

    assert abs(stats['mean'] - 55.0) < 0.01, "Mean calculation error"
    assert abs(stats['median'] - 55.0) < 0.01, "Median calculation error"
    print("✓ Descriptive stats OK")


def test_significance_tests(results, strategies):
    """Test significance tests."""
    print("\n=== Testing Significance Tests ===")

    # Kruskal-Wallis
    kw_result = SignificanceTests.kruskal_wallis(results, "coverage", strategies)
    print(f"\nKruskal-Wallis for coverage:")
    print(f"  H-statistic: {kw_result.get('H_statistic', 'N/A')}")
    print(f"  p-value: {kw_result.get('p_value', 'N/A')}")
    print(f"  Significant: {kw_result.get('significant', 'N/A')}")

    # Pairwise Wilcoxon
    pairwise = SignificanceTests.all_pairwise(results, "coverage", strategies)
    print(f"\nPairwise Wilcoxon tests (coverage):")
    for pw in pairwise:
        if "error" in pw:
            print(f"  {pw['comparison']}: {pw['error']}")
        else:
            print(f"  {pw['comparison']}: p={pw.get('p_value', 'N/A')}, sig={pw.get('significant', 'N/A')}")

    print("✓ Significance tests OK")


def test_effect_sizes(results, strategies):
    """Test effect size calculations."""
    print("\n=== Testing Effect Sizes ===")

    # Cliff's Delta
    values_a = [r["coverage"] for r in results if r["strategy"] == "rvagent"]
    values_b = [r["coverage"] for r in results if r["strategy"] == "dfs"]

    delta, interp = EffectSize.cliffs_delta(values_a, values_b)
    print(f"\nCliff's Delta (rvagent vs dfs): {delta} ({interp})")

    # Cohen's d
    d, interp = EffectSize.cohens_d(values_a, values_b)
    print(f"Cohen's d (rvagent vs dfs): {d} ({interp})")

    # Full pairwise
    pairwise = EffectSize.all_pairwise(results, "coverage", strategies)
    print(f"\nAll pairwise effect sizes (coverage):")
    for pw in pairwise:
        print(f"  {pw['comparison']}: δ={pw['cliff_delta']} ({pw['cliff_interpretation']})")

    # Effect size matrix
    matrix = EffectSize.summary_matrix(results, "coverage", strategies)
    print(f"\nEffect size matrix (Cliff's Delta):")
    header = "        " + " ".join(f"{s:>8}" for s in strategies)
    print(header)
    for s1 in strategies:
        row = f"{s1:>8}" + " ".join(f"{matrix[s1].get(s2, 0):>8.3f}" for s2 in strategies)
        print(row)

    print("✓ Effect sizes OK")


def test_exporters(results, strategies):
    """Test report exporters."""
    print("\n=== Testing Report Exporters ===")

    metrics = ["coverage", "states_explored", "actions_executed"]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # CSV per-run
        csv_path = CSVExporter.export_per_run(
            results, tmpdir / "per_run.csv", metrics
        )
        print(f"✓ CSV per-run exported: {csv_path.name}")

        # Calculate summary for other exports
        summary = {}
        for strategy in strategies:
            strategy_results = [r for r in results if r["strategy"] == strategy]
            summary[strategy] = {}
            for metric in metrics:
                values = [r[metric] for r in strategy_results if r.get(metric) is not None]
                summary[strategy][metric] = DescriptiveStats.calculate(values)

        # CSV summary
        csv_summary_path = CSVExporter.export_summary(
            summary, tmpdir / "summary.csv", metrics
        )
        print(f"✓ CSV summary exported: {csv_summary_path.name}")

        # LaTeX summary table
        latex_path = LaTeXExporter.export_summary_table(
            summary, tmpdir / "summary.tex", metrics
        )
        print(f"✓ LaTeX summary exported: {latex_path.name}")

        # LaTeX effect size matrix
        matrix = EffectSize.summary_matrix(results, "coverage", strategies)
        latex_matrix_path = LaTeXExporter.export_effect_size_matrix(
            matrix, strategies, tmpdir / "effect_matrix.tex"
        )
        print(f"✓ LaTeX effect matrix exported: {latex_matrix_path.name}")

        # JSON aggregate
        config = {
            "experiment_id": "pilot_test",
            "experiment_name": "Pilot Test",
        }
        json_path = JSONExporter.export_aggregate(
            results, config, tmpdir / "aggregate.json", strategies, metrics
        )
        print(f"✓ JSON aggregate exported: {json_path.name}")

        # Verify JSON content
        with open(json_path) as f:
            data = json.load(f)
        print(f"  - Total runs: {data['experiment']['total_runs']}")
        print(f"  - Strategies: {list(data['summary_by_strategy'].keys())}")

        # Show sample LaTeX output
        print(f"\nSample LaTeX table ({latex_path.name}):")
        with open(latex_path) as f:
            for line in f.readlines()[:10]:
                print(f"  {line.rstrip()}")
        print("  ...")


def test_experiment_config():
    """Test experiment configuration."""
    print("\n=== Testing Experiment Configuration ===")

    from experiment import ExperimentConfig, RunConfig, SeedManager, CheckpointManager

    # Create config
    config = ExperimentConfig(
        experiment_id="test_001",
        experiment_name="Pilot Test",
        apps=["app_1", "app_2"],
        strategies=["rvagent", "dfs"],
        repetitions=2,
        timeout_seconds=300,
        base_seed=42,
    )

    # Generate runs
    runs = config.generate_runs()
    print(f"Generated {len(runs)} runs:")
    for run in runs[:4]:
        print(f"  - {run.run_id}: {run.app} / {run.strategy} / rep {run.repetition}")

    # Test seed manager
    seed_mgr = SeedManager(base_seed=42)
    seed1 = seed_mgr.get_seed("app_1", "rvagent", 0)
    seed2 = seed_mgr.get_seed("app_1", "rvagent", 1)
    seed3 = seed_mgr.get_seed("app_1", "rvagent", 0)  # Same as seed1

    print(f"\nSeed generation:")
    print(f"  app_1/rvagent/0: {seed1}")
    print(f"  app_1/rvagent/1: {seed2}")
    print(f"  app_1/rvagent/0 (repeat): {seed3}")
    assert seed1 == seed3, "Seed reproducibility error"
    assert seed1 != seed2, "Seeds should differ between repetitions"
    print("✓ Seed manager OK")

    # Test checkpoint manager
    with tempfile.TemporaryDirectory() as tmpdir:
        cp_mgr = CheckpointManager(Path(tmpdir) / "checkpoint.json")

        # Create RunConfig objects for testing
        run_1 = RunConfig(app="app_1", strategy="rvagent", repetition=1, seed=100, run_id="run_1")
        run_2 = RunConfig(app="app_1", strategy="dfs", repetition=1, seed=101, run_id="run_2")
        run_3 = RunConfig(app="app_2", strategy="rvagent", repetition=1, seed=102, run_id="run_3")
        run_4 = RunConfig(app="app_2", strategy="dfs", repetition=1, seed=103, run_id="run_4")
        run_5 = RunConfig(app="app_3", strategy="rvagent", repetition=1, seed=104, run_id="run_5")

        # Mark some as completed
        cp_mgr.mark_completed(run_1)
        cp_mgr.mark_completed(run_2)
        cp_mgr.mark_failed(run_3, "timeout")

        # Get pending
        all_runs = [run_1, run_2, run_3, run_4, run_5]
        pending = cp_mgr.get_pending_runs(all_runs)

        print(f"\nCheckpoint manager:")
        print(f"  Completed: {len(cp_mgr._completed_runs)}")
        print(f"  Failed: {len(cp_mgr._failed_runs)}")
        print(f"  Pending: {[r.run_id for r in pending]}")

        assert len(pending) == 3, f"Expected 3 pending, got {len(pending)}"
        print("✓ Checkpoint manager OK")

    print("✓ Experiment config OK")


def main():
    """Run all pilot tests."""
    print("=" * 60)
    print("PILOT TEST - Validation Framework")
    print("=" * 60)

    # Set seed for reproducibility
    random.seed(42)

    # Generate synthetic data
    print("\nGenerating synthetic test data...")
    results, strategies = generate_synthetic_results(n_apps=5, n_strategies=4, n_reps=3)
    print(f"Generated {len(results)} synthetic results")

    # Run tests
    test_descriptive_stats()
    test_significance_tests(results, strategies)
    test_effect_sizes(results, strategies)
    test_exporters(results, strategies)
    test_experiment_config()

    print("\n" + "=" * 60)
    print("ALL PILOT TESTS PASSED ✓")
    print("=" * 60)
    print("\nThe validation framework is ready for the full experiment.")
    print("Run with: python run_experiment.py --test")


if __name__ == "__main__":
    main()

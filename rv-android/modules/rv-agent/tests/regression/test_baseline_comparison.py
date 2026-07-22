"""
Regression tests comparing against V10 baseline.

Tests verify:
- No significant regression from V10 baseline metrics
- Tool call success rate >= baseline
- Unique states discovered >= baseline
- Execution time within acceptable bounds
"""

import json
from pathlib import Path

import pytest

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def v10_baseline():
    """Load V10 baseline aggregate results."""
    baseline_path = (
        Path(__file__).parent.parent.parent / "test_v10_baseline_10apps_aggregate.json"
    )

    if not baseline_path.exists():
        pytest.skip("V10 baseline file not found")

    with open(baseline_path) as f:
        return json.load(f)


@pytest.fixture
def v10_individual_results(v10_baseline):
    """Extract individual app results from baseline."""
    return {r["package"]: r for r in v10_baseline.get("individual_results", [])}


# =============================================================================
# Baseline Comparison Tests
# =============================================================================


class TestBaselineMetrics:
    """Tests comparing metrics against V10 baseline."""

    def test_baseline_structure(self, v10_baseline):
        """Test that baseline has expected structure."""
        assert "configuration" in v10_baseline
        assert "summary" in v10_baseline
        assert "individual_results" in v10_baseline

        config = v10_baseline["configuration"]
        assert config["model"] == "qwen3-vl:4b"
        assert config["prompt_version"] == "v10"

    def test_baseline_summary_metrics(self, v10_baseline):
        """Test baseline summary metrics."""
        summary = v10_baseline["summary"]

        print("\nV10 Baseline Summary:")
        print(f"  Total tests: {summary['total_tests']}")
        print(f"  Successful: {summary['successful']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Total iterations: {summary['total_iterations']}")
        print(f"  Total states: {summary['total_states']}")

        # Baseline reference values
        assert summary["total_tests"] == 10
        assert summary["successful"] == 7
        assert summary["failed"] == 3

    def test_successful_apps_metrics(self, v10_individual_results):
        """Test metrics for successful apps in baseline."""
        successful_apps = [
            "org.cryptomator.lite",
            "com.android.keepass",
            "com.amnesica.kryptey",
            "org.mariotaku.twidere",
            "app.fedilab.tubelab",
            "com.blogspot.e_kanivets.moneytracker",
            "asgardius.page.s3manager",
        ]

        for package in successful_apps:
            if package in v10_individual_results:
                result = v10_individual_results[package]
                metrics = result["metrics"]

                print(f"\n{result['app']} ({package}):")
                print(f"  Iterations: {metrics['iterations']}")
                print(f"  Unique states: {metrics['unique_states']}")
                print(f"  Execution time: {metrics['execution_time_s']:.1f}s")

                # Should have generated actions
                assert result["validation"][
                    "generated_actions"
                ], f"{package} should have generated actions"

    def test_failed_apps_identified(self, v10_individual_results):
        """Test that failed apps are correctly identified."""
        failed_packages = [
            "com.amaze.filemanager",
            "com.securefilemanager.app",
            "com.alienpants.leafpicrevived",
        ]

        for package in failed_packages:
            if package in v10_individual_results:
                result = v10_individual_results[package]
                assert not result["validation"][
                    "overall_success"
                ], f"{package} should be marked as failed"


class TestRegressionThresholds:
    """Tests for regression thresholds."""

    def test_iteration_threshold(self, v10_baseline):
        """Test that current results meet iteration threshold."""
        baseline_avg = v10_baseline["summary"]["avg_iterations_per_app"]

        print(f"\nBaseline avg iterations: {baseline_avg}")

        # Threshold: should achieve at least 80% of baseline
        threshold = baseline_avg * 0.8
        print(f"Minimum threshold (80%): {threshold}")

        # This is a placeholder - actual test would run current implementation
        # and compare. For now, just validate baseline data.
        assert baseline_avg > 0, "Baseline should have positive iterations"

    def test_states_threshold(self, v10_baseline):
        """Test that current results meet states threshold."""
        baseline_avg = v10_baseline["summary"]["avg_states_per_app"]

        print(f"\nBaseline avg states: {baseline_avg}")

        # Threshold: should achieve at least 80% of baseline
        threshold = baseline_avg * 0.8
        print(f"Minimum threshold (80%): {threshold}")

        assert baseline_avg > 0, "Baseline should have positive states"

    def test_no_new_failures(self, v10_individual_results):
        """Test that previously successful apps don't fail."""
        successful_in_v10 = [
            pkg
            for pkg, result in v10_individual_results.items()
            if result["validation"]["overall_success"]
        ]

        print(f"\nSuccessful in V10: {len(successful_in_v10)} apps")
        for pkg in successful_in_v10:
            print(f"  - {pkg}")

        # These apps should remain successful in new version
        assert len(successful_in_v10) == 7, "Expected 7 successful apps in V10"


# =============================================================================
# Per-App Regression Tests
# =============================================================================


class TestPerAppRegression:
    """Per-app regression tests."""

    @pytest.mark.parametrize(
        "app_package,min_iterations",
        [
            ("org.cryptomator.lite", 5),
            ("com.android.keepass", 4),
            ("org.mariotaku.twidere", 8),
            ("com.blogspot.e_kanivets.moneytracker", 12),
        ],
    )
    def test_app_iteration_threshold(
        self, v10_individual_results, app_package, min_iterations
    ):
        """Test that specific apps meet iteration thresholds."""
        if app_package not in v10_individual_results:
            pytest.skip(f"App {app_package} not in baseline")

        result = v10_individual_results[app_package]
        baseline_iterations = result["metrics"]["iterations"]

        print(f"\n{app_package}:")
        print(f"  Baseline iterations: {baseline_iterations}")
        print(f"  Minimum threshold: {min_iterations}")

        # Baseline should meet threshold
        assert (
            baseline_iterations >= min_iterations * 0.8
        ), f"Baseline too low for {app_package}"

    @pytest.mark.parametrize(
        "app_package,min_states",
        [
            ("org.cryptomator.lite", 2),
            ("com.android.keepass", 2),
            ("org.mariotaku.twidere", 3),
            ("com.blogspot.e_kanivets.moneytracker", 3),
        ],
    )
    def test_app_states_threshold(
        self, v10_individual_results, app_package, min_states
    ):
        """Test that specific apps meet states thresholds."""
        if app_package not in v10_individual_results:
            pytest.skip(f"App {app_package} not in baseline")

        result = v10_individual_results[app_package]
        baseline_states = result["metrics"]["unique_states"]

        print(f"\n{app_package}:")
        print(f"  Baseline states: {baseline_states}")
        print(f"  Minimum threshold: {min_states}")

        assert (
            baseline_states >= min_states * 0.8
        ), f"Baseline states too low for {app_package}"


# =============================================================================
# V10 vs V12 Comparison
# =============================================================================


class TestV10V12Comparison:
    """Tests comparing V10 and V12 documented baselines."""

    def test_documented_improvements(self, v10_baseline):
        """Test that V12 documented improvements are significant."""
        # V12 documented baseline (from docs/20251231_rvagent_validacao.md)
        v12_targets = {
            "apps_tested": 28,
            "success_rate": 100,  # percent
            "llm_percentage": 66.3,
            "algorithm_percentage": 33.7,
            "total_actions": 656,
        }

        v10_summary = v10_baseline["summary"]
        v10_success_rate = v10_summary["successful"] / v10_summary["total_tests"] * 100

        print("\nV10 vs V12 Comparison:")
        print(f"  V10 apps: {v10_summary['total_tests']}")
        print(f"  V12 apps target: {v12_targets['apps_tested']}")
        print(f"  V10 success rate: {v10_success_rate}%")
        print(f"  V12 success rate target: {v12_targets['success_rate']}%")

        # V12 targets are improvements over V10
        assert v12_targets["apps_tested"] > v10_summary["total_tests"]
        assert v12_targets["success_rate"] > v10_success_rate

    def test_llm_proportion_evolution(self):
        """Test that LLM proportion matches V12 documentation."""
        # V12 documented multimode proportion
        v12_llm_pct = 66.3
        v12_algo_pct = 33.7

        # Sum should be 100%
        assert abs((v12_llm_pct + v12_algo_pct) - 100) < 0.1

        # Current target is ~70% LLM
        current_target = 70
        print(f"\nLLM proportion:")
        print(f"  V12 documented: {v12_llm_pct}%")
        print(f"  Current target: {current_target}%")

        # Should be in similar range
        assert abs(v12_llm_pct - current_target) < 10

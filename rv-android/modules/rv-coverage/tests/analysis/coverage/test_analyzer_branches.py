"""
Branch-coverage tests for CoverageAnalyzer.

These tests target the calculation-mode selection, partial-mode metric path, and
the ``analyze()`` input-dispatch arms of ``analyzer.py`` that the happy-path
suites in ``test_analyzer.py`` and ``test_analyzer_fallback.py`` leave uncovered.
No production code is changed.

### Test design rationale
- **Equivalence Partitioning + Boundary Value Analysis** on
  ``_determine_calculation_mode``: the ``total_methods`` domain splits into three
  classes — ``0`` (RUNTIME_ONLY), ``<10`` (PARTIAL, already covered), and
  ``>=10`` (FULL). The ``>=10`` class is exercised at its lower boundary (exactly
  10 methods) and the ``0`` class at its degenerate boundary.
- **Decision-table / dispatch coverage** on ``analyze``: one test per supported
  input type (``str`` path, ``RvCoverageLog``, ``RvErrorLog``, non-empty ``list``)
  so every branch of the isinstance ladder — and the loop body inside the list
  arm — executes at least once.
- **Traceability**: partial-mode metrics correspond to the CLAUDE.md
  ``PARTIAL_STATIC_ANALYSIS`` mode; the assertions check the documented
  ``partial_analysis_warning`` / ``reachability_analysis`` markers.
- **Test Independence**: each test constructs its own analyzer and, where a
  logcat file is needed, its own temp file.
"""

import pytest
from rv_android_core.domain.classes import Classes, Method
from rv_android_core.domain.log import RvCoverageLog, RvErrorLog
from rv_android_core.domain.static import (
    StaticAnalysisData,
    Windows,
    WindowTransitionGraph,
)
from rv_coverage.analysis.coverage.analyzer import (
    CoverageAnalyzer,
    CoverageCalculationMode,
)


def _static_data_with_n_methods(n: int) -> StaticAnalysisData:
    """Build StaticAnalysisData for one class carrying ``n`` reachable methods."""
    classes = Classes()
    classes.add_clazz("com.test.Sample", component_type="activity", is_main=True)
    for i in range(n):
        classes.add_method(
            Method(
                class_name="com.test.Sample",
                name=f"m{i}",
                params=[],
                signature=f"com.test.Sample: void m{i}()",
                reachable=True,
                reaches_target=False,
                directly_reaches_target=False,
            )
        )
    return StaticAnalysisData(
        classes=classes, windows=Windows(), wtg=WindowTransitionGraph()
    )


# ---------------------------------------------------------------------------
# _determine_calculation_mode(): RUNTIME_ONLY (159) and FULL (163) boundaries
# ---------------------------------------------------------------------------


class TestDetermineCalculationModeBoundaries:
    """Equivalence Partitioning / BVA on the total_methods domain."""

    def test_zero_methods_yields_runtime_only(self):
        """WHEN classes exist but hold zero methods THEN mode is RUNTIME_ONLY (line 159)."""
        analyzer = CoverageAnalyzer()
        data = _static_data_with_n_methods(0)
        assert (
            analyzer._determine_calculation_mode(data)
            == CoverageCalculationMode.RUNTIME_ONLY
        )

    def test_ten_methods_yields_full_static(self):
        """WHEN methods >= the partial threshold (10) THEN mode is FULL (line 163)."""
        analyzer = CoverageAnalyzer()
        data = _static_data_with_n_methods(10)
        assert (
            analyzer._determine_calculation_mode(data)
            == CoverageCalculationMode.FULL_STATIC_ANALYSIS
        )


# ---------------------------------------------------------------------------
# get_coverage_metrics_with_fallback() PARTIAL arm (226-227) + _calculate_partial_metrics (285-293)
# ---------------------------------------------------------------------------


class TestFallbackModeGuard:
    """Cover the else arm of _initialize_fallback_mode_if_needed (branch 167->exit)."""

    def test_non_degraded_mode_is_left_untouched(self):
        """WHEN mode is not RUNTIME_ONLY/FALLBACK THEN fallback init is skipped."""
        analyzer = CoverageAnalyzer()
        analyzer.calculation_mode = CoverageCalculationMode.FULL_STATIC_ANALYSIS
        analyzer.fallback_reason = None

        analyzer._initialize_fallback_mode_if_needed()

        # The guard's false branch: mode unchanged, no fallback reason set.
        assert (
            analyzer.calculation_mode
            == CoverageCalculationMode.FULL_STATIC_ANALYSIS
        )
        assert analyzer.fallback_reason is None


class TestFullModeMetrics:
    """Cover the no-adjustment arm of get_coverage_metrics_with_fallback (226->229)."""

    def test_full_mode_returns_base_metrics_without_adjustment(self):
        """WHEN mode is FULL THEN neither fallback nor partial adjustment is applied."""
        analyzer = CoverageAnalyzer(static_data=_static_data_with_n_methods(10))
        assert (
            analyzer.calculation_mode
            == CoverageCalculationMode.FULL_STATIC_ANALYSIS
        )

        metrics = analyzer.get_coverage_metrics_with_fallback()

        assert (
            metrics["calculation_mode"]
            == CoverageCalculationMode.FULL_STATIC_ANALYSIS.value
        )
        assert metrics["is_degraded_mode"] is False
        assert "partial_analysis_warning" not in metrics
        assert "runtime_method_calls" not in metrics


class TestPartialStaticMetrics:
    """Cover the partial-static-analysis metric adjustment path."""

    def test_partial_mode_adds_partial_markers(self):
        """WHEN mode is PARTIAL_STATIC_ANALYSIS THEN partial markers are added (226-227, 285-293)."""
        # 3 methods -> below the 10-method threshold -> PARTIAL_STATIC_ANALYSIS.
        analyzer = CoverageAnalyzer(static_data=_static_data_with_n_methods(3))
        assert (
            analyzer.calculation_mode
            == CoverageCalculationMode.PARTIAL_STATIC_ANALYSIS
        )

        metrics = analyzer.get_coverage_metrics_with_fallback()

        assert metrics["partial_analysis_warning"] == (
            "Limited static analysis data available"
        )
        assert metrics["static_coverage_confidence"] == "low"
        assert metrics["reachability_analysis"] == "partial"


# ---------------------------------------------------------------------------
# analyze(): every input-dispatch arm (346, 348-349, 351-352, 356-359, 375-391)
# ---------------------------------------------------------------------------


class TestAnalyzeDispatch:
    """Decision-table coverage over analyze()'s supported input types."""

    def test_analyze_str_path_processes_logcat_file(self, tmp_path):
        """WHEN given a file path THEN analyze() parses it and merges errors (346, 375-391)."""
        logcat = tmp_path / "run.logcat"
        logcat.write_text(
            "03-24 19:37:25.398  4110  4110 V RVSEC   : SecretKeySpecSpec,"
            "br.unb.cic.cryptoapp.generated.CryptographyActivity,CryptographyActivity,"
            "executeSecretKeyOperation,Unknown Source:1,UnsatisfiedConstraint,bad key\n"
        )
        analyzer = CoverageAnalyzer()

        result = analyzer.analyze(str(logcat))

        assert isinstance(result, dict)
        assert result["total_errors"] == 1

    def test_analyze_single_coverage_log(self):
        """WHEN given an RvCoverageLog THEN it is dispatched to add_method_call (348-349)."""
        analyzer = CoverageAnalyzer()
        cov = RvCoverageLog(
            clazz="com.test.Sample",
            method="m0",
            params="",
            signature="com.test.Sample: void m0()",
        )
        # In runtime-only/fallback mode the metric denominator is absent, so
        # called_methods stays 0; the meaningful outcome is that the coverage-log
        # arm ran (register_method_call was invoked) and a metrics dict came back.
        called = []
        analyzer.add_method_call = lambda log: called.append(log)

        result = analyzer.analyze(cov)

        assert isinstance(result, dict)
        assert called == [cov]

    def test_analyze_single_error_log(self):
        """WHEN given an RvErrorLog THEN it is registered as an error (351-352)."""
        analyzer = CoverageAnalyzer()
        err = RvErrorLog(
            spec="SecretKeySpecSpec",
            error_type="UnsatisfiedConstraint",
            class_full_name="com.test.Sample",
            method="m0",
            source="Unknown Source:1",
            message="bad key",
        )

        result = analyzer.analyze(err)

        assert isinstance(result, dict)
        assert result["total_errors"] == 1

    def test_analyze_mixed_list(self):
        """WHEN given a non-empty list THEN each item is dispatched by type (356-359)."""
        analyzer = CoverageAnalyzer()
        items = [
            RvCoverageLog(
                clazz="com.test.Sample",
                method="m0",
                params="",
                signature="com.test.Sample: void m0()",
            ),
            RvErrorLog(
                spec="SecretKeySpecSpec",
                error_type="UnsatisfiedConstraint",
                class_full_name="com.test.Sample",
                method="m0",
                source="Unknown Source:1",
                message="bad key",
            ),
        ]

        result = analyzer.analyze(items)

        # The error is stored regardless of static data; the method call runs the
        # coverage-log arm of the loop even though it isn't counted without a
        # static universe.
        assert isinstance(result, dict)
        assert result["total_errors"] == 1
        assert len(analyzer.repository.errors) == 1

    def test_analyze_list_skips_unsupported_items(self):
        """WHEN a list holds an unsupported item THEN it is silently skipped (358->355)."""
        analyzer = CoverageAnalyzer()
        # An int matches neither RvCoverageLog nor RvErrorLog: the loop's elif is
        # false and control returns to the loop header without registering it.
        result = analyzer.analyze([42])

        assert isinstance(result, dict)
        assert len(analyzer.repository.errors) == 0


# ---------------------------------------------------------------------------
# get_metrics(): BaseAnalyzer interface delegation (439)
# ---------------------------------------------------------------------------


class TestGetMetrics:
    """Cover the BaseAnalyzer get_metrics() delegation."""

    def test_get_metrics_matches_coverage_metrics(self):
        """WHEN get_metrics() is called THEN it returns the coverage metrics dict (line 439)."""
        analyzer = CoverageAnalyzer()
        metrics = analyzer.get_metrics()
        assert isinstance(metrics, dict)
        assert "method_coverage" in metrics
        assert metrics == analyzer.get_coverage_metrics()

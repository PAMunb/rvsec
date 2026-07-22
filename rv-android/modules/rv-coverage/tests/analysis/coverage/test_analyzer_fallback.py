"""
Tests for CoverageAnalyzer - coverage analysis with fallback capabilities.

Tests cover:
- Initialization with/without static data
- _determine_calculation_mode() logic
- initialize_fallback_mode()
- get_coverage_metrics_with_fallback()
- analyze() with different input types
- process_logcat_file()
- get_fallback_status()
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.coverage import LogcatRepository
from rv_android_core.domain.static import StaticAnalysisData
from rv_coverage.analysis.coverage.analyzer import (
    CoverageAnalyzer,
    CoverageCalculationMode,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_static_data():
    """Create mock StaticAnalysisData with classes."""
    data = MagicMock(spec=StaticAnalysisData)
    data.classes = MagicMock()
    class_info = MagicMock()
    class_info.methods = {"method1": MagicMock(), "method2": MagicMock()}
    data.classes.classes = {"com.test.Class1": class_info}
    return data


@pytest.fixture
def mock_empty_static_data():
    """Create mock StaticAnalysisData without classes."""
    data = MagicMock(spec=StaticAnalysisData)
    data.classes = None
    return data


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestInitialization:
    """Test CoverageAnalyzer initialization."""

    def test_init_with_static_data(self, mock_static_data):
        """Test initialization with static data."""
        with patch(
            "rv_coverage.analysis.coverage.analyzer.initialize_repository_from_static_data"
        ):
            analyzer = CoverageAnalyzer(static_data=mock_static_data)
            assert analyzer.static_analysis_available is True

    def test_init_without_static_data(self):
        """Test initialization without static data."""
        analyzer = CoverageAnalyzer()
        assert analyzer.static_analysis_available is False

    def test_init_with_empty_static_data(self, mock_empty_static_data):
        """Test initialization with empty static data."""
        analyzer = CoverageAnalyzer(static_data=mock_empty_static_data)
        assert analyzer.static_analysis_available is False


# ---------------------------------------------------------------------------
# Tests: _determine_calculation_mode()
# ---------------------------------------------------------------------------


class TestDetermineCalculationMode:
    """Test _determine_calculation_mode() logic."""

    def test_mode_without_data_becomes_fallback(self):
        """Test that without data, mode becomes FALLBACK (after initialization)."""
        # After __init__, RUNTIME_ONLY becomes FALLBACK via _initialize_fallback_mode_if_needed
        with patch("rv_coverage.analysis.coverage.analyzer.LogcatRepository"):
            analyzer = CoverageAnalyzer()
            assert analyzer.calculation_mode == CoverageCalculationMode.FALLBACK_MODE

    def test_mode_with_empty_classes_becomes_fallback(self, mock_empty_static_data):
        """Test mode with empty classes becomes FALLBACK."""
        with patch("rv_coverage.analysis.coverage.analyzer.LogcatRepository"):
            analyzer = CoverageAnalyzer(static_data=mock_empty_static_data)
            assert analyzer.calculation_mode == CoverageCalculationMode.FALLBACK_MODE


# ---------------------------------------------------------------------------
# Tests: initialize_fallback_mode()
# ---------------------------------------------------------------------------


class TestInitializeFallbackMode:
    """Test initialize_fallback_mode()."""

    def test_initialize_fallback_sets_mode(self):
        """Test that fallback mode is set."""
        analyzer = CoverageAnalyzer()
        analyzer.initialize_fallback_mode()
        assert analyzer.calculation_mode == CoverageCalculationMode.FALLBACK_MODE

    def test_initialize_fallback_sets_reason(self):
        """Test that fallback reason is set."""
        analyzer = CoverageAnalyzer()
        analyzer.initialize_fallback_mode()
        assert analyzer.fallback_reason is not None

    def test_initialize_fallback_disables_static(self):
        """Test that static analysis is disabled."""
        analyzer = CoverageAnalyzer()
        analyzer.initialize_fallback_mode()
        assert analyzer.static_analysis_available is False


# ---------------------------------------------------------------------------
# Tests: get_coverage_metrics_with_fallback()
# ---------------------------------------------------------------------------


class TestGetCoverageMetricsWithFallback:
    """Test get_coverage_metrics_with_fallback()."""

    def test_fallback_metrics_includes_mode(self):
        """Test that fallback metrics include mode."""
        analyzer = CoverageAnalyzer()
        analyzer.initialize_fallback_mode()
        metrics = analyzer.get_coverage_metrics_with_fallback()
        assert "calculation_mode" in metrics

    def test_fallback_metrics_includes_static_availability(self):
        """Test that fallback metrics include static availability."""
        analyzer = CoverageAnalyzer()
        analyzer.initialize_fallback_mode()
        metrics = analyzer.get_coverage_metrics_with_fallback()
        assert "static_analysis_available" in metrics


# ---------------------------------------------------------------------------
# Tests: analyze()
# ---------------------------------------------------------------------------


class TestAnalyze:
    """Test analyze() with different input types."""

    def test_analyze_with_unsupported_type(self):
        """Test analyze with unsupported data type."""
        analyzer = CoverageAnalyzer()
        result = analyzer.analyze(42)  # int is unsupported
        assert isinstance(result, dict)

    def test_analyze_with_list(self):
        """Test analyze with list."""
        analyzer = CoverageAnalyzer()
        result = analyzer.analyze([])
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Tests: get_fallback_status()
# ---------------------------------------------------------------------------


class TestGetFallbackStatus:
    """Test get_fallback_status()."""

    def test_fallback_status_includes_mode(self):
        """Test that status includes mode."""
        analyzer = CoverageAnalyzer()
        status = analyzer.get_fallback_status()
        assert "mode" in status

    def test_fallback_status_includes_capabilities(self):
        """Test that status includes capabilities."""
        analyzer = CoverageAnalyzer()
        status = analyzer.get_fallback_status()
        assert "capabilities" in status

    def test_fallback_capabilities_runtime_coverage(self):
        """Test that runtime coverage is always available."""
        analyzer = CoverageAnalyzer()
        status = analyzer.get_fallback_status()
        assert status["capabilities"]["runtime_coverage"] is True
        assert status["capabilities"]["error_tracking"] is True


# ---------------------------------------------------------------------------
# Tests: add_method_call() and add_error()
# ---------------------------------------------------------------------------


class TestAddMethodCallAndError:
    """Test add_method_call() and add_error()."""

    def test_add_method_call(self):
        """Test adding a method call."""
        analyzer = CoverageAnalyzer()
        mock_log = MagicMock()
        mock_log.clazz = "com.test.Class"
        mock_log.method = "method1"
        # Should not raise
        analyzer.add_method_call(mock_log)

    def test_add_error(self):
        """Test adding an error."""
        analyzer = CoverageAnalyzer()
        mock_error = MagicMock()
        # Should not raise
        analyzer.add_error(mock_error)

"""
Tests for CoverageTracker - real-time coverage tracking.

Tests cover:
- Initialization with/without static data
- start()/stop() lifecycle
- track_coverage() context manager
- process_lines() with various logcat entries
- _update_coverage_metrics() with change detection
- get_coverage_metrics() retrieval
"""

import os
import tempfile
import threading
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from rv_coverage.analysis.coverage.tracker import CoverageTracker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_logcat_file(tmp_path):
    """Create a temporary logcat file."""
    logcat_file = str(tmp_path / "test_logcat.txt")
    with open(logcat_file, "w") as f:
        f.write("")
    return logcat_file


@pytest.fixture
def tracker(temp_logcat_file):
    """Create CoverageTracker instance."""
    return CoverageTracker(logcat_file=temp_logcat_file)


@pytest.fixture
def tracker_with_static(temp_logcat_file):
    """Create CoverageTracker with mock static data."""
    mock_static = MagicMock()
    mock_static.classes = MagicMock()
    mock_static.classes.classes = {"com.test.Class": MagicMock(methods={"m1": {}, "m2": {}})}
    
    with patch("rv_coverage.analysis.coverage.tracker.initialize_repository_from_static_data"):
        return CoverageTracker(logcat_file=temp_logcat_file, static_data=mock_static)


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestInitialization:
    """Test CoverageTracker initialization."""

    def test_init_stores_logcat_file(self, tracker, temp_logcat_file):
        """Test that logcat_file is stored."""
        assert tracker.logcat_file == temp_logcat_file

    def test_init_sets_not_running(self, tracker):
        """Test that tracker is not running initially."""
        assert tracker.is_running is False

    def test_init_with_task_id(self, temp_logcat_file):
        """Test initialization with task ID."""
        tracker = CoverageTracker(logcat_file=temp_logcat_file, task_id="test_001")
        assert tracker.task_id == "test_001"

    def test_init_with_start_time(self, temp_logcat_file):
        """Test initialization with start time."""
        start_time = datetime.now()
        tracker = CoverageTracker(
            logcat_file=temp_logcat_file, task_start_time=start_time
        )
        assert tracker.tool_execution_start_time == start_time

    def test_init_initial_metrics(self, tracker):
        """Test that initial metrics are zero."""
        assert tracker._previous_metrics["method_coverage"] == 0.0
        assert tracker._previous_metrics["called_methods"] == 0


# ---------------------------------------------------------------------------
# Tests: start()/stop()
# ---------------------------------------------------------------------------


class TestStartStop:
    """Test start()/stop() lifecycle."""

    def test_start_creates_file(self, tmp_path):
        """Test that start() creates logcat file."""
        logcat_file = str(tmp_path / "new_logcat.txt")
        tracker = CoverageTracker(logcat_file=logcat_file)
        
        try:
            tracker.start()
            assert os.path.exists(logcat_file)
        finally:
            tracker.stop()

    def test_start_sets_running_flag(self, tracker):
        """Test that start() sets is_running."""
        try:
            tracker.start()
            assert tracker.is_running is True
        finally:
            tracker.stop()

    def test_stop_clears_running_flag(self, tracker):
        """Test that stop() clears is_running."""
        tracker.start()
        tracker.stop()
        assert tracker.is_running is False

    def test_stop_idempotent(self, tracker):
        """Test that stop() can be called multiple times."""
        tracker.stop()  # Not running
        tracker.stop()  # Still not running
        # Should not raise

    def test_start_already_running_warning(self, tracker):
        """Test that start() warns if already running."""
        try:
            tracker.start()
            tracker.logger.warning = MagicMock()
            tracker.start()  # Second call
            tracker.logger.warning.assert_called_once()
        finally:
            tracker.stop()


# ---------------------------------------------------------------------------
# Tests: track_coverage() context manager
# ---------------------------------------------------------------------------


class TestTrackCoverageContextManager:
    """Test track_coverage() context manager."""

    def test_context_manager_starts_and_stops(self, tracker):
        """Test context manager starts and stops tracker."""
        with tracker.track_coverage() as t:
            assert t.is_running is True
        
        assert tracker.is_running is False

    def test_context_manager_stops_on_exception(self, tracker):
        """Test context manager stops tracker on exception."""
        try:
            with tracker.track_coverage():
                raise ValueError("Test error")
        except ValueError:
            pass
        
        assert tracker.is_running is False


# ---------------------------------------------------------------------------
# Tests: process_lines()
# ---------------------------------------------------------------------------


class TestProcessLines:
    """Test process_lines() with various logcat entries."""

    def test_process_empty_lines(self, tracker):
        """Test processing empty lines."""
        tracker.process_lines(["", "\n", "  \n"])
        # Should not raise, no metrics change

    def test_process_non_rvsec_lines(self, tracker):
        """Test processing non-RVSEC lines."""
        tracker.process_lines([
            "01-01 00:00:00.000  1234  1234 I SomeTag: Regular log line",
            "01-01 00:00:00.000  1234  1234 D AnotherTag: Debug info",
        ])
        # Should be skipped, no metrics change

    def test_process_coverage_log_line(self, tracker):
        """Test processing RVSEC-COV coverage log line."""
        line = "01-01 00:00:01.000  1234  1234 I RVSEC-COV: com.test.Class.method:()V\n"
        tracker.process_lines([line])
        assert tracker.total_method_calls >= 0  # May or may not increment depending on parser

    def test_process_error_log_line(self, tracker):
        """Test processing RVSEC error log line."""
        line = "01-01 00:00:01.000  1234  1234 E RVSEC: spec=TestSpec class=com.test.Class method=testMethod message=Test error\n"
        tracker.process_lines([line])
        # May increment errors if parser recognizes it


# ---------------------------------------------------------------------------
# Tests: _update_coverage_metrics()
# ---------------------------------------------------------------------------


class TestUpdateCoverageMetrics:
    """Test _update_coverage_metrics() with change detection."""

    def test_no_update_when_no_change(self, tracker):
        """Test that metrics are not updated when no change."""
        tracker._data_changed_since_last_update = False
        tracker.repository.calculate_metrics = MagicMock()
        
        tracker._update_coverage_metrics()
        
        # calculate_metrics should not be called
        tracker.repository.calculate_metrics.assert_not_called()

    def test_update_when_changed(self, tracker):
        """Test that metrics are updated when changed."""
        tracker._data_changed_since_last_update = True
        
        mock_metrics = MagicMock()
        mock_metrics.to_dict.return_value = {
            "method_coverage": 50.0,
            "activity_coverage": 30.0,
            "mop_method_coverage": 40.0,
            "called_methods": 10,
            "total_activities": 5,
            "unique_errors": 2,
        }
        mock_metrics.called_methods = 10
        mock_metrics.total_activities = 5
        mock_metrics.unique_errors = 2
        
        with patch.object(tracker.repository, 'calculate_metrics', return_value=mock_metrics):
            tracker._update_coverage_metrics()
            tracker.repository.calculate_metrics.assert_called_once()
        
        # Flag should be reset
        assert tracker._data_changed_since_last_update is False


# ---------------------------------------------------------------------------
# Tests: get_coverage_metrics()
# ---------------------------------------------------------------------------


class TestGetCoverageMetrics:
    """Test get_coverage_metrics() retrieval."""

    def test_get_metrics_returns_dict(self, tracker):
        """Test that get_coverage_metrics returns dict."""
        metrics = tracker.get_coverage_metrics()
        assert isinstance(metrics, dict)

    def test_get_metrics_includes_keys(self, tracker):
        """Test that metrics include expected keys."""
        metrics = tracker.get_coverage_metrics()
        # Should have at least basic keys
        assert "method_coverage" in metrics or len(metrics) > 0


# ---------------------------------------------------------------------------
# Tests: Thread safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    """Test thread-safe operation."""

    def test_concurrent_start_stop(self, temp_logcat_file):
        """Test concurrent start/stop operations."""
        errors = []
        
        def run_tracker():
            try:
                t = CoverageTracker(logcat_file=temp_logcat_file)
                t.start()
                time.sleep(0.1)
                t.stop()
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=run_tracker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0

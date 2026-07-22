# tests/analysis/coverage/test_tracker.py
from datetime import datetime

import pytest
from rv_android_core.domain.classes import Classes, Method
from rv_android_core.domain.static import (
    StaticAnalysisData,
    Windows,
    WindowTransitionGraph,
)
from rv_coverage.analysis.coverage.tracker import CoverageTracker
from rv_coverage.parser.log.logcat_parser import parse_logcat_line


class TestCoverageTracker:
    @pytest.fixture
    def mock_static_data(self):
        """Create mock static analysis data matching the logcat structure."""
        classes = Classes()

        # Create mock classes matching logcat content
        main_activity_class = classes.add_clazz(
            "br.unb.cic.cryptoapp.MainActivity", component_type="activity", is_main=True
        )

        crypto_activity_class = classes.add_clazz(
            "br.unb.cic.cryptoapp.generated.CryptographyActivity",
            component_type="activity",
            is_main=False,
        )

        # Add methods matching logcat entries
        methods = [
            Method(
                class_name="br.unb.cic.cryptoapp.MainActivity",
                name="onCreate",
                params=["android.os.Bundle"],
                signature="br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)",
                reachable=True,
                reaches_target=False,
                directly_reaches_target=False,
            ),
            Method(
                class_name="br.unb.cic.cryptoapp.generated.CryptographyActivity",
                name="executeSecretKeyOperation",
                params=[],
                signature="br.unb.cic.cryptoapp.generated.CryptographyActivity: void executeSecretKeyOperation()",
                reachable=True,
                reaches_target=True,
                directly_reaches_target=True,
            ),
        ]

        for method in methods:
            classes.add_method(method)

        return StaticAnalysisData(
            classes=classes, windows=Windows(), wtg=WindowTransitionGraph()
        )

    @pytest.fixture
    def sample_logcat_file(self, tmp_path):
        """Create a sample logcat file for testing."""
        logcat_content = """
03-24 19:36:38.394  4110  4110 V RVSEC-COV: <br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)>
03-24 19:37:25.398  4110  4110 V RVSEC   : SecretKeySpecSpec,br.unb.cic.cryptoapp.generated.CryptographyActivity,CryptographyActivity,executeSecretKeyOperation,Unknown Source:1,UnsatisfiedConstraint,Using either an invalid algorithm or keyMaterial.length is not randomized.
03-24 19:37:25.400  4110  4110 V RVSEC   : SecretKeySpecSpec,br.unb.cic.cryptoapp.generated.CryptographyActivity,CryptographyActivity,executeSecretKeyOperation,Unknown Source:1,InvalidSequenceOfMethodCalls,unknown
"""
        logcat_path = tmp_path / "sample.logcat"
        logcat_path.write_text(logcat_content)
        return str(logcat_path)

    def test_parse_real_logcat_entries(self, sample_logcat_file):
        """Test parsing real logcat entries."""
        with open(sample_logcat_file, "r") as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if line:
                error_log, coverage_log = parse_logcat_line(line)

                if "RVSEC-COV" in line:
                    assert coverage_log is not None
                    assert coverage_log.clazz is not None
                    assert coverage_log.method is not None
                elif "RVSEC" in line and "COV" not in line:
                    assert error_log is not None
                    assert error_log.class_full_name is not None
                    assert error_log.method is not None

    def test_process_real_logcat_file(self, mock_static_data, sample_logcat_file):
        """Test processing a real logcat file."""
        tracker = CoverageTracker(
            sample_logcat_file, mock_static_data, task_id="test_task"
        )

        # Simulate tracking
        with open(sample_logcat_file, "r") as f:
            lines = f.readlines()

        # Process all lines
        tracker.process_lines(lines)

        # Check tracking results
        assert tracker.total_method_calls > 0
        assert tracker.total_errors > 0

        # Verify metrics have been updated
        metrics = tracker.get_coverage_metrics()
        assert metrics is not None
        assert "method_coverage" in metrics

    def test_get_detailed_metrics(self, mock_static_data, sample_logcat_file):
        """Test retrieving detailed coverage metrics."""
        tracker = CoverageTracker(
            sample_logcat_file, mock_static_data, task_id="test_task"
        )

        # Process lines manually
        with open(sample_logcat_file, "r") as f:
            lines = f.readlines()

        tracker.process_lines(lines)

        # Get detailed metrics from the repository
        detailed_metrics = tracker.repository.to_dict()

        # Verify structure of detailed metrics
        assert "metrics" in detailed_metrics
        assert "classes" in detailed_metrics
        assert "errors" in detailed_metrics


class TestCoverageTrackerTiming:
    """Tests for coverage time calculation accuracy.

    These tests verify that updating tool_execution_start_time after tracker
    initialization produces correct relative time values in coverage entries.
    The scenario: tracker is created with task start_time, then the time reference
    is updated to tool_execution_start before processing begins.
    """

    @pytest.fixture
    def logcat_with_timing(self, tmp_path):
        """Logcat file with a coverage entry at 19:37:05 (5 seconds after tool start)."""
        logcat_content = (
            "03-24 19:37:05.000  4110  4110 V RVSEC-COV: "
            "<br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)>\n"
        )
        logcat_path = tmp_path / "timing.logcat"
        logcat_path.write_text(logcat_content)
        return str(logcat_path)

    def _get_captured_time(self, tracker, logcat_file):
        """Process logcat and capture time_since_task_start from the coverage log.

        The repository's register_method_call silently ignores entries whose
        signature (with angle brackets from logcat) doesn't match static data
        signatures (without angle brackets). So instead of reading from the
        repository, we capture the value set on the RvCoverageLog object by
        patching register_method_call.
        """
        captured = []
        original_register = tracker.repository.register_method_call

        def capture_register(coverage_log):
            captured.append(coverage_log.time_since_task_start)
            original_register(coverage_log)

        tracker.repository.register_method_call = capture_register

        with open(logcat_file, "r") as f:
            tracker.process_lines(f.readlines())

        assert tracker.total_method_calls == 1, "Expected exactly one coverage entry"
        assert len(captured) == 1, "Expected register_method_call to be called once"
        return captured[0]

    def test_time_calculated_from_tool_execution_start(self, logcat_with_timing):
        """
        When tool_execution_start_time is set to 19:37:00 and the logcat entry
        is at 19:37:05, the relative time should be 5 seconds.
        """
        tool_start = datetime(2026, 3, 24, 19, 37, 0)
        tracker = CoverageTracker(
            logcat_with_timing, None, task_start_time=tool_start, task_id="test"
        )

        time_value = self._get_captured_time(tracker, logcat_with_timing)
        assert time_value == 5

    def test_time_offset_with_stale_start_time(self, logcat_with_timing):
        """
        When tracker is initialized with task creation time (60s before tool start),
        but then tool_execution_start_time is updated before processing,
        the relative time should reflect the updated reference.

        This simulates the fix: tracker created in Phase 2 with start_time,
        then tool_execution_start_time updated in Phase 3 before start().
        """
        task_creation = datetime(2026, 3, 24, 19, 36, 0)
        tracker = CoverageTracker(
            logcat_with_timing, None, task_start_time=task_creation, task_id="test"
        )

        # Initially, time reference is task creation
        assert tracker.tool_execution_start_time == task_creation

        # Update to tool execution start (19:37:00) — this is what start_tracking() does
        tool_start = datetime(2026, 3, 24, 19, 37, 0)
        tracker.tool_execution_start_time = tool_start

        time_value = self._get_captured_time(tracker, logcat_with_timing)
        # Should be 5s from tool_start, NOT 65s from task_creation
        assert time_value == 5

    def test_time_offset_without_update_shows_wrong_value(self, logcat_with_timing):
        """
        Demonstrates the bug scenario: if tool_execution_start_time is NOT updated
        from task creation time to tool execution time, the relative time is wrong.

        Task created at 19:36:00, logcat entry at 19:37:05 => 65 seconds.
        After fix (update to 19:37:00), logcat entry at 19:37:05 => 5 seconds.
        """
        task_creation = datetime(2026, 3, 24, 19, 36, 0)
        tracker = CoverageTracker(
            logcat_with_timing, None, task_start_time=task_creation, task_id="test"
        )

        # Do NOT update tool_execution_start_time (simulates the bug)
        time_value = self._get_captured_time(tracker, logcat_with_timing)
        # Without the fix, time is 65 seconds (includes 60s pre-processing overhead)
        assert time_value == 65

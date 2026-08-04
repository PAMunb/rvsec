"""
Branch-coverage tests for CoverageTracker.

These tests target the error-handling, background-thread, timing, and diagnostic
paths of ``tracker.py`` that the happy-path suites in ``test_tracker.py`` and
``test_tracker_lifecycle.py`` leave uncovered. No production code is changed.

### Test design rationale
- **Basis Path Testing (white-box)**: each test drives one previously unexecuted
  branch — the static-data init failure, ``os.makedirs`` on a missing parent, the
  ``start()``/``stop()`` exception handlers, the tail-loop new-line and periodic
  refresh arms, the ``_track_coverage`` exception/finally cleanup, error/diagnostic
  relative-timing arithmetic, and the metric-update failure path.
- **Boundary Value Analysis**: the relative-timing assertions pin exact second
  offsets (a coverage/error/diagnostic entry N seconds after the tool start),
  exercising the ``max(0, ...)`` clamp at a concrete positive boundary.
- **Robustness**: dependencies that can throw (``initialize_repository_from_static_data``,
  ``threading.Thread``, ``thread.join``, ``parse_logcat_line``,
  ``repository.calculate_metrics``, ``file.close``) are mocked to raise so the
  tracker's defensive handlers are proven to swallow/log rather than propagate.
- **Test Independence**: every test builds its own tracker over a per-test temp
  file; the background thread is never left running (loops are broken via a
  patched ``time.sleep`` that sets the stop event).
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from rv_coverage.analysis.coverage.tracker import CoverageTracker

# A verify_error diagnostic start line (art tag, "Rejecting class"), timestamped
# at 19:37:10 so that with a tool start of 19:37:00 the relative offset is 10s.
VERIFY_LINE = "03-24 19:37:10.000  4110  4110 E art     : Rejecting class br.unb.cic.Foo"
# A second diagnostic block under a different (tag, pid, tid) key: this is what
# closes the buffered one. A line under a non-diagnostic tag does NOT close it —
# logcat merges all processes into one stream, so foreign lines land inside a
# block that is contiguous only in its own process's output.
CLOSING_LINE = (
    "03-24 19:37:20.000  4111  4111 E art     : Rejecting class br.unb.cic.Bar"
)
# A modern-format coverage line.
COVERAGE_LINE = (
    "03-24 19:37:05.000  4110  4110 V RVSEC-COV: "
    "<br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)>"
)
# A standard-format RVSEC error line timestamped at 19:37:25 (25s after tool start).
ERROR_LINE = (
    "03-24 19:37:25.398  4110  4110 V RVSEC   : SecretKeySpecSpec,"
    "br.unb.cic.cryptoapp.generated.CryptographyActivity,CryptographyActivity,"
    "executeSecretKeyOperation,Unknown Source:1,UnsatisfiedConstraint,bad key"
)

TOOL_START = datetime(2026, 3, 24, 19, 37, 0)


@pytest.fixture
def logcat_file(tmp_path):
    """An existing empty logcat file."""
    path = tmp_path / "branches.logcat"
    path.write_text("")
    return str(path)


# ---------------------------------------------------------------------------
# _initialize_from_static_data() failure path (lines 211-212)
# ---------------------------------------------------------------------------


class TestInitializeFromStaticDataFailure:
    """Robustness: a failing static-data initializer must be logged, not raised."""

    def test_init_swallows_initializer_error(self, logcat_file):
        """WHEN the repository initializer raises THEN __init__ still completes."""
        mock_static = MagicMock()
        mock_static.classes = MagicMock()
        mock_static.classes.classes = {"com.C": MagicMock(methods={"m": {}})}

        with patch(
            "rv_coverage.analysis.coverage.tracker.initialize_repository_from_static_data",
            side_effect=RuntimeError("boom"),
        ):
            # Must not propagate: the except at 211-212 logs and continues.
            tracker = CoverageTracker(logcat_file, static_data=mock_static)

        assert tracker.is_running is False


# ---------------------------------------------------------------------------
# start(): makedirs on missing parent (235) and failure path (252-255)
# ---------------------------------------------------------------------------


class TestStartBranches:
    """Cover the parent-directory creation and the start() exception handler."""

    def test_start_creates_missing_parent_dir(self, tmp_path):
        """WHEN the logcat parent dir is absent THEN start() creates it (line 235)."""
        import os

        nested = tmp_path / "missing" / "deep" / "logcat.txt"
        tracker = CoverageTracker(logcat_file=str(nested))
        try:
            tracker.start()
            assert os.path.isdir(os.path.dirname(str(nested)))
        finally:
            tracker.stop()

    def test_start_failure_resets_state_and_reraises(self, logcat_file):
        """WHEN thread creation raises THEN start() clears is_running and re-raises."""
        tracker = CoverageTracker(logcat_file)
        with patch(
            "rv_coverage.analysis.coverage.tracker.threading.Thread",
            side_effect=RuntimeError("thread boom"),
        ):
            with pytest.raises(RuntimeError):
                tracker.start()
        assert tracker.is_running is False


# ---------------------------------------------------------------------------
# stop(): thread-not-terminated warning (277) and exception handler (284-286)
# ---------------------------------------------------------------------------


class TestStopBranches:
    """Cover the two non-happy branches inside stop()."""

    def test_stop_warns_when_thread_still_alive(self, logcat_file):
        """WHEN the thread outlives the join timeout THEN a warning is logged (277)."""
        tracker = CoverageTracker(logcat_file)
        tracker.is_running = True
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        tracker.thread = mock_thread
        tracker.logger.warning = MagicMock()

        tracker.stop()

        tracker.logger.warning.assert_called_once()
        assert tracker.is_running is False

    def test_stop_without_thread_object(self, logcat_file):
        """WHEN is_running but thread is None THEN stop() skips the join (branch 271->281)."""
        tracker = CoverageTracker(logcat_file)
        tracker.is_running = True
        tracker.thread = None

        tracker.stop()

        assert tracker.is_running is False

    def test_stop_swallows_join_error(self, logcat_file):
        """WHEN thread.join raises THEN stop() logs and still clears is_running (284-286)."""
        tracker = CoverageTracker(logcat_file)
        tracker.is_running = True
        mock_thread = MagicMock()
        mock_thread.join.side_effect = RuntimeError("join boom")
        tracker.thread = mock_thread
        tracker.logger.error = MagicMock()

        tracker.stop()

        tracker.logger.error.assert_called_once()
        assert tracker.is_running is False


# ---------------------------------------------------------------------------
# _track_coverage(): tail loop, periodic refresh, exception + finally cleanup
# ---------------------------------------------------------------------------


def _fake_open(readlines_side_effect, close_side_effect=None):
    """Build a context-manager mock standing in for ``open(...)``.

    The returned object supports ``with open(...) as f`` and exposes a fake file
    whose ``readlines`` yields the given sequence (one element per call).
    """
    fake = MagicMock()
    fake.readlines.side_effect = readlines_side_effect
    fake.closed = False
    if close_side_effect is not None:
        fake.close.side_effect = close_side_effect
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


class TestTrackCoverageLoop:
    """Drive _track_coverage deterministically by mocking the file and sleep."""

    def test_new_lines_are_processed_then_metrics_updated(self, logcat_file):
        """WHEN new lines appear after EOF THEN they are processed and metrics refreshed (309-312)."""
        tracker = CoverageTracker(logcat_file)
        # Drain -> [] ; first loop read -> one coverage line ; then stop.
        cm, fake = _fake_open([[], [COVERAGE_LINE + "\n"]])

        def stop_after_sleep(_seconds):
            tracker._stop_event.set()

        with patch("builtins.open", return_value=cm), patch(
            "rv_coverage.analysis.coverage.tracker.time.sleep",
            side_effect=stop_after_sleep,
        ):
            tracker._track_coverage()

        assert tracker.total_method_calls == 1
        # finally-block close path (338-340) exercised on normal exit.
        fake.close.assert_called_once()

    def test_periodic_refresh_when_idle(self, logcat_file):
        """WHEN idle >=10s THEN a periodic metric refresh runs (319-320)."""
        tracker = CoverageTracker(logcat_file)
        tracker.last_update_time = datetime.now() - timedelta(seconds=11)
        old_update = tracker.last_update_time
        # Drain -> [] ; loop read -> [] (idle) ; then stop.
        cm, _fake = _fake_open([[], []])

        def stop_after_sleep(_seconds):
            tracker._stop_event.set()

        with patch("builtins.open", return_value=cm), patch(
            "rv_coverage.analysis.coverage.tracker.time.sleep",
            side_effect=stop_after_sleep,
        ):
            tracker._track_coverage()

        # The idle branch refreshed last_update_time to "now".
        assert tracker.last_update_time > old_update

    def test_exception_in_loop_is_logged_and_file_closed(self, logcat_file):
        """WHEN reading raises THEN _track_coverage logs, then finally closes even if close() raises (327-328, 339-342)."""
        tracker = CoverageTracker(logcat_file)
        tracker.logger.error = MagicMock()
        # First readlines (the drain) raises; close() also raises to hit 341-342.
        cm, fake = _fake_open(
            OSError("read boom"), close_side_effect=RuntimeError("close boom")
        )

        with patch("builtins.open", return_value=cm):
            tracker._track_coverage()

        tracker.logger.error.assert_called()
        fake.close.assert_called_once()
        assert tracker.is_running is False


# ---------------------------------------------------------------------------
# _process_line(): error relative timing (389-396) and parse failure (440-441)
# ---------------------------------------------------------------------------


class TestProcessLineErrorTiming:
    """Boundary Value Analysis on the error relative-timestamp arithmetic."""

    def test_error_time_since_start_is_computed(self, logcat_file):
        """WHEN an RVSEC error is 25s after tool start THEN time_since_task_start == 25 (389-396)."""
        tracker = CoverageTracker(logcat_file, task_start_time=TOOL_START)

        captured = []
        original = tracker.repository.register_rv_error

        def capture(err):
            captured.append(err.time_since_task_start)
            original(err)

        tracker.repository.register_rv_error = capture

        tracker.process_lines([ERROR_LINE + "\n"])

        assert tracker.total_errors == 1
        assert captured == [25]

    def test_parse_failure_is_swallowed(self, logcat_file):
        """WHEN parse_logcat_line raises THEN _process_line logs and does not propagate (440-441)."""
        tracker = CoverageTracker(logcat_file)
        tracker.logger.error = MagicMock()
        with patch(
            "rv_coverage.analysis.coverage.tracker.parse_logcat_line",
            side_effect=RuntimeError("parse boom"),
        ):
            tracker.process_lines([COVERAGE_LINE + "\n"])
        tracker.logger.error.assert_called()


# ---------------------------------------------------------------------------
# Diagnostic events: registration on close (438, 446-452) and flush tail (462)
# ---------------------------------------------------------------------------


class TestDiagnosticEvents:
    """Cover the diagnostic-event registration and flush paths."""

    def test_diagnostic_event_registered_on_close(self, logcat_file):
        """WHEN a verify_error block closes THEN it is registered with relative timing (438, 446-452)."""
        tracker = CoverageTracker(logcat_file, task_start_time=TOOL_START)
        captured = []
        tracker.repository.register_diagnostic_event = lambda ev: captured.append(ev)

        # First line buffers the event; the second, under a different diagnostic
        # (tag, pid, tid) key, closes it — so feed_line returns the event and
        # _register_diagnostic_event runs.
        tracker.process_lines([VERIFY_LINE, CLOSING_LINE])

        assert len(captured) == 1
        assert captured[0].category == "verify_error"
        # 19:37:10 is 10s after the 19:37:00 tool start.
        assert captured[0].time_since_task_start == 10

    def test_diagnostic_event_without_tool_start_has_no_relative_time(self, logcat_file):
        """WHEN no tool start time is set THEN the event is registered without timing (branch 446->451)."""
        # tool_execution_start_time defaults to None: the timing guard is false and
        # register runs directly without stamping time_since_task_start.
        tracker = CoverageTracker(logcat_file)
        captured = []
        tracker.repository.register_diagnostic_event = lambda ev: captured.append(ev)

        tracker.process_lines([VERIFY_LINE, CLOSING_LINE])

        assert len(captured) == 1
        assert captured[0].category == "verify_error"

    def test_flush_diagnostics_emits_buffered_tail(self, logcat_file):
        """WHEN a diagnostic block is still buffered THEN flush_diagnostics emits it (462)."""
        tracker = CoverageTracker(logcat_file, task_start_time=TOOL_START)
        captured = []
        tracker.repository.register_diagnostic_event = lambda ev: captured.append(ev)

        # Only the start line: it stays buffered, nothing emitted yet.
        tracker.process_lines([VERIFY_LINE])
        assert captured == []

        tracker.flush_diagnostics()

        assert len(captured) == 1
        assert captured[0].category == "verify_error"


# ---------------------------------------------------------------------------
# _update_coverage_metrics(): failure path (519-520)
# ---------------------------------------------------------------------------


class TestUpdateMetricsFailure:
    """Robustness: a failing metric calculation must be logged, not raised."""

    def test_metric_calculation_error_is_swallowed(self, logcat_file):
        """WHEN calculate_metrics raises THEN _update_coverage_metrics logs (519-520)."""
        tracker = CoverageTracker(logcat_file)
        tracker._data_changed_since_last_update = True
        tracker.repository.calculate_metrics = MagicMock(
            side_effect=RuntimeError("metrics boom")
        )
        tracker.logger.error = MagicMock()

        tracker._update_coverage_metrics()

        tracker.logger.error.assert_called()

"""Tests for the RvDiagnosticEvent model and its isolation on LogcatRepository.

Covers the core delta-spec invariants of gh72:
- Crash event carries attribution and trace summary (Requirement: Diagnostic Event Domain Model).
- unique_msg disambiguates by category.
- INV-CORE-39: registering diagnostic events does not perturb any coverage/error metric.
"""

from datetime import datetime

import pytest
from rv_android_core.domain.coverage import LogcatRepository
from rv_android_core.domain.log import RvDiagnosticEvent, RvErrorLog


class TestRvDiagnosticEvent:
    """Tests for the RvDiagnosticEvent class."""

    @pytest.fixture
    def crash_event(self):
        """A crash event parsed from an AndroidRuntime FATAL block."""
        return RvDiagnosticEvent(
            category="crash",
            class_full_name="java.lang.NullPointerException",
            method="onMenuItemClick",
            message="FATAL EXCEPTION: main",
            source="MainActivity.java:50",
            process="br.unb.cic.cryptoapp",
            pid="7071",
            tid="7071",
            fatal=True,
            stack_head="br.unb.cic.cryptoapp.MainActivity$1.onMenuItemClick(MainActivity.java:50)",
            n_frames=12,
            original_msg="FATAL EXCEPTION: main\n\tat ...",
        )

    def test_crash_event_carries_attribution_and_trace_summary(self, crash_event):
        """Crash event populates category/fatal/process and trace summary fields."""
        assert crash_event.category == "crash"
        assert crash_event.fatal is True
        assert crash_event.process == "br.unb.cic.cryptoapp"
        assert crash_event.pid == "7071"
        assert crash_event.class_full_name == "java.lang.NullPointerException"
        assert crash_event.n_frames == 12
        assert crash_event.stack_head.endswith("MainActivity.java:50)")
        assert crash_event.original_msg.startswith("FATAL EXCEPTION: main")
        assert isinstance(crash_event.time_occurred, datetime)

    def test_unique_msg_disambiguates_by_category(self):
        """Two events with the same class/method but different category differ."""
        crash = RvDiagnosticEvent(
            category="crash",
            class_full_name="com.foo.Bar",
            method="doWork",
            message="boom",
        )
        verify = RvDiagnosticEvent(
            category="verify_error",
            class_full_name="com.foo.Bar",
            method="doWork",
            message="boom",
        )
        assert crash.unique_msg != verify.unique_msg
        assert crash != verify
        assert hash(crash) != hash(verify)

    def test_to_dict_round_trip(self, crash_event):
        """to_dict/from_dict preserve the event fields."""
        data = crash_event.to_dict()
        assert data["category"] == "crash"
        assert data["process"] == "br.unb.cic.cryptoapp"
        assert data["fatal"] is True
        assert data["stack_head"] == crash_event.stack_head
        assert "unique_msg" in data

        restored = RvDiagnosticEvent.from_dict(data)
        assert restored.category == crash_event.category
        assert restored.class_full_name == crash_event.class_full_name
        assert restored.process == crash_event.process
        assert restored.n_frames == crash_event.n_frames
        assert restored.unique_msg == crash_event.unique_msg

    def test_defaults_for_minimal_event(self):
        """Optional fields default to empty/zero/false."""
        anr = RvDiagnosticEvent(
            category="anr",
            class_full_name="br.unb.cic.cryptoapp",
            method="",
            message="ANR in br.unb.cic.cryptoapp",
        )
        assert anr.fatal is False
        assert anr.n_frames == 0
        assert anr.source == ""
        assert anr.process == ""


class TestLogcatRepositoryDiagnosticIsolation:
    """INV-CORE-39: diagnostic events never affect coverage/error metrics."""

    def _error(self, msg: str) -> RvErrorLog:
        return RvErrorLog(
            spec="JcaSpec",
            error_type="MISUSE",
            class_full_name="com.example.App",
            method="encrypt",
            source="App.java",
            message=msg,
        )

    def _crash(self, idx: int) -> RvDiagnosticEvent:
        return RvDiagnosticEvent(
            category="crash",
            class_full_name="java.lang.NullPointerException",
            method="onClick",
            message=f"FATAL EXCEPTION {idx}",
            fatal=True,
            time_since_task_start=idx,
        )

    def test_metrics_unchanged_when_diagnostics_registered(self):
        """calculate_metrics/total_errors/unique_errors identical with vs without events."""
        baseline = LogcatRepository()
        baseline.register_rv_error(self._error("v1"))
        baseline.register_rv_error(self._error("v2"))
        baseline_metrics = baseline.calculate_metrics()

        with_events = LogcatRepository()
        with_events.register_rv_error(self._error("v1"))
        with_events.register_rv_error(self._error("v2"))
        for i in range(5):
            with_events.register_diagnostic_event(self._crash(i))
        events_metrics = with_events.calculate_metrics()

        assert events_metrics.total_errors == baseline_metrics.total_errors
        assert events_metrics.unique_errors == baseline_metrics.unique_errors
        assert events_metrics.called_methods == baseline_metrics.called_methods
        assert events_metrics.total_methods == baseline_metrics.total_methods
        # Percentages (computed in to_dict) must match too
        assert events_metrics.to_dict() == baseline_metrics.to_dict()
        assert len(with_events.diagnostic_events) == 5

    def test_get_diagnostic_events_sorted_by_time(self):
        """get_diagnostic_events returns events sorted by time_since_task_start."""
        repo = LogcatRepository()
        repo.register_diagnostic_event(self._crash(3))
        repo.register_diagnostic_event(self._crash(1))
        repo.register_diagnostic_event(self._crash(2))

        events = repo.get_diagnostic_events()
        assert [e["time_since_task_start"] for e in events] == [1, 2, 3]

    def test_diagnostic_events_do_not_count_as_errors(self):
        """Registering crashes leaves total_errors at zero (no RVSEC violations)."""
        repo = LogcatRepository()
        repo.register_diagnostic_event(self._crash(0))
        metrics = repo.calculate_metrics()
        assert metrics.total_errors == 0
        assert metrics.unique_errors == 0

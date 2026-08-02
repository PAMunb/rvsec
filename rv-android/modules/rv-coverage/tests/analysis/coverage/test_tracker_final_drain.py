"""Tests for the final drain performed when the tracking thread stops.

The tail loop exits on the stop signal without a last read, so every line
appended since its previous `readlines()` used to be lost. The repository is
the only input `CoverageComponent.process_results()` has on the live path,
while the resume path re-parses the whole file — so a missing drain is a
standing violation of INV-PLT-18 (live and reconstructed metrics must agree
within 0.01).

These tests use a real temporary file and the real background thread, because
what is under test is the interaction between the thread's exit and the
writes that race it.

The repository is seeded with a class and its methods, because
`LogcatRepository.register_method_call` only records calls to methods that
static analysis already knows about — an unseeded repository silently ignores
every RVSEC-COV line and would make these tests pass for the wrong reason.
"""

import time
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from rv_coverage.analysis.coverage.tracker import CoverageTracker
from rv_coverage.parser.log.logcat_parser import parse_logcat_file

# The tail loop sleeps 0.5 s with data and 1.0 s idle. Waiting longer than one
# idle cycle guarantees the loop has completed an iteration and is parked, so
# lines appended afterwards are genuinely unread and only the drain can
# recover them.
TAIL_CYCLE_SECONDS = 1.3

APP_CLASS = "br.unb.cic.cryptoapp.MainActivity"
METHODS = (
    "seenByTheLoop",
    "appendedAfterA",
    "appendedAfterB",
    "appendedAfterC",
    "methodOne",
    "methodTwo",
    "drainedLine",
    "neverRead",
    "onlyOnce",
)


def signature_of(method: str) -> str:
    """Soot signature as the RVSEC-COV instrumentation emits it."""
    return f"<{APP_CLASS}: void {method}()>"


def coverage_line(method: str) -> str:
    """Build an RVSEC-COV logcat line naming one method."""
    return f"03-24 19:36:38.394  4110  4110 V RVSEC-COV: {signature_of(method)}\n"


def violation_line(method: str) -> str:
    """Build an RVSEC logcat line carrying one monitored-operation violation."""
    return (
        f"03-24 19:36:39.000  4110  4110 E RVSEC: "
        f"TestSpec,{APP_CLASS},init,{method},Main.java,ERROR_STATE,bad usage\n"
    )


def static_data():
    """The static universe both the live and the reconstruction path start from.

    `initialize_repository_from_static_data` only reads attributes, so a
    structural stand-in is enough and keeps the fixture readable.
    """
    methods = [
        SimpleNamespace(
            class_name=APP_CLASS,
            name=method,
            signature=signature_of(method),
            params=[],
            reachable=True,
            reaches_target=False,
            directly_reaches_target=False,
        )
        for method in METHODS
    ]
    class_info = SimpleNamespace(
        component_type="ACTIVITY", is_main=True, methods=methods
    )
    return SimpleNamespace(classes=SimpleNamespace(classes={APP_CLASS: class_info}))


@pytest.fixture
def logcat_file(tmp_path):
    path = tmp_path / "task.logcat"
    path.write_text("")
    return str(path)


@pytest.fixture
def tracker(logcat_file):
    tracker = CoverageTracker(
        logcat_file=logcat_file,
        static_data=static_data(),
        task_start_time=datetime.now(),
    )
    yield tracker
    if tracker.is_running:
        tracker.stop()


def append(path: str, text: str) -> None:
    with open(path, "a") as handle:
        handle.write(text)
        handle.flush()


def called_methods(tracker: CoverageTracker) -> set:
    """Method names the repository has recorded as executed."""
    return {
        method.method_name
        for class_data in tracker.repository.classes.values()
        for method in class_data.methods.values()
        if method.called
    }


class TestFinalDrain:
    """Lines written after the last tail iteration still reach the repository."""

    def test_drain_recovers_trailing_lines(self, tracker, logcat_file):
        tracker.start()
        append(logcat_file, coverage_line("seenByTheLoop"))
        time.sleep(TAIL_CYCLE_SECONDS)

        assert called_methods(tracker) == {"seenByTheLoop"}

        # The loop is parked now; these three lines are written into the gap
        # between its last read and the stop signal.
        append(logcat_file, coverage_line("appendedAfterA"))
        append(logcat_file, coverage_line("appendedAfterB"))
        append(logcat_file, coverage_line("appendedAfterC"))

        tracker.stop()

        assert called_methods(tracker) == {
            "seenByTheLoop",
            "appendedAfterA",
            "appendedAfterB",
            "appendedAfterC",
        }
        assert tracker.repository.calculate_metrics().to_dict()["called_methods"] == 4

    def test_drain_does_not_double_count(self, tracker, logcat_file):
        """A violation the loop already processed is not registered twice."""
        tracker.start()
        append(logcat_file, violation_line("alreadyRead"))
        time.sleep(TAIL_CYCLE_SECONDS)

        errors_before_stop = len(tracker.repository.errors)
        assert errors_before_stop == 1

        append(logcat_file, violation_line("readByTheDrain"))
        tracker.stop()

        assert len(tracker.repository.errors) == errors_before_stop + 1

    def test_drain_precedes_flush_diagnostics(self, tracker, logcat_file):
        """A diagnostic event completed by a drained line must still be emitted,
        which is only possible if the drain runs first."""
        order = []
        real_process_lines = tracker.process_lines
        real_flush = tracker.flush_diagnostics

        def record_process(lines):
            if lines:
                order.append("process")
            return real_process_lines(lines)

        def record_flush():
            order.append("flush")
            return real_flush()

        tracker.process_lines = record_process
        tracker.flush_diagnostics = record_flush

        tracker.start()
        time.sleep(TAIL_CYCLE_SECONDS)
        append(logcat_file, coverage_line("drainedLine"))
        tracker.stop()

        assert "flush" in order, "flush_diagnostics never ran"
        assert "process" in order, "the drain processed nothing"
        assert order.index("process") < order.index(
            "flush"
        ), f"drain must precede flush_diagnostics, got {order}"

    def test_read_failure_during_drain_does_not_propagate(self, tracker, logcat_file):
        """stop() is invoked from a `finally` on the platform side, where a
        raised exception would replace the exception being propagated."""
        tracker.start()
        time.sleep(TAIL_CYCLE_SECONDS)
        append(logcat_file, coverage_line("neverRead"))

        with patch.object(
            tracker, "process_lines", side_effect=OSError("disk went away")
        ):
            tracker.stop()

        assert tracker.is_running is False

    def test_stopping_an_already_stopped_tracker_is_inert(self, tracker, logcat_file):
        """The platform now finalizes from a single owner while
        _cleanup_components() still calls cleanup() afterwards, so a second
        stop() happens on every task."""
        tracker.start()
        append(logcat_file, coverage_line("onlyOnce"))
        time.sleep(TAIL_CYCLE_SECONDS)
        tracker.stop()

        metrics_after_first_stop = tracker.repository.calculate_metrics().to_dict()

        tracker.stop()

        assert (
            tracker.repository.calculate_metrics().to_dict() == metrics_after_first_stop
        )


class TestLiveMatchesReparse:
    """INV-PLT-18: live metrics equal the metrics obtained by re-parsing."""

    def test_live_metrics_match_parse_logcat_file(self, tracker, logcat_file):
        """The producer stops first (nothing writes after `stop()` here), then
        the tracker drains — which is exactly the order the platform enforces."""
        task_start = tracker.tool_execution_start_time

        tracker.start()
        append(logcat_file, coverage_line("methodOne"))
        append(logcat_file, violation_line("methodOne"))
        time.sleep(TAIL_CYCLE_SECONDS)
        # Written into the gap the drain exists to close.
        append(logcat_file, coverage_line("methodTwo"))
        append(logcat_file, violation_line("methodTwo"))
        tracker.stop()

        live = tracker.repository.calculate_metrics().to_dict()

        # The reconstruction path rebuilds from the file plus the same static
        # analysis data, which is what ResultProcessorComponent does on resume.
        reparsed = (
            parse_logcat_file(
                logcat_file,
                static_data=static_data(),
                tool_execution_start=task_start,
            )
            .calculate_metrics()
            .to_dict()
        )

        for field, live_value in live.items():
            if isinstance(live_value, bool) or not isinstance(live_value, (int, float)):
                continue
            assert (
                abs(live_value - reparsed[field]) <= 0.01
            ), f"{field}: live={live_value} reparsed={reparsed[field]}"

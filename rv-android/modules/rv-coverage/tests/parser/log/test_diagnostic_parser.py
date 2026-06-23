"""Tests for the stateful DiagnosticEventParser (gh72).

Covers the analysis delta-spec scenarios:
- Multi-line AndroidRuntime FATAL assembled into one crash event.
- Event closes on tag/pid change and flush at EOF.
- VerifyError at class load (art).
- ANR event.
- RVSEC/COV path produces no diagnostic events.
- Tag-field match avoids the isAndroidRuntime() substring false positive (INV-ANA-47).
"""

from pathlib import Path

from rv_coverage.parser.log.diagnostic_parser import DiagnosticEventParser

FIXTURES = Path(__file__).parent / "fixtures"


def _feed_file(parser: DiagnosticEventParser, path: Path):
    """Feed every line of a fixture and return the list of emitted events."""
    events = []
    with open(path, "r") as f:
        for line in f:
            event = parser.feed_line(line)
            if event:
                events.append(event)
    tail = parser.flush()
    if tail:
        events.append(tail)
    return events


class TestCrashAssembly:
    def test_multiline_fatal_assembled_into_one_event(self):
        parser = DiagnosticEventParser()
        events = _feed_file(parser, FIXTURES / "crash_npe.logcat")

        assert len(events) == 1
        crash = events[0]
        assert crash.category == "crash"
        assert crash.fatal is True
        assert crash.class_full_name == "java.lang.NullPointerException"
        assert crash.process == "br.unb.cic.cryptoapp"
        assert crash.pid == "7071"
        assert crash.message == "FATAL EXCEPTION: main"

    def test_app_frame_selected_for_stack_head(self):
        """stack_head/method/source point to the app frame (by package), not the
        framework frame that is physically first in the trace."""
        parser = DiagnosticEventParser()
        crash = _feed_file(parser, FIXTURES / "crash_npe.logcat")[0]

        assert (
            crash.stack_head
            == "br.unb.cic.cryptoapp.MainActivity$1.onMenuItemClick(MainActivity.java:50)"
        )
        assert crash.method == "onMenuItemClick"
        assert crash.source == "MainActivity.java:50"

    def test_n_frames_counts_only_at_frames(self):
        parser = DiagnosticEventParser()
        crash = _feed_file(parser, FIXTURES / "crash_npe.logcat")[0]
        # Four "\tat" frames; "... 11 more" and the Caused by header are not frames.
        assert crash.n_frames == 4

    def test_original_msg_preserves_full_block(self):
        parser = DiagnosticEventParser()
        crash = _feed_file(parser, FIXTURES / "crash_npe.logcat")[0]
        assert "FATAL EXCEPTION: main" in crash.original_msg
        assert "Caused by: java.lang.NullPointerException" in crash.original_msg
        # The non-threadtime separator line is skipped, not buffered.
        assert "beginning of crash" not in crash.original_msg


class TestEventClosing:
    def test_event_closes_on_tag_change_then_flush(self):
        """A crash followed by an RVSEC-COV line closes on the key change; flush
        at EOF emits nothing more (the crash was already closed)."""
        parser = DiagnosticEventParser()
        crash_lines = [
            "06-23 12:00:01.100  7071  7071 E AndroidRuntime: FATAL EXCEPTION: main\n",
            "06-23 12:00:01.100  7071  7071 E AndroidRuntime: Process: com.x, PID: 7071\n",
            "06-23 12:00:01.100  7071  7071 E AndroidRuntime: java.lang.IllegalStateException: bad\n",
            "06-23 12:00:01.100  7071  7071 E AndroidRuntime: \tat com.x.A.m(A.java:1)\n",
        ]
        emitted = [parser.feed_line(line) for line in crash_lines]
        assert all(e is None for e in emitted)

        # An RVSEC-COV line (different tag) closes the buffered crash.
        closing = parser.feed_line(
            "06-23 12:00:02.000  7071  7071 I RVSEC-COV: <com.x.A: void m()>\n"
        )
        assert closing is not None
        assert closing.category == "crash"
        assert closing.class_full_name == "java.lang.IllegalStateException"

        # Nothing left buffered.
        assert parser.flush() is None

    def test_flush_emits_last_buffered_event(self):
        """When input ends mid-crash, flush() emits the buffered event."""
        parser = DiagnosticEventParser()
        parser.feed_line(
            "06-23 12:00:01.100  900  900 E AndroidRuntime: FATAL EXCEPTION: main\n"
        )
        parser.feed_line(
            "06-23 12:00:01.100  900  900 E AndroidRuntime: java.lang.RuntimeException: x\n"
        )
        tail = parser.flush()
        assert tail is not None
        assert tail.category == "crash"
        # flush is idempotent.
        assert parser.flush() is None


class TestVerifyError:
    def test_art_rejecting_class(self):
        parser = DiagnosticEventParser()
        events = _feed_file(parser, FIXTURES / "verify_error.logcat")
        assert len(events) == 1
        ve = events[0]
        assert ve.category == "verify_error"
        assert ve.class_full_name == "com.example.bad.BadClass"
        assert ve.fatal is False


class TestAnr:
    def test_anr_in_package(self):
        parser = DiagnosticEventParser()
        events = _feed_file(parser, FIXTURES / "anr.logcat")
        assert len(events) == 1
        anr = events[0]
        assert anr.category == "anr"
        assert anr.process == "br.unb.cic.cryptoapp"
        assert anr.class_full_name == "br.unb.cic.cryptoapp"

    def test_process_has_died(self):
        parser = DiagnosticEventParser()
        event = parser.feed_line(
            "06-23 12:00:05.000 1000 1015 W ActivityManager: Process com.dead (pid 4242) has died\n"
        )
        # single-line event stays buffered until flush
        assert event is None
        died = parser.flush()
        assert died is not None
        assert died.category == "anr"
        assert died.process == "com.dead"


class TestNoFalsePositives:
    def test_rvsec_cov_lines_produce_no_events(self):
        """INV-ANA-47: tag-field match — RVSEC/RVSEC-COV lines (even one whose
        message contains isAndroidRuntime()) yield no diagnostic events."""
        parser = DiagnosticEventParser()
        events = _feed_file(parser, FIXTURES / "rvsec_false_positive.logcat")
        assert events == []

    def test_separator_and_nonmatching_lines_skipped(self):
        """INV-ANA-48: non-threadtime lines are skipped without error."""
        parser = DiagnosticEventParser()
        assert parser.feed_line("--------- beginning of crash\n") is None
        assert parser.feed_line("not a logcat line at all\n") is None
        assert parser.feed_line("\n") is None
        assert parser.flush() is None

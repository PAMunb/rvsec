"""
Tests for the offline clock-to-violation join (gh90 group 4, INV-APV-35).

The corpus test is the sharpest gate in the change: reproducing 9,586 `RVSEC`
lines across exactly 605 runs and 32 APKs over the recorded iter0 traces is a
three-way check no plausible-but-wrong join passes by accident. It is skipped
when that tree is absent rather than failing, and it never writes to it.
"""

import hashlib
from pathlib import Path

import pytest

from aperv_tool.analysis.clock_logcat_join import (
    JoinReport,
    Phase,
    join_run,
    join_tree,
    main,
)

CORPUS = Path(__file__).resolve().parents[3] / "experimento-cal" / "iter0" / "results"

# A run whose logcat carries violations at launch and again at teardown.
RUN_WITH_VIOLATIONS = (
    CORPUS
    / "cala_00/cala_00/at.linuxtage.Eventfahrplan_1700028.apk"
    / "at.linuxtage.Eventfahrplan_1700028.apk__1__300__aperv:cal_a1.trace"
)

requires_corpus = pytest.mark.skipif(
    not CORPUS.is_dir(), reason="recorded iter0 corpus not present in this checkout"
)

# 2026-07-23T23:42:17.964Z, rendered by a device at UTC-3 as 20:42:17.964. The
# offset is what the join has to recover without being told.
FIRST_STEP_MS = 1784850137964
STEP_INTERVAL_MS = 10_000


def _step(index, activity="com.example.MainActivity"):
    clock = FIRST_STEP_MS + index * STEP_INTERVAL_MS
    return (
        f"[APE] [APE-STEP] step={index + 1} clock={clock} activity={activity} "
        f"state={activity}@1@Naming[0]@[W=3] action=g0a0@MODEL_CLICKclass=android.view.View "
        f"decision_source=Coverage priority=100 mop=0 wtg=0 coverage=100 menu=0 form=0"
    )


def _logcat_line(
    hour,
    minute,
    second,
    millis,
    tag="RVSEC   ",
    payload="Spec,c,C,m,F.kt:1,UnsafeAlgorithm,expecting one of A,B but found C.",
):
    return f"07-23 {hour:02d}:{minute:02d}:{second:02d}.{millis:03d}  3035  3035 V {tag}: {payload}"


def _write_run(
    tmp_path, steps=(), logcat_lines=(), name="app.apk__1__300__aperv:cal_a1"
):
    """Write a synthetic (.trace, .logcat) pair for one run."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    trace = tmp_path / f"{name}.trace"
    trace.write_text(
        "[APE] *** INFO *** Let's wait for activity loading...\n"
        + "\n".join(steps)
        + ("\n" if steps else "")
    )
    logcat = tmp_path / f"{name}.logcat"
    logcat.write_text("--------- beginning of main\n" + "\n".join(logcat_lines) + "\n")
    return trace


class TestClockAlignment:
    """The two clocks are one device clock rendered two ways."""

    def test_zone_offset_is_recovered_not_assumed(self, tmp_path):
        # Capture starts 6.696 s before the first step; the device runs at UTC-3.
        trace = _write_run(
            tmp_path,
            steps=[_step(0), _step(1)],
            logcat_lines=[
                _logcat_line(20, 42, 11, 268, tag="ActivityManager"),
                _logcat_line(20, 42, 27, 964),
            ],
        )

        run = join_run(trace)

        assert run.clock_offset_ms == 3 * 60 * 60 * 1000
        # What the rounding leaves over is the measured capture-to-first-step gap.
        assert run.alignment_residual_ms == 6696

    def test_violation_lands_on_the_step_that_was_executing(self, tmp_path):
        # Violation at 20:42:27.964 device time = first step + 10 s = step 2.
        trace = _write_run(
            tmp_path,
            steps=[_step(0), _step(1), _step(2)],
            logcat_lines=[
                _logcat_line(20, 42, 11, 268, tag="ActivityManager"),
                _logcat_line(20, 42, 27, 964),
            ],
        )

        violation = join_run(trace).violations[0]

        assert violation.phase is Phase.EXPLORATION
        assert violation.step == 2
        assert violation.activity == "com.example.MainActivity"
        assert violation.seconds_from_first_step == pytest.approx(10.0)

    def test_violation_before_the_first_step_is_pre_exploration(self, tmp_path):
        trace = _write_run(
            tmp_path,
            steps=[_step(0), _step(1)],
            logcat_lines=[_logcat_line(20, 42, 15, 964)],
        )

        violation = join_run(trace).violations[0]

        assert violation.phase is Phase.PRE_EXPLORATION
        assert violation.step is None
        # The distance is what separates a launch-time monitor from a line the
        # uncleared buffer carried over from an earlier run.
        assert violation.seconds_from_first_step == pytest.approx(-2.0)

    def test_violation_after_the_last_step_is_post_exploration(self, tmp_path):
        trace = _write_run(
            tmp_path,
            steps=[_step(0), _step(1)],
            logcat_lines=[
                _logcat_line(20, 42, 11, 268, tag="ActivityManager"),
                _logcat_line(20, 45, 0, 0),
            ],
        )

        assert join_run(trace).violations[0].phase is Phase.POST_EXPLORATION

    def test_run_without_steps_is_unaligned_but_still_counted(self, tmp_path):
        # The `ape` arm emits no [APE-STEP] at all — 80 of the corpus's 880 runs.
        # Its violations are real and must not vanish for lack of a timeline.
        trace = _write_run(
            tmp_path, steps=[], logcat_lines=[_logcat_line(20, 42, 27, 964)]
        )

        run = join_run(trace)

        assert run.steps == 0
        assert run.violation_lines == 1
        assert run.violations[0].phase is Phase.UNALIGNED
        assert run.clock_offset_ms is None


class TestViolationLines:
    """Which logcat lines count, and how their payload splits."""

    def test_coverage_stream_is_not_mistaken_for_violations(self, tmp_path):
        # RVSEC-COV is the coverage tag: ~100k lines per file against a handful of
        # violations. Admitting it would inflate the gate by four orders.
        trace = _write_run(
            tmp_path,
            steps=[_step(0)],
            logcat_lines=[
                "07-23 20:42:11.268  3035  3035 I RVSEC-COV: <com.example.A: void <init>()>",
                _logcat_line(20, 42, 17, 964),
            ],
        )

        assert join_run(trace).violation_lines == 1

    def test_message_commas_do_not_shift_the_violation_type(self, tmp_path):
        # The message legally contains commas ("expecting one of A,B but found C"),
        # so an unbounded split would report the wrong type.
        trace = _write_run(
            tmp_path, steps=[_step(0)], logcat_lines=[_logcat_line(20, 42, 17, 964)]
        )

        violation = join_run(trace).violations[0]

        assert violation.spec == "Spec"
        assert violation.violation_type == "UnsafeAlgorithm"
        assert violation.message == "expecting one of A,B but found C."

    def test_run_without_violations_is_reported_not_omitted(self, tmp_path):
        # 275 of the 880 recorded runs look like this. "No violation" is a
        # measurement, so the run keeps its row.
        trace = _write_run(tmp_path, steps=[_step(0)], logcat_lines=[])

        run = join_run(trace)

        assert run.violation_lines == 0
        assert run.violations == ()
        assert run.has_violations is False

    def test_missing_logcat_is_zero_violations_not_an_error(self, tmp_path):
        trace = _write_run(tmp_path, steps=[_step(0)], logcat_lines=[])
        trace.with_suffix(".logcat").unlink()

        assert join_run(trace).violation_lines == 0


@requires_corpus
class TestRecordedCorpus:
    """The validation gate, over read-only recorded artifacts."""

    def test_join_reproduces_iter0_totals(self):
        # Three totals at once (task 4.3). The 12 cala_smoke_* runs are excluded:
        # they ran at timeout=90, outside the campaign's 880.
        report = JoinReport(
            runs=tuple(
                run
                for run in join_tree(CORPUS).runs
                if "smoke" not in str(run.trace_path)
            )
        )

        assert len(report.runs) == 880
        assert report.violation_lines == 9586
        assert report.runs_with_violations == 605
        assert report.apks_with_violations == 32
        # 605 violation-bearing + 275 violation-free = 880: the accounting is
        # exhaustive, which is what makes the three totals a real check.
        assert len(report.runs) - report.runs_with_violations == 275

    def test_artifacts_are_never_modified(self):
        # INV-APV-35: read-only over recorded artifacts.
        paths = [RUN_WITH_VIOLATIONS, RUN_WITH_VIOLATIONS.with_suffix(".logcat")]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

        join_run(RUN_WITH_VIOLATIONS)

        for path, digest in before.items():
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest

    def test_recorded_alignment_stays_inside_the_rounding_tolerance(self):
        # The anchor is only sound while the capture-to-first-step gap stays well
        # under the ±7.5 min the quarter-hour rounding allows.
        run = join_run(RUN_WITH_VIOLATIONS)

        assert run.clock_offset_ms is not None
        assert abs(run.alignment_residual_ms) < 60_000


class TestCli:
    def test_missing_directory_is_usage_error(self, tmp_path, capsys):
        missing = tmp_path / "nope"

        with pytest.raises(SystemExit) as exit_info:
            main([str(missing)])

        assert exit_info.value.code == 2
        assert str(missing) in capsys.readouterr().err

    def test_wrong_argument_count_is_usage_error(self):
        with pytest.raises(SystemExit) as exit_info:
            main([])

        assert exit_info.value.code == 2

    def test_run_without_violations_still_emits_a_row(self, tmp_path, capsys):
        _write_run(tmp_path, steps=[_step(0)], logcat_lines=[])

        assert main([str(tmp_path)]) == 0

        rows = capsys.readouterr().out.splitlines()
        assert rows[0].startswith("apk,repetition,timeout,arm,steps,violation_lines")
        assert len(rows) == 2

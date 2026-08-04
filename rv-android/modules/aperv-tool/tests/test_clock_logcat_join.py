"""
Tests for the offline clock-to-violation join (gh90 group 4, INV-APV-35).

The corpus test is the sharpest gate in the change: reproducing 9,586 `RVSEC`
lines across exactly 605 runs and 32 APKs over the recorded iter0 traces is a
three-way check no plausible-but-wrong join passes by accident. It is skipped
when that tree is absent rather than failing, and it never writes to it.
"""

import hashlib
import json
from pathlib import Path

import pytest

from aperv_tool.analysis.clock_logcat_join import (
    JoinReport,
    Phase,
    _read_heartbeats,
    _read_steps,
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

# Run-local `ACT` dictionary IDs. Stage-4 records reference an activity by
# integer and the reader resolves it, so a synthetic trace has to define the
# entry before any record that uses it (INV-SNK-06).
_ACTIVITY_IDS = {
    "com.example.MainActivity": 1,
    "com.example.SecondActivity": 2,
}


def _step(index, activity="com.example.MainActivity"):
    """One stage-4 `StepRecord`, as the sink writes it.

    `t` is run-relative and the trace's `RUN_START` carries `t0=FIRST_STEP_MS`,
    so step *i* still lands at `FIRST_STEP_MS + i * STEP_INTERVAL_MS` on the
    epoch clock — the same instant the retired `[APE-STEP] clock=` field named.
    The migration changed where the step series comes from, not what it means.
    """
    return json.dumps(
        {
            "s": index + 1,
            "t": index * STEP_INTERVAL_MS,
            "act": _ACTIVITY_IDS[activity],
            "st": 1,
            "dec": {
                "a": "g0a0@MODEL_CLICK class=android.view.View",
                "src": "Coverage",
                "ch": "roulette_greedy",
                "pri": 100,
                "cov": 100,
            },
        },
        separators=(",", ":"),
    )


def _heartbeat(index, hour, minute, second, millis):
    """One `ApeRvHb` logcat line for step *index*, as the stage-4 jar writes it."""
    return _logcat_line(
        hour,
        minute,
        second,
        millis,
        tag="ApeRvHb ",
        payload=f"s={index + 1} t={index * STEP_INTERVAL_MS}",
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


def _preamble():
    """`RUN_START` plus the dictionary entries every step record references.

    The free-text `[APE] ` line is kept because a real trace interleaves them
    into the same stdout, and the reader has to step over them without counting
    them as damage.
    """
    lines = [
        json.dumps(
            {
                "type": "RUN_START",
                "run_id": "app.apk__1__300__aperv:cal_a1",
                "t0": FIRST_STEP_MS,
                "params": {},
            },
            separators=(",", ":"),
        ),
        "[APE] *** INFO *** Let's wait for activity loading...",
    ]
    for activity, act_id in _ACTIVITY_IDS.items():
        lines.append(
            json.dumps(
                {"type": "ACT", "id": act_id, "name": activity, "mop": 0},
                separators=(",", ":"),
            )
        )
    lines.append(
        json.dumps(
            {"type": "STATE", "id": 1, "key": "S1", "act": 1}, separators=(",", ":")
        )
    )
    return lines


def _write_run(
    tmp_path, steps=(), logcat_lines=(), name="app.apk__1__300__aperv:cal_a1"
):
    """Write a synthetic (.trace, .logcat) pair for one run."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    trace = tmp_path / f"{name}.trace"
    trace.write_text("\n".join([*_preamble(), *steps]) + "\n")
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


class TestStepsComeFromTheReader:
    """The step series is read through the native NDJSON reader (task 5.1)."""

    def test_steps_are_keyed_by_step_number(self, tmp_path):
        trace = _write_run(tmp_path, steps=[_step(0), _step(1), _step(2)])

        steps = _read_steps(trace)

        assert sorted(steps) == [1, 2, 3]
        assert steps[2].activity == "com.example.MainActivity"
        # The epoch clock is expanded from RUN_START.t0 + t, which is the same
        # instant the retired `clock=` field carried.
        assert steps[2].t_epoch_ms == FIRST_STEP_MS + STEP_INTERVAL_MS

    def test_free_text_and_dictionary_records_yield_no_steps(self, tmp_path):
        """A trace with a preamble but no step record has no steps, not an error."""
        trace = _write_run(tmp_path, steps=[])

        assert _read_steps(trace) == {}


class TestHeartbeats:
    """The per-step heartbeat lines the stage-4 jar writes into logcat.

    These are the fixtures the placement migration (5.5, gated on the recorded
    device evidence of INV-APV-54) will consume. Until then they pin the parse:
    a heartbeat carries a step number and its run-relative offset, on the same
    clock and in the same rendering as the `RVSEC` lines beside it.
    """

    def test_heartbeats_are_read_with_step_and_relative_time(self, tmp_path):
        trace = _write_run(
            tmp_path,
            steps=[_step(0), _step(1)],
            logcat_lines=[
                _heartbeat(0, 20, 42, 17, 964),
                _logcat_line(20, 42, 20, 100),
                _heartbeat(1, 20, 42, 27, 964),
            ],
        )

        heartbeats = _read_heartbeats(trace.with_suffix(".logcat"))

        assert [(step, rel) for _, step, rel in heartbeats] == [
            (1, 0),
            (2, STEP_INTERVAL_MS),
        ]
        # The stamps are the logcat's own rendering: no year, no zone, and none
        # is invented here — placement compares two stamps from this one file.
        first_stamp = heartbeats[0][0]
        assert (first_stamp.hour, first_stamp.minute, first_stamp.second) == (
            20,
            42,
            17,
        )

    def test_heartbeat_steps_match_the_trace_step_records(self, tmp_path):
        """The two series agree, which is the whole point of the heartbeat."""
        trace = _write_run(
            tmp_path,
            steps=[_step(0), _step(1), _step(2)],
            logcat_lines=[
                _heartbeat(0, 20, 42, 17, 964),
                _heartbeat(1, 20, 42, 27, 964),
                _heartbeat(2, 20, 42, 37, 964),
            ],
        )

        steps = _read_steps(trace)
        heartbeats = _read_heartbeats(trace.with_suffix(".logcat"))

        assert [step for _, step, _ in heartbeats] == sorted(steps)
        for _, step, rel in heartbeats:
            assert steps[step].t_rel_ms == rel

    def test_logcat_without_heartbeat_yields_none(self, tmp_path):
        """A capture with violations but no heartbeat is the honest empty case.

        It happens when the tag is outside the device-side allowlist, or the
        jar predates stage 4. Nothing is reconstructed to compensate — the run
        keeps its violation lines and its denominator.
        """
        trace = _write_run(
            tmp_path,
            steps=[_step(0), _step(1)],
            logcat_lines=[
                _logcat_line(20, 42, 11, 268, tag="ActivityManager"),
                _logcat_line(20, 42, 27, 964),
            ],
        )

        assert _read_heartbeats(trace.with_suffix(".logcat")) == []

        run = join_run(trace)
        assert run.violation_lines == 1
        assert len(run.violations) == 1

    def test_coverage_stream_is_not_mistaken_for_a_heartbeat(self, tmp_path):
        """Tag matching is on the tag field, never a substring of the payload."""
        trace = _write_run(
            tmp_path,
            steps=[_step(0)],
            logcat_lines=[
                _logcat_line(
                    20, 42, 18, 0, tag="RVSEC-COV", payload="<com.x.A: void s=1 t=0()>"
                ),
                _heartbeat(0, 20, 42, 17, 964),
            ],
        )

        heartbeats = _read_heartbeats(trace.with_suffix(".logcat"))

        assert [step for _, step, _ in heartbeats] == [1]


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

    def test_legacy_recorded_trace_yields_no_steps_and_stays_in_the_report(self):
        """A legacy trace is no longer readable, and that is the intended break.

        The join reads its step series through the native NDJSON reader, so the
        `[APE-*]` `key=value` corpus recorded before stage 4 contributes no
        steps. There is deliberately no format sniffer and no fallback branch:
        the frozen-corpus scripts named by INV-APV-55 are what read that data,
        and they are untouched.

        What must NOT break is the accounting. The violation series comes from
        the logcat, which stage 4 does not change, so the run keeps its
        violation lines and stays in the report with its denominator — its
        violations are simply reported as `UNALIGNED` rather than placed against
        a fabricated clock.
        """
        run = join_run(RUN_WITH_VIOLATIONS)

        assert run.steps == 0
        assert run.clock_offset_ms is None
        assert run.violation_lines > 0
        assert len(run.violations) == run.violation_lines
        assert all(v.phase is Phase.UNALIGNED for v in run.violations)
        assert all(v.timestamp_ms is None for v in run.violations)
        # The payload is still parsed: what is unavailable is the placement.
        assert all(v.spec for v in run.violations)


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

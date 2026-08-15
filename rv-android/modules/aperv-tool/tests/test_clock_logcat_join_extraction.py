"""The placement rule and the line reader, now that they are public and tagged.

`place_on_timeline` and `read_tagged_lines` were lifted out of `join_run` so that
every logcat stream is placed by one rule rather than by a copy per consumer
(INV-APV-63). Two things have to be true for that to be worth doing, and this
file asserts both: the extraction changed nothing about the join it came from,
and the extracted pair really is tag-agnostic — `RVSEC-COV` places by the same
rule, and neither tag admits the other's lines.

`test_clock_logcat_join.py` is deliberately not touched, so that "the existing
suite passes unmodified" stays checkable with `git diff` rather than by reading.
The new cases live here instead.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
from pathlib import Path

import pytest

from aperv_tool.analysis.clock_logcat_join import (
    Phase,
    RunJoin,
    join_run,
    place_on_timeline,
    read_tagged_lines,
)

# The same epoch base and step cadence the sibling suite uses, so a value read
# here is comparable with one read there.
FIRST_STEP_MS = 1784850137964
STEP_INTERVAL_MS = 10_000

# The digest of the join's output over the run built below. It is the value the
# PRE-extraction implementation produced on this fixture, not one read off the
# code it now guards, and the two were also shown to agree field for field over
# all 892 recorded runs of `experimento-cal/iter0/results`. So it pins behaviour
# the extraction inherited rather than behaviour the extraction defined.
JOIN_DIGEST = "1b63b44e039d16828c713ed9e224b72ca8a99010a6814effe5d473b238561965"


def _line(hour, minute, second, millis, tag, payload):
    """One logcat line, with the tag padded as logcat pads it."""
    return (
        f"07-23 {hour:02d}:{minute:02d}:{second:02d}.{millis:03d}"
        f"  3035  3035 V {tag:<8}: {payload}"
    )


# Wall-clock second at which the run's first step opens, so that a heartbeat
# cadence expressed in seconds rolls over minutes the way the device's does.
FIRST_STEP_CLOCK = dt.time(20, 42, 17, 964_000)


def _at(seconds_after_first_step):
    """The `(hour, minute, second, millis)` of a stamp on the run's clock."""
    moment = dt.datetime.combine(dt.date(1900, 7, 23), FIRST_STEP_CLOCK) + dt.timedelta(
        seconds=seconds_after_first_step
    )
    return moment.hour, moment.minute, moment.second, moment.microsecond // 1000


def _heartbeat(index):
    """The `ApeRvHb` line opening step *index*, ten seconds after the last."""
    return _line(
        *_at(index * STEP_INTERVAL_MS / 1000),
        "ApeRvHb",
        f"s={index + 1} t={index * STEP_INTERVAL_MS}",
    )


def _violation(hour, minute, second, millis, spec="Spec"):
    return _line(
        hour,
        minute,
        second,
        millis,
        "RVSEC",
        f"{spec},c,C,m,F.kt:1,UnsafeAlgorithm,expecting one of A,B but found C.",
    )


def _coverage(hour, minute, second, millis, signature="<c: void m()>"):
    return _line(hour, minute, second, millis, "RVSEC-COV", signature)


def _step(index):
    return json.dumps(
        {
            "s": index + 1,
            "t": index * STEP_INTERVAL_MS,
            "act": 1,
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


def _write_run(
    directory: Path, steps, logcat_lines, name="app.apk__1__300__aperv:cal_a1"
):
    directory.mkdir(parents=True, exist_ok=True)
    trace = directory / f"{name}.trace"
    trace.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "RUN_START",
                        "v": 1,
                        "run_id": name,
                        "t0": FIRST_STEP_MS,
                        "params": {},
                    },
                    separators=(",", ":"),
                ),
                "[APE] *** INFO *** Let's wait for activity loading...",
                json.dumps(
                    {
                        "type": "ACT",
                        "id": 1,
                        "name": "com.example.MainActivity",
                        "mop": 0,
                    },
                    separators=(",", ":"),
                ),
                json.dumps(
                    {"type": "STATE", "id": 1, "key": "S1", "act": 1},
                    separators=(",", ":"),
                ),
                *steps,
            ]
        )
        + "\n"
    )
    (directory / f"{name}.logcat").write_text(
        "--------- beginning of main\n" + "\n".join(logcat_lines) + "\n"
    )
    return trace


def _eight_step_run(directory: Path) -> Path:
    """Eight steps, eight heartbeats ten seconds apart, and one line per stream.

    The coverage line sits between heartbeat 7 and heartbeat 8, which is the
    interval the spec names; the violations bracket the window on both sides so
    every phase is exercised by the same fixture.
    """
    return _write_run(
        directory,
        steps=[_step(index) for index in range(8)],
        logcat_lines=[
            _line(*_at(-7), "ActivityManager", "Displayed com.example/.Main"),
            _violation(*_at(-3.5)),
            *[_heartbeat(index) for index in range(8)],
            # Heartbeat 7 opens at +60 s and heartbeat 8 at +70 s, so both of
            # these belong to step 7 — one per stream, placed by the one rule.
            _coverage(*_at(65)),
            _violation(*_at(66), spec="OtherSpec"),
            _violation(*_at(95), spec="LateSpec"),
        ],
    )


def _heartbeats_of(logcat: Path):
    """The run's heartbeats in the shape `place_on_timeline` takes them.

    Read through the public line reader, which is how `step_bundle` will reach
    them too: `s=<step> t=<run-relative ms>` is the payload the jar writes.
    """
    return [
        (stamp, int(payload.split()[0][2:]), int(payload.split()[1][2:]))
        for stamp, payload in read_tagged_lines(logcat, "ApeRvHb")
    ]


def _render(run: RunJoin) -> str:
    """A canonical rendering of every field of a `RunJoin`.

    The paths come out as basenames because the absolute ones carry the checkout
    location, which is not part of what the join computed.
    """
    record = dataclasses.asdict(run)
    record["trace_path"] = Path(record["trace_path"]).name
    record["logcat_path"] = Path(record["logcat_path"]).name
    for violation in record["violations"]:
        violation["phase"] = violation["phase"].value
    return json.dumps(record, sort_keys=True, default=str)


class TestJoinIsUnchanged:
    def test_join_unchanged_after_extraction(self, tmp_path):
        """Every field of the joined run still hashes to the recorded value.

        The extraction is the risk this change accepts: `join_run` is the one
        consumer of the placement rule that already has recorded output behind
        it, and a rule that moved and drifted would still place *something* for
        every violation. Hashing the whole `RunJoin` rather than asserting a
        field at a time is what makes a drift anywhere in the record fail here.
        """
        run = join_run(_eight_step_run(tmp_path))
        rendered = _render(run)

        assert hashlib.sha256(rendered.encode()).hexdigest() == JOIN_DIGEST, (
            "the join's output changed:\n" + rendered
        )

    def test_the_fixture_exercises_all_three_phases(self, tmp_path):
        """Non-vacuity: a digest over a run with one phase would prove little."""
        run = join_run(_eight_step_run(tmp_path))

        assert run.violation_lines == 3
        assert [violation.phase for violation in run.violations] == [
            Phase.PRE_EXPLORATION,
            Phase.EXPLORATION,
            Phase.POST_EXPLORATION,
        ]
        assert run.violations[1].step == 7
        assert run.violations[1].activity == "com.example.MainActivity"


class TestTagAgnosticReading:
    def test_rvsec_cov_lines_are_placed_by_the_same_rule(self, tmp_path):
        """A coverage line between heartbeats 7 and 8 belongs to step 7.

        Same file, same clock, same rule — the only difference is which tag was
        asked for. That is the whole point of taking the tag as an argument.
        """
        trace = _eight_step_run(tmp_path)
        logcat = trace.with_suffix(".logcat")

        heartbeats = _heartbeats_of(logcat)
        coverage = read_tagged_lines(logcat, "RVSEC-COV")

        assert len(coverage) == 1
        stamp, payload = coverage[0]
        assert payload == "<c: void m()>"

        phase, step, _anchor = place_on_timeline(stamp, heartbeats)
        assert phase is Phase.EXPLORATION
        assert step == 7, "the line falls between heartbeat 7 and heartbeat 8"

    def test_tag_matching_is_exact_never_a_prefix(self, tmp_path):
        """`RVSEC` does not admit `RVSEC-COV`, and the reverse holds too.

        The coverage stream outnumbers the violation stream by two orders of
        magnitude, so a prefix match here would not read as a bug — it would read
        as a hundredfold increase in violations.
        """
        trace = _eight_step_run(tmp_path)
        logcat = trace.with_suffix(".logcat")

        violations = read_tagged_lines(logcat, "RVSEC")
        coverage = read_tagged_lines(logcat, "RVSEC-COV")

        assert len(violations) == 3
        assert len(coverage) == 1
        assert all("<c: void m()>" not in payload for _stamp, payload in violations)
        assert all(",UnsafeAlgorithm," not in payload for _stamp, payload in coverage)

    def test_an_unlogged_tag_reads_as_an_empty_list(self, tmp_path):
        """Absence is a measurement: no line under a tag is not a failure."""
        trace = _eight_step_run(tmp_path)

        assert read_tagged_lines(trace.with_suffix(".logcat"), "AndroidRuntime") == []

    def test_a_tag_inside_a_payload_is_not_a_tag(self, tmp_path):
        """The tag is read from the tag position, not found anywhere in the line."""
        directory = tmp_path / "quoted"
        trace = _write_run(
            directory,
            steps=[_step(0)],
            logcat_lines=[
                _heartbeat(0),
                _line(*_at(1), "ActivityManager", "restarting RVSEC: monitor"),
            ],
        )

        assert read_tagged_lines(trace.with_suffix(".logcat"), "RVSEC") == []


class TestPlacementBoundaries:
    @pytest.mark.parametrize(
        "offset_s, expected_phase, expected_step",
        [
            (-1, Phase.PRE_EXPLORATION, None),
            (0, Phase.EXPLORATION, 1),
            (5, Phase.EXPLORATION, 1),
            (10, Phase.EXPLORATION, 2),
            (100, Phase.POST_EXPLORATION, None),
        ],
        ids=["before", "on_first", "inside", "on_second", "after"],
    )
    def test_a_stamp_lands_on_the_last_heartbeat_at_or_before_it(
        self, tmp_path, offset_s, expected_phase, expected_step
    ):
        """The boundaries are inclusive at the heartbeat: `<=`, not `<`.

        The jar logs the heartbeat as the step envelope opens, before dispatch,
        so an event sharing a heartbeat's millisecond belongs to that step rather
        than to the one before it.
        """
        trace = _eight_step_run(tmp_path)
        heartbeats = _heartbeats_of(trace.with_suffix(".logcat"))

        stamp = heartbeats[0][0] + dt.timedelta(seconds=offset_s)
        phase, step, _anchor = place_on_timeline(stamp, heartbeats)

        assert phase is expected_phase
        assert step == expected_step

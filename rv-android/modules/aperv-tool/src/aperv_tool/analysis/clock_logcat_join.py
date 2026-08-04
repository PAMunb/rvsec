"""
Offline join of a run's exploration clock against its violation log.

The MOP-frontier mechanism steers exploration toward screens whose code reaches a
monitored operation. It rests on a premise nobody has measured: that *reaching* a
MOP screen is enough to fire its monitor. The premise is plausible — the
monitored operation fires in `onCreate` for 84% of the apps, and UI handlers
account for 0.4% of direct reach — but if it is false, the mechanism is steering
toward screens that need interaction rather than arrival, and every conclusion
about MOP guidance is measuring the wrong thing.

This module produces the evidence. It reads the two artifacts a run already
leaves behind — the `.trace`, an NDJSON stream with one record per decision, and
the `.logcat` with one `RVSEC` line per violation — and places every violation on
the exploration timeline: before the first step, next to the step that was
executing, or after the last one. It is also the evidence base for the deferred
N5 decision (reading logcat at runtime): it establishes what signal a runtime
reader would have had, and with what latency, before any runtime mechanism is
proposed.

**The steps come from the native reader.** `analysis/trace_ndjson.py` is the one
way this module reads a trace: it yields a row per step with the epoch clock
already expanded from the run-relative `t` through `RUN_START.t0`. A run whose
trace carries no `RUN_START` has no absolute clock, and none is invented — its
violations are reported as `UNALIGNED` rather than placed against a guess.

**The two clocks are the same clock, rendered differently.** The step clock
is `System.currentTimeMillis()` inside the agent process; logcat stamps the same
device clock as local wall time, with no year and no zone. So the difference
between the two series is exactly the device's UTC offset — a multiple of 15
minutes, as every real UTC offset is — and it is recovered per run rather than
assumed: the year is chosen from the three candidates around the trace's own
clock, and the difference is rounded to the nearest quarter hour. The anchor is
the first logcat line of any tag, because logcat capture starts within seconds of
the run and stays inside the rounding tolerance even on an 1800 s budget, where
anchoring on the first *violation* could be off by twenty minutes and would round
to the wrong zone. What the rounding leaves over is kept as
`alignment_residual_ms`: it is the true gap between capture start and first step
(seconds, in practice), so a value of minutes is the signal that the anchoring
assumption does not hold for that run.

**A logcat file may hold more than its own run.** The buffer is not always
cleared between runs, so lines from an earlier run on the same device can appear
in the file. That is why a violation before the first step is reported as
`PRE_EXPLORATION` with its distance from that step, not as "fired at launch":
a violation 3 s before the first step is a launch-time monitor, one 300 s before
it is the previous run talking. The join records the distance and lets the
analysis draw the line.

Offline and read-only (INV-APV-35): no device, no emulator, no adb, and no
artifact is written.
"""

from __future__ import annotations

import csv
import datetime as dt
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from aperv_tool.analysis.trace_ndjson import StepRow, TraceReader

# `MM-DD HH:MM:SS.mmm  PID  TID  LEVEL TAG: message`, with the tag padded to eight
# characters. `RVSEC` is the violation tag; `RVSEC-COV` is the coverage tag and is
# a different, far more numerous stream — the pattern must not admit it.
_TIMESTAMP = (
    r"(?P<month>\d{2})-(?P<day>\d{2}) "
    r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})\.(?P<millis>\d{3})"
)
_VIOLATION_LINE = re.compile(
    rf"^{_TIMESTAMP}\s+\d+\s+\d+\s+[VDIWEF] RVSEC\s*:\s*(?P<payload>.*)$"
)
# Any stamped logcat line, used only to anchor the two clocks. The file opens
# with unstamped `--------- beginning of main` separators, which this skips.
_ANY_STAMPED_LINE = re.compile(rf"^{_TIMESTAMP}\s")

# The per-step heartbeat: `... I ApeRvHb: s=<step> t=<run-relative ms>`. The tag
# is the contract with the jar (`ape` design D-6) and is declared on this side in
# rv_android_core's logging constants, which put it in the capture allowlist.
_HEARTBEAT_LINE = re.compile(
    rf"^{_TIMESTAMP}\s+\d+\s+\d+\s+[VDIWEF] ApeRvHb\s*:\s*"
    r"s=(?P<step>\d+)\s+t=(?P<rel>\d+)"
)

# The logger emits `spec,class,simpleClass,method,location,violationType,message`
# and the message itself contains commas ("expecting one of {TLSv1.2, TLSv1.3}"),
# so the split is bounded at six and the remainder is the message.
_VIOLATION_FIELDS = 6

_QUARTER_HOUR_MS = 15 * 60 * 1000

# <apk>.apk__<repetition>__<timeout>__<tool>[:<variant>] — rv-platform's run identity.
_RUN_FILENAME = re.compile(
    r"^(?P<apk>.+\.apk)__(?P<repetition>\d+)__(?P<timeout>\d+)__(?P<arm>.+)$"
)


class Phase(str, Enum):
    """Where a violation sits on the exploration timeline."""

    PRE_EXPLORATION = "pre_exploration"
    EXPLORATION = "exploration"
    POST_EXPLORATION = "post_exploration"
    # The run has no `[APE-STEP]` line to align against — the `ape` arm emits
    # none at all, and a run that died at startup has none either. The violation
    # is still counted; only its position is unknown.
    UNALIGNED = "unaligned"


@dataclass(frozen=True)
class Violation:
    """One `RVSEC` line, placed on the run's exploration timeline.

    Attributes:
        timestamp_ms: Epoch milliseconds of the violation, obtained by adding
            the run's recovered clock offset to the logcat stamp. None when the
            run had no step to align against.
        spec: Specification whose monitor fired, as the logger names it.
        violation_type: Violation category reported by the logger. Empty when
            the payload does not carry the full field shape.
        message: Violation message. Holds the whole payload when the field
            shape is unexpected, so no information is dropped.
        phase: Where the violation sits relative to the exploration window.
        step: Step that was executing when the monitor fired: the last step at
            or before the violation. None outside the exploration window.
        activity: Activity that step was exploring. None outside the window.
        seconds_from_first_step: Signed distance from the first step, negative
            before exploration began. This is what separates a launch-time
            monitor (seconds before) from a leftover of an earlier run on the
            same device (minutes before).
    """

    timestamp_ms: int | None
    spec: str
    violation_type: str
    message: str
    phase: Phase
    step: int | None = None
    activity: str | None = None
    seconds_from_first_step: float | None = None


@dataclass(frozen=True)
class RunJoin:
    """One run's correlation between its step clock and its violation log.

    Attributes:
        trace_path: The `.trace` file that was read.
        logcat_path: Its `.logcat` sibling. Recorded even when absent, so the
            analysis can tell a run with no violations from a run with no log.
        apk: APK name parsed from the run filename. None when the filename does
            not follow rv-platform's run identity.
        repetition: Repetition index from the run filename.
        timeout_seconds: Exploration budget from the run filename.
        arm: Tool and variant from the run filename, e.g. `aperv:sata_mop`.
        steps: Number of step records in the trace. Zero for arms that emit no
            telemetry and for runs that died at startup.
        violation_lines: Every `RVSEC` line in the file, whether or not it could
            be placed. This is the quantity the validation gate counts.
        violations: One entry per violation line, placed on the timeline.
        clock_offset_ms: Device-to-epoch offset recovered for this run. None
            when there was no step to anchor against.
        alignment_residual_ms: What the quarter-hour rounding left over — the
            measured distance between capture start and first step. Seconds in
            a healthy run; minutes means the anchoring assumption failed here.
    """

    trace_path: Path
    logcat_path: Path
    apk: str | None
    repetition: int | None
    timeout_seconds: int | None
    arm: str | None
    steps: int
    violation_lines: int
    violations: tuple[Violation, ...] = ()
    clock_offset_ms: int | None = None
    alignment_residual_ms: int | None = None

    @property
    def has_violations(self) -> bool:
        return self.violation_lines > 0


@dataclass(frozen=True)
class JoinReport:
    """A tree of runs, with the three totals the validation gate checks.

    Attributes:
        runs: One entry per `.trace` read, in filename order, including the runs
            that produced no violation at all — the denominator is part of the
            result.
    """

    runs: tuple[RunJoin, ...]

    @property
    def violation_lines(self) -> int:
        return sum(run.violation_lines for run in self.runs)

    @property
    def runs_with_violations(self) -> int:
        return sum(1 for run in self.runs if run.has_violations)

    @property
    def apks_with_violations(self) -> int:
        return len({run.apk for run in self.runs if run.has_violations})

    def __str__(self) -> str:
        return (
            f"{self.violation_lines} RVSEC lines across "
            f"{self.runs_with_violations} runs and {self.apks_with_violations} APKs "
            f"(of {len(self.runs)} runs read)"
        )


def _split_run_identity(
    trace_path: Path,
) -> tuple[str | None, int | None, int | None, str | None]:
    """
    Recover a run's identity from its trace filename.

    Args:
        trace_path: Recorded `.trace` file. Only its name is inspected.

    Returns:
        `(apk, repetition, timeout_seconds, arm)`, all None when the name does
        not follow rv-platform's run identity — a hand-named or foreign trace is
        still joined, only without its identity fields.
    """
    match = _RUN_FILENAME.match(trace_path.name.removesuffix(".trace"))
    if not match:
        return None, None, None, None
    return (
        match.group("apk"),
        int(match.group("repetition")),
        int(match.group("timeout")),
        match.group("arm"),
    )


def _read_steps(trace_path: Path) -> dict[int, StepRow]:
    """
    Read the run's steps, keyed by step number.

    The steps come from the native NDJSON reader rather than from a regex over
    the trace. That is a change of source and nothing else: a reader row carries
    the same epoch clock the retired `[APE-STEP] clock=` field carried, expanded
    from the run-relative `t` through `RUN_START.t0`.

    Args:
        trace_path: Recorded `.trace` file. Not written to.

    Returns:
        `{step: StepRow}` in file order, which is chronological — the agent
        writes one record per decision and step numbers increase strictly within
        a run. Empty for an arm that emits no telemetry and for a run that died
        before its first step.
    """
    return {row.step: row for row in TraceReader(trace_path)}


def _step_timeline(steps: dict[int, StepRow]) -> list[tuple[int, int, str]]:
    """
    Reduce the step map to the `(step, clock_ms, activity)` placement timeline.

    Rows whose epoch clock is unavailable are dropped rather than guessed: a
    trace with no `RUN_START` has a run-relative clock only, and inventing an
    absolute one is what the reader refuses to do (INV-APV-51). A run left with
    no timeline reports its violations as `UNALIGNED` and keeps its denominator.
    """
    return [
        (row.step, row.t_epoch_ms, row.activity)
        for row in steps.values()
        if row.t_epoch_ms is not None
    ]


def _read_heartbeats(logcat_path: Path) -> list[tuple[dt.datetime, int, int]]:
    """
    Read the per-step heartbeat lines the jar writes into logcat.

    From stage 4 the agent emits one `Log.i` line per exploration step under the
    `ApeRvHb` tag, carrying the step number and its run-relative milliseconds.
    Its whole purpose is to put the step series and the violation series in the
    same file, on the same clock, in the same rendering — so a violation can be
    placed by comparing two stamps that are both unzoned and both yearless, and
    whose unknowns therefore cancel.

    The tag reaches the file only because it is in the capture allowlist: `adb
    logcat -s <tags>` filters at the device, so a heartbeat under an unadmitted
    tag is discarded before capture and this function legitimately returns an
    empty list. That is reported as `UNALIGNED`, never papered over.

    Args:
        logcat_path: Recorded `.logcat` file. Not written to.

    Returns:
        One `(stamp, step, t_rel_ms)` per heartbeat line, in file order.
    """
    heartbeats: list[tuple[dt.datetime, int, int]] = []
    with open(logcat_path, "r", encoding="utf-8", errors="replace") as logcat_file:
        for line in logcat_file:
            match = _HEARTBEAT_LINE.match(line)
            if match:
                heartbeats.append(
                    (
                        _stamp_of(match),
                        int(match.group("step")),
                        int(match.group("rel")),
                    )
                )
    return heartbeats


def _read_violation_lines(logcat_path: Path) -> list[tuple[dt.datetime, str]]:
    """
    Read every `RVSEC` violation line as `(naive device timestamp, payload)`.

    The year is absent from the logcat stamp, so the datetime carries a
    placeholder year that `_align_clocks` replaces. The cheap byte tests come
    first because the coverage stream (`RVSEC-COV`, ~100k lines per file) dwarfs
    the violation stream and must not be decoded line by line.

    Args:
        logcat_path: Recorded `.logcat` file. Not written to.

    Returns:
        One `(stamp, payload)` per `RVSEC` line, in file order. The stamp is the
        device wall clock with a placeholder year; the payload is everything
        after the tag, still unparsed.
    """
    violations: list[tuple[dt.datetime, str]] = []
    with open(logcat_path, "rb") as logcat_file:
        for raw_line in logcat_file:
            if b"RVSEC" not in raw_line or b"RVSEC-" in raw_line:
                continue
            match = _VIOLATION_LINE.match(raw_line.decode("utf-8", errors="replace"))
            if match:
                violations.append((_stamp_of(match), match.group("payload")))
    return violations


def _stamp_of(match: re.Match) -> dt.datetime:
    """
    Build the device stamp of a logcat line, with a placeholder year.

    Logcat omits the year entirely, so the year is supplied later by
    `_align_clocks` from the trace's own clock.

    Args:
        match: A match of `_TIMESTAMP`, carrying the month, day, hour, minute,
            second and millis groups.

    Returns:
        The stamp read as if it were UTC, in the placeholder year 1900. Only
        differences against another stamp read the same way are meaningful.
    """
    return dt.datetime(
        1900,
        int(match.group("month")),
        int(match.group("day")),
        int(match.group("hour")),
        int(match.group("minute")),
        int(match.group("second")),
        int(match.group("millis")) * 1000,
        tzinfo=dt.timezone.utc,
    )


def _read_capture_start(logcat_path: Path) -> dt.datetime | None:
    """
    Read the first stamped line of the logcat — the clock anchor.

    Capture starts within seconds of the run, which keeps the anchor well inside
    the quarter-hour rounding tolerance regardless of the exploration budget.

    Args:
        logcat_path: Recorded `.logcat` file. Not written to.

    Returns:
        The device stamp of the first stamped line, or None when the file holds
        no stamped line at all.
    """
    with open(logcat_path, "rb") as logcat_file:
        for raw_line in logcat_file:
            match = _ANY_STAMPED_LINE.match(raw_line.decode("utf-8", errors="replace"))
            if match:
                return _stamp_of(match)
    return None


def _naive_epoch_ms(stamp: dt.datetime, year: int) -> int:
    """Epoch ms for a device stamp read as if it were UTC, in the given year."""
    return int(stamp.replace(year=year).timestamp() * 1000)


def _align_clocks(first_step_ms: int, capture_start: dt.datetime) -> tuple[int, int]:
    """
    Recover the device-to-epoch offset for one run.

    Both series come from the same device clock: `clock=` is
    `System.currentTimeMillis()` in the agent process, and logcat renders that
    same clock as local wall time without a year or a zone. Their difference is
    therefore exactly the device's UTC offset plus however far apart the two
    anchor events actually were — capture start and first step, seconds apart in
    practice. Rounding to the nearest quarter hour recovers the zone, since every
    real UTC offset is a multiple of 15 minutes, and the remainder is returned
    rather than discarded: it is the measured gap between capture start and first
    step, and a value of minutes rather than seconds is the signal that the
    anchoring assumption does not hold for that run.

    The year is chosen from the three candidates around the trace's own clock so
    that a run spanning New Year is not misaligned by twelve months.

    Args:
        first_step_ms: Epoch milliseconds of the run's first `[APE-STEP]` line.
        capture_start: Device stamp of the first stamped logcat line.

    Returns:
        `(offset_ms, residual_ms)`, where a device stamp becomes epoch time by
        adding `offset_ms` to its as-if-UTC reading.
    """
    trace_year = dt.datetime.fromtimestamp(first_step_ms / 1000, dt.timezone.utc).year
    best_difference = min(
        (
            first_step_ms - _naive_epoch_ms(capture_start, year)
            for year in (trace_year - 1, trace_year, trace_year + 1)
        ),
        key=abs,
    )
    offset = round(best_difference / _QUARTER_HOUR_MS) * _QUARTER_HOUR_MS
    return offset, best_difference - offset


def _place(
    timestamp_ms: int, steps: list[tuple[int, int, str]]
) -> tuple[Phase, int | None, str | None]:
    """
    Find which step was executing when a violation fired.

    Args:
        timestamp_ms: Epoch milliseconds of the violation, already aligned.
        steps: The run's `(step, clock_ms, activity)` tuples, chronological and
            non-empty — a run with no step never reaches here.

    Returns:
        `(phase, step, activity)`. The step and activity are set only inside the
        exploration window; outside it the violation has a phase but no step,
        because there is no decision it can be attributed to.
    """
    if timestamp_ms < steps[0][1]:
        return Phase.PRE_EXPLORATION, None, None
    if timestamp_ms > steps[-1][1]:
        return Phase.POST_EXPLORATION, None, None
    # Last step at or before the violation. Linear from the end: violations
    # cluster early, but runs are a few hundred steps, so this stays trivial.
    for step, clock, activity in reversed(steps):
        if clock <= timestamp_ms:
            return Phase.EXPLORATION, step, activity
    return Phase.PRE_EXPLORATION, None, None


def _parse_payload(payload: str) -> tuple[str, str, str]:
    """Split an `RVSEC` payload into `(spec, violation_type, message)`."""
    fields = payload.split(",", _VIOLATION_FIELDS)
    if len(fields) <= _VIOLATION_FIELDS:
        # A shape the logger did not produce in the recorded corpus. Kept rather
        # than dropped: the line is still a violation, and the count is the gate.
        return fields[0] if fields else "", "", payload
    return fields[0], fields[5], fields[6]


def join_run(trace_path: Path | str) -> RunJoin:
    """
    Join one run's step clock against its violation log.

    Args:
        trace_path: Recorded `.trace` file. Its `.logcat` sibling is read
            alongside it. Neither is written to.

    Returns:
        The run's violations placed on its exploration timeline. A run with no
        violations yields a valid report with an empty violation set — never an
        omission, because "no violation" is a measurement.

    Raises:
        OSError: The trace cannot be read. A missing `.logcat` sibling is not an
            error: it means the run recorded no violation log, which is reported
            as zero violation lines.
    """
    trace_path = Path(trace_path)
    logcat_path = trace_path.with_suffix(".logcat")
    apk, repetition, timeout_seconds, arm = _split_run_identity(trace_path)

    step_map = _read_steps(trace_path)
    steps = _step_timeline(step_map)
    raw_violations = _read_violation_lines(logcat_path) if logcat_path.is_file() else []

    offset_ms: int | None = None
    residual_ms: int | None = None
    if steps and raw_violations:
        # Anchor on capture start, not on the first violation: on a long budget a
        # late first violation would round to the wrong quarter hour. Fall back to
        # the first violation only when the file carries no stamped line before it,
        # which cannot happen while the violation itself is stamped.
        capture_start = _read_capture_start(logcat_path) or raw_violations[0][0]
        offset_ms, residual_ms = _align_clocks(steps[0][1], capture_start)

    first_step_ms = steps[0][1] if steps else None
    violations: list[Violation] = []
    for stamp, payload in raw_violations:
        spec, violation_type, message = _parse_payload(payload)
        if offset_ms is None or first_step_ms is None:
            violations.append(
                Violation(
                    timestamp_ms=None,
                    spec=spec,
                    violation_type=violation_type,
                    message=message,
                    phase=Phase.UNALIGNED,
                )
            )
            continue
        year = dt.datetime.fromtimestamp(first_step_ms / 1000, dt.timezone.utc).year
        timestamp_ms = _naive_epoch_ms(stamp, year) + offset_ms
        phase, step, activity = _place(timestamp_ms, steps)
        violations.append(
            Violation(
                timestamp_ms=timestamp_ms,
                spec=spec,
                violation_type=violation_type,
                message=message,
                phase=phase,
                step=step,
                activity=activity,
                seconds_from_first_step=(timestamp_ms - first_step_ms) / 1000,
            )
        )

    return RunJoin(
        trace_path=trace_path,
        logcat_path=logcat_path,
        apk=apk,
        repetition=repetition,
        timeout_seconds=timeout_seconds,
        arm=arm,
        steps=len(step_map),
        violation_lines=len(raw_violations),
        violations=tuple(violations),
        clock_offset_ms=offset_ms,
        alignment_residual_ms=residual_ms,
    )


def join_tree(root: Path | str) -> JoinReport:
    """
    Join every recorded run under a results tree, in stable filename order.

    Every run is reported, including the ones with no violation at all — the
    denominator is part of the result.

    Args:
        root: Results directory searched recursively for `.trace` files. Not
            written to.

    Returns:
        A report over every run found, sorted by path so that two invocations
        over the same tree emit rows in the same order.

    Raises:
        OSError: A trace under the tree cannot be read. A run whose `.logcat`
            sibling is missing is not an error.
    """
    root = Path(root)
    return JoinReport(
        runs=tuple(join_run(trace) for trace in sorted(root.rglob("*.trace")))
    )


def main(argv: list[str] | None = None) -> int:
    """
    Print per-violation rows as CSV for a results tree.

    Usage: python -m aperv_tool.analysis.clock_logcat_join <results_dir>

    Rows go to stdout and the totals line to stderr, so the output can be piped
    straight into an analysis without the summary contaminating the CSV.

    Args:
        argv: Argument list without the program name. Defaults to `sys.argv[1:]`.

    Returns:
        0. Failures exit rather than return a code.

    Raises:
        SystemExit: The argument list is not a single readable directory.
    """
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(
            "usage: python -m aperv_tool.analysis.clock_logcat_join <results_dir>",
            file=sys.stderr,
        )
        raise SystemExit(2)

    root = Path(args[0])
    if not root.is_dir():
        print(f"not a readable run directory: {root}", file=sys.stderr)
        raise SystemExit(2)

    report = join_tree(root)
    writer = csv.writer(sys.stdout)
    writer.writerow(
        [
            "apk",
            "repetition",
            "timeout",
            "arm",
            "steps",
            "violation_lines",
            "phase",
            "step",
            "activity",
            "seconds_from_first_step",
            "spec",
            "violation_type",
        ]
    )
    for run in report.runs:
        if not run.violations:
            # A run with no violation is a row too: the analysis needs to know it
            # was read and found nothing, not that it was skipped.
            writer.writerow(
                [run.apk, run.repetition, run.timeout_seconds, run.arm, run.steps, 0]
                + [""] * 6
            )
            continue
        for violation in run.violations:
            writer.writerow(
                [
                    run.apk,
                    run.repetition,
                    run.timeout_seconds,
                    run.arm,
                    run.steps,
                    run.violation_lines,
                    violation.phase.value,
                    violation.step if violation.step is not None else "",
                    violation.activity or "",
                    (
                        f"{violation.seconds_from_first_step:.3f}"
                        if violation.seconds_from_first_step is not None
                        else ""
                    ),
                    violation.spec,
                    violation.violation_type,
                ]
            )

    print(f"# {report}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

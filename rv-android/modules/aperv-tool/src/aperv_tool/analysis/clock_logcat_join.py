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

**Both series live in the logcat, on one clock.** The jar writes one `ApeRvHb`
heartbeat per exploration step into the same file that carries the `RVSEC` lines,
in the same rendering. Placing a violation is therefore a comparison between two
stamps out of that one file: the violation belongs to the step of the last
heartbeat at or before it. Neither stamp carries a year or a zone, and neither
needs one — the unknowns are identical on both sides and cancel in the
difference. Month and day are present, so a run crossing midnight places
correctly.

**The placement rule is the module's, the tag is the caller's.**
`read_tagged_lines(path, tag)` and `place_on_timeline(stamp, heartbeats)` are
public and tag-agnostic (INV-APV-63). The same file carries the violations, the
monitored operations under `RVSEC-COV` and the opt-in diagnostic tags, all on the
one heartbeat clock, so the rule that turns a stamp into a step belongs to the
timeline rather than to any one stream. This module's own join calls them with
`VIOLATION_TAG`; `step_bundle` calls them with the others. Three copies of the
loop is how three consumers come to disagree about which step an event was on.

**The trace supplies what the logcat cannot.** `analysis/trace_ndjson.py` is the
one way this module reads a trace: the matched step keys into its rows for the
activity and the abstract state the run was on. `RUN_START.t0` is the only source
of an absolute clock, so where a violation's epoch time is reported it is
composed forward — `t0 + heartbeat.t_rel_ms + (violation stamp − heartbeat
stamp)` — out of values the run itself recorded. A trace with no `RUN_START`
reports no absolute time rather than a guess (INV-APV-51).

**A run whose logcat carries no heartbeat is reported, not repaired.** Its
violations come back `UNALIGNED` and the run keeps its denominator in the report.
The heartbeat reaches the file only because `ApeRvHb` is in the capture
allowlist: `adb logcat -s <tags>` filters at the device, so a heartbeat under an
unadmitted tag is discarded before capture and there is nothing here to recover
it from.

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
from functools import lru_cache
from pathlib import Path

from aperv_tool.analysis.run_identity import try_parse_run_filename
from aperv_tool.analysis.trace_ndjson import StepRow, TraceReader

# `MM-DD HH:MM:SS.mmm  PID  TID  LEVEL TAG: message`, with the tag padded to eight
# characters.
_TIMESTAMP = (
    r"(?P<month>\d{2})-(?P<day>\d{2}) "
    r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})\.(?P<millis>\d{3})"
)

# The tag this module's own join reads. It is one argument of a tag-agnostic
# reader (INV-APV-63), not a property of the reader: `step_bundle` calls the same
# function with `RVSEC-COV` and with the diagnostic tags.
VIOLATION_TAG = "RVSEC"

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

# One parsed `ApeRvHb` line: when it was logged, which step it opened, and that
# step's run-relative milliseconds.
Heartbeat = tuple[dt.datetime, int, int]


class Phase(str, Enum):
    """Where a violation sits on the exploration timeline."""

    PRE_EXPLORATION = "pre_exploration"
    EXPLORATION = "exploration"
    POST_EXPLORATION = "post_exploration"
    # The run's logcat carries no heartbeat to place against: a run that died
    # before its first step logged none, and neither did a capture whose tag
    # allowlist omitted `ApeRvHb`. The violation is still counted; only its
    # position is unknown.
    UNALIGNED = "unaligned"


@dataclass(frozen=True)
class Violation:
    """One `RVSEC` line, placed on the run's exploration timeline.

    Attributes:
        timestamp_ms: Epoch milliseconds of the violation, composed forward from
            the run's `t0` through the heartbeat that placed it. None when the
            trace carried no `RUN_START`, and None when the run had no heartbeat
            to place against at all.
        spec: Specification whose monitor fired, as the logger names it.
        violation_type: Violation category reported by the logger. Empty when
            the payload does not carry the full field shape.
        message: Violation message. Holds the whole payload when the field
            shape is unexpected, so no information is dropped.
        phase: Where the violation sits relative to the exploration window.
        step: Step that was executing when the monitor fired: the step of the
            last heartbeat at or before the violation. None outside the
            exploration window.
        activity: Activity that step was exploring. None outside the window, and
            None when the trace carries no row for the step the heartbeat names.
        state_key: Abstract state that step was on, from the same row. Run-local
            by construction, so it joins within a run and never across runs.
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
    state_key: str | None = None
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
    key = try_parse_run_filename(trace_path)
    if key is None:
        return None, None, None, None
    return key.apk, key.repetition, key.timeout_s, key.arm


def _read_trace(trace_path: Path) -> tuple[dict[int, StepRow], int | None]:
    """
    Read the run's steps, keyed by step number, and its epoch base.

    Both come from the native NDJSON reader in one pass. The step map is what a
    placed violation keys into for its activity and state; `t0` is the only
    absolute clock the run recorded, and a trace without `RUN_START` simply has
    none — this returns None rather than deriving one from anywhere else.

    Args:
        trace_path: Recorded `.trace` file. Not written to.

    Returns:
        `({step: StepRow}, t0_ms)`. The map is empty for an arm that emits no
        telemetry and for a run that died before its first step.
    """
    reader = TraceReader(trace_path)
    steps = {row.step: row for row in reader}
    run_start = reader.run_start
    return steps, run_start.t0_ms if run_start is not None else None


def _read_heartbeats(logcat_path: Path) -> list[Heartbeat]:
    """
    Read the per-step heartbeat lines the jar writes into logcat.

    The agent emits one `Log.i` line per exploration step under the `ApeRvHb`
    tag, carrying the step number and its run-relative milliseconds. Its whole
    purpose is to put the step series and the violation series in the same file,
    on the same clock, in the same rendering — so a violation can be placed by
    comparing two stamps that are both unzoned and both yearless, and whose
    unknowns therefore cancel.

    The tag reaches the file only because it is in the capture allowlist: `adb
    logcat -s <tags>` filters at the device, so a heartbeat under an unadmitted
    tag is discarded before capture and this function legitimately returns an
    empty list. That is reported as `UNALIGNED`, never papered over.

    **The series is assumed to belong to one run**, which is what makes file order
    chronological and step numbers monotonic. `LogcatManager` clears the buffer at
    capture start, so the assumption holds on the standard path. It is not checked
    here: a file holding a previous run's heartbeats as well would restart the step
    numbering partway through, and placement would attribute violations to that
    run's step numbers while resolving activity and state from this run's rows.
    The equivalent hazard on the violation side is handled by reporting distance
    rather than a verdict (see the module docstring); the heartbeat side has no
    such defence, and adding one would change which runs report as `UNALIGNED`.

    Args:
        logcat_path: Recorded `.logcat` file. Not written to.

    Returns:
        One `(stamp, step, t_rel_ms)` per heartbeat line, in file order — which
        is chronological, since the agent logs one as each step opens.
    """
    heartbeats: list[Heartbeat] = []
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


@lru_cache(maxsize=None)
def _tagged_line(tag: str) -> re.Pattern[str]:
    """The line pattern for exactly one logcat tag, compiled once per tag.

    The tag is escaped, so a caller cannot smuggle a pattern in through it, and
    it is followed by `\\s*:` rather than by anything looser — logcat pads the
    tag out to eight characters, and that colon is what stops `RVSEC` from
    admitting `RVSEC-COV`, a stream two orders of magnitude larger.
    """
    return re.compile(
        rf"^{_TIMESTAMP}\s+\d+\s+\d+\s+[VDIWEF] {re.escape(tag)}\s*:\s*(?P<payload>.*)$"
    )


def read_tagged_lines(logcat_path: Path, tag: str) -> list[tuple[dt.datetime, str]]:
    """
    Read every line of one logcat tag as `(device timestamp, payload)`.

    The admitted tag is a parameter rather than a property of this module
    (INV-APV-63): the same three streams — violations under `RVSEC`, monitored
    operations under `RVSEC-COV`, the opt-in diagnostics — arrive in one file
    under one clock, and there is no reason for each consumer to re-derive how a
    logcat line is shaped. Matching is exact, never a prefix: a request for
    `RVSEC` returns no `RVSEC-COV` line and the reverse holds too.

    The cheap byte tests come first because the coverage stream (~100k lines per
    file) dwarfs the violation stream, and decoding every one of its lines only
    to reject it would cost more than the join it feeds.

    Args:
        logcat_path: Recorded `.logcat` file. Not written to.
        tag: The logcat tag to admit, e.g. `RVSEC`. Matched exactly.

    Returns:
        One `(stamp, payload)` per line carrying the tag, in file order. The
        stamp is the device wall clock as logcat rendered it; the payload is
        everything after the tag, still unparsed.
    """
    pattern = _tagged_line(tag)
    needle = tag.encode()
    end_of_tag = len(needle)

    lines: list[tuple[dt.datetime, str]] = []
    with open(logcat_path, "rb") as logcat_file:
        for raw_line in logcat_file:
            start = raw_line.find(needle)
            if start < 0:
                continue
            # What separates a tag from a longer tag it prefixes is the very next
            # byte: logcat writes `RVSEC   : …` and `RVSEC-COV: …`, so rejecting
            # on that byte keeps the violation reader from paying the decode cost
            # of the coverage stream. The pattern below would reject it anyway;
            # this is why it never has to.
            if raw_line[start + end_of_tag : start + end_of_tag + 1] not in (
                b" ",
                b":",
            ):
                continue
            match = pattern.match(raw_line.decode("utf-8", errors="replace"))
            if match:
                lines.append((_stamp_of(match), match.group("payload")))
    return lines


def _stamp_of(match: re.Match) -> dt.datetime:
    """
    Build the device stamp of a logcat line, with a placeholder year.

    Logcat omits the year, and nothing here supplies one: every stamp this
    module compares is read out of the same file by this same function, so the
    placeholder is identical on both sides of every difference and cancels.

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


def place_on_timeline(
    stamp: dt.datetime, heartbeats: list[Heartbeat]
) -> tuple[Phase, int | None, Heartbeat]:
    """
    Find which step was executing when a logcat line was written.

    The jar logs the heartbeat where the step envelope opens — at selection
    start, before dispatch — so a line between heartbeat N and heartbeat N+1
    belongs to step N.

    The rule is about the timeline, not about what is being placed, so it lives
    here once and takes no tag (INV-APV-63): a violation, a monitored operation
    and a diagnostic line are all stamps out of one file, and placing them by
    three copies of this loop is how three consumers come to disagree about which
    step an event belonged to.

    Args:
        stamp: Device stamp of the line, as `_stamp_of` read it.
        heartbeats: The run's heartbeats, chronological and non-empty — a run
            with none is `UNALIGNED` and never reaches here.

    Returns:
        `(phase, step, anchor)`. The step is set only inside the exploration
        window; outside it the line has a phase but no step, because there is no
        decision it can be attributed to. The anchor is the heartbeat the
        absolute timestamp is composed from, which outside the window is the
        nearer end of the run.
    """
    if stamp < heartbeats[0][0]:
        return Phase.PRE_EXPLORATION, None, heartbeats[0]
    if stamp > heartbeats[-1][0]:
        return Phase.POST_EXPLORATION, None, heartbeats[-1]
    # Last heartbeat at or before the violation. Linear from the end: violations
    # cluster early, but runs are a few hundred steps, so this stays trivial.
    # The loop always returns: the two guards above leave the stamp inside the
    # window, so the final candidate, `heartbeats[0]`, satisfies the condition by
    # construction. A fallback return after it would be unreachable, and would
    # answer PRE_EXPLORATION for a stamp already proven not to be before the run.
    for heartbeat in reversed(heartbeats):
        if heartbeat[0] <= stamp:
            return Phase.EXPLORATION, heartbeat[1], heartbeat


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

    step_map, t0_ms = _read_trace(trace_path)
    has_logcat = logcat_path.is_file()
    heartbeats = _read_heartbeats(logcat_path) if has_logcat else []
    raw_violations = read_tagged_lines(logcat_path, VIOLATION_TAG) if has_logcat else []

    violations: list[Violation] = []
    for stamp, payload in raw_violations:
        spec, violation_type, message = _parse_payload(payload)
        if not heartbeats:
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

        phase, step, anchor = place_on_timeline(stamp, heartbeats)
        anchor_stamp, _anchor_step, anchor_rel_ms = anchor
        # Both stamps came out of the same file through the same reader, so the
        # placeholder year and the missing zone cancel in the subtraction.
        offset_from_anchor_ms = round((stamp - anchor_stamp).total_seconds() * 1000)
        row = step_map.get(step) if step is not None else None
        violations.append(
            Violation(
                timestamp_ms=(
                    t0_ms + anchor_rel_ms + offset_from_anchor_ms
                    if t0_ms is not None
                    else None
                ),
                spec=spec,
                violation_type=violation_type,
                message=message,
                phase=phase,
                step=step,
                activity=row.activity if row is not None else None,
                state_key=row.state_key if row is not None else None,
                seconds_from_first_step=(stamp - heartbeats[0][0]).total_seconds(),
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
            "state",
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
                + [""] * 7
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
                    violation.state_key or "",
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

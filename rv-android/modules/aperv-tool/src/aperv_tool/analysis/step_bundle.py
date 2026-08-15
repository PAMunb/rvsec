"""
One record per exploration step, with every logcat stream placed on it.

A run leaves four artefacts that describe the same moments from four angles: the
`.trace` says what the agent decided, the `RVSEC` lines say what the monitors
caught, the `RVSEC-COV` lines say which instrumented methods executed, and the
opt-in diagnostic tags say what the platform reported going wrong. Every consumer
of the chain from a decision to a violation has so far reassembled those four by
hand, each with its own idea of which step an event belonged to. This module is
that assembly, done once: `bundle_run` returns a `StepBundle` per step carrying
the step's own record plus the events that happened while it was executing, plus
the teardown coverage payload of the state it stood on.

**One rule places all three streams** (INV-CAN-18, INV-APV-63). The heartbeat
series and every event series live in the same file under the same clock, so the
placement is `clock_logcat_join.place_on_timeline`, imported and never
reimplemented. Three copies of that loop is how three consumers come to disagree
about which step an event was on — and the disagreement would be invisible,
because each copy answers plausibly.

**The heartbeat⇄step discrepancy is reported as a number, not repaired.** Over 60
recorded runs the corpus carries 15,701 heartbeats for 15,702 steps: exactly one
step opened without its heartbeat reaching the file. `BundleDiagnostics` names
the gap and the steps that lack one, and the events that fall in such a step's
window are attributed to the preceding heartbeat with `absorbs_steps` set on that
bundle — attributed with a flag, never dropped, and never invented onto the step
that has no clock of its own.

**A run whose logcat carries no heartbeat is `UNALIGNED` and stays that way.**
Its events are counted per tag and placed nowhere. Repairing them — from the
step's own `t`, say — would manufacture a correspondence the artefacts do not
support, and the run's denominator is preserved without it.

**It is intra-`aperv` by construction.** The baseline tools write no NDJSON, so
their traces yield no step rows and therefore no bundles. Zero bundles for such a
run is a measurement of the artefact, not a failure of the reader.

Offline and read-only over recorded artefacts (INV-APV-35): no device, no
emulator, no `adb`, and nothing is written.
"""

from __future__ import annotations

import bisect
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from aperv_tool.analysis import coverage_dump, monitored_ops, state_coverage_join
from aperv_tool.analysis import violations as violations_module
from aperv_tool.analysis.clock_logcat_join import (
    VIOLATION_TAG,
    Heartbeat,
    Phase,
    _read_heartbeats,
    place_on_timeline,
)
from aperv_tool.analysis.coverage_dump import StateCoverage
from aperv_tool.analysis.state_coverage_join import JoinTotals
from aperv_tool.analysis.trace_ndjson import StepRow, TraceReader

#: The three streams this module places, named as they are counted. The first two
#: are logcat tags; the third is a stream assembled from four diagnostic tags by
#: `rv_coverage`'s parser, which owns their multi-line grammar.
STREAMS = (VIOLATION_TAG, monitored_ops.MONITORED_OP_TAG, "diagnostics")

#: Key of the assembled diagnostic stream in the per-tag counters.
DIAGNOSTIC_STREAM = "diagnostics"


@dataclass(frozen=True)
class StepBundle:
    """One step and everything the run recorded while it was executing.

    Attributes:
        row: The step's own record, dictionary references already resolved.
        violations: `RVSEC` events placed on this step.
        monitored_ops: `RVSEC-COV` executions placed on this step.
        diagnostics: Platform diagnostic events placed on this step, as
            `rv_coverage`'s parser assembled them. Empty when the capture ran
            without the opt-in diagnostic tags, which is the default.
        uicov: The teardown coverage payload of the state this step stood on, or
            None when the dump carried no row for it. **Cumulative over the whole
            run** — the dump is written once, at teardown — so it describes the
            state across every visit and never this step alone.
        heartbeat: Whether this step's own heartbeat reached the logcat. False
            means the step's window is covered by the preceding heartbeat.
        absorbs_steps: Steps with no heartbeat whose events this bundle received,
            in step order. Empty on a run with no gap. Its presence is the flag
            that an event on this bundle may belong to a later step.
    """

    row: StepRow
    violations: tuple[violations_module.ViolationEvent, ...] = ()
    monitored_ops: tuple[monitored_ops.MonitoredOp, ...] = ()
    diagnostics: tuple[Any, ...] = ()
    uicov: StateCoverage | None = None
    heartbeat: bool = True
    absorbs_steps: tuple[int, ...] = ()


@dataclass(frozen=True)
class BundleDiagnostics:
    """What the assembly saw, so nothing it could not place disappears.

    Every line of every stream lands in exactly one of the four per-tag counters,
    so `lines_by_tag == placed + unaligned + outside_window + placed_without_row`
    holds per tag by construction (INV-CAN-04).

    Attributes:
        steps: Step records the trace yielded.
        heartbeats: Heartbeat lines the logcat carried.
        heartbeat_gap: `steps - heartbeats`. Positive when steps opened without
            their heartbeat reaching the file; negative when the trace was cut
            after its heartbeat was written.
        steps_without_heartbeat: Those steps, by number, in order.
        heartbeats_without_step: Heartbeats naming a step the trace has no record
            for — the other side of the same discrepancy.
        lines_by_tag: Lines read per stream.
        placed_by_tag: Lines attached to a bundle.
        unaligned_by_tag: Lines the run had no heartbeat to place against
            (`Phase.UNALIGNED`). Non-zero only when the logcat carried no
            heartbeat at all, in which case it equals `lines_by_tag`.
        outside_window_by_tag: Lines before the first heartbeat or after the
            last. Kept as a count rather than forced onto an end of the run: a
            line seconds before the first step is a launch-time event, one
            minutes before it is an earlier run still in the buffer.
        placed_without_row_by_tag: Lines placed on a step the trace has no record
            for. Distinct from `outside_window`: the clock knew where they were
            and the trace did not.
        logcat_present: Whether a logcat file was read at all.
        diagnostics_read: Whether the diagnostic parser ran. False when the
            caller asked for no diagnostics or when `rv_coverage` is not
            installed — reported so an empty stream is never read as "the run had
            no diagnostics".
        uicov: The state-key join's own accounting for this run, or None when the
            trace carried no dump.
    """

    steps: int
    heartbeats: int
    heartbeat_gap: int
    steps_without_heartbeat: tuple[int, ...]
    heartbeats_without_step: tuple[int, ...]
    lines_by_tag: Mapping[str, int]
    placed_by_tag: Mapping[str, int]
    unaligned_by_tag: Mapping[str, int]
    outside_window_by_tag: Mapping[str, int]
    placed_without_row_by_tag: Mapping[str, int]
    logcat_present: bool
    diagnostics_read: bool
    uicov: JoinTotals | None


def _read_diagnostic_events(
    logcat_path: Path,
) -> tuple[list[tuple[dt.datetime, Any]], bool]:
    """
    Assemble platform diagnostic events, reusing `rv_coverage`'s parser.

    Crashes, class-load verify errors and ANRs are multi-line blocks interleaved
    with every other process's output, and `rv_coverage.DiagnosticEventParser`
    already owns that grammar — it groups by `(tag, pid, tid)` so a foreign line
    between two stack frames does not truncate the block. A third parser of the
    same four tags is exactly the duplication this layer exists to absorb, so the
    parser is imported rather than rewritten.

    It is imported lazily because `rv_coverage` is not a declared dependency of
    this module's package: the diagnostic stream is opt-in on the capture side
    too (`RV_LOGCAT_DIAGNOSTICS`), so its absence must degrade to "not read"
    rather than break every bundle.

    Args:
        logcat_path: Recorded `.logcat` file. Not written to.

    Returns:
        `([(stamp, event)], parser_available)`. The stamp is rebuilt in the same
        placeholder frame the heartbeats are read in — the parser resolves the
        year against today's date and returns a naive value, which is
        incomparable with a heartbeat stamp; month, day and time of day are the
        only parts either side actually carries.
    """
    try:
        from rv_coverage.parser.log.diagnostic_parser import DiagnosticEventParser
    except ImportError:
        return [], False

    parser = DiagnosticEventParser()
    events: list[Any] = []
    with open(logcat_path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            completed = parser.feed_line(line)
            if completed is not None:
                events.append(completed)
    trailing = parser.flush()
    if trailing is not None:
        events.append(trailing)

    stamped: list[tuple[dt.datetime, Any]] = []
    for event in events:
        occurred = getattr(event, "time_occurred", None)
        if occurred is None:
            continue
        stamped.append((_placeholder_frame(occurred), event))
    return stamped, True


def _placeholder_frame(moment: dt.datetime) -> dt.datetime:
    """Rebuild a parsed logcat moment in the frame the heartbeats are read in.

    Logcat writes no year and no zone. `clock_logcat_join` reads every stamp as
    UTC in a placeholder year, so the unknowns are identical on both sides of
    every comparison and cancel; a stamp that arrived with a resolved year and no
    zone has to be put back into that frame before it can be compared with one.
    """
    return dt.datetime(
        1900,
        moment.month,
        moment.day,
        moment.hour,
        moment.minute,
        moment.second,
        moment.microsecond,
        tzinfo=dt.timezone.utc,
    )


def _absorbing_step(heartbeat_steps: Sequence[int], step: int) -> int | None:
    """The heartbeat step whose window covers a step that opened without one."""
    position = bisect.bisect_left(heartbeat_steps, step)
    return heartbeat_steps[position - 1] if position else None


def bundle_run(
    trace: Path | str,
    logcat: Path | str | None = None,
    *,
    diagnostics: bool = True,
) -> tuple[list[StepBundle], BundleDiagnostics]:
    """
    Assemble one run's steps with every stream placed on them.

    Args:
        trace: Recorded `.trace` file. Read twice — once as NDJSON for the step
            records, once as text for the teardown coverage dump, which the jar
            writes into the same stdout.
        logcat: The run's `.logcat`. None means the sibling beside the trace; a
            path that does not exist yields empty streams and a run that is
            reported rather than dropped.
        diagnostics: Whether to assemble the platform diagnostic stream. It costs
            a full pass over a file that is mostly executions, so a caller
            reading many runs for their violations alone turns it off — and the
            report says it did.

    Returns:
        `(bundles, diagnostics)`. One bundle per step record in file order, and
        the accounting for every line that could not be attached to one. A trace
        with no step records — every baseline arm — yields no bundles, which is a
        fact about the artefact and not an error.

    Raises:
        OSError: The trace cannot be read. A missing logcat is not an error.
    """
    trace = Path(trace)
    logcat_path = Path(logcat) if logcat is not None else trace.with_suffix(".logcat")

    rows = list(TraceReader(trace))
    coverage = coverage_dump.parse_run(trace)
    uicov_index = state_coverage_join.state_index(coverage)
    uicov_totals = (
        state_coverage_join.totals((row.state_key for row in rows), coverage)
        if coverage.has_dump or rows
        else None
    )

    logcat_present = logcat_path.is_file()
    heartbeats: list[Heartbeat] = (
        _read_heartbeats(logcat_path) if logcat_present else []
    )

    streams: dict[str, list[tuple[dt.datetime, Any]]] = {
        VIOLATION_TAG: (
            violations_module.read_logcat(logcat_path) if logcat_present else []
        ),
        monitored_ops.MONITORED_OP_TAG: (
            monitored_ops.read_logcat(logcat_path) if logcat_present else []
        ),
    }
    diagnostic_events: list[tuple[dt.datetime, Any]] = []
    diagnostics_read = False
    if logcat_present and diagnostics:
        diagnostic_events, diagnostics_read = _read_diagnostic_events(logcat_path)
    streams[DIAGNOSTIC_STREAM] = diagnostic_events

    by_step: dict[int, dict[str, list[Any]]] = {
        row.step: {stream: [] for stream in STREAMS} for row in rows
    }
    lines = {stream: len(events) for stream, events in streams.items()}
    placed = {stream: 0 for stream in STREAMS}
    unaligned = {stream: 0 for stream in STREAMS}
    outside = {stream: 0 for stream in STREAMS}
    without_row = {stream: 0 for stream in STREAMS}

    for stream, events in streams.items():
        for stamp, payload in events:
            if not heartbeats:
                unaligned[stream] += 1
                continue
            phase, step, _anchor = place_on_timeline(stamp, heartbeats)
            if phase is not Phase.EXPLORATION:
                outside[stream] += 1
                continue
            bucket = by_step.get(step)
            if bucket is None:
                without_row[stream] += 1
                continue
            bucket[stream].append(payload)
            placed[stream] += 1

    heartbeat_steps = sorted({heartbeat[1] for heartbeat in heartbeats})
    row_steps = [row.step for row in rows]
    missing_heartbeat = tuple(
        step for step in row_steps if step not in set(heartbeat_steps)
    )
    absorbed: dict[int, list[int]] = {}
    for step in missing_heartbeat:
        anchor = _absorbing_step(heartbeat_steps, step)
        if anchor is not None:
            absorbed.setdefault(anchor, []).append(step)

    bundles = [
        StepBundle(
            row=row,
            violations=tuple(by_step[row.step][VIOLATION_TAG]),
            monitored_ops=tuple(by_step[row.step][monitored_ops.MONITORED_OP_TAG]),
            diagnostics=tuple(by_step[row.step][DIAGNOSTIC_STREAM]),
            uicov=uicov_index.get(row.state_key),
            heartbeat=row.step in set(heartbeat_steps),
            absorbs_steps=tuple(absorbed.get(row.step, ())),
        )
        for row in rows
    ]

    report = BundleDiagnostics(
        steps=len(rows),
        heartbeats=len(heartbeats),
        heartbeat_gap=len(rows) - len(heartbeats),
        steps_without_heartbeat=missing_heartbeat,
        heartbeats_without_step=tuple(
            step for step in heartbeat_steps if step not in set(row_steps)
        ),
        lines_by_tag=lines,
        placed_by_tag=placed,
        unaligned_by_tag=unaligned,
        outside_window_by_tag=outside,
        placed_without_row_by_tag=without_row,
        logcat_present=logcat_present,
        diagnostics_read=diagnostics_read,
        uicov=uicov_totals,
    )
    return bundles, report


def frame(bundles: Iterable[StepBundle]) -> pd.DataFrame:
    """
    Lay bundles out as one tidy row per step.

    The event lists themselves stay on the records — a frame cell is the wrong
    place for a stream — so what crosses into the frame is their counts plus the
    joined coverage payload, whose scope label travels with it.

    Args:
        bundles: The run's bundles, as `bundle_run` returned them.

    Returns:
        One row per step with the step's identity, the three stream counts, the
        joined coverage counters and the two heartbeat flags.
    """
    records = [
        {
            "step": bundle.row.step,
            "t_rel_ms": bundle.row.t_rel_ms,
            "activity": bundle.row.activity,
            "activity_has_mop": bundle.row.activity_has_mop,
            "state_key": bundle.row.state_key,
            "n_violations": len(bundle.violations),
            "n_monitored_ops": len(bundle.monitored_ops),
            "n_diagnostics": len(bundle.diagnostics),
            "uicov_present": bundle.uicov is not None,
            "uicov_discovered": (
                None if bundle.uicov is None else bundle.uicov.discovered
            ),
            "uicov_interacted": (
                None if bundle.uicov is None else bundle.uicov.interacted
            ),
            "uicov_scope": state_coverage_join.CUMULATIVE_SCOPE,
            "heartbeat": bundle.heartbeat,
            "absorbs_steps": len(bundle.absorbs_steps),
        }
        for bundle in bundles
    ]
    return pd.DataFrame(
        records,
        columns=[
            "step",
            "t_rel_ms",
            "activity",
            "activity_has_mop",
            "state_key",
            "n_violations",
            "n_monitored_ops",
            "n_diagnostics",
            "uicov_present",
            "uicov_discovered",
            "uicov_interacted",
            "uicov_scope",
            "heartbeat",
            "absorbs_steps",
        ],
    )

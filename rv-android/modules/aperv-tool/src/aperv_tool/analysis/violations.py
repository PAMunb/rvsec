"""
The violation stream at event grain, from a run's logcat or the campaign's CSV.

A violation is what the monitor writes when a specification's automaton enters an
error state. The logger emits one line per violation under the `RVSEC` tag, and
the campaign's consolidator collects the same events into `errors.csv`. Both
sources are read here, because they carry different fields and are trusted for
different things: the logcat carries the device stamp that places an event on the
exploration timeline and the `simpleClass` the CSV drops, while the CSV carries
the run identity without which an event cannot be attributed to a cell.

**The payload is seven comma-separated fields and the seventh contains commas.**
The shape is `spec,class,simpleClass,method,location,violationType,message`, and
a real message reads `expecting one of {TLSv1.2, TLSv1.3} but found TLS.` —
splitting it on every comma yields nine fields and a message cut in half. The
split is therefore bounded at six and everything after the sixth comma is the
message, verbatim. That bound is `clock_logcat_join`'s too, and it is imported
from there rather than restated: two modules parsing one logger's line with two
constants is how they come to disagree about what a violation was.

**A line of an unexpected shape is kept, not dropped** (INV-CAN-04). The count of
violation lines is what a validity gate reads, so a parser that discarded a line
it could not decompose would shrink the very quantity being measured. Such a line
comes back with its whole payload in `message` and `shape_ok` False.

**`errors.csv`'s `time` column times the violation, not the tool.** It is the
offset at which the monitor fired, and reading it as an action latency has
already misled one analysis. The column is carried under a name that says so.

Offline and read-only over recorded artefacts (INV-APV-35).
"""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from aperv_tool.analysis.clock_logcat_join import (
    _VIOLATION_FIELDS,
    VIOLATION_TAG,
    read_tagged_lines,
)

#: The logger's field order, and the frame's column order for the logcat source.
PAYLOAD_FIELDS = (
    "spec",
    "class_name",
    "simple_class",
    "method",
    "location",
    "violation_type",
    "message",
)

#: The consolidated CSV's header, exactly as rv-platform writes it. Declared so a
#: header change is a loud failure here rather than a silently missing column
#: three layers up.
ERRORS_CSV_HEADER = (
    "apk",
    "rep",
    "timeout",
    "tool",
    "time",
    "spec",
    "class",
    "method",
    "source",
    "message",
    "unique_msg",
)

#: `unique_msg` joins five fields with this separator. It is the only place the
#: CSV carries the violation type, which the consolidator otherwise drops.
_UNIQUE_SEPARATOR = ":::"
_UNIQUE_FIELDS = 5


@dataclass(frozen=True)
class ViolationEvent:
    """One violation, decomposed as the logger wrote it.

    Attributes:
        spec: Specification whose monitor fired.
        class_name: Fully-qualified class the violating call sits in.
        simple_class: The same class without its package, as the logger repeats
            it. Absent from `errors.csv`, which is why the logcat is not
            redundant with it.
        method: Method the violating call sits in.
        location: Source location as `File.kt:line`, when the instrumentation
            resolved one.
        violation_type: The monitor's category, e.g. `UnsafeProtocol`.
        message: The human-readable message, commas included and uncut. Holds the
            entire payload when the field shape was not the logger's.
        shape_ok: Whether the payload decomposed into the seven fields. False
            keeps the line countable without pretending it was understood.
    """

    spec: str
    class_name: str
    simple_class: str
    method: str
    location: str
    violation_type: str
    message: str
    shape_ok: bool = True


@dataclass(frozen=True)
class CsvDiagnostics:
    """What reading `errors.csv` encountered.

    Attributes:
        rows: Data rows read.
        unique_msg_unparsed: Rows whose `unique_msg` did not carry the five
            `:::`-joined fields, and whose `violation_type` is therefore empty.
            Counted rather than raised: the event itself is intact.
    """

    rows: int
    unique_msg_unparsed: int


def parse_payload(payload: str) -> ViolationEvent:
    """
    Decompose one `RVSEC` payload into its seven fields.

    Args:
        payload: The line's text after the tag, never the whole line.

    Returns:
        The decomposed event. A payload with fewer than seven fields is returned
        whole in `message` with `shape_ok` False — the line is still a violation
        and still counts.
    """
    fields = payload.split(",", _VIOLATION_FIELDS)
    if len(fields) <= _VIOLATION_FIELDS:
        return ViolationEvent(
            spec=fields[0] if fields else "",
            class_name="",
            simple_class="",
            method="",
            location="",
            violation_type="",
            message=payload,
            shape_ok=False,
        )
    return ViolationEvent(
        spec=fields[0],
        class_name=fields[1],
        simple_class=fields[2],
        method=fields[3],
        location=fields[4],
        violation_type=fields[5],
        message=fields[6],
    )


def read_logcat(logcat_path: Path | str) -> list[tuple[dt.datetime, ViolationEvent]]:
    """
    Read one run's violations from its logcat, in file order.

    Args:
        logcat_path: Recorded `.logcat` file. Not written to.

    Returns:
        `(stamp, event)` per `RVSEC` line. The stamp is the device wall clock in
        the placeholder frame `clock_logcat_join` reads it in — comparable
        against that module's heartbeats and against nothing else.

    Raises:
        OSError: The file cannot be read. A run with no logcat is the caller's to
            report as such; an empty list here means the file existed and carried
            no violation, which is a measurement.
    """
    return [
        (stamp, parse_payload(payload))
        for stamp, payload in read_tagged_lines(Path(logcat_path), VIOLATION_TAG)
    ]


def frame(events: Iterable[tuple[dt.datetime, ViolationEvent]]) -> pd.DataFrame:
    """
    Lay violation events out as a tidy frame at event grain.

    Args:
        events: `(stamp, event)` pairs, as `read_logcat` returns them.

    Returns:
        One row per event with `stamp` first and the seven payload fields after
        it, plus `shape_ok`. Empty input yields an empty frame of the same
        columns, so a run with no violation concatenates like any other.
    """
    records = [
        {
            "stamp": stamp,
            "spec": event.spec,
            "class_name": event.class_name,
            "simple_class": event.simple_class,
            "method": event.method,
            "location": event.location,
            "violation_type": event.violation_type,
            "message": event.message,
            "shape_ok": event.shape_ok,
        }
        for stamp, event in events
    ]
    return pd.DataFrame(records, columns=["stamp", *PAYLOAD_FIELDS, "shape_ok"])


def read_errors_csv(path: Path | str) -> tuple[pd.DataFrame, CsvDiagnostics]:
    """
    Read a campaign's consolidated `errors.csv` at event grain.

    The CSV is the only source that carries the run identity, and the only one
    that survives when a logcat was not retained. It drops `simpleClass` and
    buries the violation type inside `unique_msg`, which this recovers into its
    own column so a consumer never has to re-split that field.

    Args:
        path: The consolidated `errors.csv`. Not written to.

    Returns:
        `(frame, diagnostics)`. The frame carries the CSV's own columns with
        `time` renamed `violation_time_s` — the column times the violation, not
        the tool's action — plus `violation_type` and `unique_message` recovered
        from `unique_msg`.

    Raises:
        OSError: The file cannot be read.
        ValueError: The header is not the one rv-platform writes. A silently
            renamed column is worse than a stopped read: every downstream count
            would be computed over a column that is no longer what it says.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != ERRORS_CSV_HEADER:
            raise ValueError(
                f"{path}: unexpected errors.csv header {reader.fieldnames!r}; "
                f"expected {list(ERRORS_CSV_HEADER)}"
            )
        rows = list(reader)

    unparsed = 0
    records = []
    for row in rows:
        parts = (row["unique_msg"] or "").split(_UNIQUE_SEPARATOR)
        if len(parts) == _UNIQUE_FIELDS:
            violation_type, unique_message = parts[3], parts[4]
        else:
            violation_type, unique_message = "", row["unique_msg"] or ""
            unparsed += 1
        records.append(
            {
                "apk": row["apk"],
                "rep": int(row["rep"]),
                "timeout": int(row["timeout"]),
                "arm": row["tool"],
                # Named for what it times. The column holds the offset at which
                # the monitor fired, and reading it as the duration of a tool
                # action has already misled one analysis.
                "violation_time_s": float(row["time"]),
                "spec": row["spec"],
                "class_name": row["class"],
                "method": row["method"],
                "location": row["source"],
                "message": row["message"],
                "violation_type": violation_type,
                "unique_message": unique_message,
            }
        )

    return (
        pd.DataFrame(
            records,
            columns=[
                "apk",
                "rep",
                "timeout",
                "arm",
                "violation_time_s",
                "spec",
                "class_name",
                "method",
                "location",
                "message",
                "violation_type",
                "unique_message",
            ],
        ),
        CsvDiagnostics(rows=len(rows), unique_msg_unparsed=unparsed),
    )


def distinct(events: Sequence[ViolationEvent], key: Sequence[str]) -> int:
    """
    Count distinct violations under an explicitly named key.

    Two dedup conventions are in use and they disagree on a third of runs, so
    this refuses to pick one: the key is the caller's argument and travels with
    the number it produced.

    Args:
        events: Decomposed violations, from one run or from many — the caller
            decides the scope and owns it.
        key: Field names of `ViolationEvent` to deduplicate on, e.g.
            `("class_name", "method", "spec")` or the message-level key.

    Returns:
        The number of distinct tuples of those fields.

    Raises:
        AttributeError: A named field does not exist on `ViolationEvent`.
    """
    return len({tuple(getattr(event, field) for field in key) for event in events})

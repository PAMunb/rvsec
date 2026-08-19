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
import re
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
    "code",
    "event",
    "message",
    "unique_msg",
)

#: `unique_msg` joins seven fields with this separator, in the order
#: `class, method, spec, error_type, code, event, message`. It is the only place the
#: CSV carries the violation type, which the consolidator otherwise drops, and — for a
#: row whose `code`/`event` columns were written by the same producer from the same
#: object — a second, independent copy of the attribution, which is why a disagreement
#: between the two is worth a number.
_UNIQUE_SEPARATOR = ":::"
_UNIQUE_FIELDS = 7

#: The v1 message envelope, as the `jca_android` monitors write it into the seventh
#: comma field:
#: `v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='…' exp='…' msg='…'`.
#: The grammar is restated here rather than imported from `rv_coverage`, which parses
#: the same envelope for the platform: that module is not a declared dependency of this
#: one (only `step_bundle` reaches for it, lazily and optionally), and a Layer-3 reader
#: that could not read a recorded artefact without the platform installed would not be
#: a reader of recorded artefacts.
_ENVELOPE_PREFIX = "v=1"
_ENVELOPE_KEY = re.compile(r"([A-Za-z][A-Za-z0-9_]*)=")
_ENVELOPE_KEYS = ("code", "ev", "obj", "val", "exp", "msg")

#: What `ViolationEvent.envelope_status` can hold.
ENVELOPE_ABSENT = "absent"
ENVELOPE_OK = "ok"
ENVELOPE_MALFORMED = "malformed"
ENVELOPE_TRUNCATED = "truncated"


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
        code: Stable violation code from the message envelope (`code=`), `""` when
            the message carries none.
        event: Automaton event that failed (`ev=`), `""` when absent.
        obj: Simple class of the monitored object (`obj=`).
        val: Observed value (`val=`).
        exp: Expected value or list (`exp=`), commas included.
        msg: Human-readable text of the envelope (`msg=`).
        shape_ok: Whether the payload decomposed into the seven fields **and** its
            envelope, if it declared one, was well formed. False keeps the line
            countable without pretending it was understood.
        envelope_status: Which of the two `shape_ok` failures applies, so the reader
            can count `envelope_malformed` and `envelope_truncated` apart without
            re-parsing the message. `absent` is not a failure: a pre-change message is
            a legitimate shape, not a defect.
    """

    spec: str
    class_name: str
    simple_class: str
    method: str
    location: str
    violation_type: str
    message: str
    shape_ok: bool = True
    code: str = ""
    event: str = ""
    obj: str = ""
    val: str = ""
    exp: str = ""
    msg: str = ""
    envelope_status: str = ENVELOPE_ABSENT


@dataclass(frozen=True)
class CsvDiagnostics:
    """What reading `errors.csv` encountered.

    Attributes:
        rows: Data rows read.
        unique_msg_unparsed: Rows whose `unique_msg` did not carry the five
            `:::`-joined fields, and whose `violation_type` is therefore empty.
            Counted rather than raised: the event itself is intact.
        unique_msg_disagrees: Rows whose `code`/`event` recovered from `unique_msg`
            differ from the CSV's own `code`/`event` columns. Both are written by one
            producer from one object, so a disagreement is a transport defect worth a
            number — not a choice the reader makes silently by preferring one of them.
    """

    rows: int
    unique_msg_unparsed: int
    unique_msg_disagrees: int = 0


@dataclass(frozen=True)
class LogcatDiagnostics:
    """What reading one run's `RVSEC` lines encountered.

    Attributes:
        lines: `RVSEC` lines read, whatever their shape.
        shape_bad: Lines that did not decompose into the seven comma fields. Kept
            whole in `message` and counted (INV-CAN-04).
        envelope_malformed: Lines whose seventh field declared `v=1` and then did not
            match the grammar. The seven comma fields are still populated.
        envelope_truncated: Lines whose last quoted value was never closed — logcat
            cuts a payload at 4068 bytes without a marker, so an unclosed quote is the
            only evidence the record is half a record.
        skipped_lines: Lines that carried the tag exactly and whose threadtime shape
            the reader could not parse at all, counted by `read_tagged_lines`.
    """

    lines: int
    shape_bad: int
    envelope_malformed: int
    envelope_truncated: int
    skipped_lines: int = 0


def _read_quoted(message: str, pos: int) -> tuple[str, int, bool]:
    """Read one single-quoted envelope value, undoing `\'` and `\n`.

    Returns `(value, position_after_the_closing_quote, closed)`.
    """
    chars: list[str] = []
    size = len(message)
    while pos < size:
        char = message[pos]
        if char == "\\" and pos + 1 < size:
            following = message[pos + 1]
            if following == "'":
                chars.append("'")
            elif following == "n":
                chars.append("\n")
            elif following == "\\":
                chars.append("\\")
            else:
                chars.append(char)
                pos += 1
                continue
            pos += 2
            continue
        if char == "'":
            return "".join(chars), pos + 1, True
        chars.append(char)
        pos += 1
    return "".join(chars), pos, False


def _parse_envelope(message: str) -> tuple[dict[str, str], str]:
    """
    Decompose the seventh comma field when it is a v1 envelope.

    Args:
        message: The seventh field, verbatim.

    Returns:
        `(fields, status)`. `status` is `absent` when the text does not declare
        `v=1` at all — a legacy `unknown`, a free-text `expecting …`, a cmp162
        message; those are legitimate shapes, not defects. It is `truncated` when a
        quoted value's closing quote never arrived, `malformed` when the envelope
        declared itself and then did not carry the six keys of the grammar, and `ok`
        otherwise. Fields parsed before a truncation are kept; nothing from the cut
        value onwards is, because a value read up to an arbitrary byte is not the
        value.
    """
    if not message.startswith(_ENVELOPE_PREFIX):
        return {}, ENVELOPE_ABSENT

    fields: dict[str, str] = {}
    pos, size = 0, len(message)
    while pos < size:
        match = _ENVELOPE_KEY.match(message, pos)
        if not match:
            pos += 1
            continue
        key = match.group(1)
        pos = match.end()
        if pos < size and message[pos] == "'":
            value, pos, closed = _read_quoted(message, pos + 1)
            if not closed:
                return fields, ENVELOPE_TRUNCATED
            fields[key] = value
        else:
            end = message.find(" ", pos)
            end = size if end == -1 else end
            fields[key] = message[pos:end]
            pos = end

    if any(key not in fields for key in _ENVELOPE_KEYS):
        return fields, ENVELOPE_MALFORMED
    return fields, ENVELOPE_OK


def parse_payload(payload: str) -> ViolationEvent:
    """
    Decompose one `RVSEC` payload into its seven fields, and its seventh into the
    envelope's keys.

    This is the only payload parser in the module. `clock_logcat_join` calls it too,
    so the step timeline, the run join and the event frame cannot disagree about what
    a line said.

    Args:
        payload: The line's text after the tag, never the whole line.

    Returns:
        The decomposed event. A payload with fewer than seven fields is returned
        whole in `message` with `shape_ok` False — the line is still a violation and
        still counts. A seventh field that declares `v=1` and then fails the grammar,
        or whose last quoted value is unclosed, keeps its seven comma fields and the
        envelope keys read before the failure, and carries `shape_ok` False with the
        reason in `envelope_status`.
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

    envelope, status = _parse_envelope(fields[6])
    return ViolationEvent(
        spec=fields[0],
        class_name=fields[1],
        simple_class=fields[2],
        method=fields[3],
        location=fields[4],
        violation_type=fields[5],
        message=fields[6],
        shape_ok=status in (ENVELOPE_ABSENT, ENVELOPE_OK),
        code=envelope.get("code", ""),
        event=envelope.get("ev", ""),
        obj=envelope.get("obj", ""),
        val=envelope.get("val", ""),
        exp=envelope.get("exp", ""),
        msg=envelope.get("msg", ""),
        envelope_status=status,
    )


def read_logcat(
    logcat_path: Path | str,
) -> tuple[list[tuple[dt.datetime, ViolationEvent]], LogcatDiagnostics]:
    """
    Read one run's violations from its logcat, in file order.

    Args:
        logcat_path: Recorded `.logcat` file. Not written to.

    Returns:
        `(events, diagnostics)`. Each event is `(stamp, event)`; the stamp is the
        device wall clock in the placeholder frame `clock_logcat_join` reads it in —
        comparable against that module's heartbeats and against nothing else. The
        diagnostics travel with the events rather than beside them because a caller
        that received only the events could not tell a run whose lines were discarded
        from a run that had none (INV-CAN-04).

    Raises:
        OSError: The file cannot be read. A run with no logcat is the caller's to
            report as such; an empty list here means the file existed and carried
            no violation, which is a measurement.
    """
    lines = read_tagged_lines(Path(logcat_path), VIOLATION_TAG)
    events = [(stamp, parse_payload(payload)) for stamp, payload in lines]
    return events, LogcatDiagnostics(
        lines=len(lines),
        # A short payload, not a bad envelope: the two failures are counted apart
        # because they have different producers and different repairs.
        shape_bad=sum(
            1
            for _, event in events
            if not event.shape_ok and event.envelope_status == ENVELOPE_ABSENT
        ),
        envelope_malformed=sum(
            1 for _, event in events if event.envelope_status == ENVELOPE_MALFORMED
        ),
        envelope_truncated=sum(
            1 for _, event in events if event.envelope_status == ENVELOPE_TRUNCATED
        ),
        skipped_lines=getattr(lines, "skipped", 0),
    )


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
            "code": event.code,
            "event": event.event,
            "shape_ok": event.shape_ok,
        }
        for stamp, event in events
    ]
    return pd.DataFrame(
        records, columns=["stamp", *PAYLOAD_FIELDS, "code", "event", "shape_ok"]
    )


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
        the tool's action — plus `violation_type`, `code`, `event` and
        `unique_message` recovered from the seven `:::` parts of `unique_msg`.

    Raises:
        OSError: The file cannot be read.
        ValueError: The header is not the one rv-platform writes. A silently
            renamed column is worse than a stopped read: every downstream count
            would be computed over a column that is no longer what it says. The
            10-column article dataset and the 11-column pre-gh104 layout both raise
            it by design: their declared readers live in the baseline scripts,
            outside this module, so no compatibility branch here can turn a header
            mismatch back into a guess (INV-CAN-25).
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
    disagrees = 0
    records = []
    for row in rows:
        parts = (row["unique_msg"] or "").split(_UNIQUE_SEPARATOR)
        if len(parts) == _UNIQUE_FIELDS:
            violation_type, code, event, unique_message = (
                parts[3],
                parts[4],
                parts[5],
                parts[6],
            )
            # The key and the columns are two copies of one attribution, written by
            # one producer from one object. Where they differ the row is kept and
            # counted: preferring either silently would turn a transport defect into
            # a reading.
            if (code, event) != (row["code"], row["event"]):
                disagrees += 1
        else:
            # Any part count other than seven — a five-part key of the previous
            # identity era, or a `message` carrying the separator the grammar
            # forbids. The row is kept whole and counted, never reinterpreted by
            # taking the parts positionally anyway (INV-CAN-26).
            violation_type, code, event = "", "", ""
            unique_message = row["unique_msg"] or ""
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
                "code": code,
                "event": event,
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
                "code",
                "event",
                "unique_message",
            ],
        ),
        CsvDiagnostics(
            rows=len(rows),
            unique_msg_unparsed=unparsed,
            unique_msg_disagrees=disagrees,
        ),
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

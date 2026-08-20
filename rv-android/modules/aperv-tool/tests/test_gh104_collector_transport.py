"""The collector's line reaches the `errors.csv` columns with its keys intact (gh104 9.3).

The input is not authored: `data/gh104/evidence/collector_lines.logcat` is a transcript of
`br.unb.cic.mop.eh.ErrorCollector.buildLine`, recorded from the compiled collector, and its
two envelope lines are asserted verbatim on the Java side by
`ErrorCollectorTest.buildLineReproducesTheRecordedFixtureLineByteForByte`. The sibling half of
this check — the same transcript through `rv-coverage`'s parser into `RvErrorLog` — lives in
`modules/rv-coverage/tests/parser/log/test_gh104_collector_transport.py`; the chain is split
by module because each half asserts the code its own module owns.

What this half establishes is that the two identity keys survive the round trip through the
file: `read_logcat` recovers them from the envelope, the thirteen-column writer puts them in
their own columns, and `read_errors_csv` finds the columns and the `unique_msg` parts saying
the same thing. The two are written by one producer from one object, so a disagreement
between them is a defect and not a reconciliation problem — which is why `read_errors_csv`
counts it.
"""

from __future__ import annotations

import csv
from pathlib import Path

from rv_android_core.domain.log import RvErrorLog

from aperv_tool.analysis.violations import ERRORS_CSV_HEADER, read_errors_csv, read_logcat

#: Recorded from the collector, not authored. Shared with the `rv-coverage` half rather than
#: copied: a second transcript is a second thing to keep in agreement with the producer.
FIXTURE = (
    Path(__file__).resolve().parents[3] / "data" / "gh104" / "evidence" / "collector_lines.logcat"
)


def _events():
    events, diagnostics = read_logcat(FIXTURE)
    return [event for _stamp, event in events], diagnostics


def test_read_logcat_recovers_both_keys_from_the_envelope():
    events, diagnostics = _events()

    assert len(events) == 3
    assert diagnostics.shape_bad == 0
    assert diagnostics.envelope_malformed == 0
    assert diagnostics.envelope_truncated == 0

    update, reset, legacy = events
    assert (update.code, update.event) == ("MESSAGEDIGEST-ORDER-00", "update")
    assert (reset.code, reset.event) == ("MESSAGEDIGEST-ORDER-00", "reset")
    # One code, two events: the code of a sequence violation is a function of the
    # specification name, so it is the event that separates the two causes at this site.
    assert update.code == reset.code

    # A pre-envelope message is a legitimate shape, not a defect: it carries no keys, and
    # the reader says so with empty strings rather than inventing any.
    assert (legacy.code, legacy.event) == ("", "")


def _errors_csv(path: Path) -> Path:
    """The thirteen columns exactly as `rv-platform` writes them (INV-PLT-19)."""
    events, _diagnostics = _events()
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(ERRORS_CSV_HEADER)
        for index, event in enumerate(events):
            # `code` and `event` are fields of the model, not values it derives from the
            # message: the producer that read the envelope is the one that knows them, and
            # the sentinel — never an empty cell — is what a record without an envelope
            # carries. `rv-platform`'s writer applies the same default.
            record = RvErrorLog(
                spec=event.spec,
                error_type=event.violation_type,
                class_full_name=event.class_name,
                method=event.method,
                source=event.location,
                code=event.code or "UNSPECIFIED",
                event=event.event or "UNSPECIFIED",
                message=event.message,
            )
            writer.writerow(
                [
                    "com.example.vault",
                    1,
                    60,
                    "monkey",
                    index,
                    event.spec,
                    event.class_name,
                    event.method,
                    event.location,
                    record.code,
                    record.event,
                    event.message,
                    record.unique_msg,
                ]
            )
    return path


def test_the_columns_and_the_unique_msg_parts_agree(tmp_path):
    frame, diagnostics = read_errors_csv(_errors_csv(tmp_path / "errors.csv"))

    assert len(frame) == 3
    assert diagnostics.unique_msg_unparsed == 0
    # Both copies of the attribution are written by one producer from one object. A
    # disagreement would mean the writer and the domain key had forked, which is the failure
    # the seven-part key exists to make visible rather than absorb.
    assert diagnostics.unique_msg_disagrees == 0

    assert list(frame["code"]) == [
        "MESSAGEDIGEST-ORDER-00",
        "MESSAGEDIGEST-ORDER-00",
        "UNSPECIFIED",
    ]
    assert list(frame["event"]) == ["update", "reset", "UNSPECIFIED"]


def test_two_events_at_one_site_are_two_rows_with_distinct_unique_msg(tmp_path):
    frame, _diagnostics = read_errors_csv(_errors_csv(tmp_path / "errors.csv"))

    at_site = frame[frame["event"].isin(["update", "reset"])]
    assert len(at_site) == 2
    # Same specification, same error kind, same call site — everything the five-part identity
    # compared. Under it these were one row and the survivor was arrival order.
    assert at_site["spec"].nunique() == 1
    assert at_site["class_name"].nunique() == 1
    assert at_site["method"].nunique() == 1
    assert at_site["location"].nunique() == 1
    assert at_site["violation_type"].nunique() == 1
    assert at_site["unique_message"].nunique() == 2

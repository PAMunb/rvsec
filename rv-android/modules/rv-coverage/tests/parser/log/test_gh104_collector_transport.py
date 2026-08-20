"""The collector's line reaches `RvErrorLog` with its two identity keys intact (gh104 9.3).

Every other test of the envelope in this suite authors its input string. This one does not:
`data/gh104/evidence/collector_lines.logcat` is a transcript of
`br.unb.cic.mop.eh.ErrorCollector.buildLine`, recorded from the compiled collector, and the
same two envelope lines are asserted verbatim on the Java side by
`ErrorCollectorTest.buildLineReproducesTheRecordedFixtureLineByteForByte`. A transcript can
go stale in silence — it would keep passing while the producer moved on, and this test would
then be measuring a format nothing emits — so the two halves pin each other and neither can
drift alone.

What it establishes is the premise of the identity change: two reports that name the same
specification, the same error kind and the same call site, and differ only in the event that
failed, arrive as **two** records. Under the five-part key that preceded gh104 they were one,
and which of the two survived was arrival order.
"""

from __future__ import annotations

from pathlib import Path

from rv_coverage.parser.log.logcat_parser import parse_logcat_line

#: Recorded from the collector, not authored. Kept under `data/gh104/evidence/` rather than
#: in this module's fixtures because the other half of the chain — the `errors.csv` columns,
#: checked in `aperv-tool` — reads the same transcript, and a second copy is a second thing
#: to keep in agreement.
FIXTURE = (
    Path(__file__).resolve().parents[5] / "data" / "gh104" / "evidence" / "collector_lines.logcat"
)

SITE = ("MessageDigestSpec", "InvalidSequenceOfMethodCalls", "com.example.vault.Hash", "digest")


def _errors() -> list:
    records = []
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        error, _coverage = parse_logcat_line(line)
        if error is not None:
            records.append(error)
    return records


def test_the_transcript_carries_the_three_recorded_reports():
    errors = _errors()

    assert len(errors) == 3
    for error in errors:
        assert (error.spec, error.error_type, error.class_full_name, error.method) == SITE
        assert error.source == "Hash.java:40"


def test_the_two_identity_keys_come_from_the_envelope():
    update, reset, legacy = _errors()

    assert (update.code, update.event) == ("MESSAGEDIGEST-ORDER-00", "update")
    assert (reset.code, reset.event) == ("MESSAGEDIGEST-ORDER-00", "reset")
    # The failure code is identical on both, which is the whole reason `event` is in the
    # identity: every specification of the set has at most one `@fail` handler, so the code of
    # a sequence violation is a function of the specification name and separates nothing.
    assert update.code == reset.code

    # A pre-envelope message keeps a readable identity rather than a null one.
    assert (legacy.code, legacy.event) == ("UNSPECIFIED", "UNSPECIFIED")


def test_unique_msg_has_seven_parts_and_carries_the_keys_in_order():
    update, _reset, legacy = _errors()

    parts = update.unique_msg.split(":::")
    assert len(parts) == 7
    assert parts[4] == "MESSAGEDIGEST-ORDER-00"
    assert parts[5] == "update"

    legacy_parts = legacy.unique_msg.split(":::")
    assert len(legacy_parts) == 7
    assert legacy_parts[4:6] == ["UNSPECIFIED", "UNSPECIFIED"]


def test_two_events_at_one_site_do_not_deduplicate():
    update, reset, _legacy = _errors()

    assert update.unique_msg != reset.unique_msg
    assert update != reset
    assert len({update, reset}) == 2

    # And the message free text is still outside the identity: it is identical on these two,
    # so what separated them was the event alone.
    assert update.message.replace("ev=update", "ev=X") == reset.message.replace("ev=reset", "ev=X")

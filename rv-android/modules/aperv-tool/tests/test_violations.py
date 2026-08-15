"""The violation stream keeps every field the logger wrote, message included.

The one defect this module exists to prevent is a message cut in half. The
payload is seven comma-separated fields and the seventh legitimately contains
commas — `expecting one of {TLSv1.2, TLSv1.3} but found TLS.` — so a split on
every comma yields nine fields, a garbled `violationType` and a truncated
message, all of which look like data. The bound is six, and the tests below pin
both the bound and the shape it produces on payloads taken verbatim from the
recorded campaign.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fixture_gate import MISSING_REAL

from aperv_tool.analysis import violations

# Verbatim from a recorded logcat: the message carries two commas of its own.
WITH_COMMAS = (
    "SSLContextSpec,okhttp3.internal.platform.Platform,Platform,"
    "newSslSocketFactory,Platform.kt:168,UnsafeProtocol,"
    "expecting one of {TLSv1.2, TLSv1.3} but found TLS."
)
WITHOUT_COMMAS = (
    "TrustManagerFactorySpec,okhttp3.internal.platform.Platform,Platform,"
    "platformTrustManager,Platform.kt:78,InvalidSequenceOfMethodCalls,unknown"
)


def test_message_with_commas_kept_whole() -> None:
    """The split is bounded at six; the remainder is the message, uncut."""
    event = violations.parse_payload(WITH_COMMAS)

    assert event.spec == "SSLContextSpec"
    assert event.class_name == "okhttp3.internal.platform.Platform"
    assert event.simple_class == "Platform"
    assert event.method == "newSslSocketFactory"
    assert event.location == "Platform.kt:168"
    assert event.violation_type == "UnsafeProtocol"
    assert event.message == "expecting one of {TLSv1.2, TLSv1.3} but found TLS."
    assert event.shape_ok


def test_a_payload_of_another_shape_is_kept_not_dropped() -> None:
    """An unexpected shape still counts as a violation, whole and flagged."""
    event = violations.parse_payload("SomeSpec,went into an error state")

    assert event.shape_ok is False
    assert event.message == "SomeSpec,went into an error state"
    assert event.spec == "SomeSpec"


def test_the_frame_carries_every_field(tmp_path: Path) -> None:
    """Reading a logcat yields one row per line with the seven fields."""
    logcat = tmp_path / "run.logcat"
    logcat.write_text(
        "\n".join(
            [
                f"08-12 19:32:45.521  3269  3572 V RVSEC   : {WITHOUT_COMMAS}",
                f"08-12 19:32:45.588  3269  3572 V RVSEC   : {WITH_COMMAS}",
                # A neighbouring tag the reader must not admit: the coverage
                # stream is two orders of magnitude larger and shares the prefix.
                "08-12 19:32:45.600  3269  3572 I RVSEC-COV: <a.B: void c()>",
            ]
        )
        + "\n"
    )

    frame = violations.frame(violations.read_logcat(logcat))

    assert len(frame) == 2
    assert list(frame["violation_type"]) == [
        "InvalidSequenceOfMethodCalls",
        "UnsafeProtocol",
    ]
    assert frame["message"].iloc[1].endswith("but found TLS.")


def test_distinct_names_its_key() -> None:
    """Two conventions disagree, so the key is the caller's and it is required."""
    events = [
        violations.parse_payload(WITH_COMMAS),
        violations.parse_payload(WITH_COMMAS.replace("but found TLS.", "but found X.")),
    ]

    assert violations.distinct(events, ("class_name", "method", "spec")) == 1
    assert violations.distinct(events, ("class_name", "method", "spec", "message")) == 2


def test_errors_csv_header_is_checked(tmp_path: Path) -> None:
    """A renamed column stops the read instead of silently changing a count."""
    path = tmp_path / "errors.csv"
    path.write_text("apk,rep,timeout,tool,time\napp.apk,1,300,ape,6\n")

    with pytest.raises(ValueError):
        violations.read_errors_csv(path)


def test_errors_csv_of_the_campaign(cmp162_root: Path, cmp162_manifest: dict) -> None:
    """The consolidated CSV reads at event grain, with the violation type recovered.

    `unique_msg` is the only column carrying the violation type, and the `time`
    column times the violation rather than a tool action — the frame's column
    name says so.
    """
    relative = next(
        (
            name
            for name in sorted(cmp162_manifest["files"])
            if name.endswith("errors.csv")
        ),
        None,
    )
    if relative is None or not (cmp162_root / relative).is_file():
        pytest.skip(f"{MISSING_REAL}: no consolidated errors.csv pinned")

    frame, diagnostics = violations.read_errors_csv(cmp162_root / relative)

    assert len(frame) == diagnostics.rows
    assert diagnostics.unique_msg_unparsed == 0
    assert "violation_time_s" in frame.columns
    assert (frame["violation_type"] != "").all()

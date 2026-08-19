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

import csv
from pathlib import Path

import pytest

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

    events, diagnostics = violations.read_logcat(logcat)
    frame = violations.frame(events)

    assert len(frame) == 2
    assert diagnostics.lines == 2
    assert (diagnostics.shape_bad, diagnostics.envelope_malformed) == (0, 0)
    assert diagnostics.envelope_truncated == 0
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


def test_errors_csv_reads_the_thirteen_column_header(tmp_path: Path) -> None:
    """The consolidated CSV reads at event grain, with the violation type, the code
    and the event recovered from the seven `:::` parts of `unique_msg`.

    The fixture is synthetic rather than cmp162's own file: cmp162 carries the
    11-column pre-change layout, which this reader rejects by design, and it is read
    for parity through the declared historical reader in the change's baseline
    scripts. cmp162 is a fixture, not a corpus.
    """
    envelope = (
        "v=1 code=MESSAGEDIGEST-ALG-01 ev=update obj=MessageDigest val='MD2' "
        "exp='MD5,SHA-224,SHA-256' msg='expecting one of MD5,SHA-224,SHA-256 but found MD2'"
    )
    unique = (
        "okio.ByteString:::digest$okio:::MessageDigestSpec:::UnsafeAlgorithm"
        f":::MESSAGEDIGEST-ALG-01:::update:::{envelope}"
    )
    path = tmp_path / "errors.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(violations.ERRORS_CSV_HEADER)
        writer.writerow(
            [
                "app.apk",
                "1",
                "300",
                "aperv",
                "6",
                "MessageDigestSpec",
                "okio.ByteString",
                "digest$okio",
                "ByteString.kt:12",
                "MESSAGEDIGEST-ALG-01",
                "update",
                envelope,
                unique,
            ]
        )

    frame, diagnostics = violations.read_errors_csv(path)

    assert len(frame) == diagnostics.rows == 1
    assert frame["violation_type"].iloc[0] == "UnsafeAlgorithm"
    assert frame["code"].iloc[0] == "MESSAGEDIGEST-ALG-01"
    assert frame["event"].iloc[0] == "update"
    assert frame["unique_message"].iloc[0] == envelope
    assert frame["violation_time_s"].iloc[0] == 6.0
    assert (diagnostics.unique_msg_unparsed, diagnostics.unique_msg_disagrees) == (0, 0)


def test_the_eleven_column_layout_is_rejected_by_name(tmp_path: Path) -> None:
    """INV-CAN-25: the error names the header expected, so the reader of a cmp162 file
    is told which instrument to use instead of guessing at a missing column."""
    path = tmp_path / "errors.csv"
    path.write_text(
        "apk,rep,timeout,tool,time,spec,class,method,source,message,unique_msg\n"
        "app.apk,1,300,aperv,6,S,C,m,C.java:1,unknown,C:::m:::S:::T:::unknown\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as raised:
        violations.read_errors_csv(path)

    assert str(path) in str(raised.value)
    assert "'code', 'event'" in str(raised.value)


def test_a_five_part_unique_msg_is_counted_unparsed(tmp_path: Path) -> None:
    """A key of the previous identity era is kept and counted, never reinterpreted by
    taking its parts positionally anyway (INV-CAN-26)."""
    five_part = "com.example.Hash:::digest:::MessageDigestSpec:::UnsafeAlgorithm:::unknown"
    path = _one_row_csv(tmp_path, code="UNSPECIFIED", event="UNSPECIFIED", unique=five_part)

    frame, diagnostics = violations.read_errors_csv(path)

    assert len(frame) == 1
    assert frame["violation_type"].iloc[0] == ""
    assert frame["code"].iloc[0] == ""
    assert frame["event"].iloc[0] == ""
    assert frame["unique_message"].iloc[0] == five_part
    assert diagnostics.unique_msg_unparsed == 1
    assert diagnostics.unique_msg_disagrees == 0


def test_a_key_that_disagrees_with_its_columns_is_counted(tmp_path: Path) -> None:
    """Both are written by one producer from one object; a disagreement is a transport
    defect worth a number, not a choice the reader makes silently."""
    unique = "com.example.Hash:::digest:::MessageDigestSpec:::UnsafeAlgorithm:::A-01:::g1:::unknown"
    path = _one_row_csv(tmp_path, code="A-02", event="g1", unique=unique)

    frame, diagnostics = violations.read_errors_csv(path)

    assert len(frame) == 1
    assert diagnostics.unique_msg_unparsed == 0
    assert diagnostics.unique_msg_disagrees == 1


def test_a_truncated_envelope_is_kept_with_shape_ok_false(tmp_path: Path) -> None:
    """Logcat cuts a payload at 4068 bytes without a marker, so an unclosed quote is
    the only evidence the record is half a record. The line is still a violation."""
    payload = (
        "CipherSpec,com.example.Crypto,Crypto,doEncrypt,Crypto.java:15,UnsafeAlgorithm,"
        "v=1 code=CIPHER-ALG-02 ev=c1 obj=Cipher val='AES/ECB/PKCS5Padding' "
        "exp='AES/GCM/NoPadding,AES/CBC/PKCS7Pad"
    )
    logcat = tmp_path / "run.logcat"
    logcat.write_text(f"08-12 19:32:45.521  3269  3572 V RVSEC   : {payload}\n")

    events, diagnostics = violations.read_logcat(logcat)
    (_, event), = events

    assert event.spec == "CipherSpec"
    assert event.class_name == "com.example.Crypto"
    assert event.simple_class == "Crypto"
    assert event.method == "doEncrypt"
    assert event.location == "Crypto.java:15"
    assert event.violation_type == "UnsafeAlgorithm"
    assert (event.code, event.event, event.obj) == ("CIPHER-ALG-02", "c1", "Cipher")
    assert event.val == "AES/ECB/PKCS5Padding"
    assert (event.exp, event.msg) == ("", "")
    assert event.shape_ok is False
    assert diagnostics.envelope_truncated == 1
    assert diagnostics.shape_bad == 0
    assert violations.distinct([event], ("class_name", "method", "spec")) == 1


def test_a_pre_change_free_text_message_is_not_a_defect() -> None:
    """A cmp162 message declares no envelope; that is a legitimate shape."""
    event = violations.parse_payload(
        "SSLContextSpec,com.example.Net,Net,open,Net.java:9,UnsafeProtocol,"
        "expecting one of TLSv1.2, TLSv1.3 but found SSLv3"
    )

    assert event.message == "expecting one of TLSv1.2, TLSv1.3 but found SSLv3"
    assert (event.code, event.event) == ("", "")
    assert event.shape_ok is True
    assert event.envelope_status == violations.ENVELOPE_ABSENT


def test_an_envelope_missing_a_key_is_malformed_and_kept() -> None:
    """It declared `v=1` and then did not carry the grammar, so the seven comma fields
    stand and the envelope is flagged rather than half-believed."""
    event = violations.parse_payload(
        "CipherSpec,com.example.C,C,enc,C.java:9,UnsafeAlgorithm,"
        "v=1 code=CIPHER-ALG-02 ev=c1 obj=Cipher"
    )

    assert event.spec == "CipherSpec"
    assert event.code == "CIPHER-ALG-02"
    assert event.shape_ok is False
    assert event.envelope_status == violations.ENVELOPE_MALFORMED


def _one_row_csv(tmp_path: Path, *, code: str, event: str, unique: str) -> Path:
    path = tmp_path / "errors.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(violations.ERRORS_CSV_HEADER)
        writer.writerow(
            [
                "app.apk",
                "1",
                "300",
                "aperv",
                "6",
                "MessageDigestSpec",
                "com.example.Hash",
                "digest",
                "Hash.java:40",
                code,
                event,
                "unknown",
                unique,
            ]
        )
    return path

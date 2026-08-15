"""Executed instrumented methods, joined to the static artefact by exact equality.

The payload is a full Soot signature, and the static artefact's `signature` field
is the same string. That is the whole join, and the tests keep it that way: no
normalisation, no erasure of parameter types, no fuzzy match. A normalisation
would collapse overloads the static analysis kept apart and would quietly answer a
different question.

The reader also has to keep two streams apart that share a prefix: `RVSEC` and
`RVSEC-COV` arrive in one file, and the coverage stream is roughly a hundred times
larger, so a prefix match in either direction is both wrong and expensive.
"""

from __future__ import annotations

from pathlib import Path

from aperv_tool.analysis import monitored_ops

CLINIT = "<io.keepalive.android.AppController: void <clinit>()>"
WITH_PARAMS = (
    "<io.keepalive.android.AppController$Companion: void "
    "<init>(kotlin.jvm.internal.DefaultConstructorMarker)>"
)


def test_signature_is_kept_verbatim_and_decomposed() -> None:
    """The join key is the payload; the decomposition is a convenience beside it."""
    op = monitored_ops.parse_payload(WITH_PARAMS)

    assert op.signature == WITH_PARAMS
    assert op.declaring_class == "io.keepalive.android.AppController$Companion"
    assert op.method == "<init>"
    assert op.parameter_types == "kotlin.jvm.internal.DefaultConstructorMarker"
    assert op.shape_ok


def test_a_static_initializer_parses() -> None:
    """`<clinit>` is a method name, not a malformed signature."""
    op = monitored_ops.parse_payload(CLINIT)

    assert op.method == "<clinit>"
    assert op.parameter_types == ""


def test_an_unexpected_payload_keeps_its_text() -> None:
    """A payload of another shape is still an execution and still counts."""
    op = monitored_ops.parse_payload("a.B:::c:::")

    assert op.shape_ok is False
    assert op.signature == "a.B:::c:::"
    assert op.declaring_class is None


def test_the_reader_admits_only_its_own_tag(tmp_path: Path) -> None:
    """`RVSEC` lines are not coverage lines, and the tags share a prefix."""
    logcat = tmp_path / "run.logcat"
    logcat.write_text(
        "\n".join(
            [
                f"08-13 08:08:26.300  3113  3113 I RVSEC-COV: {CLINIT}",
                "08-13 08:08:26.400  3113  3113 V RVSEC   : Spec,a.B,B,c,B.kt:1,Type,msg",
                f"08-13 08:08:26.500  3113  3113 I RVSEC-COV: {WITH_PARAMS}",
            ]
        )
        + "\n"
    )

    ops = monitored_ops.read_logcat(logcat)

    assert [op.signature for _stamp, op in ops] == [CLINIT, WITH_PARAMS]
    assert len(monitored_ops.frame(ops)) == 2


def test_match_is_exact_string_equality() -> None:
    """An overload is a different method, and the denominator travels with the match."""
    ops = [
        monitored_ops.parse_payload(CLINIT),
        monitored_ops.parse_payload(CLINIT),
        monitored_ops.parse_payload(WITH_PARAMS),
    ]
    static = {
        CLINIT,
        "<io.keepalive.android.AppController$Companion: void <init>()>",
    }

    report = monitored_ops.match_signatures(ops, static)

    assert report.executions == 3
    assert report.distinct_signatures == 2
    # The parameterless overload of the same constructor is in the static set;
    # the one that ran is not the same method and does not match it.
    assert report.matched == 1
    assert report.unmatched == 1
    assert report.static_signatures == 2

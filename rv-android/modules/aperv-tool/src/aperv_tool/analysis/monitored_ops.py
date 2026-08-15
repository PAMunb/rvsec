"""
The monitored-operation stream: which instrumented methods actually executed.

The `RVSEC-COV` tag carries one line per execution of a method the coverage
aspect instruments, and its payload is the method's **full Soot signature** —
`<class: returnType name(paramTypes)>` — byte-identical to the `signature` field
of `reachability[].methods[]` in the static-analysis artefact. That identity is
what makes the two artefacts joinable at all, and it is why the join key here is
**exact string equality**: no normalisation, no erasure of parameter types, no
fuzzy match. A normalisation would collapse overloads that the static analysis
kept apart, and the resulting count would answer a different question than the
one it is labelled with.

The stream is dense — roughly a hundred times the violation stream in the
recorded corpus — which is why the tag reader it uses rejects a line on the byte
after the tag rather than by decoding it: `RVSEC` and `RVSEC-COV` are two streams
in one file, and a prefix match between them would silently mix them.

An execution line says a method **ran**; the static artefact says a method is
**reachable** and whether it reaches a monitored operation. The join of the two
is the observed half of a static prediction, and this module supplies only the
observed half.

Offline and read-only over recorded artefacts (INV-APV-35).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Collection, Iterable

import pandas as pd

from aperv_tool.analysis.clock_logcat_join import read_tagged_lines

#: The tag the coverage aspect writes under. Declared beside the violation tag in
#: rv-android-core's logging constants, and in the device-side capture allowlist:
#: a tag outside that allowlist never reaches the file at all.
MONITORED_OP_TAG = "RVSEC-COV"

# `<class: returnType name(paramTypes)>`. `name` admits `<init>` and `<clinit>`,
# whose angle brackets are part of the name the static analysis also carries.
_SIGNATURE = re.compile(
    r"^<(?P<class>[^:]+):\s+(?P<returns>[^ ]+)\s+"
    r"(?P<method>[^(]+)\((?P<params>[^)]*)\)>$"
)


@dataclass(frozen=True)
class MonitoredOp:
    """One execution of an instrumented method.

    Attributes:
        signature: The payload verbatim. This is the join key against the static
            artefact, compared by exact string equality and never rewritten.
        declaring_class: Class from the signature, or None when the payload was
            not a Soot signature. None is never filled in by guessing.
        method: Method name from the signature, `<init>` / `<clinit>` included,
            or None under the same condition.
        parameter_types: The comma-joined parameter list as written, or None.
        shape_ok: Whether the payload parsed as a Soot signature. A False still
            carries the payload in `signature`, so the line counts.
    """

    signature: str
    declaring_class: str | None = None
    method: str | None = None
    parameter_types: str | None = None
    shape_ok: bool = True


@dataclass(frozen=True)
class MatchReport:
    """The observed stream measured against a static signature set.

    Attributes:
        executions: Lines read, i.e. executions observed.
        distinct_signatures: Distinct signatures among them.
        matched: Distinct signatures the static set also carries.
        unmatched: Distinct signatures absent from it — never zero by
            construction, since the aspect instruments what the build reached
            while the artefact describes what the analysis reached.
        static_signatures: Size of the set that was matched against, so the
            fraction is never quoted without its denominator (INV-CAN-09).
    """

    executions: int
    distinct_signatures: int
    matched: int
    unmatched: int
    static_signatures: int


def parse_payload(payload: str) -> MonitoredOp:
    """
    Decompose one `RVSEC-COV` payload, keeping it verbatim either way.

    Args:
        payload: The line's text after the tag, never the whole line.

    Returns:
        The execution record. The signature is kept exactly as written whether or
        not it decomposed, because the decomposition is a convenience and the
        signature is the join key.
    """
    match = _SIGNATURE.match(payload)
    if match is None:
        return MonitoredOp(signature=payload, shape_ok=False)
    return MonitoredOp(
        signature=payload,
        declaring_class=match.group("class"),
        method=match.group("method"),
        parameter_types=match.group("params"),
    )


def read_logcat(logcat_path: Path | str) -> list[tuple[dt.datetime, MonitoredOp]]:
    """
    Read one run's monitored-operation executions, in file order.

    Args:
        logcat_path: Recorded `.logcat` file. Not written to.

    Returns:
        `(stamp, op)` per `RVSEC-COV` line, the stamp in the placeholder frame
        `clock_logcat_join` reads device stamps in.

    Raises:
        OSError: The file cannot be read.
    """
    return [
        (stamp, parse_payload(payload))
        for stamp, payload in read_tagged_lines(Path(logcat_path), MONITORED_OP_TAG)
    ]


def frame(ops: Iterable[tuple[dt.datetime, MonitoredOp]]) -> pd.DataFrame:
    """
    Lay executions out as a tidy frame at event grain.

    Args:
        ops: `(stamp, op)` pairs, as `read_logcat` returns them.

    Returns:
        One row per execution, columns fixed so an empty run concatenates with a
        populated one.
    """
    records = [
        {
            "stamp": stamp,
            "signature": op.signature,
            "declaring_class": op.declaring_class,
            "method": op.method,
            "parameter_types": op.parameter_types,
            "shape_ok": op.shape_ok,
        }
        for stamp, op in ops
    ]
    return pd.DataFrame(
        records,
        columns=[
            "stamp",
            "signature",
            "declaring_class",
            "method",
            "parameter_types",
            "shape_ok",
        ],
    )


def match_signatures(
    ops: Iterable[MonitoredOp], signatures: Collection[str]
) -> MatchReport:
    """
    Measure the observed stream against a static signature set, by exact equality.

    Args:
        ops: Executions observed, from one run or from many — the scope is the
            caller's and travels with the result.
        signatures: Signatures from `static_artifact`, e.g. every method or only
            the ones that reach a monitored operation. Which set was supplied is
            the caller's to record; this reports its size beside the match.

    Returns:
        The match, with both denominators. Comparison is `==` on the whole
        signature string: an overload differing only in parameter types is a
        different method here, as it is in the artefact.
    """
    observed = list(ops)
    distinct = {op.signature for op in observed}
    matched = distinct & set(signatures)
    return MatchReport(
        executions=len(observed),
        distinct_signatures=len(distinct),
        matched=len(matched),
        unmatched=len(distinct) - len(matched),
        static_signatures=len(signatures),
    )

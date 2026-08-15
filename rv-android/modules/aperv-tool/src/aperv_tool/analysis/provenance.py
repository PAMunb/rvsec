"""What produced a number, recorded so the number can be produced again.

An estimate is re-derivable when two things are unchanged: the inputs it read
and the parameters it was given. This module records both — each input by
sha256 where the input is a file, by path where it is not — and compares two
such records so that a rerun over changed inputs is **reported before anything
is computed**, not discovered afterwards from a moved decimal.

**Timestamps live here and never inside an estimate.** The temptation is
obvious: a result table carrying the moment it was computed is convenient. But
an estimate that carries the moment it ran is different from itself on every
rerun, so nothing downstream can compare two of them bit for bit, and the one
property that makes a re-derivation checkable is lost to a convenience. The
envelope therefore carries a ``provenance_ref``; the timestamp is on this side
of that reference, and ``differences`` ignores it by construction — a rerun an
hour later over the same bytes is a re-derivation, and saying otherwise would
make the comparison useless.

The record is deliberately blunt about what it cannot verify. An input recorded
by path alone has no digest to compare, so a change in it *cannot* be reported;
``differences`` says so rather than staying silent, because a silent absence of
evidence reads exactly like evidence of no change.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

#: Read size for hashing. Traces run to hundreds of megabytes, so inputs are
#: streamed rather than held.
_CHUNK = 1 << 20


@dataclass(frozen=True)
class InputRef:
    """One input an analysis read.

    Attributes:
        path: The input's path, as a string, so a record survives being written
            to disk and read back.
        sha256: The file's digest, or None when the input was recorded by path
            alone — a directory, a tree too large to hash, or a path that did
            not exist when the stamp was taken. None is a statement about the
            record, not about the file: it means a change here will not be
            reported.
    """

    path: str
    sha256: Optional[str]


@dataclass(frozen=True)
class Provenance:
    """The inputs, parameters and moment of one analysis run.

    Attributes:
        ref: The identifier an ``Envelope`` carries in ``provenance_ref``.
            Chosen by the caller; it is what ties a table cell back to this
            record.
        inputs: Every input read, sorted by path so two records of the same run
            compare directly.
        parameters: The parameter set the analysis was given, including every
            freeze item the caller had to supply explicitly. A parameter that
            changed silently is indistinguishable from a bug in the estimator,
            which is why the set is recorded whole rather than summarised.
        stamped_at: When the stamp was taken, ISO-8601 in UTC. It lives here
            precisely so it does not live in an estimate.
    """

    ref: str
    inputs: tuple[InputRef, ...]
    parameters: Mapping[str, Any]
    stamped_at: str


def sha256_of(path: Path) -> str:
    """Stream a file into a sha256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stamp(
    ref: str,
    inputs: Iterable[Path | str],
    parameters: Mapping[str, Any],
    *,
    now: Optional[datetime] = None,
) -> Provenance:
    """Record what an analysis is about to read and what it was told.

    Args:
        ref: The identifier envelopes of this run will carry.
        inputs: The files the analysis reads. Each existing regular file is
            hashed; anything else — a directory, a path that is not there — is
            recorded by path with no digest, which ``differences`` then reports
            as uncomparable rather than as unchanged.
        parameters: The parameter set, recorded whole.
        now: The stamping instant, injectable so a test can hold it fixed.
            Defaults to the current UTC time.

    Returns:
        The ``Provenance``.
    """
    moment = now if now is not None else datetime.now(timezone.utc)
    refs = []
    for entry in inputs:
        path = Path(entry)
        digest = sha256_of(path) if path.is_file() else None
        refs.append(InputRef(path=str(path), sha256=digest))
    return Provenance(
        ref=ref,
        inputs=tuple(sorted(refs, key=lambda item: item.path)),
        parameters=dict(parameters),
        stamped_at=moment.isoformat(),
    )


def differences(previous: Provenance, current: Provenance) -> tuple[str, ...]:
    """Everything that stops ``current`` from being a re-derivation of ``previous``.

    Call this **before** computing. An empty result is the only state in which
    two estimates are comparable bit for bit; a non-empty one is a report to
    print, and each line names the input or parameter that moved.

    ``stamped_at`` and ``ref`` are not compared: a rerun is expected to happen
    at a different moment under a different label, and treating either as a
    difference would make every rerun look incomparable.

    Args:
        previous: The record the earlier estimate was produced under.
        current: The record the rerun would be produced under.

    Returns:
        One line per difference, ordered inputs-then-parameters and sorted
        within each, so two reports of the same divergence read identically.
    """
    before = {item.path: item.sha256 for item in previous.inputs}
    after = {item.path: item.sha256 for item in current.inputs}

    report: list[str] = []
    for path in sorted(set(before) | set(after)):
        if path not in after:
            report.append(f"input removed: {path}")
        elif path not in before:
            report.append(f"input added: {path}")
        elif before[path] is None or after[path] is None:
            report.append(
                f"input not comparable: {path} was recorded by path alone, so a "
                "change in it cannot be reported"
            )
        elif before[path] != after[path]:
            report.append(
                f"input changed: {path} sha256 {before[path]} -> {after[path]}"
            )

    keys = sorted(set(previous.parameters) | set(current.parameters))
    for key in keys:
        if key not in current.parameters:
            report.append(f"parameter removed: {key}")
        elif key not in previous.parameters:
            report.append(f"parameter added: {key}")
        elif previous.parameters[key] != current.parameters[key]:
            report.append(
                f"parameter changed: {key} "
                f"{previous.parameters[key]!r} -> {current.parameters[key]!r}"
            )
    return tuple(report)

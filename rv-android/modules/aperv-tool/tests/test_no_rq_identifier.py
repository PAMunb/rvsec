"""No research-question identifier appears in the library (INV-CAN-22).

The library's second organising rule is that it is generic: it computes
estimates, and it does not know which question an estimate answers. That rule is
worth enforcing mechanically because the failure it prevents is silent. A column
named for a question, a flag named for a hypothesis, a branch that behaves one
way "for the primary" — each is small on its own, and together they are how a
library stops being reusable and becomes one campaign's script with a package
around it. The seat for a question identifier is `analysis/callers/` and its
`rq_map.toml`, where an entry maps to a builder, an estimator and its parameters.

The scan covers docstrings and comments as well as code, deliberately. A
docstring that says which question a function serves is the same coupling one
edit away from being read as licence to act on it.
"""

from __future__ import annotations

import re
from pathlib import Path

# `E1`, `T05`, `R13`, `RQ`, `RQ2` and the like, on word boundaries so an ordinary
# word is not flagged and `RVSEC` — R followed by letters — is not either.
#
# This implements INV-CAN-22 as the invariant states it (`E\d+`, `T\d+`, `R\d+`,
# `RQ`), not as its scenario writes it. The scenario's `\b[ETR]\d{2}\b` requires
# two digits and its `\bRQ\b` requires nothing after the Q, so between them they
# match none of the identifiers this project actually uses — and a shipped module
# under `analysis/` carried one at the moment this test was written. A pattern
# that cannot fail on the real vocabulary is not a guard.
RQ_IDENTIFIER = re.compile(r"\b[ETR]\d+\b|\bRQ\d*\b")

# The one place a question identifier is allowed to appear, by design.
ALLOWED = ("callers",)


def _analysis_root() -> Path:
    return Path(__import__("aperv_tool").__file__).parent / "analysis"


def _scanned_files() -> list[Path]:
    root = _analysis_root()
    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(part in ALLOWED for part in path.relative_to(root).parts)
    )


def test_no_rq_identifier_in_the_library() -> None:
    """Every `.py` under `analysis/`, `callers/` excepted."""
    offenders: list[str] = []
    for path in _scanned_files():
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            match = RQ_IDENTIFIER.search(line)
            if match:
                offenders.append(
                    f"{path.name}:{number}: {match.group(0)!r} in {line.strip()}"
                )

    assert (
        offenders == []
    ), "research-question identifiers in the library:\n" + "\n".join(offenders)


def test_the_scan_reaches_the_whole_package() -> None:
    """Non-vacuity: a scan over nothing passes while proving nothing."""
    scanned = _scanned_files()

    assert scanned, "no analysis module scanned — the package moved"
    assert any(
        path.name == "run_identity.py" for path in scanned
    ), "the scan is not reaching the shipped modules"


def test_the_pattern_catches_what_it_is_for() -> None:
    """Positive control for the pattern, and a negative one for its neighbours.

    The negatives matter as much as the positives: a pattern that flagged `RVSEC`
    or an invariant anchor would be turned off within a week, and then it would
    be guarding nothing.
    """
    for flagged in (
        "E1 is answered by",
        "column T05",
        "R13",
        "RQ2",
        "the RQ it serves",
    ):
        assert RQ_IDENTIFIER.search(flagged), flagged

    for allowed in (
        "RVSEC",
        "RVSEC-COV",
        "INV-CAN-22",
        "INV-APV-61",
        "the R replicas",
        "TEARDOWN_GRACE_S",
    ):
        assert not RQ_IDENTIFIER.search(allowed), allowed

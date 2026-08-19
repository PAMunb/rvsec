"""Gates over the successor specification set `jca_android` (gh104).

The set is seeded from the frozen `jca` and differs from it only by hunks a record
names, so what makes it checkable is enumeration rather than equality. Two gates
hold that shape:

    INV-INS-118   every hunk between the seed and the successor is named in
                  `data/jca_android/divergence_record.csv`, and no entry names a
                  hunk that no longer exists
    INV-INS-128   every `ExecutionContext` site of the seed survives into the
                  successor at the same event and unrewritten -- the predicate
                  machinery is carried over, not removed (design D-11)

Group 6 writes the structural gates over the generated monitor in
`test_gh104_structural_gates.py`; they read the same records and are kept in a
separate file so the two groups do not edit one.

All of these run against the sibling Java reactor, so they skip when it is absent.
"""

from __future__ import annotations

import collections
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data" / "jca_android"
SCRIPTS = REPO / "scripts"

SEED = "rvsec/rvsec-mop/src/main/resources/jca"
SUCCESSOR = "rvsec/rvsec-mop/src/main/resources/jca_android"

# A line belongs to the predicate machinery when it names the singleton or imports
# the property enum. Counted over the frozen seed, keyed by the construct each line
# performs, this is what the successor must still carry.
PREDICATE = re.compile(r"ExecutionContext")
EXPECTED_CONSTRUCTS = {
    "import": 23,
    "validate(": 27,
    "setProperty(": 49,
    "remove(": 9,
    "accepting-state": 25,
    "comment": 1,
}
EXPECTED_PREDICATE_LINES = 134
EXPECTED_SPECS = 23


def _rvsec_home() -> Path:
    home = os.environ.get("RVSEC_HOME")
    if not home or not (Path(home) / SUCCESSOR).is_dir():
        pytest.skip("RVSEC_HOME not set or the successor set is absent from the Java reactor")
    return Path(home)


def _classify(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("import"):
        return "import"
    for construct in ("validate(", "setProperty(", "remove("):
        if construct in stripped:
            return construct
    if "ObjectAsInAcceptingState" in stripped:
        return "accepting-state"
    return "comment"


def test_jca_android_hunks_all_recorded():
    """INV-INS-118: the seed diff and the divergence record name the same hunks.

    A hunk with no row is an unattributed change to an instrument; a row naming no
    hunk is a reason recorded for content that has since moved, which is worse than
    no reason at all because it reads as one.
    """
    _rvsec_home()
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "gh104_divergence_record.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_jca_android_predicates_preserved():
    """INV-INS-128: G-PRED, preservation, checked against the seed file by file.

    An earlier revision of this change deleted the predicate machinery outright.
    That is the largest behavioural change the set could take -- it deletes
    detection at 11 of the 21 predicate-reading events -- and it went in with no
    before/after evidence behind it, which is exactly what this gate exists to
    stop. The decision is withdrawn (design D-11) and the gate now runs the other
    way: the successor must carry every site the seed has, in the same order,
    byte-for-byte, so that a deletion cannot slip in as a side effect of an
    allow-list edit.

    Order matters as much as content. Comparing multisets would pass a file whose
    predicate moved from the event that reads a key to the one that writes it, and
    that is a behavioural change wearing an unchanged grep count.
    """
    home = _rvsec_home()
    specs = sorted((home / SUCCESSOR).glob("*.mop"))
    assert len(specs) == EXPECTED_SPECS, (
        f"expected {EXPECTED_SPECS} specifications, found {len(specs)} -- the two pure "
        "propagators travel with the set (D-11)"
    )

    divergences = []
    for path in specs:
        seed = home / SEED / path.name
        assert seed.is_file(), f"{path.name} has no counterpart in the frozen seed"
        want = [line for line in seed.read_text(encoding="utf-8").splitlines() if PREDICATE.search(line)]
        got = [line for line in path.read_text(encoding="utf-8").splitlines() if PREDICATE.search(line)]
        if want != got:
            divergences.append(f"{path.name}: seed has {len(want)} site(s), successor {len(got)}")

    assert not divergences, "predicate sites rewritten or lost:\n" + "\n".join(divergences)

    # The construct census, so that a gate cannot pass by comparing two files that
    # both stopped carrying predicates: the totals are asserted per construct
    # because the sum alone would let a `validate(` become a `setProperty(`.
    census = collections.Counter(
        _classify(line)
        for path in specs
        for line in path.read_text(encoding="utf-8").splitlines()
        if PREDICATE.search(line)
    )
    assert dict(census) == EXPECTED_CONSTRUCTS, dict(census)
    assert sum(census.values()) == EXPECTED_PREDICATE_LINES

    # And there is no record of a removal, because there is no removal: neither the
    # withdrawn `predicate_removal.csv` nor gh101's `predicate_omissions.csv`, which
    # justifies a `Property` written and never read.
    assert not (DATA / "predicate_removal.csv").exists()
    assert not (DATA / "predicate_omissions.csv").exists()

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
# performs, this is the census of the `jca` lock -- and, until gh105's first
# migrated file landed, of what the successor had to carry unchanged.
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
        pytest.skip(
            "RVSEC_HOME not set or the successor set is absent from the Java reactor"
        )
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


def test_the_frozen_seed_still_carries_every_predicate_site_it_was_frozen_with():
    """INV-INS-128, rescoped by INV-INS-141 to the `jca` lock it still governs.

    The gate was written the other way round. An earlier revision of gh104 deleted
    the successor set's predicate machinery outright -- the largest behavioural
    change the set could take, detection gone at 11 of the 21 predicate-reading
    events, with no before/after evidence behind it -- so the requirement became
    *the successor carries every site the seed has, in the same order,
    byte-for-byte* (design D-11), and a deletion could no longer slip in as a side
    effect of an allow-list edit.

    gh105 supersedes that for `jca_android` alone, and only from the first migrated
    file (INV-INS-141). The successor's predicate machinery is now the subject of a
    change rather than a thing to preserve: `SecureRandomSpec`'s twin fusions
    removed two guards and moved a third read into an event body, which is exactly
    the class of edit this assertion was built to refuse. What replaces it is not
    trust -- it is three instruments that measure the departure instead of denying
    it: `divergence_record.csv` names every hunk with a reason
    (`test_jca_android_hunks_all_recorded`, which is the check that would catch an
    unattributed deletion today), `data/jca_android/predicate_graph.csv` inventories
    every surviving site, and G-PRED2 closes the graph.

    What is left here is the half INV-INS-141 keeps verbatim: the frozen `jca` set,
    whose 134 sites are the census every published measurement was taken against.
    If this number moves, the freeze was broken.
    """
    home = _rvsec_home()
    specs = sorted((home / SEED).glob("*.mop"))
    assert (
        len(specs) == EXPECTED_SPECS
    ), f"expected {EXPECTED_SPECS} specifications in the frozen seed, found {len(specs)}"

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

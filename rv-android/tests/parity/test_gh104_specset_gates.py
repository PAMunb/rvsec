"""Gates over the successor specification set `jca_android` (gh104).

The set is seeded from the frozen `jca` and differs from it only by hunks a record
names, so what makes it checkable is enumeration rather than equality. Three gates
hold that shape:

    INV-INS-118   every hunk between the seed and the successor is named in
                  `data/jca_android/divergence_record.csv`, and no entry names a
                  hunk that no longer exists
    INV-INS-128   no `.mop` of the successor references `ExecutionContext` -- the
                  gate is a grep, so it cannot drift -- and the cost of that
                  removal is enumerated in `predicate_removal.csv`

Group 6 writes the structural gates over the generated monitor in
`test_gh104_structural_gates.py`; they read the same records and are kept in a
separate file so the two groups do not edit one.

All of these run against the sibling Java reactor, so they skip when it is absent.
"""

from __future__ import annotations

import collections
import csv
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data" / "jca_android"
SCRIPTS = REPO / "scripts"

SUCCESSOR = "rvsec/rvsec-mop/src/main/resources/jca_android"

# What predicate_removal.csv must account for, measured on the seed: the 21
# predicate-reading events, the 9 remove(...) sites and the 25 accepting-state
# calls. The 46 setProperty deletions, the 21 import deletions and the comment at
# MessageDigestSpec.mop:25 are divergence-record entries, one per file, not rows
# of this record -- they cost no detection, so there is nothing per-site to say.
EXPECTED_CLASS_TOTALS = {
    "guard": 10,
    "total-loss": 7,
    "partial-loss": 1,
    "provenance": 3,
    "remove": 9,
    "accepting-state": 25,
}
EXPECTED_ROWS = 55


def _rvsec_home() -> Path:
    home = os.environ.get("RVSEC_HOME")
    if not home or not (Path(home) / SUCCESSOR).is_dir():
        pytest.skip("RVSEC_HOME not set or the successor set is absent from the Java reactor")
    return Path(home)


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


def test_jca_android_has_no_execution_context():
    """INV-INS-128: G-PRED, and it is a grep so that it cannot drift.

    Zero occurrences of the identifier, imports and comments included -- not "no
    validate call". A file that still imports `ExecutionContext` is a file where
    re-adding one predicate is a one-line change, and the whole point of removing
    the machinery rather than repairing it is that there is nothing left to re-add.
    """
    home = _rvsec_home()
    specs = sorted((home / SUCCESSOR).glob("*.mop"))
    assert len(specs) == 21, f"expected 21 specifications, found {len(specs)}"

    offenders = []
    for path in specs:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "ExecutionContext" in line or re.search(r"\bProperty\.", line):
                offenders.append(f"{path.name}:{number}: {line.strip()}")

    assert not offenders, "predicate machinery left in jca_android:\n" + "\n".join(offenders)

    # The negative control: the same grep over the frozen seed still finds the 134
    # occurrences the removal was measured against, so a gate that passes because
    # it stopped looking would fail here.
    frozen = sorted((home / "rvsec/rvsec-mop/src/main/resources/jca").glob("*.mop"))
    total = sum(
        path.read_text(encoding="utf-8").count("ExecutionContext") for path in frozen
    )
    assert total == 134, f"the frozen jca no longer carries its 134 occurrences ({total})"


def test_predicate_removal_record_complete():
    """INV-INS-128: the cost of the removal is enumerated, not absorbed.

    Fifty-five rows: 21 + 9 + 25. The class totals are asserted individually
    because the sum alone would let one loss be reclassified as a guard -- and the
    difference between those two words is the difference between a detection this
    change gave up and one it recovered.
    """
    with (DATA / "predicate_removal.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == EXPECTED_ROWS, f"expected {EXPECTED_ROWS} rows, found {len(rows)}"
    assert sum(EXPECTED_CLASS_TOTALS.values()) == EXPECTED_ROWS

    totals = collections.Counter(row["class"] for row in rows)
    assert dict(totals) == EXPECTED_CLASS_TOTALS

    # Every row says which site it removed and why; a row that loses an accusation
    # says which sentence stops being raised.
    for row in rows:
        assert row["file"] and row["line"] and row["spec"] and row["event"], row
        assert row["reason"].strip(), f"no reason for {row['file']}:{row['line']}"
        if row["class"] in {"total-loss", "partial-loss", "provenance"}:
            assert row["lost_accusation"].strip(), (
                f"{row['class']} row with no accusation recorded: "
                f"{row['file']}:{row['line']} {row['event']}"
            )

    # And there is no predicate_omissions.csv: that record justifies a Property
    # written and never read, and this set writes none.
    assert not (DATA / "predicate_omissions.csv").exists()

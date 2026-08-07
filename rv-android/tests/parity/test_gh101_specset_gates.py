"""Gates over the two JCA specification sets (gh101).

The `jca` set produced published measurements, which makes it an experimental
instrument rather than merely code: altering it after the fact invalidates the
reproduction of every result computed with it. It is therefore frozen at this
change's base commit, and the layer-2 repairs -- bindings, automaton membership,
predicate-graph edges -- land in `jca_android` alone, even though the same defect
is visibly present in both.

That decision costs the property the sets used to have. A difference in outcome
between them could once be attributed to the platform allow-list alone; it can now
come from the allow-list or from a repair present in one set only, and no
measurement decomposes it after the fact. The gates below are what keeps the
difference at least *attributable*: the frozen set cannot move, and every hunk by
which the sets differ is named in a versioned record with the reason it exists.

    INV-INS-109 (a)  the frozen paths are byte-identical to the base commit,
                     and the frozen set's predicate inventory is unchanged
    INV-INS-109 (b)  every hunk of the set diff is named by a record entry,
                     and no entry names a hunk that no longer exists
    INV-INS-113      every one of the 23 derived specifications carries a
                     conformance verdict against the generated API 30 rules

All four run against the sibling Java reactor, so they skip when it is absent.
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data" / "gh101"
SCRIPTS = REPO / "scripts"

# The commit the freeze is measured against: the one that opened this change,
# before any of its edits. Hardcoded on purpose -- a freeze whose baseline moves
# is not a freeze.
BASE_COMMIT = "7e7acb69"

# Everything the freeze covers. The whole `jca` directory, and the utility its
# CipherSpec delegates its transformation verdict to.
FROZEN_PATHS = (
    "rvsec/rvsec-mop/src/main/resources/jca",
    "rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/CipherTransformationUtil.java",
)


def _rvsec_home() -> Path:
    home = os.environ.get("RVSEC_HOME")
    if not home or not (Path(home) / "rvsec/rvsec-mop/src/main/resources/jca").is_dir():
        pytest.skip("RVSEC_HOME not set or the sibling Java reactor is absent")
    return Path(home)


def _run(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def test_frozen_paths_byte_identical_to_base_commit():
    """INV-INS-109 (a): no edit reaches `jca/` or its CipherTransformationUtil.

    The check is deliberately blunt. It fails on any byte changed under a frozen
    path whatever its merit, because the failure mode it guards is precisely the
    well-intentioned one: reading the same defective line twice and repairing
    both copies.
    """
    home = _rvsec_home()
    result = _run("git", "-C", str(home), "diff", BASE_COMMIT, "--", *FROZEN_PATHS)
    if result.returncode != 0:
        pytest.skip(f"git diff unavailable in {home}: {result.stderr.strip()}")
    assert result.stdout == "", (
        "the frozen Java SE specification set changed since "
        f"{BASE_COMMIT}; move the edit to jca_android:\n{result.stdout}"
    )


def test_frozen_set_predicate_inventory_matches_baseline():
    """INV-INS-109 (a): the frozen set's predicate graph is where it was.

    A byte-level freeze already implies this, but the inventory is what every
    downstream count is derived from, so it is compared in its own right: a
    regeneration that disagrees with the committed baseline means either the set
    moved or the inventory script changed what it reports.
    """
    home = _rvsec_home()
    baseline = DATA / "predicate_inventory_jca.csv"
    result = _run(
        sys.executable,
        str(SCRIPTS / "gh101_predicate_inventory.py"),
        str(home / "rvsec/rvsec-mop/src/main/resources/jca"),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == baseline.read_text(encoding="utf-8"), (
        "the regenerated `jca` predicate inventory differs from the committed "
        f"baseline at {baseline.relative_to(REPO)}"
    )


def test_every_divergence_between_the_sets_is_recorded():
    """INV-INS-109 (b): the set diff and the divergence record name the same hunks."""
    _rvsec_home()
    result = _run(sys.executable, str(SCRIPTS / "gh101_divergence_record.py"), "--check")
    assert result.returncode == 0, result.stderr


def test_conformance_record_covers_all_twenty_three():
    """INV-INS-113: a verdict per derived specification, and no blanks.

    "Carried verbatim" is not a verdict. A file with no verdict is unverified,
    which is exactly the state the derivation left thirteen of them in.
    """
    with (DATA / "conformance_record.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 23, f"expected 23 verdicts, found {len(rows)}"
    blank = [row["mop_file"] for row in rows if not row["verdict"].strip()]
    assert not blank, f"no conformance verdict for: {', '.join(blank)}"

    # A `no-anchor` verdict is admissible only when it says why.
    unexplained = [
        row["mop_file"]
        for row in rows
        if row["verdict"] == "no-anchor" and not row["reason"].strip()
    ]
    assert not unexplained, f"no-anchor without a reason: {', '.join(unexplained)}"

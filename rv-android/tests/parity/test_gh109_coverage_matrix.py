"""The coverage matrix over the pinned expert oracle (gh109, INV-INS-150).

    INV-INS-150   every rule of the pinned expert oracle ends in exactly one of three
                  terminal states -- `covered`, `na-platform`, `na-value` -- and an
                  oracle defect is an attribute of the rule's row, never a fourth state

The artifact is `data/jca_android/coverage_matrix.csv`, derived by
`scripts/gh109_coverage_matrix.py`. What is asserted here is that the committed artifact
still says what the tree says, that the states it uses are the three the model has, and
that the defect column is a join a reader can reproduce rather than a judgement typed by
hand.

**Totals are derived, never hardcoded.** gh109 lands its coverage in tiers, so a pinned
`49 covered` here would be a test that fails for the whole change and passes for one
commit at the end -- which is a test that gets deleted rather than a test that guards
anything. The assertions below hold at every point of the change: they check the shape of
the answer, and the count of rules still pending is reported rather than pinned. The
completeness assertion -- 49 of 49 with a state -- is the `--require-complete` mode of the
script, and it is task 7.3 that runs it, once, at final verification.

These run against the sibling Java reactor and the pinned oracle, so they skip when either
is absent.
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data" / "jca_android"
SCRIPTS = REPO / "scripts"
MATRIX = DATA / "coverage_matrix.csv"
RECORD = DATA / "divergence_record.csv"

SUCCESSOR = "rvsec/rvsec-mop/src/main/resources/jca_android"

TERMINAL_STATES = {"covered", "na-platform", "na-value"}


def _oracle() -> Path:
    """The pinned expert copy, or a skip.

    Located the same way the derivation locates it -- two levels above the repo -- so a
    checkout without the replication package skips instead of failing on a path nobody
    promised.
    """
    rules = REPO.parent.parent / "RVSec-replication-package/tools/rules"
    if not rules.is_dir():
        pytest.skip(f"the pinned expert oracle is absent: {rules}")
    return rules


def _reactor() -> Path:
    home = os.environ.get("RVSEC_HOME")
    if not home or not (Path(home) / SUCCESSOR).is_dir():
        pytest.skip(
            "RVSEC_HOME not set or the successor set is absent from the Java reactor"
        )
    return Path(home)


def _rows() -> list[dict[str, str]]:
    """The committed matrix, header comment dropped.

    The `#` lines carry the definition of `covered`, which is the one thing a reader of
    this CSV is most likely to get wrong, so they live in the artifact and not only in the
    script that writes it.
    """
    with MATRIX.open(encoding="utf-8", newline="") as handle:
        lines = [line for line in handle if not line.startswith("#")]
    return [
        {key: (value or "").strip() for key, value in row.items()}
        for row in csv.DictReader(lines)
    ]


def test_the_committed_matrix_still_says_what_the_tree_says():
    """The derivation reproduces the artifact, in both directions.

    A committed row for a rule the oracle no longer has is a claim nobody re-verified; a
    rule with no committed row is the question left unanswered, which is the exact failure
    this whole change exists to close.
    """
    _oracle()
    _reactor()
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "gh109_coverage_matrix.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_every_rule_of_the_oracle_has_exactly_one_row():
    """One row per rule, and the oracle decides the population.

    Derived from the rule directory rather than pinned, because gh109 does not change how
    many rules the oracle has and a pinned 49 would only record that fact twice -- once
    where it can drift.
    """
    rules = _oracle()
    _reactor()
    expected = sorted(path.stem for path in rules.glob("*.crysl"))
    rows = _rows()
    assert [row["rule"] for row in rows] == expected


def test_no_row_carries_a_state_outside_the_three():
    """Three terminal states and no fourth (design D-19).

    A fourth state -- `defective`, say -- would put `Cipher` in two at once: it is paired,
    and a defect is recorded against `Cipher.crysl:140-141`. An empty state is not a fourth
    state either; it is a rule this change has not yet adjudicated, and it is counted below
    rather than admitted here.
    """
    _oracle()
    _reactor()
    for row in _rows():
        if row["terminal_state"]:
            assert row["terminal_state"] in TERMINAL_STATES, row


def test_a_rule_with_a_state_names_the_evidence_for_it():
    """No state without a warrant.

    `covered` names the `.mop` that covers the rule; an `na-` state names the argument
    that adjudicates it. A state with an empty evidence cell records a decision nobody can
    check, which is the shape of record this family of gates exists to refuse.
    """
    _oracle()
    _reactor()
    for row in _rows():
        if row["terminal_state"]:
            assert row["evidence"], row


def test_the_defect_column_is_a_join_a_reader_can_reproduce():
    """`oracle_defect_row` is derived from the divergence record, not typed (D-21).

    Every rule carrying a defect summary must have an `oracle-wart` row of
    `divergence_record.csv` whose `file` column names its rule path, and every such row
    must reach the rule it names. That two-way check is what makes the column a join
    instead of a judgement: a defect recorded against no rule would be invisible in the
    matrix, and a summary in the matrix with no row behind it would be an unsourced claim.
    """
    _oracle()
    _reactor()
    with RECORD.open(encoding="utf-8", newline="") as handle:
        recorded = {
            Path(row["file"].strip()).stem
            for row in csv.DictReader(handle)
            if (row.get("kind") or "").strip() == "oracle-wart"
            and (row.get("file") or "").strip().startswith("tools/rules/")
        }
    carried = {row["rule"] for row in _rows() if row["oracle_defect_row"]}
    assert carried == recorded


def test_the_pending_rules_are_the_ones_no_tier_has_landed_yet():
    """Progress is reported, not pinned.

    A rule with no terminal state is a rule gh109 has not reached. Asserting a count here
    would make this test a checklist that has to be edited by every task of the change,
    and a checklist edited by every task stops being read. What is asserted is the
    invariant that survives every tier: a pending rule has no `.mop` and no adjudication,
    so its evidence cell says so instead of claiming something.
    """
    _oracle()
    _reactor()
    for row in _rows():
        if not row["terminal_state"]:
            assert "pending" in row["evidence"], row

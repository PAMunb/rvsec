#!/usr/bin/env python3
"""INV-INS-111: every constant a specification writes has a reader or a record.

Specifications talk to one another through `ExecutionContext`, a static map keyed
by a `Property` constant. Nothing links a write to a read: a specification that
writes a constant no other specification ever reads compiles, runs, and reports
nothing. That is the shape of a translation defect in this set -- the `ENSURES`
side of a CrySL clause was transcribed and the `REQUIRES` side was not, so the
fact is established and never consulted.

The pairing is therefore a check rather than a convention (D-S5). The list of
expected pairs is not written by hand -- it would drift from the specifications
the first time one changes. This script recomputes it from the `.mop` files
themselves, using the same inventory the committed record is built from, and
fails on any constant written and neither read nor named in the deliberate-
omission list. An omission is admissible; an unrecorded silent write is not.

Three failure classes, all of them defects rather than warnings:

    written, never read, not recorded   the fact is established and unconsulted
    read, never written                 the requirement is unsatisfiable, so it
                                        reports on every conforming call (D-S14)
    recorded, but no longer unread      the record has drifted from the set

The second class is not in INV-INS-111's text and is checked here because D-S14
turns on it: a read in an event body whose producer is absent from the set fails
on every execution, which is worse than the open gap it was meant to close. It
holds today with nothing recorded, and the check exists so that it keeps holding.

The committed inventory is verified against the specifications before the pairing
is computed, so a stale CSV fails here instead of quietly deciding the answer.

Usage:
    gh101_predicate_pairing_check.py [--specs <dir>] [--inventory <csv>]
                                     [--omissions <csv>]

gh104 rebound the name `jca_android` to a successor set and archived the
derived set this gate guards as `jca_android_bug_predicate/`. The default
path therefore names the archive: the gate keeps gh101's freeze and
divergence records resolving over the artefact they were computed on
(INV-INS-118), and says nothing about the successor set.
"""

from __future__ import annotations

import argparse
import collections
import csv
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gh101_predicate_inventory import FIELDS as INVENTORY_FIELDS  # noqa: E402
from gh101_predicate_inventory import inventory_set  # noqa: E402

# What an entry in the omission list is. `constant-write-no-read` names a Property
# constant that exists and is written; `predicate-no-constant` names a CrySL
# predicate for which no constant was added at all, which is what task 5.1d
# records. Only the first kind participates in the pairing -- the second is here
# because both are omissions from the same graph and splitting them across two
# files would let one drift from the other.
KINDS = {"constant-write-no-read", "predicate-no-constant"}


def render(rows: list[dict[str, object]]) -> str:
    """The inventory rows as the CSV text the committed record is written in."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=INVENTORY_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def pairing(rows: list[dict[str, object]]) -> tuple[dict, dict]:
    """Which specifications write and which read each constant."""
    writes: dict[str, set[str]] = collections.defaultdict(set)
    reads: dict[str, set[str]] = collections.defaultdict(set)
    for row in rows:
        # REMOVE is neither: a removal retracts a fact, so it can neither
        # establish one for a reader nor consult one a writer established.
        target = {"WRITE": writes, "READ": reads}.get(str(row["kind"]))
        if target is not None:
            target[str(row["property"])].add(str(row["spec"]))
    return writes, reads


def check(specs_dir: Path, inventory: Path, omissions: Path) -> int:
    live = inventory_set(specs_dir)
    failures: list[str] = []

    committed = inventory.read_text(encoding="utf-8")
    if render(live) != committed:
        failures.append(
            f"stale inventory        {inventory} does not match {specs_dir} "
            f"({len(live)} live site(s)); regenerate with gh101_predicate_inventory.py"
        )

    with omissions.open(encoding="utf-8") as handle:
        recorded = list(csv.DictReader(handle))

    listed: set[str] = set()
    for entry in recorded:
        kind = (entry.get("kind") or "").strip()
        constant = (entry.get("constant") or "").strip()
        name = constant or (entry.get("predicate") or "").strip() or "<unnamed>"
        if kind not in KINDS:
            failures.append(f"unknown kind           {name}  {kind!r}")
        if not (entry.get("reason") or "").strip():
            failures.append(f"entry with no reason   {name}")
        if kind == "constant-write-no-read":
            if not constant:
                failures.append(f"entry with no constant {name}")
            listed.add(constant)
        elif constant:
            failures.append(
                f"constant on a predicate-no-constant entry  {name}  {constant}"
            )

    writes, reads = pairing(live)

    for constant in sorted(set(writes) - set(reads)):
        if constant not in listed:
            wrote = ", ".join(sorted(writes[constant]))
            failures.append(f"written, never read    {constant}  written by {wrote}")

    for constant in sorted(set(reads) - set(writes)):
        read_by = ", ".join(sorted(reads[constant]))
        failures.append(f"read, never written    {constant}  read by {read_by}")

    for constant in sorted(listed):
        if constant not in writes:
            failures.append(
                f"stale entry            {constant}  no specification writes it"
            )
        elif constant in reads:
            read_by = ", ".join(sorted(reads[constant]))
            failures.append(f"stale entry            {constant}  now read by {read_by}")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        print(f"\n{len(failures)} problem(s)", file=sys.stderr)
        return 1

    paired = len(set(writes) & set(reads))
    print(
        f"{len(writes)} constant(s) written: {paired} read by another specification, "
        f"{len(listed)} recorded as deliberate omissions",
        file=sys.stderr,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mop_base = (
        Path(os.environ.get("RVSEC_HOME", "")) / "rvsec/rvsec-mop/src/main/resources"
    )
    here = Path(__file__).resolve().parent.parent
    parser.add_argument(
        "--specs", type=Path, default=mop_base / "jca_android_bug_predicate"
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=here / "data/gh101/predicate_inventory_jca_android.csv",
    )
    parser.add_argument(
        "--omissions", type=Path, default=here / "data/gh101/predicate_omissions.csv"
    )
    args = parser.parse_args()

    if not args.specs.is_dir():
        print(f"specs directory not found: {args.specs}", file=sys.stderr)
        return 1
    for label, path in (("inventory", args.inventory), ("omissions", args.omissions)):
        if not path.is_file():
            print(f"{label} not found: {path}", file=sys.stderr)
            return 1

    return check(args.specs, args.inventory, args.omissions)


if __name__ == "__main__":
    raise SystemExit(main())

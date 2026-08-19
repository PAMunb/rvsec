#!/usr/bin/env python3
"""The enumeration that replaced the parity check between the two JCA sets.

Until this change the two sets were required to differ by allow-list content and
nothing else, and that single criterion was what made a difference in outcome
between them attributable to the platform. Freezing `jca` makes the criterion
false by design: the repairs land in `jca_android` alone, so the sets now diverge
outside their allow-lists on purpose.

Dropping the criterion would leave the sets free to drift with nothing recording
why, so it is replaced rather than removed (D-S7). Every hunk by which the sets
differ carries a row naming it, what kind of difference it is, why it exists and
which task introduced it. A hunk with no row fails the check; a row naming no
hunk is stale and fails too. The sets are no longer identical outside allow-lists,
but the ways in which they differ stay finite, named and attributable.

Hunks are keyed by a digest of their changed lines rather than by position, so an
edit elsewhere in the file does not invalidate every row below it. Changing what
a hunk contains does change its key -- which is correct: the reason recorded for
the old content has not been shown to hold for the new.

Usage:
    gh101_divergence_record.py --check    [--record <csv>]   # exit 1 on any mismatch
    gh101_divergence_record.py --refresh  [--record <csv>]   # print rows for the live diff

gh104 rebound the name `jca_android` to a successor set and archived the
derived set this gate guards as `jca_android_bug_predicate/`. The default
path therefore names the archive: the gate keeps gh101's freeze and
divergence records resolving over the artefact they were computed on
(INV-INS-118), and says nothing about the successor set.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import os
import sys
from pathlib import Path

FIELDS = ["file", "hunk", "kind", "summary", "reason", "task"]

# What a difference between the sets is. `allow-list` is the derivation acting as
# it may; everything else is a repair confined to the derived set, and it is the
# everything-else that INV-INS-109 (b) exists to keep enumerated.
KINDS = {"allow-list", "layer-2-repair", "predicate-graph", "cipher-import"}


def hunks(frozen: Path, derived: Path) -> list[dict[str, str]]:
    """Every hunk of the set diff, keyed by the content that makes it one."""
    rows: list[dict[str, str]] = []
    for path in sorted(derived.glob("*.mop")):
        counterpart = frozen / path.name
        if not counterpart.exists():
            rows.append(
                {
                    "file": path.name,
                    "hunk": "new-file",
                    "summary": "present only in the derived set",
                }
            )
            continue

        before = counterpart.read_text(encoding="utf-8").splitlines()
        after = path.read_text(encoding="utf-8").splitlines()
        changed: list[str] = []
        for line in difflib.unified_diff(before, after, n=0, lineterm=""):
            if line.startswith(("---", "+++")):
                continue
            if line.startswith("@@"):
                if changed:
                    rows.append(digest_row(path.name, changed))
                changed = []
                continue
            if line.startswith(("-", "+")):
                changed.append(line.rstrip())
        if changed:
            rows.append(digest_row(path.name, changed))

    return rows


def digest_row(name: str, changed: list[str]) -> dict[str, str]:
    payload = "\n".join(changed).encode("utf-8")
    first = next((line for line in changed if line.startswith("+")), changed[0])
    return {
        "file": name,
        "hunk": hashlib.sha1(payload).hexdigest()[:12],
        "summary": first[1:].strip()[:110],
    }


def load(record: Path) -> list[dict[str, str]]:
    if not record.exists():
        return []
    with record.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check(record: Path, frozen: Path, derived: Path) -> int:
    live = {(row["file"], row["hunk"]): row for row in hunks(frozen, derived)}
    recorded = {(row["file"], row["hunk"]): row for row in load(record)}
    failures: list[str] = []

    for key, row in sorted(live.items()):
        entry = recorded.get(key)
        if entry is None:
            failures.append(f"unrecorded divergence  {key[0]} {key[1]}  {row['summary']}")
        elif not entry.get("reason", "").strip():
            failures.append(f"entry with no reason   {key[0]} {key[1]}")
        elif entry.get("kind") not in KINDS:
            failures.append(f"unknown kind {entry.get('kind')!r}  {key[0]} {key[1]}")

    for key, entry in sorted(recorded.items()):
        if key not in live:
            failures.append(
                f"stale entry            {key[0]} {key[1]}  {entry.get('summary', '')}"
            )

    if failures:
        print("\n".join(failures), file=sys.stderr)
        print(f"\n{len(failures)} problem(s); {len(live)} hunk(s) in the set diff", file=sys.stderr)
        return 1

    kinds = sorted({row["kind"] for row in recorded.values()})
    print(f"{len(live)} hunk(s), all recorded; kinds: {', '.join(kinds) or 'none'}", file=sys.stderr)
    return 0


def refresh(record: Path, frozen: Path, derived: Path) -> int:
    """Print the live hunks with any reason already on record, for editing by hand."""
    recorded = {(row["file"], row["hunk"]): row for row in load(record)}
    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in hunks(frozen, derived):
        kept = recorded.get((row["file"], row["hunk"]), {})
        writer.writerow(
            {
                "file": row["file"],
                "hunk": row["hunk"],
                "kind": kept.get("kind", ""),
                "summary": row["summary"],
                "reason": kept.get("reason", ""),
                "task": kept.get("task", ""),
            }
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mop_base = Path(os.environ.get("RVSEC_HOME", "")) / "rvsec/rvsec-mop/src/main/resources"
    here = Path(__file__).resolve().parent.parent
    parser.add_argument("--record", type=Path, default=here / "data/gh101/divergence_record.csv")
    parser.add_argument("--frozen", type=Path, default=mop_base / "jca")
    parser.add_argument(
        "--derived", type=Path, default=mop_base / "jca_android_bug_predicate"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    for label, path in (("frozen", args.frozen), ("derived", args.derived)):
        if not path.is_dir():
            print(f"{label} set not found: {path}", file=sys.stderr)
            return 1

    if args.refresh:
        return refresh(args.record, args.frozen, args.derived)
    return check(args.record, args.frozen, args.derived)


if __name__ == "__main__":
    raise SystemExit(main())

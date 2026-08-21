#!/usr/bin/env python3
"""Every hunk between the frozen `jca` seed and the successor set `jca_android`.

`jca_android` is seeded from the frozen `jca` and differs from it only by hunks
this record names (INV-INS-118). The seed is an experimental instrument -- it
produced the published measurements -- so the successor cannot be checked against
it by equality; what it can be checked against is enumeration. Every changed line
belongs to a hunk, every hunk carries a row saying what kind of change it is, why
it exists and which task made it, and a hunk with no row fails the gate. A row
naming a hunk that no longer exists fails too, because a reason recorded for
content that has since changed has not been shown to hold for the new content.

Hunks are keyed by a digest of their changed lines rather than by position, so an
edit elsewhere in the file does not invalidate every row below it.

Two shapes of row are not hunks and are exempt from the stale check, recognised by
an empty `hunk` column: the archival of the reproved derived set, and the recorded
departures from literal transcription that live in this file by INV-INS-125 -- the
two `api30-omits` exceptions (`EC` in `KeyPairGenerator`, the four `SHA*withECDSA`
in `Signature`) and the one `behavioural` case (`OAEPWithSHA1AndMGF1Padding`,
which no Conscrypt registration explains and which therefore gets no alias row).
They are statements about the set, not about a diff, and G-CONF reads them here.

The successor carries all 23 specifications of the seed, predicates included, so
neither set holds a file the other lacks; a `removed-file` or `new-file` hunk would
therefore be a real divergence and needs a row like any other.

Usage:
    gh104_divergence_record.py --check    [--record <csv>]   # exit 1 on any mismatch
    gh104_divergence_record.py --refresh  [--record <csv>]   # print rows for the live diff
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

# What a difference between the seed and the successor is allowed to be.
KINDS = {
    "set-archived",      # the reproved derived set moved out of the way (task 2.1)
    "allow-list",        # a list was transcribed from the api30 rule (tasks 2.4-2.7)
    "cipher-import",     # CipherSpec now names Api30CipherTransformationUtil (task 2.8)
    "api30-omits",       # a value the rule omits and the platform provably carries
    "behavioural",       # a spelling proved to work on the platform and cited to no rule
    "message",           # a report site rewritten as a v=1 envelope (tasks 7.3-7.5)
    "automaton",         # a structural repair proved against the api30 rule, the JDK
                         # signature or the generated monitor (tasks 8.1-8.6, 8.14-8.16)
    # gh105 (predicate wiring). The successor set stops carrying the seed's
    # predicate machinery unchanged when its first file is migrated (INV-INS-141),
    # so the four things that migration does to a `.mop` each need a name a reason
    # can be filed under. Without them every gh105 row fails `check()` as an
    # unknown kind, which reads as a defect in the record rather than a gap in it.
    "predicate-store",   # a site moves from ExecutionContext to PredicateStore
    "placement",         # a read leaves `condition(...)` for the body, or a write
                         # moves to the rule's acceptance point (INV-INS-133/134)
    "junction",          # a junction specification for a co-observable chain
    "predicate-removal",  # a `remove`/`negate` site, or a `@fail` undo retired
}

# Kinds that describe the set rather than a diff, so they carry no hunk key.
NARRATIVE_KINDS = {"set-archived", "api30-omits", "behavioural"}


def hunks(base: Path, target: Path) -> list[dict[str, str]]:
    """Every hunk of the set diff, keyed by the content that makes it one."""
    rows: list[dict[str, str]] = []
    for path in sorted(target.glob("*.mop")):
        counterpart = base / path.name
        if not counterpart.exists():
            rows.append(
                {
                    "file": path.name,
                    "hunk": "new-file",
                    "summary": "present only in the successor set",
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

    # A file the seed has and the successor does not; the successor should have none.
    for path in sorted(base.glob("*.mop")):
        if not (target / path.name).exists():
            rows.append(
                {
                    "file": path.name,
                    "hunk": "removed-file",
                    "summary": "present in the seed and absent from the successor set",
                }
            )

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


def check(record: Path, base: Path, target: Path) -> int:
    live = {(row["file"], row["hunk"]): row for row in hunks(base, target)}
    recorded: dict[tuple[str, str], dict[str, str]] = {}
    narrative: list[dict[str, str]] = []
    failures: list[str] = []

    for row in load(record):
        if not row.get("hunk", "").strip():
            narrative.append(row)
            continue
        recorded[(row["file"], row["hunk"])] = row

    for row in narrative:
        if row.get("kind") not in NARRATIVE_KINDS:
            failures.append(
                f"entry with no hunk key   {row.get('file')}  kind {row.get('kind')!r} "
                f"is not one of {sorted(NARRATIVE_KINDS)}"
            )
        elif not row.get("reason", "").strip():
            failures.append(f"entry with no reason     {row.get('file')} (narrative)")

    for key, row in sorted(live.items()):
        entry = recorded.get(key)
        if entry is None:
            failures.append(f"unrecorded divergence    {key[0]} {key[1]}  {row['summary']}")
        elif not entry.get("reason", "").strip():
            failures.append(f"entry with no reason     {key[0]} {key[1]}")
        elif entry.get("kind") not in KINDS:
            failures.append(f"unknown kind {entry.get('kind')!r}  {key[0]} {key[1]}")

    for key, entry in sorted(recorded.items()):
        if key not in live:
            failures.append(
                f"stale entry              {key[0]} {key[1]}  {entry.get('summary', '')}"
            )

    if failures:
        print("\n".join(failures), file=sys.stderr)
        print(f"\n{len(failures)} problem(s); {len(live)} hunk(s) in the set diff", file=sys.stderr)
        return 1

    kinds = sorted({row["kind"] for row in load(record)})
    print(
        f"{len(live)} hunk(s), all recorded; {len(narrative)} narrative entr(ies); "
        f"kinds: {', '.join(kinds) or 'none'}",
        file=sys.stderr,
    )
    return 0


def refresh(record: Path, base: Path, target: Path) -> int:
    """Print the live hunks with any reason already on record, for editing by hand."""
    recorded = {
        (row["file"], row["hunk"]): row for row in load(record) if row.get("hunk", "").strip()
    }
    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in load(record):
        if not row.get("hunk", "").strip():
            writer.writerow(row)
    for row in hunks(base, target):
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
    parser.add_argument("--record", type=Path, default=here / "data/jca_android/divergence_record.csv")
    parser.add_argument("--base", type=Path, default=mop_base / "jca")
    parser.add_argument("--target", type=Path, default=mop_base / "jca_android")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    for label, path in (("base", args.base), ("target", args.target)):
        if not path.is_dir():
            print(f"{label} set not found: {path}", file=sys.stderr)
            return 1

    if args.refresh:
        return refresh(args.record, args.base, args.target)
    return check(args.record, args.base, args.target)


if __name__ == "__main__":
    raise SystemExit(main())

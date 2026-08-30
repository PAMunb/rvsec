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
    "set-archived",  # the reproved derived set moved out of the way (task 2.1)
    "allow-list",  # a list was transcribed from the api30 rule (tasks 2.4-2.7)
    "cipher-import",  # which Cipher transformation utility CipherSpec names
    # (task 2.8 pointed it at Api30CipherTransformationUtil; task 11.3, under
    # D-15, points it at the frozen jca's CipherTransformationUtil)
    "api30-omits",  # a value the rule omits and the platform provably carries
    "behavioural",  # a spelling proved to work on the platform and cited to no rule
    "message",  # a report site rewritten as a v=1 envelope (tasks 7.3-7.5)
    "automaton",  # a structural repair proved against the api30 rule, the JDK
    # signature or the generated monitor (tasks 8.1-8.6, 8.14-8.16)
    # gh105 (predicate wiring). The successor set stops carrying the seed's
    # predicate machinery unchanged when its first file is migrated (INV-INS-141),
    # so the four things that migration does to a `.mop` each need a name a reason
    # can be filed under. Without them every gh105 row fails `check()` as an
    # unknown kind, which reads as a defect in the record rather than a gap in it.
    "predicate-store",  # a site moves from ExecutionContext to PredicateStore
    "placement",  # a read leaves `condition(...)` for the body, or a write
    # moves to the rule's acceptance point (INV-INS-133/134)
    "junction",  # a junction specification for a co-observable chain
    "predicate-removal",  # a `remove`/`negate` site retired, a `@fail` undo retired,
    # or a write deleted because it translates no clause of
    # the rule and has no reader to lose
    # D-15 (the value oracle moves to the pinned expert CrySL copy). INV-INS-125
    # enumerates five admissible departures from a literal transcription of the
    # expert rule; three of them are divergence-record kinds of their own, and the
    # other two are the alias table and the conformance record's deferred constants.
    "platform-value",  # a value the expert rule omits whose rejection would accuse a
    # practice the platform itself recommends, admitted only with a
    # primary-source citation; the set is closed (INV-INS-125)
    "oracle-wart",  # a measured quirk of the expert rule, transcribed faithfully
    # rather than corrected, with the quirk named
    "spelling-variant",  # a frozen-set list entry that duplicates an expert entry under
    # case folding or an alias row, kept because removing it could
    # move a verdict and keeping it cannot
    # gh106 (the MOP/CrySL conformance component). A CI gate may measure something
    # the component deliberately does not measure. That is not a failure of either
    # one, it is a boundary, and it needs a name for the same reason the gh105 kinds
    # needed theirs: without it the row fails `check()` as an unknown kind, which
    # reads as a defect in the record rather than as the recorded decision it is.
    "gate-scope",  # a verdict one of the surviving ad-hoc gates produces and the
    # component declines to produce, with the decision that declined it
    # gh109 (expert-oracle coverage parity). A ratified decision that changes what
    # the set accuses is not a departure from a literal transcription -- the closed
    # five of INV-INS-125 are all about a value list differing from its clause, and
    # these are not that. Two of them move the set TOWARDS the oracle (the PBE
    # families it stopped refusing), one is a comparison semantics rather than a
    # list (the keysize-suffixed service names), one is a mechanism the producers
    # share (canonical predicate values), and one is a non-addition (no accusation
    # surface the oracle does not name). What they have in common is the only thing
    # a record can act on: a campaign measured before them is not comparable with
    # one measured after, so the comparability caveat needs one anchor to point at.
    "value-decision",  # a ratified decision of the change that moves what is accused,
    # recorded so the campaign caveat has an enumerable anchor
    # gh109 again, and for the one thing gh104 and gh105 never did: those two
    # campaigns repaired the 23 specifications the seed already carried, so every
    # kind above names something that happens to an existing file. gh109 adds files.
    # A specification written for a rule the seed left unspecified is not a
    # `junction` (that word names the co-observable chain of `IvChainJunction`, the
    # only new file either predecessor produced), and calling it one to reuse a
    # word would file 27 rules' worth of coverage under a name that describes one
    # of them. It gets a word of its own, and the word carries the obligation: the
    # successor answers to all 49 rules of the pinned oracle, and each of these
    # files is one rule moving from unspecified to `covered` in the matrix.
    "coverage-spec",  # a specification the seed did not carry, written for a rule of
    # the pinned expert oracle that the seed left unspecified
}

# Kinds that describe the set rather than a diff, so they carry no hunk key.
NARRATIVE_KINDS = {
    "set-archived",
    "api30-omits",
    "behavioural",
    # D-15: a platform value and an oracle wart are both admitted by an argument
    # rather than by a diff, so both owe the record a narrative reason.
    "platform-value",
    "oracle-wart",
    # A spelling variant is admitted by an argument about the normalisation rule,
    # not by a diff either: the row says which expert entry it duplicates.
    "spelling-variant",
    # A scope boundary is a statement about what the conformance component measures,
    # so it attaches to no hunk of the seed-to-successor diff at all.
    "gate-scope",
    # A value decision is argued from the oracle and from the platform, never from a
    # diff: the hunks it produces are recorded separately, by the tasks that write
    # them, and this row is the decision itself.
    "value-decision",
}


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
    """
    Key one hunk by a digest of its changed lines, never by its position.

    Position would make every row below an edit stale at once. Content will not:
    a hunk keeps its key while its lines keep their text, and changing what the
    hunk contains does change the key, which is the intended behaviour -- the
    reason recorded for the old content has not been shown to hold for the new.

    The summary is the first added line when there is one, because a divergence
    is nearly always something the successor says and the seed does not.
    """
    payload = "\n".join(changed).encode("utf-8")
    first = next((line for line in changed if line.startswith("+")), changed[0])
    return {
        "file": name,
        "hunk": hashlib.sha1(payload).hexdigest()[:12],
        "summary": first[1:].strip()[:110],
    }


def load(record: Path) -> list[dict[str, str]]:
    """
    Read the record, treating an absent file as an empty one.

    `--refresh` is how the record is first written, so it has to run before the
    file exists; `--check` against no record then reports every live hunk as
    unrecorded, which is the correct answer and not a crash.
    """
    if not record.exists():
        return []
    with record.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check(record: Path, base: Path, target: Path) -> int:
    """
    Check the record against the live seed-to-successor diff, and return an exit code.

    Rows split in two by whether they carry a hunk key. The keyed ones are
    checked in both directions -- a hunk with no row fails, a row naming no hunk
    is stale and fails -- because a record that only had to cover the diff would
    accumulate reasons for divergences that no longer exist.

    A key may appear twice, because the hunk digest is over the changed lines and
    two places in one file can change identically; what fails is two rows under one
    key that DISAGREE, since the reader would silently see only the last of them.

    The unkeyed ones are the narrative entries of INV-INS-125: statements about
    the set rather than about a diff, so they are exempt from the stale check and
    pay for it with a stricter one. Their `kind` must be in `NARRATIVE_KINDS`,
    which is what stops an empty `hunk` column from becoming a way to record a
    real divergence without a hunk to attach it to. Both shapes fail on an empty
    `reason`: an unexplained entry records nothing.
    """
    live = {(row["file"], row["hunk"]): row for row in hunks(base, target)}
    recorded: dict[tuple[str, str], dict[str, str]] = {}
    narrative: list[dict[str, str]] = []
    failures: list[str] = []

    for row in load(record):
        if not row.get("hunk", "").strip():
            narrative.append(row)
            continue
        key = (row["file"], row["hunk"])
        # Two hunks of one file can share a key legitimately -- the digest is over the
        # changed lines, so the same guard written at two events digests the same -- and
        # the record then carries two rows under one key. Keeping the last silently is
        # what this guard removes: identical rows are the same statement written twice
        # and cost nothing, while rows that DISAGREE mean the record says two things
        # about one key and the reader would only ever see one of them. Measured when
        # this was added (gh109 task 6.3): eight duplicated keys, all eight identical.
        first = recorded.get(key)
        if first is not None and any(
            first.get(field, "") != row.get(field, "")
            for field in ("kind", "summary", "reason", "task")
        ):
            failures.append(
                f"contradicting duplicate  {key[0]} {key[1]}  two rows under one key "
                f"disagree; only the last would be read"
            )
        recorded[key] = row

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
            failures.append(
                f"unrecorded divergence    {key[0]} {key[1]}  {row['summary']}"
            )
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
        print(
            f"\n{len(failures)} problem(s); {len(live)} hunk(s) in the set diff",
            file=sys.stderr,
        )
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
        (row["file"], row["hunk"]): row
        for row in load(record)
        if row.get("hunk", "").strip()
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
    """
    Parse arguments and dispatch to `--check` or `--refresh`.

    The two modes are mutually exclusive and one is required, because the
    difference between them is asserting and proposing: `--check` returns 1 on
    any mismatch, `--refresh` writes the live hunks to stdout with whatever
    reasons are already on record, for a human to complete.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mop_base = (
        Path(os.environ.get("RVSEC_HOME", "")) / "rvsec/rvsec-mop/src/main/resources"
    )
    here = Path(__file__).resolve().parent.parent
    parser.add_argument(
        "--record", type=Path, default=here / "data/jca_android/divergence_record.csv"
    )
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

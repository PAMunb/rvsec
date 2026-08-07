#!/usr/bin/env python3
"""Inventory of the predicate graph carried by a JCA specification set.

Specifications in the `jca` and `jca_android` sets talk to one another through a
static `Map<Property, Set<Object>>` held by `br.unb.cic.mop.ExecutionContext`.
One specification writes that a key was generated or a value randomised; another
reads that fact to decide whether a later call is a misuse. Nothing links the
write to the read: both sides name an enum constant, so a specification that
writes a neighbouring specification's constant compiles, runs, and reports
nothing. Two specifications do exactly that today.

This script turns those edges into data. It walks a set's `.mop` files and emits
one CSV row per `ExecutionContext` site keyed by a `Property` constant, so the
graph can be diffed, counted and guarded instead of read. The three operations
that touch the graph are the only ones inventoried:

    setProperty(Property.X, v)   -> WRITE
    validate(Property.X, v)      -> READ
    remove(Property.X[, v])      -> REMOVE

`setObjectAsInAcceptingState` and its `unset` counterpart are deliberately out of
scope: they carry no `Property` and are never read back from any `.mop`, which is
recorded separately as the half-built substitution it is.

Usage:
    gh101_predicate_inventory.py <specs-dir> [-o <out.csv>]
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

# The three graph operations, mapped to the kind recorded in the inventory.
# Anchored on `Property.` so a call keyed by anything else is not mistaken for
# an edge -- `remove()` also has a deprecated bulk overload with no constant.
SITE_PATTERNS: dict[str, re.Pattern[str]] = {
    "WRITE": re.compile(r"setProperty\(\s*Property\.(\w+)"),
    "READ": re.compile(r"validate\(\s*Property\.(\w+)"),
    "REMOVE": re.compile(r"remove\(\s*Property\.(\w+)"),
}

# A .mop file is flat: a spec declaration at column 0, then event blocks, an
# automaton, and handler blocks. Tracking which of those we are inside is enough
# to attribute every site, and no site in either set sits deeper than that.
SPEC_DECL = re.compile(r"^(\w+)\s*\(")
EVENT_DECL = re.compile(r"^\s*event\s+(\w+)\b")
HANDLER_DECL = re.compile(r"^\s*@(\w+)\s*\{")
AUTOMATON_DECL = re.compile(r"^\s*(fsm|ere)\s*:")

FIELDS = ["property", "kind", "file", "line", "spec", "event", "snippet"]


def inventory_file(path: Path) -> list[dict[str, object]]:
    """Every Property-keyed ExecutionContext site in one .mop file."""
    rows: list[dict[str, object]] = []
    # The declared spec name, which is not always the file name: IvParameterSpec.mop
    # declares IvParameterSpecSpec and RandomStringPassword.mop declares
    # RandomStringPasswordSpec. The declaration is what the monitor is named after.
    spec = path.stem
    block = "<spec-body>"

    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if match := SPEC_DECL.match(raw):
            spec = match.group(1)
        elif match := EVENT_DECL.match(raw):
            block = match.group(1)
        elif match := HANDLER_DECL.match(raw):
            block = "@" + match.group(1)
        elif AUTOMATON_DECL.match(raw):
            block = "<automaton>"

        for kind, pattern in SITE_PATTERNS.items():
            for constant in pattern.findall(raw):
                rows.append(
                    {
                        "property": constant,
                        "kind": kind,
                        "file": path.name,
                        "line": number,
                        "spec": spec,
                        "event": block,
                        "snippet": raw.strip(),
                    }
                )

    return rows


def inventory_set(specs_dir: Path) -> list[dict[str, object]]:
    """Every site in a set, ordered by file then line so two runs compare byte for byte."""
    rows: list[dict[str, object]] = []
    for path in sorted(specs_dir.glob("*.mop")):
        rows.extend(inventory_file(path))
    return sorted(rows, key=lambda row: (row["file"], row["line"], row["kind"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("specs_dir", type=Path, help="directory of .mop files")
    parser.add_argument("-o", "--output", type=Path, help="CSV path (default: stdout)")
    args = parser.parse_args()

    if not args.specs_dir.is_dir():
        print(f"not a directory: {args.specs_dir}", file=sys.stderr)
        return 1

    rows = inventory_set(args.specs_dir)
    handle = args.output.open("w", encoding="utf-8", newline="") if args.output else sys.stdout
    try:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if args.output:
            handle.close()

    counts = {kind: sum(1 for row in rows if row["kind"] == kind) for kind in SITE_PATTERNS}
    summary = ", ".join(f"{count} {kind.lower()}s" for kind, count in counts.items())
    print(f"{len(rows)} sites ({summary})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

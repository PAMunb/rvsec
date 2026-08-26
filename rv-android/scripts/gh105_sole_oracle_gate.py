#!/usr/bin/env python3
"""Nothing in the successor set names the withdrawn catalogue as an authority.

Task 11.4 of gh105, under design decision D-16: the sole oracle of `jca_android` is the
pinned expert copy `RVSec-replication-package/tools/rules/`. `MetaCrySL/generated/api30/`
keeps no oracle role in any dimension -- values, `ORDER`, event alphabets and predicates
alike. It stays on disk as the historical input the pre-D-16 records were written against,
and may be named only inside a supersession adendum.

This gate reads the three surfaces the successor set presents to a reader, and each one is
here for a reason of its own:

  * **the records of `data/jca_android/`** -- a row or a section that cites the generated
    rule as the thing a verdict answers to;
  * **the comments of the set's `.mop` files** -- the justification a maintainer reads
    before editing an event;
  * **the strings the set emits** -- the text a person reads in a violation report, which
    is the only one of the three that leaves the repository.

The third is not a widening for tidiness. Written as "no `.mop` comment" the gate reads
over the report strings, because a string handed to `ErrorDescription` is not a comment;
and those strings are exactly what task 11.8 repairs, so a gate that could not see them
could not prove 11.8 done.

**A supersession adendum is the one admissible form.** A row that says "the api30 rule
declares X" and then says D-15 or D-16 withdrew that reading is history, and history is
what keeps the era the published measurements answer to readable. A line that names the
catalogue with nothing beside it is a citation still standing, and that is the defect.

The gate derives its universe by enumeration and never from a list of expected findings:
every `.csv` and `.md` of the records directory, every `.mop` of the set. What it cannot
read it skips **declaredly**, and it counts what it skipped, so a run that stopped looking
cannot be told from a run that found nothing.

Usage:
    python scripts/gh105_sole_oracle_gate.py
    python scripts/gh105_sole_oracle_gate.py --records data/jca_android --set-dir <dir>
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: The successor set, under the reactor `RVSEC_HOME` points at.
def default_set_dir() -> Path:
    home = os.environ.get("RVSEC_HOME")
    root = Path(home) if home else REPO.parent / "rvsec"
    return root / "rvsec/rvsec-mop/src/main/resources/jca_android"


DEFAULT_RECORDS = REPO / "data/jca_android"

#: What naming the withdrawn catalogue looks like. `api30` catches the prose, `.cryptsl`
#: the citation of a file: both spellings occur alone, so the gate looks for either.
WITHDRAWN = re.compile(r"api30|\.cryptsl")

#: What makes a citation history rather than an authority: the row or section names the
#: decision that withdrew it. D-15 (2026-08-24) took the value dimension from the generated
#: catalogue and D-16 (2026-08-25) took the rest, and both wrote their adenda into what
#: they superseded. Naming the decision is the whole test, and it is deliberately a low
#: bar: the gate's job is to catch a citation left standing with nothing beside it, not to
#: grade the prose of an adendum a researcher wrote.
ADENDUM = re.compile(r"\bD-1[56]\b")

#: The records exempt by declaration and not by accident, each with the reason written.
#:
#: The first group is the output of the three instruments that carried out the
#: substitution -- `gh105_expert_ledger.py` (11.1), `gh105_expert_alphabet.py` (11.2) and
#: `gh105_expert_conformance.py` (11.4). Naming the withdrawn catalogue is what those
#: tables are FOR: a delta that could not say which clause it is a delta against would say
#: nothing at all. They are also the tables a hand edit cannot reach, because each
#: instrument's `--check` reproduces its file and fails if it does not -- so exempting them
#: here moves the guarantee to a sharper gate rather than dropping it.
#:
#: The other two are exempt for reasons of their own, and neither is derived.
EXEMPT = {
    "predicate_ledger.csv":
        "derived by gh105_expert_ledger.py (11.1) and reproduced by its --check",
    "predicate_ledger.md":
        "the prose reading of that ledger, which says what the sweep covers that the "
        "api30 one did not",
    "predicate_ledger_delta.csv":
        "the delta of the expert ledger against the api30-derived one (task 11.1)",
    "order_alphabet_map_expert.csv":
        "derived by gh105_expert_alphabet.py (11.2) and reproduced by its --check; its "
        "`reason` column exists to say what the substitution did to each association",
    "order_alphabet_map_delta.csv":
        "what the substitution cost the alphabet map, association by association (11.2)",
    "conformance_record_delta.csv":
        "the clause-by-clause census of the two catalogues (task 11.4): its `api30_line` "
        "and `api30_clause` columns are the delta",
    "order_alphabet_map.csv":
        "the pre-D-16 map, kept on disk and read by nothing (INV-INS-118)",
    "alias_table.csv":
        "`in_api30_allowlist` is a column name kept for continuity; README.md says which "
        "lists it is computed against, and they are the expert ones since D-15",
}

#: A report string is a `.mop` line handing text to `ErrorDescription`. The set writes
#: them one way -- a `v=1 code=...` envelope inside a string literal -- so the gate
#: recognises the envelope and not the call, which may sit lines above.
REPORT = re.compile(r'"v=1 code=')


@dataclass(frozen=True)
class Finding:
    """One place that names the withdrawn catalogue with no adendum beside it."""

    where: str
    surface: str
    text: str


def _record_findings(path: Path) -> list[Finding]:
    """A row of a `.csv`, or a section of a `.md`, that cites the catalogue bare.

    The unit differs by format for a reason: a CSV row is self-contained, so its adendum
    has to be in the row; a Markdown section is read as a whole, so an adendum anywhere
    in it covers the sentences above it -- which is how the D-15 and D-16 sections of
    `README.md` are written.
    """
    findings: list[Finding] = []
    if path.suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            for number, row in enumerate(csv.reader(handle), 1):
                text = " ".join(row)
                if WITHDRAWN.search(text) and not ADENDUM.search(text):
                    findings.append(Finding(f"{path.name}:{number}", "record", text[:120]))
        return findings

    section, heading, start = [], "(preamble)", 1
    def close(lines: list[str], name: str, line: int) -> None:
        body = "\n".join(lines)
        if WITHDRAWN.search(body) and not ADENDUM.search(body):
            hit = next(l for l in lines if WITHDRAWN.search(l))
            findings.append(Finding(f"{path.name}:{line} ({name})", "record", hit.strip()[:120]))

    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("#"):
            close(section, heading, start)
            section, heading, start = [], line.strip("# ").strip(), number
            continue
        section.append(line)
    close(section, heading, start)
    return findings


def _spec_findings(path: Path) -> list[Finding]:
    """A comment or an emitted string of one `.mop` that cites the catalogue bare.

    The unit is the line, and deliberately so: a `.mop` comment block is prose a reader
    stops at, and an adendum three paragraphs below does not reach the sentence that
    misleads. A line that needs the catalogue named carries its own marker.
    """
    findings: list[Finding] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not WITHDRAWN.search(line) or ADENDUM.search(line):
            continue
        surface = "message" if REPORT.search(line) else "comment"
        findings.append(Finding(f"{path.name}:{number}", surface, line.strip()[:120]))
    return findings


def run(records: Path, set_dir: Path) -> tuple[list[Finding], list[str], int]:
    """Sweep both surfaces.

    Returns:
        `(findings, skips, checked)` -- the skips are declared, one sentence each, and
        `checked` is how many files were actually read, so a silent universe is visible.
    """
    findings: list[Finding] = []
    skips: list[str] = []
    checked = 0

    if records.is_dir():
        for path in sorted(records.iterdir()):
            if path.is_dir():
                skips.append(f"{path.name}/: a directory of evidence, not a record of the set")
                continue
            if path.suffix not in (".csv", ".md"):
                skips.append(f"{path.name}: not a record format this gate reads")
                continue
            if path.name in EXEMPT:
                skips.append(f"{path.name}: {EXEMPT[path.name]}")
                continue
            checked += 1
            findings.extend(_record_findings(path))
    else:
        skips.append(f"{records}: the records directory is absent")

    if set_dir.is_dir():
        for path in sorted(set_dir.glob("*.mop")):
            checked += 1
            findings.extend(_spec_findings(path))
    else:
        skips.append(f"{set_dir}: the specification set is absent (RVSEC_HOME unset?)")

    return findings, skips, checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--records", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--set-dir", type=Path, default=None)
    arguments = parser.parse_args(argv)
    set_dir = arguments.set_dir or default_set_dir()

    findings, skips, checked = run(arguments.records, set_dir)
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.surface] = counts.get(finding.surface, 0) + 1
    tally = ", ".join(f"{counts[k]} {k}" for k in sorted(counts)) or "0"
    print(f"G-ORACLE: {checked} file(s) read, {len(findings)} finding(s) ({tally}), "
          f"{len(skips)} skipped")
    for finding in findings:
        print(f"  [{finding.surface}] {finding.where}: {finding.text}")
    for skip in skips:
        print(f"  skipped {skip}")
    if not checked:
        print("compared no file at all", file=sys.stderr)
        return 2
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

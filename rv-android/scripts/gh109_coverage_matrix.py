#!/usr/bin/env python3
"""Every rule of the pinned expert oracle, and the terminal state it ends in (INV-INS-150).

The master question of the `jca_android` set is whether everything the expert CrySL
oracle covers is also covered by MOP. Answering it needs an artifact that enumerates the
oracle rather than an argument that summarises it, because the failure mode is a rule
nobody remembered: before gh109, 27 of the 49 rules had no paired `.mop` and the absence
was visible only as six predicates with no possible producer.

Three terminal states, and no fourth:

  covered       the rule has a `.mop` in the set that specifies it.
  na-platform   the rule's subject class exists on no Android API level the set targets,
                so no trace can reach it.
  na-value      the class exists, but the rule states nothing an RV instrument can turn
                into a verdict at run time.

**`covered` is a verdict of pairing and adjudication, not of clause completeness.** That
distinction is the thing a reader will get wrong, so it is written here, in the CSV header
comment, and nowhere else does this script hedge it. Measured at the time of writing, 15 of
the 22 rules paired before gh109 carry at least one clause with no verdict surface --
`constraint_table.csv` reads 42 `CRYSL-NAO-IMPLEMENTADO` and 14 `NAO-DERIVADO` against 22
`IGUAL`, and `predicate_graph.csv` records 12 `omission` rows. The depth of a transcription
is measured elsewhere and MUST NOT be re-derived here: per rule by M0-M4 of the
`rvsec-crysl` conformance component (`SpecRulePairing`, `Silence`, `ConformanceReport`, the
`compare` CLI, all under CI), and clause by clause by `constraint_table.csv` and
`predicate_ledger.csv`. A second derivation would be a second translation of the oracle,
which is exactly what design decision D-19 forbids.

An **oracle defect is an attribute of a rule's row, never a state of its own** (D-21). The
`oracle_defect_row` column is a join, not a judgement: `divergence_record.csv` rows of kind
`oracle-wart` whose `file` column names a rule path (`tools/rules/<Rule>.crysl`) attach to
that rule, and the rule is transcribed by evident intent and still ends `covered`. A fourth
state would put `Cipher` in two at once -- it is paired, and a defect is recorded against
`Cipher.crysl:140-141`.

Two mappings are adjudicated rather than derived, and both are named in the source so that
neither can be mistaken for a convention:

  SecretKey -> SecretKeySpec.mop is `covered`. `SecretKeySpec.mop` sits in the ledger's
  `NON_PAIRING_FILES`, which governs *specification* pairing and not coverage: the file does
  realise the rule's ENSURES, and the rule's `Destroy` tail is recorded platform-dead
  (INV-INS-137 -- `destroy()` throws on every observable implementation), so no reachable
  trace yields a further verdict.

  HMACParameterSpec is `na-platform` despite having a `.mop`. Its subject class exists on no
  Android API level (INV-INS-155); the file is kept as documentation of untranslatability.

Rules with neither a pairing nor an adjudication are emitted with an empty
`terminal_state`. That is the honest state of an unfinished change, and it is why `--check`
distinguishes two failures: an inconsistency (a rule in two states, or a state outside the
three) always fails, while an unadjudicated rule fails only under `--require-complete`,
which is what gh109's final verification asks for.

Usage:
    gh109_coverage_matrix.py --emit                     # write the CSV
    gh109_coverage_matrix.py --check                    # re-derive and compare, exit 0/1
    gh109_coverage_matrix.py --check --require-complete  # ... and demand 49/49 states
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# The record family is a flat directory of scripts and not a package, so importing a
# sibling needs this directory on the path whatever the caller's working directory is.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gh105_expert_ledger import (  # noqa: E402
    DEFAULT_EXPERT_RULES,
    DEFAULT_SET_DIR,
    paired_rules,
)

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = REPO / "data/jca_android/coverage_matrix.csv"
DEFAULT_DIVERGENCE = REPO / "data/jca_android/divergence_record.csv"

FIELDS = ["rule", "terminal_state", "evidence", "oracle_defect_row"]

#: The three terminal states, and the whole of them (D-19).
TERMINAL_STATES = ("covered", "na-platform", "na-value")

#: The rule whose coverage is a mapping the ledger's pairing convention cannot express,
#: because the file that covers it is exempt from that convention. See the module docstring.
ADJUDICATED_PAIRINGS = {
    "SecretKey": (
        "SecretKeySpec.mop",
        "realises the rule's ENSURES; the Destroy tail is platform-dead (INV-INS-137), "
        "so no reachable trace yields a further verdict. NON_PAIRING_FILES governs "
        "specification pairing, not coverage",
    ),
}

#: Rules adjudicated to a non-`covered` state, with the evidence that adjudicates them.
#: gh109 tasks 4.4 and 5.1 fill this; a rule absent from here and from the set is pending.
ADJUDICATED_STATES = {
    "HMACParameterSpec": (
        "na-platform",
        "javax.crypto.spec.HMACParameterSpec exists on no Android API level (INV-INS-155); "
        "the .mop is kept as documentation of untranslatability, not as coverage",
    ),
    "Cookie": (
        "na-platform",
        "the rule's SPEC line names javax.servlet.http.Cookie, and the api30 jar holds zero "
        "entries under javax/servlet (archive listing of "
        "platforms/android-30/android.jar): the servlet API is not part of the Android "
        "platform at any level. Android's own cookie types -- java.net.HttpCookie, "
        "android.webkit.CookieManager -- are different classes with different methods, so "
        "there is no class here for the rule to be about",
    ),
    "DSAGenParameterSpec": (
        "na-platform",
        "java.security.spec.DSAGenParameterSpec has zero entries in the api30 jar (archive "
        "listing); the class first ships with API 35. The rule's sibling producer for the "
        "same predicate, DSAParameterSpec, is present and covered, so the DSA parameter "
        "route the set can observe is specified",
    ),
    "PasswordAuthentication": (
        "na-value",
        "java.net.PasswordAuthentication exists on api30 (archive listing), so the "
        "adjudication is about the rule and not the platform, and it rests on two verified "
        "legs (INV-INS-156). (a) Both CONSTRAINTS clauses are static-analysis predicates the "
        "instrument cannot evaluate at run time: neverTypeOf[password, java.lang.String] "
        "asks about the DECLARED type of the expression that produced the argument, which is "
        "erased by the time an advice sees a char[], and notHardCoded[password] asks whether "
        "the value came from a literal in the source. (b) generatedPasswordAuthentication "
        "(PasswordAuthentication.crysl:26) is required by no rule of the 49 -- it is this "
        "rule's own ENSURES and nothing else names it -- so a specification for the rule "
        "would monitor every construction and reach no verdict a reader could act on. What "
        "the ORDER would still accuse is recorded rather than assumed away: "
        "Con, (GetPassword | GetUserName)* refuses a getPassword() on an object whose "
        "construction went unobserved, exactly as every `ere : c1 ...` of the set does. That "
        "residue is the whole of what a specification here would add, and it is an artefact "
        "of instrumentation reach rather than a misuse the expert rule names -- which is why "
        "the once-claimed third leg, 'the ORDER is unviolatable', is withdrawn as imprecise "
        "and is not what this adjudication rests on",
    ),
}

#: The kind of divergence row that records an oracle defect (D-21).
ORACLE_DEFECT_KIND = "oracle-wart"

#: What the `file` column of such a row looks like when it names a rule rather than a `.mop`.
RULE_PATH_PREFIX = "tools/rules/"


def oracle_defects(record: Path) -> dict[str, list[str]]:
    """Collect the `oracle-wart` rows the divergence record holds against each rule.

    The join is by enumeration and not by judgement, which is the whole point of D-21's
    requirement that the row name the rule in its `file` column: a reader can check that
    the matrix's warrant exists by reading two files, without trusting either.

    Rows of the same kind that name a `.mop` instead are the older, specification-scoped
    warts (the CCM entry, the SHA-224 omissions) and belong to no rule's row here.

    Args:
        record: Path to `divergence_record.csv`. A missing file is not an error -- it
            yields no defects, so a tree without the record still derives a matrix.

    Returns:
        Rule name -> the `summary` of every `oracle-wart` row whose `file` column names
        that rule, in the order the record lists them. Rules with no defect are absent.
    """
    defects: dict[str, list[str]] = {}
    if not record.is_file():
        return defects
    with record.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row.get("kind") or "").strip() != ORACLE_DEFECT_KIND:
                continue
            name = (row.get("file") or "").strip()
            if not name.startswith(RULE_PATH_PREFIX):
                continue
            rule = Path(name).stem
            defects.setdefault(rule, []).append((row.get("summary") or "").strip())
    return defects


def derive(rules_dir: Path, set_dir: Path, record: Path) -> list[dict[str, str]]:
    """Derive one row per rule of the oracle, in rule order.

    A rule reaches a state by exactly one route -- pairing, adjudicated pairing, or
    adjudicated state -- and `check` is what asserts that the routes do not overlap. The
    order of the tests here is therefore not a precedence: it is the order in which the
    three are cheapest to establish, and `ADJUDICATED_STATES` deliberately wins over a
    pairing so that `HMACParameterSpec` reads `na-platform` while still having a `.mop`.

    Args:
        rules_dir: Directory of the pinned expert `.crysl` rules. Its `*.crysl` files are
            the enumeration itself -- the oracle is whatever this directory holds.
        set_dir: Directory of the `jca_android` `.mop` files, read to establish pairing.
        record: Path to `divergence_record.csv`, joined for `oracle_defect_row`.

    Returns:
        One dictionary per rule, keyed by FIELDS:
        - "rule" (str): The rule's file stem, e.g. "Cipher"
        - "terminal_state" (str): One of TERMINAL_STATES, or "" when unadjudicated
        - "evidence" (str): The `.mop` that covers it, or why it cannot be covered
        - "oracle_defect_row" (str): Joined defect summaries, "; "-separated, or ""
    """
    defects = oracle_defects(record)
    pairs = paired_rules(set_dir, {p.stem: None for p in sorted(rules_dir.glob("*.crysl"))})
    rows: list[dict[str, str]] = []

    for path in sorted(rules_dir.glob("*.crysl")):
        rule = path.stem
        state, evidence = "", "pending adjudication (gh109 tasks 4.4, 5.1)"

        if rule in ADJUDICATED_STATES:
            state, evidence = ADJUDICATED_STATES[rule]
        elif rule in pairs:
            state, evidence = "covered", pairs[rule]
        elif rule in ADJUDICATED_PAIRINGS:
            mop, why = ADJUDICATED_PAIRINGS[rule]
            state, evidence = "covered", f"{mop} ({why})"

        rows.append(
            {
                "rule": rule,
                "terminal_state": state,
                "evidence": evidence,
                "oracle_defect_row": "; ".join(defects.get(rule, [])),
            }
        )
    return rows


def inconsistencies(rows: list[dict[str, str]], set_dir: Path) -> list[str]:
    """Audit the matrix for defects of its own, whatever the change's progress.

    A rule in two states is the failure D-19 exists to prevent, and it can only arise one
    way: an entry in `ADJUDICATED_STATES` for a rule the set also pairs, where the
    adjudication was not meant to override the pairing. `HMACParameterSpec` is that shape
    on purpose, so it is named rather than detected -- which is what makes every other
    occurrence a finding.

    Args:
        rows: The derived rows to audit, as returned by `derive`.
        set_dir: Directory of the `.mop` files. Pairing is re-established here so that the
            audit reads the tree rather than trusting the `evidence` column it audits.

    Returns:
        One human-readable line per failure, empty when the matrix is internally sound.
        An unadjudicated rule is not a failure here -- that is `check`'s call to make,
        and only under `--require-complete`.
    """
    failures: list[str] = []
    seen: set[str] = set()
    pairs = paired_rules(set_dir, {row["rule"]: None for row in rows})

    for row in rows:
        rule, state = row["rule"], row["terminal_state"]
        if rule in seen:
            failures.append(f"duplicate row            {rule}")
        seen.add(rule)
        if state and state not in TERMINAL_STATES:
            failures.append(
                f"state outside the three  {rule}  {state!r} not in {list(TERMINAL_STATES)}"
            )
        if (
            rule in ADJUDICATED_STATES
            and rule in pairs
            and rule not in {"HMACParameterSpec"}
        ):
            failures.append(
                f"two states               {rule}  paired to {pairs[rule]} and "
                f"adjudicated {ADJUDICATED_STATES[rule][0]}"
            )
    return failures


def read_matrix(matrix: Path) -> list[dict[str, str]]:
    """Read the committed matrix, with the header comment skipped.

    The `#` lines at the top of the file are the definition of `covered` -- the one thing a
    reader of this CSV is most likely to get wrong -- so they are carried in the artifact
    itself and not only in this module. `csv` has no notion of a comment, and reading the
    file without dropping them would take the first `#` line as the header row, so the skip
    happens here rather than being a rule every consumer has to remember.

    Args:
        matrix: Path to the committed `coverage_matrix.csv`.

    Returns:
        One dictionary per data row, keyed by FIELDS, with every value stripped.

    Raises:
        OSError: When `matrix` cannot be opened. Callers test `is_file()` first, so that a
            missing matrix is reported as a finding rather than as a traceback.
    """
    with matrix.open(encoding="utf-8", newline="") as handle:
        lines = [line for line in handle if not line.startswith("#")]
    return [
        {key: (value or "").strip() for key, value in row.items()}
        for row in csv.DictReader(lines)
    ]


def check(matrix: Path, rows: list[dict[str, str]], set_dir: Path, complete: bool) -> int:
    """Compare the committed matrix against the live derivation, and return an exit code.

    Drift is a failure in both directions for the same reason the divergence record checks
    both: a committed row for a rule the oracle no longer has is a claim nobody re-verified,
    and a rule with no committed row is a rule that left the question unanswered.

    Args:
        matrix: Path to the committed `coverage_matrix.csv`.
        rows: The live derivation, as returned by `derive`.
        set_dir: Directory of the `.mop` files, passed through to `inconsistencies`.
        complete: When True, a rule with no terminal state is a failure
            (`--require-complete`, gh109 task 7.3).

    Returns:
        0 when the committed matrix and the tree agree, 1 when anything was reported.
        Every failure is printed to stderr, one per line, followed by a count.
    """
    # Step 1: defects the matrix carries on its own, before the committed file is read --
    # these fail whether or not a matrix has ever been emitted.
    failures = inconsistencies(rows, set_dir)

    # Step 2: load the committed answer. Its absence is itself a finding, not a crash.
    committed = []
    if matrix.is_file():
        committed = read_matrix(matrix)
    else:
        failures.append(f"no committed matrix      {matrix}")

    # Step 3: compare in both directions -- a rule missing a row and a row outstripping
    # the oracle are different failures and are named differently.
    live = {row["rule"]: row for row in rows}
    held = {row["rule"]: row for row in committed}
    for rule in sorted(set(live) | set(held)):
        if rule not in held:
            failures.append(f"rule with no row         {rule}  ({live[rule]['terminal_state'] or 'pending'})")
        elif rule not in live:
            failures.append(f"stale row                {rule}  the oracle has no such rule")
        else:
            for field in ("terminal_state", "evidence", "oracle_defect_row"):
                if held[rule][field] != live[rule][field]:
                    failures.append(
                        f"drifted {field:<16} {rule}\n"
                        f"    committed: {held[rule][field]!r}\n"
                        f"    derived:   {live[rule][field]!r}"
                    )

    # Step 4: completeness, which is a demand of the caller and not a property of the file.
    pending = [row["rule"] for row in rows if not row["terminal_state"]]
    if pending and complete:
        failures.append(
            f"{len(pending)} rule(s) with no terminal state: {', '.join(pending)}"
        )

    if failures:
        print("\n".join(failures), file=sys.stderr)
        print(f"\n{len(failures)} problem(s); {len(rows)} rule(s) in the oracle", file=sys.stderr)
        return 1

    counts = {state: sum(1 for row in rows if row["terminal_state"] == state) for state in TERMINAL_STATES}
    print(
        f"{len(rows)} rule(s): "
        + ", ".join(f"{count} {state}" for state, count in counts.items())
        + (f", {len(pending)} pending" if pending else "")
        + f"; {sum(1 for row in rows if row['oracle_defect_row'])} carrying an oracle-defect row",
        file=sys.stderr,
    )
    return 0


def emit(matrix: Path, rows: list[dict[str, str]]) -> int:
    """Write the matrix, header comment first.

    Args:
        matrix: Destination path. Its parent directory is created when absent.
        rows: The derivation to write, as returned by `derive`.

    Returns:
        0. Writing is unconditional, so nothing here fails without raising.
    """
    matrix.parent.mkdir(parents=True, exist_ok=True)
    with matrix.open("w", encoding="utf-8", newline="") as handle:
        handle.write(
            "# Derived by scripts/gh109_coverage_matrix.py --emit. Do not edit by hand.\n"
            "# terminal_state is one of covered | na-platform | na-value (D-19).\n"
            "# `covered` is a verdict of PAIRING AND ADJUDICATION, NOT of clause completeness:\n"
            "#   the depth of a transcription is measured per rule by M0-M4 of the rvsec-crysl\n"
            "#   conformance component and clause by clause by constraint_table.csv and\n"
            "#   predicate_ledger.csv. This file does not re-derive it.\n"
            "# oracle_defect_row is a join on divergence_record.csv rows of kind `oracle-wart`\n"
            "#   whose `file` column names tools/rules/<Rule>.crysl. A defect is an attribute of\n"
            "#   a rule's row, never a terminal state of its own (D-21).\n"
        )
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} row(s) written to {matrix}", file=sys.stderr)
    return 0


def main() -> int:
    """Parse arguments and dispatch to `--emit` or `--check`.

    The two are asserting and proposing, as everywhere else in this record family:
    `--emit` writes what the tree says, `--check` returns 1 when the committed answer and
    the tree have come apart.

    Returns:
        The exit code of the selected mode, or 1 when the rules or the set directory is
        missing -- a mistyped path must not be allowed to read as an empty oracle.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rules", type=Path, default=DEFAULT_EXPERT_RULES)
    parser.add_argument("--set-dir", type=Path, default=DEFAULT_SET_DIR)
    parser.add_argument("--record", type=Path, default=DEFAULT_DIVERGENCE)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="fail when any rule has no terminal state (gh109 task 7.3)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--emit", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    for label, path in (("rules", args.rules), ("set", args.set_dir)):
        if not path.is_dir():
            print(f"{label} directory not found: {path}", file=sys.stderr)
            return 1

    rows = derive(args.rules, args.set_dir, args.record)
    if args.emit:
        return emit(args.matrix, rows)
    return check(args.matrix, rows, args.set_dir, args.require_complete)


if __name__ == "__main__":
    raise SystemExit(main())

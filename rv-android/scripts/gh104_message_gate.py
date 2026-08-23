#!/usr/bin/env python3
"""The message-property gate over a specification set (INV-INS-121, D-13).

Four properties, each of which has been violated in the frozen `jca` by a site
that reads perfectly well:

  literal-mismatch          a number in the message that the guard does not use.
                            `PBEKeySpecSpec.mop:50` says "should be >= 1000"
                            under a guard reading `iterationCount < 10000`; the
                            report is off by a factor of ten and nothing catches
                            it, because a message is free text to the compiler.

  code-bijection            every report site has exactly one row of the set's
                            `codes.csv`, and every row has exactly one site. A
                            code that names no site is a dead identifier in the
                            corpus; a site with no code cannot be counted.

  code-anchor               the `file_line` column of each `codes.csv` row against
                            the line the code is actually emitted from. The anchor
                            is what a reader follows from a report back to the
                            site that made it, and nothing else in the tree checks
                            it: two passes of this change found it drifted -- six
                            rows in one, five in the next -- and both times only
                            because someone re-anchored the whole file by script.
                            An anchor no gate checks is an anchor that drifts.

  wrong-error-type          the `ErrorType` of a site against the CrySL clause
                            family behind its event. A `FORBIDDEN` clause is not
                            a sequencing failure, so a site that reports
                            `InvalidSequenceOfMethodCalls` for it is telling the
                            reader to look at the call order for a defect that
                            has nothing to do with order (D-13, which adds
                            `ForbiddenMethod` for exactly this).

  self-contradicting        the guard reads one operand and the message reports
  envelope                  another. When the guard tests a monitor field and
                            the message prints the observed object's real
                            algorithm, the envelope can carry `val` inside the
                            `exp` list it is accused of missing -- an accusation
                            that refutes itself in its own text.

  not-observed-family       a three-valued predicate read reports NOT_OBSERVED
                            -- "no producer of this object was ever seen" -- with
                            a code family of its own, distinct from the violation
                            codes (INV-INS-143). Folded into one family, a reach
                            limit of the instrumentation is counted as a misuse,
                            and the two are not the same claim: one says the
                            program did something the rule forbids, the other
                            says the monitor never saw the half of the program
                            that would settle it. The branch a site sits in is
                            read from the equality test on `PredicateVerdict`
                            that admits it, and its family from the `site_kind`
                            column the code already carries in `codes.csv`.

On the frozen `jca` the envelope flag is zero by construction: every guard-on-
field site there reports the same field it guards ("but found ." when the field
is empty). Those nine sites are reported as `guard-on-field` notes, because they
are what E1 changes and what makes the flag fire on `jca_android` until E4 task
8.16 moves the guard to the getter as well.

Usage:
    gh104_message_gate.py <set directory> [--crysl <generated/api30>]
                          [--json report.json]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gh104_gates import (  # noqa: E402
    MopEvent,
    MopSpec,
    _call_signature,
    _crysl_params,
    classify_orphan,
    parse_mop,
    rule_for,
)
from gh104_mop_lint import error_sites  # noqa: E402

# A standalone integer: `>= 1000` yes, the `256` of `SHA-256` no. The negative
# look-around on `-` and `.` is what keeps algorithm names out of the count.
STANDALONE_INT = re.compile(r"(?<![\w.\-])\d+(?![\w.\-])")

# The envelope's version marker (design D-3) is structure, not sentence. `v=1`
# reads as a standalone integer to the pattern above, so without this every
# envelope of `jca_android` would be reported as a number its guard does not
# use -- fifty findings that would bury the one real off-by-a-factor-of-ten.
ENVELOPE_VERSION = re.compile(r"(?<![\w.\-])v=\d+")

# The failure code as the envelope carries it: `code=<SPEC>-<KIND>-<NN>`, inside
# the message rather than as a literal of its own, so the bijection is read out
# of the grammar the report actually uses.
CODE_TOKEN = re.compile(r"\bcode=([A-Z0-9][A-Z0-9\-]*)")

# The `site_kind` of the *not observed* code family. A code is `<SPEC>-<KIND>-<NN>`
# and `codes.csv` carries the kind in its own column, so the family is read from
# the row rather than parsed back out of the identifier.
NOT_OBSERVED_KIND = "NOBS"

# Only the equality form is read. `v != PredicateVerdict.SATISFIED` names a verdict
# without saying which branch this site is, and a gate that guessed there would
# report a finding the reader has to dismiss -- worse than reporting nothing.
VERDICT_TEST = re.compile(r"==\s*(?:\w+\s*\.\s*)?PredicateVerdict\s*\.\s*(\w+)")
STRING_LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')
FIELD_READ = re.compile(r"\b(current\w+)\b")
GETTER_READ = re.compile(r"\b(\w+)\.get(\w+)\(\)")

# What each CrySL clause family says the report is about. `ForbiddenMethod` is
# D-13's addition; a set that has not taken it yet fails this check on the two
# `PBEKeySpecSpec` sites, which is the point.
EXPECTED_TYPE = {
    "FORBIDDEN": {"ForbiddenMethod"},
    "REQUIRES": {"UnsatisfiedConstraint"},
    "CONSTRAINTS-value": {"UnsafeAlgorithm", "UnsafeProtocol", "InvalidKeyStoreType"},
    "CONSTRAINTS-numeric": {"UnsatisfiedConstraint", "InvalidKeySize"},
}


def _site_type(site: dict) -> str | None:
    match = re.search(r"ErrorType\s*\.\s*(\w+)", site["arguments"][0] if site["arguments"] else "")
    return match.group(1) if match else None


def _messages(site: dict) -> list[str]:
    """The free-text arguments of a report site (everything past the location).

    The envelope's version marker is dropped first, so that what is scanned for
    numbers is what a reader would call the message: the sentence and the
    expected value, never the grammar's own header.
    """
    return [
        ENVELOPE_VERSION.sub("", literal)
        for argument in site["arguments"][3:]
        for literal in STRING_LITERAL.findall(argument)
    ]


def _enclosing_event(mop: MopSpec, line: int) -> MopEvent | None:
    """The event whose *body* contains this line, or None for a `@fail` handler.

    Handler sites deliberately map to no event: the clause family behind an
    event says what its own report is about, and says nothing about the
    sequencing report the handler emits.
    """
    for event in mop.events:
        if event.body_start <= line <= event.body_end:
            return event
    return None


def _nested_in_condition(mop: MopSpec, event: MopEvent, line: int) -> bool:
    """True when the site sits under an `if` inside the body rather than at its top.

    A site at the top of an event body *is* the violating branch, and the CrySL
    clause the event encodes is what it reports. A site under an `if` is a
    second, hand-written guard inside an event that has its own purpose -- the
    guard-on-field sites -- and the event's clause says nothing about it.
    """
    lines = mop.text.splitlines()[event.body_start - 1 : line - 1]
    return any(re.search(r"\bif\s*\(", text) for text in lines)


def _verdict_branch(guard: str) -> str | None:
    """Which three-valued verdict admits a report site, or None if it is not one.

    Args:
        guard: The site's admitting condition, as `_guard_text` renders it.

    Returns:
        `NOT_OBSERVED` when the guard tests for it, `VIOLATED` when it tests for
        that instead, and None when the guard names no verdict by equality --
        which is every site of a set that has no three-valued read, and every
        ordinary `CONSTRAINTS` guard in a set that does.
    """
    names = VERDICT_TEST.findall(guard)
    if "NOT_OBSERVED" in names:
        return "NOT_OBSERVED"
    if "VIOLATED" in names:
        return "VIOLATED"
    return None


def _guard_text(mop: MopSpec, event: MopEvent | None, site: dict) -> str:
    """The condition that admits this site: the event's, plus any enclosing `if`."""
    parts = []
    if event and event.condition:
        parts.append(event.condition)
    lines = mop.text.splitlines()
    for number in range(site["line"] - 1, max(site["line"] - 6, 0), -1):
        text = lines[number - 1]
        if "if" in text and "(" in text:
            parts.append(text)
            break
    return " ".join(parts)


def _clause_family(mop: MopSpec, event: MopEvent, crysl_dir: Path) -> str | None:
    """The clause family behind an event, via the same classifier G-2 uses."""
    rule = rule_for(mop.spec, crysl_dir)
    if rule is None:
        return None
    verdict = classify_orphan(mop, event, rule, accept_requires=True)
    if verdict["verdict"] != "orphan-with-clause":
        return None
    clause = verdict["clause"]
    if " FORBIDDEN " in clause:
        return "FORBIDDEN"
    if " REQUIRES " in clause:
        return "REQUIRES"
    if " in {" not in clause:
        return "CONSTRAINTS-numeric"
    # An allow-list over a numeric object is a size constraint, not an algorithm
    # one: `keySize in {2048}` is reported as an invalid key size, not as an
    # unsafe algorithm.
    constrained = re.search(r"(\w+)\s+in\s*\{", clause.split("=>")[-1])
    if constrained and rule.objects.get(constrained.group(1), "").lower() in ("int", "long"):
        return "CONSTRAINTS-numeric"
    return "CONSTRAINTS-value"


def check(directory: Path, crysl_dir: Path | None) -> dict:
    findings: list[dict] = []
    notes: list[dict] = []
    skipped: list[str] = []

    codes_path = directory / "codes.csv"
    codes: dict[str, dict] = {}
    if codes_path.is_file():
        with codes_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                codes[(row.get("code") or "").strip()] = row
    else:
        skipped.append(f"code-bijection: {codes_path} does not exist")

    site_codes: set[str] = set()
    verdict_sites = 0

    for path in sorted(directory.glob("*.mop")):
        mop = parse_mop(path)
        for site in error_sites(mop):
            if site["commented"]:
                continue  # a report the set holds and does not emit
            event = _enclosing_event(mop, site["line"])
            guard = _guard_text(mop, event, site)
            messages = _messages(site)

            # -- literal-mismatch -------------------------------------------
            guard_numbers = set(STANDALONE_INT.findall(guard))
            for message in messages:
                for number in STANDALONE_INT.findall(message):
                    if number not in guard_numbers:
                        findings.append(
                            {
                                "kind": "literal-mismatch",
                                "spec": mop.spec,
                                "file": path.name,
                                "line": site["line"],
                                "detail": f"the message says {number} and the guard uses "
                                f"{sorted(guard_numbers) or 'no literal'}",
                            }
                        )

            # -- wrong-error-type -------------------------------------------
            declared = _site_type(site)
            if (
                declared
                and event
                and crysl_dir
                and crysl_dir.is_dir()
                and not _nested_in_condition(mop, event, site["line"])
            ):
                family = _clause_family(mop, event, crysl_dir)
                if family and declared not in EXPECTED_TYPE[family]:
                    findings.append(
                        {
                            "kind": "wrong-error-type",
                            "spec": mop.spec,
                            "file": path.name,
                            "line": site["line"],
                            "detail": f"`{declared}` on a site whose clause family is {family}; "
                            f"expected one of {sorted(EXPECTED_TYPE[family])}",
                        }
                    )

            # -- self-contradicting envelope --------------------------------
            guard_fields = set(FIELD_READ.findall(guard))
            message_fields = {
                field for message_part in site["arguments"][3:]
                for field in FIELD_READ.findall(message_part)
            }
            message_getters = {
                f"{obj}.get{name}()"
                for argument in site["arguments"][3:]
                for obj, name in GETTER_READ.findall(argument)
            }
            if guard_fields:
                notes.append(
                    {
                        "kind": "guard-on-field",
                        "spec": mop.spec,
                        "file": path.name,
                        "line": site["line"],
                        "detail": f"the guard reads the monitor field(s) {sorted(guard_fields)} "
                        "rather than the observed object",
                    }
                )
            if guard_fields and (message_getters or (message_fields and message_fields != guard_fields)):
                findings.append(
                    {
                        "kind": "self-contradicting envelope",
                        "spec": mop.spec,
                        "file": path.name,
                        "line": site["line"],
                        "detail": f"the guard reads {sorted(guard_fields)} and the message reports "
                        f"{sorted(message_getters | (message_fields - guard_fields))}; "
                        "the envelope can carry `val` inside `exp`",
                    }
                )

            # -- code-bijection ---------------------------------------------
            # Only meaningful once the set has a `codes.csv`; the frozen `jca`
            # has none and its sites carry no code, so the whole property is
            # skipped there rather than reported as fifty absences.
            if codes_path.is_file():
                emitted = {
                    code
                    for argument in site["arguments"][3:]
                    for literal in STRING_LITERAL.findall(argument)
                    for code in CODE_TOKEN.findall(literal)
                }
                if not emitted:
                    findings.append(
                        {
                            "kind": "code-bijection",
                            "spec": mop.spec,
                            "file": path.name,
                            "line": site["line"],
                            "detail": "the site emits no `code=` and cannot be counted",
                        }
                    )
                for code in sorted(emitted):
                    if code not in codes:
                        findings.append(
                            {
                                "kind": "code-bijection",
                                "spec": mop.spec,
                                "file": path.name,
                                "line": site["line"],
                                "detail": f"`{code}` is emitted and listed in no row of codes.csv",
                            }
                        )
                    elif code in site_codes:
                        findings.append(
                            {
                                "kind": "code-bijection",
                                "spec": mop.spec,
                                "file": path.name,
                                "line": site["line"],
                                "detail": f"`{code}` is emitted by more than one report site",
                            }
                        )
                    anchor = (codes.get(code) or {}).get("file_line", "").strip()
                    here = f"{path.name}:{site['line']}"
                    if code in codes and anchor != here:
                        findings.append(
                            {
                                "kind": "code-anchor",
                                "spec": mop.spec,
                                "file": path.name,
                                "line": site["line"],
                                "detail": f"`{code}` is emitted here and codes.csv anchors it at "
                                f"`{anchor or 'nothing'}`",
                            }
                        )
                    site_codes.add(code)

                # -- not-observed family --------------------------------
                branch = _verdict_branch(guard)
                if branch:
                    verdict_sites += 1
                    for code in sorted(emitted):
                        family = (codes.get(code) or {}).get("site_kind", "").strip()
                        if branch == "NOT_OBSERVED" and family != NOT_OBSERVED_KIND:
                            findings.append(
                                {
                                    "kind": "not-observed-family",
                                    "spec": mop.spec,
                                    "file": path.name,
                                    "line": site["line"],
                                    "detail": f"`{code}` is emitted under a NOT_OBSERVED branch "
                                    f"and codes.csv files it as `{family or 'nothing'}`, not "
                                    f"`{NOT_OBSERVED_KIND}`; a verdict of "
                                    "\"no producer was observed\" would be counted as a violation",
                                }
                            )
                        elif branch != "NOT_OBSERVED" and family == NOT_OBSERVED_KIND:
                            findings.append(
                                {
                                    "kind": "not-observed-family",
                                    "spec": mop.spec,
                                    "file": path.name,
                                    "line": site["line"],
                                    "detail": f"`{code}` belongs to the {NOT_OBSERVED_KIND} family "
                                    f"and is emitted under a {branch} branch; the family exists to "
                                    "keep the two apart",
                                }
                            )

    if not verdict_sites:
        skipped.append(
            "not-observed-family: no report site is admitted by a `PredicateVerdict` "
            "equality test, so the set carries no three-valued read"
        )

    if codes:
        for code in sorted(set(codes) - site_codes):
            findings.append(
                {
                    "kind": "code-bijection",
                    "spec": codes[code].get("spec", ""),
                    "file": "codes.csv",
                    "line": 0,
                    "detail": f"`{code}` is listed and no report site emits it",
                }
            )

    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding["kind"]] = counts.get(finding["kind"], 0) + 1

    return {
        "directory": str(directory),
        "findings": findings,
        "notes": notes,
        "counts": counts,
        "skipped": skipped,
        "ok": not findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--crysl", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    if not args.directory.is_dir():
        print(f"not a specification-set directory: {args.directory}", file=sys.stderr)
        return 2

    report = check(args.directory, args.crysl)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    for reason in report["skipped"]:
        print(f"skipped -- {reason}", file=sys.stderr)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

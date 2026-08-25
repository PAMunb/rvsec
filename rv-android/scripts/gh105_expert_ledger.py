#!/usr/bin/env python3
"""Derive the predicate ledger of a specification set from a CrySL rule catalogue.

Task 11.1 of gh105, under design decision D-16: the sole oracle of `jca_android` is the
pinned expert copy `RVSec-replication-package/tools/rules/`. The 36-clause ledger this
replaces (design.md, "The 36-Clause Ledger (REQUIRES, api30)") was derived against
`MetaCrySL/generated/api30/`, and a disposition that only held under that anchor has to
be re-derived rather than copied.

The script sweeps `REQUIRES`, `ENSURES` and `NEGATES` of every rule in a catalogue and
emits two tables:

  * the ledger -- one row per REQUIRES clause, with the predicate it consumes, the
    variables it binds, whether the rule's own EVENTS bind them, which rules produce the
    predicate, and the disposition that follows;
  * the delta -- the same derivation run over two catalogues, matched clause by clause,
    reporting what appears in only one of them and what appears in both with a different
    binding or arity.

Everything the script prints is derived by enumeration over the rule text. The one input
that is *not* derived is the platform-limit override table below: a handful of clauses
whose disposition rests on a measurement against android-30 rather than on rule text.
D-16 carries those measurements over explicitly ("re-cited, never re-litigated"), so they
are applied as named overrides with their citation instead of being silently recomputed.

Usage:
    python scripts/gh105_expert_ledger.py --emit ledger
    python scripts/gh105_expert_ledger.py --emit delta
    python scripts/gh105_expert_ledger.py --check      # arithmetic closes, exit 0/1
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REACTOR = REPO.parent

DEFAULT_EXPERT_RULES = REACTOR.parent / "RVSec-replication-package/tools/rules"
DEFAULT_API30_RULES = REACTOR.parent / "MetaCrySL/generated/api30"
DEFAULT_SET_DIR = REACTOR / "rvsec/rvsec-mop/src/main/resources/jca_android"

RULE_EXTENSIONS = (".crysl", ".cryptsl")

SECTION_KEYWORDS = (
    "SPEC",
    "OBJECTS",
    "EVENTS",
    "ORDER",
    "CONSTRAINTS",
    "REQUIRES",
    "ENSURES",
    "NEGATES",
    "FORBIDDEN",
)

# Dispositions whose ground is a measurement against the platform, not the rule text.
# Each entry names the rule, the predicate, and the evidence D-16 carries over. A clause
# listed here is derived like any other and then overridden, so the override shows up in
# the output as a disposition that disagrees with the derivation -- which is the point:
# the reader sees both the structural verdict and the measured one.
PLATFORM_OVERRIDES: dict[tuple[str, str], tuple[str, str]] = {
    ("KeyPairGenerator", "preparedDH"): (
        "unreachable-composition",
        "the JCA refuses DHGenParameterSpec at KeyPairGenerator.initialize; measured, "
        "ledger clause #17 of the api30 derivation",
    ),
    ("Mac", "preparedHMAC"): (
        "unreachable-composition",
        "javax.xml.crypto.dsig.spec.HMACParameterSpec is absent from the api30 "
        "android.jar, so the producing class cannot be loaded; measured, ledger clause "
        "#21 of the api30 derivation",
    ),
}

# Clauses whose emptiness is a runtime fact the rule text cannot show. Structurally the
# variable is bound and a producer exists, so the derivation calls them wireable; what
# makes them empty is what the platform does with the object at run time. Kept apart from
# PLATFORM_OVERRIDES because the ground is different: there the composition is refused,
# here it is admitted and can never carry the predicate.
VACUITY_OVERRIDES: dict[tuple[str, str, str], tuple[str, str]] = {
    ("Mac", "encrypted", "output2"): (
        "vacuous",
        "the negated clause over `output2`, which `f2: output2 = doFinal(input)` binds "
        "only as a returned array; the JCA allocates it fresh on every call, so no "
        "`encrypted` can be standing on it; measured, ledger clause #23 of the api30 "
        "derivation. The sibling clause over `output1` is wired and is not this row.",
    ),
}

# Rules that carry no `.mop` because the class does not exist on the target platform, as
# opposed to rules the set chose not to specify. Kept apart so a reader can tell a
# platform absence from a scope decision.
PLATFORM_ABSENT_CLASSES = {"Cookie"}

# Files of the set that specify no rule, and so are not pairings. Naming alone cannot
# tell them apart from one, which is why the exception is declared instead of inferred:
# `SecretKeySpec.mop` differs from `SecretKeySpecSpec.mop` by one suffix, and a rule
# named `SecretKey` would otherwise claim the first as its own. It is the propagator --
# `grep -c "new ErrorDescription("` returns 0 and it has no `@fail` -- and it exists to
# realise `SecretKey.crysl`'s ENSURES for another specification to read, which is not the
# same as specifying the rule. `RandomStringPassword.mop` is the heuristic bridge and
# `IvChainJunction.mop` the junction; neither has a rule of its own.
NON_PAIRING_FILES = {
    "SecretKeySpec.mop",
    "RandomStringPassword.mop",
    "IvChainJunction.mop",
}

# Predicates the two catalogues spell differently for the same thing. Matching the delta
# on the raw name would report each of these as two orphan rows -- one "expert-only" and
# one "api30-only" -- and hide that the clause is the same clause under a new name. The
# pairing is resolved here, in the ledger, and not in the specifications: the property
# the wired reads name in code is a `Property` enum constant of the store, which answers
# to neither catalogue.
PREDICATE_ALIASES = {
    "generatedKeyManager": "generatedKeyManagers",
    "generatedTrustManager": "generatedTrustManagers",
}


def canonical(predicate: str) -> str:
    return PREDICATE_ALIASES.get(predicate, predicate)


# ---------------------------------------------------------------------------
# Rule parsing
# ---------------------------------------------------------------------------


@dataclass
class Clause:
    """One REQUIRES / ENSURES / NEGATES entry of a rule."""

    section: str
    rule: str
    line: int
    text: str
    predicate: str
    arguments: tuple[str, ...]
    negated: bool
    guard: str = ""
    after: str = ""

    @property
    def arity(self) -> int:
        return len(self.arguments)

    @property
    def variables(self) -> tuple[str, ...]:
        """The rule variables the clause names, anonymous positions and literals dropped.

        An argument position is not always a bare variable: both catalogues write
        splitter applications in the second position of `Cipher`'s `generatedKey`
        (`alg(transformation)` in the expert copy, `part(0,"/",transformation)` in the
        generated one). What the clause depends on is the variable inside, so that is
        what is extracted -- reading the position as an opaque name would call the
        clause unbindable and invert its disposition.
        """
        found: list[str] = []
        for argument in self.arguments:
            if argument == "_":
                continue
            for name in _identifiers(argument):
                if name not in found:
                    found.append(name)
        return tuple(found)


@dataclass
class Rule:
    name: str
    path: Path
    objects: dict[str, str] = field(default_factory=dict)
    bound: set[str] = field(default_factory=set)
    events: list[str] = field(default_factory=list)
    requires: list[Clause] = field(default_factory=list)
    ensures: list[Clause] = field(default_factory=list)
    negates: list[Clause] = field(default_factory=list)


def _sections(path: Path) -> dict[str, list[tuple[int, str]]]:
    """Split a rule into sections, each a list of (line number, joined statement).

    Statements are joined until the terminating `;` because CrySL wraps long value lists
    and implications across lines, and a half-read clause parses into a different clause
    rather than into an error.
    """
    out: dict[str, list[tuple[int, str]]] = {k: [] for k in SECTION_KEYWORDS}
    current = ""
    buffer = ""
    start = 0
    for number, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("//"):
            continue
        head = re.match(r"^([A-Z]+)\b\s*:?\s*(.*)$", stripped)
        if head and head.group(1) in SECTION_KEYWORDS:
            if buffer.strip() and current:
                out[current].append((start, buffer.strip()))
            current = head.group(1)
            buffer = head.group(2)
            start = number
            if buffer.strip().endswith(";"):
                out[current].append((number, buffer.strip()))
                buffer = ""
            continue
        if not current:
            continue
        if not buffer.strip():
            start = number
        buffer += " " + stripped
        if stripped.endswith(";"):
            out[current].append((start, buffer.strip()))
            buffer = ""
    if buffer.strip() and current:
        out[current].append((start, buffer.strip()))
    return out


_PREDICATE = re.compile(r"^(!?)\s*([A-Za-z_][A-Za-z0-9_]*)\s*\[([^\]]*)\]\s*(.*)$")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _split_arguments(text: str) -> tuple[str, ...]:
    """Split a predicate's argument list on its top-level commas.

    Nesting matters because a splitter application carries commas of its own:
    `part(0,"/",transformation)` is *one* argument, and splitting it naively turns a
    two-place predicate into a four-place one, which then matches nothing in the delta.
    """
    if not text.strip():
        return ()
    out: list[str] = []
    depth = 0
    quoted = False
    current = ""
    for character in text:
        if character == '"':
            quoted = not quoted
        if not quoted:
            if character in "([{":
                depth += 1
            elif character in ")]}":
                depth -= 1
            elif character == "," and depth == 0:
                out.append(current.strip())
                current = ""
                continue
        current += character
    out.append(current.strip())
    return tuple(a for a in out if a)


def _identifiers(expression: str) -> list[str]:
    """The variable names of an expression: identifiers that are not applied as functions.

    `alg(transformation)` yields `transformation`; `part(0,"/",transformation)` yields the
    same; a quoted literal yields nothing.
    """
    without_strings = re.sub(r'"[^"]*"', " ", expression)
    names: list[str] = []
    for match in _IDENTIFIER.finditer(without_strings):
        tail = without_strings[match.end() :].lstrip()
        if tail.startswith("("):
            continue
        names.append(match.group(0))
    return names


def _parse_clause(section: str, rule: str, line: int, statement: str) -> Clause | None:
    text = statement.rstrip(";").strip()
    if not text:
        return None
    guard = ""
    body = text
    if "=>" in text:
        guard, _, body = text.partition("=>")
        guard = guard.strip()
        body = body.strip()
    match = _PREDICATE.match(body)
    if not match:
        return None
    negated, predicate, inside, tail = match.groups()
    arguments = _split_arguments(inside)
    after = ""
    tail = tail.strip()
    if tail.startswith("after"):
        after = tail[len("after") :].strip()
    return Clause(
        section=section,
        rule=rule,
        line=line,
        text=text,
        predicate=predicate,
        arguments=arguments,
        negated=bool(negated),
        guard=guard,
        after=after,
    )


def _event_bindings(statement: str) -> tuple[str, set[str]]:
    """The event's declared name and the variables it binds.

    A signature binds every named argument position plus, where the event is written as
    an assignment, the variable on the left. `_` binds nothing, which is exactly what
    made api30's `Init: init(kms, tms, _)` leave `sr` unbound and its `randomized[sr]`
    clause vacuous.
    """
    text = statement.rstrip(";").strip()
    name, _, rest = text.partition(":")
    name = name.strip()
    rest = rest.strip()
    if not rest or ":=" in text.split(":", 1)[0]:
        return name, set()
    bound: set[str] = set()
    target, sep, call = rest.partition("=")
    if sep and "(" not in target:
        bound.add(target.strip())
        rest = call.strip()
    inside = rest.partition("(")[2].rpartition(")")[0]
    for argument in inside.split(","):
        argument = argument.strip()
        if argument and argument != "_" and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", argument):
            bound.add(argument)
    return name, bound


def read_rule(path: Path) -> Rule:
    name = path.stem
    rule = Rule(name=name, path=path)
    sections = _sections(path)
    for _, statement in sections["OBJECTS"]:
        declaration = statement.rstrip(";").strip()
        parts = declaration.split()
        if len(parts) >= 2:
            rule.objects[parts[-1]] = " ".join(parts[:-1])
    for _, statement in sections["EVENTS"]:
        if ":=" in statement:
            continue
        event, bound = _event_bindings(statement)
        if event:
            rule.events.append(event)
        rule.bound |= bound
    rule.bound.add("this")
    for section, target in (
        ("REQUIRES", rule.requires),
        ("ENSURES", rule.ensures),
        ("NEGATES", rule.negates),
    ):
        for line, statement in sections[section]:
            clause = _parse_clause(section, name, line, statement)
            if clause is not None:
                target.append(clause)
    return rule


def read_catalogue(directory: Path) -> dict[str, Rule]:
    rules: dict[str, Rule] = {}
    for path in sorted(directory.iterdir()):
        if path.suffix in RULE_EXTENSIONS:
            rule = read_rule(path)
            rules[rule.name] = rule
    return rules


# ---------------------------------------------------------------------------
# Pairing with the specification set
# ---------------------------------------------------------------------------


def paired_rules(set_dir: Path, rules: dict[str, Rule]) -> dict[str, str]:
    """Rule name -> the `.mop` that specifies it, for the rules the set covers.

    Two spellings are in use and both are the set's own: `Cipher.crysl` is specified by
    `CipherSpec.mop` and `IvParameterSpec.crysl` by `IvParameterSpec.mop`. Anything else
    in the directory specifies no rule -- the two propagators and the junction -- and is
    not a pairing.
    """
    present = {p.name for p in set_dir.glob("*.mop")} - NON_PAIRING_FILES
    pairs: dict[str, str] = {}
    for name in rules:
        for candidate in (f"{name}Spec.mop", f"{name}.mop"):
            if candidate in present:
                pairs[name] = candidate
                break
    return pairs


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------


@dataclass
class LedgerRow:
    number: int
    section: str
    consumer: str
    clause: str
    predicate: str
    arity: int
    negated: bool
    guarded: bool
    bindable: bool
    producers: tuple[str, ...]
    producers_with_mop: tuple[str, ...]
    disposition: str
    reason: str
    rule_line: str


def derive_ledger(rules: dict[str, Rule], pairs: dict[str, str]) -> list[LedgerRow]:
    producers: dict[str, list[str]] = {}
    consumers: dict[str, list[str]] = {}
    for rule in rules.values():
        for clause in rule.ensures:
            producers.setdefault(canonical(clause.predicate), []).append(rule.name)
        for clause in rule.requires:
            consumers.setdefault(canonical(clause.predicate), []).append(rule.name)

    rows: list[LedgerRow] = []
    number = 0
    for name in sorted(rules):
        rule = rules[name]
        for clause in rule.requires:
            number += 1
            named = clause.variables
            bindable = all(argument in rule.bound for argument in named) if named else True
            produced_by = tuple(sorted(set(producers.get(canonical(clause.predicate), ()))))
            produced_with_mop = tuple(p for p in produced_by if p in pairs)

            if not bindable:
                unbound = [a for a in named if a not in rule.bound]
                disposition = "vacuous"
                reason = (
                    f"the rule's own EVENTS bind no {'/'.join(unbound)}, so the clause has "
                    "no site to read at"
                )
            elif name not in pairs:
                disposition = "unmonitored-consumer"
                reason = (
                    "no .mop specifies the consuming rule"
                    + (" (class absent from the platform)" if name in PLATFORM_ABSENT_CLASSES else "")
                )
            elif not produced_by:
                disposition = "unclosable"
                reason = f"no rule of the catalogue ENSURES {clause.predicate}"
            elif not produced_with_mop:
                disposition = "unmonitored-producer"
                reason = (
                    f"{clause.predicate} is ensured only by {', '.join(produced_by)}, "
                    "none of which has a .mop"
                )
            else:
                disposition = "wireable"
                reason = f"consumer and producer both specified ({', '.join(produced_with_mop)})"

            override = PLATFORM_OVERRIDES.get((name, clause.predicate))
            if override is not None:
                disposition, reason = override[0], f"{override[1]} [platform measurement, D-16 carry-over]"

            first = named[0] if named else ""
            vacuity = VACUITY_OVERRIDES.get((name, clause.predicate, first))
            if vacuity is not None:
                disposition, reason = vacuity[0], f"{vacuity[1]} [runtime measurement, D-16 carry-over]"

            rows.append(
                LedgerRow(
                    number=number,
                    section="REQUIRES",
                    consumer=name,
                    clause=clause.text,
                    predicate=clause.predicate,
                    arity=clause.arity,
                    negated=clause.negated,
                    guarded=bool(clause.guard),
                    bindable=bindable,
                    producers=produced_by,
                    producers_with_mop=produced_with_mop,
                    disposition=disposition,
                    reason=reason,
                    rule_line=f"{rule.path.name}:{clause.line}",
                )
            )

    # The production half of the sweep. A produced predicate nobody consumes is as much a
    # break in the chain as a consumed one nobody produces, and only the two halves
    # together let the arithmetic close -- which is what task 11.7 checks.
    for name in sorted(rules):
        rule = rules[name]
        for section, clauses in (("ENSURES", rule.ensures), ("NEGATES", rule.negates)):
            for clause in clauses:
                number += 1
                read_by = tuple(sorted(set(consumers.get(canonical(clause.predicate), ()))))
                read_with_mop = tuple(r for r in read_by if r in pairs)
                if name not in pairs:
                    disposition = "unmonitored-producer-side"
                    reason = "no .mop specifies the producing rule"
                elif not read_by:
                    disposition = "unread"
                    reason = f"no rule of the catalogue REQUIRES {clause.predicate}"
                elif not read_with_mop:
                    disposition = "unmonitored-consumer-side"
                    reason = (
                        f"{clause.predicate} is required only by {', '.join(read_by)}, "
                        "none of which has a .mop"
                    )
                else:
                    disposition = "producible"
                    reason = f"read by {', '.join(read_with_mop)}"
                rows.append(
                    LedgerRow(
                        number=number,
                        section=section,
                        consumer=name,
                        clause=clause.text,
                        predicate=clause.predicate,
                        arity=clause.arity,
                        negated=clause.negated,
                        guarded=bool(clause.guard),
                        bindable=all(v in rule.bound for v in clause.variables)
                        if clause.variables
                        else True,
                        producers=read_by,
                        producers_with_mop=read_with_mop,
                        disposition=disposition,
                        reason=reason,
                        rule_line=f"{rule.path.name}:{clause.line}",
                    )
                )
    return rows


def _key(row: LedgerRow) -> tuple[str, str, str, int, bool, bool]:
    """What makes two clauses of different catalogues the same clause.

    Variable *names* are deliberately out of the key: the two catalogues spell the same
    binding `km` and `kms`, `random` and `sr`. Arity, negation and the presence of a
    guard are in, because those change what the clause says.
    """
    return (row.section, row.consumer, canonical(row.predicate), row.arity, row.negated, row.guarded)


def _shape_key(row: LedgerRow) -> tuple[str, str, str]:
    """The clause's identity without its shape, for the second matching pass."""
    return (row.section, row.consumer, canonical(row.predicate))


def derive_delta(expert: list[LedgerRow], api30: list[LedgerRow]) -> list[dict[str, str]]:
    left = {_key(r): r for r in expert}
    right = {_key(r): r for r in api30}

    # Second pass, for the case task 11.1 names outright: "in both with different binding
    # or arity". A clause the two catalogues write at different arity misses the exact
    # key and would otherwise leave two orphan rows -- one expert-only, one api30-only --
    # which reads as a clause appearing and another disappearing rather than as one
    # clause changing shape. Matched on rule and predicate alone, and only where exactly
    # one candidate stands on each side, so an ambiguous match stays two honest orphans.
    unmatched_left = {k: r for k, r in left.items() if k not in right}
    unmatched_right = {k: r for k, r in right.items() if k not in left}
    shaped_left: dict[tuple[str, str, str], list] = {}
    shaped_right: dict[tuple[str, str, str], list] = {}
    for k, r in unmatched_left.items():
        shaped_left.setdefault(_shape_key(r), []).append((k, r))
    for k, r in unmatched_right.items():
        shaped_right.setdefault(_shape_key(r), []).append((k, r))
    reshaped: dict[tuple, tuple] = {}
    for shape, lefts in shaped_left.items():
        rights = shaped_right.get(shape, [])
        if len(lefts) == 1 and len(rights) == 1:
            reshaped[lefts[0][0]] = (lefts[0][1], rights[0][1], rights[0][0])

    out: list[dict[str, str]] = []
    skip = {right_key for _, _, right_key in reshaped.values()}
    for key in sorted(set(left) | set(right)):
        if key in skip:
            continue
        if key in reshaped:
            a, b, _ = reshaped[key]
            differences = []
            if a.arity != b.arity:
                differences.append(f"arity api30={b.arity} expert={a.arity}")
            if a.negated != b.negated:
                differences.append(f"negated api30={b.negated} expert={a.negated}")
            if a.guarded != b.guarded:
                differences.append(f"guard api30={b.guarded} expert={a.guarded}")
            if a.disposition != b.disposition:
                differences.append(f"disposition {b.disposition} -> {a.disposition}")
            section, consumer, predicate = _shape_key(a)
            out.append(
                {
                    "section": section,
                    "consumer": consumer,
                    "predicate": predicate,
                    "arity": str(a.arity),
                    "negated": "yes" if a.negated else "no",
                    "guarded": "yes" if a.guarded else "no",
                    "kind": "reshaped",
                    "expert_disposition": a.disposition,
                    "api30_disposition": b.disposition,
                    "expert_line": a.rule_line,
                    "api30_line": b.rule_line,
                    "note": "; ".join(differences),
                }
            )
            continue
        a, b = left.get(key), right.get(key)
        section, consumer, predicate, arity, negated, guarded = key
        if a is not None and b is None:
            kind, note = "expert-only", "the api30 rule does not declare the clause"
        elif a is None and b is not None:
            kind, note = "api30-only", "the expert rule does not declare the clause"
        else:
            assert a is not None and b is not None
            differences = []
            if a.bindable != b.bindable:
                differences.append(
                    f"bindable expert={a.bindable} api30={b.bindable}"
                )
            if a.disposition != b.disposition:
                differences.append(f"disposition {b.disposition} -> {a.disposition}")
            if not differences:
                continue
            kind, note = "changed", "; ".join(differences)
        out.append(
            {
                "section": section,
                "consumer": consumer,
                "predicate": predicate,
                "arity": str(arity),
                "negated": "yes" if negated else "no",
                "guarded": "yes" if guarded else "no",
                "kind": kind,
                "expert_disposition": a.disposition if a else "-",
                "api30_disposition": b.disposition if b else "-",
                "expert_line": a.rule_line if a else "-",
                "api30_line": b.rule_line if b else "-",
                "note": note,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

LEDGER_HEADER = [
    "n",
    "section",
    "rule",
    "predicate",
    "arity",
    "negated",
    "guarded",
    "bindable",
    "counterparts",
    "counterparts_with_mop",
    "disposition",
    "reason",
    "rule_line",
    "clause",
]


def write_ledger(rows: list[LedgerRow], stream) -> None:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(LEDGER_HEADER)
    for row in rows:
        writer.writerow(
            [
                row.number,
                row.section,
                row.consumer,
                row.predicate,
                row.arity,
                "yes" if row.negated else "no",
                "yes" if row.guarded else "no",
                "yes" if row.bindable else "no",
                "|".join(row.producers) or "-",
                "|".join(row.producers_with_mop) or "-",
                row.disposition,
                row.reason,
                row.rule_line,
                row.clause,
            ]
        )


DELTA_HEADER = [
    "section",
    "consumer",
    "predicate",
    "arity",
    "negated",
    "guarded",
    "kind",
    "expert_disposition",
    "api30_disposition",
    "expert_line",
    "api30_line",
    "note",
]


def write_delta(rows: list[dict[str, str]], stream) -> None:
    writer = csv.DictWriter(stream, fieldnames=DELTA_HEADER, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)


def summarise(rows: list[LedgerRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.disposition] = counts.get(row.disposition, 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit", choices=("ledger", "delta", "summary"), default="summary")
    parser.add_argument("--expert-rules", type=Path, default=DEFAULT_EXPERT_RULES)
    parser.add_argument("--api30-rules", type=Path, default=DEFAULT_API30_RULES)
    parser.add_argument("--set-dir", type=Path, default=DEFAULT_SET_DIR)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--check", action="store_true", help="assert the arithmetic closes")
    args = parser.parse_args(argv)

    if not args.expert_rules.is_dir():
        print(f"expert rules not found: {args.expert_rules}", file=sys.stderr)
        return 2

    expert_rules = read_catalogue(args.expert_rules)
    pairs = paired_rules(args.set_dir, expert_rules)
    expert_ledger = derive_ledger(expert_rules, pairs)

    if args.emit == "ledger":
        stream = args.out.open("w", encoding="utf-8") if args.out else sys.stdout
        write_ledger(expert_ledger, stream)
        if args.out:
            stream.close()
        return 0

    if args.emit == "delta":
        if not args.api30_rules.is_dir():
            print(f"api30 rules not found: {args.api30_rules}", file=sys.stderr)
            return 2
        api30_rules = read_catalogue(args.api30_rules)
        api30_pairs = paired_rules(args.set_dir, api30_rules)
        api30_ledger = derive_ledger(api30_rules, api30_pairs)
        stream = args.out.open("w", encoding="utf-8") if args.out else sys.stdout
        write_delta(derive_delta(expert_ledger, api30_ledger), stream)
        if args.out:
            stream.close()
        return 0

    total = len(expert_ledger)
    print(f"expert catalogue : {len(expert_rules)} rules, {len(pairs)} paired with a .mop")
    print(f"clauses swept    : {total}")
    for section in ("REQUIRES", "ENSURES", "NEGATES"):
        rows = [r for r in expert_ledger if r.section == section]
        if not rows:
            continue
        counts = summarise(rows)
        print(f"  {section} ({len(rows)})")
        for disposition in sorted(counts):
            print(f"    {disposition:<26} {counts[disposition]}")
    counts = summarise(expert_ledger)
    if args.check and sum(counts.values()) != total:
        print("arithmetic does not close", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Structural, symbol, conformance and predicate gates over a specification set.

Nine gates run from one entry point, over one generated monitor and the `.mop`
directory it was generated from:

    G-2     an event whose transition row sends every state to `fail`, split by
            the CrySL clause that accounts for it (see below)
    G-2a    an event whose transition row is the identity (inert everywhere)
    G-2b'   an event that loops at the initial state
    G-2c    a state unreachable from the initial state, or an accepting state
            unreachable from it
    G-2d    the highest state index is not the `fail` category
    G-6'    the number of generated event methods differs from the number of
            transition rows (an event name that did not survive generation)
    G-ERE   a symbol named in the `ere`/`fsm` expression with no event
            declaration behind it
    G-CONF  an `Arrays.asList` allow-list that does not transcribe the
            `CONSTRAINTS ... in {...}` clause of the corresponding api30 rule
    G-PRED  a predicate site of the frozen `jca` seed that the set under test
            has lost or rewritten

Why G-2 takes the CrySL rule as a second input
----------------------------------------------
The gate as first written read every all-`fail` row as a defect and reported 18
of them on the frozen `jca`. Seventeen are correct code. A CrySL rule has four
clause families and only `ORDER` produces automaton structure; `CONSTRAINTS`,
`REQUIRES` and `FORBIDDEN` are predicates over a single call -- "this call is
wrong on these arguments", not "this call is wrong at this point in the
sequence". The natural JavaMOP encoding of such a clause is exactly an event
with a `condition()`, a report site and no place in the `ere`, and the generator
gives that event an all-`fail` row because the state is irrelevant to the
accusation. A gate that calls those 17 defects spends the reviewer's attention
on false positives and buries the one real hit.

So G-2 splits its verdict:

    orphan-with-clause      the event maps to a CONSTRAINTS/REQUIRES/FORBIDDEN
                            clause of the rule -- reported as a note, never a
                            failure, naming the rule and the clause consulted
    orphan-without-clause   no clause accounts for it -- a failure

`REQUIRES` clears only where the set still carries predicates, which the gate
decides by looking rather than by name: a set with no `ExecutionContext` has
nothing left to evaluate a `REQUIRES` clause, so only `CONSTRAINTS` and
`FORBIDDEN` clear there. Both `jca` and `jca_android` carry them (D-11), so
`REQUIRES` clears on both.

Usage:
    gh104_gates.py --monitor <MultiSpec_1RuntimeMonitor.java>
                   [--allowlist data/<set>/gate_allowlist.csv]
                   [--crysl <generated/api30>]
                   [--alias data/jca_android/alias_table.csv]
                   [--json <report.json>]

The `.mop` directory is *derived* from the set the monitor was generated from
(the `specification_set` of the run's `experiment_config.json`, or a
`gh104_set.txt` marker written next to a scratch generation), never passed: a
gate that could be pointed at a different set than the monitor came from would
compare two artefacts that never met.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# the generated monitor
# --------------------------------------------------------------------------

# The generator emits two monitor kinds and the gates must read both. A
# specification whose events all bind its parameter gets an
# AbstractAtomicMonitor; one whose events land in the empty parameter slice gets
# an AbstractSynchronizedMonitor -- exactly the shape the defective bindings
# produce, so matching only the first kind would skip them.
MONITOR_CLASS = re.compile(
    r"^(?:final )?class (\w+)Monitor extends .*Abstract(?:Atomic|Synchronized)Monitor"
)
TRANSITION = re.compile(r"static final int (\w+)_transition_(\w+)\[\]\s*=\s*\{([^}]*)\}")
EVENT_METHOD = re.compile(r"\bboolean (\w+)_event_(\w+)\s*\(")
# `...Category_fail = nextstate == 4;` in the atomic form,
# `...Category_fail = Prop_1_state == 3;` in the synchronized one.
CATEGORY = re.compile(
    r"(\w+)Monitor_(\w+)_Category_(\w+)\s*=\s*(?:nextstate|\w*_?state) == (\d+)"
)


@dataclass
class Property:
    """One property of one specification, as the generator wrote it."""

    spec: str
    prop: str
    transitions: dict[str, list[int]] = field(default_factory=dict)
    event_methods: list[str] = field(default_factory=list)
    categories: dict[str, int] = field(default_factory=dict)

    @property
    def fail_state(self) -> int | None:
        return self.categories.get("fail")

    @property
    def states(self) -> set[int]:
        seen: set[int] = set()
        for row in self.transitions.values():
            seen.update(range(len(row)))
            seen.update(row)
        seen.update(self.categories.values())
        return seen

    def reachable(self) -> set[int]:
        reached = {0}
        frontier = [0]
        while frontier:
            state = frontier.pop()
            for row in self.transitions.values():
                if state < len(row) and row[state] not in reached:
                    reached.add(row[state])
                    frontier.append(row[state])
        return reached


def parse_monitor(path: Path) -> list[Property]:
    text = path.read_text(encoding="utf-8")

    properties: dict[tuple[str, str], Property] = {}

    def slot(spec: str, prop: str) -> Property:
        key = (spec, prop)
        if key not in properties:
            properties[key] = Property(spec=spec, prop=prop)
        return properties[key]

    # The category constants are written into every event method, so the first
    # occurrence per (spec, property, category) is the definition.
    for spec, prop, category, state in CATEGORY.findall(text):
        slot(spec, prop).categories.setdefault(category, int(state))

    current: str | None = None
    for line in text.splitlines():
        if match := MONITOR_CLASS.match(line):
            current = match.group(1)
            continue
        if current is None:
            continue
        if match := TRANSITION.search(line):
            prop, event, body = match.groups()
            row = [int(value) for value in body.split(",") if value.strip()]
            slot(current, prop).transitions[event] = row
        if match := EVENT_METHOD.search(line):
            prop, event = match.groups()
            slot(current, prop).event_methods.append(event)

    return [properties[key] for key in sorted(properties)]


# --------------------------------------------------------------------------
# the .mop set
# --------------------------------------------------------------------------

SPEC_HEADER = re.compile(r"^(\w+)\s*\([^)]*\)\s*\{", re.MULTILINE)
EVENT_START = re.compile(r"\bevent\s+(\w+)\s+(before|after)\b")
LIST_LITERAL = re.compile(r"(?:List<\w+>\s+)?(\w+)\s*=\s*Arrays\.asList\s*\(")


def _match_delimiters(text: str, start: int, opening: str, closing: str) -> tuple[int, int]:
    """Index range of the balanced group whose opener is at or after `start`."""
    index = text.index(opening, start)
    depth = 0
    for position in range(index, len(text)):
        if text[position] == opening:
            depth += 1
        elif text[position] == closing:
            depth -= 1
            if depth == 0:
                return index, position
    raise ValueError(f"unbalanced {opening}{closing} from offset {index}")


def _split_top_level(text: str) -> list[str]:
    """Split on commas that are not inside brackets, parentheses or quotes."""
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    buffer: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if quote:
            buffer.append(char)
            if char == "\\":
                if index + 1 < len(text):
                    buffer.append(text[index + 1])
                    index += 1
            elif char == quote:
                quote = None
        elif char in "\"'":
            quote = char
            buffer.append(char)
        elif char in "([{":
            depth += 1
            buffer.append(char)
        elif char in ")]}":
            depth -= 1
            buffer.append(char)
        elif char == "," and depth == 0:
            parts.append("".join(buffer).strip())
            buffer = []
        else:
            buffer.append(char)
        index += 1
    tail = "".join(buffer).strip()
    if tail:
        parts.append(tail)
    return parts


@dataclass
class MopEvent:
    name: str
    kind: str
    line: int
    calls: list[str]
    args: list[str]
    condition: str | None
    body: str
    body_start: int = 0
    body_end: int = 0


@dataclass
class MopSpec:
    path: Path
    spec: str
    declarations: str
    events: list[MopEvent]
    formula_kind: str | None
    formula_text: str
    formula_line: int
    lists: dict[str, list[str]]
    text: str

    def event(self, name: str) -> MopEvent | None:
        for candidate in self.events:
            if candidate.name == name:
                return candidate
        return None

    def formula_symbols(self) -> list[tuple[str, int]]:
        """Event symbols named in the `ere`/`fsm`, with their line number."""
        if self.formula_kind is None:
            return []
        base = self.formula_line
        found: list[tuple[str, int]] = []
        if self.formula_kind == "ere":
            for match in re.finditer(r"[A-Za-z_]\w*", self.formula_text):
                if match.group(0) == "ere":
                    continue
                line = base + self.formula_text[: match.start()].count("\n")
                found.append((match.group(0), line))
        else:
            # `g1 -> s1`: the left side is an event, the right side a state.
            for match in re.finditer(r"(\w+)\s*->", self.formula_text):
                line = base + self.formula_text[: match.start()].count("\n")
                found.append((match.group(1), line))
        return found


def parse_mop(path: Path) -> MopSpec:
    text = path.read_text(encoding="utf-8")

    header = SPEC_HEADER.search(text)
    spec = header.group(1) if header else path.stem
    body_start = header.end() if header else 0

    events: list[MopEvent] = []
    for match in EVENT_START.finditer(text, body_start):
        open_brace, close_brace = _match_delimiters(text, match.end(), "{", "}")
        head = text[match.start() : open_brace]
        calls = []
        for call in re.finditer(r"\bcall\s*\(", head):
            start, end = _match_delimiters(head, call.end() - 1, "(", ")")
            calls.append(head[start + 1 : end].strip())
        args: list[str] = []
        if args_match := re.search(r"&&\s*args\s*\(", head) or re.search(r"\bargs\s*\(", head):
            start, end = _match_delimiters(head, args_match.end() - 1, "(", ")")
            args = [part.strip() for part in _split_top_level(head[start + 1 : end])]
        condition = None
        if cond_match := re.search(r"\bcondition\s*\(", head):
            start, end = _match_delimiters(head, cond_match.end() - 1, "(", ")")
            condition = head[start + 1 : end].strip()
        events.append(
            MopEvent(
                name=match.group(1),
                kind=match.group(2),
                line=text[: match.start()].count("\n") + 1,
                calls=calls,
                args=args,
                condition=condition,
                body=text[open_brace + 1 : close_brace],
                body_start=text[: open_brace].count("\n") + 1,
                body_end=text[: close_brace].count("\n") + 1,
            )
        )

    formula_kind: str | None = None
    formula_text = ""
    formula_line = 0
    if formula := re.search(r"^[ \t]*(ere|fsm)\s*:", text, re.MULTILINE):
        formula_kind = formula.group(1)
        formula_line = text[: formula.start()].count("\n") + 1
        tail = text[formula.end() :]
        stop = re.search(r"\n\s*(?:@|alias\b)", tail)
        formula_text = tail[: stop.start()] if stop else tail

    lists: dict[str, list[str]] = {}
    for match in LIST_LITERAL.finditer(text):
        start, end = _match_delimiters(text, match.end() - 1, "(", ")")
        raw = _split_top_level(text[start + 1 : end])
        lists[match.group(1)] = [item.strip().strip('"') for item in raw]

    first_event = min((event.line for event in events), default=None)
    declarations = ""
    if first_event is not None:
        lines = text.splitlines()
        start_line = text[:body_start].count("\n")
        declarations = "\n".join(lines[start_line : first_event - 1])

    return MopSpec(
        path=path,
        spec=spec,
        declarations=declarations,
        events=events,
        formula_kind=formula_kind,
        formula_text=formula_text,
        formula_line=formula_line,
        lists=lists,
        text=text,
    )


def parse_set(directory: Path) -> dict[str, MopSpec]:
    """Every `.mop` of a set, keyed by the specification name it declares."""
    specs: dict[str, MopSpec] = {}
    for path in sorted(directory.glob("*.mop")):
        parsed = parse_mop(path)
        specs[parsed.spec] = parsed
    return specs


# --------------------------------------------------------------------------
# the api30 CrySL rules
# --------------------------------------------------------------------------

SECTIONS = (
    "SPEC",
    "OBJECTS",
    "FORBIDDEN",
    "EVENTS",
    "ORDER",
    "CONSTRAINTS",
    "REQUIRES",
    "ENSURES",
    "NEGATES",
)


@dataclass
class CryslRule:
    path: Path
    sections: dict[str, list[tuple[int, str]]]
    events: dict[str, tuple[str, list[str]]]
    objects: dict[str, str]

    def clauses(self, section: str) -> list[tuple[int, str]]:
        return self.sections.get(section, [])


def parse_crysl(path: Path) -> CryslRule:
    sections: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    buffer: list[str] = []
    buffer_line = 0

    def flush() -> None:
        nonlocal buffer, buffer_line
        clause = " ".join(part.strip() for part in buffer).strip().strip(";").strip()
        if current and clause:
            sections.setdefault(current, []).append((buffer_line, clause))
        buffer = []

    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        head = line.rstrip(":").strip()
        if head in SECTIONS:
            flush()
            current = head
            continue
        if not line:
            continue
        if not buffer:
            buffer_line = number
        buffer.append(line)
        if line.endswith(";"):
            flush()
    flush()

    # `g1: getInstance(alg);`, `k1: kp = generateKeyPair();`, `Cons := c1 | c2;`
    events: dict[str, tuple[str, list[str]]] = {}
    for _, clause in sections.get("EVENTS", []):
        if ":=" in clause or ":" not in clause:
            continue
        label, expression = clause.split(":", 1)
        expression = expression.strip()
        if "=" in expression.split("(", 1)[0]:
            expression = expression.split("=", 1)[1].strip()
        call = re.match(r"([\w.]+)\s*\((.*)\)\s*$", expression)
        if not call:
            continue
        name = call.group(1).split(".")[-1]
        params = [part.strip() for part in _split_top_level(call.group(2)) if part.strip()]
        events[label.strip()] = (name, params)

    # `java.security.spec.AlgorithmParameterSpec params;` -> params: AlgorithmParameterSpec
    objects: dict[str, str] = {}
    for _, clause in sections.get("OBJECTS", []):
        declaration = clause.split()
        if len(declaration) >= 2:
            objects[declaration[-1]] = declaration[0].split(".")[-1]

    return CryslRule(path=path, sections=sections, events=events, objects=objects)


def rule_for(spec: str, crysl_dir: Path) -> CryslRule | None:
    """`IvParameterSpecSpec` -> `IvParameterSpec.cryptsl`; `SecretKeySpec` -> `SecretKey`."""
    candidates = [spec]
    if spec.endswith("Spec"):
        candidates.append(spec[: -len("Spec")])
    for name in candidates[1:] + candidates[:1]:
        path = crysl_dir / f"{name}.cryptsl"
        if path.is_file():
            return parse_crysl(path)
    return None


# --------------------------------------------------------------------------
# the allowlist
# --------------------------------------------------------------------------


@dataclass
class AllowRow:
    gate: str
    spec: str
    target: str
    verdict: str
    clause: str
    reason: str


class Allowlist:
    """`data/<set>/gate_allowlist.csv`; `*` matches any spec or target.

    Two columns beyond the shared schema carry G-2's clause mapping: `verdict`
    (`orphan-with-clause` / `orphan-without-clause`) and `clause` (the api30
    file, line and text that cleared it). They are optional, so a file written
    to the shared six-column schema still reads.
    """

    def __init__(self, rows: list[AllowRow]):
        self.rows = rows

    @classmethod
    def load(cls, path: Path | None) -> "Allowlist":
        if path is None or not path.is_file():
            return cls([])
        rows: list[AllowRow] = []
        with path.open(encoding="utf-8", newline="") as handle:
            for raw in csv.DictReader(handle):
                rows.append(
                    AllowRow(
                        gate=(raw.get("gate") or "").strip(),
                        spec=(raw.get("spec") or "*").strip() or "*",
                        target=(raw.get("event_or_state") or raw.get("event") or "*").strip()
                        or "*",
                        verdict=(raw.get("verdict") or "").strip(),
                        clause=(raw.get("clause") or "").strip(),
                        reason=(raw.get("reason") or "").strip(),
                    )
                )
        return cls(rows)

    def find(self, gate: str, spec: str, target: str) -> AllowRow | None:
        for row in self.rows:
            if row.gate != gate:
                continue
            if row.spec not in ("*", spec):
                continue
            if row.target not in ("*", target):
                continue
            return row
        return None


# --------------------------------------------------------------------------
# G-2: the orphan split
# --------------------------------------------------------------------------

# Both substrates, because gh105 migrates the successor set one file at a time:
# for the length of that change a set legitimately holds `ExecutionContext` sites
# and `PredicateStore` sites at once, and a gate that knew only the first would
# report the half it was taught about as the whole (INV-INS-141). The frozen `jca`
# only ever holds the first, so nothing about its verdicts moves.
PREDICATE_CALL = re.compile(
    r"(?:ExecutionContext|PredicateStore)\s*\.\s*instance\s*\(\s*\)\s*\.\s*validate\s*"
    r"\(\s*Property\s*\.\s*(\w+)\s*,\s*(\w+)"
)


def _normalise(name: str) -> str:
    return name.replace("_", "").replace("-", "").lower()


def _call_signature(call: str) -> tuple[str, list[str]] | None:
    """`public IvParameterSpec.new(byte[])` -> ("IvParameterSpec", ["byte[]"])."""
    match = re.search(r"([\w.$\[\]]+)\s*\(([^()]*)\)\s*$", call.strip())
    if not match:
        return None
    qualified = match.group(1)
    params = [part.strip() for part in _split_top_level(match.group(2)) if part.strip()]
    parts = qualified.split(".")
    method = parts[-1]
    if method == "new":
        method = parts[-2] if len(parts) > 1 else method
    return method, params


def _crysl_params(
    rule: CryslRule, method: str, arity: int, declared: list[str] | None = None
) -> list[str] | None:
    """The parameter names of the CrySL event that binds the same call.

    A rule may declare several events with one method name and one arity --
    `KeyPairGenerator` has `i1: initialize(params)` and `i3: initialize(keySize)`
    -- so the declared Java parameter types of the pointcut break the tie
    against the types of `OBJECTS`. Without that, `initialize(int)` would be
    read against `AlgorithmParameterSpec params` and no clause would be found
    for a guard that constrains the key size.
    """
    candidates = [params for name, params in rule.events.values() if name == method]
    if not candidates:
        return None
    exact = [params for params in candidates if len(params) == arity]
    pool = exact or sorted((p for p in candidates if len(p) >= arity), key=len) or candidates
    if len(pool) == 1 or not declared:
        return pool[0]

    def score(params: list[str]) -> int:
        agreed = 0
        for index, param in enumerate(params):
            if index >= len(declared):
                break
            wanted = _simple_type(declared[index]).lower()
            if wanted in ("", "..", "*"):
                continue
            if param == "_":
                continue
            if _simple_type(rule.objects.get(param, "")).lower() == wanted:
                agreed += 1
        return agreed

    return max(pool, key=score)


def _clause_hit(rule: CryslRule, sections: tuple[str, ...], needle: str) -> tuple[str, int, str] | None:
    pattern = re.compile(rf"\b{re.escape(needle)}\b")
    for section in sections:
        for line, clause in rule.clauses(section):
            if pattern.search(clause):
                return section, line, clause
    return None


def _predicate_hit(
    rule: CryslRule, sections: tuple[str, ...], predicate: str, obj: str
) -> tuple[str, int, str] | None:
    for section in sections:
        for line, clause in rule.clauses(section):
            for match in re.finditer(r"(\w+)\s*\[([^\]]*)\]", clause):
                if _normalise(match.group(1)) != _normalise(predicate):
                    continue
                operands = [part.strip() for part in match.group(2).split(",")]
                if obj in operands:
                    return section, line, clause
    return None


def _forbidden_hit(rule: CryslRule, method: str, params: list[str]) -> tuple[str, int, str] | None:
    """A FORBIDDEN clause naming the very constructor or method the event binds."""
    wanted = (method, [_simple_type(param) for param in params])
    for line, clause in rule.clauses("FORBIDDEN"):
        head = clause.split("=>", 1)[0].strip()
        signature = _call_signature(head)
        if signature is None:
            continue
        name, declared = signature
        if (name, [_simple_type(part) for part in declared]) == wanted:
            return "FORBIDDEN", line, clause
    return None


def _simple_type(declared: str) -> str:
    token = declared.strip().split()[0] if declared.strip() else ""
    return token.split(".")[-1]


def classify_orphan(
    mop: MopSpec, event: MopEvent, rule: CryslRule | None, accept_requires: bool
) -> dict:
    """`orphan-with-clause` (a note) or `orphan-without-clause` (a failure)."""
    sections = ("CONSTRAINTS", "FORBIDDEN") + (("REQUIRES",) if accept_requires else ())
    verdict = {
        "spec": mop.spec,
        "event": event.name,
        "file": str(mop.path),
        "line": event.line,
        "rule": str(rule.path) if rule else None,
        "verdict": "orphan-without-clause",
        "clause": "",
        "why": "",
    }
    if rule is None:
        verdict["why"] = "no api30 rule corresponds to this specification"
        return verdict

    signature = _call_signature(event.calls[0]) if event.calls else None
    if signature is None:
        verdict["why"] = "the event declares no `call(...)` pointcut"
        return verdict
    method, declared = signature

    if not event.condition:
        # No guard: only a FORBIDDEN clause naming this very call accounts for
        # an event that accuses on sight.
        hit = _forbidden_hit(rule, method, declared)
        if hit:
            section, line, clause = hit
            verdict.update(
                verdict="orphan-with-clause",
                clause=f"{rule.path.name}:{line} {section} {clause}",
                why="no condition(); the rule forbids this call outright",
            )
        else:
            verdict["why"] = "no condition() and no FORBIDDEN clause names this call"
        return verdict

    params = _crysl_params(rule, method, len(event.args), declared)
    if params is None:
        verdict["why"] = f"no CrySL event of {rule.path.name} binds {method}(...)"
        return verdict

    def crysl_object(argument: str) -> str | None:
        if argument not in event.args:
            return None
        index = event.args.index(argument)
        if index >= len(params):
            return None
        name = params[index].strip()
        return None if name in ("_", "") else name.split()[-1]

    # The guard *and* the body. gh105's F2 pass moves every predicate read out of
    # `condition(...)` and into the event body, where a failed read can accuse
    # about what it saw instead of suppressing the transition (INV-INS-133). A
    # classifier that read only the guard would call every migrated event an
    # orphan without a clause -- the clause did not go away, it moved.
    guard = f"{event.condition or ''}\n{event.body or ''}"
    predicates = PREDICATE_CALL.findall(guard)
    consumed = {argument for _, argument in predicates}
    for predicate, argument in predicates:
        obj = crysl_object(argument)
        if obj is None:
            continue
        hit = _predicate_hit(rule, sections, predicate, obj)
        if hit:
            section, line, clause = hit
            verdict.update(
                verdict="orphan-with-clause",
                clause=f"{rule.path.name}:{line} {section} {clause}",
                why=f"the event tests Property.{predicate} on {argument} -> {obj}",
            )
            return verdict

    # Anything else the guard reads is a value constraint: it clears when a
    # CONSTRAINTS (or FORBIDDEN) clause of the rule constrains the same object.
    for argument in event.args:
        if argument in consumed or not re.fullmatch(r"\w+", argument):
            continue
        if not re.search(rf"\b{re.escape(argument)}\b", guard):
            continue
        obj = crysl_object(argument)
        if obj is None:
            continue
        hit = _clause_hit(rule, ("CONSTRAINTS", "FORBIDDEN"), obj)
        if hit:
            section, line, clause = hit
            verdict.update(
                verdict="orphan-with-clause",
                clause=f"{rule.path.name}:{line} {section} {clause}",
                why=f"condition() constrains {argument} -> {obj}",
            )
            return verdict

    tested = ", ".join(sorted(consumed | {a for a in event.args if re.fullmatch(r"\w+", a)}))
    verdict["why"] = (
        f"no {'/'.join(sections)} clause of {rule.path.name} constrains "
        f"what the condition() tests ({tested or 'nothing nameable'})"
    )
    return verdict


# --------------------------------------------------------------------------
# G-CONF: allow-list conformance
# --------------------------------------------------------------------------

IN_SET = re.compile(r"(\w+)\s+in\s*\{([^}]*)\}")
JAVA_LIST = re.compile(r"(?:List<String>\s+)?(\w+)\s*=\s*(?:Arrays\.asList|new String\[\]\s*\{)")


def read_java_lists(path: Path) -> dict[str, list[str]]:
    """The string lists a Java utility declares, one regex per literal.

    Fails closed: a literal the regex does not find raises rather than yielding
    an empty list, because an empty allow-list silently conforms to nothing.
    """
    text = path.read_text(encoding="utf-8")
    lists: dict[str, list[str]] = {}
    for match in JAVA_LIST.finditer(text):
        opener = "(" if "asList" in match.group(0) else "{"
        closer = ")" if opener == "(" else "}"
        start, end = _match_delimiters(text, match.end() - 1, opener, closer)
        items = [item.strip().strip('"') for item in _split_top_level(text[start + 1 : end])]
        lists[match.group(1)] = [item for item in items if item]
    if not lists:
        raise ValueError(f"no string-array or Arrays.asList literal found in {path}")
    return lists


def load_aliases(path: Path | None) -> dict[tuple[str, str], str]:
    """`(service, alias) -> canonical` from the auditable registry, not from code."""
    if path is None or not path.is_file():
        return {}
    aliases: dict[tuple[str, str], str] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            service = (row.get("service") or "").strip()
            alias = (row.get("alias") or "").strip()
            canonical = (row.get("canonical") or "").strip()
            if alias and canonical:
                aliases[(service, _normalise(alias))] = canonical
    return aliases


def allow_list_of(mop: MopSpec) -> tuple[str, list[str]] | None:
    """The allow-list a specification actually guards its events with."""
    if not mop.lists:
        return None
    used = [name for name in mop.lists if f"{name}.contains(" in mop.text]
    name = used[0] if used else next(iter(mop.lists))
    return name, mop.lists[name]


def _relation(clause: str) -> bool:
    return bool(re.search(r"(>=|<=|==|>|<)", clause)) and " in " not in clause


def _list_guarding(mop: MopSpec, rule: CryslRule, obj: str) -> tuple[str, list[str]] | None:
    """The `Arrays.asList` a specification guards a CrySL object with.

    The link is the pointcut, not the name: the event's `call(...)` is matched
    to the CrySL event, `args(...)` gives the position, the position gives the
    object, and the event's `condition()` names the list it tests that argument
    against. A specification and a rule are free to spell the same argument
    differently (`alg` against `randAlg`), so nothing here compares identifiers.
    """
    for event in mop.events:
        if not event.calls or not event.condition:
            continue
        signature = _call_signature(event.calls[0])
        if signature is None:
            continue
        method, declared = signature
        params = _crysl_params(rule, method, len(event.args), declared)
        if not params:
            continue
        for index, argument in enumerate(event.args):
            if index >= len(params) or params[index] != obj:
                continue
            # Two shapes guard an argument against a list: the seed's
            # `algorithms.contains(alg)` and the successor set's
            # `ConscryptAliasTable.matches("Service", alg, algorithms)`, which
            # applies the alias table before the membership test (INV-INS-112).
            for pattern in (
                rf"(\w+)\s*\.contains\(\s*{re.escape(argument)}\b",
                rf"ConscryptAliasTable\s*\.\s*matches\(\s*\"[^\"]*\"\s*,\s*"
                rf"{re.escape(argument)}\s*(?:\.\w+\(\))?\s*,\s*(\w+)",
            ):
                hit = re.search(pattern, event.condition)
                if hit and hit.group(1) in mop.lists:
                    return hit.group(1), mop.lists[hit.group(1)]
    return None


def _argument_binding(mop: MopSpec, event: MopEvent, rule: CryslRule) -> dict[str, str]:
    """CrySL object name -> the argument the event's pointcut binds it to."""
    if not event.calls:
        return {}
    signature = _call_signature(event.calls[0])
    if signature is None:
        return {}
    method, declared = signature
    params = _crysl_params(rule, method, len(event.args), declared)
    if not params:
        return {}
    return {
        param: event.args[index]
        for index, param in enumerate(params)
        if index < len(event.args) and param != "_"
    }


def _switch_case(mop: MopSpec, value: str) -> tuple[int, list[str]] | None:
    """`case "RSA": return Arrays.asList(4096, 3072, 2048).contains(keySize);`"""
    for number, line in enumerate(mop.text.splitlines(), start=1):
        if not re.search(rf'case\s+"{re.escape(value)}"\s*:', line):
            continue
        literals = re.findall(r"\b(\d+)\b", line.split(":", 1)[1])
        return number, literals
    return None


def constraint_rows(
    specs: dict[str, MopSpec],
    crysl_dir: Path,
    aliases: dict[tuple[str, str], str],
    cipher_util: Path | None,
) -> list[dict]:
    """One row per api30 `CONSTRAINTS` clause, plus the set's unbacked lists.

    Verdict vocabulary (the `constraint_table.csv` schema):
      IGUAL                   the two sets agree under the normalisation rule
      MOP-MAIS-PERMISSIVO     the specification admits values the rule does not
      MOP-MAIS-RESTRITIVO     the rule admits values the specification does not
      DIVERGENTE              both directions at once
      MOP-SEM-BASE            the specification guards a list no clause backs
      CRYSL-NAO-IMPLEMENTADO  the clause reaches no guard of the specification

    A seventh value, `NAO-DERIVADO`, is this gate's own and never appears in the
    record: it marks a clause whose mapping to the specification is a reading of
    Java control flow rather than a parse -- every `part(0,"/",transformation)`
    clause of the `Cipher` rule, which the record maps to line ranges of
    `CipherTransformationUtil.java` by hand. Marking them is what keeps the
    agreement figure honest: the gate does not agree with a record it did not
    reproduce.
    """
    rows: list[dict] = []
    for spec, mop in sorted(specs.items()):
        rule = rule_for(spec, crysl_dir)
        if rule is None:
            continue
        service = rule.path.stem
        matched: set[str] = set()

        for line, clause in rule.clauses("CONSTRAINTS"):
            row = {
                "spec": spec,
                "cryptsl_line": f"{service}.cryptsl:{line}",
                "mop_line": "",
                "verdict": "CRYSL-NAO-IMPLEMENTADO",
                "clause": clause,
            }

            if "part(" in clause:
                # The Cipher transformation tables live in Java control flow
                # (D-b), and the record maps each clause to a line range of it
                # by hand. The gate reads the lists (below) but does not claim
                # to have re-derived that mapping.
                row["verdict"] = "NAO-DERIVADO"
                row["mop_line"] = cipher_util.name if cipher_util else ""
                rows.append(row)
                continue

            implication = re.match(r"(.+?)\s*=>\s*(.+)$", clause)
            if implication:
                left = IN_SET.search(implication.group(1))
                right = IN_SET.search(implication.group(2))
                if left and right:
                    wanted = {
                        item.strip().strip('"')
                        for item in _split_top_level(right.group(2))
                        if item.strip()
                    }
                    for guard in _split_top_level(left.group(2)):
                        case = _switch_case(mop, guard.strip().strip('"'))
                        if case is None:
                            continue
                        number, literals = case
                        row["mop_line"] = f"{mop.path.name}:{number}"
                        row["verdict"] = _compare(set(literals), wanted, service, aliases)
                        break
                rows.append(row)
                continue

            in_set = IN_SET.search(clause)
            if in_set:
                obj = in_set.group(1)
                wanted = {
                    item.strip().strip('"')
                    for item in _split_top_level(in_set.group(2))
                    if item.strip()
                }
                guarding = _list_guarding(mop, rule, obj)
                if guarding:
                    matched.add(guarding[0])
                    row["mop_line"] = f"{mop.path.name}:{_line_of(mop, guarding[0])}"
                    row["verdict"] = _compare(set(guarding[1]), wanted, service, aliases)
                rows.append(row)
                continue

            if _relation(clause):
                # A numeric bound is implemented when some guard states the same
                # relation; the record calls that IGUAL and nothing finer.
                operands = [
                    name for name in re.findall(r"[A-Za-z_]\w*", clause) if name in rule.objects
                ]
                bound = re.search(r"(>=|<=|==|>|<)\s*(\d+)", clause)
                for event in mop.events:
                    if not event.condition:
                        continue
                    if bound and bound.group(0).replace(" ", "") in event.condition.replace(" ", ""):
                        row["verdict"] = "IGUAL"
                        row["mop_line"] = f"{mop.path.name}:{event.line}"
                        break
                    # The rule and the specification spell the same argument
                    # differently (`off` against `offset`), so the operands are
                    # mapped through the pointcut before being looked for.
                    binding = _argument_binding(mop, event, rule)
                    if not bound and operands and all(
                        name in binding
                        and re.search(rf"\b{re.escape(binding[name])}\b", event.condition)
                        for name in operands
                    ):
                        row["verdict"] = "IGUAL"
                        row["mop_line"] = f"{mop.path.name}:{event.line}"
                        break
            rows.append(row)

        # A list the specification guards with and no clause backs.
        for name in sorted(mop.lists):
            if name in matched:
                continue
            if f"{name}.contains(" not in mop.text:
                continue
            rows.append(
                {
                    "spec": spec,
                    "cryptsl_line": "",
                    "mop_line": f"{mop.path.name}:{_line_of(mop, name)}",
                    "verdict": "MOP-SEM-BASE",
                    "clause": f"`{name}` guards calls no CONSTRAINTS clause reaches",
                }
            )

    return rows


def _compare(
    declared: set[str], wanted: set[str], service: str, aliases: dict[tuple[str, str], str]
) -> str:
    left = {_canonical(service, value, aliases) for value in declared}
    right = {_canonical(service, value, aliases) for value in wanted}
    extra, missing = left - right, right - left
    if not extra and not missing:
        return "IGUAL"
    if extra and missing:
        return "DIVERGENTE"
    return "MOP-MAIS-PERMISSIVO" if extra else "MOP-MAIS-RESTRITIVO"


def _canonical(service: str, value: str, aliases: dict[tuple[str, str], str]) -> str:
    """The declared normalisation rule: case-insensitive, plus the alias table.

    Case and nothing else. Folding separators away as well would silently equate
    `SHA256` with `SHA-256`, which is exactly the equality the alias table is
    there to record with a primary-source pointer -- an unrecorded equality is
    the failure mode this whole conformance record exists to prevent.
    """
    key = value.strip().lower()
    canonical = aliases.get((service, _normalise(value))) or aliases.get(("", _normalise(value)))
    return canonical.strip().lower() if canonical else key


def _line_of(mop: MopSpec, name: str) -> int:
    for number, line in enumerate(mop.text.splitlines(), start=1):
        if re.search(rf"\b{re.escape(name)}\b\s*=", line):
            return number
    return 0


# --------------------------------------------------------------------------
# G-PRED
# --------------------------------------------------------------------------

# INV-INS-128 names the identifier `ExecutionContext`, not the bare `validate(`:
# `KeyPairGeneratorSpec` keeps a local `private boolean validate(int)` that has
# nothing to do with the predicate architecture.
PREDICATE_MARKER = "ExecutionContext"


def predicate_sites(text: str) -> list[str]:
    """The file's predicate lines, in the order it declares them."""
    return [line for line in text.splitlines() if PREDICATE_MARKER in line]


def predicate_divergences(specs: dict[str, MopSpec], seed: Path | None) -> list[dict]:
    """G-PRED: what the set under test lost or rewrote against the frozen seed.

    The gate compares sequences, not counts. A set that moved a `validate(` from
    the event reading a key to the event writing it keeps its grep count and has
    changed what it accuses, so an equal-totals check would wave it through.

    The seed is its own oracle, which makes the gate trivially green on `jca` --
    that is the intended reading: `jca` is frozen, so nothing there can drift, and
    the gate exists for the sets derived from it.
    """
    if seed is None:
        return []
    hits: list[dict] = []
    for spec, mop in sorted(specs.items()):
        counterpart = seed / mop.path.name
        if not counterpart.is_file():
            continue
        want = predicate_sites(counterpart.read_text(encoding="utf-8"))
        got = predicate_sites(mop.text)
        if want == got:
            continue
        lost = [line.strip() for line in want if line not in got]
        hits.append(
            {
                "spec": spec,
                "file": mop.path.name,
                "seed_sites": len(want),
                "set_sites": len(got),
                "lost": lost[:10],
            }
        )
    return hits


# --------------------------------------------------------------------------
# the gate suite
# --------------------------------------------------------------------------


def derive_set(monitor: Path) -> tuple[str | None, Path | None]:
    """The set the monitor was generated from, and its `.mop` directory.

    A run directory carries `experiment_config.json` with `specification_set`; a
    scratch generation carries a `gh104_set.txt` naming the directory it was
    generated from. Nothing is passed on the command line, because a gate that
    could be pointed at a set the monitor did not come from would compare two
    artefacts that never met.
    """
    for parent in [monitor.parent, *monitor.parents]:
        marker = parent / "gh104_set.txt"
        if marker.is_file():
            named = marker.read_text(encoding="utf-8").strip()
            path = Path(named)
            if path.is_dir():
                return path.name, path
        config = parent / "experiment_config.json"
        if config.is_file():
            name = json.loads(config.read_text(encoding="utf-8")).get("specification_set")
            if name:
                return name, resolve_set_dir(name)
    return None, None


def resolve_set_dir(name: str) -> Path | None:
    home = os.environ.get("RVSEC_HOME")
    if not home:
        return None
    path = Path(home) / "rvsec/rvsec-mop/src/main/resources" / name
    return path if path.is_dir() else None


CIPHER_UTILS = {
    "jca": "CipherTransformationUtil.java",
    "jca_android": "Api30CipherTransformationUtil.java",
    "jca_android_bug_predicate": "AndroidCipherTransformationUtil.java",
}


def cipher_util_for(set_name: str | None) -> tuple[Path | None, str | None]:
    """The Java utility that holds this set's Cipher transformation lists."""
    name = CIPHER_UTILS.get(set_name or "")
    home = os.environ.get("RVSEC_HOME")
    if name is None or not home:
        return None, (
            f"no Cipher transformation utility is declared for set {set_name!r}"
            if name is None
            else "RVSEC_HOME is not set, so the Cipher utility cannot be located"
        )
    path = Path(home) / "rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util" / name
    if not path.is_file():
        return None, f"the Cipher transformation utility {name} does not exist yet at {path}"
    return path, None


def read_records(set_dir_name: str, repo: Path) -> dict[str, list[dict]]:
    """The two records a divergence must be backed by, keyed by specification.

    `divergence_record.csv` carries the `api30-omits` half of the asymmetric
    rule -- a value the successor list keeps that the api30 rule omits, which is
    the only kind of divergence that needs its own entry. The `api30-admits`
    half needs none: a value the rule admits is simply accepted, and its cost is
    recorded in `conformance_record.csv` as a consequence, together with every
    `deferred-constant` and narrowing note.
    """
    records: dict[str, list[dict]] = {}
    for name in ("divergence_record.csv", "conformance_record.csv"):
        path = repo / "data" / set_dir_name / name
        if not path.is_file():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                key = (row.get("mop_file") or row.get("file") or "").strip()
                spec = Path(key).stem.replace(".mop", "") if key else ""
                records.setdefault(spec, []).append({**row, "record": name})
    return records


def backing_record(row: dict, records: dict[str, list[dict]]) -> str:
    """The record entry that accounts for one clause-level difference, or `unbacked`.

    The match is by the CrySL object the clause constrains (`rule_object`) or by the
    clause text the set declares it does not implement (`absent_from_mop`) -- not by
    specification name. A record row for the specification says nothing about *this*
    clause, and accepting it would make the gate agree with any record that mentions
    the file at all.
    """
    clause = row.get("clause", "")
    constrained = IN_SET.search(clause)
    obj = constrained.group(1) if constrained else ""
    for spec in (row["spec"], row["spec"].removesuffix("Spec")):
        for entry in records.get(spec, []):
            if obj and entry.get("rule_object", "").strip() == obj:
                return f"{entry['record']}: {entry.get('verdict', '').strip()}"
            absent = entry.get("absent_from_mop", "").strip()
            if absent and absent not in ("-", "") and absent in clause:
                return f"{entry['record']}: {entry.get('verdict', '').strip()}"
            if entry.get("kind", "").strip() == "api30-omits" and obj:
                return f"{entry['record']}: api30-omits"
    return "unbacked"


def read_constraint_table(path: Path | None) -> list[dict] | None:
    """The committed oracle `data/jca_android/constraint_table.csv`, or None.

    A header-only file is not an oracle: it is the record before the task that
    fills it has landed, and G-CONF names that as a skip rather than declaring
    a zero-row agreement.
    """
    if path is None or not path.is_file():
        return None
    with path.open(encoding="utf-8", newline="") as handle:
        rows = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]
    return rows or None


def run_gates(
    monitor: Path,
    allowlist: Allowlist,
    crysl_dir: Path | None,
    alias_csv: Path | None,
    cipher_util: Path | None,
    constraint_table: Path | None = None,
) -> dict:
    set_name, set_dir = derive_set(monitor)
    specs = parse_set(set_dir) if set_dir else {}
    properties = parse_monitor(monitor)
    # A set carries REQUIRES clauses when its specifications read predicates at
    # all -- on either substrate, because gh105 replaces one with the other file by
    # file and the flag must not flip halfway through the migration.
    accept_requires = bool(specs) and any(
        "ExecutionContext" in mop.text or "PredicateStore" in mop.text
        for mop in specs.values()
    )

    report: dict = {
        "monitor": str(monitor),
        "set": set_name,
        "set_dir": str(set_dir) if set_dir else None,
        "crysl_dir": str(crysl_dir) if crysl_dir else None,
        "requires_clears": accept_requires,
        "gates": {},
        "skipped": [],
    }

    def gate(name: str, hits: list[dict], notes: list[dict] | None = None) -> None:
        failures = []
        allowlisted = []
        for hit in hits:
            row = allowlist.find(name, hit.get("spec", "*"), str(hit.get("event") or hit.get("state") or "*"))
            if row and row.reason:
                allowlisted.append({**hit, "allowlisted": row.reason})
            else:
                failures.append(hit)
        report["gates"][name] = {
            "hits": hits,
            "notes": notes or [],
            "allowlisted": allowlisted,
            "failures": failures,
            "count": len(hits),
        }

    # ---- the structural family, read off the generated transition tables ----
    orphan_raw: list[tuple[Property, str]] = []
    inertia: list[dict] = []
    redundant: list[dict] = []
    dead: list[dict] = []
    sink: list[dict] = []
    injectivity: list[dict] = []

    for prop in properties:
        fail = prop.fail_state
        reachable = prop.reachable()
        highest = max(prop.states) if prop.states else 0

        for event, row in sorted(prop.transitions.items()):
            if not row:
                continue
            if fail is not None and all(value == fail for value in row):
                orphan_raw.append((prop, event))
            if all(row[index] == index for index in range(len(row))):
                inertia.append({"spec": prop.spec, "event": event, "row": row})
            if row[0] == 0:
                redundant.append({"spec": prop.spec, "event": event, "row": row})

        unreachable = sorted(state for state in prop.states if state not in reachable)
        accepting = [
            state for name, state in prop.categories.items() if name.startswith("match")
        ]
        unreachable_accepting = sorted(set(accepting) - reachable)
        if unreachable or unreachable_accepting:
            dead.append(
                {
                    "spec": prop.spec,
                    "state": str(unreachable or unreachable_accepting),
                    "unreachable": unreachable,
                    "unreachable_accepting": unreachable_accepting,
                }
            )

        if fail is None or highest != fail:
            sink.append(
                {
                    "spec": prop.spec,
                    "state": str(highest),
                    "highest": highest,
                    "fail": fail,
                    "reason": "no `fail` category" if fail is None else "the sink is not `fail`",
                }
            )

        if len(prop.event_methods) != len(prop.transitions):
            injectivity.append(
                {
                    "spec": prop.spec,
                    "event": "*",
                    "event_methods": len(prop.event_methods),
                    "transition_rows": len(prop.transitions),
                    "dropped": sorted(set(prop.event_methods) - set(prop.transitions)),
                }
            )

    # ---- G-2 ----
    if crysl_dir is None or not crysl_dir.is_dir():
        report["skipped"].append("G-2: --crysl not given, the orphan split has no second input")
        gate("G-2", [{"spec": prop.spec, "event": event} for prop, event in orphan_raw])
    else:
        notes: list[dict] = []
        failures_raw: list[dict] = []
        for prop, event in orphan_raw:
            mop = specs.get(prop.spec)
            if mop is None:
                failures_raw.append(
                    {
                        "spec": prop.spec,
                        "event": event,
                        "verdict": "orphan-without-clause",
                        "why": "the specification source was not found in the derived set directory",
                    }
                )
                continue
            declared = mop.event(event)
            if declared is None:
                failures_raw.append(
                    {
                        "spec": prop.spec,
                        "event": event,
                        "verdict": "orphan-without-clause",
                        "why": f"no `event {event}` in {mop.path.name}",
                    }
                )
                continue
            verdict = classify_orphan(
                mop, declared, rule_for(prop.spec, crysl_dir), accept_requires
            )
            row = allowlist.find("G-2", prop.spec, event)
            if row and row.verdict and row.verdict != verdict["verdict"]:
                verdict["disagreement"] = (
                    f"the allowlist calls this {row.verdict}, the classifier {verdict['verdict']}"
                )
            if verdict["verdict"] == "orphan-with-clause":
                notes.append(verdict)
            else:
                failures_raw.append(verdict)
        gate("G-2", failures_raw, notes)
        report["gates"]["G-2"]["orphans_raw"] = len(orphan_raw)

    gate("G-2a", inertia)
    gate("G-2b'", redundant)
    gate("G-2c", dead)
    gate("G-2d", sink)
    gate("G-6'", injectivity)

    # ---- G-ERE ----
    undeclared: list[dict] = []
    if specs:
        for spec, mop in sorted(specs.items()):
            names = {event.name for event in mop.events}
            for symbol, line in mop.formula_symbols():
                if symbol not in names:
                    undeclared.append(
                        {
                            "spec": spec,
                            "event": symbol,
                            "file": mop.path.name,
                            "line": line,
                            "declared": sorted(names),
                        }
                    )
    else:
        report["skipped"].append("G-ERE: the set directory could not be derived from the monitor")
    gate("G-ERE", undeclared)

    # ---- G-CONF ----
    if not specs or crysl_dir is None or not crysl_dir.is_dir():
        report["skipped"].append("G-CONF: needs both the set directory and --crysl")
        gate("G-CONF", [])
    else:
        # D-b keeps the Cipher transformation lists in Java, one utility per set:
        # each set selects its own by name, so no runtime state can put one
        # set's verdict under the control of another's table (INV-INS-112).
        if cipher_util is None:
            cipher_util, missing = cipher_util_for(set_name)
            if missing:
                report["skipped"].append(f"G-CONF: {missing}")
        aliases = load_aliases(alias_csv)
        if alias_csv is not None and not aliases:
            report["skipped"].append(
                f"G-CONF: {alias_csv} carries no alias row; comparison is case-insensitive only"
            )
        try:
            rows = constraint_rows(specs, crysl_dir, aliases, cipher_util)
        except ValueError as error:  # a Java literal the extraction could not find
            report["skipped"].append(f"G-CONF: {error}")
            rows = []
        # The frozen `jca` is a report, not an assertion: its lists were written
        # by hand against the Java SE providers and every divergence from api30
        # is the measurement this change exists to explain.
        hits = [] if set_name == "jca" else [
            row for row in rows if row["verdict"] not in ("IGUAL", "NAO-DERIVADO")
        ]
        # `constraint_table.csv` records the clause-by-clause comparison of the
        # api30 rules against the **seed**, so it is an oracle for `jca` and for
        # nothing else. Reading it on the successor set would report every
        # correct transcription as a disagreement with the set it replaced.
        oracle = read_constraint_table(constraint_table) if set_name == "jca" else None
        agreement = {"agree": 0, "disagree": 0, "not-derived": 0, "unrecorded": 0}
        if oracle is None:
            if set_name == "jca":
                report["skipped"].append(
                    "G-CONF: no committed constraint_table.csv rows to reproduce "
                    f"({constraint_table}); reporting the derived rows only"
                )
        else:
            # The record's `mop_line` is a reading of where a specification
            # implements a clause; the verdict is the substantive column, and it
            # is the one this gate reproduces.
            recorded: dict[tuple[str, str], str] = {}
            for row in oracle:
                key = (row.get("spec", ""), row.get("cryptsl_line", ""))
                if key[1]:
                    recorded[key] = row.get("verdict", "")
            for row in rows:
                if not row["cryptsl_line"]:
                    continue
                key = (row["spec"], row["cryptsl_line"])
                if row["verdict"] == "NAO-DERIVADO":
                    agreement["not-derived"] += 1
                    continue
                if key not in recorded:
                    agreement["unrecorded"] += 1
                    continue
                if recorded[key] == row["verdict"]:
                    agreement["agree"] += 1
                else:
                    agreement["disagree"] += 1
                    hits.append(
                        {
                            "spec": row["spec"],
                            "event": row["cryptsl_line"],
                            "kind": "oracle-mismatch",
                            "derived": row["verdict"],
                            "recorded": recorded[key],
                            "clause": row.get("clause", ""),
                        }
                    )
        repo = Path(__file__).resolve().parents[1]
        records = read_records(set_name or "", repo)
        for row in rows:
            if row["verdict"] in ("IGUAL", "NAO-DERIVADO"):
                continue
            row["record"] = backing_record(row, records)
        # A difference the record accounts for is not a finding: the records are
        # where the set states, per clause, what it transcribed, what it deferred
        # and what it kept against the rule. A difference nothing accounts for is.
        hits = [hit for hit in hits if hit.get("record", "unbacked") == "unbacked"]
        cipher_lists: dict[str, list[str]] = {}
        if cipher_util is not None:
            try:
                cipher_lists = read_java_lists(cipher_util)
            except ValueError as error:
                report["skipped"].append(f"G-CONF: {error}")
        gate("G-CONF", hits, notes=rows)
        report["gates"]["G-CONF"]["report_only"] = set_name == "jca"
        report["gates"]["G-CONF"]["oracle_rows"] = len(oracle) if oracle else 0
        report["gates"]["G-CONF"]["oracle_agreement"] = agreement
        report["gates"]["G-CONF"]["cipher_util"] = str(cipher_util) if cipher_util else None
        report["gates"]["G-CONF"]["cipher_lists"] = {
            name: len(values) for name, values in cipher_lists.items()
        }
        report["gates"]["G-CONF"]["names_alias_class_in_jca"] = sorted(
            mop.path.name
            for mop in specs.values()
            if set_name == "jca" and "ConscryptAliasTable" in mop.text
        )

    # ---- G-PRED ----
    seed_dir = resolve_set_dir("jca")
    if not specs:
        report["skipped"].append("G-PRED: the set directory could not be derived from the monitor")
        gate("G-PRED", [])
    elif seed_dir is None:
        report["skipped"].append("G-PRED: the frozen jca seed is not reachable (RVSEC_HOME)")
        gate("G-PRED", [])
    else:
        divergences = predicate_divergences(specs, seed_dir)
        gate("G-PRED", divergences)
        report["gates"]["G-PRED"]["seed"] = str(seed_dir)
        report["gates"]["G-PRED"]["predicate_sites"] = sum(
            len(predicate_sites(mop.text)) for mop in specs.values()
        )

    report["ok"] = not any(gate["failures"] for gate in report["gates"].values())
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--monitor", type=Path, required=True)
    parser.add_argument("--allowlist", type=Path)
    parser.add_argument("--crysl", type=Path)
    parser.add_argument("--alias", type=Path)
    parser.add_argument(
        "--cipher-util",
        type=Path,
        help="Api30CipherTransformationUtil.java; D-b keeps the Cipher lists in Java",
    )
    parser.add_argument(
        "--constraint-table",
        type=Path,
        help="data/jca_android/constraint_table.csv, the oracle G-CONF reproduces on `jca`",
    )
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    if not args.monitor.is_file():
        print(f"generated monitor not found: {args.monitor}", file=sys.stderr)
        return 2

    report = run_gates(
        monitor=args.monitor,
        allowlist=Allowlist.load(args.allowlist),
        crysl_dir=args.crysl,
        alias_csv=args.alias,
        cipher_util=args.cipher_util,
        constraint_table=args.constraint_table,
    )

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    for reason in report["skipped"]:
        print(f"skipped -- {reason}", file=sys.stderr)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""G-ORDER: the automaton of a `.mop` accepts the language its CrySL rule orders.

A CrySL rule states the legal call sequences of an API in its `ORDER` clause; the
`.mop` that monitors it states them again as an `fsm` or an `ere`. Nothing checks
that the two say the same thing, and when they disagree the monitor accuses a
conforming program: the measured case is `SecureRandom`, whose rule orders
`Ins, Seeds?, Ends*` -- Kleene star -- while the specification's `end` state has no
transition for `next2`, so a second `nextBytes()` is reported as a wrong call
sequence. 12,400 events, 99.98 % of them raised inside libraries.

Both languages are regular, so the comparison is decidable and is decided rather
than reviewed: the `Order` grammar is sequence, alternative, cardinality and
grouping, its aggregates (`Gets := g1 | g2`) are regular, and an `fsm`/`ere` is an
automaton already. Each side becomes an NFA over the rule's base event alphabet,
both are determinised, and the product is walked for a word one accepts and the
other does not. That word is the finding: a verdict nobody can act on is a verdict
nobody reads.

**The mapping is the gate's real work, and it is never inferred** (INV-INS-138).
The `.mop` splits overloads to bind arguments and the rule aggregates them, so the
alphabets do not correspond by name -- `SecureRandomSpec.g3` is the rule's `gI`,
`setSeed1` is `s2` and `setSeed2` is `s1`. The associations live in
`data/jca_android/order_alphabet_map.csv`, versioned and revised with the
specification that uses it. Without a rule or without a complete mapping the gate
reports `skipped` with the reason: a heuristic guess here is a wrong verdict in
both directions, and a wrong verdict about an ordering is how a false accusation
gets blessed.

An event whose mapping row says `order-unmapped` is erased from the automaton's
language before the comparison -- it is an accuser the rule's alphabet has no
symbol for, such as `initError` or `unsafe_protocol`. That erasure is what lets
Group 3 absorb an orphan into the automaton (G-ACC) without changing the language
the automaton accepts (G-ORDER).

Usage:
    uv run python scripts/gh105_order_gate.py --sets jca_android [--json]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gh105_predicate_graph import SPECIFICATION_SETS, read_mop  # noqa: E402

# The oracle. gh104 fixed it as read-only: where a generated rule is judged
# defective the judgement is a row of `divergence_record.csv`, never an edit here.
DEFAULT_RULES = Path(
    "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv"
    "/MetaCrySL/generated/api30"
)

DEFAULT_MAP = Path("data/jca_android/order_alphabet_map.csv")

_SECTION = re.compile(
    r"^\s*(SPEC|OBJECTS|EVENTS|ORDER|CONSTRAINTS|REQUIRES|ENSURES|NEGATES|FORBIDDEN)\b"
)
# `Gets := g1 | g2;` -- an aggregate. `g1: getInstance(alg);` -- a base event.
_AGGREGATE = re.compile(r"^\s*(?P<name>\w+)\s*:=\s*(?P<definition>[^;]+);")
_BASE_EVENT = re.compile(r"^\s*(?P<name>\w+)\s*:(?!=)\s*(?P<signature>[^;]*);")

_FSM_STATE = re.compile(r"(?P<name>\w+)\s*\[")
_FSM_TRANSITION = re.compile(r"(?P<event>\w+)\s*->\s*(?P<target>\w+)")
# `alias match1 = init` -- the accepting states of an `fsm`. JavaMOP names the
# accepting category by the handler the alias feeds, so the alias table is where
# an automaton says which of its states is a match.
_MATCH_ALIAS = re.compile(r"^match\d*$")

_ERE_EMPTY = {"epsilon"}


# ------------------------------------------------------------------ the oracle


@dataclass(frozen=True)
class Rule:
    """One api30 rule, reduced to what an ordering comparison needs."""

    name: str
    events: tuple[str, ...]
    aggregates: dict[str, str]
    order: str


def read_rule(path: Path) -> Rule:
    """The rule's event alphabet, its aggregates and its `ORDER` expression."""
    events: list[str] = []
    aggregates: dict[str, str] = {}
    order: list[str] = []
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = _SECTION.match(line)
        if heading:
            section = heading.group(1)
            continue
        if section == "EVENTS":
            aggregate = _AGGREGATE.match(line)
            if aggregate:
                aggregates[aggregate.group("name")] = aggregate.group("definition")
                continue
            base = _BASE_EVENT.match(line)
            if base:
                events.append(base.group("name"))
        elif section == "ORDER":
            order.append(line)
    return Rule(path.stem, tuple(events), aggregates, " ".join(order).strip())


# --------------------------------------------------------------- the expression


def tokenize(text: str) -> list[str]:
    """Identifiers and operators; `,` is dropped.

    Sequence is written `a, b` in an `ORDER` and by juxtaposition in an `ere`, and
    the two mean the same thing, so one parser reads both once the comma is gone.
    """
    tokens: list[str] = []
    for match in re.finditer(r"[A-Za-z_$][\w$]*|[()|*+?,]", text):
        token = match.group(0)
        if token != ",":
            tokens.append(token)
    return tokens


class ParseError(Exception):
    """A grammar the gate cannot read is a skip with a reason, never a verdict."""


def parse_expression(text: str) -> tuple:
    """`alt := cat ('|' cat)*`, `cat := postfix+`, `postfix := atom [*+?]*`."""
    tokens = tokenize(text)
    position = 0

    def peek() -> str | None:
        return tokens[position] if position < len(tokens) else None

    def parse_alt() -> tuple:
        branches = [parse_cat()]
        while peek() == "|":
            nonlocal position
            position += 1
            branches.append(parse_cat())
        return branches[0] if len(branches) == 1 else ("alt", tuple(branches))

    def parse_cat() -> tuple:
        nonlocal position
        items: list[tuple] = []
        while peek() is not None and peek() not in ("|", ")"):
            items.append(parse_postfix())
        if not items:
            return ("eps",)
        return items[0] if len(items) == 1 else ("cat", tuple(items))

    def parse_postfix() -> tuple:
        nonlocal position
        node = parse_atom()
        while peek() in ("*", "+", "?"):
            node = ({"*": "star", "+": "plus", "?": "opt"}[tokens[position]], node)
            position += 1
        return node

    def parse_atom() -> tuple:
        nonlocal position
        token = peek()
        if token is None:
            raise ParseError("the expression ends where a symbol was expected")
        if token == "(":
            position += 1
            node = parse_alt()
            if peek() != ")":
                raise ParseError("an unclosed `(` in the expression")
            position += 1
            return node
        if token in ("|", "*", "+", "?", ")"):
            raise ParseError(f"`{token}` where a symbol was expected")
        position += 1
        return ("eps",) if token in _ERE_EMPTY else ("sym", token)

    node = parse_alt()
    if position != len(tokens):
        raise ParseError(f"`{tokens[position]}` left over at the end of the expression")
    return node


def expand_aggregates(node: tuple, aggregates: dict[str, str], seen: frozenset = frozenset()) -> tuple:
    """Replace every aggregate symbol by its definition, recursively.

    `Ins := Gets | Cons` over `Gets := g1 | g2 | gI` is two levels deep in the
    SecureRandom rule, and a cycle would be a defect in the oracle rather than
    input to trust, so the recursion carries the names it is already inside.
    """
    kind = node[0]
    if kind == "sym":
        name = node[1]
        if name not in aggregates:
            return node
        if name in seen:
            raise ParseError(f"the aggregate `{name}` is defined in terms of itself")
        return expand_aggregates(
            parse_expression(aggregates[name]), aggregates, seen | {name}
        )
    if kind in ("alt", "cat"):
        return (kind, tuple(expand_aggregates(child, aggregates, seen) for child in node[1]))
    if kind in ("star", "plus", "opt"):
        return (kind, expand_aggregates(node[1], aggregates, seen))
    return node


def symbols_of(node: tuple) -> set[str]:
    kind = node[0]
    if kind == "sym":
        return {node[1]}
    if kind in ("alt", "cat"):
        return set().union(*(symbols_of(child) for child in node[1])) if node[1] else set()
    if kind in ("star", "plus", "opt"):
        return symbols_of(node[1])
    return set()


# ------------------------------------------------------------------- automata


@dataclass
class Nfa:
    """A Thompson construction: epsilon moves plus one symbol move per edge."""

    transitions: list[dict[str, set[int]]] = field(default_factory=list)
    epsilons: list[set[int]] = field(default_factory=list)
    start: int = 0
    accepting: set[int] = field(default_factory=set)

    def state(self) -> int:
        self.transitions.append({})
        self.epsilons.append(set())
        return len(self.transitions) - 1

    def edge(self, source: int, symbol: str, target: int) -> None:
        self.transitions[source].setdefault(symbol, set()).add(target)

    def epsilon(self, source: int, target: int) -> None:
        self.epsilons[source].add(target)

    def closure(self, states: frozenset[int]) -> frozenset[int]:
        stack = list(states)
        reached = set(states)
        while stack:
            state = stack.pop()
            for target in self.epsilons[state]:
                if target not in reached:
                    reached.add(target)
                    stack.append(target)
        return frozenset(reached)


def nfa_of_expression(node: tuple, translate=None) -> Nfa:
    """Thompson's construction over the expression, one fragment per node.

    `translate` maps a leaf symbol to the set of alphabet symbols that stand for
    it -- the mapping's non-bijection, applied at the only place it matters. An
    empty set is the `order-unmapped` erasure: the leaf becomes an epsilon move,
    so the event disappears from the language instead of failing the comparison.
    """
    nfa = Nfa()

    def build(current: tuple) -> tuple[int, int]:
        kind = current[0]
        if kind == "eps":
            start = nfa.state()
            end = nfa.state()
            nfa.epsilon(start, end)
            return start, end
        if kind == "sym":
            start = nfa.state()
            end = nfa.state()
            symbols = {current[1]} if translate is None else translate(current[1])
            if not symbols:
                nfa.epsilon(start, end)
            for symbol in symbols:
                nfa.edge(start, symbol, end)
            return start, end
        if kind == "cat":
            start, end = build(current[1][0])
            for child in current[1][1:]:
                child_start, child_end = build(child)
                nfa.epsilon(end, child_start)
                end = child_end
            return start, end
        if kind == "alt":
            start = nfa.state()
            end = nfa.state()
            for child in current[1]:
                child_start, child_end = build(child)
                nfa.epsilon(start, child_start)
                nfa.epsilon(child_end, end)
            return start, end
        if kind in ("star", "plus", "opt"):
            child_start, child_end = build(current[1])
            start = nfa.state()
            end = nfa.state()
            nfa.epsilon(start, child_start)
            nfa.epsilon(child_end, end)
            if kind != "plus":
                nfa.epsilon(start, end)
            if kind != "opt":
                nfa.epsilon(child_end, child_start)
            return start, end
        raise ParseError(f"unreadable expression node `{kind}`")

    start, end = build(node)
    nfa.start = start
    nfa.accepting = {end}
    return nfa


@dataclass
class Dfa:
    """A total deterministic automaton: every state answers for every symbol."""

    alphabet: tuple[str, ...]
    transitions: list[dict[str, int]]
    accepting: set[int]
    start: int = 0


def determinize(nfa: Nfa, alphabet: tuple[str, ...]) -> Dfa:
    """Subset construction, with the dead state made explicit.

    Totality is not decoration here: an `fsm` accuses precisely by *not* having a
    transition, so the sink that a missing transition leads to is part of what is
    being compared.
    """
    start = nfa.closure(frozenset({nfa.start}))
    index = {start: 0}
    order = [start]
    transitions: list[dict[str, int]] = []
    while len(transitions) < len(order):
        subset = order[len(transitions)]
        row: dict[str, int] = {}
        for symbol in alphabet:
            targets: set[int] = set()
            for state in subset:
                targets |= nfa.transitions[state].get(symbol, set())
            reached = nfa.closure(frozenset(targets))
            if reached not in index:
                index[reached] = len(order)
                order.append(reached)
            row[symbol] = index[reached]
        transitions.append(row)
    accepting = {
        position for subset, position in index.items() if subset & nfa.accepting
    }
    return Dfa(alphabet, transitions, accepting)


def difference_witness(left: Dfa, right: Dfa) -> tuple[str, ...] | None:
    """The shortest word the two disagree on, or None when they agree.

    Breadth-first over the product, so the word that comes back is the shortest
    one -- a three-symbol counterexample is something a reader can check against
    the rule by hand, and a thirty-symbol one is another opaque verdict.
    """
    alphabet = left.alphabet
    start = (left.start, right.start)
    parents: dict[tuple[int, int], tuple[tuple[int, int], str] | None] = {start: None}
    queue = [start]
    while queue:
        current = queue.pop(0)
        if (current[0] in left.accepting) != (current[1] in right.accepting):
            word: list[str] = []
            step = current
            while parents[step] is not None:
                previous, symbol = parents[step]
                word.append(symbol)
                step = previous
            return tuple(reversed(word))
        for symbol in alphabet:
            nxt = (left.transitions[current[0]][symbol], right.transitions[current[1]][symbol])
            if nxt not in parents:
                parents[nxt] = (current, symbol)
                queue.append(nxt)
    return None


def accepts(dfa: Dfa, word: tuple[str, ...]) -> bool:
    state = dfa.start
    for symbol in word:
        if symbol not in dfa.alphabet:
            return False
        state = dfa.transitions[state][symbol]
    return state in dfa.accepting


# ------------------------------------------------------------------ the mapping


@dataclass(frozen=True)
class MapRow:
    spec: str
    mop_event: str
    order_symbol: str
    symbol_kind: str
    rule: str
    disposition: str
    reason: str


def read_map(path: Path) -> dict[str, list[MapRow]]:
    """The versioned mapping, by specification.

    The file carries a header comment enumerating what it covers and what is still
    owed, which is what makes its completeness checkable before the closing task
    claims it -- so the reader drops `#` lines rather than the file dropping the
    comment.
    """
    if not path.is_file():
        return {}
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines(keepends=True)
        if not line.startswith("#")
    ]
    mapping: dict[str, list[MapRow]] = {}
    for row in csv.DictReader(lines):
        entry = MapRow(
            row["spec"],
            row["mop_event"],
            row["order_symbol"],
            row["symbol_kind"],
            row["rule"],
            row["disposition"],
            row["reason"],
        )
        mapping.setdefault(entry.spec, []).append(entry)
    return mapping


# -------------------------------------------------------------------- the gate


@dataclass(frozen=True)
class OrderFinding:
    spec_set: str
    spec: str
    message: str
    witness: tuple[str, ...] = ()
    accepted_by: str = ""


@dataclass
class OrderRun:
    passed: list[str] = field(default_factory=list)
    findings: list[OrderFinding] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.passed) + len(self.findings) + len(self.skipped)


def _automaton_region(source):
    return next((region for region in source.regions if region.kind == "automaton"), None)


def _match_states(source) -> set[str]:
    """The states an `alias match…` names -- an `fsm`'s accepting set."""
    return {
        target
        for name, target in source.aliases.items()
        if _MATCH_ALIAS.match(name)
    }


def _fsm_nfa(source, text: str, translate) -> Nfa:
    """The `fsm` as an NFA over the rule's alphabet, transition by transition."""
    states: dict[str, tuple[int, int]] = {}
    nfa = Nfa()
    declared_order: list[str] = []
    blocks: dict[str, str] = {}
    for match in _FSM_STATE.finditer(text):
        name = match.group("name")
        opening = text.index("[", match.start())
        depth = 0
        for index in range(opening, len(text)):
            if text[index] == "[":
                depth += 1
            elif text[index] == "]":
                depth -= 1
                if depth == 0:
                    break
        blocks[name] = text[opening : index + 1]
        declared_order.append(name)

    for name in declared_order:
        states[name] = (nfa.state(), 0)
    for name in declared_order:
        for transition in _FSM_TRANSITION.finditer(blocks[name]):
            target = transition.group("target")
            if target not in states:
                raise ParseError(f"the state `{target}` is named and never declared")
            symbols = translate(transition.group("event"))
            source_state = states[name][0]
            target_state = states[target][0]
            if not symbols:
                nfa.epsilon(source_state, target_state)
            for symbol in symbols:
                nfa.edge(source_state, symbol, target_state)

    if not declared_order:
        raise ParseError("the `fsm` declares no state")
    nfa.start = states[declared_order[0]][0]
    accepting = _match_states(source)
    unknown = accepting - set(states)
    if unknown:
        raise ParseError(f"an alias names states the `fsm` does not declare: {sorted(unknown)}")
    nfa.accepting = {states[name][0] for name in accepting}
    return nfa


def build_automata(
    mop: Path,
    rules_root: Path,
    mapping: dict[str, list[MapRow]],
) -> tuple[Dfa, Dfa] | str:
    """The two languages of one specification, or the reason there is no pair.

    Returns `(specified, ordered)` -- the `.mop` automaton and the rule's `ORDER`,
    both determinised over the same alphabet, both total. Kept separate from the
    verdict so a reader can ask either language a direct question: whether it
    accepts `Ins nB nB` is exactly the SecureRandom case, and a gate that only ever
    reported its own witness could not be checked against a known one.
    """
    spec = mop.stem
    rows = mapping.get(spec, [])
    if not rows:
        return f"no rows in the alphabet mapping for `{spec}`; G-ORDER never infers one"

    rule_name = rows[0].rule
    rule_path = rules_root / rule_name
    if not rule_path.is_file():
        return f"the mapping names `{rule_name}`, which is not under {rules_root}"

    source = read_mop(mop)
    if source.parse_error:
        return f"the specification could not be read: {source.parse_error}"

    region = _automaton_region(source)
    if region is None:
        return "the specification declares no automaton"

    missing = [event for event in source.declared_events if event not in {row.mop_event for row in rows}]
    if missing:
        return (
            f"the mapping is incomplete for `{spec}`: {sorted(set(missing))} carry no row, "
            "and an association that is not written down is not inferred"
        )

    rule = read_rule(rule_path)
    if not rule.order:
        return f"`{rule_name}` states no ORDER"

    try:
        order = expand_aggregates(parse_expression(rule.order), rule.aggregates)
    except ParseError as error:
        return f"the ORDER of `{rule_name}` could not be read: {error}"

    # A `.mop` event stands for every ORDER symbol its rows name, expanded through
    # the rule's aggregates: `SignatureSpec.update` is `Updates` whole, and
    # `CipherSpec.i2` is six of the rule's `init` overloads at once.
    translation: dict[str, set[str]] = {}
    for row in rows:
        if row.disposition == "order-unmapped" or not row.order_symbol:
            translation.setdefault(row.mop_event, set())
            continue
        try:
            expanded = symbols_of(
                expand_aggregates(parse_expression(row.order_symbol), rule.aggregates)
            )
        except ParseError as error:
            return f"the mapping row for `{spec}.{row.mop_event}` could not be read: {error}"
        translation.setdefault(row.mop_event, set()).update(expanded)

    def translate(event: str) -> set[str]:
        # An event the automaton names and the mapping does not carry is not
        # erased silently: erasure is the recorded `order-unmapped` decision, and
        # a symbol nobody wrote a row for is a mapping that is not finished.
        if event not in translation:
            raise ParseError(f"`{event}` is named by the automaton and carries no mapping row")
        return translation[event]

    alphabet = tuple(sorted(symbols_of(order) | set().union(*translation.values(), set())))
    if not alphabet:
        return f"`{rule_name}` orders an empty alphabet"

    text = source.neutral[region.start : region.end]
    try:
        if region.owner == "fsm":
            automaton = _fsm_nfa(source, text, translate)
        else:
            automaton = nfa_of_expression(parse_expression(text), translate)
    except ParseError as error:
        return f"the automaton of `{spec}` could not be read: {error}"

    return determinize(automaton, alphabet), determinize(nfa_of_expression(order), alphabet)


def check_specification(
    spec_set: str,
    mop: Path,
    rules_root: Path,
    mapping: dict[str, list[MapRow]],
) -> OrderFinding | str | None:
    """One specification: a finding, a skip reason, or None when the two agree.

    Every exit that is not a decision is a skip that says why. The gate is written
    to be run over the whole enumerated universe, most of which has no CrySL rule
    at all, and a gate that answered `green` there would be answering about files
    it never compared (INV-INS-140).
    """
    built = build_automata(mop, rules_root, mapping)
    if isinstance(built, str):
        return built

    specified, ordered = built
    witness = difference_witness(specified, ordered)
    if witness is None:
        return None

    accepted_by = "the api30 ORDER" if accepts(ordered, witness) else "the specification"
    rejected_by = "the specification" if accepted_by.endswith("ORDER") else "the api30 ORDER"
    word = " ".join(witness) if witness else "the empty sequence"
    return OrderFinding(
        spec_set,
        mop.stem,
        f"`{word}` is accepted by {accepted_by} and rejected by {rejected_by}",
        witness,
        accepted_by,
    )


def run(
    specs_root: Path,
    selection: str = "all",
    rules_root: Path = DEFAULT_RULES,
    map_path: Path = DEFAULT_MAP,
) -> OrderRun:
    """G-ORDER over the enumerated universe, skipping what it cannot decide."""
    mapping = read_map(map_path)
    names = SPECIFICATION_SETS if selection == "all" else (selection,)
    result = OrderRun()
    for name in names:
        set_dir = specs_root / name
        if not set_dir.is_dir():
            continue
        for mop in sorted(set_dir.glob("*.mop")):
            # The mapping is `jca_android`'s. `jca` is frozen and the archived set
            # is a record: comparing either against the oracle would report a
            # divergence nobody may repair.
            if name != "jca_android":
                result.skipped.append(
                    (f"{name}/{mop.stem}", "the alphabet mapping covers the migrated set only")
                )
                continue
            outcome = check_specification(name, mop, rules_root, mapping)
            if outcome is None:
                result.passed.append(f"{name}/{mop.stem}")
            elif isinstance(outcome, str):
                result.skipped.append((f"{name}/{mop.stem}", outcome))
            else:
                result.findings.append(outcome)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--specs-root",
        type=Path,
        default=Path("../rvsec/rvsec-mop/src/main/resources"),
        help="directory holding the specification sets",
    )
    parser.add_argument("--sets", default="all", help="`all` or the name of one set")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES, help="the api30 rules")
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP, help="the alphabet mapping")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    arguments = parser.parse_args(argv)

    result = run(arguments.specs_root, arguments.sets, arguments.rules, arguments.map)

    payload = {
        "passed": len(result.passed),
        "failed": len(result.findings),
        "skipped": len(result.skipped),
        "total": result.total,
        "findings": [
            {
                "set": finding.spec_set,
                "spec": finding.spec,
                "message": finding.message,
                "witness": list(finding.witness),
                "accepted_by": finding.accepted_by,
            }
            for finding in result.findings
        ],
        "skips": [{"spec": spec, "reason": reason} for spec, reason in result.skipped],
    }

    if arguments.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"G-ORDER: {len(result.passed)} passed, {len(result.findings)} failed, "
            f"{len(result.skipped)} skipped of {result.total} specifications"
        )
        for finding in result.findings:
            print(f"  [{finding.spec_set}/{finding.spec}] {finding.message}")
        for spec, reason in result.skipped:
            print(f"  skipped {spec}: {reason}")

    return 1 if result.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

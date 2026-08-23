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

A divergence the set keeps on purpose is a row of `data/jca_android/gate_allowlist.csv`
and is reported as `allow-listed`, not as a failure. There are two kinds, and
neither has a repair on the specification's side: the rule orders a symbol no
monitored program can produce -- `CipherInputStream`'s one-argument constructor is
`protected` on android-30, and `SecretKeySpec.destroy()` throws in both
implementations this set sees, so the `.mop` does not observe it -- and the
specification is the frozen `jca`'s, where an edit would break the freeze task 8.2
proves. Each row carries the witness, the measurement and the task that decided
it, which is what separates it from an expectation nobody voted for: the gate
asserts zero findings on its own, and the exceptions are named in a file under
review rather than recorded by whatever a run happened to measure.

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

# Both data paths are anchored to this file, not to the working directory. A
# relative default makes the gate answer "0 of 24 compared, every specification
# skipped for want of mapping rows" from any other cwd, and exit 0 saying it --
# a mis-pathed CSV would be indistinguishable from a genuinely unmapped
# specification, which is the one confusion this gate exists to prevent.
REPO = Path(__file__).resolve().parents[1]

DEFAULT_MAP = REPO / "data/jca_android/order_alphabet_map.csv"

# A divergence this gate reports may be one the set is keeping on purpose: the
# rule orders a symbol no monitored program can produce, or the specification is
# the frozen `jca`'s and may not be edited here. Those live in the allow-list,
# and the difference from a recorded expectation is the whole point -- a row of
# `gate_allowlist.csv` names the witness, the reason, and the task that decided
# it, so the finding stays visible and stays owned.
DEFAULT_ALLOWLIST = REPO / "data/jca_android/gate_allowlist.csv"

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
    """One api30 rule, reduced to what an ordering comparison needs.

    Attributes:
        name: The rule's file stem, which is the API class it governs.
        events: Base event names of the `EVENTS` section, in declaration order.
        aggregates: Aggregate name to its unexpanded definition (`"g1 | g2"`).
        order: The `ORDER` clause joined into one line, aggregates unexpanded.
    """

    name: str
    events: tuple[str, ...]
    aggregates: dict[str, str]
    order: str


def read_rule(path: Path) -> Rule:
    """Read a rule's event alphabet, its aggregates and its `ORDER` expression.

    Args:
        path: A generated api30 CrySL rule.

    Returns:
        A Rule carrying only the ordering-relevant sections. `CONSTRAINTS`,
        `REQUIRES` and `ENSURES` are walked past and dropped -- they are the
        predicate graph's subject, not this gate's.
    """
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
    """Split an expression into identifiers and operators, comma included.

    Sequence is written `a, b` in an `ORDER` and by juxtaposition in an `ere`, and
    the two mean the same thing but do not bind the same way: `CrySL.xtext:103-120`
    makes `Sequence` the outermost production, so the comma is weaker than `|`,
    while juxtaposition in an `ere` is tighter than `|` as in any regular
    expression. One parser still reads both notations -- it keeps the two
    spellings apart instead of erasing the comma into juxtaposition, which is what
    made `a, b | c` parse as `(a b) | c` instead of `a, (b | c)`.

    Args:
        text: An `ORDER` clause, an `ere`, or one mapping row's `order_symbol`.

    Returns:
        The tokens in source order: identifiers and the operators `( ) | * + ? ,`.
    """
    return [
        match.group(0) for match in re.finditer(r"[A-Za-z_$][\w$]*|[()|*+?,]", text)
    ]


class ParseError(Exception):
    """A grammar the gate cannot read is a skip with a reason, never a verdict."""


def parse_expression(text: str) -> tuple:
    """Parse a regular expression into a syntax tree.

    The grammar is `seq := alt (',' alt)*`, `alt := cat ('|' cat)*`,
    `cat := postfix+`, `postfix := atom [*+?]*` -- every form an `ORDER` and an
    `ere` share, with each notation's own sequence operator at its own strength:
    the `ORDER`'s comma weakest, per `CrySL.xtext:103-120`, and the `ere`'s
    juxtaposition tightest. An `ere` never carries a comma and an `ORDER` never
    juxtaposes, so neither notation is read under the other's precedence.

    Args:
        text: The expression, in either notation.

    Returns:
        A nested tuple headed by its node kind: `("sym", name)`, `("eps",)`,
        `("cat", children)`, `("alt", branches)`, or
        `("star" | "plus" | "opt", child)`.

    Raises:
        ParseError: When the expression is unbalanced, ends where a symbol was
            expected, or places an operator in a symbol's position.
    """
    tokens = tokenize(text)
    position = 0

    def peek() -> str | None:
        return tokens[position] if position < len(tokens) else None

    def parse_seq() -> tuple:
        nonlocal position
        items = [parse_alt()]
        while peek() == ",":
            position += 1
            items.append(parse_alt())
        return items[0] if len(items) == 1 else ("cat", tuple(items))

    def parse_alt() -> tuple:
        branches = [parse_cat()]
        while peek() == "|":
            nonlocal position
            position += 1
            branches.append(parse_cat())
        return branches[0] if len(branches) == 1 else ("alt", tuple(branches))

    def parse_cat() -> tuple:
        items: list[tuple] = []
        while peek() is not None and peek() not in ("|", ")", ","):
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
            node = parse_seq()
            if peek() != ")":
                raise ParseError("an unclosed `(` in the expression")
            position += 1
            return node
        if token in ("|", "*", "+", "?", ")", ","):
            raise ParseError(f"`{token}` where a symbol was expected")
        position += 1
        return ("eps",) if token in _ERE_EMPTY else ("sym", token)

    node = parse_seq()
    if position != len(tokens):
        raise ParseError(f"`{tokens[position]}` left over at the end of the expression")
    return node


def expand_aggregates(
    node: tuple, aggregates: dict[str, str], seen: frozenset = frozenset()
) -> tuple:
    """Replace every aggregate symbol by its definition, recursively.

    `Ins := Gets | Cons` over `Gets := g1 | g2 | gI` is two levels deep in the
    SecureRandom rule, and a cycle would be a defect in the oracle rather than
    input to trust, so the recursion carries the names it is already inside.

    Args:
        node: A tree from parse_expression.
        aggregates: The rule's aggregate definitions, unexpanded.
        seen: Aggregate names the recursion is already inside, for cycle detection.

    Returns:
        The same tree with every aggregate leaf replaced by its parsed and
        expanded definition; leaves naming base events are returned untouched.

    Raises:
        ParseError: When an aggregate is defined in terms of itself, or when a
            definition does not parse.
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
        return (
            kind,
            tuple(expand_aggregates(child, aggregates, seen) for child in node[1]),
        )
    if kind in ("star", "plus", "opt"):
        return (kind, expand_aggregates(node[1], aggregates, seen))
    return node


def symbols_of(node: tuple) -> set[str]:
    """Collect every leaf symbol of a parsed expression.

    Args:
        node: A tree from parse_expression, aggregates already expanded.

    Returns:
        The distinct symbol names. The empty word contributes none, so an
        expression that only matches epsilon yields the empty set.
    """
    kind = node[0]
    if kind == "sym":
        return {node[1]}
    if kind in ("alt", "cat"):
        return (
            set().union(*(symbols_of(child) for child in node[1])) if node[1] else set()
        )
    if kind in ("star", "plus", "opt"):
        return symbols_of(node[1])
    return set()


# ------------------------------------------------------------------- automata


@dataclass
class Nfa:
    """A Thompson construction: epsilon moves plus one symbol move per edge.

    Attributes:
        transitions: Per state, the symbol-labelled moves out of it.
        epsilons: Per state, the states reachable without consuming a symbol.
        start: Index of the initial state.
        accepting: Indices of the accepting states.
    """

    transitions: list[dict[str, set[int]]] = field(default_factory=list)
    epsilons: list[set[int]] = field(default_factory=list)
    start: int = 0
    accepting: set[int] = field(default_factory=set)

    def state(self) -> int:
        """Add a fresh state and return its index."""
        self.transitions.append({})
        self.epsilons.append(set())
        return len(self.transitions) - 1

    def edge(self, source: int, symbol: str, target: int) -> None:
        """Add a move from `source` to `target` labelled `symbol`."""
        self.transitions[source].setdefault(symbol, set()).add(target)

    def epsilon(self, source: int, target: int) -> None:
        """Add a move from `source` to `target` that consumes nothing."""
        self.epsilons[source].add(target)

    def closure(self, states: frozenset[int]) -> frozenset[int]:
        """Expand a state set along epsilon moves until it stops growing.

        Args:
            states: The states reached by consuming one symbol.

        Returns:
            Those states plus everything reachable from them without consuming
            another, which is the subset construction's unit of work.
        """
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
    """Build an NFA from a parsed expression, one Thompson fragment per node.

    Args:
        node: A tree from parse_expression, aggregates already expanded.
        translate: Maps a leaf symbol to the set of alphabet symbols that stand
            for it -- the mapping's non-bijection, applied at the only place it
            matters. An empty set is the `order-unmapped` erasure: the leaf
            becomes an epsilon move, so the event disappears from the language
            instead of failing the comparison. None leaves symbols as they are.

    Returns:
        An NFA with a single start and a single accepting state.

    Raises:
        ParseError: When the tree carries a node kind the construction has no
            fragment for.
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
    """A total deterministic automaton: every state answers for every symbol.

    Attributes:
        alphabet: The symbols every state has a row for, sorted.
        transitions: Per state, one target per alphabet symbol.
        accepting: Indices of the accepting states.
        start: Index of the initial state.
    """

    alphabet: tuple[str, ...]
    transitions: list[dict[str, int]]
    accepting: set[int]
    start: int = 0


def determinize(nfa: Nfa, alphabet: tuple[str, ...]) -> Dfa:
    """Determinise an NFA by subset construction, dead state made explicit.

    Totality is not decoration here: an `fsm` accuses precisely by *not* having a
    transition, so the sink that a missing transition leads to is part of what is
    being compared.

    Args:
        nfa: The automaton to determinise.
        alphabet: The symbols to build a row for. Both sides of a comparison are
            determinised over the same one, which is what makes the product walk
            in difference_witness well defined.

    Returns:
        A total DFA whose state 0 is the epsilon closure of the NFA's start.
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
    """Find the shortest word the two automata disagree on.

    Breadth-first over the product, so the word that comes back is the shortest
    one -- a three-symbol counterexample is something a reader can check against
    the rule by hand, and a thirty-symbol one is another opaque verdict.

    Args:
        left: One total DFA.
        right: The other, determinised over the same alphabet.

    Returns:
        The shortest symbol sequence one accepts and the other rejects, or None
        when the two accept the same language. An empty tuple means they already
        disagree on the empty word.
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
            nxt = (
                left.transitions[current[0]][symbol],
                right.transitions[current[1]][symbol],
            )
            if nxt not in parents:
                parents[nxt] = (current, symbol)
                queue.append(nxt)
    return None


def accepts(dfa: Dfa, word: tuple[str, ...]) -> bool:
    """Run a word through a DFA and report whether it lands in an accepting state.

    Args:
        dfa: A total automaton from determinize.
        word: The symbols to consume, in order.

    Returns:
        False as soon as a symbol falls outside the alphabet the automaton was
        determinised over, since no state answers for it.
    """
    state = dfa.start
    for symbol in word:
        if symbol not in dfa.alphabet:
            return False
        state = dfa.transitions[state][symbol]
    return state in dfa.accepting


# ------------------------------------------------------------------ the mapping


@dataclass(frozen=True)
class MapRow:
    """One association between a `.mop` event and the `ORDER` symbols it stands for.

    Attributes:
        spec: Specification stem the row belongs to.
        mop_event: Event name as the `.mop` declares it.
        order_symbol: The rule symbol, or an expression over rule symbols, the
            event stands for. Empty when the row records an erasure.
        symbol_kind: `event` or `aggregate` -- which side of the mapping's
            non-bijection the row is on. Empty on an erasure row.
        rule: File name of the api30 rule the specification is compared against.
        disposition: `mapped` for an ordinary association; `order-unmapped`
            erases the event from both languages before the comparison.
        reason: Why the association or the erasure was decided, in prose.
    """

    spec: str
    mop_event: str
    order_symbol: str
    symbol_kind: str
    rule: str
    disposition: str
    reason: str


def read_map(path: Path) -> dict[str, list[MapRow]]:
    """Read the versioned alphabet mapping, grouped by specification.

    The file carries a header comment enumerating what it covers and what is still
    owed, which is what makes its completeness checkable before the closing task
    claims it -- so the reader drops `#` lines rather than the file dropping the
    comment.

    Args:
        path: The mapping CSV. A missing file is not an error here: it makes
            every specification skip with the reason, which is the honest answer
            for a gate that never infers an association.

    Returns:
        Specification stem to its rows, in file order. Empty when the file does
        not exist.
    """
    if not path.is_file():
        return {}
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines(keepends=True)
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
    """One specification whose automaton and whose rule order different languages.

    Attributes:
        spec_set: Specification set the `.mop` belongs to.
        spec: Specification file stem.
        message: The witness word and which of the two sides accepts it.
        witness: The shortest disagreeing call sequence, as rule symbols. It is
            carried apart from the message so a reader can replay it.
        accepted_by: `the api30 ORDER` or `the specification` -- which side
            admits the witness, and therefore which side is the accuser.
    """

    spec_set: str
    spec: str
    message: str
    witness: tuple[str, ...] = ()
    accepted_by: str = ""


@dataclass
class OrderRun:
    """Everything one G-ORDER run produced, skips included.

    The three lists are disjoint and together account for every `.mop` visited.
    Most of the enumerated universe lands in `skipped`, and that is the designed
    outcome: a gate that answered green where it never compared anything would be
    answering about files it never read (INV-INS-140).

    Attributes:
        passed: `<set>/<spec>` of each specification whose two languages agree.
        findings: One entry per specification whose languages differ and whose
            divergence nobody has decided to keep.
        allowed: One entry per specification whose languages differ and whose
            divergence `gate_allowlist.csv` records as deliberate. It is a
            finding in every respect except its verdict: it is printed, it is
            counted, and it names the task that owns it -- what it is not is a
            reason to fail. Kept apart from `findings` so the gate can assert
            zero findings on its own.
        skipped: `(<set>/<spec>, reason)` for each specification the gate could
            not decide.
    """

    passed: list[str] = field(default_factory=list)
    findings: list[OrderFinding] = field(default_factory=list)
    allowed: list[OrderFinding] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            len(self.passed)
            + len(self.findings)
            + len(self.allowed)
            + len(self.skipped)
        )


# The witness word of the empty sequence. A row has to say *something* there, and
# the empty string already means "this row names no witness", so the empty word
# gets a token of its own.
EMPTY_WITNESS = "<empty>"


def witness_word(witness: tuple[str, ...]) -> str:
    """The witness as one comparable word, with the empty sequence spelled out."""
    return " ".join(witness) or EMPTY_WITNESS


def read_allowlist(path: Path) -> set[tuple[str, str, str, str]]:
    """The ordering divergences `gate_allowlist.csv` records as deliberate.

    A row with an empty `reason` allows nothing. That is not defensive coding: it
    is the difference between this file and the expected-baseline it replaced.
    A baseline row was three fields a run happened to measure; an allow-list row
    is a decision, and a decision with no reason written down is the thing task
    7.6 removed. `gh104_gates.py` reads its own allow-list the same way.

    A row with an empty `witness` allows nothing either, and for a sharper reason.
    Keyed on the specification alone, a row that forgives one measured divergence
    forgives every future one of the same specification -- nine of the twenty-two
    compared specifications would stop being guarded the moment their row landed.
    The witness is what makes the row about the divergence it was written for.

    Args:
        path: The allow-list CSV. Rows of other gates are ignored here.

    Returns:
        `(set, spec, event_or_state, witness)` for each G-ORDER row that carries
        both a reason and a witness, or the empty set when the file does not
        exist.
    """
    if not path.is_file():
        return set()
    allowed: set[tuple[str, str, str, str]] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            witness = (row.get("witness") or "").strip()
            if row["gate"] != "G-ORDER" or not row["reason"].strip() or not witness:
                continue
            allowed.add((row["set"], row["spec"], row["event_or_state"], witness))
    return allowed


def _is_allowed(finding: OrderFinding, allowed: set[tuple[str, str, str, str]]) -> bool:
    """Whether the allow-list covers *this* ordering divergence.

    Two widths, and no more: the row names one specification, or it names every
    ordering divergence of one set (`*, *`). There is no third width, because the
    subject of a G-ORDER row is the constant `order` -- a per-event allowance
    would be a key this gate never produces.

    In both widths the witness has to match. A specification whose divergence was
    forgiven may diverge again for another reason, and that second divergence is
    a finding: the row was a decision about one counterexample, not a licence for
    the specification's whole language.
    """
    word = witness_word(finding.witness)
    candidates = {
        (finding.spec_set, finding.spec, "order", word),
        (finding.spec_set, "*", "*", word),
    }
    return bool(candidates & allowed)


def _automaton_region(source):
    """The parsed source's `automaton` region, or None when it declares none."""
    return next(
        (region for region in source.regions if region.kind == "automaton"), None
    )


def _match_states(source) -> set[str]:
    """The states an `alias match…` names -- an `fsm`'s accepting set."""
    return {
        target for name, target in source.aliases.items() if _MATCH_ALIAS.match(name)
    }


def _fsm_nfa(source, text: str, translate) -> Nfa:
    """Build the `fsm` as an NFA over the rule's alphabet, transition by transition.

    The `fsm` states become NFA states one for one -- there is nothing to
    construct, since an `fsm` is an automaton already. What the translation adds
    is the mapping: an edge labelled by a `.mop` event becomes one edge per rule
    symbol it stands for, or an epsilon move when the event is erased.

    Args:
        source: The parsed `.mop`, read for its `alias match…` accepting set.
        text: The neutralised `fsm` block.
        translate: Maps a `.mop` event to the rule symbols it stands for.

    Returns:
        An NFA whose start is the first state the block declares, JavaMOP's own
        convention, and whose accepting set is what the match aliases name.

    Raises:
        ParseError: When the block declares no state, a transition targets a
            state that is never declared, or an alias names one.
    """
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
        raise ParseError(
            f"an alias names states the `fsm` does not declare: {sorted(unknown)}"
        )
    nfa.accepting = {states[name][0] for name in accepting}
    return nfa


def build_automata(
    mop: Path,
    rules_root: Path,
    mapping: dict[str, list[MapRow]],
) -> tuple[Dfa, Dfa] | str:
    """Build the two languages of one specification, or say why there is no pair.

    Kept separate from the verdict so a reader can ask either language a direct
    question: whether it accepts `Ins nB nB` is exactly the SecureRandom case, and
    a gate that only ever reported its own witness could not be checked against a
    known one.

    Args:
        mop: The specification to compare.
        rules_root: Directory of generated api30 rules.
        mapping: The alphabet mapping, by specification stem.

    Returns:
        `(specified, ordered)` -- the `.mop` automaton and the rule's `ORDER`,
        both determinised over the same alphabet and both total -- or a string
        naming the reason the pair could not be built. Every such string is a
        skip reason, never a verdict: no rule, no mapping rows, an incomplete
        mapping, an unreadable specification, an `ORDER` that does not parse.
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

    missing = [
        event
        for event in source.declared_events
        if event not in {row.mop_event for row in rows}
    ]
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
            raise ParseError(
                f"`{event}` is named by the automaton and carries no mapping row"
            )
        return translation[event]

    alphabet = tuple(
        sorted(symbols_of(order) | set().union(*translation.values(), set()))
    )
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

    return determinize(automaton, alphabet), determinize(
        nfa_of_expression(order), alphabet
    )


def check_specification(
    spec_set: str,
    mop: Path,
    rules_root: Path,
    mapping: dict[str, list[MapRow]],
) -> OrderFinding | str | None:
    """Decide one specification: a finding, a skip reason, or agreement.

    Every exit that is not a decision is a skip that says why. The gate is written
    to be run over the whole enumerated universe, most of which has no CrySL rule
    at all, and a gate that answered `green` there would be answering about files
    it never compared (INV-INS-140).

    Args:
        spec_set: Specification set the `.mop` belongs to, carried into findings.
        mop: The specification to decide.
        rules_root: Directory of generated api30 rules.
        mapping: The alphabet mapping, by specification stem.

    Returns:
        An OrderFinding when the two languages differ, a string carrying the skip
        reason when the comparison could not be built, or None when they agree.
    """
    built = build_automata(mop, rules_root, mapping)
    if isinstance(built, str):
        return built

    specified, ordered = built
    witness = difference_witness(specified, ordered)
    if witness is None:
        return None

    accepted_by = (
        "the api30 ORDER" if accepts(ordered, witness) else "the specification"
    )
    rejected_by = (
        "the specification" if accepted_by.endswith("ORDER") else "the api30 ORDER"
    )
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
    allowlist_path: Path = DEFAULT_ALLOWLIST,
) -> OrderRun:
    """Run G-ORDER over the enumerated universe, skipping what it cannot decide.

    Args:
        specs_root: Directory holding the specification sets, one per subdirectory.
        selection: `"all"` for the enumerated universe, or the name of one set.
        rules_root: Directory of generated api30 rules.
        map_path: The alphabet mapping CSV.
        allowlist_path: The allow-list CSV. A divergence it covers is reported
            under `allowed` instead of `findings`.

    Returns:
        An OrderRun whose passed, findings, allowed and skipped lists together
        account for every `.mop` visited.
    """
    mapping = read_map(map_path)
    # An absent mapping file and a specification with no rows in it are two
    # different facts, and `read_map` returns `{}` for both. The distinction is
    # made here, once, so that every skip reason says which of the two it is.
    map_absent = (
        None
        if map_path.is_file()
        else f"the alphabet mapping {map_path} does not exist"
    )
    # The subject column of a G-ORDER row is the constant `order`: the finding is
    # about the specification's whole language, not about one event of it.
    allowed = read_allowlist(allowlist_path)
    names = SPECIFICATION_SETS if selection == "all" else (selection,)
    result = OrderRun()
    for name in names:
        set_dir = specs_root / name
        if not set_dir.is_dir():
            # Recorded rather than dropped: a set the caller named and the tree
            # does not have is exactly the kind of silent nothing the
            # skip-and-count contract is written against.
            result.skipped.append((name, f"no directory {set_dir}"))
            continue
        for mop in sorted(set_dir.glob("*.mop")):
            # The mapping is `jca_android`'s. `jca` is frozen and the archived set
            # is a record: comparing either against the oracle would report a
            # divergence nobody may repair.
            if name != "jca_android":
                result.skipped.append(
                    (
                        f"{name}/{mop.stem}",
                        "the alphabet mapping covers the migrated set only",
                    )
                )
                continue
            outcome = map_absent or check_specification(name, mop, rules_root, mapping)
            if outcome is None:
                result.passed.append(f"{name}/{mop.stem}")
            elif isinstance(outcome, str):
                result.skipped.append((f"{name}/{mop.stem}", outcome))
            elif _is_allowed(outcome, allowed):
                result.allowed.append(outcome)
            else:
                result.findings.append(outcome)
    return result


def main(argv: list[str] | None = None) -> int:
    """Run the gate from the command line and report its verdict.

    Args:
        argv: Command-line arguments, or None to read `sys.argv`.

    Returns:
        1 when any specification's automaton and rule order different languages,
        2 when the run compared nothing at all, 0 otherwise. A skip is not a
        failure: the reasons are printed, and the count is what a reader checks
        the gate's coverage against. Comparing *nothing* is a different thing --
        a typo in `--sets`, a mis-pathed CSV or an absent tree all produce a
        clean "0 failed", and a gate that reports success for a comparison it
        never made is worse than no gate.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--specs-root",
        type=Path,
        default=Path("../rvsec/rvsec-mop/src/main/resources"),
        help="directory holding the specification sets",
    )
    parser.add_argument("--sets", default="all", help="`all` or the name of one set")
    parser.add_argument(
        "--rules", type=Path, default=DEFAULT_RULES, help="the api30 rules"
    )
    parser.add_argument(
        "--map", type=Path, default=DEFAULT_MAP, help="the alphabet mapping"
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=DEFAULT_ALLOWLIST,
        help="the allow-list of deliberately kept divergences",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    arguments = parser.parse_args(argv)

    result = run(
        arguments.specs_root,
        arguments.sets,
        arguments.rules,
        arguments.map,
        arguments.allowlist,
    )

    def describe(finding: OrderFinding) -> dict[str, object]:
        return {
            "set": finding.spec_set,
            "spec": finding.spec,
            "message": finding.message,
            "witness": list(finding.witness),
            "accepted_by": finding.accepted_by,
        }

    payload = {
        "passed": len(result.passed),
        "failed": len(result.findings),
        "allowed": len(result.allowed),
        "skipped": len(result.skipped),
        "total": result.total,
        "findings": [describe(finding) for finding in result.findings],
        "allow_listed": [describe(finding) for finding in result.allowed],
        "skips": [{"spec": spec, "reason": reason} for spec, reason in result.skipped],
    }

    if arguments.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"G-ORDER: {len(result.passed)} passed, {len(result.findings)} failed, "
            f"{len(result.allowed)} allow-listed, {len(result.skipped)} skipped "
            f"of {result.total} specifications"
        )
        for finding in result.findings:
            print(f"  [{finding.spec_set}/{finding.spec}] {finding.message}")
        for finding in result.allowed:
            print(
                f"  allow-listed [{finding.spec_set}/{finding.spec}] {finding.message}"
            )
        for spec, reason in result.skipped:
            print(f"  skipped {spec}: {reason}")

    if not (result.passed or result.findings or result.allowed):
        print(
            "G-ORDER compared no specification at all -- check `--sets`, `--map` "
            "and `--specs-root`; the skip reasons above say which",
            file=sys.stderr,
        )
        return 2
    return 1 if result.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

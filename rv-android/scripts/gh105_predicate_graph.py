#!/usr/bin/env python3
"""The predicate graph of a JavaMOP specification set, read out of the sources.

A CrySL rule links its specifications through predicates: one rule *ensures* that
a key was generated or a value randomised, another *requires* that fact before it
accepts a call. In a `.mop` set those two halves are ordinary Java calls into a
shared store, and nothing links them -- both sides name an enum constant, so a
specification that writes a constant nobody reads, or reads one nobody writes,
compiles and runs and reports nothing at all. The `jca_android` set does both.

This module turns the sites into data so the link can be gated instead of read.
It is built in three passes, each usable on its own:

    pass 1  the reader     -- neutralise comments and strings, walk the blocks,
                              find the predicate sites and the symbols they name
    pass 2  the alphabet   -- the declared events and the ones the automaton
                              names, in both directions
    pass 3  the emitter     -- `data/jca_android/predicate_graph.csv` and the
                              gate verdicts over the enumerated universe

Passes 1 and 2 live here so far.

**Why the reader is not a regex over the raw text.** Two things in these files
defeat that. Every accusing event carries an English message naming its own
predicate and code, so a pattern that scans raw text finds sites inside string
literals; and several specifications declare private helpers whose names shadow
the store's API -- `KeyPairGeneratorSpec` has `private boolean validate(int
keySize)`, called from three conditions. Neutralising literals and comments
answers the first; anchoring every site on a literal `Property.` first argument
answers the second, and also excludes the collection `.remove(...)` calls that
have nothing to do with the graph.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# The store operations that carry a `Property` constant, mapped to what they do
# to the graph. The two substrates are recognised together on purpose: the
# migration replaces one with the other file by file, so for the length of the
# change a set legitimately contains both, and a reader that knew only one would
# report the half it was taught about as the whole.
GRAPH_OPERATIONS = {
    "setProperty": "write",
    "ensure": "write",
    "validate": "read",
    "validateAbsent": "read-absent",
    "negate": "negate",
    "remove": "remove",
}

# Bookkeeping that carries no `Property` at all. It is read out anyway because
# the migration has to drive its 25 sites to zero, and a count nobody produces is
# a count nobody checks.
ACCEPTING_STATE_OPERATIONS = {
    "setObjectAsInAcceptingState": "accepting-state",
    "unsetObjectAsInAcceptingState": "accepting-state-unset",
}

_SUBSTRATES = ("ExecutionContext", "PredicateStore")

# `<Substrate>.instance().<op>(Property.<CONSTANT>` -- the discriminator is the
# literal `Property.` in first position, which is what separates a graph site
# from a helper method that happens to share the name.
_GRAPH_SITE = re.compile(
    r"\b(?P<substrate>" + "|".join(_SUBSTRATES) + r")\s*\.\s*instance\s*\(\s*\)\s*\.\s*"
    r"(?P<op>" + "|".join(GRAPH_OPERATIONS) + r")\s*\(\s*Property\s*\.\s*(?P<predicate>\w+)"
)

_ACCEPTING_SITE = re.compile(
    r"\b(?P<substrate>" + "|".join(_SUBSTRATES) + r")\s*\.\s*instance\s*\(\s*\)\s*\.\s*"
    r"(?P<op>" + "|".join(ACCEPTING_STATE_OPERATIONS) + r")\s*\("
)

_SPEC_DECL = re.compile(r"^(?P<name>\w+)\s*\(", re.MULTILINE)
# JavaMOP admits modifiers before `event`; the universe uses exactly one,
# `creation`, on ten declarations. It is captured rather than skipped because a
# junction specification that declares its *consumer* event `creation` accuses
# the conforming trace -- the pilot measured it -- and that rule is gated.
_EVENT_DECL = re.compile(r"\b(?P<modifiers>(?:creation|unsync|blocking)\s+)*event\s+(?P<name>\w+)\b")
_HANDLER_DECL = re.compile(r"@(?P<name>\w+)\s*\{")
_AUTOMATON_DECL = re.compile(r"\b(?P<kind>fsm|ere)\s*:")
_ALIAS_DECL = re.compile(r"\balias\s+(?P<name>\w+)\s*=\s*(?P<target>\w+)")

# `byte[] iv`, `IvParameterSpec s`, `List<String> algorithms` -- a declared type
# followed by a name. Used for the event parameters and the specification fields,
# which together are every symbol a predicate site can name.
_DECLARATION = re.compile(
    r"(?P<type>[A-Za-z_$][\w.$]*(?:\s*<[^<>;={}]*>)?(?:\s*\[\s*\])*)\s+"
    r"(?P<name>[A-Za-z_$]\w*)\s*(?=[,)\n;=])"
)


def neutralize(text: str) -> str:
    """Blank out comments and string/char literals, keeping every offset in place.

    Offsets are preserved -- each removed character becomes a space, newlines
    survive -- so a match found in the neutralised text can be reported against
    the real file's line and column without a second mapping. That matters more
    than it sounds: the sites this reader must *not* find live inside accusation
    messages that name their own predicate, and reporting them at the wrong line
    would be worse than not finding them.
    """
    out = list(text)
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == "/" and index + 1 < length and text[index + 1] == "/":
            while index < length and text[index] != "\n":
                out[index] = " "
                index += 1
        elif char == "/" and index + 1 < length and text[index + 1] == "*":
            out[index] = out[index + 1] = " "
            index += 2
            while index < length and not (text[index] == "*" and index + 1 < length and text[index + 1] == "/"):
                if text[index] != "\n":
                    out[index] = " "
                index += 1
            if index < length:
                out[index] = out[index + 1] = " "
                index += 2
        elif char in "\"'":
            quote = char
            out[index] = " "
            index += 1
            while index < length and text[index] != quote:
                if text[index] == "\\" and index + 1 < length:
                    out[index] = " "
                    index += 1
                if index < length:
                    if text[index] != "\n":
                        out[index] = " "
                    index += 1
            if index < length:
                out[index] = " "
                index += 1
        else:
            index += 1
    return "".join(out)


@dataclass(frozen=True)
class Region:
    """One attributable stretch of a specification.

    `kind` is what the predicate-placement invariants talk about -- a read inside
    `condition` is a guard and a read inside `body` is an accusation -- and
    `owner` names the event or handler it belongs to.
    """

    kind: str
    owner: str
    start: int
    end: int


@dataclass(frozen=True)
class Site:
    """One predicate operation, with everything needed to place and judge it."""

    file: str
    spec: str
    owner: str
    site_kind: str
    operation: str
    substrate: str
    predicate: str
    arguments: tuple[str, ...]
    line: int
    source_negated: bool
    snippet: str

    @property
    def arity(self) -> int:
        """Argument positions after the `Property` constant: bound plus values."""
        return len(self.arguments)


@dataclass
class MopSource:
    """A parsed `.mop` file: its regions, its symbols, and its predicate sites."""

    path: Path
    spec: str
    text: str
    neutral: str
    regions: list[Region] = field(default_factory=list)
    aliases: dict[str, str] = field(default_factory=dict)
    fields: dict[str, str] = field(default_factory=dict)
    event_parameters: dict[str, dict[str, str]] = field(default_factory=dict)
    # Declarations in source order, repeats included: `jca/GCMParameterSpecSpec.mop`
    # declares `c1` twice, over different signatures, and the second silently
    # replaces the first everywhere a name is the key.
    declared_events: list[str] = field(default_factory=list)
    creation_events: set[str] = field(default_factory=set)
    sites: list[Site] = field(default_factory=list)
    parse_error: str = ""
    alphabet: "Alphabet" = field(default_factory=lambda: Alphabet("", (), (), ()))

    @property
    def has_specification(self) -> bool:
        """False for a file that declares events and no specification block.

        The `generic_new` set has 17 of them. They are not broken; they are a
        different kind of file, and a gate that judged them would be judging
        something it was never told about.
        """
        return bool(self.regions) and not self.parse_error

    def line_of(self, offset: int) -> int:
        return self.neutral.count("\n", 0, offset) + 1

    def declared_type(self, owner: str, name: str) -> str:
        """The declared type of a symbol as seen from inside `owner`.

        Event parameters shadow specification fields, which is the order a Java
        compiler resolves them in, and the order that matters here: several
        specifications keep a field with the same name as the parameter their
        events bind.
        """
        return self.event_parameters.get(owner, {}).get(name) or self.fields.get(name, "")


def _match_delimiter(neutral: str, start: int, opening: str, closing: str) -> int:
    """Index just past the delimiter that closes the one at `start`."""
    depth = 0
    index = start
    while index < len(neutral):
        if neutral[index] == opening:
            depth += 1
        elif neutral[index] == closing:
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return len(neutral)


def _split_arguments(argument_text: str) -> list[str]:
    """Split an argument list on its top-level commas.

    Nested calls are ordinary here -- `part(0, "/", transformation)` translated
    into Java is a `split(...)[0]` -- so a plain `str.split(",")` would cut one
    argument into three.
    """
    arguments: list[str] = []
    depth = 0
    current: list[str] = []
    for char in argument_text:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        if char == "," and depth == 0:
            arguments.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    tail = "".join(current).strip()
    if tail:
        arguments.append(tail)
    return arguments


def _collect_declarations(neutral: str, start: int, end: int) -> dict[str, str]:
    return {
        match.group("name"): re.sub(r"\s+", "", match.group("type"))
        for match in _DECLARATION.finditer(neutral, start, end)
    }


def _region_for(regions: list[Region], offset: int) -> Region | None:
    """The innermost region containing `offset`, or None outside every region."""
    best: Region | None = None
    for region in regions:
        if region.start <= offset < region.end:
            if best is None or (region.end - region.start) < (best.end - best.start):
                best = region
    return best


def _scan_regions(source: MopSource, body_start: int, body_end: int) -> None:
    """Walk the specification body once, classifying every top-level construct.

    The grammar is flat enough that one pass with a delimiter counter is the whole
    parser: events, handlers, the automaton and the specification's own fields and
    helper methods are all direct children of the specification block. The reason
    to walk it rather than to pattern-match line by line is the helper methods --
    they carry braces and statements that look exactly like an event body, and
    only their position tells them apart.
    """
    neutral = source.neutral
    index = body_start
    while index < body_end:
        char = neutral[index]
        if char.isspace():
            index += 1
            continue

        alias = _ALIAS_DECL.match(neutral, index)
        if alias:
            source.aliases[alias.group("name")] = alias.group("target")
            index = alias.end()
            continue

        event = _EVENT_DECL.match(neutral, index)
        if event:
            name = event.group("name")
            open_brace = _find_body_brace(neutral, event.end(), body_end)
            if open_brace < 0:
                index = event.end()
                continue
            close = _match_delimiter(neutral, open_brace, "{", "}")
            source.regions.append(Region("body", name, open_brace + 1, close - 1))
            source.declared_events.append(name)
            source.event_parameters[name] = _collect_declarations(neutral, event.end(), open_brace)
            if "creation" in (event.group("modifiers") or ""):
                source.creation_events.add(name)
            for start, end in _condition_spans(neutral, event.end(), open_brace):
                source.regions.append(Region("condition", name, start, end))
            index = close
            continue

        handler = _HANDLER_DECL.match(neutral, index)
        if handler:
            open_brace = neutral.index("{", handler.start())
            close = _match_delimiter(neutral, open_brace, "{", "}")
            source.regions.append(Region(f"@{handler.group('name')}", handler.group("name"), open_brace + 1, close - 1))
            index = close
            continue

        automaton = _AUTOMATON_DECL.match(neutral, index)
        if automaton:
            end = _automaton_end(neutral, automaton.end(), body_end)
            source.regions.append(Region("automaton", automaton.group("kind"), automaton.end(), end))
            index = end
            continue

        # Anything else is a specification-level declaration: a field, an
        # initializer, or a helper method. A method ends at its closing brace and
        # a field at its semicolon, and which one it is is decided by whichever
        # comes first at depth zero.
        index = _skip_member(neutral, index, body_end, source)


def _find_body_brace(neutral: str, start: int, limit: int) -> int:
    """The `{` that opens an event body: the first one outside every parenthesis.

    `condition(...)` and `args(...)` sit between the event declaration and its
    body and contain no braces, but generics and array initialisers in a pointcut
    would, so the depth counter is what makes this safe rather than the absence of
    braces in today's files.
    """
    depth = 0
    index = start
    while index < limit:
        char = neutral[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "{" and depth == 0:
            return index
        index += 1
    return -1


def _condition_spans(neutral: str, start: int, limit: int) -> list[tuple[int, int]]:
    """Every `condition(...)` span in an event's pointcut section."""
    spans: list[tuple[int, int]] = []
    for match in re.finditer(r"\bcondition\s*\(", neutral[start:limit]):
        open_paren = start + match.end() - 1
        close = _match_delimiter(neutral, open_paren, "(", ")")
        spans.append((open_paren + 1, close - 1))
    return spans


def _automaton_end(neutral: str, start: int, limit: int) -> int:
    """Where an `fsm`/`ere` section stops.

    It stops at the next top-level construct, because neither form has a closing
    token of its own: an `ere` is one expression and an `fsm` is a run of
    bracketed state blocks. Scanning for the next construct keyword outside every
    bracket is what ends it without inventing a terminator the grammar lacks.
    """
    depth = 0
    index = start
    while index < limit:
        char = neutral[index]
        if char in "[({":
            depth += 1
        elif char in "])}":
            depth -= 1
        elif depth == 0:
            if neutral.startswith("@", index):
                return index
            for keyword in ("event ", "alias ", "fsm ", "ere "):
                if neutral.startswith(keyword, index) and (index == 0 or not neutral[index - 1].isalnum()):
                    return index
        index += 1
    return limit


def _skip_member(neutral: str, start: int, limit: int, source: MopSource) -> int:
    """Consume one specification-level member, recording the symbols it declares."""
    depth = 0
    index = start
    while index < limit:
        char = neutral[index]
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        elif char == "{" and depth == 0:
            close = _match_delimiter(neutral, index, "{", "}")
            # A helper method body: its statements are specification-level, and a
            # predicate site inside one is attributable to the specification
            # rather than to any event.
            source.regions.append(Region("spec-body", "<spec-body>", index + 1, close - 1))
            # No symbols are harvested here: a member that opens a brace is a
            # helper method or an initializer, and its parameters are local to it.
            # Recording them as specification fields would let one shadow the
            # field an event of the same name really binds.
            return close
        elif char == ";" and depth == 0:
            source.fields.update(_collect_declarations(neutral, start, index + 1))
            return index + 1
        index += 1
    return limit


def _collect_sites(source: MopSource) -> None:
    neutral = source.neutral
    for match in _GRAPH_SITE.finditer(neutral):
        open_paren = neutral.index("(", match.end("op"))
        close = _match_delimiter(neutral, open_paren, "(", ")")
        arguments = _split_arguments(neutral[open_paren + 1 : close - 1])[1:]
        region = _region_for(source.regions, match.start())
        prefix = neutral[max(0, match.start() - 2) : match.start()].strip()
        source.sites.append(
            Site(
                file=source.path.name,
                spec=source.spec,
                owner=region.owner if region else "<unattributed>",
                site_kind=region.kind if region else "<unattributed>",
                operation=GRAPH_OPERATIONS[match.group("op")],
                substrate=match.group("substrate"),
                predicate=match.group("predicate"),
                arguments=tuple(re.sub(r"\s+", " ", argument) for argument in arguments),
                line=source.line_of(match.start()),
                source_negated=prefix.endswith("!"),
                snippet=" ".join(source.text[match.start() : close].split()),
            )
        )

    for match in _ACCEPTING_SITE.finditer(neutral):
        open_paren = neutral.index("(", match.end("op"))
        close = _match_delimiter(neutral, open_paren, "(", ")")
        region = _region_for(source.regions, match.start())
        source.sites.append(
            Site(
                file=source.path.name,
                spec=source.spec,
                owner=region.owner if region else "<unattributed>",
                site_kind=region.kind if region else "<unattributed>",
                operation=ACCEPTING_STATE_OPERATIONS[match.group("op")],
                substrate=match.group("substrate"),
                predicate="",
                arguments=tuple(_split_arguments(neutral[open_paren + 1 : close - 1])),
                line=source.line_of(match.start()),
                source_negated=False,
                snippet=" ".join(source.text[match.start() : close].split()),
            )
        )

    source.sites.sort(key=lambda site: site.line)


# `epsilon` is the empty word of an `ere`, not an event. It is the one reserved
# identifier these expressions use.
_ERE_RESERVED = {"epsilon"}

_FSM_STATE = re.compile(r"(?P<name>\w+)\s*\[")
_FSM_TRANSITION = re.compile(r"(?P<event>\w+)\s*->\s*(?P<target>\w+)")
_ERE_IDENTIFIER = re.compile(r"[A-Za-z_$]\w*")


@dataclass(frozen=True)
class Alphabet:
    """What a specification declares and what its automaton actually names.

    The two are not the same set, in either direction, and both directions are
    defects with different consequences. An event declared and never named is an
    *orphan accuser*: it is woven, it fires, and in the `jca_android` set 17 of
    them accuse from outside the automaton, which is how a specification reports a
    violation for a call its own ordering never modelled. An event named and never
    declared is the reverse -- the automaton references an alphabet symbol the
    generator has no advice for -- and the archived set has two.

    `referenced` is a multiset, and deliberately so. An `fsm` names the same event
    once per state where the call is legal, and the count is what tells a benign
    self-loop added at every reachable state from one added at a single one.
    """

    kind: str
    declared: tuple[str, ...]
    referenced: tuple[str, ...]
    states: tuple[str, ...]

    @property
    def has_automaton(self) -> bool:
        return bool(self.kind)

    @property
    def orphans(self) -> tuple[str, ...]:
        """Declared, never named by the automaton -- accusers outside the ordering."""
        named = set(self.referenced)
        return tuple(name for name in self.declared if name not in named)

    @property
    def undeclared(self) -> tuple[str, ...]:
        """Named by the automaton, never declared -- symbols with no advice."""
        declared = set(self.declared)
        seen: list[str] = []
        for name in self.referenced:
            if name not in declared and name not in seen:
                seen.append(name)
        return tuple(seen)

    @property
    def duplicates(self) -> tuple[str, ...]:
        """Event names declared more than once, over different signatures.

        The generator keys advice by name, so the second declaration is the one
        that survives and the first is woven nowhere. `jca/GCMParameterSpecSpec`
        is the live case and it is allow-listed, never repaired -- it is frozen.
        """
        seen: dict[str, int] = {}
        for name in self.declared:
            seen[name] = seen.get(name, 0) + 1
        return tuple(name for name, count in seen.items() if count > 1)

    def occurrences(self, event: str) -> int:
        return self.referenced.count(event)


def _read_alphabet(source: MopSource) -> Alphabet:
    declared = tuple(source.declared_events)
    automaton = next((region for region in source.regions if region.kind == "automaton"), None)
    if automaton is None:
        return Alphabet(kind="", declared=declared, referenced=(), states=())

    text = source.neutral[automaton.start : automaton.end]
    if automaton.owner == "fsm":
        states = tuple(match.group("name") for match in _FSM_STATE.finditer(text))
        referenced = tuple(match.group("event") for match in _FSM_TRANSITION.finditer(text))
        return Alphabet(kind="fsm", declared=declared, referenced=referenced, states=states)

    # An `ere` is one expression: every identifier in it is an event except the
    # empty word.
    referenced = tuple(
        name for name in _ERE_IDENTIFIER.findall(text) if name not in _ERE_RESERVED
    )
    return Alphabet(kind="ere", declared=declared, referenced=referenced, states=())


def _delimiter_imbalance(neutral: str) -> str:
    """The first delimiter defect in a file, described, or the empty string.

    A `.mop` file whose parentheses do not balance cannot be walked, and the
    frozen `jca` set holds exactly one: `SecretKeySpecSpec.mop` carries a stray
    `)` after its `c1` condition. It is frozen, so it is not repaired -- it is
    reported, so that every gate built on this reader skips it with a reason and
    counts the skip, instead of reading half a file and calling the result a
    verdict.
    """
    for opening, closing, name in (("(", ")", "parenthesis"), ("{", "}", "brace"), ("[", "]", "bracket")):
        depth = 0
        for index, char in enumerate(neutral):
            if char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth < 0:
                    line = neutral.count("\n", 0, index) + 1
                    return f"unbalanced {name}: unmatched `{closing}` at line {line}"
        if depth > 0:
            return f"unbalanced {name}: {depth} unclosed `{opening}`"
    return ""


def read_mop(path: Path) -> MopSource:
    """Parse one `.mop` file into regions, symbols and predicate sites.

    A file with no specification block at all -- the `generic_new` set has 17 of
    them, event declarations and nothing else -- parses to an empty source rather
    than an error. The gates built on this reader must be able to skip such a file
    declaredly and count the skip, which they cannot do if reading it throws.
    """
    text = path.read_text(encoding="utf-8")
    neutral = neutralize(text)

    imbalance = _delimiter_imbalance(neutral)
    if imbalance:
        return MopSource(path=path, spec=path.stem, text=text, neutral=neutral, parse_error=imbalance)

    spec_name = path.stem
    body_start = -1
    for match in _SPEC_DECL.finditer(neutral):
        keyword = match.group("name")
        if keyword in {"if", "for", "while", "switch", "catch", "return", "import", "package"}:
            continue
        open_paren = match.end() - 1
        after_params = _match_delimiter(neutral, open_paren, "(", ")")
        remainder = neutral[after_params:]
        if remainder.lstrip().startswith("{"):
            spec_name = keyword
            body_start = after_params + remainder.index("{")
            break

    source = MopSource(path=path, spec=spec_name, text=text, neutral=neutral)
    if body_start < 0:
        return source

    body_end = _match_delimiter(neutral, body_start, "{", "}") - 1
    _scan_regions(source, body_start + 1, body_end)
    _collect_sites(source)
    source.alphabet = _read_alphabet(source)
    return source


# --------------------------------------------------------------------- pass 3


# The 15 columns of the delta's Output contract, in its order.
#
# Two of them needed a decision the contract leaves open, recorded here so the
# next reader does not have to re-derive it:
#
# * `site_kind` is the *placement* -- `condition`, `body`, `@match`, `@fail` --
#   because that is the vocabulary the placement invariants are written in
#   ("classifies any read site as `condition`").
# * `verdict` therefore carries what the site *does* and how that reads against
#   the placement rules, as `<operation>:<class>` -- `read:condition-guard`,
#   `write:acceptance`, `remove:fail-handler`. It is the analyzer's judgment of
#   the site, which is what a verdict is, and it is the column the closure gate
#   filters reads and writes on.
#
# The five judgment columns are carried, not derived: the source cannot say which
# CrySL clause a site translates, which mechanism a chain was wired with, or why
# a write was deliberately left off the acceptance point. They are written by the
# tasks that make those decisions and preserved across every regeneration.
COLUMNS = (
    "file",
    "event",
    "site_kind",
    "polarity",
    "guard",
    "arity",
    "predicate",
    "position_types",
    "splitter",
    "clause",
    "mechanism",
    "verdict",
    "disposition",
    "reason",
    "automaton_membership",
)

CARRIED_COLUMNS = ("guard", "clause", "mechanism", "disposition", "reason")

# Where a write belongs. A CrySL rule ensures its predicate *after* its ORDER
# accepts, so the acceptance point is the `@match` handler -- reached directly or
# through an `alias`. A write anywhere else marks an object the rule has not
# finished judging, which is how a set ends up ensuring `generatedKey` for a key
# whose generator was never initialised.
_ACCEPTANCE_HANDLERS = re.compile(r"^@match\d*$")

_SPLITTER = re.compile(r"\.\s*split\s*\(")


def _placement(site: Site) -> str:
    """The `site_kind` column: where the site sits, in the invariants' vocabulary."""
    if site.site_kind.startswith("@"):
        return "@match" if _ACCEPTANCE_HANDLERS.match(site.site_kind) else site.site_kind
    return site.site_kind


def _verdict(site: Site) -> str:
    """The `verdict` column: the operation, and how its placement reads."""
    placement = _placement(site)
    if site.operation in ("read", "read-absent"):
        if placement == "condition":
            # INV-INS-133: a guard suppresses the transition, so an unobserved
            # predicate is reported as a wrong call sequence rather than as what
            # it is. Every read of the set sits here before the migration.
            return f"{site.operation}:condition-guard"
        return f"{site.operation}:{placement.lstrip('@') or 'body'}"
    if site.operation == "write":
        if placement == "@match":
            return "write:acceptance"
        if placement == "@fail":
            return "write:fail-handler"
        return f"write:{placement.lstrip('@') or 'body'}"
    if site.operation in ("remove", "negate"):
        return f"{site.operation}:{placement.lstrip('@') or 'body'}"
    return f"bookkeeping:{placement.lstrip('@') or 'body'}"


def _membership(source: MopSource, site: Site) -> str:
    """Whether the event carrying the site is part of the declared automaton.

    A handler is not an event and has no membership; an event the automaton never
    names is an orphan, and an orphan that accuses is a specification reporting a
    violation for a call its own ordering does not model.
    """
    if site.site_kind.startswith("@") or site.site_kind == "spec-body":
        return "n/a"
    if not source.alphabet.has_automaton:
        return "no-automaton"
    return "member" if site.owner in source.alphabet.referenced else "orphan"


def _row(source: MopSource, site: Site) -> dict[str, str]:
    types = [source.declared_type(site.owner, argument) for argument in site.arguments]
    splitters = [argument for argument in site.arguments if _SPLITTER.search(argument)]
    return {
        "file": site.file,
        "event": site.owner,
        "site_kind": _placement(site),
        "polarity": "negated" if site.operation == "read-absent" else "positive",
        "guard": "",
        "arity": str(site.arity),
        "predicate": site.predicate,
        "position_types": "|".join(types),
        "splitter": "|".join(splitters),
        "clause": "",
        "mechanism": "",
        "verdict": _verdict(site),
        "disposition": "",
        "reason": "",
        "automaton_membership": _membership(source, site),
    }


def _row_key(row: dict[str, str], ordinal: int) -> tuple[str, str, str, str, int]:
    """What identifies a row across regenerations.

    Deliberately not the line number: every edit of this change moves lines, and a
    key that moved with them would drop the judgment columns of every site in a
    file the moment that file was touched.
    """
    return (row["file"], row["event"], row["predicate"], row["verdict"].split(":")[0], ordinal)


def build_rows(sources: list[MopSource]) -> list[dict[str, str]]:
    """Every predicate site of the given sources, as graph rows.

    Sorted by file and then by the order the sites appear in it, so the emitted
    CSV is a function of the tree and nothing else -- which is what lets a
    regeneration over an unedited tree reproduce the file byte for byte.
    """
    rows: list[dict[str, str]] = []
    for source in sorted(sources, key=lambda item: item.path.name):
        for site in source.sites:
            rows.append(_row(source, site))
    return rows


def carry_judgments(rows: list[dict[str, str]], existing: list[dict[str, str]]) -> list[dict[str, str]]:
    """Copy the hand-written columns of a previous graph onto freshly read rows.

    The five judgment columns record decisions -- which clause a site translates,
    which mechanism wired it, why a write was left where it is -- and no analyzer
    can re-derive them from the source. Regenerating without carrying them would
    silently erase the record this change exists to build.
    """
    carried: dict[tuple[str, str, str, str, int], dict[str, str]] = {}
    seen: dict[tuple[str, str, str, str], int] = {}
    for row in existing:
        stem = (row["file"], row["event"], row["predicate"], row["verdict"].split(":")[0])
        ordinal = seen.get(stem, 0)
        seen[stem] = ordinal + 1
        carried[(*stem, ordinal)] = row

    seen.clear()
    for row in rows:
        stem = (row["file"], row["event"], row["predicate"], row["verdict"].split(":")[0])
        ordinal = seen.get(stem, 0)
        seen[stem] = ordinal + 1
        previous = carried.get((*stem, ordinal))
        if previous:
            for column in CARRIED_COLUMNS:
                row[column] = previous.get(column, "")
    return rows


@dataclass
class SetReport:
    """What one specification set contributed, including what was not read.

    `skipped` is not an afterthought. A gate that cannot classify a file must skip
    it, count it and say why: green by vacuity and red by absence are the two ways
    a generic gate lies, and the only defence is a report where the three numbers
    always add up to the files that exist.
    """

    name: str
    read: int = 0
    skipped: list[tuple[str, str]] = field(default_factory=list)
    rows: list[dict[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.read + len(self.skipped)


def analyze_set(set_dir: Path) -> SetReport:
    report = SetReport(name=set_dir.name)
    sources: list[MopSource] = []
    for path in sorted(set_dir.glob("*.mop")):
        source = read_mop(path)
        if source.parse_error:
            report.skipped.append((path.name, source.parse_error))
            continue
        if not source.has_specification:
            report.skipped.append((path.name, "no specification block: event declarations only"))
            continue
        report.read += 1
        sources.append(source)
    report.rows = build_rows(sources)
    return report


# ------------------------------------------------------------------------ CLI


# Every set the gates run over. The universe is enumerated from these directories
# and never written down as a number: this change adds junction specifications to
# `jca_android`, so any gate holding a literal count would fail on the day the
# first one lands, for a reason that has nothing to do with what it measures.
SPECIFICATION_SETS = (
    "jca",
    "jca_android",
    "jca_android_bug_predicate",
    "generic",
    "generic_new",
)

DEFAULT_GRAPH = Path("data/jca_android/predicate_graph.csv")


def _resolve_sets(root: Path, selection: str) -> list[Path]:
    names = SPECIFICATION_SETS if selection == "all" else (selection,)
    return [root / name for name in names if (root / name).is_dir()]


def read_graph(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_graph(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--specs-root",
        type=Path,
        default=Path("../rvsec/rvsec-mop/src/main/resources"),
        help="directory holding the specification sets",
    )
    parser.add_argument("--sets", default="all", help="`all` or the name of one set")
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH, help="the graph CSV")
    parser.add_argument("--emit", action="store_true", help="rewrite the graph CSV")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    arguments = parser.parse_args(argv)

    set_dirs = _resolve_sets(arguments.specs_root, arguments.sets)
    if not set_dirs:
        print(f"no specification set found under {arguments.specs_root}", file=sys.stderr)
        return 2

    reports = [analyze_set(set_dir) for set_dir in set_dirs]

    target = next((report for report in reports if report.name == "jca_android"), None)
    if arguments.emit and target is not None:
        rows = carry_judgments(list(target.rows), read_graph(arguments.graph))
        write_graph(arguments.graph, rows)

    payload = {
        "universe": sum(report.total for report in reports),
        "sets": [
            {
                "set": report.name,
                "files": report.total,
                "read": report.read,
                "skipped": [{"file": name, "reason": reason} for name, reason in report.skipped],
                "sites": len(report.rows),
            }
            for report in reports
        ],
    }

    if arguments.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"universe: {payload['universe']} .mop files enumerated under {arguments.specs_root}")
        for report in reports:
            print(
                f"  {report.name:26s} files={report.total:3d} read={report.read:3d} "
                f"skipped={len(report.skipped):2d} sites={len(report.rows):3d}"
            )
            for name, reason in report.skipped:
                print(f"      skipped {name}: {reason}")

    # The reader itself never fails a run: it reports. The gates built on it
    # (G-ACC, G-PRED2, the placement checks) are what carry exit codes.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

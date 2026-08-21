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
    # The specification's own parameter list -- the monitor's index. These names
    # are NOT visible inside `@match`/`@fail` handlers, which is a compile-time
    # fact and INV-INS-136(d)'s whole subject.
    parameters: dict[str, str] = field(default_factory=dict)
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
    parameters: dict[str, str] = {}
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
            parameters = _collect_declarations(neutral, open_paren, after_params)
            body_start = after_params + remainder.index("{")
            break

    source = MopSource(path=path, spec=spec_name, text=text, neutral=neutral)
    if body_start < 0:
        return source
    source.parameters.update(parameters)

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


# ------------------------------------------------------- the enumerated universe


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


# ---------------------------------------------------------------- the gates


# The dispositions that close a read without a producer in the set. Each names a
# reason the edge cannot be wired, and each is a decision somebody wrote down --
# which is the difference between a gap that is known and a gap that is missing.
RECORDED_READ_DISPOSITIONS = {
    "unclosable",           # no producing rule exists at all (`preparedEC`)
    "unmonitored-producer",  # the producing rule has no `.mop` in the set
    "unmonitored-consumer",  # the consuming rule has no `.mop` in the set
    "vacuous",              # the clause binds a value no event of the rule binds
    "propagation",          # the read translates no clause; it forwards a mark
}

# The disposition that closes a write with no reader: an `ENSURES`-only dead end,
# recorded rather than given a fabricated reader.
RECORDED_WRITE_DISPOSITIONS = {"omission", "propagation"}

# A junction specification, by name. The convention is what makes the four rules
# of INV-INS-136 checkable at all: they apply to mechanism B and to nothing else,
# and a typestate specification that fails on an unexpected call is doing its job.
JUNCTION_SUFFIX = "Junction.mop"


# The one set this change edits. The placement invariants and the closure gate
# are its contract and nobody else's: `jca` is frozen because it produced
# published measurements, and the archived set is a record. Running those gates
# against either would report, correctly and uselessly, that a frozen file is
# still what it was frozen as.
TARGET_SET = "jca_android"


@dataclass(frozen=True)
class Finding:
    """One gate hit, identified by something stable enough to allow-list.

    The key deliberately excludes line numbers and messages: an allow-list entry
    or a baseline row that stopped matching because a file was reformatted would
    reappear as a new finding, and a gate that cries wolf on formatting is a gate
    that gets muted.
    """

    gate: str
    spec_set: str
    file: str
    subject: str
    message: str
    # `informative` is a finding in a set the gate does not govern -- the orphan
    # in `generic/FSM246.mop` is real and is nobody's task. It is reported so that
    # the gate is visibly running over the whole universe, and it does not fail a
    # run, because failing on it would make the only cure to stop running there.
    severity: str = "failing"

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.gate, self.spec_set, self.file, self.subject)


def gate_acc(report: SetReport, sources: list[MopSource]) -> list[Finding]:
    """G-ACC (INV-INS-135): the declared alphabet and the automaton's, both ways.

    An event declared and never named by the automaton is an *orphan accuser*: it
    is woven, it fires, and it can report a violation for a call the specification's
    own ordering does not model. An event named and never declared is the mirror
    image -- an alphabet symbol with no advice behind it, so the transition it
    labels can never be taken.

    A third direction rides along: an event name declared twice. The generator
    keys advice by name, so the second declaration wins and the first is woven
    nowhere; the file reads as if both were live.
    """
    findings: list[Finding] = []
    for source in sources:
        alphabet = source.alphabet
        if not alphabet.has_automaton:
            continue
        for event in alphabet.orphans:
            findings.append(
                Finding(
                    "G-ACC",
                    report.name,
                    source.path.name,
                    event,
                    f"`{event}` is declared and never named by the {alphabet.kind}: "
                    "it fires outside the ordering it belongs to",
                )
            )
        for event in alphabet.undeclared:
            findings.append(
                Finding(
                    "G-ACC",
                    report.name,
                    source.path.name,
                    event,
                    f"the {alphabet.kind} names `{event}`, which no event declares: "
                    "the transition it labels can never be taken",
                )
            )
        for event in alphabet.duplicates:
            findings.append(
                Finding(
                    "G-ACC",
                    report.name,
                    source.path.name,
                    event,
                    f"`{event}` is declared more than once; the generator keys advice by "
                    "name, so only the last declaration is woven",
                )
            )
    return findings


def gate_placement(report: SetReport) -> list[Finding]:
    """INV-INS-133 and INV-INS-134: reads out of guards, writes at acceptance.

    A read inside `condition(...)` compiles to a boolean guard: when it is false
    the transition does not happen, so an unobserved predicate is reported as a
    wrong call sequence instead of as an unsatisfied constraint. That is the
    mechanism behind the set's largest published error category, and it is why the
    reads move to event bodies where they can accuse about what they saw.

    A write belongs at the rule's acceptance point, because that is when the rule
    has finished judging the object it is about to vouch for. A write kept
    elsewhere is not forbidden -- it needs a recorded reason, in the graph, where
    the next reader will find it.
    """
    findings: list[Finding] = []
    for row in report.rows:
        operation = row["verdict"].split(":")[0]
        if operation in ("read", "read-absent") and row["site_kind"] == "condition":
            findings.append(
                Finding(
                    "INV-INS-133",
                    report.name,
                    row["file"],
                    f"{row['event']}/{row['predicate']}",
                    "a predicate read inside `condition(...)` suppresses the transition "
                    "instead of accusing at it",
                )
            )
        if operation == "write" and row["verdict"] != "write:acceptance" and not row["reason"]:
            findings.append(
                Finding(
                    "INV-INS-134",
                    report.name,
                    row["file"],
                    f"{row['event']}/{row['predicate']}",
                    f"a write at `{row['verdict']}` rather than at the acceptance point, "
                    "with no recorded reason",
                )
            )
    return findings


def gate_pred2(report: SetReport) -> list[Finding]:
    """G-PRED2 (INV-INS-137): the graph closes, or says in writing why it does not.

    Every read needs a producer somewhere in the set or a disposition naming the
    reason there is none; every write needs a reader or a recorded deliberate
    omission. Over a set with no predicates the correct answer is zero rows and
    green -- the closure of an empty graph is the empty graph.
    """
    written: set[str] = set()
    read: set[str] = set()
    for row in report.rows:
        operation = row["verdict"].split(":")[0]
        if operation == "write":
            written.add(row["predicate"])
        elif operation in ("read", "read-absent"):
            read.add(row["predicate"])

    findings: list[Finding] = []
    for row in report.rows:
        operation = row["verdict"].split(":")[0]
        subject = f"{row['event']}/{row['predicate']}"
        if operation in ("read", "read-absent"):
            if row["predicate"] not in written and row["disposition"] not in RECORDED_READ_DISPOSITIONS:
                findings.append(
                    Finding(
                        "G-PRED2",
                        report.name,
                        row["file"],
                        subject,
                        f"`{row['predicate']}` is read and written by no specification of the "
                        "set, and no disposition names the absent producer",
                    )
                )
        elif operation == "write":
            if row["predicate"] not in read and row["disposition"] not in RECORDED_WRITE_DISPOSITIONS:
                findings.append(
                    Finding(
                        "G-PRED2",
                        report.name,
                        row["file"],
                        subject,
                        f"`{row['predicate']}` is written and read by no specification of the "
                        "set, and no deliberate omission is recorded for it",
                    )
                )
    return findings


def gate_junction_rules(report: SetReport, sources: list[MopSource]) -> list[Finding]:
    """INV-INS-136 (a), (b) and (d), decided from the `.mop` alone.

    Each of the three exists because the pilot measured its violation, and each is
    gated rather than reviewed: a rule checked once per chain is not protected
    against the edit that comes after the review.

    (a) A consumer event declared `creation` starts a monitor at the consuming
        call. The producer's mark was written on an instance that monitor never
        saw, so the conforming trace is the one that gets accused.

    (b) A junction's automaton must be total over its own alphabet. A state with
        no transition for an event sends that event to `fail`, and the events that
        arrive at unexpected states here are the cross-product instances -- pairs
        whose parameters never met in a single event. They must stay silent, which
        in an `fsm` means a benign self-loop at every state.

    (d) `@match` and `@fail` handlers cannot see the specification's parameters;
        only monitor fields are in scope. Naming a parameter there does not fail
        the gate at runtime -- it fails to compile, which is worse, because it
        fails late and far from the edit.
    """
    findings: list[Finding] = []
    for source in sources:
        if not source.path.name.endswith(JUNCTION_SUFFIX):
            continue

        consumers = {
            site.owner
            for site in source.sites
            if site.operation in ("read", "read-absent") and not site.site_kind.startswith("@")
        }
        for event in sorted(consumers & source.creation_events):
            findings.append(
                Finding(
                    "INV-INS-136(a)",
                    report.name,
                    source.path.name,
                    event,
                    f"the consumer event `{event}` is declared `creation`: a monitor created at "
                    "the consuming call never saw the producer, and accuses the conforming trace",
                )
            )

        alphabet = source.alphabet
        if alphabet.kind == "fsm":
            transitions = _fsm_transitions(source)
            for state in alphabet.states:
                missing = [event for event in dict.fromkeys(alphabet.declared) if event not in transitions.get(state, set())]
                for event in missing:
                    findings.append(
                        Finding(
                            "INV-INS-136(b)",
                            report.name,
                            source.path.name,
                            f"{state}/{event}",
                            f"state `{state}` has no transition for `{event}`, so a disconnected "
                            "join arriving there fails instead of staying silent",
                        )
                    )

        for region in source.regions:
            if not region.kind.startswith("@"):
                continue
            body = source.neutral[region.start : region.end]
            named = {name for name in _ERE_IDENTIFIER.findall(body)}
            for parameter in sorted(named & set(source.parameters) - set(source.fields)):
                findings.append(
                    Finding(
                        "INV-INS-136(d)",
                        report.name,
                        source.path.name,
                        f"{region.kind}/{parameter}",
                        f"`{parameter}` is a specification parameter, which is not in scope "
                        f"inside `{region.kind}`; handler state belongs in a monitor field",
                    )
                )
    return findings


def _fsm_transitions(source: MopSource) -> dict[str, set[str]]:
    """The out-alphabet of each state, read off the `fsm` block."""
    automaton = next((region for region in source.regions if region.kind == "automaton"), None)
    if automaton is None or automaton.owner != "fsm":
        return {}

    text = source.neutral[automaton.start : automaton.end]
    transitions: dict[str, set[str]] = {}
    for match in _FSM_STATE.finditer(text):
        state = match.group("name")
        open_bracket = text.index("[", match.start())
        close = _match_delimiter(text, open_bracket, "[", "]")
        transitions[state] = {
            transition.group("event")
            for transition in _FSM_TRANSITION.finditer(text[open_bracket:close])
        }
    return transitions


@dataclass
class GateRun:
    """Everything one run of the gate suite produced, skips included."""

    findings: list[Finding] = field(default_factory=list)
    informative: list[Finding] = field(default_factory=list)
    allowed: list[Finding] = field(default_factory=list)
    reports: list[SetReport] = field(default_factory=list)
    gate_skips: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def universe(self) -> int:
        return sum(report.total for report in self.reports)

    @property
    def read(self) -> int:
        return sum(report.read for report in self.reports)

    @property
    def skipped(self) -> int:
        return sum(len(report.skipped) for report in self.reports)


def read_allowlist(path: Path) -> set[tuple[str, str, str, str]]:
    """Findings that are deliberately permanent, keyed like a `Finding`.

    An allow-list row is a decision with a reason attached, not a mute button:
    every row of `gate_allowlist.csv` carries the measurement behind it and the
    task that owns it. A `*` in the spec or event column allows a family, which is
    how eight instances of one idiom are recorded as one reason.
    """
    if not path.is_file():
        return set()
    allowed: set[tuple[str, str, str, str]] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            allowed.add((row["gate"], row["set"], row["spec"], row["event_or_state"]))
    return allowed


def _is_allowed(finding: Finding, allowed: set[tuple[str, str, str, str]]) -> bool:
    spec = finding.file.removesuffix(".mop")
    subject = finding.subject
    candidates = {
        (finding.gate, finding.spec_set, spec, subject),
        (finding.gate, finding.spec_set, spec, "*"),
        (finding.gate, finding.spec_set, "*", "*"),
    }
    return bool(candidates & allowed)


def run_gates(
    specs_root: Path,
    selection: str = "all",
    graph: Path = DEFAULT_GRAPH,
    allowlist: Path | None = None,
) -> GateRun:
    """The whole structural suite over the enumerated universe.

    The graph rows of `jca_android` are merged with the committed record before
    the gates read them, because the judgment columns -- the dispositions that
    close an edge nobody can wire, the reasons a write stays where it is -- live
    there and nowhere else. Every other set is judged from its source alone,
    which for the 145 predicate-free files means zero rows and green.
    """
    allowed = read_allowlist(allowlist) if allowlist else set()
    run = GateRun()

    for set_dir in _resolve_sets(specs_root, selection):
        report = analyze_set(set_dir)
        sources = [
            read_mop(path)
            for path in sorted(set_dir.glob("*.mop"))
            if path.name not in {name for name, _ in report.skipped}
        ]
        if report.name == "jca_android":
            report.rows = carry_judgments(report.rows, read_graph(graph))

        run.reports.append(report)

        produced = gate_acc(report, sources) + gate_junction_rules(report, sources)
        if report.name == TARGET_SET:
            produced += gate_placement(report) + gate_pred2(report)
        else:
            for gate in ("INV-INS-133", "INV-INS-134", "G-PRED2"):
                run.gate_skips.append(
                    (
                        gate,
                        report.name,
                        "the placement and closure contract governs the migrated set only; "
                        f"`{report.name}` is frozen or predicate-free",
                    )
                )
            produced = [
                finding if report.name == TARGET_SET else _informative(finding)
                for finding in produced
            ]

        for finding in produced:
            if _is_allowed(finding, allowed):
                run.allowed.append(finding)
            elif finding.severity == "informative":
                run.informative.append(finding)
            else:
                run.findings.append(finding)

    return run


def _informative(finding: Finding) -> Finding:
    """The same finding, in a set the gate reports on but does not govern."""
    return Finding(
        finding.gate,
        finding.spec_set,
        finding.file,
        finding.subject,
        finding.message,
        severity="informative",
    )


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
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=Path("data/jca_android/gate_allowlist.csv"),
        help="findings recorded as deliberately permanent",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    arguments = parser.parse_args(argv)

    set_dirs = _resolve_sets(arguments.specs_root, arguments.sets)
    if not set_dirs:
        print(f"no specification set found under {arguments.specs_root}", file=sys.stderr)
        return 2

    if arguments.emit:
        emitted = analyze_set(arguments.specs_root / "jca_android")
        write_graph(arguments.graph, carry_judgments(list(emitted.rows), read_graph(arguments.graph)))

    run = run_gates(arguments.specs_root, arguments.sets, arguments.graph, arguments.allowlist)

    payload = {
        "universe": run.universe,
        "read": run.read,
        "skipped": run.skipped,
        "passed": run.universe - run.skipped - len({finding.file for finding in run.findings}),
        "failed": len(run.findings),
        "allowed": len(run.allowed),
        "informative": len(run.informative),
        "gate_skips": [
            {"gate": gate, "set": spec_set, "reason": reason}
            for gate, spec_set, reason in run.gate_skips
        ],
        "sets": [
            {
                "set": report.name,
                "files": report.total,
                "read": report.read,
                "skipped": [{"file": name, "reason": reason} for name, reason in report.skipped],
                "sites": len(report.rows),
            }
            for report in run.reports
        ],
        "findings": [
            {
                "gate": finding.gate,
                "set": finding.spec_set,
                "file": finding.file,
                "subject": finding.subject,
                "message": finding.message,
            }
            for finding in run.findings
        ],
    }

    if arguments.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"universe: {run.universe} .mop files enumerated under {arguments.specs_root}")
        for report in run.reports:
            print(
                f"  {report.name:26s} files={report.total:3d} read={report.read:3d} "
                f"skipped={len(report.skipped):2d} sites={len(report.rows):3d}"
            )
            for name, reason in report.skipped:
                print(f"      skipped {name}: {reason}")
        for gate, spec_set, reason in run.gate_skips:
            print(f"  gate {gate} skipped over {spec_set}: {reason}")
        print(
            f"findings: {len(run.findings)} failing, {len(run.allowed)} allow-listed, "
            f"{len(run.informative)} informative"
        )
        for finding in run.findings + run.informative:
            marker = "" if finding.severity == "failing" else " (informative)"
            print(
                f"  [{finding.gate}]{marker} {finding.spec_set}/{finding.file} "
                f"{finding.subject}: {finding.message}"
            )

    return 1 if run.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())



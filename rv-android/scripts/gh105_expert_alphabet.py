#!/usr/bin/env python3
"""Re-derive a specification set's ORDER alphabet mapping against a CrySL catalogue.

Task 11.2 of gh105, under design decision D-16: the sole oracle of `jca_android` is the
pinned expert copy `RVSec-replication-package/tools/rules/`. `order_alphabet_map.csv` was
written against `MetaCrySL/generated/api30/`, and every one of its 138 rows names an api30
symbol and an api30 line. This script re-derives the same associations against the expert
rules and reports, clause by clause, what the move costs.

The association a row carries -- *which* `.mop` event stands for *which* rule symbol -- is
a human judgement (INV-INS-138 forbids inferring it), and this script does not re-decide
it. What it re-derives is the **anchor**: given that `SecureRandomSpec.setSeed1` is the
rule's `setSeed(long)` event, which symbol is that in the expert rule, on which line, and
inside which aggregate.

Matching is by **signature and never by name**, because the two catalogues permute names
over the same calls: `KeyPairGenerator`'s `i1..i4` are a four-way permutation between the
two rules, and `Signature`'s `u1` and `u2` are swapped. A re-anchoring by name would look
mechanical and be wrong in exactly the places that matter.

The script emits two tables:

  * the map -- the same rows, re-keyed to the expert rule's symbols and line numbers;
  * the delta -- one row per association, saying whether the anchor moved by name only,
    changed shape (a different aggregate holds it), appeared, or disappeared -- plus the
    rule-side symbols each catalogue declares that no `.mop` event of the set covers.

Rows written after the oracle switch have no anchor to move: their association was decided
against the expert rule in the first place, and for most of their rules api30 generated no
file at all. Those rows are declared in `EXPERT_NATIVE_SPECS`, carried through untouched,
and reported as `expert-native` -- an origin, not a move.

Nothing here infers an association. A disposition that flips -- an event erased from the
comparison under api30 whose expert counterpart exists -- is reported as a delta row and
goes no further on this script's own strength: reopening one changes the language the
automaton is compared against, which is a decision, not a derivation. Three rows are in
that position (`MacSpec.updateBuffer`, `SecureRandomSpec.next1`/`next3`), and task 11.6
decided the first of them: `RESTORED_ROWS` carries it, with the decision written beside
the symbol it restores. The two `SecureRandomSpec` rows stay erased, undecided.

Usage:
    python scripts/gh105_expert_alphabet.py --emit map
    python scripts/gh105_expert_alphabet.py --emit delta
    python scripts/gh105_expert_alphabet.py --check      # committed == derived, exit 0/1
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
DEFAULT_MAP = REPO / "data/jca_android/order_alphabet_map.csv"
DEFAULT_EXPERT_MAP = REPO / "data/jca_android/order_alphabet_map_expert.csv"
DEFAULT_DELTA = REPO / "data/jca_android/order_alphabet_map_delta.csv"

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

MAP_FIELDS = (
    "spec",
    "mop_event",
    "order_symbol",
    "symbol_kind",
    "rule",
    "rule_line",
    "disposition",
    "reason",
)

DELTA_FIELDS = (
    "spec",
    "mop_event",
    "api30_symbol",
    "expert_symbol",
    "klass",
    "signature",
    "note",
)

# The `.mop` files of the set that pair with no rule in either catalogue. They are
# declared G-ORDER skips and carry no data row anywhere, by the mapping's own contract:
# a row of any kind takes the file out of the skip.
NO_RULE = ("IvChainJunction", "RandomStringPassword")


# The specifications of gh109 group G2, whose alphabet rows have no api30 anchor to re-key.
# They were written from the pinned expert oracle alone (D-16), for rules the withdrawn
# api30 generation mostly never produced: eight of the fourteen have no `.cryptsl` file at
# all. So there is nothing to pair a row of theirs against, and pairing the six whose file
# does exist would invent a provenance the association never had -- the rule they transcribe
# is the expert one either way, and which of them api30 happened to generate says nothing
# about where the judgement came from.
#
# Declared here rather than inferred from the filesystem, because "the api30 file is
# missing" and "this association was decided under the expert oracle" are different claims
# and only the second is true of all fourteen. A row whose `spec` is named here carries an
# expert symbol already: the re-anchoring has nothing to do, and the delta records the row
# as `expert-native`, which is an origin and not a move.
EXPERT_NATIVE_SPECS = frozenset(
    {
        "AlgorithmParameterGeneratorSpec",
        "AlgorithmParametersSpec",
        "CertPathTrustManagerParametersSpec",
        "CertificateFactorySpec",
        "DHParameterSpecSpec",
        "DSAParameterSpecSpec",
        "DigestInputStreamSpec",
        "DigestOutputStreamSpec",
        "ECGenParameterSpecSpec",
        "ECParameterSpecSpec",
        "KeyFactorySpec",
        "KeySpec",
        "KeyStoreBuilderParametersSpec",
        "MGF1ParameterSpecSpec",
        "OAEPParameterSpecSpec",
        "PKIXBuilderParametersSpec",
        "PKIXParametersSpec",
        "RSAKeyGenParameterSpecSpec",
        "SecretKeyFactorySpec",
        "TrustAnchorSpec",
        "X509EncodedKeySpecSpec",
    }
)


# The pairing is by signature, and a signature the api30 rule declares **twice** cannot be
# paired that way: both copies are compatible with the same expert event, and picking one
# would be an inference. Every such case in this set is in `Mac.cryptsl`, whose generator
# transcribed two overloads as one signature -- the defect is in its source too
# (`MetaCrySL samples/jca/base/Mac.cryptsl:17-18,26,28`), and `order_alphabet_map.csv`
# already says so in the reasons of the `MacSpec.g1`, `g2` and `updateBytes` rows. They are
# settled here by name, with the call each one actually stands for named next to it, and
# `None` withdraws the row: the api30 symbol was a duplicate and the expert rule writes a
# different call under that name.
DUPLICATE_OVERRIDES: dict[tuple[str, str], tuple[str | None, str]] = {
    ("Mac", "g1"): (
        "g1",
        "`getInstance(String)`; api30 declares this signature as both g1 and g2, and the "
        "expert rule writes it once, as g1",
    ),
    ("Mac", "g2"): (
        "g2",
        "the provider overload the `.mop` event observes, `getInstance(String, String)`. "
        "api30's g2 repeats g1's one-argument signature; the expert rule writes the "
        "overload as `g2: getInstance(algorithm, _)`",
    ),
    ("Mac", "u2"): (
        "u2",
        "`update(byte[])`; api30 declares this signature as both u2 and u4, and the expert "
        "rule writes it once, as u2",
    ),
    ("Mac", "u4"): (
        None,
        "api30's u4 is its second declaration of `update(byte[])`, and the map carries a "
        "row for it only so that no symbol of the rule goes unclaimed. The expert rule "
        "writes `u4: update(ByteBuffer)` -- a different call, which this set observes at "
        "`MacSpec.updateBuffer` -- so the duplicate has no expert counterpart and the row "
        "that held it is withdrawn",
    ),
}


# The rows the api30 map erases and the expert rule does name: `order_symbol` empty on the
# way in, a symbol of the sole oracle on the way out. This is the one table here that
# *widens* what the gate compares, so it is the one table that cannot be a derivation --
# each entry is a decision of task 11.6, and the reason says which. It is keyed by
# (`spec`, `mop_event`) and not by symbol, because the row it reopens has no symbol to key
# on. The input row is left alone: `order_alphabet_map.csv` answers to api30, where the
# erasure is correct, and a restoration written there would be a claim about a call that
# catalogue never declared.
RESTORED_ROWS: dict[tuple[str, str], tuple[str, str]] = {
    ("MacSpec", "updateBuffer"): (
        "u4",
        "`update(ByteBuffer)`, the rule's `u4: update(preInputByteBuffer)` "
        "(`Mac.crysl:9,30`), held by `Update` (`:31`). The row was erased under api30, "
        "correctly: that rule declared no such overload, and its `u4` was a second "
        "declaration of `update(byte[])`. Restored at task 11.6 against the sole oracle, "
        "and the restoration is load-bearing rather than decorative, which measurement "
        "settled against the expectation the task was written with. Against the `ere` as "
        "it stood the restoration is verdict-neutral -- that `ere` accepted zero updates "
        "through `(update | ... | updateBuffer)*`, so the witness `g1 i1 f1` stands "
        "whether or not `updateBuffer` carries a symbol. Against the repaired `ere`, "
        "which writes `+` where the rule writes `Update+`, it is what makes the repair "
        "hold: G-ORDER erases an unmapped event as an epsilon move, so an erased symbol "
        "inside a `+` satisfies the `+` with no call at all, and `g1 i1 f1` survives the "
        "repair unchanged. Measured both ways on 2026-08-26. The two changes are separate "
        "commits because one moves an accusation and the other does not, and this one "
        "goes first: a record whose effect appears only once the automaton catches up is "
        "still a record",
    ),
}


# A reason that names the api30 rule -- its line, its symbol, or a wart only it had -- is
# false against the sole oracle, and a record whose reason contradicts its own anchor is
# worse than one with no reason. These are the rows whose prose had to be rewritten, keyed
# by the row and the api30 symbol it carried; every other reason of the file survives
# verbatim because its claim holds against both catalogues. Each replacement was checked
# against the expert rule text on 2026-08-26.
REASON_OVERRIDES: dict[tuple[str, str, str], str] = {
    ("CipherInputStreamSpec", "c1", "c2"): (
        "the pointcut is `call(public CipherInputStream.new(InputStream, Cipher))`, and "
        "under the sole oracle that is the whole constructor alphabet: "
        "`CipherInputStream.crysl:11` declares `c1: CipherInputStream(inputStream, "
        "cipher)` and no other constructor. api30 also declared the one-argument "
        "`CipherInputStream(is)` -- `protected` in android-30's "
        "`javax/crypto/CipherInputStream`, so no application call site could reach it -- "
        "and named it inside its `Constructs`. What was a deliberate narrowing of the "
        "pointcut against the old anchor is the alphabet itself against this one"
    ),
    ("CipherOutputStreamSpec", "c1", "c2"): (
        "the pointcut is `call(public CipherOutputStream.new(OutputStream, Cipher))`, and "
        "under the sole oracle that is the whole constructor alphabet: "
        "`CipherOutputStream.crysl:12` declares `c1: CipherOutputStream(outputStream, "
        "cipher)` and no other. api30 also declared the one-argument "
        "`CipherOutputStream(os)`, `protected` in android-30 and unreachable from an "
        "application call site; the expert rule does not name it"
    ),
    ("CipherOutputStreamSpec", "w1", "w1"): (
        "`write(int)`, which the expert rule types by name: `w1: write(specifiedByte)` "
        "over `int specifiedByte` (`CipherOutputStream.crysl:9,15`)"
    ),
    ("CipherOutputStreamSpec", "w1", "w2"): (
        "the second half of the same pointcut: `write(byte[])`, the rule's "
        "`w2: write(data)` over `byte[] data` (`CipherOutputStream.crysl:6,16`). Under "
        "api30 this row carried a warning, because that rule declared the byte-array "
        "parameter under an object literally named `byte` and reading its `w2` as the "
        "integer overload was a live risk; the expert rule types both positions and the "
        "risk is gone"
    ),
    ("CipherOutputStreamSpec", "fl", ""): (
        "`flush()`. The rule's EVENTS declare no flush event at all -- `Con`, "
        "`Write := w1 | w2 | w3` and `Close` are the whole alphabet "
        "(`CipherOutputStream.crysl:11-21`) -- so the call is outside the rule's alphabet "
        "and has no ORDER symbol. Same reading as PBEKeySpecSpec.f1. The erasure exposes a "
        "divergence rather than hiding one: the `ere` puts `fl` inside the mandatory "
        "`(w1 | w2 | fl)+`, so a stream that only flushes reaches `cl`"
    ),
    ("MacSpec", "g1", "g1"): (
        "`getInstance(String)`, the rule's `g1: getInstance(algorithm)` "
        "(`Mac.crysl:19`). The association needed a judgement under api30, whose rule "
        "declared `getInstance(macAlg)` twice -- as `g1` and again as `g2` -- so the two "
        "could not be told apart by their text; the expert rule writes the one-argument "
        "overload once and the row is now a plain reading"
    ),
    ("MacSpec", "g2", "g2"): (
        "`getInstance(String, String)`, the provider overload, which the rule writes as "
        "`g2: getInstance(algorithm, _)` (`Mac.crysl:20`). This is the row api30 could not "
        "support: its `g2` repeated `g1`'s one-argument signature, so the `.mop` event for "
        "the two-argument call was matched to a symbol that did not name it. "
        "`getInstance(String, Provider)` exists on android-30 and neither catalogue "
        "declares it"
    ),
    ("MacSpec", "g3", ""): (
        "the unsafe-algorithm accuser over the same `getInstance(String)` call as g1; "
        "`algorithm in {..}` is a CONSTRAINTS clause (`Mac.crysl:44`) and an ORDER has no "
        "symbol for a call it rejects on a constraint. Same reading as CipherSpec.g3 and "
        "KeyPairGeneratorSpec.g3. The erasure is also what makes the `ere`'s "
        "`g3* g1 | g3* g2` prefix read as the rule's `Get`"
    ),
    ("MacSpec", "update", "u1"): (
        "`update(byte)`; the rule's `u1: update(inputByte)` is over the primitive "
        "`byte inputByte` (`Mac.crysl:6,27`). The `.mop` keeps the name `update` for this "
        "one overload after the aggregate split"
    ),
    ("MacSpec", "updateBytes", "u2"): (
        "`update(byte[])`, the rule's `u2: update(preInput)` (`Mac.crysl:7,28`). Under "
        "api30 this event needed two rows, because that rule declared the same signature "
        "as both `u2` and `u4` and the map claimed both so no symbol went unclaimed; the "
        "expert rule declares it once and the second row is withdrawn (see "
        "`order_alphabet_map_delta.csv`, klass `withdrawn-duplicate`)"
    ),
    ("SecureRandomSpec", "next1", ""): (
        "`nextInt(int)`. The erasure was correct against api30, whose only near event was "
        "`ne: next(numB)` -- the protected `next(int)` -- and which named no `nextInt` at "
        "all, so mapping the two together would have been an inference INV-INS-138 "
        "forbids. It is **not** correct against the sole oracle: `SecureRandom.crysl:33` "
        "declares `nIR: randIntInRange = nextInt(range)` and `:34` puts it inside `Next`, "
        "which the ORDER reaches through `End`. Kept erased here, for the same reason as "
        "`MacSpec.updateBuffer`: the repair changes what the automaton is compared against "
        "and belongs to 11.5/11.6"
    ),
    ("SecureRandomSpec", "next3", ""): (
        "`nextInt()` with no argument. Same reading as next1: api30 named no such event, "
        "the expert rule declares `nI: randInt = nextInt()` (`SecureRandom.crysl:32`, "
        "inside `Next`), and the erasure is kept pending 11.5/11.6"
    ),
    ("SecureRandomSpec", "next2", "nB"): (
        "`nextBytes(byte[])`, the rule's `nB` (`SecureRandom.crysl:31`). This is the "
        "anchored case: a second `nextBytes()` used to be accused of a wrong call sequence "
        "because the automaton's end state omitted next2 -- 12,400 events, 99.98 % of them "
        "in libraries. Task 4.5 added the row against api30's `Ends*`; the expert ORDER "
        "`Ins, (Seed?, End*)*` (`:39`) keeps the repetition and adds one of its own, so "
        "the row holds and the mapping itself never changed"
    ),
    ("SecretKeySpec", "e1", "ge"): (
        "this specification translates `SecretKey.crysl`, not `SecretKeySpec.crysl` -- its "
        "object is `javax.crypto.SecretKey` and its one event is `getEncoded()`, the "
        "rule's `ge1` inside `GetEnc` (`SecretKey.crysl:7-8`)"
    ),
    ("SSLContextSpec", "init", "Init"): (
        "the rule names one init event and the `.mop` has one event for it: "
        "`i1: init(km, tm, random)` (`SSLContext.crysl:18`), held by `Init := i1` (`:19`). "
        "api30 wrote the same call with its third position wildcarded and the symbol "
        "itself named `Init`; the expert rule types that position as "
        "`java.security.SecureRandom` and binds it, which is what makes its `:34` "
        "`randomized[random]` a clause with a subject -- the D-16 delta that retires "
        "ledger clause #30's `vacuous` disposition"
    ),
    ("SSLContextSpec", "getDefault", ""): (
        "`getDefault()` is a FORBIDDEN clause and the rule's EVENTS do not name it, so it "
        "has no ORDER symbol -- the same reading as PBEKeySpecSpec.f1/f2 over the "
        "identical `PBEKeySpec(char[]) => Con` (`PBEKeySpec.crysl:10`). The oracle does "
        "write `getDefault() => Get` (`SSLContext.crysl:11`), which reads the forbidden "
        "call as filling the position the legitimate getInstance fills; this set "
        "deliberately does not model it that way, because making a forbidden call an "
        "alternative opening of the ordering is the opposite of what FORBIDDEN says (the "
        "reason PBEKeySpecSpec.mop:183-189 already records). The event is a self-loop at "
        "every state, so it moves the language nowhere and the erasure hides nothing. "
        "Added by task 9.9"
    ),
    ("KeyStoreSpec", "g2", ""): (
        "the rejected-type twin over the same `getInstance(String)` call as g1 -- the "
        "pointcut is the same one-argument overload under the negated "
        "`ConscryptAliasTable.matches` guard, so this is NOT the rule's g2, which is "
        "`getInstance(type, _)` (`KeyStore.crysl:28`). The type is a CONSTRAINTS clause "
        "(`type in {..}`, `:52`) and an ORDER has no symbol for a call it rejects on a "
        "constraint"
    ),
    ("KeyStoreSpec", "g3", "g2"): (
        "`getInstance(String, Object+)` -- the rule's own `g2: getInstance(type, _)` "
        "(`KeyStore.crysl:28`), whose wildcard second position is what the `Object+` "
        "pointcut covers. Added by task 9.16; before it the file had no two-argument event "
        "at all and the rule's g2 had no `.mop` symbol"
    ),
    ("KeyPairSpec", "c1", "co"): (
        "`new KeyPair(PublicKey, PrivateKey)` is the rule's "
        "`c1: KeyPair(publicKey, privateKey)` (`KeyPair.crysl:10`), held by `Con` (`:11`); "
        "the two REQUIRES the body reads are CONSTRAINTS-side clauses and cost no symbol"
    ),
}


# ------------------------------------------------------------------ rule reading


@dataclass
class Atom:
    """One atomic event declaration of a rule.

    Attributes:
        name: The symbol as the rule writes it (`gk1`, `sE`, `nIR`).
        line: 1-based line of the declaration inside the rule file.
        text: The declaration's right-hand side, verbatim.
        key: Signature key -- the method and the resolved type of every argument,
            with `*` where the rule does not say. This is what pairs the two
            catalogues; the name never is.
    """

    name: str
    line: int
    text: str
    key: tuple[str, tuple[str, ...]]


@dataclass
class Rule:
    """The alphabet and ORDER of one CrySL rule.

    Attributes:
        path: The rule file.
        atoms: Atomic events, by name, in declaration order.
        aggregates: Aggregate name to (line, member names).
        order: The ORDER expression as one line, or the empty string.
    """

    path: Path
    atoms: dict[str, Atom] = field(default_factory=dict)
    aggregates: dict[str, tuple[int, list[str]]] = field(default_factory=dict)
    order: str = ""

    def expand(self, symbol: str) -> frozenset[str]:
        """Every atomic event a symbol stands for, aggregates resolved recursively."""
        if symbol in self.atoms:
            return frozenset({symbol})
        if symbol not in self.aggregates:
            return frozenset()
        out: set[str] = set()
        for member in self.aggregates[symbol][1]:
            out |= self.expand(member)
        return frozenset(out)

    def line_of(self, symbol: str) -> int | None:
        if symbol in self.atoms:
            return self.atoms[symbol].line
        if symbol in self.aggregates:
            return self.aggregates[symbol][0]
        return None

    def kind_of(self, symbol: str) -> str:
        return "event" if symbol in self.atoms else "aggregate"

    def order_symbols(self) -> set[str]:
        """The symbols the ORDER expression names, before expansion."""
        return set(re.findall(r"\w+", self.order))


_OBJECT = re.compile(r"^\s*([\w.$]+(?:\[\])?)\s+(\w+)\s*;")
_AGGREGATE = re.compile(r"^\s*(\w+)\s*:=\s*(.+?);\s*$")
_EVENT = re.compile(r"^\s*(\w+)\s*:\s*(.+?);\s*$")
_CALL = re.compile(r"^([\w.$]+)\s*\((.*)\)$")


def read_rule(path: Path) -> Rule:
    """Parse the OBJECTS, EVENTS and ORDER of a CrySL rule.

    OBJECTS is read first because a parameter's declared type is what makes a
    signature key comparable across catalogues: the two rules name the same
    argument `keyStoreAlg` and `type`, and only the type says they are the same
    position of the same call.
    """
    rule = Rule(path=path)
    types: dict[str, str] = {}
    section = None
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        head = line.strip().split(" ")[0]
        if head in SECTION_KEYWORDS:
            section = head
            continue
        if section == "OBJECTS":
            match = _OBJECT.match(line)
            if match:
                types[match.group(2)] = match.group(1)
        elif section == "EVENTS":
            aggregate = _AGGREGATE.match(line)
            if aggregate:
                members = [part.strip() for part in aggregate.group(2).split("|")]
                rule.aggregates[aggregate.group(1)] = (number, members)
                continue
            event = _EVENT.match(line)
            if event:
                name, text = event.group(1), event.group(2).strip()
                rule.atoms[name] = Atom(name, number, text, _signature(text, types))
        elif section == "ORDER":
            if line.strip():
                rule.order = f"{rule.order} {line.strip()}".strip()
    return rule


def _signature(text: str, types: dict[str, str]) -> tuple[str, tuple[str, ...]]:
    """The signature key of one event declaration: method and argument types.

    A `_` wildcard and an argument the rule never declared both become `*`, which
    matches any type at that position. Both cases occur and mean the same thing --
    the rule does not say: api30's `Cipher` writes `u2: update(pre_plaintext,
    pre_plain_off, _)` and its `Signature` leaves `offset` and `len` out of OBJECTS
    entirely, while the expert rule types both. Arity is never wildcarded, because
    two overloads of different arity are two different calls.

    The return binding is deliberately **not** part of the key. The two catalogues
    disagree about whether `verify` binds its boolean result, and that is a
    difference about the rule's predicates, not about which call it observes.
    """
    body = text
    if "=" in body.split("(")[0]:
        body = body.split("=", 1)[1].strip()
    call = _CALL.match(body)
    if not call:
        return body, ()
    method, arguments = call.group(1), call.group(2).strip()
    parts = [part.strip() for part in arguments.split(",")] if arguments else []
    resolved = tuple("*" if part == "_" else types.get(part, "*") for part in parts)
    return method, resolved


Signature = tuple[str, tuple[str, ...]]


def _compatible(left: Signature, right: Signature) -> bool:
    """Whether two signature keys can name the same call."""
    if left[0] != right[0] or len(left[1]) != len(right[1]):
        return False
    return all(a == b or "*" in (a, b) for a, b in zip(left[1], right[1]))


def pair_atoms(source: Rule, target: Rule) -> tuple[dict[str, str], list[str]]:
    """Pair the atomic events of two catalogues by signature.

    A pair is made only when it is **unambiguous**: exactly one target event whose
    signature is compatible, and that target compatible with exactly this source
    event. Anything else is left unpaired and reported, because the ambiguous cases
    are not near-misses -- they are the places where one of the two rules declares
    the same call twice (api30's `Mac` writes `getInstance(macAlg)` as both `g1`
    and `g2`, and `update(pre_input)` as both `u2` and `u4`), and guessing which
    duplicate is which would put a false association in a record whose whole
    purpose is that associations are never inferred. Those are settled by name in
    `DUPLICATE_OVERRIDES`, with the reason written next to each.

    Returns:
        `(pairing, unpaired)` -- source symbol to target symbol, and the source
        symbols with no counterpart.
    """
    pairing: dict[str, str] = {}
    unpaired: list[str] = []
    for name, atom in source.atoms.items():
        candidates = [
            other
            for other, target_atom in target.atoms.items()
            if _compatible(atom.key, target_atom.key)
        ]
        if len(candidates) != 1:
            unpaired.append(name)
            continue
        back = [
            other
            for other, source_atom in source.atoms.items()
            if _compatible(source_atom.key, target.atoms[candidates[0]].key)
        ]
        if back != [name]:
            unpaired.append(name)
            continue
        pairing[name] = candidates[0]
    return pairing, unpaired


def name_symbol(rule: Rule, atoms: frozenset[str]) -> str:
    """The shortest honest name for a set of the rule's atomic events.

    An aggregate whose expansion is exactly this set is preferred, and among
    aggregates one the ORDER actually names wins -- a symbol the ORDER does not
    contain would compare against nothing. Failing that, a single atom is its own
    name, and a set the rule groups no way is written as the disjunction, which is
    what `order_symbol` already admits (the column is parsed as an expression).
    """
    if not atoms:
        return ""
    exact = [name for name in rule.aggregates if rule.expand(name) == atoms]
    ordered = [name for name in exact if name in rule.order_symbols()]
    if ordered:
        return sorted(ordered, key=len)[0]
    if exact:
        return sorted(exact, key=len)[0]
    if len(atoms) == 1:
        return next(iter(atoms))
    return " | ".join(sorted(atoms))


# ------------------------------------------------------------------ the mapping


def read_map(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a mapping CSV, keeping its leading `#` header apart from the rows."""
    text = path.read_text(encoding="utf-8")
    header = [line for line in text.splitlines(keepends=True) if line.startswith("#")]
    body = [line for line in text.splitlines(keepends=True) if not line.startswith("#")]
    return header, list(csv.DictReader(body))


def derive(
    rows: list[dict[str, str]],
    expert_rules: Path,
    api30_rules: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Re-anchor every mapping row on the expert catalogue and diff the two.

    Returns:
        `(map_rows, delta_rows)`. The map rows are the input rows with `rule`,
        `rule_line`, `order_symbol` and `symbol_kind` re-derived; everything a
        human wrote -- the association, the disposition, the reason -- is carried
        through untouched.
    """
    map_rows: list[dict[str, str]] = []
    delta_rows: list[dict[str, str]] = []
    cache: dict[str, tuple[Rule, Rule, dict[str, str], list[str]]] = {}
    covered: dict[str, set[str]] = {}

    for row in rows:
        stem = Path(row["rule"]).stem
        native = row["spec"] in EXPERT_NATIVE_SPECS
        if stem not in cache:
            # An expert-native rule is paired against an empty api30 side rather than
            # against a file: for most of them there is no file, and for the rest reading
            # one would only offer an anchor no row ever used.
            api30 = (
                Rule(path=api30_rules / f"{stem}.cryptsl")
                if native
                else read_rule(api30_rules / f"{stem}.cryptsl")
            )
            expert = read_rule(expert_rules / f"{stem}.crysl")
            pairing, unpaired = ({}, []) if native else pair_atoms(api30, expert)
            cache[stem] = (api30, expert, pairing, unpaired)
            covered.setdefault(stem, set())
        api30, expert, pairing, _ = cache[stem]

        out = dict(row)
        out["rule"] = f"{stem}.crysl"

        if native:
            symbol = row["order_symbol"].strip()
            covered[stem] |= expert.expand(symbol)
            out["symbol_kind"] = expert.kind_of(symbol) if symbol else ""
            line = expert.line_of(symbol)
            out["rule_line"] = str(line) if line else ""
            map_rows.append(out)
            delta_rows.append(
                {
                    "spec": row["spec"],
                    "mop_event": row["mop_event"],
                    "api30_symbol": "",
                    "expert_symbol": symbol,
                    "klass": "expert-native",
                    "signature": (
                        expert.atoms[symbol].text if symbol in expert.atoms else ""
                    ),
                    "note": "decided under the expert oracle; api30 never carried this "
                    "association",
                }
            )
            continue
        override = DUPLICATE_OVERRIDES.get((stem, row["order_symbol"].strip()))
        if override is not None:
            target, why = override
            delta_rows.append(
                {
                    "spec": row["spec"],
                    "mop_event": row["mop_event"],
                    "api30_symbol": row["order_symbol"].strip(),
                    "expert_symbol": target or "",
                    "klass": "duplicate-settled" if target else "withdrawn-duplicate",
                    "signature": api30.atoms[row["order_symbol"].strip()].text,
                    "note": why,
                }
            )
            if target is None:
                continue
            covered[stem].add(target)
            out["order_symbol"] = target
            out["symbol_kind"] = expert.kind_of(target)
            out["rule_line"] = str(expert.line_of(target))
            _reword(out, row["order_symbol"].strip())
            map_rows.append(out)
            continue

        symbol = row["order_symbol"].strip()

        if not symbol:
            # An `order-unmapped` row erases the event from both languages. The
            # erasure is a decision about the api30 alphabet, so the expert
            # catalogue is asked whether the symbol it lacked now exists -- and
            # where a task has decided to reopen the row, `RESTORED_ROWS` names
            # the expert symbol it gains.
            restored = RESTORED_ROWS.get((row["spec"], row["mop_event"]))
            if restored is not None:
                target, why = restored
                covered[stem].add(target)
                out["order_symbol"] = target
                out["symbol_kind"] = expert.kind_of(target)
                out["rule_line"] = str(expert.line_of(target))
                out["disposition"] = "mapped"
                out["reason"] = why
                map_rows.append(out)
                delta_rows.append(
                    {
                        "spec": row["spec"],
                        "mop_event": row["mop_event"],
                        "api30_symbol": "",
                        "expert_symbol": target,
                        "klass": "restored-under-expert",
                        "signature": expert.atoms[target].text,
                        "note": why,
                    }
                )
                continue
            out["rule_line"] = ""
            _reword(out, "")
            map_rows.append(out)
            delta_rows.append(
                {
                    "spec": row["spec"],
                    "mop_event": row["mop_event"],
                    "api30_symbol": "",
                    "expert_symbol": "",
                    "klass": "order-unmapped",
                    "signature": "",
                    "note": row["disposition"],
                }
            )
            continue

        source_atoms = frozenset().union(
            *[api30.expand(part.strip()) for part in symbol.split("|")]
        )
        target_atoms = frozenset(
            pairing[atom] for atom in source_atoms if atom in pairing
        )
        lost = sorted(atom for atom in source_atoms if atom not in pairing)
        expert_symbol = name_symbol(expert, target_atoms)
        covered[stem] |= target_atoms

        out["order_symbol"] = expert_symbol
        out["symbol_kind"] = expert.kind_of(expert_symbol) if expert_symbol else ""
        line = expert.line_of(expert_symbol)
        out["rule_line"] = str(line) if line else ""
        _reword(out, symbol)
        map_rows.append(out)

        if lost:
            klass = "unpaired" if not target_atoms else "narrowed"
        elif expert_symbol == symbol:
            klass = "same-name"
        elif expert.expand(expert_symbol) == target_atoms and len(target_atoms) == len(
            source_atoms
        ):
            klass = "renamed"
        else:
            klass = "regrouped"
        delta_rows.append(
            {
                "spec": row["spec"],
                "mop_event": row["mop_event"],
                "api30_symbol": symbol,
                "expert_symbol": expert_symbol,
                "klass": klass,
                "signature": "; ".join(
                    api30.atoms[atom].text for atom in sorted(source_atoms)
                ),
                "note": (
                    f"api30 {sorted(source_atoms)} has no expert counterpart: {lost}"
                    if lost
                    else ""
                ),
            }
        )

    # Rule-side symbols: what each catalogue declares and no `.mop` event covers.
    # `order_alphabet_map.csv` has no data row that can hold one (its rows erase
    # events, never symbols), so the record is this table and the map's header.
    for stem, (api30, expert, pairing, unpaired) in sorted(cache.items()):
        for name, atom in expert.atoms.items():
            if name in covered[stem]:
                continue
            delta_rows.append(
                {
                    "spec": "",
                    "mop_event": "",
                    "api30_symbol": next(
                        (source for source, t in pairing.items() if t == name), ""
                    ),
                    "expert_symbol": f"{stem}.crysl:{name}",
                    "klass": "uncovered-expert-symbol",
                    "signature": atom.text,
                    "note": (
                        "named by the expert ORDER"
                        if _reaches(expert, name)
                        else "declared and never used by the expert ORDER"
                    ),
                }
            )
        for name in unpaired:
            if (stem, name) in DUPLICATE_OVERRIDES:
                # Settled by name above; it is not a symbol the expert rule dropped.
                continue
            delta_rows.append(
                {
                    "spec": "",
                    "mop_event": "",
                    "api30_symbol": f"{stem}.cryptsl:{name}",
                    "expert_symbol": "",
                    "klass": "withdrawn-api30-symbol",
                    "signature": api30.atoms[name].text,
                    "note": (
                        "named by the api30 ORDER"
                        if _reaches(api30, name)
                        else "declared and never used by the api30 ORDER"
                    ),
                }
            )
    return map_rows, delta_rows


def _reword(row: dict[str, str], api30_symbol: str) -> None:
    """Replace a reason whose claim is about the withdrawn catalogue, in place."""
    replacement = REASON_OVERRIDES.get((row["spec"], row["mop_event"], api30_symbol))
    if replacement is not None:
        row["reason"] = replacement


def _reaches(rule: Rule, atom: str) -> bool:
    """Whether the rule's ORDER names the atom, directly or through an aggregate."""
    return any(atom in rule.expand(symbol) for symbol in rule.order_symbols())


# ------------------------------------------------------------------------- CLI


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]], header: str):
    with path.open("w", newline="", encoding="utf-8") as handle:
        handle.write(header)
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


MAP_HEADER = """\
# The event-alphabet mapping re-anchored on the sole oracle (task 11.2, D-16). One row per
# (`.mop` event -> `ORDER` symbol) association, per specification, exactly as
# `order_alphabet_map.csv` carries it -- same associations, same dispositions, same
# reasons -- with `order_symbol`, `symbol_kind`, `rule` and `rule_line` re-derived against
# `RVSec-replication-package/tools/rules/`.
#
# Derived, never hand-written: `scripts/gh105_expert_alphabet.py --emit map` reproduces
# this file byte for byte, and `--check` fails if it does not. The pairing between the two
# catalogues is by signature and never by name -- `KeyPairGenerator`'s `i1..i4` are a
# permutation between them and `Signature`'s `u1`/`u2` are swapped, so a re-anchoring by
# name would look mechanical and be wrong exactly where it matters.
#
# What moved, and what did not: `order_alphabet_map_delta.csv` is the row-by-row account,
# including the symbols each catalogue declares that no event of this set covers. Nothing
# in either file moves a specification. Three rows change disposition under the expert
# alphabet -- `MacSpec.updateBuffer`, `SecureRandomSpec.next1` and `next3`, erased under
# api30 because the generated rule named no such call. Task 11.6 decided the first: it is
# mapped to `Mac.crysl`'s `u4` here and stays erased in the api30 map, which is the record
# of a different catalogue. The two `SecureRandomSpec` rows are undecided and stay erased;
# reopening either widens the language G-ORDER compares and needs a decision of its own.
#
# The two declared G-ORDER skips are unchanged and stay prose, never a data row:
# `RandomStringPassword` and `IvChainJunction`. The expert catalogue enunciates no rule for
# either -- there is no `RandomStringPassword.crysl` and no `IvChainJunction.crysl` among
# the 49 -- so the reason the api30 map gives for each holds verbatim against the sole
# oracle: the first bridges two JDK conversions no rule of the catalogue orders, and the
# second states no ordering of its own and would compare a free star against Cipher's.
"""

DELTA_HEADER = """\
# What re-anchoring `order_alphabet_map.csv` on the expert catalogue costs, row by row
# (task 11.2, D-16). Derived by `scripts/gh105_expert_alphabet.py --emit delta`.
#
# `klass` reads:
#   same-name                the expert rule names the same call by the same symbol
#   renamed                  same call, same grouping, different symbol
#   regrouped                same call, and a differently shaped aggregate holds it
#   narrowed                 the api30 symbol stood for calls the expert rule splits apart
#   unpaired                 the api30 symbol names a call the expert rule does not
#   order-unmapped           the row erases the event from both languages (INV-INS-138)
#   restored-under-expert    the api30 map erases the event and a task reopened it against
#                            the expert symbol the erasure could not know about
#   uncovered-expert-symbol  the expert rule declares it and no `.mop` event of the set
#                            observes it -- the KeyStore setter case, generalised
#   withdrawn-api30-symbol   api30 declared it and the expert rule does not
#
# An `order-unmapped` row whose erasure rested on the api30 alphabet is never reopened by
# derivation: the row keeps its disposition and the delta records that the expert rule does
# name the call. Reopening one is a decision, and a decided row leaves this table as
# `restored-under-expert` with the deciding task's reason attached -- `MacSpec.updateBuffer`
# at task 11.6, the only one so far.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--emit", choices=("map", "delta"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--expert-rules", type=Path, default=DEFAULT_EXPERT_RULES)
    parser.add_argument("--api30-rules", type=Path, default=DEFAULT_API30_RULES)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--expert-map", type=Path, default=DEFAULT_EXPERT_MAP)
    parser.add_argument("--delta", type=Path, default=DEFAULT_DELTA)
    arguments = parser.parse_args(argv)

    for directory in (arguments.expert_rules, arguments.api30_rules):
        if not directory.is_dir():
            print(f"rule catalogue absent: {directory}", file=sys.stderr)
            return 2

    _, rows = read_map(arguments.map)
    map_rows, delta_rows = derive(rows, arguments.expert_rules, arguments.api30_rules)

    if arguments.emit == "map":
        _write(arguments.expert_map, MAP_FIELDS, map_rows, MAP_HEADER)
        print(f"{arguments.expert_map}: {len(map_rows)} row(s)")
        return 0
    if arguments.emit == "delta":
        _write(arguments.delta, DELTA_FIELDS, delta_rows, DELTA_HEADER)
        print(f"{arguments.delta}: {len(delta_rows)} row(s)")
        return 0

    if arguments.check:
        problems: list[str] = []
        # A stale override is worse than a missing one: it is prose nobody reads any
        # more, sitting next to prose that is checked. Both tables must be spent.
        used = {row["reason"] for row in map_rows}
        for key, text in REASON_OVERRIDES.items():
            if text not in used:
                problems.append(f"REASON_OVERRIDES{key}: written and never applied")
        settled = {
            (row["api30_symbol"], row["note"])
            for row in delta_rows
            if row["klass"] in ("duplicate-settled", "withdrawn-duplicate")
        }
        for (stem, symbol), (_, why) in DUPLICATE_OVERRIDES.items():
            if (symbol, why) not in settled:
                problems.append(
                    f"DUPLICATE_OVERRIDES[({stem!r}, {symbol!r})]: "
                    "written and never applied"
                )
        reopened = {
            (row["spec"], row["mop_event"])
            for row in delta_rows
            if row["klass"] == "restored-under-expert"
        }
        for spec, event in RESTORED_ROWS:
            if (spec, event) not in reopened:
                problems.append(
                    f"RESTORED_ROWS[({spec!r}, {event!r})]: written and never applied"
                )
        for path, fields, derived, header in (
            (arguments.expert_map, MAP_FIELDS, map_rows, MAP_HEADER),
            (arguments.delta, DELTA_FIELDS, delta_rows, DELTA_HEADER),
        ):
            if not path.is_file():
                problems.append(f"{path.name}: absent")
                continue
            expected = path.with_suffix(".derived")
            _write(expected, fields, derived, header)
            if expected.read_bytes() != path.read_bytes():
                problems.append(
                    f"{path.name}: committed file disagrees with the derivation"
                )
            expected.unlink()
        counts: dict[str, int] = {}
        for row in delta_rows:
            counts[row["klass"]] = counts.get(row["klass"], 0) + 1
        for klass, count in sorted(counts.items()):
            print(f"  {klass:26s} {count:>4d}")
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1 if problems else 0

    parser.error("one of --emit or --check is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

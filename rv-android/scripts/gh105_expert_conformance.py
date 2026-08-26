"""Re-derive a specification set's conformance record against a CrySL catalogue.

Task 11.4 of gh105, under design decision D-16: the sole oracle of `jca_android` is the
pinned expert copy `RVSec-replication-package/tools/rules/`. `conformance_record.csv`
names two rules per specification -- 50 of its rows cite a clause of
`MetaCrySL/generated/api30/` and 57 cite the expert copy, the arrangement D-15 created
when it took the value dimension alone. This script derives the census that lets the
record answer to one oracle, and then holds the record to it.

**No verdict is decided here.** Whether a list is a `transcription`, a `deferred-constant`
or a `measured-not-repaired` was settled against the specification's own text, and
substituting the oracle does not reopen it. What is derived is the **anchor**: given a row
about the clause the generated rule states at `Cipher.cryptsl:129`, which clause of the
expert rule is that, on which line, and does it say the same thing.

Pairing is by clause, in four stages, each requiring the match to be unique in **both**
directions among what is still unpaired:

  1. `identical`      the same clause, the same objects, the same values -- only the two
                      dialects' spellings differ (`length(x)` against `length[x]`,
                      `part(0,"/",t)` against `alg(t)`);
  2. `renamed`        the same clause and the same values over objects the two catalogues
                      spell differently (`alg` against `algorithm`, `pre_plaintext`
                      against `prePlainText`);
  3. `values-differ`  the same clause over the same objects, with different value lists --
                      the D-15 dimension, which the divergence record already accounts for;
  4. `renamed+values` both at once.

What the stages refuse to decide is decided by hand in `PAIRING_OVERRIDES`, with the
reason written, because the alternative to an override is a guess and a guessed clause
correspondence is a record citing the wrong line. Three of those overrides are the
finding of this task: `Cipher.cryptsl:131`, `:133` and `:135` state the bounds of the
`update`/`doFinal` buffers with the comparison **inverted** against the oracle's `:123`,
`:127` and `:128` -- satisfied exactly where the oracle is violated. The generated chain
inverts semantics in the arithmetic as well as in the values, which is what D-15 found and
D-16 generalised.

What does not pair is not guessed. An api30 clause with no expert counterpart is
`withdrawn`: the oracle states no such thing, so a row that deferred it defers nothing.
An expert clause with no api30 counterpart is `restored`: the generated catalogue had
dropped it, and it is mostly bounds clauses the `.mop` already tests -- which is why task
10.5 had to classify those tests as `MOP-SEM-BASE` for want of anything to anchor them to.

`--check` is what makes the record reproducible instead of hand-kept. It asserts three
things, and they are what a hand edit gets wrong: the `rule` column names one catalogue;
a row that names the withdrawn one carries a supersession adendum; and the census closes
-- every clause the oracle states is anchored by a row of its rule, and every clause the
generated catalogue stated and the oracle does not is anchored by exactly one, so a
withdrawal is recorded and never dropped in silence.

Nothing here moves a specification. No `.mop` changes and no accusation changes class.

Usage:
    python scripts/gh105_expert_conformance.py                # census summary
    python scripts/gh105_expert_conformance.py --emit pairs   # clause by clause
    python scripts/gh105_expert_conformance.py --emit delta --out <csv>
    python scripts/gh105_expert_conformance.py --check        # exit 0/1, findings on stderr
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REACTOR = REPO.parent

DEFAULT_EXPERT_RULES = REACTOR.parent / "RVSec-replication-package/tools/rules"
DEFAULT_API30_RULES = REACTOR.parent / "MetaCrySL/generated/api30"
DEFAULT_RECORD = REPO / "data/jca_android/conformance_record.csv"
DEFAULT_DELTA = REPO / "data/jca_android/conformance_record_delta.csv"

SECTION = re.compile(
    r"^\s*(SPEC|OBJECTS|EVENTS|ORDER|CONSTRAINTS|REQUIRES|ENSURES|NEGATES|FORBIDDEN)\b"
)

#: The CrySL call predicates. The two dialects write them with different brackets and
#: nothing else, so the normalisation below folds `f[...]` onto `f(...)` rather than
#: treating them as different predicates.
CALL_PREDICATES = (
    "length",
    "neverTypeOf",
    "notHardCoded",
    "instanceOf",
    "noCallTo",
    "callTo",
    "elements",
)

RECORD_FIELDS = (
    "mop_file",
    "rule",
    "variable",
    "rule_object",
    "verdict",
    "changed_from_jca",
    "mop_literals",
    "rule_literals",
    "spelling_variants",
    "aliases",
    "unmatched",
    "absent_from_mop",
    "reason",
)

DELTA_FIELDS = (
    "rule",
    "klass",
    "api30_line",
    "api30_clause",
    "expert_line",
    "expert_clause",
    "disposition",
    "note",
)

#: The supersession adendum every re-anchored row carries. One spelling, so a reader
#: grepping for it finds every row the substitution touched and no row it did not.
ADENDUM = "D-16 (2026-08-26, task 11.4):"


@dataclass(frozen=True)
class Clause:
    """One CONSTRAINTS clause of a rule, with the keys the four stages pair on.

    Attributes:
        rule: The rule's file name, which is what a citation names.
        line: Line of the clause's first token, which is what a citation points at.
        text: The clause as written, minus its terminating `;`.
        full: Dialect-normalised, objects kept, values kept -- stage 1's key.
        renamed: Dialect-normalised, objects erased, values kept -- stage 2's key.
        valueless: Dialect-normalised, objects kept, values erased -- stage 3's key.
        skeleton: Dialect-normalised, objects erased, values erased -- stage 4's key.
    """

    rule: str
    line: int
    text: str
    full: str
    renamed: str
    valueless: str
    skeleton: str


def constraint_clauses(path: Path) -> list[tuple[int, str]]:
    """The `(line, text)` of every CONSTRAINTS clause of a rule.

    A clause runs to its `;` and may span lines -- the expert `Cipher.crysl` wraps its
    PBE lists over four -- so the reader accumulates until the semicolon and reports the
    line the clause *starts* on, which is the line a citation has to point at for a
    reader to find it.

    Args:
        path: A CrySL rule in either dialect.

    Returns:
        One entry per clause, in file order. Empty when the rule states no CONSTRAINTS.
    """
    out: list[tuple[int, str]] = []
    inside, buffer, start = False, "", 0
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = raw.strip()
        if SECTION.match(text):
            inside = text.startswith("CONSTRAINTS")
            continue
        if not inside or not text:
            continue
        if not buffer:
            start = number
        buffer = f"{buffer} {text}" if buffer else text
        if text.endswith(";"):
            out.append((start, buffer.rstrip(";").strip()))
            buffer = ""
    return out


def declared_objects(path: Path) -> set[str]:
    """The names of the rule's OBJECTS, which is what the renaming stages erase."""
    names: set[str] = set()
    inside = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if SECTION.match(text):
            inside = text.startswith("OBJECTS")
            continue
        if inside and text.endswith(";"):
            parts = text.rstrip(";").split()
            if len(parts) >= 2:
                names.add(parts[-1])
    return names


def _dialect(text: str) -> str:
    """Fold the two dialects' spellings of the same clause onto one.

    Three differences, and only three, separate a `.cryptsl` clause from the `.crysl`
    clause that says the same thing: the transformation splitter (`part(0,"/",t)` against
    `alg(t)`), the call predicates' brackets, and whitespace. Everything else this
    function leaves alone -- in particular it does not touch values, because a different
    value list is a different clause and D-15 exists because of it.
    """
    out = text
    for index, name in ((0, "ALG"), (1, "MODE"), (2, "PAD")):
        out = re.sub(
            rf'part\(\s*{index}\s*,[^,]*,\s*([A-Za-z_]\w*)\s*\)', rf"{name}(\1)", out
        )
    for short, name in (("alg(", "ALG("), ("mode(", "MODE("), ("pad(", "PAD(")):
        out = out.replace(short, name)
    for predicate in CALL_PREDICATES:
        out = re.sub(
            rf"\b{predicate}\s*\[([^\]]*)\]",
            lambda match, predicate=predicate: f"{predicate}({match.group(1)})",
            out,
        )
    return out


def _sorted_values(text: str) -> str:
    """`in {2, 4, 1, 3}` and `in {1,2,3,4}` are the same list, so both sort."""

    def one(match: re.Match[str]) -> str:
        values = sorted(v.strip().strip('"') for v in match.group(1).split(","))
        return "{" + ",".join(values) + "}"

    return re.sub(r"\{([^}]*)\}", one, text)


def _fold_identifiers(text: str, objects: set[str], erase: bool) -> str:
    """Case-fold the identifiers outside value sets, optionally erasing the objects.

    The split on `{...}` is what keeps a value from being folded with an identifier:
    `{"AES"}` and an object named `aes` are different things, and a normalisation that
    could not tell them apart would pair clauses that say different things.
    """

    def one(match: re.Match[str]) -> str:
        word = match.group(0)
        if erase and word in objects:
            return "@"
        return word.lower()

    parts = re.split(r"(\{[^}]*\})", text)
    return "".join(
        part if part.startswith("{") else re.sub(r"[A-Za-z_]\w*", one, part)
        for part in parts
    )


def read_rule(path: Path) -> list[Clause]:
    """Every CONSTRAINTS clause of one rule, with its four pairing keys."""
    objects = declared_objects(path)
    clauses = []
    for line, text in constraint_clauses(path):
        dialect = _dialect(text)
        with_values = _sorted_values(dialect)
        without_values = re.sub(r"\{[^}]*\}", "{V}", dialect)

        def squeeze(source: str, erase: bool) -> str:
            return re.sub(r"\s+", "", _fold_identifiers(source, objects, erase))

        clauses.append(
            Clause(
                rule=path.name,
                line=line,
                text=text,
                full=squeeze(with_values, False),
                renamed=squeeze(with_values, True),
                valueless=squeeze(without_values, False),
                skeleton=squeeze(without_values, True),
            )
        )
    return clauses


#: The four stages, in the order they run. Each pairs only what the ones before it left
#: unpaired, and each demands the match be unique in both directions: a key that two
#: clauses of the same rule share pairs nothing, because picking one would be a guess.
STAGES = (
    ("full", "identical"),
    ("renamed", "renamed"),
    ("valueless", "values-differ"),
    ("skeleton", "renamed+values"),
)


#: What the four stages refuse to decide, decided by hand with the reason written.
#: Keyed by `(rule stem, api30 line)`; the value is `(expert line or None, class, why)`.
#:
#: Every entry here is a case where the two catalogues *do* speak about the same clause
#: and the stages cannot see it, because the key that would pair them is shared by other
#: clauses of the same rule. A pair is made only when it is unique in both directions --
#: the discipline task 11.2 set for the alphabet -- so the alternative to an override is
#: a guess, and a guessed clause correspondence is a record that cites the wrong line.
#:
#: `merged` is not a pair and not a withdrawal: the expert rule states the clause, inside
#: a clause another api30 row already pairs with. Recording it as withdrawn would say the
#: oracle dropped a check it did not drop.
PAIRING_OVERRIDES: dict[tuple[str, int], tuple[int | None, str, str]] = {
    ("Cipher", 129): (
        122,
        "renamed",
        "`length(pre_plaintext) >= pre_plain_off + len` is `length[prePlainText] >= "
        "prePlainTextOffset + prePlainTextLen`. The stage that erases object names sees "
        "two clauses of this shape in the expert rule -- the `pre` family at :122 and the "
        "plain family at :127 -- and refuses both. The `pre` prefix is what tells them "
        "apart, and it survives the rename in both catalogues",
    ),
    ("Cipher", 137): (
        97,
        "values-differ",
        "AES to mode, in both. The stage that erases values sees six antecedent families "
        "in api30 and three in the expert rule and cannot tell which is which; the "
        "antecedent value `AES` is unique on both sides and is what pairs them. The "
        "consequent lists differ -- api30 admits ECB, the expert rule does not, which is "
        "the D-15 finding on this clause",
    ),
    ("Cipher", 141): (
        112,
        "values-differ",
        "AES with CBC to padding, in both. api30 states the clause over `{DESede, AES}` "
        "because its catalogue carries a DESede family the expert rule does not; the AES "
        "half is the same clause, and the expert rule widens the mode side to `{CBC, "
        "PCBC}` and narrows the padding side by dropping PKCS7Padding",
    ),
    ("Cipher", 143): (
        113,
        "values-differ",
        "AES with a streaming mode to NoPadding, in both. Same DESede asymmetry as :141; "
        "the expert rule states the mode side as `{CCM, GCM, CTR, CTS, CFB, OFB}`, which "
        "is api30's `{OFB, CTR, CFB}` plus the three api30 states at :149 and nowhere",
    ),
    ("Cipher", 147): (
        107,
        "split",
        "RSA to padding. api30 states it once, unconditional on the mode; the expert rule "
        "states it twice, split by mode -- `:106` for the empty mode and `:107` for ECB -- "
        "and :107 is the one that carries the OAEP list this row is about. The split is "
        "the pair: one api30 clause against two expert clauses is not a withdrawal",
    ),
    ("Cipher", 149): (
        None,
        "merged",
        "AES with GCM to NoPadding. The expert rule states it inside `:113`, whose mode "
        "list is `{CCM, GCM, CTR, CTS, CFB, OFB}`, and `:143` already pairs with that "
        "clause. Nothing was dropped -- api30 needed two clauses where the expert rule "
        "needs one -- so this is a merge and not a withdrawal",
    ),
    ("Cipher", 131): (
        123,
        "inverted",
        "`length(pre_ciphertext) <= pre_ciphertext_off` against `length[preCipherText] >= "
        "preCipherTextOffset`. Same objects, same arithmetic, the comparison the other way "
        "round: the generated clause is satisfied exactly where the oracle's is violated. "
        "No stage pairs them, because a clause that says the opposite thing is not the same "
        "clause -- and recording them as one withdrawal and one restoration would hide the "
        "finding, which is that the generated chain inverts semantics in the arithmetic too, "
        "the same defect that took its value dimension away in D-15",
    ),
    ("Cipher", 133): (
        127,
        "inverted",
        "`length(plainText) <= plain_off + len` against `length[plainText] >= plainTextOffset "
        "+ plainTextLen` -- the same inversion as :131, over renamed objects",
    ),
    ("Cipher", 135): (
        128,
        "inverted",
        "`length(cipherText) <= ciphertext_off` against `length[cipherText] >= "
        "cipherTextOffset` -- the same inversion as :131. Three of the four bounds clauses "
        "the generated rule carries in this family are inverted; the fourth (:129) is the "
        "`renamed` pair above, which is what makes the other three a defect and not a dialect",
    ),
    ("KeyPairGenerator", 47): (
        31,
        "values-differ",
        "DiffieHellman to key size. api30 names the algorithm `DH` and the expert rule "
        "names it `{DiffieHellman, DH}`; both bound it to 2048. The stages cannot pair "
        "them because the objects are renamed (`alg`/`keySize` against "
        "`algorithm`/`keysize`) *and* the values differ, and the last stage sees two "
        "clauses of that shape unpaired on each side",
    ),
    ("KeyPairGenerator", 51): (
        29,
        "values-differ",
        "RSA to key size, the same double ambiguity as :47. The expert rule admits "
        "`{4096, 3072, 2048}` where api30 admits `{4096, 2048}`: 3072 is a key size the "
        "generated catalogue dropped, and the `.mop` carries it -- task 10.6 re-anchored "
        "this message on the expert clause for exactly this reason",
    ),
}


def pair_clauses(
    api30: list[Clause], expert: list[Clause], stem: str
) -> tuple[list[tuple[Clause, Clause | None, str, str]], list[Clause], list[Clause]]:
    """Pair one rule's clauses across the two catalogues.

    The overrides are applied first, so a hand-decided pair is never re-decided by a
    stage, and the clauses they consume leave the pool the stages search.

    Args:
        api30: The generated rule's clauses.
        expert: The oracle's clauses.
        stem: The rule stem, which is the overrides' first key.

    Returns:
        `(pairs, withdrawn, restored)`. A pair is `(api30 clause, expert clause or None,
        class, why)`; `why` is empty for a pair a stage made, because the stage is the
        reason. `withdrawn` are the api30 clauses the oracle states no counterpart for,
        `restored` the expert clauses the generated catalogue had dropped.
    """
    pairs: list[tuple[Clause, Clause | None, str, str]] = []
    left, right = list(api30), list(expert)

    by_line = {clause.line: clause for clause in expert}
    for clause in list(left):
        override = PAIRING_OVERRIDES.get((stem, clause.line))
        if override is None:
            continue
        target, kind, why = override
        counterpart = by_line.get(target) if target is not None else None
        if target is not None and counterpart is None:
            raise SystemExit(
                f"the override for {stem}:{clause.line} names expert line {target}, "
                "which states no clause -- the rule moved and the override did not"
            )
        pairs.append((clause, counterpart, kind, why))
        left.remove(clause)
        if counterpart is not None:
            right.remove(counterpart)

    for key, kind in STAGES:
        moved = True
        while moved:
            moved = False
            for clause in list(left):
                value = getattr(clause, key)
                hits = [other for other in right if getattr(other, key) == value]
                twins = [other for other in left if getattr(other, key) == value]
                if len(hits) == 1 and len(twins) == 1:
                    pairs.append((clause, hits[0], kind, ""))
                    left.remove(clause)
                    right.remove(hits[0])
                    moved = True
    return pairs, left, right


# --------------------------------------------------------------------------
# the census, and what the record has to answer for
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Entry:
    """One line of the census: what became of one clause under the substitution.

    Attributes:
        stem: The rule stem both catalogues spell it under.
        disposition: The pairing class, or `withdrawn`/`restored` when nothing paired.
        api30: The generated rule's clause, or None for a `restored` one.
        expert: The oracle's clause, or None for a `withdrawn` or `merged` one.
        note: Why, for a pair a stage could not make. Empty when a stage made it.
    """

    stem: str
    disposition: str
    api30: Clause | None
    expert: Clause | None
    note: str


def paired_stems(record_path: Path) -> list[str]:
    """The rule stems the record names, enumerated from it rather than listed."""
    with record_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return sorted({Path(row["rule"]).stem for row in rows if row["rule"] != "-"})


def census(expert_rules: Path, api30_rules: Path, stems: list[str]) -> list[Entry]:
    """Pair every CONSTRAINTS clause of every named rule across the two catalogues.

    A rule the generated catalogue never stated contributes only `restored` entries, and
    one the oracle does not state only `withdrawn` ones -- neither is an error, and both
    are the shape of what D-16 substituted.
    """
    entries: list[Entry] = []
    for stem in stems:
        expert_path = expert_rules / f"{stem}.crysl"
        api30_path = api30_rules / f"{stem}.cryptsl"
        expert = read_rule(expert_path) if expert_path.is_file() else []
        api30 = read_rule(api30_path) if api30_path.is_file() else []
        pairs, withdrawn, restored = pair_clauses(api30, expert, stem)
        for left, right, kind, why in pairs:
            entries.append(Entry(stem, kind, left, right, why))
        for clause in withdrawn:
            entries.append(Entry(stem, "withdrawn", clause, None, ""))
        for clause in restored:
            entries.append(Entry(stem, "restored", None, clause, ""))
    return sorted(
        entries,
        key=lambda e: (e.stem, e.api30.line if e.api30 else 10**6, e.expert.line if e.expert else 0),
    )


DELTA_FIELDS = (
    "rule",
    "disposition",
    "api30_line",
    "api30_clause",
    "expert_line",
    "expert_clause",
    "note",
)


def write_delta(entries: list[Entry], stream) -> None:
    """Emit the census as CSV, LF-terminated like the other derived tables of the set."""
    writer = csv.DictWriter(stream, fieldnames=DELTA_FIELDS, lineterminator="\n")
    writer.writeheader()
    for entry in entries:
        writer.writerow(
            {
                "rule": entry.stem,
                "disposition": entry.disposition,
                "api30_line": entry.api30.line if entry.api30 else "-",
                "api30_clause": entry.api30.text if entry.api30 else "-",
                "expert_line": entry.expert.line if entry.expert else "-",
                "expert_clause": entry.expert.text if entry.expert else "-",
                "note": entry.note,
            }
        )


#: A citation, in either dialect, of one clause or of a run of them. `Cipher.crysl:88-124`
#: is how a row that transcribes a whole value family names what it answers for.
CITATION = re.compile(r"([A-Za-z]+)\.(crysl|cryptsl):(\d+)(?:\s*-\s*(\d+))?")

#: The marker a supersession adendum of this record opens with. D-15 took the value
#: dimension away from the generated catalogue and D-16 took the rest, and both wrote
#: their adenda into the rows they superseded. A row may name the withdrawn catalogue
#: only after one of these, which is what keeps "kept as history" apart from "still
#: cited as authority".
ADENDUM = re.compile(r"D-1[56] \(")


def _citations(row: dict[str, str], dialect: str) -> set[tuple[str, int]]:
    """Every `(stem, line)` the row cites in one dialect, ranges expanded."""
    found: set[tuple[str, int]] = set()
    for cell in (row["rule_object"], row["reason"], row["mop_literals"]):
        for stem, seen, first, last in CITATION.findall(cell):
            if seen != dialect:
                continue
            for line in range(int(first), int(last or first) + 1):
                found.add((stem, line))
    return found


def check(record_path: Path, entries: list[Entry]) -> int:
    """Assert the record answers to one oracle, clause by clause.

    Three things are asserted, and they are what a hand edit gets wrong:

      1. no row's `rule` names a `.cryptsl` -- the column has one meaning again;
      2. no row names the withdrawn catalogue without carrying a supersession adendum,
         so a citation kept as history cannot be read as an authority still standing --
         the shape D-15 established, where the row's original sentence stays as written
         and the adendum below it says what replaced the reading;
      3. the census closes: every clause the oracle states is anchored by a row of its
         rule, and every clause the generated catalogue stated and the oracle does not is
         anchored by exactly one, which is what stops a withdrawal from being dropped
         silently instead of recorded.

    Returns:
        0 when all three hold, 1 otherwise. Findings go to stderr, one per line.
    """
    with record_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    findings: list[str] = []

    for number, row in enumerate(rows, 2):
        if row["rule"].endswith(".cryptsl"):
            findings.append(f"line {number}: `rule` still names {row['rule']}")
        text = " ".join(row.values())
        if ("api30" in text or ".cryptsl" in text) and not ADENDUM.search(text):
            findings.append(
                f"line {number}: names the withdrawn catalogue and carries no "
                "supersession adendum"
            )

    expert_anchors: dict[str, set[int]] = {}
    api30_anchors: dict[str, list[int]] = {}
    for row in rows:
        if row["rule"] == "-":
            continue
        stem = Path(row["rule"]).stem
        for cited, line in _citations(row, "crysl"):
            if cited == stem:
                expert_anchors.setdefault(stem, set()).add(line)
        for cited, line in _citations(row, "cryptsl"):
            if cited == stem:
                api30_anchors.setdefault(stem, []).append(line)

    for entry in entries:
        if entry.expert is not None:
            if entry.expert.line not in expert_anchors.get(entry.stem, set()):
                findings.append(
                    f"{entry.stem}.crysl:{entry.expert.line} ({entry.disposition}) "
                    f"is anchored by no row: {entry.expert.text[:70]}"
                )
        if entry.disposition == "withdrawn":
            hits = api30_anchors.get(entry.stem, []).count(entry.api30.line)
            if hits != 1:
                findings.append(
                    f"{entry.stem}.cryptsl:{entry.api30.line} (withdrawn) is anchored by "
                    f"{hits} rows, expected 1: {entry.api30.text[:70]}"
                )

    for finding in findings:
        print(finding, file=sys.stderr)
    return 1 if findings else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--expert-rules", type=Path, default=DEFAULT_EXPERT_RULES)
    parser.add_argument("--api30-rules", type=Path, default=DEFAULT_API30_RULES)
    parser.add_argument("--record", type=Path, default=DEFAULT_RECORD)
    parser.add_argument("--emit", choices=("delta", "pairs", "summary"), default="summary")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)

    for directory in (arguments.expert_rules, arguments.api30_rules):
        if not directory.is_dir():
            print(f"catalogue not found: {directory}", file=sys.stderr)
            return 2

    stems = paired_stems(arguments.record)
    entries = census(arguments.expert_rules, arguments.api30_rules, stems)

    if arguments.check:
        return check(arguments.record, entries)

    if arguments.emit == "delta":
        stream = arguments.out.open("w", encoding="utf-8", newline="") if arguments.out else sys.stdout
        write_delta(entries, stream)
        if arguments.out:
            stream.close()
        return 0

    if arguments.emit == "pairs":
        for stem in stems:
            print(f"### {stem}")
            for entry in (e for e in entries if e.stem == stem):
                left = f":{entry.api30.line:<4}" if entry.api30 else "----- "
                right = f":{entry.expert.line:<4}" if entry.expert else "----- "
                text = (entry.expert or entry.api30).text
                print(f"  {entry.disposition:15} {left} -> {right} {text[:88]}")
        return 0

    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.disposition] = counts.get(entry.disposition, 0) + 1
    print(f"rules named by the record : {len(stems)}")
    print(f"clauses paired or moved   : {len(entries)}")
    for disposition in sorted(counts):
        print(f"  {disposition:<16} {counts[disposition]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

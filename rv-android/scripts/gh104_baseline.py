#!/usr/bin/env python3
"""E0 baseline for gh104: the measured state of violation-report legibility.

This script is the *instrument* of the gh104 baseline. It reads two corpora that were
produced by different pipelines and have different CSV layouts, and it declares a frozen
reader for each one instead of importing the canonical reader from the analysis layer.

Why a private reader (design.md D-9). `aperv_tool.analysis.violations.read_errors_csv`
checks one in-place literal, ``ERRORS_CSV_HEADER``, and raises on any other header. gh104
Group 5 rewrites that literal to a 13-column layout; from that commit on, the shared reader
rejects every comp162 file, which is the 11-column corpus this baseline is measured on. An
import would therefore pin nothing - it would resolve to whatever the header happens to be
on the day the script runs, which is the opposite of what a baseline is for. So the two
readers below are frozen here, in this file, and the baseline reproduces byte-identically
before and after Group 5 lands.

Parity is not correctness. Reproducing a number proves the pipeline unchanged; it proves
nothing about whether the estimator was right in the first place
(``docs/20260815_gh103_analysis_layer.md:108-110``).

Two disciplines are copied from the analysis layer:

* **Freeze items** - a knob that changes the answer has no default. Every measurement asks
  the registry for the definitions it needs, and a missing one raises ``FreezeItemUnset``
  naming what is absent rather than proceeding with something plausible.
* **Envelopes** - a bare float cannot be emitted. Every published number leaves with its
  numerator, its denominator, the unit it counted, the ids of the definitions that produced
  it, the input files (with sha256) it was read from, and what it left out.

Run::

    python3 scripts/gh104_baseline.py

It writes ``data/gh104/baseline.json`` (the machine artefact the byte-identical test
compares), ``data/gh104/baseline.md`` (the reading) and ``data/gh104/definitions.md``
(the freeze items and the instrument discontinuity).
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

RV_ANDROID = Path(__file__).resolve().parents[1]
RVSEC = RV_ANDROID.parent
WORKSPACE = RVSEC.parent

COMP162_RESULTS = RV_ANDROID / "experimento-comp162" / "results"
COMP162_GLOB = "*/*/errors.csv"
CMP162_MANIFEST = (
    RV_ANDROID
    / "modules"
    / "aperv-tool"
    / "tests"
    / "fixtures"
    / "cmp162_manifest.json"
)

ARTICLE_ERRORS_CSV = WORKSPACE / "ase-journal" / "dataset" / "results" / "errors.csv"
ARTICLE_TIER_REPORT = (
    WORKSPACE / "ase-journal" / "docs" / "20260806_owasp_cwe_mapping_report.md"
)
ARTICLE_DATASET_TEX = WORKSPACE / "ase-journal" / "dataset.tex"

MOP_RESOURCES = RVSEC / "rvsec" / "rvsec-mop" / "src" / "main" / "resources"
SPEC_SET_DIRS = ("jca", "jca_android_bug_predicate", "generic", "generic_new")

OUT_DIR = RV_ANDROID / "data" / "gh104"

# The comp162 tree is ~40 GB and lives outside the repository; the article corpus is a
# 26 MB CSV in the sibling ase-journal checkout. Neither is vendored here, so both are
# addressed by content: every number below names the sha256 of the bytes it read.

csv.field_size_limit(1 << 30)


def rel(path: Path) -> str:
    """Path as written in the artefacts: relative to the workspace root when possible.

    Absolute host paths would still be stable across two runs on this machine, but they
    make the published artefact unreadable on any other, so the display form is anchored
    at ``workspace-rv/``.
    """
    try:
        return str(path.relative_to(WORKSPACE))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    """
    The sha256 of a file, read in one-megabyte chunks.

    Every input a measurement reads carries its digest into the artefact, so that
    a reproduced number and a changed input can never look alike.
    """
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Freeze items
# ---------------------------------------------------------------------------


class FreezeItemUnset(Exception):
    """A definition that decides a number was not supplied.

    Raised instead of falling back to a default. Each of these knobs changes the answer,
    and each has a value that looks obviously right until someone checks: ``site`` is a
    4-tuple on comp162 and a 3-tuple on the article because the article layout has no
    ``source`` column at all, and the lineage's twin counts reproduce only under that
    split.
    """

    def __init__(self, item_id: str) -> None:
        """
        Build the message naming the missing item, and keep its id on the exception.

        The message says explicitly that omitting a definition is an error rather
        than a way of saying "default", because the tempting reading of this
        exception is that the caller forgot a convenience argument.
        """
        super().__init__(
            f"freeze item {item_id!r} is unset: supply it explicitly; "
            "omitting a definition is an error, not a way of saying 'default'"
        )
        self.item_id = item_id


THIRD_PARTY_PREFIXES: tuple[str, ...] = (
    "okhttp3.",
    "com.google.",
    "kotlin.",
    "io.ktor.",
    "org.bouncycastle.",
    "androidx.",
    "org.conscrypt.",
    "okio.",
    "org.spongycastle.",
)

# The first seven are the vendor list the lineage argued from; ``okio.`` and
# ``org.spongycastle.`` are the two it left out. All three cuts are reported, because the
# choice of cut moves the headline by seven points.
THIRD_PARTY_CUTS: tuple[tuple[str, int], ...] = (
    ("seven-vendor list", 7),
    ("plus okio.", 8),
    ("all nine prefixes", 9),
)

FREEZE_ITEMS: dict[str, dict[str, Any]] = {
    "mute": {
        "definition": "A row is *mute* when `message.strip()` equals the literal below.",
        "value": "unknown",
        "why": (
            "`unknown` is the literal the three-argument `new ErrorDescription(...)` constructor "
            "writes when no message argument is supplied. It is not missing data and not a parse "
            "failure: it is the report the specification actually emitted, and it is the quantity "
            "this whole change exists to remove."
        ),
    },
    "site_comp162": {
        "definition": "A *site* on comp162 is the 4-tuple `(spec, class, method, source)`.",
        "value": ("spec", "class", "method", "source"),
        "why": (
            "comp162's `errors.csv` has 11 columns and carries `source` (the `File.java:line` of "
            "the accused call), so a site can be resolved to the call and not merely to the method."
        ),
    },
    "site_article": {
        "definition": "A *site* on the article dataset is the 3-tuple `(spec, class, method)`.",
        "value": ("spec", "class", "method"),
        "why": (
            "The article dataset has 10 columns and **no `source`** at all. Using the comp162 "
            "4-tuple here would raise `KeyError`; using a 4-tuple with a synthesised blank would "
            "silently merge distinct call sites. The lineage's twin numbers reproduce only under "
            "the 3-tuple."
        ),
    },
    "third_party_prefixes": {
        "definition": (
            "A row is *third-party* when its `class` starts with one of nine package prefixes: "
            + ", ".join(f"`{p}`" for p in THIRD_PARTY_PREFIXES)
            + "."
        ),
        "value": THIRD_PARTY_PREFIXES,
        "why": (
            "The cut is reported three ways because it moves the headline: the seven-vendor list "
            "the lineage argued from, that list plus `okio.`, and all nine. Publishing one number "
            "without naming its prefix set would be publishing a choice as if it were a fact."
        ),
    },
    "shards": {
        "definition": (
            "The eight files matched by `experimento-comp162/results/*/*/errors.csv` are eight "
            "disjoint **shards**, never replicas: 112 distinct APKs partitioned across them with "
            "zero overlap, each shard running 3 tools x 3 repetitions."
        ),
        "value": "disjoint shards of one campaign; union, never average",
        "why": (
            "If they were replicas, the eight files would be eight measurements of the same APKs "
            "and the right operation would be to average them. They are not: no APK appears in two "
            "shards, so the right operation is to concatenate. Calling them replicas would divide "
            "every count by eight."
        ),
    },
    "identity8": {
        "definition": (
            "A repeated report is counted under the 8-tuple "
            "`(apk, rep, tool, spec, class, method, source, message)`. The `ErrorSummary` identity "
            "is a different, coarser 5-tuple: `(spec, error, class, method, location)`."
        ),
        "value": ("apk", "rep", "tool", "spec", "class", "method", "source", "message"),
        "why": (
            "The two tuples answer different questions and give different numbers on the same "
            "rows - 6,344 against 409 - so every repetition figure states which one produced it. "
            "`location` in the `ErrorSummary` tuple is the `source` column."
        ),
    },
    "error_type": {
        "definition": "The `ErrorType` of a row is `unique_msg.split(':::')[3]`, never parsed from `message`.",
        "value": "unique_msg.split(':::')[3]",
        "why": (
            "`unique_msg` is the machine field: `class:::method:::spec:::ErrorType:::message`. "
            "`message` is the free text this change is rewriting, so deriving the type from it "
            "would make the baseline move when the messages move - the one thing a baseline may "
            "not do."
        ),
    },
    "misuse_article": {
        "definition": (
            "A *unique misuse* on the article dataset is the 4-tuple `(apk, spec, class, method)` "
            "(rule R1 of the OWASP/CWE mapping report)."
        ),
        "value": ("apk", "spec", "class", "method"),
        "why": (
            "This is the denominator of the publishable Android tier (84 of 454 = 18.5 %). It is "
            "reproduced here rather than quoted: the 4-tuple gives 454 on the corpus and gives "
            "65 / 12 / 5 / 1 / 1 on the five tier rows, matching the report exactly. The 3-tuple "
            "`(apk, class, method)` gives 450, and `(class, method)` gives 11 for the largest row "
            "instead of 65 - so the tuple is a freeze item, not a detail."
        ),
    },
    "observed_value": {
        "definition": (
            "The *observed value* of a legible row is the text after the last `but found ` in "
            "`message`, with a single trailing `.` removed. A row whose observed value is the "
            "empty string is a `but found .` row."
        ),
        "value": r"message.rsplit('but found ', 1)[1].rstrip('.')",
        "why": (
            "`but found .` is the visible face of the same defect as `unknown`: the specification "
            "reached the report site with nothing to say about what it saw. Extracting the value "
            "is also what identifies the five rows of the publishable Android tier "
            "(`TLS`, `AndroidKeyStore`, `X509`, ...), so the same rule serves both."
        ),
    },
}


@dataclass(frozen=True)
class FreezeRegistry:
    """The definitions in force for one run of the baseline."""

    items: Mapping[str, Mapping[str, Any]]

    def require(self, item_id: str) -> Any:
        """
        The value of a definition, or `FreezeItemUnset` naming what is missing.

        There is no default and no fallback: every one of these knobs changes the
        answer, so a measurement that reached this point without its definition has
        to stop rather than proceed with something plausible.
        """
        if item_id not in self.items:
            raise FreezeItemUnset(item_id)
        return self.items[item_id]["value"]

    def without(self, item_id: str) -> "FreezeRegistry":
        """The same registry with one definition removed - used by the freeze-item test."""
        return FreezeRegistry({k: v for k, v in self.items.items() if k != item_id})


DEFAULT_FREEZE = FreezeRegistry(FREEZE_ITEMS)


# ---------------------------------------------------------------------------
# The two frozen readers (design.md D-9)
# ---------------------------------------------------------------------------

COMP162_HEADER: tuple[str, ...] = (
    "apk",
    "rep",
    "timeout",
    "tool",
    "time",
    "spec",
    "class",
    "method",
    "source",
    "message",
    "unique_msg",
)  # 11 columns - carries `source`

ARTICLE_HEADER: tuple[str, ...] = (
    "apk",
    "rep",
    "timeout",
    "tool",
    "time",
    "spec",
    "class",
    "method",
    "message",
    "unique_msg",
)  # 10 columns - no `source`


class FrozenHeaderMismatch(ValueError):
    """The file does not have the layout this reader was frozen against."""


def _read_frozen(path: Path, header: Sequence[str], label: str) -> list[dict[str, str]]:
    """
    Read a CSV that must have exactly this header, or raise `FrozenHeaderMismatch`.

    The layout is checked twice -- the header against the frozen tuple, then
    every row's field count -- and both raise instead of skipping. The whole
    point of a frozen reader is that it refuses a file it was not frozen against
    (design D-9); one that tolerated a widened header would silently measure a
    different corpus than the baseline was computed on.
    """
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        try:
            actual = next(reader)
        except StopIteration:
            raise FrozenHeaderMismatch(f"{label}: {path} is empty") from None
        if tuple(actual) != tuple(header):
            raise FrozenHeaderMismatch(
                f"{label}: {path} has header {actual!r}, frozen layout is {list(header)!r}"
            )
        width = len(header)
        rows = []
        for record in reader:
            if len(record) != width:
                raise FrozenHeaderMismatch(
                    f"{label}: {path} row {reader.line_num} has {len(record)} fields, expected {width}"
                )
            rows.append(dict(zip(header, record)))
    return rows


def read_comp162_errors_csv(path: Path) -> list[dict[str, str]]:
    """Frozen 11-column reader for `experimento-comp162/results/*/*/errors.csv`."""
    return _read_frozen(path, COMP162_HEADER, "comp162 frozen 11-column reader")


def read_article_errors_csv(path: Path) -> list[dict[str, str]]:
    """Frozen 10-column reader for the article dataset (`ase-journal/dataset/results/errors.csv`)."""
    return _read_frozen(path, ARTICLE_HEADER, "article frozen 10-column reader")


# ---------------------------------------------------------------------------
# Envelopes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Envelope:
    """A number that cannot be emitted bare.

    `quantity` says what was estimated; `numerator`/`denominator` are the two cardinalities
    of its basis in the stated `unit`; `definitions` names the freeze items that produced
    it; `inputs` names the input keys (each of which carries a path and a sha256);
    `excluded` says what was left out; `expected` is the value the gh104 group file
    predicted, so the artefact records agreement or disagreement rather than asserting it.
    """

    quantity: str
    numerator: int
    denominator: int | None
    unit: str
    definitions: tuple[str, ...]
    inputs: tuple[str, ...]
    excluded: str = "nothing"
    expected: int | None = None
    note: str = ""

    @property
    def percent(self) -> float | None:
        """
        The ratio as a percentage rounded to two places, or None without a denominator.

        None rather than zero: a quantity with no denominator has no percentage, and
        rendering it as `0.00 %` would state something false.
        """
        if not self.denominator:
            return None
        return round(100.0 * self.numerator / self.denominator, 2)

    @property
    def agrees(self) -> bool | None:
        """
        Whether the measurement equals the value the group file predicted.

        None when nothing was predicted. The three states are kept apart everywhere
        downstream, because "no expectation" and "expectation met" are different
        facts about how much this number has been checked.
        """
        if self.expected is None:
            return None
        return self.numerator == self.expected

    def to_dict(self) -> dict[str, Any]:
        """
        The envelope as plain data, with `percent` and `agrees` computed in.

        The two derived properties are written out rather than left to the reader, so
        that the JSON artefact carries the same verdict the markdown does.
        """
        return {
            "quantity": self.quantity,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "unit": self.unit,
            "percent": self.percent,
            "definitions": list(self.definitions),
            "inputs": list(self.inputs),
            "excluded": self.excluded,
            "expected": self.expected,
            "agrees": self.agrees,
            "note": self.note,
        }

    def render(self) -> str:
        """The measurement as one line: numerator, denominator, unit and percentage."""
        pct = "" if self.percent is None else f" = {self.percent:.2f} %"
        den = "-" if self.denominator is None else f"{self.denominator:,}"
        return f"{self.numerator:,} / {den} {self.unit}{pct}"


# ---------------------------------------------------------------------------
# Row helpers (each one names the freeze item it consumes)
# ---------------------------------------------------------------------------

_BUT_FOUND = "but found "


def make_is_mute(freeze: FreezeRegistry) -> Callable[[Mapping[str, str]], bool]:
    """
    A predicate for "this row's message is the mute literal", from the definition.

    The literal is required from the registry rather than written here, because
    which message counts as mute is exactly the kind of knob that decides how
    many rows are legible.
    """
    literal = freeze.require("mute")
    return lambda row: (row.get("message") or "").strip() == literal


def make_error_type(freeze: FreezeRegistry) -> Callable[[Mapping[str, str]], str]:
    """
    A reader for the error type a row's `unique_msg` carries.

    The registry is consulted for its side effect: the definition has no value to
    substitute into the parse, but a measurement that split `unique_msg` without
    declaring that it did would be reading an undeclared layout.
    """
    freeze.require("error_type")

    def error_type(row: Mapping[str, str]) -> str:
        """The fourth `:::` field of `unique_msg`, or `?` when the row carries fewer."""
        parts = (row.get("unique_msg") or "").split(":::")
        return parts[3] if len(parts) > 3 else "?"

    return error_type


def make_observed_value(
    freeze: FreezeRegistry,
) -> Callable[[Mapping[str, str]], str | None]:
    """A reader for the value a message says it found, from the frozen definition."""
    freeze.require("observed_value")

    def observed(row: Mapping[str, str]) -> str | None:
        """The text after `but found `, with a trailing full stop removed, or None."""
        message = (row.get("message") or "").strip()
        if _BUT_FOUND not in message:
            return None
        tail = message.rsplit(_BUT_FOUND, 1)[1]
        return tail[:-1] if tail.endswith(".") else tail

    return observed


def make_key(fields: Sequence[str]) -> Callable[[Mapping[str, str]], tuple[str, ...]]:
    """
    A tuple-builder over the given fields, for identity and site keys.

    Missing fields raise rather than default to the empty string: a key silently
    short of a component would collapse identities that the definition keeps
    apart.
    """
    return lambda row: tuple(row[f] for f in fields)


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------


@dataclass
class Corpus:
    """One corpus's rows, with the input records saying where they came from."""

    key: str
    rows: list[dict[str, str]]
    inputs: dict[str, dict[str, Any]] = field(default_factory=dict)


def load_article() -> Corpus:
    """
    Read the article corpus through the frozen 10-column reader.

    The article layout has no `source` column at all, which is why it gets its
    own reader and its own site definition -- the lineage's twin counts reproduce
    only under that split.
    """
    rows = read_article_errors_csv(ARTICLE_ERRORS_CSV)
    return Corpus(
        key="article",
        rows=rows,
        inputs={
            "article_errors_csv": {
                "path": rel(ARTICLE_ERRORS_CSV),
                "sha256": sha256_file(ARTICLE_ERRORS_CSV),
                "reader": "frozen 10-column reader (no `source`)",
                "header": list(ARTICLE_HEADER),
                "rows": len(rows),
            }
        },
    )


def load_comp162() -> Corpus:
    """
    Read the eight comp162 shards through the frozen 11-column reader.

    An empty glob raises instead of returning an empty corpus, because every
    comp162 measurement would then be a well-formed zero.

    The shards enter the envelopes as one input key, since every measurement
    reads all eight at once, and the aggregate digest is over the shard names as
    well as their contents -- a digest of the contents alone would call two
    different groupings the same input. The eight per-shard records stay beside
    it: the aggregate is what a reader checks, the members are what they check it
    against. The `_shard` tag is bookkeeping that proves the files disjoint and
    never enters a published tuple.
    """
    files = sorted(COMP162_RESULTS.glob(COMP162_GLOB))
    if not files:
        raise FileNotFoundError(
            f"no comp162 shards under {COMP162_RESULTS}/{COMP162_GLOB}"
        )
    rows: list[dict[str, str]] = []
    inputs: dict[str, dict[str, Any]] = {}
    for path in files:
        shard = path.parent.parent.name
        shard_rows = read_comp162_errors_csv(path)
        # The shard tag is bookkeeping, not data: it is what proves the eight files are
        # disjoint (no identity crosses a shard) and it never enters any published tuple.
        for row in shard_rows:
            row["_shard"] = shard
        rows.extend(shard_rows)
        inputs[shard] = {
            "path": rel(path),
            "sha256": sha256_file(path),
            "reader": "frozen 11-column reader (carries `source`)",
            "header": list(COMP162_HEADER),
            "rows": len(shard_rows),
        }
    # Every comp162 measurement reads all eight shards at once, so they enter the envelopes
    # as one input key. The per-shard rows stay in the map beside it: the aggregate digest
    # is what a reader checks, the eight digests are what they check it against.
    aggregate = hashlib.sha256()
    for shard in sorted(inputs):
        aggregate.update(shard.encode())
        aggregate.update(b"\0")
        aggregate.update(bytes.fromhex(inputs[shard]["sha256"]))
    combined = {
        "comp162_shards": {
            "path": rel(COMP162_RESULTS) + "/" + COMP162_GLOB,
            "sha256": aggregate.hexdigest(),
            "reader": "frozen 11-column reader (carries `source`), eight shards concatenated",
            "header": list(COMP162_HEADER),
            "rows": len(rows),
            "members": {shard: inputs[shard] for shard in sorted(inputs)},
        }
    }
    return Corpus(key="comp162", rows=rows, inputs=combined)


# ---------------------------------------------------------------------------
# Article measurements
# ---------------------------------------------------------------------------

ART_IN = ("article_errors_csv",)


def measure_article(
    rows: list[dict[str, str]], freeze: FreezeRegistry
) -> dict[str, Any]:
    """
    Measure the article corpus and return its envelopes.

    Each measurement asks the registry for the definitions it consumes before it
    counts anything, so a run missing one fails naming the definition rather than
    producing a number whose basis is unstated. The `_article` site and misuse
    keys are the ones without `source`, and using the comp162 keys here would not
    fail -- it would quietly answer a different question.
    """
    is_mute = make_is_mute(freeze)
    error_type = make_error_type(freeze)
    observed = make_observed_value(freeze)
    site = make_key(freeze.require("site_article"))
    misuse = make_key(freeze.require("misuse_article"))
    prefixes = tuple(freeze.require("third_party_prefixes"))

    total = len(rows)
    messages = collections.Counter((r.get("message") or "").strip() for r in rows)
    mute_rows = [r for r in rows if is_mute(r)]

    env: dict[str, Envelope] = {}
    env["rows"] = Envelope(
        "rows in the article dataset",
        total,
        total,
        "rows",
        (),
        ART_IN,
        excluded="nothing; the file is read whole",
        expected=97018,
    )
    env["distinct_messages"] = Envelope(
        "distinct `message` strings",
        len(messages),
        total,
        "distinct strings / rows",
        (),
        ART_IN,
        expected=19,
        note="19 strings for 97,018 events: the report vocabulary of the whole published corpus.",
    )
    env["mute"] = Envelope(
        "mute rows (`unknown`)",
        len(mute_rows),
        total,
        "rows",
        ("mute",),
        ART_IN,
        expected=70760,
    )
    env["mute_sites"] = Envelope(
        "distinct sites emitting a mute row",
        len({site(r) for r in mute_rows}),
        None,
        "sites",
        ("mute", "site_article"),
        ART_IN,
    )
    env["misuses"] = Envelope(
        "unique misuses (R1)",
        len({misuse(r) for r in rows}),
        total,
        "misuses / rows",
        ("misuse_article",),
        ART_IN,
        expected=454,
    )
    env["apps"] = Envelope(
        "applications with at least one violation",
        len({r["apk"] for r in rows}),
        None,
        "apks",
        (),
        ART_IN,
        expected=113,
    )

    # `but found .` - the legible-looking rows that say nothing either.
    bf_dot = [r for r in rows if observed(r) == ""]
    env["but_found_dot"] = Envelope(
        "rows whose observed value is empty (`but found .`)",
        len(bf_dot),
        total,
        "rows",
        ("observed_value",),
        ART_IN,
        expected=8843,
    )
    bf_by_spec = collections.Counter(r["spec"] for r in bf_dot)
    but_found_dot_by_spec = {
        spec: Envelope(
            f"`but found .` rows in {spec}",
            n,
            len(bf_dot),
            "rows",
            ("observed_value",),
            ART_IN,
        )
        for spec, n in bf_by_spec.most_common()
    }

    # Third-party attribution, at all three cuts.
    third_party = {}
    for label, k in THIRD_PARTY_CUTS:
        cut = prefixes[:k]
        n = sum(1 for r in rows if r["class"].startswith(cut))
        third_party[label] = Envelope(
            f"rows in third-party packages ({label})",
            n,
            total,
            "rows",
            ("third_party_prefixes",),
            ART_IN,
            excluded=f"prefixes beyond the first {k} of the nine",
            expected={7: 76154, 8: 80204, 9: 82890}[k],
            note="prefixes: " + ", ".join(cut),
        )

    # UnsafeAlgorithm / weak digest - three denominators, three different questions.
    weak_digests = ("MD5", "SHA-1", "SHA1", "SHA")
    ua_rows = [r for r in rows if error_type(r) == "UnsafeAlgorithm"]
    md_rows = [r for r in rows if r["spec"] == "MessageDigestSpec"]
    md_ua_rows = [r for r in md_rows if error_type(r) == "UnsafeAlgorithm"]
    weak = [r for r in md_ua_rows if observed(r) in weak_digests]
    weak_by_value = collections.Counter(observed(r) for r in weak)

    unsafe_algorithm = {
        "weak_of_all_unsafe_algorithm": Envelope(
            "weak-digest rows among all `UnsafeAlgorithm` rows",
            len(weak),
            len(ua_rows),
            "rows",
            ("error_type", "observed_value"),
            ART_IN,
            expected=5892,
            note="denominator: every `UnsafeAlgorithm` row of the corpus, all specifications.",
        ),
        "weak_of_spec_unsafe_algorithm": Envelope(
            "weak-digest rows among `MessageDigestSpec`'s own `UnsafeAlgorithm` rows",
            len(weak),
            len(md_ua_rows),
            "rows",
            ("error_type", "observed_value"),
            ART_IN,
            expected=5892,
            note="denominator: the specification's own labelled rows - what the api30 rule governs.",
        ),
        "weak_of_spec_rows": Envelope(
            "weak-digest rows among all `MessageDigestSpec` rows",
            len(weak),
            len(md_rows),
            "rows",
            ("error_type", "observed_value"),
            ART_IN,
            expected=5892,
            note="denominator: every row the specification emitted, sequence reports included.",
        ),
        "weak_of_corpus": Envelope(
            "weak-digest rows in the whole corpus",
            len(weak),
            total,
            "rows",
            ("error_type", "observed_value"),
            ART_IN,
            expected=5892,
            note="denominator: the whole 97,018-row corpus.",
        ),
    }
    weak_breakdown = {
        value: Envelope(
            f"`MessageDigestSpec` `UnsafeAlgorithm` rows observing `{value}`",
            weak_by_value.get(value, 0),
            len(weak),
            "rows",
            ("observed_value",),
            ART_IN,
        )
        for value in weak_digests
    }

    # Structural footprint: the clause-encoding orphan's second `@fail` report.
    footprint = {}
    for spec, labelled in (
        ("SSLContextSpec", "UnsafeProtocol"),
        ("TrustManagerFactorySpec", "UnsafeAlgorithm"),
    ):
        by_type = collections.Counter(error_type(r) for r in rows if r["spec"] == spec)
        footprint[spec] = {
            "sequence": Envelope(
                f"{spec} `InvalidSequenceOfMethodCalls` rows",
                by_type.get("InvalidSequenceOfMethodCalls", 0),
                sum(by_type.values()),
                "rows",
                ("error_type",),
                ART_IN,
                expected={"SSLContextSpec": 17510, "TrustManagerFactorySpec": 9015}[
                    spec
                ],
            ),
            "labelled": Envelope(
                f"{spec} `{labelled}` rows",
                by_type.get(labelled, 0),
                sum(by_type.values()),
                "rows",
                ("error_type",),
                ART_IN,
                expected={"SSLContextSpec": 8802, "TrustManagerFactorySpec": 9014}[
                    spec
                ],
            ),
            "ratio": (
                round(
                    by_type.get("InvalidSequenceOfMethodCalls", 0) / by_type[labelled],
                    4,
                )
                if by_type.get(labelled)
                else None
            ),
        }

    return {
        "scalars": {k: v.to_dict() for k, v in env.items()},
        "but_found_dot_by_spec": {
            k: v.to_dict() for k, v in but_found_dot_by_spec.items()
        },
        "third_party": {k: v.to_dict() for k, v in third_party.items()},
        "unsafe_algorithm": {k: v.to_dict() for k, v in unsafe_algorithm.items()},
        "weak_digest_breakdown": {k: v.to_dict() for k, v in weak_breakdown.items()},
        "error_types": dict(
            sorted(collections.Counter(error_type(r) for r in rows).items())
        ),
        "structural_footprint": {
            spec: {
                "sequence": d["sequence"].to_dict(),
                "labelled": d["labelled"].to_dict(),
                "sequence_over_labelled": d["ratio"],
            }
            for spec, d in footprint.items()
        },
    }


# ---------------------------------------------------------------------------
# comp162 measurements
# ---------------------------------------------------------------------------


def measure_comp162(
    rows: list[dict[str, str]], input_keys: Sequence[str], freeze: FreezeRegistry
) -> dict[str, Any]:
    """
    Measure the corpus the published numbers came from, and return its envelopes.

    The split into mute and legible rows is what the whole baseline is about: a
    mute report is a row that was written and says nothing a reader can act on.
    Sites are counted on each side separately, because the same site can emit
    both, and collapsing them would hide how much of the corpus is legible per
    site rather than per row.
    """
    is_mute = make_is_mute(freeze)
    error_type = make_error_type(freeze)
    observed = make_observed_value(freeze)
    site = make_key(freeze.require("site_comp162"))
    identity = make_key(freeze.require("identity8"))
    freeze.require("shards")
    inputs = tuple(input_keys)

    total = len(rows)
    mute_rows = [r for r in rows if is_mute(r)]
    legible_rows = [r for r in rows if not is_mute(r)]
    mute_sites = collections.Counter(site(r) for r in mute_rows)
    legible_sites = collections.Counter(site(r) for r in legible_rows)

    env: dict[str, Envelope] = {}
    env["rows"] = Envelope(
        "rows in the comp162 fixture",
        total,
        total,
        "rows",
        ("shards",),
        inputs,
        excluded="nothing; the eight shards are concatenated, never averaged",
        expected=19664,
    )
    env["mute"] = Envelope(
        "mute rows (`unknown`)",
        len(mute_rows),
        total,
        "rows",
        ("mute",),
        inputs,
        expected=15714,
    )
    env["mute_sites"] = Envelope(
        "distinct sites emitting a mute row",
        len(mute_sites),
        None,
        "sites",
        ("mute", "site_comp162"),
        inputs,
        expected=296,
    )
    env["legible_rows"] = Envelope(
        "legible rows (message is not `unknown`)",
        len(legible_rows),
        total,
        "rows",
        ("mute",),
        inputs,
        expected=3950,
    )
    env["legible_sites"] = Envelope(
        "distinct sites emitting a legible row",
        len(legible_sites),
        None,
        "sites",
        ("mute", "site_comp162"),
        inputs,
        expected=101,
    )

    # Twins: the same site emits both a mute row and a legible one. These are the sites
    # where the muteness is demonstrably gratuitous - the specification had the words.
    twin_sites = [s for s in mute_sites if s in legible_sites]
    env["mute_legible_twin_rows"] = Envelope(
        "mute rows at sites that also emit a legible row",
        sum(mute_sites[s] for s in twin_sites),
        len(mute_rows),
        "rows",
        ("mute", "site_comp162"),
        inputs,
        expected=3950,
    )
    env["mute_legible_twin_sites"] = Envelope(
        "sites emitting both a mute and a legible row",
        len(twin_sites),
        len(mute_sites),
        "sites",
        ("mute", "site_comp162"),
        inputs,
        expected=101,
    )
    env["legible_only_sites"] = Envelope(
        "sites emitting only legible rows",
        len([s for s in legible_sites if s not in mute_sites]),
        len(legible_sites),
        "sites",
        ("mute", "site_comp162"),
        inputs,
        expected=0,
        note="zero: every legible site is also a mute site, so muteness is never the site's fault.",
    )

    # Mute-mute twins: one site, two ErrorTypes, equal counts - the same call accused twice
    # under two labels, both mute.
    per_site_types: dict[tuple[str, ...], collections.Counter] = (
        collections.defaultdict(collections.Counter)
    )
    for row in mute_rows:
        per_site_types[site(row)][error_type(row)] += 1
    mute_mute = {
        s: c
        for s, c in per_site_types.items()
        if len(c) > 1 and min(c.values()) == max(c.values())
    }
    env["mute_mute_twin_rows"] = Envelope(
        "mute rows at sites emitting two ErrorTypes in equal numbers",
        sum(sum(c.values()) for c in mute_mute.values()),
        len(mute_rows),
        "rows",
        ("mute", "site_comp162", "error_type"),
        inputs,
        expected=838,
    )
    env["mute_mute_twin_sites"] = Envelope(
        "sites emitting two ErrorTypes in equal numbers, all mute",
        len(mute_mute),
        len(mute_sites),
        "sites",
        ("mute", "site_comp162", "error_type"),
        inputs,
        expected=12,
    )
    mute_mute_by_type = collections.Counter()
    mute_mute_specs = {s[0] for s in mute_mute}
    for counter in mute_mute.values():
        mute_mute_by_type.update(counter)
    for etype, n in sorted(mute_mute_by_type.items()):
        env[f"mute_mute_twin_rows_{etype}"] = Envelope(
            f"of those, rows labelled `{etype}`",
            n,
            sum(mute_mute_by_type.values()),
            "rows",
            ("mute", "site_comp162", "error_type"),
            inputs,
            expected=419,
            note="the two labels split the twin sites exactly in half, which is what "
            "'equal counts' means: the same call accused twice under two names, "
            "both mute. Every one of these sites belongs to "
            + ", ".join(sorted(mute_mute_specs))
            + ".",
        )
    remainder_sites = [
        s for s in mute_sites if s not in legible_sites and s not in mute_mute
    ]
    env["mute_only_rows"] = Envelope(
        "mute rows at sites with no legible twin and no equal-count second type",
        sum(mute_sites[s] for s in remainder_sites),
        len(mute_rows),
        "rows",
        ("mute", "site_comp162", "error_type"),
        inputs,
        expected=10926,
    )
    env["mute_only_sites"] = Envelope(
        "sites in that remainder",
        len(remainder_sites),
        len(mute_sites),
        "sites",
        ("mute", "site_comp162", "error_type"),
        inputs,
        expected=183,
    )
    env["but_found_dot"] = Envelope(
        "rows whose observed value is empty (`but found .`)",
        sum(1 for r in rows if observed(r) == ""),
        total,
        "rows",
        ("observed_value",),
        inputs,
        expected=98,
    )

    # Repetition, under the 8-tuple - and, separately, under the ErrorSummary 5-tuple.
    ident = collections.Counter(identity(r) for r in rows)
    env["identities_8tuple"] = Envelope(
        "distinct identities under the 8-tuple",
        len(ident),
        total,
        "identities / rows",
        ("identity8",),
        inputs,
        expected=6344,
    )
    env["repeated_rows"] = Envelope(
        "rows that are a repeat of an identity already seen",
        total - len(ident),
        total,
        "rows",
        ("identity8",),
        inputs,
        expected=total - 6344,
        note="67.74 % of the corpus is repetition of an identity under the 8-tuple.",
    )
    env["max_repetition"] = Envelope(
        "largest number of rows carried by one 8-tuple identity",
        max(ident.values()),
        total,
        "rows",
        ("identity8",),
        inputs,
        expected=49,
    )
    summary5 = {
        (r["spec"], error_type(r), r["class"], r["method"], r["source"]) for r in rows
    }
    env["identities_errorsummary_5tuple"] = Envelope(
        "distinct identities under the `ErrorSummary` 5-tuple `(spec, error, class, method, location)`",
        len(summary5),
        total,
        "identities / rows",
        ("identity8", "error_type"),
        inputs,
        expected=409,
        note="a different question from the 8-tuple; the two are never interchanged.",
    )

    # Shard disjointness - what makes `shards` and not `replicas` the right word.
    shards_of_identity: dict[tuple[str, ...], set[str]] = collections.defaultdict(set)
    apks_by_shard: dict[str, set[str]] = collections.defaultdict(set)
    for row in rows:
        shards_of_identity[identity(row)].add(row["_shard"])
        apks_by_shard[row["_shard"]].add(row["apk"])
    seen: set[str] = set()
    overlap = 0
    for shard in sorted(apks_by_shard):
        overlap += len(seen & apks_by_shard[shard])
        seen |= apks_by_shard[shard]
    env["identities_spanning_shards"] = Envelope(
        "8-tuple identities appearing in more than one shard",
        sum(1 for s in shards_of_identity.values() if len(s) > 1),
        len(ident),
        "identities",
        ("identity8", "shards"),
        inputs,
        expected=0,
        note="zero, so 0 % of the repetition comes from replication: it is all within-shard.",
    )
    env["shard_apk_overlap"] = Envelope(
        "APKs appearing in more than one shard",
        overlap,
        len(seen),
        "apks",
        ("shards",),
        inputs,
        expected=0,
    )
    env["distinct_apks"] = Envelope(
        "distinct APKs across the eight shards",
        len(seen),
        None,
        "apks",
        ("shards",),
        inputs,
        expected=112,
    )

    per_spec_mute = {
        spec: Envelope(
            f"mute rows in {spec}",
            n,
            len(mute_rows),
            "rows",
            ("mute",),
            inputs,
        )
        for spec, n in collections.Counter(r["spec"] for r in mute_rows).most_common()
    }

    footprint = {}
    for spec, labelled in (
        ("TrustManagerFactorySpec", "UnsafeAlgorithm"),
        ("SecureRandomSpec", "UnsafeAlgorithm"),
    ):
        by_type = collections.Counter(error_type(r) for r in rows if r["spec"] == spec)
        seq = by_type.get("InvalidSequenceOfMethodCalls", 0)
        lab = by_type.get(labelled, 0)
        footprint[spec] = {
            "sequence": Envelope(
                f"{spec} `InvalidSequenceOfMethodCalls` rows",
                seq,
                sum(by_type.values()),
                "rows",
                ("error_type",),
                inputs,
                expected={"TrustManagerFactorySpec": 2855, "SecureRandomSpec": 2882}[
                    spec
                ],
            ).to_dict(),
            "labelled": Envelope(
                f"{spec} `{labelled}` rows",
                lab,
                sum(by_type.values()),
                "rows",
                ("error_type",),
                inputs,
                expected={"TrustManagerFactorySpec": 61, "SecureRandomSpec": 0}[spec],
            ).to_dict(),
            "sequence_over_labelled": round(seq / lab, 4) if lab else None,
        }

    return {
        "scalars": {k: v.to_dict() for k, v in env.items()},
        "per_spec_mute": {k: v.to_dict() for k, v in per_spec_mute.items()},
        "error_types": dict(
            sorted(collections.Counter(error_type(r) for r in rows).items())
        ),
        "shards": {shard: len(apks) for shard, apks in sorted(apks_by_shard.items())},
        "tools": sorted({r["tool"] for r in rows}),
        "reps": sorted({r["rep"] for r in rows}),
        "structural_footprint": footprint,
    }


# ---------------------------------------------------------------------------
# The publishable Android tier (task 1.4)
# ---------------------------------------------------------------------------

# Transcribed from ase-journal/docs/20260806_owasp_cwe_mapping_report.md:1251-1259 and the
# per-row tables at :146-164. Every one of these is re-measured from the article corpus
# below; the transcription is the claim, the measurement is the check.
ANDROID_TIER: tuple[tuple[str, str, str, int, int, int], ...] = (
    ("SSLContextSpec", "UnsafeProtocol", "TLS", 8648, 60, 65),
    ("KeyStoreSpec", "InvalidKeyStoreType", "AndroidKeyStore", 2005, 11, 12),
    ("TrustManagerFactorySpec", "UnsafeAlgorithm", "X509", 643, 3, 5),
    ("CipherSpec", "UnsafeAlgorithm", "RSA/ECB/OAEPWithSHA1AndMGF1Padding", 109, 1, 1),
    ("SignatureSpec", "UnsafeAlgorithm", "SHA256WITHRSA", 4, 1, 1),
)


def measure_android_tier(
    rows: list[dict[str, str]], freeze: FreezeRegistry
) -> dict[str, Any]:
    """
    Measure the per-specification tier the group file predicts, row by row.

    Each tier row is selected by specification, error type and observed value at
    once. All three are needed: the same specification reports several types, and
    the same type reports several values, so a looser selection would reproduce
    the expected count by accident.

    Events and unique misuses are both carried, because the two answer different
    questions -- how often it was reported, and how many distinct misuses were
    behind it -- and the lineage published both.
    """
    error_type = make_error_type(freeze)
    observed = make_observed_value(freeze)
    misuse = make_key(freeze.require("misuse_article"))

    total_rows = len(rows)
    all_misuses = len({misuse(r) for r in rows})

    out: list[dict[str, Any]] = []
    ev_sum = um_sum = 0
    for spec, etype, value, exp_ev, exp_apps, exp_um in ANDROID_TIER:
        sel = [
            r
            for r in rows
            if r["spec"] == spec and error_type(r) == etype and observed(r) == value
        ]
        apps = len({r["apk"] for r in sel})
        misuses = len({misuse(r) for r in sel})
        ev_sum += len(sel)
        um_sum += misuses
        out.append(
            {
                "spec": spec,
                "error_type": etype,
                "observed_value": value,
                "events": Envelope(
                    f"{spec} / {etype} / `{value}` events",
                    len(sel),
                    total_rows,
                    "rows",
                    ("error_type", "observed_value"),
                    ART_IN,
                    expected=exp_ev,
                ).to_dict(),
                "apps": Envelope(
                    f"{spec} / {etype} / `{value}` applications",
                    apps,
                    113,
                    "apks",
                    ("error_type", "observed_value"),
                    ART_IN,
                    expected=exp_apps,
                ).to_dict(),
                "misuses": Envelope(
                    f"{spec} / {etype} / `{value}` unique misuses",
                    misuses,
                    all_misuses,
                    "misuses",
                    ("error_type", "observed_value", "misuse_article"),
                    ART_IN,
                    expected=exp_um,
                ).to_dict(),
            }
        )

    return {
        "rows": out,
        "total_events": Envelope(
            "events in the publishable Android tier",
            ev_sum,
            total_rows,
            "rows",
            ("error_type", "observed_value"),
            ART_IN,
            expected=11409,
        ).to_dict(),
        "total_misuses": Envelope(
            "unique misuses in the publishable Android tier",
            um_sum,
            all_misuses,
            "misuses",
            ("error_type", "observed_value", "misuse_article"),
            ART_IN,
            expected=84,
        ).to_dict(),
        "source": {
            "tier_table": rel(ARTICLE_TIER_REPORT) + ":1251-1259 (rows at :146-164)",
            "tier_table_sha256": sha256_file(ARTICLE_TIER_REPORT),
            "api_level": "API 30 (Android 11)",
            "api_level_sources": [
                rel(ARTICLE_DATASET_TEX) + ":5",
                rel(ARTICLE_TIER_REPORT) + ":622-648",
            ],
            "conscrypt_branch": "android11-release",
        },
    }


# ---------------------------------------------------------------------------
# Specification sets (task 1.5 context: what emits the mute rows)
# ---------------------------------------------------------------------------


def _split_call_args(text: str, start: int) -> list[str]:
    """Split the argument list of a call whose `(` has just been consumed.

    String literals are respected, so the comma inside `"{SHA-256, SHA-384, SHA-512}"`
    does not create a fifth argument - the naive split reports 6 arguments for 6 of the
    51 sites and would put the three/four-argument census three apart.
    """
    depth = 1
    i = start
    in_quote = False
    escaped = False
    args: list[str] = []
    current: list[str] = []
    while depth:
        ch = text[i]
        if escaped:
            escaped = False
            current.append(ch)
            i += 1
            continue
        if in_quote and ch == "\\":
            escaped = True
            current.append(ch)
            i += 1
            continue
        if ch == '"':
            in_quote = not in_quote
        if not in_quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            elif ch == "," and depth == 1:
                args.append("".join(current))
                current = []
                i += 1
                continue
        current.append(ch)
        i += 1
    args.append("".join(current))
    return args


def measure_spec_sets() -> dict[str, Any]:
    """
    Count what the specification sets carry: files, report sites and their arity.

    `addError` and `Log.v` are counted per file rather than per occurrence, since
    the question is how many specifications report at all, not how loudly.

    The arity histogram is over `jca` alone and is what makes INV-INS-119
    measurable: a `new ErrorDescription(` with three arguments passes its message
    where the location is read, so the count of three-argument sites is the size
    of that defect in the frozen seed.
    """
    sets: dict[str, Any] = {}
    for name in SPEC_SET_DIRS:
        directory = MOP_RESOURCES / name
        files = sorted(directory.glob("*.mop"))
        with_add_error = sum(
            1
            for f in files
            if "addError" in f.read_text(encoding="utf-8", errors="replace")
        )
        with_log_v = sum(
            1
            for f in files
            if "Log.v" in f.read_text(encoding="utf-8", errors="replace")
        )
        sets[name] = {
            "path": rel(directory),
            "files": len(files),
            "with_addError": with_add_error,
            "with_Log_v": with_log_v,
        }

    jca = MOP_RESOURCES / "jca"
    arity = collections.Counter()
    per_file = collections.Counter()
    for path in sorted(jca.glob("*.mop")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"new ErrorDescription\(", text):
            args = _split_call_args(text, match.end())
            arity[len(args)] += 1
            per_file[path.name] += 1
    total = sum(arity.values())
    return {
        "sets": sets,
        "error_description": {
            "total": Envelope(
                "`new ErrorDescription(` sites in the frozen `jca` set",
                total,
                total,
                "sites",
                (),
                ("jca_spec_set",),
                expected=51,
            ).to_dict(),
            "three_arg": Envelope(
                "three-argument sites (no message: these emit `unknown`)",
                arity.get(3, 0),
                total,
                "sites",
                (),
                ("jca_spec_set",),
                expected=25,
            ).to_dict(),
            "four_arg": Envelope(
                "four-argument sites (a message is supplied)",
                arity.get(4, 0),
                total,
                "sites",
                (),
                ("jca_spec_set",),
                expected=26,
            ).to_dict(),
            "other_arity": {
                str(k): v for k, v in sorted(arity.items()) if k not in (3, 4)
            },
            "by_file": dict(sorted(per_file.items())),
        },
    }


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def build_baseline(freeze: FreezeRegistry = DEFAULT_FREEZE) -> dict[str, Any]:
    """
    Assemble both corpora, the set counts and the definitions into one result.

    The definitions travel inside the artefact, not beside it, so a recorded
    number and the definition that produced it cannot be separated. The `jca` set
    enters as an input with a digest over its `.mop` files, for the same reason
    every CSV does.
    """
    article = load_article()
    comp162 = load_comp162()

    inputs = dict(article.inputs)
    inputs.update(comp162.inputs)
    inputs["jca_spec_set"] = {
        "path": rel(MOP_RESOURCES / "jca"),
        "sha256": _dir_sha256(MOP_RESOURCES / "jca", "*.mop"),
        "reader": "text scan (`new ErrorDescription(` with string-literal-aware argument split)",
        "files": len(list((MOP_RESOURCES / "jca").glob("*.mop"))),
    }

    return {
        "change": "gh104-legible-violation-reports",
        "group": "E0 - baseline and definitions",
        "definitions": {
            key: {
                "definition": item["definition"],
                "value": (
                    list(item["value"])
                    if isinstance(item["value"], tuple)
                    else item["value"]
                ),
                "why": item["why"],
            }
            for key, item in sorted(freeze.items.items())
        },
        "instrument": {
            "comp162_reader": {
                "columns": len(COMP162_HEADER),
                "header": list(COMP162_HEADER),
                "frozen_in": "scripts/gh104_baseline.py",
            },
            "article_reader": {
                "columns": len(ARTICLE_HEADER),
                "header": list(ARTICLE_HEADER),
                "frozen_in": "scripts/gh104_baseline.py",
            },
            "why_not_shared": (
                "aperv_tool.analysis.violations.read_errors_csv checks one in-place literal "
                "(ERRORS_CSV_HEADER) and raises on any other header; gh104 Group 5 rewrites that "
                "literal to 13 columns, after which the shared reader rejects every comp162 file. "
                "An import pins nothing."
            ),
            "parity_is_not_correctness": (
                "Reproducing a campaign's number proves the pipeline is unchanged. It proves "
                "nothing whatever about whether the estimator is right - if the original was "
                "wrong, parity reproduces the error exactly. "
                "(docs/20260815_gh103_analysis_layer.md:108-110)"
            ),
        },
        "inputs": inputs,
        "article": measure_article(article.rows, freeze),
        "comp162": measure_comp162(comp162.rows, sorted(comp162.inputs), freeze),
        "android_tier": measure_android_tier(article.rows, freeze),
        "spec_sets": measure_spec_sets(),
    }


def _dir_sha256(directory: Path, pattern: str) -> str:
    """One digest over the sorted (name, bytes) of a directory - the set's content address."""
    h = hashlib.sha256()
    for path in sorted(directory.glob(pattern)):
        h.update(path.name.encode())
        h.update(b"\0")
        h.update(path.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Disagreement census
# ---------------------------------------------------------------------------


def collect_envelopes(
    node: Any, path: str = ""
) -> Iterable[tuple[str, dict[str, Any]]]:
    """
    Walk the result and yield every envelope with its dotted path.

    An envelope is recognised structurally -- a mapping carrying `numerator` and
    `definitions` -- rather than by where it sits, so a measurement added
    anywhere in the tree is checked without this walker being told about it. The
    recursion stops at an envelope: its own fields are data, not more
    envelopes.
    """
    if isinstance(node, dict):
        if "numerator" in node and "definitions" in node:
            yield path, node
            return
        for key, value in node.items():
            yield from collect_envelopes(value, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from collect_envelopes(value, f"{path}[{i}]")


def disagreements(baseline: Mapping[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """
    Every envelope whose measurement contradicts its expected value.

    Only `agrees is False` qualifies. An envelope with no expectation is not a
    disagreement -- it is a number nobody predicted, which is a different thing
    and is reported separately by `main`.
    """
    return [(p, e) for p, e in collect_envelopes(baseline) if e["agrees"] is False]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _env_row(env: Mapping[str, Any]) -> str:
    """
    One markdown table row for an envelope.

    A disagreement is rendered in bold and an absent expectation as a dash, so
    that the two ways of not saying "reproduces" stay distinguishable at a
    glance.
    """
    den = "-" if env["denominator"] is None else f"{env['denominator']:,}"
    pct = "-" if env["percent"] is None else f"{env['percent']:.2f} %"
    defs = ", ".join(f"`{d}`" for d in env["definitions"]) or "-"
    exp = "-" if env["expected"] is None else f"{env['expected']:,}"
    mark = {True: "reproduces", False: "**DISAGREES**", None: "-"}[env["agrees"]]
    return (
        f"| {env['quantity']} | {env['numerator']:,} | {den} | {pct} | {defs} | "
        f"{', '.join('`' + i + '`' for i in env['inputs'])} | {exp} | {mark} |"
    )


_TABLE_HEAD = (
    "| quantity | numerator | denominator | % | definitions | inputs | expected | verdict |\n"
    "|---|---:|---:|---:|---|---|---:|---|"
)


def render_markdown(b: Mapping[str, Any]) -> str:
    """
    Render the baseline as the reading of it.

    The numbers come with their basis and the definitions live in the companion
    file, which is what lets this document be read straight through: parity is
    the claim here, and parity is not correctness -- reproducing a number proves
    the pipeline unchanged and says nothing about the estimator.
    """
    L: list[str] = []
    add = L.append

    add("# gh104 E0 - the measured baseline")
    add("")
    add(
        "Generated by `scripts/gh104_baseline.py`. Every number below carries its numerator, its "
        "denominator, the unit it counted, the ids of the freeze items that produced it, and the "
        "input files it was read from. The definitions themselves, and the reason there are two "
        "readers rather than one, are in `definitions.md` beside this file."
    )
    add("")
    add(
        "The `expected` column is the value the change's E0 brief predicted on 2026-08-16. It is "
        "recorded so that agreement is visible as a result and not assumed as a premise: where a "
        "measurement disagrees with the brief, the measurement is what this file publishes."
    )
    add("")
    add(
        "**Identity era.** Every deduplicated count in this file belongs to the **five-part "
        "era**: the identity is `(spec, error, class, method, location)` and `unique_msg` has "
        "five parts. Task 9.2 of this change adds `code` and `event` to it, and counts of the "
        "two eras are not comparable (INV-CORE-41, INV-CORE-57). The discontinuity between them "
        "is measured in `identity_discontinuity.md` beside this file — zero on comp162, which "
        "predates the envelope, and non-zero on the differential-harness corpus, which carries "
        "`ev=`. A reader comparing a number here with a number from a later campaign must read "
        "that file first."
    )
    add("")

    dis = disagreements(b)
    add("## Disagreements with the brief")
    add("")
    if dis:
        add(
            "The following measurements do **not** reproduce the expected value. The data wins."
        )
        add("")
        add(_TABLE_HEAD)
        for path, env in dis:
            add(_env_row(env))
    else:
        add(
            "None. Every expected value in the E0 brief reproduces exactly from the pinned inputs "
            "under the declared definitions."
        )
    add("")

    add("## Inputs")
    add("")
    add("| key | path | sha256 | reader | rows/files |")
    add("|---|---|---|---|---:|")
    for key, meta in b["inputs"].items():
        count = meta.get("rows", meta.get("files", ""))
        add(
            f"| `{key}` | `{meta['path']}` | `{meta['sha256']}` | {meta['reader']} | "
            f"{count:,} |"
        )
        for member, mmeta in meta.get("members", {}).items():
            add(
                f"| &nbsp;&nbsp;`{member}` | `{mmeta['path']}` | `{mmeta['sha256']}` | "
                f"(shard of `{key}`) | {mmeta['rows']:,} |"
            )
    add("")
    add(
        "The comp162 shards are additionally pinned, byte for byte, by "
        "`modules/aperv-tool/tests/fixtures/cmp162_manifest.json` (465 entries, the eight "
        "`errors.csv` among them). `tests/parity/test_gh104_baseline.py` fails - it does not skip - "
        "if the tree on disk is present and disagrees with that pin."
    )
    add("")

    add("## The instrument, and its discontinuity")
    add("")
    add(
        "The two corpora were produced by different pipelines and do not have the same CSV layout. "
        "comp162 has **11 columns** and carries `source`, the `File.java:line` of the accused call. "
        "The article dataset has **10 columns** and has no `source` at all. There is no single "
        "reader for both, and the canonical reader in the analysis layer reads neither for long: "
        "it checks one in-place header literal that Group 5 rewrites to 13 columns."
    )
    add("")
    add("| corpus | columns | header |")
    add("|---|---:|---|")
    add(
        f"| comp162 (fixture) | {b['instrument']['comp162_reader']['columns']} | "
        f"`{','.join(b['instrument']['comp162_reader']['header'])}` |"
    )
    add(
        f"| article (published) | {b['instrument']['article_reader']['columns']} | "
        f"`{','.join(b['instrument']['article_reader']['header'])}` |"
    )
    add("")
    add("> " + b["instrument"]["parity_is_not_correctness"])
    add("")
    add(
        "This is why the site tuple is a freeze item and not a helper: it is a 4-tuple on comp162 "
        "and a 3-tuple on the article, and the two are not variants of one convention - they are "
        "what the two layouts admit."
    )
    add("")

    add("## The article dataset (published corpus)")
    add("")
    add(_TABLE_HEAD)
    for env in b["article"]["scalars"].values():
        add(_env_row(env))
    add("")
    add(
        "Nineteen distinct message strings for 97,018 events, and 72.93 % of the events say only "
        "`unknown`. The mute rows are not a tail: they are the corpus."
    )
    add("")

    add("### `but found .` - legible in form, mute in content")
    add("")
    add(_TABLE_HEAD)
    add(_env_row(b["article"]["scalars"]["but_found_dot"]))
    for env in b["article"]["but_found_dot_by_spec"].values():
        add(_env_row(env))
    add("")
    add(
        "These rows ran the full message-building path and arrived with an empty observed value. "
        "They are the same defect as `unknown` wearing a sentence."
    )
    add("")

    add("### Third-party attribution")
    add("")
    add(_TABLE_HEAD)
    for env in b["article"]["third_party"].values():
        add(_env_row(env))
    add("")
    add(
        "The prefix set is a decision, so all three cuts are published. Seven points of headline "
        "separate the narrowest from the widest."
    )
    add("")

    add(
        "### Weak digests under `UnsafeAlgorithm` - three denominators, three questions"
    )
    add("")
    add(_TABLE_HEAD)
    for env in b["article"]["unsafe_algorithm"].values():
        add(_env_row(env))
    add("")
    add("Composition of the numerator, by observed value:")
    add("")
    add(_TABLE_HEAD)
    for env in b["article"]["weak_digest_breakdown"].values():
        add(_env_row(env))
    add("")
    add(
        "Group 2 task 2.4 quotes the second and third of these as the declared cost of accepting "
        "what the api30 rule admits, so all three denominators are stated here: they are different "
        "questions and the same numerator answers none of them twice."
    )
    add("")

    add("## The comp162 fixture")
    add("")
    add(
        "`cmp162 is a fixture, not a corpus`: no number computed on it answers a research question "
        "(`docs/20260815_gh103_analysis_layer.md:112`). It is here because it is the only tree that "
        "carries `source`, so it is the only one on which a *site* can be resolved to a call."
    )
    add("")
    add(_TABLE_HEAD)
    for env in b["comp162"]["scalars"].values():
        add(_env_row(env))
    add("")
    add(
        "The twin rows are the argument of this change in one line: at 101 sites the specification "
        "emits a mute row **and** a legible row, so the words existed and the report went out "
        "without them. There are zero sites that emit only legible rows."
    )
    add("")

    add("### Mute rows per specification")
    add("")
    add(
        "The specification names here are the names in the data: `IvParameterSpecSpec` and "
        "`SecretKeySpecSpec` carry the doubled suffix, and the E0 brief's shorter labels for the "
        "same two rows are abbreviations, not different quantities."
    )
    add("")
    add(_TABLE_HEAD)
    for env in b["comp162"]["per_spec_mute"].values():
        add(_env_row(env))
    add("")

    add("## The structural footprint Group 8 records but does not repair")
    add("")
    add(
        "Two structural facts leave a measurable mass in both corpora. Neither is repaired by this "
        "change - repairing either changes what is accused - so both are recorded as ratios, per "
        "specification, on both corpora (design D-1; task 8.12)."
    )
    add("")
    add(
        "**(a) The clause-encoding orphan's second report.** Every clause-encoding orphan fires its "
        "body report *and* its all-`fail` row, so an `InvalidSequenceOfMethodCalls` accompanies each "
        "labelled accusation. On the article corpus the two counts sit side by side:"
    )
    add("")
    add(_TABLE_HEAD)
    for spec, d in b["article"]["structural_footprint"].items():
        add(_env_row(d["sequence"]))
        add(_env_row(d["labelled"]))
    add("")
    add(
        "| specification | sequence / labelled |\n|---|---:|\n"
        + "\n".join(
            f"| {spec} | {d['sequence_over_labelled']} |"
            for spec, d in b["article"]["structural_footprint"].items()
        )
    )
    add("")
    add(
        "`TrustManagerFactorySpec` at 9,015 against 9,014 is the signature: one sequence report per "
        "labelled one, off by a single row. `SSLContextSpec` at 1.99 is the same shape at twice the "
        "rate."
    )
    add("")
    add(
        "**(b) The DEX-path `g1`+`g2` double fire.** On the DEX path the one-argument `getInstance` "
        "fires both `g1` and `g2` and reaches `fail`, so the sequence report appears without any "
        "labelled sibling at all:"
    )
    add("")
    add(_TABLE_HEAD)
    for spec, d in b["comp162"]["structural_footprint"].items():
        add(_env_row(d["sequence"]))
        add(_env_row(d["labelled"]))
    add("")
    add(
        "| specification | sequence / labelled |\n|---|---:|\n"
        + "\n".join(
            f"| {spec} | {d['sequence_over_labelled'] if d['sequence_over_labelled'] is not None else 'undefined (no labelled rows)'} |"
            for spec, d in b["comp162"]["structural_footprint"].items()
        )
    )
    add("")
    add(
        "`SecureRandomSpec` emits 2,882 sequence rows and not one labelled row: there is no "
        "accusation behind the accusation."
    )
    add("")

    add("## The Android tier this change is aimed at")
    add("")
    src = b["android_tier"]["source"]
    add(
        f"The pivot to Android rests on a publishable tier with primary-source evidence, transcribed "
        f"from `{src['tier_table']}` and **re-measured here from the article corpus**. It is the "
        "denominator against which Group 2's allow-list transcription and Group 10 task 10.5's "
        "device reading are judged."
    )
    add("")
    add("| spec / ErrorType / observed value | events | apps | misuses | verdict |")
    add("|---|---:|---:|---:|---|")
    for row in b["android_tier"]["rows"]:
        verdicts = {
            row["events"]["agrees"],
            row["apps"]["agrees"],
            row["misuses"]["agrees"],
        }
        mark = "reproduces" if verdicts == {True} else "**DISAGREES**"
        add(
            f"| `{row['spec']} / {row['error_type']} / {row['observed_value']}` | "
            f"{row['events']['numerator']:,} | {row['apps']['numerator']:,} | "
            f"{row['misuses']['numerator']:,} | {mark} |"
        )
    tot_e = b["android_tier"]["total_events"]
    tot_m = b["android_tier"]["total_misuses"]
    add(
        f"| **total** | **{tot_e['numerator']:,}** | | **{tot_m['numerator']:,}** | "
        f"{tot_m['numerator']:,} of {tot_m['denominator']:,} misuses = {tot_m['percent']:.1f} % |"
    )
    add("")
    add(
        f"Events are counted over the {tot_e['denominator']:,}-row corpus under `error_type` and "
        f"`observed_value`; misuses under `misuse_article`, the 4-tuple "
        "`(apk, spec, class, method)`, which reproduces the report's own R1 counts exactly."
    )
    add("")
    add("### Context fixation")
    add("")
    add(
        f"Every application ran in **one** environment: an x86_64 Android emulator at "
        f"**{src['api_level']}**, and the Conscrypt sources behind the allow-list verdicts are "
        f"pinned to branch **`{src['conscrypt_branch']}`** rather than to `master`. Sources: "
        + ", ".join(f"`{s}`" for s in src["api_level_sources"])
        + "."
    )
    add("")
    add(
        "This is what makes `MetaCrySL/generated/api30/*.cryptsl` *the* oracle and not one option "
        "among several. The constants that decide the largest violation bucket differ between "
        "`android11-release` and `master`, so an allow-list transcribed against the wrong branch "
        "would be wrong in exactly the bucket that matters most."
    )
    add("")

    add("## The specification sets that emit these reports")
    add("")
    add("| set | path | `.mop` files | with `addError` | with `Log.v` |")
    add("|---|---|---:|---:|---:|")
    for name, meta in b["spec_sets"]["sets"].items():
        add(
            f"| `{name}` | `{meta['path']}` | {meta['files']} | {meta['with_addError']} | "
            f"{meta['with_Log_v']} |"
        )
    add("")
    add(
        "The JCA family reports through `addError`; the two generic families report through "
        "`Log.v` and have no structured report at all. `jca_android_bug_predicate` is the archived "
        "derived set, renamed out of the way by the wave-0 barrier so the successor may take the "
        "`jca_android` name; it is not selectable."
    )
    add("")
    add("### The mechanical origin of `unknown`")
    add("")
    add(_TABLE_HEAD)
    for key in ("total", "three_arg", "four_arg"):
        add(_env_row(b["spec_sets"]["error_description"][key]))
    add("")
    add(
        "Half the report sites in the frozen `jca` set - 25 of 51 - call the three-argument "
        "`new ErrorDescription(...)`, which has no message parameter. Those 25 sites are where "
        "`unknown` comes from. It is not a runtime failure, a lost field or a transport defect: it "
        "is the constructor the specification chose."
    )
    add("")
    return "\n".join(L) + "\n"


def render_definitions(b: Mapping[str, Any]) -> str:
    """
    Render the freeze items and the instrument discontinuity as `definitions.md`.

    It is generated from the same registry the measurements enforce, so the
    document cannot drift from the code that produced `baseline.json` -- a
    hand-written definitions file would be wrong the first time an item
    changed.
    """
    L: list[str] = []
    add = L.append
    add("# gh104 E0 - definitions and the instrument")
    add("")
    add(
        "Generated by `scripts/gh104_baseline.py` from the freeze-item registry it enforces, so "
        "this file cannot drift from the code that produced `baseline.json`."
    )
    add("")
    add("## The freeze-item rule")
    add("")
    add(
        "A **freeze item** is a knob that decides a number, and which the code must therefore not "
        "decide on its own. `scripts/gh104_baseline.py` supplies no default for any of them: a "
        "measurement reached without one raises `FreezeItemUnset` naming what is missing rather "
        "than proceeding with something plausible. The rule is copied from the campaign analysis "
        "layer (`docs/20260815_gh103_analysis_layer.md:62-84`), and it is not defensive "
        "programming - each of the items below changes the answer, and each has a value that looks "
        "obviously right until someone checks."
    )
    add("")
    add("## The items")
    add("")
    for key, item in b["definitions"].items():
        value = item["value"]
        rendered = (
            ", ".join(f"`{v}`" for v in value)
            if isinstance(value, list)
            else f"`{value}`"
        )
        add(f"### `{key}`")
        add("")
        add(item["definition"])
        add("")
        add(f"**Frozen value.** {rendered}")
        add("")
        add(f"**Why it is frozen.** {item['why']}")
        add("")
    add("## The instrument, and the discontinuity between the two corpora")
    add("")
    add(
        "The baseline is measured on two corpora that do not share a CSV layout, and it reads each "
        "through a reader frozen in `scripts/gh104_baseline.py` itself."
    )
    add("")
    add("| corpus | columns | header |")
    add("|---|---:|---|")
    add(
        f"| comp162 (`experimento-comp162/results/*/*/errors.csv`) | "
        f"{b['instrument']['comp162_reader']['columns']} | "
        f"`{','.join(b['instrument']['comp162_reader']['header'])}` |"
    )
    add(
        f"| article (`ase-journal/dataset/results/errors.csv`) | "
        f"{b['instrument']['article_reader']['columns']} | "
        f"`{','.join(b['instrument']['article_reader']['header'])}` |"
    )
    add("")
    add("### Why not the canonical reader")
    add("")
    add(b["instrument"]["why_not_shared"])
    add("")
    add(
        "So the shared reader would resolve to whichever header happens to be in force on the day "
        "the script runs - the opposite of what a baseline is for. Both readers are declared here, "
        "beside each other, and both raise `FrozenHeaderMismatch` on any other layout. "
        "gh104's own `specs/campaign-analysis/spec.md` delta states the same rule from the other "
        "side (INV-CAN-25): no reader under `analysis/` may accept a historical layout, and a "
        "reader for the 10-column article dataset or the 11-column pre-change layout lives outside "
        "the module, in the E0 baseline script, declared where its numbers are published."
    )
    add("")
    add("### Parity is not correctness")
    add("")
    add("> " + b["instrument"]["parity_is_not_correctness"])
    add("")
    add(
        "Every number in `baseline.md` is a parity claim about the pipeline that produced these "
        "bytes. None of them is a claim that the estimator behind it was right - that is precisely "
        "what the rest of gh104 is about."
    )
    add("")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def write_baseline(
    out_dir: Path = OUT_DIR, freeze: FreezeRegistry = DEFAULT_FREEZE
) -> dict[str, Any]:
    """
    Build the baseline and write the JSON and both markdown documents.

    All three come from one build, so the artefact the byte-identical test
    compares and the two documents a human reads can never describe different
    runs.
    """
    baseline = build_baseline(freeze)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "baseline.json").write_text(
        json.dumps(baseline, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "baseline.md").write_text(render_markdown(baseline), encoding="utf-8")
    (out_dir / "definitions.md").write_text(
        render_definitions(baseline), encoding="utf-8"
    )
    return baseline


def main(argv: Sequence[str] | None = None) -> int:
    """
    Write the baseline and report the envelope counts, returning 1 on any disagreement.

    Three numbers are printed rather than one: how many envelopes there are, how
    many carry an expected value, and how many disagree. The middle one is what
    keeps the exit code honest -- a run where nothing disagreed because nothing
    was predicted is green, and only the count says so.
    """
    parser = argparse.ArgumentParser(description="gh104 E0 baseline")
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_DIR,
        help="output directory (default: data/gh104)",
    )
    args = parser.parse_args(argv)

    baseline = write_baseline(args.out)
    envs = list(collect_envelopes(baseline))
    checked = [e for _, e in envs if e["expected"] is not None]
    bad = disagreements(baseline)
    print(f"wrote {args.out / 'baseline.json'}, baseline.md, definitions.md")
    print(
        f"envelopes: {len(envs)}; with an expected value: {len(checked)}; disagreements: {len(bad)}"
    )
    for path, env in bad:
        print(
            f"  DISAGREES {path}: measured {env['numerator']} expected {env['expected']}"
        )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

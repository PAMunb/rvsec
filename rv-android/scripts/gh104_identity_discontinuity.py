#!/usr/bin/env python3
"""gh104 E6 - the identity discontinuity `code` and `event` introduce.

`ErrorSummary.equals`/`hashCode` decide which violation reports survive deduplication
*inside the JVM*, before anything is written: `ErrorCollector.addError` writes a line only
when `errors.add(err)` succeeds on a `HashSet<ErrorDescription>`, and `ErrorDescription`
compares nothing but its `ErrorSummary`. Adding `code` and `event` to that identity is
therefore not bookkeeping - it changes how many lines a run emits, and it splits every
published deduplicated count into two eras that are not comparable (INV-CORE-57).

This script measures the split before it is made, on two corpora that answer two different
questions:

* **comp162** (`experimento-comp162/results/*/*/errors.csv`, the E3 trial) is the corpus the
  published numbers came from. It is read through Group 1's frozen 11-column reader, never
  through `aperv_tool.analysis.violations.read_errors_csv`, which Group 5 rewrote to a
  13-column header and which now rejects every comp162 file (design D-9). Its records
  predate the envelope, so every `code` and every `event` parses to the sentinel and the
  discontinuity is **zero by construction**. That zero is the five-part baseline, recorded
  as such - it is not a result about whether the identity change works.

* **the differential-harness evidence** (`data/gh104/evidence/harness/*.md`) is the corpus
  whose records carry `ev=`, and it is the one that decides E6. If the discontinuity is
  zero *there*, `code` and `event` add nothing to the identity, the change would be a no-op
  and design D-5 is re-opened (INV-INS-126).

Both corpora are measured under the same rule: `code` and `event` are read from the message
envelope exactly as `ErrorDescription` will read them - `code=<value>`, `ev=<value>` inside
a `v=1` envelope - and are the sentinel `UNSPECIFIED` when the message carries none. The
sentinel is what makes a legacy record's identity readable rather than empty.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gh104_baseline import FREEZE_ITEMS as BASELINE_FREEZE_ITEMS  # noqa: E402
from gh104_baseline import (  # noqa: E402
    Envelope,
    FreezeRegistry,
    load_comp162,
    make_error_type,
    make_key,
    rel,
    sha256_file,
)

RV_ANDROID = Path(__file__).resolve().parents[1]
OUT_DIR = RV_ANDROID / "data" / "gh104"
HARNESS_DIR = OUT_DIR / "evidence" / "harness"

SENTINEL = "UNSPECIFIED"

# The envelope grammar E1 emits, read exactly as `ErrorDescription` will read it: the two
# keys are matched on a word boundary so that `code=` inside the free-text `msg='...'` tail
# cannot be mistaken for the record's own key, and a value runs to the next space.
ENVELOPE_MARKER = "v=1 "
CODE_RE = re.compile(r"(?:^|\s)code=(\S+)")
EV_RE = re.compile(r"(?:^|\s)ev=(\S+)")

# One line of a harness report's `## Envelopes` section:
#     - `<trace>` (A) `spec=<S>,ev=<e>,type=<T>,msg=<message>`
# `msg=` is last and its value may contain commas, so it is taken as the whole remainder.
HARNESS_LINE_RE = re.compile(
    r"^- `(?P<trace>[^`]+)` \((?P<side>[AB])\) `spec=(?P<spec>[^,]*),ev=(?P<ev>[^,]*),"
    r"type=(?P<type>[^,]*),msg=(?P<msg>.*)`$"
)

# The self-test reports replay a synthetic mutant the harness writes into scratch to prove
# its four verdicts are reachable (design D-7). They measure the instrument, not the set, so
# they are excluded from the corpus and the exclusion is stated in every envelope below.
SELFTEST_PREFIX = "selftest"


# ---------------------------------------------------------------------------
# Freeze items - the definitions that decide these numbers
# ---------------------------------------------------------------------------

FREEZE_ITEMS: dict[str, dict[str, Any]] = {
    "identity8": BASELINE_FREEZE_ITEMS["identity8"],
    "error_type": BASELINE_FREEZE_ITEMS["error_type"],
    "identity5": {
        "definition": (
            "The identity era in force before this change: `ErrorSummary.equals`/`hashCode` "
            "compare `(spec, error, classQualifiedName, methodName, location)`. On comp162 "
            "`location` is the `source` column and `error` is part 4 of `unique_msg`."
        ),
        "value": ("spec", "error", "class", "method", "location"),
        "why": (
            "It is the identity every deduplicated count published before this change was "
            "computed under, so it is the baseline the discontinuity is measured against - "
            "not a candidate design."
        ),
    },
    "identity7": {
        "definition": (
            "The identity era this change introduces: the five fields of `identity5` plus "
            "`code` and `event`, both read from the message envelope. The message free text "
            "stays outside the identity in both eras."
        ),
        "value": ("spec", "error", "class", "method", "location", "code", "event"),
        "why": (
            "`code` alone would refine nothing - every specification of the set has at most "
            "one `@fail`, so `code=<SPEC>-ORDER-00` is a function of `spec` (design D-5). It "
            "is `event` that separates causes that share a call site, which is why the "
            "measurement that decides E6 must be taken on a corpus carrying `ev=`."
        ),
    },
    "envelope_parse": {
        "definition": (
            "`code` and `event` are the `code=` and `ev=` values of a `v=1` message "
            "envelope. A message carrying no envelope yields the sentinel `UNSPECIFIED` for "
            "both, never an empty string."
        ),
        "value": {"marker": ENVELOPE_MARKER.strip(), "sentinel": SENTINEL},
        "why": (
            "It is the rule `ErrorDescription.createErrorSummary` will apply on the device, "
            "so the measurement and the production path read the same field the same way. "
            "The sentinel keeps a legacy record's key readable and distinguishable from an "
            "envelope record whose event was named (INV-CORE-25)."
        ),
    },
    "harness_site": {
        "definition": (
            "On the harness corpus `class`, `method` and `location` are constant across "
            "every record and are held fixed, because `TraceRunner` resolves every trace "
            "line through one reflective frame and its record carries no frame at all "
            "(`spec`, `ev`, `type`, `msg` - `TraceRunner.java:320-324`)."
        ),
        "value": "one call site, held constant",
        "why": (
            "It is what makes this corpus the right instrument rather than a limitation of "
            "it: with the site fixed, the difference between the two identities is exactly "
            "what `code` and `event` add at one site - the case INV-INS-126 names, two "
            "events reported at one location."
        ),
    },
    "harness_corpus": {
        "definition": (
            "The deciding corpus is every `## Envelopes` record of "
            "`data/gh104/evidence/harness/*.md` whose file name does not begin with "
            f"`{SELFTEST_PREFIX}`; both replay sides (A and B) are read."
        ),
        "value": {
            "dir": "data/gh104/evidence/harness",
            "excluded_prefix": SELFTEST_PREFIX,
        },
        "why": (
            "The self-test reports replay a synthetic mutant written into scratch to prove "
            "the harness can reach all four verdicts; they measure the instrument, not the "
            "specification set, and counting them would inflate the corpus with authored "
            "differences. Both sides are read because the A side of the E4 rounds is itself "
            "a post-E1 snapshot and carries envelopes."
        ),
    },
}

DEFAULT_FREEZE = FreezeRegistry(FREEZE_ITEMS)


# ---------------------------------------------------------------------------
# The envelope parse - one rule, both corpora
# ---------------------------------------------------------------------------


def parse_envelope(message: str) -> tuple[str, str]:
    """`(code, event)` of a message, or the sentinel twice when it carries no envelope.

    Absence of the `v=1` marker is what decides, not absence of the keys: a message that
    merely happened to contain the text `ev=` outside an envelope is a legacy message and
    must produce the sentinel, or the two eras would not be distinguishable in the record.
    """
    text = message or ""
    if ENVELOPE_MARKER not in text:
        return SENTINEL, SENTINEL
    code = CODE_RE.search(text)
    event = EV_RE.search(text)
    return (
        code.group(1) if code else SENTINEL,
        event.group(1) if event else SENTINEL,
    )


# ---------------------------------------------------------------------------
# comp162 - the published corpus, zero by construction
# ---------------------------------------------------------------------------

CMP_IN = ("comp162_shards",)


def measure_comp162(
    rows: Sequence[Mapping[str, str]], freeze: FreezeRegistry
) -> dict[str, Any]:
    """
    Measure the discontinuity on the published corpus, where it is zero by construction.

    The zero is the point: comp162's records predate the envelope, so every `code`
    and `event` parses to the sentinel and the seven-part identity cannot separate
    anything the five-part identity joined. Recording that as a five-part baseline
    is what makes the harness figure readable -- without it, a reader has no way
    to tell a corpus the identity does not refine from an identity that refines
    nothing.

    The 8-tuple is reproduced here, from Group 1's frozen definition, for one
    reason: it is the tuple every published count of this corpus was computed
    under, and the two tuples must never be interchanged. Each envelope names the
    freeze items that produced it, so a definition that moves invalidates the
    number rather than silently changing it.
    """
    error_type = make_error_type(freeze)
    identity8 = make_key(freeze.require("identity8"))
    freeze.require("identity5")
    freeze.require("identity7")
    freeze.require("envelope_parse")

    total = len(rows)
    parsed = [(row, *parse_envelope(row.get("message", ""))) for row in rows]

    five = {
        (r["spec"], error_type(r), r["class"], r["method"], r["source"]) for r in rows
    }
    seven = {
        (r["spec"], error_type(r), r["class"], r["method"], r["source"], code, event)
        for r, code, event in parsed
    }
    enveloped = [
        1 for _, code, event in parsed if code != SENTINEL or event != SENTINEL
    ]
    eight = collections.Counter(identity8(r) for r in rows)

    env: dict[str, Envelope] = {}
    env["identities_8tuple"] = Envelope(
        "distinct identities under the 8-tuple `(apk, rep, tool, spec, class, method, source, message)`",
        len(eight),
        total,
        "identities / rows",
        ("identity8",),
        CMP_IN,
        expected=6344,
        note="Group 1's freeze item, reproduced here so the two tuples are never interchanged.",
    )
    env["identities_5tuple"] = Envelope(
        "distinct identities under the `ErrorSummary` 5-tuple `(spec, error, class, method, location)`",
        len(five),
        total,
        "identities / rows",
        ("identity5", "error_type"),
        CMP_IN,
        expected=409,
        note="the era every published deduplicated count of this corpus belongs to.",
    )
    env["identities_7tuple"] = Envelope(
        "distinct identities under the 7-tuple `(spec, error, class, method, location, code, event)`",
        len(seven),
        total,
        "identities / rows",
        ("identity7", "error_type", "envelope_parse"),
        CMP_IN,
        expected=409,
        note="equal to the 5-tuple count by construction: this corpus predates the envelope.",
    )
    env["records_carrying_an_envelope"] = Envelope(
        "records whose message carries a `v=1` envelope",
        len(enveloped),
        total,
        "rows",
        ("envelope_parse",),
        CMP_IN,
        expected=0,
        note="zero is the reason the discontinuity below is zero, and it is a property of the "
        "corpus, not a result about the identity.",
    )
    env["discontinuity"] = Envelope(
        "identities the 7-tuple adds over the 5-tuple",
        len(seven) - len(five),
        len(five),
        "identities / identities",
        ("identity5", "identity7", "envelope_parse"),
        CMP_IN,
        expected=0,
        note="zero **by construction** - labelled so, not read as a failure (INV-CORE-57).",
    )
    return {
        "corpus": "comp162 (E3 trial)",
        "reader": "frozen 11-column reader of `scripts/gh104_baseline.py`",
        "rows": total,
        "decides_e6": False,
        "envelopes": {key: value.to_dict() for key, value in env.items()},
    }


# ---------------------------------------------------------------------------
# the differential harness - the corpus that decides
# ---------------------------------------------------------------------------


def read_harness_records(
    directory: Path,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Every `## Envelopes` record of the harness reports, with the files they came from."""
    files = sorted(
        path
        for path in directory.glob("*.md")
        if not path.name.startswith(SELFTEST_PREFIX)
    )
    if not files:
        raise FileNotFoundError(f"no harness reports under {directory}/*.md")

    records: list[dict[str, str]] = []
    members: dict[str, Any] = {}
    for path in files:
        found = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            match = HARNESS_LINE_RE.match(line)
            if not match:
                continue
            code, event = parse_envelope(match.group("msg"))
            records.append(
                {
                    "report": path.name,
                    "run": path.name.split("-", 1)[0],
                    "trace": match.group("trace"),
                    "side": match.group("side"),
                    "spec": match.group("spec"),
                    "dispatched_event": match.group("ev"),
                    "error": match.group("type"),
                    "message": match.group("msg"),
                    "code": code,
                    "event": event,
                }
            )
            found += 1
        members[path.name] = {"sha256": sha256_file(path), "records": found}
    inputs = {
        "harness_reports": {
            "path": rel(directory) + "/*.md",
            "sha256": _aggregate_sha(members),
            "reader": "`## Envelopes` bullets of the differential-harness reports",
            "files": len(files),
            "records": len(records),
            "excluded": f"reports named `{SELFTEST_PREFIX}*` (the harness self-test mutant)",
            "members": members,
        }
    }
    return records, inputs


def _aggregate_sha(members: Mapping[str, Any]) -> str:
    """
    One digest over a group of input files, from their names and their digests.

    The names are hashed alongside the digests and in sorted order, so that
    renaming a member or reordering the group changes the aggregate. A digest of
    the contents alone would call two different corpora the same input.
    """
    digest = hashlib.sha256()
    for name in sorted(members):
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(bytes.fromhex(members[name]["sha256"]))
    return digest.hexdigest()


HARNESS_IN = ("harness_reports",)


def measure_harness(
    records: Sequence[Mapping[str, str]], freeze: FreezeRegistry
) -> dict[str, Any]:
    """
    Measure the discontinuity on the corpus that decides E6.

    This is the corpus whose records carry `ev=`, so this is where "does `code`
    and `event` separate anything" has an answer that is about the identity rather
    than about the era.

    Three narrowings, each guarding a way the number could flatter the change.
    `class`, `method` and `location` are constant across the corpus (freeze item
    `harness_site`), so they are held fixed rather than invented: including them
    would add a component that separates nothing. The collision count is computed
    over the enveloped records alone, because a split between an enveloped record
    and a legacy one is the era boundary showing through and not a cause the
    identity separated -- E6 is decided on that conservative number. And
    `by_event_alone` isolates the separations where all the causes share one
    `code`, which is the direct test of design D-5's claim that `code` on its own
    would refine nothing.
    """
    freeze.require("identity5")
    freeze.require("identity7")
    freeze.require("envelope_parse")
    freeze.require("harness_site")
    freeze.require("harness_corpus")

    total = len(records)
    enveloped = [r for r in records if r["code"] != SENTINEL or r["event"] != SENTINEL]

    # `class`, `method` and `location` are constant across the corpus (freeze item
    # `harness_site`), so they contribute nothing to either identity and are held fixed
    # rather than invented.
    five = {(r["spec"], r["error"]) for r in records}
    seven = {(r["spec"], r["error"], r["code"], r["event"]) for r in records}
    five_env = {(r["spec"], r["error"]) for r in enveloped}
    seven_env = {(r["spec"], r["error"], r["code"], r["event"]) for r in enveloped}

    # A collision is a five-part identity that the seven-part identity splits: the reports
    # that a run emitting both of them would have written as one line and now writes as two.
    # It is computed on the enveloped records alone, because a split between an envelope
    # record and a legacy one is the era boundary showing through, not a cause the identity
    # separated - the whole-corpus figure above keeps that mixture visible, this one removes
    # it, and E6 is decided on the conservative number.
    split: dict[tuple[str, str], set[tuple[str, str]]] = collections.defaultdict(set)
    for record in enveloped:
        split[(record["spec"], record["error"])].add((record["code"], record["event"]))
    separated = {key: value for key, value in split.items() if len(value) > 1}
    # Where the separated causes share one `code`, `event` is doing the separating on its
    # own - the claim of design D-5 that `code` alone would refine nothing.
    by_event_alone = {
        key: value
        for key, value in separated.items()
        if len({code for code, _ in value}) == 1
    }

    env: dict[str, Envelope] = {}
    env["records"] = Envelope(
        "violation records read from the harness reports",
        total,
        total,
        "records",
        ("harness_corpus",),
        HARNESS_IN,
        excluded=f"the `{SELFTEST_PREFIX}*` reports of the harness self-test",
    )
    env["records_carrying_an_envelope"] = Envelope(
        "records whose message carries a `v=1` envelope",
        len(enveloped),
        total,
        "records",
        ("envelope_parse",),
        HARNESS_IN,
        note="the remainder are pre-E1 messages replayed as the A side of the E1 rounds; they "
        "parse to the sentinel exactly as a legacy device record would.",
    )
    env["distinct_events"] = Envelope(
        "distinct `ev=` values inside the envelopes",
        len({r["event"] for r in enveloped}),
        len(enveloped),
        "events / records",
        ("envelope_parse",),
        HARNESS_IN,
    )
    env["distinct_codes"] = Envelope(
        "distinct `code=` values inside the envelopes",
        len({r["code"] for r in enveloped}),
        len(enveloped),
        "codes / records",
        ("envelope_parse",),
        HARNESS_IN,
    )
    env["identities_5tuple"] = Envelope(
        "distinct identities under the 5-tuple, with the site held constant",
        len(five),
        total,
        "identities / records",
        ("identity5", "harness_site"),
        HARNESS_IN,
    )
    env["identities_7tuple"] = Envelope(
        "distinct identities under the 7-tuple, with the site held constant",
        len(seven),
        total,
        "identities / records",
        ("identity7", "harness_site", "envelope_parse"),
        HARNESS_IN,
    )
    env["discontinuity"] = Envelope(
        "identities the 7-tuple adds over the 5-tuple",
        len(seven) - len(five),
        len(five),
        "identities / identities",
        ("identity5", "identity7", "harness_site", "envelope_parse"),
        HARNESS_IN,
        note="the whole-corpus figure, which spans both eras: the A sides of the E1 rounds "
        "replay a pre-envelope snapshot, so some of this number is a sentinel standing "
        "beside a named event. E6 is decided on `discontinuity_envelope_only` below, "
        "not on this one.",
    )
    env["discontinuity_envelope_only"] = Envelope(
        "identities the 7-tuple adds over the 5-tuple, counting only enveloped records",
        len(seven_env) - len(five_env),
        len(five_env),
        "identities / identities",
        ("identity5", "identity7", "harness_site", "envelope_parse"),
        HARNESS_IN,
        excluded="records whose message carries no envelope",
        note="the number that decides E6: it must be non-zero, or `code` and `event` add "
        "nothing to the identity and design D-5 is re-opened. It counts only records "
        "carrying an envelope, so the sentinel cannot pass the gate on its own.",
    )
    env["five_part_identities_split"] = Envelope(
        "five-part identities that the seven-part identity splits into more than one",
        len(separated),
        len(five_env),
        "identities / identities",
        ("identity5", "identity7", "harness_site"),
        HARNESS_IN,
        excluded="records whose message carries no envelope",
    )
    env["split_by_event_alone"] = Envelope(
        "of those, the ones whose separated causes share a single `code`",
        len(by_event_alone),
        len(separated),
        "identities / identities",
        ("identity5", "identity7", "harness_site", "envelope_parse"),
        HARNESS_IN,
        excluded="records whose message carries no envelope",
        note="these are the reports `event` separates on its own, with `code` identical - the "
        "measured form of design D-5's claim that `code` alone would refine nothing.",
    )

    return {
        "corpus": "differential harness (`data/gh104/evidence/harness/*.md`)",
        "reader": "`## Envelopes` bullets of the harness reports",
        "rows": total,
        "decides_e6": True,
        "envelopes": {key: value.to_dict() for key, value in env.items()},
        "separated": {
            f"{spec}/{error}": {
                "causes": sorted(f"code={code} ev={event}" for code, event in causes),
                "by_event_alone": (spec, error) in by_event_alone,
            }
            for (spec, error), causes in sorted(separated.items())
        },
        "runs": {
            run: count
            for run, count in sorted(
                collections.Counter(r["run"] for r in records).items()
            )
        },
    }


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------


def build(freeze: FreezeRegistry = DEFAULT_FREEZE) -> dict[str, Any]:
    """
    Assemble both corpora, the frozen definitions and the era split into one result.

    The verdict reads the conservative discontinuity rather than the headline one.
    The headline counts the whole harness corpus, which mixes the pre-E1 A sides
    of the E1 rounds with post-E1 records, so part of it is the era boundary; a
    gate that could be passed by the sentinel standing beside a named event would
    not be measuring the change at all.

    The freeze definitions travel inside the result, not beside it, so that a
    recorded number and the definition that produced it cannot be separated.
    """
    comp162 = load_comp162()
    harness_records, harness_inputs = read_harness_records(HARNESS_DIR)

    inputs = dict(comp162.inputs)
    inputs.update(harness_inputs)

    published = measure_comp162(comp162.rows, freeze)
    deciding = measure_harness(harness_records, freeze)
    delta = deciding["envelopes"]["discontinuity"]["numerator"]
    # The headline `delta` counts the whole corpus, which mixes the pre-E1 A sides of the E1
    # rounds with post-E1 records, so part of it is the era boundary rather than a cause the
    # identity separated. `conservative` removes that mixture, and it is what decides E6: a
    # gate that can be passed by the sentinel alone would not be measuring the change.
    conservative = deciding["envelopes"]["discontinuity_envelope_only"]["numerator"]
    by_event_alone = deciding["envelopes"]["split_by_event_alone"]["numerator"]

    return {
        "change": "gh104-legible-violation-reports",
        "group": "E6 - identity",
        "task": "9.1",
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
        "inputs": inputs,
        "corpora": {"comp162": published, "harness": deciding},
        "era": {
            "before": {
                "name": "five-part identity",
                "identity": list(freeze.require("identity5")),
                "unique_msg_parts": 5,
                "applies_to": (
                    "every deduplicated count published before this change, including the "
                    "E3 trial `experimento-comp162` and the journal-article dataset"
                ),
            },
            "after": {
                "name": "seven-part identity",
                "identity": list(freeze.require("identity7")),
                "unique_msg_parts": 7,
                "applies_to": (
                    "every count computed from a run whose monitors were generated from "
                    "`jca_android` after task 9.2 landed"
                ),
            },
            "rule": (
                "A count of one era MUST NOT be compared to a count of the other without the "
                "discontinuity stated beside the comparison (INV-CORE-41, INV-CORE-57)."
            ),
        },
        "verdict": {
            "deciding_corpus": deciding["corpus"],
            "discontinuity": delta,
            "discontinuity_envelope_only": conservative,
            "split_by_event_alone": by_event_alone,
            "e6_lands": conservative > 0,
            "rule": (
                "E6 lands only if the discontinuity is non-zero on a corpus whose records "
                "carry `ev=`, counting only the records that carry an envelope - so that the "
                "sentinel cannot pass the gate on its own. On comp162 the discontinuity is "
                "zero by construction and is not the gate."
            ),
        },
    }


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

_TABLE_HEAD = (
    "| quantity | measured | definitions | expected | agrees |\n"
    "|---|---|---|---|---|"
)


def _row(env: Mapping[str, Any]) -> str:
    """
    One markdown table row for a measurement envelope.

    `agrees` renders a disagreement in bold and an absent expectation as a dash,
    because those are different states: nothing was expected, versus something was
    expected and the measurement contradicts it.
    """
    pct = "" if env["percent"] is None else f" = {env['percent']:.2f} %"
    den = "-" if env["denominator"] is None else f"{env['denominator']:,}"
    measured = f"{env['numerator']:,} / {den} {env['unit']}{pct}"
    expected = "-" if env["expected"] is None else f"{env['expected']:,}"
    agrees = {None: "-", True: "yes", False: "**no**"}[env["agrees"]]
    return (
        f"| {env['quantity']} | {measured} | "
        f"{', '.join(f'`{d}`' for d in env['definitions'])} | {expected} | {agrees} |"
    )


def _notes(envelopes: Mapping[str, Any]) -> Iterable[str]:
    """
    The note and exclusion lines for a group of envelopes, in order.

    An exclusion is emitted only when there is one -- `nothing` is the default and
    prints no line -- so the exclusions that do appear are read as deliberate.
    """
    for key, env in envelopes.items():
        if env["note"]:
            yield f"- `{key}` — {env['note']}"
        if env["excluded"] != "nothing":
            yield f"- `{key}` — excluded: {env['excluded']}"


def render_markdown(b: Mapping[str, Any]) -> str:
    """
    Render the whole result as the evidence document.

    The verdict comes first and the definitions last, but the numbers in between
    each name the definition ids that produced them, so the document can be read
    top-down for the answer and bottom-up for how it was computed. Every number
    carries numerator, denominator and unit: a bare count in an evidence file is a
    number nobody can re-derive.
    """
    L: list[str] = []
    add = L.append
    verdict = b["verdict"]
    harness = b["corpora"]["harness"]
    comp162 = b["corpora"]["comp162"]

    add("# gh104 E6 — the identity discontinuity")
    add("")
    add(
        "Generated by `scripts/gh104_identity_discontinuity.py` (task 9.1). Every number carries "
        "its numerator, its denominator, the unit it counted and the ids of the definitions that "
        "produced it; the definitions themselves are at the foot of this file."
    )
    add("")
    add(
        "The question is narrow and it decides whether task 9.2 lands: does adding `code` and "
        "`event` to `ErrorSummary`'s identity separate reports that the five-field identity "
        "collapses? If it does not, the change is a no-op and design D-5 is re-opened."
    )
    add("")

    add("## Verdict")
    add("")
    add(f"- **Deciding corpus**: {verdict['deciding_corpus']}")
    add(
        f"- **Discontinuity, whole corpus**: {verdict['discontinuity']:,} identities the "
        "7-tuple adds — but this corpus holds both eras, so part of that number is the "
        "sentinel standing beside a named event rather than a cause being separated"
    )
    add(
        f"- **Discontinuity, enveloped records only**: **{verdict['discontinuity_envelope_only']:,}** "
        "— the conservative figure, and the one E6 is decided on"
    )
    add(
        f"- **Separated by `event` alone**: {verdict['split_by_event_alone']:,} of those, with "
        "`code` identical on both sides"
    )
    add(
        f"- **E6 lands**: {'yes' if verdict['e6_lands'] else '**no** — re-open design D-5'}"
    )
    add("")
    add(verdict["rule"])
    add("")

    add("## Why the deciding number does not come from comp162")
    add("")
    add(
        "comp162 is the corpus the published numbers came from, and it is the corpus this file "
        "must state the baseline on. It is **not** the corpus that decides E6, because its "
        "records predate the envelope: "
        f"{comp162['envelopes']['records_carrying_an_envelope']['numerator']:,} of its "
        f"{comp162['rows']:,} rows carry a `v=1` envelope, so every `code` and every `event` "
        "parses to the sentinel `UNSPECIFIED` and the two identities cannot possibly differ. "
        "Its zero is a property of the input, recorded and labelled, never read as a result "
        "about the identity (INV-CORE-57)."
    )
    add("")

    add("## comp162 — the published corpus, zero by construction")
    add("")
    add(f"Reader: {comp162['reader']}. Rows: {comp162['rows']:,}.")
    add("")
    add(_TABLE_HEAD)
    for env in comp162["envelopes"].values():
        add(_row(env))
    add("")
    for note in _notes(comp162["envelopes"]):
        add(note)
    add("")

    add("## The differential harness — the corpus that decides")
    add("")
    add(
        "These are the replay records of the E4, E1 and S rounds, the only inputs in the tree "
        "whose accusations carry `ev=`. `TraceRunner` resolves every trace line through one "
        "reflective frame and its record carries no stack frame at all, so `class`, `method` and "
        "`location` are constant across the corpus and are held fixed. That is what makes it the "
        "right instrument rather than a limitation of it: with the site constant, the difference "
        "between the two identities is exactly what `code` and `event` add **at one site** — the "
        "case INV-INS-126 names."
    )
    add("")
    add(
        "Records per round: "
        + ", ".join(f"`{run}` {count:,}" for run, count in harness["runs"].items())
        + "."
    )
    add("")
    add(_TABLE_HEAD)
    for env in harness["envelopes"].values():
        add(_row(env))
    add("")
    for note in _notes(harness["envelopes"]):
        add(note)
    add("")

    add("### The five-part identities the seven-part identity splits")
    add("")
    add(
        "Each row is one `(spec, error)` pair that the five-field identity reports as a single "
        "record at a given site, and the causes the seven-field identity separates it into."
    )
    add("")
    add(
        "Only records carrying an envelope are counted, so a row here is never the era "
        "boundary showing through. The last column marks the rows where the separated causes "
        "share one `code` and `event` is therefore doing the separating on its own."
    )
    add("")
    add("| spec / error | causes separated | by `event` alone |")
    add("|---|---|---|")
    for key, entry in harness["separated"].items():
        causes = "; ".join(f"`{cause}`" for cause in entry["causes"])
        add(f"| `{key}` | {causes} | {'yes' if entry['by_event_alone'] else 'no'} |")
    add("")

    add("### Why 17 distinct events and not 19")
    add("")
    add(
        "A `grep` for `ev=` over `data/gh104/evidence/harness/*.md` returns 19 distinct values. "
        "This file measures 17, and the difference is the instrument, not the data: the `grep` "
        "reaches the 24 `selftest*` reports, which replay a synthetic mutant and are excluded "
        "here, and it also matches the harness's own record header — `spec=…,ev=…,type=…` — "
        "which is what `TraceRunner` knows it dispatched, not what the message carries. The "
        "identity is built from the message envelope alone, because that is the only field "
        "`ErrorDescription` will have on the device."
    )
    add("")

    add("## The 8.15 reversion becomes measurable — a candidate, not a decision")
    add("")
    add(
        "Task 8.15 added `__RESET;` to `KeyPairGeneratorSpec`'s `@fail` handler. It is correct "
        "by construction — the other 20 handlers of the set reset, and `Category_fail` is "
        "sticky — but the harness classified `unchanged` on all 62 traces and the task's rule "
        "reverted it. The cause was measured and recorded in `evidence/e4_automata.md`: the "
        "replay has one call site, so every report carries the same `location`, and the "
        "five-field identity collapsed the repetition inside `ErrorCollector`'s `HashSet` "
        "before it could reach a row. The edit was reverted and the chain written into "
        "`data/jca_android/conformance_record.csv`."
    )
    add("")
    add(
        "The seven-field identity changes that premise. A handler re-running at one site under "
        "a **different event** no longer collapses, so a repeat that 8.15 removes can now "
        "become visible to the same instrument. This file records that as a **candidate for "
        "re-measurement**, against the corpus named here — the differential-harness traces of "
        "`data/gh104/traces`, replayed after task 9.2 has landed — and nothing more. 8.15 "
        "stays closed with the record it has; re-opening it is a decision for the researcher, "
        "and it needs its own before/after evidence, not this measurement."
    )
    add("")
    add(
        "One limit is worth stating with it, because it bounds what a re-measurement could "
        "show: the seven-field identity separates two *different* events at one site, but two "
        "runs of the *same* event at the same site still collapse. That repeat is exactly what "
        "8.15 removes in production, and staging it still needs either a replay that gives "
        "each trace line its own call site or a device run — which is task 10.4's, not this "
        "group's."
    )
    add("")

    add("## Era")
    add("")
    era = b["era"]
    add(
        f"**{era['before']['name']}** — identity "
        f"`({', '.join(era['before']['identity'])})`, `unique_msg` of "
        f"{era['before']['unique_msg_parts']} parts. Applies to {era['before']['applies_to']}."
    )
    add("")
    add(
        f"**{era['after']['name']}** — identity "
        f"`({', '.join(era['after']['identity'])})`, `unique_msg` of "
        f"{era['after']['unique_msg_parts']} parts. Applies to {era['after']['applies_to']}."
    )
    add("")
    add(era["rule"])
    add("")

    add("## Inputs")
    add("")
    add("| key | path | sha256 | size |")
    add("|---|---|---|---|")
    for key, meta in sorted(b["inputs"].items()):
        size = meta.get("rows", meta.get("records", meta.get("files", "-")))
        size = f"{size:,}" if isinstance(size, int) else size
        add(f"| `{key}` | `{meta['path']}` | `{meta['sha256'][:16]}…` | {size} |")
    add("")

    add("## Definitions")
    add("")
    for key, item in b["definitions"].items():
        add(f"### `{key}`")
        add("")
        add(item["definition"])
        add("")
        value = item["value"]
        rendered = (
            ", ".join(f"`{v}`" for v in value)
            if isinstance(value, list)
            else (json.dumps(value) if isinstance(value, dict) else f"`{value}`")
        )
        add(f"**Value**: {rendered}")
        add("")
        add(f"**Why**: {item['why']}")
        add("")

    return "\n".join(L) + "\n"


def write(
    out_dir: Path = OUT_DIR, freeze: FreezeRegistry = DEFAULT_FREEZE
) -> dict[str, Any]:
    """
    Build the result and write both the JSON and the markdown into `out_dir`.

    Both are written from one build, so the machine-readable and the human-readable
    artefact can never disagree about what was measured.
    """
    result = build(freeze)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "identity_discontinuity.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "identity_discontinuity.md").write_text(
        render_markdown(result), encoding="utf-8"
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """
    Parse arguments, write the evidence, and print both corpora's headline figures.

    The summary prints comp162's discontinuity with "zero by construction" spelled
    out, and the harness's twice -- whole corpus and enveloped records only -- so
    that the conservative number is the one a reader takes away.
    """
    parser = argparse.ArgumentParser(
        description="gh104 E6 identity discontinuity (task 9.1)"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_DIR,
        help="output directory (default: data/gh104)",
    )
    args = parser.parse_args(argv)

    result = write(args.out)
    verdict = result["verdict"]
    comp = result["corpora"]["comp162"]["envelopes"]
    harness = result["corpora"]["harness"]["envelopes"]
    print(
        f"wrote {args.out / 'identity_discontinuity.json'}, identity_discontinuity.md"
    )
    print(
        "comp162: 8-tuple "
        f"{comp['identities_8tuple']['numerator']:,}, "
        f"5-tuple {comp['identities_5tuple']['numerator']:,}, "
        f"7-tuple {comp['identities_7tuple']['numerator']:,} "
        f"(discontinuity {comp['discontinuity']['numerator']:,}, zero by construction)"
    )
    print(
        "harness: "
        f"5-tuple {harness['identities_5tuple']['numerator']:,}, "
        f"7-tuple {harness['identities_7tuple']['numerator']:,} "
        f"(discontinuity {harness['discontinuity']['numerator']:,}; "
        f"enveloped records only {harness['discontinuity_envelope_only']['numerator']:,}, "
        f"of which {harness['split_by_event_alone']['numerator']:,} by `event` alone)"
    )
    if not verdict["e6_lands"]:
        print(
            "DISCONTINUITY IS ZERO on the deciding corpus: E6 does not land; re-open design D-5"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

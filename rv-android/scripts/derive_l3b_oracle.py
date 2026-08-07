#!/usr/bin/env python3
"""Derive the L3-b paired-execution oracle from recorded ajc executions.

Layer 3 compares the event sets two weavers produce for the same APK against a
ground truth. Its blocker was never the comparator — it was that a ground truth
derived from a run of the pipeline under test is circular, so the oracle slots
stayed empty and the layer was declared N/A.

An execution of a *different* weaver is not circular in the same way. The
`ajc` variant (dex2jar + AspectJ + d8) is an independent implementation of the
same 23 JCA specifications, and it was run on the same corpus, in the same
emulator, paired with dexlib2. This script reads what it observed and writes it
out as a ground-truth oracle for dexlib2 (INV-INS-107).

What the oracle can and cannot settle
-------------------------------------
It discriminates the **wrapper-collision** defect: a call site bound to the
wrong specification shows up as an entire (spec, errorType) category dexlib2
reports and the independent weaver never does.

It cannot speak to the **inline-truncation** defect. `UnsatisfiedConstraint`
is absent from *both* variants in this recording — the erased events live in
application code that GUI exploration does not reach. L3-c, derived from the
JVM `-javaagent` control group, is the only regime where that category exists.

Presence, not counts
--------------------
Both sides are reduced to distinct `(spec, errorType, class, method)` tuples
before being written out. Occurrence counts are not comparable across the two
variants: each side was driven by its own GUI exploration, so a category firing
1,675 times against 40 says more about which screens were reached than about
either weaver. `TraceComparator.countFalsePositives` counts per occurrence, so
feeding it raw multiplicities would let exploration depth decide the verdict.
The reduction is declared in the oracle's provenance block so it is auditable
rather than implicit.

Usage
-----
    python3 scripts/derive_l3b_oracle.py [--events CSV] [--out-dir DIR]
                                         [--traces-dir DIR]
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEXLIB2 = REPO_ROOT.parent / "rvsec/rvsec-android/rvsec-instrumentation-dexlib2"

DEFAULT_EVENTS = REPO_ROOT / "out/run_jca_compare_consolidated/events_fair.csv"
DEFAULT_ORACLE_DIR = DEXLIB2 / "validator/oracles"
DEFAULT_TRACES_DIR = DEXLIB2 / "validator/traces"

ORACLE_NAME = "l3b-paired"
GROUND_TRUTH_VARIANT = "ajc"
UNDER_TEST_VARIANT = "dexlib2"


def error_type(unique_msg: str) -> str:
    """`class:::method:::spec:::ErrorType:::message` — field 4."""
    parts = unique_msg.split(":::")
    return parts[3] if len(parts) >= 4 else "Unknown"


def message(unique_msg: str) -> str:
    parts = unique_msg.split(":::")
    return parts[4] if len(parts) >= 5 else ""


def load(events_csv: Path):
    """Distinct (spec, errorType, class, method) tuples per variant, paired APKs only."""
    rows = list(csv.DictReader(events_csv.open()))
    by_variant_apks = collections.defaultdict(set)
    for r in rows:
        by_variant_apks[r["variant"]].add(r["apk"])
    shared = by_variant_apks[GROUND_TRUTH_VARIANT] & by_variant_apks[UNDER_TEST_VARIANT]

    # Keyed by (spec, errorType) — the granularity TraceComparator actually
    # matches on. Its matched() is existential and ignores the oracle's
    # location field, so an oracle carrying one entry per (spec, errorType,
    # class, method) would list several entries that any single event
    # satisfies, inflating the recall denominator with distinctions the
    # comparator cannot see. Class names make that worse rather than better
    # here: R8 renames them per build, so the same site reads `jh.h.c` under
    # one variant and `okio.ByteString.digest$okio(...)` under the other.
    # Sites are kept alongside for the reader, not for matching.
    categories = collections.defaultdict(dict)
    for r in rows:
        if r["apk"] not in shared:
            continue
        key = (r["spec"], error_type(r["unique_msg"]))
        entry = categories[r["variant"]].setdefault(
            key, {"message": message(r["unique_msg"]), "sites": set(), "count": 0})
        entry["sites"].add(f"{r['class']}.{r['method']}")
        entry["count"] += 1
    return shared, categories


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_oracle(path: Path, events, shared, events_csv: Path, digest: str) -> None:
    lines = [
        f"name: {ORACLE_NAME}",
        "profile: paired_execution",
        "provenance:",
        "  class: derived_from_independent_weaver",
        f"  source_weaver: {GROUND_TRUTH_VARIANT}",
        f"  source_data: {events_csv.relative_to(REPO_ROOT)}",
        f"  source_sha256: {digest}",
        "  derivation_script: derive_l3b_oracle.py",
        "  source: |",
        "    Recorded events of the ajc variant (dex2jar + AspectJ + d8), an",
        "    independent implementation of the same 23 JCA specifications, run on",
        f"    the {len(shared)} APKs executed under both variants in the same emulator",
        "    campaign. Reduced to distinct (spec, errorType) categories: occurrence",
        "    counts reflect how deep each side's GUI exploration went rather than",
        "    what either weaver emits, and the comparator counts false positives",
        "    per occurrence.",
        "description: |",
        "  Paired-execution profile. Discriminates the wrapper-registry collision:",
        "  a call site bound to the wrong specification surfaces as a (spec,",
        "  errorType) category the implementation under test reports and the",
        "  independent weaver never does.",
        "",
        "  It says nothing about the inline-truncation defect. UnsatisfiedConstraint",
        "  is absent from both variants in this recording, because the erased events",
        "  live in application code GUI exploration does not reach. That is L3-c's",
        "  question, not this oracle's.",
        "",
        "  One entry per (spec, errorType): that is what TraceComparator.matched()",
        "  keys on — it is existential and ignores the location field. The observed",
        "  sites are listed under each entry for the reader; they are documentary,",
        "  not matched, and under R8 the same site is named differently by the two",
        "  variants anyway.",
        "expected_events:",
    ]
    for i, ((spec, etype), info) in enumerate(sorted(events.items()), start=1):
        sites = sorted(info["sites"])
        representative = sites[0].rsplit(".", 1)
        lines += [
            f"  - id: {i}",
            f"    spec: {spec}",
            f"    error_type: {etype}",
            f"    location: {{ class: {representative[0]}, method: "
            f"{representative[1] if len(representative) > 1 else '?'} }}",
            "    expected_message_substring: null",
            f"    observed_sites: {len(sites)}   # documentary; not matched",
        ]
    lines += [
        "acceptance:",
        f"  required_event_count: {len(events)}",
        "  full_coverage_required: true",
        "notes: |",
        "  Both sides of this oracle are frozen pre-repair recordings, so executing",
        "  it characterises the defect rather than certifying its repair. A verdict",
        "  that flips would need a fresh dexlib2 run over the same APKs, which means",
        "  an emulator session (L3-a) and is out of scope of the change that derived",
        "  this oracle. Any report citing it must say so.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_trace(path: Path, events) -> None:
    """Reconstruct a logcat the comparator can read: `[Spec] ErrorType: msg`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = []
    for (spec, etype), info in sorted(events.items()):
        detail = (info["message"] or "").replace("\n", " ") or f"{len(info['sites'])} site(s)"
        out.append(f"RVSEC: [{spec}] {etype}: {detail}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--events", type=Path, default=DEFAULT_EVENTS)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_ORACLE_DIR)
    ap.add_argument("--traces-dir", type=Path, default=DEFAULT_TRACES_DIR)
    args = ap.parse_args()

    if not args.events.is_file():
        raise SystemExit(f"paired events CSV not found at {args.events}")

    shared, tuples = load(args.events)
    ground_truth = tuples[GROUND_TRUTH_VARIANT]
    under_test = tuples[UNDER_TEST_VARIANT]
    digest = sha256(args.events)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    oracle_path = args.out_dir / f"{ORACLE_NAME}-oracle.yaml"
    write_oracle(oracle_path, ground_truth, shared, args.events, digest)

    trace_dir = args.traces_dir / ORACLE_NAME
    write_trace(trace_dir / "ajc.logcat", ground_truth)
    write_trace(trace_dir / "dexlib2.logcat", under_test)

    only_under_test = set(under_test) - set(ground_truth)
    only_ground_truth = set(ground_truth) - set(under_test)

    print(f"paired APKs                        {len(shared)}")
    print(f"source sha256                      {digest}")
    print(f"expected categories (ajc)          {len(ground_truth)}")
    print(f"categories reported by dexlib2     {len(under_test)}")
    print(f"  absent from dexlib2              {len(only_ground_truth)}")
    print(f"  reported only by dexlib2         {len(only_under_test)}")
    for spec, etype in sorted(only_under_test):
        info = under_test[(spec, etype)]
        print(f"    + {spec}/{etype}  "
              f"{info['count']} events over {len(info['sites'])} site(s)")
    for spec, etype in sorted(only_ground_truth):
        info = ground_truth[(spec, etype)]
        print(f"    - {spec}/{etype}  "
              f"{info['count']} events over {len(info['sites'])} site(s)")
    print(f"\noracle  {oracle_path}")
    print(f"traces  {trace_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

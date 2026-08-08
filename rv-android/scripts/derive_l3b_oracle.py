#!/usr/bin/env python3
"""Derive the L3-b paired-execution oracles from recorded ajc executions.

Layer 3 compares the event sets two weavers produce for the same APK against a
ground truth. Its blocker was never the comparator — it was that a ground truth
derived from a run of the pipeline under test is circular, so the oracle slots
stayed empty and the layer was declared N/A.

An execution of a *different* weaver is not circular in the same way. The
`ajc` variant (dex2jar + AspectJ + d8) is an independent implementation of the
same 23 JCA specifications, and it was run on the same corpus, in the same
emulator, paired with dexlib2. This script reads what it observed and writes it
out as ground truth for dexlib2 (INV-INS-107).

What the oracles can and cannot settle
--------------------------------------
They discriminate the **wrapper-collision** defect: a call site bound to the
wrong specification shows up as a misuse dexlib2 reports and the independent
weaver never does.

They cannot speak to the **inline-truncation** defect. `UnsatisfiedConstraint`
is absent from *both* variants in this recording — the erased events live in
application code that GUI exploration does not reach. L3-c, derived from the
JVM `-javaagent` control group, is the only regime where that category exists.

The unit of analysis, and the repair it forced
----------------------------------------------
Counting is at the article's unique-misuse key, `(apk, class, method, spec)`
(`results-rq1.tex:41`) — that is what the reported totals mean, and it is what
the comparison between the two variants is stated in.

The oracle's `expected_events` are one step finer, `(spec, class, method,
errorType)`, for a mechanical reason rather than a different definition: an
oracle event without an `error_type` is dropped by the comparator's parser, and
the comparator scores TP/FP/FN per event. Every such event was observed — the
finer split adds no claim, it only declines to merge two recorded error types at
one site into a single unscoreable entry. A site that produced both
`InvalidSequenceOfMethodCalls` and `UnsafeAlgorithm` is one misuse in the counts
and two expected events in the file.

Getting to that key required repairing 2,476 rows in which the
upstream summarizer's fallback had copied a whole stack frame into both the
class and the method column, putting the line number into the key and counting
one misuse once per line. The repair uses the producer's own rule
(`ErrorDescription.FRAME_SUFFIX`), not the article's `repair_frame_keys.py`,
which requires the stripped group to look like `File.ext:NN` and therefore
repairs none of these — the campaign's frames are `(Unknown Source:1)` and
`(r8-map-id-…:17)`.

Output shape
------------
One oracle per APK, `<apkBaseName>-oracle.yaml`, with its trace pair under
`validator/traces/<apkBaseName>/`. `TraceComparator.resolveOracleForApk` maps an
APK filename to exactly that name; a pooled file resolves for no APK at all in
batch mode, and lets one app dominate a profile's verdict besides.

Usage
-----
    python3 scripts/derive_l3b_oracle.py [--events CSV] [--out-dir DIR]
                                         [--traces-dir DIR]
"""

from __future__ import annotations

import argparse
import collections
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rv_oracle_common import (  # noqa: E402
    apk_base_name, error_type, message, oracle_events_block, repair_frame_form,
    sha256, write_trace,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEXLIB2 = REPO_ROOT.parent / "rvsec/rvsec-android/rvsec-instrumentation-dexlib2"

DEFAULT_EVENTS = REPO_ROOT / "out/run_jca_compare_consolidated/events_fair.csv"
DEFAULT_ORACLE_DIR = DEXLIB2 / "validator/oracles"
DEFAULT_TRACES_DIR = DEXLIB2 / "validator/traces"

PROFILE = "paired_execution"
GROUND_TRUTH_VARIANT = "ajc"
UNDER_TEST_VARIANT = "dexlib2"

# What the repair is expected to find in the pinned source. Asserted rather than
# reported: a different number means the source moved under the derivation, and
# an oracle silently derived from different data is worse than no oracle.
EXPECTED_FRAME_REPAIRS = 2476


def load(events_csv: Path):
    """Unique misuses per (variant, apk), over the APKs run under both variants."""
    rows = list(csv.DictReader(events_csv.open()))

    repaired = 0
    for r in rows:
        r.setdefault("location", "")
        if repair_frame_form(r):
            repaired += 1
    if repaired != EXPECTED_FRAME_REPAIRS:
        raise SystemExit(
            f"frame-form repair touched {repaired} rows, expected "
            f"{EXPECTED_FRAME_REPAIRS}. The source recording is not the one this "
            f"derivation was written against; re-check {events_csv} before "
            f"deriving an oracle from it.")
    # Zero residue is part of the claim, not a hope: a row still carrying a
    # frame after the pass would enter the key with its line number attached.
    residue = [r for r in rows if repair_frame_form(dict(r))]
    if residue:
        raise SystemExit(f"{len(residue)} rows still frame-form after the repair")

    by_variant_apks = collections.defaultdict(set)
    for r in rows:
        by_variant_apks[r["variant"]].add(r["apk"])
    shared = by_variant_apks[GROUND_TRUTH_VARIANT] & by_variant_apks[UNDER_TEST_VARIANT]

    # (variant, apk) -> {(spec, class, method, errorType): misuse}
    misuses = collections.defaultdict(dict)
    for r in rows:
        if r["apk"] not in shared:
            continue
        etype = error_type(r["unique_msg"])
        key = (r["spec"], r["class"], r["method"], etype)
        entry = misuses[(r["variant"], r["apk"])].setdefault(key, {
            "spec": r["spec"], "class": r["class"], "method": r["method"],
            "error_type": etype, "message": message(r["unique_msg"]),
            "location": r.get("location") or "", "count": 0,
        })
        entry["count"] += 1
    return shared, misuses, repaired


def write_oracle(path: Path, apk: str, events, events_csv: Path, digest: str,
                 repaired: int, misuse_count: int) -> None:
    lines = [
        f"name: {apk_base_name(apk)}",
        f"profile: {PROFILE}",
        f"apk: {apk}",
        "provenance:",
        "  class: derived_from_independent_weaver",
        f"  source_weaver: {GROUND_TRUTH_VARIANT}",
        f"  source_data: {events_csv.relative_to(REPO_ROOT)}",
        f"  source_sha256: {digest}",
        "  derivation_script: derive_l3b_oracle.py",
        "  source: |",
        "    Recorded events of the ajc variant (dex2jar + AspectJ + d8), an",
        "    independent implementation of the same 23 JCA specifications, run in",
        "    the same emulator campaign as the dexlib2 variant it is ground truth",
        "    for. Reduced to unique misuses (apk, class, method, spec): occurrence",
        "    counts reflect how deep each side's GUI exploration went rather than",
        "    what either weaver emits, and the comparator counts false positives",
        "    per occurrence.",
        "  repair: |",
        f"    {repaired} rows of the source carried a whole stack frame in both the",
        "    class and the method column — the fallback in",
        "    ErrorDescription.createErrorSummary, which fires when its split fails.",
        "    They were repaired with the producer's own rule (FRAME_SUFFIX: a",
        "    trailing (…:<digits>) group with no nested parenthesis, then a split at",
        "    the last dot), leaving zero residue. The article's repair_frame_keys.py",
        "    is NOT used: it requires the stripped group to look like File.ext:NN and",
        "    repairs 0 of these rows, whose frames are (Unknown Source:1) and",
        "    (r8-map-id-…:17).",
        "description: |",
        "  Paired-execution profile for a single APK. Discriminates the",
        "  wrapper-registry collision: a call site bound to the wrong specification",
        "  surfaces as a misuse the implementation under test reports and the",
        "  independent weaver never does.",
        "",
        "  It says nothing about the inline-truncation defect. UnsatisfiedConstraint",
        "  is absent from both variants in this recording, because the erased events",
        "  live in application code GUI exploration does not reach. That is L3-c's",
        "  question, not this oracle's.",
        "",
        f"  {misuse_count} unique misuse(s) at the article's key (apk, class, method,",
        f"  spec), listed below as {len(events)} expected event(s): a site that produced",
        "  two error types is one misuse and two events, because the comparator scores",
        "  per event and drops an event that declares no error_type.",
    ]
    lines += oracle_events_block(events)
    lines += [
        "acceptance:",
        f"  unique_misuse_count: {misuse_count}",
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--events", type=Path, default=DEFAULT_EVENTS)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_ORACLE_DIR)
    ap.add_argument("--traces-dir", type=Path, default=DEFAULT_TRACES_DIR)
    args = ap.parse_args()

    if not args.events.is_file():
        raise SystemExit(f"paired events CSV not found at {args.events}")

    shared, misuses, repaired = load(args.events)
    digest = sha256(args.events)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    all_ground_truth: set = set()
    all_under_test: set = set()
    print(f"paired APKs                        {len(shared)}")
    print(f"source sha256                      {digest}")
    print(f"frame-form rows repaired           {repaired} (zero residue)")
    print()

    def unique_misuses(entries, apk):
        """Collapse the per-errorType entries onto the article's key."""
        return {(apk, e["spec"], e["class"], e["method"]) for e in entries}

    for apk in sorted(shared):
        base = apk_base_name(apk)
        ground_truth = list(misuses[(GROUND_TRUTH_VARIANT, apk)].values())
        under_test = list(misuses[(UNDER_TEST_VARIANT, apk)].values())
        gt_misuses = unique_misuses(ground_truth, apk)
        ut_misuses = unique_misuses(under_test, apk)
        all_ground_truth |= gt_misuses
        all_under_test |= ut_misuses

        write_oracle(args.out_dir / f"{base}-oracle.yaml", apk, ground_truth,
                     args.events, digest, repaired, len(gt_misuses))
        trace_dir = args.traces_dir / base
        write_trace(trace_dir / "ajc.logcat", ground_truth)
        write_trace(trace_dir / "dexlib2.logcat", under_test)
        print(f"  {base:44} ajc={len(gt_misuses):3} misuses / "
              f"{len(ground_truth):3} events   "
              f"dexlib2={len(ut_misuses):3} / {len(under_test):3}")

    both = all_ground_truth & all_under_test
    print()
    print("unique misuses, at the article's key (apk, class, method, spec):")
    print(f"  ajc                              {len(all_ground_truth)}")
    print(f"  dexlib2                          {len(all_under_test)}")
    print(f"  reported by both                 {len(both)}")
    print(f"  only ajc                         {len(all_ground_truth - all_under_test)}")
    print(f"  only dexlib2                     {len(all_under_test - all_ground_truth)}")
    for apk, spec, clazz, method in sorted(all_under_test - all_ground_truth):
        print(f"    + {spec}  {clazz}.{method}  [{apk}]")
    for apk, spec, clazz, method in sorted(all_ground_truth - all_under_test):
        print(f"    - {spec}  {clazz}.{method}  [{apk}]")
    print(f"\noracles  {args.out_dir}")
    print(f"traces   {args.traces_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

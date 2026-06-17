#!/usr/bin/env python3
"""Full per-APK invariance gate for the gh66 WTG sweep vs the baseline.

gh66 changes only `FlowgraphRebuilder.buildFlowThroughContainer`, which feeds the
WTG stages → the `transitions[]` section. It does NOT touch the code paths that
produce `reachability` (SPARK call-graph reachability), `windows`/`components`
(GUI analysis), `package`, or `mainActivity`. So between the baseline sweep
(`out/sweep_20260604_wtg_spark`) and a gh66 candidate sweep, for every APK:

  - `package`, `mainActivity`, `components`, `reachability`, `windows`
    MUST be IDENTICAL.  Any difference is a FAIL — it means gh66 had an
    unexpected side effect (or GATOR is non-deterministic), which must be
    investigated, not accepted.
  - `transitions` is the ONLY field allowed to differ, and only in the
    sanctioned direction:
        * on APKs the baseline produced transitions for (the 72), the edge set
          MUST be IDENTICAL (diff-zero, INV-ANA-39);
        * on APKs the baseline had no transitions for (the 97 timeouts), the
          candidate MAY ADD transitions (recovery) but MUST NOT remove any
          (baseline is empty, so removals are impossible) — added edges are the
          measured benefit, not a failure.
  - `complete` is reported but not hard-failed (a recovered APK legitimately
    flips toward complete).

This complements `wtg_edge_diff.py` (transitions-only gate, reused here for the
edge set): this script is the WHOLE-JSON regression gate the corpus run needs.

Comparison is ID-INDEPENDENT and ORDER-INDEPENDENT: GATOR's numeric window/widget
node IDs are not stable across builds, so window `id` fields are stripped before
comparison and every list is canonicalized to an order-independent form. The
transitions edge key (resolved to stable window/widget NAMES) comes from
`wtg_edge_diff._load_edges`.

Baseline scope: canonical `<dir>/<app>/<app>.apk.json`, EXCLUDING `_backup/`.

Exit codes:
  0 — PASS (every common APK: invariant fields identical AND transitions sanctioned)
  1 — FAIL (≥1 APK with a non-transitions diff, or a transitions diff on a baseline-tr>0 APK)
  2 — usage / IO error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wtg_edge_diff import _load_edges  # noqa: E402  (stable-key transitions edge set)

# Fields that gh66 MUST leave untouched (compared ID-independently below).
INVARIANT_FIELDS = ("package", "mainActivity", "components", "reachability", "windows")


def _canon(obj):
    """Order-independent canonical form: dicts -> sorted-key tuples, lists ->
    sorted tuple of canonical elements. Makes structural equality insensitive to
    JSON array ordering (GATOR does not guarantee a stable order)."""
    if isinstance(obj, dict):
        return tuple(sorted((k, _canon(v)) for k, v in obj.items()))
    if isinstance(obj, list):
        return tuple(sorted((_canon(x) for x in obj), key=repr))
    return obj


def _strip_ids(obj):
    """Recursively drop GATOR-assigned numeric node `id` fields (window + widget),
    which are not stable across builds, so windows compare on stable content
    (name/type/idName/text/...) rather than on volatile IDs."""
    if isinstance(obj, dict):
        return {k: _strip_ids(v) for k, v in obj.items() if k != "id"}
    if isinstance(obj, list):
        return [_strip_ids(x) for x in obj]
    return obj


def _field_canon(data: dict, field_name: str):
    val = data.get(field_name)
    if field_name == "windows":
        val = _strip_ids(val)
    return _canon(val)


@dataclass
class PerApk:
    apk: str
    baseline_tr: int
    candidate_tr: int
    diff_fields: list = field(default_factory=list)   # invariant fields that differ (FAIL)
    tr_added: int = 0
    tr_removed: int = 0
    baseline_had_tr: bool = False
    complete_changed: bool = False

    @property
    def transitions_violation(self) -> bool:
        # On a baseline-tr>0 APK, any add/remove is a violation (diff-zero).
        # On a baseline-tr==0 APK, removals are impossible; additions are recovery.
        if self.baseline_had_tr:
            return self.tr_added > 0 or self.tr_removed > 0
        return self.tr_removed > 0

    @property
    def failed(self) -> bool:
        return bool(self.diff_fields) or self.transitions_violation


def _walk(directory: Path) -> dict:
    out = {}
    for p in directory.glob("**/*.apk.json"):
        if "_backup" in p.parts:
            continue
        out[p.stem] = p
    return out


def compare(baseline_dir: Path, candidate_dir: Path) -> list:
    base, cand = _walk(baseline_dir), _walk(candidate_dir)
    common = sorted(set(base) & set(cand))
    only_base = sorted(set(base) - set(cand))
    only_cand = sorted(set(cand) - set(base))
    if only_base:
        print(f"[invariance] WARN baseline-only APKs (not compared): {len(only_base)}", file=sys.stderr)
    if only_cand:
        print(f"[invariance] WARN candidate-only APKs (not compared): {len(only_cand)}", file=sys.stderr)

    results = []
    for apk in common:
        b = json.loads(base[apk].read_text())
        c = json.loads(cand[apk].read_text())

        diff_fields = [f for f in INVARIANT_FIELDS if _field_canon(b, f) != _field_canon(c, f)]

        b_edges, _ = _load_edges(base[apk])
        c_edges, _ = _load_edges(cand[apk])
        b_tr = len(b.get("transitions") or [])
        results.append(PerApk(
            apk=apk,
            baseline_tr=b_tr,
            candidate_tr=len(c.get("transitions") or []),
            diff_fields=diff_fields,
            tr_added=len(c_edges - b_edges),
            tr_removed=len(b_edges - c_edges),
            baseline_had_tr=b_tr > 0,
            complete_changed=(b.get("complete") != c.get("complete")),
        ))
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Full per-APK invariance gate for the gh66 WTG sweep (vs baseline)")
    ap.add_argument("baseline", type=Path, help="Baseline sweep dir (pre-change)")
    ap.add_argument("candidate", type=Path, help="gh66 candidate sweep dir")
    ap.add_argument("--report", type=Path, default=None, help="Optional JSON report path")
    args = ap.parse_args()

    if not args.baseline.is_dir() or not args.candidate.is_dir():
        print("[invariance] baseline or candidate dir missing", file=sys.stderr)
        return 2
    try:
        results = compare(args.baseline, args.candidate)
    except (OSError, RuntimeError) as exc:
        print(f"[invariance] {exc}", file=sys.stderr)
        return 2
    if not results:
        print("[invariance] no APKs in common", file=sys.stderr)
        return 2

    field_fails = [r for r in results if r.diff_fields]
    tr_viol = [r for r in results if r.transitions_violation]
    recovered = [r for r in results if not r.baseline_had_tr and r.tr_added > 0]
    diffzero_72 = [r for r in results if r.baseline_had_tr]

    # Per-APK detail only for anything noteworthy.
    for r in results:
        if r.failed:
            why = []
            if r.diff_fields:
                why.append("INVARIANT FIELDS DIFFER: " + ",".join(r.diff_fields))
            if r.transitions_violation:
                why.append(f"transitions violation (+{r.tr_added}/-{r.tr_removed} on baseline-tr>0)")
            print(f"  FAIL {r.apk}: {'; '.join(why)}")

    print()
    print(f"APKs compared:                 {len(results)}")
    print(f"baseline-tr>0 (diff-zero set): {len(diffzero_72)}")
    print(f"invariant-field diffs (FAIL):  {len(field_fails)}"
          + (f" -> {[r.apk for r in field_fails][:10]}" if field_fails else ""))
    print(f"transitions violations (FAIL): {len(tr_viol)}"
          + (f" -> {[r.apk for r in tr_viol][:10]}" if tr_viol else ""))
    print(f"recovered (tr 0 -> >0):        {len(recovered)}")
    print(f"complete flag changed:         {sum(1 for r in results if r.complete_changed)}")

    verdict = "PASS" if not field_fails and not tr_viol else "FAIL"
    print(f"verdict: {verdict}")
    print("  (PASS = reachability/windows/components/package/mainActivity identical on ALL APKs,"
          " AND transitions diff-zero on every baseline-tr>0 APK; recovered APKs only ADD transitions.)")

    if args.report:
        args.report.write_text(json.dumps({
            "verdict": verdict,
            "apks_compared": len(results),
            "invariant_field_fails": [{"apk": r.apk, "fields": r.diff_fields} for r in field_fails],
            "transitions_violations": [
                {"apk": r.apk, "added": r.tr_added, "removed": r.tr_removed} for r in tr_viol
            ],
            "recovered": [{"apk": r.apk, "added": r.tr_added} for r in recovered],
        }, indent=2))

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

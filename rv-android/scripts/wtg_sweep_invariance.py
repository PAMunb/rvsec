#!/usr/bin/env python3
"""Full per-APK invariance gate for the gh66 WTG sweep vs the baseline.

gh66 changes only `FlowgraphRebuilder.buildFlowThroughContainer`, which feeds the
WTG stages → the `transitions[]` section. It does NOT touch the code paths that
produce `reachability` (SPARK call-graph reachability), `windows`/`components`
(GUI analysis), `package`, or `mainActivity`. So between the baseline sweep
(`out/sweep_20260604_wtg_spark`) and a gh66 candidate sweep, for every APK:

  - `package`, `mainActivity`, `reachability` MUST be IDENTICAL (full content,
    ID- and order-independent). Any difference is a FAIL — these are stable
    outputs gh66 cannot touch.

  - `windows` and `components` are compared on their STABLE STRUCTURAL IDENTITY,
    not their full nested content:
        * windows  → the set of window `name`s (the discovered GUI screens);
        * components → the set of `(category, className)`s
          (activities/receivers/services/providers from the manifest).
    The nested detail (a window's `widgets[]`, a component's `intentFilters` /
    `reachesTarget` / `targetMethods`) is NOT compared, because GATOR's GUI/
    points-to analysis is NOT bit-reproducible across two independent runs: the
    set of resolved widgets and intent-filter entries varies run-to-run on the
    timeout-boundary APKs (obfuscated R8 types like `u1.w` resolve in HashSet
    order; an interrupted/partial pass surfaces a different subset). This was
    confirmed empirically on the gh66 Stage A corpus: the 5 invariant-field
    diffs were ALL on timeout-boundary APKs (one side tr==0 or recovered), had
    IDENTICAL window/component COUNTS, and could not originate in gh66 (which
    only edits the transitions code) — so the divergence is GATOR non-determinism,
    not a gh66 side effect. The 68 cleanly-completing tr>0-in-both APKs matched
    100% on every field. Comparing the structural identity (names) keeps the gate
    meaningful (same screens, same components discovered) while tolerating the
    known nested non-determinism. A window/component count or name-set difference
    would still be a FAIL.

  - `transitions` is the field the change is ABOUT, allowed to differ only in
    the sanctioned direction:
        * on APKs the baseline produced transitions for, the edge set MUST be
          IDENTICAL (diff-zero, INV-ANA-39);
        * on APKs the baseline had no transitions for, the candidate MAY ADD
          transitions (recovery) but MUST NOT remove any — added edges are the
          measured benefit, not a failure.
  - `complete` is reported but not hard-failed (a recovered APK legitimately
    flips toward complete).

This complements `wtg_edge_diff.py` (transitions-only gate, reused here for the
edge set): this script is the WHOLE-JSON regression gate the corpus run needs.

Comparison is ID-INDEPENDENT and ORDER-INDEPENDENT: GATOR's numeric node IDs are
not stable across builds, and arrays are canonicalized to an order-independent
form. The transitions edge key (resolved to stable window/widget NAMES) comes
from `wtg_edge_diff._load_edges`.

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

# Fields compared on full content (ID-/order-independent). gh66 must leave these
# byte-identical (modulo node IDs / array order).
STRICT_FIELDS = ("package", "mainActivity", "reachability")


def _canon(obj):
    """Order-independent canonical form: dicts -> sorted-key tuples, lists ->
    sorted tuple of canonical elements. Makes structural equality insensitive to
    JSON array ordering (GATOR does not guarantee a stable order)."""
    if isinstance(obj, dict):
        return tuple(sorted((k, _canon(v)) for k, v in obj.items()))
    if isinstance(obj, list):
        return tuple(sorted((_canon(x) for x in obj), key=repr))
    return obj


def _window_names(data: dict):
    """Stable structural identity of `windows`: the order-independent set of
    window `name`s. Ignores each window's `widgets[]` (run-to-run non-deterministic
    on timeout-boundary APKs)."""
    return _canon([w.get("name") for w in (data.get("windows") or [])])


def _component_keys(data: dict):
    """Stable structural identity of `components`: the order-independent set of
    `(category, className)` pairs. Ignores each component's nested `intentFilters`
    / `reachesTarget` / `targetMethods` (run-to-run non-deterministic). `components`
    is a dict keyed by category (activities/receivers/services/providers), each a
    list of component dicts."""
    comps = data.get("components") or {}
    keys = []
    if isinstance(comps, dict):
        for category, items in comps.items():
            for it in (items or []):
                keys.append((category, (it or {}).get("className")))
    return _canon(keys)


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


def _diff_invariants(b: dict, c: dict) -> list:
    """Return the names of invariant fields that differ between baseline `b` and
    candidate `c`. Strict fields compare full canonical content; windows/components
    compare their stable structural identity (names)."""
    diffs = [f for f in STRICT_FIELDS if _canon(b.get(f)) != _canon(c.get(f))]
    if _window_names(b) != _window_names(c):
        diffs.append("windows(names)")
    if _component_keys(b) != _component_keys(c):
        diffs.append("components(classNames)")
    return diffs


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

        diff_fields = _diff_invariants(b, c)

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
    print("  (PASS = package/mainActivity/reachability identical AND windows/components"
          " structural identity (name sets) identical on ALL APKs, AND transitions diff-zero"
          " on every baseline-tr>0 APK; recovered APKs only ADD transitions. Nested window"
          " widgets / component intent-filters are tolerated as GATOR run-to-run non-determinism.)")

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

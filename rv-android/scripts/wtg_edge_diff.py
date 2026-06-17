#!/usr/bin/env python3
"""Exact edge-set diff-zero gate for gh66 (buildFlowThroughContainer perf fix).

The gh66 optimization (hoist + memoize the container-flow linking pass in
GATOR's `FlowgraphRebuilder.buildFlowThroughContainer`) MUST be edge-set-
identical to the unoptimized pass (INV-ANA-39). This script is the gate: for
every APK present in both a baseline and a candidate sweep, it asserts the
`transitions[]` edge set is *exactly* equal — zero edges added, zero removed.

Why not `wtg_paridade_diff.py`: that comparator keys on the 3-tuple
`(sourceId, targetId, event_type)` of *raw numeric* node IDs and tolerates
divergence via a Jaccard threshold. Two problems make it unfit as the gh66
gate: (1) GATOR assigns window/widget node IDs per build — they are NOT stable
across builds, so a raw-ID key can report spurious diffs (or mask real ones)
when the only thing that changed is ID numbering; (2) it omits widget and
handler identity, and tolerates non-zero divergence. gh66 requires set
EQUALITY on a key built from STABLE identifiers.

Stable edge key (per event):
    (source window NAME, target window NAME,
     event type, widget name, widget class, handler signature)
`sourceId`/`targetId` are resolved to their window `name` via the same JSON's
`windows[]`. Widget identity comes from the event's inline `widgetName` /
`widgetClass` (widgets are nested under windows, and each event already carries
its widget's name+class), so no separate widget table lookup is needed. A
transition with no events still contributes one keyed edge (events part empty)
so source/target structure is not silently dropped.

Baseline scope: the canonical per-APK JSONs `<dir>/<app>/<app>.apk.json`,
EXCLUDING any `_backup/` subtree (duplicates would inflate the APK set).

Exit codes:
  0 — PASS (every common APK edge-set-identical)
  1 — FAIL (≥1 APK with added or removed edges)
  2 — usage / IO error
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# Edge key = 6-field tuple of strings (see module docstring).
Edge = tuple


def _window_name_map(data: dict) -> dict:
    """Map window id -> window name from `windows[]`.

    IDs are build-unstable; names are stable. Used to translate the numeric
    `sourceId`/`targetId` of each transition into a stable key.
    """
    out: dict = {}
    for win in data.get("windows", []) or []:
        wid = win.get("id")
        if wid is not None:
            out[wid] = win.get("name") or ""
    return out


def _load_edges(path: Path) -> tuple[set[Edge], int]:
    """Return (edge set keyed on stable identifiers, count of unresolved endpoints).

    An unresolved endpoint is a transition whose `sourceId`/`targetId` is not
    present in `windows[]`; it is keyed with a `<unresolved:ID>` sentinel and
    counted, because a raw numeric fallback would not be comparable across
    builds. A non-zero unresolved count is reported so the operator knows the
    key degraded for those edges.
    """
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"failed to read {path}: {exc}") from exc

    winmap = _window_name_map(data)
    edges: set[Edge] = set()
    unresolved = 0

    def name_of(node_id) -> str:
        nonlocal unresolved
        if node_id in winmap:
            return winmap[node_id]
        unresolved += 1
        return f"<unresolved:{node_id}>"

    for tr in data.get("transitions", []) or []:
        src = tr.get("sourceId")
        tgt = tr.get("targetId")
        if src is None or tgt is None:
            continue
        src_name = name_of(src)
        tgt_name = name_of(tgt)
        events = tr.get("events") or []
        if not events:
            edges.add((src_name, tgt_name, "", "", "", ""))
            continue
        for ev in events:
            if not isinstance(ev, dict):
                continue
            edges.add((
                src_name,
                tgt_name,
                ev.get("type") or "",
                ev.get("widgetName") or "",
                ev.get("widgetClass") or "",
                ev.get("handler") or "",
            ))
    return edges, unresolved


@dataclass
class PerApk:
    apk: str
    baseline: int
    candidate: int
    added: list = field(default_factory=list)     # in candidate, not baseline
    removed: list = field(default_factory=list)    # in baseline, not candidate
    unresolved_base: int = 0
    unresolved_cand: int = 0

    @property
    def identical(self) -> bool:
        return not self.added and not self.removed


def _walk_apks(directory: Path) -> dict[str, Path]:
    """Map `<app>.apk` (the .apk.json stem) -> path, skipping any `_backup/` subtree."""
    out: dict[str, Path] = {}
    for p in directory.glob("**/*.apk.json"):
        if "_backup" in p.parts:
            continue
        out[p.stem] = p
    return out


def compute(baseline_dir: Path, candidate_dir: Path) -> list[PerApk]:
    base_map = _walk_apks(baseline_dir)
    cand_map = _walk_apks(candidate_dir)

    common = sorted(set(base_map) & set(cand_map))
    only_base = sorted(set(base_map) - set(cand_map))
    only_cand = sorted(set(cand_map) - set(base_map))
    if only_base:
        print(f"[edge-diff] WARN baseline-only APKs (not compared): {len(only_base)}",
              file=sys.stderr)
    if only_cand:
        print(f"[edge-diff] WARN candidate-only APKs (not compared): {len(only_cand)}",
              file=sys.stderr)

    results: list[PerApk] = []
    for apk in common:
        base_set, unres_b = _load_edges(base_map[apk])
        cand_set, unres_c = _load_edges(cand_map[apk])
        results.append(PerApk(
            apk=apk,
            baseline=len(base_set),
            candidate=len(cand_set),
            added=sorted(cand_set - base_set),
            removed=sorted(base_set - cand_set),
            unresolved_base=unres_b,
            unresolved_cand=unres_c,
        ))
    return results


def _format(results: Iterable[PerApk], show_edges: bool) -> str:
    rows = list(results)
    header = f"{'APK':<55s} {'base':>6s} {'cand':>6s} {'+added':>7s} {'-removed':>8s} {'status':>8s}"
    lines = [header, "-" * len(header)]
    for r in rows:
        status = "OK" if r.identical else "DIFF"
        lines.append(
            f"{r.apk:<55s} {r.baseline:>6d} {r.candidate:>6d} "
            f"{len(r.added):>7d} {len(r.removed):>8d} {status:>8s}"
        )
        if show_edges and not r.identical:
            for e in r.added[:20]:
                lines.append(f"    + {e}")
            for e in r.removed[:20]:
                lines.append(f"    - {e}")
            if len(r.added) > 20 or len(r.removed) > 20:
                lines.append("    ... (truncated; see --report for full lists)")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exact transitions[] edge-set diff-zero gate (gh66 / INV-ANA-39)",
    )
    parser.add_argument("baseline", type=Path,
                        help="Baseline sweep dir (pre-change), e.g. out/sweep_20260604_wtg_spark")
    parser.add_argument("candidate", type=Path,
                        help="Candidate sweep dir produced by the gh66-corrected JAR")
    parser.add_argument("--show-edges", action="store_true",
                        help="Print the first added/removed edges for each diverging APK")
    parser.add_argument("--report", type=Path, default=None,
                        help="Optional path to write a full JSON report")
    args = parser.parse_args()

    if not args.baseline.is_dir() or not args.candidate.is_dir():
        print("[edge-diff] baseline or candidate dir missing", file=sys.stderr)
        return 2

    try:
        results = compute(args.baseline, args.candidate)
    except RuntimeError as exc:
        print(f"[edge-diff] {exc}", file=sys.stderr)
        return 2

    if not results:
        print("[edge-diff] no APKs in common — nothing to compare", file=sys.stderr)
        return 2

    print(_format(results, args.show_edges))

    diverged = [r for r in results if not r.identical]
    unresolved = [r for r in results if r.unresolved_base or r.unresolved_cand]
    print()
    print(f"APKs compared: {len(results)}")
    print(f"edge-set-identical: {len(results) - len(diverged)}")
    print(f"diverged: {len(diverged)}")
    if unresolved:
        print(f"WARN: {len(unresolved)} APK(s) had transitions referencing windows "
              f"absent from windows[] (key degraded for those edges)")
    verdict = "PASS" if not diverged else "FAIL"
    print(f"verdict: {verdict}")

    if args.report:
        args.report.write_text(json.dumps({
            "verdict": verdict,
            "apks_compared": len(results),
            "identical": len(results) - len(diverged),
            "diverged": [
                {
                    "apk": r.apk,
                    "baseline_edges": r.baseline,
                    "candidate_edges": r.candidate,
                    "added": r.added,
                    "removed": r.removed,
                    "unresolved_base": r.unresolved_base,
                    "unresolved_cand": r.unresolved_cand,
                }
                for r in diverged
            ],
        }, indent=2))

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

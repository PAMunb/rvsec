#!/usr/bin/env python3
"""Jaccard paridade gate for the gh57 WTG-SPARK delegation (Group 6, M3).

Compares two directories of GATOR analysis JSONs (one produced with
cgDelegation=false — the pre-gh57 legacy CG path — and one with
cgDelegation=true — Scene.v().getCallGraph() delegation plus the
IGNORED_CLASSES bytecode-scan complement). For every APK present in
both dirs, computes the Jaccard similarity of the transition set —
each transition is a tuple (source_id, target_id, event_type) — and
reports per-APK + average.

Pass criteria (per spec scenario "Paridade Jaccard WTG-SPARK on
baseline-OK APKs"):
  - average Jaccard ≥ 0.95 AND
  - minimum per-APK Jaccard ≥ 0.85

Exit codes:
  0 — PASS
  1 — FAIL (any threshold missed)
  2 — usage / IO error
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


def _load_transitions(path: Path) -> set[tuple]:
    """Return the set of (source_id, target_id, event_type) tuples.

    A widget-event without an explicit `type` is keyed as "_" so the
    Jaccard computation still discriminates source/target ordering.
    """
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"failed to read {path}: {exc}") from exc

    out: set[tuple] = set()
    for tr in data.get("transitions", []) or []:
        src = tr.get("sourceId")
        tgt = tr.get("targetId")
        if src is None or tgt is None:
            continue
        events = tr.get("events") or []
        if not events:
            out.add((src, tgt, "_"))
            continue
        for ev in events:
            ev_type = ev.get("type") if isinstance(ev, dict) else None
            out.add((src, tgt, ev_type or "_"))
    return out


@dataclass
class PerApk:
    apk: str
    baseline: int
    candidate: int
    intersection: int
    union: int
    jaccard: float


def _jaccard(a: set, b: set) -> tuple[int, int, float]:
    inter = len(a & b)
    union = len(a | b)
    if union == 0:
        return 0, 0, 1.0  # both empty → identical
    return inter, union, inter / union


def _walk_apks(directory: Path) -> dict[str, Path]:
    """Map basename (without .json) → path. Skips files lacking .apk.json suffix."""
    out: dict[str, Path] = {}
    for p in directory.glob("**/*.apk.json"):
        # Use the filename minus the .json so foo.apk and foo.apk.json keys
        # align with how the sweep names artifacts.
        out[p.stem] = p
    return out


def compute(baseline_dir: Path, candidate_dir: Path) -> list[PerApk]:
    base_map = _walk_apks(baseline_dir)
    cand_map = _walk_apks(candidate_dir)

    common = sorted(set(base_map) & set(cand_map))
    only_base = sorted(set(base_map) - set(cand_map))
    only_cand = sorted(set(cand_map) - set(base_map))
    if only_base:
        print(f"[paridade] WARN baseline-only APKs (skipped): {only_base}",
              file=sys.stderr)
    if only_cand:
        print(f"[paridade] WARN candidate-only APKs (skipped): {only_cand}",
              file=sys.stderr)

    results: list[PerApk] = []
    for apk in common:
        base_set = _load_transitions(base_map[apk])
        cand_set = _load_transitions(cand_map[apk])
        inter, union, j = _jaccard(base_set, cand_set)
        results.append(PerApk(apk, len(base_set), len(cand_set), inter, union, j))
    return results


def _format(results: Iterable[PerApk]) -> str:
    rows = list(results)
    header = (
        f"{'APK':<60s} {'base':>6s} {'cand':>6s} "
        f"{'inter':>6s} {'union':>6s} {'jaccard':>8s}"
    )
    lines = [header, "-" * len(header)]
    for r in rows:
        lines.append(
            f"{r.apk:<60s} {r.baseline:>6d} {r.candidate:>6d} "
            f"{r.intersection:>6d} {r.union:>6d} {r.jaccard:>8.3f}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Jaccard paridade gate for gh57 cgDelegation (WTG-SPARK)",
    )
    parser.add_argument("baseline", type=Path,
                        help="Directory with JSONs produced under cgDelegation=false")
    parser.add_argument("candidate", type=Path,
                        help="Directory with JSONs produced under cgDelegation=true")
    parser.add_argument("--threshold-avg", type=float, default=0.95,
                        help="Minimum average Jaccard (default: 0.95)")
    parser.add_argument("--threshold-min", type=float, default=0.85,
                        help="Minimum per-APK Jaccard (default: 0.85)")
    parser.add_argument("--report", type=Path, default=None,
                        help="Optional path to write a JSON report")
    args = parser.parse_args()

    if not args.baseline.is_dir() or not args.candidate.is_dir():
        print(f"[paridade] baseline or candidate dir missing", file=sys.stderr)
        return 2

    try:
        results = compute(args.baseline, args.candidate)
    except RuntimeError as exc:
        print(f"[paridade] {exc}", file=sys.stderr)
        return 2

    if not results:
        print("[paridade] no APKs in common — nothing to compare", file=sys.stderr)
        return 2

    print(_format(results))

    avg = sum(r.jaccard for r in results) / len(results)
    minimum = min(r.jaccard for r in results)
    print()
    print(f"average Jaccard: {avg:.3f}")
    print(f"minimum Jaccard: {minimum:.3f}  ({min(results, key=lambda r: r.jaccard).apk})")

    pass_avg = avg >= args.threshold_avg
    pass_min = minimum >= args.threshold_min
    verdict = "PASS" if (pass_avg and pass_min) else "FAIL"
    print(f"verdict: {verdict}  "
          f"(avg≥{args.threshold_avg} → {pass_avg}; "
          f"min≥{args.threshold_min} → {pass_min})")

    if args.report:
        args.report.write_text(json.dumps({
            "average_jaccard": avg,
            "minimum_jaccard": minimum,
            "threshold_avg": args.threshold_avg,
            "threshold_min": args.threshold_min,
            "verdict": verdict,
            "apks": [r.__dict__ for r in results],
        }, indent=2))

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Gate G_gh60_sweep_delta — 380-APK sweep regression against pre-gh60 baseline.

Closes design.md line 433 + tasks.md 9.3 + 9.4.

Context
-------
gh60 renamed every gator-local "MOP" identifier to "Target": Java field
`reachesMop` → `reachesTarget`, Python `reaches_mop` → `reaches_target`,
JSON key `directlyReachesMop` → `directlyReachesTarget`. The rename is a
pure dictionary swap with no algorithmic change, so the **counts** the
analyzer produces per APK MUST stay within a small tolerance of the
pre-gh60 baseline. Drift beyond that means something on the matching /
reachability path silently changed semantics.

Two-step pipeline
-----------------
    1. Run `scripts/static_analysis_sweep.py` twice:
         (a) on the pre-gh60 commit, output → `<baseline-dir>/`
         (b) on the gh60 commit,     output → `<new-dir>/`
       Each pass emits one `<package>/<apk>.json` per APK + a `progress.csv`.
    2. Run this script against the two sweep dirs to produce a per-APK
       delta CSV + verdict.

This script is read-only — it does not invoke GATOR. Bundling the run
and the regression check in one script would make the slow GATOR phase
hard to resume; the existing sweep script already handles resume well.

Gate checks (design.md line 433 + line 188)
-------------------------------------------
    G1. Per-APK relative delta of `reachesTarget` count ≤ THRESHOLD (5%)
    G2. Per-APK relative delta of `windows[]` length     ≤ THRESHOLD
    G3. Per-APK relative delta of `transitions[]` length ≤ THRESHOLD
    G4. `complete=true` rate in the NEW sweep ≥ FLOOR (80%)
    G5. APKs present in baseline but missing from new (and vice versa)
        are reported but not load-bearing — sweeps may diverge in
        coverage if the dataset shifted; surfaces in the report.

Naming-scheme transparency
--------------------------
Baseline JSONs use `reachesMop`/`directlyReachesMop` (pre-rename).
New JSONs use `reachesTarget`/`directlyReachesTarget`. The count extractor
below reads EITHER key — the count semantics is what the gate cares about,
the bytes-on-disk name is renaming-out-of-scope for this regression test.

Exit codes
----------
    0  — all gates PASS
    1  — at least one gate FAIL (per-APK outliers or complete rate floor)
    2  — operator error (missing dirs, bad CLI args)
    77 — prerequisites missing (POSIX skipped convention)

Output files (written to --report-dir, default `<new-dir>/delta_report/`)
-------------------------------------------------------------------------
    per_apk_delta.csv      — every APK with old/new counts + rel_delta
    outliers.csv           — subset of per_apk_delta.csv where any
                             metric exceeded the threshold
    summary.json           — machine-readable verdict, all aggregates
    summary.txt            — human-readable verdict (printed to stdout too)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_THRESHOLD = 0.05  # 5%
DEFAULT_COMPLETE_FLOOR = 0.80
SKIP_EXIT = 77


@dataclass
class ApkCounts:
    """Numeric summary of one APK's analysis JSON, naming-scheme agnostic."""

    apk_name: str = ""
    methods_total: int = 0
    methods_reachable: int = 0
    reaches_target: int = 0  # `reachesTarget` OR legacy `reachesMop`
    directly_reaches_target: int = 0
    windows: int = 0
    transitions: int = 0
    complete: Optional[bool] = None  # None = sentinel absent (gh57 / pre-ADR-6)
    json_ok: bool = False


@dataclass
class DeltaRow:
    """Per-APK comparison record, one line in `per_apk_delta.csv`."""

    apk_name: str = ""
    in_baseline: bool = False
    in_new: bool = False
    base_reaches_target: int = 0
    new_reaches_target: int = 0
    rel_delta_reaches_target: Optional[float] = None
    base_windows: int = 0
    new_windows: int = 0
    rel_delta_windows: Optional[float] = None
    base_transitions: int = 0
    new_transitions: int = 0
    rel_delta_transitions: Optional[float] = None
    new_complete: Optional[bool] = None
    new_methods_total: int = 0
    flagged_metrics: List[str] = field(default_factory=list)


def _count_apk(json_path: Path) -> ApkCounts:
    """Parse one APK JSON and produce naming-scheme-agnostic counts.

    Tolerates missing keys, partial timeouts (no transitions section), and
    legacy MOP names. Returns `json_ok=False` on unparseable bytes so the
    delta report can still emit a row for the APK without crashing.
    """
    counts = ApkCounts(apk_name=json_path.stem)
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return counts

    counts.json_ok = True
    counts.complete = raw.get("complete") if isinstance(raw.get("complete"), bool) else None

    # Reachability — iterate classes, count methods with the bool flags set.
    # Accept BOTH naming schemes per the script docstring; baseline uses
    # `reachesMop`, new uses `reachesTarget`.
    for cls in raw.get("reachability", []) or []:
        if not isinstance(cls, dict):
            continue
        for m in cls.get("methods", []) or []:
            if not isinstance(m, dict):
                continue
            counts.methods_total += 1
            if m.get("reachable"):
                counts.methods_reachable += 1
            if m.get("reachesTarget") or m.get("reachesMop"):
                counts.reaches_target += 1
            if m.get("directlyReachesTarget") or m.get("directlyReachesMop"):
                counts.directly_reaches_target += 1

    windows = raw.get("windows", []) or []
    if isinstance(windows, list):
        counts.windows = len(windows)
    transitions = raw.get("transitions", []) or []
    if isinstance(transitions, list):
        counts.transitions = len(transitions)
    return counts


def _scan_sweep_dir(sweep_dir: Path) -> Dict[str, ApkCounts]:
    """Walk a sweep output dir and index every APK JSON by basename.

    The sweep writes `<package>/<apk_name>.json` (apk_name still carries
    the .apk suffix per `static_analysis_sweep.py:436`). We strip the
    suffix once for the map key so a baseline sweep and a new sweep
    keyed by different package layouts still line up.
    """
    out: Dict[str, ApkCounts] = {}
    for json_path in sweep_dir.rglob("*.apk.json"):
        # Skip _backup/, _logs/, _progress/, delta_report/ — those carry
        # auxiliary state, not the canonical per-APK analysis output.
        rel = json_path.relative_to(sweep_dir).as_posix()
        if rel.startswith(("_backup/", "_logs/", "_progress/", "delta_report/")):
            continue
        # `apk.stem` would strip only the .json; we want the .apk too.
        basename = json_path.name.removesuffix(".json")  # foo.apk
        counts = _count_apk(json_path)
        counts.apk_name = basename
        out[basename] = counts
    return out


def _rel_delta(base: int, new: int) -> Optional[float]:
    """Relative delta with a sane baseline-zero policy.

    base == 0:
        new == 0 → 0.0   (no signal, no drift — vacuously fine)
        new  > 0 → None  (cannot normalise; flagged separately in the
                          outlier rule so the operator sees the growth)
    base > 0:
        |new - base| / base, always defined.

    Returning None lets the caller distinguish "cannot compute" from
    "computed to zero", which matters for the flagged_metrics list.
    """
    if base == 0:
        return 0.0 if new == 0 else None
    return abs(new - base) / base


def _compute_deltas(
    baseline: Dict[str, ApkCounts],
    new: Dict[str, ApkCounts],
    threshold: float,
) -> List[DeltaRow]:
    """Build one DeltaRow per APK seen in either sweep."""
    rows: List[DeltaRow] = []
    all_apks = sorted(set(baseline.keys()) | set(new.keys()))
    for apk in all_apks:
        b = baseline.get(apk)
        n = new.get(apk)
        row = DeltaRow(
            apk_name=apk,
            in_baseline=b is not None,
            in_new=n is not None,
            base_reaches_target=b.reaches_target if b else 0,
            new_reaches_target=n.reaches_target if n else 0,
            base_windows=b.windows if b else 0,
            new_windows=n.windows if n else 0,
            base_transitions=b.transitions if b else 0,
            new_transitions=n.transitions if n else 0,
            new_complete=n.complete if n else None,
            new_methods_total=n.methods_total if n else 0,
        )
        # Only compute deltas when both sides exist; an APK absent from one
        # side is reported via in_baseline/in_new and isn't a "drift outlier".
        if b is not None and n is not None:
            row.rel_delta_reaches_target = _rel_delta(b.reaches_target, n.reaches_target)
            row.rel_delta_windows = _rel_delta(b.windows, n.windows)
            row.rel_delta_transitions = _rel_delta(b.transitions, n.transitions)

            for metric, value in (
                ("reaches_target", row.rel_delta_reaches_target),
                ("windows", row.rel_delta_windows),
                ("transitions", row.rel_delta_transitions),
            ):
                # None means base==0, new>0 — count it as an outlier so the
                # operator sees the growth-from-nothing case explicitly.
                if value is None or value > threshold:
                    row.flagged_metrics.append(metric)
        rows.append(row)
    return rows


def _write_per_apk_csv(rows: List[DeltaRow], path: Path) -> None:
    fields = [
        "apk_name", "in_baseline", "in_new",
        "base_reaches_target", "new_reaches_target", "rel_delta_reaches_target",
        "base_windows", "new_windows", "rel_delta_windows",
        "base_transitions", "new_transitions", "rel_delta_transitions",
        "new_complete", "new_methods_total", "flagged_metrics",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(fields)
        for r in rows:
            writer.writerow([
                r.apk_name, r.in_baseline, r.in_new,
                r.base_reaches_target, r.new_reaches_target,
                _fmt_pct(r.rel_delta_reaches_target),
                r.base_windows, r.new_windows, _fmt_pct(r.rel_delta_windows),
                r.base_transitions, r.new_transitions, _fmt_pct(r.rel_delta_transitions),
                _fmt_bool(r.new_complete), r.new_methods_total,
                "|".join(r.flagged_metrics),
            ])


def _fmt_pct(v: Optional[float]) -> str:
    return "" if v is None else f"{v:.4f}"


def _fmt_bool(v: Optional[bool]) -> str:
    return "" if v is None else ("True" if v else "False")


def _summarise(
    rows: List[DeltaRow],
    threshold: float,
    floor: float,
) -> Dict[str, object]:
    """Compute aggregate verdict + dict for summary.json / summary.txt."""
    common = [r for r in rows if r.in_baseline and r.in_new]
    only_baseline = [r for r in rows if r.in_baseline and not r.in_new]
    only_new = [r for r in rows if r.in_new and not r.in_baseline]
    outliers = [r for r in common if r.flagged_metrics]

    new_rows = [r for r in rows if r.in_new]
    complete_true = sum(1 for r in new_rows if r.new_complete is True)
    complete_rate = (complete_true / len(new_rows)) if new_rows else 0.0

    gates = {
        "G1_reaches_target_within_threshold": all(
            r.rel_delta_reaches_target is not None
            and r.rel_delta_reaches_target <= threshold
            for r in common
        ),
        "G2_windows_within_threshold": all(
            r.rel_delta_windows is not None
            and r.rel_delta_windows <= threshold
            for r in common
        ),
        "G3_transitions_within_threshold": all(
            r.rel_delta_transitions is not None
            and r.rel_delta_transitions <= threshold
            for r in common
        ),
        "G4_complete_rate_above_floor": complete_rate >= floor,
    }

    return {
        "threshold": threshold,
        "complete_floor": floor,
        "n_total_apks": len(rows),
        "n_common": len(common),
        "n_only_baseline": len(only_baseline),
        "n_only_new": len(only_new),
        "n_outliers": len(outliers),
        "complete_true_count": complete_true,
        "complete_total_count": len(new_rows),
        "complete_rate": complete_rate,
        "gates": gates,
        "pass": all(gates.values()),
        "outlier_apks": [r.apk_name for r in outliers],
        "only_baseline_apks": [r.apk_name for r in only_baseline],
        "only_new_apks": [r.apk_name for r in only_new],
    }


def _format_summary_txt(summary: Dict[str, object]) -> str:
    lines = [
        "G_gh60_sweep_delta " + ("PASS" if summary["pass"] else "FAIL"),
        f"  threshold:       {summary['threshold']:.4f}",
        f"  complete floor:  {summary['complete_floor']:.4f}",
        f"  total APKs:      {summary['n_total_apks']}",
        f"  in both:         {summary['n_common']}",
        f"  baseline only:   {summary['n_only_baseline']}",
        f"  new only:        {summary['n_only_new']}",
        f"  outliers:        {summary['n_outliers']}",
        f"  complete=true:   {summary['complete_true_count']}/{summary['complete_total_count']} "
        f"({summary['complete_rate']:.4f})",
        "",
        "Gates:",
    ]
    for name, ok in summary["gates"].items():
        lines.append(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if summary["outlier_apks"]:
        lines.append("")
        lines.append(f"Outlier APKs ({len(summary['outlier_apks'])}):")
        for apk in summary["outlier_apks"][:20]:
            lines.append(f"  {apk}")
        if len(summary["outlier_apks"]) > 20:
            lines.append(f"  ... and {len(summary['outlier_apks']) - 20} more")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline-dir", required=True, type=Path,
                        help="Sweep output dir from the PRE-gh60 commit "
                             "(uses `reachesMop` key)")
    parser.add_argument("--new-dir", required=True, type=Path,
                        help="Sweep output dir from the gh60 commit "
                             "(uses `reachesTarget` key)")
    parser.add_argument("--report-dir", type=Path, default=None,
                        help="Where to write per_apk_delta.csv / outliers.csv / "
                             "summary.{json,txt} (default: <new-dir>/delta_report/)")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help=f"Per-APK relative-delta tolerance (default: "
                             f"{DEFAULT_THRESHOLD})")
    parser.add_argument("--complete-floor", type=float,
                        default=DEFAULT_COMPLETE_FLOOR,
                        help=f"Minimum `complete=true` rate in the new sweep "
                             f"(default: {DEFAULT_COMPLETE_FLOOR})")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    if not args.baseline_dir.is_dir():
        print(f"[skip] baseline dir missing at {args.baseline_dir}", file=sys.stderr)
        return SKIP_EXIT
    if not args.new_dir.is_dir():
        print(f"[skip] new dir missing at {args.new_dir}", file=sys.stderr)
        return SKIP_EXIT

    report_dir = args.report_dir or (args.new_dir / "delta_report")
    report_dir.mkdir(parents=True, exist_ok=True)

    if args.verbose:
        print(f"[scan] baseline = {args.baseline_dir}", file=sys.stderr)
    baseline = _scan_sweep_dir(args.baseline_dir)
    if args.verbose:
        print(f"[scan] new      = {args.new_dir}", file=sys.stderr)
    new = _scan_sweep_dir(args.new_dir)

    if not baseline:
        print(f"[skip] baseline dir has no *.apk.json files: {args.baseline_dir}",
              file=sys.stderr)
        return SKIP_EXIT
    if not new:
        print(f"[skip] new dir has no *.apk.json files: {args.new_dir}",
              file=sys.stderr)
        return SKIP_EXIT

    rows = _compute_deltas(baseline, new, args.threshold)

    per_apk_csv = report_dir / "per_apk_delta.csv"
    outliers_csv = report_dir / "outliers.csv"
    _write_per_apk_csv(rows, per_apk_csv)
    _write_per_apk_csv([r for r in rows if r.flagged_metrics], outliers_csv)

    summary = _summarise(rows, args.threshold, args.complete_floor)
    (report_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    summary_txt = _format_summary_txt(summary)
    (report_dir / "summary.txt").write_text(summary_txt + "\n", encoding="utf-8")
    print(summary_txt)
    print(f"\nArtifacts written to: {report_dir}")

    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""CONSOLIDATE — build the campaign's paired datasets from raw result files.

Copy of ``experimento-cal/scripts/consolidate_cal.py`` with only its trace-reading path
adapted (see "Trace reading" below). It reads the raw outputs the campaign wrote under
``results/`` — per-container ``tasks.json`` files, per-task ``.logcat`` files, and per-task
``.trace`` files (LLM arms) — and emits the two datasets the comparison consumes:

    per_apk_paired.csv   one row per APK; column "apk" then {arm_label}__{metric} for
                         each arm × metric in
                         [cov_method, cov_act, cov_mop, mop_unique, mop_total, crashes];
                         reps AVERAGED per (apk, arm). This is the file `compare.py`
                         pairs against leg A's, so its shape is load-bearing.
    tel_proxies.csv      one row per (arm, apk, rep) with LLM telemetry aggregates
                         summed from the .trace files.

Anti-gh58 sourcing (INV-CAL-08). Coverage percentages and MOP-unique counts come from
``tasks.json -> result.coverage_metrics`` (the field a resume pass leaves intact); the total
MOP-violation count (``mop_total``) is counted directly from the raw logcat ``RVSEC`` lines.
The per-container CSV fields that a resume pass may have zeroed are NEVER read here.

Identity + dedup (INV-CAL-08, INV-CAL-07). Every task is keyed by its identity
``(apk_name, tool_name, variant, repetition, timeout)`` — never by ``task_id``, because a
resume appends fresh task_ids for the same identity and would double-count it. When two
records share one identity (the classic resume duplicate), the record with a COMPLETED state
and the larger coverage is kept, so a resume that re-emitted a zeroed record cannot drag the
identity's metrics down.

Arm labelling. The column-group label for an arm is its RV_TOOLS token
``f"{tool}:{variant}"`` (e.g. ``ape:default``, ``aperv:cal_a1``). The logcat/trace FILENAME
fragment differs for the ape builtin — it is ``ape`` (no variant) — so the two are computed
separately: ``arm_label`` for the CSV column, ``toolfrag`` for the file name.

Trace reading. This copy reads the stage-4 NDJSON trace through
``aperv_tool.analysis.trace_ndjson``, which is the only sanctioned reader of that format.
The original under ``experimento-cal/scripts/`` parses the retired ``[APE-*]`` ``key=value``
family and stays that way: it reads a finished corpus that will not be regenerated
(INV-APV-55), so it is copied here and never edited there.

**The adaptation is deliberately narrow.** Only the trace path moved. The logcat and
``tasks.json`` paths — which produce every headline outcome and the whole of
``per_apk_paired.csv`` — are carried over unchanged, so this campaign's leg stays
column-identical and aggregation-identical to the leg it is paired against. Anything wider
would break the pairing the gate rests on.

Usage, from the campaign directory (uv, so `aperv_tool` resolves):
    uv run python scripts/consolidate.py --iter-dir .
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

from aperv_tool.analysis import trace_ndjson

# --- metric contract -------------------------------------------------------------------
# The six per-APK metrics, in the fixed column order downstream analysis expects.
METRICS: List[str] = [
    "cov_method",
    "cov_act",
    "cov_mop",
    "mop_unique",
    "mop_total",
    "crashes",
]

# The three coverage percentages read from tasks.json (used for best-record selection).
_COVERAGE_KEYS = (
    "method_coverage",
    "activities_coverage",
    "methods_mop_reachable_coverage",
)

# --- logcat markers --------------------------------------------------------------------
# A property-violation (MOP) line: tag RVSEC, message begins "<Name>Spec,". Note that the
# coverage tag RVSEC-COV is NOT matched: after "RVSEC" it carries "-COV", not ":".
_RVSEC_RE = re.compile(r"\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$")

# --- trace reading ---------------------------------------------------------------------
# `decision_source` names the mechanism whose boost was largest; the LLM's own value is the
# jar's DecisionSource.LLM, written verbatim. A step can carry several LLM attempts and
# still be decided by another channel, which is why `llm_tap` is counted from the step and
# not from the calls.
_LLM_DECISION_SOURCE = "LLM"

# tel_proxies columns beyond the (arm, apk, rep) key. The no_match reasons and decision
# modes are enumerated so the CSV has a fixed, stable header regardless of which reasons or
# modes a given trace happened to exercise.
_NO_MATCH_REASONS = ("degenerate", "boundary", "other")
_MODES = ("new_state", "stagnation", "random")
_TEL_SUMMARY_FIELDS = (
    "calls",
    "time_ms",
    "tokens_in",
    "tokens_out",
    "matched",
    "llm_tap",
    "no_match",
)
TEL_COLUMNS: List[str] = (
    ["arm", "apk", "rep"]
    + list(_TEL_SUMMARY_FIELDS)
    + [f"no_match_{r}" for r in _NO_MATCH_REASONS]
    + [f"mode_{m}" for m in _MODES]
)


def arm_label(name: str, variant: Optional[str]) -> str:
    """RV_TOOLS column label for an arm: ``f"{tool}:{variant}"`` (ape builtin included)."""
    return f"{name}:{variant}"


def toolfrag(name: str, variant: Optional[str]) -> str:
    """Filename fragment of an arm's logcat/trace: ``ape`` for the builtin, else tool:variant."""
    return "ape" if name == "ape" else f"{name}:{variant}"


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# --- raw task loading ------------------------------------------------------------------
def load_task_records(iter_dir: Path) -> List[Dict[str, Any]]:
    """Every task record under ``iterN/results/*/*/tasks.json`` with its identity + base dir.

    Returns a flat list; dedup happens later. Each element carries the parsed identity,
    the raw ``result`` block, and the container base directory (parent of tasks.json) so
    the co-located logcat/trace files can be found.
    """
    records: List[Dict[str, Any]] = []
    for tasks_json in sorted((iter_dir / "results").glob("*/*/tasks.json")):
        try:
            payload = json.loads(tasks_json.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        base = tasks_json.parent
        for task in payload.get("tasks", []):
            cfg = task.get("config") or {}
            tc = cfg.get("tool_config") or {}
            name = tc.get("name")
            variant = tc.get("variant")
            if name is None:
                continue
            identity = (
                cfg.get("apk_name"),
                name,
                variant,
                cfg.get("repetition"),
                cfg.get("timeout"),
            )
            records.append(
                {
                    "identity": identity,
                    "apk": cfg.get("apk_name"),
                    "name": name,
                    "variant": variant,
                    "rep": cfg.get("repetition"),
                    "timeout": cfg.get("timeout"),
                    "result": task.get("result") or {},
                    "base": base,
                }
            )
    return records


def _record_rank(record: Dict[str, Any]) -> Tuple[int, float]:
    """Sort key that prefers a COMPLETED record and then the one with the most coverage.

    A resume that re-emits a zeroed duplicate for an already-finished identity ranks below
    the real record, so ``max()`` on this key keeps the genuine measurement.
    """
    result = record["result"]
    completed = 1 if result.get("state") == "COMPLETED" else 0
    cov = result.get("coverage_metrics") or {}
    cov_sum = sum(_to_float(cov.get(k)) for k in _COVERAGE_KEYS)
    return (completed, cov_sum)


def dedup_by_identity(records: List[Dict[str, Any]]) -> Dict[Tuple, Dict[str, Any]]:
    """Collapse records to one per identity, keeping the best record (see ``_record_rank``)."""
    best: Dict[Tuple, Dict[str, Any]] = {}
    for rec in records:
        ident = rec["identity"]
        if ident not in best or _record_rank(rec) > _record_rank(best[ident]):
            best[ident] = rec
    return best


# --- logcat + trace parsing ------------------------------------------------------------
def count_mop_total(base: Path, apk: str, rep: Any, timeout: Any, frag: str) -> int:
    """Count raw ``RVSEC`` MOP-violation lines in the identity's logcat (0 if absent)."""
    logcat = base / apk / f"{apk}__{rep}__{timeout}__{frag}.logcat"
    try:
        with open(logcat, errors="ignore") as fh:
            return sum(1 for line in fh if "RVSEC" in line and _RVSEC_RE.search(line))
    except FileNotFoundError:
        return 0


def parse_trace_telemetry(path: Path) -> Optional[Dict[str, Any]]:
    """Aggregate one NDJSON ``.trace`` into a telemetry row dict, or None if no LLM ran.

    The stage-4 jar emits no run-level Summary line: the per-step records carry every LLM
    call inside the step that made it, so the run-level aggregates are summed here instead
    of being read off a line the jar computed. That is the whole of the adaptation — the
    columns, their names and their order are unchanged, so ``tel_proxies.csv`` from this
    campaign and from the calibration corpus stay readable by the same consumer.

    Each column, and what it now sums over:

    ``calls``      LLM entries that were a routing attempt. The breaker's once-per-episode
                   decline is excluded: it records that no call was made.
    ``time_ms``    Sum of the per-call ``ms``.
    ``tokens_in``  / ``tokens_out``  Sum of the per-call token pair.
    ``matched``    Attempts whose result was ``matched``.
    ``no_match``   Attempts whose result was ``no_match``.
    ``llm_tap``    Steps whose action the LLM actually selected, counted from the step's
                   own ``decision_source`` rather than from the calls — a step can carry
                   several attempts and still not be decided by any of them.

    Returning None for a trace with no LLM attempt preserves the original contract: a
    non-LLM arm contributes no telemetry row rather than a row of zeros.
    """
    try:
        reader = trace_ndjson.TraceReader(path)
    except OSError:
        return None

    totals = {field: 0 for field in _TEL_SUMMARY_FIELDS}
    reason_counts: Counter = Counter()
    mode_counts: Counter = Counter()
    saw_attempt = False

    try:
        for step in reader:
            if step.decision_source == _LLM_DECISION_SOURCE:
                totals["llm_tap"] += 1
            for call in step.llm:
                if call.result in (None, "breaker_open"):
                    continue
                saw_attempt = True
                totals["calls"] += 1
                totals["time_ms"] += call.ms or 0
                if call.tokens:
                    totals["tokens_in"] += call.tokens[0]
                    totals["tokens_out"] += call.tokens[1]
                if call.result == "matched":
                    totals["matched"] += 1
                elif call.result == "no_match":
                    totals["no_match"] += 1
                    reason = call.reason or "other"
                    reason_counts[
                        reason if reason in _NO_MATCH_REASONS else "other"
                    ] += 1
                mode = (call.mode or "").replace("-", "_")
                if mode in _MODES:
                    mode_counts[mode] += 1
    except OSError:
        return None

    if not saw_attempt:
        return None
    row = dict(totals)
    for reason in _NO_MATCH_REASONS:
        row[f"no_match_{reason}"] = reason_counts.get(reason, 0)
    for mode in _MODES:
        row[f"mode_{mode}"] = mode_counts.get(mode, 0)
    return row


# --- arm ordering ----------------------------------------------------------------------
def resolve_arm_order(iter_dir: Path, observed: List[str]) -> List[str]:
    """Column-group order for the arms: manifest order if a manifest is present, else sorted.

    Using the manifest keeps the CSV column order identical to the declared arm order across
    iterations; without one (e.g. a bare fixture tree) the observed labels are sorted for a
    deterministic header.
    """
    manifest_path = iter_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            ordered = [a["rv_tools_token"] for a in manifest.get("arms", [])]
            if ordered:
                # keep declared order, then append any observed arm not in the manifest.
                extra = [a for a in sorted(observed) if a not in ordered]
                return ordered + extra
        except (OSError, json.JSONDecodeError, KeyError):
            pass
    return sorted(observed)


# --- consolidation ---------------------------------------------------------------------
def build_per_apk_paired(
    deduped: Dict[Tuple, Dict[str, Any]], arms: List[str]
) -> Tuple[List[str], List[List[Any]]]:
    """Build the per-APK paired table (header, rows): one row per APK, reps averaged.

    For each identity the six metrics are gathered (coverage/MOP-unique/crashes from
    tasks.json, mop_total from the logcat), then averaged over reps within each (apk, arm).
    """
    # (apk, arm_label) -> metric -> list of per-identity values (one per rep).
    per_cell: Dict[Tuple[str, str], Dict[str, List[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for rec in deduped.values():
        apk = rec["apk"]
        label = arm_label(rec["name"], rec["variant"])
        result = rec["result"]
        cov = result.get("coverage_metrics") or {}
        frag = toolfrag(rec["name"], rec["variant"])
        mop_total = count_mop_total(rec["base"], apk, rec["rep"], rec["timeout"], frag)
        values = {
            "cov_method": _to_float(cov.get("method_coverage")),
            "cov_act": _to_float(cov.get("activities_coverage")),
            "cov_mop": _to_float(cov.get("methods_mop_reachable_coverage")),
            "mop_unique": _to_float(cov.get("total_errors")),
            "mop_total": float(mop_total),
            "crashes": _to_float(result.get("detected_errors_count")),
        }
        for metric, value in values.items():
            per_cell[(apk, label)][metric].append(value)

    apks = sorted({apk for apk, _ in per_cell})
    header = ["apk"] + [f"{arm}__{metric}" for arm in arms for metric in METRICS]
    rows: List[List[Any]] = []
    for apk in apks:
        row: List[Any] = [apk]
        for arm in arms:
            cell = per_cell.get((apk, arm))
            for metric in METRICS:
                if cell and cell.get(metric):
                    row.append(round(mean(cell[metric]), 4))
                else:
                    row.append("")  # arm absent for this APK (paired-completeness gap)
        rows.append(row)
    return header, rows


def build_tel_proxies(deduped: Dict[Tuple, Dict[str, Any]]) -> List[List[Any]]:
    """Build the LLM telemetry rows (one per arm×apk×rep that has a parseable .trace)."""
    rows: List[List[Any]] = []
    for rec in sorted(
        deduped.values(), key=lambda r: (r["name"], r["variant"], r["apk"], r["rep"])
    ):
        frag = toolfrag(rec["name"], rec["variant"])
        trace = (
            rec["base"]
            / rec["apk"]
            / f'{rec["apk"]}__{rec["rep"]}__{rec["timeout"]}__{frag}.trace'
        )
        if not trace.exists():
            continue
        tel = parse_trace_telemetry(trace)
        if tel is None:
            continue
        label = arm_label(rec["name"], rec["variant"])
        row = [label, rec["apk"], rec["rep"]] + [
            tel.get(col, 0) for col in TEL_COLUMNS[3:]
        ]
        rows.append(row)
    return rows


def run_timeout(iter_dir: Path) -> Optional[Any]:
    """The run's timeout from ``iterN/manifest.json`` — the single source of the smoke filter.

    Consolidation keeps only identities whose ``timeout`` equals this value, dropping the
    smoke tasks (90s, written by the ``cala_smoke_*`` containers under the same ``results/``
    tree). Smoke and run identities share ``(apk, tool, variant, rep)`` and differ only in
    ``timeout``; since ``build_per_apk_paired`` groups by ``(apk, arm)`` without keying on
    timeout, an un-filtered smoke identity (shorter budget, lower coverage) would pollute the
    reps-averaged cell of every smoke arm×APK pair. Returns ``None`` when no manifest is
    present, in which case no filtering happens (e.g. synthetic test trees).
    """
    manifest_path = iter_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text()).get("timeout")
    except (OSError, json.JSONDecodeError):
        return None


def consolidate(iter_dir: Path) -> Dict[str, Any]:
    """Run the full consolidation, writing both CSVs. Returns a small summary dict."""
    records = load_task_records(iter_dir)
    if not records:
        sys.stderr.write(f"no task records found under {iter_dir}/results/\n")
        raise SystemExit(1)

    # Keep only the run's identities: drop smoke tasks whose timeout differs from the
    # manifest run timeout (see run_timeout). Without this, the 90s smoke reps average into
    # the 300s per-APK cells of the smoke arms.
    expected_timeout = run_timeout(iter_dir)
    dropped_smoke = 0
    if expected_timeout is not None:
        kept = [r for r in records if r["timeout"] == expected_timeout]
        dropped_smoke = len(records) - len(kept)
        records = kept

    deduped = dedup_by_identity(records)
    observed_arms = sorted(
        {arm_label(r["name"], r["variant"]) for r in deduped.values()}
    )
    arms = resolve_arm_order(iter_dir, observed_arms)

    header, rows = build_per_apk_paired(deduped, arms)
    paired_path = iter_dir / "per_apk_paired.csv"
    with open(paired_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)

    tel_rows = build_tel_proxies(deduped)
    tel_path = iter_dir / "tel_proxies.csv"
    with open(tel_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(TEL_COLUMNS)
        writer.writerows(tel_rows)

    return {
        "records": len(records),
        "identities": len(deduped),
        "dropped_smoke": dropped_smoke,
        "apks": len(rows),
        "arms": arms,
        "tel_rows": len(tel_rows),
        "per_apk_paired": paired_path,
        "tel_proxies": tel_path,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--iter-dir", required=True, help="path to the iteration tree (iterN/)"
    )
    args = parser.parse_args(argv)

    iter_dir = Path(args.iter_dir).resolve()
    if not (iter_dir / "results").is_dir():
        sys.stderr.write(f"no results/ under {iter_dir}\n")
        return 2

    summary = consolidate(iter_dir)
    smoke_note = (
        f" (dropped {summary['dropped_smoke']} smoke records)"
        if summary["dropped_smoke"]
        else ""
    )
    print(
        f"consolidated {iter_dir.name}: "
        f"{summary['records']} records{smoke_note} -> {summary['identities']} identities, "
        f"{summary['apks']} APKs, arms={summary['arms']}, "
        f"tel rows={summary['tel_rows']}"
    )
    print(f"  {summary['per_apk_paired']}")
    print(f"  {summary['tel_proxies']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Analyze APE-RV LLM telemetry for the cmpv2 base×v2 smoke (and full run).

Reads the per-task APE stdout traces under ``data/results/<exp>_*/**/*.trace`` and
aggregates the LLM routing telemetry that APE-RV prints on two markers:

  [APE-LLM-TEL] ... result=<matched|llm_tap|no_match> [reason=<degenerate|boundary>] ...
  [APE-RV] LLM Summary calls=N ... matched=N [llm_tap=N] no_match=N null=N ...

The ``llm-coordinate-tap`` change adds:
  * a new first-class per-decision outcome ``result=llm_tap`` (the off-tree coordinate
    tap: a valid in-bounds LLM coordinate that matched no widget is now dispatched as a
    raw tap instead of being discarded as ``no_match``);
  * an ``llm_tap=<N>`` counter on the Summary line, inserted between ``matched=`` and
    ``no_match=`` and joined into the ``decisions`` denominator
    (``decisions = matched + llm_tap + no_match + null``); and
  * a ``reason=degenerate|boundary`` sub-field on the ``no_match`` telemetry line,
    separating the (0,0) degenerate emission from the status/nav-band boundary reject.

WHY the Summary parse is field-based (``key=int`` dict) rather than a fixed positional
regex: the pre-change base traces (image 0.9.2) have NO ``llm_tap=`` field, while the
post-change re-run will. A positional regex pinned to ``matched .. no_match`` breaks the
moment ``llm_tap=`` is inserted between them. Reading every ``key=int`` pair makes the
parser insertion-order-independent: ``llm_tap`` defaults to 0 on old traces and is read on
new ones, so the SAME script analyzes both the current base results and the re-run.

Coverage (``cov_method`` / ``cov_mop`` / ``cov_act``) is read from
``tasks.json -> result.coverage_metrics`` (not the telemetry), and the no-LLM baseline is
joined from the cmpma consolidation (``aperv:sata_mop_activity`` on the same APKs).

Usage:
  python3 scripts/analyze_cmpv2_llm.py cmpv2s_base
  python3 scripts/analyze_cmpv2_llm.py cmpv2s_v2
  python3 scripts/analyze_cmpv2_llm.py --selftest      # parser unit check, no data needed
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, median

BASE = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE / "results"
CMPMA_BASELINE = BASE.parent / "data" / "results" / "cmpma_consolidado" / "per_apk_paired.csv"
BASELINE_ARM = "aperv:sata_mop_activity"  # no-LLM reference arm from cmpma

# The four completed-mapping outcomes that form the decisions denominator. `llm_tap` is
# new (off-tree tap); `null` here means the aggregate Summary `null=` counter (infra
# failures), which is not emitted as a per-decision [APE-LLM-TEL] line.
DECISION_OUTCOMES = ("matched", "llm_tap", "no_match", "null")

# --- line matchers ---------------------------------------------------------------------
_TEL_RE = re.compile(r"\[APE-LLM-TEL\]")
_SUMMARY_RE = re.compile(r"\[APE-RV\] LLM Summary\b")
_KV_INT_RE = re.compile(r"(\w+)=(-?\d+)\b")
_RESULT_RE = re.compile(r"\bresult=(\w+)")
_REASON_RE = re.compile(r"\breason=(\w+)")
_ACTION_RE = re.compile(r"\baction=(\w+)")
_NEAREST_RE = re.compile(r"\bnearest_dist=(-?\d+(?:\.\d+)?)")
_TIME_RE = re.compile(r"\btime_ms=(\d+)")


# --- parsing ---------------------------------------------------------------------------
def parse_summary(line: str) -> dict:
    """Parse an ``[APE-RV] LLM Summary`` line into a counter dict, field-based.

    ``llm_tap`` defaults to 0 so pre-change traces (which omit it) parse cleanly, and the
    decisions denominator stays comparable across the change.
    """
    fields = {k: int(v) for k, v in _KV_INT_RE.findall(line)}
    summary = {
        "calls": fields.get("calls", 0),
        "tokens_in": fields.get("tokens_in", 0),
        "tokens_out": fields.get("tokens_out", 0),
        "time_ms": fields.get("time_ms", 0),
        "matched": fields.get("matched", 0),
        "llm_tap": fields.get("llm_tap", 0),  # NEW — absent on pre-change traces -> 0
        "no_match": fields.get("no_match", 0),
        "null": fields.get("null", 0),
        "screenshot_failed": fields.get("screenshot_failed", 0),
        "breaker_trips": fields.get("breaker_trips", 0),
    }
    summary["decisions"] = (
        summary["matched"] + summary["llm_tap"] + summary["no_match"] + summary["null"]
    )
    return summary


def parse_tel(line: str) -> dict | None:
    """Parse one ``[APE-LLM-TEL]`` per-decision line, or None if it carries no result."""
    m = _RESULT_RE.search(line)
    if not m:
        return None
    result = m.group(1)
    reason = _REASON_RE.search(line)
    action = _ACTION_RE.search(line)
    nearest = _NEAREST_RE.search(line)
    tms = _TIME_RE.search(line)
    return {
        "result": result,  # matched | llm_tap | no_match
        "reason": reason.group(1) if reason else None,  # degenerate | boundary (no_match only)
        "action": action.group(1) if action else None,  # click | long_click | type_text | back
        "nearest_dist": float(nearest.group(1)) if nearest else None,
        "time_ms": int(tms.group(1)) if tms else None,
    }


def read_trace(path: Path) -> str:
    """APE stdout traces are binary-ish; decode latin-1 (lossless byte->char)."""
    return path.read_text(encoding="latin-1", errors="replace")


def parse_trace_file(path: Path) -> dict:
    """Aggregate one trace: last Summary line + all per-decision TEL lines."""
    summary = None
    decisions: list[dict] = []
    for line in read_trace(path).splitlines():
        if _SUMMARY_RE.search(line):
            summary = parse_summary(line)  # keep the last (final) summary
        elif _TEL_RE.search(line):
            tel = parse_tel(line)
            if tel:
                decisions.append(tel)
    return {"summary": summary, "decisions": decisions}


# --- coverage + baseline joins ---------------------------------------------------------
def load_coverage_by_apk(exp_prefix: str) -> dict[str, list[dict]]:
    """apk_name -> list of per-task coverage_metrics dicts, from every tasks.json."""
    out: dict[str, list[dict]] = {}
    for tasks_json in RESULTS_DIR.glob(f"{exp_prefix}_*/**/tasks.json"):
        try:
            data = json.loads(tasks_json.read_text())
        except Exception:
            continue
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        if isinstance(tasks, dict):
            tasks = list(tasks.values())
        for t in tasks:
            cfg = t.get("config", {}) or {}
            apk = cfg.get("apk_name")
            cov = (t.get("result", {}) or {}).get("coverage_metrics") or {}
            if apk and cov:
                out.setdefault(apk, []).append(cov)
    return out


def _norm_apk(name: str) -> str:
    return name[:-4] if name.endswith(".apk") else name


def load_baseline() -> dict[str, dict]:
    """cmpma no-LLM baseline (sata_mop_activity): norm_apk -> {cov_method, cov_mop}."""
    if not CMPMA_BASELINE.exists():
        return {}
    out: dict[str, dict] = {}
    with open(CMPMA_BASELINE) as f:
        for row in csv.DictReader(f):
            out[_norm_apk(row["apk"])] = {
                "cov_method": _to_float(row.get(f"{BASELINE_ARM}__cov_method")),
                "cov_mop": _to_float(row.get(f"{BASELINE_ARM}__cov_mop")),
            }
    return out


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# --- reporting -------------------------------------------------------------------------
def analyze(exp_prefix: str) -> str:
    traces = sorted(RESULTS_DIR.glob(f"{exp_prefix}_*/**/*.trace"))
    if not traces:
        return f"No trace files found under {RESULTS_DIR}/{exp_prefix}_*/"

    agg_summary = Counter()
    n_with_summary = 0
    tel_results = Counter()
    no_match_reasons = Counter()
    llm_tap_actions = Counter()
    decision_latencies: list[float] = []

    for tf in traces:
        parsed = parse_trace_file(tf)
        if parsed["summary"]:
            n_with_summary += 1
            for k, v in parsed["summary"].items():
                agg_summary[k] += v
        for d in parsed["decisions"]:
            tel_results[d["result"]] += 1
            if d["result"] == "no_match":
                no_match_reasons[d["reason"] or "unspecified"] += 1
            if d["result"] == "llm_tap":
                llm_tap_actions[d["action"] or "unknown"] += 1
            if d["time_ms"] is not None:
                decision_latencies.append(d["time_ms"])

    lines = [f"# cmpv2 LLM telemetry — {exp_prefix}\n",
             f"Traces: {len(traces)} | with LLM Summary: {n_with_summary}\n"]

    # Aggregate Summary (denominator now includes llm_tap).
    matched = agg_summary["matched"]
    llm_tap = agg_summary["llm_tap"]
    no_match = agg_summary["no_match"]
    null_ = agg_summary["null"]
    decisions = matched + llm_tap + no_match + null_
    lines.append("## Aggregate Summary (all traces)\n")
    lines.append(f"- calls: {agg_summary['calls']}")
    lines.append(f"- matched: {matched}")
    lines.append(f"- llm_tap: {llm_tap}   (NEW — off-tree coordinate taps)")
    lines.append(f"- no_match: {no_match}")
    lines.append(f"- null: {null_}  (screenshot_failed={agg_summary['screenshot_failed']})")
    lines.append(f"- breaker_trips: {agg_summary['breaker_trips']}")
    lines.append(f"- decisions (= matched+llm_tap+no_match+null): {decisions}")
    if decisions:
        lines.append(f"- widget-match rate (matched/decisions): {matched * 100 / decisions:.1f}%")
        lines.append(f"- off-tree tap rate (llm_tap/decisions): {llm_tap * 100 / decisions:.1f}%")
    # Off-tree recovery: fraction of the former no_match population now captured as a tap.
    former_no_match = llm_tap + no_match
    if former_no_match:
        lines.append(
            f"- off-tree recovery (llm_tap / (llm_tap+no_match)): "
            f"{llm_tap * 100 / former_no_match:.1f}%  "
            f"(share of pre-change no_match now acted on)")

    # Per-decision TEL cross-check (independent of the Summary counters).
    lines.append("\n## Per-decision [APE-LLM-TEL] outcomes\n")
    tel_total = sum(tel_results.values())
    for r in ("matched", "llm_tap", "no_match"):
        c = tel_results.get(r, 0)
        pct = f"{c * 100 / tel_total:.1f}%" if tel_total else "n/a"
        lines.append(f"- {r}: {c} ({pct})")
    if no_match_reasons:
        lines.append("\n### no_match reason breakdown\n")
        for reason, c in no_match_reasons.most_common():
            lines.append(f"- reason={reason}: {c}")
    if llm_tap_actions:
        lines.append("\n### llm_tap action breakdown\n")
        for act, c in llm_tap_actions.most_common():
            lines.append(f"- action={act}: {c}")
    if decision_latencies:
        lines.append("\n### decision latency (ms, per [APE-LLM-TEL])\n")
        lines.append(f"- median: {median(decision_latencies):.0f}  "
                     f"mean: {mean(decision_latencies):.0f}  "
                     f"max: {max(decision_latencies):.0f}  n={len(decision_latencies)}")

    # Coverage vs no-LLM baseline (paired on the same APKs).
    lines.append("\n## Coverage vs cmpma no-LLM baseline (" + BASELINE_ARM + ")\n")
    cov_by_apk = load_coverage_by_apk(exp_prefix)
    baseline = load_baseline()
    if not cov_by_apk:
        lines.append("No coverage_metrics found in tasks.json.")
    elif not baseline:
        lines.append(f"No baseline CSV at {CMPMA_BASELINE} — skipping paired delta.")
    else:
        deltas_method, deltas_mop = [], []
        for apk, covs in cov_by_apk.items():
            b = baseline.get(_norm_apk(apk))
            if not b:
                continue
            arm_method = mean(c["method_coverage"] for c in covs if "method_coverage" in c)
            arm_mop = mean(c["methods_mop_reachable_coverage"] for c in covs
                           if "methods_mop_reachable_coverage" in c)
            if b["cov_method"] is not None:
                deltas_method.append(arm_method - b["cov_method"])
            if b["cov_mop"] is not None:
                deltas_mop.append(arm_mop - b["cov_mop"])
        if deltas_method:
            lines.append(f"- Δ cov_method (arm − baseline): mean {mean(deltas_method):+.2f}pp "
                         f"(n={len(deltas_method)} APKs)")
        if deltas_mop:
            lines.append(f"- Δ cov_mop    (arm − baseline): mean {mean(deltas_mop):+.2f}pp "
                         f"(n={len(deltas_mop)} APKs)")
        lines.append("  (Wilcoxon signed-rank on these paired deltas is done in the "
                     "consolidation step; this is the descriptive mean.)")

    return "\n".join(lines)


# --- self-test (no data required) ------------------------------------------------------
def selftest() -> int:
    """Prove the parser handles BOTH the pre-change and post-change telemetry formats."""
    old_summary = ("[APE] [APE-RV] LLM Summary calls=98 tokens_in=112728 tokens_out=2262 "
                   "time_ms=75468 matched=66 no_match=21 null=11 screenshot_failed=0 "
                   "breaker_trips=1")
    new_summary = ("[APE] [APE-RV] LLM Summary calls=98 tokens_in=112728 tokens_out=2262 "
                   "time_ms=75468 matched=60 llm_tap=6 no_match=15 null=11 "
                   "screenshot_failed=0 breaker_trips=1")

    old = parse_summary(old_summary)
    assert old["llm_tap"] == 0, "pre-change trace must default llm_tap to 0"
    assert old["matched"] == 66 and old["no_match"] == 21 and old["null"] == 11
    assert old["decisions"] == 66 + 0 + 21 + 11 == 98, old["decisions"]

    new = parse_summary(new_summary)
    assert new["llm_tap"] == 6, "post-change llm_tap must be read"
    assert new["matched"] == 60 and new["no_match"] == 15 and new["null"] == 11
    # Denominator stability: an off-tree event formerly under no_match is now under llm_tap,
    # both inside decisions -> decisions is unchanged vs the old line (98).
    assert new["decisions"] == 60 + 6 + 15 + 11 == 92, new["decisions"]

    # Per-decision TEL: old (no reason), new llm_tap, new no_match with reason.
    tel_matched = parse_tel("[APE-LLM-TEL] call=1 action=click result=matched "
                            "nearest_dist=11.0 time_ms=1597")
    assert tel_matched["result"] == "matched" and tel_matched["reason"] is None
    assert tel_matched["action"] == "click" and tel_matched["time_ms"] == 1597

    tel_tap = parse_tel("[APE-LLM-TEL] call=2 action=long_click result=llm_tap "
                        "nearest_dist=294.0 time_ms=900")
    assert tel_tap["result"] == "llm_tap" and tel_tap["action"] == "long_click"

    tel_deg = parse_tel("[APE-LLM-TEL] call=3 action=click qwen=(0,0) result=no_match "
                        "reason=degenerate nearest_dist=823.1 time_ms=1251")
    assert tel_deg["result"] == "no_match" and tel_deg["reason"] == "degenerate"

    tel_bnd = parse_tel("[APE-LLM-TEL] call=4 action=click result=no_match reason=boundary")
    assert tel_bnd["reason"] == "boundary"

    assert parse_tel("[APE-LLM-TEL] no result here") is None

    print("selftest OK — parser reads both pre-change (no llm_tap) and post-change "
          "(llm_tap + reason) telemetry; decisions denominator includes llm_tap.")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--selftest":
        return selftest()
    print(analyze(argv[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

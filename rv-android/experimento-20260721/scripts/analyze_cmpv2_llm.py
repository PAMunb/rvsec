#!/usr/bin/env python3
"""Analyze APE-RV LLM telemetry for the cmp_llm_20260721 base×v2 comparison.

Reads the per-task APE stdout traces under ``results/<exp>_*/**/*.trace`` and aggregates
the semi-structured LLM telemetry APE-RV prints. The trace grammar is self-describing
(each run records the exact LLM config it ran under) and per-decision joinable (each LLM
decision joins to its outcome on a ``step`` key). The grammar is defined by the APE
``llm-experiment-logging`` change (ape commit d90c1f4); this parser is its consumer.

LINE GRAMMAR (all key=value, insertion-order-independent):

  [APE-LLM-CONFIG] model=<m> temperature=<t> top_p=<p> top_k=<k> max_tokens=<mt>
      timeout_ms=<ms> prompt_variant=<v> llm_percentage=<pct> on_new_state=<b>
      on_stagnation=<b> stagnation_threshold=<n> url=<u>
        -> once per run at LlmRouter construction; the *requested* effective config.
  [APE-LLM-CONFIG-ACK] server_model=<m>
        -> once per run after the first successful chat(); the model the server *served*
           (proves base vs v2 talked to the intended weights).
  [APE-STEP] step=<N> clock=<ms> activity=<A> state=<S> action=<T> decision_source=<src> ...
        -> one per finally-selected action (gated by stepTelemetryEnabled); join anchor.
  [APE-LLM-TEL] step=<N> mode=<new-state|stagnation|random> result=<matched|llm_tap|no_match>
      [reason=<degenerate|boundary>] tokens_in=<N> tokens_out=<N> time_ms=<N>
        -> one per LLM routing attempt that reached the coordinate-mapping step.
  [APE-LLM-ERROR] step=<N> cause=<timeout|http_<status>|connection|parse|image|internal> detail=<msg>
        -> one per attempt abandoned before mapping (screenshot failures excepted).
  [APE-OUTCOME] step=<N> decision_source=<src> new_state=<bool> target_state=<key> activity_changed=<bool>
        -> one per recorded transition (gated by stepTelemetryEnabled); joins to [APE-STEP]
           and [APE-LLM-TEL] by step.
  [APE-RV] LLM Summary calls=<N> tokens_in=<N> tokens_out=<N> time_ms=<N> matched=<N>
      llm_tap=<N> no_match=<N> timeout=<N> http_error=<N> conn_error=<N> parse_error=<N>
      image_error=<N> internal_error=<N> screenshot_failed=<N> breaker_trips=<N>
        -> aggregate at tearDown; the seven cause counters partition the retired null count.

BACKWARD TOLERANCE: pre-change traces (image 0.9.2, cmpm) carry NO step/config/outcome
lines and an aggregate ``null=<N>`` on the Summary instead of the per-cause counters. The
parser detects the grammar generation per Summary line (``null=`` present -> old) and
forms the decisions denominator identically in value across both:
  old: decisions = matched + llm_tap + no_match + null           (screenshot_failed ⊂ null)
  new: decisions = matched + llm_tap + no_match + Σ(seven causes) (screenshot_failed is a peer)
so the SAME script analyzes both the confounded cmpm traces and the cmp_llm_20260721 re-run.

THREE-WAY JOIN (the point of the d90c1f4 change): within each trace, [APE-LLM-TEL],
[APE-STEP] and [APE-OUTCOME] share a per-run-unique ``step``. Joining on it answers, per
arm and without timestamp reconstruction:
  * of the actions the LLM chose, what fraction discovered a NEW state vs SATA's;
  * per-call cost (tokens, latency) attributed to the decision AND its outcome.

Coverage (``cov_method`` / ``cov_mop`` / ``cov_act``) is read from
``tasks.json -> result.coverage_metrics`` (the dependent variable, not the telemetry); the
no-LLM baseline is joined from the cmpma consolidation (``aperv:sata_mop_activity``).

Usage:
  python3 scripts/analyze_cmpv2_llm.py cmp_llm_20260721_base
  python3 scripts/analyze_cmpv2_llm.py cmp_llm_20260721_v2
  python3 scripts/analyze_cmpv2_llm.py --selftest      # parser unit check, no data needed
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

BASE = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE / "results"
CMPMA_BASELINE = BASE.parent / "data" / "results" / "cmpma_consolidado" / "per_apk_paired.csv"
BASELINE_ARM = "aperv:sata_mop_activity"  # no-LLM reference arm from cmpma

# The seven failure-cause counters that (new grammar) partition the retired null count and
# form the non-decision tail of the decisions denominator.
FAILURE_CAUSES = ("timeout", "http_error", "conn_error", "parse_error",
                  "image_error", "internal_error", "screenshot_failed")

# --- line matchers ---------------------------------------------------------------------
_CONFIG_RE = re.compile(r"\[APE-LLM-CONFIG\](?!-ACK)")
_ACK_RE = re.compile(r"\[APE-LLM-CONFIG-ACK\]")
_STEP_RE = re.compile(r"\[APE-STEP\]")
_TEL_RE = re.compile(r"\[APE-LLM-TEL\]")
_ERROR_RE = re.compile(r"\[APE-LLM-ERROR\]")
_OUTCOME_RE = re.compile(r"\[APE-OUTCOME\]")
_SUMMARY_RE = re.compile(r"\[APE-RV\] LLM Summary\b")

# key=value where value runs to the next whitespace. Insertion-order-independent: every
# reader looks a field up by name, never by position, so an inserted/omitted field (e.g.
# llm_tap on old traces, step on new ones) never shifts another field's parse.
_KV_RE = re.compile(r"(\w+)=(\S+)")
# `detail=<message>` may contain spaces and is the last field on [APE-LLM-ERROR]; captured
# whole so an error message with spaces does not fragment into spurious key=value tokens.
_DETAIL_RE = re.compile(r"\bdetail=(.*)$")


def _kv(line: str) -> dict[str, str]:
    """All key=value tokens on a line as strings (value = up to next whitespace)."""
    return {k: v for k, v in _KV_RE.findall(line)}


def _as_int(v: str | None) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _as_bool(v: str | None) -> bool | None:
    if v is None:
        return None
    return v.strip().lower() == "true"


# --- parsing ---------------------------------------------------------------------------
def parse_config(line: str) -> dict:
    """Parse the [APE-LLM-CONFIG] manifest (requested effective config). Strings kept raw."""
    kv = _kv(line)
    return {f: kv.get(f) for f in (
        "model", "temperature", "top_p", "top_k", "max_tokens", "timeout_ms",
        "prompt_variant", "llm_percentage", "on_new_state", "on_stagnation",
        "stagnation_threshold", "url")}


def parse_ack(line: str) -> str | None:
    """Parse [APE-LLM-CONFIG-ACK] -> the server-reported model, or None."""
    return _kv(line).get("server_model")


def parse_step(line: str) -> dict | None:
    """Parse [APE-STEP] -> the selection join anchor; None if it carries no step."""
    kv = _kv(line)
    step = _as_int(kv.get("step"))
    if step is None:
        return None
    return {
        "step": step,
        "decision_source": kv.get("decision_source"),
        "activity": kv.get("activity"),
        "state": kv.get("state"),
        "action": kv.get("action"),
        "clock": _as_int(kv.get("clock")),
    }


def parse_tel(line: str) -> dict | None:
    """Parse one [APE-LLM-TEL] per-decision line, or None if it carries no result.

    ``step`` is None on pre-change (0.9.2) traces, which do not stamp it — such a decision
    cannot join to an outcome and is counted as unjoinable, not dropped.
    """
    kv = _kv(line)
    result = kv.get("result")
    if not result:
        return None
    return {
        "step": _as_int(kv.get("step")),  # None on pre-change traces
        "mode": kv.get("mode"),           # new-state | stagnation | random
        "result": result,                 # matched | llm_tap | no_match
        "reason": kv.get("reason"),       # degenerate | boundary (no_match only)
        "action": kv.get("action"),       # click | long_click | type_text | back
        "tokens_in": _as_int(kv.get("tokens_in")),
        "tokens_out": _as_int(kv.get("tokens_out")),
        "time_ms": _as_int(kv.get("time_ms")),
    }


def parse_error(line: str) -> dict | None:
    """Parse [APE-LLM-ERROR] -> {step, cause, detail}; None if no cause."""
    kv = _kv(line)
    cause = kv.get("cause")
    if not cause:
        return None
    detail = _DETAIL_RE.search(line)
    return {
        "step": _as_int(kv.get("step")),
        "cause": cause,  # timeout | http_<status> | connection | parse | image | internal
        "detail": detail.group(1).strip() if detail else None,
    }


def parse_outcome(line: str) -> dict | None:
    """Parse [APE-OUTCOME] -> the per-step decision outcome; None if it carries no step."""
    kv = _kv(line)
    step = _as_int(kv.get("step"))
    if step is None:
        return None
    return {
        "step": step,
        "decision_source": kv.get("decision_source"),
        "new_state": _as_bool(kv.get("new_state")),
        "target_state": kv.get("target_state"),
        "activity_changed": _as_bool(kv.get("activity_changed")),
    }


def parse_summary(line: str) -> dict:
    """Parse an [APE-RV] LLM Summary line, field-based, backward-tolerant.

    Detects the grammar generation from the line itself: pre-change traces carry ``null=``,
    post-change traces replaced it with the seven per-cause counters. The decisions
    denominator is formed identically in value across both (see module docstring), so the
    counter is NOT silently under-formed on new traces where ``null`` is absent.
    """
    fields = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)\b", line)}
    g = fields.get
    is_old = "null" in fields  # old grammar: single aggregate null (screenshot_failed ⊂ null)
    cause_sum = sum(g(c, 0) for c in FAILURE_CAUSES)
    failures = g("null", 0) if is_old else cause_sum
    summary = {
        "calls": g("calls", 0),
        "tokens_in": g("tokens_in", 0),
        "tokens_out": g("tokens_out", 0),
        "time_ms": g("time_ms", 0),
        "matched": g("matched", 0),
        "llm_tap": g("llm_tap", 0),
        "no_match": g("no_match", 0),
        "breaker_trips": g("breaker_trips", 0),
        "grammar": "old" if is_old else "new",
        # Failure tail: per-cause on new traces; the single opaque null on old ones.
        "null": g("null", 0),
        **{c: g(c, 0) for c in FAILURE_CAUSES},
        "failures": failures,
    }
    summary["decisions"] = (
        summary["matched"] + summary["llm_tap"] + summary["no_match"] + failures
    )
    return summary


def read_trace(path: Path) -> str:
    """APE stdout traces are binary-ish; decode latin-1 (lossless byte->char)."""
    return path.read_text(encoding="latin-1", errors="replace")


def parse_trace_file(path: Path) -> dict:
    """Aggregate one trace: config manifest, server ACK, last Summary, and every
    per-decision line, indexed by ``step`` for the three-way join."""
    config = None
    server_model = None
    summary = None
    decisions: list[dict] = []
    errors: list[dict] = []
    steps: dict[int, dict] = {}
    outcomes: dict[int, dict] = {}
    tel_by_step: dict[int, dict] = {}

    for line in read_trace(path).splitlines():
        # [APE-LLM-CONFIG-ACK] must be tested before [APE-LLM-CONFIG] (prefix overlap).
        if _ACK_RE.search(line):
            if server_model is None:
                server_model = parse_ack(line)
        elif _CONFIG_RE.search(line):
            if config is None:
                config = parse_config(line)
        elif _SUMMARY_RE.search(line):
            summary = parse_summary(line)  # keep the last (final) summary
        elif _TEL_RE.search(line):
            tel = parse_tel(line)
            if tel:
                decisions.append(tel)
                if tel["step"] is not None:
                    tel_by_step[tel["step"]] = tel
        elif _ERROR_RE.search(line):
            err = parse_error(line)
            if err:
                errors.append(err)
        elif _OUTCOME_RE.search(line):
            oc = parse_outcome(line)
            if oc:
                outcomes[oc["step"]] = oc
        elif _STEP_RE.search(line):
            st = parse_step(line)
            if st:
                steps[st["step"]] = st

    return {
        "config": config,
        "server_model": server_model,
        "summary": summary,
        "decisions": decisions,
        "errors": errors,
        "steps": steps,
        "outcomes": outcomes,
        "tel_by_step": tel_by_step,
    }


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
    grammar_seen = Counter()
    tel_results = Counter()
    no_match_reasons = Counter()
    llm_tap_actions = Counter()
    error_causes = Counter()
    decision_latencies: list[float] = []

    # Config-manifest + server-model consistency across the arm (all traces should agree).
    manifests: Counter = Counter()
    server_models: Counter = Counter()
    n_config = n_ack = 0

    # Three-way join accumulators.
    # new_state discovery by decision source (LLM vs SATA vs ...): source -> [total, new].
    outcome_by_source: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    # LLM call cost attributed to outcome: (new_state -> lists of tokens_out / time_ms).
    llm_cost_by_outcome: dict[str, dict[str, list[int]]] = {
        "new_state": {"tokens_out": [], "time_ms": []},
        "same_state": {"tokens_out": [], "time_ms": []},
    }
    n_joined = 0  # LLM decisions joined tel<->outcome by step

    for tf in traces:
        parsed = parse_trace_file(tf)
        if parsed["summary"]:
            n_with_summary += 1
            grammar_seen[parsed["summary"]["grammar"]] += 1
            for k, v in parsed["summary"].items():
                if isinstance(v, int):
                    agg_summary[k] += v
        if parsed["config"]:
            n_config += 1
            manifests[_manifest_key(parsed["config"])] += 1
        if parsed["server_model"]:
            n_ack += 1
            server_models[parsed["server_model"]] += 1
        for d in parsed["decisions"]:
            tel_results[d["result"]] += 1
            if d["result"] == "no_match":
                no_match_reasons[d["reason"] or "unspecified"] += 1
            if d["result"] == "llm_tap":
                llm_tap_actions[d["action"] or "unknown"] += 1
            if d["time_ms"] is not None:
                decision_latencies.append(d["time_ms"])
        for e in parsed["errors"]:
            error_causes[e["cause"]] += 1

        # --- three-way join within this trace, keyed by step ---
        for step, oc in parsed["outcomes"].items():
            src = oc["decision_source"] or "unknown"
            bucket = outcome_by_source[src]
            bucket[0] += 1
            if oc["new_state"]:
                bucket[1] += 1
            tel = parsed["tel_by_step"].get(step)
            if tel:  # an LLM-routed decision with a recorded outcome
                n_joined += 1
                key = "new_state" if oc["new_state"] else "same_state"
                if tel["tokens_out"] is not None:
                    llm_cost_by_outcome[key]["tokens_out"].append(tel["tokens_out"])
                if tel["time_ms"] is not None:
                    llm_cost_by_outcome[key]["time_ms"].append(tel["time_ms"])

    lines = [f"# cmp_llm_20260721 LLM telemetry — {exp_prefix}\n",
             f"Traces: {len(traces)} | with LLM Summary: {n_with_summary} | "
             f"grammar: {dict(grammar_seen)}\n"]

    # Arm self-description: config manifest + served model (base vs v2 identity proof).
    lines.append("## Arm self-description ([APE-LLM-CONFIG] / [APE-LLM-CONFIG-ACK])\n")
    lines.append(f"- traces carrying a config manifest: {n_config}/{len(traces)}")
    if manifests:
        if len(manifests) == 1:
            lines.append(f"- config manifest: CONSISTENT across the arm — {next(iter(manifests))}")
        else:
            lines.append(f"- config manifest: **{len(manifests)} DISTINCT variants** (arm not homogeneous):")
            for man, c in manifests.most_common():
                lines.append(f"    [{c} traces] {man}")
    lines.append(f"- traces with a server-model ACK: {n_ack}/{len(traces)}")
    if server_models:
        if len(server_models) == 1:
            lines.append(f"- server_model: **{next(iter(server_models))}** "
                         f"(single served model — identity confirmed)")
        else:
            lines.append(f"- server_model: **{len(server_models)} DISTINCT served models** (mixed arm!):")
            for m, c in server_models.most_common():
                lines.append(f"    [{c} traces] {m}")

    # Aggregate Summary with the per-cause failure breakdown and the correct denominator.
    matched = agg_summary["matched"]
    llm_tap = agg_summary["llm_tap"]
    no_match = agg_summary["no_match"]
    failures = agg_summary["failures"]
    decisions = matched + llm_tap + no_match + failures
    lines.append("\n## Aggregate Summary (all traces)\n")
    lines.append(f"- calls: {agg_summary['calls']}")
    lines.append(f"- matched: {matched}")
    lines.append(f"- llm_tap: {llm_tap}   (off-tree coordinate taps)")
    lines.append(f"- no_match: {no_match}")
    lines.append(f"- failures (abandoned before mapping): {failures}")
    if grammar_seen.get("new"):
        lines.append("    per-cause: " + " ".join(
            f"{c}={agg_summary[c]}" for c in FAILURE_CAUSES))
    if grammar_seen.get("old"):
        lines.append(f"    (old-grammar traces contribute an aggregate null={agg_summary['null']}; "
                     f"screenshot_failed is a subset of it)")
    lines.append(f"- breaker_trips: {agg_summary['breaker_trips']}")
    lines.append(f"- decisions (= matched+llm_tap+no_match+failures): {decisions}")
    if decisions:
        lines.append(f"- widget-match rate (matched/decisions): {matched * 100 / decisions:.1f}%")
        lines.append(f"- off-tree tap rate (llm_tap/decisions): {llm_tap * 100 / decisions:.1f}%")
    former_no_match = llm_tap + no_match
    if former_no_match:
        lines.append(
            f"- off-tree recovery (llm_tap / (llm_tap+no_match)): "
            f"{llm_tap * 100 / former_no_match:.1f}%  "
            f"(share of pre-change no_match now acted on)")

    # Per-decision failure causes from the [APE-LLM-ERROR] lines (finer than the summary).
    if error_causes:
        lines.append("\n### [APE-LLM-ERROR] cause breakdown (per-decision)\n")
        for cause, c in error_causes.most_common():
            lines.append(f"- cause={cause}: {c}")

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

    # --- Decision -> outcome attribution (the d90c1f4 three-way join) ---
    lines.append("\n## Decision→outcome attribution ([APE-OUTCOME] joined by step)\n")
    if not outcome_by_source:
        lines.append("No [APE-OUTCOME] lines found — pre-change traces (0.9.2) do not emit "
                     "them, so this attribution is unavailable for this arm.")
    else:
        lines.append("New-state discovery rate by decision source "
                     "(of executed actions with a recorded transition):\n")
        for src, (total, new) in sorted(outcome_by_source.items(),
                                        key=lambda kv: -kv[1][0]):
            rate = f"{new * 100 / total:.1f}%" if total else "n/a"
            lines.append(f"- {src}: {new}/{total} reached a new state ({rate})")
        lines.append(f"\nLLM decisions joined to an outcome by step: {n_joined}")
        new_tok = llm_cost_by_outcome["new_state"]["tokens_out"]
        same_tok = llm_cost_by_outcome["same_state"]["tokens_out"]
        new_ms = llm_cost_by_outcome["new_state"]["time_ms"]
        same_ms = llm_cost_by_outcome["same_state"]["time_ms"]
        if new_tok or same_tok:
            lines.append("\n### LLM call cost attributed to its outcome\n")
            if new_tok:
                lines.append(f"- new-state decisions:  n={len(new_tok)}  "
                             f"median tokens_out={median(new_tok):.0f}  "
                             f"median time_ms={median(new_ms):.0f}" if new_ms else
                             f"- new-state decisions:  n={len(new_tok)}  "
                             f"median tokens_out={median(new_tok):.0f}")
            if same_tok:
                lines.append(f"- same-state decisions: n={len(same_tok)}  "
                             f"median tokens_out={median(same_tok):.0f}  "
                             f"median time_ms={median(same_ms):.0f}" if same_ms else
                             f"- same-state decisions: n={len(same_tok)}  "
                             f"median tokens_out={median(same_tok):.0f}")

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


def _manifest_key(config: dict) -> str:
    """A compact, comparable string for the fields that define an arm (not the url)."""
    return " ".join(f"{f}={config.get(f)}" for f in (
        "model", "temperature", "top_p", "top_k", "max_tokens", "timeout_ms",
        "prompt_variant", "llm_percentage", "on_new_state", "on_stagnation",
        "stagnation_threshold"))


# --- self-test (no data required) ------------------------------------------------------
def selftest() -> int:
    """Prove the parser handles BOTH the pre-change and post-change telemetry formats and
    the three-way step join."""
    # --- Summary: old grammar (aggregate null) vs new grammar (per-cause) ---
    old_summary = ("[APE] [APE-RV] LLM Summary calls=98 tokens_in=112728 tokens_out=2262 "
                   "time_ms=75468 matched=66 no_match=21 null=11 screenshot_failed=3 "
                   "breaker_trips=1")
    new_summary = ("[APE] [APE-RV] LLM Summary calls=98 tokens_in=112728 tokens_out=2262 "
                   "time_ms=75468 matched=60 llm_tap=6 no_match=15 timeout=4 http_error=1 "
                   "conn_error=2 parse_error=1 image_error=0 internal_error=0 "
                   "screenshot_failed=3 breaker_trips=1")

    old = parse_summary(old_summary)
    assert old["grammar"] == "old"
    assert old["llm_tap"] == 0, "pre-change trace defaults llm_tap to 0"
    assert old["failures"] == 11, "old failures = aggregate null (screenshot ⊂ null)"
    # screenshot_failed present on the old line but MUST NOT add on top of null.
    assert old["decisions"] == 66 + 0 + 21 + 11 == 98, old["decisions"]

    new = parse_summary(new_summary)
    assert new["grammar"] == "new"
    assert new["llm_tap"] == 6, "post-change llm_tap is read"
    # failures = Σ(seven causes) = 4+1+2+1+0+0+3 = 11 — value-identical to the retired null.
    assert new["failures"] == 4 + 1 + 2 + 1 + 0 + 0 + 3 == 11, new["failures"]
    assert new["decisions"] == 60 + 6 + 15 + 11 == 92, new["decisions"]
    assert new["timeout"] == 4 and new["http_error"] == 1 and new["conn_error"] == 2

    # A new-grammar Summary with a nonzero cause but null ABSENT must NOT under-form the
    # denominator (the exact staleness bug the rewrite fixes).
    assert parse_summary(
        "[APE-RV] LLM Summary calls=10 matched=5 llm_tap=0 no_match=0 timeout=5 "
        "http_error=0 conn_error=0 parse_error=0 image_error=0 internal_error=0 "
        "screenshot_failed=0 breaker_trips=0")["decisions"] == 10

    # --- Config manifest + ACK ---
    cfg = parse_config(
        "[APE] [APE-LLM-CONFIG] model=Qwen/Qwen3-VL-4B-Instruct temperature=0.0 top_p=0.9 "
        "top_k=20 max_tokens=1024 timeout_ms=60000 prompt_variant=default "
        "llm_percentage=1.0 on_new_state=true on_stagnation=false stagnation_threshold=200 "
        "url=http://sglang:30000/v1")
    assert cfg["model"] == "Qwen/Qwen3-VL-4B-Instruct"
    assert cfg["max_tokens"] == "1024" and cfg["temperature"] == "0.0"
    assert cfg["llm_percentage"] == "1.0" and cfg["stagnation_threshold"] == "200"
    assert parse_ack("[APE] [APE-LLM-CONFIG-ACK] server_model=qwen3-vl-4b") == "qwen3-vl-4b"

    # --- Per-call TEL now carries step (join key); pre-change lacks it ---
    tel_new = parse_tel("[APE-LLM-TEL] step=42 mode=new-state action=click result=matched "
                        "tokens_in=1100 tokens_out=23 time_ms=1597")
    assert tel_new["step"] == 42 and tel_new["result"] == "matched"
    assert tel_new["tokens_out"] == 23 and tel_new["mode"] == "new-state"
    tel_old = parse_tel("[APE-LLM-TEL] call=1 action=click result=matched "
                        "nearest_dist=11.0 time_ms=1597")
    assert tel_old["step"] is None and tel_old["result"] == "matched", "pre-change TEL: no step"
    tel_deg = parse_tel("[APE-LLM-TEL] step=7 action=click result=no_match "
                        "reason=degenerate time_ms=1251")
    assert tel_deg["reason"] == "degenerate" and tel_deg["step"] == 7
    assert parse_tel("[APE-LLM-TEL] no result here") is None

    # --- [APE-LLM-ERROR] with a spaced detail message ---
    err = parse_error("[APE-LLM-ERROR] step=9 cause=http_500 detail=server returned 500")
    assert err["step"] == 9 and err["cause"] == "http_500"
    assert err["detail"] == "server returned 500", err["detail"]
    assert parse_error("[APE-LLM-ERROR] step=3 cause=timeout")["cause"] == "timeout"

    # --- [APE-STEP] / [APE-OUTCOME] and the three-way join ---
    st = parse_step("[APE-STEP] step=42 clock=1737000000000 activity=A state=S1 "
                    "action=MODEL_CLICK decision_source=LLM mop=0 wtg=0")
    assert st["step"] == 42 and st["decision_source"] == "LLM" and st["clock"] == 1737000000000
    oc = parse_outcome("[APE-OUTCOME] step=42 decision_source=LLM new_state=true "
                       "target_state=S7 activity_changed=false")
    assert oc["step"] == 42 and oc["new_state"] is True and oc["activity_changed"] is False
    assert oc["target_state"] == "S7"
    oc_false = parse_outcome("[APE-OUTCOME] step=43 decision_source=SATA new_state=false "
                             "target_state=S1 activity_changed=true")
    assert oc_false["new_state"] is False and oc_false["activity_changed"] is True
    assert parse_step("[APE-STEP] no step here") is None
    assert parse_outcome("[APE-OUTCOME] no step here") is None

    # --- End-to-end trace parse: one LLM new-state decision joins tel<->step<->outcome ---
    synthetic = "\n".join([
        "[APE-LLM-CONFIG] model=phtcosta/aperv-qwen3vl-4b-v2-merged temperature=0.0 top_p=0.9 "
        "top_k=20 max_tokens=1024 timeout_ms=60000 prompt_variant=default llm_percentage=1.0 "
        "on_new_state=true on_stagnation=false stagnation_threshold=200 url=http://x/v1",
        "[APE-STEP] step=42 clock=1 activity=A state=S1 action=MODEL_CLICK decision_source=LLM",
        "[APE-LLM-TEL] step=42 mode=new-state action=click result=matched tokens_in=1100 "
        "tokens_out=23 time_ms=1500",
        "[APE-LLM-CONFIG-ACK] server_model=aperv-v2",
        "[APE-OUTCOME] step=42 decision_source=LLM new_state=true target_state=S7 activity_changed=false",
        "[APE-STEP] step=43 clock=2 activity=A state=S7 action=MODEL_CLICK decision_source=SATA",
        "[APE-OUTCOME] step=43 decision_source=SATA new_state=false target_state=S7 activity_changed=false",
        "[APE-RV] LLM Summary calls=1 tokens_in=1100 tokens_out=23 time_ms=1500 matched=1 "
        "llm_tap=0 no_match=0 timeout=0 http_error=0 conn_error=0 parse_error=0 image_error=0 "
        "internal_error=0 screenshot_failed=0 breaker_trips=0",
    ])
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".trace", delete=True) as fh:
        fh.write(synthetic)
        fh.flush()
        p = parse_trace_file(Path(fh.name))
    assert p["config"]["model"] == "phtcosta/aperv-qwen3vl-4b-v2-merged"
    assert p["server_model"] == "aperv-v2"
    assert p["summary"]["grammar"] == "new" and p["summary"]["decisions"] == 1
    assert set(p["outcomes"]) == {42, 43}
    assert p["outcomes"][42]["new_state"] is True and p["outcomes"][42]["decision_source"] == "LLM"
    assert p["tel_by_step"][42]["tokens_out"] == 23
    # The LLM step joins tel<->outcome; the SATA step has an outcome but no TEL.
    assert 42 in p["tel_by_step"] and 43 not in p["tel_by_step"]

    print("selftest OK — parses [APE-LLM-CONFIG]/[APE-LLM-CONFIG-ACK]/[APE-STEP]/"
          "[APE-LLM-TEL]/[APE-LLM-ERROR]/[APE-OUTCOME]/Summary; backward-tolerant on "
          "0.9.2 traces (null → failures, no step); decisions denominator value-identical "
          "across grammars; three-way step join verified.")
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

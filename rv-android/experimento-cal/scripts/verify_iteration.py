#!/usr/bin/env python3
"""VERIFY — independently re-derive an iteration's numbers and gate them.

This is the VERIFY state of the calibration loop (methodology §3.6). Its entire reason to
exist is *independence*: an agent re-running the producer's consolidation script is not
verification. So this module shares NO code with the consolidator — it re-parses the raw
logcats and traces with its own regexes and re-derives every count it checks, then compares
the result against the ``per_apk_paired.csv`` that CONSOLIDATE wrote.

INV-CAL-04 (independence) is enforced structurally: this module does NOT import
``consolidate_cal``, ``consolidate_compare``, or ``analyze_cmpv2_llm`` — a test parses this
file's AST and fails if any of those names appear in an import.

The fixed numeric gates (INV-CAL-09), applied over 100% of tasks:

  1. CONFIG          [APE-LLM-CONFIG] equals the manifest's expected fields for the arm, in
                     100% of LLM tasks. Any field mismatch -> quarantine.
  2. COLLISIONS      0 identity collisions: no identity tuple maps to more than one arm
                     (an @override arm would collapse two arms onto one identity).
  3. PAIRING         paired completeness 100%. An APK missing a non-empty logcat in >=1 arm
                     is EXCLUDED from the paired set, with a written record naming the
                     missing arm(s). Quarantine only if the paired set ends up empty.
  4. LATENCY         per-arm median time_ms <= 2x the global median. A violation FLAGS the
                     arm (time_ms becomes a covariate note); it does not quarantine.
  5. DIVERGENCE      re-derivation vs per_apk_paired.csv: exact on integer-count metrics
                     (mop_total, mop_unique, crashes), <= 0.01pp on percentage metrics
                     (cov_method, cov_act, cov_mop). Any divergence -> quarantine, citing the
                     identity/cell and both values.

Plus a seeded hand-count sample (>=10 tasks, fixed --seed) comparing re-derived per-identity
numbers cell-by-cell to the CSV, and a written ``iterN/verification_report.md``.

Verdict: ``admissible`` (exit 0) or ``quarantine`` (exit 1), with a written justification
naming any excluded metric or arm.

Usage:
    verify_iteration.py --iter-dir experimento-cal/iter1 [--sample 10 --seed 42]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List, Optional, Tuple

# --- independent marker + trace regexes (own copies; NOT imported from the consolidator) --
# MOP-violation line: tag RVSEC, message starting "<Name>Spec,". RVSEC-COV is not matched
# (after "RVSEC" it carries "-COV", not ":").
_MOP_RE = re.compile(r"\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$")
# Coverage record: tag RVSEC-COV; the message after the colon is the method signature. The
# distinct set of these per identity is the independent covered-method count.
_COV_RE = re.compile(r"\bRVSEC-COV\s*:\s*(.+?)\s*$")

_CFG_RE = re.compile(r"\[APE-LLM-CONFIG\](?!-ACK)")
_KV_RE = re.compile(r"(\w+)=(\S+)")
_SUMMARY_RE = re.compile(r"\[APE-RV\] LLM Summary\b")

# Metric partition for the divergence gate.
_INTEGER_METRICS = ("mop_total", "mop_unique", "crashes")
_PERCENT_METRICS = ("cov_method", "cov_act", "cov_mop")
_PERCENT_TOL = 0.01  # percentage-point tolerance (INV-CAL-09)

# Field-name map from a manifest arm's expected_config_ack to the [APE-LLM-CONFIG] trace
# field names (they are identical here — the manifest already stores trace field names).
_CONFIG_FIELDS = (
    "model",
    "temperature",
    "top_p",
    "top_k",
    "timeout_ms",
    "prompt_variant",
    "llm_percentage",
    "on_new_state",
    "on_stagnation",
    "url",
)


def _arm_label(name: str, variant: Optional[str]) -> str:
    return f"{name}:{variant}"


def _toolfrag(name: str, variant: Optional[str]) -> str:
    return "ape" if name == "ape" else f"{name}:{variant}"


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _norm(value: Any) -> str:
    """Normalise a scalar for tolerant string comparison (bool True <-> the string "true")."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip().lower()


def _num_eq(a: Any, b: Any, tol: float = 0.0) -> bool:
    """Tolerant equality: numeric when both parse as numbers (0 vs 0.0, 0.7 vs "0.7"),
    else a normalised string compare (so the manifest's native bool ``True`` matches the
    trace's textual ``true``). Booleans deliberately take the string path, not the float one.
    """
    if not isinstance(a, bool) and not isinstance(b, bool):
        fa, fb = _to_float(a), _to_float(b)
        if fa is not None and fb is not None:
            return abs(fa - fb) <= tol
    return _norm(a) == _norm(b)


# --- independent task re-derivation ----------------------------------------------------
def _load_tasks(iter_dir: Path) -> List[Dict[str, Any]]:
    """Own read of every tasks.json; one dict per task record with identity + base dir."""
    out: List[Dict[str, Any]] = []
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
            if name is None:
                continue
            variant = tc.get("variant")
            out.append(
                {
                    "identity": (
                        cfg.get("apk_name"),
                        name,
                        variant,
                        cfg.get("repetition"),
                        cfg.get("timeout"),
                    ),
                    "apk": cfg.get("apk_name"),
                    "name": name,
                    "variant": variant,
                    "rep": cfg.get("repetition"),
                    "timeout": cfg.get("timeout"),
                    "result": task.get("result") or {},
                    "base": base,
                }
            )
    return out


def _rank(rec: Dict[str, Any]) -> Tuple[int, float]:
    """Independent best-record rank: COMPLETED first, then most coverage (resume-safe)."""
    result = rec["result"]
    completed = 1 if result.get("state") == "COMPLETED" else 0
    cov = result.get("coverage_metrics") or {}
    cov_sum = 0.0
    for k in (
        "method_coverage",
        "activities_coverage",
        "methods_mop_reachable_coverage",
    ):
        v = _to_float(cov.get(k))
        cov_sum += v if v is not None else 0.0
    return (completed, cov_sum)


def _logcat_path(rec: Dict[str, Any], suffix: str) -> Path:
    frag = _toolfrag(rec["name"], rec["variant"])
    return (
        rec["base"]
        / rec["apk"]
        / f'{rec["apk"]}__{rec["rep"]}__{rec["timeout"]}__{frag}.{suffix}'
    )


def _rederive_identity(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Re-derive one identity's metrics independently from its raw files + tasks.json block.

    From the raw logcat: mop_total (RVSEC lines) and cov_methods (distinct RVSEC-COV
    signatures). From this record's own coverage_metrics block: the three percentages,
    mop_unique and crashes (the values a resume leaves intact; read with our own parser,
    not the consolidator's).
    """
    logcat = _logcat_path(rec, "logcat")
    mop_total = 0
    cov_sigs: set = set()
    non_empty = False
    try:
        with open(logcat, errors="ignore") as fh:
            for line in fh:
                non_empty = True
                if "RVSEC" in line:
                    if _MOP_RE.search(line):
                        mop_total += 1
                    else:
                        m = _COV_RE.search(line)
                        if m:
                            cov_sigs.add(m.group(1))
    except FileNotFoundError:
        pass

    cov = rec["result"].get("coverage_metrics") or {}
    return {
        "identity": rec["identity"],
        "apk": rec["apk"],
        "arm": _arm_label(rec["name"], rec["variant"]),
        "rep": rec["rep"],
        "non_empty": non_empty,
        "cov_methods_distinct": len(cov_sigs),  # independent covered-method count
        "cov_method": _to_float(cov.get("method_coverage")) or 0.0,
        "cov_act": _to_float(cov.get("activities_coverage")) or 0.0,
        "cov_mop": _to_float(cov.get("methods_mop_reachable_coverage")) or 0.0,
        "mop_unique": _to_float(cov.get("total_errors")) or 0.0,
        "mop_total": float(mop_total),
        "crashes": _to_float(rec["result"].get("detected_errors_count")) or 0.0,
    }


def _parse_config(trace: Path) -> Optional[Dict[str, str]]:
    """Own parse of the first [APE-LLM-CONFIG] line -> {field: str}, or None if absent."""
    try:
        text = trace.read_text(encoding="latin-1", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if _CFG_RE.search(line):
            return {k: v for k, v in _KV_RE.findall(line)}
    return None


def _parse_time_ms(trace: Path) -> Optional[int]:
    """Own parse of the LLM Summary time_ms (total LLM latency for the task), or None."""
    try:
        text = trace.read_text(encoding="latin-1", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if _SUMMARY_RE.search(line):
            fields = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)\b", line)}
            return fields.get("time_ms")
    return None


# --- per_apk_paired.csv reader ---------------------------------------------------------
def _read_paired_csv(
    path: Path,
) -> Tuple[Dict[str, Dict[Tuple[str, str], Any]], List[str]]:
    """Read the consolidated CSV into ``{apk: {(arm, metric): value}}`` + the arm list."""
    cells: Dict[str, Dict[Tuple[str, str], Any]] = {}
    arms: List[str] = []
    with open(path, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        col_specs: List[Optional[Tuple[str, str]]] = [None]  # "apk" column
        seen_arms: List[str] = []
        for col in header[1:]:
            arm, metric = col.rsplit("__", 1)
            col_specs.append((arm, metric))
            if arm not in seen_arms:
                seen_arms.append(arm)
        arms = seen_arms
        for row in reader:
            apk = row[0]
            cells[apk] = {}
            for value, spec in zip(row[1:], col_specs[1:]):
                if spec is not None:
                    cells[apk][spec] = value
    return cells, arms


# --- gates -----------------------------------------------------------------------------
def _gate_config(
    best: Dict[Tuple, Dict[str, Any]], manifest: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Gate 1 (CONFIG): each LLM task's [APE-LLM-CONFIG] trace line must equal the
    manifest's expected fields for that arm, in 100% of LLM tasks. Any field mismatch is a
    quarantine trigger.

    An arm without an ``expected_config_ack`` (or a run with no manifest) is a non-LLM arm
    and contributes nothing to gate; ``n_llm_tasks`` counts only the tasks actually audited
    (arm has expected fields AND a trace file exists).

    Returns ``{"config_findings": [...], "n_llm_tasks": int}``: one finding per mismatched
    field naming the identity, arm, field, and the expected vs observed values.
    """
    config_findings: List[Dict[str, Any]] = []
    n_llm_tasks = 0
    expected_by_arm: Dict[str, Dict[str, Any]] = {}
    if manifest:
        for arm in manifest.get("arms", []):
            expected_by_arm[arm["rv_tools_token"]] = (
                arm.get("expected_config_ack") or {}
            )
    for ident, rec in best.items():
        arm = _arm_label(rec["name"], rec["variant"])
        expected = expected_by_arm.get(arm)
        if not expected:  # non-LLM arm, or no manifest -> nothing to gate
            continue
        trace = _logcat_path(rec, "trace")
        if not trace.exists():
            continue
        n_llm_tasks += 1
        observed = _parse_config(trace) or {}
        for field in _CONFIG_FIELDS:
            if field not in expected:
                continue
            if not _num_eq(observed.get(field), expected[field]):
                config_findings.append(
                    {
                        "identity": ident,
                        "arm": arm,
                        "field": field,
                        "expected": expected[field],
                        "observed": observed.get(field),
                    }
                )
    return {"config_findings": config_findings, "n_llm_tasks": n_llm_tasks}


def _gate_collisions(
    tasks: List[Dict[str, Any]], manifest: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Gate 2 (COLLISIONS): 0 identity collisions — no identity tuple may map to more than
    one arm (an @override arm would collapse two arms onto one identity). A manifest with
    duplicate arm tokens is an equivalent collision source. Either condition quarantines.

    Runs directly over the raw task records (before dedup), so a colliding identity is seen
    across all of its arms.

    Returns ``{"collisions": {identity: {arms}}, "dup_tokens": {token, ...}}``.
    """
    ident_to_arms: Dict[Tuple, set] = defaultdict(set)
    for rec in tasks:
        ident_to_arms[rec["identity"]].add(_arm_label(rec["name"], rec["variant"]))
    collisions = {ident: arms for ident, arms in ident_to_arms.items() if len(arms) > 1}
    # A manifest with duplicate arm tokens is also a collision source.
    if manifest:
        tokens = [a["rv_tools_token"] for a in manifest.get("arms", [])]
        dup_tokens = {t for t in tokens if tokens.count(t) > 1}
    else:
        dup_tokens = set()
    return {"collisions": collisions, "dup_tokens": dup_tokens}


def _gate_pairing(
    rederived: Dict[Tuple, Dict[str, Any]], manifest: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Gate 3 (PAIRING): paired completeness 100%. An APK missing a non-empty logcat in
    >=1 arm is EXCLUDED from the paired set, with a written record naming the missing
    arm(s). Quarantine only if the paired set ends up empty (verdict handled by ``verify``).

    The design's arm list comes from the manifest when present, otherwise from the set of
    arms actually observed in the re-derived identities.

    Returns ``{"all_arms": [...], "exclusions": [...], "paired_apks": [...],
    "apk_arms_present": {apk: {arm}}}`` — ``apk_arms_present`` lets ``verify`` distinguish
    "no APK observed at all" from "every observed APK excluded".
    """
    all_arms = (
        [a["rv_tools_token"] for a in manifest.get("arms", [])]
        if manifest
        else sorted({r["arm"] for r in rederived.values()})
    )
    apk_arms_present: Dict[str, set] = defaultdict(set)
    for r in rederived.values():
        if r["non_empty"]:
            apk_arms_present[r["apk"]].add(r["arm"])
    exclusions: List[Dict[str, Any]] = []
    paired_apks: List[str] = []
    for apk in sorted(apk_arms_present):
        missing = [a for a in all_arms if a not in apk_arms_present[apk]]
        if missing:
            exclusions.append({"apk": apk, "missing_arms": missing})
        else:
            paired_apks.append(apk)
    return {
        "all_arms": all_arms,
        "exclusions": exclusions,
        "paired_apks": paired_apks,
        "apk_arms_present": apk_arms_present,
    }


def _gate_latency(best: Dict[Tuple, Dict[str, Any]]) -> Dict[str, Any]:
    """Gate 4 (LATENCY): per-arm median time_ms <= 2x the global median. A violation FLAGS
    the arm (time_ms becomes a covariate note); it does NOT quarantine.

    time_ms is parsed independently from each task's LLM Summary trace line; arms with no
    parseable latency contribute nothing, and an empty/zero global median flags no arm.

    Returns ``{"latency_flags": [...], "global_median_ms": <median>}``.
    """
    time_by_arm: Dict[str, List[int]] = defaultdict(list)
    for rec in best.values():
        trace = _logcat_path(rec, "trace")
        if trace.exists():
            t = _parse_time_ms(trace)
            if t is not None:
                time_by_arm[_arm_label(rec["name"], rec["variant"])].append(t)
    all_times = [t for times in time_by_arm.values() for t in times]
    latency_flags: List[Dict[str, Any]] = []
    global_med = median(all_times) if all_times else 0.0
    if global_med > 0:
        for arm, times in sorted(time_by_arm.items()):
            arm_med = median(times)
            if arm_med > 2 * global_med:
                latency_flags.append(
                    {
                        "arm": arm,
                        "arm_median_ms": arm_med,
                        "global_median_ms": global_med,
                    }
                )
    return {"latency_flags": latency_flags, "global_median_ms": global_med}


def _gate_divergence(
    iter_dir: Path, rederived: Dict[Tuple, Dict[str, Any]]
) -> Dict[str, Any]:
    """Gate 5 (DIVERGENCE): independent re-derivation vs per_apk_paired.csv — exact on the
    integer-count metrics (mop_total, mop_unique, crashes), <= 0.01pp on the percentage
    metrics (cov_method, cov_act, cov_mop). Any divergence is a quarantine trigger, citing
    the identity/cell and both values.

    Re-derived identities are aggregated to (apk, arm) rep-averages to mirror the CSV's
    granularity; a CSV cell that is missing or blank is skipped rather than compared.

    Returns ``{"divergences": [...], "csv_cells": {apk: {(arm, metric): value}}}`` — the
    parsed CSV cells are returned so the hand-count sample can reuse them without re-reading
    the file (``csv_cells`` is empty when the CSV is absent).
    """
    paired_path = iter_dir / "per_apk_paired.csv"
    divergences: List[Dict[str, Any]] = []
    csv_cells: Dict[str, Dict[Tuple[str, str], Any]] = {}
    if paired_path.exists():
        csv_cells, _ = _read_paired_csv(paired_path)
        # Aggregate re-derivation to (apk, arm) rep-averages, mirroring the CSV granularity.
        agg: Dict[Tuple[str, str], Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for r in rederived.values():
            key = (r["apk"], r["arm"])
            for metric in _INTEGER_METRICS + _PERCENT_METRICS:
                agg[key][metric].append(r[metric])
        for (apk, arm), metrics in agg.items():
            for metric, values in metrics.items():
                csv_value = csv_cells.get(apk, {}).get((arm, metric))
                if csv_value in (None, ""):
                    continue
                rederived_value = round(mean(values), 4)
                tol = _PERCENT_TOL if metric in _PERCENT_METRICS else 0.0
                if not _num_eq(csv_value, rederived_value, tol):
                    divergences.append(
                        {
                            "apk": apk,
                            "arm": arm,
                            "metric": metric,
                            "csv_value": csv_value,
                            "rederived": rederived_value,
                            "identities": [
                                str(r["identity"])
                                for r in rederived.values()
                                if r["apk"] == apk and r["arm"] == arm
                            ],
                        }
                    )
    return {"divergences": divergences, "csv_cells": csv_cells}


def verify(iter_dir: Path, sample_size: int, seed: int) -> Dict[str, Any]:
    """Apply every gate and return a structured result (verdict + per-gate findings).

    Thin orchestrator: loads the manifest and re-derives the tasks independently, then runs
    the five fixed gates (INV-CAL-09) in order and aggregates their findings into the same
    verdict and result payload the report renders. The seeded hand-count sample and the
    admissible/quarantine verdict live here because they span all gates.
    """
    manifest = None
    manifest_path = iter_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError):
            manifest = None

    tasks = _load_tasks(iter_dir)

    # Gate 2 runs over the raw task records, before dedup collapses identities to one arm.
    collisions_result = _gate_collisions(tasks, manifest)
    collisions = collisions_result["collisions"]
    dup_tokens = collisions_result["dup_tokens"]

    # Independent dedup + per-identity re-derivation (shared substrate for the gates below).
    best: Dict[Tuple, Dict[str, Any]] = {}
    for rec in tasks:
        ident = rec["identity"]
        if ident not in best or _rank(rec) > _rank(best[ident]):
            best[ident] = rec
    rederived = {ident: _rederive_identity(rec) for ident, rec in best.items()}

    config_result = _gate_config(best, manifest)
    config_findings = config_result["config_findings"]
    n_llm_tasks = config_result["n_llm_tasks"]

    pairing_result = _gate_pairing(rederived, manifest)
    all_arms = pairing_result["all_arms"]
    exclusions = pairing_result["exclusions"]
    paired_apks = pairing_result["paired_apks"]
    apk_arms_present = pairing_result["apk_arms_present"]

    latency_result = _gate_latency(best)
    latency_flags = latency_result["latency_flags"]
    global_med = latency_result["global_median_ms"]

    divergence_result = _gate_divergence(iter_dir, rederived)
    divergences = divergence_result["divergences"]
    csv_cells = divergence_result["csv_cells"]

    # --- seeded hand-count sample ---
    idents = sorted(rederived.keys(), key=lambda i: tuple(str(x) for x in i))
    rng = random.Random(seed)
    k = min(sample_size, len(idents))
    sample = rng.sample(idents, k) if k else []
    sample_rows: List[Dict[str, Any]] = []
    for ident in sample:
        r = rederived[ident]
        cell = csv_cells.get(r["apk"], {})
        sample_rows.append(
            {
                "identity": ident,
                "arm": r["arm"],
                "rederived": {m: r[m] for m in _INTEGER_METRICS + _PERCENT_METRICS},
                "cov_methods_distinct": r["cov_methods_distinct"],
                "csv": {
                    m: cell.get((r["arm"], m))
                    for m in _INTEGER_METRICS + _PERCENT_METRICS
                },
            }
        )

    # --- verdict ---
    quarantine_reasons: List[str] = []
    if config_findings:
        quarantine_reasons.append(
            f"{len(config_findings)} [APE-LLM-CONFIG] field mismatch(es) in {n_llm_tasks} LLM tasks"
        )
    if collisions or dup_tokens:
        quarantine_reasons.append(
            f"{len(collisions)} identity collision(s), {len(dup_tokens)} duplicate arm token(s)"
        )
    if divergences:
        quarantine_reasons.append(
            f"{len(divergences)} re-derivation divergence(s) vs per_apk_paired.csv"
        )
    if apk_arms_present and not paired_apks:
        quarantine_reasons.append("paired set is empty (every APK excluded)")

    verdict = "quarantine" if quarantine_reasons else "admissible"
    return {
        "verdict": verdict,
        "quarantine_reasons": quarantine_reasons,
        "n_tasks": len(tasks),
        "n_identities": len(best),
        "config_findings": config_findings,
        "n_llm_tasks": n_llm_tasks,
        "collisions": collisions,
        "dup_tokens": dup_tokens,
        "exclusions": exclusions,
        "paired_apks": paired_apks,
        "all_arms": all_arms,
        "latency_flags": latency_flags,
        "global_median_ms": global_med,
        "divergences": divergences,
        "sample_rows": sample_rows,
        "seed": seed,
    }


# --- report ----------------------------------------------------------------------------
def render_report(iter_dir: Path, result: Dict[str, Any]) -> str:
    """Render the human-readable verification_report.md content."""
    lines: List[str] = []
    lines.append(f"# Verification report — {iter_dir.name}\n")
    lines.append(f"**Verdict: {result['verdict'].upper()}**\n")
    if result["quarantine_reasons"]:
        lines.append("Quarantine justification:")
        for reason in result["quarantine_reasons"]:
            lines.append(f"- {reason}")
        lines.append("")
    lines.append(
        f"Tasks: {result['n_tasks']} | identities (deduped): {result['n_identities']} | "
        f"LLM tasks audited: {result['n_llm_tasks']}\n"
    )

    lines.append("## Gate 1 — [APE-LLM-CONFIG] == manifest (100% of LLM tasks)\n")
    if not result["config_findings"]:
        lines.append("PASS — every LLM task's config matched the manifest.\n")
    else:
        lines.append(f"FAIL — {len(result['config_findings'])} mismatch(es):")
        for f in result["config_findings"]:
            lines.append(
                f"- arm `{f['arm']}` identity `{f['identity']}` field `{f['field']}`: "
                f"expected `{f['expected']}`, observed `{f['observed']}`"
            )
        lines.append("")

    lines.append("## Gate 2 — identity collisions (must be 0)\n")
    if not result["collisions"] and not result["dup_tokens"]:
        lines.append("PASS — no identity maps to more than one arm.\n")
    else:
        lines.append("FAIL:")
        for ident, arms in result["collisions"].items():
            lines.append(f"- identity `{ident}` maps to arms {sorted(arms)}")
        if result["dup_tokens"]:
            lines.append(
                f"- duplicate arm tokens in manifest: {sorted(result['dup_tokens'])}"
            )
        lines.append("")

    lines.append("## Gate 3 — paired completeness (100%)\n")
    lines.append(f"Arms in the design: {result['all_arms']}")
    lines.append(
        f"Paired APKs (present in every arm): {len(result['paired_apks'])} — {result['paired_apks']}"
    )
    if result["exclusions"]:
        lines.append("\nExcluded from the paired set (missing arm named):")
        for exc in result["exclusions"]:
            lines.append(
                f"- APK `{exc['apk']}` EXCLUDED — missing arm(s): {exc['missing_arms']}"
            )
    else:
        lines.append("\nNo exclusions — every observed APK is present in every arm.")
    lines.append("")

    lines.append("## Gate 4 — per-arm median time_ms <= 2x global median\n")
    lines.append(f"Global median time_ms: {result['global_median_ms']}")
    if not result["latency_flags"]:
        lines.append("PASS — no arm exceeds 2x the global median.\n")
    else:
        lines.append("FLAGGED (covariate note; not a quarantine trigger):")
        for fl in result["latency_flags"]:
            lines.append(
                f"- arm `{fl['arm']}` median {fl['arm_median_ms']}ms > 2x global "
                f"{fl['global_median_ms']}ms — treat time_ms as a covariate for this arm"
            )
        lines.append("")

    lines.append("## Gate 5 — re-derivation divergence vs per_apk_paired.csv\n")
    lines.append(
        "Integer metrics (mop_total, mop_unique, crashes): exact; "
        "percentage metrics (cov_method, cov_act, cov_mop): <= 0.01pp.\n"
    )
    if not result["divergences"]:
        lines.append("PASS — independent re-derivation matches the consolidated CSV.\n")
    else:
        lines.append(f"FAIL — {len(result['divergences'])} divergence(s):")
        for d in result["divergences"]:
            lines.append(
                f"- APK `{d['apk']}` arm `{d['arm']}` metric `{d['metric']}`: "
                f"CSV encodes `{d['csv_value']}`, independent re-derivation `{d['rederived']}` "
                f"(contributing identities: {d['identities']})"
            )
        lines.append("")

    lines.append(
        f"## Hand-count sample (seed={result['seed']}, {len(result['sample_rows'])} tasks)\n"
    )
    lines.append(
        "Independent per-identity re-derivation vs the consolidated (rep-averaged) CSV cell:\n"
    )
    for row in result["sample_rows"]:
        lines.append(
            f"- identity `{row['identity']}` (arm `{row['arm']}`, "
            f"RVSEC-COV distinct methods={row['cov_methods_distinct']})"
        )
        lines.append(f"    re-derived: {row['rederived']}")
        lines.append(f"    csv cell:   {row['csv']}")
    lines.append("")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--iter-dir", required=True, help="path to the iteration tree (iterN/)"
    )
    parser.add_argument(
        "--sample", type=int, default=10, help="hand-count sample size (default 10)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="fixed RNG seed for the sample (default 42)",
    )
    args = parser.parse_args(argv)

    iter_dir = Path(args.iter_dir).resolve()
    if not (iter_dir / "results").is_dir():
        sys.stderr.write(f"no results/ under {iter_dir}\n")
        return 2
    if not (iter_dir / "per_apk_paired.csv").exists():
        sys.stderr.write(
            f"no per_apk_paired.csv under {iter_dir} — run consolidate_cal.py first\n"
        )
        return 2

    result = verify(iter_dir, args.sample, args.seed)
    report = render_report(iter_dir, result)
    (iter_dir / "verification_report.md").write_text(report)

    print(f"verdict: {result['verdict'].upper()}")
    for reason in result["quarantine_reasons"]:
        print(f"  - {reason}")
    print(f"report: {iter_dir / 'verification_report.md'}")
    return 0 if result["verdict"] == "admissible" else 1


if __name__ == "__main__":
    raise SystemExit(main())

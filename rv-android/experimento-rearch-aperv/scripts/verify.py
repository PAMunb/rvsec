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

  1. CONFIG          RUN_START's preset and params equal what the manifest declared for the
                     arm, in 100% of tasks. Any mismatch -> quarantine.
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
  6. INTEGRITY       every identity admissible under six criteria (C1-C6 below), judged
                     before any aggregation and blind to which arm it is judging. Any
                     inadmissible identity, or a count that misses the manifest's
                     `predicted_identities`, quarantines.

Gate 6 exists because `COMPLETED` is a claim the harness makes, not one anything checked.
Two runs of the gh97 leg B campaign returned early — one at 1284 s of an 1800 s budget when
the emulator died, one at 1012 s when APE-RV stopped on its own — and both were stored
`COMPLETED` with `error_message` null. Gates 1-5 all pass on such a run: `_rank` puts
`COMPLETED` first and the pairing gate asks only that a logcat be non-empty, which a run
truncated at 68 % of its budget amply satisfies. Nothing above reads duration.

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

from aperv_tool.analysis import trace_ndjson

# --- independent marker + trace regexes (own copies; NOT imported from the consolidator) --
# MOP-violation line: tag RVSEC, message starting "<Name>Spec,". RVSEC-COV is not matched
# (after "RVSEC" it carries "-COV", not ":").
_MOP_RE = re.compile(r"\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$")
# Coverage record: tag RVSEC-COV; the message after the colon is the method signature. The
# distinct set of these per identity is the independent covered-method count.
_COV_RE = re.compile(r"\bRVSEC-COV\s*:\s*(.+?)\s*$")

# Metric partition for the divergence gate.
_INTEGER_METRICS = ("mop_total", "mop_unique", "crashes")
_PERCENT_METRICS = ("cov_method", "cov_act", "cov_mop")
_PERCENT_TOL = 0.01  # percentage-point tolerance (INV-CAL-09)

# Gate 6's floor on distinct RVSEC-COV signatures (C4). It is 1 and it stays 1: a structural
# floor asks whether the application executed any instrumented method at all, which is a
# question about whether the run happened. Any higher number is one somebody chose, and
# choosing it against this campaign's own distribution is precisely what a pre-registration
# exists to prevent. The observed distribution is reported instead, so a later change can
# calibrate a floor on evidence it is not simultaneously reading the result of.
_COV_SIGNATURE_FLOOR = 1

# The six admissibility criteria, in the order they are applied and reported. Kept as data
# so the report, the per-criterion tally and repair_tasks.py all name them identically.
ADMISSIBILITY_CRITERIA = {
    "C1": "state == COMPLETED with an empty error_message",
    "C2": "execution_time_seconds >= timeout",
    "C3": "the trace carries at least one step beyond RUN_START",
    "C4": f"at least {_COV_SIGNATURE_FLOOR} distinct RVSEC-COV signature in the logcat",
    "C5": "cov_method > 0 and cov_act > 0",
    "C6": "admissible identities == the manifest's predicted_identities",
}

# The manifest declares each arm as `preset` plus `expected_params`, keyed by the jar's own
# `ape.*` names — the same shape `RUN_START.params` reports, so the gate compares like with
# like and no field-name map is needed. The manifest is generated from the tool's variant
# definitions rather than transcribed (see scripts/make_manifest.py), because a hand-copied
# expectation checks the transcription and not the run.


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
        for index, task in enumerate(payload.get("tasks", [])):
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
                    # Where this record physically lives. repair_tasks.py rewrites a record
                    # in place, so it needs the file and the position within it; a resume
                    # APPENDS rather than overwrites, so position is the only thing that
                    # distinguishes two records of the same identity.
                    "tasks_json": tasks_json,
                    "index": index,
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


def artifact_path(rec: Dict[str, Any], suffix: str) -> Path:
    """Path to one of a run's artifacts — `logcat`, `trace` or `trace.ndjson.gz`.

    Public because `repair_tasks.py` preserves those three before it rewrites a record,
    and it must locate them exactly as the gate that condemned them did.
    """
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
    logcat = artifact_path(rec, "logcat")
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


def _trace_has_steps(trace: Path) -> bool:
    """True when the trace carries at least one exploration step beyond `RUN_START` (C3).

    Read through `aperv_tool.analysis.trace_ndjson`, the sanctioned reader of the format:
    step records key their timestamp on `t` and carry no `type`, so a scan looking for a
    record type would misclassify every one of them. A missing or unreadable trace is a
    failure of the criterion, not a skip — a run that recorded no steps is exactly what
    this asks about.
    """
    try:
        reader = trace_ndjson.TraceReader(trace)
    except OSError:
        return False
    try:
        for _step in reader:
            return True
    except OSError:
        return False
    return False


# --- admissibility (Gate 6) -------------------------------------------------------------
def admissibility_failures(
    rec: Dict[str, Any], rederived: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """The criteria this record fails, in C1..C5 order. An empty list means admissible.

    C6 is deliberately absent: it compares a campaign-wide count against the manifest and
    has no meaning for a single record. `_gate_integrity` applies it over the whole set.

    The criteria are **blind to the arm and to the direction of the effect** — nothing here
    reads `variant`, and none of the thresholds was derived from the numbers being judged.
    An admissibility rule that could see which arm it was judging would be able to prune one
    side of the comparison, which is the failure the whole gate exists to prevent.

    `rederived` is accepted so a caller that has already re-derived this identity does not
    pay for a second pass over the same logcat; when omitted it is computed here, which is
    what makes the predicate usable on its own by `repair_tasks.py`.
    """
    if rederived is None:
        rederived = _rederive_identity(rec)

    failures: List[Dict[str, Any]] = []
    result = rec["result"]

    # C1 — what already failed declaredly. An empty error_message is part of the criterion:
    # a COMPLETED record carrying a message is a contradiction worth surfacing.
    state = result.get("state")
    error_message = result.get("error_message")
    if state != "COMPLETED" or error_message:
        failures.append(
            {
                "criterion": "C1",
                "detail": f"state={state!r}, error_message={error_message!r}",
            }
        )

    # C2 — the truncated run. The exploration is budget-bound by construction, so a run
    # that returned before its budget did not do the work, whatever ended it. The exit code
    # cannot say this: APE-RV exits non-zero when it detects an application crash during
    # exploration, so a dead emulator and a crashing application look identical through it.
    elapsed = _to_float(result.get("execution_time_seconds"))
    timeout = _to_float(rec["timeout"])
    if elapsed is None or timeout is None or elapsed < timeout:
        failures.append(
            {
                "criterion": "C2",
                "detail": f"execution_time_seconds={elapsed} < timeout={timeout}",
            }
        )

    # C3 — the silent startup crash. `_check_empty_trace` in the tool already detects this
    # and downgrades it to a warning, so the signal was being produced and discarded.
    if not _trace_has_steps(artifact_path(rec, "trace")):
        failures.append(
            {"criterion": "C3", "detail": "trace carries no step beyond RUN_START"}
        )

    # C4 — an application that never launched. Structural floor of 1; see _COV_SIGNATURE_FLOOR.
    signatures = rederived["cov_methods_distinct"]
    if signatures < _COV_SIGNATURE_FLOOR:
        failures.append(
            {
                "criterion": "C4",
                "detail": f"{signatures} distinct RVSEC-COV signature(s)",
            }
        )

    # C5 — the deliberately zeroed coverage row. rv-platform emits one when a logcat is
    # present but its static-analysis JSON cannot be resolved (INV-PLT-16), which is
    # designed behaviour that would otherwise pass as a valid task carrying zero coverage.
    if rederived["cov_method"] <= 0 or rederived["cov_act"] <= 0:
        failures.append(
            {
                "criterion": "C5",
                "detail": (
                    f"cov_method={rederived['cov_method']}, "
                    f"cov_act={rederived['cov_act']}"
                ),
            }
        )

    return failures


def admissibility_by_identity(iter_dir: Path) -> Dict[Tuple, Dict[str, Any]]:
    """Best record per identity plus the criteria it fails — the scan `repair_tasks.py` runs.

    Deduping to the best record first is not a detail: a resume **appends** a task record
    rather than overwriting the failed one, so judging records instead of identities
    double-counts every recovery. During the leg B campaign that arithmetic turned 3
    outstanding tasks into an apparent 8.

    Lives here rather than in `repair_tasks.py` so there is one derivation of admissibility
    and the repair imports it, never the reverse. INV-CAL-04 forbids this module sharing
    derivation with the *consolidator*; a repair tool downstream of it does not touch that.
    """
    best: Dict[Tuple, Dict[str, Any]] = {}
    for rec in _load_tasks(iter_dir):
        ident = rec["identity"]
        if ident not in best or _rank(rec) > _rank(best[ident]):
            best[ident] = rec
    return {
        ident: {"record": rec, "failures": admissibility_failures(rec)}
        for ident, rec in best.items()
    }


def _parse_config(trace: Path) -> Optional[Dict[str, Any]]:
    """Own read of the trace's `RUN_START` record, or None if the trace has none.

    Read as the first line, with `json.loads`, rather than through
    `aperv_tool.analysis.trace_ndjson`. Not a shortcut: that reader keeps `run_id`, `t0`
    and `params` and drops `preset`, `build` and `corpus_basis`, which are three of the
    four fields this gate exists to check. Reading the line directly is also what the
    campaign's pre-flight does, for the same reason (design D7).

    `params` carries the jar's own `ape.*` names with typed values, and holds only what
    someone chose plus the activation key of every active feature — a default that was
    never overridden is absent by design, not missing.
    """
    try:
        with open(trace, encoding="utf-8", errors="replace") as handle:
            first = handle.readline()
    except OSError:
        return None
    if not first.startswith("{"):
        return None
    try:
        record = json.loads(first)
    except json.JSONDecodeError:
        return None
    return record if record.get("type") == "RUN_START" else None


def _parse_time_ms(trace: Path) -> Optional[int]:
    """Total LLM latency for the task: the sum of every call's `ms`, or None.

    The stage-4 jar emits no run-level Summary line — each call is recorded inside the
    step that made it — so the total is summed rather than read off a line the jar
    computed. Steps are walked through `aperv_tool.analysis.trace_ndjson`, the sanctioned
    reader of the format.

    INV-CAL-04 (independence) still holds. What it forbids is this module re-using the
    consolidator's derivation, and none is shared: the counts this file gates on are
    re-derived here from the raw logcat. Sharing the *format reader* is the opposite of a
    risk — two hand-rolled NDJSON parsers that disagree would produce a divergence gate
    that fires on the parsers rather than on the data.
    """
    try:
        reader = trace_ndjson.TraceReader(trace)
    except OSError:
        return None
    total = 0
    seen = False
    try:
        for step in reader:
            for call in step.llm:
                if call.ms is not None:
                    total += call.ms
                    seen = True
    except OSError:
        return None
    return total if seen else None


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
    """Gate 1 (CONFIG): every task's `RUN_START` must state the arm the manifest declared.

    Two checks per task: the record's `preset` equals the arm's declared preset, and every
    key of the arm's `expected_params` appears in `RUN_START.params` with the declared
    value. That is the whole of "the run executed the arm it is filed under" — an arm is a
    preset name plus its override deltas, and both halves are echoed.

    This now covers every arm rather than only the LLM ones. Under the retired
    `[APE-LLM-CONFIG]` line only LLM arms announced their configuration, so a non-LLM arm
    silently resolving to jar defaults was unobservable; `RUN_START` is emitted by every
    run, which closes that hole rather than widening the gate for its own sake.

    A missing `RUN_START` is a finding, not a skip: a task whose trace cannot say which arm
    ran it is exactly what this gate exists to catch. An arm absent from the manifest, or a
    run with no manifest at all, has nothing declared and contributes nothing.

    Returns ``{"config_findings": [...], "n_audited_tasks": int}``: one finding per
    mismatch, naming the identity, arm, field, and the expected vs observed values.
    """
    config_findings: List[Dict[str, Any]] = []
    n_audited_tasks = 0
    declared_by_arm: Dict[str, Dict[str, Any]] = {}
    if manifest:
        for arm in manifest.get("arms", []):
            declared_by_arm[arm["rv_tools_token"]] = arm
    for ident, rec in best.items():
        arm = _arm_label(rec["name"], rec["variant"])
        declared = declared_by_arm.get(arm)
        if not declared:  # nothing declared for this arm -> nothing to gate
            continue
        trace = artifact_path(rec, "trace")
        if not trace.exists():
            continue
        n_audited_tasks += 1
        observed = _parse_config(trace)
        if observed is None:
            config_findings.append(
                {
                    "identity": ident,
                    "arm": arm,
                    "field": "RUN_START",
                    "expected": "present",
                    "observed": "absent",
                }
            )
            continue
        if _norm(observed.get("preset")) != _norm(declared.get("preset")):
            config_findings.append(
                {
                    "identity": ident,
                    "arm": arm,
                    "field": "preset",
                    "expected": declared.get("preset"),
                    "observed": observed.get("preset"),
                }
            )
        params = observed.get("params") or {}
        for key, expected_value in (declared.get("expected_params") or {}).items():
            if not _num_eq(params.get(key), expected_value):
                config_findings.append(
                    {
                        "identity": ident,
                        "arm": arm,
                        "field": key,
                        "expected": expected_value,
                        "observed": params.get(key),
                    }
                )
    return {"config_findings": config_findings, "n_audited_tasks": n_audited_tasks}


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
        trace = artifact_path(rec, "trace")
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


def _gate_integrity(
    best: Dict[Tuple, Dict[str, Any]],
    rederived: Dict[Tuple, Dict[str, Any]],
    manifest: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Gate 6 (INTEGRITY): every identity admissible under C1-C5, and the admissible count
    equal to the manifest's `predicted_identities` (C6).

    Applied over 100% of identities before any aggregation, so an inadmissible run never
    reaches a mean, a pairing or a comparison. Nothing here reads the arm.

    The distribution of distinct RVSEC-COV signatures is returned whether the gate passes or
    fails, because C4's floor is structural and someone will eventually want to calibrate it
    — on a campaign whose result they are not simultaneously reading.

    Returns ``{"inadmissible": [...], "criterion_counts": {...}, "n_admissible": int,
    "predicted_identities": int|None, "count_matches": bool,
    "cov_signature_distribution": {...}}``.
    """
    inadmissible: List[Dict[str, Any]] = []
    criterion_counts: Dict[str, int] = {c: 0 for c in ADMISSIBILITY_CRITERIA}
    signature_counts: List[int] = []

    for ident in sorted(best, key=lambda i: tuple(str(x) for x in i)):
        rec = best[ident]
        r = rederived[ident]
        signature_counts.append(r["cov_methods_distinct"])
        failures = admissibility_failures(rec, r)
        if failures:
            for failure in failures:
                criterion_counts[failure["criterion"]] += 1
            inadmissible.append(
                {
                    "identity": ident,
                    "arm": r["arm"],
                    "container": rec["base"].parent.name,
                    "failures": failures,
                }
            )

    n_admissible = len(best) - len(inadmissible)
    predicted = manifest.get("predicted_identities") if manifest else None
    count_matches = predicted is None or n_admissible == predicted
    if not count_matches:
        criterion_counts["C6"] = 1

    signature_counts.sort()
    distribution = {
        "n": len(signature_counts),
        "min": signature_counts[0] if signature_counts else None,
        "median": median(signature_counts) if signature_counts else None,
        "max": signature_counts[-1] if signature_counts else None,
        "at_floor_or_below": sum(
            1 for c in signature_counts if c <= _COV_SIGNATURE_FLOOR
        ),
    }
    return {
        "inadmissible": inadmissible,
        "criterion_counts": criterion_counts,
        "n_admissible": n_admissible,
        "predicted_identities": predicted,
        "count_matches": count_matches,
        "cov_signature_distribution": distribution,
    }


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

    # Same identity scope as consolidation, re-derived independently (INV-CAL-04 — VERIFY reads
    # the manifest itself, never imports consolidate_cal): keep only the run's timeout, dropping
    # the smoke tasks (90s) the smoke containers write under the same results/ tree. Without this
    # VERIFY re-derives over a wider identity set than consolidation and reports the smoke-arm
    # cells as spurious divergences.
    run_timeout = manifest.get("timeout") if manifest else None
    if run_timeout is not None:
        tasks = [t for t in tasks if t["timeout"] == run_timeout]

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

    # Gate 6 runs first among the identity-scoped gates: admissibility decides which data
    # may enter an analysis, so it is judged before anything aggregates. Inadmissible
    # identities are not filtered out of the gates below — an inadmissible one quarantines
    # the whole run, which makes the downstream numbers moot rather than in need of repair.
    integrity_result = _gate_integrity(best, rederived, manifest)

    config_result = _gate_config(best, manifest)
    config_findings = config_result["config_findings"]
    n_audited_tasks = config_result["n_audited_tasks"]

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
    if integrity_result["inadmissible"]:
        quarantine_reasons.append(
            f"{len(integrity_result['inadmissible'])} inadmissible identity(ies) "
            "under Gate 6"
        )
    if not integrity_result["count_matches"]:
        quarantine_reasons.append(
            f"{integrity_result['n_admissible']} admissible identities against "
            f"{integrity_result['predicted_identities']} predicted by the manifest (C6)"
        )
    if config_findings:
        quarantine_reasons.append(
            f"{len(config_findings)} RUN_START mismatch(es) in {n_audited_tasks} audited tasks"
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
        "integrity": integrity_result,
        "config_findings": config_findings,
        "n_audited_tasks": n_audited_tasks,
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
        f"Tasks audited: {result['n_audited_tasks']}\n"
    )

    integrity = result["integrity"]
    lines.append("## Gate 6 — admissibility (100% of identities, before any aggregation)\n")
    lines.append("Criteria, applied blind to arm and to the direction of the effect:\n")
    for code, description in ADMISSIBILITY_CRITERIA.items():
        lines.append(f"- **{code}** — {description}")
    lines.append("")
    lines.append(
        f"Admissible: {integrity['n_admissible']} / {result['n_identities']} identities"
        + (
            f" | manifest predicts {integrity['predicted_identities']}"
            if integrity["predicted_identities"] is not None
            else ""
        )
        + "\n"
    )
    if not integrity["inadmissible"] and integrity["count_matches"]:
        lines.append("PASS — every identity is admissible and the count is as predicted.\n")
    else:
        lines.append(f"FAIL — {len(integrity['inadmissible'])} inadmissible identity(ies):")
        for row in integrity["inadmissible"]:
            failed = ", ".join(
                f"{f['criterion']} ({f['detail']})" for f in row["failures"]
            )
            lines.append(
                f"- `{row['container']}` identity `{row['identity']}` "
                f"arm `{row['arm']}` fails {failed}"
            )
        if not integrity["count_matches"]:
            lines.append(
                f"- C6: {integrity['n_admissible']} admissible against "
                f"{integrity['predicted_identities']} predicted"
            )
        lines.append("")
    lines.append(
        "Failures per criterion (an identity may fail more than one): "
        + ", ".join(f"{c}={n}" for c, n in integrity["criterion_counts"].items())
        + "\n"
    )
    # Reported on every run, pass or fail: C4's floor is structural, and calibrating it
    # later needs a distribution measured by a campaign that was not also reading its own
    # result to choose the number.
    dist = integrity["cov_signature_distribution"]
    lines.append(
        f"Distinct RVSEC-COV signatures per identity — n={dist['n']}, min={dist['min']}, "
        f"median={dist['median']}, max={dist['max']}, "
        f"at or below the floor of {_COV_SIGNATURE_FLOOR}: {dist['at_floor_or_below']}\n"
    )

    lines.append("## Gate 1 — RUN_START == manifest (100% of tasks)\n")
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

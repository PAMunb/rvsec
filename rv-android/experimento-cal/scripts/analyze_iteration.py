#!/usr/bin/env python3
"""ANALYZE — gated screening analysis of a consolidated calibration iteration.

This is the ANALYZE state of the calibration loop (methodology §3; spec "Gated Analysis",
INV-CAL-10). It reads the consolidated outcome table, the LLM telemetry proxies, and the
iteration manifest, and writes `iterN/analysis.md` applying FOUR gates in a FIXED,
pre-declared order:

    Gate 1  proxy elimination        (from tel_proxies.csv)
    Gate 2  outcome ranking          (trimmed-mean 10% + paired bootstrap CIs vs ANC1/ANC2,
                                       raw mean ALWAYS reported alongside — INV-CAL-10)
    Gate 3  mechanistic prediction   (predicted Δcov_mop = Δactions/task × +46%/action,
                                       vs the observed CI95; H3 temperature arms are
                                       DESCRIPTIVE ONLY and exempt from elimination here)
    Gate 4  determinism              (identical-trace rate between reps; <30% target for
                                       temperature>0 arms)

The order is not cosmetic: eliminating on a cheap proxy (Gate 1) before ranking (Gate 2)
prevents an arm that only *looks* good on a tail-driven mean from surviving on telemetry
grounds it already fails, and the mechanistic check (Gate 3) can only be read once the
observed CI (Gate 2) exists.

Screening SELECTS candidates for the next phase; it NEVER concludes. No victory is declared
by a screening p-value (INV-CAL-10). The Friedman + Holm omnibus is reported DESCRIPTIVELY.

Statistics come from the local `multiarm_stats` module (which imports the vendored
`stats_utils`); there is no runtime dependency on the `rvsec-calibracao` repo.

Input contracts (see the contracts doc):
  * `iterN/per_apk_paired.csv` — one row per APK; columns `apk` then `{arm_label}__{metric}`
    for metric in [cov_method, cov_act, cov_mop, mop_unique, mop_total, crashes]. Reps are
    already averaged per (apk, arm). `arm_label` is the RV_TOOLS token (`ape:default`,
    `aperv:cal_a1`).
  * `iterN/tel_proxies.csv` — one row per (arm, apk, rep) with LLM telemetry aggregates:
    `arm, apk, rep, calls, time_ms, matched, llm_tap, no_match, no_match_parse_error,
    mode_new_state, mode_stagnation, mode_random` (plus token columns; read defensively).
  * `iterN/manifest.json` — arms (role, rv_tools_token, keys incl. `llm_temperature`),
    anchors by role (ANC1/ANC2), and `bootstrap_seed`.

Usage:
    analyze_iteration.py --iter-dir experimento-cal/iterN
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import multiarm_stats
import numpy as np
import pandas as pd

# --- fixed analysis constants (pre-declared; documented in the plan) -------------------
# Primary decision metric of the campaign: MOP-reachable method coverage.
PRIMARY_METRIC = "cov_mop"
# Bootstrap resamples for the paired CIs (spec floor B >= 10,000).
BOOTSTRAP_B = 10_000
# Gate 1 thresholds.
PARSE_FAIL_HIGH = 0.20  # >20% of LLM calls failing to parse -> proxy elimination
LATENCY_MULT = 2.0  # per-arm mean latency >= 2x the between-arm median -> eliminate
# Gate 3: the llm-gap diagnosis coverage elasticity — extra cov_mop (pp) per extra LLM
# action/task. The predicted Δcov_mop of an arm is its Δactions/task times this factor;
# the +46%/action figure was measured on the widget substrate and is treated as a
# cross-substrate estimate until the Phase-A run re-anchors it (design decision 3).
PER_ACTION_COV_FACTOR = 0.46
# Roles of the H3 temperature-sweep arms (plan §6.1 gate 3): descriptive only at Gate 3.
TEMPERATURE_ROLES = {"A5", "A6", "A7"}
# Gate 4: identical-trace rate between reps must stay below this for temperature>0 arms
# (a stochastic policy should rarely replay an identical action trace).
DETERMINISM_TARGET = 0.30


# --- loading ---------------------------------------------------------------------------
def load_manifest(iter_dir: Path) -> dict:
    return json.loads((iter_dir / "manifest.json").read_text())


def anchors_and_arms(manifest: dict):
    """Return (anc1_token, anc2_token, [candidate arm dicts]) resolved from manifest roles.

    Candidate arms are every arm that is not an anchor (roles A1..A9). Each candidate dict
    carries role, token, and the manifest-resolved keys (used for `llm_temperature`).
    """
    by_role = {a["role"]: a for a in manifest["arms"]}
    anc1 = by_role["ANC1"]["rv_tools_token"]
    anc2 = by_role["ANC2"]["rv_tools_token"]
    candidates = [a for a in manifest["arms"] if a["role"] not in ("ANC1", "ANC2")]
    return anc1, anc2, candidates


def metric_vectors(
    paired: pd.DataFrame, tokens: List[str], metric: str
) -> Dict[str, np.ndarray]:
    """Per-arm per-APK value vector for one metric; arms with no column are skipped."""
    out: Dict[str, np.ndarray] = {}
    for tok in tokens:
        col = f"{tok}__{metric}"
        if col in paired.columns:
            out[tok] = paired[col].to_numpy(dtype=float)
    return out


def telemetry_by_arm(tel: pd.DataFrame) -> Dict[str, dict]:
    """Aggregate tel_proxies rows into per-arm proxy statistics.

    Returns, per arm token: mean latency (mean time_ms per task), actions/task (mean calls),
    parse-fail rate (Σ parse-fail / Σ calls), and the per-(apk) rep signatures used by the
    determinism gate. Reads columns defensively — a missing reason column counts as zero.
    """
    if tel is None or tel.empty or "arm" not in tel.columns:
        return {}

    def col(frame, name):
        return frame[name] if name in frame.columns else pd.Series(0, index=frame.index)

    out: Dict[str, dict] = {}
    for arm, sub in tel.groupby("arm"):
        calls = col(sub, "calls").astype(float)
        time_ms = col(sub, "time_ms").astype(float)
        parse_fail = col(sub, "no_match_parse_error").astype(float)
        total_calls = float(calls.sum())
        # Rep-signature per APK for the determinism gate: the action counts of each rep.
        sig_cols = [
            c for c in ("calls", "matched", "llm_tap", "no_match") if c in sub.columns
        ]
        rep_sigs: Dict[str, list] = {}
        if "apk" in sub.columns and "rep" in sub.columns:
            for apk, apk_sub in sub.groupby("apk"):
                ordered = apk_sub.sort_values("rep")
                rep_sigs[str(apk)] = [tuple(r) for r in ordered[sig_cols].to_numpy()]
        out[arm] = {
            "mean_latency_ms": float(time_ms.mean()) if len(time_ms) else float("nan"),
            "actions_per_task": float(calls.mean()) if len(calls) else float("nan"),
            "parse_fail_rate": (
                (float(parse_fail.sum()) / total_calls) if total_calls else 0.0
            ),
            "rep_signatures": rep_sigs,
        }
    return out


# --- gates -----------------------------------------------------------------------------
def gate1_proxy_elimination(
    candidates: List[dict],
    tel_stats: Dict[str, dict],
    vecs: Dict[str, np.ndarray],
    a1_token: Optional[str],
) -> List[dict]:
    """Gate 1: eliminate an LLM arm on a telemetry proxy BEFORE it is ranked.

    An arm is eliminated if ANY of: (a) parse-fail rate > PARSE_FAIL_HIGH; (b) its mean
    latency >= LATENCY_MULT × the between-arm median mean-latency; (c) it runs fewer
    actions/task than the reference arm cal_a1 WITHOUT a coverage gain (cov_mop not above
    cal_a1). Anchors carry no LLM telemetry and are not subject to this gate.
    """
    latencies = [
        tel_stats[c["rv_tools_token"]]["mean_latency_ms"]
        for c in candidates
        if c["rv_tools_token"] in tel_stats
        and not np.isnan(tel_stats[c["rv_tools_token"]]["mean_latency_ms"])
    ]
    median_latency = float(np.median(latencies)) if latencies else float("nan")

    a1_actions = a1_cov = float("nan")
    if a1_token and a1_token in tel_stats:
        a1_actions = tel_stats[a1_token]["actions_per_task"]
    if a1_token and a1_token in vecs:
        a1_cov = float(np.nanmean(vecs[a1_token]))

    rows = []
    for c in candidates:
        tok = c["rv_tools_token"]
        st = tel_stats.get(tok)
        reasons = []
        if st is not None:
            if st["parse_fail_rate"] > PARSE_FAIL_HIGH:
                reasons.append(
                    f"parse-fail rate {st['parse_fail_rate']:.1%} > {PARSE_FAIL_HIGH:.0%}"
                )
            if (
                not np.isnan(median_latency)
                and not np.isnan(st["mean_latency_ms"])
                and st["mean_latency_ms"] >= LATENCY_MULT * median_latency
            ):
                reasons.append(
                    f"mean latency {st['mean_latency_ms']:.0f} ms >= "
                    f"{LATENCY_MULT:g}× between-arm median {median_latency:.0f} ms"
                )
            if (
                a1_token
                and tok != a1_token
                and not np.isnan(a1_actions)
                and not np.isnan(a1_cov)
                and tok in vecs
                and st["actions_per_task"] < a1_actions
                and float(np.nanmean(vecs[tok])) <= a1_cov
            ):
                reasons.append(
                    f"actions/task {st['actions_per_task']:.1f} < cal_a1 {a1_actions:.1f} "
                    f"without cov_mop gain"
                )
        rows.append(
            {
                "role": c["role"],
                "token": tok,
                "eliminated": bool(reasons),
                "reasons": reasons,
                "has_telemetry": st is not None,
            }
        )
    return rows


def gate3_mechanistic(
    candidates: List[dict],
    tel_stats: Dict[str, dict],
    comparisons: Dict[str, Dict[str, dict]],
    anc2_token: str,
) -> List[dict]:
    """Gate 3: predicted vs observed Δcov_mop, reported side by side per arm.

    Predicted Δcov_mop = Δactions/task × PER_ACTION_COV_FACTOR, where Δactions/task is the
    arm's LLM actions/task minus the anchor's — and the ANC2 non-LLM control performs zero
    LLM actions, so Δactions/task equals the arm's own actions/task. Observed = the Gate-2
    paired bootstrap CI95 of the arm vs ANC2. Prediction OUTSIDE the observed CI is flagged
    "mechanism not understood — do not promote without investigation". Temperature arms
    (roles A5/A6/A7) are DESCRIPTIVE ONLY here: prediction and CI are still shown, but they
    are never eliminated by this gate (plan §6.1 gate 3).
    """
    rows = []
    for c in candidates:
        tok = c["rv_tools_token"]
        role = c["role"]
        is_temp = role in TEMPERATURE_ROLES
        st = tel_stats.get(tok)
        actions = st["actions_per_task"] if st else float("nan")
        predicted = (
            actions * PER_ACTION_COV_FACTOR if not np.isnan(actions) else float("nan")
        )
        obs = comparisons.get(tok, {}).get(anc2_token)
        ci_lo = obs["ci_lo"] if obs else float("nan")
        ci_hi = obs["ci_hi"] if obs else float("nan")
        inside = (
            not np.isnan(predicted)
            and not np.isnan(ci_lo)
            and ci_lo <= predicted <= ci_hi
        )
        flagged = bool(not inside and not np.isnan(predicted) and not np.isnan(ci_lo))
        rows.append(
            {
                "role": role,
                "token": tok,
                "temperature_arm": is_temp,
                "predicted_dcov_mop": predicted,
                "ci_lo": ci_lo,
                "ci_hi": ci_hi,
                "prediction_inside_ci": bool(inside),
                # Temperature arms are exempt from elimination by this gate.
                "flagged": flagged and not is_temp,
                "descriptive_only": is_temp,
            }
        )
    return rows


def gate4_determinism(candidates: List[dict], tel_stats: Dict[str, dict]) -> List[dict]:
    """Gate 4: identical-trace rate between reps; <30% target for temperature>0 arms.

    For each (arm, apk) with two reps, the reps' action-count signatures are compared; the
    identical-trace rate is the fraction of such APK pairs whose reps match exactly. A
    temperature>0 arm whose rate reaches DETERMINISM_TARGET is flagged (a stochastic policy
    that keeps replaying identical traces is behaving deterministically — a red flag).
    """
    rows = []
    for c in candidates:
        tok = c["rv_tools_token"]
        role = c["role"]
        temp = float(c.get("keys", {}).get("llm_temperature", 0) or 0)
        st = tel_stats.get(tok)
        identical = total = 0
        if st:
            for _apk, sigs in st["rep_signatures"].items():
                if len(sigs) >= 2:
                    total += 1
                    if sigs[0] == sigs[1]:
                        identical += 1
        rate = (identical / total) if total else float("nan")
        is_stochastic = temp > 0
        flagged = bool(
            is_stochastic and not np.isnan(rate) and rate >= DETERMINISM_TARGET
        )
        rows.append(
            {
                "role": role,
                "token": tok,
                "temperature": temp,
                "identical_trace_rate": rate,
                "n_apk_pairs": total,
                "stochastic": is_stochastic,
                "flagged": flagged,
            }
        )
    return rows


# --- rendering -------------------------------------------------------------------------
def _fmt(x: float, nd: int = 2) -> str:
    return (
        "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"
    )


def render_markdown(
    manifest: dict,
    anc1: str,
    anc2: str,
    summary: dict,
    g1: List[dict],
    g3: List[dict],
    g4: List[dict],
    primary_metric: str,
) -> str:
    lines: List[str] = []
    it = manifest["iteration"]
    phase = manifest["phase"]
    lines.append(f"# Analysis — iteration {it} (phase {phase})")
    lines.append("")
    lines.append(
        "**This is a SCREENING analysis.** It SELECTS candidate arms for the next phase; "
        "it does NOT conclude and declares NO winner by a screening p-value (INV-CAL-10). "
        "All statistics below are descriptive decision inputs."
    )
    lines.append("")
    lines.append(
        f"Primary metric: `{primary_metric}`. Anchors: ANC1=`{anc1}`, ANC2=`{anc2}`. "
        f"Paired bootstrap B={BOOTSTRAP_B}, seed={manifest['bootstrap_seed']}."
    )
    lines.append("")

    # ---- Gate 1 ----
    lines.append("## Gate 1 — Proxy elimination")
    lines.append("")
    lines.append(
        "Eliminates an LLM arm on a telemetry proxy (parse-fail, latency, or "
        "actions/task without coverage gain) BEFORE ranking."
    )
    lines.append("")
    lines.append("| Arm | Token | Eliminated | Reasons |")
    lines.append("|---|---|---|---|")
    for r in g1:
        reasons = "; ".join(r["reasons"]) if r["reasons"] else "—"
        lines.append(
            f"| {r['role']} | `{r['token']}` | "
            f"{'YES' if r['eliminated'] else 'no'} | {reasons} |"
        )
    lines.append("")

    # ---- Gate 2 ----
    lines.append("## Gate 2 — Outcome ranking")
    lines.append("")
    lines.append(
        "Trimmed mean (10%) reported ALONGSIDE the raw mean (INV-CAL-10); paired "
        "bootstrap CI95 of each arm vs BOTH anchors on the pinned estimand "
        "(difference of trimmed means), with matched-pairs rank-biserial effect size."
    )
    lines.append("")
    lines.append(
        "| Arm | Token | raw mean | trimmed mean | Δ vs ANC1 [CI95] | rb₁ | "
        "Δ vs ANC2 [CI95] | rb₂ |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    summaries = summary["summaries"]
    comparisons = summary["comparisons"]
    for a in manifest["arms"]:
        tok = a["rv_tools_token"]
        if tok not in summaries:
            continue
        s = summaries[tok]
        c1 = comparisons.get(tok, {}).get(anc1)
        c2 = comparisons.get(tok, {}).get(anc2)

        def cell(c):
            if not c:
                return "—", "—"
            return (
                f"{_fmt(c['trimmed_diff'])} [{_fmt(c['ci_lo'])}, {_fmt(c['ci_hi'])}]",
                _fmt(c["rank_biserial"]),
            )

        d1, rb1 = cell(c1)
        d2, rb2 = cell(c2)
        lines.append(
            f"| {a['role']} | `{tok}` | {_fmt(s['raw_mean'])} | "
            f"{_fmt(s['trimmed_mean'])} | {d1} | {rb1} | {d2} | {rb2} |"
        )
    lines.append("")

    # ---- Gate 3 ----
    lines.append("## Gate 3 — Mechanistic prediction vs observed")
    lines.append("")
    lines.append(
        f"Predicted Δcov_mop = Δactions/task × {PER_ACTION_COV_FACTOR:g} (+46%/action, "
        "llm-gap diagnosis, cross-substrate estimate). Observed = the Gate-2 CI95 vs "
        "ANC2. Prediction outside the CI is flagged unless the arm is an H3 "
        "temperature arm (descriptive only, exempt from Gate-3 elimination)."
    )
    lines.append("")
    lines.append(
        "| Arm | Token | Predicted Δcov_mop | Observed CI95 (vs ANC2) | "
        "Inside CI | Status |"
    )
    lines.append("|---|---|---|---|---|---|")
    for r in g3:
        ci = f"[{_fmt(r['ci_lo'])}, {_fmt(r['ci_hi'])}]"
        if r["descriptive_only"]:
            status = (
                "descriptive only (H3 temperature arm) — exempt from Gate-3 elimination"
            )
        elif r["flagged"]:
            status = "mechanism not understood — do not promote without investigation"
        else:
            status = "consistent"
        lines.append(
            f"| {r['role']} | `{r['token']}` | {_fmt(r['predicted_dcov_mop'])} | "
            f"{ci} | {'yes' if r['prediction_inside_ci'] else 'no'} | {status} |"
        )
    lines.append("")

    # ---- Gate 4 ----
    lines.append("## Gate 4 — Determinism (between-reps identical-trace rate)")
    lines.append("")
    lines.append(
        f"Identical-trace rate between reps; target < {DETERMINISM_TARGET:.0%} for "
        "temperature>0 arms (a stochastic policy should rarely replay an identical "
        "trace)."
    )
    lines.append("")
    lines.append(
        "| Arm | Token | temperature | identical-trace rate | n APK pairs | Flag |"
    )
    lines.append("|---|---|---|---|---|---|")
    for r in g4:
        flag = "FLAG (>= target)" if r["flagged"] else "—"
        lines.append(
            f"| {r['role']} | `{r['token']}` | {_fmt(r['temperature'])} | "
            f"{_fmt(r['identical_trace_rate'])} | {r['n_apk_pairs']} | {flag} |"
        )
    lines.append("")

    # ---- Friedman + Holm (descriptive) ----
    lines.append("## Descriptive Friedman + Holm (all arms)")
    lines.append("")
    fr = summary["friedman"]
    if not fr.get("available"):
        lines.append(
            f"Omnibus unavailable: {fr.get('reason', 'insufficient complete cases')}."
        )
    else:
        lines.append(
            f"Friedman χ² = {_fmt(fr['statistic'], 3)}, p = {_fmt(fr['pvalue'], 4)} "
            f"(n_complete = {fr['n_complete']} APKs). DESCRIPTIVE — not a verdict."
        )
        lines.append("")
        lines.append("Mean rank per arm (higher = better on cov_mop):")
        lines.append("")
        lines.append("| Token | mean rank |")
        lines.append("|---|---|")
        for tok, mr in sorted(fr["mean_rank"].items(), key=lambda kv: -kv[1]):
            lines.append(f"| `{tok}` | {_fmt(mr, 2)} |")
        lines.append("")
        lines.append("Holm-adjusted pairwise Wilcoxon (descriptive):")
        lines.append("")
        lines.append("| Arm A | Arm B | p (raw) | p (Holm) |")
        lines.append("|---|---|---|---|")
        for a, b, p_raw, p_holm in fr["pairwise_holm"]:
            lines.append(f"| `{a}` | `{b}` | {_fmt(p_raw, 4)} | {_fmt(p_holm, 4)} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "_Screening output: the gates above SELECT candidates for the next phase. "
        "No arm is declared a winner here (INV-CAL-10)._"
    )
    lines.append("")
    return "\n".join(lines)


# --- orchestration ---------------------------------------------------------------------
def analyze(iter_dir: Path) -> Path:
    """Run all four gates and write `iterN/analysis.md`. Returns the analysis path."""
    manifest = load_manifest(iter_dir)
    seed = int(manifest["bootstrap_seed"])
    anc1, anc2, candidates = anchors_and_arms(manifest)
    all_tokens = [a["rv_tools_token"] for a in manifest["arms"]]

    paired = pd.read_csv(iter_dir / "per_apk_paired.csv")
    tel_path = iter_dir / "tel_proxies.csv"
    tel = pd.read_csv(tel_path) if tel_path.exists() else None

    vecs = metric_vectors(paired, all_tokens, PRIMARY_METRIC)
    tel_stats = telemetry_by_arm(tel)

    summary = multiarm_stats.multiarm_summary(
        per_apk=vecs,
        arm_labels=all_tokens,
        anchor_labels=[anc1, anc2],
        B=BOOTSTRAP_B,
        seed=seed,
    )

    a1_token = next(
        (c["rv_tools_token"] for c in candidates if c["role"] == "A1"), None
    )
    g1 = gate1_proxy_elimination(candidates, tel_stats, vecs, a1_token)
    g3 = gate3_mechanistic(candidates, tel_stats, summary["comparisons"], anc2)
    g4 = gate4_determinism(candidates, tel_stats)

    md = render_markdown(manifest, anc1, anc2, summary, g1, g3, g4, PRIMARY_METRIC)
    out = iter_dir / "analysis.md"
    out.write_text(md, encoding="utf-8")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--iter-dir", required=True, help="path to experimento-cal/iterN"
    )
    args = parser.parse_args(argv)

    iter_dir = Path(args.iter_dir)
    if not iter_dir.is_absolute():
        iter_dir = (Path.cwd() / iter_dir).resolve()
    for required in ("manifest.json", "per_apk_paired.csv"):
        if not (iter_dir / required).exists():
            sys.stderr.write(f"missing required input: {iter_dir / required}\n")
            return 2

    out = analyze(iter_dir)
    print(f"wrote {out}")
    print(
        "journal line: "
        + json.dumps(
            {
                "state": "ANALYZE",
                "iter": load_manifest(iter_dir)["iteration"],
                "artifact": str(out),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

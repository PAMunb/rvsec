#!/usr/bin/env python3
"""Fase 0 / P3 — stratified calibration subset generator (offline, no GPU/emulator).

Produces the stratified APK subsets the calibration loop consumes:
  - calibracao/subset40.txt  (Phase A/B screening — gen_iteration.py hard-fails without it)
  - calibracao/subset90.txt  (Phase C confirmation, SESOI n=80-100)
  - calibracao/llm_proxy.csv (per-APK LLM engagement proxy, cached provenance)
  - calibracao/subset_representativeness.md (means, KS, strata, leave-10-out stability)

Method (methodology doc §P3):
  INPUT   cmpma per_apk_paired.csv (181-APK, 5 historical arms) + cmp_llm base-run
          traces (per-APK LLM proxy) + physical selected181 dataset (.apk + .apk.json).
  ACTION  stratify on ape__cov_mop quartiles + mop_unique>0 fraction (~70%) + LLM proxy
          (llm_tap / #LLM calls) terciles; greedy forward selection minimising |Δmean|;
          leave-10-out stability of the historical 5-arm cov_mop ranking on the subset.
  GATE    |Δmean| <= 1.0pp on cov_mop for every arm; KS n.s. (p>0.05); .apk + .apk.json
          present for every selected APK.

Deterministic: all tie-breaking and leave-10-out draws use a fixed seed. Re-running with
the same inputs yields byte-identical subsets.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

# --- paths -----------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
CMPMA_CSV = REPO_ROOT / "data/results/cmpma_consolidado/per_apk_paired.csv"
BASE_RUN_GLOB = "experimento-20260721/results/cmp_llm_20260721_base_0*/*/*.apk/*.trace"
DATASET_DIR = Path(
    "/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/"
    "APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706_selected181"
)
OUT_DIR = REPO_ROOT / "calibracao"

# The 5 historical cmpma arms, in the column-prefix form used by per_apk_paired.csv.
ARMS = [
    "ape",
    "aperv:ape_pure",
    "aperv:sata",
    "aperv:sata_mop_activity",
    "aperv:sata_mop_act_frontier",
]
# ape builtin is the historical primary reference for the cov_mop stratification axis.
PRIMARY_ARM = "ape"
FRONTIER_ARM = "aperv:sata_mop_act_frontier"  # ANC2 substrate; expected rank #1
COV_METRICS = ["cov_method", "cov_act", "cov_mop"]

SEED = 42

# --- LLM proxy from base-run traces ----------------------------------------------------
_TEL = re.compile(r"\[APE-LLM-TEL\].*?\bresult=(matched|llm_tap|no_match)\b")


def build_llm_proxy(cache: Path) -> pd.DataFrame:
    """Per-APK LLM engagement proxy from the cmp_llm base run (reference LLM arm).

    Each [APE-LLM-TEL] line is one LLM call whose result is one of:
      matched   — Qwen coordinate grounded to a widget within tolerance (widget tap)
      llm_tap   — deliberate raw-coordinate tap (no widget match, tapped anyway)
      no_match  — no action taken
    Proxy axis (methodology §P3): llm_tap_rate = llm_tap / (#LLM calls), aggregated over
    the 3 reps. Captures how much the LLM arm falls back to raw-coordinate taps on an app,
    which co-varies with app UI structure and is orthogonal to the coverage axis.
    """
    if cache.exists():
        return pd.read_csv(cache)
    counts: dict[str, dict[str, int]] = {}
    for tf in REPO_ROOT.glob(BASE_RUN_GLOB):
        apk = tf.parent.name  # ".../<apk>.apk/<...>.trace"
        c = counts.setdefault(apk, {"matched": 0, "llm_tap": 0, "no_match": 0})
        for line in tf.read_text(errors="replace").splitlines():
            m = _TEL.search(line)
            if m:
                c[m.group(1)] += 1
    rows = []
    for apk, c in counts.items():
        calls = c["matched"] + c["llm_tap"] + c["no_match"]
        rows.append(
            {
                "apk": apk,
                "llm_calls": calls,
                "llm_matched": c["matched"],
                "llm_tap": c["llm_tap"],
                "llm_no_match": c["no_match"],
                "llm_tap_rate": (c["llm_tap"] / calls) if calls else 0.0,
            }
        )
    proxy = pd.DataFrame(rows).sort_values("apk").reset_index(drop=True)
    proxy.to_csv(cache, index=False)
    return proxy


# --- objective + greedy selection ------------------------------------------------------
def full_means(df: pd.DataFrame) -> dict[str, float]:
    """Full-set means for every arm x cov metric (the targets the subset must match)."""
    return {f"{a}__{m}": df[f"{a}__{m}"].mean() for a in ARMS for m in COV_METRICS}


def objective(sub: pd.DataFrame, targets: dict[str, float], frac_full: float) -> float:
    """Composite deviation of a candidate subset from the full set (lower = better).

    cov_mop (the gate metric) carries unit weight per arm; cov_method and cov_act carry
    half weight per arm so the subset does not drift on the diagnostic coverage axes while
    cov_mop is pinned; the mop_unique>0 fraction and LLM-proxy tercile balance are the
    remaining light terms. Applied as the secondary term under the hinge score below, this
    co-balances cov_act/cov_method once cov_mop is comfortably inside the gate.
    """
    j = 0.0
    for a in ARMS:
        j += abs(sub[f"{a}__cov_mop"].mean() - targets[f"{a}__cov_mop"])
        j += 0.5 * abs(sub[f"{a}__cov_method"].mean() - targets[f"{a}__cov_method"])
        j += 0.5 * abs(sub[f"{a}__cov_act"].mean() - targets[f"{a}__cov_act"])
    j += 2.0 * abs((sub[f"{PRIMARY_ARM}__mop_unique"] > 0).mean() - frac_full) * 100.0
    for t in (0, 1, 2):
        j += 1.0 * abs((sub["llm_tercile"] == t).mean() - 1 / 3) * 100.0
    return j


def max_cov_mop_delta(sub: pd.DataFrame, targets: dict[str, float]) -> float:
    """Largest per-arm |Δmean cov_mop| — the quantity the §P3 gate bounds at 1.0pp."""
    return max(abs(sub[f"{a}__cov_mop"].mean() - targets[f"{a}__cov_mop"]) for a in ARMS)


# Once every arm's cov_mop is within this slack (well inside the 1.0pp gate) the primary
# score saturates to 0 and refinement spends its remaining freedom on the composite
# (cov_method/cov_act/mop-fraction/tercile balance) instead of over-fitting cov_mop.
GATE_SLACK = 0.5


def _score(sub: pd.DataFrame, targets, frac_full) -> tuple[float, float]:
    """Hinge subset score: (cov_mop overshoot beyond slack, composite). Lower is better."""
    primary = max(0.0, max_cov_mop_delta(sub, targets) - GATE_SLACK)
    return primary, objective(sub, targets, frac_full)


def select_subset(df: pd.DataFrame, n: int) -> list[str]:
    """Greedy forward selection under proportional quartile quotas, then swap refinement.

    Quartile quotas on ape__cov_mop guarantee the coverage spectrum is represented. Greedy
    forward selection gives a good start; per-APK cov_mop is correlated across arms, so the
    myopic path drifts all arm means the same direction. Swap refinement then exchanges a
    selected APK for a non-selected one *in the same quartile* (preserving quotas) whenever
    it lowers the lexicographic score (primary: max per-arm |Δcov_mop| = the gate metric;
    secondary: the composite balance objective). Same-quartile swaps keep the stratification
    fixed while pulling the means onto target. Deterministic under the seed.
    """
    targets = full_means(df)
    frac_full = (df[f"{PRIMARY_ARM}__mop_unique"] > 0).mean()
    rng = np.random.default_rng(SEED)

    # Proportional quartile quotas (largest-remainder rounding to sum exactly to n).
    q_counts = df["cov_mop_quartile"].value_counts().sort_index()
    raw = {q: n * c / len(df) for q, c in q_counts.items()}
    quota = {q: int(np.floor(v)) for q, v in raw.items()}
    rem = n - sum(quota.values())
    for q in sorted(raw, key=lambda k: raw[k] - quota[k], reverse=True)[:rem]:
        quota[q] += 1

    order = list(rng.permutation(df.index.to_numpy()))
    selected: list[int] = []
    used = {q: 0 for q in quota}
    while len(selected) < n:
        best_idx, best_j = None, np.inf
        for idx in order:
            if idx in selected:
                continue
            q = df.at[idx, "cov_mop_quartile"]
            if used[q] >= quota[q]:
                continue
            j = objective(df.loc[selected + [idx]], targets, frac_full)
            if j < best_j:
                best_j, best_idx = j, idx
        selected.append(best_idx)
        used[df.at[best_idx, "cov_mop_quartile"]] += 1

    # Swap refinement (steepest-descent local search, same-quartile swaps only).
    sel = set(selected)
    quart = df["cov_mop_quartile"]
    cur = _score(df.loc[list(sel)], targets, frac_full)
    for _ in range(200):  # cap; converges well before this on 181 APKs
        best_swap, best = None, cur
        for s in list(sel):
            qs = quart.at[s]
            for c in order:
                if c in sel or quart.at[c] != qs:
                    continue
                trial = (sel - {s}) | {c}
                sc = _score(df.loc[list(trial)], targets, frac_full)
                if sc < best:
                    best, best_swap = sc, (s, c)
        if best_swap is None:
            break
        s, c = best_swap
        sel = (sel - {s}) | {c}
        cur = best
    return sorted(df.loc[list(sel), "apk"].tolist())


# --- leave-10-out ranking stability ----------------------------------------------------
def ranking(df: pd.DataFrame) -> list[str]:
    """Arms ordered by mean cov_mop, descending (the historical screening ranking)."""
    means = {a: df[f"{a}__cov_mop"].mean() for a in ARMS}
    return sorted(means, key=means.get, reverse=True)


def leave_10_out(df: pd.DataFrame, sub_apks: list[str], draws: int = 500) -> dict:
    """Robustness of the 5-arm cov_mop ranking to removing 10 APKs from the subset.

    The middle three arms sit within ~0.9pp on the full set (statistically tied), so the
    meaningful, testable invariant is the frontier arm staying rank #1 (and ape_pure last).
    Reports the fraction of seeded 10-out draws preserving each, plus mean Kendall tau vs
    the subset's full ranking.
    """
    sub = df[df["apk"].isin(sub_apks)].reset_index(drop=True)
    base_rank = ranking(sub)
    rng = np.random.default_rng(SEED)
    idx = sub.index.to_numpy()
    front_top = last_bottom = tau_sum = 0
    for _ in range(draws):
        drop = rng.choice(idx, size=10, replace=False)
        r = ranking(sub.drop(index=drop))
        front_top += r[0] == FRONTIER_ARM
        last_bottom += r[-1] == base_rank[-1]
        # Kendall tau between r and base_rank (concordant - discordant) / pairs.
        pos = {a: i for i, a in enumerate(r)}
        b = [pos[a] for a in base_rank]
        conc = disc = 0
        for i in range(len(b)):
            for k in range(i + 1, len(b)):
                if b[i] < b[k]:
                    conc += 1
                else:
                    disc += 1
        tau_sum += (conc - disc) / (conc + disc)
    return {
        "base_rank": base_rank,
        "frontier_top_frac": front_top / draws,
        "last_stable_frac": last_bottom / draws,
        "mean_kendall_tau": tau_sum / draws,
        "draws": draws,
    }


# --- memo + gate -----------------------------------------------------------------------
def representativeness(df: pd.DataFrame, sub_apks: list[str]) -> pd.DataFrame:
    """Per arm x metric: full mean, subset mean, Δmean (pp for coverage), KS p-value."""
    sub = df[df["apk"].isin(sub_apks)]
    rows = []
    for a in ARMS:
        for m in COV_METRICS + ["mop_unique"]:
            col = f"{a}__{m}"
            fmean, smean = df[col].mean(), sub[col].mean()
            p = ks_2samp(df[col].to_numpy(), sub[col].to_numpy()).pvalue
            rows.append(
                {
                    "arm": a,
                    "metric": m,
                    "full_mean": fmean,
                    "subset_mean": smean,
                    "delta": smean - fmean,
                    "ks_p": p,
                }
            )
    return pd.DataFrame(rows)


def check_dataset(sub_apks: list[str]) -> list[str]:
    """APKs missing either the .apk or the .apk.json in the physical dataset (gate: none)."""
    missing = []
    for apk in sub_apks:
        if not (DATASET_DIR / apk).exists() or not (DATASET_DIR / f"{apk}.json").exists():
            missing.append(apk)
    return missing


def write_memo(
    df: pd.DataFrame, proxy: pd.DataFrame, r40: pd.DataFrame, r90: pd.DataFrame,
    sub40: list[str], sub90: list[str], lo40: dict, lo90: dict,
    gate40: dict, gate90: dict, path: Path,
) -> None:
    def fmt_rep(rep: pd.DataFrame, n: int) -> str:
        lines = [
            f"### subset{n} vs full (n={n})\n",
            "| arm | metric | full | subset | Δ | KS p |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for _, x in rep.iterrows():
            unit = "pp" if x.metric != "mop_unique" else ""
            lines.append(
                f"| {x.arm} | {x.metric} | {x.full_mean:.3f} | {x.subset_mean:.3f} "
                f"| {x.delta:+.3f}{unit} | {x.ks_p:.3f} |"
            )
        return "\n".join(lines)

    def fmt_gate(g: dict, n: int) -> str:
        cov = g["cov_mop_delta"]
        worst = max(abs(v) for v in cov.values())
        ksmin = g["ks_min_p"]
        return (
            f"- **subset{n}**: max |Δmean cov_mop| = **{worst:.3f}pp** (gate ≤1.0pp) → "
            f"{'PASS' if worst <= 1.0 else 'FAIL'}; "
            f"min KS p (cov_mop) = **{ksmin:.3f}** (gate >0.05) → "
            f"{'PASS' if ksmin > 0.05 else 'FAIL'}; "
            f"dataset .apk+.apk.json present → {'PASS' if not g['missing'] else 'FAIL'}"
        )

    def fmt_lo(lo: dict, n: int) -> str:
        return (
            f"- **subset{n}** ({lo['draws']} seeded 10-out draws): frontier stays rank #1 "
            f"in **{lo['frontier_top_frac']*100:.1f}%**; last arm stable in "
            f"**{lo['last_stable_frac']*100:.1f}%**; mean Kendall τ vs subset ranking = "
            f"**{lo['mean_kendall_tau']:.3f}**. Subset ranking: {' > '.join(lo['base_rank'])}."
        )

    frac_full = (df[f"{PRIMARY_ARM}__mop_unique"] > 0).mean()
    frac40 = (df[df.apk.isin(sub40)][f"{PRIMARY_ARM}__mop_unique"] > 0).mean()
    frac90 = (df[df.apk.isin(sub90)][f"{PRIMARY_ARM}__mop_unique"] > 0).mean()
    pm = proxy.set_index("apk")["llm_tap_rate"]
    strata = "\n".join(
        f"| Q{q+1} | {int((df.cov_mop_quartile==q).sum())} | "
        f"{sum(df[df.apk.isin(sub40)].cov_mop_quartile==q)} | "
        f"{sum(df[df.apk.isin(sub90)].cov_mop_quartile==q)} |"
        for q in range(4)
    )
    md = f"""# Fase 0 / P3 — Representatividade do subset de calibração

Gerado por `calibracao/gen_subset.py` (offline, determinístico, seed={SEED}).
Fontes: `data/results/cmpma_consolidado/per_apk_paired.csv` (181 APKs, 5 braços cmpma) +
proxy LLM do run base `cmp_llm_20260721` (`calibracao/llm_proxy.csv`) + dataset físico
`selected181`.

## 1. Portões (GATE §P3)

{fmt_gate(gate40, 40)}
{fmt_gate(gate90, 90)}

Gate global: |Δmédia| ≤ 1,0pp em cov_mop para **todos** os braços; KS n.s. (p>0,05);
`.apk`+`.apk.json` presentes para todos os APKs selecionados.

## 2. Estratificação

Eixo primário: quartis de `ape__cov_mop` (referência histórica). Cotas proporcionais por
quartil garantem o espectro de cobertura; dentro das cotas, seleção gulosa minimiza o
desvio composto de médias. Eixos secundários balanceados no objetivo: fração
`mop_unique>0` (alvo ≈ fração do conjunto completo) e tercis do proxy LLM `llm_tap_rate`.

Fração `mop_unique>0` (braço {PRIMARY_ARM}): full={frac_full:.3f}, subset40={frac40:.3f},
subset90={frac90:.3f}.

| quartil ape__cov_mop | full | subset40 | subset90 |
|---|---:|---:|---:|
{strata}

Proxy LLM `llm_tap_rate` (full): min={pm.min():.3f}, mediana={pm.median():.3f},
máx={pm.max():.3f}. Tercis balanceados na seleção.

## 3. Representatividade por braço × métrica

{fmt_rep(r40, 40)}

{fmt_rep(r90, 90)}

## 4. Estabilidade do ranking (leave-10-out)

Ranking histórico (full): {' > '.join(ranking(df))}. Os três braços centrais estão a
~0,9pp entre si no conjunto completo (empate estatístico), então o invariante testável é
o braço `{FRONTIER_ARM}` permanecer em 1º.

{fmt_lo(lo40, 40)}
{fmt_lo(lo90, 90)}

## 5. Arquivos gerados

- `calibracao/subset40.txt` — {len(sub40)} APKs (Fase A/B screening).
- `calibracao/subset90.txt` — {len(sub90)} APKs (Fase C confirmação).
- `calibracao/llm_proxy.csv` — proxy LLM por APK (proveniência).
- `calibracao/subset_representativeness.md` — este memo.
"""
    path.write_text(md)


def gate_summary(rep: pd.DataFrame, missing: list[str]) -> dict:
    cov = rep[rep.metric == "cov_mop"]
    return {
        "cov_mop_delta": dict(zip(cov.arm, cov.delta)),
        "ks_min_p": cov.ks_p.min(),
        "missing": missing,
    }


# --- main ------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-a", type=int, default=40, help="screening subset size (Phase A/B)")
    ap.add_argument("--n-c", type=int, default=90, help="confirmation subset size (Phase C)")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    df = pd.read_csv(CMPMA_CSV)
    proxy = build_llm_proxy(OUT_DIR / "llm_proxy.csv")

    if len(df) != len(proxy) or set(df.apk) != set(proxy.apk):
        sys.stderr.write(
            f"apk mismatch: cmpma={len(df)} proxy={len(proxy)}; "
            f"missing in proxy={set(df.apk) - set(proxy.apk)}\n"
        )
        return 2

    # Feature columns used by stratification / greedy objective.
    df = df.merge(proxy[["apk", "llm_tap_rate"]], on="apk")
    df["cov_mop_quartile"] = pd.qcut(
        df[f"{PRIMARY_ARM}__cov_mop"], 4, labels=False, duplicates="drop"
    )
    df["llm_tercile"] = pd.qcut(
        df["llm_tap_rate"].rank(method="first"), 3, labels=False
    )

    sub40 = select_subset(df, args.n_a)
    sub90 = select_subset(df, args.n_c)

    r40, r90 = representativeness(df, sub40), representativeness(df, sub90)
    lo40, lo90 = leave_10_out(df, sub40), leave_10_out(df, sub90)
    g40 = gate_summary(r40, check_dataset(sub40))
    g90 = gate_summary(r90, check_dataset(sub90))

    (OUT_DIR / "subset40.txt").write_text("\n".join(sub40) + "\n")
    (OUT_DIR / "subset90.txt").write_text("\n".join(sub90) + "\n")
    write_memo(df, proxy, r40, r90, sub40, sub90, lo40, lo90, g40, g90,
               OUT_DIR / "subset_representativeness.md")

    # Console gate report.
    ok = True
    for n, g in [(40, g40), (90, g90)]:
        worst = max(abs(v) for v in g["cov_mop_delta"].values())
        p = f"PASS" if worst <= 1.0 and g["ks_min_p"] > 0.05 and not g["missing"] else "FAIL"
        ok &= p == "PASS"
        print(
            f"subset{n}: max|Δcov_mop|={worst:.3f}pp  min_KS_p={g['ks_min_p']:.3f}  "
            f"missing={len(g['missing'])}  frontier_top="
            f"{(lo40 if n==40 else lo90)['frontier_top_frac']*100:.1f}%  -> {p}"
        )
    print("GATE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

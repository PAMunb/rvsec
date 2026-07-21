#!/usr/bin/env python3
"""Análise pareada offline base vs v2 (cmpm).

Junta os dois per_apk_paired.csv por APK (cada APK = média das 3 reps, já
consolidada). Para cada métrica calcula Wilcoxon signed-rank pareado e o
tamanho de efeito rank-biserial. Direção do delta: v2 - base
(positivo => modelo tuned melhor).

Não usa CSV por-container (anti-gh58); lê os consolidados de logcat.
"""
import csv
import statistics as st
from pathlib import Path

from scipy.stats import wilcoxon

RESULTS = Path(__file__).resolve().parent.parent / "results"
ARM = "aperv:sata_mop_llm_v13"
METRICS = ["cov_method", "cov_act", "cov_mop", "mop_unique", "mop_total", "crashes"]
BASE = "cmpm_base"
V2 = "cmpm_v2"


def load(run):
    """apk -> {metric: float} a partir do per_apk_paired.csv consolidado."""
    p = RESULTS / f"{run}_consolidado" / "per_apk_paired.csv"
    out = {}
    with open(p) as f:
        for row in csv.DictReader(f):
            apk = row["apk"]
            out[apk] = {m: float(row[f"{ARM}__{m}"]) for m in METRICS}
    return out


def rank_biserial(xs, ys):
    """rank-biserial para Wilcoxon signed-rank = (W+ - W-)/(W+ + W-).

    Sinal positivo => xs (v2) tende a ser maior que ys (base). Ignora zeros
    (mesmo tratamento do Wilcoxon zero_method='wilcox').
    """
    diffs = [x - y for x, y in zip(xs, ys) if (x - y) != 0]
    if not diffs:
        return 0.0
    ranks = _avg_ranks([abs(d) for d in diffs])
    wp = sum(r for r, d in zip(ranks, diffs) if d > 0)
    wm = sum(r for r, d in zip(ranks, diffs) if d < 0)
    tot = wp + wm
    return (wp - wm) / tot if tot else 0.0


def _avg_ranks(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1  # ranks 1-based
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def main():
    base = load(BASE)
    v2 = load(V2)
    apks = sorted(set(base) & set(v2))
    print(f"APKs pareados: {len(apks)}  (base={len(base)}, v2={len(v2)})")

    rows = []
    for m in METRICS:
        b = [base[a][m] for a in apks]  # base
        t = [v2[a][m] for a in apks]    # tuned/v2
        diffs = [x - y for x, y in zip(t, b)]  # v2 - base
        wins_v2 = sum(d > 0 for d in diffs)
        losses_v2 = sum(d < 0 for d in diffs)
        ties = len(diffs) - wins_v2 - losses_v2
        if any(d != 0 for d in diffs):
            try:
                W, p = wilcoxon(t, b, zero_method="wilcox", alternative="two-sided")
            except ValueError:
                W, p = float("nan"), float("nan")
        else:
            W, p = float("nan"), 1.0
        rb = rank_biserial(t, b)
        rows.append(dict(
            metric=m, n=len(apks),
            mean_base=round(st.mean(b), 3), mean_v2=round(st.mean(t), 3),
            mean_diff=round(st.mean(diffs), 3),
            median_base=round(st.median(b), 3), median_v2=round(st.median(t), 3),
            median_diff=round(st.median(diffs), 3),
            wins_v2=wins_v2, losses_v2=losses_v2, ties=ties,
            W=(round(W, 1) if W == W else "nan"),
            p_value=(round(p, 6) if p == p else "nan"),
            rank_biserial=round(rb, 4),
            significant=("sim" if (p == p and p < 0.05) else "nao"),
        ))

    out = RESULTS / "cmpm_compare_base_v2"
    out.mkdir(exist_ok=True)
    dest = out / "paired_wilcoxon.csv"
    with open(dest, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"CSV: {dest}\n")

    hdr = f"{'metric':11s} {'meanB':>7s} {'meanV2':>7s} {'Δmean':>7s} {'v2>':>4s} {'v2<':>4s} {'p':>9s} {'rb':>7s} sig"
    print(hdr)
    for r in rows:
        print(f"{r['metric']:11s} {r['mean_base']:7.3f} {r['mean_v2']:7.3f} {r['mean_diff']:7.3f} "
              f"{r['wins_v2']:4d} {r['losses_v2']:4d} {str(r['p_value']):>9s} {r['rank_biserial']:7.3f} {r['significant']}")


if __name__ == "__main__":
    main()

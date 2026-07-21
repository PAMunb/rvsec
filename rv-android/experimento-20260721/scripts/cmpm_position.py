#!/usr/bin/env python3
"""Posicionamento dos braços LLM (base, v2) vs baselines no-LLM widget (H4).

widget@300 = aperv:sata_mop_widget do cmpft5 (mesmo orçamento de 300s, sem LLM).
widget@600 = aperv:sata_mop_widget do cmpv2w (600s, controle de efeito-tempo).

Compara cada braço LLM contra cada baseline por APK (interseção), Wilcoxon
pareado. H4: o v2 fecha/inverte o déficit do LLM vs widget@300? (delta = LLM - widget)
"""
import csv
import statistics as st
from pathlib import Path

from scipy.stats import wilcoxon

RESULTS = Path(__file__).resolve().parent.parent / "results"  # base/v2 do run (self-contained)
# baselines externos (cmpft5/cmpv2w widget) vivem no data/results principal do rv-android
BASELINES = Path(__file__).resolve().parents[2] / "data" / "results"
LLM_ARM = "aperv:sata_mop_llm_v13"
WID_ARM = "aperv:sata_mop_widget"


def _norm(a):
    return a[:-4] if a.endswith(".apk") else a


def load(run, arm, metric):
    root = BASELINES if run in ("cmpft5", "cmpv2w", "cmpma") else RESULTS
    p = root / f"{run}_consolidado" / "per_apk_paired.csv"
    out = {}
    with open(p) as f:
        for row in csv.DictReader(f):
            key = f"{arm}__{metric}"
            if key in row and row[key] not in ("", None):
                out[_norm(row["apk"])] = float(row[key])
    return out


def compare(name, llm, wid):
    apks = sorted(set(llm) & set(wid))
    a = [llm[x] for x in apks]  # LLM arm
    b = [wid[x] for x in apks]  # widget baseline
    diffs = [x - y for x, y in zip(a, b)]
    wins = sum(d > 0 for d in diffs)
    losses = sum(d < 0 for d in diffs)
    if any(diffs):
        try:
            W, p = wilcoxon(a, b, zero_method="wilcox", alternative="two-sided")
        except ValueError:
            W, p = float("nan"), float("nan")
    else:
        W, p = float("nan"), 1.0
    print(f"  {name:28s} n={len(apks):3d}  meanLLM={st.mean(a):6.2f}  meanWID={st.mean(b):6.2f}  "
          f"Δ={st.mean(diffs):+6.2f}  win/lose={wins}/{losses}  p={p if p != p else round(p, 6)}")


def main():
    for metric in ["cov_mop", "cov_method"]:
        print(f"\n== {metric} :: LLM arm − widget baseline (Δ<0 = LLM pior) ==")
        base = load("cmpm_base", LLM_ARM, metric)
        v2 = load("cmpm_v2", LLM_ARM, metric)
        w300 = load("cmpft5", WID_ARM, metric)
        w600 = load("cmpv2w", WID_ARM, metric)
        compare("base  vs widget@300", base, w300)
        compare("v2    vs widget@300", v2, w300)
        compare("base  vs widget@600", base, w600)
        compare("v2    vs widget@600", v2, w600)


if __name__ == "__main__":
    main()

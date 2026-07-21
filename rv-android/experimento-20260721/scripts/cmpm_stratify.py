#!/usr/bin/env python3
"""Estratificação FLAG_SECURE (screenshot_failed) para cmpm base×v2.

Para cada APK mede a taxa de screenshot_failed/calls (média das reps) a partir
das linhas ``[APE-RV] LLM Summary`` dos traces. APKs com taxa alta = FLAG_SECURE
(o LLM não enxerga a tela → o braço degrada para sata_mop_widget e o modelo é
inerte): nesse estrato de CONTROLE base deve ≈ v2 (sanity check de confound
run-to-run). O estrato de TRATAMENTO (LLM ativo) carrega o efeito real.

Compara base↔v2 (cov_mop, cov_method) por estrato com Wilcoxon pareado.
"""
import csv
import json
import re
import statistics as st
from pathlib import Path

from scipy.stats import wilcoxon

RESULTS = Path(__file__).resolve().parent.parent / "results"
ARM = "aperv:sata_mop_llm_v13"
SUMMARY_RE = re.compile(r"\[APE-RV\] LLM Summary\b")
CTRL_THRESHOLD = 0.50  # >=50% dos calls com screenshot_failed => FLAG_SECURE/controle


def _norm(a):
    return a[:-4] if a.endswith(".apk") else a


def summary_fields(line):
    return {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", line)}


def screenshot_rate_by_apk(run):
    """apk -> (screenshot_failed_total, calls_total) somados nas reps."""
    agg = {}
    for tj in RESULTS.glob(f"{run}_*/**/tasks.json"):
        try:
            data = json.loads(tj.read_text())
        except Exception:
            continue
        tasks = data.get("tasks", data) if isinstance(data, dict) else data
        for t in tasks:
            cfg = t.get("config", {}) or {}
            res = t.get("result", {}) or {}
            apk = _norm(cfg.get("apk_name", ""))
            tf = res.get("trace_file")
            if not apk or not tf:
                continue
            p = Path(tf)
            if not p.is_absolute():
                p = tj.parent / tf
            if not p.exists():
                # tenta achar pelo basename sob o dir do run
                cands = list(tj.parent.glob(f"**/{Path(tf).name}"))
                if not cands:
                    continue
                p = cands[0]
            sf = calls = 0
            for line in p.read_text(encoding="latin-1", errors="replace").splitlines():
                if SUMMARY_RE.search(line):
                    f = summary_fields(line)
                    sf, calls = f.get("screenshot_failed", 0), f.get("calls", 0)
            s, c = agg.get(apk, (0, 0))
            agg[apk] = (s + sf, c + calls)
    return agg


def cov_by_apk(run, metric):
    p = RESULTS / f"{run}_consolidado" / "per_apk_paired.csv"
    out = {}
    with open(p) as f:
        for row in csv.DictReader(f):
            out[_norm(row["apk"])] = float(row[f"{ARM}__{metric}"])
    return out


def wil(t, b):
    diffs = [x - y for x, y in zip(t, b)]
    if not any(diffs):
        return float("nan"), 1.0
    try:
        return wilcoxon(t, b, zero_method="wilcox", alternative="two-sided")
    except ValueError:
        return float("nan"), float("nan")


def main():
    rate = screenshot_rate_by_apk("cmpm_v2")  # usa v2 p/ classificar (mesmos APKs)
    control, treatment = [], []
    for apk, (sf, calls) in rate.items():
        r = (sf / calls) if calls else 0.0
        (control if r >= CTRL_THRESHOLD else treatment).append(apk)

    print(f"APKs c/ telemetria: {len(rate)}")
    print(f"  CONTROLE (screenshot_failed>={CTRL_THRESHOLD:.0%}, FLAG_SECURE): {len(control)}")
    print(f"  TRATAMENTO (LLM ativo): {len(treatment)}")
    if control:
        print("  controle:", ", ".join(sorted(control)[:20]))

    for metric in ["cov_mop", "cov_method"]:
        cb, cv = cov_by_apk("cmpm_base", metric), cov_by_apk("cmpm_v2", metric)
        print(f"\n== {metric} ==")
        for name, grp in [("TRATAMENTO", treatment), ("CONTROLE", control)]:
            apks = sorted(a for a in grp if a in cb and a in cv)
            if not apks:
                print(f"  {name:10s} n=0  (estrato vazio)")
                continue
            b = [cb[a] for a in apks]
            t = [cv[a] for a in apks]
            W, p = wil(t, b)
            print(f"  {name:10s} n={len(apks):3d}  meanB={st.mean(b):6.2f}  meanV2={st.mean(t):6.2f}  "
                  f"Δ={st.mean(t) - st.mean(b):+6.2f}  p={p if p != p else round(p, 5)}")


if __name__ == "__main__":
    main()

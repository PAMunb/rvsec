#!/usr/bin/env python3
"""Consolidacao offline + Wilcoxon all-pairs de uma comparacao gerada por gen_compare.py.

Uso: consolidate_compare.py <name>

Regras (licoes da corrida 2026-06-19):
  - FONTE DA VERDADE = logcats; CSVs por container podem ter cobertura zerada em tasks
    resumidas se o <apk>.json nao estiver co-localizado (bug gh58). Aqui lemos tasks.json
    (coberturas + mop_unique) e logcats (mop_total).
  - DEDUP por identidade (apk,tool,variant,rep,timeout) — nunca por task_id (resume infla).
  - Pareamento: cada APK = media das R reps; Wilcoxon signed-rank em TODOS os pares de tools.

Metricas:
  cov_method = coverage_metrics.method_coverage
  cov_act    = coverage_metrics.activities_coverage
  cov_mop    = coverage_metrics.methods_mop_reachable_coverage
  mop_unique = coverage_metrics.total_errors  (violacoes distintas Spec,classe,metodo,tipo)
  mop_total  = nº de linhas 'RVSEC : <Spec>,...' no logcat
  crashes    = detected_errors_count

Saidas em data/results/<name>_consolidado/:
  per_task.csv, per_apk_paired.csv, per_tool_summary.csv, wilcoxon.csv
"""
import json, os, re, csv, sys, itertools
from pathlib import Path
from collections import defaultdict
import statistics as st

try:
    from scipy.stats import wilcoxon
except ImportError:
    sys.exit("scipy ausente — rode com: uv run python <este script> <name>")

ROOT = Path(__file__).resolve().parents[4]
RVSEC = re.compile(r'\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$')
METRICS = ["cov_method", "cov_act", "cov_mop", "mop_unique", "mop_total", "crashes"]
WMETRICS = ["cov_mop", "mop_unique", "cov_method", "mop_total"]


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else sys.exit("uso: consolidate_compare.py <name>")
    meta = json.loads((ROOT / "data" / "results" / f"{name}_compare_meta.json").read_text())
    containers, tools_order = meta["containers"], meta["tools"]
    # normaliza rotulos de tool: 'ape' ou 'aperv:<variant>' (sem @overrides).
    # Um spec pode carregar VARIOS variants ('aperv:v1:v2'), e cada variant e' um braco
    # separado no tasks.json. Sem expandir, o rotulo composto nao casa com nenhum registro,
    # 'tools' fica com um elemento so e o Wilcoxon all-pairs sai vazio. E' a mesma pegadinha
    # que obriga a corrigir 'n_tools' no meta a mao.
    def expand(label: str) -> list:
        parts = label.split(":")
        return [label] if len(parts) <= 2 else [f"{parts[0]}:{v}" for v in parts[1:]]

    tool_labels = [lbl for t in tools_order for lbl in expand(t.split("@")[0])]
    out = ROOT / "data" / "results" / f"{name}_consolidado"
    out.mkdir(parents=True, exist_ok=True)

    rows, seen = [], set()
    for i in range(containers):
        nn = f"{i:02d}"
        base = ROOT / "data" / "results" / f"{name}_{nn}" / f"{name}_{nn}"
        tj = base / "tasks.json"
        if not tj.exists():
            continue
        for t in json.loads(tj.read_text())["tasks"]:
            r = t.get("result") or {}
            if r.get("state") != "COMPLETED":
                continue
            c = t["config"]; tc = c["tool_config"]; variant = tc.get("variant")
            ident = (c["apk_name"], tc["name"], variant, c["repetition"], c["timeout"])
            if ident in seen:
                continue
            seen.add(ident)
            tool = "ape" if tc["name"] == "ape" else f"{tc['name']}:{variant}"
            cm = r.get("coverage_metrics") or {}
            tf = "ape" if tc["name"] == "ape" else f"{tc['name']}:{variant}"
            lc = base / c["apk_name"] / f'{c["apk_name"]}__{c["repetition"]}__{c["timeout"]}__{tf}.logcat'
            mop_total = 0
            try:
                with open(lc, errors="ignore") as fh:
                    mop_total = sum(1 for ln in fh if "RVSEC" in ln and RVSEC.search(ln))
            except FileNotFoundError:
                pass
            rows.append(dict(
                apk=c["apk_name"], rep=c["repetition"], tool=tool,
                cov_method=cm.get("method_coverage", 0) or 0,
                cov_act=cm.get("activities_coverage", 0) or 0,
                cov_mop=cm.get("methods_mop_reachable_coverage", 0) or 0,
                mop_unique=cm.get("total_errors", 0) or 0,
                mop_total=mop_total,
                crashes=r.get("detected_errors_count", 0) or 0,
            ))

    if not rows:
        sys.exit("nenhuma task COMPLETED encontrada")

    with open(out / "per_task.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    byat = defaultdict(lambda: defaultdict(list))
    for r in rows:
        for m in METRICS:
            byat[(r["apk"], r["tool"])][m].append(r[m])
    apk_tool = {k: {m: st.mean(v[m]) for m in METRICS} for k, v in byat.items()}
    apks = sorted({a for a, _ in apk_tool})
    tools = [t for t in tool_labels if any((a, t) in apk_tool for a in apks)]

    with open(out / "per_apk_paired.csv", "w", newline="") as f:
        cols = ["apk"] + [f"{t}__{m}" for t in tools for m in METRICS]
        w = csv.writer(f); w.writerow(cols)
        for apk in apks:
            row = [apk]
            for t in tools:
                d = apk_tool.get((apk, t), {})
                row += [round(d.get(m, float("nan")), 4) for m in METRICS]
            w.writerow(row)

    with open(out / "per_tool_summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tool", "n_apks"] + [f"{m}_mean" for m in METRICS] + [f"{m}_median" for m in METRICS])
        for t in tools:
            vals = {m: [apk_tool[(a, t)][m] for a in apks if (a, t) in apk_tool] for m in METRICS}
            w.writerow([t, len(vals["cov_mop"])]
                       + [round(st.mean(vals[m]), 3) for m in METRICS]
                       + [round(st.median(vals[m]), 3) for m in METRICS])

    wres = []
    for A, B in itertools.combinations(tools, 2):
        for m in WMETRICS:
            xs, ys = [], []
            for apk in apks:
                if (apk, A) in apk_tool and (apk, B) in apk_tool:
                    xs.append(apk_tool[(apk, A)][m]); ys.append(apk_tool[(apk, B)][m])
            diffs = [x - y for x, y in zip(xs, ys)]
            wins = sum(d > 0 for d in diffs); losses = sum(d < 0 for d in diffs)
            if any(d != 0 for d in diffs):
                try:
                    W, p = wilcoxon(xs, ys, zero_method="wilcox", alternative="two-sided")
                except ValueError:
                    W, p = float("nan"), float("nan")
            else:
                W, p = float("nan"), 1.0
            wres.append(dict(
                A=A, B=B, metric=m, n=len(xs),
                median_A=round(st.median(xs), 3) if xs else "nan",
                median_B=round(st.median(ys), 3) if ys else "nan",
                median_diff=round(st.median(diffs), 3) if diffs else "nan",
                wins_A=wins, losses_A=losses, ties=len(diffs) - wins - losses,
                W=(round(W, 1) if W == W else "nan"),
                p_value=(round(p, 5) if p == p else "nan"),
                significant=("sim" if (p == p and p < 0.05) else "nao"),
            ))
    with open(out / "wilcoxon.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(wres[0].keys())); w.writeheader(); w.writerows(wres)

    print(f"APKs pareados: {len(apks)} | tasks: {len(rows)} | tools: {tools}")
    print(f"CSVs em: {out}\n")
    print(f"{'A':22s} {'B':22s} {'metric':10s} {'medA':>7s} {'medB':>7s} {'A>B':>4s} {'A<B':>4s} {'p':>8s} sig")
    for r in wres:
        print(f"{r['A']:22s} {r['B']:22s} {r['metric']:10s} "
              f"{str(r['median_A']):>7s} {str(r['median_B']):>7s} {r['wins_A']:4d} {r['losses_A']:4d} "
              f"{str(r['p_value']):>8s} {r['significant']}")


if __name__ == "__main__":
    main()

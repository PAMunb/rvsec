#!/usr/bin/env python3
"""Consolidacao + analise pareada (Wilcoxon) da comparacao APE x APE-RV.

Le os tasks.json dos 6 containers (dedup por identidade), conta violacoes MOP
brutas dos logcats, faz media das 3 reps por APK (pareamento) e roda Wilcoxon
signed-rank pareado para H1/H2/H3. Salva 4 CSVs em data/results/comparacao_consolidado/.

Metricas:
  cov_method  = coverage_metrics.method_coverage
  cov_act     = coverage_metrics.activities_coverage
  cov_mop     = coverage_metrics.methods_mop_reachable_coverage  (PRIMARIA)
  mop_unique  = coverage_metrics.total_errors  (violacoes distintas Spec,classe,metodo,tipo)
  mop_total   = nº de eventos brutos 'RVSEC : <Spec>,...' no logcat
  crashes     = detected_errors_count
"""
import json, os, re, csv
from collections import defaultdict
import statistics as st
from scipy.stats import wilcoxon

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "data", "results")
OUT = os.path.join(RES, "comparacao_consolidado")
os.makedirs(OUT, exist_ok=True)
TOOLS = ["ape", "aperv:sata", "aperv:sata_mop", "aperv:sata_mop_llm"]
RVSEC = re.compile(r'\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$')

# ---------- 1. coleta por-task (dedup por identidade) ----------
rows = []          # uma linha por task
seen = set()
for n in ["00", "01", "02", "03", "04", "05"]:
    base = os.path.join(RES, f"cmp_{n}", f"cmp_{n}")
    tj = os.path.join(base, "tasks.json")
    if not os.path.exists(tj):
        continue
    for t in json.load(open(tj))["tasks"]:
        r = t.get("result") or {}
        if r.get("state") != "COMPLETED":
            continue
        c = t["config"]; tc = c["tool_config"]
        variant = tc.get("variant")
        ident = (c["apk_name"], tc["name"], variant, c["repetition"], c["timeout"])
        if ident in seen:
            continue
        seen.add(ident)
        tool = "ape" if tc["name"] == "ape" else f"aperv:{variant}"
        cm = r.get("coverage_metrics") or {}
        # eventos MOP brutos do logcat
        toolfile = "ape" if tc["name"] == "ape" else f"aperv:{variant}"
        lc = os.path.join(base, c["apk_name"],
                          f'{c["apk_name"]}__{c["repetition"]}__{c["timeout"]}__{toolfile}.logcat')
        mop_total = 0
        try:
            with open(lc, errors="ignore") as fh:
                for line in fh:
                    if "RVSEC" in line and RVSEC.search(line):
                        mop_total += 1
        except FileNotFoundError:
            mop_total = 0
        rows.append(dict(
            apk=c["apk_name"], rep=c["repetition"], tool=tool,
            cov_method=cm.get("method_coverage", 0) or 0,
            cov_act=cm.get("activities_coverage", 0) or 0,
            cov_mop=cm.get("methods_mop_reachable_coverage", 0) or 0,
            mop_unique=cm.get("total_errors", 0) or 0,
            mop_total=mop_total,
            crashes=r.get("detected_errors_count", 0) or 0,
        ))

# ---------- 2. CSV por-task ----------
with open(os.path.join(OUT, "per_task.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

# ---------- 3. media das 3 reps por (apk, tool) ----------
METRICS = ["cov_method", "cov_act", "cov_mop", "mop_unique", "mop_total", "crashes"]
byat = defaultdict(lambda: defaultdict(list))
for r in rows:
    for m in METRICS:
        byat[(r["apk"], r["tool"])][m].append(r[m])
apk_tool = {k: {m: st.mean(v[m]) for m in METRICS} for k, v in byat.items()}
apks = sorted({a for a, _ in apk_tool})

# ---------- 4. CSV pareado por APK (wide) ----------
with open(os.path.join(OUT, "per_apk_paired.csv"), "w", newline="") as f:
    cols = ["apk"] + [f"{t}__{m}" for t in TOOLS for m in METRICS]
    w = csv.writer(f); w.writerow(cols)
    for apk in apks:
        row = [apk]
        for t in TOOLS:
            d = apk_tool.get((apk, t), {})
            row += [round(d.get(m, float("nan")), 4) for m in METRICS]
        w.writerow(row)

# ---------- 5. CSV resumo por tool (sobre as 169 medias-por-APK) ----------
with open(os.path.join(OUT, "per_tool_summary.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["tool", "n_apks"] + [f"{m}_mean" for m in METRICS] + [f"{m}_median" for m in METRICS])
    for t in TOOLS:
        vals = {m: [apk_tool[(a, t)][m] for a in apks if (a, t) in apk_tool] for m in METRICS}
        nap = len(vals["cov_mop"])
        w.writerow([t, nap]
                   + [round(st.mean(vals[m]), 3) for m in METRICS]
                   + [round(st.median(vals[m]), 3) for m in METRICS])

# ---------- 6. Wilcoxon pareado ----------
def paired(a_tool, b_tool, metric):
    xs, ys = [], []
    for apk in apks:
        ka, kb = (apk, a_tool), (apk, b_tool)
        if ka in apk_tool and kb in apk_tool:
            xs.append(apk_tool[ka][metric]); ys.append(apk_tool[kb][metric])
    return xs, ys

COMPARISONS = [
    ("H1", "ape", "aperv:sata", "p>0.05 (equivalencia)"),
    ("H2", "aperv:sata_mop", "ape", "p<0.05 (ganho)"),
    ("H2", "aperv:sata_mop", "aperv:sata", "p<0.05 (ganho)"),
    ("H3", "aperv:sata_mop_llm", "aperv:sata_mop", "exploratoria"),
]
WMETRICS = ["cov_mop", "mop_unique", "cov_method", "mop_total"]

wres = []
for hyp, A, B, expect in COMPARISONS:
    for m in WMETRICS:
        xs, ys = paired(A, B, m)
        diffs = [x - y for x, y in zip(xs, ys)]
        nz = [d for d in diffs if d != 0]
        wins = sum(1 for d in diffs if d > 0)
        losses = sum(1 for d in diffs if d < 0)
        if len(nz) >= 1:
            try:
                W, p = wilcoxon(xs, ys, zero_method="wilcox", alternative="two-sided")
            except ValueError:
                W, p = float("nan"), float("nan")
        else:
            W, p = float("nan"), 1.0
        wres.append(dict(
            hypothesis=hyp, A=A, B=B, metric=m, n=len(xs),
            median_A=round(st.median(xs), 3), median_B=round(st.median(ys), 3),
            median_diff=round(st.median(diffs), 3),
            mean_diff=round(st.mean(diffs), 3),
            wins_A=wins, losses_A=losses, ties=len(diffs) - len(nz),
            W=round(W, 1) if W == W else "nan",
            p_value=round(p, 5) if p == p else "nan",
            significant=("sim" if (p == p and p < 0.05) else "nao"),
            expectativa=expect,
        ))

with open(os.path.join(OUT, "wilcoxon.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(wres[0].keys()))
    w.writeheader(); w.writerows(wres)

# ---------- 7. echo no stdout ----------
print(f"APKs pareados: {len(apks)} | tasks: {len(rows)}")
print(f"CSVs salvos em: {OUT}\n")
print("=== Wilcoxon pareado por APK (media das 3 reps) ===")
hdr = f"{'H':3s} {'A':18s} {'B':18s} {'metric':10s} {'medA':>7s} {'medB':>7s} {'dif':>7s} {'A>B':>4s} {'A<B':>4s} {'p':>8s} {'sig':>3s}"
print(hdr)
for r in wres:
    print(f"{r['hypothesis']:3s} {r['A']:18s} {r['B']:18s} {r['metric']:10s} "
          f"{r['median_A']:7.2f} {r['median_B']:7.2f} {r['median_diff']:7.2f} "
          f"{r['wins_A']:4d} {r['losses_A']:4d} {str(r['p_value']):>8s} {r['significant']:>3s}")

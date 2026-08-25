#!/usr/bin/env python3
"""Consolidação offline da gh104: tasks.json + logcats -> CSVs em consolidado/.

    uv run python scripts/consolidate.py

CÓPIA de `../../experimento-comp162/scripts/consolidate.py`. Mudou o prefixo dos diretórios
de resultado (`comp162_NN` -> `gh104_NN`) e nada mais: as colunas, a agregação e a
identidade de dedupe têm de ser idênticas às da campanha de referência, senão o pareamento
entre as duas compara coisas diferentes com o mesmo nome. Toda mudança de métrica aqui
seria uma segunda diferença entre as campanhas, onde o desenho admite uma só — o conjunto
de specs.

O que continua valendo do original:

1. Os resultados moram em `experimento-gh104/results/`, não em `data/results/<name>_NN`,
   e não há `_compare_meta.json` — os braços vêm do `manifest.json`.
2. `per_rep.csv` guarda uma linha por identidade; é o único CSV em que uma réplica ainda é
   distinguível da outra, e o insumo do `analise.py` para o desvio-padrão entre réplicas.

Uma advertência específica desta campanha: `mop_total` conta linhas `RVSEC:` no logcat, e a
contagem muda por QUATRO forças simultâneas entre as duas eras de spec — allow-lists que
removem eventos, remoção do `reset` do `MessageDigestSpec`, identidade de dedupe que passa
de 5 para 7 campos, e guardas por predicado que voltam a rodar. Elas não são separáveis a
posteriori a partir deste CSV. Ler uma diferença de `mop_total` sem nomear a qual dessas
causas ela é atribuída é leitura errada; `msg_diff.py` é quem faz essa atribuição.

A FONTE DA VERDADE das coberturas é o `tasks.json`, e a de `mop_total` é o logcat (gh58):
o CSV por container pode ter cobertura zerada em task resumida se o `<apk>.json` não
resolver.
"""

from __future__ import annotations

import csv
import itertools
import json
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

try:
    from scipy.stats import wilcoxon
except ImportError:
    sys.exit("scipy ausente — rode com: uv run python scripts/consolidate.py")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from admissibility import arm_label  # noqa: E402

EXP = Path(__file__).resolve().parents[1]
RESULTS = EXP / "results"
OUT = EXP / "consolidado"
MANIFEST = json.loads((EXP / "manifest.json").read_text())

RVSEC = re.compile(r"\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$")
METRICS = ["cov_method", "cov_act", "cov_mop", "mop_unique", "mop_total", "crashes"]
WMETRICS = ["cov_mop", "mop_unique", "cov_method", "cov_act", "mop_total"]

# O rótulo de braço vem de `admissibility.arm_label` e de nenhum outro lugar. Ele decide o
# nome da coluna nos CSVs, a chave do julgamento de admissibilidade E o nome do arquivo de
# logcat que este script abre para contar `mop_total` — se as três leituras discordassem, o
# braço `ape` contaria zero violação em silêncio, porque o arquivo dele se chama
# `..__ape.logcat` e não `..__ape:default.logcat`.
ARMS = [arm_label(a["tool"], a["variant"]) for a in MANIFEST["arms"]]
CONTAINERS = MANIFEST["containers"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    rows, seen = [], set()
    for i in range(CONTAINERS):
        nn = f"gh104_{i:02d}"
        base = RESULTS / nn / nn
        tj = base / "tasks.json"
        if not tj.exists():
            print(f"aviso: {tj} ausente", file=sys.stderr)
            continue
        doc = json.loads(tj.read_text())
        for t in (doc["tasks"] if isinstance(doc, dict) else doc):
            r = t.get("result") or {}
            if r.get("state") != "COMPLETED":
                continue
            c = t["config"]
            tc = c["tool_config"]
            variant = tc.get("variant")
            # Dedup por identidade — nunca por task_id, que o resume infla com UUID novo.
            ident = (c["apk_name"], tc["name"], variant, c["repetition"], c["timeout"])
            if ident in seen:
                continue
            seen.add(ident)
            tool = arm_label(tc["name"], variant)
            cm = r.get("coverage_metrics") or {}
            lc = (base / c["apk_name"] /
                  f'{c["apk_name"]}__{c["repetition"]}__{c["timeout"]}__{tool}.logcat')
            mop_total = 0
            try:
                with open(lc, errors="ignore") as fh:
                    mop_total = sum(1 for ln in fh if "RVSEC" in ln and RVSEC.search(ln))
            except FileNotFoundError:
                pass
            rows.append(dict(
                apk=c["apk_name"], rep=c["repetition"], tool=tool, container=nn,
                elapsed_s=r.get("execution_time_seconds") or 0,
                cov_method=cm.get("method_coverage", 0) or 0,
                cov_act=cm.get("activities_coverage", 0) or 0,
                cov_mop=cm.get("methods_mop_reachable_coverage", 0) or 0,
                mop_unique=cm.get("total_errors", 0) or 0,
                mop_total=mop_total,
                crashes=r.get("detected_errors_count", 0) or 0,
            ))

    if not rows:
        sys.exit("nenhuma task COMPLETED encontrada")

    # per_rep.csv: uma linha por identidade. É o insumo da dispersão entre réplicas e da
    # admissibilidade, e o único CSV em que uma réplica ainda é distinguível da outra.
    with (OUT / "per_rep.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    byat = defaultdict(lambda: defaultdict(list))
    for r in rows:
        for m in METRICS:
            byat[(r["apk"], r["tool"])][m].append(r[m])
    apk_tool = {k: {m: st.mean(v[m]) for m in METRICS} for k, v in byat.items()}
    n_reps = {k: len(v["cov_method"]) for k, v in byat.items()}
    apks = sorted({a for a, _ in apk_tool})
    tools = [t for t in ARMS if any((a, t) in apk_tool for a in apks)]

    # per_apk_paired.csv: o valor por aplicação é a MÉDIA das réplicas. É a unidade do
    # teste pareado e a mesma agregação da comp162, para que as duas campanhas possam ser
    # pareadas entre si sem assimetria de definição.
    with (OUT / "per_apk_paired.csv").open("w", newline="") as f:
        cols = ["apk"] + [f"{t}__{m}" for t in tools for m in METRICS] + \
               [f"{t}__n_reps" for t in tools]
        w = csv.writer(f)
        w.writerow(cols)
        for apk in apks:
            row = [apk]
            for t in tools:
                d = apk_tool.get((apk, t), {})
                row += [round(d.get(m, float("nan")), 4) for m in METRICS]
            row += [n_reps.get((apk, t), 0) for t in tools]
            w.writerow(row)

    with (OUT / "per_tool_summary.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tool", "n_apks"] + [f"{m}_mean" for m in METRICS]
                   + [f"{m}_median" for m in METRICS])
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
                    xs.append(apk_tool[(apk, A)][m])
                    ys.append(apk_tool[(apk, B)][m])
            diffs = [x - y for x, y in zip(xs, ys)]
            wins = sum(d > 0 for d in diffs)
            losses = sum(d < 0 for d in diffs)
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
    with (OUT / "wilcoxon.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(wres[0].keys()))
        w.writeheader()
        w.writerows(wres)

    incompletas = [(k, n) for k, n in n_reps.items() if n != MANIFEST["reps"]]
    print(f"APKs: {len(apks)} | identidades: {len(rows)} | braços: {tools}")
    print(f"CSVs em: {OUT}")
    if incompletas:
        print(f"\nAVISO: {len(incompletas)} células com número de réplicas != {MANIFEST['reps']}:")
        for (apk, tool), n in sorted(incompletas)[:15]:
            print(f"  {apk[:40]:40s} {tool:24s} {n} réplica(s)")
        print("  (a média por aplicação fica sobre menos réplicas nessas células —")
        print("   `analise.py` decide o que fazer com elas)")
    print()
    print(f"{'A':24s} {'B':24s} {'metric':11s} {'medA':>8s} {'medB':>8s} "
          f"{'A>B':>4s} {'A<B':>4s} {'p':>9s} sig")
    for r in wres:
        print(f"{r['A']:24s} {r['B']:24s} {r['metric']:11s} "
              f"{str(r['median_A']):>8s} {str(r['median_B']):>8s} "
              f"{r['wins_A']:4d} {r['losses_A']:4d} {str(r['p_value']):>9s} {r['significant']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

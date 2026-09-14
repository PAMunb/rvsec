#!/usr/bin/env python3
"""Consolidacao offline + Wilcoxon all-pairs de uma comparacao gerada por gen_compare.py.

Uso: consolidate_compare.py <name> [--admissibility veredictos.json]

Regras (licoes das corridas 2026-06-19 e 2026-09-14):
  - FONTE DA VERDADE = logcats; CSVs por container podem ter cobertura zerada em tasks
    resumidas se o <apk>.json nao estiver co-localizado (bug gh58). Aqui lemos tasks.json
    (coberturas + mop_unique) e logcats (mop_total, mop_unique4, crashes, anrs).
  - O logcat de cada identidade e' o que `result.logcat_file` aponta, nunca um nome montado:
    os bracos sem variante gravam `variant='default'` no indice e `__monkey.logcat` no disco,
    e um nome montado com `:default` nao existe. Logcat ausente ABORTA a consolidacao em vez
    de virar zero — zero que nao foi medido nao entra em media nenhuma.
  - DEDUP por identidade (apk,tool,variant,rep,timeout) — nunca por task_id (resume infla).
    Fica o ULTIMO registro COMPLETED, o mesmo que `admissibility.py` julga.
  - Pareamento: cada APK = media das R reps; Wilcoxon signed-rank em TODOS os pares de tools.

Metricas por identidade (per_task.csv):
  cov_method  = coverage_metrics.method_coverage
  cov_act     = coverage_metrics.activities_coverage
  cov_mop     = coverage_metrics.methods_mop_reachable_coverage
  mop_unique  = coverage_metrics.total_errors — chave de SETE partes de `RvErrorLog.unique_msg`
                (class:::method:::spec:::error_type:::code:::event:::message)
  mop_unique4 = |{(class, method, spec)}| recontado do logcat — a chave de QUATRO partes
                (apk, class, method, spec) que o artigo chama de "unique misuse". As duas
                convivem porque nao sao numericamente comparaveis (mop_unique ~ 2,4 x mop_unique4
                na estudo02) e qualquer numero publicado tem de dizer a qual pertence.
  mop_total   = nº de linhas 'RVSEC : <spec>,...' no logcat (o nome da spec pode ter digitos:
                X509EncodedKeySpecSpec, MGF1ParameterSpecSpec)
  crashes     = nº de 'FATAL EXCEPTION' no logcat (o campo detected_errors_count do indice
                nunca e' preenchido pelo pipeline e sai 0 por construcao)
  anrs        = nº de 'ANR in' no logcat
  sa_methods_reaches_mop = metodos do modelo estatico (<apk>.json co-localizado) que alcancam
                uma API monitorada — a covariavel log(...) do modelo binomial negativo do artigo;
                recomputada aqui porque depende do conjunto de specs da campanha.
  tool_seconds = end_time - tool_execution_start (exposicao real; o offset do modelo, nao o orcamento)
  + colunas de admissibilidade (admissible, category, fails) quando --admissibility e' dado;
    elas sao COLUNAS, a agregacao nao filtra por elas — excluir e' decisao humana.

Saidas em data/results/<name>_consolidado/:
  per_task.csv, per_apk_static.csv, per_apk_paired.csv, per_tool_summary.csv, wilcoxon.csv
"""
import argparse, json, os, re, csv, sys, itertools
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from multiprocessing import Pool
import statistics as st

try:
    from scipy.stats import wilcoxon
except ImportError:
    sys.exit("scipy ausente — rode com: uv run python <este script> <name>")

ROOT = Path(__file__).resolve().parents[4]
# Linha de violacao: 'RVSEC : spec,classe,classeSimples,metodo,local,tipo,mensagem' (ErrorSummary.java).
RVSEC = re.compile(r'\bRVSEC\s*:\s*([^,\s]+,.+)$')
METRICS = ["cov_method", "cov_act", "cov_mop", "mop_unique", "mop_unique4", "mop_total", "crashes", "anrs"]
WMETRICS = ["cov_mop", "mop_unique", "mop_unique4", "cov_method", "mop_total"]


def tool_label(tc: dict) -> str:
    """`ape` e os bracos sem variante real (`variant='default'`) viram o nome seco."""
    variant = tc.get("variant")
    return tc["name"] if tc["name"] == "ape" or not variant or variant == "default" \
        else f"{tc['name']}:{variant}"


def scan_logcat(path: str) -> dict:
    """Uma passagem pelo logcat: mop_total, mop_unique4, crashes, anrs."""
    total, crashes, anrs, keys4 = 0, 0, 0, set()
    with open(path, errors="ignore") as fh:
        for ln in fh:
            if "RVSEC" in ln:
                m = RVSEC.search(ln)
                if m:
                    total += 1
                    p = m.group(1).split(",", 4)
                    if len(p) >= 4:
                        keys4.add((p[1], p[3], p[0]))
            elif "FATAL EXCEPTION" in ln:
                crashes += 1
            elif "ANR in" in ln:
                anrs += 1
    return dict(mop_total=total, mop_unique4=len(keys4), crashes=crashes, anrs=anrs)


def tool_seconds(r: dict) -> int:
    """`end_time - tool_execution_start`: o tempo em que a ferramenta rodou. `execution_time_seconds`
    e' a tarefa inteira (boot, instalacao, teardown; ~53 s a mais) e nao serve de exposicao."""
    start, end = r.get("tool_execution_start"), r.get("end_time")
    if not start or not end:
        return int(r.get("execution_time_seconds") or 0)
    return int((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds())


def static_covariate(path: Path) -> dict:
    """`sa_methods` e `sa_methods_reaches_mop` do <apk>.json (GATOR): metodos cujo
    `reachesTarget` e' verdadeiro alcancam uma API monitorada pelo conjunto de specs da campanha."""
    d = json.loads(path.read_text())
    methods = [m for c in d.get("reachability") or [] for m in (c.get("methods") or [])]
    return dict(sa_methods=len(methods),
                sa_methods_reaches_mop=sum(1 for m in methods if m.get("reachesTarget")))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("name")
    ap.add_argument("--admissibility", metavar="JSON",
                    help="veredictos de experimento-estudo02/scripts/admissibility.py --json; "
                         "entram como colunas de per_task.csv")
    args = ap.parse_args()
    name = args.name
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

    best, statics = {}, {}
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
            c = t["config"]; tc = c["tool_config"]
            ident = (c["apk_name"], tc["name"], tc.get("variant"), c["repetition"], c["timeout"])
            # O container escreve `results/<cid>/<apk>/<arquivo>` relativo ao seu workdir; no
            # host isso vive sob data/results/<cid>/<cid>/. Sem `logcat_file` (indices antigos)
            # o nome e' montado com o rotulo ja colapsado.
            rel = r.get("logcat_file")
            lc = base / rel.replace(f"results/{name}_{nn}/", "", 1) if rel else \
                base / c["apk_name"] / f'{c["apk_name"]}__{c["repetition"]}__{c["timeout"]}__{tool_label(tc)}.logcat'
            best[ident] = (c, r, lc)
            if c["apk_name"] not in statics:
                statics[c["apk_name"]] = base / c["apk_name"] / f'{c["apk_name"]}.json'

    if not best:
        sys.exit("nenhuma task COMPLETED encontrada")
    missing = sorted(str(lc) for _, _, lc in best.values() if not lc.exists())
    if missing:
        sys.exit(f"{len(missing)} logcat(s) ausentes — nada consolidado. Primeiros:\n  "
                 + "\n  ".join(missing[:10]))
    missing = sorted(str(p) for p in statics.values() if not p.exists())
    if missing:
        sys.exit(f"{len(missing)} <apk>.json ausentes — nada consolidado. Primeiros:\n  "
                 + "\n  ".join(missing[:10]))

    idents = sorted(best)
    with Pool(max(1, (os.cpu_count() or 2) // 2)) as pool:
        scans = pool.map(scan_logcat, [str(best[i][2]) for i in idents], chunksize=64)
    covariates = {apk: static_covariate(p) for apk, p in statics.items()}

    verdicts = json.loads(Path(args.admissibility).read_text()) if args.admissibility else None
    rows = []
    for ident, scan in zip(idents, scans):
        c, r, _ = best[ident]; tc = c["tool_config"]; tool = tool_label(tc)
        cm = r.get("coverage_metrics") or {}
        row = dict(
            apk=c["apk_name"], timeout=c["timeout"], rep=c["repetition"], tool=tool,
            cov_method=cm.get("method_coverage", 0) or 0,
            cov_act=cm.get("activities_coverage", 0) or 0,
            cov_mop=cm.get("methods_mop_reachable_coverage", 0) or 0,
            mop_unique=cm.get("total_errors", 0) or 0,
            **scan,
            tool_seconds=tool_seconds(r),
            **covariates[c["apk_name"]],
        )
        if verdicts is not None:
            v = verdicts.get(f'{c["apk_name"]}|{tool}|{c["repetition"]}|{c["timeout"]}') or {}
            row["category"] = ("estrutural" if v.get("structural") else
                               "parada_ferramenta" if v.get("tool_stop") else
                               "lancamento_externo" if v.get("foreign_launcher") else
                               "inadmissivel" if v.get("fails") else
                               "admissivel" if v else "sem_veredicto")
            row["admissible"] = int(row["category"] == "admissivel")
            row["fails"] = "+".join(v.get("fails") or [])
        rows.append(row)

    with open(out / "per_task.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with open(out / "per_apk_static.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["apk", "sa_methods", "sa_methods_reaches_mop"])
        for apk in sorted(covariates):
            w.writerow([apk, covariates[apk]["sa_methods"], covariates[apk]["sa_methods_reaches_mop"]])
    if verdicts is not None:
        cats = defaultdict(int)
        for row in rows:
            cats[row["category"]] += 1
        print("admissibilidade (colunas, nao filtro):", dict(cats))

    # A unidade pareada e' (apk, timeout): a media das reps so' faz sentido dentro do mesmo
    # orcamento. Numa campanha com varios timeouts na mesma corrida (RV_TIMEOUTS em lista),
    # juntar 60 s com 300 s na mesma media compararia orcamentos, nao ferramentas.
    byat = defaultdict(lambda: defaultdict(list))
    for r in rows:
        for m in METRICS:
            byat[(r["apk"], r["timeout"], r["tool"])][m].append(r[m])
    apk_tool = {k: {m: st.mean(v[m]) for m in METRICS} for k, v in byat.items()}
    units = sorted({(a, to) for a, to, _ in apk_tool})
    timeouts = sorted({to for _, to in units})
    tools = [t for t in tool_labels if any((a, to, t) in apk_tool for a, to in units)]

    with open(out / "per_apk_paired.csv", "w", newline="") as f:
        cols = ["apk", "timeout"] + [f"{t}__{m}" for t in tools for m in METRICS]
        w = csv.writer(f); w.writerow(cols)
        for apk, to in units:
            row = [apk, to]
            for t in tools:
                d = apk_tool.get((apk, to, t), {})
                row += [round(d.get(m, float("nan")), 4) for m in METRICS]
            w.writerow(row)

    with open(out / "per_tool_summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tool", "timeout", "n_apks"] + [f"{m}_mean" for m in METRICS] + [f"{m}_median" for m in METRICS])
        for to in timeouts:
            for t in tools:
                vals = {m: [apk_tool[(a, to, t)][m] for a, x in units if x == to and (a, to, t) in apk_tool]
                        for m in METRICS}
                if not vals["cov_mop"]:
                    continue
                w.writerow([t, to, len(vals["cov_mop"])]
                           + [round(st.mean(vals[m]), 3) for m in METRICS]
                           + [round(st.median(vals[m]), 3) for m in METRICS])

    wres = []
    for to in timeouts:
      for A, B in itertools.combinations(tools, 2):
        for m in WMETRICS:
            xs, ys = [], []
            for apk, x in units:
                if x == to and (apk, to, A) in apk_tool and (apk, to, B) in apk_tool:
                    xs.append(apk_tool[(apk, to, A)][m]); ys.append(apk_tool[(apk, to, B)][m])
            if not xs:
                continue
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
                timeout=to, A=A, B=B, metric=m, n=len(xs),
                median_A=round(st.median(xs), 3) if xs else "nan",
                median_B=round(st.median(ys), 3) if ys else "nan",
                median_diff=round(st.median(diffs), 3) if diffs else "nan",
                wins_A=wins, losses_A=losses, ties=len(diffs) - wins - losses,
                W=(round(W, 1) if W == W else "nan"),
                p_value=(round(p, 5) if p == p else "nan"),
                significant=("sim" if (p == p and p < 0.05) else "nao"),
            ))
    # Uma campanha de UM braco nao tem par intra-campanha: `combinations` devolve vazio e o
    # Wilcoxon nao tem o que comparar. Nao e' erro — e' o desenho (o contraste dessas campanhas
    # atravessa campanhas, como em `experimento-cal163/scripts/pair_gh104.py`). Sem esta guarda
    # o script escrevia os tres CSVs reais e morria na ultima linha, com um `wilcoxon.csv` vazio
    # deixado para tras: parece falha da consolidacao, e nao e'.
    if wres:
        with open(out / "wilcoxon.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(wres[0].keys())); w.writeheader(); w.writerows(wres)

    print(f"unidades (apk, timeout) pareadas: {len(units)} | timeouts: {timeouts} | "
          f"tasks: {len(rows)} | tools: {tools}")
    print(f"CSVs em: {out}\n")
    if not wres:
        print("braco unico: sem contraste intra-campanha (wilcoxon.csv nao escrito)")
        return
    print(f"{'T':>4s} {'A':22s} {'B':22s} {'metric':10s} {'medA':>7s} {'medB':>7s} {'A>B':>4s} {'A<B':>4s} {'p':>8s} sig")
    for r in wres:
        print(f"{r['timeout']:4d} {r['A']:22s} {r['B']:22s} {r['metric']:10s} "
              f"{str(r['median_A']):>7s} {str(r['median_B']):>7s} {r['wins_A']:4d} {r['losses_A']:4d} "
              f"{str(r['p_value']):>8s} {r['significant']}")


if __name__ == "__main__":
    main()

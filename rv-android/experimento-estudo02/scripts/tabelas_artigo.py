#!/usr/bin/env python3
"""The four per-tool tables of the article (tabs/jca-violations-unique, jca-violations, coverage,
coverage_mop), recomputed for estudo02 and printed next to the published values.

Aggregation is the article's: per app, the mean across the three repetitions; then, per
(tool, timeout), the SUM over apps for misuse counts and the MEAN over apps for coverages.

Sources: data/results/estudo02_consolidado/per_task.csv (mop_unique4 = distinct (class,
method, spec) per run — the article's key; mop_total = violation lines; cov_method) and
summary.csv (cov_directly_reaches_target = the article's cov_directly_reaches_mop). The
published numbers are parsed from the article's tabs/*.tex, read-only.

    uv run python experimento-estudo02/scripts/tabelas_artigo.py > experimento-estudo02/docs/20260914_tabelas_por_ferramenta.md
"""
import csv, re, statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONS = ROOT / "data" / "results" / "estudo02_consolidado"
ARTICLE = Path("/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/tabs")
TOOLS = ["ape", "ares", "droidbot:bfs_greedy", "droidbot:bfs_naive", "droidbot:dfs_greedy",
         "droidbot:dfs_naive", "droidmate", "fastbot", "humanoid", "monkey", "qtesting"]
TIMEOUTS = (60, 180, 300)


def article_table(name: str) -> dict:
    """{tool: {timeout: value}} from a tabs/*.tex file of the article."""
    out = {}
    for line in (ARTICLE / f"{name}.tex").read_text().splitlines():
        m = re.match(r"([\w:\\_]+) & ([\d.]+) & ([\d.]+) & ([\d.]+)", line)
        if m:
            out[m.group(1).replace("\\_", "_")] = dict(zip(TIMEOUTS, map(float, m.groups()[1:])))
    return out


def load() -> dict:
    """{(apk, tool, timeout): {metric: [3 values]}} from per_task.csv + summary.csv."""
    cells = defaultdict(lambda: defaultdict(list))
    for r in csv.DictReader(open(CONS / "per_task.csv")):
        c = cells[(r["apk"], r["tool"], int(r["timeout"]))]
        for m in ("mop_unique4", "mop_unique", "mop_total", "cov_method"):
            c[m].append(float(r[m]))
    for r in csv.DictReader(open(CONS / "summary.csv")):
        cells[(r["apk"], r["tool"], int(r["timeout"]))]["cov_mop"].append(float(r["cov_directly_reaches_target"] or 0))
    return cells


def aggregate(cells: dict, metric: str, how: str) -> dict:
    """Per-app mean of the reps, then SUM or MEAN over apps, per (tool, timeout)."""
    per_app = defaultdict(list)
    for (apk, tool, to), c in cells.items():
        per_app[(tool, to)].append(statistics.mean(c[metric]))
    f = sum if how == "sum" else statistics.mean
    return {tool: {to: f(per_app[(tool, to)]) for to in TIMEOUTS} for tool in TOOLS}


def emit(title: str, note: str, ours: dict, theirs: dict, fmt: str, gain: bool) -> None:
    print(f"### {title}\n\n{note}\n")
    head = "| ferramenta | 60 s | 180 s | 300 s |" + (" ganho 300/60 |" if gain else "") + " artigo 60 | artigo 180 | artigo 300 |"
    print(head)
    print("|---|" + "---:|" * (head.count("|") - 2))
    for tool in TOOLS:
        o, t = ours[tool], theirs.get(tool, {})
        row = [tool] + [fmt % o[to] for to in TIMEOUTS]
        if gain:
            row.append("%.1f %%" % (100 * (o[300] - o[60]) / o[60]) if o[60] else "—")
        row += [fmt % t[to] if to in t else "—" for to in TIMEOUTS]
        print("| " + " | ".join(row) + " |")
    print()


def main() -> None:
    cells = load()
    n_apks = len({k[0] for k in cells})
    print(f"# Tabelas por ferramenta — estudo02 (`jca_android`) ao lado do artigo (`jca`)\n")
    print(f"Agregação do artigo: média das 3 repetições por app; depois soma (contagens) ou média "
          f"(coberturas) sobre os {n_apks} apps. Valores da campanha vêm de `estudo02_consolidado/` "
          f"(todas as 16 137 identidades, sem filtro de admissibilidade); os do artigo, de "
          f"`ase-journal/tabs/*.tex`. O corpus tem 162 apps em comum; o monkey roda com "
          f"`ignore_crashes/ignore_timeouts` só na campanha.\n")
    emit("Maus usos únicos por ferramenta e orçamento",
         "Chave do artigo, `(apk, classe, método, spec)` por execução (`mop_unique4`). Soma sobre apps.",
         aggregate(cells, "mop_unique4", "sum"), article_table("jca-violations-unique"), "%.0f", True)
    emit("Eventos de violação por ferramenta e orçamento",
         "Linhas `RVSEC` no logcat (`mop_total`). Soma sobre apps.",
         aggregate(cells, "mop_total", "sum"), article_table("jca-violations"), "%.0f", True)
    emit("Cobertura de métodos (%)",
         "`cov_method`, média sobre apps.",
         aggregate(cells, "cov_method", "mean"), article_table("coverage"), "%.2f", False)
    emit("Cobertura de métodos que alcançam diretamente API monitorada (%)",
         "`cov_directly_reaches_target` do `summary.csv` regerado (= `cov_directly_reaches_mop` do artigo), média sobre apps.",
         aggregate(cells, "cov_mop", "mean"), article_table("coverage_mop"), "%.2f", False)
    emit("Maus usos únicos, chave de sete partes da campanha (sem equivalente no artigo)",
         "`mop_unique` = `coverage_metrics.total_errors` (`class:::method:::spec:::error_type:::code:::event:::message`). Soma sobre apps. Não comparável ao artigo.",
         aggregate(cells, "mop_unique", "sum"), {}, "%.0f", True)


if __name__ == "__main__":
    main()

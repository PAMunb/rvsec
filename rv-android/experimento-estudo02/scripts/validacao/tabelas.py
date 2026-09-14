#!/usr/bin/env python3
"""G3, Z4, R1, R2, R3 and E2 over the regenerated estudo02 tables.

Reads only `data/results/estudo02_consolidado/` (summary.csv, errors.csv, per_task.csv,
per_apk_paired.csv, per_tool_summary.csv, per_apk_static.csv). Thresholds are the ones
declared in `docs/20260914_validacao_execucao.md` before this script first ran; each
detector prints PASS or the offending rows, and the full offender lists go to
`$VALIDACAO_DIR/tabelas_<detector>.tsv`.

Identity is (apk, tool, rep, timeout) with the collapsed tool label that both the
consolidator and the exporter write (`monkey`, `droidbot:dfs_naive`).
"""
import csv
import os
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TABLES = ROOT / "data" / "results" / "estudo02_consolidado"
OUT = Path(os.environ.get("VALIDACAO_DIR", "."))
csv.field_size_limit(sys.maxsize)

N_APKS, N_ARMS, N_REPS = 163, 11, 3
PAIRED_METRICS = ["cov_method", "cov_act", "cov_mop", "mop_unique", "mop_unique4", "mop_total", "crashes", "anrs"]
Z4_TASK = PAIRED_METRICS + ["tool_seconds"]
Z4_SUMMARY = ["cov_act", "cov_class", "cov_method", "cov_reachable", "cov_reaches_target",
              "cov_directly_reaches_target", "mop_errors_total", "mop_errors_unique",
              "classes_total", "methods_total", "unmatched_out_of_scope", "unmatched_in_scope"]
R1_TOL, R2_TOL = 5e-5, 5e-4
R3_KNOWN = {"traficparis", "moememos"}
E2_COV, E2_OUT = 1.0, 100


def read(name):
    with open(TABLES / name, newline="") as f:
        return list(csv.DictReader(f))


def ident(r):
    return (r["apk"], r["tool"], int(r["rep"]), int(r["timeout"]))


def dump(name, header, rows):
    with open(OUT / f"tabelas_{name}.tsv", "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(header)
        w.writerows(rows)


def verdict(tag, bad, detail=""):
    print(f"{tag}: {'PASS' if not bad else 'ACUSA'} {detail}")


def g3(summary, static):
    by_apk = defaultdict(list)
    for r in summary:
        by_apk[r["apk"]].append(r)
    bad, secondary = [], []
    for apk, rows in sorted(by_apk.items()):
        pairs = Counter((r["classes_total"], r["methods_total"]) for r in rows)
        if len(pairs) != 1 or len(rows) != N_ARMS * N_REPS * 3:
            bad.append((apk, len(rows), dict(pairs)))
        ((_, methods), _), = pairs.most_common(1)
        if methods != static[apk]["sa_methods"]:
            secondary.append((apk, methods, static[apk]["sa_methods"]))
    dump("g3", ["apk", "rows", "pairs"], bad)
    dump("g3_secondary", ["apk", "methods_total", "sa_methods"], secondary)
    verdict("G3", bad, f"apks={len(by_apk)} variando={len(bad)} | secundario methods_total!=sa_methods: {len(secondary)}")


def z4(task, summary):
    bad = []
    for table, rows, cols in (("per_task", task, Z4_TASK), ("summary", summary, Z4_SUMMARY)):
        arms = defaultdict(list)
        for r in rows:
            arms[r["tool"]].append(r)
        for col in cols:
            total = {r[col] for r in rows}
            if len(total) < 2:
                bad.append((table, col, "(total)", sorted(total)))
            for arm, arm_rows in sorted(arms.items()):
                vals = {r[col] for r in arm_rows}
                if len(vals) < 2:
                    bad.append((table, col, arm, sorted(vals)))
    dump("z4", ["table", "column", "arm", "values"], bad)
    verdict("Z4", bad, f"colunas constantes: {[(t, c, a, v) for t, c, a, v in bad]}")


def r1(task, paired):
    cells = defaultdict(lambda: defaultdict(list))
    for r in task:
        for m in PAIRED_METRICS:
            cells[(r["apk"], int(r["timeout"]), r["tool"])][m].append(float(r[m]))
    bad, checked, worst = [], 0, 0.0
    for row in paired:
        for (apk, to, tool), d in [((row["apk"], int(row["timeout"]), t), cells.get((row["apk"], int(row["timeout"]), t)))
                                   for t in {k.split("__")[0] for k in row if "__" in k}]:
            if d is None or any(len(d[m]) != N_REPS for m in PAIRED_METRICS):
                bad.append((apk, to, tool, "n", None if d is None else len(d["cov_method"]), ""))
                continue
            for m in PAIRED_METRICS:
                cell = row[f"{tool}__{m}"]
                if cell in ("", "nan"):
                    bad.append((apk, to, tool, m, "vazio", ""))
                    continue
                diff = abs(float(cell) - st.mean(d[m]))
                worst = max(worst, diff)
                checked += 1
                if diff > R1_TOL:
                    bad.append((apk, to, tool, m, cell, st.mean(d[m])))
    n_cells = len(paired) * N_ARMS
    dump("r1", ["apk", "timeout", "tool", "metric", "paired", "recomputed"], bad)
    verdict("R1", bad or n_cells != N_APKS * 3 * N_ARMS,
            f"unidades={len(paired)} celulas={n_cells} valores={checked} maior_diff={worst:.2e} divergencias={len(bad)}")


def r2(paired, summary_rows):
    bad, worst = [], 0.0
    for row in summary_rows:
        tool, to = row["tool"], int(row["timeout"])
        vals = {m: [float(p[f"{tool}__{m}"]) for p in paired if int(p["timeout"]) == to and p[f"{tool}__{m}"] not in ("", "nan")]
                for m in PAIRED_METRICS}
        if int(row["n_apks"]) != N_APKS:
            bad.append((tool, to, "n_apks", row["n_apks"], N_APKS))
        for m in PAIRED_METRICS:
            for agg, fn in (("mean", st.mean), ("median", st.median)):
                diff = abs(float(row[f"{m}_{agg}"]) - fn(vals[m]))
                worst = max(worst, diff)
                if diff > R2_TOL:
                    bad.append((tool, to, f"{m}_{agg}", row[f"{m}_{agg}"], fn(vals[m])))
    dump("r2", ["tool", "timeout", "field", "table", "recomputed"], bad)
    verdict("R2", bad or len(summary_rows) != N_ARMS * 3,
            f"linhas={len(summary_rows)} n_apks={sorted({r['n_apks'] for r in summary_rows})} maior_diff={worst:.2e}")
    return bad


def r2_confront(bad, task, summary_rows):
    """Recompute the R2 offenders from the unrounded per-APK means (per_task.csv).

    per_apk_paired.csv is rounded to 4 places and per_tool_summary.csv to 3, so a median
    recomputed from the rounded cells can sit up to 5e-5 past the 5e-4 rounding boundary.
    The consolidator aggregates the unrounded means; this is the check against its own input.
    """
    cells = defaultdict(list)
    for r in task:
        cells[(r["apk"], int(r["timeout"]), r["tool"])].append(r)
    by = {(r["tool"], int(r["timeout"])): r for r in summary_rows}
    left = []
    for tool, to, field, table, _ in bad:
        if field == "n_apks":
            left.append((tool, to, field))
            continue
        m, agg = field.rsplit("_", 1)
        means = [st.mean(float(x[m]) for x in rows) for (a, t, tl), rows in cells.items() if t == to and tl == tool]
        value = (st.mean if agg == "mean" else st.median)(means)
        if round(value, 3) != float(by[(tool, to)][field]):
            left.append((tool, to, field, table, value))
    print(f"R2 (confronto com as medias sem arredondar): {len(bad) - len(left)} de {len(bad)} explicadas por arredondamento duplo; restam {left}")


def r3(task, summary):
    uniq, lines = defaultdict(set), Counter()
    with open(TABLES / "errors.csv", newline="") as f:
        for r in csv.DictReader(f):
            k = ident(r)
            uniq[k].add(r["unique_msg"])
            lines[k] += 1
    s_by = {ident(r): r for r in summary}
    bad, known, secondary = [], [], []
    for r in task:
        k = ident(r)
        n_uniq, n_lines = len(uniq.get(k, ())), lines.get(k, 0)
        mop_unique = int(float(r["mop_unique"]))
        if n_uniq != mop_unique:
            row = (*k, n_uniq, mop_unique)
            (known if any(s in k[0] for s in R3_KNOWN) and k[1] == "qtesting" and k[3] == 300 and abs(n_uniq - mop_unique) == 1
             else bad).append(row)
        s_total = int(s_by[k]["mop_errors_total"])
        if not (n_lines == s_total == int(r["mop_total"])):
            secondary.append((*k, n_lines, s_total, r["mop_total"]))
    extra = set(uniq) - {ident(r) for r in task}
    dump("r3", ["apk", "tool", "rep", "timeout", "errors_csv_unique", "per_task_mop_unique"], bad + known)
    dump("r3_secondary", ["apk", "tool", "rep", "timeout", "errors_csv_rows", "summary_total", "per_task_mop_total"], secondary)
    verdict("R3", bad or len(known) != 2 or extra,
            f"iguais={len(task) - len(bad) - len(known)} conhecidas={len(known)} novas={len(bad)} "
            f"identidades_so_no_errors={len(extra)} | secundario linhas!=total: {len(secondary)} "
            f"(Σ errors.csv={sum(lines.values())}, Σ mop_total={sum(int(r['mop_total']) for r in task)})")


def e2(summary):
    hits, low = [], Counter()
    for r in summary:
        if r["measured"] != "true" or r["cov_method"] == "":
            continue
        cov, out = float(r["cov_method"]), int(r["unmatched_out_of_scope"] or 0)
        if cov < E2_COV:
            low[(r["tool"], "out>=100" if out >= E2_OUT else "out<100")] += 1
            if out >= E2_OUT:
                hits.append((*ident(r), cov, out, r["unmatched_in_scope"]))
    dump("e2", ["apk", "tool", "rep", "timeout", "cov_method", "unmatched_out_of_scope", "unmatched_in_scope"], hits)
    verdict("E2", hits, f"hits={len(hits)} | cov_method<1 por braço: {dict(sorted(low.items()))}")


def main():
    summary, task = read("summary.csv"), read("per_task.csv")
    paired, tool_summary = read("per_apk_paired.csv"), read("per_tool_summary.csv")
    static = {r["apk"]: {"sa_methods": r["sa_methods"]} for r in read("per_apk_static.csv")}
    if len(summary) != len(task) or {ident(r) for r in summary} != {ident(r) for r in task}:
        sys.exit("summary.csv e per_task.csv nao tem as mesmas identidades — nada comparado")
    g3(summary, static)
    z4(task, summary)
    r1(task, paired)
    r2_bad = r2(paired, tool_summary)
    if r2_bad:
        r2_confront(r2_bad, task, tool_summary)
    e2(summary)
    r3(task, summary)


if __name__ == "__main__":
    main()

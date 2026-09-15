#!/usr/bin/env python3
"""Clean errors.csv files, per-run outcome counts and the RQ1 model refitted on them.

The campaign's outcome `mop_unique4` counts every misuse the monitor reported. The re-analysis
of 15/09 (`docs/20260915_reanalise_acusacoes.md`) read each one and found that 23.2 % are
sustained by the rules and 5.8 % are security-relevant; the rest is correct code the monitor
cannot see, rule decisions, legal reuse the rule refuses and instrumenter artefacts. Its verdict
per misuse is `full_partition_keys.csv`: `strict` = NOBS real misuse or genuine per rule,
`sec` = NOBS real misuse or genuine relevant or debatable.

Three steps, in order:

1. `errors_sustentado.csv` and `errors_relevante.csv` beside `errors.csv`: the lines of the
   sustained / relevant misuses, every column as it is. The filter is by misuse, not by line: a
   sustained misuse keeps all its lines, the ORDER cascades included, which changes no count of
   distinct misuses.
2. `per_task_desfechos.csv`: per run, the distinct (class, method, spec) of each clean file, plus
   the sustained count without the 379 debatable misuses. The raw count recomputed the same way
   from `errors.csv` must equal `per_task.csv`'s `mop_unique4` in every run, or nothing is written.
3. The primary model of `rq1_estudo02.py` fitted to each outcome, side by side, with the reading
   rule fixed before the fit: a conclusion holds when the IRR keeps its side of 1 and each
   estimate lies inside the other's 95 % interval. A lost significance with overlapping
   intervals is fewer data, not a different effect.

Misuse ids are `errors.csv` grouped by (apk, tool, rep, timeout, class, method, spec) with
pandas' default dtypes, which is how the re-analysis numbered them (`nonnobs_project.py`); the
join is checked against the partition's apk, tool and timeout before anything is used.

    uv run python experimento-estudo02/scripts/desfechos_sustentados.py --out experimento-estudo02/docs/<data>_modelo_rq1_desfechos.md
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rq1_estudo02 as rq1  # noqa: E402  (needs the sys.path above)

TABLES = rq1.TABLES
PARTITION = (Path(__file__).resolve().parents[1] / "docs" / "adjudicacao_nobs" / "reanalise_20260915"
             / "full_partition_keys.csv")
RUN = ["apk", "tool", "rep", "timeout"]
KEY = RUN + ["class", "method", "spec"]
#: Totals of the re-analysis; a different number means the partition and errors.csv drifted apart.
EXPECTED = {"misuses": 27068, "strict": 6278, "sec": 1572, "debatable": 379}
LABELS = {
    rq1.RAW: "bruto",
    "mop_sustentado": "sustentado",
    "mop_sustentado_sem_discutivel": "sustentado sem discutíveis",
    "mop_relevante": "relevante",
}


def clean_files() -> None:
    keys = pd.read_csv(TABLES / "errors.csv", usecols=KEY)
    kid = keys.groupby(KEY).ngroup()
    part = pd.read_csv(PARTITION, usecols=["kid", "apk", "tool", "timeout", "status", "strict", "sec"])
    assert kid.nunique() == len(part) == EXPECTED["misuses"], "misuse count differs from the partition"
    part = part.set_index("kid").sort_index()
    first = keys.assign(kid=kid).drop_duplicates("kid").set_index("kid").sort_index()
    for col in ["apk", "tool", "timeout"]:
        assert (first[col] == part[col]).all(), f"partition misaligned on {col}"
    assert int(part["strict"].sum()) == EXPECTED["strict"]
    assert int(part["sec"].sum()) == EXPECTED["sec"]
    debatable = part["status"] == "OTHER:GENUINE_debatable"
    assert int(debatable.sum()) == EXPECTED["debatable"]

    lines = pd.read_csv(TABLES / "errors.csv", dtype=str, keep_default_na=False)
    assert len(lines) == len(kid)
    for name, flag in [("errors_sustentado.csv", part["strict"]), ("errors_relevante.csv", part["sec"])]:
        keep = kid.map(flag).astype(bool).values
        lines[keep].to_csv(TABLES / name, index=False)
        print(f"{name}: {int(keep.sum())} linhas, {int(flag.sum())} maus usos")

    task = pd.read_csv(TABLES / "per_task.csv", usecols=RUN + [rq1.RAW])

    def per_run(frame: pd.DataFrame, column: str) -> pd.Series:
        counts = frame.groupby(RUN)[["class", "method", "spec"]].apply(lambda g: len(g.drop_duplicates()))
        return task.merge(counts.rename(column).reset_index(), on=RUN, how="left")[column].fillna(0).astype(int)

    out = task[RUN].copy()
    raw = per_run(keys, "recount")
    assert (raw.values == task[rq1.RAW].values).all(), "errors.csv recount differs from mop_unique4"
    out["mop_sustentado"] = per_run(pd.read_csv(TABLES / "errors_sustentado.csv", usecols=KEY), "s")
    out["mop_relevante"] = per_run(pd.read_csv(TABLES / "errors_relevante.csv", usecols=KEY), "r")
    no_debatable = keys.assign(kid=kid)
    no_debatable = no_debatable[no_debatable["kid"].map(part["strict"] & ~debatable).astype(bool)]
    out["mop_sustentado_sem_discutivel"] = per_run(no_debatable, "d")
    assert out["mop_sustentado"].sum() == EXPECTED["strict"]
    assert out["mop_relevante"].sum() == EXPECTED["sec"]
    assert out["mop_sustentado_sem_discutivel"].sum() == EXPECTED["strict"] - EXPECTED["debatable"]
    out.to_csv(rq1.DESFECHOS, index=False)
    print(f"{rq1.DESFECHOS.name}: {len(out)} execuções")


def fit(outcome: str) -> dict:
    df = rq1.load(outcome)
    y = df[outcome]
    res = rq1._glm_fit_nb(f"{outcome} ~ {rq1.RHS}", df)
    obs0, exp0 = rq1._glm_zeros_nb(res, y)
    return {"df": df, "res": res, "holm": rq1.holm(res), "zeros": (obs0, exp0),
            "total": int(y.sum()), "zero_share": float((y == 0).mean()),
            "apks": int(df.loc[y > 0, "apk"].nunique()),
            "converged": bool(res.mle_retvals.get("converged", False))}


def irr_cell(f: dict, name: str) -> str:
    res = f["res"]
    lo, hi = np.exp(res.conf_int().loc[name])
    mark = ""
    if name in f["holm"]:
        mark = " †" if f["holm"][name][1] < 0.05 else ""
    elif res.pvalues[name] < 0.05:
        mark = " *"
    return f"{np.exp(res.params[name]):.3f} [{lo:.3f}; {hi:.3f}]{mark}"


def report(out_path: Path) -> None:
    fits = {o: fit(o) for o in LABELS}
    raw = fits[rq1.RAW]
    names = [n for n in raw["res"].params.index if n not in ("Intercept", "alpha")]
    md = []
    md.append("# Modelo do RQ1 com o desfecho sustentado — `estudo02`")
    md.append("")
    md.append("Gerado por `experimento-estudo02/scripts/desfechos_sustentados.py`. Mesmo modelo de "
              "`rq1_estudo02.py` (NB2, alpha por ML, erros-padrão agrupados por app, Holm sobre as 10 "
              "comparações com o `monkey`); muda só o que se conta por execução.")
    md.append("")
    md.append("## Os desfechos")
    md.append("")
    md.append("| desfecho | maus usos | execuções com zero | apps com algum | alpha | zeros obs/esp | convergiu |")
    md.append("|---|---:|---:|---:|---:|---:|---|")
    for o, f in fits.items():
        obs0, exp0 = f["zeros"]
        md.append(f"| {LABELS[o]} (`{o}`) | {f['total']} | {100 * f['zero_share']:.1f} % | {f['apks']} | "
                  f"{f['res'].params['alpha']:.2f} | {obs0 / exp0:.3f} | {'sim' if f['converged'] else '**não**'} |")
    md.append("")
    md.append("## Razões de taxa (IRR) e intervalos de 95 %")
    md.append("")
    md.append("Referências: `monkey` e 60 s. `†` = rejeita H0 depois de Holm (comparações de ferramenta); "
              "`*` = p < 0,05 sem correção (orçamento e covariável).")
    md.append("")
    md.append("| termo | " + " | ".join(LABELS[o] for o in fits) + " |")
    md.append("|---|" + "---|" * len(fits))
    for n in names:
        md.append(f"| `{rq1._glm_short(n)}` | " + " | ".join(irr_cell(f, n) for f in fits.values()) + " |")
    md.append("")

    md.append("## Regra de leitura aplicada a cada desfecho contra o bruto")
    md.append("")
    md.append("Uma conclusão se mantém quando a IRR fica do mesmo lado de 1 **e** cada estimativa cai dentro "
              "do intervalo da outra. Perder significância com intervalos que se sobrepõem é menos dado, "
              "não efeito diferente.")
    md.append("")
    rci = np.exp(raw["res"].conf_int())
    for o, f in fits.items():
        if o == rq1.RAW:
            continue
        res, ci = f["res"], np.exp(f["res"].conf_int())
        flips, outside, lost, gained = [], [], [], []
        for n in names:
            if np.sign(res.params[n]) != np.sign(raw["res"].params[n]):
                flips.append(rq1._glm_short(n))
            e_o, e_r = np.exp(res.params[n]), np.exp(raw["res"].params[n])
            if not (rci.loc[n, 0] <= e_o <= rci.loc[n, 1] and ci.loc[n, 0] <= e_r <= ci.loc[n, 1]):
                outside.append(rq1._glm_short(n))
        rej_r = {n for n, (_, a) in raw["holm"].items() if a < 0.05}
        rej_o = {n for n, (_, a) in f["holm"].items() if a < 0.05}
        lost = sorted(rq1._glm_short(n) for n in rej_r - rej_o)
        gained = sorted(rq1._glm_short(n) for n in rej_o - rej_r)
        md.append(f"**{LABELS[o]}**")
        md.append(f"- mudou de lado de 1: {', '.join(flips) if flips else 'nenhum termo'}")
        md.append(f"- estimativa fora do intervalo da outra: {', '.join(outside) if outside else 'nenhum termo'}")
        md.append(f"- Holm: rejeita {', '.join(sorted(rq1._glm_short(n) for n in rej_o)) or 'nenhuma'}; "
                  f"perdeu {', '.join(lost) or 'nenhuma'}; ganhou {', '.join(gained) or 'nenhuma'}")
        md.append("")

    md.append("## `ape` contra cada ferramenta que não é a referência (Wald, agrupado por app, p sem correção)")
    md.append("")
    md.append("| contraste | " + " | ".join(LABELS[o] for o in fits) + " |")
    md.append("|---|" + "---|" * len(fits))
    ape = "C(tool, Treatment('monkey'))[T.ape]"
    tools = [n for n in names if n.startswith("C(tool") and n != ape]
    for other in tools:
        cells = []
        for f in fits.values():
            params = list(f["res"].params.index)
            r = np.zeros(len(params))
            r[params.index(ape)], r[params.index(other)] = 1.0, -1.0
            t = f["res"].t_test(r)
            cells.append(f"{float(np.exp(t.effect[0])):.3f} (p {rq1._glm_pfmt(float(t.pvalue))})")
        md.append(f"| ape × {rq1._glm_short(other)[5:-1]} | " + " | ".join(cells) + " |")
    md.append("")

    md.append("## Em quantos apps")
    md.append("")
    part = pd.read_csv(PARTITION, usecols=["apk", "status", "strict", "sec"])
    sus = part[part["strict"]]
    n_corpus = raw["df"]["apk"].nunique()
    md.append("| recorte | apps | % do corpus |")
    md.append("|---|---:|---:|")
    for label, apps in [("com alguma acusação (bruto)", part["apk"].nunique()),
                        ("com algum mau uso sustentado", sus["apk"].nunique()),
                        ("com algum mau uso relevante", part.loc[part["sec"], "apk"].nunique())]:
        md.append(f"| {label} | {apps} | {100 * apps / n_corpus:.1f} % |")
    md.append("")
    kind = sus["status"].map({"NOBS:MISUSE": "mau uso real (NOBS)", "OTHER:GENUINE_yes": "relevante",
                              "OTHER:GENUINE_debatable": "discutível"}).fillna("sem relevância")
    per_app = pd.crosstab(sus["apk"], kind)
    per_app["total"] = per_app.sum(axis=1)
    per_app = per_app.sort_values("total", ascending=False)
    only_irrelevant = int((per_app["total"] == per_app.get("sem relevância", 0)).sum())
    md.append(f"Dos {len(per_app)} apps com mau uso sustentado, {only_irrelevant} só têm casos sem relevância. "
              f"Os 5 maiores somam {100 * per_app['total'].head(5).sum() / len(sus):.1f} % dos {len(sus)}; "
              f"os 10 maiores, {100 * per_app['total'].head(10).sum() / len(sus):.1f} %.")
    md.append("")
    md.append("| app | " + " | ".join(per_app.columns) + " |")
    md.append("|---|" + "---:|" * len(per_app.columns))
    for apk, row in per_app.head(15).iterrows():
        md.append(f"| {apk} | " + " | ".join(str(int(v)) for v in row) + " |")
    md.append("")

    md.append("## Fração sustentada, descritiva")
    md.append("")
    df = raw["df"].merge(pd.read_csv(rq1.DESFECHOS), on=RUN, how="left", validate="1:1")
    for by in ["tool", "timeout"]:
        g = df.groupby(by)[[rq1.RAW, "mop_sustentado", "mop_relevante"]].sum()
        md.append(f"| {by} | bruto | sustentado | fração | relevante | fração |")
        md.append("|---|---:|---:|---:|---:|---:|")
        for k, row in g.iterrows():
            md.append(f"| {k} | {int(row[rq1.RAW])} | {int(row['mop_sustentado'])} | "
                      f"{row['mop_sustentado'] / row[rq1.RAW]:.3f} | {int(row['mop_relevante'])} | "
                      f"{row['mop_relevante'] / row[rq1.RAW]:.3f} |")
        md.append("")
    out_path.write_text("\n".join(md) + "\n")
    print("\n".join(md))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    clean_files()
    report(Path(args.out))


if __name__ == "__main__":
    main()

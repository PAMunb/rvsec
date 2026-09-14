#!/usr/bin/env python3
"""Every pairwise tool contrast of the RQ1 model, fitted to the article and to estudo02 alike.

The model reports each tool against monkey, and monkey is not the same program in the two
campaigns: estudo02 runs it with ignore_crashes/ignore_timeouts, the article did not. A
contrast between two other arms does not pass through monkey, so it answers only to what the
two campaigns share besides the tools — above all, the specification set. This script fits
the article's primary model (`rq1_jca.py`, NB2, alpha by ML, cluster-robust SEs by apk) to
both data sets, reads the 55 tool-vs-tool contrasts out of each fit as Wald tests, and applies
Holm over the 55 within each campaign.

The article side is recomputed from its published per-run data (read-only):
`ase-journal/dataset/results/summary.csv` and the covariate in `dataset/dataset.csv`, merged the
way `rq1_jca.py:294-299` merges them. The fit is checked against the IRRs published in
`rq1_jca_stats.txt` before any contrast is read.

    uv run python experimento-estudo02/scripts/contrastes_ferramentas.py > experimento-estudo02/docs/<data>_contrastes_ferramentas.md
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rq1_estudo02 as rq1  # noqa: E402  (needs the sys.path above)

ARTICLE = Path("/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal")
TOOL = "C(tool, Treatment('monkey'))[T.{}]"
#: Published IRRs are printed with 4 decimals; a refit that reproduces the article stays within this.
IRR_TOL = 5e-4


def article_data() -> pd.DataFrame:
    runs = pd.read_csv(ARTICLE / "dataset" / "results" / "summary.csv")
    apks = pd.read_csv(ARTICLE / "dataset" / "dataset.csv", usecols=["apk", "sa_methods_reaches_mop"])
    df = runs.merge(apks, on="apk", how="left", validate="m:1")
    assert len(df) == rq1.N_EXPECTED, f"article: expected {rq1.N_EXPECTED} runs, got {len(df)}"
    assert df["sa_methods_reaches_mop"].min() >= 1, "article: log undefined"
    return df.rename(columns={"mop_errors_unique": "mop_unique4"})


def contrasts(res) -> pd.DataFrame:
    """IRR and raw p of every tool pair (a over b), Holm over all pairs."""
    names = list(res.params.index)
    prefix = TOOL.split("{}")[0]
    tools = sorted(["monkey"] + [n[len(prefix):-1] for n in names if n.startswith(prefix)])
    rows = []
    for a, b in itertools.combinations(tools, 2):
        r = np.zeros(len(names))
        if a != "monkey":
            r[names.index(TOOL.format(a))] += 1.0
        if b != "monkey":
            r[names.index(TOOL.format(b))] -= 1.0
        t = res.t_test(r)
        rows.append({"a": a, "b": b, "irr": float(np.exp(t.effect[0])), "p": float(t.pvalue)})
    df = pd.DataFrame(rows).sort_values("p", kind="mergesort").reset_index(drop=True)
    m = len(df)
    df["p_holm"] = np.minimum(1.0, np.maximum.accumulate([(m - i) * p for i, p in enumerate(df["p"])]))
    return df


def main():
    formula = f"mop_unique4 ~ {rq1.RHS}"
    art = rq1._glm_fit_nb(formula, article_data())
    cam = rq1._glm_fit_nb(formula, rq1.load())

    published = rq1.article_irrs()
    worst = max(abs(np.exp(art.params[n]) - published[rq1._glm_short(n)][0])
                for n in art.params.index if rq1._glm_short(n) in published)
    assert worst <= IRR_TOL, f"article refit does not reproduce rq1_jca_stats.txt (max |dIRR| = {worst})"

    ca, cc = contrasts(art), contrasts(cam)
    both = ca.merge(cc, on=["a", "b"], suffixes=("_art", "_cam"))
    sig_a, sig_c = both["p_holm_art"] < 0.05, both["p_holm_cam"] < 0.05
    flips = both[(both["irr_art"] > 1) != (both["irr_cam"] > 1)]

    print("# Contrastes entre ferramentas: artigo (`jca`) × estudo02 (`jca_android`)\n")
    print("Mesmo modelo nos dois lados (NB2, `mop_unique4 ~ C(timeout) + C(tool) + "
          "log(sa_methods_reaches_mop)`, erros robustos por APK). O ajuste do artigo foi refeito dos "
          f"dados publicados e reproduz os IRRs de `rq1_jca_stats.txt` (maior diferença {worst:.1e}). "
          "Cada linha é a razão de taxas `a ÷ b` com teste de Wald; Holm sobre os 55 pares, "
          "separadamente em cada campanha. Gerado por `scripts/contrastes_ferramentas.py`.\n")
    print(f"- pares significativos após Holm: artigo {int(sig_a.sum())}, estudo02 {int(sig_c.sum())}, "
          f"nos dois {int((sig_a & sig_c).sum())}")
    print(f"- pares que mudam de direção (IRR de um lado de 1 para o outro): {len(flips)}"
          + (", todos sem significância nos dois lados" if len(flips) and not (flips['p_holm_art'] < 0.05).any()
             and not (flips['p_holm_cam'] < 0.05).any() else ""))
    print(f"- pares com `monkey`: {int(((both.a == 'monkey') | (both.b == 'monkey')).sum())} de 55\n")

    def table(sub: pd.DataFrame, title: str):
        print(f"## {title}\n")
        print("| a | b | artigo IRR | p | Holm | estudo02 IRR | p | Holm |")
        print("|---|---|---:|---:|---:|---:|---:|---:|")
        for _, r in sub.iterrows():
            print(f"| {r.a} | {r.b} | {r.irr_art:.3f} | {rq1._glm_pfmt(r.p_art)} | {rq1._glm_pfmt(r.p_holm_art)} "
                  f"| {r.irr_cam:.3f} | {rq1._glm_pfmt(r.p_cam)} | {rq1._glm_pfmt(r.p_holm_cam)} |")
        print()

    # Orient every pair so that `a` is the arm with the higher rate in the article.
    swap = both["irr_art"] < 1
    for x, y in (("a", "b"),):
        both.loc[swap, [x, y]] = both.loc[swap, [y, x]].values
    both.loc[swap, ["irr_art", "irr_cam"]] = 1.0 / both.loc[swap, ["irr_art", "irr_cam"]]
    both = both.sort_values(["p_holm_art", "p_art"], kind="mergesort")

    with_monkey = (both.a == "monkey") | (both.b == "monkey")
    table(both[~with_monkey & (sig_a | sig_c)[both.index]],
          "Pares sem `monkey`, significativos após Holm em pelo menos uma campanha")
    table(both[with_monkey], "Pares com `monkey`")
    table(both[~with_monkey & ~(sig_a | sig_c)[both.index]],
          "Pares sem `monkey`, sem significância após Holm em nenhuma campanha")


if __name__ == "__main__":
    main()

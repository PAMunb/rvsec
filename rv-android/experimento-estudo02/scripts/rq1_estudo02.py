#!/usr/bin/env python3
"""The article's RQ1 negative-binomial model, fitted to the estudo02 campaign.

The model is `ase-journal/data-analysis/rvsec/rq1_jca.py` (lines 185-594), copied because the
article is read-only: discrete NB2 with alpha estimated by ML, one row per run
(apk x tool x timeout x rep), `tool` and `timeout` categorical with monkey / 60 s as reference,
cluster-robust standard errors by apk, Holm over the ten tool contrasts. What changes is where
the columns come from:

- outcome `mop_unique4` from `per_task.csv`: distinct (class, method, spec) per run, recounted
  from the logcat. It is the article's key. `mop_unique` of the same file is the seven-part
  `unique_msg` key and is ~2.4x larger; it is fitted only as a sensitivity on the key.
- covariate `log(sa_methods_reaches_mop)` from `per_apk_static.csv`, recomputed from the
  campaign's own `.apk.json`: the monitored-API targets changed with `jca_android`, so the
  article's `dataset.csv` value does not describe these APKs.
- the admissibility `category` column of `per_task.csv` decides the sensitivity subsets; the
  main model, like the article's, keeps every run.

`--outcome` swaps the counted misuses and nothing else. The default is `mop_unique4`, every
misuse the monitor reported. The other outcomes are the same per-run count taken over the
misuses the re-analysis of 15/09 sustained (`docs/20260915_reanalise_acusacoes.md`), read from
`per_task_desfechos.csv`, which `desfechos_sustentados.py` writes. Formula, clustering, Holm and
the admissibility sensitivities are identical. The sections that only make sense for the raw
count are skipped for them: the event count, the seven-part key, and the article's IRRs, which
answer to the raw `jca` count.

    uv run python experimento-estudo02/scripts/rq1_estudo02.py --out experimento-estudo02/docs/<data>_modelo_rq1.txt
    uv run python experimento-estudo02/scripts/rq1_estudo02.py --outcome mop_sustentado --out experimento-estudo02/docs/<data>_modelo_rq1_sustentado.txt
"""
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as _scistats

ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "data" / "results" / "estudo02_consolidado"
ARTICLE_STATS = ROOT.parents[1] / "ase-journal" / "data-analysis" / "stats" / "rq1_jca_stats.txt"
if not ARTICLE_STATS.exists():
    ARTICLE_STATS = Path("/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/"
                         "ase-journal/data-analysis/stats/rq1_jca_stats.txt")

N_EXPECTED = 16137
RHS = "C(timeout) + C(tool, Treatment('monkey')) + log(sa_methods_reaches_mop)"
RHS_NO_COV = "C(timeout) + C(tool, Treatment('monkey'))"
#: patsy resolves `log()` in the formulas from the calling frame's namespace.
log = np.log
COV_COLS = ["cov_act", "cov_class", "cov_method", "cov_reachable",
            "cov_reaches_target", "cov_directly_reaches_target"]
RAW = "mop_unique4"
#: Outcome column -> how its "outcome (primary)" line reads. All but RAW come from DESFECHOS.
OUTCOMES = {
    RAW: "mop_unique4 — per-run nunique(class, method, spec), the article's key,"
         " recounted from the logcat (per_task.csv)",
    "mop_sustentado": "mop_sustentado — per-run nunique(class, method, spec) over the misuses sustained by"
                      " the rules (NOBS real misuse + genuine per rule; errors_sustentado.csv)",
    "mop_sustentado_sem_discutivel": "mop_sustentado_sem_discutivel — mop_sustentado without the 379"
                                     " debatable genuine misuses",
    "mop_relevante": "mop_relevante — per-run nunique(class, method, spec) over the security-relevant"
                     " misuses (NOBS real misuse + genuine relevant + debatable; errors_relevante.csv)",
}
DESFECHOS = TABLES / "per_task_desfechos.csv"


def _glm_short(name: str) -> str:
    return (name
            .replace("C(tool, Treatment('monkey'))[T.", "tool[")
            .replace("C(tool, Sum)[S.", "tool_sum[")
            .replace("C(timeout)[T.", "timeout["))


def _glm_pfmt(p: float) -> str:
    if p == 0.0:
        return "<1e-300"
    if p < 1e-3:
        return f"{p:.2e}"
    return f"{p:.4f}"


def _glm_fit_nb(formula: str, data, offset=None):
    """Discrete NB2 (alpha by ML), cluster-robust SEs by apk; Poisson starts WITH the offset
    (rq1_jca.py: statsmodels' default start ignores the offset and the offset model diverges)."""
    pois = sm.Poisson.from_formula(formula, data=data, offset=offset).fit(disp=0)
    start = np.append(np.asarray(pois.params), 0.5)
    model = sm.NegativeBinomial.from_formula(formula, data=data, offset=offset)
    return model.fit(start_params=start, method='bfgs', maxiter=500, disp=0,
                     cov_type='cluster', cov_kwds={'groups': data['apk']})


def _glm_param_table(res, title: str):
    ci = res.conf_int()
    lines = [f"### {title}"]
    lines.append(f"  {'term':<34} {'coef':>9} {'rob_SE':>8} {'z':>8} {'p':>10}"
                 f" {'CI95_lo':>9} {'CI95_hi':>9} {'IRR':>9} {'IRR_lo':>9} {'IRR_hi':>9}")
    for name in res.params.index:
        b, se, z, p = res.params[name], res.bse[name], res.tvalues[name], res.pvalues[name]
        lo, hi = ci.loc[name]
        if name == 'alpha':
            lines.append(f"  {'alpha (dispersion)':<34} {b:9.4f} {se:8.4f} {z:8.2f}"
                         f" {_glm_pfmt(p):>10} {lo:9.4f} {hi:9.4f} {'-':>9} {'-':>9} {'-':>9}")
        else:
            lines.append(f"  {_glm_short(name):<34} {b:9.4f} {se:8.4f} {z:8.2f}"
                         f" {_glm_pfmt(p):>10} {lo:9.4f} {hi:9.4f}"
                         f" {np.exp(b):9.4f} {np.exp(lo):9.4f} {np.exp(hi):9.4f}")
    lines.append(f"  converged = {res.mle_retvals.get('converged', None)}"
                 f"   llf = {res.llf:.2f}   AIC = {res.aic:.2f}   BIC = {res.bic:.2f}")
    return lines


def holm(res):
    """Holm-adjusted p for the tool contrasts vs monkey: {term: (p_raw, p_holm)}."""
    toolnames = [n for n in res.params.index if n.startswith("C(tool, Treatment('monkey'))")]
    pr = res.pvalues[toolnames].sort_values(kind='mergesort')
    m, running, out = len(pr), 0.0, {}
    for i, (name, p) in enumerate(pr.items()):
        running = max(running, min(1.0, (m - i) * p))
        out[name] = (p, running)
    return out


def _glm_holm_lines(res):
    h = holm(res)
    lines = [f"### Holm-adjusted p-values for the {len(h)} tool contrasts (vs monkey)"]
    lines.append(f"  {'tool':<26} {'p_raw':>10} {'p_holm':>10}  reject@0.05")
    for name, (p, adj) in h.items():
        lines.append(f"  {_glm_short(name):<26} {_glm_pfmt(p):>10} {_glm_pfmt(adj):>10}"
                     f"  {'yes' if adj < 0.05 else 'no'}")
    return lines


def _glm_zeros_nb(res, y):
    mu = res.predict()
    alpha = res.params['alpha']
    p0 = (1.0 / (1.0 + alpha * mu)) ** (1.0 / alpha)
    return int((y == 0).sum()), float(p0.sum())


def _glm_irr_cell(res, name):
    if res is None or name not in res.params.index:
        return f"{'--':>9} "
    star = '*' if res.pvalues[name] < 0.05 else ' '
    return f"{np.exp(res.params[name]):9.3f}{star}"


def article_irrs() -> dict:
    """Primary-model IRR and p of the article, from its stats file (read-only)."""
    if not ARTICLE_STATS.exists():
        return {}
    text = ARTICLE_STATS.read_text()
    block = text.split("### coefficients — primary model", 1)[1].split("###", 1)[0]
    out = {}
    for ln in block.splitlines():
        m = re.match(r"\s+(\S+(?:\[[^\]]+\])?)\s+(-?\d+\.\d+)\s+\S+\s+\S+\s+(\S+)\s+\S+\s+\S+\s+(\d+\.\d+)", ln)
        if m and m.group(1) != "alpha":
            out[m.group(1)] = (float(m.group(4)), m.group(3))
    return out


def load(outcome: str = RAW) -> pd.DataFrame:
    task = pd.read_csv(TABLES / "per_task.csv")
    summary = pd.read_csv(TABLES / "summary.csv")
    key = ["apk", "tool", "rep", "timeout"]
    df = task.merge(summary[key + COV_COLS], on=key, how="left", validate="1:1",
                    suffixes=("", "_summary"))
    if outcome != RAW:
        desf = pd.read_csv(DESFECHOS)
        df = df.merge(desf[key + [outcome]], on=key, how="left", validate="1:1")
        assert df[outcome].notna().all(), f"{DESFECHOS.name} does not cover every run"
    assert len(df) == N_EXPECTED, f"expected {N_EXPECTED} runs, got {len(df)}"
    assert df["sa_methods_reaches_mop"].min() >= 1, "log undefined (min < 1)"
    assert df["category"].notna().all(), "per_task.csv without admissibility columns"
    assert (df["category"] != "sem_veredicto").all(), "runs without a verdict"
    assert df["tool_seconds"].min() > 0, "offset log(tool_seconds) undefined"
    df["_all_cov_zero"] = (df[[c + ("_summary" if c in task.columns else "") for c in COV_COLS]]
                           .fillna(0) == 0).all(axis=1).astype(int)
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--outcome", choices=list(OUTCOMES), default=RAW)
    args = ap.parse_args()
    out = args.outcome
    raw = out == RAW
    df = load(out)
    lines = []
    y = df[out]
    cats = df["category"].value_counts().to_dict()

    lines.append("## GLM — negative binomial regression on estudo02 (article spec, rq1_jca.py)")
    lines.append("")
    lines.append("### model specification")
    lines.append(f"  outcome (primary)  : {OUTCOMES[out]}")
    if raw:
        lines.append("  outcome (key sens.): mop_unique — seven-part unique_msg (class:::method:::spec:::error_type:::code:::event:::message)")
        lines.append("  outcome (secondary): mop_total — violation events (RVSEC lines)")
    lines.append(f"  observations       : 1 row = apk x tool x timeout x rep; N = {len(df)}")
    lines.append(f"  formula            : {out} ~ {RHS}")
    lines.append("  estimator          : sm.NegativeBinomial (NB2), alpha estimated by ML")
    lines.append(f"  standard errors    : cluster-robust by apk ({df['apk'].nunique()} clusters)")
    lines.append("  size covariate     : sa_methods_reaches_mop from per_apk_static.csv (campaign .apk.json,"
                 f" jca_android targets); min {df['sa_methods_reaches_mop'].min()},"
                 f" median {int(df.drop_duplicates('apk')['sa_methods_reaches_mop'].median())},"
                 f" max {df['sa_methods_reaches_mop'].max()}")
    lines.append(f"  dispersion context : var/mean = {y.var() / y.mean():.2f} (mean {y.mean():.2f}, var {y.var():.2f});"
                 f" zeros = {int((y == 0).sum())}/{len(df)} ({100.0 * (y == 0).mean():.1f}%); total = {int(y.sum())}")
    lines.append(f"  admissibility      : {cats}")
    lines.append("  interpretation     : associative (not causal); IRR = exp(beta), reference tool = monkey,"
                 " reference timeout = 60s")
    lines.append("")

    formula = f"{out} ~ {RHS}"
    nb = _glm_fit_nb(formula, df)
    alpha_ci = nb.conf_int().loc['alpha']
    lines.append("### alpha (overdispersion, primary model)")
    lines.append(f"  alpha = {nb.params['alpha']:.4f}   cluster-robust 95% CI [{alpha_ci[0]:.4f}, {alpha_ci[1]:.4f}]")
    pois = sm.Poisson.from_formula(formula, data=df).fit(disp=0)
    lr = 2.0 * (nb.llf - pois.llf)
    lines.append(f"  LR NB vs Poisson = {lr:.2f}   p (0.5*chi2_1) = {_glm_pfmt(0.5 * _scistats.chi2.sf(lr, 1))}")
    lines.append("")
    lines.extend(_glm_param_table(nb, f"coefficients — primary model ({out})"))
    lines.append("")
    lines.extend(_glm_holm_lines(nb))
    lines.append("")
    obs0, exp0 = _glm_zeros_nb(nb, y)
    lines.append("### zeros: observed vs expected (primary model)")
    lines.append(f"  observed = {obs0}   expected (NB2) = {exp0:.1f}   obs/exp = {obs0 / exp0:.3f}")
    lines.append("")

    lines.append("### omnibus Wald test: tool x timeout interaction (cluster-robust)")
    try:
        nb_int = _glm_fit_nb(f"{out} ~ C(timeout) * C(tool, Treatment('monkey')) + log(sa_methods_reaches_mop)", df)
        names = list(nb_int.params.index)
        ipos = [i for i, n in enumerate(names) if ':C(' in n]
        R = np.zeros((len(ipos), len(names)))
        for r_i, i in enumerate(ipos):
            R[r_i, i] = 1.0
        wt = nb_int.wald_test(R, scalar=True)
        lines.append(f"  chi2 = {float(wt.statistic):.2f}   df = {len(ipos)}   p = {_glm_pfmt(float(wt.pvalue))}")
    except Exception as e:  # registered, never silent
        lines.append(f"  FAILED ({type(e).__name__}: {e})")
    lines.append("")

    if raw:
        nb_tot = _glm_fit_nb(f"mop_total ~ {RHS}", df)
        lines.append(f"### secondary outcome: mop_total (events; var/mean = {df['mop_total'].var() / df['mop_total'].mean():.1f})")
        lines.extend(_glm_param_table(nb_tot, "coefficients — secondary model (mop_total)"))
        lines.append("")
        nb_k7 = _glm_fit_nb(f"mop_unique ~ {RHS}", df)
        lines.append(f"### key sensitivity: mop_unique (seven-part key; total = {int(df['mop_unique'].sum())})")
        lines.extend(_glm_param_table(nb_k7, "coefficients — seven-part key (mop_unique)"))
        lines.append("")

    # --- sensitivities on the primary outcome --------------------------------
    subsets = {
        "s1": ("excluding inadmissible runs (C2/C4/C5 not in a declared category)",
               df[df["category"] != "inadmissivel"]),
        "s2": ("excluding inadmissible + tool stop + foreign launcher (keeps admissible and structural zero)",
               df[df["category"].isin(["admissivel", "estrutural"])]),
        "s3": ("admissible runs only", df[df["category"] == "admissivel"]),
        "s4": ("excluding all-cov-zero runs (article's sensitivity i)", df[df["_all_cov_zero"] == 0]),
    }
    fits = {"main": nb}
    lines.append("### sensitivity analyses (primary outcome)")
    for tag, (desc, sub) in subsets.items():
        fits[tag] = _glm_fit_nb(formula, sub)
        lines.append(f"  ({tag}) {desc} -> N = {len(sub)};  alpha = {fits[tag].params['alpha']:.4f}")
    fits["s5"] = _glm_fit_nb(formula, df, offset=np.log(df["tool_seconds"].values))
    lines.append(f"  (s5) offset log(tool_seconds) — exposure is the tool's own time, not the budget (M1)"
                 f" -> N = {len(df)};  alpha = {fits['s5'].params['alpha']:.4f}")
    fits["s6"] = _glm_fit_nb(f"{out} ~ {RHS_NO_COV}", df, offset=np.log(df["sa_methods_reaches_mop"].values))
    lines.append(f"  (s6) pure offset log(sa_methods_reaches_mop) instead of covariate (article's iii)"
                 f" -> N = {len(df)};  alpha = {fits['s6'].params['alpha']:.4f}")
    lines.append("")

    focal = [n for n in nb.params.index if n.startswith('C(') or n == 'log(sa_methods_reaches_mop)']
    order = ["main", "s1", "s2", "s3", "s4", "s5", "s6"]
    if raw:
        order.append("k7")
        fits["k7"] = nb_k7
    lines.append("  IRR comparison (focal terms; '*' = p < 0.05 raw, cluster-robust"
                 + ("; k7 = seven-part key)" if raw else ")"))
    lines.append(f"  {'term':<26} " + " ".join(f"{t:>10}" for t in order))
    for name in focal:
        lines.append(f"  {_glm_short(name):<26} " + " ".join(_glm_irr_cell(fits[t], name) for t in order))
    lines.append("")
    lines.append("  Holm (tool contrasts) reject@0.05 per fit:")
    for t in order:
        rej = [_glm_short(n) for n, (_, adj) in holm(fits[t]).items() if adj < 0.05]
        lines.append(f"    {t:<5} {', '.join(rej) if rej else 'none'}")
    sig_main = [n for n in focal if nb.pvalues[n] < 0.05]
    flips = [f"{_glm_short(n)} in {t}" for n in sig_main for t in order[1:]
             if n in fits[t].params.index and (fits[t].params[n] > 0) != (nb.params[n] > 0)]
    lost = [f"{_glm_short(n)} in {t}" for n in sig_main for t in order[1:]
            if n in fits[t].params.index and fits[t].pvalues[n] >= 0.05]
    lines.append(f"  main-significant terms: {', '.join(_glm_short(n) for n in sig_main)}")
    lines.append(f"  direction changed: {', '.join(flips) if flips else 'none'}")
    lines.append(f"  significance lost: {', '.join(lost) if lost else 'none'}")
    lines.append("")

    # --- against the article --------------------------------------------------
    # The article's IRRs answer to the raw jca count; set beside a sustained count they would
    # read as a comparison the two numbers do not support, so the column is left empty then.
    art = article_irrs() if raw else {}
    if raw:
        lines.append("### against the article (jca, rq1_jca_stats.txt primary model) — IRR (p raw)")
        lines.append(f"  {'term':<26} {'article':>18} {'estudo02':>18}")
        for name in nb.params.index:
            if name == 'alpha':
                continue
            short = _glm_short(name)
            a = art.get(short)
            a_cell = f"{a[0]:.3f} ({a[1]})" if a else "--"
            lines.append(f"  {short:<26} {a_cell:>18} {np.exp(nb.params[name]):.3f} ({_glm_pfmt(nb.pvalues[name])})".replace(") ", ")  "))
        lines.append("")

    # --- ape against the other arms ---------------------------------------------
    # The reference arm is not the same program in the two campaigns: estudo02 runs monkey
    # with ignore_crashes/ignore_timeouts, the article did not, and monkey is the one arm
    # whose unique-misuse total barely moved between them. A contrast between two arms that
    # share their configuration is free of that shift, so ape's position is read here too.
    # Article side: point ratio of its two published IRRs (its covariance is not published).
    lines.append("### ape against each non-reference arm (primary model; Wald, cluster-robust, p raw)")
    lines.append(f"  {'contrast':<32} {'article ratio':>14} {'estudo02 IRR':>13} {'p':>10}")
    names = list(nb.params.index)
    ape = "C(tool, Treatment('monkey'))[T.ape]"
    for other in [n for n in names if n.startswith("C(tool") and n != ape]:
        r = np.zeros(len(names))
        r[names.index(ape)], r[names.index(other)] = 1.0, -1.0
        t = nb.t_test(r)
        a, b = art.get("tool[ape]"), art.get(_glm_short(other))
        a_cell = f"{a[0] / b[0]:.3f}" if a and b else "--"
        lines.append(f"  {'ape vs ' + _glm_short(other)[5:-1]:<32} {a_cell:>14}"
                     f" {float(np.exp(t.effect[0])):13.3f} {_glm_pfmt(float(t.pvalue)):>10}")
    lines.append("")

    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Where the unique misuses of the article (`jca`) and of estudo02 (`jca_android`) differ, per spec.

Both campaigns ran the same design over 162 common APKs; only the specification set changed.
The article's `errors.csv` (read-only) and estudo02's regenerated `errors.csv` share the
columns `apk, rep, timeout, tool, spec, class, method`, and that is all this reads.

Two counts per spec, on the 162 common APKs:
- `soma_run`: the article's tabulated quantity — distinct (class, method) per run, summed over
  runs (so a point found in many runs counts many times);
- `pontos`: distinct (apk, class, method) over the whole campaign.

And the point-level set difference, ignoring the spec: (apk, class, method) that the article
flags and estudo02 never flags, and the converse, each with the specs that flagged it.

    uv run python experimento-estudo02/scripts/specs_jca_vs_android.py > experimento-estudo02/docs/<data>_specs_jca_vs_android.md
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ARTICLE = Path("/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/"
               "ase-journal/dataset/results/errors.csv")
CAMPAIGN = ROOT / "data" / "results" / "estudo02_consolidado" / "errors.csv"
# The corpus is the summary's APK set: errors.csv only lists APKs that violated something.
ARTICLE_SUMMARY = ARTICLE.with_name("summary.csv")
CAMPAIGN_SUMMARY = CAMPAIGN.with_name("summary.csv")
COLS = ["apk", "rep", "timeout", "tool", "spec", "class", "method"]
RUN = ["apk", "rep", "timeout", "tool"]


def per_spec(d: pd.DataFrame) -> pd.DataFrame:
    run4 = d[RUN + ["class", "method", "spec"]].drop_duplicates()
    return pd.DataFrame({
        "linhas": d.groupby("spec").size(),
        "soma_run": run4.groupby("spec").size(),
        "pontos": d[["apk", "class", "method", "spec"]].drop_duplicates().groupby("spec").size(),
        "apks": d.groupby("spec")["apk"].nunique(),
    })


def main():
    a = pd.read_csv(ARTICLE, usecols=COLS)
    b = pd.read_csv(CAMPAIGN, usecols=COLS)
    corpus_a = set(pd.read_csv(ARTICLE_SUMMARY, usecols=["apk"])["apk"])
    corpus_b = set(pd.read_csv(CAMPAIGN_SUMMARY, usecols=["apk"])["apk"])
    common = corpus_a & corpus_b
    only = sorted((corpus_a | corpus_b) - common)
    a, b = a[a["apk"].isin(common)], b[b["apk"].isin(common)]

    t = per_spec(a).join(per_spec(b), how="outer", lsuffix="_jca", rsuffix="_android").fillna(0).astype(int)
    t = t.sort_values("soma_run_jca", ascending=False)
    print(f"# Maus usos por spec: `jca` (artigo) × `jca_android` (estudo02)\n")
    print(f"{len(common)} APKs em comum; fora da comparação: {', '.join(only)}.\n")
    print("| spec | linhas jca | linhas android | Σ por run jca | Σ por run android | pontos jca | pontos android | APKs jca | APKs android |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for spec, r in t.iterrows():
        print(f"| {spec} | {r.linhas_jca} | {r.linhas_android} | {r.soma_run_jca} | {r.soma_run_android} "
              f"| {r.pontos_jca} | {r.pontos_android} | {r.apks_jca} | {r.apks_android} |")
    tot = t.sum()
    print(f"| **total** | {tot.linhas_jca} | {tot.linhas_android} | {tot.soma_run_jca} | {tot.soma_run_android} "
          f"| {tot.pontos_jca} | {tot.pontos_android} | | |\n")

    run3_a = a[RUN + ["class", "method"]].drop_duplicates()
    run3_b = b[RUN + ["class", "method"]].drop_duplicates()
    print(f"Sem a spec na chave — distintos (class, method) por run, somados: jca {len(run3_a)}, android {len(run3_b)}.\n")

    pa = a.groupby(["apk", "class", "method"])["spec"].agg(lambda s: ",".join(sorted(set(s))))
    pb = b.groupby(["apk", "class", "method"])["spec"].agg(lambda s: ",".join(sorted(set(s))))
    lost, gained = pa[~pa.index.isin(pb.index)], pb[~pb.index.isin(pa.index)]
    print(f"## Pontos (apk, class, method)\n")
    print(f"jca {len(pa)}, android {len(pb)}, em ambos {len(pa.index.intersection(pb.index))}; "
          f"só no jca {len(lost)}; só no android {len(gained)}.\n")
    for title, s in (("Só o `jca` acusa, por spec que acusava", lost), ("Só o `jca_android` acusa, por spec que acusa", gained)):
        print(f"### {title}\n")
        print("| specs | pontos | APKs |")
        print("|---|---:|---:|")
        g = s.reset_index().groupby("spec").agg(pontos=("method", "size"), apks=("apk", "nunique"))
        for spec, r in g.sort_values("pontos", ascending=False).iterrows():
            print(f"| {spec} | {r.pontos} | {r.apks} |")
        print()


if __name__ == "__main__":
    main()

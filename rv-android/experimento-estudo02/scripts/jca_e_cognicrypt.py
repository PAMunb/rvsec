#!/usr/bin/env python3
"""The numbers behind sections 7 and 8 of the executive report of 15/09: the article's jca
accusations by mechanism, the jca_android check that no value accusation is empty, and the
CogniCrypt reports over the corpus.

1. **jca by mechanism.** The article's published `errors.csv` has no code or event column; the
   error type is the fourth field of `unique_msg`. Misuses are counted with the article's key
   (apk, tool, rep, timeout, class, method, spec) and each is put in one bucket by spec and
   message, in the order `bucket()` tests them. The mechanism behind each bucket was read in the
   `jca` `.mop` files and the pinned CrySL rules (report, section 7); what this script proves is
   the size of each bucket, not the mechanism.
2. **jca_android values.** Every ALG/PROTO/KEYSIZE line of the estudo02 `errors.csv` carries the
   observed value in `val='...'`; an empty one would be the jca "but found ." defect again.
3. **CogniCrypt.** `rvsec-dataset/cognicrypt/*_CryptoAnalysis-Report.csv` (CogniCrypt 5.0.1, `;`
   separated, one row per finding), restricted to nothing: every report file is read, and the
   overlap with the campaign's APKs is stated beside it.

Inputs are read only; the article is never written.

    uv run python experimento-estudo02/scripts/jca_e_cognicrypt.py > experimento-estudo02/docs/<data>_jca_e_cognicrypt.md
"""
import glob
import os
import sys
from pathlib import Path

import pandas as pd

WORKSPACE = Path("/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv")
ARTICLE_ERRORS = WORKSPACE / "ase-journal" / "dataset" / "results" / "errors.csv"
COGNICRYPT = WORKSPACE / "rvsec-dataset" / "cognicrypt"
TABLES = Path(__file__).resolve().parents[2] / "data" / "results" / "estudo02_consolidado"
KEY = ["apk", "tool", "rep", "timeout", "class", "method", "spec"]
ORDER = "InvalidSequenceOfMethodCalls"
#: Bucket -> report group. Group A: the rule's list refuses the platform's correct value;
#: B: defect of the jca spec itself; C: key origin not seen, reported as a wrong sequence;
#: D: MD5/SHA-1, faithful to the rule and rarely relevant.
GROUPS = {
    'SSLContext "TLS" fora da lista': "A", "SSLContext só ORDER (getInstance(\"TLS\"))": "A",
    "KeyStore AndroidKeyStore": "A", "KeyStore só ORDER": "A", "TrustManagerFactory X509": "A",
    'algoritmo vazio ("found .")': "B", "SecureRandomSpec só ORDER": "B",
    "CipherSpec só ORDER": "C",
    "MD5/SHA-1": "D",
}


def bucket(spec: str, msg: str, types: str) -> str:
    if spec == "SSLContextSpec":
        if "found TLS." in msg:
            return 'SSLContext "TLS" fora da lista'
        if "found SSL." in msg:
            return 'SSLContext "SSL"'
        if msg.endswith("found ."):
            return 'algoritmo vazio ("found .")'
        return "SSLContext só ORDER (getInstance(\"TLS\"))"
    if msg.endswith("found ."):
        return 'algoritmo vazio ("found .")'
    if spec == "TrustManagerFactorySpec":
        return "TrustManagerFactory X509"
    if spec == "KeyStoreSpec":
        return "KeyStore AndroidKeyStore" if msg else "KeyStore só ORDER"
    if spec == "MessageDigestSpec" and any(a in msg for a in ("MD5", "SHA-1", "SHA1", "SHA.")):
        return "MD5/SHA-1"
    if types == ORDER:
        return f"{spec} só ORDER"
    return f"{spec}: {msg[:70]}"


def table(frame: pd.DataFrame) -> str:
    cols = list(frame.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(str(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join(out)


def jca() -> None:
    e = pd.read_csv(ARTICLE_ERRORS)
    e["etype"] = e["unique_msg"].str.split(":::").str[3]
    g = e.groupby(KEY).agg(
        types=("etype", lambda s: "+".join(sorted(set(s)))),
        msg=("message", lambda s: "|".join(sorted({m for m in s if m != "unknown"}))),
    ).reset_index()
    g["bucket"] = [bucket(s, m, t) for s, m, t in zip(g["spec"], g["msg"], g["types"])]
    g["group"] = g["bucket"].map(GROUPS).fillna("resto")
    n = len(g)
    print("## 1. `jca`: as acusações publicadas do artigo, por mecanismo\n")
    print(f"Arquivo: `{ARTICLE_ERRORS}` (somente leitura). {len(e)} linhas, **{n} maus usos por execução**,"
          f" em {g['apk'].nunique()} apps.\n")
    print("### Por tipo de erro combinado dentro do mau uso\n")
    print(table(g["types"].value_counts().rename_axis("tipos").reset_index(name="maus usos")))
    print("\n### Por grupo\n")
    grp = g.groupby("group").size().reindex(["A", "B", "C", "D", "resto"]).rename("maus usos").reset_index()
    grp["%"] = (100 * grp["maus usos"] / n).round(1)
    print(table(grp))
    print("\n### Por mecanismo\n")
    b = g.groupby(["group", "bucket"]).size().rename("maus usos").reset_index().sort_values(
        ["group", "maus usos"], ascending=[True, False])
    print(table(b))
    assert b["maus usos"].sum() == n
    print("\n### Em quantos apps\n")
    corpus = set(pd.read_csv(ARTICLE_ERRORS.parent / "summary.csv", usecols=["apk"])["apk"])
    campaign = set(pd.read_csv(TABLES / "per_task.csv", usecols=["apk"])["apk"])
    common = corpus & campaign
    jca_apps = set(g["apk"])
    android_apps = set(pd.read_csv(TABLES / "errors.csv", usecols=["apk"])["apk"])
    groups = g.groupby("apk")["group"].agg(set)
    only_ab = int(groups.map(lambda s: s <= {"A", "B"}).sum())
    print(f"- `jca`: {len(jca_apps)} de {len(corpus)} apps com alguma acusação;"
          f" `jca_android` (bruto da `estudo02`): {len(android_apps)} de {len(campaign)}.")
    print(f"- Nos {len(common)} apps em comum: nos dois {len(jca_apps & android_apps & common)};"
          f" só no `jca` {len((jca_apps - android_apps) & common)};"
          f" só no `jca_android` {len((android_apps - jca_apps) & common)}.")
    print(f"- Apps do `jca` só com acusações dos grupos A e B: {only_ab};"
          f" com algo em C, D ou resto: {len(groups) - only_ab}.")
    empty = g[g["bucket"] == 'algoritmo vazio ("found .")'].groupby("spec").size()
    print("\n### Algoritmo vazio por spec\n")
    print(table(empty.rename("maus usos").reset_index()))
    print("\n### Trechos com mais maus usos só de ORDER\n")
    top = (g[g["types"] == ORDER].groupby(["spec", "class", "method"]).size()
           .sort_values(ascending=False).head(20).rename("maus usos").reset_index())
    print(table(top))


def jca_android_values() -> None:
    e = pd.read_csv(TABLES / "errors.csv", usecols=["spec", "code", "message"])
    v = e[e["code"].str.contains(r"-(?:ALG|PROTO|KEYSIZE)-", na=False)].copy()
    v["val"] = v["message"].str.extract(r"val='([^']*)'")[0].fillna("")
    print("\n## 2. `jca_android`: acusações de valor na `estudo02`\n")
    print(f"Linhas ALG/PROTO/KEYSIZE: **{len(v)}**; com valor vazio: **{int((v['val'] == '').sum())}**;"
          f" do `TrustManagerFactorySpec`: **{int((v['spec'] == 'TrustManagerFactorySpec').sum())}**.\n")
    print(table(v.groupby(["spec", "val"]).size().sort_values(ascending=False).head(15)
                .rename("linhas").reset_index()))


def cognicrypt() -> None:
    files = sorted(glob.glob(str(COGNICRYPT / "*_CryptoAnalysis-Report.csv")))
    frames = [pd.read_csv(f, sep=";", dtype=str).assign(apk=os.path.basename(f).split("_CryptoAnalysis")[0])
              for f in files]
    c = pd.concat(frames, ignore_index=True)
    campaign = set(pd.read_csv(TABLES / "per_task.csv", usecols=["apk"])["apk"])
    reported = {os.path.basename(f).split("_CryptoAnalysis")[0] for f in files}
    rpe = c[c["ErrorType"] == "RequiredPredicateError"]
    tls = rpe["ViolatedRule"].isin(["javax.net.ssl.SSLContext", "javax.net.ssl.TrustManagerFactory"])
    okhttp = rpe["Class"].str.startswith("okhttp3", na=False)
    print("\n## 3. CogniCrypt 5.0.1 sobre o corpus\n")
    print(f"Arquivos de relatório: {len(files)}; apps da campanha com relatório: "
          f"**{len(campaign & reported)} de {len(campaign)}**; apps com algum achado: {c['apk'].nunique()}.\n")
    print(f"Achados: **{len(c)}**; `RequiredPredicateError`: **{len(rpe)}** ({100 * len(rpe) / len(c):.1f} %);"
          f" desses, `SSLContext` + `TrustManagerFactory`: {int(tls.sum())} ({100 * tls.mean():.1f} %);"
          f" em classes do okhttp: {int(okhttp.sum())} ({100 * okhttp.mean():.1f} %).\n")
    print("### Por tipo de erro\n")
    print(table(c["ErrorType"].value_counts().rename_axis("tipo").reset_index(name="achados")))
    print("\n### `RequiredPredicateError` por regra\n")
    print(table(rpe["ViolatedRule"].value_counts().rename_axis("regra").reset_index(name="achados")))
    print("\n### `RequiredPredicateError` por método\n")
    print(table(rpe.groupby(["ViolatedRule", "Class", "Method"]).size().sort_values(ascending=False)
                .head(12).rename("achados").reset_index()))
    print("\n### `RequiredPredicateError` por mensagem\n")
    print(table(rpe["Message"].value_counts().head(12).rename_axis("mensagem").reset_index(name="achados")))


def main():
    print("# `jca` do artigo, valores do `jca_android` e CogniCrypt — números do relatório executivo\n")
    print("Gerado por `experimento-estudo02/scripts/jca_e_cognicrypt.py`. Os mecanismos estão explicados nas"
          " seções 7 e 8 de `20260915_relatorio_executivo.md`; aqui estão só as contagens.\n")
    jca()
    jca_android_values()
    cognicrypt()


if __name__ == "__main__":
    sys.exit(main())

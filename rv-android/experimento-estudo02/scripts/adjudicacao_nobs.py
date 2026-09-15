"""Project the NOBS census verdicts onto the campaign's accusations.

Reads the 181 site verdicts (`docs/adjudicacao_nobs/vereditos.csv`, one row per
`(class, method, spec, code)`) and the campaign's `errors.csv`, and prints, as Markdown,
how many lines, points and per-run misuses each verdict category covers.

A per-run misuse is the article's key `(apk, tool, rep, timeout, class, method, spec)`.
It is decided by NOBS only when none of its codes is something else. ORDER-00 lines of
TrustManagerFactorySpec, KeyManagerFactorySpec and SecureRandomSpec in a key that also
has an ORDER-00 on event `g2` are counted as the getInstance(String) double-match
artifact: the dexlib2 weaver fires both `g1` and `g2` for the one-argument overload,
so the automaton fails on `g2` and the following `init`/`gtm1`/`gkm1` fail with it.
A key whose only non-NOBS codes are that artifact is decided by its NOBS verdicts.

When a key has several NOBS codes, the most severe category wins
(MISUSE > SPEC_DEFECT > LEGIT_UNOBSERVABLE), and its confidence is the lowest among
the codes carrying that category.

Usage:
    uv run python experimento-estudo02/scripts/adjudicacao_nobs.py > <out>.md
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ERRORS = ROOT / "data/results/estudo02_consolidado/errors.csv"
VERDICTS = ROOT / "experimento-estudo02/docs/adjudicacao_nobs/vereditos.csv"

KEY = ["apk", "tool", "rep", "timeout", "cls", "method", "spec"]
CATEGORY_RANK = {"MISUSE": 0, "SPEC_DEFECT": 1, "LEGIT_UNOBSERVABLE": 2}
CONFIDENCE_RANK = {"baixa": 0, "média": 1, "alta": 2}
DOUBLE_MATCH_SPECS = ["TrustManagerFactorySpec", "KeyManagerFactorySpec", "SecureRandomSpec"]

# Which part of the monitoring chain a SPEC_DEFECT root belongs to. Cascades inherit
# the part of their root and are resolved through the `root` column.
DEFECT_PART = {
    "getencoded_producer_not_woven": "weaver",
    "producer_reset_by_g1_g2_double_match": "weaver",
    "keystore_getentry_route_not_credited": "spec: produtor ausente",
    "producer_missing_in_specset": "spec: produtor ausente",
    "random_bytes_not_credited_as_key_material": "spec: decisão registrada (regra CrySL)",
}


def library(cls: str) -> str:
    for prefix, name in [("okhttp3.", "okhttp"), ("com.google.crypto.tink.", "tink"), ("io.ktor.", "ktor")]:
        if cls.startswith(prefix):
            return name
    return "apps e outras bibliotecas"


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    verdicts = pd.read_csv(VERDICTS)
    errors = pd.read_csv(
        ERRORS, usecols=["apk", "rep", "timeout", "tool", "spec", "class", "method", "code", "event"]
    ).rename(columns={"class": "cls"})
    errors["nobs"] = errors.code.str.contains("-NOBS-", na=False)
    errors = errors.merge(
        verdicts[["cls", "method", "spec", "code", "category", "confidence", "mechanism"]],
        on=["cls", "method", "spec", "code"],
        how="left",
    )
    unclassified = errors[errors.nobs & errors.category.isna()]
    if len(unclassified):
        raise SystemExit(f"{len(unclassified)} NOBS lines have no verdict")
    order = errors.code.str.endswith("-ORDER-00", na=False) & errors.spec.isin(DOUBLE_MATCH_SPECS)
    g2_keys = errors[order & (errors.event == "g2")][KEY].drop_duplicates().assign(has_g2=True)
    errors = errors.merge(g2_keys, on=KEY, how="left")
    errors["artifact"] = order & errors.has_g2.fillna(False).astype(bool)
    return verdicts, errors


def decide(errors: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, lines in errors.groupby(KEY):
        other = lines[~lines.nobs & ~lines.artifact]
        nobs = lines[lines.nobs]
        category = confidence = None
        if len(other):
            status = "sustentada por outro código"
        elif len(nobs):
            category = min(nobs.category, key=CATEGORY_RANK.get)
            carrying = nobs[nobs.category == category].confidence
            confidence = min(carrying, key=CONFIDENCE_RANK.get)
            status = f"decidida por NOBS: {category}"
        else:
            status = "só ORDER do duplo casamento"
        rows.append((*key, status, category, confidence, lines.artifact.any()))
    return pd.DataFrame(rows, columns=KEY + ["status", "category", "confidence", "artifact"])


def table(frame: pd.DataFrame) -> str:
    # tabulate is not a workspace dependency, so the Markdown table is written by hand.
    frame = frame.reset_index()
    header = "| " + " | ".join(str(c) for c in frame.columns) + " |"
    rule = "|" + "---|" * len(frame.columns)
    body = ["| " + " | ".join(str(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, rule, *body])


def main() -> None:
    verdicts, errors = load()
    decided = decide(errors)
    nobs = errors[errors.nobs]

    print("## Sítios, pontos e linhas por categoria\n")
    points = nobs.drop_duplicates(["apk", "cls", "method", "spec", "code"])
    summary = pd.DataFrame(
        {
            "sítios": verdicts.category.value_counts(),
            "pontos": points.category.value_counts(),
            "linhas": nobs.category.value_counts(),
        }
    ).fillna(0).astype(int)
    summary.loc["total"] = summary.sum()
    print(table(summary), "\n")

    print("## Maus usos por execução, pelo que os sustenta\n")
    status = decided.status.value_counts().rename("maus usos por execução").to_frame()
    status.loc["total"] = status.sum()
    print(table(status), "\n")
    print(f"Com ORDER do duplo casamento entre os códigos: {int(decided.artifact.sum())}.\n")

    print("## Maus usos decididos por NOBS: categoria × confiança\n")
    nobs_decided = decided[decided.category.notna()]
    print(table(pd.crosstab(nobs_decided.category, nobs_decided.confidence, margins=True)), "\n")

    print("## Maus usos decididos por NOBS: categoria × biblioteca\n")
    print(table(pd.crosstab(nobs_decided.cls.map(library), nobs_decided.category, margins=True)), "\n")

    print("## Maus usos decididos por NOBS e classificados como MISUSE, por método\n")
    misuse = nobs_decided[nobs_decided.category == "MISUSE"]
    print(table(misuse.groupby(["cls", "method"]).agg(maus_usos=("apk", "size"), apks=("apk", "nunique"))), "\n")

    print("## SPEC_DEFECT por parte da cadeia (raízes e cascatas)\n")
    defects = verdicts[verdicts.category == "SPEC_DEFECT"].copy()
    by_site = {(r.cls, r.method, r.code): r for r in defects.itertuples()}

    def part(row) -> str:
        if row.mechanism in DEFECT_PART:
            return DEFECT_PART[row.mechanism]
        root_code, _, root_site = str(row.root).partition(" @ ")
        for (cls, method, code), candidate in by_site.items():
            if code == root_code and root_site.endswith(f"{cls.rsplit('.', 1)[-1]}.{method}") and candidate.mechanism in DEFECT_PART:
                return DEFECT_PART[candidate.mechanism]
        return "não resolvida"

    defects["parte"] = defects.apply(part, axis=1)
    defect_keys = nobs_decided[nobs_decided.category == "SPEC_DEFECT"]
    site_part = defects.set_index(["cls", "method", "spec"]).parte
    site_part = site_part[~site_part.index.duplicated()]
    defect_keys = defect_keys.join(site_part, on=["cls", "method", "spec"])
    print(
        table(
            pd.DataFrame(
                {
                    "sítios": defects.parte.value_counts(),
                    "maus usos decididos": defect_keys.parte.value_counts(),
                }
            ).fillna(0).astype(int)
        ),
        "\n",
    )

    print("## Duplo casamento de getInstance(String)\n")
    artifact = errors[errors.artifact]
    by_spec = pd.DataFrame(
        {
            "linhas ORDER-00 atribuídas": artifact.groupby("spec").size(),
            "maus usos com o artefato": decided[decided.artifact].spec.value_counts(),
            "maus usos só com o artefato": decided[decided.status == "só ORDER do duplo casamento"].spec.value_counts(),
        }
    ).fillna(0).astype(int)
    print(table(by_spec), "\n")

    total = len(decided)
    kept = int((decided.status == "sustentada por outro código").sum()) + int((decided.category == "MISUSE").sum())
    print("## Sensibilidade\n")
    print(f"- Maus usos por execução na campanha: {total}.")
    print(f"- Sustentados por outro código ou decididos por NOBS como MISUSE: {kept} ({kept / total:.1%}).")


if __name__ == "__main__":
    main()

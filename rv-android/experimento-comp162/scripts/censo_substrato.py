#!/usr/bin/env python3
"""Censo do substrato MOP dos 162 APKs, calculado como o `aperv-tool` calcula.

O censo não é lido do `.apk.json` cru: ele chama `derive()` — a mesma função pura que o
`aperv-tool` roda antes de empurrar o artefato para o dispositivo — porque é o resultado
dela, e não o JSON de entrada, que o jar consome. Contar `transitions` no JSON daria outro
número: `wtgEdges` é a visão só-de-clique do WTG depois das regras de fusão de diálogo e
do descarte de janela sem widget.

Três colunas existem por causa do P11 (`docs/20260812_registro_execucao_prontidao_e3.md`
§3.1), e elas medem coisas diferentes que é fácil confundir:

- `complete` é o que o **produtor afirma** sobre a própria saída. O P11 é justamente a
  descoberta de que ele afirma completude em saída truncada.
- `transitions` é o WTG **cru** no JSON. Zero aqui é o predicado do P11 — 41 dos 162, dos
  quais 40 são truncamento e 1 é grafo genuinamente vazio. Separar os dois exige o
  `timed_out` do `_progress`, que mora no `rvsec-dataset-sa` e não neste diretório.
- `wtg_edges` é o que **sobra depois da derivação**: a visão só-de-clique, depois da fusão
  de diálogo e do descarte de janela sem widget. É o que o jar de fato recebe, e é bem
  menor — um app pode ter transições e nenhuma aresta de clique.

O censo reporta as três porque a leitura da cobertura do braço guiado depende da terceira,
enquanto a rastreabilidade até o defeito da análise estática depende das duas primeiras.

Uso:
    uv run python scripts/censo_substrato.py            # escreve censo_substrato.csv
    uv run python scripts/censo_substrato.py --summary  # só o resumo, sem escrever
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parent

sys.path.insert(0, str(ROOT / "modules" / "aperv-tool" / "src"))
from aperv_tool.tools.aperv.derive_mop_artifact import DerivationError, derive  # noqa: E402

DATASET = Path(
    "/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET"
    "/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162"
)
OUT = EXP / "censo_substrato.csv"

COLUMNS = [
    "apk",
    "windows",
    "widgets",
    "flagged",
    "wtg_edges",
    "recovered",
    "mop_acts",
    "mop_acts_aug",
    "opt_menus",
    "transitions",  # WTG cru no JSON; zero é o predicado do P11
    "complete",  # o sentinela do produtor, que o P11 mostrou não ser confiável
]


def census_row(apk: str) -> dict:
    doc = json.loads((DATASET / f"{apk}.json").read_text())
    raw = {
        "transitions": len(doc.get("transitions") or []),
        "complete": bool(doc.get("complete", False)),
    }
    try:
        art = derive(doc, source_file=f"{apk}.json", source_digest="")
    except DerivationError as e:
        return {"apk": apk, **{c: -1 for c in COLUMNS[1:-2]}, **raw, "error": str(e)}
    s = art.get("stats", {})
    return {
        "apk": apk,
        "windows": s.get("windows", 0),
        "widgets": s.get("widgets", 0),
        "flagged": s.get("flagged", 0),
        "wtg_edges": s.get("wtgEdges", 0),
        "recovered": s.get("recovered", 0),
        "mop_acts": len(art.get("mopActivities", [])),
        "mop_acts_aug": len(art.get("mopActivitiesAugmented", [])),
        "opt_menus": len(art.get("optionsMenus", [])),
        **raw,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true", help="não escreve o CSV")
    args = ap.parse_args()

    apks = sorted(p.name for p in DATASET.glob("*.apk"))
    rows = [census_row(a) for a in apks]

    if not args.summary:
        with OUT.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"escrito {OUT} ({len(rows)} APKs)")

    flagged = [r for r in rows if r["flagged"] > 0]
    wtg = [r for r in rows if r["wtg_edges"] > 0]
    tres = [r for r in rows if r["flagged"] > 0 and r["wtg_edges"] > 0 and r["mop_acts"] > 0]
    cru_zero = [r for r in rows if r["transitions"] == 0]
    cru_zero_mentiu = [r for r in cru_zero if r["complete"]]

    print()
    print(f"{'total':40s} {len(rows):4d}")
    print(f"{'com widget sinalizado (flagged>0)':40s} {len(flagged):4d}")
    print(f"{'com WTG povoado após derivação (>0)':40s} {len(wtg):4d}")
    print(f"{'com os três sinais':40s} {len(tres):4d}")
    print()
    print(f"{'WTG cru vazio (transitions==0) — P11':40s} {len(cru_zero):4d}")
    print(f"{'   destes, declarando complete=true':40s} {len(cru_zero_mentiu):4d}")
    print(f"{'WTG derivado vazio (wtg_edges==0)':40s} {len(rows) - len(wtg):4d}")
    print()
    print("Os três primeiros são os estratos da análise: um efeito que só pode existir onde")
    print("há substrato aparece diluído no agregado. Os três últimos são a leitura do P11 —")
    print("`transitions==0` é o predicado dele (40 truncados + 1 genuinamente vazio, separáveis")
    print("só pelo `timed_out` do `_progress`), e `wtg_edges==0` é quanto do corpus entrega")
    print("grafo de clique vazio ao braço guiado, que é o número que a leitura da cobertura usa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

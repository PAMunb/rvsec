#!/usr/bin/env python3
"""Deriva os filtros da comp162 dos filtros da cmp163, removendo o APK que saiu.

Os filtros NÃO são gerados por round-robin sobre a lista nova, e a distinção importa.
A comp162 vai ser comparada pareada contra a cmp163 por aplicação, e as duas campanhas
rodam no mesmo host com oito containers competindo. Se uma aplicação trocasse de índice
de container entre as campanhas, efeito-de-container deixaria de cancelar na diferença
pareada — foi o custo que a emenda 01 da gh97 teve de assumir e registrar quando
reparticionou de 8 x 5 para 10 x 4.

Aqui esse custo não precisa ser pago. O corpus novo é o antigo menos exatamente um APK
(`info.dvkr.screenstream_44000.apk`, excluído por estourar o teto de 64K referências do
DEX), então herdar os oito arquivos e apagar uma linha preserva o índice de container de
todas as 162 aplicações. Gerar round-robin sobre a lista nova faria o oposto: remover um
elemento renumera tudo que vem depois dele e desloca ~metade do corpus.

Uso:
    python3 scripts/make_filters.py            # verifica e escreve filters/
    python3 scripts/make_filters.py --check    # só verifica, não escreve
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parent

SOURCE_FILTERS = ROOT / "data" / "cmp163_filters"
DEST_FILTERS = EXP / "filters"
DATASET = Path(
    "/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET"
    "/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162"
)
DROPPED = "info.dvkr.screenstream_44000.apk"
N_BATCHES = 8

# Os dois APKs do smoke, um por container. Escolhidos pelo artefato, não por cobertura: o
# smoke existe para provar que os três braços resolvem o que declaram, e um APK sem
# substrato MOP deixaria os portões do RUN_START vazios de conteúdo. Ambos têm os três
# sinais no censo — `flagged`, `wtgEdges` e `mopActivities` todos > 0 — então o braço de
# referência tem o que consumir em cada uma das três vias.
#
# O `binaryeye` é deliberado: é um dos dez APKs cujo WTG a re-análise da gh91 recuperou
# (0 -> 177 arestas). Pôr justamente ele no smoke faz o portão exercitar o substrato novo,
# que é a diferença desta campanha para a cmp163 que mais toca o braço guiado.
SMOKE = ["io.keepalive.android_133.apk", "de.markusfisch.android.binaryeye_174.apk"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verifica sem escrever")
    args = ap.parse_args()

    on_disk = {p.name for p in DATASET.glob("*.apk")}
    batches: list[list[str]] = []
    for i in range(N_BATCHES):
        src = SOURCE_FILTERS / f"batch_{i:02d}.txt"
        lines = [ln.strip() for ln in src.read_text().splitlines() if ln.strip()]
        batches.append([a for a in lines if a != DROPPED])

    union = [a for b in batches for a in b]
    problems = []
    if len(union) != 162:
        problems.append(f"união tem {len(union)} APKs, esperado 162")
    if len(set(union)) != len(union):
        problems.append("há APK duplicado entre os lotes")
    if set(union) != on_disk:
        missing = sorted(on_disk - set(union))
        extra = sorted(set(union) - on_disk)
        problems.append(f"união != dataset (faltando {missing}, sobrando {extra})")
    for a in SMOKE:
        if a not in on_disk:
            problems.append(f"APK do smoke ausente do dataset: {a}")

    sizes = [len(b) for b in batches]
    print(f"lotes: {sizes}  (soma {sum(sizes)})")
    print(f"lote mais cheio: {max(sizes)} APKs -> {max(sizes) * 3 * 3} runs no container crítico")
    for p in problems:
        print(f"FALHA: {p}", file=sys.stderr)
    if problems:
        return 1

    if args.check:
        print("VERIFICAÇÃO OK — nada escrito (--check)")
        return 0

    DEST_FILTERS.mkdir(parents=True, exist_ok=True)
    for i, b in enumerate(batches):
        (DEST_FILTERS / f"batch_{i:02d}.txt").write_text("\n".join(b) + "\n")
    for i, a in enumerate(SMOKE):
        (DEST_FILTERS / f"smoke_{i:02d}.txt").write_text(a + "\n")
    print(f"escritos {N_BATCHES} lotes + {len(SMOKE)} filtros de smoke em {DEST_FILTERS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

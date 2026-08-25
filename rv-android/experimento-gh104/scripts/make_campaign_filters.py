#!/usr/bin/env python3
"""Deriva a partição da CAMPANHA herdando a da `comp162` e apenas podando o que caiu.

    uv run python experimento-gh104/scripts/make_campaign_filters.py --check
    uv run python experimento-gh104/scripts/make_campaign_filters.py --corpus <dir>

## Dois particionamentos diferentes moram no mesmo `filters/`, e confundi-los custa caro

- `s0.txt` … `sN.txt` são os **shards da instrumentação** (estágio 1). Existem para dividir
  trabalho entre processos `rv-experiment` concorrentes no host; a única propriedade que
  importa neles é que cada shard tenha seu próprio `--output-dir`, porque o `BatchRunner`
  resolve `workDir.resolve("woven_...")` com nomes planos e duas JVMs no mesmo work dir se
  sobrescrevem **sem erro**.
- `batch_00.txt` … `batch_07.txt` são a **partição da campanha** (estágio 2), e é o que
  este script escreve. Aqui a propriedade que importa é outra, e é a razão do script
  existir.

## Por que herdar e podar, em vez de gerar

Cada aplicação tem de cair no **mesmo índice de container** que caiu na `comp162`. É isso
que faz o efeito-de-container CANCELAR na diferença pareada entre as duas campanhas em vez
de virar parte dela: as duas rodam no mesmo host, com oito containers disputando CPU,
memória e I/O, e um container é sistematicamente mais lento que outro ao longo da corrida.
Se uma aplicação trocasse de índice, essa diferença sistemática entraria no efeito medido
sob o nome de "conjunto de specs", que é exatamente o que a campanha quer isolar.

Gerar round-robin sobre a lista de sobreviventes faria o oposto do que parece: remover um
elemento renumera tudo que vem depois dele e desloca cerca de metade do corpus. Foi o custo
que a emenda 01 da gh97 teve de assumir e registrar quando reparticionou de 8 x 5 para
10 x 4, e aqui ele não precisa ser pago.

**O preço da poda**, declarado e não escondido: os lotes ficam desiguais e um container
termina antes, o que muda a contenção do host ao longo do tempo em relação à `comp162`. É
custo de segunda ordem — muito menor que o de quebrar o pareamento de índice — e o script
imprime os tamanhos resultantes justamente para que a assimetria seja **vista**, e não
descoberta depois.

## O que faz o script parar, antes de escrever qualquer arquivo

- um sobrevivente que não está em lote nenhum — significa que o corpus contém uma aplicação
  que a partição da `comp162` nunca teve, e aí a herança não descreve mais o corpus;
- um lote que ficaria vazio — container sem trabalho é erro de configuração, não poda;
- nenhum candidato a APK de smoke com os três sinais do censo.

## Os APKs do smoke

Herdados da `comp162` quando sobrevivem. Se um deles cair no estágio 1, o substituto é
**derivado, não escolhido**: o primeiro sobrevivente, em ordem, com os três sinais no censo
(`flagged > 0`, `wtg_edges > 0`, `mop_acts > 0`). O censo da `comp162` serve para isso
porque esta campanha **reusa os `.apk.json` dela** — o substrato é literalmente o mesmo
artefato, então o censo antigo descreve o corpus novo sem uma linha de diferença. Toda
substituição é impressa em voz alta.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import CorpusPending, dataset_dir  # noqa: E402

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parent

REFERENCE = ROOT / "experimento-comp162"
SOURCE_FILTERS = REFERENCE / "filters"
REFERENCE_CENSO = REFERENCE / "censo_substrato.csv"
DEST_FILTERS = EXP / "filters"
N_BATCHES = 8
N_SMOKE = 2


def read_lines(p: Path) -> list[str]:
    return [ln.strip() for ln in p.read_text().splitlines() if ln.strip()]


def smoke_candidates() -> list[str]:
    """Sobreviventes com os três sinais, em ordem — a fonte dos substitutos do smoke."""
    if not REFERENCE_CENSO.exists():
        return []
    with REFERENCE_CENSO.open() as f:
        return [
            r["apk"]
            for r in csv.DictReader(f)
            if int(r["flagged"]) > 0 and int(r["wtg_edges"]) > 0 and int(r["mop_acts"]) > 0
        ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--corpus",
        default=None,
        help="diretório do corpus instrumentado novo; sem isto, resolvido por padrão",
    )
    ap.add_argument("--check", action="store_true", help="verifica sem escrever")
    args = ap.parse_args()

    try:
        dataset = dataset_dir(args.corpus)
    except CorpusPending as e:
        print(f"FALHA: {e}", file=sys.stderr)
        return 1

    alive = {p.name for p in dataset.glob("*.apk")}
    if not alive:
        print(f"FALHA: nenhum .apk em {dataset}", file=sys.stderr)
        return 1

    batches = {i: read_lines(SOURCE_FILTERS / f"batch_{i:02d}.txt") for i in range(N_BATCHES)}
    pruned = {i: [a for a in b if a in alive] for i, b in batches.items()}
    dropped = {i: [a for a in b if a not in alive] for i, b in batches.items()}

    union_before = {a for b in batches.values() for a in b}
    union_after = {a for b in pruned.values() for a in b}

    # Os do smoke da `comp162`, na mesma ordem, com substituição derivada quando preciso.
    herdados = [read_lines(SOURCE_FILTERS / f"smoke_{i:02d}.txt")[0] for i in range(N_SMOKE)]
    candidatos = [a for a in smoke_candidates() if a in alive]
    smoke: list[str] = []
    substituicoes: list[tuple[str, str]] = []
    for a in herdados:
        if a in alive:
            smoke.append(a)
            continue
        alternativa = next((c for c in candidatos if c not in smoke), None)
        if alternativa is None:
            smoke.append("")  # vira problema abaixo
            continue
        smoke.append(alternativa)
        substituicoes.append((a, alternativa))

    problems = []
    orfaos = sorted(alive - union_before)
    if orfaos:
        problems.append(
            f"{len(orfaos)} sobrevivente(s) fora de qualquer lote: {orfaos[:5]}"
            " — a partição herdada da comp162 não descreve mais o corpus"
        )
    vazios = [i for i, b in pruned.items() if not b]
    if vazios:
        problems.append(f"lote(s) que ficariam vazios: {vazios}")
    if any(not a for a in smoke):
        problems.append(
            "sem candidato a APK de smoke com os três sinais do censo — escolher à mão e "
            f"conferir contra {REFERENCE_CENSO}"
        )

    sizes_before = [len(batches[i]) for i in range(N_BATCHES)]
    sizes_after = [len(pruned[i]) for i in range(N_BATCHES)]
    print(f"corpus: {dataset}")
    print(f"sobreviventes: {len(alive)}   união dos lotes da comp162: {len(union_before)}")
    print(f"lotes herdados: {sizes_before}  (soma {sum(sizes_before)})")
    print(f"lotes podados:  {sizes_after}  (soma {sum(sizes_after)})")
    print(f"perdidos no estágio 1: {len(union_before - union_after)}")
    for i in range(N_BATCHES):
        if dropped[i]:
            print(f"  batch_{i:02d}: -{len(dropped[i])}  {', '.join(dropped[i])}")

    maior = max(sizes_after) if sizes_after else 0
    menor = min(sizes_after) if sizes_after else 0
    print(f"lote mais cheio: {maior} APKs -> {maior * 3 * 3} runs no container crítico")
    print(
        f"desequilíbrio: {maior - menor} APK(s) entre o maior e o menor lote — o container "
        "mais vazio termina antes e a contenção do host cai no fim da corrida"
    )
    print(f"identidades previstas: {len(union_after) * 3 * 3}")
    for antigo, novo in substituicoes:
        print(f"SMOKE substituído: {antigo} não sobreviveu -> {novo} (três sinais no censo)")
    print(f"smoke: {smoke}")

    for p in problems:
        print(f"FALHA: {p}", file=sys.stderr)
    if problems:
        return 1

    if args.check:
        print("VERIFICAÇÃO OK — nada escrito (--check)")
        return 0

    DEST_FILTERS.mkdir(parents=True, exist_ok=True)
    for i in range(N_BATCHES):
        (DEST_FILTERS / f"batch_{i:02d}.txt").write_text("\n".join(pruned[i]) + "\n")
    for i, a in enumerate(smoke):
        (DEST_FILTERS / f"smoke_{i:02d}.txt").write_text(a + "\n")
    print(
        f"escritos {N_BATCHES} lotes + {N_SMOKE} filtros de smoke em {DEST_FILTERS} "
        "(índice de container preservado)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

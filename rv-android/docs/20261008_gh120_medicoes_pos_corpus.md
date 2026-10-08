# gh120 — medições pós-corpus (A4 e A6), rodada A do E6

Data: 08/10/2026. Leitura só, sobre os resultados da análise estática do Estudo 03 já prontos.
Objetivo: decidir se os dois riscos que a revisão de código da gh120 adiou (A4 e A6, ver
`docs/20261007_gh120_code_review.md` e o design arquivado em
`openspec/changes/archive/2026-10-07-gh120-gator-distance-hosted-windows/design.md`) justificam
uma change nova.

## Fonte e proveniência

- Dados: `rvsec-study03-replication-package/data/raw/e6-static-analysis/A/<apk>/` (`<apk>.json`,
  `analysis.log`, `record.json`). A rodada A terminou; nada é escrito ali. As rodadas C, D e S
  ainda rodavam às 16h de 08/10 e não entram nesta medição.
- Código do GATOR que gerou a rodada: árvore `rvsec-gator` `057be1d1`, a mesma do commit de
  arquivo da gh120 (`c9a43d98`) — conferido com `git rev-parse <commit>:rvsec/rvsec-android/rvsec-gator`.
  Os jars foram construídos dentro da imagem `phtcosta/rvandroid:0.9.5`, a partir dessa árvore;
  o código é o mesmo do jar das 17:33 de 07/10, os bytes dos jars não foram comparados.
- Script: `medir_a4_a6.py` (scratchpad da sessão), executado com `python3 -I`.

## Amostra

| | APKs | proporção dos 163 |
|---|---:|---:|
| Diretórios na rodada A | 163 | 100 % |
| Com JSON | 92 | 56 % |
| JSON com `complete: true` (WTG terminada) | 70 | 43 % |
| JSON com `complete: false` (JSON pré-WTG, GATOR cortado em 1800 s) | 22 | 13 % |
| Sem JSON (vão para a rodada C) | 71 | 44 % |

A amostra é de quem terminou primeiro: tende para os APKs menores. Os 71 que faltam são os que
estouraram tempo ou memória.

## A6 — falha ao gerar as arestas de lambda

O risco: se `LambdaEdges.addTo` lança, o artefato sai com wrappers marcados só pelo SPARK e o
derive confia neles (INV-DRV-09).

- `Lambda edges failed` aparece em **0 dos 92** logs com JSON (e em 0 dos 163 logs da rodada).
- A linha `[LambdaEdges] added N edges` aparece nos 92: todos passaram pela fase. O log
  efetivamente carrega o stdout do cliente, então a ausência da falha é medida, não suposta.
- 6 dos 92 (7 %) adicionaram 0 arestas. Não é falha: nos seis, `wrapper: 0, sam: 0` e todas as
  lambdas já estavam no grafo de chamadas (`already in call graph` de 2 a 206).

**Resultado: 0/92. Nada a corrigir com base nesta amostra.**

## A4 — janela HOSTED cuja hospedeira não está no manifesto

O risco: `HostResolver.hostsOf` aceitar como hospedeira uma activity que o manifesto não declara
(uma activity base, por exemplo), gerando uma janela que nunca abre no dispositivo.

- 66 dos 92 APKs (72 %) têm janelas HOSTED; são 1 813 janelas HOSTED de 3 748 janelas no total
  (48 %), 1 260 delas com pelo menos um listener.
- Janelas HOSTED cuja hospedeira (o nome antes de `#`) não está em
  `components.activities[].className`: **0 de 1 813, em 0 APKs**.

**Resultado: 0/1 813. Nada a corrigir com base nesta amostra.**

## Achado lateral (não é da gh120)

O `sa_runs.csv` do replication package marca as 92 tarefas da rodada A como `complete`, mas 22
desses JSON têm `complete: false`: o GATOR gravou o JSON pré-WTG (entre 76 s e 1 791 s) e foi
cortado no teto de 1 800 s antes de terminar a WTG. Se a escada C/D/S só re-executa quem ficou
sem JSON, esses 22 APKs terminam a campanha sem WTG. Passado para a sessão `rep-pack-e03`.

## Pendências que dependem do conjunto final

Nenhuma da gh120. A lista de APKs sem artefato ou sem `complete` no fim da escada é conferência da
própria campanha e fica com o replication package.

# `experimento-estudo02-20260916` — re-execução da estudo02 com o tecelão consertado

Estudo 2 da tese, relatado no `ase-journal`: 11 configurações de ferramenta × corpus `jca_android` ×
3 repetições × 60/180/300 s. É o mesmo desenho da `experimento-estudo02/` (08–14/09), agora com a
gh114 (tecelão A1–A5, rótulos de `-NOBS-`, exportação sem OOM) e a imagem 0.9.4 (gh115).

- **Plano:** `docs/20260916_plano.md`. O que muda, as perguntas, os portões, a escolha de 12
  containers e os riscos.
- **Constantes:** `scripts/campanha.env`, a única fonte. Os scripts leem dele.
- **Nome:** `estudo02-20260916`. Containers `estudo02-20260916_NN`, resultados
  `data/results/estudo02-20260916_NN/`, filtros `data/estudo02-20260916_filters/`. Smoke:
  `estudo02-20260916-smoke`.

## Estado

Preparado em 15/09/2026. **Esperando as etapas 1–5**, que são de outras changes.

| # | Etapa | Estado |
|---|---|---|
| 1 | gh114 implementada e comitada | pendente (0 de ~90 tarefas em 15/09) |
| 2 | gh115 aplicada (0.9.4-SNAPSHOT, reator verde, commit) | pendente, atrás da gh114 |
| 3 | push do branch `modules` | pendente |
| 4 | cadeia Docker 0.9.4 construída (camadas 1–4) | pendente |
| 5 | reinstrumentação do corpus (`rvsec-dataset`, `reinstrument-jca-android`) | pendente, atrás da 3 e da 4 |
| 6 | `RVSEC_MIN_COMMIT` preenchido em `campanha.env` | pendente |
| 7 | exportação do corpus | — |
| 8 | sweep de tecelagem + `docs/tecelagem.md` | — |
| 9 | compose/filtros/meta gerados; sha256 do corpus: `________________` | — |
| 10 | preflight (smoke) | — |
| 11 | smoke + `docs/smoke.md` | — |
| 12 | preflight (campanha) + launch | — |

## Propostas a confirmar pelo Pedro

Escolhidas na preparação, com base nos dados da `estudo02`. Nenhuma foi confirmada; os scripts já as
usam, mas cada uma se troca em `campanha.env`.

1. **12 containers × 10 g, `restart: on-failure:50`** (plano §4): ~4,1 dias de máquina contra ~4,95
   com 10, pelo mesmo método (a `estudo02` levou 5,87 dias do launch ao fim do reparo).
2. **Smoke com 12 containers e 12 APKs** escolhidos pelos consertos da gh114 (plano §7.4), no lugar
   dos 2 APKs em 2 containers da `estudo02`.
3. **Nome `estudo02-20260916`, com hífen**, e não `estudo02_...`.
4. **Corpus montado a partir de uma cópia** em `RV_ANDROID_DATASET_FINAL/..._dexlib2_094`, e não do
   diretório do `rvsec-dataset`.
5. **Portões novos 7–9 do smoke** e a exigência do sweep de tecelagem sobre o corpus inteiro antes do
   launch.
6. **Análise:** a pergunta Q3 e um desfecho definido pelos rótulos da gh114 (plano §3, §9) são
   sugestões; nenhum script foi escrito para eles.

## Arquivos

```
experimento-estudo02-20260916/
├── README.md                          este arquivo
├── docs/
│   └── 20260916_plano.md              plano
│   (gerados na execução: <data>_<nome>_gerado.md, tecelagem_sweep.csv, tecelagem.md, smoke.md)
├── scripts/
│   ├── campanha.env                   constantes (bash e Python)
│   ├── campanha.py                    leitor do campanha.env para os scripts Python
│   ├── exportar_corpus.py             rvsec-dataset → pasta montada, com os 5 portões da exportação
│   ├── gerar_campanha.sh              gen_compare do smoke e da campanha; compose vem para cá
│   ├── preflight.sh                   smoke | campanha
│   ├── smoke_gates.py                 os 9 portões do smoke + calibração de contenção
│   ├── admissibility.py               C1–C6 por identidade (cópia parametrizada da estudo02)
│   └── repair.py                      devolve inadmissíveis à fila (cópia parametrizada)
└── (gerados) docker-compose.estudo02-20260916{,-smoke}.yml
```

Filtros e meta ficam em `data/`, onde o `monitor_compare.sh`, o `consolidate_compare.py` e o
`admissibility.py` os procuram. Os composes usam `../data/...`, que resolve igual daqui.

## Execução, passo a passo

Todos os comandos rodam da raiz do `rv-android/`.

### 0. Antes de tudo: gh114 → gh115 → push → Docker 0.9.4 → reinstrumentação

Nada aqui substitui essas changes. Depois do build da imagem, preencher `RVSEC_MIN_COMMIT` em
`scripts/campanha.env` com o commit da gh115, que já está no `origin/modules`.

### 1. Exportar o corpus

```bash
uv run python experimento-estudo02-20260916/scripts/exportar_corpus.py            # confere
uv run python experimento-estudo02-20260916/scripts/exportar_corpus.py --apply    # copia
```

Reprova se o N₄ mudar de composição, se um `.apk` for byte-idêntico ao da `estudo02`, se um
`.apk.json` diferir do da `estudo02`, se um sha256 não bater com os manifestos, ou se a proveniência
não contiver o commit da gh115. Uma mudança de composição aceita entra com `--aceitar-corpus` e é
registrada no plano (§5).

### 2. Sweep de tecelagem sobre o corpus inteiro

O script é da gh114 (`scripts/gh114_weave_sweep.py <apk_dir> <descriptor.json> <out.csv>`, tarefa 6.3
dela). Rodar sobre `$DATASET` com o descritor gerado pelas specs da gh114:

```bash
source experimento-estudo02-20260916/scripts/campanha.env
uv run python scripts/gh114_weave_sweep.py "$DATASET" <descriptor.json> \
    experimento-estudo02-20260916/docs/tecelagem_sweep.csv
```

Aceite (plano §7.2): (a) = (b) = (c) = 0 em todo APK, e (d) tecido onde a chamada existe. Escrever o
veredito em `docs/tecelagem.md`, com qualquer resíduo listado por APK.

### 3. Gerar compose, filtros e meta

```bash
experimento-estudo02-20260916/scripts/gerar_campanha.sh
```

Anotar o sha256 do corpus na tabela de Estado.

### 4. Preflight e smoke

```bash
experimento-estudo02-20260916/scripts/preflight.sh smoke
docker compose -f experimento-estudo02-20260916/docker-compose.estudo02-20260916-smoke.yml up -d
.claude/skills/rv-experiment-compare/scripts/monitor_compare.sh estudo02-20260916-smoke --no-resume
# quando todos os 12 tiverem saído (~30 min):
uv run python experimento-estudo02-20260916/scripts/smoke_gates.py    # ANTES do down
docker compose -f experimento-estudo02-20260916/docker-compose.estudo02-20260916-smoke.yml down
```

Escrever `docs/smoke.md` com o veredito dos 9 portões e a calibração de contenção. Se o overhead
total passar de 90 s, ou aparecer OOM do host, recuar para 11 × 10 g **antes** do launch: editar
`campanha.env`, remover os composes gerados e rodar o passo 3 de novo.

### 5. Launch

```bash
experimento-estudo02-20260916/scripts/preflight.sh campanha
docker compose -f experimento-estudo02-20260916/docker-compose.estudo02-20260916.yml up -d
```

### 6. Monitoramento

```bash
.claude/skills/rv-experiment-compare/scripts/monitor_compare.sh estudo02-20260916 --no-resume
docker ps -a --filter name=estudo02-20260916_ --format '{{.Names}} {{.Status}}'
docker stats --no-stream ; free -g ; journalctl -k -g oom-kill --since today | tail
```

- **O Docker religa** o container que sai com erro (`on-failure:50`).
- **Religamento à mão:** só para container que saiu e parou (esgotou a política).
- **Travamento:** é alerta a partir de ≥ 2 h sem nenhuma task fechar, e se confirma pelo
  `docker logs` antes de tocar.
- **Não usar o auto-resume do monitor em intervalo curto:** vira laço de restart.

### 7. Pós-corrida

```bash
docker compose -f experimento-estudo02-20260916/docker-compose.estudo02-20260916.yml up -d   # passada de resume final
# com tudo parado:
uv run python experimento-estudo02-20260916/scripts/admissibility.py --json experimento-estudo02-20260916/docs/admissibilidade.json
docker run --rm -u 0 -v "$PWD:/w" -w /w --entrypoint python3 phtcosta/rvandroid:0.9.4 \
    experimento-estudo02-20260916/scripts/repair.py estudo02-20260916_00     # sem --apply: só mostra
uv run python .claude/skills/rv-experiment-compare/scripts/consolidate_compare.py estudo02-20260916 \
    --admissibility experimento-estudo02-20260916/docs/admissibilidade.json
```

A análise (plano §9) ainda pede dois scripts:

- a adaptação do `rq1_estudo02.py`, que tem `N_EXPECTED` e o caminho do consolidado fixos;
- o desfecho por rótulos, que só se escreve depois que a gh114 fixar o vocabulário.

## Lições da estudo02 que valem aqui

- **Contagem:** sempre por identidade `(apk, braço, rep, orçamento)`, nunca por registro, nunca grep
  cru no `tasks.json`.
- **Zero estrutural do `qtesting`:** o `qtesting` zera nos APKs sem `launchable-activity` (19 na
  `estudo02`). É categoria declarada e não volta à fila. O mesmo vale para a parada da ferramenta (a
  marca nas 3 réplicas) e o lançamento fora do app.
- **C2:** mede o tempo da **ferramenta** (`end_time − tool_execution_start`) com piso de
  orçamento − 5 s. O `execution_time_seconds` inclui ~54 s de boot e instalação.
- **`monkey`:** as flags vão com `=true` em cada uma; flag nua vira ferramenta nova. O `gen_compare`
  agora conta os braços certo com essa sintaxe.
- **`RestartCount`:** não conta `docker restart` manual; só o `StartedAt` denuncia.
- **Resultados:** pertencem ao root. Escrever neles só via `docker run -u 0`.
- **Nome da campanha:** o `monitor_compare.sh estudo02` filtra por substring `estudo02_` e não pega
  esta campanha. O hífen do nome novo é de propósito.

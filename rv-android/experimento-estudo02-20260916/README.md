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

Preparado em 15/09/2026. Smoke rodado e aprovado em 16/09/2026. **Campanha lançada em 16/09/2026 13:52:42** (etapa 12).

| # | Etapa | Estado |
|---|---|---|
| 1 | gh114 implementada e comitada | OK — `c375e445` (arquivada 15/09) |
| 2 | gh115 aplicada (0.9.4-SNAPSHOT, reator verde, commit) | OK — `fc51ab64` |
| 3 | push do branch `modules` | OK — `origin/modules` em `fc51ab64` |
| 4 | cadeia Docker 0.9.4 construída (camadas 1–4) | OK — 15/09 22:20, `--no-cache` nas quatro |
| 5 | reinstrumentação do corpus (`rvsec-dataset`, `reinstrument-jca-android`) | OK — 15–16/09, arquivada em `31d0045f20`; N₄ = 163, mesma composição |
| 6 | `RVSEC_MIN_COMMIT` preenchido em `campanha.env` | OK — `fc51ab648dbf…` |
| 7 | exportação do corpus | OK — cópia feita à mão em 16/09, os 5 portões conferidos (ver nota abaixo) |
| 8 | sweep de tecelagem + `docs/tecelagem.md` | OK — (a)(b)(c) = 0, (d) 23/23, 163/163 sem erro |
| 9 | compose/filtros/meta gerados; sha256 do corpus: `84a03578f0c7203b` | OK — 16 137 tasks, maior lote 14 APKs |
| 10 | preflight (smoke) | OK — 22 PASS, 0 FAIL |
| 11 | smoke + `docs/smoke.md` | rodado 16/09 13:10–13:40; **7/9 portões** — 3 e 5 reprovam com causa identificada, dispensados pelo Pedro em 16/09 (`docs/smoke.md`, Decisão) |
| 12 | preflight (campanha) + launch | OK — preflight 24 PASS, 0 FAIL; launch 16/09/2026 13:52:42 |
| 13 | reboot da máquina e retomada | OK — reboot 19/09/2026 ~20:13; os 12 containers voltaram sozinhos às 20:13:15 e o resume rodou (ver nota abaixo) |
| 14 | fase principal encerrada | OK — 20/09/2026 14:48:30 (último: `_04`); **16 137 / 16 137 COMPLETED**, os 12 com exit=0 e os seis arquivos escritos; nenhum container precisou da passada de resume final |
| 15 | admissibilidade C1–C6 completa | OK — 20/09 14:56:40→15:05:43; 15 602 admissíveis, 171 estruturais, 246 paradas, 45 lançamentos externos, 76 inadmissíveis; C6 fecha (`docs/admissibilidade.md`) |
| 16 | reparo das inadmissíveis | OK — 20/09 15:57:49→15:58:31; **72 devolvidas à fila**, 1 `REVISAR`, 144 artefatos em `backup/estudo02-20260916-inadmissiveis/` |
| 17 | passada de resume do reparo | OK — 20/09 15:59:14→17:33:11; os 12 saíram `exit=0` sem OOM; **51 das 72 recuperaram**, 21 repetiram a falha |
| 18 | admissibilidade de novo | OK — 20/09 17:34:12→17:38:02; **15 653 admissíveis, 25 inadmissíveis**, C6 fecha; candidatas à exclusão: 45, **todas por categoria declarada** |
| 19 | consolidação | OK — 20/09 19:26:26→19:26:45; `data/results/estudo02-20260916_consolidado/` com `per_task.csv` de **16 137 linhas** e 489 unidades pareadas |
| 20 | análise (plano §9) | **pendente** — os dois scripts não existem; nada se escreve sem decisão do Pedro |

### Fim da fase principal (20/09) e a passada de resume final

A corrida fechou em **20/09/2026 14:48:30**, com o `_04`, **4,04 dias depois do launch** de 16/09
13:52:42 — contra os ~4,1 dias que o plano §4.2 projetou para 12 containers. Os 12 saíram com
`exit=0` e **16 137 / 16 137 identidades COMPLETED**, zero `ERROR` residual. A soma das linhas dos
doze `summary.csv` dá exatamente **16 137**, e cada container fechou com `summary` e `performance`
do tamanho do seu lote (1 386 nos sete de 14 APKs, 1 287 nos cinco de 13).

**A passada de resume final não foi necessária, e é por construção.** Cada container teve
`RestartCount = 1`: ao esvaziar a fila da sua passada, saiu, o Docker o religou, e a passada
seguinte refez o punhado de `ERROR` que sobrava e exportou. Quando o container saiu pela última
vez, já não havia identidade a recuperar — conferido um a um contra o `batch_NN.txt`, pendentes 0
em todos os doze. Rodar o `up -d` agora só regeraria as tabelas que já estão escritas.

O **A6 da gh114 passou**: os seis arquivos saíram em uma passada em todos os doze, sem o laço de
exportação por OOM que obrigou a `estudo02` a regerar as tabelas offline. Na corrida inteira foram
**6 `oom-kill`, todos `CONSTRAINT_MEMCG` e todos no `_07`** (madrugada de 20/09), contra os 230 da
`estudo02`; nenhum do host.

Próximo passo: admissibilidade C1–C6 completa (com a campanha parada, sem `--skip-artifacts`),
depois reparo e consolidação.

### Pós-corrida (20/09)

Conduzido na ordem do procedimento, sem pular etapa: admissibilidade completa → reparo (dry-run
antes) → resume → admissibilidade de novo → consolidação. O veredito de cada passo, com as horas,
está em `docs/admissibilidade.md`; as saídas cruas em `docs/*.out` e os veredictos por identidade,
antes e depois do reparo, em `docs/admissibilidade_veredictos.zip`.

**Das 72 identidades devolvidas à fila, 51 se recuperaram e 21 repetiram a falha** — na `estudo02`
foram 36 de 57, e, por coincidência, as mesmas 21 a repetir. Nenhuma identidade nova ficou
inadmissível, então a passada de resume não introduziu defeito.

**O aumento de inadmissíveis sobre a `estudo02` (76 contra 58) tinha causa localizada:** 16 das 76
eram um APK só, a `de.markusfisch.android.binaryeye_174`, numa janela de 32 min do `_05` em 18/09,
com `adb: device offline` no traço do `ares` e o traço do `fastbot` cortado no meio de uma ação. As
13 reparadas dela recuperaram-se **todas**, o que confirmou o episódio transiente — e com isso a
campanha passou a ter **45 APKs candidatos à exclusão, os 45 apenas por categoria declarada e
nenhum por outro motivo**, o mesmo desfecho da `estudo02`.

**Decisão do Pedro em 20/09:** as 3 `ares@300 s` da `binaryeye` ficam como parada da ferramenta, sem
`--rerun`, embora o marcador delas venha depois de um `adb: device offline`. A regra escrita
prevalece; nenhum critério de admissibilidade foi alterado.

**As médias do consolidado incluem os zeros das categorias declaradas** — é o comportamento certo,
porque o artigo publicou esses mesmos zeros, mas quer dizer que elas não são "só admissíveis".
Quem citar um número dessas tabelas tem de dizer isso; as colunas `admissible`/`category` do
`per_task.csv` recortam a sensibilidade sem reconsolidar (`docs/admissibilidade.md`).

### Nota sobre o reboot de 19/09

O Pedro reiniciou a máquina no meio da campanha. **Não foi preciso religar nada à mão:** a política
`restart: on-failure:50` faz o Docker restaurar no boot do daemon os containers que estavam
rodando, e os 12 voltaram juntos às **19/09/2026 20:13:15**, com o resume de sempre — por exemplo,
o `_00` registrou `Resume: skipped 1127 already-completed tasks (259 remaining)`. Como o `up -d` da
retomada não chegou a ser necessário, o preflight de campanha foi rodado **depois**, com a corrida
já viva, e por isso reprova três portões que medem o host parado: containers desta campanha vivos,
irmãos do `ares` em `docker ps -a` (os efêmeros da corrida) e RAM disponível 87 g < 92 g (os
emuladores em regime). Os 21 portões substantivos — imagens, commit `fc51ab64` dentro da imagem,
as duas metades da gh114, `/dev/kvm`, `docker.sock`, corpus íntegro contra o `MANIFEST.sha256`,
sweep de tecelagem, veredito do smoke, composes, disco e pressão de I/O — passaram.

Estado às 20:20 de 19/09: **13 495 identidades COMPLETED de 16 137 (83,6 %)**, contra 13 480 lidas
nos `tasks.json` logo depois do boot; as `ERROR` caíram de 246 para 231, que é o resume refazendo-as.
O **vazamento de emuladores acabou com o reboot**: exatamente um `qemu-system-x86` por container,
nenhum `oom-kill` no dia, 36 g de RAM em uso e pressão de I/O em 2,5 %.

O único irmão órfão do pré-reboot, `ares_96b6b6c7` (criado 20:11, morto no shutdown), o Pedro
removeu à mão às 21:04. Os demais `ares_*`/`qtesting_*` que aparecerem em `docker ps -a` são
efêmeros da corrida viva e **não** se removem: o comando do procedimento que casa `^ares_` sem
olhar o estado mataria task em execução.

### Nota sobre a pasta do corpus (16/09)

A cópia dos APKs reinstrumentados foi feita à mão para
`RV_ANDROID_DATASET_FINAL/APKS_INSTRUMENTED_jca_android_dexlib2` — a **mesma** pasta que a
`estudo02` montou, e não a `..._094` que o plano previa. Os `.apk` da `estudo02` foram
sobrescritos; os `.apk.json`, não (são os mesmos bytes, a análise estática não foi refeita).

`campanha.env` passou a apontar para essa pasta, e os portões 3 e 4 da exportação deixaram de
comparar arquivos: comparam **manifestos**. O da instrumentação da `estudo02` está preservado no
git do `rvsec-dataset` em `ESTUDO02_MANIFEST_REV=cc6554baf7`. Com ele, os dois portões passam do
mesmo jeito — 163 `.apk` todos diferentes, 163 `.apk.json` todos iguais — e sem depender de
arquivo nenhum que já não exista.

Também foram removidos do host os 5 irmãos `ares_*`/`qtesting_*` da `estudo02` e o `rv-humanoid`
de 14/09, que o compose do smoke recria com o mesmo `container_name`.

## Propostas a confirmar pelo Pedro

Escolhidas na preparação, com base nos dados da `estudo02`. Nenhuma foi confirmada; os scripts já as
usam, mas cada uma se troca em `campanha.env`.

1. **12 containers × 10 g, `restart: on-failure:50`** (plano §4): ~4,1 dias de máquina contra ~4,95
   com 10, pelo mesmo método (a `estudo02` levou 5,87 dias do launch ao fim do reparo).
2. **Smoke com 12 containers e 12 APKs** escolhidos pelos consertos da gh114 (plano §7.4), no lugar
   dos 2 APKs em 2 containers da `estudo02`.
3. **Nome `estudo02-20260916`, com hífen**, e não `estudo02_...`.
4. **Corpus montado a partir de uma cópia**, e não do diretório do `rvsec-dataset`. A pasta é a
   `..._dexlib2` (decisão do Pedro em 16/09; o plano previa `..._dexlib2_094`).
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

Com o `DATASET` já povoado — o caso de 16/09, em que a cópia foi feita à mão — o `--apply` **não
copia**: confere cada arquivo que está lá contra os manifestos da fonte e regrava o
`MANIFEST.sha256`, que é o que o preflight verifica.

### 2. Sweep de tecelagem sobre o corpus inteiro

O script é da gh114 (`scripts/gh114_weave_sweep.py <apk_dir> <descriptor.json> <out.csv>`, tarefa 6.3
dela). Rodar sobre `$DATASET` com o descritor gerado pelas specs da gh114:

```bash
source experimento-estudo02-20260916/scripts/campanha.env
DESC="$DATASET_SRC/instrument_results/instrument_00/instrument_00/monitors/MultiSpec_1MonitorAspect.json"
uv run python scripts/gh114_weave_sweep.py "$DATASET" "$DESC" \
    experimento-estudo02-20260916/docs/tecelagem_sweep.csv \
    --sites experimento-estudo02-20260916/docs/tecelagem_sweep_sites.csv --jobs 6
```

O descritor é o que o gerador escreveu durante a reinstrumentação; os oito lotes escreveram o
mesmo arquivo, então qualquer `instrument_NN` serve. Levou ~4 min nos 163 APKs.

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

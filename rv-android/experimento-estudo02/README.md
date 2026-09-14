# `experimento-estudo02` — o Estudo 2 da tese, re-medido com o `jca_android`

**Ponto de entrada.** Plano: `docs/20260908_estudo02.md`. Compose: `docker/docker-compose.estudo02.yml`.
Filtros e corpus: `data/estudo02_filters/`. Resultados: `data/results/estudo02_NN/`.

## O que é

A repetição **local** do experimento do artigo (`ase-journal/`, Estudo 2 da tese — 11
configurações de ferramenta × 163 APKs × 3 repetições × 60/180/300 s = 16 137 runs), trocando
um único fator: o conjunto de specs `jca` (23 `.mop`, congelado) pelo `jca_android` (47 `.mop`,
gh100–gh111). Reusa os APKs instrumentados e a análise estática do corpus
`RV_ANDROID_DATASET_FINAL/APKS_INSTRUMENTED_jca_android_dexlib2`, produzidos pelo funil
`rvsec-dataset/jca_android` em 05/09 — nada é reinstrumentado.

## Decisões de 08/09

- **Corpus = 163**: os 164 do funil menos `com.google.android.stardroid_1678.apk` (derruba o
  emulador; evidência na gh104). O par `.apk`/`.apk.json` foi movido do diretório do dataset
  para `RV_ANDROID_DATASET_FINAL/excluidos/` em 08/09; o corte está registrado no funil
  (`rvsec-dataset/jca_android/FUNIL.md`, "Coverage-scope cut", `weaver_pkgfilter_zero`, o
  mesmo critério que o funil `jca` publicado já aplicava a este APK).
- **Nenhuma exclusão nova**: a análise de anomalias da gh104 (`docs/20260908_anomalias_gh104.md`)
  só reprova o `stardroid`. `org.fossify.messages_20` (sem árvore de UI para o APE) e
  `it.danieleverducci.nextcloudmaps_9` (muro de login) ficam, para o critério do artigo
  ("cobertura zero sob as 11 configurações") ser aplicado ao fim.
- **Três timeouts na mesma corrida** (`RV_TIMEOUTS=60,180,300`), não três passadas como no GCP:
  um só launch, um só resume, e o monitor conta contra `× 3`.
- **10 containers** (~6,2 dias); 8 dá 7,7 e 12 encosta na RAM. Trocar = `gen_compare.py --force`.
- **`RV_STRIP_BUILD_TYPE_SUFFIX` fora**: com os skips, a chave de escopo já vive no `.apk.json`.
- **Diagnósticos ligados** (`RV_LOGCAT_DIAGNOSTICS`): aditivo, não toca nas métricas.

## Diferenças em relação ao artigo (registro de 14/09)

O desenho é o do artigo — 11 configurações, 163 APKs, 3 repetições, 60/180/300 s, 16 137
identidades — mas a execução difere em pontos que quem for comparar os números precisa saber.
Nenhum deles altera o artigo: são propriedades desta campanha.

| | artigo (`ase-journal`) | `estudo02` |
|---|---|---|
| Specs | `jca`, 23 `.mop` | `jca_android`, 47 `.mop` — **o fator estudado** |
| Corpus | 163 apps | 163 apps, **162 em comum**: `info.dvkr.screenstream_44000` saiu (o instrumentador falhou no funil `jca_android`, `rvsec-dataset/jca_android/FUNIL.md`); `com.shatteredpixel.shatteredpixeldungeon_896` entrou (o único entrante do funil) |
| `monkey` | sem parâmetros; abortava no primeiro crash/ANR e fechou 1 961/1 962 | `@ignore_crashes=true,ignore_timeouts=true` (commit `f34cb120`): com 47 monitores o app fica mais lento e o ANR aparece sob a chuva de eventos; sem os flags, 201 de 330 identidades saíam `ERROR`. Os outros dez braços já seguem após crash. É o braço de **referência** do modelo binomial negativo, e a diferença de configuração tem de ser dita |
| Orçamentos | três passadas sequenciais, uma por orçamento (`RV_TIMEOUTS` único por passada) | os três orçamentos intercalados numa corrida só (`RV_TIMEOUTS=60,180,300`); cada orçamento continua sendo uma execução independente com emulador próprio |
| Imagem | `rvandroid:0.9.1` | `rvandroid:0.9.3` (código das changes gh100–gh113); `droidbot` pinado em `52aeea4`; `ares:latest` e `qtesting:latest` do host são de 13/08, posteriores às do GCP, e a igualdade de conteúdo não é verificável |
| Diagnósticos | desligados | `RV_LOGCAT_DIAGNOSTICS=true`: aditivo, não toca nas métricas; é o que permite crash/ANR por identidade |
| Infra | 16 containers em 4 VMs | 10 containers num host, 4 CPU / 10 GiB cada |

Duas consequências de medição que não são diferenças de desenho, mas mudam a leitura:

- **`mop_unique` não é o "unique misuse" do artigo.** O índice conta uma chave de sete partes
  (`class:::method:::spec:::error_type:::code:::event:::message`); o artigo conta
  `(apk, class, method, spec)`. Na campanha a razão entre as duas é 2,42. O consolidador escreve
  as duas (`mop_unique` e `mop_unique4`); só a segunda é comparável ao número publicado.
- **A covariável do modelo** (`log(sa_methods_reaches_mop)`) depende de quais APIs são
  monitoradas, e mudou com as specs. O consolidador a recomputa dos 163 `.apk.json` da
  campanha (`per_apk_static.csv`); o `dataset.csv` do artigo não serve aqui.

## Estado em 14/09

Campanha encerrada: 16 137/16 137 identidades `COMPLETED`, zero em erro. Validação executada em
`docs/20260914_validacao_execucao.md` (plano em `docs/20260912_validacao_anomalias.md`).
A exportação final de cada container morreu por falta de memória dentro do primeiro escritor
(`coverage.csv`). As tabelas foram regeradas offline por `scripts/regenerate_tables.py`, um
logcat por vez, sem religar container, com os escritores do próprio `result_processor` (mesmo
esquema de colunas): por container em `data/results/estudo02_regen/estudo02_NN/`
(`coverage`, `errors`, `app_events`, `summary`, `performance`, `results.json`) e concatenadas
para a campanha em `data/results/estudo02_consolidado/`. Depois do reparo (abaixo):
`summary.csv` 16 137 linhas, `errors.csv` 139 916, `app_events.csv` 2 996, `coverage.csv`
15 642 699. Conferido na primeira regeração: as identidades de `summary.csv` são as 16 137 do
índice; `mop_errors_unique` bate com o índice em 16 135 (as 2 restantes diferem em 1);
`cov_method` bate em 16 120, e nas 17 restantes o offline é maior por 0,01 a 0,4 ponto (o
logcat guardou linhas depois do instante em que a métrica ao vivo foi tirada). Contra o `coverage.csv` parcial da corrida ao vivo, o conjunto de
(tempo, assinatura) e os valores finais por identidade são idênticos; só a ordem das linhas
dentro do mesmo segundo muda, porque depende do hash seed (`PYTHONHASHSEED=0` fixa a do
regenerador). As tabelas ficam em `estudo02_regen/` porque os diretórios dos containers são de
`root` (criados pelo Docker); para movê-las para o lugar, `chown` primeiro e rode o script sem
`--out-dir`, que preserva o parcial como `coverage.csv.oom-partial`.
Admissibilidade: `scripts/admissibility.py` (C2 sobre o tempo da ferramenta; três categorias
declaradas que ficam na análise e não voltam à fila: **zero estrutural** do `qtesting`,
**parada da ferramenta** e **lançamento fora do app**). Veredictos em
`docs/20260914_admissibilidade.json`, que entram como colunas do `per_task.csv` via
`consolidate_compare.py --admissibility`.

**Reparo (14/09).** As 57 inadmissíveis fora de categoria declarada voltaram à fila
(`scripts/repair.py --apply`, artefatos preservados em `backup/estudo02-inadmissiveis/`), os
containers foram religados só para elas, com `restart=no`, e parados antes da exportação final.
36 se recuperaram e 21 repetiram a falha; duas delas tiveram uma terceira tentativa
(`repair.py --rerun`) e repetiram de novo. As tabelas foram regeradas e reconsolidadas depois
disso. Estado final: **15 650 admissíveis, 171 zeros estruturais, 249 paradas da ferramenta, 45
lançamentos fora do app, 22 inadmissíveis**, todas as 16 137 no modelo principal. Detalhe em
`docs/20260914_validacao_execucao.md` (Parte IV, item 6).

**Lançamento fora do app, uma diferença que o artigo também tem.** O build da
`org.wikipedia_50595` traz o `activity-alias` de lançamento do LeakCanary, e o androguard do
DroidBot o devolve como atividade principal: nas 45 identidades da família droidbot
(`bfs/dfs × greedy/naive` e `humanoid`) as ferramentas exploraram o LeakCanary, não a Wikipedia
(`cov_act = 0`). O `summary.csv` do artigo tem o mesmo zero nas mesmas 45. É zero da ferramenta,
determinístico, e fica na análise como categoria declarada.

**Leitura.** Tabelas por ferramenta ao lado do artigo: `docs/20260914_tabelas_por_ferramenta.md`.
Modelo binomial negativo do artigo com as sensibilidades: `docs/20260914_modelo_rq1.txt`.
Maus usos por spec, `jca` × `jca_android`: `docs/20260914_specs_jca_vs_android.md`. O que muda
nas conclusões: `docs/20260914_veredito.md`.

## Como rodar

```bash
bash experimento-estudo02/scripts/preflight.sh                      # tudo OK antes de qualquer up
docker compose -f docker/docker-compose.estudo02smoke.yml up -d     # smoke: 22 tasks, ~40 min
.claude/skills/rv-experiment-compare/scripts/monitor_compare.sh estudo02smoke --no-resume
uv run python experimento-estudo02/scripts/smoke_gates.py    # os 6 portões do plano §7
#   → só com SMOKE APROVADO, e depois de dar `down` no compose do smoke:
docker compose -f docker/docker-compose.estudo02.yml up -d
.claude/skills/rv-experiment-compare/scripts/monitor_compare.sh estudo02
docker compose -f docker/docker-compose.estudo02.yml up -d          # passada de resume final
#   → com a campanha fechada e nenhum container de pé:
for n in 00 01 02 03 04 05 06 07 08 09; do                          # tabelas por container
  PYTHONHASHSEED=0 uv run python experimento-estudo02/scripts/regenerate_tables.py \
      data/results/estudo02_$n/estudo02_$n --out-dir data/results/estudo02_regen/estudo02_$n &
done; wait
uv run python experimento-estudo02/scripts/admissibility.py --json experimento-estudo02/docs/20260914_admissibilidade.json
uv run python .claude/skills/rv-experiment-compare/scripts/consolidate_compare.py estudo02 \
    --admissibility experimento-estudo02/docs/20260914_admissibilidade.json
```

O smoke e a campanha usam nomes distintos (`estudo02smoke_*` / `estudo02_*`), mas o sidecar
`rv-humanoid` é um só: dar `down` no compose do smoke antes do `up` da campanha.

## Conteúdo

```
experimento-estudo02/
├── README.md
├── docs/20260908_anomalias_gh104.md      # por que só o stardroid sai
├── anomalias_gh104/                      # CSVs por APK e por identidade + sumário
├── docs/20260908_smoke.md                # veredito do smoke (escrito depois de rodá-lo)
├── docs/20260912_validacao_anomalias.md  # catálogo de anomalias de 2025 e os detectores
├── docs/20260914_validacao_execucao.md   # os detectores executados e as correções ao handoff
├── docs/20260914_admissibilidade.json    # veredictos C1–C6 por identidade
├── docs/20260914_tabelas_por_ferramenta.md  # as tabelas do artigo recomputadas, lado a lado
├── docs/20260914_modelo_rq1.txt          # modelo NB do artigo, sensibilidades, contrastes do ape
├── docs/20260914_contrastes_ferramentas.md  # os 55 pares de ferramentas, artigo × campanha, Holm
├── docs/20260914_specs_jca_vs_android.md # maus usos por spec, artigo × campanha
├── docs/20260914_veredito.md             # o que muda nas conclusões entre jca e jca_android
└── scripts/
    ├── admissibility.py                  # C1–C6 por identidade; nunca exclui APK
    ├── repair.py                         # devolve à fila o que a admissibilidade reprovou (--rerun: decisão humana)
    ├── regenerate_tables.py              # coverage/errors/app_events/summary por container, offline
    ├── tabelas_artigo.py                 # as quatro tabelas por ferramenta do artigo
    ├── rq1_estudo02.py                   # o modelo RQ1 do artigo sobre a campanha
    ├── contrastes_ferramentas.py         # os 55 contrastes entre ferramentas, nas duas campanhas
    ├── specs_jca_vs_android.py           # errors.csv do artigo × da campanha, por spec
    ├── validacao/                        # detectores da validação de 14/09 (README próprio)
    ├── anomalias_gh104.py                # a análise da gh104 (ainda aponta para gh104_*)
    ├── preflight.sh
    └── smoke_gates.py                    # os 6 portões do smoke, bloqueantes
```

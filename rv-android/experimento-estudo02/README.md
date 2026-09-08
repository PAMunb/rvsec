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
  para `RV_ANDROID_DATASET_FINAL/excluidos/` em 08/09; o corte ainda não está no `rvsec-dataset`.
- **Nenhuma exclusão nova**: a análise de anomalias da gh104 (`docs/20260908_anomalias_gh104.md`)
  só reprova o `stardroid`. `org.fossify.messages_20` (sem árvore de UI para o APE) e
  `it.danieleverducci.nextcloudmaps_9` (muro de login) ficam, para o critério do artigo
  ("cobertura zero sob as 11 configurações") ser aplicado ao fim.
- **Três timeouts na mesma corrida** (`RV_TIMEOUTS=60,180,300`), não três passadas como no GCP:
  um só launch, um só resume, e o monitor conta contra `× 3`.
- **10 containers** (~6,2 dias); 8 dá 7,7 e 12 encosta na RAM. Trocar = `gen_compare.py --force`.
- **`RV_STRIP_BUILD_TYPE_SUFFIX` fora**: com os skips, a chave de escopo já vive no `.apk.json`.
- **Diagnósticos ligados** (`RV_LOGCAT_DIAGNOSTICS`): aditivo, não toca nas métricas.

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
uv run python .claude/skills/rv-experiment-compare/scripts/consolidate_compare.py estudo02
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
└── scripts/
    ├── anomalias_gh104.py                # a análise (reaplicar ao estudo02 ao fim)
    ├── preflight.sh
    └── smoke_gates.py                    # os 6 portões do smoke, bloqueantes
```

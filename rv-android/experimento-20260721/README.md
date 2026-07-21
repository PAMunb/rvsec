# Experimento 2026-07-21 — `cmp_llm_20260721` (base × v2, APE corrigido, img 0.9.3)

Re-execução da campanha `cmpm` (docs `20260718_cmpmodels.md`) para **decidir qual modelo LLM
de visão** entra no experimento final: **base** (`Qwen/Qwen3-VL-4B-Instruct`, stock) × **v2**
(`phtcosta/aperv-qwen3vl-4b-v2-merged`, tunado), no braço LLM do APE-RV. Mesmo desenho do
cmpm; muda **apenas a imagem** (0.9.2 → **0.9.3**, com o APE corrigido) — o cmpm ficou
**confundido** porque o `MODEL_LLM_TAP` nunca injetava tap (dois bugs geométricos, agora
corrigidos). Ver o **doc mestre** `docs/20260721_cmp_llm_20260721.md` para o porquê completo,
hipóteses, ameaças e o veredito de verificação pré-lançamento (§9).

> **Execução LOCAL** — 1 GPU de 16 GB. Os dois modelos 4B **não coexistem** (~13 GB cada),
> então as runs são **estritamente sequenciais**: base inteira → troca de modelo → v2 inteira.
> **Não** roda na nuvem (diferente dos `experimento-2026xxxx` anteriores).

## O que muda vs cmpm

| | cmpm | **cmp_llm_20260721** |
|---|---|---|
| Imagem | `phtcosta/rvandroid:0.9.2` | **`phtcosta/rvandroid:0.9.3`** (jar APE `d90c1f4` = tap-fix `4ee12ba`/`8ab8355` + logging `llm-experiment-logging`) |
| MODEL_LLM_TAP | no-op (100 % dropado) | **injeta de fato** (validade = display físico) |
| Diagnósticos logcat | OFF | **ON** (`RV_LOGCAT_DIAGNOSTICS=true`) — crashes/VerifyError/ANR → `app_events.csv` |
| Telemetria LLM | básica | **enriquecida** — `[APE-LLM-CONFIG]`, `[APE-OUTCOME]`, `[APE-LLM-CONFIG-ACK] server_model`, `[APE-LLM-ERROR] cause=` |
| Estrutura | avulsa (`docker/`, `data/`) | **pasta autocontida** `experimento-20260721/` |

## Configuração

| Item | Valor |
|---|---|
| Braço (idêntico nas 2 runs) | `aperv:sata_mop_llm_v13@llm_temperature=0` |
| Modelos (sequenciais) | base = `Qwen/Qwen3-VL-4B-Instruct` · v2 = `phtcosta/aperv-qwen3vl-4b-v2-merged` |
| APKs × reps × timeout | 181 × 3 × 300 s |
| Containers | 8 → **543 tasks por run** |
| Spec-set / variante | jca / dexlib2 (dataset já instrumentado; skips monitors+instrument+static) |
| Dataset | `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706_selected181` (absoluto) |
| SGLang | `lmsysorg/sglang:v0.5.6.post2`, 1 GPU, porta 30000 (não publicada no host) |

## Pré-processing (imagem)

A imagem `phtcosta/rvandroid:0.9.3` **já foi buildada e verificada por bytecode** (jar embute
tap-fix + logging; ver `docs/20260721_cmp_llm_20260721.md` §9). Para rebuild: `docker/build_all.sh`
na raiz do rv-android (clona+`mvn package` o `ape` da default branch, sem SHA pin).

## Execução (LOCAL, sequencial, 1 GPU)

Rodar **a partir desta pasta** (`experimento-20260721/`); os composes usam paths relativos
(`./filters`, `./results`).

```bash
cd experimento-20260721

# 1. SMOKE GATE (modelo base, 4 APKs, 90 s) — obrigatório antes das runs
docker compose -f docker-compose.smoke.yml up -d
scripts/monitor.sh cmp_llm_20260721_smoke        # aguardar 4/4 COMPLETED
#   validar os gates fix-specific do §4 do plano (tap injeta / muda estado / server_model)
docker compose -f docker-compose.smoke.yml down   # só após extrair traces

# 2. RUN base (543 tasks)
docker compose -f docker-compose.base.yml up -d
scripts/monitor.sh cmp_llm_20260721_base          # loop até 543/543; resume = re-rodar up -d
#   NÃO dar down antes de preservar traces (efêmeros no device, por task no bind mount)
docker compose -f docker-compose.base.yml down

# 3. TROCA DE MODELO → RUN v2 (543 tasks) — o v2 compose já aponta o outro --model-path
docker compose -f docker-compose.v2.yml up -d
scripts/monitor.sh cmp_llm_20260721_v2            # loop até 543/543
docker compose -f docker-compose.v2.yml down
```

`monitor.sh <name>` conta identidades distintas `(apk,tool,variant,rep,timeout)` e faz
auto-resume de container não-running/travado. `--no-resume` só reporta.

## Monitoramento

- Progresso/saúde: `scripts/monitor.sh cmp_llm_20260721_{base,v2}`.
- SGLang (porta não publicada → não usar curl no host): `docker logs sglang-server` (procurar
  `served_model_name`, `Decode batch`).
- Truncamento/saúde por identidade: `python3 scripts/cmpm_truncation.py cmp_llm_20260721_base --expected 543`.

## Consolidação + análise (offline)

CSVs a partir dos **logcats** (fonte da verdade; CSV por-container zera cobertura em resume — gh58):

```bash
python3 scripts/consolidate_compare.py cmp_llm_20260721_base   # → results/cmp_llm_20260721_base_consolidado/
python3 scripts/consolidate_compare.py cmp_llm_20260721_v2
#   (wilcoxon.csv vazio = esperado, 1 braço; per_apk_paired.csv/per_task.csv saem antes do IndexError cosmético)

python3 scripts/cmpm_paired_stats.py       # Wilcoxon pareado base↔v2 (cov_mop primário + rank-biserial)
python3 scripts/cmpm_stratify.py <run>     # estratificação FLAG_SECURE
python3 scripts/cmpm_position.py           # posicionamento vs widget@300 (cmpft5) / widget@600 (cmpv2w)
python3 scripts/analyze_cmpv2_llm.py --selftest && python3 scripts/analyze_cmpv2_llm.py cmp_llm_20260721_base  # telemetria
```

Os scripts leem os resultados **desta pasta** (`results/`) e as metas de `configs/`; baselines
externos (cmpft5/cmpv2w/cmpma) são lidos do `data/results` principal do rv-android.

## Estrutura

```
experimento-20260721/
├── README.md                         # este runbook
├── docker-compose.smoke.yml          # gate (base, 4 APKs, 90 s, 1 rep)
├── docker-compose.base.yml           # run base  (181×3×300 s, 8 containers → 543)
├── docker-compose.v2.yml             # run v2    (idem, --model-path v2-merged)
├── configs/                          # *_compare_meta.json (registro declarativo, filters_dir aponta p/ ./filters)
├── filters/{base,v2,smoke}/          # batches (base/v2: 8×; smoke: 4×1 APK)
├── scripts/                          # monitor.sh + consolidate/análise (adaptados p/ ./results + ./configs)
├── docs/20260721_cmp_llm_20260721.md # doc mestre (desenho, hipóteses, ameaças, §9 verificação)
└── results/                          # criado em runtime (cmp_llm_20260721_{base,v2,smoke}_00..NN + _consolidado)
```

## Notas / gotchas

- **1 GPU → sequencial obrigatório.** `up -d` pode estourar timeout de shell enquanto o SGLang
  carrega o modelo (containers em `Created`); re-rodar o **mesmo** `up -d` sobe instantâneo.
- **Não dar `down`** antes de preservar os traces (efêmeros no device; ficam por task no bind mount `results/`).
- **Consolidar de logcats**, nunca do CSV por-container (gh58 zera cobertura em resume). Dedup por
  identidade, nunca por task_id (resume infla `tasks.json`).
- **Modelo servido**: confirmar no trace via `[APE-LLM-CONFIG-ACK] server_model=…` (prova base vs v2)
  e no `docker logs sglang-server`.
- Datas em logs de container são UTC−3; host é UTC.

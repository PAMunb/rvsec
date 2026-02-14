# RVAgent Calibration and Validation Framework v2

**Data**: 2026-02-07
**Status**: Fase A concluida, paralelismo implementado. Proximo: Fase B (baseline).
**Objetivo**: Criar framework sistematico e automatizado de validacao e calibracao para o RVAgent, visando atingir metricas de cobertura superiores ao APE e FastBot, com dataset expandido (105 APKs)
**Paralelismo**: 6 emuladores simultaneos
**Orcamento de tempo**: ~12.5 dias (wall-clock)

## Proximo Passo: Fase B - Baseline com 105 APKs

**Fase 0 CONCLUIDA** em 2026-02-07 (3.3h de processamento)
**Fase A CONCLUIDA** em 2026-02-08 (1.0h instrumentacao + 0.8h analise estatica = 1.8h total, 6 workers)
**Dataset selecionado**: 75 calibration / 30 holdout (105 APKs)

### Resultado do Filtro

| Etapa | Quantidade | Descricao |
|-------|-----------|-----------|
| Input | 188 APKs | `exp01_jca=True` no CSV |
| Apos filtro .methods | 165 APKs | 23 excluidos por .methods header-only (43 bytes) |
| Apos filtro SA | 105 APKs | GESDA + GATOR + REACH OK (64.8% pass rate) |
| Apos Fase A | **105 APKs** | -1 dex2jar fail, -1 REACH timeout na re-execucao |
| Falhas (Fase 0) | 58 APKs | REACH: 52 falhas (43 timeout), GATOR: 10 falhas |
| Falhas (Fase A) | 2 APKs | `com.danielme.muspyforandroid_3` (dex2jar), `org.dystopia.email_118` (REACH) |

**Arquivos gerados**:
- `out/static_analysis_filter/passed_apks.txt` — 105 APKs validos
- `out/static_analysis_filter/filter_results.csv` — Detalhes por APK
- `out/static_analysis_filter/summary.txt` — Resumo do filtro

### Estatisticas do Dataset (105 APKs)

**Distribuicao por tamanho** (metodos monitoraveis):
| Bucket | Range | Total | Cal | Holdout |
|--------|-------|-------|-----|---------|
| tiny | 0-50 | 15 | 11 (14.7%) | 4 (13.3%) |
| small | 50-200 | 34 | 23 (30.7%) | 11 (36.7%) |
| medium | 200-500 | 36 | 26 (34.7%) | 10 (33.3%) |
| large | 500-1500 | 19 | 14 (18.7%) | 5 (16.7%) |
| xlarge | 1500+ | 1 | 1 (1.3%) | 0 (0.0%) |

**Distribuicao por categoria** (top 10):
| Categoria | Total | Cal | Holdout |
|-----------|-------|-----|---------|
| Multimedia | 17 | 13 | 4 |
| Internet | 15 | 11 | 4 |
| System | 12 | 9 | 3 |
| Security | 10 | 7 | 3 |
| Games | 8 | 6 | 2 |
| Development | 8 | 5 | 3 |
| Navigation | 7 | 5 | 2 |
| Science & Education | 5 | 3 | 2 |
| Outras (9 categorias) | 23 | 16 | 7 |

**Methods**: min=11, Q1=82, median=220, Q3=488, max=2417, mean=321
**Crashes**: min=4, median=40, max=261
**Package mismatches**: 9/105 (tratado pelo PackageDetector)
**Strata unicos** (category|size): 42

---

## Motivacao: Por que Expandir o Dataset

A validacao anterior (20260202) usou apenas 15 APKs — um dataset pequeno demais para conclusoes robustas:
- **15 APKs**: Alta variancia, poucos graus de liberdade para testes estatisticos
- **50-100 APKs**: Poder estatistico adequado para Wilcoxon signed-rank (p < 0.05)
- **Fonte**: 188 APKs do experimento `exp01_jca`, ja catalogados e com .methods
- **Filtro**: Apenas APKs que suportam analise estatica completa (GESDA + GATOR + REACH)

---

## Dataset (105 APKs - 75 calibration / 30 holdout)

**Total**: 105 APKs (de 165 processados, 64.8% pass rate)
**Split**: 75 calibration + 30 holdout (seed 42, estratificado por category + size_bucket)

### Criterios de Validacao

- Arquivo `.gesda` presente e nao-vazio (GESDA executou com sucesso)
- Arquivo `.wtg` presente e nao-vazio (GATOR executou com sucesso)
- Arquivo `.reach` presente e nao-vazio (REACH executou com sucesso)
- Arquivo `.methods` com mais de 43 bytes (nao e apenas header)

### Selecao e Divisao do Dataset

**Script**: `scripts/select_dataset.py`

O script faz a selecao e split usando:
1. Lista de APKs validos (`passed_apks.txt` do filtro)
2. Metadados do `apks_complete.csv` (categorias, methods, crashes, packages)
3. **Split estratificado** por `primary_category` + `size_bucket` (methods count)

**Size buckets** (por numero de metodos monitoraveis):
| Bucket | Methods range |
|--------|---------------|
| tiny | 0-50 |
| small | 50-200 |
| medium | 200-500 |
| large | 500-1500 |
| xlarge | 1500+ |

**Metadados disponiveis do CSV** (para analise e diversidade):
| Coluna | Descricao | Uso |
|--------|-----------|-----|
| `categories` | Categoria F-Droid (17 unicas) | Estratificacao |
| `methods` | Metodos monitoraveis | Estratificacao (size bucket) |
| `crashes` | Crashes em execucoes anteriores | Analise de estabilidade |
| `manifest_package` / `detected_package` | Package mismatch | Ja tratado pelo PackageDetector |

**Comando usado para gerar o split**:
```bash
python scripts/select_dataset.py \
    --passed-apks ./out/static_analysis_filter/passed_apks.txt \
    --csv /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/apks/apks_complete.csv \
    --cal-size 75 \
    --output-dir ./out/dataset_selection \
    --seed 42
```

**Output gerado** (em `out/dataset_selection/`):
- `calibration_set_v2.txt` — 75 APKs para calibracao (Fases C e D)
- `holdout_set_v2.txt` — 30 APKs para validacao final (Fase E)
- `all_valid_apks.txt` — 105 APKs (para Fase B baseline)
- `dataset_split.csv` — CSV combinado com metadados e set assignment
- `calibration_set_v2.csv` / `holdout_set_v2.csv` — CSVs detalhados por set

### Decisao de Split: 75 cal / 30 holdout

**Razao**: Maximizar trials de calibracao (opcao "ambiciosa" com 80 macro + 100 micro trials) mantendo holdout >20 APKs (minimo para Wilcoxon signed-rank com p < 0.05). Com 6 emuladores em paralelo, cabe em ~12.5 dias.

---

## Visao Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│ FASE 0: SELECAO DE DATASET - ✅ CONCLUIDA                      │
│                                                                 │
│  188 APKs → 165 (filtro .methods) → 107 validados (64.8%)      │
│  Split: 75 calibration + 30 holdout (seed 42, estratificado)   │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ FASE A: PRE-PROCESSAMENTO - ✅ CONCLUIDA           1.8h (6 wkrs) │
│                                                                 │
│  105 APKs instrumentados (107-2: dex2jar fail + REACH timeout)  │
│  .gesda, .wtg, .reach gerados para 105 APKs                    │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ FASE B: BASELINE - EM EXECUCAO                 ~18h (6 emu)    │
│                                                                 │
│  APE, FastBot, RVAgent × 105 APKs × 3 reps = 945 tasks         │
│  6 emuladores em paralelo                                      │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ FASE C: CALIBRACAO MACRO - PENDENTE          ~122h/5.1d (6 emu)│
│                                                                 │
│  80 trials × 75 cal APKs, pure_algorithm, 8 params             │
│  Optuna TPESampler, 6 trials em paralelo (n_jobs=6)            │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ FASE D: CALIBRACAO MICRO - PENDENTE          ~160h/6.7d (6 emu)│
│                                                                 │
│  100 trials × 75 cal APKs, multimode, 17 params                │
│  Optuna TPESampler, 6 trials em paralelo (n_jobs=6)            │
│  Requer: SGLang server (Qwen3-VL-4B)                           │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ FASE E: VALIDACAO FINAL - PENDENTE             ~6h (6 emu)     │
│                                                                 │
│  3 tools × 30 holdout × 3 reps = 270 tasks                    │
│  6 emuladores em paralelo                                      │
└─────────────────────────────────────────────────────────────────┘

Total estimado: ~299h (~12.5 dias wall-clock com 6 emuladores)
```

## Estrategia de Paralelismo (6 Emuladores)

**Recursos**: 128GB RAM, 64 CPUs — suporta 6 emuladores (~3GB cada = ~18GB)

**AVD base**: "RVSec" (instancias adicionais via `--read-only` ou AVDs clonados)

### Como funciona o paralelismo em cada fase

| Fase | Tipo de paralelismo | Implementacao |
|------|---------------------|---------------|
| **B** (Baseline) | Tasks independentes divididas entre emuladores | Cada emulador recebe subset de APKs/tools |
| **C** (Macro) | N trials em paralelo | Optuna `n_jobs=6`, cada worker usa 1 emulador |
| **D** (Micro) | N trials em paralelo | Optuna `n_jobs=6`, SGLang compartilhado |
| **E** (Validacao) | Tasks independentes divididas entre emuladores | Cada emulador recebe subset de APKs/tools |

### Requisitos de implementacao — ✅ CONCLUIDOS

Implementacao detalhada em `docs/20260207_refactoring_parallel.md`.

1. ✅ **Criar 5 AVDs adicionais** (ou usar `emulator -read-only` com portas distintas)
2. ✅ **CalibrationRunner**: Aceita `device_port` por worker, `EmulatorPool` thread-safe
3. ✅ **Optuna**: `study.optimize(objective, n_trials=N, n_jobs=6)` com EmulatorPool
4. ✅ **Baseline/Validacao**: `scripts/parallel_run.py` divide APKs entre N instancias
5. **SGLang** (Fase D): Servidor unico, ~4.2 requests concorrentes (Qwen3-VL-4B aguenta)

**Flags adicionadas ao rv-experiment**:
- `--skip-execution`: Roda apenas pre-processamento (monitores + instrumentacao + static analysis)
- `--device-port N`: Porta do emulador para execucao paralela (default: 5554)
- `--apks-filter FILE`: Filtra APKs por lista em arquivo texto (um por linha)
- `--name NAME`: Nome do experimento (controla nome do results_dir)

---

## Melhorias nos Parsers de Analise Estatica (2026-02-07)

Commit `bf4d18b5` introduziu duas melhorias que beneficiam a qualidade dos dados de analise estatica:

1. **`PackageDetector` + `App.code_package`**: Detecta o package real do codigo (via analise de componentes) ao inves de usar apenas o package do manifest. Resolve mismatches em apps com build variants ou game engines. Os parsers de analise estatica (`gator_parser`, `gesda_parser`, `reach_parser`) agora usam `code_package` para filtragem de classes.

2. **`SignatureNormalizer`**: Normaliza notacao de inner classes (`OuterClass.InnerClass` → `OuterClass$InnerClass`) nos tres parsers. Melhora o matching entre assinaturas de metodos da analise estatica e do runtime.

**Impacto no plano**: Estas melhorias melhoram a qualidade dos dados de WTG, GESDA e REACH durante as fases B-E. O filtro de APKs (Fase 0) nao e afetado, pois executa as ferramentas como subprocessos, nao os parsers Python.

---

## Regras de Implementacao

### Principios Gerais
1. **Simplicidade**: Codigo simples e direto, sem complexidades desnecessarias. Seguir boas praticas de engenharia de software (KISS, DRY, SOLID onde aplicavel). Preferir solucoes simples — tres linhas similares sao melhores que uma abstracao prematura.
2. **Sem over-engineering**: Nao adicionar features, configurabilidade ou abstraçoes alem do necessario. Nao projetar para requisitos hipoteticos futuros.

### Evolucao do Codigo
3. **Implementacao completa**: Todas as alteracoes devem ser totalmente implementadas, nao parciais.
4. **Sem codigo legado**: Nao usar adapters, shims, wrappers de compatibilidade ou re-exports para manter codigo antigo funcionando. Codigo legado deve ser removido ou sobrescrito, nunca encapsulado.
5. **Backup antes de substituir**: Mover arquivos antigos para `backup/` antes de substituir.
6. **Atualizar todas as referencias**: Todos os imports e referencias devem apontar para as novas implementacoes.

### Comentarios e Nomenclatura
7. **Estado atual apenas**: Comentarios devem refletir o estado atual do codigo. Nao mencionar migracao, fases anteriores, "o que era antes", "legacy", "o que foi feito", etc.
8. **Sem linguagem promocional**: Nao usar termos de vies como "moderno", "sofisticado", "elegante", "avançado", "inteligente", "robusto" em comentarios, docstrings ou nomes de variaveis/classes.
9. **Publico-alvo**: Desenvolvedores e pesquisadores. Linguagem tecnica e objetiva.

## Metricas a Otimizar

1. **Method Coverage** (primaria) - % de metodos do app executados
2. **MOP Errors Detected** (critica) - quanto mais melhor, indica caminhos de codigo com operacoes monitoradas alcancados
3. **UI Coverage** (secundaria) - % de elementos UI interagidos (via UI tracker)
4. **cov_rv_method** - Cobertura de metodos RV (metodos que alcancam operacoes monitoradas)

---

## Fases do Framework

### Fase 0: Selecao de Dataset (✅ CONCLUIDA)

**Status**: Concluida em 2026-02-07 (3.3h de processamento, 5 workers, timeout 600s/tool)

**Pipeline de filtragem**:
```
188 APKs (exp01_jca=True)
  → 165 APKs (excluidos 23 com .methods header-only)
  → 105 APKs validados (excluidos 58 com falha em GESDA/GATOR/REACH)
```

**Motivos de falha** (58 APKs):
- REACH timeout (600s): 43 APKs — APK muito grande/complexo
- REACH output vazio: 9 APKs — REACH nao conseguiu analisar
- GATOR timeout: 5 APKs — APK com muitas activities
- GATOR output vazio: 3 APKs — GATOR nao conseguiu analisar
- GESDA: 0 falhas (100% success rate)
- Nota: Alguns APKs falharam em mais de uma ferramenta

**Entregaveis**:
- `out/static_analysis_filter/passed_apks.txt` (105 APKs)
- `out/dataset_selection/calibration_set_v2.txt` (75 APKs)
- `out/dataset_selection/holdout_set_v2.txt` (30 APKs)
- `out/dataset_selection/dataset_split.csv` (metadados completos)

### Fase A: Pre-processamento / Instrumentacao (✅ CONCLUIDA)

**Status**: Concluida em 2026-02-08 (1.0h instrumentacao + 0.8h analise estatica = 1.8h total, 6 workers)

**Objetivo**: Instrumentar os 105 APKs validados com monitores JCA

**Dependencia**: Resultado da Fase 0

**Script**: `scripts/validation/fase_a_preprocess.py` — preprocessamento paralelo com 3 fases macro (monitores → instrumentacao → analise estatica). Detalhes em `docs/20260207_refactoring_parallel.md` Parte 9.

```bash
# IMPORTANTE: Definir RVSEC_HOME (necessario para monitores e analise estatica)
export RVSEC_HOME="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec"

# Preprocessamento paralelo: monitores + instrumentacao + analise estatica
# 6 workers para instrumentacao e analise estatica
python scripts/validation/fase_a_preprocess.py \
  --apks-dir /home/pedro/desenvolvimento/RV_ANDROID/NOVO/APKS \
  --apks-filter ./out/static_analysis_filter/passed_apks.txt \
  --specification-set jca \
  --output-dir ./results/preprocessing_v2 \
  --max-workers 6

# Copiar APKs instrumentados para diretorio de calibracao
cp -r ./results/preprocessing_v2/instrumented_apks/* \
  modules/rv-agent-validation/data/calibration_dataset_v2/
```

**Tempo real (6 workers)**: 1.8h total (vs ~14h sequencial)
- Fase 1 (monitores): ~77s (sequencial)
- Fase 2 (instrumentacao): ~55 min (6 workers, 105/107 OK)
- Fase 3 (analise estatica): ~48 min (6 workers, 105/106 OK)

**Falhas (2 APKs removidos do dataset)**:
- `com.danielme.muspyforandroid_3` — dex2jar failure silenciosa (detectada via verificacao pos-instrumentacao)
- `org.dystopia.email_118` — REACH timeout na re-execucao da analise estatica

**Resultados**: `results/preprocessing_v2/`
- `instrumented_apks/` — 105 APKs instrumentados
- `static_analysis/` — .gesda, .wtg, .reach para 105 APKs
- `instrumented_apks_list.txt` — Lista dos APKs instrumentados

**Entregaveis**:
- `data/calibration_dataset_v2/` — 105 APKs instrumentados + SA flat (420 arquivos)
- `data/calibration_set_v2.txt` — Lista de 75 APKs para calibracao
- `data/holdout_set_v2.txt` — Lista de 30 APKs para validacao final
- `data/all_valid_apks.txt` — Lista de 105 APKs (todos)
- `data/dataset_split.csv` — Metadados + set assignment

**Estrutura do dataset** (flat — exigido pelo StaticAnalysisComponent):
```
data/calibration_dataset_v2/
├── byrne.utilities.hashpass_2.apk         ← APK instrumentado
├── byrne.utilities.hashpass_2.apk.gesda   ← GESDA (GUI elements)
├── byrne.utilities.hashpass_2.apk.wtg     ← GATOR (Window Transition Graph)
├── byrne.utilities.hashpass_2.apk.reach   ← REACH (reachability)
├── ...                                     ← 105 APKs × 4 arquivos = 420 arquivos
```

**Convencao de nomes**: O `StaticAnalysisComponent` usa `task.config.apk_name` (que inclui `.apk`) para construir o nome dos arquivos SA. Portanto, os arquivos devem ser nomeados como `{nome}.apk.{ext}` (e.g., `byrne.utilities.hashpass_2.apk.gesda`). O script `filter_apks_static_analysis.py` gera os arquivos SEM a extensao `.apk` — ao copiar para o dataset, renomear de `{nome}.{ext}` para `{nome}.apk.{ext}`.

**Nota**: Subdiretórios não são suportados — todos os arquivos devem estar no mesmo diretório (flat). O arquivo `.methods` não é mais utilizado — o REACH fornece a estrutura de classes/métodos para o cálculo de cobertura.

### Fase B: Comparacao Baseline (EM EXECUCAO)

**Objetivo**: Estabelecer baseline de performance das 3 ferramentas no novo dataset

**Dependencia**: Fase A concluida

**Repeticoes**: 3 reps para validade estatistica (Wilcoxon signed-rank test, comparacoes pareadas)

```bash
export RVSEC_HOME="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec"

# Baseline: 3 tools × 105 APKs × 3 reps = 945 tasks
# 3 reps para significancia estatistica (Wilcoxon signed-rank, p < 0.05)
# 6 emuladores distribuem tasks em paralelo via parallel_run.py
uv run python scripts/parallel_run.py \
  --tools ape,fastbot,rvagent:pure_algorithm \
  --apks-dir modules/rv-agent-validation/data/calibration_dataset_v2 \
  --n-emulators 6 \
  --timeout 300 \
  --repetitions 3 \
  --output-base ./results/baseline_v2 \
  --skip-preprocessing \
  2>&1 | tee ./results/baseline_v2/baseline_v2.log
```

**Estimativa de tempo (6 emuladores)**:
- 3 tools × 105 APKs × 3 reps = 945 tasks
- ceil(945/6) = 158 batches × 7 min = ~18.4 horas

**Entregaveis**:
- `results/baseline_v2/summary.csv`
- `BASELINE_MAX_ERRORS` — calculado para normalizacao adaptativa

### Fase C: Calibracao Macro (PENDENTE)

**Objetivo**: Otimizar 8 parametros de alto impacto usando Optuna (modo `pure_algorithm`)

**Dependencia**: Fase B concluida (necessita BASELINE_MAX_ERRORS)

**Parametros**: 8 macro params (scorer weights + exploration)

```bash
# 80 trials × 75 cal APKs, 6 emuladores em paralelo
# Optuna TPESampler com n_jobs=6
uv run python -m rv_agent_validation calibrate \
  --apks-dir $CALIBRATION_DATASET \
  --apks-filter calibration_set_v2.txt \
  --phase macro \
  --n-trials 80 \
  --n-jobs 6 \
  --timeout 300 \
  --seed 42 \
  --output ./results/calibration_macro_v2
```

**Estimativa de tempo (6 emuladores)**:
- Cada trial: 75 APKs × 7 min = 8.75h
- 80 trials / 6 emuladores = ceil(80/6) = 14 rodadas
- 14 × 8.75h = **~122h (~5.1 dias)**

### Fase D: Calibracao Micro (PENDENTE)

**Objetivo**: Ajuste fino de 17 parametros (16 numericos + 1 categorico) em modo `multimode`

**Dependencia**: Fase C concluida (fixa macro params otimizados)

**Modo**: `multimode` (hibrido LLM + algoritmo) — necessario para exercitar parametros LLM

**Requer**: SGLang server (Qwen3-VL-4B-Instruct) rodando em 192.168.0.36:30000

```bash
# 100 trials × 75 cal APKs, multimode, 6 emuladores em paralelo
# Requer: SGLang server (6 emuladores geram ~4.2 requests LLM concorrentes)
uv run python -m rv_agent_validation calibrate \
  --apks-dir "$CALIBRATION_DATASET" \
  --apks-filter calibration_set_v2.txt \
  --phase micro \
  --n-trials 100 \
  --n-jobs 6 \
  --timeout 300 \
  --seed 42 \
  --agent-mode multimode \
  --best-macro ./results/calibration_macro_v2/optimal_params.json \
  --baseline-dir ./results/baseline_v2 \
  --output ./results/calibration_micro_v2
```

**Estimativa de tempo (6 emuladores)**:
- Cada trial: 75 APKs × 7.5 min (overhead LLM) = 9.4h
- 100 trials / 6 emuladores = ceil(100/6) = 17 rodadas
- 17 × 9.4h = **~160h (~6.7 dias)**

**Consideracoes sobre paralelismo com LLM**:
- SGLang server compartilhado entre 6 emuladores
- Com llm_probability=0.7, ~4.2 requests LLM concorrentes em media
- Qwen3-VL-4B (4B params) suporta essa carga com latencia aceitavel (~700ms/request)
- Timeout de 300s por APK domina — overhead LLM e marginal (~0.5 min/APK extra)

### Fase E: Validacao Final (PENDENTE)

**Objetivo**: Validar parametros calibrados no holdout set (nunca visto durante calibracao)

**Dependencia**: Fase D concluida

```bash
# IMPORTANTE: Usar HOLDOUT SET para validacao final
# Isso prova que os parametros generalizam alem do dataset de calibracao
# 3 repeticoes para significancia estatistica, 6 emuladores via parallel_run.py

# Holdout set (30 APKs × 3 tools × 3 reps = 270 tasks)
python scripts/parallel_run.py \
  --tools "ape,fastbot,rvagent:pure_algorithm@$(cat ./results/calibration_micro_v2/param_string.txt)" \
  --apks-dir $CALIBRATION_DATASET \
  --n-emulators 6 \
  --timeout 300 \
  --repetitions 3 \
  --output-base ./results/validation_holdout_v2 \
  --skip-preprocessing
```

**Estimativa de tempo (6 emuladores)**:
- 3 tools × 30 holdout × 3 reps = 270 tasks
- ceil(270/6) = 45 batches × 7 min = **~5.3 horas**

---

## DSL de Especificacao de Tool para Calibracao

rv-experiment suporta passagem de parametros via formato DSL:
```
tool[:variant][@param1=value1,param2=value2,...]
```

Exemplo de trial de calibracao:
```bash
rv-experiment run \
  --tools "rvagent:pure_algorithm@mop_direct_score=350,stochastic_probability=0.4,max_re_enables=8" \
  --apks-dir ./calibration_dataset \
  --skip-monitors --skip-instrument --skip-static \
  --timeout 300 \
  --output-dir ./calibration/trial_42
```

## Fluxo de Configuracao de Parametros

**Fluxo atual** (rv-experiment → rv-platform → rvagent-tool → rv-agent):

```
PlatformConfig.tools = [
    ToolConfig(
        name="rvagent",
        variants=["pure_algorithm"],
        parameters={                    # <-- Parametros de calibracao vao aqui
            "agent_mode": "pure_algorithm",
            "stochastic_probability": 0.3,
            "stochastic_temperature": 1.0,
            "plateau_window": 10,
            "max_input_variations": 3,
            # Pesos dos scorers
            "mop_direct_score": 300.0,
            "wtg_guided_score": 250.0,
            ...
        }
    )
]
```

## Funcao Objetivo

**Decisao**: Objetivo com 3 componentes (40% cobertura + 40% erros + 20% UI coverage)

**Fontes de dados**:
- `cov_method` e `errors`: lidos do `summary.csv` (gerado pelo rv-platform, generico para qualquer tool)
- `element_coverage`: lido dos `*.rvagent_metrics.json` (gerado pelo rv-agent via MetricsExporter)

| Componente | Peso | Fonte | Escala | Descricao |
|------------|------|-------|--------|-----------|
| Method Coverage | 40% | `summary.csv` → `cov_method` | 0-100% | Cobertura de metodos do app |
| MOP Errors | 40% | `summary.csv` → `errors` | normalizado 0-100 | Erros de operacoes monitoradas |
| UI Coverage | 20% | `*.rvagent_metrics.json` → `ui_coverage.element_coverage` | 0-100% | Elementos UI interagidos |

```python
# score = 0.40 * avg_method_cov + 0.40 * normalized_errors + 0.20 * avg_ui_cov

objective_fn = ObjectiveFunction(
    coverage_weight=0.40,
    errors_weight=0.40,
    ui_coverage_weight=0.20,
    baseline_max_errors=BASELINE_MAX_ERRORS  # da Fase B
)
score = objective_fn.compute(results_dir)
```

**Notas**:
- Maior contagem de erros e MELHOR - indica que mais operacoes monitoradas foram disparadas e violacoes detectadas
- Normalizacao adaptativa de erros usa maximo do baseline (APE/FastBot)
- UI coverage incentiva o agente a interagir com mais elementos distintos, nao apenas navegar entre telas
- O JSON `*.rvagent_metrics.json` so existe para runs do rvagent — se nenhum arquivo for encontrado, UI coverage = 0
- APE e FastBot nao geram rvagent_metrics.json, entao no baseline apenas cov_method e errors contribuem

## Espaco de Parametros (24 parametros)

### Parametros Macro (Fase C - 8 params)
| Parametro | Default | Range | Impacto |
|-----------|---------|-------|---------|
| mop_direct_score | 300.0 | 200-500 | Priorizacao de metodos MOP |
| wtg_guided_score | 250.0 | 100-400 | Guia de navegacao WTG |
| unsaturated_bonus | 80.0 | 40-120 | Diversidade de estados |
| max_re_enables | 6 | 3-15 | Profundidade de exploracao de successors |
| ui_coverage_threshold | 0.9 | 0.7-1.0 | Trigger de re-enable |
| stochastic_probability | 0.3 | 0.1-0.7 | Aleatoriedade de exploracao |
| strength_weight | 50.0 | 25-100 | Sucesso historico de acoes |
| visitation_penalty_factor | -10.0 | -20 a -5 | Penalidade para over-visited |

### Parametros Micro (Fase D - 17 params: 16 numericos + 1 categorico)

**Modo de execucao**: `multimode` (hibrido LLM + algoritmo)

| Parametro | Default | Range | Tipo |
|-----------|---------|-------|------|
| mop_transitive_score | 150.0 | 75-250 | float |
| stochastic_temperature | 1.0 | 0.1-5.0 | float |
| scroll_probability | 0.15 | 0.05-0.3 | float |
| plateau_window | 10 | 5-20 | int |
| max_input_variations | 3 | 1-6 | int |
| gradual_decay_rate | 0.7 | 0.5-0.9 | float |
| component_high_priority | 50.0 | 30-80 | float |
| component_medium_priority | 40.0 | 20-60 | float |
| gradual_decay_base | 200.0 | 100-300 | float |
| gradual_decay_min_visits | 5 | 3-10 | int |
| max_short_term_iterations | 10 | 5-20 | int |
| **llm_probability** | 0.7 | **0.1-0.9** | float |
| **llm_temperature** | 0.01 | **0.001-0.9** | float |
| **llm_top_p** | 0.6 | **0.1-0.99** | float |
| **llm_top_k** | 50 | **10-100** | int |
| **llm_max_retries** | 2 | 0-5 | int |
| **prompt_version** | v13 | **v13, v14, v15, v16** | categorical |

---

## Criterios de Sucesso

**No Calibration Set**:
1. **Method Coverage**: RVAgent > APE em agregado (target: >30% media)
2. **MOP Errors**: RVAgent detecta MAIS erros que APE/FastBot
3. **Win Rate**: RVAgent vence >70% dos APKs em comparacoes pareadas
4. **Composite Score**: RVAgent calibrado supera baseline em >10%

**No Holdout Validation Set** - CRITICO:
5. **Generalizacao**: RVAgent mantem vantagem sobre APE no holdout set
6. **Sem Overfitting**: Performance no holdout >= 80% da performance no calibration set

**Ambos os Sets**:
7. **Significancia Estatistica**: p < 0.05 (teste Wilcoxon signed-rank)
8. **Sem Regressoes**: Nenhum APK onde RVAgent performa >20% pior que baseline

**Nota**: Com dataset maior (50-100 APKs), os testes estatisticos terao poder adequado para detectar diferencas menores. Com 15 APKs, apenas diferencas grandes (>15%) eram detectaveis.

---

## Referencia: Resultados Anteriores (15 APKs)

> **IMPORTANTE**: Os resultados abaixo sao do dataset anterior (15 APKs, doc `20260202_rvagent_validacao.md`).
> Servem como ponto de comparacao mas **nao sao validos para o novo dataset expandido**.
> Todas as fases serao refeitas do zero com o novo dataset.

### Baseline Anterior (15 APKs, 3 reps)

| Metrica | APE | FastBot | RVAgent | Observacao |
|---------|-----|---------|---------|------------|
| cov_method medio | 26.7% | 21.2% | 19.3% | APE lidera |
| cov_act medio | 73.0% | 75.6% | 63.0% | FastBot lidera |
| Erros MOP total | 48 | 43 | 43 | APE detecta mais |
| Max errors/run | 5 | 5 | 5 | openpass |

**BASELINE_MAX_ERRORS = 5** (anterior — sera recalculado para o novo dataset)

### Calibracao Macro Anterior (Trial #33, Score 62.14)

| Parametro | Default | Otimizado | Variacao |
|-----------|---------|-----------|----------|
| mop_direct_score | 300.0 | 473.51 | +58% |
| wtg_guided_score | 250.0 | 359.64 | +44% |
| unsaturated_bonus | 80.0 | 48.15 | -40% |
| max_re_enables | 6 | 3 | -50% |
| ui_coverage_threshold | 0.9 | 0.86 | -4% |
| stochastic_probability | 0.3 | 0.55 | +83% |
| strength_weight | 50.0 | 62.22 | +24% |
| visitation_penalty_factor | -10.0 | -13.20 | +32% |

**Insights** (a validar com dataset maior):
1. MOP Prioritization aumentada: mop_direct_score +58%
2. WTG Guidance aumentada: wtg_guided_score +44%
3. Exploracao mais estocastica: stochastic_probability de 0.3→0.55
4. Menos re-enables: max_re_enables de 6→3
5. Penalidade de visitacao maior: -10→-13.2

**Melhoria de cobertura (15 APKs)**: 22.1% → 24.3% (+2.2% absoluto, +10% relativo)

### Calibracao Micro Anterior

**Status no momento da criacao deste documento**: Em execucao (Fase D, 80 trials multimode)

---

## Plano de Implementacao

### Task 1: Estender RVAgentConfig para Pesos dos Scorers

**Arquivo**: `modules/rv-agent/src/rv_agent/config/agent_config.py`

Campos:
```python
# Pesos dos scorers (calibraveis)
mop_direct_score: float = 300.0
mop_transitive_score: float = 150.0
wtg_guided_score: float = 250.0
unsaturated_bonus: float = 80.0
visitation_penalty_factor: float = -10.0
strength_weight: float = 50.0

# Successor tracker
max_re_enables: int = 6
coverage_threshold: float = 0.9

# Exploracao
scroll_probability: float = 0.15
```

### Task 2: Atualizar Scorers para Usar Valores de Config

**Arquivo**: `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ranking/scorers.py`

```python
class MopScorer(ActionScorer):
    def __init__(self, config: RVAgentConfig):
        self.direct_score = config.mop_direct_score
        self.transitive_score = config.mop_transitive_score
```

### Task 3: Atualizar Mapeamento de Config do rvagent-tool

**Arquivo**: `modules/rvagent-tool/src/rvagent_tool/tools/rvagent/config.py`

```python
scorer_params = [
    "mop_direct_score", "mop_transitive_score", "wtg_guided_score",
    "unsaturated_bonus", "visitation_penalty_factor", "strength_weight",
    "max_re_enables", "coverage_threshold", "scroll_probability"
]
for param in scorer_params:
    if param in tool_config:
        config_dict[param] = tool_config[param]
```

### Task 4: Modulo de Calibracao

**Localizacao**: `modules/rv-agent-validation/src/rv_agent_validation/calibration/`

**Arquivos**:
- `parameter_space.py` - 24 parametros tuneaveis com ranges
- `objective.py` - Scoring composto (method_coverage + errors)
- `optimizer.py` - Wrapper Optuna com TPESampler
- `runner.py` - Orquestra trials de calibracao via rv-experiment
- `cli.py` - Comandos CLI (calibrate, compare)

### Task 5: Dataset Preparado

- Copiar APKs instrumentados para `data/calibration_dataset_v2/`
- Criar `calibration_set_v2.txt`
- Criar `holdout_set_v2.txt`

### Task 6: Calibration Runner

```python
import subprocess
import logging
from typing import Dict, Any

class CalibrationRunner:
    def __init__(self, dataset_dir: str, timeout: int = 300):
        self.dataset_dir = dataset_dir  # APKs pre-instrumentados
        self.timeout = timeout

    def run_trial(self, trial_id: int, params: Dict[str, Any]) -> float:
        # Construir especificacao de tool com parametros
        param_str = ",".join(f"{k}={v}" for k, v in params.items())
        tool_spec = f"rvagent:pure_algorithm@{param_str}"

        output_dir = f"./calibration/trial_{trial_id}"

        # Executar via rv-experiment com flags skip (sem preprocessing)
        cmd = [
            "uv", "run", "rv-experiment", "run",
            "--tools", tool_spec,
            "--apks-dir", self.dataset_dir,
            "--skip-monitors", "--skip-instrument", "--skip-static",
            "--timeout", str(self.timeout),
            "--output-dir", output_dir,
            "--no-window",
            "--repetitions", "1"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logging.warning(f"Trial {trial_id} falhou: {result.stderr}")
            return 0.0

        # Parse resultados e computar score
        return self.compute_objective_score(output_dir)
```

---

## Selecao de Dataset

**Decisao**: 105 APKs filtrados do experimento `exp01_jca`, split 75 calibration / 30 holdout

**Fonte dos APKs originais**: `/home/pedro/desenvolvimento/RV_ANDROID/NOVO/APKS` (557 APKs, 105 validos apos Fase A)
**CSV de referencia**: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/apks/apks_complete.csv` (coluna `exp01_jca=True`)
**Script de selecao**: `scripts/select_dataset.py` (split estratificado, seed 42)
**Script de filtro**: `scripts/filter_apks_static_analysis.py` (GESDA + GATOR + REACH)

---

## Verificacao

1. **Testes unitarios**: Testar passagem de parametros pelo fluxo de config
2. **Teste de integracao**: Executar trial unico de calibracao, verificar params aplicados
3. **Smoke test**: Executar mini calibracao de 3 trials em 2 APKs
4. **Validacao completa**: Comparar RVAgent calibrado vs APE/FastBot no holdout

```bash
# Definir dataset
export CALIBRATION_DATASET="modules/rv-agent-validation/data/calibration_dataset_v2"

# Testar fluxo de parametros
cd modules/rv-agent
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/unit/test_agent_config.py -v

# Teste de integracao com rv-experiment (1 APK apenas para teste rapido)
uv run rv-experiment run \
  --tools "rvagent:pure_algorithm@mop_direct_score=400" \
  --apks-dir $CALIBRATION_DATASET \
  --skip-monitors --skip-instrument --skip-static \
  --timeout 60 \
  --output-dir ./test_calibration_v2

# Verificar que parametros foram aplicados
cat ./test_calibration_v2/summary.csv
```

## Dependencias

```toml
# modules/rv-agent-validation/pyproject.toml
[project.dependencies]
optuna = "^3.5.0"
plotly = "^5.18.0"  # Opcional: para visualizacao Optuna
```

## Reprodutibilidade

Para garantir reprodutibilidade dos resultados de otimizacao:

```python
import optuna

def create_study(seed: int = 42) -> optuna.Study:
    """Cria estudo Optuna com seed fixo para reprodutibilidade."""
    sampler = optuna.samplers.TPESampler(seed=seed)
    return optuna.create_study(
        direction="maximize",
        sampler=sampler,
        study_name="rvagent_calibration_v2"
    )
```

### Seed Support em rv-agent

O seed e propagado do CLI de calibracao ate o rv-agent para garantir reproducibilidade total:

```
CLI --seed 42 → CalibrationRunner.seed → params["seed"] → tool_spec → rv-experiment → rvagent-tool → RVAgentConfig.seed → random.seed()
```

**Notas**:
- Seed 42 usado como padrao para reproducao de resultados
- Resultados serao identicos se executados com mesmos parametros e seed
- Logs de cada trial incluem parametros para auditoria

---

## Timeline Estimado (6 emuladores)

| Fase | Wall-clock | Descricao | Status |
|------|-----------|-----------|--------|
| Fase 0: Dataset | 3.3h | 188 → 105 APKs, split 75/30 | ✅ CONCLUIDA |
| Fase A: Pre-processamento | **1.8h** | 105 APKs instrumentados (6 workers) | ✅ CONCLUIDA |
| Fase B: Baseline | **~18.4h** | 945 tasks / 6 emu (3 reps) | ⏳ EM EXECUCAO |
| Fase C: Calibracao Macro | **~122h (5.1d)** | 80 trials × 75 APKs, 6 paralelos | ⏳ PENDENTE |
| Fase D: Calibracao Micro | **~160h (6.7d)** | 100 trials × 75 APKs, 6 paralelos | ⏳ PENDENTE |
| Fase E: Validacao Final | **~5.6h** | 270 tasks / 6 emu (3 reps, holdout) | ⏳ PENDENTE |
| **Total estimado** | **~299h (~12.5 dias)** | Margem: ~2.5 dias para imprevistos | |

**Configuracao**: 75 cal / 30 holdout, 80 trials macro + 100 trials micro, 6 emuladores paralelos

---

## Checklist de Implementacao

### Task 1: Estender RVAgentConfig
- [x] 1.1 Adicionar campos de pesos dos scorers em `agent_config.py`
- [x] 1.2 Adicionar campos de parametros do successor_tracker
- [x] 1.3 Adicionar campos de exploracao (scroll_probability)
- [x] 1.4 Testes unitarios para novos campos

### Task 2: Atualizar Scorers
- [x] 2.1 MopScorer: aceitar config no __init__
- [x] 2.2 WtgScorer: aceitar config no __init__
- [x] 2.3 SaturationScorer: aceitar config no __init__
- [x] 2.4 VisitationPenaltyScorer: aceitar config no __init__
- [x] 2.5 StrengthScorer: aceitar config no __init__
- [x] 2.6 Atualizar RVAgentStrategy para passar config aos scorers
- [x] 2.7 Testes unitarios para scorers configurados

### Task 3: Atualizar rvagent-tool Config Mapping
- [x] 3.1 Adicionar parametros dos scorers ao mapeamento
- [x] 3.2 Testar passagem de parametros via DSL (validado no smoke test)

### Task 4: Modulo de Calibracao
- [x] 4.1 Criar `parameter_space.py`
- [x] 4.2 Criar `objective.py` (com tratamento robusto de erros)
- [x] 4.3 Criar `optimizer.py` (Optuna wrapper com seed para reprodutibilidade)
- [x] 4.4 Criar `runner.py` (CalibrationRunner)
- [x] 4.5 Criar `cli.py` (comando calibrate com --seed)
- [x] 4.6 Adicionar dependencia optuna ao pyproject.toml

### Task 5: Dataset Preparado
- [x] 5.1 Dataset anterior disponivel (15 APKs validos)
- [x] 5.2 Executar filtro de APKs (Fase 0) — 107/165 passaram (64.8%)
- [x] 5.3 Instrumentar APKs filtrados (Fase A) — 105/107 OK, 2 falhas
- [x] 5.4 Criar calibration_set_v2.txt (75 APKs) — `out/dataset_selection/`
- [x] 5.5 Criar holdout_set_v2.txt (30 APKs) — `out/dataset_selection/`
- [x] 5.6 Copiar APKs e arquivos de analise estatica para data/calibration_dataset_v2/

### Task 6: Validacao
- [x] 6.1 Testes unitarios passando
- [x] 6.2 Teste de integracao (1 trial com parametro customizado)
- [x] 6.3 Smoke test (3 trials em 2 APKs) — concluido 2026-02-02
- [ ] 6.4 Baseline no novo dataset (Fase B)
- [ ] 6.5 Calibracao macro no novo dataset (Fase C)
- [ ] 6.6 Calibracao micro no novo dataset (Fase D)
- [ ] 6.7 Validar no holdout set — generalizacao (Fase E)

---

## Referencias

- Documento anterior de validacao (15 APKs):
  - `docs/20260202_rvagent_validacao.md`
- Documentos de referencia:
  - `docs/20260115_rvagent_validacao_multimodal.md`
  - `docs/20260105_rvagent_validacao.md`
  - `docs/20251231_rvagent_validacao.md`
- Modulo rv-agent-validation: `modules/rv-agent-validation/`
- Plano de refactoring (paralelismo): `modules/rv-agent-validation/docs/20260207_refactoring_parallel.md`
- Script de filtro: `scripts/filter_apks_static_analysis.py`
- Script de selecao: `scripts/select_dataset.py`
- Script de execucao paralela: `scripts/parallel_run.py`
- Experimento base (188 APKs): exp01_jca
- Resultados do filtro: `out/static_analysis_filter/`
- Dataset selecionado: `out/dataset_selection/`

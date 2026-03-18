# APE-RV: Plano de Calibração via Optuna

**Data**: 2026-03-17 (planejamento), execução TBD
**Status**: Consolidado — exp3 DONE, 30 APKs selecionados, aguardando implementação dos scripts
**Dependências**: exp3 baseline (rodando), gh42 (concluída), gh9 infra (reutilizável)
**Contexto**: `docs/20260316_aperv_llm.md` (ideação), `openspec/changes/gh9-docker-calibration/design.md` (referência)

---

## 1. Objetivo

Calibrar os 19 parâmetros configuráveis do APE-RV (exploração + MOP + LLM) em duas fases para maximizar cobertura MOP e method coverage. A calibração segue o padrão do gh9 (rv-agent): Optuna TPESampler → Docker containers → scoring → feedback.

### 1.1 Por que calibrar?

- Os defaults do APE-RV nunca foram calibrados — são valores heurísticos do APE original (2020)
- Os pesos MOP (500/300/100) foram escolhidos manualmente com base em 2 experimentos
- Os parâmetros LLM (temperature=0.3, top_p=0.6) são defaults do gh6 sem tuning
- Resultado do exp3 (baseline LLM) mostrará o gap entre defaults e potencial máximo

### 1.2 Métricas de sucesso

1. `aperv:sata_mop_llm` calibrado > `aperv:sata_mop_v1` (28.35%) em method coverage (Wilcoxon p<0.05)
2. MOP coverage calibrado > baseline (37.02%)
3. Violation types ≥ 23 (igualar melhor resultado atual)

---

## 2. Pré-requisitos

| # | Pré-requisito | Status | Detalhes |
|---|--------------|--------|----------|
| 1 | gh42 — all params in ape.properties | DONE | `APERV_PROPERTY_MAPPING` com 23 entries |
| 2 | gh41 — LLM variants registrados | DONE | `aperv:sata_mop_llm` com 9 LLM keys |
| 3 | Exp3 — baseline LLM (defaults) | DONE | 507/507 tasks, 0 failures |
| 4 | Exp1+Exp2 — baselines sem LLM | DONE | 5 ferramentas, 169 APKs |
| 5 | calibration_orchestrator.py | DONE (gh9) | Precisa adaptação para aperv |
| 6 | Docker image 0.8.0 | DONE | Inclui gh41+gh42 |
| 7 | SGLang server | DISPONÍVEL | Qwen3-VL-4B-Instruct (só para MICRO) |
| 8 | APKs pré-instrumentados | DONE | 169 APKs + JSONs em `data/apks/` |
| 9 | **Fix no_match rate** | **A FAZER** | Investigar coordinate mapping antes de calibrar (ver Seção 11) |
| 10 | **Fix llmMaxCalls** | **A FAZER** | Setar default para sem limite (ver Seção 11) |

---

## 3. Espaço de Parâmetros (19 params)

### 3.1 Visão geral

A calibração é dividida em duas fases com ferramentas diferentes:

| Fase | Tool | Params | LLM | SGLang | Otimiza |
|------|------|--------|-----|--------|---------|
| **MACRO** | `aperv:sata_mop` | 13 efetivos (exploração + MOP) | Desligado | Não precisa | Engine de exploração pura |
| **MICRO** | `aperv:sata_mop_llm` | 4 (LLM mode + sampling) | Ligado | Sim | Como o LLM integra na exploração otimizada |

**Racional MACRO sem LLM**: A fase MACRO otimiza a engine de exploração (SATA + MOP weights) sem interferência do LLM. Os 600s de cada trial são 100% exploração algorítmica. O LLM adicionaria ruído (overhead de latência + ações no_match) que confundiria a otimização dos params de exploração. Além disso, não precisa de SGLang — libera GPU e remove um ponto de falha.

**Risco**: params ótimos sem LLM podem não ser ótimos com LLM (efeito de interação). Mitigação: a fase MICRO roda com LLM ativo usando os params MACRO como base. Para calibração full futura, MACRO pode ser re-executada com LLM se necessário.

### 3.2 Fase MACRO — 14 parâmetros (exploração + MOP)

**Tool**: `aperv:sata_mop` (sem LLM)

| # | Python key | Java key | Default | Range | Tipo | Controla |
|---|-----------|----------|---------|-------|------|----------|
| 1 | `default_epsilon` | `ape.defaultEpsilon` | 0.05 | [0.01, 0.20] | float | % ações aleatórias vs greedy |
| 2 | `graph_stable_restart_threshold` | `ape.graphStableRestartThreshold` | 100 | [30, 300] | int | Steps sem crescimento → restart |
| 3 | `state_stable_restart_threshold` | `ape.stateStableRestartThreshold` | 50 | [20, 150] | int | Steps no mesmo state → restart |
| 4 | `fuzzing_rate` | `ape.fuzzingRate` | 0.02 | [0.0, 0.10] | float | % fuzzing por step |
| 5 | `do_fuzzing` | `ape.doFuzzing` | true | {true, false} | bool | Liga/desliga fuzzing |
| 6 | `throttle_for_activity_transition` | `ape.throttleForActivityTransition` | 500 | [200, 1000] | int | Delay transição activity (ms) |
| 7 | `throttle_ms` | `ape.defaultGUIThrottle` | 200 | [100, 500] | int | Delay entre ações (ms) |
| 8 | `max_extra_priority_aliased_actions` | `ape.maxExtraPriorityAliasedActions` | 5 | [1, 15] | int | Boost ações multi-alvo |
| 9 | `max_states_per_activity` | `ape.maxStatesPerActivity` | 10 | [5, 30] | int | Cap states por activity |
| 10 | `trivial_activity_rank_threshold` | `ape.trivialActivityRankThreshold` | 3 | [1, 8] | int | Threshold activity trivial |
| 11 | `do_back_to_trivial_activity` | `ape.doBackToTrivialActivity` | false | {true, false} | bool | Backtrack para triviais |
| 12 | `mop_weight_direct` | `ape.mopWeightDirect` | 500 | [100, 1000] | int | Boost MOP direto |
| 13 | `mop_weight_transitive` | `ape.mopWeightTransitive` | 300 | [50, 600] | int | Boost MOP transitivo |
| 14 | `mop_weight_activity` | `ape.mopWeightActivity` | 100 | [10, 200] | int | Boost MOP activity-level |

### 3.3 Fase MICRO — 4 parâmetros (LLM)

**Tool**: `aperv:sata_mop_llm` (com LLM, params MACRO fixados nos valores ótimos)

| # | Optuna key | Java keys | Default | Range | Tipo | Controla |
|---|-----------|-----------|---------|-------|------|----------|
| 15 | `llm_mode` | `ape.llmOnNewState` + `ape.llmOnStagnation` | both | {new_state_only, stagnation_only, both} | categorical | Quando chamar o LLM |
| 16 | `llm_temperature` | `ape.llmTemperature` | 0.3 | [0.0, 0.7] | float | Criatividade/aleatoriedade LLM |
| 17 | `llm_top_p` | `ape.llmTopP` | 0.6 | [0.3, 0.95] | float | Nucleus sampling threshold |
| 18 | `llm_top_k` | `ape.llmTopK` | 50 | [10, 100] | int | Top-K tokens considerados |

**Nota sobre `llm_mode`**: Substituiu 2 booleanos independentes (`llm_on_new_state`, `llm_on_stagnation`) para evitar o caso degenerado onde ambos=false (= sem LLM = idêntico ao MACRO). O `suggest_params` mapeia o categórico para as 2 propriedades Java.

**Parâmetros fixos (não calibráveis)**:
- `llm_timeout_ms` = 15000 (fixo — timeout de rede, não afeta qualidade de exploração)
- `llm_max_calls` = 999999 (efetivamente sem limite — o routing natural via llm_mode controla quantas chamadas ocorrem; o cap artificial foi removido)

---

## 4. Função Objetivo

### 4.1 Decisão: 50% MOP + 50% Method (opção B)

```
score = 0.50 × mop_coverage + 0.50 × method_coverage
```

| Componente | Peso | Justificativa |
|-----------|------|---------------|
| MOP coverage (`cov_rv_method`) | 50% | Objetivo primário da tese: atingir operações monitoradas |
| Method coverage (`cov_method`) | 50% | Exploração ampla — proxy de qualidade geral |

**Por que não incluir violations (errors)?**
- Violations têm alta variância — 1 violation rara num APK pode dominar o score de um trial
- Existe correlação entre MOP coverage e violations: atingir mais operações monitoradas → mais chance de detectar misuse
- Violations entram na **análise de validação** (fase E), não no scoring de otimização
- Simplifica: score mais estável → Optuna converge melhor

### 4.2 Implementação

```python
def compute(results_dir: str) -> float:
    """Compute calibration score from summary.csv.

    Uses trimmed mean (10% cut) for robustness against outlier APKs.
    """
    summary = pd.read_csv(f"{results_dir}/summary.csv")
    avg_method = trim_mean(summary["cov_method"].values, 0.1)
    avg_mop = trim_mean(summary["cov_rv_method"].values, 0.1)
    return 0.50 * avg_mop + 0.50 * avg_method
```

---

## 5. Dataset de Calibração

### 5.1 APKs disponíveis

| Dataset | # APKs | Path | Uso |
|---------|--------|------|-----|
| Completo | 169 | `data/apks/available_169.txt` | Experimentos finais (validação) |
| Viáveis | 149 | `out/aperv_dataset_selection/all_valid_apks.txt` | Filtrados: method_coverage >= 5% em pelo menos uma tool |
| **Pre-cal APE-RV** | **30** | **`data/apks/aperv_precal_30.txt`** | **Calibração MACRO + MICRO** |
| Pre-cal rv-agent (gh9) | 40 | `modules/rv-agent-validation/data/precal_set.txt` | Referência (independente) |

### 5.2 Pre-calibração: 30 APKs — DONE

**Path**: `data/apks/aperv_precal_30.txt`
**Artefatos de seleção**: `out/aperv_dataset_selection/` (CSVs, relatório, holdout)

**Processo de seleção** (2026-03-18):

1. **Filtro de viabilidade**: dos 169 APKs, removidos 20 com method_coverage < 5% em todas as tools (apps crashando, stuck em loop, ou irresponsivos — não discriminam params bons vs ruins)
2. **Estratificação `category × size_bucket`**: via `scripts/select_dataset.py` usando metadata de `apks_complete.csv` (253 APKs, 17 categorias, 5 faixas de tamanho por número de métodos). Resultado: 30 APKs proporcionalmente distribuídos em 25 estratos
3. **Cross-validation com baseline**: cruzamento da cobertura dos 30 pré-selecionados com todas as 6 ferramentas do exp1+exp2+exp3 (ape, aperv:sata, aperv:sata_mop_v1/v2, aperv:sata_mop_llm, rvsmart:mvp)
4. **Remoção de APKs problemáticos**: huewidgets (widget app, ALL_LOW), routerkeygen (ALL_LOW, max 7,2%), poul.bits (ALL_LOW, max 9,8%), superuser (app de root, precisa root)
5. **Swap gap-based**: removidos 6 APKs com gap 0pp (todas as tools performam igual — não discriminam params) e incluídos 9 APKs com gap >= 10pp (onde outra tool performa melhor que `aperv:sata_mop_v2` — oportunidades de calibração)

**Resultado final**:

| Métrica | Subset (30) | Pop viável (149) |
|---------|-------------|------------------|
| Method mean (v2) | 28,8% | 30,8% |
| Strata cobertos | 25 | 56 |
| Big-gap (>=10pp) | 11/30 (37%) | 13/149 (9%) |
| Gap médio vs best tool | 9,5pp | — |

**Top oportunidades de calibração** (APKs com maior gap vs melhor ferramenta):

| APK | sata_mop_v2 | max (best tool) | gap |
|-----|------------|-----------------|-----|
| sandwichroulette | 21,4% | 67,2% (sata_mop_v1) | +45,9pp |
| potdroid | 5,6% | 39,3% (sata) | +33,7pp |
| fas | 20,2% | 49,9% (rvsmart) | +29,6pp |
| hashmypass | 33,6% | 52,5% (sata_mop_v1) | +18,9pp |
| munch | 15,7% | 34,3% (rvsmart) | +18,7pp |

**Fontes de dados usadas**:
- Cobertura: `data/results/exp3_consolidated.csv` (6 tools, 169 APKs)
- Metadata: `/home/pedro/.../ase-journal/dataset/results/apks/apks_complete.csv` (253 APKs, categorias, métodos, crashes)
- Script: `scripts/select_dataset.py` (seleção estratificada)

### 5.3 Validação: 149 APKs viáveis

Comparação direta com exp1-3 usando os 149 APKs viáveis (excluindo os 20 com coverage < 5% em todas as tools).

---

## 6. Como o Optuna Funciona em Paralelo

### 6.1 Rounds (bateladas)

O orchestrator não lança todas as trials de uma vez. Trabalha em **rounds**:

```
Round 1: lança N containers em paralelo → N trials → espera TODOS terminarem
          Optuna recebe N scores, atualiza o modelo
Round 2: lança mais N → usa aprendizado do round 1 para sugerir melhores params
Round 3: ...
Round K: últimos trials
```

Cada round demora o tempo de **1 trial** (todos rodam em paralelo). O aprendizado do Optuna acontece **entre rounds**. Total de rounds = ceil(trials / containers).

### 6.2 Startup random vs TPE learning

O TPESampler tem `n_startup_trials` que controla quantas trials são quasi-random antes do TPE começar a aprender. Exemplo com 10 containers e startup=20:

```
Round 1: 10 trials random     ← sem aprendizado (0 scores disponíveis)
Round 2: 10 trials random     ← sem aprendizado (10 scores < startup=20)
Round 3: 10 trials TPE-guided ← APRENDIZADO começa (20 scores disponíveis)
Round 4+: TPE cada vez melhor
```

### 6.3 Constant Liar (paralelismo correto)

Dentro de cada round, N trials rodam em paralelo. O TPESampler é sequencial por natureza — quando o worker 3 pede params, os workers 1 e 2 ainda estão rodando (sem score). O `constant_liar=True` resolve isso:

- Atribui score pessimista (infinito) aos trials em execução
- Força o Optuna a sugerir params em regiões DIFERENTES para cada worker
- Evita que N workers recebam configurações quase idênticas

**Config do sampler** (já implementada no orchestrator do gh9):
```python
TPESampler(
    constant_liar=True,      # diversidade entre workers paralelos
    multivariate=True,       # modela correlações entre params
    n_startup_trials=N,      # configurável por fase (MACRO=20, MICRO=10)
    seed=42,                 # reprodutibilidade (dentro de cada round)
)
```

### 6.4 Quantas trials são suficientes?

Regra prática: `3-5× número de parâmetros` para boa convergência do TPE.

| Fase | Params | Mínimo (3×) | Ideal (5×) | Escolhido | Containers | Startup | TPE efetivo |
|------|--------|------------|-----------|-----------|-----------|---------|-------------|
| MACRO | 13 efetivos | 39 | 65 | **130** | 10 | 20 (15%) | **110 (85%)** |
| MICRO | 4 | 12 | 20 | **80** | 8 | 10 (13%) | **70 (88%)** |

Para MACRO com 130 trials e 10 containers: 85% de eficiência (110 trials guiados pelo TPE, ~8.5× cobertura dos 13 params efetivos). Excelente convergência.

---

## 7. Pre-Calibração MACRO

### 7.1 Configuração

| Parâmetro | Valor |
|-----------|-------|
| Tool | `aperv:sata_mop` (sem LLM) |
| Params calibrados | 14 (exploração + MOP) |
| Trials | 130 |
| n_startup_trials | 20 (2 × 10 containers) |
| TPE efetivo | 110 trials (85% eficiência) |
| APKs | 30 (subset estratificado dos 169) |
| Timeout | 600s |
| Containers | 10 (sem SGLang → mais parallelismo) |
| SGLang | Não precisa |
| Scoring | 50% MOP + 50% method |
| Baseline | `aperv:sata_mop_v1` (exp1, pesos v1: 500/300/100) |
| Rounds | ceil(130/10) = 13 |
| Tempo/round | 30 × 680s ÷ 3600 = 5.7h |
| **Tempo total** | **13 × 5.7h = ~74h (~3.1 dias)** |

### 7.2 Comando

```bash
nohup uv run python scripts/calibration_orchestrator.py \
  --phase macro --n-trials 130 --n-containers 10 \
  --data-dir data/apks \
  --filter-file data/apks/aperv_precal_30.txt \
  --output-dir ./results/aperv_precal_macro \
  --timeout 600 --tool aperv:sata_mop \
  --cpus 4 --memory 10g --seed 42 \
  > results/aperv_precal_macro.log 2>&1 &
```

**Sem `--sglang-url`** — MACRO roda sem LLM, não precisa de SGLang. A GPU fica livre.
**10 containers** — sem SGLang, a máquina aguenta mais emuladores (40 CPUs, 100GB RAM).

### 7.3 Output esperado

- `results/aperv_precal_macro/optuna_study.db` — banco Optuna (crash-resilient)
- `results/aperv_precal_macro/optimal_params.json` — 14 melhores params
- `results/aperv_precal_macro/trial_history.json` — histórico completo
- `results/aperv_precal_macro/param_string.txt` — DSL pronta para usar

---

## 8. Pre-Calibração MICRO

### 8.1 Configuração

| Parâmetro | Valor |
|-----------|-------|
| Tool | `aperv:sata_mop_llm` (com LLM) |
| Params calibrados | 4 (LLM mode + sampling) |
| Params fixos | 14 MACRO (de `optimal_params.json`) |
| Trials | 80 |
| n_startup_trials | 10 (4 params não precisam de 16 random) |
| TPE efetivo | 70 trials (88% eficiência) |
| APKs | 30 (mesmo subset do MACRO) |
| Timeout | 600s |
| Containers | 8 (SGLang ocupa recursos) |
| SGLang | Sim (Qwen3-VL-4B-Instruct) |
| Scoring | 50% MOP + 50% method |
| Baseline | exp3 (`aperv:sata_mop_llm` com defaults LLM) |
| Rounds | ceil(80/8) = 10 |
| Tempo/round | 30 × 680s ÷ 3600 = 5.7h |
| **Tempo total** | **10 × 5.7h = ~57h (~2.4 dias)** |

### 8.2 Comando

```bash
nohup uv run python scripts/calibration_orchestrator.py \
  --phase micro --n-trials 80 --n-containers 8 \
  --data-dir data/apks \
  --filter-file data/apks/aperv_precal_30.txt \
  --output-dir ./results/aperv_precal_micro \
  --timeout 600 --tool aperv:sata_mop_llm \
  --best-macro ./results/aperv_precal_macro/optimal_params.json \
  --sglang-url http://host.docker.internal:30000/v1 \
  --cpus 4 --memory 10g --seed 42 \
  > results/aperv_precal_micro.log 2>&1 &
```

### 8.3 Nota sobre startup reduzido

O MICRO usa `n_startup_trials=10` em vez do padrão `2 × containers = 16`. Com 4 params, 10 pontos random já cobrem bem o espaço. Com 8 containers, `ceil(10/8)=2` rounds random — o TPE começa a guiar a partir do round 2 (6 dos 8 trials do round 2 já são TPE-guided). Resultado: 70 trials TPE efetivos em 80 totais = 88% eficiência.

---

## 9. Validação (Fase E)

Após MACRO + MICRO, rodar o variant calibrado no dataset completo:

```
aperv:sata_mop_llm@{all 19 optimal params} × 169 APKs × 3 reps × 600s
```

Comparação com todas as ferramentas (6 tools: ape, aperv:sata, aperv:sata_mop_v1/v2, rvsmart:mvp, aperv:sata_mop_llm baseline).

Docker compose similar ao exp3 mas com params calibrados via `RV_TOOLS`.

---

## 10. Adaptação da Infraestrutura

### 10.1 Artefatos necessários

| Artefato | Path | Descrição |
|----------|------|-----------|
| `aperv_parameter_space.py` | `scripts/` | 19 params, ranges, suggest_params(), params_to_tool_spec() |
| `aperv_objective.py` | `scripts/` | Função objetivo 50/50 (mop/method) |
| Adaptação orchestrator | `scripts/calibration_orchestrator.py` | Flag `--tool` genérico |
| `aperv_precal_30.txt` | `data/apks/` | 30 APKs estratificados |

### 10.2 Adaptação do orchestrator

Mudanças mínimas:

1. **Flag `--tool`**: generalizar tool spec
   ```python
   # Atual: tool_spec = f"rvagent:{mode}@{params_to_tool_spec(merged_params)}"
   # Novo:  tool_spec = f"{args.tool}@{params_to_tool_spec(merged_params)}"
   ```

2. **Import parameter_space**: selecionar por `--tool` (rv-agent vs aperv)

3. **Import objective function**: selecionar por `--tool`

4. **Env vars no compose**: `RVSMART_LLM_MODE: "true"` para socat bridge (só MICRO)

5. **Sem SGLang no compose MACRO**: apenas containers rvandroid

### 10.3 aperv_parameter_space.py

```python
"""Parameter space for APE-RV calibration via Optuna."""

MACRO_PARAMS = [
    {"name": "default_epsilon", "type": "float", "low": 0.01, "high": 0.20, "default": 0.05},
    {"name": "graph_stable_restart_threshold", "type": "int", "low": 30, "high": 300, "default": 100},
    {"name": "state_stable_restart_threshold", "type": "int", "low": 20, "high": 150, "default": 50},
    {"name": "fuzzing_rate", "type": "float", "low": 0.0, "high": 0.10, "default": 0.02},
    {"name": "do_fuzzing", "type": "categorical", "choices": ["true", "false"], "default": "true"},
    {"name": "throttle_for_activity_transition", "type": "int", "low": 200, "high": 1000, "default": 500},
    {"name": "throttle_ms", "type": "int", "low": 100, "high": 500, "default": 200},
    {"name": "max_extra_priority_aliased_actions", "type": "int", "low": 1, "high": 15, "default": 5},
    {"name": "max_states_per_activity", "type": "int", "low": 5, "high": 30, "default": 10},
    {"name": "trivial_activity_rank_threshold", "type": "int", "low": 1, "high": 8, "default": 3},
    {"name": "do_back_to_trivial_activity", "type": "categorical", "choices": ["true", "false"], "default": "false"},
    {"name": "mop_weight_direct", "type": "int", "low": 100, "high": 1000, "default": 500},
    {"name": "mop_weight_transitive", "type": "int", "low": 50, "high": 600, "default": 300},
    {"name": "mop_weight_activity", "type": "int", "low": 10, "high": 200, "default": 100},
]

MICRO_PARAMS = [
    {"name": "llm_on_new_state", "type": "categorical", "choices": ["true", "false"], "default": "true"},
    {"name": "llm_on_stagnation", "type": "categorical", "choices": ["true", "false"], "default": "true"},
    {"name": "llm_temperature", "type": "float", "low": 0.01, "high": 0.5, "default": 0.3},
    {"name": "llm_top_p", "type": "float", "low": 0.3, "high": 0.95, "default": 0.6},
    {"name": "llm_top_k", "type": "int", "low": 10, "high": 100, "default": 50},
]

def suggest_params(trial, phase):
    params = {}
    param_list = MACRO_PARAMS if phase == "macro" else MICRO_PARAMS
    for p in param_list:
        if p["type"] == "float":
            params[p["name"]] = trial.suggest_float(p["name"], p["low"], p["high"])
        elif p["type"] == "int":
            params[p["name"]] = trial.suggest_int(p["name"], p["low"], p["high"])
        elif p["type"] == "categorical":
            params[p["name"]] = trial.suggest_categorical(p["name"], p["choices"])
    return params

def params_to_tool_spec(params: dict) -> str:
    parts = []
    for key, value in sorted(params.items()):
        if isinstance(value, float):
            parts.append(f"{key}={value:.6f}")
        else:
            parts.append(f"{key}={value}")
    return ",".join(parts)
```

---

## 11. Ações ANTES da Calibração

### 11.1 CRÍTICO: Investigar no_match rate (37,3%)

O exp3 (9.525 chamadas LLM em 507 tasks) mostra **37,3% no_match** (3.554 chamadas). 8 APKs com 100% no_match, 80 APKs (47%) na faixa 26-50%. Cada chamada no_match é **~1.5s de overhead puro** sem benefício.

**Causas identificadas** (análise preliminar dos traces):
1. App crashes → launcher aparece → LLM vê tela errada (100% no_match)
2. State mismatch → coordenada válida visualmente mas cai em gap entre widgets
3. Euclidean fallback conservador (tolerância `max(50, min(w,h)/2)` px)

**Ação**: gh46 — investigação completa em 3 fases (replay forense, comparação de prompts, melhorias + testes de integração). Ver `docs/20260318_aperv_coordenadas_gh46.md`. Meta: reduzir no_match para <20% ANTES da calibração MICRO.

### 11.2 Fix llmMaxCalls

O `LlmRouter.java` tem um cap de chamadas LLM (`Config.llmMaxCalls`, default 200). Isso limita artificialmente o número de consultas ao LLM por run. O routing natural via `llmOnNewState` e `llmOnStagnation` já controla quando o LLM é chamado (~60-110 vezes por run de 10min).

**Ação**: setar `llmMaxCalls` default para 999999 no variant `sata_mop_llm` (efetivamente sem limite). O cap não é um parâmetro de calibração — é uma proteção de custo que não faz sentido quando o routing já limita as chamadas.

Alternativamente, manter o cap mas com valor alto (ex: 1000) como safety net.

### 11.3 Selecionar 30 APKs para pre-cal — DONE

**CONCLUÍDO** em 2026-03-18. Ver Seção 5.2 para detalhes completos do processo de seleção.

Path: `data/apks/aperv_precal_30.txt` (30 APKs, estratificados por `category × size_bucket`, com 11 big-gap APKs para maximizar potencial de calibração).

---

## 12. Fluxo de Dados End-to-End

### 12.1 MACRO (sem LLM)

```
Optuna.suggest_params()
  → {"default_epsilon": 0.08, "mop_weight_direct": 400, ...}
  ↓
tool_spec = "aperv:sata_mop@default_epsilon=0.080000,mop_weight_direct=400,..."
  ↓
Docker ENV: RV_TOOLS="aperv:sata_mop@..."
            (sem RVSMART_LLM_MODE, sem SGLang)
  ↓
docker-entrypoint.sh → rv-experiment CLI
  ↓
ApeRVTool._push_properties() → APERV_PROPERTY_MAPPING → ape.properties
  ↓
Java Config.java reads → APE-RV explora com SATA+MOP calibrado
  ↓
summary.csv → score = 50% MOP + 50% method
  ↓
Optuna.tell(trial, score)
```

### 12.2 MICRO (com LLM)

```
Optuna.suggest_params()
  → {"llm_temperature": 0.15, "llm_top_p": 0.8, ...}
  ↓
merged_params = {**optimal_macro_params, **micro_params}
  ↓
tool_spec = "aperv:sata_mop_llm@default_epsilon=0.08,...,llm_temperature=0.15,..."
  ↓
Docker ENV: RV_TOOLS="aperv:sata_mop_llm@..."
            RVSMART_LLM_MODE="true"  (socat bridge)
  ↓
docker-entrypoint.sh → socat bridge + rv-experiment CLI
  ↓
ApeRVTool._push_properties() → ape.properties (14 MACRO fixos + 5 MICRO calibrados)
  ↓
Java Config.java reads → APE-RV explora com SATA+MOP+LLM calibrado
  ↓
summary.csv → score = 50% MOP + 50% method
  ↓
Optuna.tell(trial, score)
```

---

## 13. Timeline Estimada

| Etapa | Tempo | Depende de |
|-------|-------|-----------|
| Exp3 baseline LLM (rodando) | ~12h | — |
| Análise exp3 + decisão | ~2h | exp3 |
| Fix no_match (gh43) | ~4-8h | análise exp3 |
| Fix llmMaxCalls + rebuild image | ~1h | — |
| Selecionar 30 APKs + aperv_parameter_space.py | ~2h | — |
| Adaptar orchestrator + aperv_objective.py | ~3h | — |
| **Pre-cal MACRO (C0)** — 130 trials, 10 ctns, sem SGLang | **~74h (3.1 dias)** | fixes acima |
| Análise MACRO + ajustes | ~2h | C0 |
| **Pre-cal MICRO (D0)** — 80 trials, 8 ctns, com SGLang | **~57h (2.4 dias)** | C0 + GPU |
| Validação (E) — 169 APKs × 3 reps | ~12h | D0 |

**Baselines**:
- MACRO: `aperv:sata_mop_v1` (exp1 — pesos v1 500/300/100, sem LLM)
- MICRO: `aperv:sata_mop_llm` (exp3 — defaults LLM, rodando agora)

---

## 14. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| No_match rate permanece alto após fix | Média | Alto | Investigar com profundidade; se não resolver, calibrar temperature/top_p agressivamente |
| Queda de luz (perda de trials) | Média | Baixo | Optuna SQLite + `--resume` no orchestrator |
| Params MACRO não convergem em 130 trials | Baixa | Médio | Analisar trial_history; se necessário, restringir ranges e rodar mais trials |
| Interação MACRO×LLM significativa | Média | Médio | Re-rodar MACRO com LLM na calibração full |
| GPU indisponível por longo período | Média | Baixo (MACRO) / Alto (MICRO) | MACRO não precisa de GPU; MICRO espera GPU disponível |

---

## 15. Artefatos de Referência

| Artefato | Path | Descrição |
|----------|------|-----------|
| Ideação LLM | `docs/20260316_aperv_llm.md` | Pre-plano com 19 params, modos LLM |
| Design gh9 | `openspec/changes/gh9-docker-calibration/design.md` | Runbook calibração rv-agent |
| Orchestrator | `scripts/calibration_orchestrator.py` | Script host-side (reutilizável) |
| Parameter space rv-agent | `modules/rv-agent-validation/src/.../parameter_space.py` | Template para aperv |
| Pre-cal APKs | `modules/rv-agent-validation/data/precal_set.txt` | 40 APKs (100% em available_169) |
| Exp1 results | `data/results/aperv_comparacao_consolidated.csv` | ape, aperv:sata, aperv:sata_mop |
| Exp2 results | `data/results/exp2_consolidated.csv` | 5 tools merged |
| Exp3 results | `data/results/exp3_00..07/` | aperv:sata_mop_llm baseline |
| Docker compose exp3 | `docker/docker-compose.exp3-aperv-llm.yml` | Template compose |
| Análises LLMs | `docs/analise_{claude,gemini,minimax,qwen}.md` | 4 análises independentes do plano |

---

## 16. Melhorias Pós-Análise (2026-03-18)

O plano foi submetido a 4 LLMs (Claude, Gemini, Minimax, Qwen) para análise independente. Todas aprovaram o plano como executável. As seguintes melhorias foram aplicadas com base na síntese cruzada das sugestões:

### 16.1 Espaço de Parâmetros (`aperv_parameter_space.py`)

| # | Melhoria | Justificativa | Fonte |
|---|---------|---------------|-------|
| 1 | `step=10` para `mop_weight_direct`, `mop_weight_transitive`, `mop_weight_activity`, `graph_stable_restart_threshold` | Reduz espaço de busca efetivo ~10× por parâmetro sem perda semântica (500 vs 501 é idêntico) | Claude, Minimax |
| 2 | `log=True` para `throttle_ms`, `throttle_for_activity_transition` | Amostragem log-uniforme — diferença 100→200ms é mais impactante que 900→1000ms | Gemini |
| 3 | Fuzzing condicional: `fuzzing_rate` só sugerido quando `do_fuzzing=true` | Elimina dimensão desperdiçada quando fuzzing está desligado | Minimax |
| 4 | `llm_mode` categórico (3 opções) substitui 2 booleanos independentes | Evita caso degenerado `llm_on_new_state=false` + `llm_on_stagnation=false` (= sem LLM = idêntico ao MACRO) | Claude, Minimax |
| 5 | `llm_temperature` expandido de [0.01, 0.5] para [0.0, 0.7] | Range original era conservador para tarefas de geração de ações GUI | Minimax |

**Parâmetros efetivos após melhorias**:
- MACRO: 13 dimensões efetivas (14 declarados, mas `fuzzing_rate` é condicional)
- MICRO: 4 parâmetros (`llm_mode`, `llm_temperature`, `llm_top_p`, `llm_top_k`)

### 16.2 Função Objetivo (`aperv_objective.py`)

| # | Melhoria | Justificativa | Fonte |
|---|---------|---------------|-------|
| 6 | Trimmed mean (corte 10%) em vez de média simples | Robustez contra outliers — 1 APK que crasha (coverage=0) distorce o score do trial inteiro | Claude, Minimax |

### 16.3 Orchestrator (`calibration_orchestrator.py`)

| # | Melhoria | Justificativa | Fonte |
|---|---------|---------------|-------|
| 7 | Warm-starting via `enqueue_trial` com defaults | Dá ao TPE um baseline conhecido desde o início em vez de random puro. ~10 linhas, custo zero | Claude, Gemini, Minimax |
| 8 | Convergence monitoring (parada antecipada) | Se `best_score` não melhorar por 5 rounds consecutivos, para. Economiza horas se MACRO convergir cedo | Qwen, Minimax |

Flags adicionadas ao orchestrator:
- `--no-enqueue-defaults`: desabilita warm-starting (para testes controlados)
- `--convergence-rounds N`: rounds sem melhoria antes de parar (default: 5, 0 = desabilitado)

### 16.4 Smoke Test

Rodar **5 trials** (1 round de 5 containers) antes da calibração real para validar end-to-end:
- Docker, Optuna DB, scoring, resume
- Testar `--resume` (matar processo e restartar)
- ~5.7h (mesmo tempo de 1 round MACRO)

### 16.5 Sugestões Descartadas

| Sugestão | Por que não | Fonte |
|---------|-----------|-------|
| Holdout validation set | Validação já planejada como experimento separado (169 APKs, 3 reps, 10min) | Todas |
| Adicionar params RVSmart do Config.java | Não se aplicam ao APE-RV SATA variants | Minimax |
| Multi-objective (Pareto) | Overengineering para primeira calibração | Claude, Minimax |
| SMAC3 / CMA-ES / BoTorch | Infraestrutura Optuna já existe e funciona | Gemini, Minimax |
| Multi-fidelity (timeout curto como proxy) | Precisa validar correlação — para futuro | Claude |
| WilcoxonPruner | Requer mudança arquitetural no orchestrator (score por APK) — para futuro | Claude |
| Aumentar para 200 trials MACRO | 130 trials com 9.3× já é suficiente | Minimax |

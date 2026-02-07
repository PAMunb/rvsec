# RVAgent Calibration and Validation Framework

**Data**: 2026-02-02 (atualizado 2026-02-07)
**Status**: Calibração Micro em execução (Fase D) - Modo multimode com LLM
**Objetivo**: Criar framework de validacao e calibracao automatizada para RVAgent superar APE e FastBot

## Próximo Passo: Fase D - Calibração Micro (EM EXECUÇÃO)

**Fase D (Calibração Micro) iniciada** (2026-02-07):
- **Modo**: `multimode` (híbrido LLM + algoritmo) — diferente da macro que usou `pure_algorithm`
- **Trials**: 80 (estimativa: ~3.9 dias)
- **Parâmetros**: 17 (16 numéricos + 1 categórico `prompt_version`)
- **Timeout**: 300s/APK (mesmo do baseline para comparabilidade)
- **SGLang**: Qwen3-VL-4B-Instruct em 192.168.0.36:30000
- **Parâmetros macro fixados** do Trial #33 da Fase C
- **Resultados parciais**: `./results/calibration_micro/`

**Decisão importante (2026-02-07)**: Migrar de `pure_algorithm` para `multimode` na fase micro.
A fase macro original usava `pure_algorithm` para calibrar os 8 parâmetros de scoring.
A fase micro inclui 5 parâmetros LLM (`llm_probability`, `llm_temperature`, `llm_top_p`, `llm_top_k`, `llm_max_retries`)
que só são exercitados em `multimode`. Rodar em `pure_algorithm` significaria calibrar esses parâmetros "às cegas".
Adicionalmente, `prompt_version` (v13, v14, v15, v16) foi incluído como parâmetro categórico.

**Ranges ampliados para exploração (LLM)**:
| Parâmetro | Range original | Range atual | Justificativa |
|-----------|---------------|-------------|---------------|
| `llm_probability` | 0.0—1.0 | 0.1—0.9 | 0% e 100% não fazem sentido em multimode |
| `llm_temperature` | 0.001—0.3 | 0.001—0.9 | Testar se criatividade melhora exploração |
| `llm_top_p` | 0.3—0.9 | 0.1—0.99 | Explorar extremos de sampling |
| `llm_top_k` | 20—80 | 10—100 | Explorar extremos de diversidade |
| `prompt_version` | — (fixo v13) | v13, v14, v15, v16 | Novo parâmetro categórico |

**Fase C (Calibração Macro) concluída com sucesso** (2026-02-06):
- 50/50 trials completados em ~52.5 horas
- Best trial: #33 com score 62.14
- Cobertura: 22.1% → 24.3% (+2.2%)
- Resultados em: `./results/calibration_macro/`

**Fase B (Baseline) concluída** (2026-02-02):
- 135/135 tasks executadas (3 tools × 15 APKs × 3 repetições)
- Resultados em: `./results/baseline/cli_experiment_20260202_152204_8c8a2811/`

### Resultados do Baseline

| Métrica | APE | FastBot | RVAgent | Observação |
|---------|-----|---------|---------|------------|
| cov_method médio | 26.7% | 21.2% | 19.3% | APE lidera |
| cov_act médio | 73.0% | 75.6% | 63.0% | FastBot lidera |
| Erros MOP total | 48 | 43 | 43 | APE detecta mais |
| Max errors/run | 5 | 5 | 5 | openpass |

**BASELINE_MAX_ERRORS = 5** (usado para normalização adaptativa na função objetivo)

### Resultados da Calibração Macro (Fase C)

**Parâmetros Otimizados (Trial #33, Score 62.14)**:

| Parâmetro | Default | Otimizado | Variação |
|-----------|---------|-----------|----------|
| mop_direct_score | 300.0 | 473.51 | +58% |
| wtg_guided_score | 250.0 | 359.64 | +44% |
| unsaturated_bonus | 80.0 | 48.15 | -40% |
| max_re_enables | 6 | 3 | -50% |
| ui_coverage_threshold | 0.9 | 0.86 | -4% |
| stochastic_probability | 0.3 | 0.55 | +83% |
| strength_weight | 50.0 | 62.22 | +24% |
| visitation_penalty_factor | -10.0 | -13.20 | +32% |

**Insights da Calibração**:
1. **MOP Prioritization aumentada**: mop_direct_score +58% indica que priorizar métodos MOP melhora cobertura
2. **WTG Guidance aumentada**: wtg_guided_score +44% confirma valor da análise estática
3. **Exploração mais estocástica**: stochastic_probability de 0.3→0.55 indica benefício de aleatoriedade
4. **Menos re-enables**: max_re_enables de 6→3 sugere exploração mais profunda antes de revisitar
5. **Penalidade de visitação maior**: -10→-13.2 evita loops em estados já explorados

**Melhoria de Cobertura**:
- Baseline RVAgent: 22.1%
- Calibrado (Trial #33): 24.3%
- Ganho: +2.2% absoluto (+10% relativo)

### Apps onde RVAgent precisa melhorar (oportunidades):

| APK | APE cov | RVAgent cov | Gap |
|-----|---------|-------------|-----|
| hashpass | 33.3% | 14.3% | -19% |
| tramhunter | 22.9% | 7.0% | -16% |
| yaab | 30.9% | 13.7% | -17% |
| classic | 33.0% | 15.2% | -18% |
| darknessimmunity | 41.9% | 31.3% | -11% |

### Apps onde RVAgent já compete:

| APK | APE cov | RVAgent cov | Obs |
|-----|---------|-------------|-----|
| blippex | 24.5% | 24.3% | Empate |
| openpass | 31.9% | 39.1% | RVAgent vence |
| verbisteandroid | 32.0% | 32.0% | Empate |
| diceware | 36.8% | 34.7% | Próximo |

**Executar Calibração Micro** (estimativa: ~93 horas / ~3.9 dias):
```bash
# Requer SGLang server rodando em 192.168.0.36:30000
# O script verifica automaticamente antes de iniciar

# Usar o script (recomendado)
./run_calibration_micro.sh

# Resume (se interrompido)
./run_calibration_micro.sh --resume
```

O estado da calibração é persistido em SQLite (`optuna_study.db`).

**Cálculo de tempo**: 80 trials × 10 APKs × ~7 min/run = ~93 horas (~3.9 dias)
**Justificativa 80 trials**: 17 parâmetros (16 numéricos + 1 categórico), modo multimode com LLM
**Justificativa multimode**: Parâmetros LLM (probability, temperature, top_p, top_k) e prompt_version só são exercitados em multimode

---

### Fase C Concluída - Resultados da Calibração Macro

**Script utilizado**: `./run_calibration_macro.sh`

**Resultado**: 50/50 trials em ~52.5 horas. Melhores parâmetros salvos em:
- `./results/calibration_macro/optimal_params.json`
- `./results/calibration_macro/param_string.txt`

**Diretórios de dados**:
- `calibration_dataset/` - 15 APKs (todos)
- `calibration_set/` - 10 APKs (para calibração)
- `holdout_set.txt` - 5 APKs para validação final (copiar de calibration_dataset quando necessário)

---

## Regras de Implementacao

1. **Simplicidade**: Codigo simples e elegante, sem complexidades desnecessarias
2. **Sem codigo legado**: Alteracoes completas, sem adapters ou shims de compatibilidade
3. **Backup**: Mover arquivos antigos para `backup/` antes de substituir
4. **Comentarios**: Refletem estado atual apenas, sem referencias a migracao ou "o que foi feito"
5. **Sem vies**: Nao usar termos como "moderno", "sofisticado", "elegante" em comentarios
6. **Publico-alvo**: Desenvolvedores e pesquisadores - sem linguagem promocional

## Objetivo

Criar um framework sistematico e automatizado de validacao e calibracao para o RVAgent, visando atingir metricas de cobertura superiores ao APE e FastBot.

## Metricas a Otimizar

1. **Method Coverage** (primaria) - % de metodos do app executados
2. **MOP Errors Detected** (critica) - quanto mais melhor, indica caminhos de codigo security-relevant alcancados
3. **UI Coverage** (secundaria) - % de elementos UI interagidos (via UI tracker)
4. **cov_rv_method** - Cobertura de metodos RV (metodos que alcancam operacoes monitoradas)

## Dataset Preparado (Fase 0 - CONCLUIDA)

**Decisao**: Usar dataset existente do experimento anterior.

**Localizacao**: `results/cli_experiment_20260201_122731_f9e9f5a4/instrumented_apks/`

### APKs Validos (15 APKs)

Todos os APKs abaixo possuem os 3 arquivos de analise estatica (.gesda, .wtg, .reach) com conteudo valido:

```
biz.gyrus.yaab_30.apk
byrne.utilities.hashpass_2.apk
ca.farrelltonsolar.classic_314.apk
com.aidinhut.simpletextcrypt_14.apk
com.allansimon.verbisteandroid_2.apk
com.andybotting.tramhunter_1300.apk
com.aptasystems.dicewarepasswordgenerator_8.apk
com.blippex.app_5.apk
com.crazyhitty.chdev.ks.munch_14.apk
com.example.openpass_1.apk
com.example.root.analyticaltranslator_6.apk
com.freezingwind.animereleasenotifier_9.apk
com.github.axet.darknessimmunity_28.apk
com.koushikdutta.superuser_1030.apk
com.linuxcounter.lico_update_003_8.apk
```

### APKs Invalidos (3 APKs - arquivo .reach vazio)

```
com.Bisha.TI89EmuDonation_1133.apk
com.easytarget.micopi_32.apk
com.euedge.openaviationmap.android_16.apk
```

### Divisao do Dataset (Prevenir Overfitting)

**Importante**: Para evitar overfitting, o dataset deve ser dividido em:

1. **Calibration Set (10 APKs)** - Usado nas Fases C e D para otimizacao Optuna
2. **Hold-out Validation Set (5 APKs)** - Usado APENAS na Fase E para validacao final

**Calibration Set (10 APKs)**:
```
byrne.utilities.hashpass_2.apk
com.allansimon.verbisteandroid_2.apk
com.andybotting.tramhunter_1300.apk
com.aptasystems.dicewarepasswordgenerator_8.apk
com.blippex.app_5.apk
com.example.openpass_1.apk
com.example.root.analyticaltranslator_6.apk
com.freezingwind.animereleasenotifier_9.apk
com.koushikdutta.superuser_1030.apk
com.linuxcounter.lico_update_003_8.apk
```

**Hold-out Validation Set (5 APKs)** - NAO usar na calibracao:
```
biz.gyrus.yaab_30.apk
ca.farrelltonsolar.classic_314.apk
com.aidinhut.simpletextcrypt_14.apk
com.crazyhitty.chdev.ks.munch_14.apk
com.github.axet.darknessimmunity_28.apk
```

### Criterios de Validacao

- Arquivo `.gesda` presente e nao-vazio
- Arquivo `.wtg` presente e nao-vazio
- Arquivo `.reach` presente e nao-vazio (critico para priorizacao MOP)

## Visao Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│ FASE 0: PRE-PROCESSAMENTO - CONCLUIDA                           │
│                                                                  │
│  Dataset ja disponivel em:                                      │
│  results/cli_experiment_20260201_122731_f9e9f5a4/instrumented_apks/│
│                                                                  │
│  Conteudo:                                                      │
│  - 15 APKs instrumentados com monitores JCA                     │
│  - *.wtg, *.gesda, *.reach (analise estatica validada)          │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ FASES 1-N: TRIALS DE CALIBRACAO (Executar MUITAS via rv-experiment)│
│                                                                  │
│  rv-experiment run                                              │
│    --tools rvagent:pure_algorithm@mop_direct_score=300,...      │
│    --apks-dir ./calibration_dataset                             │
│    --skip-monitors --skip-instrument --skip-static              │
│    --timeout 300 --output-dir ./calibration/trial_N             │
│                                                                  │
│  Para cada trial:                                               │
│  1. Optuna sugere valores de parametros                         │
│  2. Parametros passados via DSL de especificacao de tool        │
│  3. rv-experiment executa (sem preprocessing, apenas execucao)  │
│  4. Parse summary.csv para metricas (cov_method, errors)        │
│  5. Reporta score de volta ao Optuna                            │
└─────────────────────────────────────────────────────────────────┘
```

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
            # Pesos dos scorers (precisam ser adicionados)
            "mop_direct_score": 300.0,
            "wtg_guided_score": 250.0,
            ...
        }
    )
]
```

**Arquivos a modificar** para suportar calibracao de pesos dos scorers:

1. `modules/rvagent-tool/src/rvagent_tool/tools/rvagent/config.py`:
   - Adicionar parametros de pesos dos scorers ao mapeamento

2. `modules/rv-agent/src/rv_agent/config/agent_config.py`:
   - Adicionar campos de pesos dos scorers ao RVAgentConfig

3. `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ranking/scorers.py`:
   - Aceitar valores de config ao inves de constantes de classe

## Plano de Implementacao

### Task 1: Estender RVAgentConfig para Pesos dos Scorers

**Arquivo**: `modules/rv-agent/src/rv_agent/config/agent_config.py`

Adicionar novos campos:
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

Mudar de constantes de classe para variaveis de instancia:
```python
class MopScorer(ActionScorer):
    def __init__(self, config: RVAgentConfig):
        self.direct_score = config.mop_direct_score
        self.transitive_score = config.mop_transitive_score
```

### Task 3: Atualizar Mapeamento de Config do rvagent-tool

**Arquivo**: `modules/rvagent-tool/src/rvagent_tool/tools/rvagent/config.py`

Adicionar parametros dos scorers ao mapeamento:
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

### Task 4: Criar Modulo de Calibracao

**Localizacao**: `modules/rv-agent-validation/src/rv_agent_validation/calibration/`

**Novos arquivos**:
- `parameter_space.py` - Definir 24 parametros tuneaveis com ranges
- `objective.py` - Scoring composto (method_coverage + errors + ui_coverage)
- `optimizer.py` - Wrapper Optuna com TPESampler
- `runner.py` - Orquestra trials de calibracao via rv-experiment
- `cli.py` - Comandos CLI (calibrate, compare)

### Task 5: ~~Criar Dataset Preparado~~ - CONCLUIDA

**Status**: Ja disponivel do experimento anterior.

**Dataset**: `results/cli_experiment_20260201_122731_f9e9f5a4/instrumented_apks/`

**APKs validos**: 15 (listados na secao "Dataset Preparado" acima)

Para usar o dataset nos trials de calibracao:
```bash
# Variavel com caminho do dataset
CALIBRATION_DATASET="results/cli_experiment_20260201_122731_f9e9f5a4/instrumented_apks"

# Executar trial de calibracao
poetry run rv-experiment run \
  --tools "rvagent:pure_algorithm@mop_direct_score=400" \
  --apks-dir $CALIBRATION_DATASET \
  --skip-monitors --skip-instrument --skip-static \
  --timeout 300
```

### Task 6: Implementar Calibration Runner

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
            "poetry", "run", "rv-experiment", "run",
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

## Funcao Objetivo

**Decisao**: Objetivo balanceado (50% cobertura + 50% erros)

```python
import pandas as pd
import logging

# Baseline de erros maximo (calculado na Fase B)
# Usado para normalizacao adaptativa
BASELINE_MAX_ERRORS = None  # Sera preenchido apos Fase B

def compute_objective_score(results_dir: str) -> float:
    """
    Computa score objetivo para um trial de calibracao.

    Tratamento robusto de erros para trials que falham.
    """
    try:
        summary = pd.read_csv(f"{results_dir}/summary.csv")
    except FileNotFoundError:
        logging.warning(f"summary.csv nao encontrado em {results_dir}")
        return 0.0
    except Exception as e:
        logging.warning(f"Erro ao ler summary.csv: {e}")
        return 0.0

    if summary.empty:
        logging.warning(f"summary.csv vazio em {results_dir}")
        return 0.0

    # Media entre todos os APKs
    avg_method_cov = summary['cov_method'].mean()  # 0-100%
    avg_errors = summary['errors'].mean()          # Contagem bruta

    # Normalizacao adaptativa de erros
    # Usa maximo do baseline (calculado na Fase B) ao inves de valor arbitrario
    if BASELINE_MAX_ERRORS and BASELINE_MAX_ERRORS > 0:
        normalized_errors = min((avg_errors / BASELINE_MAX_ERRORS) * 100, 100)
    else:
        # Fallback: assumir max ~10 erros por app
        normalized_errors = min(avg_errors * 10, 100)

    # OBJETIVO BALANCEADO: 50% cobertura + 50% erros
    score = (
        0.50 * avg_method_cov +       # 50% peso em cobertura de metodos
        0.50 * normalized_errors       # 50% peso em erros MOP detectados
    )

    return score
```

**Notas**:
- Maior contagem de erros e MELHOR - indica que mais operacoes monitoradas foram disparadas e violacoes detectadas
- Normalizacao adaptativa usa maximo do baseline (APE/FastBot) para escala mais precisa
- Tratamento robusto de erros para trials que falham

## Espaco de Parametros (24 parametros)

### Parametros Macro (Fase 1 - 8 params)
| Parametro | Default | Range | Impacto |
|-----------|---------|-------|---------|
| mop_direct_score | 300.0 | 200-500 | Priorizacao de metodos MOP |
| wtg_guided_score | 250.0 | 100-400 | Guia de navegacao WTG |
| unsaturated_bonus | 80.0 | 40-120 | Diversidade de estados |
| max_re_enables | 6 | 3-15 | Profundidade de exploracao de successors |
| coverage_threshold | 0.9 | 0.7-1.0 | Trigger de re-enable |
| stochastic_probability | 0.3 | 0.1-0.7 | Aleatoriedade de exploracao |
| strength_weight | 50.0 | 25-100 | Sucesso historico de acoes |
| visitation_penalty_factor | -10.0 | -20 a -5 | Penalidade para over-visited |

### Parametros Micro (Fase 2 - 17 params: 16 numéricos + 1 categórico)

**Modo de execução**: `multimode` (híbrido LLM + algoritmo)

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

## Workflow de Calibracao

### Fase A: ~~Preparar Dataset~~ - CONCLUIDA

**Dataset ja disponivel**: `results/cli_experiment_20260201_122731_f9e9f5a4/instrumented_apks/`

- 15 APKs instrumentados com monitores JCA
- Arquivos de analise estatica validados (.gesda, .wtg, .reach)

```bash
# IMPORTANTE: Definir RVSEC_HOME (necessario para carregar analise estatica)
export RVSEC_HOME="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec"

# Definir variavel de ambiente para uso nos comandos seguintes
export CALIBRATION_DATASET="modules/rv-agent-validation/data/calibration_dataset"

# Verificar dataset
ls $CALIBRATION_DATASET/*.apk   # 15 APKs instrumentados
ls $CALIBRATION_DATASET/*.wtg   # Arquivos WTG
ls $CALIBRATION_DATASET/*.reach # Analise REACH
```

### Fase B: Comparacao Baseline (14-15 horas)
```bash
# IMPORTANTE: RVSEC_HOME necessário para carregar dados de análise estática
export RVSEC_HOME="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec"

# Executar APE, FastBot, RVAgent nos mesmos APKs (sem preprocessing)
# 3 repetições para melhor significância estatística
# Output redirecionado para arquivo de log
poetry run rv-experiment run \
  --tools ape,fastbot,rvagent:pure_algorithm \
  --apks-dir $CALIBRATION_DATASET \
  --skip-monitors --skip-instrument --skip-static \
  --timeout 300 \
  --repetitions 3 \
  --output-dir ./results/baseline \
  2>&1 | tee ./results/baseline_$(date +%Y%m%d_%H%M%S).log
```

### Fase C: Calibracao Macro (24-48 horas)
```bash
# Usar apenas CALIBRATION_SET (10 APKs) - NAO usar hold-out set
# Seed fixo para reprodutibilidade
poetry run python -m rv_agent_validation calibrate \
  --apks-dir $CALIBRATION_DATASET \
  --apks-filter calibration_set.txt \
  --phase macro \
  --n-trials 50 \
  --timeout 300 \
  --seed 42 \
  --output ./calibration_macro

# Isso internamente executa rv-experiment com skip flags para cada trial
```

### Fase D: Calibracao Micro em Multimode (~93 horas / ~3.9 dias)

**Mudanças em relação ao plano original**:
- Modo: `pure_algorithm` → `multimode` (para exercitar parâmetros LLM)
- Parâmetros: 16 → 17 (adicionado `prompt_version` categórico)
- Trials: 50 → 80 (espaço de busca maior requer mais exploração)
- Ranges LLM ampliados (temperature até 0.9, top_p até 0.99)
- Requer SGLang server (Qwen3-VL) rodando

```bash
# Usar apenas CALIBRATION_SET (10 APKs) - NAO usar hold-out set
# 80 trials para 17 params (16 numéricos + 1 categórico)
# Modo multimode para calibrar parâmetros LLM de forma efetiva
# Requer: SGLang server em 192.168.0.36:30000

# Via script (recomendado)
./run_calibration_micro.sh

# Ou manualmente:
poetry run python -m rv_agent_validation calibrate \
  --apks-dir "$CALIBRATION_SET" \
  --phase micro \
  --n-trials 80 \
  --timeout 300 \
  --seed 42 \
  --agent-mode multimode \
  --best-macro ./results/calibration_macro/optimal_params.json \
  --baseline-dir ./results/baseline/cli_experiment_20260202_152204_8c8a2811 \
  --output ./results/calibration_micro
```

**Cálculo de tempo**: 80 trials × 10 APKs × ~7 min/run = ~93 horas (~3.9 dias)

### Fase E: Validacao Final (12-16 horas)
```bash
# IMPORTANTE: Usar HOLD-OUT SET (5 APKs) para validacao final
# Isso prova que os parametros generalizam alem do dataset de calibracao
# 3 repetições para significância estatística
poetry run rv-experiment run \
  --tools "ape,fastbot,rvagent:pure_algorithm@$(cat ./calibration_micro/param_string.txt)" \
  --apks-dir $CALIBRATION_DATASET \
  --apks-filter holdout_set.txt \
  --skip-monitors --skip-instrument --skip-static \
  --timeout 600 \
  --repetitions 3 \
  --output-dir ./results/validation_holdout

# Tambem executar no calibration set para comparacao completa
poetry run rv-experiment run \
  --tools "ape,fastbot,rvagent:pure_algorithm@$(cat ./calibration_micro/param_string.txt)" \
  --apks-dir $CALIBRATION_DATASET \
  --apks-filter calibration_set.txt \
  --skip-monitors --skip-instrument --skip-static \
  --timeout 600 \
  --repetitions 3 \
  --output-dir ./results/validation_calibration
```

## Selecao de Dataset

**Decisao**: Usar todos os 15 APKs validos do experimento anterior

### Caracteristicas do Dataset (de `results/cli_experiment_20260201_122731_f9e9f5a4/summary.csv`):

**Apps com erros MOP detectados** (bons para calibracao de deteccao de erros):
| APK | Erros APE | Erros RVAgent |
|-----|-----------|---------------|
| byrne.utilities.hashpass_2.apk | 3 | 0 |
| com.allansimon.verbisteandroid_2.apk | 2 | 2 |
| com.example.openpass_1.apk | 5 | 5 |
| com.blippex.app_5.apk | 3 | 0 |
| com.aptasystems.dicewarepasswordgenerator_8.apk | 2 | 2 |
| com.example.root.analyticaltranslator_6.apk | 2 | 2 |
| com.freezingwind.animereleasenotifier_9.apk | 2 | 2 |
| com.linuxcounter.lico_update_003_8.apk | 2 | 0 |

**Apps onde RVAgent perde em cobertura** (espaco para melhoria):
| APK | cov_method APE | cov_method RVAgent |
|-----|----------------|-------------------|
| byrne.utilities.hashpass_2.apk | 38.1% | 14.3% |
| com.andybotting.tramhunter_1300.apk | 29.0% | 12.1% |
| com.linuxcounter.lico_update_003_8.apk | 33.3% | 13.1% |
| com.blippex.app_5.apk | 31.9% | 23.9% |

**Apps onde RVAgent ja performa bem** (garantir nao regressao):
| APK | cov_method APE | cov_method RVAgent |
|-----|----------------|-------------------|
| com.aptasystems.dicewarepasswordgenerator_8.apk | 37.9% | 42.1% |
| com.example.openpass_1.apk | 41.3% | 42.8% |

## Criterios de Sucesso

**No Calibration Set (10 APKs)**:
1. **Method Coverage**: RVAgent > APE em agregado (target: >30% media)
2. **MOP Errors**: RVAgent detecta MAIS erros que APE/FastBot
3. **Win Rate**: RVAgent vence >70% dos APKs em comparacoes pareadas
4. **Composite Score**: RVAgent calibrado supera baseline em >10%

**No Hold-out Validation Set (5 APKs)** - CRITICO:
5. **Generalizacao**: RVAgent mantem vantagem sobre APE no hold-out set
6. **Sem Overfitting**: Performance no hold-out >= 80% da performance no calibration set

**Ambos os Sets**:
7. **Significancia Estatistica**: p < 0.05 (teste Wilcoxon signed-rank)
8. **Sem Regressoes**: Nenhum APK onde RVAgent performa >20% pior que baseline

## Arquivos a Criar/Modificar

### Novos Arquivos
- `modules/rv-agent-validation/src/rv_agent_validation/calibration/__init__.py`
- `modules/rv-agent-validation/src/rv_agent_validation/calibration/parameter_space.py`
- `modules/rv-agent-validation/src/rv_agent_validation/calibration/objective.py`
- `modules/rv-agent-validation/src/rv_agent_validation/calibration/optimizer.py`
- `modules/rv-agent-validation/src/rv_agent_validation/calibration/runner.py`
- `modules/rv-agent-validation/src/rv_agent_validation/calibration/cli.py`

### Arquivos a Modificar
- `modules/rv-agent/src/rv_agent/config/agent_config.py` - Adicionar campos de pesos dos scorers
- `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ranking/scorers.py` - Usar valores de config
- `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/rvagent_strategy.py` - Passar config para scorers
- `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/successor_tracker.py` - Usar valores de config
- `modules/rvagent-tool/src/rvagent_tool/tools/rvagent/config.py` - Mapear params dos scorers
- `modules/rv-agent-validation/pyproject.toml` - Adicionar dependencia optuna
- `modules/rv-agent-validation/src/rv_agent_validation/__main__.py` - Adicionar comando calibrate

## Verificacao

1. **Testes unitarios**: Testar passagem de parametros pelo fluxo de config
2. **Teste de integracao**: Executar trial unico de calibracao, verificar params aplicados
3. **Smoke test**: Executar mini calibracao de 3 trials em 2 APKs
4. **Validacao completa**: Comparar RVAgent calibrado vs APE/FastBot

```bash
# Definir dataset
export CALIBRATION_DATASET="modules/rv-agent-validation/data/calibration_dataset"

# Testar fluxo de parametros
cd modules/rv-agent
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/unit/test_agent_config.py -v

# Teste de integracao com rv-experiment (1 APK apenas para teste rapido)
# Nota: usar um APK pequeno como com.aidinhut.simpletextcrypt_14.apk
poetry run rv-experiment run \
  --tools "rvagent:pure_algorithm@mop_direct_score=400" \
  --apks-dir $CALIBRATION_DATASET \
  --skip-monitors --skip-instrument --skip-static \
  --timeout 60 \
  --output-dir ./test_calibration

# Verificar que parametros foram aplicados
cat ./test_calibration/summary.csv
```

## Dependencias a Adicionar

```toml
# modules/rv-agent-validation/pyproject.toml
[tool.poetry.dependencies]
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
        study_name="rvagent_calibration"
    )
```

### Seed Support em rv-agent (Implementado 2026-02-02)

O seed e propagado do CLI de calibracao ate o rv-agent para garantir reproducibilidade total:

```
CLI --seed 42 → CalibrationRunner.seed → params["seed"] → tool_spec → rv-experiment → rvagent-tool → RVAgentConfig.seed → random.seed()
```

**Arquivos modificados**:
- `modules/rv-agent/src/rv_agent/config/agent_config.py` - Campo `seed: Optional[int]`
- `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/rvagent_strategy.py` - `random.seed(config.seed)`
- `modules/rv-agent/src/rv_agent/routing/routing_manager.py` - `random.seed(config.seed)`
- `modules/rv-agent/src/rv_agent/strategies/strategy_registry.py` - `random.seed(config.seed)`
- `modules/rv-agent-validation/src/rv_agent_validation/calibration/runner.py` - Passa seed via tool spec
- `modules/rv-agent-validation/src/rv_agent_validation/calibration/cli.py` - Passa seed ao runner

**Notas**:
- Seed 42 usado como padrao para reproducao de resultados
- Resultados serao identicos se executados com mesmos parametros e seed
- Logs de cada trial incluem parametros para auditoria

## Timeline Estimado

| Fase | Duracao | Descricao | Status |
|------|---------|-----------|--------|
| Prep Dataset | ~~1 dia~~ | Dataset de APKs instrumentados | ✅ CONCLUIDA |
| Implementacao | 2-3 dias | Mudancas de codigo (Tasks 1-4, 6) | ✅ CONCLUIDA |
| Smoke Test | 15 min | 3 trials em 2 APKs | ✅ CONCLUIDA (2026-02-02) |
| Baseline (B) | 14-15 horas | Executar comparacao APE/FastBot/RVAgent (3 reps) | ✅ CONCLUIDA (2026-02-02) |
| Calibração Macro (C) | ~52.5 horas | 50 trials em params macro, pure_algorithm (10 APKs) | ✅ CONCLUIDA (2026-02-06) |
| **Calibração Micro (D)** | **~93 horas** | **80 trials, 17 params, multimode com LLM (10 APKs)** | 🔄 **EM EXECUÇÃO** (2026-02-07) |
| Validação (E) | 12-16 horas | Comparacao final no hold-out set (3 reps) | ⏳ Pendente |
| **Total** | **~4-5 dias restantes** | | |

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

### Task 4: Criar Modulo de Calibracao
- [x] 4.1 Criar `parameter_space.py`
- [x] 4.2 Criar `objective.py` (com tratamento robusto de erros)
- [x] 4.3 Criar `optimizer.py` (Optuna wrapper com seed para reprodutibilidade)
- [x] 4.4 Criar `runner.py` (CalibrationRunner)
- [x] 4.5 Criar `cli.py` (comando calibrate com --seed)
- [x] 4.6 Adicionar dependencia optuna ao pyproject.toml

### Task 5: Dataset Preparado
- [x] 5.1 Dataset disponivel (15 APKs validos)
- [x] 5.2 Criar calibration_set.txt (10 APKs)
- [x] 5.3 Criar holdout_set.txt (5 APKs)
- [x] 5.4 Copiar APKs e arquivos de analise estatica para rv-agent-validation/data/

### Task 6: Validacao
- [x] 6.1 Testes unitarios passando
- [x] 6.2 Teste de integracao (1 trial com parametro customizado)
- [x] 6.3 Smoke test (3 trials em 2 APKs) - **Concluido 2026-02-02**
  - 3 trials executados com sucesso
  - Score: 7.38 (14.8% coverage, 0 MOP errors)
  - Resultados em: `modules/rv-agent-validation/results/smoke_test_calibration/`
- [ ] 6.4 Validar no hold-out set (generalizacao)

---

## Referencias

- Documentos anteriores de validacao:
  - `docs/20260115_rvagent_validacao_multimodal.md`
  - `docs/20260105_rvagent_validacao.md`
  - `docs/20251231_rvagent_validacao.md`
- Modulo rv-agent-validation existente: `modules/rv-agent-validation/`
- Experimento recente: `results/cli_experiment_20260201_122731_f9e9f5a4/`

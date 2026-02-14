# Validacao RV-Agent - Metodologia Revisada (3 Fases)

**Data**: 19/01/2026 (revisao)
**Status**: EM REVISAO - Descoberta critica sobre static analysis
**Referencia**: `docs/20260113_rvagent_validacao_multimodal.md` (infraestrutura e dataset)

---

## DESCOBERTA CRITICA (19/01/2026)

**Problema**: Todos experimentos anteriores rodaram com `enable_static_analysis: false`.

**Impacto por estrategia**:

| Estrategia | Uso de Static Analysis | Impacto sem SA |
|------------|------------------------|----------------|
| **rvagent** | MopScorer (+100/+50) + WtgScorer (+100) | **MAIOR IMPACTO** - perde 2 scorers principais |
| **dfs** | `_get_mop_priority()` como tiebreaker | Medio - perde priorizacao MOP |
| **bfs** | `_get_mop_priority()` como tiebreaker | Medio - perde priorizacao MOP |
| **greedy** | `_get_mop_priority()` como tiebreaker | Medio - perde priorizacao MOP |

**Conclusao**: Precisamos medir o impacto real da analise estatica em todas as fases. Nova metodologia inclui `static_analysis` como variavel experimental.

---

## Regras de Implementacao

1. **Simplicidade**: Sistema simples e elegante, sem complexidades desnecessarias, seguindo boas praticas.

2. **Sem codigo legado**: Todas alteracoes realizadas, sem adapters de compatibilidade. Codigo legado removido/sobrescrito. Arquivos antigos em `backup/`.

3. **Comentarios**: Refletir apenas estado atual. Sem mencoes a migracao/fases/legado. Sem linguagem promocional ou termos de vies.

4. **Sempre usar uv**: Todos os comandos Python devem ser executados via `uv run` dentro do diretorio do modulo.

---

## Resumo Executivo

Nova metodologia de validacao em 3 fases sequenciais, com **static analysis como variavel experimental**:

| Fase | Objetivo | Variaveis | Configs | Runs | Timeout | Tempo |
|------|----------|-----------|---------|------|---------|-------|
| **1. Algoritmos** | Estrategia + Static | 4 strategies × 2 static | 8 | 360 | 180s | ~21h |
| **2. Prompts + Params** | Prompt + Params + Static | 2 prompts × 3 params × 2 static | 12 | 540 | 180s | ~32h |
| **3. Multimode** | Proporcoes + Static | 4 proporcoes × 2 static | 8 | 360 | 300s | ~33h |
| **TOTAL** | | | | **1260** | | **~86h** |

**Tempo total**: ~3.5 dias de execucao continua.
**Nota**: Tempo inclui overhead de ~30s por run (install, cleanup, etc).

**Nota sobre Timeouts**:
- Fases 1 e 2: 180s (3 min) - validacao rapida; se igualar/superar baseline (5 min), ja eh bom sinal
- Fase 3: 300s (5 min) - comparavel com experimentos anteriores de outras ferramentas

**Parametros Fixos**:
- **Apps**: 15 APKs instrumentados (ver Secao 5)
- **Seeds**: 3 (42, 123, 456)
- **Timeout**: variavel por fase (ver tabela acima)

---

## 0. Fase 0: Pre-Calibracao de Scores (CONCLUIDA)

### 0.1 Objetivo

Calibrar os scores de prioridade dos componentes UI usando dados reais de apps Android.

### 0.2 Dataset de Calibracao

```
/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/
├── 14 apps diferentes
├── 255 telas (screenshots + UI dumps)
└── 35 tipos de componentes identificados
```

### 0.3 Script de Calibracao

```bash
cd modules/rv-agent-validation
python scripts/calibrate_scores.py \
  --dataset /home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots \
  --output data/scores_config.json \
  --generate-code
```

### 0.4 Resultados da Calibracao

| Componente | Score | Clickable% | Justificativa |
|------------|-------|------------|---------------|
| **Spinner** | **80.0** | 100% | Revela opcoes ocultas (dropdown) |
| **Button** | 55.0 | 100% | Acoes primarias |
| **ImageButton** | 54.4 | 97% | Navegacao e acoes |
| **EditText** | 50.0 | 100% | Inputs de formulario |
| **DrawerLayout** | 50.0 | - | Menu de navegacao |
| CheckBox | 45.0 | 100% | Toggle de estado |
| Switch | 45.0 | 100% | Toggle de configuracoes |
| RadioButton | 39.0 | 100% | Selecao de opcoes |
| ViewPager | 38.5 | 93% | Navegacao de telas |
| RecyclerView | 31.1 | 56% | Listas de conteudo |
| CheckedTextView | 25.0 | 75% | Itens selecionaveis |

### 0.5 Implementacao

Novo scorer `ComponentPriorityScorer` em:
```
modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ranking/scorers.py
```

**Sistema de Scoring Final**:

| Scorer | Score | Condicao |
|--------|-------|----------|
| UntestedScorer | +200 | Elemento nunca testado |
| ComponentPriorityScorer | +25 a +80 | Tipo de componente |
| MopScorer | +100/+50 | Alcanca operacoes monitoradas |
| WtgScorer | +100 | Guiado por WTG (quando ativo) |
| ExecutionCountScorer | +10/(1+n) | Inverso do contador de execucao |
| FailedActionScorer | -9999 | Acao que falhou previamente |

**Exemplo de Score Final** (Spinner untested):
```
290 = 200 (untested) + 80 (component) + 10 (exec)
```

### 0.6 Arquivos Gerados

| Arquivo | Descricao |
|---------|-----------|
| `data/scores_config.json` | Configuracao de scores calibrados |
| `data/scores_config.py` | Codigo Python do scorer |
| `scripts/calibrate_scores.py` | Script de calibracao |

### 0.7 Bug Fix: Auto-Load de Static Data

Corrigido bug onde static data (WTG) era carregado automaticamente do diretorio APK mesmo com `use_wtg: false`.

**Alteracao em `runner.py`**:
```python
disable_autoload = (
    wtg_variant == "without_wtg" or
    (wtg_variant is None and not config.use_wtg)
)
```

---

## 0.8 Mini Experimento: Calibracao de Prioridades

**Status**: CONCLUIDO
**Data Inicio**: 16/01/2026 06:15
**Data Conclusao**: 16/01/2026 ~12:00
**Duracao**: ~6h (9 APKs × 8 seeds × 300s = 72 runs)

### 0.8.1 Problema Identificado (Validacao Inicial)

Experimento de validacao inicial (5 APKs × 1 seed × 180s) mostrou:
- **UI coverage baixa**: 17-41%
- **Alta taxa de repeticao**: ate 64.83%
- **30+ elementos nao testados** apesar de 925 interacoes
- **Mecanismo de re-enablement nao funcionava**: successor_re_enables = 0

### 0.8.2 Root Cause Analysis

**Problema 1: COVERAGE_THRESHOLD muito alto**
- Valor anterior: 0.7 (70%)
- Significado: Acoes so eram re-habilitadas se cobertura do estado sucessor < 70%
- Resultado: Estados com 70-99% de cobertura nao disparavam re-habilitacao

**Problema 2: Key mismatch nas estatisticas**
- Runner buscava `"actions_re_enabled"` mas tracker retornava `"successor_re_enables"`
- Resultado: Metrica sempre mostrava 0

### 0.8.3 Correcoes Implementadas

**Fix 1: `successor_tracker.py`**
```python
# Antes
COVERAGE_THRESHOLD = 0.7

# Depois (commit 16/01/2026)
COVERAGE_THRESHOLD = 0.9  # Re-enable se sucessor < 90% cobertura
```

**Fix 2: `runner.py`**
```python
# Antes
metrics["successor_re_enables"] = tracker_stats.get("actions_re_enabled", 0)

# Depois
metrics["successor_re_enables"] = tracker_stats.get("successor_re_enables", 0)
```

### 0.8.4 Resultados da Validacao (Dicer app, 90s)

| Metrica | Antes (0.7) | Depois (0.9) | Melhoria |
|---------|-------------|--------------|----------|
| action_repetition_rate | 64.83% | **25.4%** | **-60%** |
| successor_re_enables | 0 | **15** | Funcionando! |
| max_action_executions | 9 | 5 | Menos repeticao |
| tested_once elements | 11 | 18 | +64% |

### 0.8.5 Arquitetura de Coleta de Metricas

**Modulo**: `rv-agent-validation/calibration/`

| Arquivo | Descricao |
|---------|-----------|
| `metrics_collector.py` | CalibrationMetricsCollector - coleta metricas pos-execucao |

**Metricas Coletadas por Run**:
- `states_discovered`, `total_transitions`
- `ui_coverage_percentage`, `ui_element_distribution`
- `action_repetition_rate`, `max_action_executions`
- `successor_re_enables`, `incomplete_successors`
- Per-screen: `total_actions`, `executed_actions`, `coverage_percent`

**Agregacoes**:
- Screen coverage distribution (0-20%, 20-40%, ..., 80-100%)
- Metricas por package (avg_states, avg_ui_coverage)

### 0.8.6 Configuracao do Experimento

```json
{
  "experiment_name": "mini_calibration_fase08",
  "apks": [9 APKs selecionados],
  "seeds": [42, 123, 456, 789, 1024, 2048, 4096, 8192],
  "timeout": 300,
  "mode": "pure_algorithm",
  "strategy": "rvagent",
  "collect_logcat": true,
  "collect_coverage": true
}
```

**Total**: 9 APKs × 8 seeds = 72 runs (~6h)

### 0.8.7 Comando de Execucao

```bash
cd modules/rv-agent-validation
uv run python -m rv_agent_validation experiment \
  --config data/configs/mini_calibration.json
```

### 0.8.8 Metricas para Analise Pos-Experimento

1. **Cobertura UI media** - deve aumentar com as correcoes
2. **Taxa de repeticao media** - deve diminuir significativamente
3. **Distribuicao de cobertura por tela** - mais telas com >80%
4. **Re-enables por run** - indicador de que o mecanismo funciona
5. **Variancia entre seeds** - estabilidade do algoritmo

### 0.8.9 Resultados do Experimento (COMPLETO - 72/72 runs)

**Status**: CONCLUIDO
**Data Conclusao**: 16/01/2026 ~12:00
**Duracao**: ~6h

| App | Cov% | Elem | Untested | ReEn | Incomp | Ratio | Rep% | States |
|-----|------|------|----------|------|--------|-------|------|--------|
| dnshero | 14.6 | 105 | 89 | 3.8 | 15.6 | 0.24 | 29.1 | 7.0 |
| simplenotes | 14.7 | 190 | 164 | 8.9 | 44.8 | 0.20 | 33.1 | 14.1 |
| hourlyreminder | 38.4 | 216 | 134 | 47.1 | 70.6 | 0.67 | 12.9 | 16.5 |
| pindroid | 40.0 | 20 | 12 | 6.6 | 0.0 | inf | 85.2 | 4.1 |
| moneytracker | 41.8 | 131 | 77 | 22.9 | 45.9 | 0.50 | 27.0 | 17.0 |
| privacyfriendlydicer | 44.9 | 49 | 27 | 22.5 | 23.1 | 0.97 | 77.6 | 7.0 |
| sonycamera | 46.1 | 42 | 22 | 0.2 | 0.2 | 1.00 | 84.6 | 3.2 |
| privacyfriendlyludo | 47.0 | 88 | 47 | 17.6 | 20.4 | 0.87 | 41.8 | 13.6 |
| fhem | 64.8 | 136 | 48 | 21.0 | 8.6 | 2.43 | 21.2 | 12.5 |
| **MEDIA GLOBAL** | **39.2** | - | - | **16.7** | - | - | **45.8** | **10.6** |

**Legenda**:
- Cov%: UI coverage percentage
- ReEn: Successor re-enables (media)
- Incomp: Incomplete successors (media)
- Ratio: ReEn / Incomp (indicador de eficiencia do re-enablement)
- Rep%: Action repetition rate

### 0.8.10 Investigacao: Baixa UI Coverage

**Problema Identificado**: Alguns apps (dnshero, simplenotes) tem cobertura muito baixa (~15%) enquanto outros (fhem) atingem ~65%.

**Root Cause Analysis**:

| Categoria | Apps | Avg Cov% | Avg Ratio | Caracteristica |
|-----------|------|----------|-----------|----------------|
| LOW (<30%) | dnshero, simplenotes | 14.7% | 0.22 | Muitos incomplete successors, poucos re-enables |
| HIGH (>=50%) | fhem | 64.8% | 2.43 | Poucos incomplete successors, muitos re-enables |

**Causa Raiz**: `MAX_RE_ENABLES=2` e muito limitante

O parametro `MAX_RE_ENABLES=2` em `successor_tracker.py` limita quantas vezes uma acao pode ser re-habilitada. Apps com muitos incomplete successors (dnshero: 16, simplenotes: 45) atingem o limite rapidamente, impedindo que estados com baixa cobertura sejam revisitados.

**Correlacao Observada**:
```
Re-enable Ratio = re_enables / incomplete_successors

- Apps com ratio < 0.5 → cobertura < 30%
- Apps com ratio > 1.0 → cobertura > 45%
```

**Recomendacoes para Proxima Iteracao**:
1. Aumentar `MAX_RE_ENABLES` de 2 para 3 ou 4
2. Implementar "priority re-enable" para estados com cobertura muito baixa
3. Ajustar state hashing para tolerar mudancas menores de UI

### 0.8.11 Correcoes Aplicadas (17/01/2026)

**Status**: IMPLEMENTADO

#### Fix 1: MAX_RE_ENABLES

```python
# Arquivo: modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/successor_tracker.py

# Antes
MAX_RE_ENABLES = 2

# Depois
MAX_RE_ENABLES = 3  # Permite mais revisitas a estados com baixa cobertura
```

**Motivo**: Apps com muitos incomplete successors (dnshero: 16, simplenotes: 45) atingiam o limite rapidamente, causando cobertura baixa (~15%).

#### Fix 2: System Actions Handling

```python
# Arquivo: modules/rv-agent/src/rv_agent/agent/nodes/algorithm_node.py

# System actions don't require coordinates
action_type = item_action.action_type.upper()
system_actions = {"BACK", "RESTART_APP", "KEY_EVENT"}

if action_type in system_actions:
    action = {
        "action_type": action_type,
        "x": 0, "y": 0,
        "text": item_action.text or "",
        "source": "algorithm",
        "id": item_action.id
    }
    # ... return action without coordinate lookup
```

**Motivo**: 959 erros "Failed to get coordinates from ItemAction" causados por acoes BACK que nao tem coordenadas.

#### Fix 3: Retry Logic para Falhas de Infraestrutura

```python
# Arquivos:
# - modules/rv-agent-validation/src/rv_agent_validation/experiment/runner.py
# - modules/rv-agent-validation/src/rv_agent_validation/multimodal/runner.py

INFRASTRUCTURE_ERRORS = [
    "INSTALL_FAILED", "device not found", "Connection refused",
    "TimeoutError", "ADB server", "cannot connect",
    "error: closed", "daemon not running",
]

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
```

**Funcionalidade**: Runs que falham por erros de infraestrutura sao automaticamente re-executados ate 3 vezes. Erros do agente nao disparam retry.

---

## 1. Protocolo de Execucao

### 1.1 Fluxo Manual Entre Fases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 1: Algoritmos                                                          │
│ Inicio: Qui 15/01 16:00 | Fim estimado: Sex 16/01 07:00 (~15h)             │
│                                                                             │
│ Executa: 4 estrategias × 15 apps × 3 seeds = 180 runs                      │
│ Modo: pure_algorithm                                                        │
│ Output: results/phase1_algorithms/                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │ PAUSA - ANALISE (~1h)         │
                    │ Sex 16/01 manha               │
                    │                               │
                    │ → Analisar method_coverage    │
                    │ → Selecionar MELHOR ESTRATEGIA│
                    │ → Se rvagent nao for melhor:  │
                    │   identificar pontos fracos   │
                    └───────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 2: Prompts + Params                                                    │
│ Inicio: Sex 16/01 09:00 | Fim estimado: Sab 17/01 23:00 (~38h)             │
│                                                                             │
│ Usa: estrategia vencedora da Fase 1                                        │
│ Executa: 2 prompts × 5 params × 15 apps × 3 seeds = 450 runs               │
│ Modo: llm_only                                                              │
│ Output: results/phase2_prompts_params/                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │ PAUSA - ANALISE (~1h)         │
                    │ Dom 18/01 manha               │
                    │                               │
                    │ → Analisar method_coverage    │
                    │ → Analisar hit_rate           │
                    │ → Analisar latency            │
                    │ → Selecionar MELHOR PROMPT +  │
                    │   PARAMS                      │
                    └───────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 3: Multimode                                                           │
│ Inicio: Dom 18/01 10:00 | Fim estimado: Seg 19/01 01:00 (~15h)             │
│                                                                             │
│ Usa: estrategia + prompt + params vencedores                               │
│ Executa: 4 proporcoes × 15 apps × 3 seeds = 180 runs                       │
│ Modo: multimode (variando llm_probability)                                  │
│ Output: results/phase3_multimode/                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │ ANALISE FINAL                 │
                    │ Seg 19/01 manha               │
                    │                               │
                    │ → Configuracao otima          │
                    │ → Comparacao com baseline     │
                    │ → Documentar resultados       │
                    └───────────────────────────────┘
```

### 1.2 Cronograma Revisado

| Fase | Runs | Timeout | Tempo | Inicio | Fim |
|------|------|---------|-------|--------|-----|
| 1. Algoritmos + Static | 360 | 180s | ~21h | Dia 1 00:00 | Dia 1 21:00 |
| **Analise 1** | - | - | ~2h | Dia 1 21:00 | Dia 1 23:00 |
| 2. Prompts + Params + Static | 540 | 180s | ~32h | Dia 2 00:00 | Dia 3 08:00 |
| **Analise 2** | - | - | ~2h | Dia 3 08:00 | Dia 3 10:00 |
| 3. Multimode + Static | 360 | 300s | ~33h | Dia 3 10:00 | Dia 4 19:00 |
| **Analise Final** | - | - | ~4h | Dia 4 19:00 | Dia 4 23:00 |

**Total**: ~4 dias de execucao (86h de runs + analises)

---

## 2. Fase 1: Algoritmos + Static Analysis Impact

### 2.1 Objetivo

Determinar:
1. Qual estrategia tem melhor desempenho **COM** static analysis
2. Qual estrategia tem melhor desempenho **SEM** static analysis
3. Impacto (delta) da static analysis em cada estrategia

### 2.2 Configuracoes

| Config | Estrategia | Static Analysis | Modo |
|--------|------------|-----------------|------|
| 1 | rvagent | **true** | pure_algorithm |
| 2 | rvagent | false | pure_algorithm |
| 3 | dfs | **true** | pure_algorithm |
| 4 | dfs | false | pure_algorithm |
| 5 | bfs | **true** | pure_algorithm |
| 6 | bfs | false | pure_algorithm |
| 7 | greedy | **true** | pure_algorithm |
| 8 | greedy | false | pure_algorithm |

### 2.3 Estrategias e Uso de Static Analysis

| Estrategia | Descricao | Uso de SA |
|------------|-----------|-----------|
| `rvagent` | DFS + WTG + MOP + scorers | MopScorer (+100/+50) + WtgScorer (+100) |
| `dfs` | DFS com priorizacao MOP | `_get_mop_priority()` tiebreaker |
| `bfs` | BFS simples | `_get_mop_priority()` tiebreaker |
| `greedy` | Greedy com 10% exploracao | `_get_mop_priority()` tiebreaker |

### 2.4 Runs

```
8 configs × 15 apps × 3 seeds = 360 runs
Timeout: 180s (3 min)
Tempo estimado: ~18 horas
```

### 2.5 Metricas de Avaliacao

**Foco**: Capacidade de exploracao sem LLM

| Metrica | Tipo | Descricao |
|---------|------|-----------|
| `method_coverage` | **Primaria** | Cobertura de metodos instrumentados |
| `ui_coverage_percentage` | **Primaria** | % de elementos UI interagidos |
| `unique_states` | Exploracao | Quantidade de estados unicos visitados |
| `reaches_mop_coverage` | MOP | % de metodos que alcancam operacoes monitoradas |
| `actions_per_minute` | Eficiencia | Taxa de acoes por minuto |

### 2.6 Hipoteses a Testar

1. **H1**: rvagent + static > rvagent - static (delta > 10%)
2. **H2**: rvagent + static > dfs/bfs/greedy + static
3. **H3**: Static analysis beneficia mais rvagent que outras estrategias

### 2.7 Criterio de Sucesso

- rvagent + static deve **superar todas as outras configs** no score composto
- Se nao superar, identificar pontos fracos e melhorar

---

## 3. Fase 2: Prompts + Parametros + Static Analysis

### 3.1 Objetivo

Determinar:
1. Melhor prompt (v13 vs v14)
2. Melhores parametros LLM
3. Impacto de static analysis na eficacia do LLM

### 3.2 Prompts

| Prompt | Descricao |
|--------|-----------|
| `v13` | Prompt atual com dialog handling |
| `v14` | Prompt com structured reasoning |

### 3.3 Configuracoes de Parametros (3 - reduzido)

**NOTA sobre `top_k`**:
- API OpenAI nativa NAO suporta `top_k`
- SGLang SUPORTA `top_k` via `extra_body` na API OpenAI-compatible
- LangChain ChatOpenAI passa `top_k` via `extra_body`

| Config | temperature | top_p | top_k | Descricao |
|--------|-------------|-------|-------|-----------|
| default | 0.01 | 0.6 | 50 | Baseline (atual) |
| deterministic | 0.001 | 0.5 | 30 | Mais consistente |
| explorative | 0.1 | 0.9 | 70 | Mais variado |

### 3.4 Static Analysis

| Variante | Descricao |
|----------|-----------|
| `true` | MOP markers [M]/[DM] + NavigationGuidance (WTG) |
| `false` | Sem informacoes de analise estatica |

### 3.5 Runs

```
2 prompts × 3 params × 2 static × 15 apps × 3 seeds = 540 runs
Timeout: 180s (3 min)
Tempo estimado: ~27 horas
```

### 3.6 Metricas de Avaliacao

**Foco**: Qualidade e eficiencia do LLM

| Metrica | Tipo | Descricao |
|---------|------|-----------|
| `method_coverage` | **Primaria** | Cobertura de metodos instrumentados |
| `ui_coverage_percentage` | **Primaria** | % de elementos UI interagidos |
| `hit_rate` | Precisao | % de acoes que acertam elementos UI |
| `latency_avg` | Eficiencia | Tempo medio de resposta do LLM (ms) |
| `tokens_total` | Custo | Total de tokens consumidos |
| `action_repetition_rate` | Exploracao | Taxa de repeticao de acoes |

### 3.7 Hipoteses a Testar

1. **H4**: v14 > v13 em hit_rate
2. **H5**: v14 > v13 em method_coverage
3. **H6**: Static analysis melhora navegacao (menos repeticao)

### 3.8 Criterio de Sucesso

- Hit rate >= 80%
- Latency <= 2000ms
- Method coverage >= baseline da fase 1

---

## 4. Fase 3: Multimode + Static Analysis

### 4.1 Objetivo

Determinar proporcao otima LLM/algoritmo considerando static analysis.
Usar **estrategia + prompt + params vencedores** das fases anteriores.

### 4.2 Proporcoes a Testar

| Config | llm_probability | Descricao |
|--------|-----------------|-----------|
| algo_only | 0.0 | 100% algoritmo |
| mostly_algo | 0.3 | 30% LLM |
| balanced | 0.5 | 50/50 |
| mostly_llm | 0.7 | 70% LLM (default atual) |

### 4.3 Static Analysis

| Variante | Descricao |
|----------|-----------|
| `true` | MOP + WTG ativos para algoritmo e LLM |
| `false` | Sem analise estatica |

### 4.4 Runs

```
4 proporcoes × 2 static × 15 apps × 3 seeds = 360 runs
Timeout: 300s (5 min) - comparavel com experimentos anteriores
Tempo estimado: ~30 horas
```

### 4.5 Metricas de Avaliacao

**Foco**: Encontrar equilibrio otimo LLM/algoritmo

| Metrica | Tipo | Descricao |
|---------|------|-----------|
| `method_coverage` | **Primaria** | Cobertura de metodos instrumentados |
| `ui_coverage_percentage` | **Primaria** | % de elementos UI interagidos |
| `llm_calls` | Custo | Quantidade de chamadas ao LLM |
| `total_latency` | Eficiencia | Tempo total gasto em LLM (ms) |
| `actions_per_minute` | Velocidade | Taxa de acoes por minuto |
| `unique_states` | Exploracao | Estados unicos visitados |

### 4.6 Hipoteses a Testar

1. **H7**: multimode > pure LLM e pure algorithm
2. **H8**: Static analysis + multimode tem sinergia positiva

### 4.7 Criterio de Sucesso

- Method coverage >= max(fase 1, fase 2)
- Proporcao otima identificada com melhor custo-beneficio
- Comparavel com baseline de outras ferramentas (Humanoid: 26.79%)

---

## 5. APKs Selecionados (15 Validados)

### 5.1 Criterios de Selecao

1. **Validados na Fase 1 anterior** (180 runs, 100% sucesso)
2. **Sem crashes ou falhas sistematicas**
3. **Todos instrumentados** com arquivos .wtg, .reach, .gesda, .methods

**APKs EXCLUIDOS por problemas:**
- `org.pulpdust.lesserpad_42.apk` - CRASH
- `max.music_cyclon_4.apk` - CRASH

### 5.2 Lista Definitiva dos 15 APKs (Todas as Fases)

| # | APK | Methods | Categoria | Method Cov (Fase 1) |
|---|-----|---------|-----------|---------------------|
| 1 | com.blogspot.e_kanivets.moneytracker_38.apk | 1205 | Money | 32.4% |
| 2 | com.gianlu.dnshero_40.apk | 435 | Internet | 15.9% |
| 3 | com.github.axet.hourlyreminder_476.apk | 724 | Multimedia | 45.1% |
| 4 | com.pindroid_69.apk | 640 | Internet | 10.6% |
| 5 | com.rafapps.simplenotes_7.apk | 161 | Writing | 37.5% |
| 6 | com.thibaudperso.sonycamera_24.apk | 454 | Multimedia | 22.8% |
| 7 | li.klass.fhem_141.apk | 2417 | Internet | 30.9% |
| 8 | com.reddyetwo.hashmypass.app_24.apk | 445 | Security | 73.0% |
| 9 | org.secuso.privacyfriendlydicer_8.apk | 82 | Games | 82.1% |
| 10 | org.secuso.privacyfriendlyludo_5.apk | 269 | Games | 29.9% |
| 11 | gg.mw.passera_2.apk | 15 | Security | 100.0% |
| 12 | org.secuso.privacyfriendlyyahtzeedicer_5.apk | 30 | Games | 96.7% |
| 13 | digital.selfdefense.lucia_20001.apk | 17 | Connectivity | 76.5% |
| 14 | net.xvello.salasana_3.apk | 11 | Security | 81.8% |
| 15 | com.github.axet.darknessimmunity_28.apk | 71 | Theming | 84.5% |

**Nota:** Method Coverage da Fase 1 foi executada **SEM** static analysis (enable_static_analysis: false).

### 5.3 Localizacao

```
modules/rv-agent-validation/data/apks_instrumented/<apk_name>/
├── <apk_name>.apk      # APK instrumentado
├── <apk_name>.gesda    # Estrutura do app
├── <apk_name>.wtg      # Window Transition Graph
├── <apk_name>.reach    # Analise de alcancabilidade
└── <apk_name>.methods  # Ground truth de metodos
```

---

## 6. Baseline das Ferramentas Tradicionais

Ver `docs/20260113_rvagent_validacao_multimodal.md` Secao 1.3 para tabela completa.

**Top 3**:
| Ferramenta | Method Coverage | Reaches MOP | Directly Reaches MOP |
|------------|-----------------|-------------|----------------------|
| Humanoid | **26.79%** | **30.32%** | **26.20%** |
| FastBot | 25.46% | 29.02% | 25.67% |
| APE | 25.29% | 28.55% | 25.95% |

**Meta**: rv-agent deve atingir >= 26.79% (Humanoid) para ser competitivo.

---

## 7. Adaptacoes nos Scripts Existentes

### 7.1 O Que Ja Existe

- CLI com comandos: `multimodal`, `experiment`, `analyze`, `report`
- Sistema de configuracao via JSON
- Coleta de metricas completa
- Analise estatistica (Kruskal-Wallis, Wilcoxon)

### 7.2 Adaptacoes Necessarias

| Arquivo | Mudanca |
|---------|---------|
| `experiment/config.py` | Adicionar `strategy`, `prompt_version`, `llm_probability` |
| `multimodal/runner.py` | Passar novos params para AgentFactory |
| `__main__.py` | Adicionar opcoes CLI |

### 7.3 Verificar no rv-agent

| Arquivo | Verificar |
|---------|-----------|
| `agent/agent_factory.py` | Se aceita `strategy` param |
| `llm/llm_client.py` | Se aceita `prompt_version` param |
| `routing/routing_manager.py` | Se aceita `llm_probability` param |

---

## 8. Comandos de Execucao

**IMPORTANTE**: Sempre executar comandos a partir do diretorio `modules/rv-agent-validation/`.

### 8.1 Verificar Configuracao

```bash
cd modules/rv-agent-validation

# Verificar config da Fase 1
uv run python -c "
from rv_agent_validation.experiment.config import ExperimentConfig
import json
with open('data/configs/phase1_static_impact.json') as f:
    config = ExperimentConfig.from_dict(json.load(f))
print(f'Total runs: {config.total_runs}')
print(f'Estimated time: {config.estimated_time_hours:.1f}h')
"
```

### 8.2 Fase 1: Algoritmos + Static Analysis

```bash
cd modules/rv-agent-validation

# Executar Fase 1
uv run python -m rv_agent_validation.experiment.runner run \
  --config data/configs/phase1_static_impact.json \
  --output results

# Com resume (continua de onde parou)
uv run python -m rv_agent_validation.experiment.runner run \
  --config data/configs/phase1_static_impact.json \
  --output results

# Sem resume (reinicia do zero)
uv run python -m rv_agent_validation.experiment.runner run \
  --config data/configs/phase1_static_impact.json \
  --output results \
  --no-resume
```

### 8.3 Fase 2: Prompts + Params + Static

```bash
cd modules/rv-agent-validation

uv run python -m rv_agent_validation.experiment.runner run \
  --config data/configs/phase2_prompt_static.json \
  --output results
```

### 8.4 Fase 3: Multimode + Static

```bash
cd modules/rv-agent-validation

uv run python -m rv_agent_validation.experiment.runner run \
  --config data/configs/phase3_multimode_static.json \
  --output results
```

### 8.5 Analise de Resultados

```bash
cd modules/rv-agent-validation

# Analise estatistica
uv run python -m rv_agent_validation analyze \
  --input results/phase1_static_impact \
  --output results/phase1_static_impact/report.json

# Gerar CSV
uv run python -m rv_agent_validation report \
  --input results/phase1_static_impact \
  --format csv \
  --output results/phase1_static_impact/summary.csv
```

### 8.6 Monitorar Progresso

```bash
cd modules/rv-agent-validation

# Ver checkpoint
cat results/phase1_static_impact/checkpoint.json | jq .

# Ver log em tempo real
tail -f results/phase1_static_impact/experiment.log
```

---

## 9. Metricas Consolidadas

### 9.1 Metricas Coletadas pelo Collector

| Categoria | Metrica | Origem | Descricao |
|-----------|---------|--------|-----------|
| **Coverage** | `method_coverage` | logcat | % de metodos instrumentados executados |
| **Coverage** | `reaches_mop` | logcat | % de metodos que alcancam operacoes monitoradas |
| **Coverage** | `direct_mop` | logcat | % de metodos que diretamente alcancam MOP |
| **UI** | `element_coverage` | UI tracker | % de elementos UI interagidos |
| **UI** | `total_unique_elements` | UI tracker | Elementos unicos encontrados |
| **UI** | `total_interactions` | UI tracker | Total de interacoes realizadas |
| **UI** | `screens_visited` | UI tracker | Telas unicas visitadas |
| **LLM** | `hit_rate` | action classifier | % de acoes que acertam elementos |
| **LLM** | `near_miss_rate` | action classifier | % de acoes proximas ao alvo |
| **LLM** | `latency_avg` | LLM client | Tempo medio de resposta (ms) |
| **LLM** | `tokens_total` | LLM client | Total de tokens consumidos |
| **Exploration** | `unique_states` | state graph | Estados unicos visitados |
| **Exploration** | `activities_discovered` | memory | Activities Android descobertas |
| **Exploration** | `iterations` | agent | Iteracoes do agente |
| **Exploration** | `stuck_events` | stuck detector | Eventos de travamento |

### 9.2 Calculo dos Scores Compostos

**Nota**: method_coverage e element_coverage (UI coverage) tem peso equivalente como metricas primarias.

**Fase 1 - Score de Exploracao**:
```
score = (method_coverage × 0.40) + (element_coverage × 0.40) + (unique_states_norm × 0.20)
```

**Fase 2 - Score de Qualidade LLM**:
```
score = (method_coverage × 0.30) + (element_coverage × 0.30) + (hit_rate × 0.20) + (1 - latency_norm) × 0.10 + (1 - tokens_norm) × 0.10
```
*onde `latency_norm` e `tokens_norm` sao normalizados em [0, 1]*

**Fase 3 - Score de Eficiencia**:
```
efficiency = (method_coverage + element_coverage) / total_time_seconds
score = (method_coverage × 0.35) + (element_coverage × 0.35) + (efficiency_norm × 0.30)
```

### 9.3 Normalizacao

Para metricas que precisam ser normalizadas:
- `unique_states_norm = unique_states / max(unique_states_all_runs)`
- `latency_norm = latency_avg / max_latency_threshold` (threshold = 3000ms)
- `tokens_norm = tokens_per_action / max_tokens_threshold` (threshold = 500)
- `efficiency_norm = efficiency / max(efficiency_all_runs)`

---

## 10. Hipoteses

### 10.1 Fase 1: Algoritmos + Static Analysis

| # | Hipotese | Criterio |
|---|----------|----------|
| H1 | rvagent + static > rvagent - static | delta method_cov > 10% |
| H2 | rvagent + static > dfs/bfs/greedy + static | method_cov(rvagent+SA) > max(others+SA) |
| H3 | Static analysis beneficia mais rvagent que outros | delta(rvagent) > delta(others) |

### 10.2 Fase 2: Prompts + Params + Static

| # | Hipotese | Criterio |
|---|----------|----------|
| H4 | v14 > v13 em hit_rate | hit_rate(v14) > hit_rate(v13) |
| H5 | v14 > v13 em method_coverage | method_cov(v14) > method_cov(v13) |
| H6 | Static analysis melhora navegacao LLM | action_repetition(+SA) < action_repetition(-SA) |

### 10.3 Fase 3: Multimode + Static

| # | Hipotese | Criterio |
|---|----------|----------|
| H7 | Multimode > pure LLM e pure algorithm | method_cov(multi) > max(llm, algo) |
| H8 | Static analysis + multimode tem sinergia | method_cov(multi+SA) > method_cov(multi-SA) + method_cov(algo+SA) - method_cov(algo-SA) |
| H9 | rv-agent supera Humanoid | method_cov(best) > 26.79% |

---

## 11. Proximos Passos

### Fase 0: Pre-calibracao (CONCLUIDA)

1. [x] Definir metodologia em 3 fases
2. [x] Selecionar 15 APKs
3. [x] Definir metricas para cada fase
4. [x] Verificar parametros existentes no rv-agent
5. [x] Adaptar config.py com novos campos
6. [x] Adaptar runner.py para passar parametros
7. [x] Criar configs JSON para cada fase
8. [x] **Fase 0: Calibrar scores de componentes** (script + dataset)
9. [x] **Bug fix: Auto-load de static data respeitando use_wtg**
10. [x] **Fase 0.8: Validacao inicial** (5 apps × 1 seed × 180s)
11. [x] **Fase 0.8: Diagnostico** - Identificado COVERAGE_THRESHOLD=0.7 causando baixa cobertura
12. [x] **Fase 0.8: Correcoes** - COVERAGE_THRESHOLD: 0.7 → 0.9, fix key mismatch
13. [x] **Fase 0.8: Validacao das correcoes** - repetition rate: 64.83% → 25.4%
14. [x] **Fase 0.8.11: MAX_RE_ENABLES** - 2 → 3 (17/01/2026)
15. [x] **Fase 0.8.11: System actions handling** - BACK, KEY_EVENT sem coordenadas (17/01/2026)
16. [x] **Fase 0.8.11: Retry logic** - 3 tentativas para erros de infra (17/01/2026)
17. [x] **Fase 0.8.11: UI coverage peso igual** - Scores compostos atualizados (17/01/2026)

### Revisao da Metodologia (19/01/2026)

18. [x] **Descoberta critica**: Experimentos anteriores rodaram sem static analysis
19. [x] **Revisar metodologia**: Incluir `static_analysis` como variavel experimental
20. [ ] **Implementar suporte a `static_analysis_variants`** em config.py e runner.py
21. [ ] **Criar configs JSON revisados**: phase1_static_impact.json, phase2_prompt_static.json, phase3_multimode_static.json

### Execucao das Fases

22. [ ] **Executar Fase 1** - 360 runs (4 strategies × 2 static × 15 APKs × 3 seeds) - 180s - ~18h
23. [ ] **Analisar resultados Fase 1** - Identificar melhor estrategia + impacto de SA
24. [ ] **Executar Fase 2** - 540 runs (2 prompts × 3 params × 2 static × 15 APKs × 3 seeds) - 180s - ~27h
25. [ ] **Analisar resultados Fase 2** - Identificar melhor prompt/params + impacto de SA
26. [ ] **Executar Fase 3** - 360 runs (4 proporcoes × 2 static × 15 APKs × 3 seeds) - 300s - ~30h
27. [ ] **Gerar relatorio final** - Comparar com baseline (Humanoid: 26.79%)

---

## 12. Arquivos de Configuracao

### 12.1 Fase 1: Algoritmos + Static

| Arquivo | Descricao |
|---------|-----------|
| `phase1_static_impact.json` | 4 estrategias × 2 static variants em pure_algorithm |

**Estrutura JSON**:
```json
{
  "experiment_id": "phase1_static_impact",
  "strategies": ["rvagent", "dfs", "bfs", "greedy"],
  "static_analysis_variants": [true, false],
  "timeout_seconds": 180,
  "agent_mode": "pure_algorithm"
}
```

### 12.2 Fase 2: Prompts + Params + Static

| Arquivo | Descricao |
|---------|-----------|
| `phase2_prompt_static.json` | 2 prompts × 3 params × 2 static em llm_only |

**Parametros LLM**:
| Config | temperature | top_p | top_k |
|--------|-------------|-------|-------|
| default | 0.01 | 0.6 | 50 |
| deterministic | 0.001 | 0.5 | 30 |
| explorative | 0.1 | 0.9 | 70 |

### 12.3 Fase 3: Multimode + Static

| Arquivo | Descricao |
|---------|-----------|
| `phase3_multimode_static.json` | 4 proporcoes × 2 static em multimode |

**Proporcoes**:
| Config | llm_probability |
|--------|-----------------|
| algo_only | 0.0 |
| mostly_algo | 0.3 |
| balanced | 0.5 |
| mostly_llm | 0.7 |

---

## 13. Referencias

- `docs/20260113_rvagent_validacao_multimodal.md` - Infraestrutura e dataset (103 APKs)
- `modules/rv-agent-validation/data/apks_validation.csv` - Baseline de cobertura
- `modules/rv-agent-validation/data/apks_complete.csv` - APKs do exp02

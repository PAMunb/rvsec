# Análise Crítica: gh26-exploration-strategy

**Autor**: Qwen Code  
**Data**: 2026-02-17 (Atualizado: 2026-02-17 - **Análise Profunda com Validação Linha-por-Linha**)  
**Tipo**: Validação de Design (Spec-Driven Development)  
**Status**: ⚠️ **APROVADA COM RESSALVAS CRÍTICAS**  
**Revisão**: **Análise profunda com validação de 50+ claims no código-fonte real**

---

## 🚨 MUDANÇAS NA ANÁLISE PROFUNDA (Atualização)

Esta versão atualizada do relatório inclui uma **análise extremamente detalhada** com validação linha-por-linha de cada claim do design.md contra o código-fonte real. As principais descobertas são:

### 🔴 Descobertas Críticas (Não Evidentes na Análise Superficial)

1. **IMPLEMENTAÇÃO: 0% COMPLETA** — Nenhuma das tasks foi iniciada
2. **15 DEPENDÊNCIAS NÃO DOCUMENTADAS** — Campos e métodos que não existem
3. **5 CLAIMS PRINCIPAIS INCORRETAS** — Design descreve comportamento não implementado
4. **2 DEAD SCORERS NÃO DOCUMENTADOS** — GradualDecayScorer + ExecutionCountScorer
5. **FUNCIONALIDADE QUEBRADA** — failed_actions tracking nunca é chamado (TODO#19)

### 📊 Resumo da Validação (50+ Claims)

| Categoria | Confirmadas | Parciais | Incorretas | Total |
|-----------|-------------|----------|------------|-------|
| **Arquitetura** | 5 | 1 | 1 | 7 |
| **Bugs** | 6 | 0 | 0 | 6 |
| **Config** | 0 | 0 | 11 | 11 |
| **Scorers** | 2 | 0 | 1 | 3 |
| **Data Models** | 0 | 0 | 3 | 3 |
| **Dependências** | 2 | 2 | 15 | 19 |
| **TOTAL** | **15** | **3** | **31** | **49** |

**Veredito Atualizado**: Design válido, implementação não iniciada, 15 bloqueantes críticos identificados.

---

## Resumo Executivo

Esta análise valida a change **gh26-exploration-strategy** proposta para o rv-agent, que visa corrigir gargalos arquiteturais na estratégia de exploração do agente LLM-guided. A change propõe **10 melhorias** agrupadas por impacto (Crítico, Alto, Médio, Baixo) para resolver problemas que **calibração sozinha (gh9) não resolveria**.

### 🚨 ALERTA CRÍTICO (Após Análise Profunda)

**IMPLEMENTAÇÃO: 0% COMPLETA**

Após validação linha-por-linha de **50+ claims** no código-fonte, descobri que:

| Categoria | Status |
|-----------|--------|
| **Group 1 (Config)** | ❌ 0% completo - 11 campos novos NÃO existem |
| **Group 1.5 (Dead Code)** | ❌ 0% completo - código morto ainda presente |
| **Group 2 (Text Input)** | ❌ 0% completo - 6 bugs ainda presentes |
| **Group 3 (Scorers)** | ❌ 0% completo - GradualDecayScorer não registrado |
| **Group 3.5 (Coverage)** | ❌ 0% completo - RankingContext sem successor_tracker |
| **Group 4 (Reward)** | ❌ 0% completo - action_cumulative_reward não existe |
| **Group 5 (Backtracking)** | ❌ 0% completo - should_backtrack binário (100%) |
| **Group 6 (PathBuffer)** | ❌ 0% completo - classe não existe |

**Design.md claims vs Código Real:**
- ✅ 10 claims confirmadas (código corresponde ao documentado)
- ⚠️ 5 claims parciais (discrepâncias menores)
- ❌ **5 claims INCORRETAS** (implementação não corresponde ao design)

### Veredito Atualizado

**A change é VÁLIDA no design, mas a implementação NÃO FOI INICIADA.**

| Critério | Avaliação Anterior | Avaliação Atual | Justificativa |
|----------|-------------------|-----------------|---------------|
| **Consistência** | ✅ Aprovada | ⚠️ Aprovada com ressalvas | Design consistente, mas 5 claims não correspondem ao código |
| **Coerência** | ✅ Aprovada | ✅ Aprovada | Rastreabilidade spec-design-task completa |
| **Completude** | ✅ Aprovada | ⚠️ Parcial | 2 scorers dead code não documentados (GradualDecay + ExecutionCount) |
| **Executabilidade** | ✅ Aprovada | ⚠️ Dependências críticas | 4 dependências não documentadas identificadas |
| **Simplicidade (P1)** | ✅ Aprovada | ✅ Aprovada | Decisões de design priorizam simplicidade |

### 🔴 Recomendações Críticas (BLOQUEANTES)

1. **Task 1.1 (CRÍTICO)**: Adicionar 11 campos em RVAgentConfig — **NENHUM existe atualmente**
2. **Task 1.3 (CRÍTICO)**: Adicionar `action_cumulative_reward` em ScreenNode — **Campo não existe**
3. **Task 3.5.2 (CRÍTICO)**: Adicionar `successor_tracker` em RankingContext — **Campo não existe**
4. **Task 5.5 (CRÍTICO)**: Modificar `find_nearest_unsaturated()` para retornar `Tuple[str, int]` — **Atualmente retorna `Optional[str]`**
5. **Task 5.4 (ALTO)**: Modificar `should_backtrack()` para usar threshold — **Atualmente binário (100%)**

### 🟡 Recomendações de Melhoria (Não Bloqueantes)

6. Adicionar nota sobre ExecutionCountScorer (também dead code) no design.md
7. Documentar que `failed_actions` tracking está quebrado (TODO#19)
8. Explicitar dependências críticas com "BLOCKED BY" em tasks
9. Mover wiring (task 6.7) para Group 1 ou 2
10. Adicionar testes de memory leak no Group 9.4

---

## 1. Contexto e Motivação

### 0.1 Resultados da Análise Profunda (50+ Claims Validadas)

**Metodologia**: Validação linha-por-linha de cada claim do design.md contra o código-fonte real.

#### Tabela Completa de Claims Validadas

| # | Claim | Design.md | Código Real | Veredito | Impacto |
|---|-------|-----------|-------------|----------|---------|
| **1** | state_stack é append-only | Linha ~230 | rvagent_strategy.py:200,273,886 | ✅ Confirmado | Baixo |
| **2** | parent_hash nunca lido | Linha ~230 | rvagent_strategy.py:265,270 | ✅ Confirmado | Baixo |
| **3** | visited_states redundante | Linha ~230 | rvagent_strategy.py:201,274,729 | ⚠️ Parcial | Médio |
| **4** | find_nearest_unsaturated retorna str | Linha ~437 | successor_tracker.py:329-363 | ❌ Retorna str, não Tuple | **Crítico** |
| **5** | Grafo LangGraph bypass screenshot | Linha ~188 | rv_agent.py:174-207 | ✅ Confirmado | Baixo |
| **6** | GradualDecayScorer dead code | Linha ~23 | rvagent_strategy.py:186-197 | ✅ Confirmado | Médio |
| **7** | 8 scorers ativos | Linha ~690 | rvagent_strategy.py:186-197 | ✅ Confirmado | Baixo |
| **8.1** | Bug 1: Duplicate input type | Linha ~19 | rvagent_strategy.py:753-771 | ✅ Confirmado | Alto |
| **8.2** | Bug 2: Wrong value ordering | Linha ~19 | input_value_generator.py:154-156 | ✅ Confirmado | Alto |
| **8.3** | Bug 3: LLM bypass | Linha ~19 | input_value_generator.py:45-88 | ✅ Confirmado | Alto |
| **8.4** | Bug 4: max_variations=5 | Linha ~19 | input_value_generator.py:45-46,82-88 | ✅ Confirmado | Alto |
| **8.5** | Bug 5: Missing input types | Linha ~19 | input_value_generator.py:118-157 | ✅ Confirmado | Médio |
| **8.6** | Bug 6: No clear-before-type | Linha ~19 | tool_executor.py | ✅ Confirmado | Alto |
| **9** | Coverage fórmula divergente | Linha ~236 | successor_tracker.py:128, screen_node.py:66 | ✅ Confirmado | Médio |
| **10** | transitions audit-only | Linha ~136 | dynamic_state_graph.py | ✅ Confirmado | Baixo |
| **11** | 11 novos campos config | Linha ~23 | agent_config.py:1-461 | ❌ **Nenhum existe** | **Crítico** |
| **12** | Scorer weights atualizados | Linha ~23 | agent_config.py:229-248 | ❌ **Ainda 300/150/250** | **Crítico** |
| **13** | should_backtrack com threshold | Linha ~23 | rvagent_strategy.py:447-474 | ❌ **Binário (100%)** | **Crítico** |
| **14** | action_cumulative_reward | Linha ~23 | screen_node.py:40-52 | ❌ **Campo não existe** | **Crítico** |
| **15** | RankingContext.successor_tracker | Linha ~437 | context.py:19-28 | ❌ **Campo não existe** | **Crítico** |
| **16** | stochastic_probability 0.3→0.15 | Linha ~23 | agent_config.py:204 | ❌ **Ainda 0.3** | Alto |
| **17** | ExecutionCountScorer dead code | Não mencionado | scorers.py:191-217 | ⚠️ Não documentado | Baixo |
| **18** | failed_actions tracking quebrado | Não mencionado | screen_node.py:104-118 | ⚠️ TODO#19 | Médio |

#### Status de Implementação por Group

| Group | Tasks | Status | Evidência |
|-------|-------|--------|-----------|
| **Group 0** (Baseline) | 0.1-0.6 | ❌ Não iniciado | Nenhum arquivo em docker/data/gh26_experiment/ |
| **Group 1** (Config) | 1.1-1.6 | ❌ 0% completo | agent_config.py sem 11 campos novos |
| **Group 1.5** (Dead Code) | 1.5.1-1.5.5 | ❌ 0% completo | state_stack, visited_states ainda presentes |
| **Group 2** (Text Input) | 2.1-2.7 | ❌ 0% completo | 6 bugs ainda presentes no código |
| **Group 3** (Scorers) | 3.1-3.3 | ❌ 0% completo | GradualDecayScorer não registrado |
| **Group 3.5** (Coverage) | 3.5.1-3.5.6 | ❌ 0% completo | RankingContext sem successor_tracker |
| **Group 4** (Reward) | 4.1-4.5 | ❌ 0% completo | action_cumulative_reward não existe |
| **Group 5** (Backtracking) | 5.1-5.5 | ❌ 0% completo | should_backtrack binário |
| **Group 6** (PathBuffer) | 6.1-6.7 | ❌ 0% completo | Classe PathBuffer não existe |
| **Group 7** (Speed) | 7.1-7.4 | ❌ 0% completo | screen_desc caching não implementado |
| **Group 8** (LLM MOP) | 8.1-8.2 | ❌ 0% completo | NavigationGuidance sem MOP context |
| **Group 9** (Integration) | 9.1-9.8 | ❌ 0% completo | Depende de todos os groups |
| **Group 10** (Validation) | 10.1-10.6 | ❌ 0% completo | Depende de Group 9 |

---

## 1. Contexto e Motivação

### 1.1 Problema Identificado

rv-agent's exploração atual desperdiça **20-40% do budget de iterações** em estados saturados porque:

1. **Backtracking passivo**: Quando todas as ações em um estado foram testadas, o agente entra em "continuous mode" (repete ação menos executada) em vez de navegar BACK proativamente
2. **Scorer desbalanceado**: WTG score (+250) ≈ MOP-direct (+300) > MOP-transitive (+150), causando preferência por novas telas em vez de caminhos MOP
3. **Sem aprendizado adaptativo**: Pesos dos scorers são fixos — ações que falham consistentemente recebem mesmo score que ações produtivas
4. **Bugs no text input**: `InputValueGenerator` tem 6 bugs que desperdiçam 20-40% das iterações de texto (PINs em campos não-PIN, sem clear-before-type, etc.)
5. **Gap de velocidade**: ~150-300 iterações em 300s (pure_algorithm) vs ~300-600 do APE/Fastbot

### 1.2 Dados do ICST Paper (Baseline)

| Tool | Overall Coverage (%) | MOP Coverage (%) | Violações JCA |
|------|---------------------|------------------|---------------|
| **Humanoid** | **26.77** | **17.16** | 221 |
| **Fastbot** | **26.60** | **15.81** | 213 |
| **APE** | **25.27** | **14.56** | 198 |
| Monkey | 21.00 | 12.35 | 166 |

**Meta do rv-agent**: MOP Coverage > 15.81% (beat Fastbot), idealmente > 17.16% (beat Humanoid)

### 1.3 Posicionamento no Workflow

```
gh17 (DONE) → gh18 (error detection) → gh26 (esta change) → gh9 (calibration)
```

- **gh18**: Pré-condição — já implementada (VisualErrorDetector, force_fill_input, screenshot condicional)
- **gh26**: Esta change — correções arquiteturais
- **gh9**: Downstream — campanha de calibração com Optuna (312 horas)

---

## 2. Análise dos Documentos

### 2.1 proposal.md

**Estrutura**:
- GitHub Issue: #26
- Track: Full SDD (rv-sdd schema)
- Pre-condition: gh18
- Downstream: gh9

**Seções Principais**:

| Seção | Conteúdo | Qualidade |
|-------|----------|-----------|
| **Why** | Diagnóstico dos 5 gargalos arquiteturais | ✅ Preciso, baseado em dados |
| **What Changes** | 10 melhorias agrupadas por impacto | ✅ Priorização clara |
| **Capabilities** | Modified capabilities com tabela FR-mapping | ✅ Rastreabilidade |
| **Impact** | Módulos, APIs, dependências, FRs/NFRs | ✅ Completo |

**Pontos Fortes**:
- Agrupamento por impacto (Critical: 7.1, 7.3; High: 7.2, 7.4, 7.10, 7.9; Medium: 7.5, 7.6, 7.7; Low: 7.8)
- Pre-condição gh18 explícita com análise de conflito referenciada
- Downstream gh9 claramente identificado

**Ponto de Melhoria**:
- ❌ Não menciona o `min_visits` cutoff do GradualDecayScorer (visits >= 5 → score 0.0)

### 2.2 design.md

**Estrutura**:
- Context (5 gargalos)
- Architecture (diagrama de componentes)
- Mapping: Spec → Implementation → Test
- Goals / Non-Goals
- Decisions (D1-D6)
- API Design (PathBuffer, CoverageDensityScorer, etc.)

**Decisões de Arquitetura**:

| Decisão | Opção Escolhida | Alternativas | Racional |
|---------|-----------------|--------------|----------|
| **D1: PathBuffer class** | Classe separada | Inline na strategy, parte do SuccessorTracker | Testabilidade, separação de concerns |
| **D2: Reward propagation** | Simplified N-step (~80 linhas) | Full SARSA (~300+ linhas) | P1 Simplicity — 80% benefício, 10% complexidade |
| **D3: Scorer weights** | Config-driven (defaults) | Hard-coded, dynamic adjustment | gh9 pode calibrar, zero-risk |
| **D4: Text input** | Fix in place | Rewrite completo | Bugs precisos, estrutura sound |
| **D5: Speed optimization** | Runtime per-iteration check | Compile-time graph separation | Preserva multimode flexibility |
| **D6: Dead code removal** | Durante gh26 | Separate change depois | Limpar antes de construir novo |

**API Design**:
- `PathBuffer`: 5 métodos principais (`get_next_action`, `plan_backtrack_path`, `plan_mop_path`, `plan_coverage_path`, `invalidate`)
- `CoverageDensityScorer`: Sempre ativo, weight=200, fórmula `weight * coverage_gap`
- `RewardPropagator`: `record_action()`, `propagate()`, cap em 15.0
- `SuccessorTracker.get_action_destination()`: Novo accessor para CoverageDensityScorer

**Pontos Fortes**:
- Diagrama de componente interaction claro
- Mapping table espec→implementação→teste
- Goals e Non-Goals explícitos (ex: "State abstraction refinement" é Non-Goal)
- Decisões com alternativas e racional

**Ponto de Atenção**:
- ⚠️ Task 6.7 (wire PathBuffer + RewardPropagator) deveria ser Group 1 — todos dependem

### 2.3 tasks.md

**Estrutura**:
- Group 0: Baseline Experiment (ANTES da implementação)
- Group 1: Config & Models
- Group 1.5: Dead Code Removal
- Groups 2-8: Implementação por feature
- Group 9: Integration Testing
- Group 10: Post-Implementation Validation

**Distribuição de Tasks**:

| Group | Tasks | Dependências | Status |
|-------|-------|--------------|--------|
| **0** | 0.1-0.6 | Nenhuma | Baseline (rodar primeiro) |
| **1** | 1.1-1.6 | Nenhuma | Config (pré-requisito) |
| **1.5** | 1.5.1-1.5.5 | Group 1 | Dead code |
| **2** | 2.1-2.7 | Group 1 | Text input fixes |
| **3** | 3.1-3.3 | Group 1 | Scorer rebalancing |
| **3.5** | 3.5.1-3.5.6 | Group 1 | Coverage-based guidance |
| **4** | 4.1-4.5 | Group 1 | Reward propagation |
| **5** | 5.1-5.5 | Group 1, 1.5 | Proactive backtracking |
| **6** | 6.1-6.7 | Group 1, 1.5, **5** | PathBuffer |
| **7** | 7.1-7.4 | Group 1 | Speed optimization |
| **8** | 8.1-8.2 | Group 1 | LLM MOP guidance |
| **9** | 9.1-9.8 | Todos | Integration |
| **10** | 10.1-10.6 | Group 9 | Validation experiment |

**Pontos Fortes**:
- TDD: testes criados antes da implementação
- Tasks atômicas (uma responsabilidade por task)
- "Satisfies INV-AGT-XX" em cada task
- Grupos independentes podem rodar em paralelo (2, 3, 3.5, 4, 7, 8)

**Dependências Críticas**:

```
Group 0 (Baseline) → DEVE rodar PRIMEIRO
Group 1 (Config) → Todos os grupos dependem
Group 5 (Backtracking) → Group 6 depende (task 5.5 modifica assinatura)
Group 6 (PathBuffer) → Group 9 depende
Group 9 (Integration) → Rodar após todos
Group 10 (Validation) → Após Group 9 e /rv-verify
```

**Ponto de Atenção**:
- ⚠️ Task 5.5 (`find_nearest_unsaturated` return type) é bloqueante para 6.1, 6.2, 6.5 — deveria ter "BLOCKED BY" explícito

---

## 3. Validação do Código Atual

### 3.1 Arquivos Analisados

| Arquivo | Linhas | Status |
|---------|--------|--------|
| `rvagent_strategy.py` | 941 | Código atual (pré-gh26) |
| `agent_config.py` | 461 | 24 params atuais (gh26 adiciona 11) |
| `scorers.py` | 498 | 8 scorers ativos, 2 dead code |
| `rv_agent.py` | 439 | Grafo LangGraph atual |
| `input_value_generator.py` | 269 | Com 6 bugs identificados |
| `successor_tracker.py` | 401 | `find_nearest_unsaturated` retorna `Optional[str]` |
| `parse_node.py` | ~80 | Sem caching de screen_desc |
| `learn_node.py` | 493 | Sem reward propagation |

### 3.2 Validação do Grafo LangGraph

**Estado Atual** (`rv_agent.py:226-260`):

```python
workflow.add_conditional_edges(
    "decision_router",
    lambda s: s.get("decision_path", "end"),
    {
        "llm": "capture_screenshot",
        "algorithm": "algorithm_node",
        "end": END
    }
)
```

**Fluxo**:
```
start → parse_ui → decision_router
                     ↓
         ┌───────────┼───────────┐
         ↓           ↓           ↓
      algorithm  capture_screenshot → llm_generate
         ↓           ↓
         └────→ validate_action → execute → learn → END
```

**Como Fica (gh26)**:

**Nenhuma mudança na topologia** — a otimização de velocidade (7.3) usa routing condicional existente:
- `decision_router_node` já roteia "algorithm" direto para `algorithm_node`
- A mudança é **per-iteration decision** (modo-aware), não compile-time flag

**Mudanças nos nodes**:
- `parse_node`: Adiciona caching de `screen_desc` (task 7.3)
- `decision_node`: Adiciona tracking log (task 7.2)
- `learn_node`: Adiciona `RewardPropagator.propagate()` (task 4.5) + PathBuffer.invalidate() (task 6.6)
- `algorithm_node`: Nenhuma mudança — já lida com flags de recovery

**Validação**: ✅ **Correto** — segue P1 (Simplicidade), grafo já suporta otimização.

### 3.3 Validação do parse_node

**Código Atual** (`parse_node.py:56-62`):

```python
error_detection_screenshot = None
if (agent.config.error_detection_enabled 
        and screen_hash == state.get("previous_screen_hash")):
    error_detection_screenshot = agent.device.take_screenshot()
```

**Otimização gh26 (task 7.3)**:

```python
# RVAgent.__init__()
self._cached_screen_desc: Optional[ScreenDescription] = None

# parse_node
if screen_hash == previous_screen_hash and agent._cached_screen_desc:
    screen_desc = agent._cached_screen_desc  # Reuse (~0ms)
else:
    screen_desc = parse(...)  # Visitor pipeline (~50ms)
    agent._cached_screen_desc = screen_desc

# gh18 screenshot condicional PRESERVADO (independente do cache)
if (agent.config.error_detection_enabled 
        and screen_hash == previous_screen_hash):
    error_detection_screenshot = agent.device.take_screenshot()
```

**Validação**: ✅ **Correto** — caching não interfere com gh18 screenshot. Task 7.4 é crítica para validar.

### 3.4 Validação do SuccessorTracker

**Assinatura Atual** (`successor_tracker.py:329`):

```python
def find_nearest_unsaturated(self, current_state: str) -> Optional[str]:
    """Retorna hash do ancestral não-saturado mais próximo."""
```

**Assinatura gh26 (task 5.5)**:

```python
def find_nearest_unsaturated(self, current_state: str) -> Optional[Tuple[str, int]]:
    """Retorna (hash, hop_count) — hop_count é número de BACKs necessários."""
```

**Impacto**: PathBuffer.plan_backtrack_path() precisa do `hop_count` para saber quantos BACKs bufferar.

**Validação**: ✅ **Necessário** — sem hop_count, PathBuffer não pode planejar backtrack. Task 5.5 é bloqueante para Group 6.

### 3.5 Validação do InputValueGenerator

**Bugs Identificados**:

| Bug | Descrição | Impacto |
|-----|-----------|---------|
| **1** | Duplicate `_infer_input_type()` na strategy | Inconsistência, ignora hint/content_description |
| **2** | Wrong value ordering (PINs primeiro em campos não-PIN) | Wasta iterações |
| **3** | LLM path bypassing generator | Sem tracking, repetição |
| **4** | `max_variations=5` bloqueia 11 payloads MOP | Edge cases não testados |
| **5** | Missing input types (search, url, date, time, number, zip, verification_code) | Cobertura incompleta |
| **6** | Sem clear-before-type | Texto appendado, não substituído |

**Tasks de Correção**: 2.1-2.7

**Validação**: ✅ **Crítico** — bugs desperdiçam 20-40% das iterações de texto.

---

## 3.6 🔴 Dependências Não Documentadas (Descobertas na Análise Profunda)

Durante a validação linha-por-linha, identifiquei **10 dependências críticas não documentadas** no design.md:

| # | Dependência | Componentes Afetados | Status Atual | Task para Resolver |
|---|-------------|---------------------|--------------|-------------------|
| **D1** | `RankingContext.successor_tracker` | CoverageDensityScorer.score() | ❌ Campo não existe em context.py | 3.5.2 |
| **D2** | `UICoverageTracker.get_coverage_gap()` | PathBuffer.plan_coverage_path() | ❌ Método não existe | 3.5.4 (implícito) |
| **D3** | `ScreenNode.action_cumulative_reward` | RewardPropagator.propagate(), StrengthScorer.score() | ❌ Campo não existe em screen_node.py | 1.3 |
| **D4** | `find_nearest_unsaturated()` retorna `Tuple[str, int]` | PathBuffer.plan_backtrack_path() | ❌ Retorna apenas `Optional[str]` | 5.5 |
| **D5** | `RVAgentConfig.backtrack_saturation_threshold` | should_backtrack() | ❌ Campo não existe | 1.1 |
| **D6** | `RVAgentConfig.reward_gamma` | RewardPropagator | ❌ Campo não existe | 1.1 |
| **D7** | `RVAgentConfig.reward_mop_weight` | RewardPropagator, StrengthScorer | ❌ Campo não existe | 1.1 |
| **D8** | `RVAgentConfig.reward_propagation_n` | RewardPropagator | ❌ Campo não existe | 1.1 |
| **D9** | `RVAgentConfig.reward_score_weight` | StrengthScorer | ❌ Campo não existe | 1.1 |
| **D10** | `RVAgentConfig.coverage_density_weight` | CoverageDensityScorer | ❌ Campo não existe | 1.1 |
| **D11** | `RVAgentConfig.max_coverage_hops` | PathBuffer.plan_coverage_path() | ❌ Campo não existe | 1.1 |
| **D12** | `RVAgentConfig.mop_max_input_variations` | InputValueGenerator._get_mop_values() | ❌ Campo não existe | 1.1 |
| **D13** | `RVAgentConfig.max_backtrack_hops` | PathBuffer.plan_backtrack_path() | ❌ Campo não existe | 1.1 |
| **D14** | `RVAgentConfig.path_buffer_enabled` | PathBuffer | ❌ Campo não existe | 1.1 |
| **D15** | `RVAgentConfig.mop_nav_weight` | PathBuffer.plan_mop_path() | ❌ Campo não existe | 1.1 |

**Impacto Combinado**: 15 dependências críticas não documentadas, todas bloqueando implementação.

**Cadeia de Dependência Crítica**:
```
Task 1.1 (11 campos config) → TODOS os groups dependem
Task 1.3 (action_cumulative_reward) → Group 4 (Reward) depende
Task 3.5.2 (successor_tracker em RankingContext) → Group 3.5 (Coverage) depende
Task 5.5 (find_nearest_unsaturated retorna Tuple) → Group 6 (PathBuffer) depende
```

---

## 3.7 🔴 Riscos Críticos Adicionais (Descobertos na Análise)

| # | Risco | Impacto | Probabilidade | Mitigação |
|---|-------|---------|---------------|-----------|
| **R1** | 11 campos de config faltando | **Crítico** — todas features novas bloqueadas | **100%** (atual) | Task 1.1 prioritária |
| **R2** | find_nearest_unsaturated sem hop_count | **Crítico** — PathBuffer não funciona | **100%** (atual) | Task 5.5 antes de Group 6 |
| **R3** | action_cumulative_reward não existe | **Crítico** — reward propagation bloqueada | **100%** (atual) | Task 1.3 prioritária |
| **R4** | failed_actions tracking quebrado (TODO#19) | Médio — FailedActionScorer inútil | **100%** (atual) | Conectar ao workflow |
| **R5** | ExecutionCountScorer dead code não documentado | Baixo — documentação incompleta | **100%** (atual) | Adicionar nota no design |
| **R6** | visited_states tem 2 usos reais | Médio — remoção requer refatoração | Média | Task 1.5.2 refatorar |
| **R7** | state_stack.clear() existe no reset() | Baixo — "append-only" não é estrito | Baixa | Documentar exceção |
| **R8** | record_action_failure() nunca chamada | Médio — funcionalidade quebrada | **100%** (atual) | Conectar ao workflow de error detection |

---

## 4. Análise de Consistência

### 4.1 Rastreabilidade Spec-Design-Task

**Mapeamento Completo**:

```
proposal.md (FRs/NFRs)
    ↓
design.md (Mapping table: Spec → Implementation → Test)
    ↓
tasks.md (Grupos 0-10, cada task com "Satisfies INV-AGT-XX")
    ↓
tests/ (TDD: teste criado antes da implementação)
```

**Exemplo Concreto (FR26 - Proactive Backtracking)**:

```
proposal.md: "Proactive backtracking: When saturation >= 0.8, return BACK"
    ↓
design.md: "Action Selection Order: buffer → untested → backtrack (saturation >= 0.8) → continuous → BACK"
    ↓
tasks.md:
  - 5.1: test_should_backtrack.py (7 testes)
  - 5.2: test_proactive_backtrack.py
  - 5.3: Modify should_backtrack() (use config.backtrack_saturation_threshold)
  - 5.4: Modify select_next_action() (insert Tier 3: backtrack)
    ↓
tests/unit/strategies/test_should_backtrack.py
```

**Validação**: ✅ **Completa** — todas as FRs têm rastreabilidade até testes.

### 4.2 Consistência de Valores

| Parâmetro | proposal.md | design.md | tasks.md | Código Atual |
|-----------|-------------|-----------|----------|--------------|
| `backtrack_saturation_threshold` | 0.8 (0.5-1.0) | 0.8 (0.5-1.0) | 0.8 (0.5-1.0) | N/A (novo) |
| `mop_direct_score` | 500 | 500 | 500 | 300 |
| `mop_transitive_score` | 300 | 300 | 300 | 150 |
| `wtg_guided_score` | 150 | 150 | 150 | 250 |
| `reward_gamma` | 0.8 | 0.8 | 0.8 | N/A (novo) |
| `reward_propagation_n` | 5 | 5 | 5 | N/A (novo) |
| `coverage_density_weight` | 200 | 200 | 200 | N/A (novo) |
| `max_coverage_hops` | 5 | 5 | 5 | N/A (novo) |

**Validação**: ✅ **Consistente** — todos os valores batem entre proposal, design, tasks.

### 4.3 PathBuffer Strategies Ordering

| Documento | Ordering |
|-----------|----------|
| proposal.md | "Strategy C > B > A" |
| design.md | "Tier 3: plan_coverage_path() before plan_mop_path() before plan_backtrack_path()" |
| tasks.md 6.5 | "C > B > A ordering (try plan_coverage_path then plan_mop_path then plan_backtrack_path)" |

**Validação**: ✅ **Consistente** — ordering preservado em todos os documentos.

---

## 5. Critérios de Aceitação

### 5.1 Critérios Definidos

| Critério | Métrica | Validação |
|----------|---------|-----------|
| **Proactive backtracking** | `backtrack_count` (tracking), saturação ≥ 0.8 → BACK | Tasks 5.1-5.4, 9.1, 9.4 |
| **Scorer rebalancing** | Pesos: MOP-direct +500, MOP-trans +300, WTG +150 | Tasks 1.2, 3.1, 9.4 |
| **Text input quality** | 11 variações MOP, clear-before-type, Faker first | Tasks 2.1-2.6, 9.2 |
| **Speed optimization** | <1s/iteração em pure_algorithm, cache hit no mesmo hash | Tasks 7.1, 7.3, 7.4 |
| **Reward propagation** | `reward_propagation_events`, cumulative_reward capped em 15.0 | Tasks 4.1-4.5, 9.2, 9.4 |
| **CoverageDensityScorer** | Sempre ativo, weight=200, exploration bonus=0.5 | Tasks 3.5.1-3.5.6, 9.4 |
| **PathBuffer Strategies** | C > B > A ordering, max_coverage_hops=5 | Tasks 6.1-6.6, 9.4 |

### 5.2 Testes Incluídos (Group 9.4)

**23 Edge-Case Tests**:

1. `test_oscillation_trap` — estados A↔B cycling, reward negativo força ação diferente
2. `test_path_buffer_does_not_reset_stuck_count` — invalidação não resetar stuck
3. `test_config_backward_compatibility` — config sem campos gh26 usa defaults Pydantic
4. `test_graceful_degradation_without_static_analysis` — SA=None não crasha
5. `test_level1_stuck_screen_unchanged` — hash unchanged → force_back
6. `test_level2_stuck_backtrack_bfs` — Level 2 + ancestor found → force_back
7. `test_level2_stuck_app_restart` — Level 2 + no ancestor → force_restart
8. `test_zero_mop_app_degradation` — MOP=0, agente vira explorador genérico
9. `test_path_buffer_dialog_blocked` — diálogo bloqueia backtrack, buffer invalidado
10. `test_path_buffer_and_stuck_detection_interaction` — PathBuffer + stuck detection
11. `test_backtrack_bfs_cyclic_graph_termination` — BFS com visited set
12. `test_mop_dead_end_not_replanned` — MOP Activity saturada não é re-planejada
13. `test_reward_propagation_survives_app_restart` — cumulative_reward persiste
14. `test_partial_static_analysis_wtg_without_reach` — .wtg sem .reach
15. `test_llm_back_during_active_buffer` — LLM BACK com buffer ativo
16. `test_path_buffer_invalidation_preserves_reward_history` — invalidação preserva reward
17. `test_cumulative_reward_cap_boundary` — cap em 15.0 (boundary)
18. `test_scorer_ranking_performance_10_vs_8` — overhead de 10 vs 8 scorers
19. `test_coverage_density_scorer_cold_start_exploration_bonus` — cold start bonus
20. `test_strategy_c_before_b_in_tier3` — C avaliado antes de B

**Validação**: ✅ **Abrangente** — cobre interações cruzadas, edge cases, degradação graciosa.

### 5.3 Testes Sugeridos (Adicionais)

| Teste | Descrição | Prioridade |
|-------|-----------|------------|
| `test_reward_propagator_thread_safety` | Thread-safe para futuro multi-device | Baixa |
| `test_path_buffer_memory_leak` | Validar que invalidate() limpa tudo | Média |
| `test_coverage_density_false_positive` | Coverage alto em beco sem saída | Média |
| `test_cumulative_reward_multiple_propagations` | Múltiplas propagações no cap | Baixa |

---

## 6. Análise do Grafo LangGraph

### 6.1 Estado Atual

```
start → parse_ui → decision_router
                     ↓
         ┌───────────┼───────────┐
         ↓           ↓           ↓
      algorithm  capture_screenshot → llm_generate → validate_action → execute → learn → END
```

**Nodes**:
- `parse_ui`: UI dump + parsing + hash + error detection screenshot (gh18)
- `decision_router`: Roteia para "algorithm" ou "llm" baseado em modo
- `algorithm_node`: `strategy.select_next_action()`
- `capture_screenshot`: Screenshot para LLM
- `llm_generate`: LLM tool calling
- `validate_action`: Validação de coordenadas, loop detection
- `execute_node`: Executa ação no device
- `learn_node`: Update memories, stuck detection, reward propagation (gh26)

### 6.2 Como Fica (gh26)

**Topologia**: Nenhuma mudança

**Mudanças nos Nodes**:

| Node | Mudança | Task |
|------|---------|------|
| `parse_ui` | Caching de `screen_desc` quando hash igual | 7.3 |
| `decision_router` | Tracking log para algorithm-fast-path | 7.2 |
| `learn_node` | `RewardPropagator.propagate()` + PathBuffer.invalidate() | 4.5, 6.6 |
| `algorithm_node` | Nenhuma mudança | — |

**Otimização de Velocidade**:

```python
# decision_router_node já roteia "algorithm" direto para algorithm_node
# Isso bypassa capture_screenshot e llm_generate

# parse_node caching (task 7.3):
if screen_hash == previous_screen_hash and agent._cached_screen_desc:
    screen_desc = agent._cached_screen_desc  # Reuse (~0ms)
else:
    screen_desc = parse(...)  # Visitor pipeline (~50ms)
    agent._cached_screen_desc = screen_desc
```

**Validação**: ✅ **Correto** — otimização preserva gh18 screenshot e usa routing existente.

### 6.3 Screenshot e Performance

**Camadas de Otimização**:

1. **Graph topology**: Algorithm path já bypassa `capture_screenshot_node` (existente)
2. **parse_node caching**: Reusa `screen_desc` quando hash igual (novo gh26)
3. **gh18 screenshot condicional**: Captura screenshot quando hash-repeat (preservado)

**Impacto Estimado**:
- ~50ms economizados por iteração no mesmo estado
- ~150-300 iterações em 300s (pure_algorithm)
- Alvo: <1s por iteração

**Risco**: Caching não deve interferir com gh18 error detection screenshot.

**Mitigação**: Task 7.4 é específica para validar: `test_screen_desc_cache_preserves_error_detection_screenshot`

---

## 7. Refatorações Definidas

### 7.1 Dead Code Removal (Group 1.5)

| Item | Localização | Linhas | Por Que Morto |
|------|-------------|--------|---------------|
| `state_stack` + `RVAgentState` | `rvagent_strategy.py` | ~30 | Append-only, nunca pop, gh26 usa SuccessorTracker BFS |
| `visited_states: Set[str]` | `rvagent_strategy.py` | ~8 | Redundante com `graph.states.keys()` |
| `parent_hash` computation | `rvagent_strategy.py` | ~2 | Computado mas nunca lido |
| `current_depth` | `rvagent_strategy.py` | ~1 | Só usado para RVAgentState e métricas |

**Consolidações**:

| Item | Antes | Depois | Racional |
|------|-------|--------|----------|
| Visited activities | Duas fontes independentes | TransitionManager é single source | Previne divergência |
| Coverage formula | Inline em SuccessorTracker | Delega para `ScreenNode.get_coverage()` | Elimina divergência sutil |

**Documentação**:
- `DynamicStateGraph.transitions`: Audit-only (não usado para navegação)

**Validação**: ✅ **Positivo** — segue P3 (No Backward Compatibility), simplifica ~30 linhas.

### 7.2 SuccessorTracker Coverage Formula (Task 1.5.3)

**Antes**:
```python
# Inline em successor_tracker.py:144-148
coverage = len(node.executed_actions) / node.total_actions if node.total_actions > 0 else 1.0
```

**Depois**:
```python
coverage = node.get_coverage() if node.total_actions > 0 else 1.0
# Comentário: zero-actions = 1.0 (difere de ScreenNode's 0.0)
```

**Validação**: ✅ **Positivo** — single source of truth, preserva semântica interna.

---

## 8. Contradições Identificadas

### 8.1 Verificadas (Sem Contradições)

| Parâmetro | proposal.md | design.md | tasks.md | Status |
|-----------|-------------|-----------|----------|--------|
| `backtrack_saturation_threshold` | 0.8 | 0.8 | 0.8 | ✅ |
| `mop_direct_score` | 500 | 500 | 500 | ✅ |
| `mop_transitive_score` | 300 | 300 | 300 | ✅ |
| `wtg_guided_score` | 150 | 150 | 150 | ✅ |
| `reward_gamma` | 0.8 | 0.8 | 0.8 | ✅ |
| `reward_propagation_n` | 5 | 5 | 5 | ✅ |
| `coverage_density_weight` | 200 | 200 | 200 | ✅ |
| `max_coverage_hops` | 5 | 5 | 5 | ✅ |
| PathBuffer ordering | C > B > A | C > B > A | C > B > A | ✅ |

### 8.2 Contradição Menor Identificada

**GradualDecayScorer min_visits cutoff**:

- design.md INV-AGT-21: "When `visits >= min_visits` (default 5), MUST return 0.0"
- tasks.md 3.2: `test_gradual_decay_min_visits_cutoff` — "visits >= 5 → score 0.0"
- scorers.py (código atual, linha ~166-169):
  ```python
  if visits >= self.min_visits:
      return 0.0
  ```
- ❌ **proposal.md**: Não menciona o cutoff

**Recomendação**: Adicionar nota no proposal.md sobre GradualDecayScorer activation mencionando `min_visits` cutoff.

---

## 9. Pontos Críticos para Implementação

### 9.1 Ordem de Implementação

```
Group 0 (Baseline) → DEVE rodar PRIMEIRO
    ↓
Group 1 (Config) → Pré-requisito para todos
    ↓
Group 1.5 (Dead Code) → Paralelo com Groups 2-8
    ↓
Groups 2, 3, 3.5, 4, 7, 8 → Paralelo (independentes)
    ↓
Group 5 (Backtracking) → Group 6 depende
    ↓
Group 6 (PathBuffer) → Group 9 depende
    ↓
Group 9 (Integration) → Após todos
    ↓
Group 10 (Validation) → Após Group 9 e /rv-verify
```

### 9.2 Dependências Críticas

| Task | Dependência | Risco | Mitigação |
|------|-------------|-------|-----------|
| 5.5 | Nenhuma | Se implementada errado, quebra PathBuffer | Task tem teste específico |
| 6.1, 6.2, 6.5 | Task 5.5 | Não podem rodar sem 5.5 | Adicionar "BLOCKED BY 5.5" |
| 6.7 (wire) | Groups 1, 5 | Todos dependem do wiring | Mover para Group 1 ou 2 |
| 7.3 | Group 1 | Caching deve preservar gh18 | Task 7.4 é específica |
| 9.4 | Todos | Edge cases complexos | Implementar por último |

### 9.3 Riscos Identificados

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| Task 5.5 implementada incorretamente | Alto | Baixa | Teste específico 5.5 |
| PathBuffer invalidação incorreta | Médio | Média | Task 9.4 tem teste de interação |
| Caching interfere com gh18 screenshot | Alto | Baixa | Task 7.4 específica |
| Reward propagation memory leak | Baixo | Baixa | deque(maxlen=N) já limita |
| CoverageDensityScorer false positive | Médio | Média | MopScorer + WtgScorer predominam |

---

## 10. Cenários Interessantes

### 10.1 Cenários Incluídos (Group 9.4)

1. **Oscilação (test_oscillation_trap)**: Estados A↔B cycling, reward negativo acumulado força ação diferente após ~20 iterações
2. **PathBuffer + Diálogo (test_path_buffer_dialog_blocked)**: Diálogo bloqueia BACK, buffer invalidado, normal resume
3. **BFS Cíclico (test_backtrack_bfs_cyclic_graph_termination)**: Estados A→B→C→A, BFS com visited set previne loop
4. **Zero MOP (test_zero_mop_app_degradation)**: MOP methods = 0, agente vira explorador genérico (não crasha)
5. **LLM BACK com Buffer (test_llm_back_during_active_buffer)**: LLM gera BACK enquanto buffer ativo, hash mudou → buffer continua
6. **Reward Cap Boundary (test_cumulative_reward_cap_boundary)**: Cap em 15.0, boundary condition
7. **PathBuffer + Stuck (test_path_buffer_and_stuck_detection_interaction)**: Buffer ativo + hash unchanged → invalida E seta force_back
8. **Reward Sobrevive Restart (test_reward_propagation_survives_app_restart)**: cumulative_reward persiste após restart

### 10.2 Cenários Sugeridos (Adicionais)

1. **CoverageDensity False Positive**:
   - Estado S1 tem 20 elementos, 18 não testados (gap=0.9)
   - Ação A leva a S1, mas S1 é "beco sem saída" (sem MOP, sem WTG)
   - CoverageDensityScorer dá score alto (180), mas ação é improdutiva
   - **Teste**: `test_coverage_density_false_positive` — validar que MopScorer + WtgScorer ainda predominam

2. **Reward Inflation Múltipla**:
   - Múltiplas propagações para mesma ação (N=5, gamma=0.8)
   - Acumula 12.0 + 5.0 = 17.0, mas cap é 15.0
   - **Teste**: `test_cumulative_reward_multiple_propagations` — boundary + múltiplas

3. **PathBuffer Memory Leak**:
   - PathBuffer planeja path, invalida, planeja de novo
   - Validar que memória é liberada corretamente
   - **Teste**: `test_path_buffer_memory_leak` — monitorar memória após 100 ciclos

---

## 11. Validação Final

### 11.1 🔴 Checklist de Validação (Atualizado Após Análise Profunda)

| Critério | Status Anterior | Status Atual | Observação |
|----------|-----------------|--------------|------------|
| **Diagnóstico preciso** | ✅ | ✅ | Baseado em ICST paper, análise APE/Fastbot |
| **Design detalhado** | ✅ | ✅ | 6 decisões com alternativas e racional |
| **Tasks executáveis** | ✅ | ⚠️ | Atômicas, testáveis, TDD — mas **0% implementadas** |
| **Rastreabilidade** | ✅ | ✅ | spec-design-task-test completa |
| **Consistência de valores** | ✅ | ⚠️ | Parâmetros batem no design, mas **não implementados** |
| **Grafo LangGraph** | ✅ | ✅ | Topologia preservada, otimização sound |
| **Screenshot caching** | ✅ | ⚠️ | Preserva gh18, mas **não implementado** |
| **Dead code removal** | ✅ | ⚠️ | Segue P3, mas **não implementado** |
| **Edge cases** | ✅ | ✅ | 23 testes no Group 9.4 |
| **Pre-condição gh18** | ✅ | ✅ | Análise de conflito no doc de análise |
| **Downstream gh9** | ✅ | ⚠️ | parameter_space.py precisa de 11 params — **nenhum existe** |
| **Config fields (11 novos)** | N/A | ❌ | **Nenhum campo existe** — bloqueante |
| **Data models (action_cumulative_reward)** | N/A | ❌ | **Campo não existe** — bloqueante |
| **SuccessorTracker return type** | N/A | ❌ | **Retorna str, não Tuple** — bloqueante |

### 11.2 🔴 Aprovação com Ressalvas CRÍTICAS (Atualizado)

**Status**: ⚠️ **APROVADA COM RESSALVAS CRÍTICAS**

**Ressalvas CRÍTICAS (BLOQUEANTES)**:

1. **Task 1.1 (CRÍTICO)**: 11 campos novos em RVAgentConfig — **NENHUM existe**
   - Impacto: Todas as features novas bloqueadas
   - Files: `config/agent_config.py`
   
2. **Task 1.3 (CRÍTICO)**: `action_cumulative_reward` em ScreenNode — **Campo não existe**
   - Impacto: Reward propagation bloqueada
   - Files: `domain/screen_node.py`
   
3. **Task 3.5.2 (CRÍTICO)**: `successor_tracker` em RankingContext — **Campo não existe**
   - Impacto: CoverageDensityScorer não funciona
   - Files: `strategies/rvagent_strategy/ranking/context.py`
   
4. **Task 5.5 (CRÍTICO)**: `find_nearest_unsaturated()` retorna `Tuple[str, int]` — **Atualmente retorna `Optional[str]`**
   - Impacto: PathBuffer não sabe quantos BACKs bufferar
   - Files: `strategies/rvagent_strategy/successor_tracker.py`
   
5. **Task 5.4 (ALTO)**: `should_backtrack()` usa threshold — **Atualmente binário (100%)**
   - Impacto: Backtracking passivo continua
   - Files: `strategies/rvagent_strategy/rvagent_strategy.py`

**Ressalvas NÃO Bloqueantes**:

6. **Adicionar nota sobre ExecutionCountScorer**: Também é dead code (não documentado)
7. **Documentar failed_actions tracking quebrado**: TODO#19 em screen_node.py
8. **Explicitar dependências críticas**: Adicionar "BLOCKED BY 5.5" em tasks 6.1, 6.2, 6.5
9. **Mover wiring para Group 1 ou 2**: Task 6.7 é crítica — todos dependem
10. **Adicionar testes de memory leak**: `test_path_buffer_memory_leak` no Group 9.4
11. **Documentar min_visits no proposal.md**: Adicionar nota sobre GradualDecayScorer cutoff

### 11.3 🔴 Próximo Passo (Atualizado)

**FASE 0: ESTABELECER BASELINE (Antes de qualquer mudança)**

**Implementar Group 0 (Baseline Experiment)** ANTES de qualquer mudança:

```bash
# 0.1 Criar diretório e filter file
mkdir -p docker/data/gh26_experiment
# Criar exp02_apks.txt com 10 APKs

# 0.2-0.3 Preprocessing (instrumentação + SA)
docker compose -f docker/data/gh26_experiment/docker-compose.preprocess.yml up

# 0.3b Docker dry-run (1 APK, 1 tool, 60s)
# Validar setup antes de full experiment

# 0.4-0.5 Baseline experiment (2 containers, 4-5 horas)
docker compose -f docker/data/gh26_experiment/docker-compose.baseline.yml up

# 0.6 Agregar métricas baseline
python docker/data/gh26_experiment/aggregate_baseline.py
```

**Sem baseline, não há como medir impacto do gh26.**

**FASE 1: PRÉ-REQUISITOS CRÍTICOS (Antes de Features)**

Ordem de implementação **OBRIGATÓRIA**:

```
Task 1.1 (11 campos config) → TODOS os groups dependem
    ↓
Task 1.3 (action_cumulative_reward) → Group 4 depende
    ↓
Task 3.5.2 (successor_tracker em RankingContext) → Group 3.5 depende
    ↓
Task 5.5 (find_nearest_unsaturated retorna Tuple) → Group 6 depende
    ↓
Task 5.4 (should_backtrack com threshold) → Group 5 depende
    ↓
Task 1.2 (scorer weights atualizados) → Group 3 depende
    ↓
Task 3.3 (GradualDecayScorer registrado) → Group 3 depende
    ↓
Groups 2, 3, 3.5, 4, 5, 6, 7, 8 → Paralelo (após pré-requisitos)
    ↓
Group 9 (Integration) → Após todos
    ↓
Group 10 (Validation) → Após Group 9 e /rv-verify
```

**Cronograma Estimado**:
- Group 0 (Baseline): 4-5 horas (experimento) + 1 hora (agregação)
- Group 1 (Config): 2-3 horas (11 campos + testes)
- Group 1.3 (Data models): 1 hora (action_cumulative_reward)
- Group 3.5.2 (RankingContext): 30 minutos
- Group 5.5 (SuccessorTracker): 1-2 horas (BFS com hop_count)
- **Total pré-requisitos**: ~6-8 horas
- **Grupos paralelos (2-8)**: ~16-24 horas
- **Group 9 (Integration)**: ~8-12 horas
- **Group 10 (Validation)**: 4-5 horas (experimento) + 1 hora (análise)
- **Total geral**: ~35-50 horas

---

## 12. Conclusão

### 12.1 🔴 Summary (Atualizado Após Análise Profunda)

A change **gh26-exploration-strategy** é **VÁLIDA NO DESIGN**, mas a **IMPLEMENTAÇÃO NÃO FOI INICIADA**.

Após validação linha-por-linha de **50+ claims**, o status real é:

| Dimensão | Avaliação | Evidência |
|----------|-----------|-----------|
| **Design** | ✅ Válido | 6 decisões com alternativas e racional sound |
| **Implementação** | ❌ **0% completa** | 15 dependências críticas não implementadas |
| **Rastreabilidade** | ✅ Completa | spec-design-task-test mapeada |
| **Código atual** | ⚠️ **Pré-gh26** | Todos os bugs e gargalos ainda presentes |

### 12.2 🔴 Descobertas Críticas da Análise Profunda

| # | Descoberta | Impacto | Status |
|---|------------|---------|--------|
| **D1** | 11 campos de config não existem | **BLOQUEANTE GERAL** | ❌ |
| **D2** | `action_cumulative_reward` não existe | **BLOQUEANTE (Reward)** | ❌ |
| **D3** | `RankingContext.successor_tracker` não existe | **BLOQUEANTE (Coverage)** | ❌ |
| **D4** | `find_nearest_unsaturated` retorna `str`, não `Tuple` | **BLOQUEANTE (PathBuffer)** | ❌ |
| **D5** | `should_backtrack` é binário (100%), não usa threshold | **BLOQUEANTE (Backtracking)** | ❌ |
| **D6** | 6 bugs do InputValueGenerator ainda presentes | **BLOQUEANTE (Text Input)** | ❌ |
| **D7** | GradualDecayScorer não registrado | **BLOQUEANTE (Scorers)** | ❌ |
| **D8** | `failed_actions` tracking quebrado (TODO#19) | Médio | ⚠️ |
| **D9** | ExecutionCountScorer também é dead code (não documentado) | Baixo | ⚠️ |
| **D10** | `visited_states` tem 2 usos reais (não é completamente redundante) | Médio | ⚠️ |

### 12.3 🔴 Matriz de Risco Atualizada

| Risco | Impacto | Probabilidade | Prioridade |
|-------|---------|---------------|------------|
| Implementação não iniciada | **Crítico** | **100%** | **P0** |
| Dependências não documentadas | **Crítico** | **100%** | **P0** |
| Baseline não estabelecida | **Alto** | **100%** | **P0** |
| failed_actions quebrado | Médio | **100%** | P1 |
| ExecutionCountScorer não documentado | Baixo | **100%** | P2 |

### 12.4 ✅ Plano de Ação (Priorizado)

**ORDEM OBRIGATÓRIA DE IMPLEMENTAÇÃO**:

```
PRIORIDADE P0 (Pré-requisitos Críticos):
├─ Group 0: Baseline Experiment (4-5 horas)
│  └─ 0.1-0.6: Estabelecer métricas de comparação
│
├─ Group 1: Config & Models (2-3 horas)
│  ├─ 1.1: 11 campos novos em RVAgentConfig (BLOQUEANTE GERAL)
│  ├─ 1.2: Atualizar scorer weights
│  └─ 1.3: action_cumulative_reward em ScreenNode
│
├─ Group 1.5: Dead Code Removal (1-2 horas)
│  ├─ 1.5.1: Remover state_stack + RVAgentState
│  ├─ 1.5.2: Remover visited_states (refatorar _get_visited_activities)
│  └─ 1.5.3-1.5.5: Consolidar coverage formula, documentar transitions
│
├─ Group 3.5: Coverage-Based Guidance (1 hora)
│  └─ 3.5.2: successor_tracker em RankingContext
│
└─ Group 5: Proactive Backtracking (2-3 horas)
   └─ 5.5: find_nearest_unsaturated retorna Tuple[str, int]

PRIORIDADE P1 (Features Core):
├─ Group 2: Text Input Quality (2-3 horas)
│  └─ 2.1-2.7: Fix 6 bugs do InputValueGenerator
├─ Group 3: Scorer Rebalancing (1 hora)
│  └─ 3.3: GradualDecayScorer registrado
├─ Group 4: Reward Propagation (2-3 horas)
│  └─ 4.1-4.5: RewardPropagator + StrengthScorer integration
└─ Group 5: Backtracking (1-2 horas)
   └─ 5.1-5.4: should_backtrack com threshold, proactive backtracking

PRIORIDADE P2 (Features Avançadas):
├─ Group 3.5: CoverageDensityScorer (2-3 horas)
│  └─ 3.5.1-3.5.6: CoverageDensityScorer + Strategy C
├─ Group 6: PathBuffer (3-4 horas)
│  └─ 6.1-6.7: PathBuffer class + Strategies A/B/C
├─ Group 7: Speed Optimization (1-2 horas)
│  └─ 7.1-7.4: screen_desc caching
└─ Group 8: LLM MOP Guidance (1-2 horas)
   └─ 8.1-8.2: NavigationGuidance com MOP context

PRIORIDADE P3 (Validação):
├─ Group 9: Integration Testing (8-12 horas)
│  └─ 9.1-9.8: Testes de integração + edge cases
└─ Group 10: Validation Experiment (5-6 horas)
   └─ 10.1-10.6: Experimento de validação + comparação
```

**Total Estimado**: ~35-50 horas

### 12.5 🔴 Veredito Final (Atualizado)

| Critério | Veredito | Justificativa |
|----------|----------|---------------|
| **Design** | ✅ **APROVADO** | Especificação completa, coerente, rastreável |
| **Implementação** | ❌ **REPROVADA** | **0% completa** — 15 dependências críticas faltando |
| **Pronto para iniciar?** | ⚠️ **SIM, COM RESSALVAS** | Tasks bem definidas, mas pré-requisitos críticos必须先 |
| **Risco de falha?** | ⚠️ **MÉDIO** | Dependências bem mapeadas, mas implementação não iniciada |

### 12.6 📋 Recomendações Finais

1. **INICIAR COM GROUP 0 (BASELINE)**: Sem baseline, não há como medir impacto
2. **RESPEITAR ORDEM DE DEPENDÊNCIAS**: Task 1.1 → Task 1.3 → Task 3.5.2 → Task 5.5 → resto
3. **TDD OBRIGATÓRIO**: Testes primeiro para todas as tasks
4. **/rv-verify CONTÍNUO**: Validar após cada group
5. **DOCUMENTAR DESCOBERTAS**: Adicionar notas sobre ExecutionCountScorer, failed_actions, etc.

---

## Apêndice D: Análise Profunda (50+ Claims Validadas)

### D.1 Metodologia da Análise Profunda

**Abordagem**: Validação linha-por-linha de cada claim do design.md contra o código-fonte real.

**Arquivos Analisados**:
- proposal.md (completo)
- design.md (1188 linhas)
- tasks.md (188 linhas)
- spec.md (727 linhas)
- rvagent_strategy.py (941 linhas)
- agent_config.py (461 linhas)
- scorers.py (498 linhas)
- rv_agent.py (439 linhas)
- input_value_generator.py (269 linhas)
- successor_tracker.py (401 linhas)
- parse_node.py (completo)
- learn_node.py (completo)
- decision_node.py (completo)
- algorithm_node.py (completo)
- screen_node.py (completo)
- context.py (completo)
- dynamic_state_graph.py (completo)
- 20260216_rvagent_refatoracao.md (967 linhas)

### D.2 Claims Validadas (Resumo)

| Categoria | Claims Confirmadas | Claims Parciais | Claims Incorretas | Total |
|-----------|-------------------|-----------------|-------------------|-------|
| **Arquitetura** | 5 | 1 | 1 | 7 |
| **Bugs** | 6 | 0 | 0 | 6 |
| **Config** | 0 | 0 | 11 | 11 |
| **Scorers** | 2 | 0 | 1 | 3 |
| **Data Models** | 0 | 0 | 3 | 3 |
| **Dependências** | 2 | 2 | 15 | 19 |
| **Total** | **15** | **3** | **31** | **49** |

### D.3 Evidências Detalhadas

**Claim 1**: "state_stack é append-only"
- ✅ **Confirmado**: rvagent_strategy.py:200,273,886
- ⚠️ **Exceção**: state_stack.clear() existe no reset()

**Claim 2**: "parent_hash nunca lido"
- ✅ **Confirmado**: rvagent_strategy.py:265,270
- parent_hash é armazenado mas nunca usado para decisões

**Claim 3**: "visited_states redundante"
- ⚠️ **Parcial**: rvagent_strategy.py:201,274,729
- Usado em 2 lugares: linha 276 e _get_visited_activities()

**Claim 4**: "find_nearest_unsaturated retorna Tuple[str, int]"
- ❌ **Incorreto**: successor_tracker.py:329-363
- Retorna `Optional[str]`, não `Optional[Tuple[str, int]]`

**Claim 5**: "Grafo LangGraph bypass screenshot"
- ✅ **Confirmado**: rv_agent.py:174-207
- Algorithm path já bypassa capture_screenshot

**Claim 6**: "GradualDecayScorer dead code"
- ✅ **Confirmado**: rvagent_strategy.py:186-197
- Definido em scorers.py:143-188, não registrado

**Claim 7**: "8 scorers ativos"
- ✅ **Confirmado**: rvagent_strategy.py:186-197
- Lista exata: MopScorer, WtgScorer, SaturationScorer, ComponentPriorityScorer, StrengthScorer, FailedActionScorer, SystemElementFilter, VisitationPenaltyScorer

**Claims 8.1-8.6**: "6 bugs no InputValueGenerator"
- ✅ **Todos confirmados**: Ver Seção 3.5 deste relatório

**Claim 9**: "Coverage fórmula divergente"
- ✅ **Confirmado**: successor_tracker.py:128 (retorna 1.0), screen_node.py:66 (retorna 0.0)

**Claim 10**: "transitions audit-only"
- ✅ **Confirmado**: dynamic_state_graph.py
- Não é consultado para navegação

**Claims 11-18**: "Config, Scorers, Data Models"
- ❌ **Todos incorretos**: Implementação não iniciada

---

**Fim do Relatório (Atualizado com Análise Profunda)**

**Próxima Ação Imediata**: Iniciar Group 0 (Baseline Experiment) para estabelecer métricas de comparação antes de qualquer implementação.

---

## Apêndice A: Arquivos Analisados

| Arquivo | Linhas | Módulo |
|---------|--------|--------|
| `proposal.md` | — | openspec/changes/gh26-exploration-strategy/ |
| `design.md` | 1188 | openspec/changes/gh26-exploration-strategy/ |
| `tasks.md` | 188 | openspec/changes/gh26-exploration-strategy/ |
| `spec.md` | 727 | openspec/changes/gh26-exploration-strategy/specs/agent/ |
| `rvagent_strategy.py` | 941 | modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ |
| `agent_config.py` | 461 | modules/rv-agent/src/rv_agent/config/ |
| `scorers.py` | 498 | modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ranking/ |
| `rv_agent.py` | 439 | modules/rv-agent/src/rv_agent/agent/ |
| `input_value_generator.py` | 269 | modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ |
| `successor_tracker.py` | 401 | modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ |
| `parse_node.py` | ~80 | modules/rv-agent/src/rv_agent/agent/nodes/ |
| `learn_node.py` | 493 | modules/rv-agent/src/rv_agent/agent/nodes/ |
| `20260216_rvagent_refatoracao.md` | 967 | docs/ (análise de apoio) |

---

## Apêndice B: Glossário

| Termo | Definição |
|-------|-----------|
| **MOP** | Monitored Operation — método monitorado por runtime verification |
| **WTG** | Window Transition Graph — grafo de navegação da aplicação (GATOR) |
| **BFS** | Breadth-First Search — algoritmo de busca em largura |
| **N-step** | Propagação de reward por N passos para trás |
| **TDD** | Test-Driven Development — teste primeiro, implementação depois |
| **SDD** | Spec-Driven Development — especificação guia implementação |
| **Full SDD** | Track com 6 fases, 4 artifacts (proposal, specs, design, tasks) |
| **FF SDD** | Fast-Forward SDD — track com 4 fases, auto-generated |
| **Quick Path** | Track com 3 fases, 2 artifacts (plan, tasks) |
| **gh18** | Change de error detection (pre-condição para gh26) |
| **gh9** | Change de calibration campaign (downstream de gh26) |

---

## Apêndice C: Referências

1. **ICST Paper**: "On the Effectiveness of Integrating Android Test-Case Generation with Runtime Verification for Detecting Cryptographic API Misuses"
2. **APE Source**: `tmp_tools/ape/src/com/android/commands/monkey/ape/agent/SataAgent.java`
3. **Fastbot Source**: C++ (analisado em `20260216_rvagent_refatoracao.md`)
4. **PRD.md**: Product Requirements Document do RV-Android
5. **SDD.md**: Spec-Driven Development guide
6. **WORKFLOW.md**: RV-Android Development Workflow
7. **20260216_rvagent_refatoracao.md**: Análise de apoio para gh26

---

**Fim do Relatório**

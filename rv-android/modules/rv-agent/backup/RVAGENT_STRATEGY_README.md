# RVAgent Strategy - Coverage-Optimized Exploration

**Data**: 2025-11-14
**Status**: ✅ Implementação Completa e Integrada
**Estratégia Padrão**: `rvagent` (substituindo `dfs` e `greedy`)

---

## Visão Geral

RVAgentStrategy é a nova estratégia de exploração padrão do RVAgent que resolve problemas críticos das estratégias anteriores (DFS, BFS, Greedy) e maximiza cobertura UI e MOP.

### Problema que Resolve: "Combobox Problem"

**Cenário**:
```
Estado A: Click "Dropdown Settings" → Estado B (menu aberto)
Estado B: Items ["Opção 1", "Opção 2", "Opção 3"]
```

**DFS/Greedy tradicional**:
- Marca "Dropdown Settings" como **executado** após primeiro clique
- **Nunca retorna** para clicar novamente
- Estados B parcialmente explorados (só 1 item testado)

**RVAgentStrategy**:
- **Tracker de Sucessores**: Monitora se Estado B foi completamente explorado
- **Re-habilita ação** "Dropdown Settings" se B ainda tem ações não testadas
- **Garante cobertura completa** de todos os itens do dropdown

---

## Características Principais

### 1. Successor Tracking (Combobox Fix)
- Rastreia mapeamento: `(estado_origem, ação) → estado_destino`
- Calcula cobertura do estado destino: `ações_executadas / total_ações`
- Re-habilita ações se sucessor tem cobertura < 100%

### 2. Plateau Detection (Terminação Automática)
- Janela deslizante (default: 10 iterações)
- Rastreia: novos estados descobertos + novos métodos MOP
- **Termina automaticamente** quando ambas métricas = 0 por 10 iterações
- Elimina necessidade de `max_iterations` manual

### 3. MOP Prioritization
Ordem de prioridade:
1. **[DM]** - Direct MOP (chama método monitorado diretamente)
2. **[M]** - Transitive MOP (alcança MOP transitivamente)
3. **Untested UI** - Elementos nunca interagidos
4. **Low test count** - Elementos menos testados

### 4. Input Value Variations
- Testa **2-3 valores** por campo de entrada
- Valores regulares: `""`, `"test"`, `"longer test input value"`
- Valores MOP (segurança): `""`, `"0"`, `"-1"`, `"2147483647"`, `"../../../etc/passwd"`, `"' OR '1'='1"`

### 5. Coverage Metrics Unificadas
Agrega métricas de múltiplas fontes:
- **DynamicStateGraph**: Estados, ações, transições
- **UICoverageTracker**: Elementos UI testados
- **CoverageMetrics**: Métodos MOP únicos alcançados

---

## Arquitetura de Componentes

```
RVAgentStrategy
├── SuccessorTracker      (tracking de sucessores - fix combobox)
├── PlateauDetector       (terminação automática)
├── InputValueGenerator   (variações de valores de entrada)
└── CoverageMetrics       (métricas unificadas)
```

### Arquivos Criados

```
modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/
├── __init__.py                     # Exports do pacote
├── rvagent_strategy.py             # Estratégia principal (498 linhas)
├── successor_tracker.py            # Tracker de sucessores (189 linhas)
├── plateau_detector.py             # Detector de plateau (175 linhas)
├── input_value_generator.py       # Gerador de valores (204 linhas)
└── coverage_metrics.py             # Métricas unificadas (177 linhas)
```

### Arquivos Modificados

```
modules/rv-agent/src/rv_agent/
├── strategies/strategy_registry.py    # Registrou rvagent como default
├── config/agent_config.py             # Adicionou plateau_window, max_input_variations
└── core/agent_factory.py              # Passa ui_coverage para estratégia
```

---

## Integração com RVAgent

### Fluxo de Execução

1. **Seleção de Ação** (`_algorithm_node`):
   ```python
   item_action = self.strategy.select_next_action(screen_hash, screen_desc)
   # RVAgentStrategy pré-marca ação e atualiza UI coverage
   ```

2. **Execução** (`_execute_node`):
   ```python
   result = self.tool_executor.execute_action(action)
   if result.get("success"):
       # Registra transição na estratégia
       self.strategy.record_transition(prev_hash, current_hash, item_action)
   ```

3. **Atualização de Memórias** (`_learn_node`):
   ```python
   # RVAgent (não a estratégia!) atualiza memórias
   memory_result = self.memory_coordinator.update_memories(...)
   ```

**Importante**: A estratégia atualiza `DynamicStateGraph` e `UICoverageTracker` diretamente durante seleção/transição. O `MemoryCoordinator` atualiza `ShortTermMemory`, `LongTermMemory`, e `AgentMemory` no nó `_learn`.

---

## Configuração

### RVAgentConfig

```python
RVAgentConfig(
    # Estratégia (DEFAULT = "rvagent")
    strategy="rvagent",

    # Parâmetros RVAgent
    plateau_window=10,          # Iterações sem progresso para plateau
    max_input_variations=3,     # Valores por campo de entrada

    # Outros configs...
    agent_mode="pure_algorithm",  # Ou "multimode", "llm_only"
    llm_provider="hf_direct",     # HuggingFace Transformers Direct
    llm_model="./models/qwen3-vl-4b-fp8",
    timeout=180,
    device_id="emulator-5554"
)
```

### Estratégias Disponíveis

Via `StrategyRegistry`:
- `"rvagent"` ⭐ - **Default** (coverage-optimized DFS)
- `"dfs"` - Depth-First Search tradicional
- `"bfs"` - Breadth-First Search
- `"greedy"` - Greedy exploration
- `"simulated_annealing"` - Simulated Annealing
- `"genetic_algorithm"` - Genetic Algorithm

---

## Testes

### Testes Unitários

```bash
# Componentes individuais
cd modules/rv-agent
poetry run python tests/test_rvagent_strategy.py
```

**Cobertura dos testes**:
- ✅ SuccessorTracker: Registro, cobertura, re-habilitação
- ✅ PlateauDetector: Detecção, janela, MOP tracking
- ✅ InputValueGenerator: Valores regulares, MOP, exaustão
- ✅ CoverageMetrics: Agregação UI + MOP + estados
- ✅ RVAgentStrategy: Seleção, transição, priorização MOP

### Testes de Integração (Emulador)

#### 1. Pure Algorithm (Sem LLM)

```bash
cd /home/pedro/desenvolvimento/workspaces/.../rv-android
poetry run python test_rvagent_pure_algorithm_cryptoapp.py
```

**Configuração**:
- Modo: `pure_algorithm` (100% RVAgent, 0% LLM)
- Estratégia: `rvagent`
- Duração: 180s (3 minutos)
- App: CryptoApp

**Métricas Coletadas**:
- Estados visitados
- Ações executadas
- UI coverage (elementos testados/descobertos)
- MOP coverage (métodos únicos)
- **Plateau**: Detectado? Iterações sem progresso
- **Successor Tracking**: Ações re-habilitadas
- **Input Variations**: Valores testados

#### 2. Multimode (LLM + RVAgent)

```bash
poetry run python test_rvagent_multimode_cryptoapp.py
```

**Configuração**:
- Modo: `multimode` (70% LLM, 30% RVAgent)
- Estratégia: `rvagent`
- LLM: HuggingFace Transformers Direct (Qwen3-VL-4B-FP8)
- Duração: 180s (3 minutos)

**Métricas Coletadas**:
- Distribuição LLM vs Algorithm
- Fallback rate
- LLM tokens e latência
- Coverage (UI + MOP)
- Plateau detection
- Successor tracking

---

## Próximos Passos

### Fase 1: Validação (Em Progresso)

1. ✅ **Testes Unitários**: Componentes individuais
2. ⏳ **Teste Pure Algorithm**: Validar estratégia isoladamente (sem LLM)
3. ⏳ **Teste Multimode**: Validar integração LLM + RVAgent

### Fase 2: Benchmarking (Após Validação)

4. ⏳ **5 Apps Benchmark**: Testar com 5 apps representativos (300s cada)
   ```python
   # Exemplo:
   TEST_APPS = [
       "br.unb.cic.cryptoapp",
       "com.amnesica.kryptey",
       "org.cryptomator.lite",
       "com.securefilemanager.app",
       "com.rafapps.simplenotes"
   ]
   ```

5. ⏳ **Dataset Completo**: Testar com 28 APKs do dataset

### Fase 3: Comparação (Após Benchmarking)

6. ⏳ **DFS vs RVAgent**: Comparar cobertura e detecção de combobox
7. ⏳ **Greedy vs RVAgent**: Comparar priorização MOP
8. ⏳ **Análise de Métricas**: Coverage rate, tempo médio, plateau efficiency

---

## Exemplo de Uso

### Pure Algorithm (Exploração Sistemática)

```python
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Criar config para pure algorithm
config = RVAgentConfig(
    package_name="br.unb.cic.cryptoapp",
    agent_mode="pure_algorithm",  # Sem LLM
    strategy="rvagent",           # RVAgent strategy
    plateau_window=10,            # Plateau após 10 iterações
    max_input_variations=3,       # 3 valores por campo
    timeout=180,
    device_id="emulator-5554"
)

# Criar agent
agent = AgentFactory.create_agent(config)

# Executar
results = agent.run()

# Análise
print(f"Estados: {results['states_visited']}")
print(f"Ações re-habilitadas: {results['successor_tracking']['actions_re_enabled']}")
print(f"Plateau: {results['plateau']['plateau_reached']}")
```

### Multimode (LLM + RVAgent Híbrido)

```python
# Config multimode
config = RVAgentConfig(
    package_name="br.unb.cic.cryptoapp",
    agent_mode="multimode",       # LLM + Algorithm
    llm_probability=0.7,          # 70% LLM, 30% RVAgent
    strategy="rvagent",
    llm_provider="hf_direct",     # HuggingFace Direct
    llm_model="./models/qwen3-vl-4b-fp8",
    prompt_version="v13",
    plateau_window=10,
    timeout=180
)

agent = AgentFactory.create_agent(config)
results = agent.run()

# Análise
print(f"LLM: {results['llm_executed']} ({results['distribution']['llm_percentage']:.1f}%)")
print(f"Algorithm: {results['algorithm_chosen']} ({results['distribution']['algorithm_percentage']:.1f}%)")
print(f"MOP Methods: {results['coverage']['mop_methods_reached']}")
```

---

## Referências

### Documentação
- `modules/rv-agent/docs/LOOP.md` - Problemas com Ollama (loop bug)
- `modules/rv-agent/docs/LOOP_vllm.md` - Migração para HuggingFace

### Código
- `src/rv_agent/strategies/rvagent_strategy/` - Implementação completa
- `src/rv_agent/core/rv_agent.py` - Integração com workflow LangGraph
- `src/rv_agent/memory/memory_coordinator.py` - Atualização de memórias

### Testes
- `tests/test_rvagent_strategy.py` - Testes unitários
- `test_rvagent_pure_algorithm_cryptoapp.py` - Teste sem LLM
- `test_rvagent_multimode_cryptoapp.py` - Teste híbrido

---

## Status da Implementação

| Componente | Status | Linhas | Testes |
|------------|--------|--------|---------|
| SuccessorTracker | ✅ Completo | 189 | ✅ Unitários |
| PlateauDetector | ✅ Completo | 175 | ✅ Unitários |
| InputValueGenerator | ✅ Completo | 204 | ✅ Unitários |
| CoverageMetrics | ✅ Completo | 177 | ✅ Unitários |
| RVAgentStrategy | ✅ Completo | 498 | ✅ Unitários |
| Integração Factory | ✅ Completo | - | ⏳ Emulador |
| Integração Config | ✅ Completo | - | ⏳ Emulador |
| Teste Pure Algorithm | ✅ Criado | - | ⏳ Executar |
| Teste Multimode | ✅ Criado | - | ⏳ Executar |
| Benchmark 5 Apps | ⏳ Pendente | - | ⏳ Pendente |
| Dataset Completo | ⏳ Pendente | - | ⏳ Pendente |

**Total**: 1,243 linhas de código + documentação + testes

---

## Contato e Suporte

- **Autor**: Claude Code + Pedro (Doutorado UnB)
- **Data**: 2025-11-14
- **Versão**: 1.0.0 (Initial Release)

Para dúvidas ou problemas, consulte os arquivos de documentação ou execute os testes de validação.

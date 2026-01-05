# RVAgent Refactoring Plan
**Data**: 2025-11-07
**Objetivo**: Refatorar RVAgent para simplicidade, elegância e modularidade

---

## 🎯 Princípios Fundamentais

### ✅ DECIDIDO
1. **Sem código legado**: Todas as alterações devem ser completas - código antigo será removido/sobrescrito
2. **Sem adapters de compatibilidade**: Não manter interfaces antigas por compatibilidade
3. **Backup de arquivos antigos**: Mover para `modules/rv-agent/backup/2025-11-07_pre-refactoring/`
4. **Simplicidade acima de tudo**: Cada componente deve ter uma responsabilidade clara
5. **Testes devem passar**: Validação em cada fase com `test_pure_dfs_cryptoapp.py` e `test_multimode_cryptoapp.py`

---

## 📊 Análise da Situação Atual

### Estado do rv_agent.py

**Estatísticas**:
- **Total de linhas**: 1,830 linhas (73KB)
- **Complexidade**: Classe monolítica com 35+ métodos
- **Densidade de código**: Alta - arquivo único gerencia toda a orquestração

**Responsabilidades Misturadas** (Violação do Princípio de Responsabilidade Única):

| Responsabilidade | % Código | Linhas | Métodos Principais |
|-----------------|----------|--------|-------------------|
| LangGraph Workflow | 15% | ~270 | `_build_agent_graph()`, `run()` |
| LLM Interaction | 20% | ~365 | `_assistant_node()`, `_build_stateless_message()` |
| UI Parsing | 15% | ~275 | `_parse_ui_node()`, `_format_ui_elements()` |
| Screenshot | 5% | ~90 | `_capture_screenshot_node()` |
| Decision Routing | 10% | ~180 | `_decision_router_node()`, `_validation_router_node()` |
| Tool Execution | 10% | ~180 | `_execute_tools_node()` |
| Memory Management | 15% | ~275 | `_learn_node()` |
| Loop Detection | 10% | ~180 | `_count_consecutive_actions()` |

**Code Smells Identificados**:
1. ❌ **God Class**: Classe única com muitas responsabilidades
2. ❌ **Long Method**: Vários métodos excedem 100 linhas
3. ❌ **Feature Envy**: Manipulação excessiva de objetos externos
4. ❌ **Primitive Obsession**: Uso pesado de dicts em vez de objetos de domínio
5. ❌ **Message Chains**: Navegação profunda em estruturas aninhadas

---

## 🗑️ Arquivos para Backup

### ✅ DECIDIDO: Lista validada

#### Categoria A: Testes Legados (85 arquivos)

**Deletar após backup**:
```
test_rvagent_basic.py
test_validation_framework.py
test_stateless_cryptoapp.py
test_stateless_cryptoapp_fixed.py
test_all_14_apps.py
test_exploration_quality.py
test_debug_unknown.py
test_tool_calling_isolated.py
test_json_parser.py
test_integrated_json_parser.py
test_json_parser_all_apps.py
test_json_parser_detailed.py
test_type_text_fix.py
test_real_emulator.py
test_qwen3vl_tools.py
test_qwen3vl_langgraph.py
test_qwen3vl_multiapp.py
test_v10_qwen3vl_cryptoapp.py
test_v10_baseline_dataset_10apps.py
test_transition_debug.py
test_qwen3vl_coordinate_validation.py
```

**Manter (Testes atuais)**:
```
✅ test_pure_dfs_cryptoapp.py
✅ test_multimode_cryptoapp.py
✅ test_multimode_fix_validation.py
```

#### Categoria B: Diretórios de Resultados Antigos

```
v5_all_29_apps_results/
v7_all_29_apps_results/
v7_cryptoapp_results/
v8_cryptoapp_results/
validation_old/
validation_results/
validation_results_all_apps/
validation_results_debug/
exploration_quality_results/
debug_unknown_results/
rvagent_results/
```

#### Categoria C: Scripts de Análise

```
analyze_coordinates.py
analyze_base64_image.py
analyze_tool_distribution.py
analyze_detailed_results.py
analyze_deep_insights.py
analyze_validation_issues.py
analyze_validation_results.py
analyze_debug_logs.py
compare_improvements.py
coordinate_visualizer.py
deep_investigation.py
extract_llm_responses.py
parse_tool_distribution.py
```

#### Categoria D: Documentação Obsoleta

```
ANALISE_UNKNOWN_F.md
ANALISE_DEBUG_COMPLETA.md
V5_TOOLCALLING_ANALYSIS.md
V5_OPTION_B_ANALYSIS.md
V5_SUCCESS_SUMMARY.md
V5_FULL_29_APPS_ANALYSIS.md
SOLUTION_FINAL.md
FINAL_INVESTIGATION_REPORT.md
VALIDATION_V8_ANALYSIS_REPORT.md
DEBUG_LOG_ANALYSIS_REPORT.md
FULL_RESOLUTION_TEST_ANALYSIS.md
```

**Manter**:
```
✅ README.md
✅ TOOLS_LANGGRAPH.md
✅ AUTONOMOUS_EVOLUTION_SUMMARY.md
✅ 20251028.md, 20251028_plano.md (documentos recentes)
```

#### Categoria E: Arquivos JSON de Resultados Antigos

```
test_*_results.json (todos exceto baseline recentes)
expanded_validation_results_*.json
real_emulator_validation_results_*.json
qwen3vl_10apps_results.json
rv_agent_test_results.json
```

---

## 🏗️ Arquitetura Proposta

### Nova Estrutura de Módulos

```
rv-agent/src/rv_agent/
├── core/
│   ├── rv_agent.py              [REDUZIDO: 400-500 linhas]  ← Apenas orquestração
│   ├── device_interface.py      [MANTER]
│   ├── dynamic_state_graph.py   [MANTER]
│   └── coordinate_converter.py  [MANTER]
│
├── llm/                          [NOVO]
│   ├── llm_client.py      [~300 linhas] - Invocação LLM + tool calling
│   ├── prompt_builder.py        [~200 linhas] - Construção de mensagens
│   └── tools/                   [MANTER]
│
├── ui/                           [NOVO]
│   ├── screen_processor.py          [~350 linhas] - Parsing UI + categorização
│   └── element_formatter.py     [~150 linhas] - Formatação elementos
│
├── vision/                       [NOVO]
│   └── image_handler.py    [~150 linhas] - Captura + otimização
│
├── routing/                      [NOVO]
│   ├── routing_manager.py       [~250 linhas] - Roteamento baseado em modo
│   └── validators.py            [~150 linhas] - Validação LLM + loop detection
│
├── execution/                    [NOVO]
│   └── tool_executor.py         [~200 linhas] - Execução de tools
│
├── strategies/                   [REFATORAR]
│   ├── base_strategy.py         [NOVO: ~150 linhas] - Interface abstrata
│   ├── dfs_strategy.py          [REFATORAR: 550 → 400 linhas]
│   ├── bfs_strategy.py          [NOVO: ~350 linhas]
│   └── registry.py              [NOVO: ~100 linhas] - Registro de estratégias
│
├── memory/
│   ├── memory_coordinator.py    [NOVO: ~200 linhas] - Coordenação unificada
│   ├── agent_memory.py          [MANTER]
│   ├── long_term.py             [MANTER]
│   ├── short_term.py            [MANTER]
│   └── ui_coverage.py           [MANTER]
│
└── validation/                   [MANTER]
```

**Redução Esperada**: rv_agent.py de 1,830 → ~400 linhas (78% redução)

---

## 🔧 Componentes a Extrair

### ✅ DECIDIDO: Ordem e detalhes definidos

### Prioridade 1: LLM Orchestrator (ALTO IMPACTO)

**Novo Arquivo**: `rv_agent/llm/llm_client.py`

**Responsabilidades**:
- Invocação LLM com tool calling
- Construção de prompts e mensagens
- Progressive sampling (mecanismo de retry)
- Parsing de tool calls (nativo + fallback JSON/XML)
- Rastreamento de tokens

**Métodos Extraídos**:
- `_assistant_node()` → `invoke_llm()`
- `_build_stateless_message()` → `build_messages()`
- Lógica de binding de tools → `setup_llm()`

**Benefícios**:
- ✅ Isola código específico de LLM
- ✅ Facilita testes de interação LLM
- ✅ Simplifica engenharia de prompts
- ✅ Permite troca de backend LLM

**Interface Proposta**:
```python
class LLMClient:
    def __init__(self, config, tools):
        self.config = config
        self.llm = self._setup_llm()
        self.tools = tools

    def invoke_llm(
        self,
        screen_desc: ScreenDescription,
        screenshot_path: str,
        memory_summaries: Dict[str, str],
        retry_count: int = 0
    ) -> LLMResponse:
        """Invoke LLM with context and return parsed response."""
        pass
```

---

### Prioridade 2: UI Processor (ALTO IMPACTO)

**Novo Arquivo**: `rv_agent/ui/screen_processor.py`

**Responsabilidades**:
- Captura e parsing de dump UI
- Categorização de elementos (text inputs, spinners, clickable)
- Transformação de coordenadas
- Matching e lookup de elementos

**Métodos Extraídos**:
- `_parse_ui_node()` → `parse_ui_state()`
- `_format_ui_elements()` → `format_elements_for_llm()`
- `_format_element_desc()` → `format_single_element()`
- `_find_item_by_coords()` → `find_element_at_coords()`

**Benefícios**:
- ✅ Centraliza lógica de parsing UI
- ✅ Reutilizável em diferentes agentes
- ✅ Facilita tratamento de coordenadas
- ✅ Melhora testes de transformações UI

**Interface Proposta**:
```python
class ScreenProcessor:
    def __init__(self, device, coordinate_converter):
        self.device = device
        self.converter = coordinate_converter

    def parse_ui_state(self) -> ScreenDescription:
        """Parse current UI state from device."""
        pass

    def format_elements_for_llm(
        self,
        screen_desc: ScreenDescription
    ) -> Dict[str, List[str]]:
        """Format UI elements for LLM consumption."""
        pass
```

---

### Prioridade 3: Screenshot Manager (MÉDIO IMPACTO)

**Novo Arquivo**: `rv_agent/vision/image_handler.py`

**Responsabilidades**:
- Captura de screenshot
- Otimização de imagem
- Encoding base64
- Gerenciamento de cache

**Métodos Extraídos**:
- `_capture_screenshot_node()` → `capture()`
- `_load_and_optimize_screenshot()` → `optimize_and_encode()`

**Benefícios**:
- ✅ Isola código específico de visão
- ✅ Permite estratégias de caching
- ✅ Simplifica testes com imagens mock

**Interface Proposta**:
```python
class ImageHandler:
    def __init__(self, device, target_dimensions):
        self.device = device
        self.target_dimensions = target_dimensions

    def capture_and_optimize(self) -> str:
        """Capture screenshot and return optimized base64."""
        pass
```

---

### Prioridade 4: Decision Router (MÉDIO IMPACTO)

**Novo Arquivo**: `rv_agent/routing/routing_manager.py`

**Responsabilidades**:
- Roteamento baseado em modo (pure_algorithm, llm_only, multimode)
- Detecção de condições de fallback
- Validação de LLM
- Detecção de loops

**Métodos Extraídos**:
- `_decision_router_node()` → `route_decision()`
- `_validation_router_node()` → `validate_llm_action()`
- `_count_consecutive_actions()` → `detect_loop()`
- `_actions_are_similar()` → `compare_actions()`

**Benefícios**:
- ✅ Centraliza lógica de roteamento
- ✅ Facilita adição de novos modos
- ✅ Melhora testabilidade de regras
- ✅ Separa decisão de execução

**Interface Proposta**:
```python
class RoutingManager:
    def __init__(self, config):
        self.config = config

    def route_decision(self, state: AgentState) -> str:
        """Route to 'llm' or 'dfs' based on mode and conditions."""
        pass

    def validate_llm_action(self, state: AgentState) -> str:
        """Validate LLM response and route to execution or fallback."""
        pass
```

---

### Prioridade 5: Tool Executor (BAIXO-MÉDIO IMPACTO)

**Novo Arquivo**: `rv_agent/execution/tool_executor.py`

**Responsabilidades**:
- Extração de tool calls
- Execução de tools com tratamento de erros
- Rastreamento de coordenadas de ações
- Processamento de resultados

**Métodos Extraídos**:
- `_execute_tools_node()` → `execute_tools()`
- `_action_to_tool_call()` → `convert_action_to_tool_call()`
- `_extract_action_from_tool_calls()` → `parse_tool_calls()`

**Benefícios**:
- ✅ Isola lógica de execução
- ✅ Permite mocking de execução de tools
- ✅ Melhora tratamento de erros e logging

---

### Prioridade 6: Memory Coordinator (BAIXO IMPACTO)

**Novo Arquivo**: `rv_agent/memory/memory_coordinator.py`

**Nota**: Sistemas de memória já estão bem separados. Apenas precisa de coordenador unificado.

**Responsabilidades**:
- Coordenar atualizações em todos os sistemas de memória
- Gerar resumos unificados
- Gerenciar ciclo de vida da memória

**Métodos Extraídos**:
- `_learn_node()` → `update_all_memories()`

**Benefícios**:
- ✅ Ponto único de entrada para updates
- ✅ Updates transacionais de memória
- ✅ Facilita adição de novos sistemas

---

### Prioridade 7: Graph Orchestrator (CORE - MANTER MÍNIMO)

**Arquivo Atualizado**: `rv_agent/core/rv_agent.py`

**Responsabilidades Finais** (Apenas coordenação):
- Construção do workflow LangGraph
- Gerenciamento do loop externo
- Inicialização de componentes
- Orquestração de alto nível

**Métodos Remanescentes**:
- `__init__()` - Inicializar todos os componentes
- `_build_agent_graph()` - Construir workflow LangGraph
- `run()` - Loop externo de execução
- Métodos de delegação de nodes (wrappers finos)

**Tamanho Alvo**: ~400-500 linhas (redução de 70%)

---

## 🎨 Abstração de Estratégias

### ✅ DECIDIDO: Interface simplificada (apenas algoritmos não-LLM)

### Análise de Estratégias Existentes (rvdroid-tool)

**Pontos Fortes a Adotar**:
1. ✅ Classe abstrata `Strategy` com interface padronizada
2. ✅ `StrategyRegistry` para descoberta dinâmica
3. ✅ Separação: geração de ação vs processamento de feedback
4. ✅ Rastreamento de metadados (execution_count, success_rate)
5. ✅ Múltiplas implementações concretas

**Problemas da DFS Strategy Atual**:
- ❌ Acoplada à inicialização do RVAgent
- ❌ Coordinate converter passado como parâmetro
- ❌ Sem interface abstrata - hardcoded no RVAgent
- ❌ Sem implementação BFS

### Interface Proposta

```python
# rv_agent/strategies/base_strategy.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

class ExplorationStrategy(ABC):
    """Base class for exploration strategies."""

    def __init__(self, graph, coordinator=None, static_data=None):
        """
        Args:
            graph: DynamicStateGraph for state tracking
            coordinator: Provides coordinate conversion, etc.
            static_data: Optional static analysis data for MOP guidance
        """
        self.graph = graph
        self.coordinator = coordinator
        self.static_data = static_data
        self.execution_count = 0
        self.success_count = 0

    @abstractmethod
    def select_next_action(
        self,
        screen_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[Dict[str, Any]]:
        """
        Select next action using strategy-specific algorithm.

        Returns:
            Action dict or None if no valid actions
        """
        pass

    @abstractmethod
    def get_guidance(
        self,
        screen_hash: str,
        screen_desc: ScreenDescription
    ) -> Dict[str, Any]:
        """
        Provide guidance for LLM-based decision making.

        Returns:
            Dict with suggested actions, priorities, etc.
        """
        pass

    def update_feedback(self, action: Dict, result: Dict) -> None:
        """Update strategy based on action results."""
        self.execution_count += 1
        if result.get("success"):
            self.success_count += 1

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count
```

```python
# rv_agent/strategies/registry.py
class StrategyRegistry:
    """Central registry for exploration strategies."""
    _strategies = {}

    @classmethod
    def register(cls, name: str, strategy_class: type):
        """Register a strategy."""
        cls._strategies[name] = strategy_class

    @classmethod
    def create(cls, name: str, **kwargs) -> ExplorationStrategy:
        """Create strategy instance by name."""
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}")
        return cls._strategies[name](**kwargs)

    @classmethod
    def list_strategies(cls) -> List[str]:
        """List all registered strategies."""
        return list(cls._strategies.keys())
```

### Estratégias a Implementar

1. **DFSStrategy** (refatorar existente)
   - Exploração depth-first
   - Signature-based action tracking
   - Filtragem de barra de navegação

2. **BFSStrategy** (nova implementação)
   - Exploração breadth-first
   - Queue-based state management
   - Level-order traversal

3. **Futuras** (inspiração rvdroid-tool):
   - RandomStrategy
   - MOPGuidedStrategy
   - HeuristicComboStrategy

---

## 📅 Fases de Implementação

### ✅ DECIDIDO: Implementação completa de uma vez

### Fase 1: Foundation (Semana 1)

**Objetivos**:
1. Criar abstração de estratégias
2. Extrair LLM orchestrator

**Tarefas**:
- [ ] Implementar `base_strategy.py` e `registry.py`
- [ ] Refatorar `DFSStrategy` para usar nova interface
- [ ] Implementar `BFSStrategy`
- [ ] Adicionar testes unitários para estratégias
- [ ] Criar `llm_client.py`
- [ ] Criar `prompt_builder.py`
- [ ] Atualizar `rv_agent.py` para usar orchestrator
- [ ] Adicionar testes de LLM orchestrator

**Critérios de Sucesso**:
- ✅ Testes `test_pure_dfs_cryptoapp.py` passam
- ✅ Testes `test_multimode_cryptoapp.py` passam
- ✅ Novos testes unitários passam

---

### Fase 2: UI and Vision (Semana 2)

**Objetivos**:
1. Extrair UI processor
2. Extrair screenshot manager

**Tarefas**:
- [ ] Criar `screen_processor.py`
- [ ] Criar `element_formatter.py`
- [ ] Atualizar `rv_agent.py` para delegar processamento UI
- [ ] Adicionar testes de UI processor
- [ ] Criar `image_handler.py`
- [ ] Atualizar `rv_agent.py` para usar manager
- [ ] Adicionar testes com imagens mock

**Critérios de Sucesso**:
- ✅ Testes de integração passam
- ✅ Transformação de coordenadas funciona
- ✅ Screenshots otimizados corretamente

---

### Fase 3: Routing and Execution (Semana 3)

**Objetivos**:
1. Extrair decision router
2. Extrair tool executor

**Tarefas**:
- [ ] Criar `routing_manager.py`
- [ ] Criar `validators.py`
- [ ] Atualizar `rv_agent.py` para usar router
- [ ] Adicionar testes para todos os modos de roteamento
- [ ] Criar `tool_executor.py`
- [ ] Atualizar `rv_agent.py` para delegar execução
- [ ] Adicionar testes com mock tools

**Critérios de Sucesso**:
- ✅ Todos os modos (pure_algorithm, llm_only, multimode) funcionam
- ✅ Detecção de loops funciona
- ✅ Fallback funciona corretamente

---

### Fase 4: Memory and Integration (Semana 4)

**Objetivos**:
1. Criar memory coordinator
2. Limpeza final e validação

**Tarefas**:
- [ ] Criar `memory_coordinator.py`
- [ ] Atualizar `rv_agent.py` para usar coordinator
- [ ] Adicionar testes de integração de memória
- [ ] Mover arquivos antigos para backup
- [ ] Executar testes completos de integração
- [ ] Atualizar documentação
- [ ] Validação de performance

**Critérios de Sucesso**:
- ✅ Todos os testes passam
- ✅ Performance mantida ou melhorada
- ✅ Código limpo sem arquivos legados
- ✅ Documentação atualizada

---

## 🧪 Estratégia de Testes

### Testes Unitários (Novos)
- Testar cada componente extraído em isolamento
- Mock de dependências (device, LLM, memory)
- Cobertura de edge cases e caminhos de erro

### Testes de Integração (Atualizados)
- Atualizar testes existentes para nova arquitetura
- Testar interações entre componentes
- Validar workflows end-to-end

### Testes de Validação (Manter)
- ✅ `test_pure_dfs_cryptoapp.py`
- ✅ `test_multimode_cryptoapp.py`
- ✅ `test_multimode_fix_validation.py`
- Executar após cada fase para garantir sem regressões

---

## 🎁 Benefícios Esperados

### Qualidade de Código
- ✅ **Complexidade Reduzida**: De 1,830 para ~400 linhas no orchestrator principal
- ✅ **Responsabilidade Única**: Cada componente com propósito claro
- ✅ **Testabilidade**: Componentes testáveis independentemente
- ✅ **Manutenibilidade**: Mudanças localizadas em componentes específicos

### Experiência do Desenvolvedor
- ✅ **Navegação Facilitada**: Limites claros de módulos
- ✅ **Onboarding Rápido**: Arquivos menores e focados
- ✅ **Melhor Suporte IDE**: Autocomplete e navegação mais rápidos
- ✅ **Dependências Claras**: Interfaces explícitas de componentes

### Flexibilidade do Sistema
- ✅ **Troca de Estratégias**: Fácil adicionar novas estratégias de exploração
- ✅ **Troca de Backend LLM**: Interação LLM isolada
- ✅ **Troca de Parser UI**: Lógica de parsing isolada
- ✅ **Modos de Teste**: Fácil injetar mocks para testes

---

## 💬 Pontos para Discussão

### 🔄 EM DISCUSSÃO

1. **Ordem de Extração de Componentes**
   - A ordem proposta (Foundation → UI/Vision → Routing/Execution → Memory) faz sentido?
   - Devemos priorizar algum componente diferente primeiro?

2. **Nomenclatura de Módulos**
   - `llm_client.py` vs `llm_manager.py`?
   - `screen_processor.py` vs `ui_handler.py`?
   - `routing_manager.py` vs `mode_router.py`?

3. **Interface de Estratégias**
   - A interface `ExplorationStrategy` está adequada?
   - Devemos ter `get_guidance()` separado de `select_next_action()`?
   - Precisamos de mais métodos abstratos?

4. **Coordenação de Componentes**
   - Como passar dependências entre componentes?
   - Usar dependency injection explícita?
   - Criar um `ComponentCoordinator`?

5. **Testes de Integração**
   - Quais cenários de integração são críticos?
   - Precisamos de novos testes além dos existentes?
   - Como garantir cobertura adequada?

6. **Performance**
   - Extração de componentes pode impactar performance?
   - Precisamos de benchmarks antes/depois?
   - Quais métricas rastrear?

7. **Backward Compatibility**
   - Confirmado: NÃO manter compatibilidade
   - Mas precisamos documentar breaking changes?
   - Como comunicar mudanças para usuários (se houver)?

---

## 📝 Status do Documento

**Versão**: 2.0 (Decisões Incorporadas)
**Última Atualização**: 2025-11-07 (Atualizado após discussão)

**Legenda**:
- ✅ **DECIDIDO**: Aprovado e pronto para implementação
- 🔄 **EM DISCUSSÃO**: Aguardando discussão e refinamento
- ⏳ **PENDENTE**: Ainda não discutido

**Próximos Passos**:
1. Revisar e discutir cada seção marcada como 🔄
2. Refinar detalhes das interfaces propostas
3. Decidir ordem final de implementação
4. Aprovar início da Fase 1

---

## 📖 Glossário de Renomeação

### ✅ DECIDIDO: Termos e conceitos renomeados

| Termo Antigo | Termo Novo | Razão |
|--------------|------------|-------|
| `pure_dfs` (modo) | `pure_algorithm` | Abstrair estratégia de busca no grafo (não específico ao DFS) |
| `hybrid` (modo) | **REMOVIDO** | Simplificação - manter apenas 3 modos |
| `dfs` (referência geral) | `algorithm` ou `graph_search` | Não amarrar código a uma estratégia específica |
| `llm_orchestrator.py` | `llm_client.py` | Nomenclatura Alternativa 2 (mais simples) |
| `ui_processor.py` | `screen_processor.py` | Foco em ScreenDescription |
| `decision_router.py` | `routing_manager.py` | Nomenclatura Alternativa 2 |
| `screenshot_manager.py` | `image_handler.py` | Nomenclatura Alternativa 2 |
| `coordinate_converter.py` | `coordinate_utils.py` | Funções estáticas/utilitárias (não classe) |
| `LLMOrchestrator` | `LLMClient` | Seguir renomeação de arquivo |
| `UIProcessor` | `ScreenProcessor` | Seguir renomeação de arquivo |
| `DecisionRouter` | `RoutingManager` | Seguir renomeação de arquivo |
| `ScreenshotManager` | `ImageHandler` | Seguir renomeação de arquivo |

### Modos de Operação Atualizados

| Modo | Descrição | Uso |
|------|-----------|-----|
| `pure_algorithm` | 100% estratégia algorítmica (DFS, BFS, etc.) | Baseline, testes de cobertura |
| `llm_only` | 100% decisões do LLM | Máxima flexibilidade, exploração inteligente |
| `multimode` | Probabilístico (70% LLM / 30% algoritmo) | Balanceamento, previne ficar preso |

**Importante**: Em todo o código, evitar referências específicas a "dfs". Usar termos genéricos como "algorithm_strategy", "graph_search", etc.

---

## 📚 Referências

- Análise completa gerada por Plan Agent (2025-11-07)
- Código atual: `modules/rv-agent/src/rv_agent/core/rv_agent.py`
- Estratégias existentes: `modules/rvdroid-tool/src/rvdroid_tool/strategy/`
- Testes atuais: `test_pure_dfs_cryptoapp.py`, `test_multimode_cryptoapp.py`

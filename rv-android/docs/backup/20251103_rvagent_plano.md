# Plano de Refatoração RVAgent - v3 + v4 Base (Multi-modo)

**Data**: 2025-11-03
**Escopo**: Detecção de loops (v3) + Arquitetura multi-modo (v4 Base)
**Estimativa**: 18-22 horas | ~930 linhas de código
**Objetivo**: Eliminar loops infinitos + Adicionar modos pure_dfs/llm_only/hybrid

---

## 1. Preparação

### 1.1 Criar Backup
```bash
mkdir -p backup/2025-11-03_v3-v4-refactor/
cp -r modules/rv-agent/src/rv_agent/ backup/2025-11-03_v3-v4-refactor/
```

### 1.2 Referências dos Documentos Base
- **v2 - Base teórica**: `docs/20251103_rvagent_pre_plano_v2.md` (linhas 1-661)
  - Problema crítico: linhas 1-67
  - Validação qwen3-vl: linhas 79-99, 563-586
  - Comparativo DFS vs BFS vs LLM: linhas 367-421

- **v3 - Decisões finais**: `docs/20251103_rvagent_pre_plano_v3.md` (linhas 1-1124)
  - Detecção de loops: linhas 41-107
  - Integração DFS/BFS: linhas 110-147
  - UI Coverage: linhas 150-205
  - Trace de sequências: linhas 207-294
  - Backtracking: linhas 297-330
  - Arquitetura final: linhas 376-473
  - Exemplos de fluxo: linhas 525-643
  - Mudanças de código: linhas 646-954

- **v4 - Multi-modo**: `docs/20251103_rvagent_pre_plano_v4_multimode.md` (linhas 1-1700+)
  - Visão geral: linhas 1-132
  - Modo PURE_DFS: linhas 135-489
  - Modo HYBRID: linhas 728-965
  - Decision Router: linhas 851-965
  - Grafo compartilhado: linhas 1028-1141
  - Sistema de configuração: linhas 1143-1386
  - Implementação técnica: linhas 1389-1652

---

## 2. Fase 1: Estruturas de Dados (v3 Base) - 2h

### 2.1 DynamicStateGraph - Trace de Sequências
**Arquivo**: `modules/rv-agent/src/rv_agent/memory/dynamic_state_graph.py`
**Referência**: v3.md linhas 649-691, v2.md linhas 213-264

**Mudanças necessárias**:

1. **Modificar classe `Transition`** (linha ~20):
   ```python
   @dataclass
   class Transition:
       from_hash: str
       to_hash: str
       action_sequence: List[Dict]  # MUDANÇA: era action_id: int
       timestamp: float
   ```

2. **Adicionar campo em `DynamicStateGraph.__init__()`** (linha ~40):
   ```python
   self.current_trace: List[Dict] = []  # NOVO: trace atual entre estados
   ```

3. **Novo método `record_action_to_trace()`**:
   - Adiciona ação individual ao trace atual
   - Chamado em cada iteração antes da transição

4. **Modificar método `record_transition()`**:
   - Salvar `self.current_trace.copy()` no campo `action_sequence`
   - Fazer reset: `self.current_trace = []` após registrar transição
   - Permite rastrear sequências completas de ações entre estados

5. **Novo método `get_transition_graph_report()`**:
   - Exporta relatório completo do grafo
   - Inclui todas as transições com suas sequências de ações
   - Formato: Dict com `states`, `transitions`, `action_sequences`

**Objetivo**: Guardar sequências completas de ações que levam a transições de estado, permitindo análise detalhada do comportamento da exploração.

**Estimativa**: ~30 linhas modificadas/adicionadas

---

### 2.2 AgentState - Novos Campos
**Arquivo**: `modules/rv-agent/src/rv_agent/llm/graph/state.py`
**Referência**: v3.md linhas 939-954, v4.md linhas 1392-1448

**Adicionar campos em `TypedDict AgentState`**:

```python
# ===== v3 - Detecção de loops =====
recent_action_window: List[Dict]      # Últimas 10 ações (para contagem consecutiva)
loop_detected: bool                   # Flag: loop foi detectado nesta iteração
used_fallback: bool                   # Flag: usou fallback DFS
last_screen_hash: Optional[str]       # Para detectar transições de estado

# ===== v4 - Multi-modo =====
execution_mode: str                   # "pure_dfs", "llm_only", "hybrid"
router_decision: Optional[str]        # "llm" ou "dfs" (decisão do router)
router_reason: Optional[str]          # Razão da decisão do router
decision_maker: str                   # "llm", "dfs", "dfs_fallback"
last_decision_maker: Optional[str]    # Decision maker da iteração anterior
consecutive_llm_failures: int         # Contador de falhas consecutivas da LLM
llm_timeout_occurred: bool            # Flag: timeout da LLM ocorreu
exploration_complete: bool            # Flag: DFS sinalizou exploração completa

# ===== v4 - Métricas =====
llm_decisions: int                    # Contador: decisões da LLM
dfs_decisions: int                    # Contador: decisões do DFS
dfs_fallbacks: int                    # Contador: fallbacks para DFS
```

**Objetivo**: Adicionar estado necessário para detecção de loops (v3) e suporte multi-modo (v4).

**Estimativa**: ~20 linhas adicionadas

---

## 3. Fase 2: Configuração Multi-modo (v4) - 2h

### 3.1 RVAgentConfig - Extensão
**Arquivo**: `modules/rv-agent/src/rv_agent/config/agent_config.py` (criar ou estender)
**Referência**: v4.md linhas 1145-1241

**Criar/estender classe de configuração**:

```python
@dataclass
class RVAgentConfig:
    # ===== Campos existentes =====
    package_name: str
    device_id: str = "emulator-5554"
    timeout: int = 300
    max_iterations: int = 200
    strategy: str = "dfs"                    # "dfs" ou "bfs"

    # LLM config
    llm_model: str = "qwen3-vl:4b"
    llm_temperature: float = 0.0
    llm_top_p: float = 0.9
    llm_top_k: int = 40

    # ===== NOVOS v4 - Multi-modo =====
    execution_mode: str = "hybrid"           # "pure_dfs", "llm_only", "hybrid"
    llm_timeout: float = 30.0                # Timeout por chamada LLM (segundos)
    llm_max_retries: int = 2                 # Tentativas antes de fallback DFS
    auto_fallback_on_timeout: bool = True    # Se timeout → DFS
    auto_fallback_on_error: bool = True      # Se erro → DFS

    # ===== NOVOS - Thresholds configuráveis =====
    threshold_type_text: int = 2             # TYPE_TEXT: máx 2 repetições consecutivas
    threshold_click: int = 3                 # CLICK: máx 3 repetições
    threshold_scroll: int = 5                # SCROLL: máx 5 repetições
    threshold_swipe: int = 5                 # SWIPE: máx 5 repetições
    threshold_back: int = 2                  # BACK: máx 2 repetições
    threshold_default: int = 3               # Default: máx 3 repetições

    # Coordenadas
    device_dimensions: tuple = (1080, 1920)
    optimized_dimensions: tuple = (720, 1280)
```

**Novos métodos**:

1. **`get_execution_mode() -> str`**:
   - Permite override via variável de ambiente `RVAGENT_MODE`
   - Prioridade: env var > campo config
   - Uso: `$ RVAGENT_MODE=pure_dfs poetry run python test.py`

2. **`get_threshold(action_type: str) -> int`**:
   - Retorna threshold configurado para tipo de ação específico
   - Mapeamento: "TYPE_TEXT" → threshold_type_text, etc.
   - Fallback para threshold_default se tipo não mapeado

3. **`validate()`**:
   - Valida execution_mode (deve ser "pure_dfs", "llm_only" ou "hybrid")
   - Valida que LLM está configurado se modo requer (llm_only, hybrid)
   - Valida strategy (deve ser "dfs" ou "bfs")
   - Raises ValueError se configuração inválida

4. **`get_mode_description() -> str`**:
   - Retorna descrição legível do modo
   - Ex: "hybrid" → "LLM + DFS validation/fallback (recommended)"

**Objetivo**: Centralizar configuração com suporte multi-modo e thresholds ajustáveis.

**Estimativa**: ~65 linhas (inclui thresholds configuráveis)

---

## 4. Fase 3: DFSStrategy - Extensões (v3 + v4) - 3h

### 4.1 Select Untested Action (v3)
**Arquivo**: `modules/rv-agent/src/rv_agent/strategies/dfs_strategy.py`
**Referência**: v3.md linhas 883-934, v2.md linhas 193-200

**Novo método `select_untested_action()`** (linha ~80):

```python
def select_untested_action(
    self,
    screen_hash: str,
    dynamic_graph: DynamicStateGraph
) -> Optional[Dict]:
    """
    Seleciona próxima ação untested no estado atual.
    Prioriza ações com MOP markers ([DM] > [M] > outros).

    Args:
        screen_hash: Hash do estado atual
        dynamic_graph: Grafo dinâmico compartilhado

    Returns:
        Dict com ação executável ou None se sem untested

    Lógica:
    1. Obtém ScreenNode do grafo
    2. Obtém todas as ações disponíveis na tela
    3. Filtra untested (id not in executed_actions)
    4. Ordena por prioridade MOP (usa _get_mop_priority)
    5. Retorna top priority como dict executável
    """
```

**Objetivo**: Usado como fallback quando loop é detectado. Escolhe inteligentemente próxima ação não testada com base em prioridade MOP.

**Estimativa**: ~40 linhas

---

### 4.2 Select Next Action - DFS Standalone (v4)
**Referência**: v4.md linhas 163-489, v2.md linhas 135-158

**Novo método `select_next_action()`** (linha ~130):

```python
def select_next_action(
    self,
    screen_hash: str,
    screen_desc: ScreenDescription
) -> Optional[Dict]:
    """
    MÉTODO PRINCIPAL: Escolhe próxima ação usando DFS puro (SEM LLM).

    Algoritmo DFS clássico:
    1. Se estado novo → adiciona à pilha DFS (self.state_stack)
    2. Se tem ações untested → escolhe uma (DEEPEN)
       - Prioriza por MOP markers
       - Incrementa profundidade
    3. Se estado esgotado → BACK (BACKTRACK)
       - Remove estado da pilha
       - Decrementa profundidade
    4. Se pilha vazia → None (exploração completa)

    Args:
        screen_hash: Hash estrutural do estado
        screen_desc: ScreenDescription object parsed

    Returns:
        Dict com ação a executar, ou None se exploração completa
    """
```

**Adicionar campos em `__init__()`**:
```python
# Estado DFS para standalone mode
self.state_stack: List[DFSState] = []     # Pilha de estados para backtracking
self.visited_states: Set[str] = set()     # Estados já visitados
self.current_depth = 0                    # Profundidade atual na árvore DFS
```

**Helper methods necessários**:

1. **`_action_to_dict(action: ScreenAction) -> Dict`**:
   - Converte ScreenAction para dict executável
   - Determina action_type baseado em flags (editable, scrollable, clickable)
   - Inclui coordenadas, descrição, id, prioridade MOP

2. **`_generate_input_text(action: ScreenAction) -> str`**:
   - Gera texto para preencher EditText **SEM usar LLM**
   - Usa heurísticas baseadas em hints textuais (resource-id, text, content-desc)
   - Exemplos: "email" → "dfs_test@example.com", "password" → "DFSTest123!"
   - Ver v4.md linhas 380-450 para lista completa de heurísticas

3. **`_get_mop_priority(action: ScreenAction) -> int`**:
   - Retorna prioridade baseada em MOP markers da análise estática
   - 3: Directly reaches MOP [DM]
   - 2: Reaches MOP [M]
   - 1: Sem marker

**Referência detalhada**: v4.md linhas 163-489 (implementação completa com todas as heurísticas)

**Objetivo**: Permitir exploração DFS completa sem dependência de LLM (modo pure_dfs).

**Estimativa**: ~230 linhas (DFS standalone completo com helpers)

---

## 5. Fase 4: RVAgent - Nós e Lógica (v3 + v4) - 8h

### 5.1 Helper Methods - Detecção de Similaridade (v3)
**Arquivo**: `modules/rv-agent/src/rv_agent/core/rv_agent.py`
**Referência**: v3.md linhas 754-781, v4.md linhas 1607-1631

**Novos métodos** (linha ~300):

```python
def _count_consecutive_actions(self, recent: List[Dict], current: Dict) -> int:
    """
    Conta repetições CONSECUTIVAS da ação atual no histórico recente.
    Para na primeira ação diferente encontrada (ordem reversa).

    Args:
        recent: Lista de ações recentes (recent_action_window)
        current: Ação atual a ser checada

    Returns:
        Número de repetições consecutivas (0 se nenhuma)
    """

def _actions_are_similar(self, a1: Dict, a2: Dict) -> bool:
    """
    Compara se duas ações são similares.

    Critérios:
    - Mesmo action_type (obrigatório)
    - TYPE_TEXT: mesmo texto exato
    - CLICK: coordenadas próximas (tolerância <20px)
    - Outros: apenas tipo

    Returns:
        True se ações são similares
    """
```

**Objetivo**: Detectar loops baseado em repetições consecutivas (não duplicatas gerais).

**Estimativa**: ~40 linhas

---

### 5.2 Strategy Validation Node (v3)
**Referência**: v3.md linhas 697-781, v2.md linhas 229-238

**Novo método** (linha ~200):

```python
def _strategy_validation_node(self, state: AgentState) -> AgentState:
    """
    Valida ação da LLM para detectar loops (repetições consecutivas).

    Fluxo:
    1. Extrai ação da LLM e histórico recente
    2. Conta repetições consecutivas (_count_consecutive_actions)
    3. Obtém threshold configurável (config.get_threshold)
    4. Se loop detectado (count >= threshold):
       a. Log warning
       b. Chama strategy.select_untested_action()
       c. Se fallback existe: retorna ação alternativa
       d. Se sem untested: retorna BACK
       e. Marca loop_detected=True, used_fallback=True
    5. Se válido: passa ação original da LLM

    Returns:
        AgentState atualizado com current_action validada/substituída
    """
```

**Uso de thresholds configuráveis**:
```python
action_type = llm_action.get("action_type", "default")
threshold = self.config.get_threshold(action_type)

if consecutive_count >= threshold:
    logger.warning(f"⚠️  LOOP: {action_type} repeated {consecutive_count}x (threshold={threshold})")
    # ... fallback logic
```

**Objetivo**: Prevenir loops infinitos via validação após decisão da LLM, com fallback automático.

**Estimativa**: ~80 linhas

---

### 5.3 Decision Router Node (v4)
**Referência**: v4.md linhas 851-965, v2.md linhas 110-130

**Novo método** (linha ~350):

```python
def _decision_router_node(self, state: AgentState) -> AgentState:
    """
    Decide se usa LLM ou DFS baseado no modo e contexto.

    Lógica por modo:
    - pure_dfs: sempre "dfs"
    - llm_only: sempre "llm"
    - hybrid:
        - Se consecutive_llm_failures >= llm_max_retries → "dfs"
        - Se loop_detected (última iteração) → "dfs" (preventivo)
        - Se llm_timeout_occurred → "dfs"
        - Senão → "llm" (padrão)

    Returns:
        AgentState com router_decision e router_reason preenchidos
    """
```

**Objetivo**: Centralizar decisão de roteamento com lógica de fallback inteligente.

**Estimativa**: ~30 linhas

---

### 5.4 DFS Decide Node (v4)
**Referência**: v4.md linhas 1599-1606

**Novo método** (linha ~380):

```python
def _dfs_decide_node(self, state: AgentState) -> AgentState:
    """
    Usa DFS para decidir ação (sem LLM).
    Chama strategy.select_next_action() standalone.

    Fluxo:
    1. Extrai screen_hash e screen_desc_obj do state
    2. Chama self.strategy.select_next_action()
    3. Se action is None:
       - Sinaliza exploration_complete=True
       - Retorna ação END
    4. Se action válida:
       - Retorna action com decision_maker="dfs"
    """
```

**Objetivo**: Permitir DFS tomar decisões autônomas (modo pure_dfs e fallback em hybrid).

**Estimativa**: ~25 linhas

---

### 5.5 Modificar Observe Node (v3)
**Referência**: v3.md linhas 783-813, v2.md linhas 161-174

**Adicionar ao método existente `_observe_node()`** (~linha 150):

```python
def _observe_node(self, state: AgentState) -> AgentState:
    # ... código existente de captura de tela e parsing ...

    screen_hash = compute_screen_hash(xml)

    # ===== NOVO: Detecta mudança de estado (transição) =====
    if state.get("last_screen_hash") and state["last_screen_hash"] != screen_hash:
        # Transição detectada!
        self.dynamic_graph.record_transition(
            from_hash=state["last_screen_hash"],
            to_hash=screen_hash,
            timestamp=time.time()
        )
        logger.info(f"📊 Transition: {state['last_screen_hash'][:8]} → {screen_hash[:8]}")
        logger.info(f"   Actions in sequence: {len(self.dynamic_graph.current_trace)}")

    # ===== NOVO: Anota UI com coverage tracker =====
    annotated_desc = self.ui_coverage.annotate_screen_elements(
        screen_desc_text,
        screen_hash
    )

    return {
        "screen_description": annotated_desc,  # Com [UNTESTED]/[TESTED-Nx]
        "last_screen_hash": screen_hash,       # Para próxima iteração
        # ... resto dos campos existentes
    }
```

**Objetivo**:
- Detectar transições de estado automaticamente
- Ativar anotações UI coverage para guiar LLM

**Estimativa**: ~15 linhas adicionadas

---

### 5.6 Modificar Learn Node (v3)
**Referência**: v3.md linhas 815-845, v2.md linhas 175-192

**Adicionar ao método existente `_learn_node()`** (~linha 180):

```python
def _learn_node(self, state: AgentState) -> AgentState:
    action = state["current_action"]
    screen_hash = state["current_screen_hash"]
    decision_maker = state.get("decision_maker", "unknown")

    # ===== NOVO: Adiciona ao trace (para relatório de transições) =====
    self.dynamic_graph.record_action_to_trace(action)

    # ===== NOVO: Registra em UI coverage =====
    element_id = self._extract_element_id(action)
    if element_id:
        self.ui_coverage.record_interaction(
            element_id=element_id,
            action_type=action["action_type"],
            screen_hash=screen_hash,
            success=True
        )

    # ===== NOVO: Atualiza recent_action_window (para loop detection) =====
    recent = state.get("recent_action_window", [])
    recent.append(action)
    if len(recent) > 10:  # Mantém últimas 10
        recent = recent[-10:]

    # ===== NOVO: Incrementa contadores de métricas =====
    llm_count = state.get("llm_decisions", 0)
    dfs_count = state.get("dfs_decisions", 0)
    fallback_count = state.get("dfs_fallbacks", 0)

    if decision_maker == "llm":
        llm_count += 1
    elif decision_maker == "dfs":
        dfs_count += 1

    if state.get("used_fallback", False):
        fallback_count += 1

    return {
        "recent_action_window": recent,
        "llm_decisions": llm_count,
        "dfs_decisions": dfs_count,
        "dfs_fallbacks": fallback_count,
        "last_decision_maker": decision_maker,
        # ... resto dos campos existentes
    }
```

**Objetivo**:
- Registrar ações no trace e coverage
- Manter histórico para detecção de loops
- Coletar métricas de uso LLM vs DFS

**Estimativa**: ~25 linhas adicionadas

---

### 5.7 Graph Builders (v4)
**Referência**: v4.md linhas 1486-1587, v3.md linhas 847-877

**Modificar método existente `_build_agent_graph()`** (~linha 100):

```python
def _build_agent_graph(self):
    """Constrói grafo baseado no execution_mode."""
    mode = self.config.get_execution_mode()

    logger.info(f"Building {mode} agent graph")

    if mode == "pure_dfs":
        return self._build_graph_pure_dfs()
    elif mode == "llm_only":
        return self._build_graph_llm_only()
    elif mode == "hybrid":
        return self._build_graph_hybrid()
    else:
        raise ValueError(f"Unknown execution_mode: {mode}")
```

**Novos métodos de construção de grafos**:

#### 5.7.1 Pure DFS Graph (~linha 410):
```python
def _build_graph_pure_dfs(self):
    """
    Grafo para modo DFS puro (sem LLM).

    Fluxo: observe → dfs_decide → tools → learn → (loop)

    Sem nós: assistant, strategy_validation, router
    """
    graph = StateGraph(AgentState)

    graph.add_node("observe", self._observe_node)
    graph.add_node("dfs_decide", self._dfs_decide_node)
    graph.add_node("tools", ToolNode(self.tools))
    graph.add_node("learn", self._learn_node)

    graph.set_entry_point("observe")
    graph.add_edge("observe", "dfs_decide")
    graph.add_edge("dfs_decide", "tools")
    graph.add_edge("tools", "learn")
    graph.add_conditional_edges(
        "learn",
        self._should_continue,
        {"continue": "observe", "end": END}
    )

    return graph.compile()
```

#### 5.7.2 LLM Only Graph (~linha 435):
```python
def _build_graph_llm_only(self):
    """
    Grafo para modo LLM apenas (V10 atual, SEM v3 validation).

    Fluxo: observe → assistant → tools → learn → (loop)

    Sem nós: strategy_validation, dfs_decide, router
    """
    graph = StateGraph(AgentState)

    graph.add_node("observe", self._observe_node)
    graph.add_node("assistant", self._assistant_node)
    graph.add_node("tools", ToolNode(self.tools))
    graph.add_node("learn", self._learn_node)

    graph.set_entry_point("observe")
    graph.add_edge("observe", "assistant")
    graph.add_edge("assistant", "tools")
    graph.add_edge("tools", "learn")
    graph.add_conditional_edges(
        "learn",
        self._should_continue,
        {"continue": "observe", "end": END}
    )

    return graph.compile()
```

#### 5.7.3 Hybrid Graph (~linha 460):
```python
def _build_graph_hybrid(self):
    """
    Grafo para modo híbrido (v3 + v4).

    Fluxo:
        observe → decision_router → (assistant | dfs_decide)

        Caminho LLM:
            assistant → strategy_validation → tools

        Caminho DFS:
            dfs_decide → tools

        Convergência:
            tools → learn → (loop ou end)

    Conditional edge em router: "llm" | "dfs" | "end"
    """
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("observe", self._observe_node)
    graph.add_node("decision_router", self._decision_router_node)
    graph.add_node("assistant", self._assistant_node)
    graph.add_node("strategy_validation", self._strategy_validation_node)
    graph.add_node("dfs_decide", self._dfs_decide_node)
    graph.add_node("tools", ToolNode(self.tools))
    graph.add_node("learn", self._learn_node)

    # Entry
    graph.set_entry_point("observe")

    # Main flow
    graph.add_edge("observe", "decision_router")

    # Router condicional
    graph.add_conditional_edges(
        "decision_router",
        self._route_decision,  # Helper method
        {
            "llm": "assistant",
            "dfs": "dfs_decide",
            "end": END
        }
    )

    # Caminho LLM (com validation)
    graph.add_edge("assistant", "strategy_validation")
    graph.add_edge("strategy_validation", "tools")

    # Caminho DFS (direto)
    graph.add_edge("dfs_decide", "tools")

    # Convergência
    graph.add_edge("tools", "learn")
    graph.add_conditional_edges(
        "learn",
        self._should_continue,
        {"continue": "observe", "end": END}
    )

    return graph.compile()

def _route_decision(self, state: AgentState) -> str:
    """Helper: retorna decisão do router."""
    return state.get("router_decision", "llm")
```

**Referência detalhada**: v4.md linhas 1500-1587

**Objetivo**: Suportar 3 modos distintos com grafos otimizados para cada caso.

**Estimativa**: ~125 linhas (3 graph builders + helper)

---

### 5.8 Modificar __init__ (v4)
**Referência**: v4.md linhas 1458-1485

**Modificar construtor** (~linha 50):

```python
def __init__(self, config: RVAgentConfig, ...):
    """Inicializa RVAgent com suporte multi-modo."""

    self.config = config
    config.validate()  # Valida configuração

    mode = config.get_execution_mode()
    logger.info(f"Initializing RVAgent")
    logger.info(f"  Mode: {mode}")
    logger.info(f"  Description: {config.get_mode_description()}")

    # ... inicialização existente (device, static_data, etc) ...

    # ===== NOVO: Estratégia com modo =====
    if config.strategy == "dfs":
        self.strategy = DFSStrategy(
            self.dynamic_graph,
            static_data,
            mode=mode  # NOVO: passa modo para estratégia
        )
    elif config.strategy == "bfs":
        self.strategy = BFSStrategy(
            self.dynamic_graph,
            static_data,
            mode=mode
        )

    # ===== NOVO: LLM opcional para pure_dfs =====
    if mode in ["llm_only", "hybrid"]:
        # Modo requer LLM
        self._initialize_llm()
        logger.info(f"  LLM: {config.llm_model}")
    else:
        # pure_dfs não precisa LLM
        self.llm = None
        logger.info("  LLM: not initialized (pure_dfs mode)")

    # ... resto da inicialização existente
```

**Objetivo**: Adaptar inicialização para suportar modo pure_dfs sem LLM.

**Estimativa**: ~20 linhas modificadas

---

### 5.9 Modificar run() - Métricas (v4)
**Referência**: v4.md linhas 1632-1652

**Adicionar ao final do método `run()`** (~linha 400):

```python
def run(self) -> Dict:
    """Executa exploração com suporte multi-modo."""

    # ... execução existente do grafo ...

    # ===== NOVO: Métricas de modo =====
    results["execution_mode"] = self.config.get_execution_mode()
    results["llm_decisions"] = final_state.get("llm_decisions", 0)
    results["dfs_decisions"] = final_state.get("dfs_decisions", 0)
    results["dfs_fallbacks"] = final_state.get("dfs_fallbacks", 0)

    # Percentual de uso LLM (para modo híbrido)
    if results["execution_mode"] == "hybrid":
        total_decisions = results["llm_decisions"] + results["dfs_decisions"]
        if total_decisions > 0:
            llm_percentage = (results["llm_decisions"] / total_decisions) * 100
            results["llm_usage_percentage"] = llm_percentage
            logger.info(f"Hybrid mode: {llm_percentage:.1f}% LLM usage")

    # ===== NOVO: Relatório de transições =====
    transition_report = self.dynamic_graph.get_transition_graph_report()
    results["transition_graph"] = transition_report

    return results
```

**Objetivo**: Coletar métricas detalhadas de uso LLM vs DFS e relatório de transições.

**Estimativa**: ~15 linhas adicionadas

---

## 6. Fase 5: Testes e Validação - 3h

### 6.1 Testes v3 - Loop Detection
**Arquivo**: `modules/rv-agent/tests/test_loop_detection.py` (NOVO)
**Referência**: v3.md linhas 957-1031

**Criar testes unitários**:

```python
import pytest
from rv_agent.core.rv_agent import RVAgent
from rv_agent.config.agent_config import RVAgentConfig

class TestLoopDetection:
    """Testes para detecção de loops v3."""

    def test_loop_detection_type_text(self):
        """3x TYPE_TEXT consecutivo deve triggerar fallback."""
        # Setup: config com threshold_type_text=2
        # Simular 3 TYPE_TEXT consecutivos
        # Assert: loop_detected=True, used_fallback=True

    def test_consecutive_counter(self):
        """Contador de consecutivos funciona corretamente."""
        # Test _count_consecutive_actions diretamente

    def test_actions_are_similar(self):
        """Comparação de similaridade funciona."""
        # Test _actions_are_similar:
        #   - TYPE_TEXT mesmo texto → True
        #   - CLICK coordenadas próximas (<20px) → True
        #   - CLICK coordenadas distantes (>20px) → False

    def test_fallback_selects_untested(self):
        """Fallback escolhe ação untested com MOP priority."""
        # Setup: tela com ações untested
        # Simular loop
        # Assert: fallback é ação com maior MOP priority

    def test_no_loop_with_legitimate_repetitions(self):
        """Combobox workflow (repetições legítimas) não triggera."""
        # Simular: CLICK dropdown → CLICK item1 → CLICK dropdown → CLICK item2
        # Assert: loop NÃO detectado (ações diferentes no meio)

    def test_trace_records_sequence(self):
        """Trace guarda sequência completa de ações."""
        # Setup: executar 3 ações na mesma tela
        # Trigger transição de estado
        # Assert: transition contém 3 ações em action_sequence
```

**Objetivo**: Validar detecção de loops e fallback funcionam corretamente.

**Estimativa**: ~100 linhas

---

### 6.2 Testes v4 - Multi-modo
**Arquivo**: `modules/rv-agent/tests/test_multi_mode.py` (NOVO)
**Referência**: v4.md linhas 1656-1700

**Criar testes por modo**:

```python
class TestPureDFSMode:
    """Testes para modo pure_dfs."""

    @pytest.fixture
    def dfs_config(self):
        return RVAgentConfig(
            package_name="com.example.testapp",
            execution_mode="pure_dfs",
            timeout=60
        )

    def test_no_llm_calls(self, dfs_config):
        """DFS puro não deve chamar LLM."""
        agent = RVAgent(dfs_config)
        results = agent.run()
        assert results.get("llm_calls", 0) == 0
        assert results.get("llm_decisions", 0) == 0

    def test_discovers_states(self, dfs_config):
        """DFS deve descobrir estados."""
        agent = RVAgent(dfs_config)
        results = agent.run()
        assert results["unique_states"] > 0

    def test_deterministic(self, dfs_config):
        """DFS é determinístico (2 runs = mesmos resultados)."""
        agent1 = RVAgent(dfs_config)
        results1 = agent1.run()

        agent2 = RVAgent(dfs_config)
        results2 = agent2.run()

        assert results1["unique_states"] == results2["unique_states"]
        # Compare transition sequences


class TestLLMOnlyMode:
    """Testes para modo llm_only."""

    def test_llm_called(self):
        """LLM é chamado no modo llm_only."""
        # ...

    def test_no_dfs_decisions(self):
        """DFS não toma decisões em llm_only."""
        # ...


class TestHybridMode:
    """Testes para modo hybrid."""

    def test_both_used(self):
        """LLM e DFS são usados em hybrid."""
        # ...

    def test_fallback_on_loop(self):
        """DFS fallback quando loop detectado."""
        # ...

    def test_llm_timeout_triggers_dfs(self):
        """Timeout da LLM ativa fallback DFS."""
        # ...

    def test_collaboration_graph_shared(self):
        """LLM e DFS compartilham mesmo grafo."""
        # Verificar que actions de ambos aparecem no mesmo grafo


class TestConfiguration:
    """Testes de configuração."""

    def test_env_override(self):
        """RVAGENT_MODE env var override funciona."""
        # Set RVAGENT_MODE=pure_dfs
        # Config tem execution_mode="hybrid"
        # Assert: get_execution_mode() retorna "pure_dfs"

    def test_threshold_config(self):
        """Thresholds configuráveis funcionam."""
        config = RVAgentConfig(threshold_type_text=5)
        assert config.get_threshold("TYPE_TEXT") == 5

    def test_mode_validation(self):
        """Validação rejeita modos inválidos."""
        config = RVAgentConfig(execution_mode="invalid")
        with pytest.raises(ValueError):
            config.validate()
```

**Objetivo**: Validar que todos os 3 modos funcionam corretamente e isoladamente.

**Estimativa**: ~200 linhas

---

### 6.3 Script de Validação CryptoApp
**Arquivo**: `modules/rv-agent/test_v3v4_validation.py` (NOVO)

**Criar script de comparação**:

```python
"""
Script de validação: Compara baseline V10 com v3 e v4.
"""

import json
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.rv_agent import RVAgent

CRYPTOAPP = "br.unb.cic.cryptoapp"
TIMEOUT = 120


def test_cryptoapp_baseline():
    """Baseline V10 atual (para comparação)."""
    # Usar código V10 original se disponível
    # Ou rodar com execution_mode="llm_only" sem validation
    pass


def test_cryptoapp_v3():
    """v3 com loop detection."""
    config = RVAgentConfig(
        package_name=CRYPTOAPP,
        execution_mode="hybrid",  # v3 é hybrid sem multi-modo
        timeout=TIMEOUT
    )

    agent = RVAgent(config)
    results = agent.run()

    return results


def test_cryptoapp_v4_hybrid():
    """v4 modo hybrid."""
    config = RVAgentConfig(
        package_name=CRYPTOAPP,
        execution_mode="hybrid",
        timeout=TIMEOUT
    )

    agent = RVAgent(config)
    results = agent.run()

    return results


def test_cryptoapp_v4_pure_dfs():
    """v4 modo pure_dfs."""
    config = RVAgentConfig(
        package_name=CRYPTOAPP,
        execution_mode="pure_dfs",
        timeout=TIMEOUT
    )

    agent = RVAgent(config)
    results = agent.run()

    return results


def compare_results(baseline, v3, v4_hybrid, v4_pure):
    """Análise comparativa."""

    metrics = [
        "unique_states",
        "total_transitions",
        "iterations",
        "execution_time_s",
        "llm_decisions",
        "dfs_decisions"
    ]

    print("\n" + "="*80)
    print("COMPARISON: Baseline vs v3 vs v4")
    print("="*80)

    for metric in metrics:
        print(f"\n{metric}:")
        print(f"  Baseline:   {baseline.get(metric, 'N/A')}")
        print(f"  v3:         {v3.get(metric, 'N/A')}")
        print(f"  v4 Hybrid:  {v4_hybrid.get(metric, 'N/A')}")
        print(f"  v4 Pure DFS:{v4_pure.get(metric, 'N/A')}")

    # Análise de loops
    print("\nLoop Detection:")
    print(f"  v3 Loops >5 reps: {count_loops(v3)}")
    print(f"  v4 Loops >5 reps: {count_loops(v4_hybrid)}")

    # Salvar resultados
    with open("v3v4_validation_results.json", "w") as f:
        json.dump({
            "baseline": baseline,
            "v3": v3,
            "v4_hybrid": v4_hybrid,
            "v4_pure_dfs": v4_pure
        }, f, indent=2)


if __name__ == "__main__":
    print("Starting validation tests...")

    baseline = test_cryptoapp_baseline()
    v3 = test_cryptoapp_v3()
    v4_hybrid = test_cryptoapp_v4_hybrid()
    v4_pure = test_cryptoapp_v4_pure_dfs()

    compare_results(baseline, v3, v4_hybrid, v4_pure)

    print("\n✅ Validation complete. Results saved to v3v4_validation_results.json")
```

**Objetivo**: Validar empiricamente que v3 resolve loops e v4 adiciona flexibilidade.

**Estimativa**: ~150 linhas

---

## 7. Fase 6: Documentação - 2h

### 7.1 Atualizar CLAUDE.md
**Arquivo**: `CLAUDE.md`

**Adicionar nova seção**:

```markdown
## RVAgent Multi-Mode Architecture

### Overview
RVAgent supports three execution modes, each optimized for different use cases:

- **pure_dfs**: DFS standalone without LLM (baseline, CI/CD, LLM unavailable)
- **llm_only**: Current V10 behavior (LLM only, maximum creativity)
- **hybrid**: LLM + DFS validation/fallback (production, recommended)

### Loop Detection (v3)
The agent detects infinite loops based on consecutive action repetitions:

- Tracks last 10 actions in sliding window
- Counts consecutive repetitions of similar actions
- Configurable thresholds per action type (TYPE_TEXT=2, CLICK=3, SCROLL=5, etc.)
- Automatic fallback to untested actions when loop detected
- Prioritizes actions with MOP markers ([DM] > [M])

### Configuration
See `RVAgentConfig` for full configuration options:

```python
config = RVAgentConfig(
    package_name="com.example.app",
    execution_mode="hybrid",        # Mode selection
    threshold_type_text=2,           # Loop detection thresholds
    llm_timeout=30.0,                # LLM timeout for fallback
    auto_fallback_on_timeout=True    # Automatic DFS fallback
)
```

Override mode via environment variable:
```bash
$ RVAGENT_MODE=pure_dfs poetry run python test.py
```

### Development Commands

```bash
# Run in pure DFS mode (no LLM)
RVAGENT_MODE=pure_dfs poetry run rv-agent run --package com.example.app

# Run in hybrid mode (default)
poetry run rv-agent run --package com.example.app

# Run tests
poetry run pytest modules/rv-agent/tests/test_loop_detection.py
poetry run pytest modules/rv-agent/tests/test_multi_mode.py
```

### Architecture Details
- **v3**: Loop detection via consecutive action counting, strategy validation node
- **v4**: Multi-mode support with decision router and shared dynamic graph
- **Transition tracking**: Complete action sequences saved between state transitions
- **UI Coverage**: Automatic annotation of tested/untested elements in prompts
```

**Estimativa**: ~50 linhas adicionadas

---

### 7.2 Criar CHANGELOG.md
**Arquivo**: `modules/rv-agent/CHANGELOG.md` (NOVO)

```markdown
# Changelog - RVAgent

## [v3+v4] - 2025-11-03

### Added
- **Loop detection system** (v3): Detects infinite loops based on consecutive action repetitions
- **Strategy validation node**: Validates LLM decisions before execution, triggers DFS fallback on loops
- **Multi-mode architecture** (v4): Support for pure_dfs, llm_only, and hybrid execution modes
- **Transition trace system**: Records complete action sequences between state transitions
- **UI coverage annotations**: Automatic [UNTESTED]/[TESTED-Nx] markers in prompts
- **Configurable thresholds**: Per-action-type loop detection thresholds via RVAgentConfig
- **Decision router node**: Intelligent routing between LLM and DFS based on context
- **DFS standalone mode**: Complete DFS exploration without LLM dependency
- **Shared dynamic graph**: LLM and DFS collaborate on same exploration graph
- **Mode override**: Environment variable RVAGENT_MODE for easy testing

### Fixed
- **Infinite loop problem**: TYPE_TEXT repeated 14x in same field (CryptoApp test)
- **Strategy integration**: DFS/BFS strategies now actively used (not passive guidance)
- **Baseline coverage**: Improved from 3 unique states to 10-15 expected

### Changed
- **DynamicStateGraph.Transition**: `action_sequence` is now `List[Dict]` instead of `action_id: int`
- **DFSStrategy**: Added standalone `select_next_action()` method for pure_dfs mode
- **AgentState**: Extended with loop detection and multi-mode tracking fields
- **RVAgentConfig**: Added execution_mode and threshold configuration fields
- **LangGraph structure**: New nodes (decision_router, strategy_validation, dfs_decide)

### Technical Details
- Estimated implementation: 18-22 hours, ~930 lines of code
- Backward compatible: v3 additions don't break existing code
- Test coverage: 300+ lines of new tests (loop detection + multi-mode)

### References
- Detailed planning: `docs/20251103_rvagent_pre_plano_v2.md`, `v3.md`, `v4_multimode.md`
- Problem analysis: v2.md lines 28-67 (loop chronology)
- Architecture decisions: v3.md lines 41-147, v4.md lines 27-59

### Migration Notes
- **For v3**: No breaking changes, automatic activation via new graph nodes
- **For v4**: Set `execution_mode` in config or use RVAGENT_MODE env var
- **Thresholds**: Defaults provided (TYPE_TEXT=2, CLICK=3, etc.), configurable if needed
```

**Estimativa**: ~80 linhas

---

## 8. Checklist de Implementação

### Ordem Recomendada

#### ✅ Dia 1 (8h): v3 Core - Loop Detection
- [ ] 1.1 - Criar backup dos arquivos existentes
- [ ] 1.2 - Modificar `DynamicStateGraph` (trace de sequências)
- [ ] 1.3 - Adicionar campos em `AgentState` (v3 apenas)
- [ ] 1.4 - Implementar helper methods em `rv_agent.py`:
  - [ ] `_count_consecutive_actions()`
  - [ ] `_actions_are_similar()`
- [ ] 1.5 - Implementar `_strategy_validation_node()` em `rv_agent.py`
- [ ] 1.6 - Implementar `select_untested_action()` em `DFSStrategy`
- [ ] 1.7 - Modificar `_observe_node()` (detecção de transição)
- [ ] 1.8 - Modificar `_learn_node()` (trace + coverage)
- [ ] 1.9 - Modificar `_build_agent_graph()` para v3 (adicionar validation node)
- [ ] 1.10 - Teste manual: CryptoApp (verificar loop eliminado)

#### ✅ Dia 2 (6h): v4 Multi-modo
- [ ] 2.1 - Criar/estender `RVAgentConfig` com campos v4 + thresholds
- [ ] 2.2 - Adicionar campos v4 em `AgentState`
- [ ] 2.3 - Estender `DFSStrategy` com `select_next_action()` standalone
- [ ] 2.4 - Implementar helpers em `DFSStrategy`:
  - [ ] `_action_to_dict()`
  - [ ] `_generate_input_text()`
  - [ ] `_get_mop_priority()`
- [ ] 2.5 - Implementar `_decision_router_node()` em `rv_agent.py`
- [ ] 2.6 - Implementar `_dfs_decide_node()` em `rv_agent.py`
- [ ] 2.7 - Implementar 3 graph builders:
  - [ ] `_build_graph_pure_dfs()`
  - [ ] `_build_graph_llm_only()`
  - [ ] `_build_graph_hybrid()`
- [ ] 2.8 - Modificar `__init__()` (modo + LLM opcional)
- [ ] 2.9 - Modificar `run()` (métricas de modo)
- [ ] 2.10 - Teste manual: 3 modos com CryptoApp

#### ✅ Dia 3 (4h): Testes e Documentação
- [ ] 3.1 - Criar `test_loop_detection.py` (5 testes unitários)
- [ ] 3.2 - Criar `test_multi_mode.py` (4 classes de testes)
- [ ] 3.3 - Criar `test_v3v4_validation.py` (script comparativo)
- [ ] 3.4 - Executar suite completa de testes
- [ ] 3.5 - Análise comparativa: baseline vs v3 vs v4
- [ ] 3.6 - Atualizar `CLAUDE.md` (seção RVAgent Multi-Mode)
- [ ] 3.7 - Criar `CHANGELOG.md`
- [ ] 3.8 - Code review final
- [ ] 3.9 - Commit com mensagem descritiva

---

## 9. Métricas de Sucesso

### ✅ Objetivo Primário (v3): Eliminar Loops
- **Zero loops com >5 repetições consecutivas**
- **Fallback DFS ativa quando loop detectado**
- **Transições com sequências completas salvas**

### ✅ Objetivo Secundário (v4): Multi-modo Funcional
- **Pure DFS funciona sem LLM** (0 chamadas LLM)
- **LLM Only funciona como V10** (comportamento idêntico)
- **Hybrid usa ambos** com fallback inteligente
- **Override via RVAGENT_MODE** funciona

### ✅ Comparação CryptoApp (120s)

| Métrica | Baseline V10 | v3 Esperado | v4 Hybrid Esperado |
|---------|-------------|-------------|---------------------|
| **Unique States** | 3 | 10-15 | 12-18 |
| **Transitions** | 0 | 15-25 | 18-28 |
| **Loops >5 reps** | 1 (TYPE_TEXT 14x) | **0** | **0** |
| **Revisit Rate** | 70%+ | 30-40% | 25-35% |
| **Coverage/Screen** | ~20% | 40-60% | 50-70% |
| **MOP Trigger Rate** | 0% | 40-60% | 50-70% |
| **LLM Calls** | 100% | 70-80% | 30-70% (variável) |

---

## 10. Considerações Importantes

### 📝 Comentários no Código
- ✅ Usar **inglês** em todo código e comentários
- ✅ Refletir **estado atual** (não mencionar migração/legado/fases/versões)
- ✅ Evitar termos de **viés** (moderna, sofisticada, avançada, poderosa)
- ✅ **Sem promotional language** (revolucionário, inovador, cutting-edge)
- ✅ **Público-alvo**: desenvolvedores e pesquisadores

**Exemplo CORRETO**:
```python
def _strategy_validation_node(self, state: AgentState) -> AgentState:
    """
    Validates LLM action to detect loops based on consecutive repetitions.
    Uses configurable thresholds per action type.
    """
```

**Exemplo INCORRETO**:
```python
def _strategy_validation_node(self, state: AgentState) -> AgentState:
    """
    ❌ Modern validation system that detects loops elegantly!
    ❌ Part of our new Phase 3 migration to advanced architecture.
    ❌ This sophisticated approach prevents infinite loops brilliantly.
    """
```

---

### 🗂️ Código Legado
- ✅ **Arquivos modificados**: backup em `backup/2025-11-03_v3-v4-refactor/`
- ✅ **Prompts versionados** (`v10.py`, etc): **permanecem onde estão**
- ✅ **Scripts de teste antigos**: mover para backup se não mais usados
- ✅ **Sem código comentado**: remover completamente (git guarda histórico)

---

### 🔧 Thresholds Configuráveis
- ✅ Implementados via `RVAgentConfig`
- ✅ Defaults: `TYPE_TEXT=2`, `CLICK=3`, `SCROLL=5`, `SWIPE=5`, `BACK=2`, `default=3`
- ✅ Acesso uniforme via `config.get_threshold(action_type)`
- ✅ Documentar defaults no código e docs

---

## 11. Referências Completas aos Documentos Base

| Tópico | Documento | Linhas | Descrição |
|--------|-----------|--------|-----------|
| **Problema crítico** | v2.md | 1-67 | Loop infinito TYPE_TEXT 14x, cronologia completa |
| **Validação qwen3-vl** | v2.md | 79-99, 563-586 | Teste com 3px precisão, aprovação |
| **Comparativo estratégias** | v2.md | 367-421 | DFS vs BFS vs LLM vs Híbrido |
| **Detecção de loops** | v3.md | 41-107 | Decisão: consecutivos, não duplicatas |
| **Integração DFS/BFS** | v3.md | 110-147 | Medium enforcement, fluxo validação |
| **UI Coverage** | v3.md | 150-205 | Reativar anotações, ciclo |
| **Trace sequências** | v3.md | 207-294 | Estender DynamicStateGraph |
| **Backtracking BACK** | v3.md | 297-330 | BACK puro, simplicidade |
| **WTG decisão** | v3.md | 332-352 | NÃO integrar no MVP |
| **Histórico ações** | v3.md | 355-373 | Manter infraestrutura |
| **Arquitetura v3** | v3.md | 376-473 | Fluxo LangGraph completo |
| **Estruturas de dados** | v3.md | 474-523 | AgentState, ScreenNode, Transition |
| **Fluxos exemplo** | v3.md | 525-643 | Exploração normal, loop detection |
| **Mudanças código v3** | v3.md | 646-954 | Detalhamento por arquivo |
| **Métricas sucesso v3** | v3.md | 957-1031 | Objetivos quantitativos |
| **Estimativas v3** | v3.md | 986-1009 | LOC, tempo, riscos |
| **Trade-offs v3** | v3.md | 1033-1055 | Decisões documentadas |
| **Modo PURE_DFS** | v4.md | 135-489 | Algoritmo DFS completo, heurísticas |
| **Modo LLM_ONLY** | v4.md | 85-101 | V10 atual |
| **Modo HYBRID** | v4.md | 103-130, 728-965 | LLM + validação + fallback |
| **Decision Router** | v4.md | 851-965 | Lógica de roteamento |
| **Grafo compartilhado** | v4.md | 1028-1141 | LLM + DFS colaboração |
| **Sistema configuração** | v4.md | 1143-1386 | RVAgentConfig estendido |
| **Implementação v4** | v4.md | 1389-1652 | Modificações em rv_agent.py |
| **Testes v4** | v4.md | 1656-1700 | Suite multi-modo |

---

## 12. Troubleshooting e Dicas

### Problema: LLM não disponível em testes
**Solução**: Use `execution_mode="pure_dfs"` para testes offline.

### Problema: Thresholds muito baixos (muitos fallbacks)
**Solução**: Ajustar via config: `threshold_type_text=3` ou superior.

### Problema: DFS não escolhe ações com MOP
**Solução**: Verificar que `static_data` está sendo passado para `DFSStrategy.__init__()`.

### Problema: Transições não sendo registradas
**Solução**: Verificar que `last_screen_hash` está sendo atualizado em `_observe_node()`.

### Problema: Testes falhando por timeout
**Solução**: Aumentar timeout em configs de teste ou usar mock de device.

---

## 13. Próximos Passos Pós-Implementação

### ✅ Curto Prazo (Após v3+v4 Base)
1. Executar benchmark com 10 apps do dataset
2. Analisar distribuição LLM vs DFS em modo hybrid
3. Ajustar thresholds baseado em dados empíricos
4. Publicar resultados comparativos

### 🔮 Médio Prazo (Próximo Sprint)
1. Implementar `BFSStrategy` completa (similar a DFS)
2. Adicionar novas estratégias (Random, GreedyCoverage)
3. Implementar `BaseStrategy` interface + Factory
4. Modo `dynamic` com seleção automática de estratégia

### 🔮 Longo Prazo (Roadmap Futuro)
1. RL Integration para otimização de decisões
2. Cross-app learning (padrões transferíveis)
3. BFS queue navigation com shortest path
4. WTG integration para modelos maiores
5. Adaptive thresholds baseados em ML

---

**Plano criado em**: 2025-11-03
**Escopo**: v3 (loop detection) + v4 Base (multi-modo)
**Estimativa total**: 18-22 horas | ~930 linhas de código
**Status**: ✅ Pronto para implementação

---

**FIM DO PLANO**

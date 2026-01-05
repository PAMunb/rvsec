# RVAgent - Plano de Refatoração Consolidado
**Data**: 2025-11-03
**Status**: Plano executável definitivo
**Baseado em**: v2, v3, v4 planning documents

---

## 1. Contexto e Problema

### 1.1 Estado Atual do RVAgent
- **Versão**: V9 com few-shot examples e native tool calling
- **Backend LLM**: Ollama com modelos Qwen2.5-Coder, Gemma2, etc.
- **Problema crítico**: Loop infinito - agente repete mesma ação 14+ vezes
  - Exemplo: TYPE_TEXT "Test message" repetido, nunca clica GENERATE HASH [M]

### 1.2 Root Causes Identificados (ver [v2] seção 1.3)
1. **Sem detecção de estado visitado**: Hash `81d640c95c72...` visitado 14+ vezes, sem alerta
2. **Sem detecção de ação repetida**: TYPE_TEXT(364, 256, "Test message") 14x, sem bloqueio
3. **Sem estratégia enforcement**: DFS diria "GENERATE HASH [M] não-testado - ALTA PRIORIDADE!"
4. **Sem backtracking**: Quando stuck, não sabe fazer BACK ou HOME
5. **Prompt inadequado**: Few-shots não ensinam "se já preencheu, NÃO preenche de novo"

### 1.3 Componentes Existentes (ver [v2] seção 1.2)
Sistema completo de estratégias DFS/BFS já existe mas NUNCA é chamado:
- ✅ `strategies/dfs_strategy.py` - DFS com backtracking
- ✅ `strategies/bfs_strategy.py` - BFS com queue
- ✅ `memory/dynamic_state_graph.py` - Grafo de estados
- ✅ `memory/long_term_memory.py` - Memória de longo prazo
- ✅ `memory/short_term_memory.py` - Memória de curto prazo
- ✅ `memory/ui_coverage_tracker.py` - Cobertura de UI

**Problema**: Estratégias fornecem apenas "guidance" passiva, LLM ignora completamente.

---

## 2. Decisões Arquiteturais Tomadas

### 2.1 DECISÃO #1: Modelo LLM (ver [v2] seção 5.1, validado em [v2] seção 15.1)
**Qwen3-VL + LangGraph VALIDADO** (3px precision!)
```
Test com LangGraph + ToolNode + ChatOllama:
- Model: qwen3-vl:4b
- Coordenadas esperadas: (364, 183)
- Coordenadas obtidas: (364, 180)
- Diferença: 0px X, 3px Y
- Precisão: PERFEITA!
```

**Escolha final**: ✅ **Opção A** - qwen3-vl:4b com LangGraph + ToolNode + visão nativa

### 2.2 DECISÃO #2: Enforcement de Estratégia (ver [v3] seção 2.2)
**Escolha final**: ✅ **Medium enforcement** - LLM decide, estratégia valida (não bloqueia completamente)

**Motivação**: Balanceamento entre criatividade da LLM e sistematicidade das estratégias

### 2.3 DECISÃO #3: Detecção de Loops (ver [v3] seção 2.1)
**Escolha final**: ✅ **Detecção de loops baseado em repetições consecutivas** (não duplicatas gerais)

**Thresholds por tipo de ação**:
- TYPE_TEXT: 2 (permitir preencher + corrigir)
- CLICK: 3 (permitir combobox workflows)
- SCROLL: 5 (listas longas)
- SWIPE: 5
- BACK: 2
- Default: 3

### 2.4 DECISÃO #4: Arquitetura Multi-Modo (ver [v4] seção 1)
**Escolha final**: ✅ **Implementar arquitetura multi-modo**
- **PURE_DFS**: DFS standalone (sem LLM, baseline)
- **LLM_ONLY**: V10 atual (máxima criatividade)
- **HYBRID**: LLM + DFS validation/fallback (recomendado)
- **DYNAMIC**: Seleção automática de estratégia (futuro)

---

## 3. Arquitetura Final

### 3.1 Fluxo LangGraph Completo (ver [v3] seção 3.1, [v4] seção 14.4)
```
┌─────────────────────────────────────────────────────────────┐
│                     LANGGRAPH WORKFLOW                      │
└─────────────────────────────────────────────────────────────┘

  ┌──────────┐
  │  START   │
  └────┬─────┘
       │
       ▼
  ┌──────────────┐
  │   OBSERVE    │  1. Captura tela (XML + screenshot)
  │              │  2. Computa screen_hash
  │              │  3. Detecta mudança de estado
  │              │  4. Registra transição (se mudou)
  │              │  5. Anota UI com coverage tracker
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │   ROUTER     │  1. Decide qual caminho seguir
  │   (MODE)     │  2. PURE_DFS → dfs_decide
  │              │  3. LLM_ONLY → assistant
  │              │  4. HYBRID → decision routing
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  STRATEGY    │  1. Analisa contexto (dynamic selection)
  │  SELECTOR    │  2. Escolhe melhor estratégia
  │  (optional)  │  3. Retorna ação
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  ASSISTANT   │  1. Constrói prompt com UI anotada
  │   (LLM)      │  2. LLM decide próxima ação
  │              │  3. Retorna tool_calls
  └──────┬───────┘
         │
         ▼
  ┌──────────────────┐
  │   STRATEGY       │  1. Analisa ação da LLM
  │   VALIDATION     │  2. Detecta loops (repetições consecutivas)
  │                  │  3. Se loop: escolhe fallback (untested action)
  │                  │  4. Se válido: passa ação original
  └──────┬───────────┘
         │
         ▼
  ┌──────────────┐
  │  DFS DECIDE  │  1. DFS escolhe próxima ação
  │  (DFS mode)  │  2. Backtracking automático
  │              │  3. Prioriza MOP markers
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │    TOOLS     │  1. Executa ação (android_click, type_text, etc.)
  │  (ToolNode)  │  2. Retorna resultado
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │    LEARN     │  1. Adiciona ação ao trace
  │              │  2. Registra em UI coverage
  │              │  3. Atualiza memórias
  │              │  4. Incrementa iteração
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  timeout?    │───No──▶ volta para OBSERVE
  └──────┬───────┘
         │
        Yes
         │
         ▼
  ┌──────────┐
  │   END    │
  └──────────┘
```

---

## 4. Componentes a Modificar/Implementar

### 4.1 Arquivo: `dynamic_state_graph.py` (ver [v3] seção 6.1)
**Modificações necessárias**:

```python
@dataclass
class Transition:
    from_hash: str                  # Identificador estrutural origem
    to_hash: str                    # Identificador estrutural destino
    action_sequence: List[Dict]     # TODAS as ações que levaram à transição (era action_id: int)
    timestamp: float                # Quando aconteceu

class DynamicStateGraph:
    def __init__(self):
        self.states: Dict[str, ScreenNode] = {}
        self.transitions: List[Transition] = []
        self.current_trace: List[Dict] = []  # NOVO: trace da sessão atual

    def record_action_to_trace(self, action: Dict):  # NOVO
        """Adiciona ação ao trace atual (entre estados)"""
        self.current_trace.append(action)

    def record_transition(self, from_hash: str, to_hash: str, timestamp: float):  # MODIFICADO
        """Quando muda estado, salva trace completo"""
        self.transitions.append(
            Transition(
                from_hash=from_hash,
                to_hash=to_hash,
                action_sequence=self.current_trace.copy(),  # Sequência completa
                timestamp=timestamp
            )
        )
        # Reset trace para próxima transição
        self.current_trace = []

    def get_transition_graph_report(self) -> Dict:  # NOVO
        """Relatório com sequências completas"""
        return {...}
```

**Estimativa**: ~30 linhas de código modificadas/adicionadas

### 4.2 Arquivo: `rv_agent.py` (ver [v3] seção 6.2, [v4] seção 14.3)
**Modificações e adições**:

```python
# NOVO Nó: Decision Router
def _decision_router_node(self, state: AgentState) -> AgentState:
    """
    Roteador que decide qual caminho seguir baseado no modo de execução.
    """
    mode = self.config.get_execution_mode()

    if mode == "pure_dfs":
        decision = "dfs"
        reason = "pure_dfs mode"
    elif mode == "llm_only":
        decision = "llm"
        reason = "llm_only mode"
    elif mode == "hybrid":
        # Verifica se deve usar fallback
        llm_failures = state.get("consecutive_llm_failures", 0)
        loop_detected_last = state.get("loop_detected", False)

        if llm_failures >= 2:
            decision = "dfs"
            reason = f"LLM failed {llm_failures} times, using DFS fallback"
        elif loop_detected_last:
            decision = "dfs"
            reason = "Loop detected in last iteration, trying DFS"
        else:
            decision = "llm"
            reason = "Normal LLM path"
    else:
        decision = "llm"
        reason = "default"

    logger.info(f"🚦 Router: {decision.upper()} path ({reason})")

    return {
        "execution_mode": mode,
        "router_decision": decision,
        "router_reason": reason
    }

def _route_decision(self, state: AgentState) -> str:
    """
    Conditional edge function.
    Returns: "llm", "dfs", ou "end"
    """
    decision = state.get("router_decision", "llm")
    
    if state.get("exploration_complete", False):
        return "end"
    
    return decision

# NOVO Nó: Strategy Validation (ver [v3] seção 4.4)
def _strategy_validation_node(self, state: AgentState) -> AgentState:
    """
    Valida ação da LLM e usa DFS como fallback se necessário.
    """
    llm_action = state['current_action']
    recent_window = state.get('recent_action_window', [])
    screen_hash = state['current_screen_hash']

    # Conta repetições consecutivas
    consecutive_count = self._count_consecutive_actions(recent_window, llm_action)

    # Thresholds por tipo de ação
    MAX_CONSECUTIVE = {
        "TYPE_TEXT": 2,
        "CLICK": 3,
        "SCROLL": 5,
        "SWIPE": 5,
        "BACK": 2,
        "default": 3
    }

    action_type = llm_action.get("action_type", "default")
    threshold = MAX_CONSECUTIVE.get(action_type, MAX_CONSECUTIVE["default"])

    if consecutive_count >= threshold:
        logger.warning(f"⚠️ LOOP: {action_type} repeated {consecutive_count}x")

        # Fallback: estratégia escolhe ação untested
        screen_desc = state["screen_description_obj"]
        fallback = self.strategy.select_next_action(screen_hash, screen_desc)

        if fallback:
            logger.info(f"   Using strategy fallback: {fallback['action_type']}")
            return {
                "current_action": fallback,
                "loop_detected": True,
                "used_fallback": True
            }
        else:
            # Sem untested? BACK
            logger.info("   No untested actions, executing BACK")
            return {
                "current_action": {"action_type": "BACK"},
                "loop_detected": True,
                "used_fallback": True
            }

    # Válido
    return {
        "current_action": llm_action,
        "loop_detected": False,
        "used_fallback": False
    }

# NOVO Nó: DFS Decide (ver [v4] seção 4.3)
def _dfs_decide_node(self, state: AgentState) -> AgentState:
    """
    Nó que usa DFS para decidir ação (sem LLM).
    """
    screen_hash = state["current_screen_hash"]
    screen_desc = state["screen_description_obj"]

    logger.info(f"🤖 DFS deciding next action for state {screen_hash[:8]}")

    # DFS escolhe próxima ação
    action = self.strategy.select_next_action(screen_hash, screen_desc)

    if action is None:
        logger.info("✅ DFS: Exploration complete, no more actions")
        return {
            "current_action": {"action_type": "END"},
            "decision_maker": "dfs",
            "exploration_complete": True
        }

    logger.info(f"   Action: {action['action_type']} - {action.get('description', '')}")
    if action.get("action_type") == "TYPE_TEXT":
        logger.info(f"   Text: {action.get('text', '')}")

    return {
        "current_action": action,
        "decision_maker": "dfs",
        "exploration_complete": False,
        "consecutive_llm_failures": 0  # Reset contador
    }

# NOVO Nó: Strategy Selector (ver [v4] seção 14.3)
def _strategy_selector_node(self, state: AgentState) -> AgentState:
    """
    Nó que seleciona dinamicamente qual estratégia usar.
    """
    screen_hash = state["current_screen_hash"]
    screen_desc = state["screen_description_obj"]
    
    # Critérios de seleção de estratégia
    if self._has_mop_markers(screen_desc):
        strategy_name = "dfs"
        reason = "MOP markers detected → DFS for systematic exploration"
    elif self._high_revisit_rate(screen_hash):
        strategy_name = "bfs"
        reason = "High revisit rate → BFS to explore breadth-first"
    elif self._is_form(screen_desc):
        if self.config.get_execution_mode() in ["llm_only", "hybrid"]:
            strategy_name = "llm"
            reason = "Form detected → LLM for semantic understanding"
        else:
            strategy_name = "dfs"
            reason = "Form detected → DFS (LLM not available)"
    elif self._is_long_list(screen_desc):
        strategy_name = "random"
        reason = "Long list detected → Random for fuzzing"
    elif self._many_options(screen_desc):
        strategy_name = "greedy"
        reason = "Many options → Greedy for coverage optimization"
    else:
        strategy_name = "dfs"
        reason = "Default → DFS for systematic exploration"

    logger.info(f"🎯 Strategy Selector: {strategy_name.upper()}")
    logger.info(f"   Reason: {reason}")

    # Executa estratégia selecionada
    if strategy_name == "llm":
        action = self._get_llm_action(state)
    else:
        strategy = self._get_or_create_strategy(strategy_name)
        action = strategy.select_next_action(screen_hash, screen_desc)

    if action is None:
        action = {"action_type": "END"}

    return {
        "selected_strategy": strategy_name,
        "selection_reason": reason,
        "current_action": action,
        "decision_maker": strategy_name
    }

# Modificação: Observe Node (ver [v3] seção 6.2)
def _observe_node(self, state: AgentState) -> AgentState:
    # ... código existente para capturar tela ...

    screen_hash = compute_screen_hash(xml)

    # NOVO: Detecta mudança de estado
    if state.get("last_screen_hash") and state["last_screen_hash"] != screen_hash:
        # Transição detectada!
        self.dynamic_graph.record_transition(
            from_hash=state["last_screen_hash"],
            to_hash=screen_hash,
            timestamp=time.time()
        )
        logger.info(f"📊 Transition: {state['last_screen_hash'][:8]} → {screen_hash[:8]}")
        logger.info(f"   Actions in sequence: {len(self.dynamic_graph.current_trace)}")

    # NOVO: Anota UI com coverage
    annotated_desc = self.ui_coverage.annotate_screen_elements(
        screen_desc_text,
        screen_hash
    )

    return {
        "current_screen_hash": screen_hash,
        "last_screen_hash": screen_hash,
        "screen_description": annotated_desc,  # Com [UNTESTED]
        # ... resto ...
    }

# Modificação: Learn Node (ver [v3] seção 6.2)
def _learn_node(self, state: AgentState) -> AgentState:
    action = state["current_action"]
    screen_hash = state["current_screen_hash"]

    # NOVO: Adiciona ação ao trace
    self.dynamic_graph.record_action_to_trace(action)

    # NOVO: Registra em UI coverage
    element_id = self._extract_element_id(action)
    if element_id:
        self.ui_coverage.record_interaction(
            element_id=element_id,
            action_type=action["action_type"],
            screen_hash=screen_hash,
            success=True
        )

    # NOVO: Atualiza recent_action_window
    recent = state.get("recent_action_window", [])
    recent.append(action)
    if len(recent) > 10:  # Mantém últimas 10
        recent = recent[-10:]

    return {
        "recent_action_window": recent,
        "iteration": state["iteration"] + 1,
        "last_action": action
    }

# Modificação: Build Agent Graph
def _build_agent_graph(self):
    """
    Constrói grafo LangGraph com suporte a modo híbrido e multi-modo.
    """
    mode = self.config.get_execution_mode()
    
    graph = StateGraph(AgentState)

    if mode == "pure_dfs":
        # Grafo DFS puro
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

    elif mode == "llm_only":
        # Grafo LLM apenas (V10 atual)
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

    elif mode == "hybrid":
        # Grafo híbrido (v3 + v4)
        graph.add_node("observe", self._observe_node)
        graph.add_node("decision_router", self._decision_router_node)
        graph.add_node("assistant", self._assistant_node)
        graph.add_node("strategy_validation", self._strategy_validation_node)
        graph.add_node("dfs_decide", self._dfs_decide_node)
        graph.add_node("tools", ToolNode(self.tools))
        graph.add_node("learn", self._learn_node)

        graph.set_entry_point("observe")
        graph.add_edge("observe", "decision_router")

        graph.add_conditional_edges(
            "decision_router",
            self._route_decision,
            {
                "llm": "assistant",
                "dfs": "dfs_decide",
                "end": END
            }
        )

        graph.add_edge("assistant", "strategy_validation")
        graph.add_edge("strategy_validation", "tools")
        graph.add_edge("dfs_decide", "tools")
        graph.add_edge("tools", "learn")
        graph.add_conditional_edges(
            "learn",
            self._should_continue,
            {"continue": "observe", "end": END}
        )

    elif mode == "dynamic":
        # Grafo com seleção dinâmica de estratégia
        graph.add_node("observe", self._observe_node)
        graph.add_node("strategy_selector", self._strategy_selector_node)
        graph.add_node("tools", ToolNode(self.tools))
        graph.add_node("learn", self._learn_node)

        graph.set_entry_point("observe")
        graph.add_edge("observe", "strategy_selector")
        graph.add_edge("strategy_selector", "tools")
        graph.add_edge("tools", "learn")
        graph.add_conditional_edges(
            "learn",
            self._should_continue,
            {"continue": "observe", "end": END}
        )

    return graph.compile()

# Helper methods para detecção de loops (ver [v3] seção 6.2)
def _count_consecutive_actions(self, recent: List[Dict], current: Dict) -> int:
    """Conta quantas vezes ação atual aparece consecutivamente no histórico"""
    count = 0
    for action in reversed(recent):
        if self._actions_are_similar(action, current):
            count += 1
        else:
            break
    return count

def _actions_are_similar(self, a1: Dict, a2: Dict) -> bool:
    """Compara se duas ações são similares"""
    if a1.get("action_type") != a2.get("action_type"):
        return False

    # Para TYPE_TEXT, compara também o texto
    if a1.get("action_type") == "TYPE_TEXT":
        return a1.get("text") == a2.get("text")

    # Para CLICK, compara coordenadas (tolerância de 20px)
    if a1.get("action_type") == "CLICK":
        x1, y1 = a1.get("x", 0), a1.get("y", 0)
        x2, y2 = a2.get("x", 0), a2.get("y", 0)
        return abs(x1 - x2) < 20 and abs(y1 - y2) < 20

    # Outros: compara apenas tipo
    return True

# Helper methods para seleção dinâmica (ver [v4] seção 14.3)
def _has_mop_markers(self, screen_desc) -> bool:
    """Verifica se tela tem ações com MOP markers."""
    if not self.static_data:
        return False

    all_actions = screen_desc.get_all_actions()
    for action in all_actions:
        if hasattr(action, 'directly_reaches_mop') and action.directly_reaches_mop:
            return True
        if hasattr(action, 'reaches_mop') and action.reaches_mop:
            return True

    return False

def _high_revisit_rate(self, screen_hash: str) -> bool:
    """Verifica se estado tem alta taxa de revisita."""
    if screen_hash not in self.dynamic_graph.states:
        return False

    node = self.dynamic_graph.states[screen_hash]
    return node.visit_count > 3

def _is_form(self, screen_desc) -> bool:
    """Detecta se tela é um formulário."""
    all_actions = screen_desc.get_all_actions()
    editable_count = sum(1 for a in all_actions if a.editable)
    has_submit = any(
        "submit" in (a.text or "").lower() or
        "login" in (a.text or "").lower() or
        "save" in (a.text or "").lower()
        for a in all_actions
    )
    return editable_count >= 2 and has_submit

def _is_long_list(self, screen_desc) -> bool:
    """Detecta se tela é uma lista longa."""
    all_actions = screen_desc.get_all_actions()
    class_counts = {}
    for action in all_actions:
        cls = action.class_name
        class_counts[cls] = class_counts.get(cls, 0) + 1
    return any(count > 10 for count in class_counts.values())

def _many_options(self, screen_desc) -> bool:
    """Verifica se tela tem muitas opções."""
    all_actions = screen_desc.get_all_actions()
    return len(all_actions) > 20

def _get_or_create_strategy(self, strategy_name: str):
    """Pega ou cria instância de estratégia."""
    if not hasattr(self, '_strategy_cache'):
        self._strategy_cache = {}

    if strategy_name not in self._strategy_cache:
        from rv_agent.strategies.strategy_factory import create_strategy

        self._strategy_cache[strategy_name] = create_strategy(
            strategy_name=strategy_name,
            dynamic_graph=self.dynamic_graph,
            static_data=self.static_data,
            mode="standalone"
        )

    return self._strategy_cache[strategy_name]
```

**Estimativa**: ~500 linhas de código adicionadas/modificadas

### 4.3 Arquivo: `state.py` (AgentState) (ver [v3] seção 6.4)
**Modificações**:

```python
class AgentState(TypedDict):
    # ... campos existentes ...

    # NOVOS CAMPOS (v3 + v4)
    recent_action_window: List[Dict]      # Para detecção de loops
    loop_detected: bool                   # Flag de loop
    used_fallback: bool                   # Flag de fallback usado
    last_screen_hash: Optional[str]       # Para detectar transições
    execution_mode: str                   # "pure_dfs", "llm_only", "hybrid", "dynamic"
    router_decision: Optional[str]        # "llm" ou "dfs"
    router_reason: Optional[str]          # Motivo da decisão
    decision_maker: str                   # "llm", "dfs", "dfs_fallback"
    last_decision_maker: Optional[str]    # Quem decidiu na última iteração
    consecutive_llm_failures: int         # Contador de falhas LLM
    llm_timeout_occurred: bool            # Flag de timeout
    exploration_complete: bool            # DFS sinalizou fim
    llm_decisions: int                    # Quantas decisões da LLM
    dfs_decisions: int                    # Quantas decisões do DFS
    dfs_fallbacks: int                    # Quantas vezes DFS foi fallback
    selected_strategy: Optional[str]      # Estratégia selecionada dinamicamente
    selection_reason: Optional[str]       # Motivo da seleção
```

**Estimativa**: ~20 linhas adicionadas

### 4.4 Arquivo: `dfs_strategy.py` (ver [v3] seção 6.3, [v4] seção 13.3)
**Extensão do DFS Strategy**:

```python
# modules/rv-agent/src/rv_agent/strategies/dfs_strategy.py

from typing import List, Optional, Dict, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class DFSState:
    """
    Estado DFS para backtracking.
    """
    screen_hash: str              # Hash do estado
    depth: int                    # Profundidade na árvore
    parent_hash: Optional[str]    # Estado pai (para backtracking)
    untested_count: int           # Ações não testadas

class DFSStrategy:
    """
    Estratégia DFS que pode operar em 3 modos:
    1. GUIDANCE: Apenas fornece recomendações (v3)
    2. STANDALONE: Toma decisões completas sem LLM (v4)
    3. FALLBACK: Backup quando LLM falha (v4)
    """

    def __init__(
        self,
        dynamic_graph: DynamicStateGraph,
        static_data: Optional[StaticAnalysisData] = None,
        mode: str = "hybrid"
    ):
        """
        Inicializa estratégia DFS.

        Args:
            dynamic_graph: Grafo dinâmico compartilhado
            static_data: Dados de análise estática (opcional)
            mode: "guidance", "standalone", "hybrid"
        """
        self.dynamic_graph = dynamic_graph
        self.static_data = static_data
        self.mode = mode

        # Estado DFS para standalone
        self.state_stack: List[DFSState] = []  # Pilha de estados
        self.visited_states: Set[str] = set()  # Estados já visitados
        self.current_depth = 0

        logger.info(f"DFSStrategy initialized in {mode} mode")

    def select_next_action(
        self,
        screen_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[Dict]:
        """
        MÉTODO PRINCIPAL: Escolhe próxima ação usando DFS puro.

        Este método opera COMPLETAMENTE SEM LLM!

        Algoritmo:
        1. Verifica se estado é novo → adiciona à pilha
        2. Se tem ações untested → escolhe uma (DEEPEN)
        3. Se estado esgotado → faz BACK (BACKTRACK)
        4. Se pilha vazia → exploração completa
        """
        logger.debug(f"🤖 DFS: Processing state {screen_hash[:8]}, depth={self.current_depth}")

        # ===== PASSO 1: Gerencia Estado no Grafo =====
        if screen_hash not in self.dynamic_graph.states:
            # Estado NOVO - primeira visita
            node = self.dynamic_graph.get_or_create_state(
                screen_hash,
                screen_desc.activity,
                screen_desc
            )

            # Determina pai (último da pilha)
            parent_hash = self.state_stack[-1].screen_hash if self.state_stack else None

            # Adiciona à pilha DFS
            dfs_state = DFSState(
                screen_hash=screen_hash,
                depth=self.current_depth,
                parent_hash=parent_hash,
                untested_count=node.total_actions
            )
            self.state_stack.append(dfs_state)
            self.visited_states.add(screen_hash)

            logger.info(f"📍 DFS: New state discovered at depth {self.current_depth}")
            logger.info(f"   Activity: {screen_desc.activity}")
            logger.info(f"   Total actions: {node.total_actions}")
        else:
            # Estado REVISITADO
            node = self.dynamic_graph.states[screen_hash]
            logger.debug(f"🔄 DFS: Revisited state (visit count: {node.visit_count})")

        # ===== PASSO 2: Pega Ações Untested =====
        all_actions = screen_desc.get_all_actions()
        untested = [
            action for action in all_actions
            if action.id not in node.executed_actions
        ]

        logger.debug(f"   Untested actions: {len(untested)}/{len(all_actions)}")

        # ===== PASSO 3: DEEPEN - Explorar Estado Atual =====
        if untested:
            # Prioriza por MOP markers
            priority_sorted = sorted(
                untested,
                key=lambda a: self._get_mop_priority(a),
                reverse=True
            )

            top_action = priority_sorted[0]

            # Incrementa profundidade (vamos mais fundo)
            self.current_depth += 1

            action_dict = self._action_to_dict(top_action)

            logger.info(f"⬇️  DFS DEEPEN: {action_dict['action_type']} - {action_dict.get('description', '')}")
            logger.info(f"   Priority: {self._get_mop_priority(top_action)} (MOP marker)")

            return action_dict

        # ===== PASSO 4: BACKTRACK - Estado Esgotado =====
        else:
            logger.info(f"🔙 DFS: State {screen_hash[:8]} exhausted, backtracking")

            # Remove estado atual da pilha
            if self.state_stack and self.state_stack[-1].screen_hash == screen_hash:
                current_state = self.state_stack.pop()
                logger.debug(f"   Popped state from depth {current_state.depth}")

            # Decrementa profundidade
            if self.current_depth > 0:
                self.current_depth -= 1

            # Verifica se pilha está vazia
            if not self.state_stack:
                logger.info("✅ DFS: Exploration complete (stack empty)")
                logger.info(f"   Total states explored: {len(self.visited_states)}")
                return None  # Sinaliza fim da exploração

            # Executa BACK para voltar ao estado anterior
            return {
                "action_type": "BACK",
                "reason": "DFS backtracking",
                "description": f"Backtrack to depth {self.current_depth}"
            }

    def _action_to_dict(self, action) -> Dict:
        """
        Converte ScreenAction para dict executável.
        """
        # Determina tipo baseado em flags
        if action.editable:
            action_type = "TYPE_TEXT"
        elif action.scrollable:
            action_type = "SCROLL"
        elif action.long_clickable:
            action_type = "LONG_CLICK"
        elif action.clickable:
            action_type = "CLICK"
        else:
            action_type = "CLICK"

        # Monta dict base
        result = {
            "action_type": action_type,
            "x": action.bounds[0] if action.bounds else 0,
            "y": action.bounds[1] if action.bounds else 0,
            "description": action.text or action.content_desc or action.class_name or "element",
            "id": action.id,
            "mop_priority": self._get_mop_priority(action)
        }

        # Para TYPE_TEXT, gera texto de entrada
        if action_type == "TYPE_TEXT":
            result["text"] = self._generate_input_text(action)

        # Para SCROLL, determina direção
        if action_type == "SCROLL":
            result["direction"] = "down"  # Default

        return result

    def _generate_input_text(self, action) -> str:
        """
        Gera texto para preencher campos SEM usar LLM.
        """
        # Concatena todas as pistas textuais
        hints = " ".join([
            action.text or "",
            action.content_desc or "",
            action.resource_id or ""
        ]).lower()

        logger.debug(f"   Generating text for field hints: '{hints}'")

        # Heurísticas por tipo de campo
        if "email" in hints or "e-mail" in hints:
            return "dfs_test@example.com"

        elif "password" in hints or "senha" in hints or "pass" in hints:
            return "DFSTest123!"

        elif "phone" in hints or "telefone" in hints or "celular" in hints:
            return "5551234567"

        elif "number" in hints or "numero" in hints or "age" in hints or "idade" in hints:
            return "42"

        elif "name" in hints or "nome" in hints:
            if "first" in hints or "primeiro" in hints:
                return "DFS"
            elif "last" in hints or "ultimo" in hints or "sobrenome" in hints:
                return "Test"
            else:
                return "DFS Test User"

        elif "address" in hints or "endereco" in hints:
            return "123 DFS Test Street"

        elif "city" in hints or "cidade" in hints:
            return "Test City"

        elif "zip" in hints or "cep" in hints or "postal" in hints:
            return "12345"

        elif "date" in hints or "data" in hints:
            return "01/01/2025"

        elif "url" in hints or "website" in hints or "site" in hints:
            return "https://example.com"

        elif "search" in hints or "busca" in hints or "query" in hints:
            return "DFS test search"

        elif "message" in hints or "mensagem" in hints or "text" in hints:
            return "DFS test message"

        else:
            # Fallback genérico
            return "DFS Test Input"

    def _get_mop_priority(self, action) -> int:
        """
        Retorna prioridade baseada em MOP markers.
        """
        if not self.static_data:
            return 1  # Sem análise estática, todas iguais

        # Verifica markers
        if hasattr(action, 'directly_reaches_mop') and action.directly_reaches_mop:
            return 3

        if hasattr(action, 'reaches_mop') and action.reaches_mop:
            return 2

        return 1

    def get_state_stack_depth(self) -> int:
        """Retorna profundidade atual da pilha DFS."""
        return len(self.state_stack)

    def get_visited_count(self) -> int:
        """Retorna número de estados únicos visitados."""
        return len(self.visited_states)

    def reset(self):
        """Reseta estado DFS (útil para testes)."""
        self.state_stack.clear()
        self.visited_states.clear()
        self.current_depth = 0
        logger.info("DFS state reset")
```

**Estimativa**: ~200 linhas de código

### 4.5 Arquivo: `agent_config.py` (ver [v4] seção 6)
**Extensão da configuração**:

```python
# modules/rv-agent/src/rv_agent/config/agent_config.py

from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class RVAgentConfig:
    """Configuração do RVAgent com suporte multi-modo."""

    # Configurações existentes
    package_name: str
    device_id: str = "emulator-5554"
    timeout: int = 300
    max_iterations: int = 200

    # Estratégia
    strategy: str = "dfs"  # "dfs" ou "bfs"

    # LLM (para modos que usam)
    llm_model: str = "qwen3-vl:4b"
    llm_temperature: float = 0.0
    llm_top_p: float = 0.9
    llm_top_k: int = 40

    # ===== NOVOS CAMPOS (v4) =====

    # Modo de execução
    execution_mode: str = "hybrid"  # "pure_dfs", "llm_only", "hybrid", "dynamic"

    # Timeouts e retries (para hybrid/llm_only)
    llm_timeout: float = 30.0           # Timeout por chamada LLM (segundos)
    llm_max_retries: int = 2            # Tentativas antes de fallback DFS

    # Fallback automático
    auto_fallback_on_timeout: bool = True   # Se timeout → DFS
    auto_fallback_on_error: bool = True     # Se erro → DFS

    # Coordenadas
    device_dimensions: tuple = (1080, 1920)
    optimized_dimensions: tuple = (720, 1280)

    # Para modo dynamic: estratégias disponíveis
    available_strategies: List[str] = None

    def __post_init__(self):
        if self.available_strategies is None:
            # Default: todas as estratégias
            self.available_strategies = ["dfs", "bfs", "random", "greedy"]

    def get_execution_mode(self) -> str:
        """
        Retorna modo de execução.

        Prioridade:
        1. Variável de ambiente RVAGENT_MODE
        2. Campo execution_mode

        Permite override via env para testes:
        $ RVAGENT_MODE=pure_dfs poetry run python test.py
        """
        return os.getenv("RVAGENT_MODE", self.execution_mode)

    def validate(self):
        """
        Valida configuração.
        """
        valid_modes = ["pure_dfs", "llm_only", "hybrid", "dynamic"]
        mode = self.get_execution_mode()

        if mode not in valid_modes:
            raise ValueError(
                f"Invalid execution_mode: {mode}. "
                f"Must be one of {valid_modes}"
            )

        # Se modo usa LLM, valida configurações LLM
        if mode in ["llm_only", "hybrid", "dynamic"]:
            if not self.llm_model:
                raise ValueError("llm_model required for llm_only/hybrid/dynamic modes")

        # Valida strategy
        if self.strategy not in ["dfs", "bfs"]:
            raise ValueError(f"Invalid strategy: {self.strategy}")

    def get_mode_description(self) -> str:
        """Retorna descrição legível do modo."""
        mode = self.get_execution_mode()

        descriptions = {
            "pure_dfs": "DFS standalone (no LLM required)",
            "llm_only": "LLM only (current V10)",
            "hybrid": "LLM + DFS validation/fallback (recommended)",
            "dynamic": "Dynamic strategy selection (advanced)"
        }

        return descriptions.get(mode, mode)
```

### 4.6 Arquivo: `strategy_factory.py` (ver [v4] seção 13.3)
**Novo arquivo para factory pattern**:

```python
# modules/rv-agent/src/rv_agent/strategies/strategy_factory.py

from typing import Dict, Type
from .base_strategy import BaseStrategy
from .dfs_strategy import DFSStrategy
from .bfs_strategy import BFSStrategy

# ===== STRATEGY MAP (FACTORY) =====
STRATEGY_MAP: Dict[str, Type[BaseStrategy]] = {
    "dfs": DFSStrategy,
    "bfs": BFSStrategy,
    # Pode adicionar mais estratégias aqui
}


def create_strategy(
    strategy_name: str,
    dynamic_graph,
    static_data=None,
    mode: str = "hybrid"
) -> BaseStrategy:
    """
    Factory para criar estratégias.
    """
    if strategy_name not in STRATEGY_MAP:
        available = ", ".join(STRATEGY_MAP.keys())
        raise ValueError(
            f"Unknown strategy: {strategy_name}. "
            f"Available: {available}"
        )

    strategy_class = STRATEGY_MAP[strategy_name]

    return strategy_class(
        dynamic_graph=dynamic_graph,
        static_data=static_data,
        mode=mode
    )
```

### 4.7 Arquivo: `base_strategy.py` (ver [v4] seção 13.2)
**Novo arquivo para interface base**:

```python
# modules/rv-agent/src/rv_agent/strategies/base_strategy.py

from typing import Optional, Dict
from abc import ABC, abstractmethod
from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_agent.domain.screen import ScreenDescription


class BaseStrategy(ABC):
    """
    Interface base para estratégias de exploração.

    Todas as estratégias devem herdar desta classe e implementar
    o método select_next_action().
    """

    def __init__(
        self,
        dynamic_graph: DynamicStateGraph,
        static_data=None,
        mode: str = "hybrid"
    ):
        """
        Inicializa estratégia.

        Args:
            dynamic_graph: Grafo dinâmico compartilhado
            static_data: Dados de análise estática (opcional)
            mode: "guidance", "standalone", "hybrid"
        """
        self.dynamic_graph = dynamic_graph
        self.static_data = static_data
        self.mode = mode

    @abstractmethod
    def select_next_action(
        self,
        screen_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[Dict]:
        """
        MÉTODO PRINCIPAL: Escolhe próxima ação.
        """
        pass

    def reset(self):
        """Reseta estado interno (útil para testes)."""
        pass

    def _action_to_dict(self, action) -> Dict:
        """
        Helper method: Converte ScreenAction para dict executável.
        """
        return {
            "action_type": "CLICK",
            "x": action.bounds[0] if action.bounds else 0,
            "y": action.bounds[1] if action.bounds else 0,
            "description": action.text or action.content_desc or "element",
            "id": action.id
        }
```

---

## 5. Estrutura de Dados

### 5.1 AgentState (LangGraph) (ver [v3] seção 4.1)
```python
class AgentState(TypedDict):
    # Screen data
    current_screen_hash: str
    last_screen_hash: Optional[str]
    screen_description: str  # Com anotações [UNTESTED]
    current_activity: str

    # Action tracking
    current_action: Dict
    last_action: Optional[Dict]
    recent_action_window: List[Dict]  # Para detecção de loops

    # Loop detection
    loop_detected: bool
    used_fallback: bool

    # Execution mode
    execution_mode: str                    # "pure_dfs", "llm_only", "hybrid", "dynamic"
    router_decision: Optional[str]         # "llm" ou "dfs"
    router_reason: Optional[str]           # Motivo da decisão

    # Decision tracking
    decision_maker: str                    # "llm", "dfs", "dfs_fallback"
    last_decision_maker: Optional[str]

    # LLM failures (para fallback)
    consecutive_llm_failures: int          # Contador de falhas
    llm_timeout_occurred: bool

    # Exploration status
    exploration_complete: bool             # DFS sinalizou fim

    # Metrics
    llm_decisions: int                     # Quantas decisões da LLM
    dfs_decisions: int                     # Quantas decisões do DFS
    dfs_fallbacks: int                     # Quantas vezes DFS foi fallback
    
    # Dynamic selection
    selected_strategy: Optional[str]       # Estratégia selecionada dinamicamente
    selection_reason: Optional[str]        # Motivo da seleção

    # Iteration control
    iteration: int
    external_navigation_count: int
```

### 5.2 ScreenNode (DynamicStateGraph) (ver [v3] seção 4.2)
```python
@dataclass
class ScreenNode:
    screen_hash: str           # Identificador estrutural (12 chars)
    activity: str              # Nome da activity (contexto)
    visit_count: int           # Quantas vezes visitado
    total_actions: int         # Total de ações na tela
    executed_actions: Set[int] # IDs das ações executadas

    def get_coverage(self) -> float:
        return len(self.executed_actions) / self.total_actions
```

### 5.3 Transition (DynamicStateGraph) (ver [v3] seção 4.3)
```python
@dataclass
class Transition:
    from_hash: str                  # Estado origem
    to_hash: str                    # Estado destino
    action_sequence: List[Dict]     # TODAS as ações que levaram à transição
    timestamp: float                # Quando aconteceu
```

---

## 6. Implementação em Fases

### 6.1 Fase 1: v3 - Loop Detection (Prioridade ALTA)
1. **Modificar DynamicStateGraph** (trace)
   - Extender Transition para incluir action_sequence
   - Adicionar current_trace para rastrear ações entre transições
   - Adicionar get_transition_graph_report
2. **Adicionar strategy_validation_node** 
   - Implementar detecção de loops baseada em repetições consecutivas
   - Implementar fallback para ações untested
3. **Testar com modo híbrido básico**
   - Validar eliminação de loops (TYPE_TEXT 14x → bloqueado após 2)
4. **Validar eliminação de loops** (ver [v2] e [v3])

**Estimativa**: 8-10 horas

### 6.2 Fase 2: v4 - Multi-Mode Architecture (Prioridade MÉDIA)
1. **Estender DFSStrategy** (standalone capability)
   - Implementar select_next_action completo
   - Implementar backtracking automático
   - Implementar geração de texto para TYPE_TEXT
2. **Adicionar RVAgentConfig** (modos)
   - Novos campos: execution_mode, llm_timeout, etc.
   - Validar configuração
   - Implementar get_execution_mode com env override
3. **Implementar decision_router**
   - Implementar roteamento baseado em modo
   - Implementar fallback automático
4. **Adicionar pure_dfs e llm_only**
   - Implementar grafos específicos
   - Implementar nós específicos
5. **Testes e benchmarks**
   - Testar cada modo isoladamente
   - Comparar performance entre modos

**Estimativa**: 10-12 horas

### 6.3 Fase 3: Extensibilidade e Otimização (Prioridade MÉDIA)
1. **Implementar strategy factory pattern**
   - Criar BaseStrategy
   - Criar StrategyFactory
   - Registrar estratégias disponíveis
2. **Testes unitários extensivos**
   - Testar cada modo
   - Testar fallbacks
   - Testar detecção de loops
3. **Documentação e exemplos**
   - Documentar cada modo
   - Criar exemplos de uso

**Estimativa**: 6-8 horas

### 6.4 Fase 4: Dynamic Selection (Prioridade BAIXA)
1. **Implementar Strategy Selector Node**
   - Critérios de seleção automática
   - Cache de estratégias
2. **Testes de performance**
   - Comparar com estratégias fixas
   - Validar otimização
3. **Validação completa**
   - Testar com múltiplos apps
   - Comparar cobertura/velocidade

**Estimativa**: 8-10 horas

---

## 7. Arquivos a Backup e a Modificar

### 7.1 Arquivos a MODIFICAR (serão sobrescritos)
1. `modules/rv-agent/src/rv_agent/core/rv_agent.py` - Core logic
2. `modules/rv-agent/src/rv_agent/core/dynamic_state_graph.py` - Graph extension
3. `modules/rv-agent/src/rv_agent/llm/graph/state.py` - State extension
4. `modules/rv-agent/src/rv_agent/strategies/dfs_strategy.py` - DFS extension

### 7.2 Arquivos a CRIAR (novos)
1. `modules/rv-agent/src/rv_agent/config/agent_config.py` - Config extended
2. `modules/rv-agent/src/rv_agent/strategies/base_strategy.py` - Interface base
3. `modules/rv-agent/src/rv_agent/strategies/strategy_factory.py` - Strategy factory

### 7.3 Arquivos a MOVER para backup (serão movidos)
1. `modules/rv-agent/src/rv_agent/core/rv_agent.py` → `backup/rv_agent_old.py`
2. `modules/rv-agent/src/rv_agent/core/dynamic_state_graph.py` → `backup/dynamic_state_graph_old.py`
3. `modules/rv-agent/src/rv_agent/llm/graph/state.py` → `backup/state_old.py`
4. `modules/rv-agent/src/rv_agent/strategies/dfs_strategy.py` → `backup/dfs_strategy_old.py`

### 7.4 Arquivos a MANTER (não modificados)
1. Prompts versionados (continuam onde estão)
2. Scripts auxiliares (movidos para backup exceto prompts)

---

## 8. Métricas de Sucesso

### 8.1 Objetivo Primário: Eliminar Loops
- ✅ **Zero loops com >5 repetições consecutivas**
- ✅ **TYPE_TEXT bloqueado após 2 repetições consecutivas**
- ✅ **Fallback automático para ações untested**

### 8.2 Objetivo Secundário: Exploração Sistemática
- ✅ **>10 unique states em 120s** (baseline atual: 3)
- ✅ **>15 transitions em 120s** (baseline atual: 0)
- ✅ **Cobertura >30% por tela visitada**

### 8.3 Objetivo Terciário: Flexibilidade
- ✅ **Três modos funcionais**: pure_dfs, llm_only, hybrid
- ✅ **Modo DFS standalone**: zero tokens, rápida execução
- ✅ **Modo híbrido**: combinação eficaz LLM + DFS

### 8.4 Comparação com Baseline

| Métrica | Baseline V10 | Esperado Pós-Mudanças | Melhoria |
|---------|-------------|----------------------|----------|
| Unique States (120s) | 3 | 10-15 | 3-5x |
| Transitions (120s) | 0 | 15-25 | ∞ (de 0!) |
| Loops >5 reps | 1 (TYPE_TEXT 14x) | 0 | ✅ Eliminado |
| Revisit Rate | 70%+ | 30-40% | -50% |
| Coverage/Screen | ~20% | 40-60% | 2-3x |
| MOP Trigger Rate | 0% | 40-60% | ∞ |

---

## 9. Testes e Validação

### 9.1 Testes Unitários
```python
# Testes para cada componente
def test_dynamic_state_graph_extensions():
    """Testa extensões do DynamicStateGraph"""
    pass

def test_strategy_validation_node():
    """Testa detecção de loops e fallbacks"""
    pass

def test_decision_router():
    """Testa roteamento baseado em modo"""
    pass

def test_dfs_standalone():
    """Testa DFS puro sem LLM"""
    pass
```

### 9.2 Testes de Integração
```python
# Testes de modo
def test_pure_dfs_mode():
    """DFS puro, zero LLM calls"""
    config = RVAgentConfig(execution_mode="pure_dfs")
    agent = RVAgent(config)
    results = agent.run()
    assert results.get("llm_calls", 0) == 0
    assert results["unique_states"] > 0

def test_llm_only_mode():
    """Modo LLM como V10"""
    config = RVAgentConfig(execution_mode="llm_only")
    agent = RVAgent(config)
    results = agent.run()
    assert results.get("llm_calls", 0) > 0

def test_hybrid_mode():
    """Modo híbrido com fallback"""
    config = RVAgentConfig(execution_mode="hybrid")
    agent = RVAgent(config)
    results = agent.run()
    assert (results.get("llm_decisions", 0) > 0 or 
            results.get("dfs_decisions", 0) > 0)
```

### 9.3 Benchmark Comparativo
```python
# modules/rv-agent/benchmarks/mode_benchmark.py
def run_benchmark():
    """Executa benchmark dos 3 modos em múltiplos apps"""
    pass

def analyze_results(results: list):
    """Analisa e imprime comparação"""
    pass
```

---

## 10. Considerações Finais

### 10.1 Compatibilidade
- **Total backward compatibility**: Mesma interface de usuário
- **Configuração opcional**: Novos campos com defaults
- **Modo padrão**: "hybrid" como recomendado

### 10.2 Performance
- **Pure DFS**: ~0.1s/it (sem LLM)
- **LLM Only**: ~2.5s/it (atual)
- **Hybrid**: ~1.5s/it (com otimização)
- **Dynamic**: ~1.6s/it (mais inteligência)

### 10.3 Custos
- **Pure DFS**: $0 (tokens)
- **LLM Only**: ~$0.005/it
- **Hybrid**: ~$0.003/it (menos fallbacks)
- **Dynamic**: ~$0.002/it (otimizado)

### 10.4 Extensibilidade
- **Fácil adição de novas estratégias**: 3 passos simples
- **Factory pattern**: Novos algoritmos plugáveis
- **Interface base**: Padrão bem definido

---

**FIM DO PLANO EXECUTÁVEL**

**Total estimado**: ~32-40 horas de desenvolvimento
**Complexidade**: Média (mudanças aditivas, estruturadas em fases)
**Risco**: Baixo (módulos bem isolados, testes extensivos)
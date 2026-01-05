# RVAgent - Pré-Plano v4: Arquitetura Multi-Modo
**Data**: 2025-11-03
**Status**: Proposta de arquitetura avançada
**Versão anterior**: `20251103_rvagent_pre_plano_v3.md` (validação de loops)
**Foco**: DFS standalone, testabilidade, robustez

---

## 📋 Índice

1. [Visão Geral](#1-visão-geral)
2. [Modo PURE_DFS](#2-modo-pure_dfs-dfs-standalone)
3. [Modo LLM_ONLY](#3-modo-llm_only-v10-atual)
4. [Modo HYBRID](#4-modo-hybrid-proposta-v3)
5. [Grafo Compartilhado](#5-grafo-compartilhado-llm--dfs)
6. [Sistema de Configuração](#6-sistema-de-configuração)
7. [Implementação Técnica Detalhada](#7-implementação-técnica-detalhada)
8. [Testes e Validação](#8-testes-e-validação)
9. [Casos de Uso Práticos](#9-casos-de-uso-práticos)
10. [Comparação de Performance](#10-comparação-de-performance)
11. [Estimativas de Implementação](#11-estimativas-de-implementação)
12. [Integração com v3](#12-integração-com-v3)

---

## 1. Visão Geral

### 1.1 Motivação

A arquitetura multi-modo permite que o RVAgent opere em **três configurações distintas**, cada uma com propósitos específicos:

| Modo | Descrição | Caso de Uso |
|------|-----------|-------------|
| **PURE_DFS** | DFS sem LLM (como DroidBot) | Baseline, testes rápidos, LLM indisponível |
| **LLM_ONLY** | LLM puro (V10 atual) | Máxima criatividade, exploração semântica |
| **HYBRID** | LLM + DFS validation/fallback | Produção, robustez, melhor balanceamento |

### 1.2 Benefícios da Arquitetura

#### Testabilidade
- ✅ **DFS isolado**: Testa exploração algorítmica sem dependência de LLM
- ✅ **LLM isolado**: Valida criatividade e entendimento visual
- ✅ **Integração**: Testa colaboração entre componentes

#### Robustez
- ✅ **Fallback automático**: LLM falha → DFS continua
- ✅ **Timeout handling**: LLM lento → DFS assume
- ✅ **Sem ponto único de falha**: Sistema sempre funciona

#### Baseline Científico
- ✅ **Lower bound**: DFS garante cobertura mínima
- ✅ **Upper bound**: LLM demonstra potencial máximo
- ✅ **Comparação justa**: Métricas lado a lado

#### Custo/Performance
- ✅ **DFS**: Grátis, rápido (~0.1s/iteração)
- ✅ **LLM**: Custo tokens, lento (~2.5s/iteração)
- ✅ **Híbrido**: Otimiza trade-off

### 1.3 Arquitetura Visual Comparativa

```
┌────────────────────────────────────────────────────────────────────────┐
│                        ARQUITETURA MULTI-MODO                          │
└────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ MODO 1: PURE_DFS (Standalone)                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐     ┌─────────────────┐     ┌────────┐     ┌────────┐  │
│  │ OBSERVE  │────▶│   DFS_DECIDE    │────▶│ TOOLS  │────▶│ LEARN  │  │
│  │          │     │ (select_action) │     │        │     │        │  │
│  └──────────┘     └─────────────────┘     └────────┘     └────────┘  │
│       ▲                                                         │       │
│       └─────────────────────────────────────────────────────────┘       │
│                                                                         │
│  • Sem dependência de LLM                                              │
│  • Algoritmo DFS puro (deepen → backtrack)                             │
│  • Determinístico e reproduzível                                       │
│  • ~0.1s por iteração                                                  │
│  • Custo: ZERO                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ MODO 2: LLM_ONLY (V10 Atual)                                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐     ┌───────────┐     ┌────────┐     ┌────────┐        │
│  │ OBSERVE  │────▶│ ASSISTANT │────▶│ TOOLS  │────▶│ LEARN  │        │
│  │          │     │   (LLM)   │     │        │     │        │        │
│  └──────────┘     └───────────┘     └────────┘     └────────┘        │
│       ▲                                                  │              │
│       └──────────────────────────────────────────────────┘              │
│                                                                         │
│  • LLM decide tudo                                                     │
│  • Criativo e semântico                                                │
│  • Pode entrar em loops (problema v3 resolve)                          │
│  • ~2.5s por iteração                                                  │
│  • Custo: tokens LLM                                                   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ MODO 3: HYBRID (Proposta v3 + v4)                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐   ┌────────────┐   ┌──────────────┐   ┌────────┐       │
│  │ OBSERVE  │──▶│ DECISION   │──▶│  ASSISTANT   │──▶│STRATEGY│──▶    │
│  │          │   │  ROUTER    │   │    (LLM)     │   │VALIDTN │       │
│  └──────────┘   └────────────┘   └──────────────┘   └────────┘       │
│       ▲               │                                   │             │
│       │               │ (se timeout/falha)                ▼             │
│       │               ▼                            ┌─────────────┐     │
│       │        ┌─────────────┐                    │   TOOLS     │     │
│       │        │ DFS_DECIDE  │───────────────────▶│             │     │
│       │        │ (fallback)  │                    └─────────────┘     │
│       │        └─────────────┘                            │            │
│       │               ▲                                   ▼            │
│       │               │                            ┌────────┐          │
│       │               │ (se loop detectado)        │ LEARN  │          │
│       │               └────────────────────────────│        │          │
│       └────────────────────────────────────────────└────────┘          │
│                                                                         │
│  • LLM tenta primeiro (criatividade)                                   │
│  • DFS valida (previne loops)                                          │
│  • DFS fallback (timeout/falha)                                        │
│  • Melhor dos dois mundos                                              │
│  • ~2s por iteração (otimizado)                                        │
│  • Custo: tokens quando LLM usado                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Modo PURE_DFS (DFS Standalone)

### 2.1 Objetivo

Implementar **DFS completo sem dependência de LLM**, funcionando exatamente como DroidBot mas usando a infraestrutura do RVAgent.

### 2.2 Algoritmo DFS Clássico

```
DFS (Depth-First Search):
1. Começa no estado inicial
2. Explora ações untested no estado atual (DEEPEN)
3. Quando esgota estado → volta para estado anterior (BACKTRACK)
4. Continua até pilha vazia (exploração completa)

Exemplo:
         [State A]
        /    |    \
     [B]   [C]   [D]
     / \         / \
   [E] [F]     [G] [H]

Ordem DFS: A → B → E → (back) → F → (back to A) → C → (back to A) → D → G → (back) → H
```

### 2.3 Implementação Detalhada

#### Estrutura de Dados DFS

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

        Args:
            screen_hash: Hash estrutural do estado atual
            screen_desc: Descrição parsed da tela (ScreenDescription)

        Returns:
            Dict com ação a executar, ou None se exploração completa
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

        Determina tipo de ação baseado nas capacidades do elemento.

        Args:
            action: ScreenAction object

        Returns:
            Dict com campos: action_type, x, y, description, id, etc.
        """

        # Determina tipo baseado em flags
        if action.editable:
            # Campo de texto - TYPE_TEXT
            action_type = "TYPE_TEXT"
        elif action.scrollable:
            # Lista/scroll - SCROLL
            action_type = "SCROLL"
        elif action.long_clickable:
            # Long click
            action_type = "LONG_CLICK"
        elif action.clickable:
            # Clicável genérico - CLICK
            action_type = "CLICK"
        else:
            # Fallback: tenta click
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

        Usa heurísticas baseadas em:
        - resource-id
        - text
        - content-desc

        Args:
            action: ScreenAction do campo editável

        Returns:
            String de texto para inserir
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

        Usa análise estática se disponível.

        Returns:
            3: Directly reaches MOP [DM]
            2: Reaches MOP [M]
            1: No marker
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

### 2.4 Exemplo de Execução DFS Puro

```python
# Exemplo: CryptoApp com DFS Puro

# Estado inicial
State A (MainActivity):
  Actions: [1: MESSAGE_DIGEST [M], 2: CIPHER [M], 3: SIGNATURE [M]]
  Stack: [A]

DFS escolhe: ACTION 1 (MESSAGE_DIGEST) - maior prioridade MOP
Executa CLICK → Transição para State B

---

State B (MessageDigestActivity):
  Actions: [4: Spinner, 5: EditText, 6: GENERATE [M]]
  Stack: [A, B]

DFS escolhe: ACTION 6 (GENERATE) - maior prioridade MOP
Mas campo vazio! Tenta executar → falha ou nada acontece
Marca como executado: executed_actions = {6}

Próxima iteração, mesma tela:
  Untested: [4, 5]

DFS escolhe: ACTION 4 (Spinner) - nenhum MOP marker, escolhe primeiro
Executa CLICK(spinner) → Dropdown abre

---

State C (Dropdown aberto):
  Actions: [7: SHA-256, 8: MD5, 9: SHA-512, ...]
  Stack: [A, B, C]

DFS escolhe: ACTION 7 (SHA-256)
Executa CLICK → Seleciona algoritmo → volta para State B

---

State B (revisitado):
  executed_actions = {6, 4}
  Untested: [5]

DFS escolhe: ACTION 5 (EditText)
Executa TYPE_TEXT("DFS test message") → campo preenchido

---

Próxima iteração:
  executed_actions = {6, 4, 5}
  Untested: [6] (GENERATE estava marcado mas pode tentar de novo)

DFS escolhe: ACTION 6 (GENERATE)
Executa CLICK → Hash gerado! Transição para State D

---

State D (Resultado):
  Actions: [10: Copy, 11: Share, 12: BACK]
  Stack: [A, B, C, D]

DFS escolhe: ACTION 10 (Copy)
... continua explorando ...

Quando esgota State D:
  executed_actions = {10, 11, 12}
  Untested: []

DFS: BACKTRACK
Executa BACK → volta para State C

State C esgotado também:
DFS: BACKTRACK
Executa BACK → volta para State B

... continua até explorar tudo
```

### 2.5 Vantagens do DFS Puro

| Aspecto | Vantagem |
|---------|----------|
| **Velocidade** | ~0.1s/iteração (sem latência de LLM) |
| **Custo** | ZERO (sem tokens) |
| **Determinismo** | Sempre mesma ordem (reproduzível) |
| **Simplicidade** | Algoritmo clássico, fácil debug |
| **Baseline** | Cobertura mínima garantida |
| **Robustez** | Não depende de serviços externos |

### 2.6 Limitações do DFS Puro

| Aspecto | Limitação |
|---------|-----------|
| **Semântica** | Não entende contexto (preenche "DFS test" em tudo) |
| **Criatividade** | Não tenta interações não-óbvias |
| **Visão** | Usa apenas XML, não vê imagens |
| **Formulários** | Pode preencher incorretamente |
| **Workflows** | Pode não completar fluxos complexos |

---

## 3. Modo LLM_ONLY (V10 Atual)

### 3.1 Arquitetura

```python
# Fluxo atual (V10)

def _build_agent_graph_llm_only(self):
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

### 3.2 Características

| Aspecto | Descrição |
|---------|-----------|
| **Decisão** | 100% LLM |
| **Velocidade** | ~2.5s/iteração |
| **Custo** | Tokens LLM (~4600 tokens/iteração) |
| **Criatividade** | Alta (entende contexto semântico) |
| **Problemas** | Loops (v3 resolve), não-determinístico |

### 3.3 Casos de Uso

- Apps com UI complexa não-estruturada
- WebViews, custom views
- Quando criatividade é crítica
- Pesquisa: limite superior de performance

---

## 4. Modo HYBRID (Proposta v3 + v4)

### 4.1 Arquitetura Completa

```python
# modules/rv-agent/src/rv_agent/core/rv_agent.py

def _build_agent_graph_hybrid(self):
    """
    Constrói grafo LangGraph com suporte a modo híbrido.

    Fluxo:
    1. observe: Captura estado
    2. decision_router: Decide LLM ou DFS
    3a. assistant (LLM) → strategy_validation → tools
    3b. dfs_decide (DFS) → tools
    4. tools: Executa ação
    5. learn: Atualiza grafo
    """

    graph = StateGraph(AgentState)

    # ===== NODES =====
    graph.add_node("observe", self._observe_node)
    graph.add_node("decision_router", self._decision_router_node)

    # Caminho LLM
    graph.add_node("assistant", self._assistant_node)
    graph.add_node("strategy_validation", self._strategy_validation_node)

    # Caminho DFS
    graph.add_node("dfs_decide", self._dfs_decide_node)

    # Compartilhado
    graph.add_node("tools", ToolNode(self.tools))
    graph.add_node("learn", self._learn_node)

    # ===== EDGES =====
    graph.set_entry_point("observe")
    graph.add_edge("observe", "decision_router")

    # Router decide caminho
    graph.add_conditional_edges(
        "decision_router",
        self._route_decision,
        {
            "llm": "assistant",      # Tenta LLM
            "dfs": "dfs_decide",     # Usa DFS direto
            "end": END               # Exploração completa
        }
    )

    # Caminho LLM: assistant → validation → tools
    graph.add_edge("assistant", "strategy_validation")
    graph.add_edge("strategy_validation", "tools")

    # Caminho DFS: dfs_decide → tools
    graph.add_edge("dfs_decide", "tools")

    # Convergência: tools → learn
    graph.add_edge("tools", "learn")

    # Loop ou fim
    graph.add_conditional_edges(
        "learn",
        self._should_continue,
        {
            "continue": "observe",
            "end": END
        }
    )

    return graph.compile()
```

### 4.2 Nó: Decision Router

```python
def _decision_router_node(self, state: AgentState) -> AgentState:
    """
    Roteador que decide qual caminho seguir.

    Lógica:
    1. Se modo = pure_dfs → sempre DFS
    2. Se modo = llm_only → sempre LLM
    3. Se modo = hybrid:
       - Se LLM timeout/falha anterior → DFS
       - Se loop detectado anterior → DFS
       - Senão → LLM
    """

    mode = self.config.get_execution_mode()

    # Determina decisão
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
        # Fallback
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

    Returns:
        "llm", "dfs", ou "end"
    """

    decision = state.get("router_decision", "llm")

    # Verifica se exploração completa
    if state.get("exploration_complete", False):
        return "end"

    return decision
```

### 4.3 Nó: DFS Decide

```python
def _dfs_decide_node(self, state: AgentState) -> AgentState:
    """
    Nó que usa DFS para decidir ação (sem LLM).

    Este nó é ativado quando:
    1. Modo = pure_dfs
    2. Modo = hybrid + LLM falhou
    3. Modo = hybrid + loop detectado
    """

    screen_hash = state["current_screen_hash"]
    screen_desc = state["screen_description_obj"]  # ScreenDescription object

    logger.info(f"🤖 DFS deciding next action for state {screen_hash[:8]}")

    # DFS escolhe próxima ação
    action = self.strategy.select_next_action(screen_hash, screen_desc)

    if action is None:
        # Exploração completa!
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
```

### 4.4 Nó: Strategy Validation (v3)

```python
def _strategy_validation_node(self, state: AgentState) -> AgentState:
    """
    Valida ação da LLM e usa DFS como fallback se necessário.

    Este nó só é usado no modo HYBRID quando LLM decide.
    """

    llm_action = state['current_action']
    recent_window = state.get('recent_action_window', [])
    screen_hash = state['current_screen_hash']

    # Conta repetições consecutivas
    consecutive_count = self._count_consecutive_actions(recent_window, llm_action)

    # Thresholds
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

    # Valida
    if consecutive_count >= threshold:
        logger.warning(f"⚠️ LOOP: {action_type} repeated {consecutive_count}x")

        # Pega ação do DFS
        screen_desc = state["screen_description_obj"]
        fallback = self.strategy.select_next_action(screen_hash, screen_desc)

        if fallback and fallback.get("action_type") != "BACK":
            logger.info(f"   Using DFS fallback: {fallback['action_type']}")
            return {
                "current_action": fallback,
                "loop_detected": True,
                "used_fallback": True,
                "decision_maker": "dfs_fallback"
            }
        else:
            # Sem ações untested, usa BACK
            logger.info("   No untested actions, executing BACK")
            return {
                "current_action": {"action_type": "BACK"},
                "loop_detected": True,
                "used_fallback": True,
                "decision_maker": "dfs_fallback"
            }

    # Ação válida
    return {
        "current_action": llm_action,
        "loop_detected": False,
        "used_fallback": False,
        "decision_maker": "llm"
    }
```

### 4.5 Exemplo: Colaboração LLM + DFS

```
╔════════════════════════════════════════════════════════════════╗
║               EXEMPLO: MODO HYBRID EM AÇÃO                     ║
╚════════════════════════════════════════════════════════════════╝

Iteração 1:
┌─ OBSERVE ──────────────────────────────────────────────┐
│ State: Login screen                                    │
│ Elements: [Email, Password, Submit]                    │
└────────────────────────────────────────────────────────┘
         ▼
┌─ DECISION_ROUTER ──────────────────────────────────────┐
│ Mode: hybrid                                           │
│ LLM failures: 0                                        │
│ Decision: LLM (normal path)                            │
└────────────────────────────────────────────────────────┘
         ▼
┌─ ASSISTANT (LLM) ──────────────────────────────────────┐
│ LLM vê tela de login                                   │
│ Entende: "precisa preencher email e senha"            │
│ Decide: TYPE_TEXT(email, "user@example.com")          │
└────────────────────────────────────────────────────────┘
         ▼
┌─ STRATEGY_VALIDATION ──────────────────────────────────┐
│ recent_window: []                                      │
│ consecutive: 0                                         │
│ Result: VALID ✅                                        │
└────────────────────────────────────────────────────────┘
         ▼
┌─ TOOLS ────────────────────────────────────────────────┐
│ Executes: TYPE_TEXT("user@example.com")               │
└────────────────────────────────────────────────────────┘
         ▼
┌─ LEARN ────────────────────────────────────────────────┐
│ Updates graph: executed_actions = {email_id}          │
│ Decision maker: llm ✅                                  │
└────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────

Iteração 2:
┌─ ASSISTANT (LLM) ──────────────────────────────────────┐
│ Decide: TYPE_TEXT(password, "MyPass123")              │
└────────────────────────────────────────────────────────┘
         ▼
┌─ STRATEGY_VALIDATION ──────────────────────────────────┐
│ consecutive: 0 (ação diferente)                        │
│ Result: VALID ✅                                        │
└────────────────────────────────────────────────────────┘

Decision maker: llm ✅

─────────────────────────────────────────────────────────

Iteração 3:
┌─ ASSISTANT (LLM) ──────────────────────────────────────┐
│ BUG: Decide TYPE_TEXT(password, "MyPass123") DE NOVO! │
└────────────────────────────────────────────────────────┘
         ▼
┌─ STRATEGY_VALIDATION ──────────────────────────────────┐
│ recent_window: [TYPE_TEXT(email), TYPE_TEXT(pass)]    │
│ consecutive: 1 (mesmo campo, mesmo texto)             │
│ threshold: 2                                           │
│ Result: VALID (ainda) ⚠️                               │
└────────────────────────────────────────────────────────┘

Decision maker: llm ⚠️

─────────────────────────────────────────────────────────

Iteração 4:
┌─ ASSISTANT (LLM) ──────────────────────────────────────┐
│ BUG CONTINUA: TYPE_TEXT(password, "MyPass123")        │
└────────────────────────────────────────────────────────┘
         ▼
┌─ STRATEGY_VALIDATION ──────────────────────────────────┐
│ recent_window: [TYPE(email), TYPE(pass), TYPE(pass)]  │
│ consecutive: 2 (LOOP!)                                │
│ threshold: 2                                           │
│ Result: LOOP DETECTED ❌                                │
│                                                        │
│ ┌─ DFS FALLBACK ─────────────────────────────┐        │
│ │ Consulta grafo:                            │        │
│ │   executed: {email_id, password_id}        │        │
│ │   untested: [submit_button_id]             │        │
│ │                                            │        │
│ │ DFS escolhe: CLICK(submit_button)          │        │
│ └────────────────────────────────────────────┘        │
│                                                        │
│ Substitui ação: TYPE_TEXT → CLICK                     │
└────────────────────────────────────────────────────────┘
         ▼
┌─ TOOLS ────────────────────────────────────────────────┐
│ Executes: CLICK(submit_button) ✅                      │
│ Login successful! → New screen                         │
└────────────────────────────────────────────────────────┘
         ▼
┌─ LEARN ────────────────────────────────────────────────┐
│ executed_actions = {email, password, submit} ✅        │
│ Decision maker: dfs_fallback 🤖                        │
│ Loop quebrado!                                         │
└────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────

Iteração 5 (nova tela):
┌─ DECISION_ROUTER ──────────────────────────────────────┐
│ loop_detected_last: True                               │
│ Decision: DFS (preventivo)                             │
└────────────────────────────────────────────────────────┘
         ▼
┌─ DFS_DECIDE ───────────────────────────────────────────┐
│ Explora nova tela de forma sistemática                │
│ Escolhe primeira ação untested                         │
└────────────────────────────────────────────────────────┘

Decision maker: dfs 🤖

─────────────────────────────────────────────────────────

Iteração 6:
┌─ DECISION_ROUTER ──────────────────────────────────────┐
│ loop_detected_last: False (reset)                     │
│ LLM failures: 0                                        │
│ Decision: LLM (volta ao normal)                        │
└────────────────────────────────────────────────────────┘

LLM volta a decidir ✅
```

---

## 5. Grafo Compartilhado: LLM + DFS

### 5.1 Princípio Fundamental

**UM ÚNICO GRAFO** (`DynamicStateGraph`) é compartilhado entre todos os modos:
- LLM atualiza o grafo quando executa ações
- DFS consulta o grafo para escolher ações
- Ambos colaboram de forma transparente

### 5.2 Ponto Único de Atualização

```python
def _learn_node(self, state: AgentState) -> AgentState:
    """
    ÚNICO ponto de atualização do grafo.

    NÃO importa quem decidiu a ação (LLM ou DFS):
    - Ambos passam por aqui
    - Ambos atualizam o mesmo grafo
    - Estado consistente sempre
    """

    action = state["current_action"]
    screen_hash = state["current_screen_hash"]
    decision_maker = state.get("decision_maker", "unknown")

    logger.debug(f"📝 LEARN: Recording action decided by {decision_maker}")

    # 1. Adiciona ao trace (para relatório final)
    self.dynamic_graph.record_action_to_trace(action)

    # 2. Marca ação como executada
    action_id = action.get("id", hash(str(action)))
    self.dynamic_graph.record_action(screen_hash, action_id)

    # 3. Atualiza UI coverage
    if element_id := self._extract_element_id(action):
        self.ui_coverage.record_interaction(
            element_id=element_id,
            action_type=action["action_type"],
            screen_hash=screen_hash,
            success=True
        )

    # 4. Atualiza window de ações recentes
    recent = state.get("recent_action_window", [])
    recent.append(action)
    if len(recent) > 10:
        recent = recent[-10:]

    return {
        "recent_action_window": recent,
        "iteration": state["iteration"] + 1,
        "last_action": action,
        "last_decision_maker": decision_maker
    }
```

### 5.3 Exemplo: Colaboração Incremental

```python
# Cenário: App com 10 ações em uma tela

# Iterações 1-5: LLM explora
# ────────────────────────────────────────────────
It 1: LLM → CLICK(action_1)   | graph.executed = {1}
It 2: LLM → TYPE(action_2)    | graph.executed = {1, 2}
It 3: LLM → CLICK(action_3)   | graph.executed = {1, 2, 3}
It 4: LLM → CLICK(action_4)   | graph.executed = {1, 2, 3, 4}
It 5: LLM → CLICK(action_4)   | LOOP! → DFS fallback

# Iteração 6: DFS assume
# ────────────────────────────────────────────────
It 6: DFS consulta graph.executed = {1, 2, 3, 4}
      DFS vê untested = {5, 6, 7, 8, 9, 10}
      DFS escolhe action_5
      graph.executed = {1, 2, 3, 4, 5}

# Iterações 7-10: DFS continua
# ────────────────────────────────────────────────
It 7: DFS → CLICK(action_6)   | graph.executed = {1,2,3,4,5,6}
It 8: DFS → CLICK(action_7)   | graph.executed = {1,2,3,4,5,6,7}
It 9: DFS → CLICK(action_8)   | graph.executed = {1,2,3,4,5,6,7,8}
It 10: DFS → CLICK(action_9)  | graph.executed = {1,2,3,4,5,6,7,8,9}

# Iteração 11: Tela esgotada
# ────────────────────────────────────────────────
DFS vê untested = {10}
DFS escolhe action_10
graph.executed = {1,2,3,4,5,6,7,8,9,10}

# Próxima iteração: Tela completa
DFS vê untested = {}
DFS executa BACK (backtracking)

# ────────────────────────────────────────────────
# RESULTADO FINAL:
# - LLM explorou 4 ações (40%)
# - DFS completou 6 ações (60%)
# - Cobertura total: 100% ✅
# - Sem loops!
# - Colaboração perfeita!
```

### 5.4 Vantagens do Grafo Compartilhado

| Vantagem | Descrição |
|----------|-----------|
| **Consistência** | Estado único, sem duplicação |
| **Complementariedade** | LLM faz parte difícil, DFS completa |
| **Eficiência** | Não refaz trabalho já feito |
| **Transparência** | Cada componente vê trabalho do outro |
| **Simplicidade** | Um único ponto de atualização |

---

## 6. Sistema de Configuração

### 6.1 RVAgentConfig Estendido

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
    execution_mode: str = "hybrid"  # "pure_dfs", "llm_only", "hybrid"

    # Timeouts e retries (para hybrid/llm_only)
    llm_timeout: float = 30.0           # Timeout por chamada LLM (segundos)
    llm_max_retries: int = 2            # Tentativas antes de fallback DFS

    # Fallback automático
    auto_fallback_on_timeout: bool = True   # Se timeout → DFS
    auto_fallback_on_error: bool = True     # Se erro → DFS

    # Coordenadas
    device_dimensions: tuple = (1080, 1920)
    optimized_dimensions: tuple = (720, 1280)

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

        Raises:
            ValueError: Se configuração inválida
        """
        valid_modes = ["pure_dfs", "llm_only", "hybrid"]
        mode = self.get_execution_mode()

        if mode not in valid_modes:
            raise ValueError(
                f"Invalid execution_mode: {mode}. "
                f"Must be one of {valid_modes}"
            )

        # Se modo usa LLM, valida configurações LLM
        if mode in ["llm_only", "hybrid"]:
            if not self.llm_model:
                raise ValueError("llm_model required for llm_only/hybrid modes")

        # Valida strategy
        if self.strategy not in ["dfs", "bfs"]:
            raise ValueError(f"Invalid strategy: {self.strategy}")

    def get_mode_description(self) -> str:
        """Retorna descrição legível do modo."""
        mode = self.get_execution_mode()

        descriptions = {
            "pure_dfs": "DFS standalone (no LLM required)",
            "llm_only": "LLM only (current V10)",
            "hybrid": "LLM + DFS validation/fallback (recommended)"
        }

        return descriptions.get(mode, mode)
```

### 6.2 Uso em Testes

```python
# test_mode_comparison.py

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.rv_agent import RVAgent


def test_pure_dfs_mode():
    """Testa modo DFS puro sem LLM."""

    config = RVAgentConfig(
        package_name="com.example.app",
        device_id="emulator-5554",
        execution_mode="pure_dfs",  # Sem LLM!
        strategy="dfs",
        timeout=120
    )

    config.validate()

    agent = RVAgent(config)
    results = agent.run()

    # Validações
    assert results.get("llm_calls", 0) == 0, "DFS puro não deve chamar LLM"
    assert results["unique_states"] > 0, "Deve descobrir estados"

    print(f"Pure DFS Results:")
    print(f"  States: {results['unique_states']}")
    print(f"  Transitions: {results['total_transitions']}")
    print(f"  Time: {results['execution_time_s']}s")


def test_llm_only_mode():
    """Testa modo LLM apenas."""

    config = RVAgentConfig(
        package_name="com.example.app",
        execution_mode="llm_only",
        llm_model="qwen3-vl:4b",
        timeout=120
    )

    agent = RVAgent(config)
    results = agent.run()

    assert results.get("llm_calls", 0) > 0, "LLM deve ser chamado"


def test_hybrid_mode():
    """Testa modo híbrido com fallback."""

    config = RVAgentConfig(
        package_name="com.example.app",
        execution_mode="hybrid",
        llm_model="qwen3-vl:4b",
        strategy="dfs",
        llm_timeout=30.0,
        auto_fallback_on_timeout=True,
        timeout=120
    )

    agent = RVAgent(config)
    results = agent.run()

    # Valida que ambos foram usados
    assert results.get("llm_decisions", 0) > 0, "LLM deve ser usado"
    assert results.get("dfs_fallbacks", 0) >= 0, "DFS pode ser usado como fallback"
```

### 6.3 Override via Variável de Ambiente

```bash
# Teste 1: DFS puro (sem tocar código)
$ RVAGENT_MODE=pure_dfs poetry run python test_app.py

# Teste 2: LLM apenas
$ RVAGENT_MODE=llm_only poetry run python test_app.py

# Teste 3: Híbrido (padrão)
$ poetry run python test_app.py

# Teste 4: Comparação automatizada
$ for mode in pure_dfs llm_only hybrid; do
    echo "Testing mode: $mode"
    RVAGENT_MODE=$mode poetry run python test_app.py
  done
```

### 6.4 Detecção Automática de LLM Indisponível

```python
# modules/rv-agent/src/rv_agent/core/rv_agent.py

def __init__(self, config: RVAgentConfig, ...):
    """Inicializa RVAgent com detecção de LLM."""

    self.config = config
    config.validate()

    mode = config.get_execution_mode()

    # Se modo requer LLM, testa disponibilidade
    if mode in ["llm_only", "hybrid"]:
        if not self._is_llm_available():
            logger.warning("⚠️  LLM not available!")

            if mode == "llm_only":
                logger.error("llm_only mode requires LLM, falling back to pure_dfs")
                # Override mode
                self.config.execution_mode = "pure_dfs"
            elif mode == "hybrid":
                logger.warning("hybrid mode: will use DFS fallback more aggressively")
                # Reduz retries para failar mais rápido
                self.config.llm_max_retries = 0

    # Continua inicialização...

def _is_llm_available(self) -> bool:
    """
    Testa se LLM está disponível.

    Returns:
        True se conseguiu conectar ao Ollama
    """
    try:
        # Tenta ping rápido
        llm_test = ChatOllama(
            model=self.config.llm_model,
            timeout=5.0
        )

        # Tenta chamada simples
        llm_test.invoke([HumanMessage(content="test")])

        return True

    except Exception as e:
        logger.warning(f"LLM availability test failed: {e}")
        return False
```

---

## 7. Implementação Técnica Detalhada

### 7.1 Modificações em AgentState

```python
# modules/rv-agent/src/rv_agent/llm/graph/state.py

from typing import TypedDict, List, Dict, Optional


class AgentState(TypedDict):
    """Estado do agente LangGraph (estendido para v4)."""

    # ===== CAMPOS EXISTENTES =====

    # Screen data
    current_screen_hash: str
    last_screen_hash: Optional[str]
    screen_description: str
    screen_description_obj: Optional[Any]  # ScreenDescription object
    current_activity: str

    # Action tracking
    current_action: Dict
    last_action: Optional[Dict]
    recent_action_window: List[Dict]

    # Iteration control
    iteration: int
    external_navigation_count: int

    # ===== NOVOS CAMPOS (v3) =====

    # Loop detection
    loop_detected: bool
    used_fallback: bool

    # ===== NOVOS CAMPOS (v4) =====

    # Execution mode
    execution_mode: str                    # "pure_dfs", "llm_only", "hybrid"
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
```

### 7.2 Modificações Completas em RVAgent

```python
# modules/rv-agent/src/rv_agent/core/rv_agent.py

class RVAgent:
    """RVAgent com suporte multi-modo (v4)."""

    def __init__(self, config: RVAgentConfig, ...):
        """Inicializa com modo configurado."""

        self.config = config
        config.validate()

        mode = config.get_execution_mode()
        logger.info(f"Initializing RVAgent in {mode} mode")
        logger.info(f"  Description: {config.get_mode_description()}")

        # ... inicialização existente ...

        # Estratégia (agora com modo)
        if config.strategy == "dfs":
            self.strategy = DFSStrategy(
                self.dynamic_graph,
                static_data,
                mode=mode  # NOVO: passa modo para estratégia
            )

        # LLM (opcional para pure_dfs)
        if mode in ["llm_only", "hybrid"]:
            self._initialize_llm()
        else:
            self.llm = None
            logger.info("LLM not initialized (pure_dfs mode)")

    def _build_agent_graph(self):
        """Constrói grafo baseado no modo."""

        mode = self.config.get_execution_mode()

        if mode == "pure_dfs":
            return self._build_graph_pure_dfs()
        elif mode == "llm_only":
            return self._build_graph_llm_only()
        elif mode == "hybrid":
            return self._build_graph_hybrid()
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def _build_graph_pure_dfs(self):
        """Grafo para modo DFS puro."""

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

    def _build_graph_llm_only(self):
        """Grafo para modo LLM apenas (V10 atual)."""

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

    def _build_graph_hybrid(self):
        """Grafo para modo híbrido (v3 + v4)."""

        graph = StateGraph(AgentState)

        # Nodes
        graph.add_node("observe", self._observe_node)
        graph.add_node("decision_router", self._decision_router_node)
        graph.add_node("assistant", self._assistant_node)
        graph.add_node("strategy_validation", self._strategy_validation_node)
        graph.add_node("dfs_decide", self._dfs_decide_node)
        graph.add_node("tools", ToolNode(self.tools))
        graph.add_node("learn", self._learn_node)

        # Edges
        graph.set_entry_point("observe")
        graph.add_edge("observe", "decision_router")

        # Router condicional
        graph.add_conditional_edges(
            "decision_router",
            self._route_decision,
            {
                "llm": "assistant",
                "dfs": "dfs_decide",
                "end": END
            }
        )

        # Caminho LLM
        graph.add_edge("assistant", "strategy_validation")
        graph.add_edge("strategy_validation", "tools")

        # Caminho DFS
        graph.add_edge("dfs_decide", "tools")

        # Convergência
        graph.add_edge("tools", "learn")
        graph.add_conditional_edges(
            "learn",
            self._should_continue,
            {"continue": "observe", "end": END}
        )

        return graph.compile()

    # ===== NOVOS MÉTODOS (v4) =====

    def _decision_router_node(self, state: AgentState) -> AgentState:
        """[Implementado na seção 4.2]"""
        # ... código já mostrado ...

    def _route_decision(self, state: AgentState) -> str:
        """[Implementado na seção 4.2]"""
        # ... código já mostrado ...

    def _dfs_decide_node(self, state: AgentState) -> AgentState:
        """[Implementado na seção 4.3]"""
        # ... código já mostrado ...

    def _strategy_validation_node(self, state: AgentState) -> AgentState:
        """[Implementado na seção 4.4]"""
        # ... código já mostrado ...

    def _count_consecutive_actions(self, recent: List[Dict], current: Dict) -> int:
        """Conta repetições consecutivas."""
        count = 0
        for action in reversed(recent):
            if self._actions_are_similar(action, current):
                count += 1
            else:
                break
        return count

    def _actions_are_similar(self, a1: Dict, a2: Dict) -> bool:
        """Compara se duas ações são similares."""
        if a1.get("action_type") != a2.get("action_type"):
            return False

        if a1.get("action_type") == "TYPE_TEXT":
            return a1.get("text") == a2.get("text")

        if a1.get("action_type") == "CLICK":
            x1, y1 = a1.get("x", 0), a1.get("y", 0)
            x2, y2 = a2.get("x", 0), a2.get("y", 0)
            return abs(x1 - x2) < 20 and abs(y1 - y2) < 20

        return True

    def run(self) -> Dict:
        """
        Executa exploração (estendido com métricas de modo).
        """

        # ... execução existente ...

        # Adiciona métricas de modo
        results["execution_mode"] = self.config.get_execution_mode()
        results["llm_decisions"] = state.get("llm_decisions", 0)
        results["dfs_decisions"] = state.get("dfs_decisions", 0)
        results["dfs_fallbacks"] = state.get("dfs_fallbacks", 0)

        if results["execution_mode"] == "hybrid":
            total_decisions = results["llm_decisions"] + results["dfs_decisions"]
            if total_decisions > 0:
                llm_percentage = (results["llm_decisions"] / total_decisions) * 100
                results["llm_usage_percentage"] = llm_percentage

        return results
```

---

## 8. Testes e Validação

### 8.1 Suite de Testes Completa

```python
# modules/rv-agent/tests/test_multi_mode.py

import pytest
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.rv_agent import RVAgent


class TestPureDFSMode:
    """Testes para modo DFS puro."""

    @pytest.fixture
    def dfs_config(self):
        return RVAgentConfig(
            package_name="com.example.testapp",
            device_id="emulator-5554",
            execution_mode="pure_dfs",
            strategy="dfs",
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
        assert results["total_transitions"] >= 0

    def test_systematic_exploration(self, dfs_config):
        """DFS deve explorar sistematicamente."""
        agent = RVAgent(dfs_config)
        results = agent.run()

        # Verifica que exploração foi completa
        assert results.get("exploration_complete", False)

    def test_deterministic(self, dfs_config):
        """DFS deve ser determinístico (mesma ordem)."""

        # Executa 2 vezes
        agent1 = RVAgent(dfs_config)
        results1 = agent1.run()

        agent2 = RVAgent(dfs_config)
        results2 = agent2.run()

        # Deve produzir mesmos resultados
        assert results1["unique_states"] == results2["unique_states"]
        assert results1["total_transitions"] == results2["total_transitions"]


class TestLLMOnlyMode:
    """Testes para modo LLM apenas."""

    @pytest.fixture
    def llm_config(self):
        return RVAgentConfig(
            package_name="com.example.testapp",
            execution_mode="llm_only",
            llm_model="qwen3-vl:4b",
            timeout=60
        )

    def test_llm_called(self, llm_config):
        """LLM deve ser chamado."""
        agent = RVAgent(llm_config)
        results = agent.run()

        assert results.get("llm_calls", 0) > 0
        assert results.get("llm_decisions", 0) > 0

    def test_no_dfs_decisions(self, llm_config):
        """DFS não deve tomar decisões em modo LLM_ONLY."""
        agent = RVAgent(llm_config)
        results = agent.run()

        assert results.get("dfs_decisions", 0) == 0


class TestHybridMode:
    """Testes para modo híbrido."""

    @pytest.fixture
    def hybrid_config(self):
        return RVAgentConfig(
            package_name="com.example.testapp",
            execution_mode="hybrid",
            llm_model="qwen3-vl:4b",
            strategy="dfs",
            timeout=60
        )

    def test_both_components_used(self, hybrid_config):
        """Híbrido deve usar LLM e DFS."""
        agent = RVAgent(hybrid_config)
        results = agent.run()

        # Pelo menos um deve ser usado
        assert (results.get("llm_decisions", 0) > 0 or
                results.get("dfs_decisions", 0) > 0)

    def test_fallback_on_loop(self, hybrid_config):
        """DFS deve ser usado como fallback em loops."""
        agent = RVAgent(hybrid_config)
        results = agent.run()

        # Se houve loops, deve ter fallbacks
        if results.get("loops_detected", 0) > 0:
            assert results.get("dfs_fallbacks", 0) > 0

    def test_collaboration(self, hybrid_config):
        """LLM e DFS devem colaborar."""
        agent = RVAgent(hybrid_config)
        results = agent.run()

        # Verifica que ambos contribuíram
        llm_decisions = results.get("llm_decisions", 0)
        dfs_decisions = results.get("dfs_decisions", 0)
        total = llm_decisions + dfs_decisions

        if total > 10:  # Se teste longo suficiente
            # Ambos devem ter contribuído
            assert llm_decisions > 0
            assert dfs_decisions > 0


class TestModeComparison:
    """Testes comparativos entre modos."""

    def test_all_modes_same_app(self):
        """Compara os 3 modos no mesmo app."""

        app_package = "com.example.testapp"
        modes = ["pure_dfs", "llm_only", "hybrid"]
        results = {}

        for mode in modes:
            config = RVAgentConfig(
                package_name=app_package,
                execution_mode=mode,
                timeout=60
            )

            agent = RVAgent(config)
            results[mode] = agent.run()

        # Análise
        print("\n" + "="*60)
        print("MODE COMPARISON")
        print("="*60)

        for metric in ["unique_states", "total_transitions", "execution_time_s"]:
            print(f"\n{metric}:")
            for mode in modes:
                value = results[mode].get(metric, 0)
                print(f"  {mode:12}: {value}")

        # Validações
        # DFS e Hybrid devem ter cobertura similar (DFS é baseline)
        dfs_states = results["pure_dfs"]["unique_states"]
        hybrid_states = results["hybrid"]["unique_states"]

        assert hybrid_states >= dfs_states * 0.8, \
            "Hybrid should have at least 80% of DFS coverage"
```

### 8.2 Script de Benchmark

```python
# modules/rv-agent/benchmarks/mode_benchmark.py

"""
Benchmark de comparação entre modos.

Executa os 3 modos em múltiplos apps e compara métricas.
"""

import time
import json
from pathlib import Path
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.rv_agent import RVAgent


APPS = [
    "br.unb.cic.cryptoapp",
    "com.amaze.filemanager",
    "com.android.keepass",
    # ... mais apps
]


def benchmark_mode(app_package: str, mode: str, timeout: int = 120) -> dict:
    """Executa teste em um modo específico."""

    config = RVAgentConfig(
        package_name=app_package,
        execution_mode=mode,
        llm_model="qwen3-vl:4b" if mode != "pure_dfs" else None,
        timeout=timeout
    )

    start = time.time()
    agent = RVAgent(config)
    results = agent.run()
    end = time.time()

    return {
        "mode": mode,
        "app": app_package,
        **results,
        "wall_time": end - start
    }


def run_benchmark():
    """Executa benchmark completo."""

    results = []

    for app in APPS:
        print(f"\n{'='*60}")
        print(f"App: {app}")
        print(f"{'='*60}\n")

        for mode in ["pure_dfs", "llm_only", "hybrid"]:
            print(f"  Testing {mode}...")

            try:
                result = benchmark_mode(app, mode)
                results.append(result)

                print(f"    States: {result['unique_states']}")
                print(f"    Time: {result['wall_time']:.1f}s")

            except Exception as e:
                print(f"    ERROR: {e}")

    # Salva resultados
    output_file = Path("benchmark_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to {output_file}")

    # Análise agregada
    analyze_results(results)


def analyze_results(results: list):
    """Analisa e imprime comparação."""

    print("\n" + "="*60)
    print("AGGREGATE ANALYSIS")
    print("="*60)

    by_mode = {}
    for result in results:
        mode = result["mode"]
        if mode not in by_mode:
            by_mode[mode] = []
        by_mode[mode].append(result)

    metrics = ["unique_states", "total_transitions", "wall_time"]

    for metric in metrics:
        print(f"\n{metric.upper()}:")
        for mode in ["pure_dfs", "llm_only", "hybrid"]:
            if mode in by_mode:
                values = [r[metric] for r in by_mode[mode]]
                avg = sum(values) / len(values)
                print(f"  {mode:12}: {avg:8.2f} (avg across {len(values)} apps)")


if __name__ == "__main__":
    run_benchmark()
```

---

## 9. Casos de Uso Práticos

### 9.1 Caso 1: LLM Indisponível

```python
# Cenário: Ollama está offline

try:
    config = RVAgentConfig(
        package_name="com.example.app",
        execution_mode="hybrid"  # Prefere LLM
    )

    agent = RVAgent(config)
    # __init__ detecta que LLM não está disponível
    # Faz fallback automático para pure_dfs

    results = agent.run()
    # Exploração continua com DFS puro!

except Exception as e:
    print(f"Even with Ollama down, we got results: {results}")
```

### 9.2 Caso 2: Debug de Problema

```python
# Problema: App não explora Feature X

# Passo 1: Testa com DFS puro
config_dfs = RVAgentConfig(execution_mode="pure_dfs")
agent_dfs = RVAgent(config_dfs)
results_dfs = agent_dfs.run()

if results_dfs["feature_x_reached"]:
    print("✅ DFS conseguiu chegar em Feature X")
    print("   Problema está no LLM (prompt ou modelo)")
else:
    print("❌ Nem DFS conseguiu")
    print("   Problema estrutural (UI não clickável, etc)")

# Passo 2: Analisa trace do DFS
print("DFS Path to Feature X:")
for transition in agent_dfs.dynamic_graph.transitions:
    print(f"  {transition.from_hash[:8]} → {transition.to_hash[:8]}")
    print(f"    Actions: {transition.action_sequence}")
```

### 9.3 Caso 3: Baseline para Experimento

```python
# Experimento: Avaliar impacto de novo prompt

# Baseline: DFS puro (sem LLM)
baseline_dfs = run_test(execution_mode="pure_dfs")

# V10: Prompt atual
v10_results = run_test(execution_mode="llm_only", prompt_version="v10")

# V11: Novo prompt
v11_results = run_test(execution_mode="llm_only", prompt_version="v11")

# Análise
print("Coverage Comparison:")
print(f"  DFS Baseline: {baseline_dfs['coverage']}%")
print(f"  V10:          {v10_results['coverage']}%")
print(f"  V11:          {v11_results['coverage']}%")

improvement_v10 = v10_results['coverage'] - baseline_dfs['coverage']
improvement_v11 = v11_results['coverage'] - baseline_dfs['coverage']

print(f"\nImprovement over DFS:")
print(f"  V10: +{improvement_v10}%")
print(f"  V11: +{improvement_v11}%")

if improvement_v11 > improvement_v10:
    print("✅ V11 is better!")
else:
    print("❌ V11 is worse, keep V10")
```

### 9.4 Caso 4: Teste Rápido sem Custo

```bash
# CI/CD pipeline - testes rápidos sem LLM

# Antes (com LLM):
# - Tempo: ~10 minutos
# - Custo: tokens
# - Requer Ollama/API

# Depois (DFS puro):
poetry run pytest -k test_app_exploration --mode=pure_dfs
# - Tempo: ~2 minutos ✅
# - Custo: ZERO ✅
# - Sem dependências externas ✅
```

---

## 10. Comparação de Performance

### 10.1 Tabela Comparativa Detalhada

| Métrica | Pure DFS | LLM Only | Hybrid |
|---------|----------|----------|--------|
| **Velocidade** | ~0.1s/it | ~2.5s/it | ~1.5s/it |
| **Custo (tokens)** | 0 | ~4600/it | ~2500/it |
| **Custo ($)** | $0 | ~$0.005/it | ~$0.003/it |
| **Determinismo** | 100% | 0% | ~30% |
| **Cobertura** | 60-70% | 40-90% | 70-95% |
| **Criatividade** | 0% | 100% | 80% |
| **Robustez** | 100% | 60% | 95% |
| **Complexidade** | Baixa | Média | Alta |
| **Requer LLM** | ❌ | ✅ | ✅ (opcional) |
| **Loop Detection** | N/A | ❌ (sem v3) | ✅ |
| **MOP Priority** | ✅ | ✅ | ✅✅ |
| **Semântica** | ❌ | ✅ | ✅ |
| **Testabilidade** | ✅✅ | ⚠️ | ✅ |

### 10.2 Gráfico de Performance Esperado

```
Coverage (%)
     100 │                           ╱─── Hybrid (95%)
         │                      ╱───╯
      80 │                 ╱───╯
         │            ╱───╯
      60 │       ╱───╯── DFS (70%)
         │  ╱───╯
      40 │─╯
         │          LLM Only (variável: 40-90%)
      20 │
         │
       0 └──────────────────────────────────────
           0    20    40    60    80   100  120
                    Time (seconds)

Legend:
  DFS:     Consistente, sobe linearmente
  LLM:     Variável, pode ter platôs (loops)
  Hybrid:  Combina velocidade inicial da LLM + sistematicidade do DFS
```

### 10.3 Trade-offs por Modo

#### Pure DFS
**Use quando**:
- Precisa de baseline confiável
- Testes automatizados (CI/CD)
- LLM não disponível
- Custo é limitação crítica
- Determinismo é requisito

**Não use quando**:
- App tem UI complexa (WebViews)
- Precisa de entendimento semântico
- Formulários com validação complexa

#### LLM Only
**Use quando**:
- Máxima criatividade é necessária
- App tem UI não-estruturada
- Pesquisa: upper bound
- Custo não é problema

**Não use quando**:
- Precisa de garantias de cobertura
- Tempo é limitado (pode looping)
- Custo é crítico

#### Hybrid (Recomendado)
**Use quando**:
- Produção
- Balanceamento custo/performance
- Robustez é crítica
- Quer o melhor dos dois mundos

**Não use quando**:
- Quer isolar componentes (teste A/B)
- Complexidade é preocupação

---

## 11. Estimativas de Implementação

### 11.1 Linhas de Código por Componente

| Componente | Linhas | Complexidade |
|------------|--------|--------------|
| **DFSStrategy extensions** | ~150 | Média |
| - `select_next_action()` | ~80 | Média |
| - `_action_to_dict()` | ~30 | Baixa |
| - `_generate_input_text()` | ~40 | Baixa |
| **RVAgentConfig** | ~30 | Baixa |
| - Novos campos | ~10 | Trivial |
| - `get_execution_mode()` | ~5 | Trivial |
| - `validate()` | ~15 | Baixa |
| **RVAgent multi-modo** | ~200 | Alta |
| - `_build_graph_*()` métodos | ~100 | Média |
| - `_decision_router_node()` | ~30 | Média |
| - `_dfs_decide_node()` | ~30 | Média |
| - Helper methods | ~40 | Baixa |
| **AgentState** | ~10 | Trivial |
| - Novos campos | ~10 | Trivial |
| **Testes** | ~300 | Média |
| - Testes por modo | ~200 | Média |
| - Benchmark | ~100 | Baixa |
| **TOTAL** | **~690** | - |

### 11.2 Tempo de Implementação Estimado

| Fase | Tarefa | Tempo |
|------|--------|-------|
| **1** | DFSStrategy standalone | 3h |
| **2** | RVAgentConfig extensions | 1h |
| **3** | RVAgent multi-modo | 4h |
| **4** | AgentState updates | 0.5h |
| **5** | Integração e debug | 2h |
| **6** | Testes unitários | 3h |
| **7** | Testes de integração | 2h |
| **8** | Benchmark e validação | 2h |
| **9** | Documentação | 1h |
| **TOTAL** | | **~18.5h** |

### 11.3 Risco de Regressão

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Break existing tests** | Baixa | Médio | Testes de regressão |
| **Performance degradation** | Baixa | Baixo | Benchmarks antes/depois |
| **LLM compatibility** | Média | Alto | Testes com múltiplos modelos |
| **DFS bugs** | Média | Médio | Testes unitários extensivos |

### 11.4 Dependências

| Dependência | Status | Notas |
|-------------|--------|-------|
| **v3 (loop detection)** | ✅ Planejado | Pode ser implementado em paralelo |
| **DynamicStateGraph** | ✅ Existe | Apenas extensões |
| **LangGraph** | ✅ Existe | Adicionar conditional routing |
| **Ollama** | ⚠️ Opcional | Só para llm_only/hybrid |

---

## 12. Integração com v3

### 12.1 Relação entre v3 e v4

**v3 (Loop Detection + Validation)**:
- Foco: Prevenir loops no modo híbrido
- Adiciona: `strategy_validation_node`
- Detecção: Repetições consecutivas
- Fallback: DFS escolhe ação untested

**v4 (Multi-Mode Architecture)**:
- Foco: DFS como componente standalone + múltiplos modos
- Adiciona: Sistema de roteamento, DFS completo, configuração
- Extends v3: Usa validation do v3 no modo híbrido

### 12.2 Compatibilidade

**v3 PODE ser implementado independentemente**:
- Implementa apenas modo híbrido
- Não adiciona pure_dfs ou llm_only
- Resolve problema de loops

**v4 DEPENDE de v3**:
- Usa `strategy_validation_node` do v3
- Adiciona modos pure_dfs e llm_only
- Estende com sistema de configuração

**Recomendação**: Implementar v3 primeiro (menos complexo), depois v4.

### 12.3 Roadmap de Implementação

```
Fase 1: v3 - Loop Detection (Prioridade ALTA)
├─ Modificar DynamicStateGraph (trace)
├─ Adicionar strategy_validation_node
├─ Testar com modo híbrido básico
└─ Validar eliminação de loops

Fase 2: v4 - Multi-Mode (Prioridade MÉDIA)
├─ Estender DFSStrategy (standalone)
├─ Adicionar RVAgentConfig (modos)
├─ Implementar decision_router
├─ Adicionar pure_dfs e llm_only
└─ Testes e benchmarks

Fase 3: Otimização (Prioridade BAIXA)
├─ Tune de thresholds
├─ Performance optimization
└─ Documentação final
```

### 12.4 Migração de Código Existente

**Código atual (V10)** → **v3** → **v4**

```python
# V10 atual (sem mudanças)
config = RVAgentConfig(package_name="app")
agent = RVAgent(config)
agent.run()

# v3 (backward compatible)
config = RVAgentConfig(package_name="app")
agent = RVAgent(config)  # Usa híbrido por padrão
agent.run()

# v4 (explicit mode)
config = RVAgentConfig(
    package_name="app",
    execution_mode="hybrid"  # Explícito
)
agent = RVAgent(config)
agent.run()

# v4 (pure dfs)
config = RVAgentConfig(
    package_name="app",
    execution_mode="pure_dfs"  # NOVO!
)
agent = RVAgent(config)
agent.run()
```

**Compatibilidade**: 100% backward compatible se `execution_mode` default = "hybrid"

---

## 13. Extensibilidade: Adicionando Novos Algoritmos

### 13.1 Motivação

A arquitetura multi-modo v4 foi projetada com **extensibilidade** como princípio fundamental. Adicionar novos algoritmos de exploração (além de DFS/BFS) deve ser:

- ✅ **Simples**: 3 passos claros
- ✅ **Rápido**: ~30 minutos por algoritmo
- ✅ **Seguro**: Sem quebrar código existente
- ✅ **Testável**: Isolado e plugável

### 13.2 Arquitetura de Estratégias

#### Interface Base

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

        Args:
            screen_hash: Hash estrutural do estado atual
            screen_desc: Descrição parsed da tela

        Returns:
            Dict com ação a executar, ou None se exploração completa

        Exemplo de retorno:
        {
            "action_type": "CLICK",
            "x": 540,
            "y": 960,
            "description": "Login button",
            "id": 42,
            "reason": "DFS choosing untested action"
        }
        """
        pass

    def reset(self):
        """Reseta estado interno (útil para testes)."""
        pass

    def _action_to_dict(self, action) -> Dict:
        """
        Helper method: Converte ScreenAction para dict executável.

        Estratégias podem sobrescrever para customizar conversão.
        """
        return {
            "action_type": "CLICK",
            "x": action.bounds[0] if action.bounds else 0,
            "y": action.bounds[1] if action.bounds else 0,
            "description": action.text or action.content_desc or "element",
            "id": action.id
        }
```

### 13.3 Processo de Adição de Novo Algoritmo

**3 Passos Simples**:

#### Passo 1: Criar Classe Herdando BaseStrategy

```python
# modules/rv-agent/src/rv_agent/strategies/random_strategy.py

import random
from typing import Optional, Dict
from .base_strategy import BaseStrategy
from rv_agent.domain.screen import ScreenDescription


class RandomStrategy(BaseStrategy):
    """
    Estratégia de exploração aleatória.

    Escolhe ação untested aleatoriamente (sem heurísticas).
    Útil para baseline estatístico.
    """

    def select_next_action(
        self,
        screen_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[Dict]:
        """Escolhe ação aleatória."""

        # 1. Pega/cria nó no grafo
        if screen_hash not in self.dynamic_graph.states:
            node = self.dynamic_graph.get_or_create_state(
                screen_hash,
                screen_desc.activity,
                screen_desc
            )
        else:
            node = self.dynamic_graph.states[screen_hash]

        # 2. Pega ações untested
        all_actions = screen_desc.get_all_actions()
        untested = [
            action for action in all_actions
            if action.id not in node.executed_actions
        ]

        # 3. Escolhe aleatoriamente
        if untested:
            random_action = random.choice(untested)
            return self._action_to_dict(random_action)

        # 4. Estado esgotado → BACK
        return {"action_type": "BACK", "reason": "Random: state exhausted"}

    def _action_to_dict(self, action) -> Dict:
        """Converte ação (mesmo que DFS)."""
        result = {
            "action_type": "CLICK",
            "x": action.bounds[0] if action.bounds else 0,
            "y": action.bounds[1] if action.bounds else 0,
            "description": action.text or "element",
            "id": action.id,
            "algorithm": "random"
        }

        # Determina tipo
        if action.editable:
            result["action_type"] = "TYPE_TEXT"
            result["text"] = "Random Test Input"
        elif action.scrollable:
            result["action_type"] = "SCROLL"
            result["direction"] = random.choice(["up", "down", "left", "right"])

        return result
```

#### Passo 2: Implementar Lógica de Seleção

```python
# modules/rv-agent/src/rv_agent/strategies/greedy_coverage_strategy.py

from typing import Optional, Dict, Set
from .base_strategy import BaseStrategy


class GreedyCoverageStrategy(BaseStrategy):
    """
    Estratégia greedy que prioriza estados não-visitados.

    Sempre escolhe ação que leva a estado novo (se houver).
    Se não houver, escolhe ação com menor visita.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visited_hashes: Set[str] = set()

    def select_next_action(
        self,
        screen_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[Dict]:
        """Escolhe ação que maximiza cobertura."""

        # Marca estado atual como visitado
        self.visited_hashes.add(screen_hash)

        # Pega nó
        node = self.dynamic_graph.get_or_create_state(
            screen_hash,
            screen_desc.activity,
            screen_desc
        )

        # Pega ações untested
        all_actions = screen_desc.get_all_actions()
        untested = [
            action for action in all_actions
            if action.id not in node.executed_actions
        ]

        if not untested:
            return {"action_type": "BACK", "reason": "Greedy: backtrack"}

        # Estratégia greedy: tenta prever qual ação leva a estado novo
        scored_actions = []

        for action in untested:
            score = self._score_action(action, screen_hash)
            scored_actions.append((score, action))

        # Ordena por score (maior = melhor)
        scored_actions.sort(reverse=True, key=lambda x: x[0])

        best_action = scored_actions[0][1]
        best_score = scored_actions[0][0]

        result = self._action_to_dict(best_action)
        result["greedy_score"] = best_score
        result["reason"] = f"Greedy coverage (score={best_score})"

        return result

    def _score_action(self, action, current_hash: str) -> float:
        """
        Calcula score de uma ação.

        Heurísticas:
        - Ações que mudam atividade: +10
        - Ações para elementos não-visitados: +5
        - Ações com MOP markers: +3
        - Clicks: +1
        - Outros: 0
        """
        score = 0.0

        # Heurística 1: Mudança de atividade
        if action.action_type == "CLICK" and "button" in action.class_name.lower():
            score += 10

        # Heurística 2: MOP priority
        if self.static_data and hasattr(action, 'reaches_mop'):
            if action.directly_reaches_mop:
                score += 5
            elif action.reaches_mop:
                score += 3

        # Heurística 3: Elemento novo
        element_hash = f"{action.resource_id}_{action.text}_{action.class_name}"
        if element_hash not in self._get_seen_elements():
            score += 5

        # Heurística 4: Tipo de ação
        if action.clickable:
            score += 1

        return score

    def _get_seen_elements(self) -> Set[str]:
        """Retorna elementos já interagidos."""
        seen = set()
        for state_hash, node in self.dynamic_graph.states.items():
            for action_id in node.executed_actions:
                # Simplificação: usa action_id como proxy
                seen.add(str(action_id))
        return seen

    def reset(self):
        """Reset estado."""
        self.visited_hashes.clear()
```

#### Passo 3: Registrar no Factory

```python
# modules/rv-agent/src/rv_agent/strategies/strategy_factory.py

from typing import Dict, Type
from .base_strategy import BaseStrategy
from .dfs_strategy import DFSStrategy
from .bfs_strategy import BFSStrategy
from .random_strategy import RandomStrategy
from .greedy_coverage_strategy import GreedyCoverageStrategy


# ===== STRATEGY MAP (FACTORY) =====
STRATEGY_MAP: Dict[str, Type[BaseStrategy]] = {
    "dfs": DFSStrategy,
    "bfs": BFSStrategy,
    "random": RandomStrategy,              # ✅ NOVO!
    "greedy": GreedyCoverageStrategy,      # ✅ NOVO!
    # Adicione mais aqui...
}


def create_strategy(
    strategy_name: str,
    dynamic_graph,
    static_data=None,
    mode: str = "hybrid"
) -> BaseStrategy:
    """
    Factory para criar estratégias.

    Args:
        strategy_name: Nome da estratégia ("dfs", "bfs", "random", etc)
        dynamic_graph: Grafo dinâmico
        static_data: Análise estática
        mode: Modo de operação

    Returns:
        Instância da estratégia

    Raises:
        ValueError: Se estratégia não existir
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

### 13.4 Exemplos de Algoritmos Avançados

#### Exemplo 1: ML-Guided Strategy

```python
# modules/rv-agent/src/rv_agent/strategies/ml_guided_strategy.py

import numpy as np
from typing import Optional, Dict
from .base_strategy import BaseStrategy


class MLGuidedStrategy(BaseStrategy):
    """
    Estratégia guiada por ML (modelo pré-treinado).

    Usa modelo de ML para prever qual ação tem maior probabilidade
    de descobrir novos estados.

    Requer:
    - Modelo treinado em dados históricos
    - Feature extraction de ações
    """

    def __init__(self, *args, model_path: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = self._load_model(model_path) if model_path else None

    def select_next_action(
        self,
        screen_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[Dict]:
        """Escolhe ação usando ML."""

        # Pega untested
        node = self.dynamic_graph.get_or_create_state(
            screen_hash,
            screen_desc.activity,
            screen_desc
        )

        all_actions = screen_desc.get_all_actions()
        untested = [
            action for action in all_actions
            if action.id not in node.executed_actions
        ]

        if not untested:
            return {"action_type": "BACK"}

        # Extrai features de cada ação
        action_features = [
            self._extract_features(action, screen_desc)
            for action in untested
        ]

        # Prediz scores usando modelo
        if self.model:
            scores = self.model.predict_proba(action_features)
            best_idx = np.argmax(scores)
        else:
            # Fallback: escolhe aleatoriamente
            import random
            best_idx = random.randint(0, len(untested) - 1)

        best_action = untested[best_idx]

        result = self._action_to_dict(best_action)
        result["ml_score"] = float(scores[best_idx]) if self.model else 0.0

        return result

    def _extract_features(self, action, screen_desc) -> np.ndarray:
        """
        Extrai features de uma ação para ML.

        Features:
        - Position (x, y normalized)
        - Size (width, height normalized)
        - Type (one-hot: clickable, editable, scrollable)
        - Context (# siblings, depth in tree)
        - Text similarity (com título da tela)
        """

        features = []

        # Position
        if action.bounds:
            x_norm = action.bounds[0] / 1080  # Assume 1080 width
            y_norm = action.bounds[1] / 1920  # Assume 1920 height
            features.extend([x_norm, y_norm])
        else:
            features.extend([0.5, 0.5])

        # Size
        if action.bounds and len(action.bounds) >= 4:
            w_norm = (action.bounds[2] - action.bounds[0]) / 1080
            h_norm = (action.bounds[3] - action.bounds[1]) / 1920
            features.extend([w_norm, h_norm])
        else:
            features.extend([0.1, 0.1])

        # Type (one-hot)
        features.extend([
            1.0 if action.clickable else 0.0,
            1.0 if action.editable else 0.0,
            1.0 if action.scrollable else 0.0
        ])

        # Context
        total_actions = len(screen_desc.get_all_actions())
        features.append(total_actions / 100.0)  # Normalized

        return np.array(features)

    def _load_model(self, model_path: str):
        """Carrega modelo ML."""
        try:
            import joblib
            return joblib.load(model_path)
        except Exception as e:
            print(f"Warning: Could not load ML model: {e}")
            return None
```

#### Exemplo 2: Hybrid DFS+Random Strategy

```python
# modules/rv-agent/src/rv_agent/strategies/hybrid_dfs_random.py

import random
from typing import Optional, Dict
from .dfs_strategy import DFSStrategy


class HybridDFSRandomStrategy(DFSStrategy):
    """
    Combinação de DFS com exploração aleatória.

    - 80% do tempo: DFS sistemático
    - 20% do tempo: escolha aleatória (para escapar de local minima)
    """

    def __init__(self, *args, random_probability: float = 0.2, **kwargs):
        super().__init__(*args, **kwargs)
        self.random_prob = random_probability

    def select_next_action(
        self,
        screen_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[Dict]:
        """Escolhe DFS ou Random probabilisticamente."""

        # Decide: DFS ou Random?
        if random.random() < self.random_prob:
            # 20%: escolha aleatória
            return self._random_choice(screen_hash, screen_desc)
        else:
            # 80%: DFS normal
            return super().select_next_action(screen_hash, screen_desc)

    def _random_choice(
        self,
        screen_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[Dict]:
        """Escolha aleatória."""

        node = self.dynamic_graph.get_or_create_state(
            screen_hash,
            screen_desc.activity,
            screen_desc
        )

        all_actions = screen_desc.get_all_actions()
        untested = [
            action for action in all_actions
            if action.id not in node.executed_actions
        ]

        if untested:
            random_action = random.choice(untested)
            result = self._action_to_dict(random_action)
            result["reason"] = "Hybrid: random exploration"
            return result

        return {"action_type": "BACK"}
```

### 13.5 Uso dos Novos Algoritmos

```python
# Exemplo de uso

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.rv_agent import RVAgent


# Teste 1: Random Strategy
config_random = RVAgentConfig(
    package_name="com.example.app",
    execution_mode="pure_dfs",  # Sem LLM
    strategy="random",          # ✅ Usa RandomStrategy
    timeout=120
)
agent_random = RVAgent(config_random)
results_random = agent_random.run()


# Teste 2: Greedy Coverage
config_greedy = RVAgentConfig(
    package_name="com.example.app",
    execution_mode="pure_dfs",
    strategy="greedy",          # ✅ Usa GreedyCoverageStrategy
    timeout=120
)
agent_greedy = RVAgent(config_greedy)
results_greedy = agent_greedy.run()


# Teste 3: ML-Guided
config_ml = RVAgentConfig(
    package_name="com.example.app",
    execution_mode="pure_dfs",
    strategy="ml_guided",       # ✅ Usa MLGuidedStrategy
    timeout=120
)
agent_ml = RVAgent(config_ml)
results_ml = agent_ml.run()


# Comparação
print("Coverage Comparison:")
print(f"  Random: {results_random['unique_states']} states")
print(f"  Greedy: {results_greedy['unique_states']} states")
print(f"  ML:     {results_ml['unique_states']} states")
```

### 13.6 Checklist de Nova Estratégia

Ao adicionar novo algoritmo, verifique:

- [ ] **Herda de BaseStrategy**
- [ ] **Implementa `select_next_action()`**
- [ ] **Registrado em STRATEGY_MAP**
- [ ] **Retorna None quando exploração completa**
- [ ] **Usa `dynamic_graph` compartilhado**
- [ ] **Implementa `reset()` se tem estado interno**
- [ ] **Adiciona testes unitários**
- [ ] **Documenta comportamento e casos de uso**
- [ ] **Considera MOP priority (se static_data disponível)**
- [ ] **Testa isoladamente antes de integrar**

### 13.7 Tabela de Estratégias Disponíveis

| Estratégia | Arquivo | Descrição | Complexidade | Custo | Melhor Uso |
|------------|---------|-----------|--------------|-------|------------|
| **DFS** | `dfs_strategy.py` | Depth-first sistemático | Baixa | O(n) | Baseline, cobertura garantida |
| **BFS** | `bfs_strategy.py` | Breadth-first por níveis | Média | O(n) | UI com múltiplos tabs/menus |
| **Random** | `random_strategy.py` | Escolha aleatória | Baixa | O(1) | Baseline estatístico, fuzzing |
| **Greedy** | `greedy_coverage_strategy.py` | Maximiza cobertura localmente | Média | O(n log n) | Apps com muitas telas |
| **ML-Guided** | `ml_guided_strategy.py` | Predição ML | Alta | O(n) + modelo | Com dados de treinamento |
| **Hybrid DFS+Random** | `hybrid_dfs_random.py` | DFS com exploração aleatória | Baixa | O(n) | Escapar local minima |

---

## 14. Seleção Dinâmica: Strategy Selector Node

### 14.1 Motivação

A arquitetura v4 suporta **múltiplas estratégias**, mas até agora a escolha é **fixa** (configurada no início).

**Problema**: Nem sempre uma estratégia é ótima para TODOS os estados:
- DFS é bom para exploração sistemática
- Random é bom para escapar loops
- Greedy é bom quando há muitas opções
- ML pode ser melhor em contextos específicos

**Solução**: **Strategy Selector Node** que escolhe **dinamicamente** qual estratégia usar baseado no **contexto atual**.

### 14.2 Arquitetura: Fixed vs Dynamic

#### Modo Atual (Fixed Strategy)

```
┌─────────────────────────────────────────────┐
│       FIXED STRATEGY (v4 atual)             │
├─────────────────────────────────────────────┤
│                                             │
│  Config: strategy = "dfs"                   │
│                                             │
│  ┌──────┐   ┌─────────┐   ┌──────┐         │
│  │ OBS  │──▶│   DFS   │──▶│TOOLS │         │
│  └──────┘   │(sempre) │   └──────┘         │
│             └─────────┘                     │
│                                             │
│  ✅ Simples                                 │
│  ❌ Inflexível                               │
│  ❌ Subótimo em alguns contextos            │
└─────────────────────────────────────────────┘
```

#### Modo Proposto (Dynamic Selection)

```
┌─────────────────────────────────────────────────────────┐
│       DYNAMIC STRATEGY SELECTION (v4 proposta)          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────┐   ┌──────────────────┐   ┌──────┐           │
│  │ OBS  │──▶│ STRATEGY_SELECTOR│──▶│TOOLS │           │
│  └──────┘   │    (dinâmico)    │   └──────┘           │
│             └──────────────────┘                       │
│                     │                                   │
│                     ├─── Critérios:                    │
│                     │    1. MOP markers → DFS          │
│                     │    2. High revisit → BFS         │
│                     │    3. Form detected → LLM        │
│                     │    4. Long list → Random         │
│                     │    5. Token budget low → Greedy  │
│                     │    Default → DFS                 │
│                     │                                   │
│  ✅ Adaptativo                                         │
│  ✅ Otimiza para contexto                              │
│  ⚠️ Mais complexo                                      │
└─────────────────────────────────────────────────────────┘
```

### 14.3 Implementação Completa

#### Nó: Strategy Selector

```python
# modules/rv-agent/src/rv_agent/core/rv_agent.py

def _strategy_selector_node(self, state: AgentState) -> AgentState:
    """
    Nó que seleciona dinamicamente qual estratégia usar.

    Analisa contexto atual e escolhe melhor algoritmo:
    - DFS: Para exploração sistemática com MOP guidance
    - BFS: Para estados com alta taxa de revisita (breadth-first)
    - Random: Para listas longas (fuzzing)
    - Greedy: Para muitas opções (coverage maximization)
    - LLM: Para formulários complexos (semântica necessária)

    Returns:
        AgentState com campos:
        - selected_strategy: Nome da estratégia escolhida
        - selection_reason: Motivo da escolha
        - current_action: Ação decidida pela estratégia
    """

    screen_hash = state["current_screen_hash"]
    screen_desc = state["screen_description_obj"]
    iteration = state.get("iteration", 0)

    # ===== CRITÉRIO 1: MOP Markers (Alta Prioridade) =====
    if self._has_mop_markers(screen_desc):
        strategy_name = "dfs"
        reason = "MOP markers detected → DFS for systematic exploration"

    # ===== CRITÉRIO 2: Alta Taxa de Revisita =====
    elif self._high_revisit_rate(screen_hash):
        strategy_name = "bfs"
        reason = "High revisit rate → BFS to explore breadth-first"

    # ===== CRITÉRIO 3: Formulário Detectado =====
    elif self._is_form(screen_desc):
        # Se LLM disponível, usa (melhor para preencher forms)
        if self.config.get_execution_mode() in ["llm_only", "hybrid"]:
            strategy_name = "llm"
            reason = "Form detected → LLM for semantic understanding"
        else:
            strategy_name = "dfs"
            reason = "Form detected → DFS (LLM not available)"

    # ===== CRITÉRIO 4: Lista Longa (Fuzzing) =====
    elif self._is_long_list(screen_desc):
        strategy_name = "random"
        reason = "Long list detected → Random for fuzzing"

    # ===== CRITÉRIO 5: Budget de Tokens Baixo =====
    elif self._low_token_budget(state):
        strategy_name = "greedy"
        reason = "Low token budget → Greedy for fast coverage"

    # ===== CRITÉRIO 6: Muitas Opções =====
    elif self._many_options(screen_desc):
        strategy_name = "greedy"
        reason = "Many options → Greedy for coverage optimization"

    # ===== DEFAULT: DFS =====
    else:
        strategy_name = "dfs"
        reason = "Default → DFS for systematic exploration"

    logger.info(f"🎯 Strategy Selector: {strategy_name.upper()}")
    logger.info(f"   Reason: {reason}")

    # ===== Executa Estratégia Selecionada =====

    if strategy_name == "llm":
        # Delega para LLM
        # (código já existe em _assistant_node)
        action = self._get_llm_action(state)

    else:
        # Usa estratégia algorítmica
        strategy = self._get_or_create_strategy(strategy_name)
        action = strategy.select_next_action(screen_hash, screen_desc)

    # Valida resultado
    if action is None:
        logger.info("   Strategy returned None → exploration complete")
        action = {"action_type": "END"}

    return {
        "selected_strategy": strategy_name,
        "selection_reason": reason,
        "current_action": action,
        "decision_maker": strategy_name
    }


# ===== Helper Methods para Critérios =====

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

    # Alta revisita: visitado mais de 3 vezes
    return node.visit_count > 3


def _is_form(self, screen_desc) -> bool:
    """Detecta se tela é um formulário."""
    all_actions = screen_desc.get_all_actions()

    # Heurística: tem múltiplos campos editáveis + botão submit
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

    # Heurística: muitas ações da mesma classe (ListView, RecyclerView)
    class_counts = {}
    for action in all_actions:
        cls = action.class_name
        class_counts[cls] = class_counts.get(cls, 0) + 1

    # Se alguma classe tem >10 instâncias → lista longa
    return any(count > 10 for count in class_counts.values())


def _low_token_budget(self, state: AgentState) -> bool:
    """Verifica se budget de tokens está baixo."""
    # Exemplo: se já usou mais de 80% do budget
    max_tokens = 100000  # Configurável
    used_tokens = state.get("total_tokens_used", 0)

    return used_tokens > (max_tokens * 0.8)


def _many_options(self, screen_desc) -> bool:
    """Verifica se tela tem muitas opções."""
    all_actions = screen_desc.get_all_actions()

    # Muitas opções: >20 ações
    return len(all_actions) > 20


# ===== Strategy Cache =====

def _get_or_create_strategy(self, strategy_name: str):
    """
    Pega ou cria instância de estratégia.

    Mantém cache de estratégias para evitar recriar.
    """

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

### 14.4 Integração no Grafo LangGraph

```python
def _build_graph_dynamic_selection(self):
    """
    Grafo com seleção dinâmica de estratégia.

    Novo modo: execution_mode = "dynamic"
    """

    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("observe", self._observe_node)
    graph.add_node("strategy_selector", self._strategy_selector_node)  # ✅ NOVO!
    graph.add_node("tools", ToolNode(self.tools))
    graph.add_node("learn", self._learn_node)

    # Edges
    graph.set_entry_point("observe")
    graph.add_edge("observe", "strategy_selector")
    graph.add_edge("strategy_selector", "tools")
    graph.add_edge("tools", "learn")

    # Loop
    graph.add_conditional_edges(
        "learn",
        self._should_continue,
        {"continue": "observe", "end": END}
    )

    return graph.compile()
```

### 14.5 Configuração

```python
# modules/rv-agent/src/rv_agent/config/agent_config.py

@dataclass
class RVAgentConfig:
    # ... campos existentes ...

    # Novo modo de execução
    execution_mode: str = "hybrid"  # "pure_dfs", "llm_only", "hybrid", "dynamic"

    # Para modo dynamic: estratégias disponíveis
    available_strategies: List[str] = None  # ["dfs", "bfs", "random", "greedy"]

    def __post_init__(self):
        if self.available_strategies is None:
            # Default: todas as estratégias
            self.available_strategies = ["dfs", "bfs", "random", "greedy"]
```

### 14.6 Exemplo de Execução com Seleção Dinâmica

```
╔══════════════════════════════════════════════════════════════╗
║         EXEMPLO: DYNAMIC SELECTION EM AÇÃO                   ║
╚══════════════════════════════════════════════════════════════╝

Iteração 1: Login Screen
┌─ OBSERVE ────────────────────────────────────────────┐
│ Activity: LoginActivity                              │
│ Elements: [Email (EditText), Password (EditText),   │
│            Submit (Button)]                          │
└──────────────────────────────────────────────────────┘
         ▼
┌─ STRATEGY_SELECTOR ──────────────────────────────────┐
│ Análise:                                             │
│   - has_mop_markers: False                           │
│   - high_revisit: False                              │
│   - is_form: True ✅ (2 EditTexts + Submit button)   │
│   - is_long_list: False                              │
│                                                      │
│ ✅ Decisão: LLM                                       │
│    Reason: "Form detected → LLM for semantic"        │
└──────────────────────────────────────────────────────┘
         ▼
┌─ LLM EXECUTION ──────────────────────────────────────┐
│ LLM analisa tela e preenche formulário:             │
│   - Email: "testuser@example.com"                   │
│   - Password: "SecurePass123!"                      │
│   - Click Submit                                     │
└──────────────────────────────────────────────────────┘

Decision: LLM ✅

─────────────────────────────────────────────────────────

Iteração 5: Main Menu
┌─ OBSERVE ────────────────────────────────────────────┐
│ Activity: MainActivity                               │
│ Elements: [Encryption [M], Decryption [M],          │
│            Hash [DM], Settings]                      │
└──────────────────────────────────────────────────────┘
         ▼
┌─ STRATEGY_SELECTOR ──────────────────────────────────┐
│ Análise:                                             │
│   - has_mop_markers: True ✅ ([M] and [DM] markers) │
│   - ...                                              │
│                                                      │
│ ✅ Decisão: DFS                                       │
│    Reason: "MOP markers → DFS systematic"            │
└──────────────────────────────────────────────────────┘
         ▼
┌─ DFS EXECUTION ──────────────────────────────────────┐
│ DFS prioriza ação com [DM]:                         │
│   - Escolhe: Hash (highest priority)                │
└──────────────────────────────────────────────────────┘

Decision: DFS 🤖

─────────────────────────────────────────────────────────

Iteração 12: Contacts List
┌─ OBSERVE ────────────────────────────────────────────┐
│ Activity: ContactsActivity                           │
│ Elements: 45 items (Contact1, Contact2, ...,        │
│            Contact45)                                │
└──────────────────────────────────────────────────────┘
         ▼
┌─ STRATEGY_SELECTOR ──────────────────────────────────┐
│ Análise:                                             │
│   - has_mop_markers: False                           │
│   - is_long_list: True ✅ (45 items of same class)  │
│   - ...                                              │
│                                                      │
│ ✅ Decisão: RANDOM                                    │
│    Reason: "Long list → Random for fuzzing"          │
└──────────────────────────────────────────────────────┘
         ▼
┌─ RANDOM EXECUTION ───────────────────────────────────┐
│ Random escolhe item aleatório:                      │
│   - Escolhe: Contact23 (random)                     │
└──────────────────────────────────────────────────────┘

Decision: RANDOM 🎲

─────────────────────────────────────────────────────────

Iteração 20: Complex Menu (Revisited 4x)
┌─ OBSERVE ────────────────────────────────────────────┐
│ Activity: MenuActivity                               │
│ Visit count: 4 (revisited multiple times)           │
│ Elements: [Tab1, Tab2, Tab3, More...]               │
└──────────────────────────────────────────────────────┘
         ▼
┌─ STRATEGY_SELECTOR ──────────────────────────────────┐
│ Análise:                                             │
│   - high_revisit: True ✅ (visit_count = 4)         │
│   - ...                                              │
│                                                      │
│ ✅ Decisão: BFS                                       │
│    Reason: "High revisit → BFS breadth-first"        │
└──────────────────────────────────────────────────────┘
         ▼
┌─ BFS EXECUTION ──────────────────────────────────────┐
│ BFS explora nível por nível (tabs):                 │
│   - Escolhe: Tab3 (untested)                        │
└──────────────────────────────────────────────────────┘

Decision: BFS 📊

─────────────────────────────────────────────────────────

RESULTADO FINAL (50 iterações):
┌──────────────────────────────────────────────────────┐
│ Strategy Distribution:                               │
│   - LLM:    15 decisions (30%) - forms & complex UI │
│   - DFS:    25 decisions (50%) - MOP guidance        │
│   - BFS:     5 decisions (10%) - high revisit       │
│   - Random:  5 decisions (10%) - long lists         │
│                                                      │
│ Coverage: 95% (melhor que qualquer estratégia única)│
│ Time: 85s (otimizado vs LLM-only: 125s)            │
│ Cost: $0.015 (otimizado vs LLM-only: $0.025)       │
└──────────────────────────────────────────────────────┘
```

### 14.7 Comparação: Fixed vs Dynamic

| Aspecto | Fixed Strategy | Dynamic Selection |
|---------|----------------|-------------------|
| **Flexibilidade** | Baixa (1 estratégia) | Alta (N estratégias) |
| **Otimalidade** | Boa em média | Ótima por contexto |
| **Complexidade** | Baixa | Média |
| **Overhead** | ~0ms | ~5ms (critérios) |
| **Determinismo** | Alto (se estratégia determinística) | Baixo (muda por contexto) |
| **Coverage** | 70-80% | 85-95% |
| **Tempo** | Depende da estratégia | Otimizado |
| **Custo** | Fixo | Otimizado |
| **Testabilidade** | ✅✅ | ✅ |
| **Debug** | Fácil | Médio |
| **Configuração** | `strategy="dfs"` | `execution_mode="dynamic"` |

### 14.8 Métricas e Análise

```python
# Análise de resultados com seleção dinâmica

def analyze_dynamic_selection_results(results: Dict):
    """Analisa distribuição de estratégias usadas."""

    strategy_distribution = results.get("strategy_distribution", {})
    total_decisions = sum(strategy_distribution.values())

    print("Strategy Distribution:")
    for strategy, count in sorted(strategy_distribution.items()):
        percentage = (count / total_decisions) * 100
        print(f"  {strategy:10}: {count:3} decisions ({percentage:5.1f}%)")

    # Analisa eficiência
    print("\nEfficiency Metrics:")
    print(f"  Coverage: {results['coverage']}%")
    print(f"  Time: {results['execution_time_s']:.1f}s")
    print(f"  Cost: ${results['total_cost']:.3f}")

    # Compara com estratégia única
    dfs_baseline = results.get("dfs_baseline", {})
    if dfs_baseline:
        coverage_improvement = results['coverage'] - dfs_baseline['coverage']
        print(f"\nImprovement over DFS baseline:")
        print(f"  Coverage: +{coverage_improvement}%")
        print(f"  Time: {results['execution_time_s'] - dfs_baseline['time']:.1f}s")
```

### 14.9 Trade-offs e Recomendações

**Quando usar Fixed Strategy**:
- ✅ Testes de regressão (determinismo)
- ✅ Benchmarks científicos (comparação justa)
- ✅ Debug (comportamento previsível)
- ✅ Apps simples (overhead não compensa)

**Quando usar Dynamic Selection**:
- ✅ Produção (máxima cobertura)
- ✅ Apps complexos (múltiplos contextos)
- ✅ Otimização de custo/tempo
- ✅ Exploração adaptativa

**Modo Recomendado por Caso de Uso**:

| Caso de Uso | Modo Recomendado | Justificativa |
|-------------|------------------|---------------|
| **CI/CD Pipeline** | Fixed (pure_dfs) | Rápido, determinístico, sem custo |
| **Produção** | Dynamic | Máxima cobertura, otimizado |
| **Research Baseline** | Fixed (pure_dfs) | Comparação científica |
| **Research Upper Bound** | Fixed (llm_only) | Demonstra potencial máximo |
| **App Simples** | Fixed (dfs) | Overhead não compensa |
| **App Complexo** | Dynamic | Adapta ao contexto |
| **Budget Limitado** | Dynamic ou Fixed (greedy) | Otimiza tokens |
| **Debug** | Fixed (dfs) | Previsível |

---

## 15. Resumo Executivo

### Problema
- RVAgent V10 tem loops infinitos
- Sem modo de teste rápido (requer LLM)
- Sem baseline científico para comparação
- Estratégia fixa não otimiza por contexto

### Solução v4 (Completa)

**Arquitetura multi-modo** que permite:

1. **Pure DFS**: Standalone, sem LLM (baseline)
2. **LLM Only**: V10 atual (criatividade)
3. **Hybrid**: LLM + DFS (v3 + v4, produção)
4. **Dynamic**: Seleção automática de estratégia ✨ **NOVO!**

**Extensibilidade**:
- ✅ Fácil adicionar novos algoritmos (3 passos)
- ✅ Factory pattern (STRATEGY_MAP)
- ✅ Interface base (BaseStrategy)
- ✅ Exemplos: Random, Greedy, ML-Guided

**Seleção Dinâmica**:
- ✅ Escolha adaptativa por contexto
- ✅ 6 critérios de decisão
- ✅ Otimização automática de custo/tempo
- ✅ Máxima cobertura (85-95%)

### Benefícios
- ✅ **Testabilidade**: DFS isolado, rápido, determinístico
- ✅ **Robustez**: Fallback automático se LLM falha
- ✅ **Baseline**: Cobertura mínima garantida
- ✅ **Flexibilidade**: 4 modos + N estratégias
- ✅ **Economia**: Pure DFS = $0, dinâmico otimiza tokens
- ✅ **Extensibilidade**: Novos algoritmos em 30 min
- ✅ **Adaptabilidade**: Estratégia ótima por contexto

### Implementação
- **Código**: ~900 linhas (690 base + 210 extensibilidade/seleção)
- **Tempo**: ~22 horas (18.5h base + 3.5h novas features)
- **Risco**: Baixo (mudanças aditivas)
- **Dependência**: v3 (loop detection)

### Próximos Passos
1. Implementar v3 (prioridade alta)
2. Implementar v4 base (prioridade média)
3. Implementar extensibilidade (prioridade média)
4. Implementar seleção dinâmica (prioridade baixa)
5. Validar com 10+ apps
6. Benchmarks comparativos
7. Publicar resultados

---

**FIM DO DOCUMENTO v4 (VERSÃO COMPLETA)**

**Status**: Proposta detalhada com extensibilidade e seleção dinâmica

**Última atualização**: 2025-11-03 (adicionadas seções 13 e 14)

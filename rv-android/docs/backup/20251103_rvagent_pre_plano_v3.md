# RVAgent - Pré-Plano de Refatoração v3 (Decisões Finais)
**Data**: 2025-11-03
**Status**: Decisões arquiteturais finalizadas
**Versão anterior**: `20251103_rvagent_pre_plano_v2.md`

---

## 1. Contexto

### 1.1 Problema Crítico
- **Loop infinito confirmado**: TYPE_TEXT repetido 14x no mesmo campo (CryptoApp test)
- **Root cause**: Estratégias DFS/BFS existem mas nunca são consultadas ("passive guidance")
- **Baseline atual**: 3 unique states, 0 transitions, 70%+ revisit rate em 120s

### 1.2 Baseline Test em Execução
```bash
timeout 1800 poetry run python test_v10_baseline_10apps.py 2>&1 | tee test_v10_baseline_10apps.log
```
- 10 apps diversos (encryption, file managers, social media, etc.)
- Timeout: 120s por app
- Modelo: qwen3-vl:4b
- Prompt: V10 Simplified

### 1.3 Arquitetura Atual
**Dois grafos diferentes** (causou confusão inicial):

1. **DynamicStateGraph** (`dynamic_state_graph.py`):
   - Estrutura de dados para tracking de exploração
   - Guarda estados visitados e transições
   - NÃO é LangGraph!

2. **LangGraph StateGraph** (framework de orquestração):
   - Orquestra fluxo: observe → assistant → tools → learn
   - Framework LangGraph para coordenação de nós

---

## 2. Decisões Arquiteturais Finalizadas

### 2.1 DECISÃO #1: Detecção de Loops (não Duplicatas)

#### Problema Identificado
Bloquear duplicatas é muito restritivo:
- **Combobox**: `CLICK(dropdown) → CLICK(item1) → CLICK(dropdown) → CLICK(item2)` (duplicata necessária!)
- **Scroll**: `SCROLL(down)` repetido 5x para listas longas
- **Formulários multi-step**: Campos com mesmo nome em diferentes telas

#### Solução: Detectar Loops Baseado em Repetições Consecutivas

```python
def strategy_validation_node(state: AgentState):
    """Detecta LOOPS (repetição excessiva), não duplicatas gerais"""

    llm_action = state['current_action']
    recent_actions = state.get('recent_action_window', [])  # Últimas N ações

    # Conta repetições CONSECUTIVAS da mesma ação
    consecutive_count = 0
    for action in reversed(recent_actions):
        if actions_are_similar(action, llm_action):
            consecutive_count += 1
        else:
            break  # Para quando encontra ação diferente

    # Thresholds por tipo de ação
    MAX_CONSECUTIVE = {
        "TYPE_TEXT": 2,      # Permitir 2x (preencher + corrigir)
        "CLICK": 3,          # Permitir 3x (combobox workflow)
        "SCROLL": 5,         # Permitir 5x (listas longas)
        "SWIPE": 5,
        "BACK": 2,
        "default": 3
    }

    action_type = llm_action.get("action_type", "default")
    threshold = MAX_CONSECUTIVE.get(action_type, MAX_CONSECUTIVE["default"])

    if consecutive_count >= threshold:
        logger.warning(f"⚠️ LOOP detected: {action_type} repeated {consecutive_count}x")

        # Estratégia escolhe ação untested como fallback
        fallback_action = strategy.select_untested_action(screen_hash)

        if fallback_action:
            return {"current_action": fallback_action, "loop_detected": True}
        else:
            # Sem ações untested? Backtrack
            return {"current_action": {"action_type": "BACK"}, "loop_detected": True}

    # Não é loop, continua normalmente
    return {"current_action": llm_action, "loop_detected": False}
```

#### Vantagens
- ✅ Permite repetições legítimas (combobox, scroll)
- ✅ Detecta loops reais (TYPE_TEXT 14x no mesmo campo)
- ✅ Thresholds configuráveis por tipo de ação
- ✅ Não bloqueia exploração válida

#### Exemplo: Resolve Problema do CryptoApp
```
It 5: TYPE_TEXT("Test message") → OK (count=1)
It 6: TYPE_TEXT("Test message") → OK (count=2, threshold=2)
It 7: TYPE_TEXT("Test message") → LOOP! (count=3 > threshold)
      → Fallback: CLICK(GENERATE HASH [M])
```

---

### 2.2 DECISÃO #2: Integração DFS/BFS com LangGraph

#### Arquitetura: Medium Enforcement

```
observe → assistant → strategy_validation → tools → learn
              ↑                                        ↓
              └────────────────────────────────────────┘
```

#### Fluxo de Validação
1. **LLM decide ação** (mantém criatividade)
2. **Estratégia valida** (detecta loops via repetições consecutivas)
3. **Se loop detectado**: Estratégia escolhe fallback (ação untested)
4. **Se sem untested**: Executa BACK (backtracking)
5. **Se válido**: Executa ação da LLM normalmente

#### Integração no LangGraph
```python
graph.add_node("observe", self._observe_node)
graph.add_node("assistant", self._assistant_node)
graph.add_node("strategy_validation", self._strategy_validation_node)  # NOVO!
graph.add_node("tools", ToolNode(self.tools))
graph.add_node("learn", self._learn_node)

# Edges
graph.add_edge("observe", "assistant")
graph.add_edge("assistant", "strategy_validation")  # Valida antes de executar
graph.add_edge("strategy_validation", "tools")
graph.add_edge("tools", "learn")
graph.add_edge("learn", "observe")  # Loop de exploração
```

#### Por que Medium (não Soft ou Hard)?
- **Soft** (LLM livre): Problema atual - loops não são prevenidos
- **Hard** (Estratégia decide): Perde criatividade da LLM
- **Medium** (LLM + validação): ✅ Melhor balanceamento

---

### 2.3 DECISÃO #3: UI Coverage Tracker - Ativação

#### Estado Atual
- ✅ Tracker criado e atualizado
- ❌ Anotações NÃO são usadas no V10 (prompt minimalista)
- ❌ Sugestões não são consultadas

#### Decisão: Reativar Anotações

```python
# OBSERVE NODE
def _observe_node(state: AgentState):
    screen_desc = get_screen_description()
    screen_hash = compute_screen_hash(xml)

    # Anotar com UI Coverage
    annotated_desc = self.ui_coverage.annotate_screen_elements(
        screen_desc,
        screen_hash
    )

    return {
        "screen_description": annotated_desc,  # Com [UNTESTED] markers
        "screen_hash": screen_hash
    }

# LEARN NODE
def _learn_node(state: AgentState):
    action = state["current_action"]
    screen_hash = state["screen_hash"]

    # Registra no UI Coverage
    element_id = extract_element_id(action)
    self.ui_coverage.record_interaction(
        element_id=element_id,
        action_type=action["action_type"],
        screen_hash=screen_hash,
        success=True
    )

    return state
```

#### Ciclo de Anotação
```
It 1: observe (anota [UNTESTED]) → assistant (LLM vê) → tools (clica) → learn (registra)
It 2: observe (anota [TESTED-1x]) → assistant (prioriza outro) → tools → learn
It 3: observe (anota [TESTED-2x]) → assistant (prioriza [UNTESTED]) → tools → learn
```

#### Integração com Estratégias
- Estratégia consulta `ui_coverage.get_untested_actions()` para fallback
- Prioriza elementos com marcador `[UNTESTED]`
- Considera MOP markers (`[DM]`, `[M]`) em conjunto

---

### 2.4 DECISÃO #4: Trace de Sequências - ESTENDER DynamicStateGraph

#### Problema: Duplicação de Conceitos
- ❌ Proposta inicial criava `SimpleNavigationSystem` (duplicava `DynamicStateGraph`)
- ✅ Solução: Estender classe existente

#### Modificação da Classe Transition
```python
@dataclass
class Transition:
    from_hash: str
    to_hash: str
    action_sequence: List[Dict]  # ✅ MUDANÇA: lista ao invés de action_id
    timestamp: float
```

#### Extensão do DynamicStateGraph
```python
class DynamicStateGraph:
    def __init__(self):
        self.states: Dict[str, ScreenNode] = {}
        self.transitions: List[Transition] = []
        self.current_trace: List[Dict] = []  # ✅ NOVO: trace da sessão atual

    def record_action_to_trace(self, action: Dict):
        """Adiciona ação ao trace atual (entre estados)"""
        self.current_trace.append(action)

    def record_transition(self, from_hash: str, to_hash: str, timestamp: float):
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

    def get_transition_graph_report(self) -> Dict:
        """Relatório com sequências completas"""
        return {
            "states": [...],
            "transitions": [
                {
                    "from": t.from_hash,
                    "to": t.to_hash,
                    "action_count": len(t.action_sequence),
                    "actions": t.action_sequence,
                    "timestamp": t.timestamp
                }
                for t in self.transitions
            ]
        }
```

#### Fluxo de Registro
```
It 1: observe (tela A) → assistant → tools (TYPE_TEXT) → learn (adiciona ao trace)
It 2: observe (ainda tela A) → assistant → tools (TYPE_TEXT) → learn (adiciona ao trace)
It 3: observe (ainda tela A) → assistant → tools (CLICK submit) → learn (adiciona ao trace)
It 4: observe (mudou para tela B!) → registra transição com 3 ações → reset trace
```

#### Exemplo de Transição Completa
```python
Transition(
    from_hash="a1b2c3d4e5f6",
    to_hash="d4e5f6a7b8c9",
    action_sequence=[
        {"action_type": "TYPE_TEXT", "text": "user@test.com"},
        {"action_type": "TYPE_TEXT", "text": "password123"},
        {"action_type": "CLICK", "description": "Submit button"}
    ],
    timestamp=1699123456.789
)
```

#### Vantagens
- ✅ **Não duplica**: usa estrutura existente
- ✅ **Backward compatible**: só adiciona campos/métodos
- ✅ **Simples**: < 30 linhas de código
- ✅ **Trace completo**: guarda sequências para análise
- ✅ **Relatório rico**: exporta grafo com todas as ações

---

### 2.5 DECISÃO #5: Backtracking - BACK Puro (Simplicidade)

#### Abordagens Avaliadas
1. **Back Button Simples** ✅ ESCOLHIDA
2. **Restart + Replay** (descartada: complexa)
3. **Sistema Híbrido** (descartada: complexidade desnecessária)

#### Solução: BACK Puro
```python
def backtrack(self, steps=1):
    """Backtracking SIMPLES: apenas BACK"""
    for _ in range(steps):
        self.device.press_back()
        time.sleep(0.5)
```

#### Justificativa
- ✅ **Simplicidade e elegância** (princípio core do projeto)
- ✅ BACK funciona na maioria dos casos
- ✅ Sistema já tem fallback de reiniciar app (3 navegações externas → restart)
- ✅ Trace completo guardado para análise/debugging (mesmo sem replay)

#### Trade-off Aceito
- ⚠️ BACK pode não chegar exatamente no estado desejado
- ⚠️ BACK pode sair do app ou fechar dialogs inesperadamente
- ✅ Mas é **rápido** e **simples** - alinhado com filosofia do projeto

#### Fallback Existente
Sistema já implementado em `rv_agent.py`:
- Detecta quando app sai da tela 3 vezes consecutivas
- Força restart do app automaticamente
- Continua exploração do zero (mas com grafo já construído)

---

### 2.6 DECISÃO #6: WTG (Window Transition Graph) - NÃO Integrar no MVP

#### Estado Atual
- ✅ `WTGMapper` existe no código
- ❌ Usado apenas em framework de validação
- ❌ NÃO integrado em runtime
- ❌ NÃO aparece nos prompts

#### Decisão: Postergar para Versão Futura

#### Justificativa
1. **MOP markers suficientes**: `[DM]`/`[M]` já fornecem guidance
2. **V10 é minimalista**: Projetado para modelos pequenos (qwen3-vl:4b)
3. **Adiciona complexidade ao prompt**: Mais tokens, mais processamento
4. **Pode ser adicionado depois**: Para modelos maiores (8b, 14b+)

#### Quando Reintroduzir
- Modelos maiores com capacidade de contexto estendido
- Versões futuras focadas em navegação guiada
- Integração com estratégias mais sofisticadas (path planning)

---

### 2.7 DECISÃO #7: Histórico de Ações - Manter Infraestrutura

#### Estado Atual
- ✅ `AgentMemoryManager` guarda últimas 5 ações
- ❌ V10 usa apenas última ação (minimalismo)

#### Decisão: Manter Como Está

#### Justificativa
1. **V10 é minimalista**: Token efficiency para modelos pequenos
2. **Infraestrutura já existe**: Pronta para versões futuras
3. **Não prejudica**: Manter código não usado não afeta performance
4. **Fácil ativar depois**: Apenas modificar `v10.py` para incluir histórico completo

#### Quando Ativar
- Versões com modelos maiores (contexto de 64K+)
- Testes com prompts mais ricos
- Comparação A/B entre histórico completo vs última ação

---

## 3. Arquitetura Final Proposta

### 3.1 Fluxo LangGraph Completo

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

### 3.2 Componentes e Responsabilidades

#### DynamicStateGraph (Tracking)
- Guarda estados visitados (`ScreenNode`)
- Guarda transições com sequências completas (`Transition`)
- Acumula trace de ações entre estados (`current_trace`)
- Calcula cobertura por estado
- Gera relatório final com grafo completo

#### DFSStrategy / BFSStrategy (Guidance)
- Consulta `DynamicStateGraph` para estados visitados
- Fornece ações prioritárias (untested + MOP markers)
- Escolhe fallback quando loop detectado
- Sugere backtracking quando estado esgotado

#### UICoverageTracker (Element-level)
- Rastreia elementos testados por tela
- Anota descrição com `[UNTESTED]`/`[TESTED-Nx]`
- Fornece sugestões de exploração
- Calcula cobertura de elementos

#### AgentMemoryManager (Summaries)
- Gera strings pré-formatadas para LLM
- Histórico de últimas 5 ações
- Navegação entre activities
- Insights de exploração

#### LangGraph StateGraph (Orchestration)
- Coordena fluxo de nós
- Gerencia estado entre iterações
- Implementa retry logic
- Controla timeout e finalização

---

## 4. Estrutura de Dados

### 4.1 AgentState (LangGraph)
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

    # Iteration control
    iteration: int
    external_navigation_count: int
```

### 4.2 ScreenNode (DynamicStateGraph)
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

### 4.3 Transition (DynamicStateGraph)
```python
@dataclass
class Transition:
    from_hash: str                  # Estado origem
    to_hash: str                    # Estado destino
    action_sequence: List[Dict]     # TODAS as ações que levaram à transição
    timestamp: float                # Quando aconteceu
```

---

## 5. Exemplos de Fluxo

### 5.1 Exploração Normal (Sem Loop)

```
It 1 (Tela Login):
  OBSERVE:
    - screen_hash: "a1b2c3d4e5f6"
    - Anota: "1. [UNTESTED] EditText 'Email'"
    - current_trace: []

  ASSISTANT:
    - LLM vê [UNTESTED]
    - Decide: TYPE_TEXT(email_field, "user@test.com")

  STRATEGY_VALIDATION:
    - recent_window: []
    - consecutive_count: 0
    - Resultado: VALID (não é loop)

  TOOLS:
    - Executa TYPE_TEXT

  LEARN:
    - Adiciona ao trace: [TYPE_TEXT...]
    - Registra em UI coverage: email_field → 1x
    - current_trace: [TYPE_TEXT...]

It 2 (Ainda Login):
  OBSERVE:
    - screen_hash: "a1b2c3d4e5f6" (mesmo!)
    - Anota: "1. [TESTED-1x] EditText 'Email'"
              "2. [UNTESTED] EditText 'Password'"
    - NO_TRANSITION (hash não mudou)

  ASSISTANT:
    - LLM vê [UNTESTED] em password
    - Decide: TYPE_TEXT(password_field, "123")

  STRATEGY_VALIDATION:
    - recent_window: [TYPE_TEXT(email)]
    - consecutive_count: 0 (ação diferente)
    - Resultado: VALID

  TOOLS:
    - Executa TYPE_TEXT(password)

  LEARN:
    - current_trace: [TYPE_TEXT(email), TYPE_TEXT(password)]

It 3 (Ainda Login):
  ASSISTANT:
    - Decide: CLICK(submit_button)

  TOOLS:
    - Executa CLICK

  LEARN:
    - current_trace: [TYPE_TEXT(email), TYPE_TEXT(password), CLICK(submit)]

It 4 (Mudou para Home!):
  OBSERVE:
    - screen_hash: "d4e5f6a7b8c9" (DIFERENTE!)
    - TRANSITION DETECTED!
    - Registra: Transition(
        from="a1b2c3d4e5f6",
        to="d4e5f6a7b8c9",
        action_sequence=[TYPE_TEXT(email), TYPE_TEXT(password), CLICK(submit)]
      )
    - Reset: current_trace = []
```

### 5.2 Detecção de Loop (CryptoApp Scenario)

```
It 5 (MessageDigest screen):
  ASSISTANT:
    - Decide: TYPE_TEXT(input_field, "Test message")

  STRATEGY_VALIDATION:
    - recent_window: []
    - consecutive_count: 0
    - Resultado: VALID

  TOOLS:
    - Executa TYPE_TEXT

It 6:
  ASSISTANT:
    - Decide: TYPE_TEXT(input_field, "Test message")  # Mesma ação!

  STRATEGY_VALIDATION:
    - recent_window: [TYPE_TEXT("Test message")]
    - consecutive_count: 1 (mesmo texto, mesmo campo)
    - Threshold: MAX_CONSECUTIVE["TYPE_TEXT"] = 2
    - Resultado: VALID (ainda dentro do threshold)

  TOOLS:
    - Executa TYPE_TEXT

It 7:
  ASSISTANT:
    - Decide: TYPE_TEXT(input_field, "Test message")  # De novo!

  STRATEGY_VALIDATION:
    - recent_window: [TYPE_TEXT("Test"), TYPE_TEXT("Test")]
    - consecutive_count: 2
    - Threshold: 2
    - Resultado: LOOP DETECTED! ❌
    - Fallback: strategy.select_untested_action()
    - Retorna: CLICK(GENERATE_HASH_button) [M]

  TOOLS:
    - Executa CLICK (fallback, não a ação da LLM)

  LEARN:
    - Log: "⚠️ Loop detected, used strategy fallback"
```

---

## 6. Mudanças Necessárias no Código

### 6.1 Arquivo: `dynamic_state_graph.py`

#### Modificações na Classe Transition
```python
@dataclass
class Transition:
    from_hash: str
    to_hash: str
    action_sequence: List[Dict]  # MUDANÇA: era action_id: int
    timestamp: float
```

#### Adições na Classe DynamicStateGraph
```python
class DynamicStateGraph:
    def __init__(self):
        self.states: Dict[str, ScreenNode] = {}
        self.transitions: List[Transition] = []
        self.current_trace: List[Dict] = []  # NOVO

    def record_action_to_trace(self, action: Dict):  # NOVO
        """Adiciona ação ao trace atual"""
        self.current_trace.append(action)

    def record_transition(self, from_hash, to_hash, timestamp):  # MODIFICADO
        """Registra transição com trace completo"""
        self.transitions.append(
            Transition(
                from_hash=from_hash,
                to_hash=to_hash,
                action_sequence=self.current_trace.copy(),
                timestamp=timestamp
            )
        )
        self.current_trace = []  # Reset

    def get_transition_graph_report(self) -> Dict:  # NOVO
        """Exporta grafo completo com sequências"""
        return {...}
```

**Estimativa**: ~30 linhas de código modificadas/adicionadas

---

### 6.2 Arquivo: `rv_agent.py`

#### Novo Nó: Strategy Validation
```python
def _strategy_validation_node(self, state: AgentState) -> AgentState:
    """
    Valida ação da LLM contra estratégia para detectar loops.
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

    if consecutive_count >= threshold:
        logger.warning(f"⚠️ LOOP: {action_type} repeated {consecutive_count}x")

        # Fallback: estratégia escolhe ação untested
        fallback = self.strategy.select_untested_action(
            screen_hash,
            self.dynamic_graph
        )

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
```

#### Modificação: Observe Node (Detecção de Transição)
```python
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
```

#### Modificação: Learn Node (Registro de Trace)
```python
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
```

#### Modificação: Build Agent Graph
```python
def _build_agent_graph(self):
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("observe", self._observe_node)
    graph.add_node("assistant", self._assistant_node)
    graph.add_node("strategy_validation", self._strategy_validation_node)  # NOVO!
    graph.add_node("tools", ToolNode(self.tools))
    graph.add_node("learn", self._learn_node)

    # Edges
    graph.set_entry_point("observe")
    graph.add_edge("observe", "assistant")
    graph.add_edge("assistant", "strategy_validation")  # NOVO!
    graph.add_edge("strategy_validation", "tools")      # NOVO!
    graph.add_edge("tools", "learn")

    # Conditional edge: continua ou termina?
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

**Estimativa**: ~150 linhas de código adicionadas/modificadas

---

### 6.3 Arquivo: `dfs_strategy.py`

#### Novo Método: Select Untested Action
```python
def select_untested_action(
    self,
    screen_hash: str,
    dynamic_graph: DynamicStateGraph
) -> Optional[Dict]:
    """
    Seleciona próxima ação untested no estado atual.
    Prioriza ações com MOP markers.

    Returns:
        Ação untested de maior prioridade, ou None se não houver
    """
    if screen_hash not in dynamic_graph.states:
        return None

    node = dynamic_graph.states[screen_hash]

    # Pega todas as ações disponíveis
    all_actions = self._get_all_actions_for_screen(screen_hash)

    # Filtra untested
    untested = [
        action for action in all_actions
        if action.id not in node.executed_actions
    ]

    if not untested:
        return None

    # Prioriza por MOP markers
    priority_sorted = sorted(
        untested,
        key=lambda a: self._get_mop_priority(a),
        reverse=True
    )

    # Retorna top priority
    top_action = priority_sorted[0]

    return {
        "action_type": "CLICK",  # Assume click por enquanto
        "x": top_action.bounds[0],
        "y": top_action.bounds[1],
        "description": top_action.text or top_action.class_name,
        "id": top_action.id
    }
```

**Estimativa**: ~40 linhas de código adicionadas

---

### 6.4 Arquivo: `state.py` (AgentState)

#### Adição de Campos
```python
class AgentState(TypedDict):
    # ... campos existentes ...

    # NOVOS CAMPOS
    recent_action_window: List[Dict]  # Para detecção de loops
    loop_detected: bool               # Flag de loop
    used_fallback: bool               # Flag de fallback usado
    last_screen_hash: Optional[str]   # Para detectar transições
```

**Estimativa**: 4 linhas adicionadas

---

## 7. Métricas de Sucesso

### 7.1 Objetivo Primário: Eliminar Loops
- ✅ **Zero loops com >5 repetições consecutivas**
- ✅ **TYPE_TEXT bloqueado após 2 repetições consecutivas**
- ✅ **Fallback automático para ações untested**

### 7.2 Objetivo Secundário: Exploração Sistemática
- ✅ **>10 unique states em 120s** (baseline atual: 3)
- ✅ **>15 transitions em 120s** (baseline atual: 0)
- ✅ **Cobertura >30% por tela visitada**

### 7.3 Objetivo Terciário: Simplicidade
- ✅ **Mudanças < 250 linhas de código**
- ✅ **Sem duplicação de conceitos**
- ✅ **Código legível e manutenível**

### 7.4 Comparação com Baseline

| Métrica | Baseline V10 | Esperado Pós-Mudanças | Melhoria |
|---------|-------------|----------------------|----------|
| Unique States (120s) | 3 | 10-15 | 3-5x |
| Transitions (120s) | 0 | 15-25 | ∞ (de 0!) |
| Loops >5 reps | 1 (TYPE_TEXT 14x) | 0 | ✅ Eliminado |
| Revisit Rate | 70%+ | 30-40% | -50% |
| Coverage/Screen | ~20% | 40-60% | 2-3x |
| MOP Trigger Rate | 0% | 40-60% | ∞ |

---

## 8. Estimativa de Complexidade

### 8.1 Linhas de Código
- **DynamicStateGraph**: ~30 linhas (extensão)
- **RVAgent**: ~150 linhas (validação + modificações)
- **DFSStrategy**: ~40 linhas (select_untested_action)
- **AgentState**: ~4 linhas (novos campos)
- **Total**: ~224 linhas ✅ Dentro do objetivo (<250)

### 8.2 Tempo de Implementação
- **Fase 1** (DynamicStateGraph): 1h
- **Fase 2** (Strategy validation node): 2h
- **Fase 3** (LangGraph modifications): 1.5h
- **Fase 4** (UI Coverage activation): 1h
- **Fase 5** (DFS integration): 1h
- **Fase 6** (Testes): 2h
- **Total**: ~8.5h de trabalho

### 8.3 Risco de Regressão
- ✅ **Baixo**: Mudanças são aditivas (não removem funcionalidade)
- ✅ **Backward compatible**: Campos novos têm defaults
- ✅ **Testável**: Pode comparar diretamente com baseline

---

## 9. Próximos Passos (NÃO IMPLEMENTAR AINDA)

### 9.1 Após Baseline Completar
1. Analisar resultados de `test_v10_baseline_10apps.py`
2. Documentar métricas atuais
3. Criar branch para desenvolvimento

### 9.2 Implementação Incremental
1. Implementar Fase 1 (DynamicStateGraph)
2. Testar isoladamente
3. Implementar Fase 2 (Strategy validation)
4. Testar com 1 app
5. Continuar fases incrementalmente

### 9.3 Validação
1. Re-executar teste baseline com mudanças
2. Comparar métricas lado a lado
3. Validar eliminação de loops
4. Gerar relatório de transições

---

## 10. Trade-offs Documentados

### 10.1 Thresholds Fixos vs Adaptativos
- ✅ **Escolhido**: Fixos (TYPE_TEXT=2, CLICK=3, etc.)
- ❌ **Descartado**: Adaptativos baseados em aprendizado
- **Razão**: Simplicidade, pode ser ajustado depois se necessário

### 10.2 BACK Puro vs Replay
- ✅ **Escolhido**: BACK puro
- ❌ **Descartado**: Restart + Replay
- **Razão**: Simplicidade e elegância, mesmo com imprecisão ocasional

### 10.3 WTG Guidance
- ✅ **Escolhido**: Não integrar no MVP
- ❌ **Descartado**: Integração completa
- **Razão**: MOP markers suficientes, V10 minimalista

### 10.4 UI Coverage Annotations
- ✅ **Escolhido**: Ativar anotações
- ❌ **Não ativado**: Sugestões automáticas (get_exploration_suggestions)
- **Razão**: Anotações são passivas, sugestões adicionam complexidade

---

## 11. Questões em Aberto (Discussão Futura)

### 11.1 Thresholds Ótimos
- TYPE_TEXT: 2 é suficiente? Ou permitir 3?
- SCROLL: 5 é muito? Apps com listas infinitas?

### 11.2 Fallback Strategy
- Priorizar sempre MOP markers?
- Ou balancear com coverage de elementos?

### 11.3 Performance
- Anotações adicionam latência significativa?
- Validação de loops impacta tempo/iteração?

### 11.4 Extensibilidade
- Como adicionar novas estratégias (e.g., Random, Hybrid)?
- Como alternar DFS/BFS dinamicamente?

---

## 12. Referências

### 12.1 Conversas Anteriores
- `20251103_rvagent_pre_plano_v2.md`: Decisões iniciais e validações
- `20251031_rvagent_plan_final.md`: Planejamento anterior

### 12.2 Código Base
- `modules/rv-agent/src/rv_agent/core/rv_agent.py`: Agente principal
- `modules/rv-agent/src/rv_agent/core/dynamic_state_graph.py`: Grafo de estados
- `modules/rv-agent/src/rv_agent/strategies/dfs_strategy.py`: Estratégia DFS

### 12.3 Testes
- `modules/rv-agent/test_v10_baseline_10apps.py`: Baseline atual
- APKs: `/pedro/desenvolvimento/.../rv-android/apks/`

---

## 13. Resumo Executivo

### Problema
Loop infinito (TYPE_TEXT 14x) causado por falta de enforcement de estratégias DFS/BFS.

### Solução
Adicionar nó de validação no LangGraph que detecta loops (repetições consecutivas) e usa estratégia como fallback.

### Benefícios
- ✅ Elimina loops infinitos
- ✅ Exploração sistemática (DFS/BFS)
- ✅ Mantém criatividade da LLM
- ✅ Simples e elegante (<250 linhas)

### Riscos
- ⚠️ Thresholds podem precisar ajuste
- ⚠️ BACK puro pode não funcionar sempre
- ✅ Mitigação: fallback de restart já existe

### Timeline
- **Implementação**: 8-10 horas
- **Testes**: 2-4 horas
- **Total**: 1-2 dias de trabalho

---

**FIM DO DOCUMENTO v3**

**Status**: Decisões finalizadas, aguardando baseline e aprovação para implementação

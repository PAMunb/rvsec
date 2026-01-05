# RVAgent - Pré-Plano: Estratégias de Exploração DFS/BFS

**Data:** 2025-11-03
**Contexto:** Teste real revelou loops infinitos. Pesquisa revelou que DFS/BFS existem mas não são usados.

---

## 📊 RESUMO EXECUTIVO

### Situação Atual
- ✅ **Screenshot optimizer:** FUNCIONANDO (55-64% redução, bug corrigido)
- ✅ **Coordinate conversion:** FUNCIONANDO (opt↔dev conversão)
- ✅ **Tool calling:** FUNCIONANDO (LLM gera tool calls)
- ❌ **Exploração:** LOOPS INFINITOS (14x mesma ação)

### Descoberta Crítica
**Estratégias DFS/BFS já existem mas NUNCA são chamadas!**

Arquivos encontrados:
- `strategies/dfs_strategy.py` - DFS completo com backtracking
- `strategies/bfs_strategy.py` - BFS com queue
- `memory/dynamic_state_graph.py` - Grafo rastreia estados e ações
- **Problema:** Zero integração! LLM decide sozinha sem consultar estratégia

### Impacto do Problema
```
Teste Real (CryptoApp, 120s):
- Iterações 0-4: ✅ Exploração funcional
- Iterações 5-18: ❌ LOOP (14x TYPE_TEXT "Test message")
- Botão "GENERATE HASH" [M] disponível desde It 4
- NUNCA clicou, ficou preso por 90+ segundos
```

---

## 🔬 ANÁLISE DETALHADA DO TESTE REAL

### Teste Executado
```bash
poetry run python test_real_emulator.py --app cryptoapp --timeout 120
```

**Configuração:**
- Device: emulator-5554 (real Android emulator)
- App: CryptoApp (br.unb.cic.cryptoapp)
- Timeout: 120 segundos (ÚNICO controle - max_iterations IGNORADO!)
- Strategy config: "dfs" (mas não usado)

### Cronologia Completa

**Iteração 0 (6.4s):** ✅ Clicou "MESSAGE DIGEST"
- LLM: android_click("MESSAGE DIGEST", 364, 183)
- Conversão: opt(364,183) → dev(540,272)
- Screenshot: 121KB → 54KB (55.7% redução)
- Status: SUCCESS

**Iteração 1 (15.8s):** ✅ Clicou Spinner (abrir dropdown)
- LLM detectou: 1 text input, 1 spinner
- Prompt incluiu: "⚠️ IMPORTANT: Use android_type_text() for EditText"
- LLM: android_click("Spinner Select algorithm", 364, 195)
- Screenshot: 122KB → 44KB (63.7% redução)
- Status: SUCCESS

**Iteração 2 (21.0s):** ✅ Dropdown abriu
- UI elements: 22 items (dropdown options visíveis)
- LLM: android_click("Spinner Select algorithm", 364, 195) [tentou abrir de novo]
- Status: SUCCESS (já estava aberto)

**Iteração 3 (24.7s):** ⚠️ Sem tool calls!
- LLM Response: 17 tokens apenas
- Sem XML/JSON de tool calls detectado
- Status: SKIPPED (retry)

**Iteração 4 (28.1s):** ✅ Selecionou SHA-256
- LLM: android_click("SHA-256", 293, 569)
- Conversão: opt(293,569) → dev(434,848)
- Status: SUCCESS

**Iteração 5 (34.6s):** ✅ Primeira TYPE_TEXT
- LLM detectou EditText corretamente
- LLM: android_type_text("Input text field", 364, 256, "Test message")
- Status: SUCCESS
- **PROBLEMA COMEÇA AQUI!**

**Iterações 6-18 (38s-95s):** ❌ LOOP INFINITO!
```
It  6: android_type_text("EditText 'Test message'", 364, 256, "Test message")
It  7: [Sem tool calls - retry]
It  8: android_type_text("EditText 'Test message'", 364, 256, "Test message")
It  9: [Sem tool calls - retry]
It 10: android_type_text("EditText 'Test message'", 364, 256, "Test message")
It 11: android_type_text("EditText 'Test message'", 364, 256, "Test message")
It 12: android_type_text("EditText 'Test message'", 364, 256, "Test message")
It 13: android_type_text("EditText 'Test message'", 364, 256, "Test message")
It 14: [Sem tool calls - retry]
It 15: android_type_text("EditText 'Test message'", 364, 256, "Test message")
It 16: [Sem tool calls - retry]
It 17: android_type_text("EditText 'Test message'", 364, 256, "Test message")
It 18: android_type_text("EditText 'Test message'", 364, 256, "Test message")
```

**Iteração 19-21:** Continuou loop até timeout (120s)

### Elementos Disponíveis Durante o Loop

**Desde Iteração 5, a tela tinha:**
```xml
=== TEXT INPUT FIELDS ===
1. EditText 'Test message' at (364, 256) - JÁ PREENCHIDO!

=== DROPDOWN SELECTORS ===
1. Spinner (spinnerMessageDigest) at (364, 195) - SHA-256 JÁ SELECIONADO!

=== CLICKABLE ELEMENTS ===
1. ImageView (back) at (153, 1245)
2. ImageView (recent_apps) at (573, 1245)
3. ImageView (home_button) at (364, 1245)
4. Button 'GENERATE HASH' at (364, 338) ← NUNCA CLICADO! ❌
```

**Observações:**
1. Botão "GENERATE HASH" tem marcação [M] (MOP-marked) - ALTA PRIORIDADE!
2. EditText já continha "Test message" desde It 5
3. Spinner já tinha SHA-256 selecionado desde It 4
4. Formulário COMPLETO, pronto para submit
5. LLM repetiu TYPE_TEXT **14 VEZES** no mesmo campo preenchido

### Root Cause Analysis

**Por que LLM ficou preso?**

1. **Sem detecção de estado visitado:**
   - Screen hash: `81d640c95c72...` visitado 14+ vezes
   - Nenhum alerta para LLM: "você já está nesta tela há 10 iterações"

2. **Sem detecção de ação repetida:**
   - `android_type_text(364, 256, "Test message")` executado 14+ vezes
   - Nenhuma validação: "você já digitou isso 5x, tente outra ação"

3. **Sem estratégia de exploração:**
   - DFS diria: "Botão GENERATE HASH [M] não-testado - PRIORIDADE ALTA!"
   - Mas estratégia nunca foi consultada

4. **Sem backtracking:**
   - Quando stuck, não sabe que deve fazer BACK ou HOME
   - Fica repetindo mesma ação indefinidamente

5. **Prompt inadequado para loops:**
   - Few-shot examples mostram sequências corretas
   - Mas não ensinam: "se já preencheu campo, NÃO preencha de novo"
   - Regra "Pre-Submit Validation" não foi seguida

### Métricas do Teste

**Exploração:**
- Unique screens: 3 (baixo!)
- Activities: 2 (MainActivity, MessageDigestActivity)
- Revisit rate: 70%+ (muito alto! indica loop)

**Ações:**
- Total: ~22 iterations
- Valid: ~18 (TYPE_TEXT repetidos contam como "valid")
- Invalid: ~4 (tentativas sem tool calls)
- TYPE_TEXT: 14+ (TODAS no mesmo campo!)
- CLICK: 4 (MESSAGE DIGEST, Spinner, SHA-256, Spinner novamente)
- Botão GENERATE HASH: 0 clicks ❌

**LLM Usage:**
- Avg tokens/iteration: ~4,600 tokens
- Total: ~100k tokens
- Avg time/iteration: ~2,500ms
- Screenshot size: 44-66KB (otimizado ✅)

**Comparação com Offline Validation (5 iterações):**
- Offline tinha: 3 unique screens, 60% valid rate, 1 TYPE_TEXT
- Real device: 3 unique screens, 80%+ valid rate (falso!), 14+ TYPE_TEXT

---

## 🏗️ DESCOBERTAS ARQUITETURAIS

### Arquivos Encontrados

#### 1. Estratégias (IMPLEMENTADAS mas NÃO USADAS!)

**`strategies/base_strategy.py`:**
```python
class BaseStrategy(ABC):
    @abstractmethod
    def get_guidance(self, current_hash: str, screen_desc: ScreenDescription) -> Dict[str, Any]:
        """Return exploration guidance for current screen"""
        pass

    @abstractmethod
    def record_transition(self, from_hash: str, to_hash: str):
        """Record state transition for strategy tracking"""
        pass
```

**`strategies/dfs_strategy.py`:**
- **Prioritização MOP:**
  - [DM] (directly_reaches_mop): Prioridade 3
  - [M] (reaches_mop): Prioridade 2
  - Sem marcação: Prioridade 1

- **Guidance retornado:**
  ```python
  {
      'exploration_focus': 'DEEPEN' | 'BACKTRACK',
      'untested_count': int,
      'priority_actions': List[str],  # Textos descritivos
      'coverage': float
  }
  ```

- **Lógica:**
  - Se `untested_count > 0` → DEEPEN (explorar ações não-testadas)
  - Se `untested_count == 0` → BACKTRACK (voltar para estado anterior)

- **PROBLEMA:** Método `get_guidance()` retorna texto descritivo, não ação executável!

**`strategies/bfs_strategy.py`:**
- **Mantém queue:** `Deque[str]` de screen hashes
- **Adiciona vizinhos:** Quando visita tela nova, adiciona à fila
- **Lógica BFS:** Esgotar nível atual antes de ir para próximo
- **PROBLEMA:** Queue nunca é usada para navegação!

#### 2. Grafo Dinâmico (BEM PROJETADO!)

**`memory/dynamic_state_graph.py`:**
```python
class ScreenNode:
    screen_hash: str           # Hash estrutural (12 chars)
    visit_count: int           # Quantas vezes visitou
    total_actions: int         # Total de ações disponíveis na tela
    executed_actions: Set[int] # IDs de ações já executadas
    first_visit: float         # Timestamp primeira visita

    def get_coverage(self) -> float:
        return len(self.executed_actions) / self.total_actions if self.total_actions > 0 else 0.0

    def get_untested_actions(self, all_actions: List) -> List:
        return [a for a in all_actions if a.id not in self.executed_actions]
```

**Funcionalidades:**
- `get_or_create_state(hash)`: Retorna nó, cria se não existe
- `record_action(hash, action_id)`: Adiciona action_id ao set executed_actions
- `get_untested_actions(hash)`: Retorna ações não em executed_actions
- `compute_coverage()`: Cobertura global = média das coberturas por tela

**PROBLEMA:** Grafo rastreia tudo mas nada FORÇA decisões!

#### 3. Memórias (RASTREIAM mas NÃO PREVINEM)

**`memory/long_term.py`:**
- Rastreia estados, ações, transições cross-session
- Oferece `get_state_guidance()`: ações bem-sucedidas nesta tela antes
- **NÃO usado para:** Bloquear ações duplicadas

**`memory/short_term.py`:**
- Últimas 5 iterações (scope: tela atual)
- Limpa ao trocar activity
- Formato compacto: "CLICK: android.widget.Button"
- **NÃO usado para:** Detecção de loops

**`memory/ui_coverage.py`:**
- Contador por elemento: `tested_elements[element_id] = count`
- Anotações: [UNTESTED], [TESTED-1x], [WELL-TESTED]
- Prioridades: high (0x), medium (1-2x), low (3+x)
- **NÃO enforçado:** LLM pode clicar 100x no mesmo elemento

**`memory/agent_memory.py`:**
- Manager stateless: gera strings para prompt LLM
- Seções: Action History, Exploration Status, Memory Insights, Navigation Path
- **Só para contexto:** LLM pode ignorar completamente

#### 4. Integração Atual (FALTANDO!)

**`rv_agent.py` linhas 121-128:**
```python
# Strategy é CRIADA mas NUNCA CHAMADA!
if config.strategy == "dfs":
    self.strategy = DFSStrategy(self.dynamic_graph, static_data)
elif config.strategy == "bfs":
    self.strategy = BFSStrategy(self.dynamic_graph, static_data)
else:
    self.strategy = None
```

**Onde DEVERIA ser chamada (mas não é):**
1. `_observe_node()`: Após capturar tela → `strategy.get_guidance()`
2. `_build_stateless_message()`: Incluir guidance no prompt
3. `_execute_tools_node()`: Validar ação contra `executed_actions`
4. `_handle_max_retries_node()`: Fallback para `strategy.select_next_action()`

**Atualmente:**
- Estratégia existe como objeto em memória
- Grafo é atualizado com transições
- **MAS:** Nenhuma consulta, nenhum enforcement, nenhum fallback

#### 5. Referência: DroidBot

**`rv-tools/builtin/droidbot/tool.py`:**
- Implementa DFS/BFS **puro** (sem LLM)
- Policies: `dfs_naive`, `dfs_greedy`, `bfs_naive`, `bfs_greedy`
- Usa grafo de UI states para decisão algorítmica
- **Diferença:** Sem visão multimodal, só XML parsing

**Lições do DroidBot:**
- DFS/BFS funcionam bem para cobertura sistemática
- Backtracking automático quando tela esgotada
- Loop detection via visited states
- **Limitação:** Sem entendimento semântico (não usa LLM)

---

## 🎯 PROBLEMA IDENTIFICADO

### Diagnóstico

**Sintoma:** LLM repete mesma ação infinitamente

**Causas Raiz:**
1. **Ausência de enforcement:** Estratégias são passivas (soft guidance)
2. **Zero validação:** Ações duplicadas não são bloqueadas
3. **Sem fallback:** Quando LLM falha, nada assume controle
4. **Prompt inadequado:** Few-shots não cobrem cenário de loop

**Consequências:**
- Baixa cobertura (fica preso em loops)
- Desperdício de tempo (90s repetindo ação)
- Desperdício de tokens (100k tokens para 3 telas)
- Frustração: vemos LLM ignorar botões [M] óbvios

### Por Que Estratégias Não Foram Integradas?

**Hipótese 1: Desenvolvimento incremental**
- Primeiro: Implementou LLM pura (proof of concept)
- Depois: Criou estratégias mas não finalizou integração
- Resultado: Estratégias ficaram "órfãs"

**Hipótese 2: Arquitetura stateless**
- Mudança de stateful → stateless (v6, v7, v8, v9)
- Estratégias foram criadas em versão stateful
- Migração não incluiu hooks para estratégias

**Evidência:**
- Estratégias usam `dynamic_graph` (stateless)
- Mas nenhum node do LangGraph chama estratégias
- Workflow: observe → assistant → tools → validate → update → learn
- Estratégia não está em nenhum desses nodes!

---

## 💡 SOLUÇÕES PROPOSTAS

### Abordagem Geral: Híbrido LLM + Estratégia

**Princípio:**
Combinar criatividade do LLM com sistematicidade do algoritmo

**Componentes:**
1. **Guidance (Soft):** LLM recebe sugestões da estratégia no prompt
2. **Validation (Medium):** Bloquear ações claramente duplicadas
3. **Fallback (Hard):** Quando LLM falha, estratégia assume controle
4. **Pure Mode (Baseline):** Estratégia pura para comparação

---

### FASE 1: Ativar Guidance (Quick Win)

**Objetivo:** Fazer estratégias fornecerem guidance para LLM

**Mudanças:**

**1.1 Modificar `_observe_node()` (após linha 299):**
```python
def _observe_node(self, state: AgentState) -> AgentState:
    # ... existing observation code ...
    screen_hash = self._compute_screen_hash(ui_state)

    # 🆕 GET STRATEGY GUIDANCE
    if self.strategy:
        strategy_guidance = self.strategy.get_guidance(
            current_hash=screen_hash,
            screen_desc=screen_description
        )
    else:
        strategy_guidance = None

    return {
        # ... existing returns ...
        "strategy_guidance": strategy_guidance,  # 🆕
    }
```

**1.2 Incluir guidance no prompt `_build_stateless_message()`:**
```python
# Após seção "# Memory Insights"
if state.get('strategy_guidance'):
    guidance = state['strategy_guidance']
    context_parts.append("")
    context_parts.append("# Exploration Strategy Guidance")
    context_parts.append(f"Strategy: {self.config.strategy.upper()}")
    context_parts.append(f"Focus: {guidance['exploration_focus']}")
    context_parts.append(f"Untested actions in current screen: {guidance['untested_count']}")

    if guidance['priority_actions']:
        context_parts.append("Recommended high-priority actions:")
        for i, action_text in enumerate(guidance['priority_actions'][:3], 1):
            context_parts.append(f"  {i}. {action_text}")

    context_parts.append("")
```

**1.3 Registrar action_id no grafo `_update_memories_node()`:**
```python
def _update_memories_node(self, state: AgentState) -> AgentState:
    # ... existing code ...

    # 🆕 Record action in dynamic graph
    current_tool_call = state.get('current_tool_call', {})
    if current_tool_call:
        # Extract action coordinates
        args = current_tool_call.get('args', {})
        coords = (args.get('x', 0), args.get('y', 0))

        # Find matching screen item by coords
        screen_desc = state.get('screen_description', {})
        screen_item = self._find_item_by_coords(coords, screen_desc)

        if screen_item and screen_item.actions:
            action_id = screen_item.actions[0].id
            self.dynamic_graph.record_action(
                screen_hash=state['current_screen_hash'],
                action_id=action_id
            )
            logger.debug(f"Recorded action {action_id} in graph for screen {state['current_screen_hash'][:8]}")
```

**Resultado Esperado:**
- LLM vê no prompt: "Untested actions: 5, Priority: GENERATE HASH button [M]"
- Pode seguir ou ignorar (soft guidance)
- Grafo rastreia quais ações foram executadas

**Riscos:**
- LLM pode continuar ignorando guidance
- Sem enforcement, loops podem persistir

**Teste:**
```bash
poetry run python test_real_emulator.py --app cryptoapp --timeout 60
```
Verificar se LLM clica em GENERATE HASH após ver guidance.

---

### FASE 2: Validação + Fallback (Critical)

**Objetivo:** Bloquear loops + fallback algorítmico

**Mudanças:**

**2.1 Validação de ação duplicada:**

Opção A: No `_execute_tools_node()` (antes de executar):
```python
def _execute_tools_node(self, state: AgentState) -> AgentState:
    tool_calls = state.get('tool_calls', [])

    for tool_call in tool_calls:
        # 🆕 Check if action already executed
        if self._is_action_duplicate(tool_call, state):
            logger.warning(f"⚠️ Action duplicate detected, skipping: {tool_call['name']}")
            continue  # Skip to next tool call

        # ... existing execution code ...

def _is_action_duplicate(self, tool_call: Dict, state: AgentState) -> bool:
    """Check if action was already executed on current screen"""
    screen_hash = state.get('current_screen_hash')
    if not screen_hash:
        return False

    node = self.dynamic_graph.states.get(screen_hash)
    if not node:
        return False  # First visit, not duplicate

    # Extract action coordinates
    args = tool_call.get('args', {})
    coords = (args.get('x', 0), args.get('y', 0))

    # Find matching screen item
    screen_desc = state.get('screen_description', {})
    screen_item = self._find_item_by_coords(coords, screen_desc)

    if screen_item and screen_item.actions:
        action_id = screen_item.actions[0].id
        if action_id in node.executed_actions:
            return True  # DUPLICATE!

    return False
```

Opção B: Contador de repetições (mais flexível):
```python
class RVAgent:
    def __init__(self, ...):
        self.action_repetition_counter = {}  # {(screen_hash, action_id): count}
        self.max_repetitions = 2  # Allow max 2 times same action

def _is_action_excessive(self, tool_call, state) -> bool:
    screen_hash = state['current_screen_hash']
    action_id = self._get_action_id(tool_call, state)

    key = (screen_hash, action_id)
    count = self.action_repetition_counter.get(key, 0)

    if count >= self.max_repetitions:
        logger.warning(f"Action {action_id} executed {count}x, blocking")
        return True

    self.action_repetition_counter[key] = count + 1
    return False
```

**2.2 Fallback para estratégia algorítmica:**

Criar método nas estratégias:
```python
# Em strategies/base_strategy.py:
class BaseStrategy(ABC):
    @abstractmethod
    def select_next_action(
        self,
        current_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[Dict[str, Any]]:
        """
        Select next action algorithmically (no LLM).

        Returns:
            Action dict with keys: action_type, coords, element_description, explanation
            None if exploration complete
        """
        pass
```

Implementar em `dfs_strategy.py`:
```python
def select_next_action(self, current_hash: str, screen_desc: ScreenDescription) -> Optional[Dict]:
    node = self.graph.states.get(current_hash)
    all_actions = screen_desc.get_all_actions()

    # Get untested actions
    if node:
        untested = [a for a in all_actions if a.id not in node.executed_actions]
    else:
        untested = all_actions

    # DFS: Select highest MOP priority
    if untested:
        # Sort by MOP priority: [DM] > [M] > none
        priority_sorted = sorted(
            untested,
            key=lambda a: (
                3 if a.directly_reaches_mop else 2 if a.reaches_mop else 1
            ),
            reverse=True
        )
        selected = priority_sorted[0]

        # Convert to action dict
        coords = self._extract_coords(selected)
        return {
            "action_type": "CLICK",  # ou TYPE_TEXT se for EditText
            "coords": coords,
            "element_description": selected.text or selected.class_name,
            "explanation": f"DFS: Priority action [{'DM' if selected.directly_reaches_mop else 'M' if selected.reaches_mop else '-'}]"
        }
    else:
        # No untested actions → BACKTRACK
        logger.info("DFS: Screen exhausted, backtracking")
        return {
            "action_type": "BACK",
            "explanation": "DFS: Backtracking to previous state"
        }

def _extract_coords(self, screen_item):
    """Extract center coordinates from screen item bounds"""
    if hasattr(screen_item, 'view') and 'bounds' in screen_item.view:
        bounds = screen_item.view['bounds']
        # bounds: [[x1, y1], [x2, y2]]
        center_x = (bounds[0][0] + bounds[1][0]) // 2
        center_y = (bounds[0][1] + bounds[1][1]) // 2
        return (center_x, center_y)
    return (0, 0)
```

Usar fallback em `_handle_max_retries_node()`:
```python
def _handle_max_retries_node(self, state: AgentState) -> AgentState:
    logger.warning("⚠️ HANDLE_MAX_RETRIES: LLM failed after 3 retries, fallback to strategy")

    if not self.strategy:
        logger.error("No strategy available for fallback!")
        return {"should_continue": False}

    # 🆕 Use strategy to select action
    selected_action = self.strategy.select_next_action(
        current_hash=state['current_screen_hash'],
        screen_desc=state['screen_description']
    )

    if selected_action:
        logger.info(f"Strategy selected: {selected_action['action_type']} - {selected_action['explanation']}")

        # Convert to tool call format
        if selected_action['action_type'] == 'CLICK':
            tool_call = {
                'name': 'android_click',
                'args': {
                    'element_description': selected_action['element_description'],
                    'x': selected_action['coords'][0],
                    'y': selected_action['coords'][1]
                }
            }
        elif selected_action['action_type'] == 'BACK':
            tool_call = {
                'name': 'android_back',
                'args': {}
            }

        return {
            "tool_calls": [tool_call],
            "retry_count": 0,
            "fallback_used": True
        }
    else:
        # Exploration complete
        logger.info("Strategy says exploration complete")
        return {"should_continue": False}
```

**Resultado Esperado:**
- Após 2-3 TYPE_TEXT no mesmo campo → bloqueado
- LLM tenta 3x gerar tool call → fallback para DFS
- DFS seleciona GENERATE HASH [M] algoritmicamente
- Zero loops infinitos

**Teste:**
```bash
poetry run python test_real_emulator.py --app cryptoapp --timeout 120
```
Verificar se clica GENERATE HASH após fallback.

---

### FASE 3: Modo Puro Estratégia (Baseline)

**Objetivo:** Rodar DFS/BFS sem LLM para baseline comparativo

**Mudanças:**

**3.1 Adicionar config `exploration_mode`:**
```python
# Em config/agent_config.py:
class RVAgentConfig(BaseModel):
    # ... existing fields ...
    exploration_mode: str = "hybrid"  # "llm" | "strategy" | "hybrid"
```

**3.2 Modificar `_assistant_node()` para pular LLM:**
```python
def _assistant_node(self, state: AgentState) -> AgentState:
    # 🆕 Check exploration mode
    if self.config.exploration_mode == "strategy":
        logger.info("🤖 STRATEGY MODE: Skipping LLM, using pure algorithmic exploration")

        selected_action = self.strategy.select_next_action(
            current_hash=state['current_screen_hash'],
            screen_desc=state['screen_description']
        )

        if selected_action:
            # Convert to tool call
            tool_call = self._action_to_tool_call(selected_action)
            return {
                "tool_calls": [tool_call],
                "messages": [],
                "strategy_decision": True
            }
        else:
            # Exploration complete
            return {"should_continue": False}

    # Normal LLM flow
    # ... existing LLM code ...
```

**3.3 Implementar BFS.select_next_action():**
```python
# Em strategies/bfs_strategy.py:
def select_next_action(self, current_hash: str, screen_desc: ScreenDescription):
    node = self.graph.states.get(current_hash)
    all_actions = screen_desc.get_all_actions()

    # Get untested actions in CURRENT screen (BFS: exhaust level first)
    if node:
        untested = [a for a in all_actions if a.id not in node.executed_actions]
    else:
        untested = all_actions

    # BFS: Prioritize MOP in current screen
    if untested:
        priority_sorted = sorted(
            untested,
            key=lambda a: (3 if a.directly_reaches_mop else 2 if a.reaches_mop else 1),
            reverse=True
        )
        selected = priority_sorted[0]
        coords = self._extract_coords(selected)

        return {
            "action_type": "CLICK",
            "coords": coords,
            "element_description": selected.text or selected.class_name,
            "explanation": f"BFS: Priority in current screen [{'DM' if selected.directly_reaches_mop else 'M' if selected.reaches_mop else '-'}]"
        }
    else:
        # Current screen exhausted → navigate to queued screen
        # TODO FASE 5: Implement pathfinding to reach next screen in queue
        # For now: just BACK
        logger.info("BFS: Current screen exhausted, backtracking")
        return {
            "action_type": "BACK",
            "explanation": "BFS: Backtracking (queue navigation not implemented yet)"
        }
```

**Resultado Esperado:**
- `exploration_mode="strategy"` → zero LLM calls
- DFS puro: exploração sistemática por profundidade
- BFS puro: exploração por largura (sem queue navigation ainda)
- Baseline para comparar com LLM

**Testes Comparativos:**
```bash
# DFS puro
poetry run python test_real_emulator.py --app cryptoapp --timeout 120 --mode strategy --strategy dfs

# BFS puro
poetry run python test_real_emulator.py --app cryptoapp --timeout 120 --mode strategy --strategy bfs

# LLM puro (atual)
poetry run python test_real_emulator.py --app cryptoapp --timeout 120 --mode llm

# Híbrido (FASE 2)
poetry run python test_real_emulator.py --app cryptoapp --timeout 120 --mode hybrid
```

Métricas para comparar:
- Unique screens
- Cobertura (ações executadas / ações totais)
- MOPs atingidas
- Tempo até primeiro loop
- Tokens usados (LLM only)

---

### FASE 4: Híbrido Inteligente (Advanced)

**Objetivo:** Coordenação LLM + Estratégia otimizada

**Componentes:**

**4.1 Decision Coordinator:**
```python
class DecisionCoordinator:
    """Coordinates LLM and strategy decisions"""

    def __init__(self, llm, strategy, config):
        self.llm = llm
        self.strategy = strategy
        self.loop_detector = LoopDetector(max_same_action=3)
        self.mode = config.exploration_mode

    def decide_next_action(self, state):
        """
        Decision flow:
        1. Try LLM (if mode allows)
        2. Validate not duplicate/loop
        3. If invalid → fallback to strategy
        4. Strategy selects algorithmically
        """
        # Try LLM first
        if self.mode in ["llm", "hybrid"]:
            llm_action = self.llm.generate_action(state)

            # Validate
            if llm_action and not self.loop_detector.is_loop(llm_action, state):
                return llm_action, "llm"

        # Fallback to strategy
        strategy_action = self.strategy.select_next_action(
            state['current_screen_hash'],
            state['screen_description']
        )
        return strategy_action, "strategy"
```

**4.2 Loop Detector:**
```python
class LoopDetector:
    def __init__(self, max_same_action=3, max_same_screen=10):
        self.action_history = deque(maxlen=max_same_action)
        self.screen_visit_count = {}
        self.max_same_screen = max_same_screen

    def is_loop(self, action, state) -> bool:
        # Check 1: Same action repeated 3x
        if len(self.action_history) == self.action_history.maxlen:
            if all(a == action for a in self.action_history):
                logger.warning(f"LOOP: Same action {max_same_action}x")
                return True
        self.action_history.append(action)

        # Check 2: Same screen visited 10x
        screen_hash = state['current_screen_hash']
        self.screen_visit_count[screen_hash] = self.screen_visit_count.get(screen_hash, 0) + 1
        if self.screen_visit_count[screen_hash] > self.max_same_screen:
            logger.warning(f"LOOP: Screen {screen_hash[:8]} visited {self.max_same_screen}x")
            return True

        return False
```

**4.3 Alternância Dinâmica DFS/BFS:**
```python
class StrategyScheduler:
    """Alternate between DFS and BFS based on coverage"""

    def __init__(self, dfs_strategy, bfs_strategy):
        self.dfs = dfs_strategy
        self.bfs = bfs_strategy
        self.current = dfs_strategy
        self.iterations_since_switch = 0
        self.switch_interval = 50  # Switch every 50 iterations

    def get_current_strategy(self):
        return self.current

    def maybe_switch(self, coverage_metrics):
        self.iterations_since_switch += 1

        # Switch based on interval OR coverage plateau
        if self.iterations_since_switch >= self.switch_interval:
            self._switch()
        elif self._is_plateau(coverage_metrics):
            logger.info("Coverage plateau detected, switching strategy")
            self._switch()

    def _switch(self):
        self.current = self.bfs if self.current == self.dfs else self.dfs
        self.iterations_since_switch = 0
        logger.info(f"Switched to {self.current.__class__.__name__}")
```

**Resultado Esperado:**
- LLM tenta primeiro (criatividade)
- Validação bloqueia loops
- Estratégia intervém quando LLM falha
- Alternância DFS↔BFS aumenta cobertura

---

### FASE 5: BFS Queue Navigation (Future)

**Objetivo:** Navegação sistemática usando fila BFS

**Desafio:**
Quando tela atual esgotada, como navegar para próxima tela na fila?

**Solução: Pathfinding no Grafo de Transições**

```python
import networkx as nx

class BFSStrategy(BaseStrategy):
    def __init__(self, graph, static_data=None):
        super().__init__(graph, static_data)
        self.transition_graph = nx.DiGraph()  # State transition graph
        self.screen_queue = deque()

    def record_transition(self, from_hash: str, to_hash: str):
        super().record_transition(from_hash, to_hash)
        # Build networkx graph
        self.transition_graph.add_edge(from_hash, to_hash)

    def select_next_action(self, current_hash, screen_desc):
        # ... existing untested action selection ...

        # If current screen exhausted AND queue not empty
        if not untested and self.screen_queue:
            target_hash = self.screen_queue.popleft()
            logger.info(f"BFS: Navigating to queued screen {target_hash[:8]}")

            # Find shortest path
            try:
                path = nx.shortest_path(self.transition_graph, current_hash, target_hash)
                logger.debug(f"BFS: Path found: {len(path)} steps")

                # Get first transition in path
                next_hash = path[1] if len(path) > 1 else target_hash

                # Find action that led to next_hash
                action = self._find_action_to_state(current_hash, next_hash)
                return action
            except nx.NetworkXNoPath:
                logger.warning(f"BFS: No path to {target_hash[:8]}, using BACK")
                return {"action_type": "BACK", "explanation": "BFS: Pathfinding failed"}

        # Fallback: BACK
        return {"action_type": "BACK", "explanation": "BFS: Queue empty"}

    def _find_action_to_state(self, from_hash, to_hash):
        """
        Find which action led from from_hash to to_hash.

        This requires storing action data in transitions!
        """
        # TODO: Enhance Transition class to store action details
        # For now: return BACK as approximation
        return {"action_type": "BACK", "explanation": "BFS: Navigation action"}
```

**Melhorias Necessárias:**

1. **Enhanced Transition Class:**
```python
@dataclass
class Transition:
    from_hash: str
    to_hash: str
    action_id: int
    action_type: str      # 🆕 CLICK, TYPE_TEXT, BACK, etc
    action_coords: Tuple  # 🆕 (x, y)
    element_desc: str     # 🆕 Button text, EditText hint, etc
    timestamp: float
```

2. **Action Replay:**
Armazenar ações executadas de forma que possam ser "replayadas" para navegar.

**Resultado Esperado:**
- BFS verdadeiro: exploração por níveis
- Quando nível esgotado → navegar para próximo nível
- Cobertura mais sistemática que DFS

---

## ❓ DÚVIDAS E DECISÕES NECESSÁRIAS

### 1. Estratégia de Implementação

**Questão:** Implementar fases sequencialmente ou pular direto para solução completa?

**Opções:**

**A) Sequencial (recomendado):**
- ✅ Menos risco, iterações menores
- ✅ Cada fase testável independentemente
- ✅ Aprendizado incremental
- ❌ Mais tempo total (3-4 semanas)

**B) Direto para Fase 2+3:**
- ✅ Solução rápida do problema crítico
- ✅ Baseline comparativo logo
- ❌ Mais risco, mudanças grandes
- ❌ Difícil debug se falhar

**C) Protótipo rápido da Fase 2:**
- ✅ Quick win: eliminar loops em 2-3 dias
- ✅ Testar conceito antes de investir
- ❌ Pode gerar código temporário

**Recomendação:** Opção C - Protótipo rápido Fase 2, depois refinar com Fase 1 e 3.

---

### 2. Validação de Duplicatas

**Questão:** Como validar se ação é duplicada?

**Opções:**

**A) Strict (bloquear 100%):**
```python
if action_id in node.executed_actions:
    return True  # BLOCKED
```
- ✅ Zero duplicatas garantido
- ❌ Pode bloquear ações legítimas (ex: scroll múltiplo)

**B) Counter (permitir N vezes):**
```python
if repetition_count[action] >= max_repetitions:
    return True  # BLOCKED
```
- ✅ Flexível, permite algumas repetições
- ✅ Bom para ações como scroll, type_text
- ❌ Precisa definir N (2? 3? 5?)

**C) Time-based (bloquear se repetido em X segundos):**
```python
if last_execution_time < now - threshold:
    return False  # Allow
```
- ✅ Permite re-executar após tempo
- ❌ Complexidade adicional

**D) Context-aware:**
```python
if action_type == "TYPE_TEXT" and text_already_in_field:
    return True  # BLOCKED
elif action_type == "CLICK" and element_not_clickable:
    return True  # BLOCKED
```
- ✅ Inteligente, considera contexto
- ❌ Precisa parse de UI state

**Recomendação:** Opção B (counter) com N=2 para maioria, N=5 para scroll/swipe.

---

### 3. Fallback Trigger

**Questão:** Quando fallback deve ativar?

**Opções:**

**A) Após N retries do LLM:**
- LLM tenta 3x gerar tool call
- Se todas falharem → fallback
- ✅ Simples, já existe `max_retries`
- ❌ Desperdiça 3 iterações com falhas

**B) Imediatamente se ação duplicada:**
- Detectou duplicata → fallback sem retry
- ✅ Rápido, zero desperdício
- ❌ LLM nunca "aprende" que repetiu

**C) Híbrido:**
- Primeira duplicata → retry com warning no prompt
- Segunda duplicata → fallback
- ✅ Dá chance para LLM corrigir
- ✅ Não desperdiça muito tempo

**D) Baseado em coverage:**
- Se coverage não aumentou em 5 iterações → fallback
- ✅ Detecta plateau
- ❌ Mais complexo

**Recomendação:** Opção C (híbrido) - warn once, fallback twice.

---

### 4. Estratégia Padrão

**Questão:** DFS ou BFS como padrão?

**Opções:**

**A) DFS (profundidade):**
- ✅ Atinge MOPs mais rápido (segue fluxos completos)
- ✅ Melhor para apps com tarefas sequenciais
- ❌ Pode perder features em caminhos laterais

**B) BFS (largura):**
- ✅ Cobertura mais uniforme
- ✅ Descobre todas telas de nível N antes de N+1
- ❌ Pode demorar para atingir MOPs profundas

**C) Alternância automática:**
- DFS por 30 iterações → BFS por 30 → repeat
- ✅ Melhor dos dois mundos
- ❌ Complexidade na coordenação

**D) App-specific:**
- CryptoApp (formulários curtos): DFS
- Apps complexos (muitas telas): BFS
- ✅ Otimizado por app
- ❌ Precisa configuração manual

**Recomendação:** Começar com DFS (A), depois testar alternância (C).

---

### 5. Modo Híbrido: LLM vs Strategy

**Questão:** Quando LLM? Quando strategy?

**Opções:**

**A) LLM sempre, strategy só em fallback:**
- ✅ Maximiza criatividade LLM
- ❌ Pode repetir loops antes de fallback

**B) Strategy sempre, LLM nunca:**
- ✅ Sistemático, previsível
- ❌ Perde entendimento semântico

**C) LLM para ações "criativas", strategy para "mecânicas":**
- LLM: Botões sem marcação MOP, campos de texto complexos
- Strategy: Botões [M]/[DM], navegação básica
- ✅ Divisão inteligente de trabalho
- ❌ Como decidir o que é "criativo"?

**D) Percentual: 70% LLM, 30% strategy:**
- Randomizar: 70% das vezes usa LLM, 30% strategy
- ✅ Balanceia criatividade + sistematicidade
- ❌ Não determinístico

**E) Adaptive: LLM até N falhas, depois strategy dominante:**
- Começa 100% LLM
- A cada falha, aumenta % de strategy
- ✅ Aprende que LLM não está performando
- ✅ Gradual, não abrupto

**Recomendação:** Opção E (adaptive) - começar confiando em LLM, adaptar se falhar.

---

### 6. Testes e Métricas

**Questão:** O que testar e como medir sucesso?

**Métricas Propostas:**

1. **Cobertura:**
   - Ações executadas / ações totais
   - Telas visitadas / telas descobertas
   - MOPs atingidas / MOPs disponíveis

2. **Eficiência:**
   - Tempo até primeira MOP
   - Iterações até 80% cobertura
   - Tokens usados (LLM only)

3. **Loops:**
   - Maior sequência de ações idênticas
   - Número de backtracks
   - Telas visitadas 5+ vezes

4. **Comparação:**
   - DFS puro vs BFS puro vs LLM puro vs Híbrido
   - Real device vs Mock device (offline)

**Apps para Testar:**

**Tier 1 (simples, validação rápida):**
- CryptoApp (formulários, dropdowns)
- SimpleNotes (texto, listas)

**Tier 2 (complexidade média):**
- Apps com múltiplas activities
- Apps com navigation drawer

**Tier 3 (complexos):**
- Apps com login
- Apps com permissões
- Apps com WebView

**Recomendação:** Começar com Tier 1, expandir após Fase 2 validada.

---

## 🔄 COMPARATIVO: DFS vs BFS vs LLM vs Híbrido

### Características

| Aspecto | DFS Puro | BFS Puro | LLM Puro | Híbrido |
|---------|----------|----------|----------|---------|
| **Decisão** | Algorítmica | Algorítmica | LLM | LLM + Algoritmo |
| **Visão** | XML only | XML only | Multimodal | Multimodal |
| **Priorização** | MOP marks | MOP marks | Semântica | MOP + Semântica |
| **Loops** | Impossível | Impossível | Frequente | Bloqueado |
| **Backtracking** | Automático | Automático | Ausente | Automático |
| **Criatividade** | Baixa | Baixa | Alta | Alta |
| **Sistematicidade** | Alta | Alta | Baixa | Alta |
| **Custo (tokens)** | Zero | Zero | Alto | Médio |
| **Velocidade** | Rápida | Rápida | Lenta | Média |

### Casos de Uso

**DFS Puro:**
- Baseline de cobertura sistemática
- Apps com fluxos profundos (wizards, formulários multi-step)
- Quando tokens/custo são limitação
- Debugging: comparar com LLM para identificar onde LLM falha

**BFS Puro:**
- Baseline de cobertura uniforme
- Apps com muitas telas no mesmo nível (tabs, menus)
- Descoberta rápida de features
- Quando quer mapear app completo antes de explorar profundidade

**LLM Puro (atual):**
- Apps com UI complexa (WebView, custom views)
- Quando criatividade é crítica
- Apps sem marcação MOP
- Pesquisa: limite superior de performance com LLM

**Híbrido (proposto):**
- Produção: melhor balanceamento
- Apps médios/grandes
- Quando quer cobertura + entendimento semântico
- Quando custo de tokens é aceitável mas não ilimitado

### Expectativas de Performance

**CryptoApp (120s timeout):**

| Métrica | DFS | BFS | LLM | Híbrido |
|---------|-----|-----|-----|---------|
| Unique screens | 8-10 | 8-10 | 3 (atual) | 10-12 |
| Coverage | 60-70% | 60-70% | 20% | 70-80% |
| MOPs atingidas | 2-3 | 2-3 | 0-1 | 3-4 |
| Iterations | 40-50 | 40-50 | 22 | 45-55 |
| Loops detectados | 0 | 0 | 1 grande | 0 |
| Tokens usados | 0 | 0 | 100k | 50-70k |

**Nota:** Expectativas baseadas em:
- DFS/BFS: Performance típica de DroidBot
- LLM: Resultado atual do teste
- Híbrido: Estimativa (LLM criatividade + DFS sistematicidade)

---

## 🚀 POSSIBILIDADES FUTURAS

### 1. Aprendizado de Padrões LLM

**Ideia:** Usar histórico de decisões LLM bem-sucedidas para melhorar estratégia.

**Implementação:**
```python
class AdaptiveStrategy:
    def __init__(self, base_strategy):
        self.base = base_strategy
        self.llm_success_patterns = {}  # {screen_hash: {action_id: success_count}}

    def record_llm_success(self, screen_hash, action_id):
        if screen_hash not in self.llm_success_patterns:
            self.llm_success_patterns[screen_hash] = {}

        self.llm_success_patterns[screen_hash][action_id] = \
            self.llm_success_patterns[screen_hash].get(action_id, 0) + 1

    def select_next_action(self, current_hash, screen_desc):
        # Check if LLM has successful patterns for this screen
        if current_hash in self.llm_success_patterns:
            # Combine LLM patterns with MOP priorities
            pass

        # Fallback to base strategy
        return self.base.select_next_action(current_hash, screen_desc)
```

**Benefício:** Estratégia aprende com LLM ao longo do tempo.

---

### 2. State Similarity e Generalização

**Problema:** Screens com estrutura similar mas hash diferente.

**Exemplo:**
- Tela de formulário em activity A
- Tela de formulário em activity B
- Estrutura idêntica, mas hash diferente

**Solução:** Clustering de telas similares.

```python
from sklearn.cluster import DBSCAN
import numpy as np

class StateSimilarityDetector:
    def __init__(self):
        self.state_vectors = {}  # {hash: feature_vector}
        self.clusters = {}       # {cluster_id: [hashes]}

    def vectorize_state(self, screen_desc):
        """Convert screen to feature vector"""
        features = [
            len(screen_desc.items),
            sum(1 for item in screen_desc.items if item.clickable),
            sum(1 for item in screen_desc.items if item.class_name == 'EditText'),
            sum(1 for item in screen_desc.items if item.reaches_mop),
            # ... more features
        ]
        return np.array(features)

    def find_similar_states(self, current_hash, threshold=0.8):
        """Find states similar to current"""
        current_vec = self.state_vectors[current_hash]

        similar = []
        for hash, vec in self.state_vectors.items():
            similarity = cosine_similarity(current_vec, vec)
            if similarity > threshold:
                similar.append(hash)

        return similar
```

**Uso:**
- Se tela atual similar a tela anterior → reutilizar ações bem-sucedidas
- Generalizar padrões: "formulários sempre precisam preencher EditText primeiro"

---

### 3. Multi-App Learning

**Ideia:** Treinar em múltiplos apps, transferir conhecimento.

**Implementação:**
```python
class CrossAppMemory:
    def __init__(self):
        self.global_patterns = {
            'form_filling': {
                'rule': 'Fill all EditText before clicking submit',
                'apps_confirmed': ['cryptoapp', 'simplenotes', 'loginapp'],
                'confidence': 0.95
            },
            'permission_dialogs': {
                'rule': 'Click Allow on bottom-right',
                'apps_confirmed': ['cameraapp', 'locationapp'],
                'confidence': 0.90
            }
        }

    def get_applicable_rules(self, screen_desc):
        """Return rules that apply to current screen"""
        rules = []

        # Detect if current screen is a form
        if self._is_form(screen_desc):
            rules.append(self.global_patterns['form_filling'])

        return rules
```

**Benefício:** Novos apps se beneficiam de conhecimento prévio.

---

### 4. Reinforcement Learning Integration

**Ideia:** Usar RL para otimizar decisão LLM vs Strategy.

**Implementação:**
```python
class RLExplorationPolicy:
    def __init__(self):
        self.q_table = {}  # {(state, decision): reward}
        self.epsilon = 0.2  # Exploration rate

    def choose_decision_maker(self, state):
        """
        Decide: use LLM or Strategy?

        State features: coverage, iteration, screen complexity
        Actions: "llm" or "strategy"
        Reward: coverage increase - token cost
        """
        state_key = self._state_to_key(state)

        if random.random() < self.epsilon:
            # Explore
            return random.choice(['llm', 'strategy'])
        else:
            # Exploit
            q_llm = self.q_table.get((state_key, 'llm'), 0)
            q_strategy = self.q_table.get((state_key, 'strategy'), 0)
            return 'llm' if q_llm > q_strategy else 'strategy'

    def update_q_value(self, state, action, reward):
        """Update Q-table after action execution"""
        state_key = self._state_to_key(state)
        current_q = self.q_table.get((state_key, action), 0)

        # Q-learning update
        learning_rate = 0.1
        discount = 0.9
        max_next_q = max([self.q_table.get((state_key, a), 0) for a in ['llm', 'strategy']])

        new_q = current_q + learning_rate * (reward + discount * max_next_q - current_q)
        self.q_table[(state_key, action)] = new_q
```

**Benefício:** Aprende automaticamente quando LLM vs Strategy é melhor.

---

### 5. Intent-Based Exploration

**Ideia:** Estratégia guiada por intents/tarefas específicas.

**Exemplo:**
```python
class IntentDrivenStrategy:
    def __init__(self, intents):
        self.intents = intents  # ["generate_hash_sha256", "save_note", "login"]
        self.current_intent = None

    def select_next_action(self, current_hash, screen_desc):
        if not self.current_intent:
            self.current_intent = self.intents.pop(0) if self.intents else None

        if self.current_intent == "generate_hash_sha256":
            # Specific actions for this intent
            if self._has_edittext(screen_desc):
                return self._fill_edittext("Test message")
            elif self._has_button(screen_desc, "GENERATE"):
                return self._click_button("GENERATE")

        # Fallback to DFS
        return super().select_next_action(current_hash, screen_desc)
```

**Benefício:** Exploração dirigida a tarefas específicas (útil para RV!).

---

## 📋 PRÓXIMOS PASSOS RECOMENDADOS

### Amanhã (2025-11-04)

1. **Decisões (30 min):**
   - Revisar este documento
   - Decidir:
     - Implementação sequencial vs protótipo rápido
     - Validação: strict vs counter
     - Fallback trigger: retry vs immediate
     - Estratégia padrão: DFS vs BFS

2. **Setup (30 min):**
   - Criar branch: `feature/exploration-strategies`
   - Criar diretório de testes: `tests/exploration/`
   - Definir métricas de sucesso

3. **Implementação Fase 1 ou 2 (3-4h):**
   - Se Fase 1: Ativar guidance
   - Se Fase 2: Protótipo fallback

4. **Testes (1-2h):**
   - Rodar em CryptoApp
   - Verificar se loops foram eliminados
   - Comparar métricas

### Semana 1 (2025-11-04 a 2025-11-08)

- **Dia 1:** Fase 1 completa + testes
- **Dia 2:** Fase 2 parte 1 (validação)
- **Dia 3:** Fase 2 parte 2 (fallback)
- **Dia 4:** Testes extensivos + ajustes
- **Dia 5:** Documentação + revisão

### Semana 2 (2025-11-11 a 2025-11-15)

- **Dia 1-2:** Fase 3 (modo puro estratégia)
- **Dia 3-4:** Testes comparativos (DFS vs BFS vs LLM vs Hybrid)
- **Dia 5:** Análise de resultados + decisão sobre Fase 4

### Semana 3+ (se aprovado)

- Fase 4: Híbrido inteligente
- Fase 5: BFS queue navigation
- Possibilidades futuras (RL, multi-app learning, etc)

---

## 📝 PERGUNTAS PARA DISCUSSÃO

1. **Priorização:**
   - Você prefere solução rápida (Fase 2 protótipo) ou incremental (Fase 1→2→3)?

2. **Validação:**
   - Permitir 2 repetições ou bloquear 100% duplicatas?
   - Considerar tipo de ação (TYPE_TEXT strict, CLICK flexível)?

3. **Estratégia:**
   - Começar com DFS ou BFS?
   - Testar alternância DFS↔BFS?

4. **Modo Híbrido:**
   - LLM sempre + fallback, ou misturar LLM/strategy randomicamente?
   - Adaptive (aprender quando usar cada um)?

5. **Testes:**
   - Focar em CryptoApp + SimpleNotes, ou expandir para mais apps?
   - Rodar comparativo completo (4 modos) ou só validar híbrido?

6. **Futuro:**
   - Interesse em RL integration?
   - Intent-based exploration útil para cenários RV?

---

## 🎯 OBJETIVO FINAL

**Criar RVAgent Híbrido que:**

✅ **NUNCA entra em loops infinitos**
- Validação bloqueia ações duplicadas
- Fallback algorítmico quando LLM falha
- Backtracking quando tela esgotada

✅ **Maximiza cobertura sistematicamente**
- DFS/BFS garantem exploração completa
- MOP prioritization atinge tarefas críticas
- Cobertura 70-80% (vs 20% atual)

✅ **Mantém criatividade do LLM**
- LLM tenta primeiro (entendimento semântico)
- Estratégia só intervém se necessário
- Melhor dos dois mundos

✅ **É configurável e testável**
- Modos: llm, strategy, hybrid
- Estratégias: dfs, bfs
- Métricas comparativas

✅ **Serve como baseline para pesquisa**
- DFS/BFS puro para comparação
- Dados para análise de quando LLM supera algoritmo
- Framework para futuras melhorias (RL, multi-app, etc)

---

**FIM DO PRÉ-PLANO**

**Próxima sessão:** Revisar este documento, tomar decisões, começar implementação.

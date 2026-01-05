# PLANO DE REFATORAÇÃO DO RVAGENT - 2025-11-10

## CONTEXTO E MOTIVAÇÃO

### Análise V12 - Baseline Completo (28 Apps)

Executamos teste completo do RVAgent V12 em 28 apps do dataset com as seguintes configurações:

**Configuração de Teste:**
- **Prompt**: V12
- **Modo**: multimode (70% LLM / 30% algoritmo)
- **Estratégia**: greedy
- **Timeout**: 180 segundos por app
- **Modelo LLM**: qwen3-vl-4b-8k:latest
- **Dimensões**: Device (1080x1920), Otimizado (704x1248)
- **Fatores de escala**: x=1.534, y=1.538

**Resultados Gerais:**
- ✅ **Taxa de sucesso**: 100% (28/28 apps completados)
- **Total de ações**: 656
- **Ações LLM**: 435 (66.3%)
- **Ações do algoritmo**: 221 (33.7%)
- **Média de ações/app**: 23.4
- **Tempo total**: ~2h55min

**Distribuição de Tipos de Ação:**
- CLICK: 588 (89.6%)
- SWIPE: 19 (2.9%)
- TYPE_TEXT: 13 (2.0%)
- SET_TEXT: 9 (1.4%)
- SCROLL: 19 (2.9%)
- LONG_CLICK: 4 (0.6%)
- BACK: 4 (0.6%)

### Problemas Identificados

Apesar do sucesso de 100%, identificamos **4 problemas críticos** que limitam a eficácia da exploração:

#### 1. UI Coverage Annotations NÃO Enviadas ao LLM

**Situação:**
- UI Coverage **existe** e está implementado (`modules/rv-agent/src/rv_agent/memory/ui_coverage.py`)
- Método `record_interaction()` **está sendo chamado** corretamente
- Método `annotate_screen_elements()` **NÃO está sendo chamado**
- LLM não recebe informação sobre elementos [UNTESTED] vs [TESTED-3x]

**Impacto:**
- LLM não sabe quais elementos já foram testados
- Resulta em exploração subótima (clica repetidamente nos mesmos elementos)
- Exemplo: `org.emunix.insteadlauncher` clicou 5 vezes no mesmo botão

**Causa Raiz:**
- `nodes.py` não chama `ui_coverage.annotate_screen_elements()` antes de enviar `screen_description` ao LLM

#### 2. Timeouts do LLM (10+ minutos)

**Situação:**
- Todos os 5 apps com <10 ações tiveram timeouts de 10+ minutos do LLM
- Não há limite de tempo nas chamadas do LLM
- Sistema fica travado esperando resposta

**Apps Afetados:**
- `cf.playhi.freezeyou`: 3 ações (1 LLM, 2 algoritmo) - múltiplos timeouts
- `org.emunix.insteadlauncher`: 6 ações - timeout de 15 minutos
- `com.aidinhut.simpletextcrypt`: 10 ações - timeout recorrente
- `org.pulpdust.lesserpad`: 11 ações - timeout no início
- `com.sam.hex`: 12 ações - timeout após 3 interações

**Causa Raiz:**
- `llm_service.py` não implementa timeout na chamada `llm.invoke()`

#### 3. Falta de Modo de Recuperação (Recovery Mode)

**Situação:**
- Quando LLM falha 3+ vezes consecutivas, sistema continua tentando usar LLM
- Não há fallback automático para modo algorítmico
- Desperdiça tempo tentando LLM repetidamente

**Impacto:**
- Reduz eficiência da exploração
- Tempo gasto em tentativas falhas poderia ser usado em ações algorítmicas

**Necessidade:**
- Após 3 falhas consecutivas do LLM, ativar "Recovery Mode"
- Recovery Mode = 10 ações puramente algorítmicas (DFS/BFS/Greedy)
- Resetar contador de falhas após sucesso do LLM

#### 4. Baixa Entrada de Texto (3.4% apesar de 71% dos apps terem formulários)

**Situação:**
- **Análise do dataset**: 20/28 apps (71%) possuem campos EditText
- **Ações de texto executadas**: 22/656 (3.4%)
- Algoritmo **nunca** gera ações TYPE_TEXT
- LLM gera TYPE_TEXT, mas sem prioridade adequada

**Apps com Formulários (EditText) no Dataset:**
- `ar.rulosoft.mimanganu`: Login fields, search bars
- `au.com.wallaceit.reddinator`: Comment box, search
- `byrne.utilities.hashpass`: Master password, domain input
- `ca.farrelltonsolar.classic`: Configuration fields
- `com.aidinhut.simpletextcrypt`: Text encryption input/output
- `com.akop.bach`: Account credentials, server config
- `com.alienpants.leafpicrevived`: Album name, description
- `com.crazyhitty.chdev.ks.munch`: Recipe search
- `com.dougkeen.bart`: Route search
- `com.dozuki.ifixit`: Search manual
- `com.gh4a`: Search issues/repos, comment fields
- `com.gianlu.dnshero`: DNS query input
- `com.github.axet.hourlyreminder`: Reminder text/notes
- `com.hwloc.lstopo`: Export path
- `com.orpheusdroid.sqliteviewer`: Query input
- `com.rafapps.simplenotes`: Note content, title
- `br.unb.cic.cryptoapp`: Message to encrypt/decrypt
- `info.zamojski.soft.towercollector`: Cell tower notes
- `livio.rssreader`: Feed URL
- `org.pulpdust.lesserpad`: Text editor content

**Causa Raiz:**
- Algoritmo não tem lógica para gerar TYPE_TEXT
- Precisamos implementar heurística de entrada de texto no algoritmo

#### 5. Loops Espaciais e Estados Presos

**Situação:**
- Alguns apps ficaram presos clicando repetidamente no mesmo elemento
- Não há detector de loop espacial (mesmas coordenadas)
- Não há detector de estado preso (mesmo screen_hash)

**Exemplos:**
- `org.emunix.insteadlauncher`: Clicou 5 vezes no mesmo botão
- `cf.playhi.freezeyou`: Clicou repetidamente em elementos sem efeito

**Necessidade:**
- **Loop espacial**: Detectar quando últimas 3 ações CLICK estão em raio <50px
- **Estado preso**: Detectar quando screen_hash não muda por 5+ ações

## SOLUÇÕES PROPOSTAS - 6 MELHORIAS

### Item 1: Ativar UI Coverage Annotations no Pipeline LLM

**Arquivo:** `modules/rv-agent/src/rv_agent/llm/graph/nodes.py`

**Localização:** Função `llm_generate()`, após obter `screen_description`

**Código a Adicionar:**

```python
def llm_generate(state: AgentState) -> dict:
    """Generate action using LLM with UI coverage annotations."""
    logger.info("🧠 Generating LLM action...")

    # Existing code...
    screen_description = state.get("screen_description", "")

    # ✅ ADICIONAR: Anotar elementos com status de cobertura
    if "ui_coverage" in state and state["ui_coverage"]:
        interactive_elements = state.get("interactive_elements", [])
        screen_description = state["ui_coverage"].annotate_screen_elements(
            screen_description,
            interactive_elements
        )
        logger.info("✅ UI Coverage annotations applied to screen description")

    # Continue with existing LLM invocation...
    messages = state["llm_service"].build_messages(
        state=state,
        screen_description=screen_description,
        # ...
    )

    # ... rest of existing code
```

**Impacto Esperado:**
- LLM recebe elementos anotados: `[UNTESTED]`, `[TESTED-1x]`, `[TESTED-3x]`
- Exploração mais inteligente, prioriza elementos não testados
- Reduz loops espaciais

---

### Item 2: Adicionar Timeout de 60s nas Chamadas LLM

**Arquivo:** `modules/rv-agent/src/rv_agent/llm/llm_service.py`

**Localização:** Método `generate()` ou similar onde `llm.invoke()` é chamado

**Código a Adicionar:**

```python
import signal
from contextlib import contextmanager
from typing import Optional

class TimeoutException(Exception):
    """Exception raised when LLM call exceeds timeout."""
    pass

@contextmanager
def timeout_context(seconds: int):
    """Context manager for enforcing timeout on blocking operations."""
    def timeout_handler(signum, frame):
        raise TimeoutException(f"Operation exceeded {seconds} seconds")

    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Restore old handler and cancel alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


class LLMService:
    # ... existing code ...

    def generate(self, state: AgentState) -> Optional[dict]:
        """Generate LLM response with 60-second timeout."""
        try:
            # Build messages
            messages = self.build_messages(state)

            # ✅ ADICIONAR: Invoke with timeout
            with timeout_context(60):
                response = self.llm.invoke(messages)
                return self._parse_response(response)

        except TimeoutException:
            logger.warning("⏱️  LLM timeout após 60 segundos")
            return None

        except Exception as e:
            logger.error(f"❌ LLM generation failed: {e}")
            return None
```

**Impacto Esperado:**
- Elimina timeouts de 10+ minutos
- Sistema mantém responsividade
- Apps com <10 ações devem executar mais ações

---

### Item 3: Implementar Recovery Mode (Fallback Automático)

**Arquivo:** `modules/rv-agent/src/rv_agent/core/rv_agent.py`

**Localização:** Classe `RVAgent`, método `run()` e `__init__()`

**Código a Adicionar:**

```python
class RVAgent:
    def __init__(self, config: RVAgentConfig):
        # ... existing initialization ...

        # ✅ ADICIONAR: Recovery Mode tracking
        self.llm_failure_count = 0
        self.in_recovery_mode = False
        self.recovery_actions_remaining = 0

        logger.info("Recovery Mode initialized (threshold: 3 failures)")

    def run(self) -> dict:
        """Execute agent with Recovery Mode support."""
        # ... existing setup ...

        while not self._should_stop():
            # ... existing state capture ...

            # ✅ ADICIONAR: Check Recovery Mode
            if self.in_recovery_mode:
                logger.info(f"🔧 RECOVERY MODE: {self.recovery_actions_remaining} actions remaining")
                routing_decision = "algorithm"
            else:
                # Normal mode: decide LLM vs algorithm
                routing_decision = self.decision_maker.decide(state)

            # Execute based on decision
            if routing_decision == "llm":
                llm_action = self.llm_graph.invoke(state)

                # ✅ ADICIONAR: Track LLM failures
                if llm_action is None or llm_action.get("action") is None:
                    self.llm_failure_count += 1
                    logger.warning(f"⚠️  LLM failure ({self.llm_failure_count}/3)")

                    # Activate Recovery Mode after 3 failures
                    if self.llm_failure_count >= 3:
                        logger.warning("🔄 ACTIVATING RECOVERY MODE - 10 algorithm actions")
                        self.in_recovery_mode = True
                        self.recovery_actions_remaining = 10
                        # Fall through to algorithm path below
                        routing_decision = "algorithm"
                    else:
                        # Try algorithm this iteration
                        routing_decision = "algorithm"
                else:
                    # LLM success - reset failure counter
                    if self.llm_failure_count > 0:
                        logger.info(f"✅ LLM recovered after {self.llm_failure_count} failures")
                    self.llm_failure_count = 0
                    action = llm_action["action"]

            if routing_decision == "algorithm":
                action = self.strategy.select_action(state)

                # ✅ ADICIONAR: Count down recovery mode
                if self.in_recovery_mode:
                    self.recovery_actions_remaining -= 1
                    if self.recovery_actions_remaining <= 0:
                        logger.info("✅ RECOVERY MODE completed - returning to normal mode")
                        self.in_recovery_mode = False
                        self.llm_failure_count = 0

            # ... rest of existing execution logic ...
```

**Impacto Esperado:**
- Reduz tempo desperdiçado em tentativas falhas
- Mantém exploração ativa durante problemas do LLM
- Recuperação automática quando LLM volta a funcionar

---

### Item 4: Detector de Loop Espacial (Base Strategy)

**Arquivo:** `modules/rv-agent/src/rv_agent/strategies/base_strategy.py`

**Localização:** Classe `BaseStrategy`, adicionar novo método

**Código a Adicionar:**

```python
from rv_android_core.domain.action import ActionType
import math

class BaseStrategy:
    # ... existing code ...

    def detect_spatial_loop(self, state: AgentState) -> bool:
        """
        Detecta loop espacial: últimas 3 ações CLICK em raio <50px.

        Args:
            state: Estado atual do agente com histórico de ações

        Returns:
            True se detectar loop espacial, False caso contrário
        """
        action_history = state.get("action_history", [])

        # Precisa de pelo menos 3 ações para detectar loop
        if len(action_history) < 3:
            return False

        # Extrair últimas 3 ações CLICK com coordenadas
        recent_clicks = []
        for action in reversed(action_history):
            if action.action_type == ActionType.CLICK and action.x is not None:
                recent_clicks.append((action.x, action.y))
            if len(recent_clicks) == 3:
                break

        # Se não temos 3 CLICKs, não é loop espacial
        if len(recent_clicks) < 3:
            return False

        # Calcular distância máxima entre todos os pares
        max_distance = 0
        for i in range(len(recent_clicks)):
            for j in range(i + 1, len(recent_clicks)):
                x1, y1 = recent_clicks[i]
                x2, y2 = recent_clicks[j]
                distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                max_distance = max(max_distance, distance)

        # Loop se todas ações em raio <50px
        is_loop = max_distance < 50

        if is_loop:
            logger.warning(f"🔁 Spatial loop detected: clicks at {recent_clicks} (max distance: {max_distance:.1f}px)")

        return is_loop
```

**Arquivos a Modificar:** `dfs_strategy.py`, `bfs_strategy.py`, `greedy_strategy.py`

**Localização:** Método `select_action()`, adicionar no **início** do método

**Código a Adicionar em Cada Estratégia:**

```python
def select_action(self, state: AgentState) -> Action:
    """Select next action with spatial loop detection."""

    # ✅ ADICIONAR: Check for spatial loop FIRST
    if self.detect_spatial_loop(state):
        logger.info("🔙 Escaping spatial loop - pressing BACK")
        return Action(action_type=ActionType.PRESS_BACK)

    # ... rest of existing strategy logic ...
```

**Impacto Esperado:**
- Detecta quando app está clicando repetidamente no mesmo lugar
- Escapa do loop com ação BACK
- Melhora exploração em apps como `org.emunix.insteadlauncher`

---

### Item 6: Text Input Fallback para Algoritmo

**Arquivos:** `dfs_strategy.py`, `bfs_strategy.py`, `greedy_strategy.py`

**Localização:** Classe de cada estratégia, adicionar novo método

**Código a Adicionar:**

```python
import random
from typing import Optional

class DFSStrategy(BaseStrategy):  # ou BFS/Greedy
    # ... existing code ...

    def try_text_input(self, elements: list) -> Optional[Action]:
        """
        Tenta gerar ação TYPE_TEXT em EditText (20% probabilidade).

        Args:
            elements: Lista de elementos interativos da tela

        Returns:
            Action com TYPE_TEXT ou None
        """
        # 20% chance de tentar entrada de texto
        if random.random() > 0.2:
            return None

        # Filtrar apenas EditText
        text_fields = [
            e for e in elements
            if "EditText" in e.get("class", "")
        ]

        if not text_fields:
            return None

        # Selecionar EditText com menor interaction_count
        target = min(text_fields, key=lambda e: e.get("interaction_count", 0))

        # Heurística: determinar tipo de texto baseado em hints
        hint = target.get("content_desc", "").lower()
        hint += " " + target.get("hint", "").lower()
        hint += " " + target.get("resource_id", "").lower()

        # Determinar texto apropriado
        if "email" in hint or "e-mail" in hint:
            text = "test@example.com"
        elif "passw" in hint or "senha" in hint:
            text = "Test123!"
        elif "name" in hint or "nome" in hint:
            text = "Test User"
        elif "phone" in hint or "tel" in hint or "fone" in hint:
            text = "5511999999999"
        elif "search" in hint or "busca" in hint or "pesquis" in hint:
            text = "test"
        elif "url" in hint or "site" in hint or "web" in hint:
            text = "https://example.com"
        elif "number" in hint or "numero" in hint:
            text = "123"
        else:
            # Generic text
            text = "test123"

        logger.info(f"📝 Algorithm generating TYPE_TEXT: '{text}' for {target.get('resource_id', 'EditText')}")

        return Action(
            action_type=ActionType.TYPE_TEXT,
            x=target["bounds"]["center_x"],
            y=target["bounds"]["center_y"],
            text=text
        )

    def select_action(self, state: AgentState) -> Action:
        """Select next action with text input support."""

        # Check spatial loop (from Item 4)
        if self.detect_spatial_loop(state):
            logger.info("🔙 Escaping spatial loop - pressing BACK")
            return Action(action_type=ActionType.PRESS_BACK)

        # ✅ ADICIONAR: Try text input before regular logic
        interactive_elements = state.get("interactive_elements", [])
        text_action = self.try_text_input(interactive_elements)
        if text_action:
            return text_action

        # ... rest of existing strategy logic ...
```

**Impacto Esperado:**
- Algoritmo passa a gerar ações TYPE_TEXT (20% quando há EditText)
- Aumento de 3.4% → ~15-20% de ações de texto
- Melhor exploração em apps com formulários (71% do dataset)

---

### Item 7: Detector de Estado Preso (Screen Hash Unchanged)

**Arquivo:** `modules/rv-agent/src/rv_agent/core/rv_agent.py`

**Localização:** Classe `RVAgent`, método `__init__()` e `run()`

**Código a Adicionar:**

```python
class RVAgent:
    def __init__(self, config: RVAgentConfig):
        # ... existing initialization ...

        # Recovery Mode (from Item 3)
        self.llm_failure_count = 0
        self.in_recovery_mode = False
        self.recovery_actions_remaining = 0

        # ✅ ADICIONAR: Stuck state detection
        self.stuck_screen_hash = None
        self.stuck_counter = 0

        logger.info("Stuck state detector initialized (threshold: 5 unchanged screens)")

    def run(self) -> dict:
        """Execute agent with stuck state detection."""
        # ... existing setup ...

        while not self._should_stop():
            # ... existing state capture ...

            # ✅ ADICIONAR: Check if stuck in same screen
            current_hash = state.get("screen_hash")

            if current_hash == self.stuck_screen_hash:
                self.stuck_counter += 1
                logger.debug(f"Same screen: {self.stuck_counter}/5")

                if self.stuck_counter >= 5:
                    logger.warning(f"⚠️  STUCK STATE detected - screen unchanged for {self.stuck_counter} actions")
                    logger.info("🔙 Forcing BACK to escape stuck state")

                    # Force BACK action
                    action = Action(action_type=ActionType.PRESS_BACK)

                    # Execute BACK
                    self.device.execute_action(action, convert_coords=False)

                    # Reset counter
                    self.stuck_counter = 0
                    self.stuck_screen_hash = None

                    # Continue to next iteration
                    continue
            else:
                # Screen changed - reset counter
                if self.stuck_counter > 0:
                    logger.debug(f"Screen changed - resetting stuck counter (was {self.stuck_counter})")
                self.stuck_counter = 0
                self.stuck_screen_hash = current_hash

            # ... rest of existing execution logic (Recovery Mode, routing, etc.) ...
```

**Impacto Esperado:**
- Detecta quando screen não muda por 5+ ações
- Escapa com BACK automático
- Evita desperdício de tempo em estados presos

---

## PROCEDIMENTO DE IMPLEMENTAÇÃO

### 1. Backup dos Arquivos

Criar backup com timestamp:

```bash
BACKUP_DIR="backup/2025-11-10_rvagent-refactoring-$(date +%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Copiar arquivos que serão modificados
cp modules/rv-agent/src/rv_agent/llm/graph/nodes.py "$BACKUP_DIR/"
cp modules/rv-agent/src/rv_agent/llm/llm_service.py "$BACKUP_DIR/"
cp modules/rv-agent/src/rv_agent/core/rv_agent.py "$BACKUP_DIR/"
cp modules/rv-agent/src/rv_agent/strategies/base_strategy.py "$BACKUP_DIR/"
cp modules/rv-agent/src/rv_agent/strategies/dfs_strategy.py "$BACKUP_DIR/"
cp modules/rv-agent/src/rv_agent/strategies/bfs_strategy.py "$BACKUP_DIR/"
cp modules/rv-agent/src/rv_agent/strategies/greedy_strategy.py "$BACKUP_DIR/"

echo "✅ Backup criado em $BACKUP_DIR"
```

### 2. Sequência de Implementação

**Ordem de implementação** (respeita dependências):

1. **Item 4**: Detector de Loop Espacial em `base_strategy.py`
   - Adicionar método `detect_spatial_loop()`
   - Não quebra nada, apenas adiciona funcionalidade

2. **Item 6**: Text Input Fallback em estratégias
   - Adicionar método `try_text_input()` em DFS, BFS, Greedy
   - Modificar `select_action()` para chamar loop detector e text input
   - Depende de Item 4

3. **Item 2**: Timeout LLM em `llm_service.py`
   - Adicionar `timeout_context()` e modificar `generate()`
   - Independente, não quebra nada

4. **Item 1**: UI Coverage Annotations em `nodes.py`
   - Modificar `llm_generate()` para chamar `annotate_screen_elements()`
   - Independente, apenas enriquece prompt

5. **Item 3**: Recovery Mode em `rv_agent.py`
   - Adicionar tracking de falhas e Recovery Mode
   - Depende de Item 2 (timeout) para funcionar bem

6. **Item 7**: Stuck State Detector em `rv_agent.py`
   - Adicionar detector de estado preso
   - Pode ser implementado junto com Item 3

### 3. Validação

**Teste Básico** (rápido, 60s):
```bash
poetry run python test_coordinate_conversion_cryptoapp.py
```

Verificar nos logs:
- ✅ "UI Coverage annotations applied to screen description"
- ✅ "LLM timeout após 60 segundos" (se houver timeout)
- ✅ "ACTIVATING RECOVERY MODE" (se LLM falhar 3x)
- ✅ "Spatial loop detected" (se houver loop)
- ✅ "Algorithm generating TYPE_TEXT" (se houver EditText)
- ✅ "STUCK STATE detected" (se ficar preso)

**Teste Completo** (demorado, ~3h):
```bash
poetry run python test_v12_complete_180s.py
```

Comparar com baseline V12:
- Taxa de entrada de texto deve aumentar de 3.4% → ~15-20%
- Apps com <10 ações devem executar mais ações
- Não deve haver timeouts de 10+ minutos
- Taxa de sucesso deve manter 100%

---

## RESULTADOS ESPERADOS

### Comparação V12 Baseline vs V12 Refatorado

| Métrica | V12 Baseline | V12 Refatorado (Esperado) | Melhoria |
|---------|--------------|---------------------------|----------|
| **Taxa de sucesso** | 100% | 100% | = |
| **Ações de texto** | 3.4% | 15-20% | +4-5x |
| **Apps <10 ações** | 5 apps | 0-2 apps | -60% a -100% |
| **Timeouts 10+ min** | 5 ocorrências | 0 ocorrências | -100% |
| **Loops espaciais** | Não detectados | Detectados e escapados | ✅ |
| **Estados presos** | Não detectados | Detectados e escapados | ✅ |
| **Annotations UI** | Não enviadas | Enviadas ao LLM | ✅ |
| **Recovery Mode** | Não existe | Ativado após 3 falhas | ✅ |
| **Média ações/app** | 23.4 | 25-30 | +7-28% |
| **Exploração** | Subótima | Otimizada | ✅ |

### Métricas de Validação

**Críticas (deve passar para aprovar refatoração):**
- ✅ Taxa de sucesso ≥ 100% (não regredir)
- ✅ Ações de texto ≥ 10% (mínimo 2-3x melhoria)
- ✅ Apps <10 ações ≤ 2 apps (reduzir de 5 para 0-2)
- ✅ Sem timeouts de 10+ minutos
- ✅ Recovery Mode ativado quando necessário

**Desejáveis (indicam sucesso da refatoração):**
- ✅ Média de ações/app ≥ 25
- ✅ UI Coverage annotations presentes nos logs
- ✅ Loops espaciais detectados e escapados
- ✅ Estados presos detectados e escapados
- ✅ Distribuição mais uniforme de tipos de ação

---

## RISCOS E MITIGAÇÕES

### Risco 1: Timeout de 60s muito curto
**Mitigação**: Se necessário, ajustar para 90s após análise dos logs

### Risco 2: Text input fallback muito agressivo (20%)
**Mitigação**: Se atrapalhar exploração, reduzir para 10%

### Risco 3: Recovery Mode ativa muito cedo (3 falhas)
**Mitigação**: Se necessário, ajustar para 5 falhas

### Risco 4: Stuck state detector muito sensível (5 ações)
**Mitigação**: Se gerar muitos falsos positivos, aumentar para 7-10 ações

---

## CONCLUSÃO

Esta refatoração implementa **6 melhorias cirúrgicas** que:

1. ✅ Ativam funcionalidade existente (UI Coverage)
2. ✅ Adicionam proteções críticas (Timeout, Recovery, Stuck Detection)
3. ✅ Melhoram exploração algorítmica (Text Input, Spatial Loop)
4. ✅ Mantêm simplicidade e elegância do sistema
5. ✅ Não introduzem código legado ou adapters
6. ✅ São testáveis e mensuráveis

**Estimativa de tempo**:
- Implementação: ~2-3 horas
- Teste básico: ~5 minutos
- Teste completo: ~3 horas
- **Total**: ~6 horas

**Impacto esperado**:
- Exploração **4-5x mais eficaz** em apps com formulários
- **Eliminação** de timeouts longos (10+ min → 0)
- **Detecção e escape** de loops e estados presos
- Sistema mais **robusto** e **resiliente**

---

**Próximos passos após implementação:**
1. Comparar resultados V12 Baseline vs V12 Refatorado
2. Ajustar hiperparâmetros se necessário (timeout, thresholds)
3. Documentar aprendizados e métricas
4. Planejar próximas melhorias (V13)

# Plano de Refatoracao: Enriquecimento do Modo LLM (Prompt v15)

**Data**: 20/01/2026
**Objetivo**: Melhorar desempenho do modo LLM passando informacoes do grafo dinamico e memorias
**Motivacao**: pure_algorithm tem 73% method coverage vs 40-46% dos modos LLM

---

## 0. Conhecimento Critico do RV-Agent (PRESERVAR)

### Qwen3-VL Coordinate System
- Coordenadas **normalizadas [0, 1000)** - conversao em `ActionNormalizer.denormalize_qwen_coords()`
- Prompt usa formato **"at position (x, y)"** para LLM copiar coordenadas (MANDATORIO)
- Hit rate ~57.7% em visual_only mode (benchmark rvsec-vision-llm)
- Referencia: `docs/009_qwen3vl_coordinates.md`

### Tool Calling Hibrido
- SGLang nao tem suporte oficial a tool calling para Qwen3-VL
- ~50% native tool_calls, ~50% XML no content
- Parser robusto em `tool_call_parser.py` trata ambos formatos
- Referencia: `docs/022_problema_sglang_native_tools.md`

### Dialog Handling (v13) - MANTER
- Tres tipos: permission dialogs, error/alert dialogs, modal dialogs
- LLM instruido a verificar dialogs **PRIMEIRO** antes de qualquer acao
- NAO remover essa logica no v15

### Parametros LLM Otimizados
- temperature=0.01, top_p=0.6, top_k=50
- Config impact minimal em accuracy (<0.5% variance)
- Referencia: `docs/005_config_sweep.md`

### Formato Critico do Prompt
- Elemento: `"Text" ClassName at position (norm_x, norm_y)`
- **NAO incluir id:resource_id** - LLM usa coordenadas, nao IDs
- Coordenadas sao NORMALIZADAS [0, 1000), NAO pixels
- Formato validado em 12,193 testes com 100% success rate

---

## Regras de Implementacao

1. **Simplicidade**: Codigo simples e elegante, sem complexidades desnecessarias
2. **Sem codigo legado**: Todas alteracoes implementadas diretamente, sem adapters de compatibilidade
3. **Arquivos antigos**: Mover para pasta `backup/` antes de sobrescrever
4. **Comentarios**: Refletir estado atual apenas (nao mencionar migracao, legacy, phase, etc)
5. **Linguagem**: Sem termos promocionais (moderna, sofisticada, elegante, etc) - publico: desenvolvedores/pesquisadores

---

## 1. Problema Identificado

### 1.1 Disparidade de Desempenho

| Metrica | pure_algorithm | multimode | llm_only |
|---------|----------------|-----------|----------|
| Activity Coverage | **80%** | 40% | 40% |
| Method Coverage | **73.3%** | 40.9% | 46.1% |
| UI Coverage | **57.4%** | 23.1% | 17.9% |
| States Discovered | **22** | 7 | 10 |
| Actions/min | **24.1** | 7.9 | 14.1 |

### 1.2 Causa Raiz

O algoritmo tem acesso direto a:
- **DynamicStateGraph**: tracking de acoes por coordenadas
- **6 Scorers numericos**: MopScorer, WtgScorer, GradualDecayScorer, ComponentPriorityScorer, ExecutionCountScorer, FailedActionScorer
- **SuccessorTracker**: re-habilitacao de acoes com sucessores incompletos
- **Pre-marking**: marca acao como executada ANTES da execucao

O LLM recebe apenas:
- Screenshot + elementos UI (com tags `[UNTESTED]`)
- Navigation hint (texto do WTG)
- Resumos textuais das memorias (sem scores numericos)

---

## 2. Solucao Proposta: Prompt v15

### 2.1 Formato Critico das Coordenadas

**IMPORTANTE**: O formato "at position (x, y)" com coordenadas NORMALIZADAS [0, 1000) eh MANDATORIO.
Este formato alcancou 100% de sucesso vs 30% sem coordenadas (validado em 12,193 testes).

Formato atual (v13/v14):
```
1. "Submit" Button at position (500, 416)
2. "Password" EditText at position (500, 312)
3. desc:"Help" ImageView at position (833, 52)
```

### 2.2 Novo Formato v15: Metadata Inline

Adicionar metadata de prioridade/status **inline** na mesma linha, sem perder coordenadas:

```
AVAILABLE ELEMENTS (sorted by priority):

1. [UNTESTED] "Submit" Button at position (500, 416) [score:260 WTG→EncryptActivity]
2. [UNTESTED] "Password" EditText at position (500, 312) [score:210]
3. [UNTESTED] "Algorithm" Spinner at position (500, 208) [score:200]
4. [TESTED-1x] "Cancel" Button at position (185, 416) [score:148 WTG→MainActivity]
5. [TESTED-2x] desc:"Help" ImageView at position (833, 52) [score:98]
```

### 2.3 Explicacao do Formato

| Tag | Significado |
|-----|-------------|
| `[UNTESTED]` | Nunca executado nesta tela |
| `[TESTED-Nx]` | Executado N vezes |
| `[WELL-TESTED]` | Executado 3+ vezes |
| `[score:XXX]` | Score numerico do algoritmo (maior = melhor) |
| `[WTG→Activity]` | WTG indica que leva a Activity (NOT VISITED se nao visitada) |
| `[M]` | Metodo alcanca MOP (monitored operation) |
| `[DM]` | Metodo alcanca MOP diretamente |

### 2.4 Secao AVOID - REMOVIDA

**NAO IMPLEMENTAR**: `record_action_failure()` existe mas nunca eh chamada no workflow.
Os dados de crash estariam sempre vazios. Remover esta secao do v15.

TODO futuro: conectar deteccao de falhas ao grafo se necessario.

### 2.5 Secao SCREEN/COVERAGE (compacta)

Formato claro com nome da activity e contexto:

```
SCREEN: MainActivity | 40% coverage (4/10 actions) | visit #3 | 7 total screens
```

- **Activity name**: identifica a tela atual
- **Coverage**: porcentagem e contagem de acoes testadas nesta tela
- **visit #N**: numero de vezes que esta tela foi visitada
- **total screens**: quantidade de telas descobertas na exploracao

### 2.6 Estrutura Completa do Prompt v15

```
SYSTEM PROMPT (igual v14 com ajustes):
- PRIORITY: Follow element order - higher score = higher priority
- Use exact coordinates from "at position (x, y)"

USER PROMPT:
Iteration {N}
Last: {last_action}

AVAILABLE ELEMENTS (sorted by priority):
{elementos_formatados_com_metadata}

SCREEN: {activity} | {coverage}% coverage ({tested}/{total} actions) | visit #{visit_count} | {total_screens} total screens

{navigation_hint}

Analyze screenshot and select next interaction. Prefer [UNTESTED] elements with high scores.
```

---

## 3. Implementacao

### 3.1 Arquivos a Criar/Modificar

| Arquivo | Acao | Descricao |
|---------|------|-----------|
| `prompts/v15.py` | **CRIAR** | Novo prompt com dialog handling + priority rules |
| `services/prompt_formatter.py` | MODIFICAR | Adicionar `format_ui_elements_for_llm_v15()` sem id:xxx |
| `services/coordinate_extractor.py` | MODIFICAR | Remover id:xxx do formato de elementos |
| `agent/dynamic_state_graph.py` | MODIFICAR | Adicionar `get_screen_line()` (activity + coverage) |
| `agent/nodes/llm_node.py` | MODIFICAR | Usar formatter v15 quando prompt_version=v15 |
| `llm/llm_client.py` | MODIFICAR | Aceitar `screen_line` |
| `agent/nodes/execute_node.py` | MODIFICAR | Pre-marking para acoes LLM |
| `domain/screen_node.py` | MODIFICAR | Adicionar TODO em `record_action_failure()` |

### 3.2 Detalhamento por Arquivo

#### 3.2.1 `prompts/v15.py` (NOVO)

```python
"""
Prompt v15: Enriched LLM context with priority scores inline.

Changes from v14:
- Elements sorted by priority score (highest first)
- Added [UNTESTED]/[TESTED-Nx] tags inline
- Added [score:XXX] and [WTG->Activity] metadata inline
- Added AVOID section for crashed positions only
- Added compact COVERAGE line
- PRESERVED: Dialog handling from v13/v14
- PRESERVED: "at position (x, y)" format with normalized coords [0, 1000)
"""

SYSTEM_PROMPT = """You are an Android UI automation assistant with vision capabilities.

REASONING STEPS (follow in order):
1. SCREEN: What type of screen is this? (dialog, form, list, main menu, etc.)
2. DIALOG CHECK: Is there a blocking dialog? If yes, handle it first.
3. ELEMENTS: Check element list - prefer [UNTESTED] with high [score:XXX]
4. AVOID: Never click positions listed in AVOID section
5. ACTION: Select one action using EXACT coordinates from "at position (x, y)"

DIALOG HANDLING:
- Permission dialogs: Click "Allow", "Accept", "OK", "Continue" (NEVER "Deny")
- Error/alert dialogs: Dismiss FIRST before background interaction
- Modal dialogs: Either interact WITH or dismiss first
- Use android_back() if no dismiss button visible

PRIORITY RULES:
- Elements are sorted by score - PREFER elements at top of list
- [UNTESTED] > [TESTED-1x] > [TESTED-Nx] > [WELL-TESTED]
- [WTG->Activity] indicates navigation target (prioritize if NOT VISITED)
- [DM] and [M] indicate monitored operations (high value)

AVOID - DO NOT CLICK:
- Positions listed in AVOID section (caused crashes)
- Navigation bar at bottom (home, back, recent apps buttons)
- Status bar at top

CRITICAL:
- Use EXACT coordinates from "at position (x, y)" - DO NOT estimate
- TEXT FIELDS: Use android_type_text() for EditText, NOT android_click()

Call the appropriate tool after your analysis."""


def build_user_message(state_info: dict, navigation_hint: str = "",
                       avoid_positions: str = "", coverage_line: str = "") -> str:
    """
    Build user message with enriched context.

    Args:
        state_info: Dict with ui_elements (formatted with inline metadata),
                    last_action, iteration
        navigation_hint: WTG guidance
        avoid_positions: Crashed positions to avoid
        coverage_line: Compact coverage string
    """
    ui_elements = state_info.get('ui_elements', [])
    last_action = state_info.get('last_action')
    iteration = state_info.get('iteration', 0)

    if ui_elements and len(ui_elements) > 0:
        elements_text = ui_elements[0]
    else:
        elements_text = "No interactive elements found."

    context = f"Iteration {iteration}\\n"
    if last_action:
        context += f"Last: {last_action}\\n"

    message = f"""{context}
AVAILABLE ELEMENTS (sorted by priority):
{elements_text}
"""

    if avoid_positions:
        message += f"""
AVOID (crashed):
{avoid_positions}
"""

    if coverage_line:
        message += f"\\n{coverage_line}\\n"

    if navigation_hint:
        message += f"\\n{navigation_hint}\\n"

    message += """
Analyze screenshot and select next interaction. Prefer [UNTESTED] elements with high scores."""

    return message


PROMPT_VERSION = "v15"
```

#### 3.2.2 `services/prompt_formatter.py` (MODIFICAR)

Modificar `format_ui_elements_for_llm` para incluir metadata inline:

```python
def format_ui_elements_for_llm_v15(
    xml_content: str,
    graph: DynamicStateGraph,
    screen_hash: str,
    scorers: List[BaseScorer],
    scorer_context: ScorerContext,
    wtg_targets: Dict[str, str] = None,  # {element_coords -> target_activity}
    device_width: int = 1080,
    device_height: int = 1920,
) -> str:
    """
    Format UI elements with inline priority metadata for v15 prompt.

    CRITICAL: Preserves "at position (x, y)" format with normalized coords.

    Format:
    1. [UNTESTED] "Submit" id:btn_submit Button at position (500, 416) [score:260 WTG->EncryptActivity]
    2. [TESTED-1x] "Cancel" id:btn_cancel Button at position (185, 416) [score:148]

    Args:
        xml_content: UIAutomator XML
        graph: DynamicStateGraph for execution counts
        screen_hash: Current screen hash
        scorers: List of scorers for priority calculation
        scorer_context: Context for scorers
        wtg_targets: Map of element coords to WTG target activities
        device_width/height: For coordinate normalization
    """
    elements = extract_clickable_elements_with_coords(xml_content, device_width, device_height)

    if not elements:
        return "No interactive elements available."

    # Get node for execution counts
    node = graph.states.get(screen_hash) if graph else None

    # Score and enrich each element
    scored_elements = []
    for element in elements:
        coords = element['center_normalized']
        signature = (coords, "CLICK")  # Assume CLICK for scoring

        # Calculate total score
        total_score = 0
        for scorer in scorers:
            # Create mock action for scoring (simplified)
            total_score += scorer.score_by_coords(coords, scorer_context)

        # Determine test status
        exec_count = 0
        if node:
            exec_count = node.action_execution_counts.get(signature, 0)

        if exec_count == 0:
            status_tag = "[UNTESTED]"
        elif exec_count == 1:
            status_tag = "[TESTED-1x]"
        elif exec_count < 3:
            status_tag = f"[TESTED-{exec_count}x]"
        else:
            status_tag = "[WELL-TESTED]"

        # Build metadata suffix
        metadata_parts = [f"score:{total_score}"]

        # Add WTG target if available
        coord_key = f"{coords[0]},{coords[1]}"
        if wtg_targets and coord_key in wtg_targets:
            target = wtg_targets[coord_key]
            metadata_parts.append(f"WTG->{target}")

        metadata = " ".join(metadata_parts)

        scored_elements.append({
            "description": element['description'],
            "status_tag": status_tag,
            "metadata": metadata,
            "score": total_score
        })

    # Sort by score descending
    scored_elements.sort(key=lambda x: x['score'], reverse=True)

    # Format output
    formatted = []
    for i, elem in enumerate(scored_elements, 1):
        # Format: 1. [UNTESTED] "Text" id:xxx Button at position (x, y) [score:260 WTG->Activity]
        line = f"{i}. {elem['status_tag']} {elem['description']} [{elem['metadata']}]"
        formatted.append(line)

    return "\\n".join(formatted)
```

#### 3.2.3 `dynamic_state_graph.py` (MODIFICAR)

Adicionar metodo para obter posicoes a evitar:

```python
def get_crashed_positions(self, screen_hash: str) -> List[str]:
    """
    Get list of positions that caused crashes.

    Returns:
        List of formatted strings: ["(666, 177) crashed 3x", ...]
    """
    node = self.states.get(screen_hash)
    if not node:
        return []

    crashed = []
    for sig in node.failed_actions:
        coords, action_type = sig
        count = node.action_failure_counts.get(sig, 3)
        crashed.append(f"({coords[0]}, {coords[1]}) crashed {count}x")

    return crashed


def get_coverage_line(self, screen_hash: str, total_screens: int) -> str:
    """
    Get compact coverage line for prompt.

    Returns:
        "COVERAGE: 40% (4/10 tested) | Visit #3 | 7 screens discovered"
    """
    node = self.states.get(screen_hash)
    if not node:
        return f"COVERAGE: 0% (0/0 tested) | Visit #1 | {total_screens} screens"

    tested = len(node.executed_actions)
    total = node.total_actions
    pct = (tested / total * 100) if total > 0 else 0

    return f"COVERAGE: {pct:.0f}% ({tested}/{total} tested) | Visit #{node.visit_count} | {total_screens} screens"
```

#### 3.2.4 `llm_node.py` (MODIFICAR)

Usar o novo formatter v15:

```python
def llm_generate_node(agent: "RVAgent", state: AgentState) -> Dict[str, Any]:
    """Generate action using LLM with enriched v15 context."""

    # Use v15 formatter if prompt_version is v15
    if agent.prompt_version == "v15":
        ui_elements_text = format_ui_elements_for_llm_v15(
            xml_content=state.get("ui_xml", ""),
            graph=agent.graph,
            screen_hash=state.get("current_screen_hash", ""),
            scorers=agent.strategy.scorers if agent.strategy else [],
            scorer_context=agent.strategy.build_scorer_context(...) if agent.strategy else None,
            wtg_targets=agent.navigation_guidance.get_wtg_targets(...) if agent.navigation_guidance else None,
        )

        # Get crashed positions
        avoid_positions = ""
        if agent.graph:
            crashed = agent.graph.get_crashed_positions(state.get("current_screen_hash", ""))
            if crashed:
                avoid_positions = "\\n".join(f"- {c}" for c in crashed)

        # Get coverage line
        coverage_line = ""
        if agent.graph:
            coverage_line = agent.graph.get_coverage_line(
                state.get("current_screen_hash", ""),
                len(agent.graph.states)
            )
    else:
        # Use original v13/v14 formatter
        ui_elements_text = format_ui_elements_for_llm(state.get("ui_xml", ""))
        avoid_positions = ""
        coverage_line = ""

    # Get navigation hint (existing logic)
    navigation_hint = ""
    if agent.navigation_guidance and agent.navigation_guidance.is_enabled:
        # ... existing navigation_guidance logic

    result = agent.llm_client.generate_action(
        screen_description=state.get("screen_description"),
        screenshot_b64=state.get("screenshot_b64", ""),
        ui_elements_text=ui_elements_text,
        iteration=state.get("iteration", 0),
        last_action_summary=state.get("action_history_summary"),
        navigation_hint=navigation_hint,
        avoid_positions=avoid_positions,      # NOVO para v15
        coverage_line=coverage_line,          # NOVO para v15
    )

    # ... rest of existing code
```

#### 3.2.5 `llm_client.py` (MODIFICAR)

Aceitar novos parametros para v15:

```python
def generate_action(
    self,
    screen_description,
    screenshot_b64: str,
    ui_elements_text: str,
    iteration: int,
    last_action_summary: str = None,
    navigation_hint: str = "",
    avoid_positions: str = "",      # NOVO para v15
    coverage_line: str = "",        # NOVO para v15
) -> Dict:
    """Generate action with optional v15 enriched context."""

    # Build state_info for prompt
    state_info = {
        'ui_elements': [ui_elements_text],
        'last_action': last_action_summary,
        'iteration': iteration
    }

    # Use appropriate prompt version
    if self.prompt_version == "v15":
        from rv_agent.prompts import v15
        user_msg = v15.build_user_message(
            state_info,
            navigation_hint=navigation_hint,
            avoid_positions=avoid_positions,
            coverage_line=coverage_line,
        )
        system_msg = v15.SYSTEM_PROMPT
    else:
        # v13/v14 logic (existing)
        ...

    # ... rest of LLM call
```

---

## 4. Pre-marking de Acoes para LLM

### 4.1 Problema

O algoritmo marca acoes como executadas ANTES da execucao:
```python
# algorithm_node.py line 353-354
graph.record_action(screen_hash, action_signature)
return selected_action
```

O LLM NAO faz isso. Se o app crashar, a acao nao eh marcada e sera repetida.

### 4.2 Solucao

Adicionar pre-marking no `execute_node.py` para acoes do LLM:

```python
def execute_node(agent: RVAgent, state: AgentState) -> Dict:
    action = state.current_action

    # Pre-mark action if from LLM (algorithm already pre-marks)
    if action.get("source") == "llm" and agent.graph:
        screen_hash = state.current_screen_hash
        signature = ((action["x"], action["y"]), action["action_type"])
        agent.graph.record_action(screen_hash, signature)

    # Execute action
    result = agent.executor.execute(action)

    # If failed, record failure
    if not result.success and agent.graph:
        agent.graph.record_action_failure(screen_hash, signature)

    return {"execution_result": result}
```

---

## 5. Validacao

### 5.1 Teste Comparativo

Rodar experimento com 2 APKs × 3 prompts × 2 modes:

| Config | Prompt | Mode | APKs |
|--------|--------|------|------|
| 1 | v13 | llm_only | hashmypass, hashpass |
| 2 | v14 | llm_only | hashmypass, hashpass |
| 3 | **v15** | llm_only | hashmypass, hashpass |
| 4 | v13 | multimode | hashmypass, hashpass |
| 5 | v14 | multimode | hashmypass, hashpass |
| 6 | **v15** | multimode | hashmypass, hashpass |

**Parametros**:
- Timeout: 180s (3 min)
- Seed: 42
- Repeticoes: 3

**Total**: 6 configs × 2 APKs × 3 seeds = 36 runs

### 5.2 Metricas de Comparacao

| Metrica | Descricao | Esperado v15 |
|---------|-----------|--------------|
| `method_coverage` | Cobertura de codigo | +10-15% vs v13/v14 |
| `ui_coverage_percentage` | Cobertura de UI | +15-20% vs v13/v14 |
| `states_discovered` | Estados unicos | +30% vs v13/v14 |
| `actions_per_minute` | Eficiencia | Similar (latencia LLM domina) |
| `action_repetition_rate` | Taxa de repeticao | -50% vs v13/v14 |

### 5.3 Script de Teste

Criar `run_prompt_comparison.py`:

```python
#!/usr/bin/env python3
"""Compare prompts v13, v14, v15 with 2 APKs."""

APKS = [
    "data/apks_instrumented/com.reddyetwo.hashmypass.app_24.apk/...",
    "data/apks_instrumented/byrne.utilities.hashpass_2.apk/...",
]
PROMPTS = ["v13", "v14", "v15"]
MODES = ["llm_only", "multimode"]
TIMEOUT = 180
SEEDS = [42, 123, 456]

def run_experiment():
    for apk in APKS:
        for prompt in PROMPTS:
            for mode in MODES:
                for seed in SEEDS:
                    run_single(apk, prompt, mode, seed)

def analyze_results():
    # Group by prompt and calculate averages
    # Generate comparison table
    pass
```

---

## 6. Cronograma

| Etapa | Tempo | Descricao |
|-------|-------|-----------|
| 1 | 2h | Criar `prompts/v15.py` |
| 2 | 2h | Modificar `dynamic_state_graph.py` |
| 3 | 1h | Modificar `llm_node.py` |
| 4 | 1h | Modificar `llm_client.py` |
| 5 | 0.5h | Adicionar pre-marking em `execute_node.py` |
| 6 | 0.5h | Criar script de teste |
| 7 | 3h | Rodar experimento (36 runs × 3 min) |
| 8 | 1h | Analisar resultados |
| **Total** | **11h** | |

---

## 7. Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Prompt muito longo | Media | Truncamento | Limitar a 5 priority actions |
| Latencia aumenta | Baixa | UX | Monitorar tokens |
| LLM ignora scores | Media | Sem melhoria | Enfatizar no system prompt |
| Overhead de calculo | Baixa | Performance | Cache de scores |

---

## 8. Arquivos Finais

```
modules/rv-agent/src/rv_agent/
├── prompts/
│   ├── v13.py                    # Existente (dialog handling)
│   ├── v14.py                    # Existente (structured reasoning)
│   └── v15.py                    # NOVO (priority inline + avoid + coverage)
├── services/
│   └── prompt_formatter.py       # MODIFICAR (add format_ui_elements_for_llm_v15)
├── agent/
│   ├── nodes/
│   │   ├── llm_node.py           # MODIFICAR (usar v15 formatter)
│   │   └── execute_node.py       # MODIFICAR (pre-marking para LLM)
│   └── dynamic_state_graph.py    # MODIFICAR (get_crashed_positions, get_coverage_line)
├── llm/
│   └── llm_client.py             # MODIFICAR (avoid_positions, coverage_line params)

modules/rv-agent-validation/
├── run_prompt_comparison.py      # NOVO (script de teste)
└── docs/
    └── 20260120_rvagent_refactoring_llm.md  # Este documento
```

---

## 9. Referencias

- `docs/20260105_rvagent_refactoring.md` - Plano de refatoracao anterior
- `strategies/rvagent_strategy/ranking/scorers.py` - Implementacao dos scorers
- `agent/dynamic_state_graph.py` - Grafo dinamico atual
- Resultados WTG fallback test (20/01/2026)

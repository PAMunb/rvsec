# Plano: Prompt v16 para RVAgent

**Data**: 21/01/2026
**Referencia**: Resultados Mini Phase 2 (docs/20260121_phase2_results.md)

---

## 0. Conhecimento Critico do RV-Agent (PRESERVAR)

### Qwen3-VL Coordinate System
- Coordenadas **normalizadas [0, 1000)** - conversao em `ActionNormalizer.denormalize_qwen_coords()`
- Prompt usa formato **"at position (x, y)"** para LLM copiar coordenadas (MANDATORIO)
- Referencia: `docs/009_qwen3vl_coordinates.md`

### Tool Calling Hibrido
- SGLang nao tem suporte oficial a tool calling para Qwen3-VL
- ~50% native tool_calls, ~50% XML no content
- Parser robusto em `tool_call_parser.py` trata ambos formatos
- Referencia: `docs/022_problema_sglang_native_tools.md`

### Dialog Handling - MANTER
- Tres tipos: permission dialogs, error/alert dialogs, modal dialogs
- LLM instruido a verificar dialogs **PRIMEIRO** antes de qualquer acao
- NAO remover essa logica no v16

### Parametros LLM
- temperature=0.01, top_p=0.6, top_k=50
- Config em `LLM_PARAM_CONFIGS["default"]`

### Formato de Elementos
- Elemento: `"Text" ClassName at position (norm_x, norm_y)`
- Coordenadas sao NORMALIZADAS [0, 1000), NAO pixels
- Formato validado com 100% success rate

---

## 1. Contexto

### 1.1 Resultados Experimentais (166 runs)

| Prompt | Method Coverage | UI Coverage | States | Hit Rate | Latencia |
|--------|-----------------|-------------|--------|----------|----------|
| v13 | 34.8% | 17.9% | 4.6 | 98.3% | 1427ms |
| **v14** | **41.1%** | **18.6%** | **6.1** | 98.4% | 1362ms |
| v15 | 34.5% | 17.0% | 5.1 | **98.7%** | **1355ms** |

### 1.2 Observacao

O prompt v15 apresentou maior precisao (hit rate 98.7%) mas menor cobertura (34.5%).
O prompt v14 obteve melhor cobertura (41.1%) com precisao equivalente.

### 1.3 Baseline de Referencia

| Ferramenta | Method Coverage |
|------------|-----------------|
| Humanoid | 26.79% |
| FastBot | 25.46% |
| APE | 25.29% |
| rv-agent (v14) | 41.1% |

---

## 2. Analise dos Prompts

### 2.1 Estrutura

| Versao | Linhas | Caracteristica Principal |
|--------|--------|--------------------------|
| v13 | 61 | Dialog handling detalhado |
| v14 | 38 | Raciocinio estruturado (4 passos) |
| v15 | 41 | Elementos com scores inline |

### 2.2 Diferencas Relevantes

**v14 inclui regra de variedade**:
```
VARIETY: Explore different elements, avoid clicking same position repeatedly
```

**v15 nao inclui esta regra** e enfatiza seguir a lista ordenada por score.

### 2.3 Hipotese

A regra VARIETY em v14 incentiva navegacao entre telas.
A enfase em scores no v15 causa comportamento repetitivo na mesma tela.

---

## 3. Especificacao do Prompt v16

### 3.1 Objetivos

1. Manter estrutura de raciocinio do v14 (4 passos)
2. Adicionar regra de variedade explicita
3. Priorizar navegacao para novas telas
4. Incluir deteccao de estagnacao

### 3.2 System Prompt

```
You are an Android UI automation assistant.

REASONING STEPS:
1. SCREEN: Identify screen type (dialog, form, list, menu).
2. DIALOG: If blocking dialog present, handle it first.
3. NAVIGATION: Check for actions leading to unvisited screens.
4. ELEMENTS: Select [UNTESTED] element if no navigation available.
5. ACTION: Call tool with coordinates from "at position (x, y)".

DIALOG HANDLING:
- Permission dialogs: Click "Allow", "Accept", "OK"
- Error dialogs: Dismiss before other actions
- Use android_back() if no dismiss button

PRIORITY:
- Actions leading to NEW screens > same-screen actions
- [UNTESTED] > [DM]/[M] > [TESTED-Nx] > [WELL-TESTED]

RULES:
- Do not click the same position consecutively
- If last action had no effect, try a different element
- Explore new screens before testing same screen deeply
- Use exact coordinates from element list

AVOID:
- Navigation bar at bottom
- Status bar at top

Use android_type_text() for EditText fields.
```

### 3.3 User Message

```python
def build_user_message(state_info: dict, navigation_hint: str = "", screen_line: str = "") -> str:
    """Build context message for LLM."""
    ui_elements = state_info.get('ui_elements', [])
    last_action = state_info.get('last_action')
    iteration = state_info.get('iteration', 0)

    elements_text = ui_elements[0] if ui_elements else "No interactive elements found."

    parts = [f"Iteration {iteration}"]
    if last_action:
        parts.append(f"Last: {last_action}")
    parts.append("")
    parts.append("ELEMENTS:")
    parts.append(elements_text)

    if screen_line:
        parts.append("")
        parts.append(screen_line)

    if navigation_hint:
        parts.append("")
        parts.append("NAVIGATION:")
        parts.append(navigation_hint)

    parts.append("")
    parts.append("Select action. Prefer navigation to new screens.")

    return "\n".join(parts)
```

---

## 4. Diferencas v14 vs v16

| Aspecto | v14 | v16 |
|---------|-----|-----|
| Passos de raciocinio | 4 | 5 (inclui NAVIGATION) |
| Regra de variedade | Implicita | Explicita |
| Deteccao de estagnacao | Nao | Sim |
| Prioridade | Elementos | Navegacao primeiro |
| Linhas | 38 | ~35 |

---

## 5. Metricas de Avaliacao

### 5.1 Metricas Primarias

| Metrica | Descricao | Meta |
|---------|-----------|------|
| method_coverage | % metodos executados | > 41.1% |
| states_discovered | Telas unicas visitadas | > 6.1 |
| hit_rate | % acoes que acertam elemento | >= 98% |

### 5.2 Metricas Secundarias

| Metrica | Descricao |
|---------|-----------|
| ui_coverage | % elementos UI interagidos |
| redundancy_rate | % acoes repetidas consecutivas |
| actions_per_minute | Throughput |
| latency_avg | Tempo medio de resposta LLM |

---

## 6. Validacao

### 6.1 Teste Rapido (pre-validacao)

Antes de executar a Fase 2 completa, rodar teste rapido para validar implementacao:

```
Prompts: v14, v16
APKs: 2 (hashmypass, dicer)
Seeds: 1 (42)
Timeout: 180s
Mode: multimode (70/30)

Total: 2 × 2 × 1 = 4 runs (~15 min)
```

**Criterio de sucesso**: v16 executa sem erros e gera metricas comparaveis.

### 6.2 Experimento Fase 2 (validacao completa)

Conforme metodologia em `docs/20260115_rvagent_validacao_multimodal.md`:

```
Prompts: v14, v16
Static Analysis: true, false
APKs: 15
Seeds: 2 (42, 123)
Timeout: 180s
Mode: multimode (70/30)

Total: 2 × 2 × 15 × 2 = 120 runs
Tempo estimado: ~7 horas
```

### 6.3 Hipoteses

| # | Hipotese | Criterio |
|---|----------|----------|
| H1 | v16 > v14 em method_coverage | method_cov(v16) > 41.1% |
| H2 | v16 > v14 em states_discovered | states(v16) > 6.1 |
| H3 | v16 >= v14 em hit_rate | hit_rate(v16) >= 98% |
| H4 | v16 < v14 em redundancy_rate | redundancy(v16) < redundancy(v14) |

---

## 7. Implementacao

### 7.1 Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `modules/rv-agent/src/rv_agent/prompts/v16.py` |

### 7.2 Passos

1. Criar arquivo `v16.py` com SYSTEM_PROMPT e build_user_message
2. Executar teste rapido (4 runs)
3. Verificar logs e metricas
4. Executar Fase 2 completa (120 runs)
5. Analisar resultados

### 7.3 Comandos

```bash
# Teste rapido
cd modules/rv-agent-validation
uv run python scripts/run_v16_quick_test.py

# Fase 2 completa
cd modules/rv-agent-validation
uv run python scripts/run_v16_phase2.py
```

---

## 8. Regras de Implementacao

1. **Simplicidade**: Codigo simples e direto, sem complexidades desnecessarias.

2. **Sem codigo legado**: Alteracoes completas, sem adapters de compatibilidade.

3. **Comentarios**: Refletem apenas estado atual. Sem mencoes a versoes anteriores.

4. **Backup**: Arquivos substituidos movidos para `backup/`.

5. **uv**: Todos comandos via `uv run`.

---

## 9. Riscos

| Risco | Mitigacao |
|-------|-----------|
| Reducao de hit_rate | Manter instrucao de coordenadas exatas |
| Incompatibilidade com tool binding | Manter mesma interface de funcao |
| Aumento de latencia | Manter prompt compacto (<40 linhas) |

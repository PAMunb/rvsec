# Prompt Engineering e Fallback Parser

Data: 2025-12-23

## Problema Identificado

Durante os testes iniciais, observamos:
- **Tool call rate: ~70%** - O modelo não chamava a tool em 30% dos casos
- **Hit rate: ~68%** - Baixa precisão geral

### Análise dos NO_TOOL Cases

Ao analisar o conteúdo das respostas sem tool call, descobrimos:

```
Content: <tool_call>
{"name": "android_click", "arguments": {"x": 352, 782, "element_description": "Deny button"...
```

**O modelo ESTAVA tentando chamar a tool**, mas:
1. Usava formato `<tool_call>` XML em vez do formato OpenAI estruturado
2. JSON malformado: `"x": 352, 782` em vez de `"x": 352, "y": 782`

O parser `qwen` do SGLang não reconhecia esse formato.

## Solução: Fallback Parser

Implementamos um parser de fallback em `src/inference/sglang_client.py`:

```python
def _extract_tool_calls_from_content(self, content: str) -> list[dict]:
    """Extrai tool calls de <tool_call> tags no content."""
    pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
    matches = re.findall(pattern, content, re.DOTALL)
    # Parse JSON e corrige malformações
    ...

def _fix_malformed_json(self, s: str) -> str | None:
    """Corrige JSON malformado do modelo."""
    # "x": 352, 782 -> "x": 352, "y": 782
    fixed = re.sub(r'"x":\s*(\d+),\s*(\d+)', r'"x": \1, "y": \2', s)
    return fixed
```

### Fluxo de Parsing

```
Resposta do modelo
       │
       ▼
┌─────────────────────────────┐
│ Verifica tool_calls struct  │
│ (formato OpenAI)            │
└─────────────┬───────────────┘
              │ Vazio?
              ▼
┌─────────────────────────────┐
│ Fallback: extrai de content │
│ (<tool_call> tags)          │
└─────────────┬───────────────┘
              │ JSON inválido?
              ▼
┌─────────────────────────────┐
│ Corrige malformações        │
│ ("x": 352, 782 → "x": 352,  │
│  "y": 782)                  │
└─────────────────────────────┘
```

## Prompt Engineering

Testamos 3 variações de prompt:

### v1 (Original)
```
You are an Android UI automation assistant...
When asked to click on an element, you MUST use the android_click tool...
```

### v2 (Strict) - VENCEDOR
```
You are an Android UI automation agent. You MUST use tools to interact with the screen.

CRITICAL RULES:
1. You MUST call the android_click tool for EVERY click request
2. NEVER respond with text only - ALWAYS use the tool
3. Use the exact coordinates provided in the UI description
```

### v3 (Minimal)
```
Android UI automation agent. Screen: {width}x{height}px.
ALWAYS use android_click tool. NEVER respond with text only.
```

## Resultados Comparativos

### Sem Fallback Parser (50 screenshots, 3 reps)

| Prompt | Hit Rate | Tool Call Rate | NO_TOOL | MISSES |
|--------|----------|----------------|---------|--------|
| v1 | 41.7% | 60.7% | 33 | 16 |
| v2 | 73.8% | 85.7% | 12 | 10 |
| v3 | 63.1% | 70.2% | 25 | 6 |

### Com Fallback Parser (20 screenshots, 3 reps)

| Prompt | Hit Rate | Tool Call Rate | NO_TOOL | MISSES |
|--------|----------|----------------|---------|--------|
| v2 | **86.2%** | **100%** | **0** | 24 |

## Configuração Final

```python
config = EvaluationConfig(
    prompt_style="v2",  # Strict prompt
    temperature=0.25,
    # ... fallback parser ativo automaticamente
)
```

## MISSES Restantes

Os erros restantes são erros genuínos do modelo:

| Elemento | Distância | Frequência |
|----------|-----------|------------|
| CheckBox:'Adventure' | ~109px | Consistente |
| LinearLayout genérico | ~175px | Consistente |

Esses elementos têm características visuais que confundem o modelo:
- Checkboxes com múltiplos items adjacentes
- LinearLayouts sem texto identificador claro

## Arquivos Modificados

- `src/inference/sglang_client.py` - Fallback parser
- `src/evaluator/evaluator.py` - Prompt templates v1/v2/v3
- `tests/test_evaluator.py` - Flag `--prompt-style`

## Comando para Benchmark

```bash
# Com prompt v2 (strict) e fallback parser ativo
poetry run python tests/test_evaluator.py \
    --prompt-style v2 \
    --repetitions 5
```

## Conclusão

A combinação de **prompt v2 (strict)** + **fallback parser** elevou:
- Tool call rate: 70% → **100%**
- Hit rate: 68% → **86%**

O fallback parser é essencial porque o Qwen3-VL frequentemente gera tool calls no formato XML `<tool_call>` em vez do formato OpenAI estruturado.

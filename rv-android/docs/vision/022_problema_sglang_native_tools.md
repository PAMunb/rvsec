# Problema: Tool Calling Inconsistente com Qwen3-VL no SGLang

**Data**: 2026-01-07
**Status**: Investigado
**Impacto**: Médio (sistema funciona com fallback, mas comportamento não é ideal)

---

## 1. Resumo Executivo

Durante a validação do RV-Agent com Qwen3-VL-4B-Instruct via SGLang, observamos comportamento inconsistente no tool calling: às vezes o modelo retorna `tool_calls` estruturados (native), outras vezes retorna XML no campo `content` (fallback). Esta investigação identificou a causa raiz e documentou as possíveis soluções.

**Causa Raiz**: O SGLang não possui suporte oficial a tool calling para modelos Qwen3-VL (vision/multimodal). O comportamento observado é resultado da falta de um chat template adequado para injetar as definições de tools no formato esperado pelo modelo.

---

## 2. Sintomas Observados

### 2.1 Logs da Validação E1

```
2026-01-07 16:15:12 - LLM response: tool_calls=1, strategy=xml, tokens=2162+27, latency=829ms
2026-01-07 16:15:15 - LLM response: tool_calls=1, strategy=xml, tokens=2277+27, latency=756ms
2026-01-07 16:15:19 - LLM response: tool_calls=1, strategy=native, tokens=2553+44, latency=935ms
2026-01-07 16:15:22 - LLM response: tool_calls=1, strategy=native, tokens=2525+28, latency=829ms
2026-01-07 16:15:26 - LLM response: tool_calls=1, strategy=xml, tokens=2298+27, latency=713ms
```

### 2.2 Padrão Observado

| Estratégia | Output Tokens | Latência | Frequência |
|------------|---------------|----------|------------|
| `xml` | ~27 tokens | ~700-800ms | ~50% |
| `native` | 28-156 tokens | ~800-2100ms | ~50% |

### 2.3 Diferença Entre Estratégias

**Native** (`response.tool_calls` populado):
```python
response.tool_calls = [
    {'name': 'android_click', 'args': {'x': 540, 'y': 143}, 'id': 'call_xxx'}
]
response.content = "The current screen shows..."  # reasoning também presente
```

**XML Fallback** (`response.tool_calls` vazio, tool call no content):
```python
response.tool_calls = []
response.content = """<tool_call>
{"name": "android_click", "arguments": {"x": [499, 141]}
</tool_call>"""
```

---

## 3. Testes Realizados

### 3.1 Teste 1: Prompt Simples (10 iterações)

**Arquivo**: `modules/rv-agent/validation/test_native_vs_xml.py`

```python
messages = [
    SystemMessage(content="You are an Android UI assistant. Use the available tools."),
    HumanMessage(content=[
        {"type": "text", "text": "Click on the first button you see."},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
    ])
]
```

**Resultado**: 0% native, 100% XML fallback

### 3.2 Teste 2: Prompt V12 Completo (10 iterações)

**Arquivo**: `modules/rv-agent/validation/test_v12_prompt.py`

Usando o prompt V12 real do RV-Agent com UI elements formatados.

**Resultado**: 50% native, 50% XML

```
Test 1: XML    | output_tokens=109
Test 2: XML    | output_tokens=152
Test 3: XML    | output_tokens=145
Test 4: XML    | output_tokens=152
Test 5: XML    | output_tokens=165
Test 6: NATIVE | output_tokens=134
Test 7: NATIVE | output_tokens=135
Test 8: NATIVE | output_tokens=152
Test 9: NATIVE | output_tokens=156
Test 10: NATIVE | output_tokens=152
```

### 3.3 Teste 3: Efeito da Iteração

**Arquivo**: `modules/rv-agent/validation/test_iteration_effect.py`

Testando se o número da iteração afeta o comportamento.

**Resultado**: Não determinístico

```
Iteration 0:  5/5 NATIVE (100%)
Iteration 5:  4/5 NATIVE (80%)
Iteration 10: 3/5 NATIVE (60%)
```

### 3.4 Conclusão dos Testes

O comportamento é **parcialmente não-determinístico**. Fatores que parecem influenciar:
- Complexidade/tamanho do prompt
- Possivelmente KV cache do SGLang
- Estado interno do modelo
- temperature=0.1 ainda permite alguma variação

---

## 4. Investigação da Causa Raiz

### 4.1 Documentação do SGLang para Qwen3-VL

**Fonte**: [SGLang Qwen3-VL Usage](https://docs.sglang.io/basic_usage/qwen3_vl.html)

A documentação oficial do SGLang para Qwen3-VL **NÃO menciona suporte a tool calling**. Apenas documenta:
- Image input
- Video input
- Configurações de memória e performance

**Citação relevante**: "Qwen3-VL is Alibaba's latest multimodal large language model with strong text, vision, and reasoning capabilities. SGLang supports Qwen3-VL Family of models with Image and Video input support."

Não há menção a `--tool-call-parser` para modelos VL.

### 4.2 Suporte a Tool Calling no SGLang

**Fonte**: [SGLang Tool Parser](https://docs.sglang.io/advanced_features/tool_parser.html)

Parsers disponíveis:
- `llama3`, `llama4`
- `mistral`
- `qwen25` (deprecated, usar `qwen`)
- `deepseekv3`
- `hermes`

**Nenhum parser específico para modelos VL/multimodal**.

### 4.3 Issues Relacionados no GitHub

#### Issue #29192 (vLLM) - Tool Calling Parsers Fail

**Fonte**: [vLLM Issue #29192](https://github.com/vllm-project/vllm/issues/29192)

> "When using tool calling with Qwen2.5-Coder models, the model correctly generates tool calls in `<tools>` XML format, but both `qwen3_xml` and `qwen3_coder` parsers fail to extract these tool calls into the tool_calls array in the API response. The tool call information remains in the content field but the tool_calls array stays empty."

**Relevância**: Mesmo problema que observamos - tool calls aparecem no `content` em vez de `tool_calls`.

#### Issue #1093 (Qwen3-VL) - Tool Call Issues with VL Models

**Fonte**: [Qwen3-VL Issue #1093](https://github.com/QwenLM/Qwen3-VL/issues/1093)

> "The default chat templates provided for Qwen2.5-VL-7B-Instruct, Qwen2.5-VL-32B-Instruct or Qwen2.5-VL-72B-Instruct don't seem to support tool usage out of the box."

**Solução proposta**: Criar um **custom chat template** que merge o formato multimodal com o formato de tool calling.

#### Issue #9184 (SGLang) - Tool Call Tags in Content

**Fonte**: [SGLang Issue #9184](https://github.com/sgl-project/sglang/issues/9184)

> "When using Qwen3-32B with qwen25 tool-call parser, XML `<tool_call>` tags occasionally appear in the response's 'content' field instead of being properly parsed into the 'tool_calls' field."

**Resolução**: O autor descobriu que era um problema de **prompt**, não do SGLang.

#### Issue #21887 (LangChain) - bind_tools with base_url

**Fonte**: [LangChain Issue #21887](https://github.com/langchain-ai/langchain/issues/21887)

> "ChatOpenAI with 'bind_tools', when using 'base_url' with another API server, doesn't call 'tool' and doesn't response 'tool_calls'."

**Status**: Fechado como "not planned" - considerado limitação de compatibilidade de terceiros.

### 4.4 Recomendações Oficiais da Qwen

**Fonte**: [Qwen Function Calling](https://qwen.readthedocs.io/en/latest/framework/function_call.html)

1. **Usar Qwen-Agent**: Framework Python que encapsula templates e parsers internamente
2. **Usar Hermes-style**: Formato recomendado para maximizar performance de function calling
3. **Evitar ReAct com reasoning models**: Modelo pode gerar stopwords no pensamento

**Citação**:
> "Qwen recommends using Hermes-style tool use for Qwen3 to maximize function calling performance."

---

## 5. Formato Hermes-Style Tool Calling

### 5.1 O Que É

Hermes é um formato padronizado criado pela [NousResearch](https://github.com/NousResearch/Hermes-Function-Calling) que usa XML tags para delimitar tool calls.

### 5.2 Estrutura do Prompt

```
<|im_start|>system
You are a function calling AI model. You are provided with function
signatures within <tools></tools> XML tags. You may call one or more
functions to assist with the user query. Don't make assumptions about
what values to plug into functions. Here are the available tools:

<tools>
[{"type": "function", "function": {"name": "android_click",
  "description": "Click on UI element",
  "parameters": {"type": "object", "properties": {"x": {"type": "integer"},
  "y": {"type": "integer"}}, "required": ["x", "y"]}}}]
</tools>

For each function call return a json object with function name and
arguments within <tool_call></tool_call> XML tags as follows:
<tool_call>
{"name": <function-name>, "arguments": <args-dict>}
</tool_call>
<|im_end|>
```

### 5.3 Output do Modelo

```
<|im_start|>assistant
<tool_call>
{"name": "android_click", "arguments": {"x": 540, "y": 350}}
</tool_call>
<|im_end|>
```

### 5.4 Observação Crítica

**O Qwen3-VL já está gerando output no formato Hermes!**

```xml
<tool_call>
{"name": "android_click", "arguments": {"x": [499, 141]}
</tool_call>
```

O problema não é o modelo - é que o **parser do SGLang/LangChain não está sendo ativado corretamente**.

---

## 6. Análise do Fluxo Atual

### 6.1 Arquitetura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   LangChain     │     │     SGLang      │     │   Qwen3-VL      │
│   ChatOpenAI    │────▶│   Server        │────▶│   Model         │
│   bind_tools()  │     │   (no parser)   │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │ Injeta tools no       │ Não processa         │ Gera output
        │ formato OpenAI        │ tool_calls           │ Hermes-style
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ RESULTADO: tool_calls vazio, XML no content                     │
│            OU às vezes tool_calls populado (não-determinístico) │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Problema Identificado

1. **LangChain `bind_tools()`**: Injeta definições de tools mas **não injeta o system prompt Hermes**
2. **SGLang**: Não foi iniciado com `--tool-call-parser hermes`
3. **Resultado**: O modelo "adivinha" que deve usar `<tool_call>` tags, mas nem sempre

### 6.3 Por Que Funciona Às Vezes?

Hipóteses:
1. O modelo foi treinado com formato Hermes e às vezes "lembra" de usá-lo
2. KV cache do SGLang pode influenciar
3. Variações de sampling com temperature=0.1

---

## 7. Solução Atual (Fallback Parser)

O sistema RV-Agent já implementa um parser robusto que extrai tool calls do content.

### 7.1 Implementação

**Arquivo**: `modules/rv-agent/src/rv_agent/llm/tools/tool_call_parser.py`

```python
def parse_tool_calls_from_text_with_strategy(response_content: str) -> tuple[list, str]:
    """
    Estratégias de parsing (em ordem de prioridade):
    1. XML <tool_call> tags (formato Hermes/Qwen)
    2. JSON array
    3. Single JSON object
    4. Markdown code blocks
    5. Pythonic function calls
    """
```

### 7.2 Fluxo no LLMClient

**Arquivo**: `modules/rv-agent/src/rv_agent/llm/llm_client.py`

```python
def _extract_tool_calls(self, response: AIMessage) -> tuple[list, str]:
    # 1. Tenta native tool calls primeiro
    if hasattr(response, "tool_calls") and response.tool_calls:
        return response.tool_calls, "native"

    # 2. Fallback: parse do content
    if response.content:
        parsed, strategy = parse_tool_calls_with_strategy(response.content)
        if parsed:
            return parsed, strategy  # "xml", "json_array", etc.

    return [], "none"
```

### 7.3 Eficácia

O fallback parser tem 100% de sucesso quando o modelo gera tool calls (em qualquer formato).

---

## 8. Possíveis Soluções

### 8.1 Solução 1: Iniciar SGLang com Parser Hermes

**Complexidade**: Baixa
**Risco**: Médio (pode não funcionar com VL models)

```bash
python -m sglang.launch_server \
    --model-path Qwen/Qwen3-VL-4B-Instruct \
    --tool-call-parser hermes \
    --port 30000
```

**Status**: Não testado. A documentação não confirma suporte para modelos VL.

### 8.2 Solução 2: Injetar System Prompt Hermes

**Complexidade**: Média
**Risco**: Baixo

Modificar o prompt V12 para incluir o formato Hermes:

```python
SYSTEM_PROMPT = """You are a function calling AI model...

<tools>
{tools_json}
</tools>

For each function call return JSON within <tool_call></tool_call> tags.
"""
```

**Prós**: Não requer mudanças no servidor
**Contras**: Aumenta tamanho do prompt, pode conflitar com LangChain bind_tools

### 8.3 Solução 3: Usar Qwen-Agent

**Complexidade**: Alta
**Risco**: Alto (requer refatoração significativa)

Substituir LangChain por Qwen-Agent:

```python
from qwen_agent import Agent

agent = Agent(
    llm={"model": "qwen3-vl-4b", "model_server": "http://..."},
    function_list=[android_click, android_back, ...]
)
response = agent.run(messages)
```

**Prós**: Solução oficial da Qwen
**Contras**: Requer reescrever a integração LLM

### 8.4 Solução 4: Manter Fallback Parser (Atual)

**Complexidade**: Nenhuma (já implementado)
**Risco**: Nenhum

Aceitar que o comportamento é não-determinístico e confiar no fallback parser.

**Prós**: Já funciona, sem mudanças necessárias
**Contras**: Não é "elegante", depende de parsing de texto

---

## 9. Recomendação

**Recomendação**: Manter a Solução 4 (Fallback Parser) por enquanto.

**Justificativa**:
1. O sistema já funciona com 100% de sucesso (native + xml fallback)
2. Não há documentação oficial de tool calling para Qwen3-VL no SGLang
3. O fallback parser é robusto e bem testado
4. Mudanças no servidor SGLang requerem validação extensiva

**Ação Futura**: Quando o SGLang adicionar suporte oficial a tool calling para modelos VL, revisitar esta decisão.

---

## 10. Métricas para Monitoramento

O sistema já coleta estatísticas do parser:

```python
parser_stats.get_stats()
# {
#     "total_calls": 100,
#     "successful_parses": 100,
#     "strategy_success_counts": {
#         "native": 48,
#         "xml_tool_call": 52,
#         ...
#     }
# }
```

**Recomendação**: Incluir essas métricas no relatório de validação para monitorar a distribuição native vs xml ao longo do tempo.

---

## 11. Referências

### Documentação Oficial

1. [SGLang Qwen3-VL Usage](https://docs.sglang.io/basic_usage/qwen3_vl.html)
2. [SGLang Tool Parser](https://docs.sglang.io/advanced_features/tool_parser.html)
3. [Qwen Function Calling](https://qwen.readthedocs.io/en/latest/framework/function_call.html)
4. [Qwen SGLang Deployment](https://qwen.readthedocs.io/en/latest/deployment/sglang.html)
5. [vLLM Tool Calling](https://docs.vllm.ai/en/latest/features/tool_calling/)

### GitHub Issues

6. [vLLM #29192 - Tool Calling Parsers Fail](https://github.com/vllm-project/vllm/issues/29192)
7. [Qwen3-VL #1093 - Tool Call Issues with VL Models](https://github.com/QwenLM/Qwen3-VL/issues/1093)
8. [SGLang #9184 - Tool Call Tags in Content](https://github.com/sgl-project/sglang/issues/9184)
9. [SGLang #13238 - Qwen3-VL Accuracy Discrepancy](https://github.com/sgl-project/sglang/issues/13238)
10. [LangChain #21887 - bind_tools with base_url](https://github.com/langchain-ai/langchain/issues/21887)

### Formato Hermes

11. [NousResearch Hermes Function Calling](https://github.com/NousResearch/Hermes-Function-Calling)
12. [Hermes Function Calling Dataset](https://huggingface.co/datasets/NousResearch/hermes-function-calling-v1)

### Modelos

13. [Qwen3-VL GitHub](https://github.com/QwenLM/Qwen3-VL)
14. [Qwen3-VL-8B-Instruct HuggingFace](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct)
15. [Alibaba Cloud Blog - Qwen3-VL](https://www.alibabacloud.com/blog/qwen3-vl-sharper-vision-deeper-thought-broader-action_602584)

---

## 12. Anexos

### A. Scripts de Teste

Localização: `modules/rv-agent/validation/`

- `test_tool_binding.py` - Teste básico de tool binding
- `test_native_vs_xml.py` - Investigação de estratégias
- `test_v12_prompt.py` - Teste com prompt real
- `test_iteration_effect.py` - Teste de efeito da iteração

### B. Logs Relevantes

Localização: `modules/rv-agent/validation_results/E1_baseline.log`

### C. Código do Parser

Localização: `modules/rv-agent/src/rv_agent/llm/tools/tool_call_parser.py`

---

*Documento gerado durante investigação de problema de tool calling em 2026-01-07*

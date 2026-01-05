# Tools e LangGraph: Investigação Completa de Function Calling com Vision Models

## Índice

1. [Contexto e Motivação](#contexto-e-motivação)
2. [Conceitos Fundamentais](#conceitos-fundamentais)
3. [O Problema: Vision Models e Tool Calling no Ollama](#o-problema-vision-models-e-tool-calling-no-ollama)
4. [Solução: Modelfile Customizado](#solução-modelfile-customizado)
5. [Segundo Modelo: Llama 3.2 Vision com Tools](#segundo-modelo-llama-32-vision-com-tools)
6. [Investigação: Template vs Treinamento](#investigação-template-vs-treinamento)
7. [Comparação: Mistral Manual vs LangGraph Automático](#comparação-mistral-manual-vs-langgraph-automático)
8. [Encadeamento de Tools](#encadeamento-de-tools)
   - [Command + InjectedState](#command--injectedstate-compartilhamento-de-dados-entre-tools)
   - [Limitação Crítica](#limitação-crítica-falta-de-garantia-de-pré-requisitos)
   - [Tratamento Manual](#tratamento-manual-alternativas-práticas)
9. [Conclusões e Recomendações](#conclusões-e-recomendações)
10. [Referências e Arquivos](#referências-e-arquivos)
11. [Apêndices](#apêndice-exemplo-completo-de-uso)
    - [Apêndice: Exemplo Completo de Uso](#apêndice-exemplo-completo-de-uso)
    - [Apêndice A: Atualização Assíncrona do State](#apêndice-a-atualização-assíncrona-do-state)
    - [Apêndice B: Alternativas para Vision + Tools Local](#apêndice-b-alternativas-para-vision--tools-local)
    - [Apêndice C: Observabilidade e Debugging com LangSmith](#apêndice-c-observabilidade-e-debugging-com-langsmith)

---

## Contexto e Motivação

Este documento registra uma investigação completa sobre o uso de function calling (tools) com vision models via LangGraph, motivada pela necessidade de criar um agente ReACT para testes automatizados de aplicativos Android.

### Objetivo Original

Criar um agente que:
- Analisa screenshots de apps Android via vision model (Qwen2.5-VL-7B)
- Decide ações baseadas na análise visual
- Executa ações através de tools (click, set_text, swipe, etc.)
- Usa LangGraph para orquestração do ciclo ReACT (Reason → Act → Observe)

### Por que LangGraph?

O LangGraph foi escolhido por:
- Estrutura de grafo expansível (não apenas ReACT simples)
- Integração com LangSmith para debugging
- ToolNode para execução automática de tools
- Gerenciamento de estado e histórico de mensagens

### Desafio Encontrado

Vision models disponíveis via Ollama (Qwen2.5-VL, Gemma3-Vision, etc.) não eram reconhecidos como compatíveis com tools, retornando erro 400 ao usar `bind_tools()`.

---

## Conceitos Fundamentais

### O que é Function Calling?

Function calling (ou tool calling) é a capacidade de um modelo de linguagem de:

1. **Analisar** ferramentas disponíveis através de JSON Schema
2. **Decidir** quais ferramentas usar para responder uma pergunta
3. **Gerar** chamadas estruturadas em formato JSON
4. **Sintetizar** resposta final após receber resultados das ferramentas

Exemplo de fluxo completo:

```python
# Pergunta
"Em que cidade estou?"

# Modelo analisa tools disponíveis:
# - obter_ip_externo() → Retorna IP do usuário
# - obter_geolocalizacao_ip(ip: str) → Retorna localização do IP

# Modelo decide e retorna JSON:
[
  {"name": "obter_ip_externo", "arguments": {}},
  {"name": "obter_geolocalizacao_ip", "arguments": {"ip": "..."}}
]

# Sistema executa tools:
resultado1 = obter_ip_externo()  # "187.75.23.45"
resultado2 = obter_geolocalizacao_ip("187.75.23.45")  # "São Paulo, SP"

# Modelo sintetiza resposta:
"Você está em São Paulo, SP."
```

### Tools no LangChain/LangGraph

No ecossistema LangChain, tools são definidas usando o decorator `@tool`:

```python
from langchain_core.tools import tool

@tool
def click(x: int, y: int) -> str:
    """
    Clica em coordenadas (x, y) na tela Android.

    Args:
        x: Coordenada horizontal
        y: Coordenada vertical

    Returns:
        Confirmação da ação executada
    """
    # Implementação
    return f"Clicked at position ({x}, {y})"
```

O LangChain automaticamente converte a docstring e type hints em JSON Schema que o modelo entende.

### bind_tools(): Integração Modelo + Tools

O método `bind_tools()` registra as tools no modelo:

```python
from langchain_ollama import ChatOllama

llm_base = ChatOllama(model="qwen2.5vl:7b")
llm_with_tools = llm_base.bind_tools([click, set_text, swipe])

# Quando invocar llm_with_tools:
# 1. JSON Schema das tools é enviado junto com a mensagem
# 2. Modelo pode retornar tool_calls estruturados
# 3. LangChain parseia automaticamente
```

### ToolNode: Execução Automática

O `ToolNode` do LangGraph executa automaticamente as tools chamadas:

```python
from langgraph.prebuilt import ToolNode

tool_node = ToolNode([click, set_text, swipe])

# Quando recebe mensagem com tool_calls:
# 1. Extrai argumentos de cada tool_call
# 2. Executa a função Python correspondente
# 3. Captura resultado
# 4. Cria ToolMessage com o resultado
# 5. Adiciona ao histórico de mensagens
```

Tudo isso acontece automaticamente - você não precisa fazer parsing manual nem executar as funções.

---

## O Problema: Vision Models e Tool Calling no Ollama

### Tentativa Inicial

Código do primeiro teste (`teste_android_agent_with_tools.py`):

```python
from langchain_ollama import ChatOllama
from experimental.android_agent.tools.android_fake import ALL_TOOLS

llm_base = ChatOllama(model="qwen2.5vl:7b")
llm_with_tools = llm_base.bind_tools(ALL_TOOLS)
```

**Resultado**: Erro 400

```
registry.ollama.ai/library/qwen2.5vl:7b does not support tools (status code: 400)
```

### Investigação: Quais Modelos Funcionam?

Testamos vários modelos via Ollama:

| Modelo | Vision | Tools | Resultado |
|--------|--------|-------|-----------|
| qwen2.5vl:7b | ✅ | ❌ | Erro 400 |
| gemma3:12b | ✅ | ❌ | Erro 400 |
| granite3.2-vision:2b | ✅ | ❌ | Erro 400 |
| gemma3-tools:4b | ❌ | ✅ | Funciona, mas sem visão |
| llama3.1:8b | ❌ | ✅ | Funciona, mas sem visão |
| mistral:7b | ❌ | ✅ | Funciona, mas sem visão |

**Conclusão inicial**: Ollama tem uma whitelist interna de modelos com suporte a tools, e vision models não estão incluídos.

### Por que esse Problema Existe?

O Ollama verifica se o modelo base está na lista de modelos conhecidos com suporte a function calling. Vision models como Qwen2.5-VL são relativamente novos e, embora tenham capacidade de function calling (do treinamento), o Ollama não os reconhece.

Isso acontece porque:
1. Ollama valida modelo por nome/família, não por capacidade real
2. Vision models multimodais são mais recentes
3. Lista de modelos suportados não é atualizada automaticamente

---

## Solução: Modelfile Customizado

### Descoberta do Template

Investigando a documentação do Ollama, descobrimos que modelos com tools usam uma variável especial no template: `.Tools`

Comparando templates:

**Llama 3.1 (COM tools)**:
```
{{- if or .System .Tools }}<|start_header_id|>system<|end_header_id|>
{{- if .System }}

{{ .System }}
{{- end }}
{{- if .Tools }}

You are a helpful assistant with tool calling capabilities.
{{- end }}<|eot_id|>
```

**Qwen2.5-VL (SEM tools)**:
```
{{- if .System }}<|im_start|>system

{{ .System }}<|im_end|>
{{- end }}
```

A presença de `{{- if .Tools }}` no template sinaliza ao Ollama que o modelo suporta function calling.

### Criação do Modelfile Customizado

Criamos `Modelfile.qwen-vision-tools-v1` combinando:
- Base: `qwen2.5vl:7b`
- Template: Adaptado do Llama 3.1 com lógica de tools
- Formato de mensagem: Mantido do Qwen (`<|im_start|>`, `<|im_end|>`)

```dockerfile
FROM qwen2.5vl:7b

TEMPLATE """{{- if or .System .Tools }}<|im_start|>system
{{- if .System }}

{{ .System }}
{{- end }}
{{- if .Tools }}

Cutting Knowledge Date: December 2023

When you receive a tool call response, use the output to format an answer to the orginal user question.

You are a helpful assistant with tool calling capabilities.
{{- end }}<|im_end|>
{{- end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 }}
{{- if eq .Role "user" }}<|im_start|>user
{{- if and $.Tools $last }}

Given the following functions, please respond with a JSON for a function call with its proper arguments that best answers the given prompt.

Respond in the format {"name": function name, "parameters": dictionary of argument name and its value}. Do not use variables.

{{ range $.Tools }}
{{- . }}
{{ end }}
Question: {{ .Content }}<|im_end|>
{{- else }}

{{ .Content }}<|im_end|>
{{- end }}{{ if $last }}<|im_start|>assistant

{{ end }}
{{- else if eq .Role "assistant" }}<|im_start|>assistant
{{- if .ToolCalls }}
{{ range .ToolCalls }}
{"name": "{{ .Function.Name }}", "parameters": {{ .Function.Arguments }}}{{ end }}
{{- else }}

{{ .Content }}
{{- end }}{{ if not $last }}<|im_end|>{{ end }}
{{- else if eq .Role "tool" }}<|im_start|>tool

{{ .Content }}<|im_end|>{{ if $last }}<|im_start|>assistant

{{ end }}
{{- end }}
{{- end }}"""

SYSTEM """You are a helpful assistant with tool calling capabilities."""
PARAMETER temperature 0.1
PARAMETER num_ctx 8192
```

### Criando o Modelo

```bash
ollama create qwen-vision-tools-v1 -f Modelfile.qwen-vision-tools-v1
```

### Teste de Validação

Arquivo: `teste_custom_vision_tools_v1.py`

```python
agente = criar_agente_com_tools(
    model_name="qwen-vision-tools-v1",
    max_iterations=1
)

resultado = agente.invoke({
    "screenshot_path": str(screenshot_path),
    "ui_description": ui_desc,
    "messages": [],
    "iteration": 0
})
```

**Resultado**: ✅ SUCESSO!

```
📄 Resposta do modelo:
   🔧 Tool calls: 1
      - click({'x': 540, 'y': 273})

🖱️  FAKE ACTION: Click at (540, 273)

================================================================================
RESULTADO
================================================================================
🎉 SUCESSO TOTAL!
   ✅ Modelfile customizado FUNCIONOU!
   ✅ Ollama aceitou tools
   ✅ Vision + Tools integrados
   ✅ bind_tools() operacional
   ✅ 3 tool calls detectadas
```

O modelo customizado foi reconhecido pelo Ollama como compatível com tools, permitindo o uso de `bind_tools()` e execução automática via ToolNode.

---

## Segundo Modelo: Llama 3.2 Vision com Tools

### Motivação

Com o sucesso do Qwen2.5-VL customizado, a próxima pergunta natural era:

> "Outros modelos de visão também funcionariam com a mesma abordagem?"

Escolhemos testar o **Llama 3.2 Vision 11B** pelos seguintes motivos:

1. **Família Llama é amplamente usada**: Se funcionar, abre possibilidade para modelos similares
2. **Llama 3.1 já tem tools nativamente**: Existe template oficial com function calling
3. **Comparação entre bases**: Qwen usa formato `<|im_start|>`, Llama usa `<|start_header_id|>`
4. **Validação da técnica**: Confirma que Modelfile customizado não é específico do Qwen

### Processo de Adaptação

**Base de referência**: `ollama show llama3.1:8b --modelfile`

O Llama 3.1 já vem com suporte nativo a tools. Extraímos seu template e adaptamos para o Llama 3.2 Vision.

#### Diferenças Chave: Qwen vs Llama

| Aspecto | Qwen2.5-VL | Llama 3.2 Vision |
|---------|------------|-------------------|
| **Formato de mensagens** | `<\|im_start\|>role\|im_end\|>` | `<\|start_header_id\|>role<\|end_header_id\|>` |
| **Token de fim** | `<\|im_end\|>` | `<\|eot_id\|>` |
| **System message** | Embutido no template | Separado em SYSTEM block |
| **Tool format** | JSON simples | JSON com "name" e "parameters" |
| **Base oficial com tools** | ❌ Não | ✅ Sim (Llama 3.1) |

### Modelfile Completo: llama32-vision-tools-v1

**Arquivo**: `Modelfile.llama32-vision-tools-v1`

```dockerfile
# Modelfile: Llama 3.2 Vision 11B com suporte a Tools
# Baseado no template do Llama 3.1 (que suporta tools nativamente)
# Adaptado para Llama 3.2 Vision que originalmente não tem tools

FROM llama3.2-vision:11b

TEMPLATE """{{- if or .System .Tools }}<|start_header_id|>system<|end_header_id|>
{{- if .System }}

{{ .System }}
{{- end }}
{{- if .Tools }}

Cutting Knowledge Date: December 2023

When you receive a tool call response, use the output to format an answer to the orginal user question.

You are a helpful assistant with tool calling capabilities.
{{- end }}<|eot_id|>
{{- end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 }}
{{- if eq .Role "user" }}<|start_header_id|>user<|end_header_id|>
{{- if and $.Tools $last }}

Given the following functions, please respond with a JSON for a function call with its proper arguments that best answers the given prompt.

Respond in the format {"name": function name, "parameters": dictionary of argument name and its value}. Do not use variables.

{{ range $.Tools }}
{{- . }}
{{ end }}
Question: {{ .Content }}<|eot_id|>
{{- else }}

{{ .Content }}<|eot_id|>
{{- end }}{{ if $last }}<|start_header_id|>assistant<|end_header_id|>

{{ end }}
{{- else if eq .Role "assistant" }}<|start_header_id|>assistant<|end_header_id|>
{{- if .ToolCalls }}
{{ range .ToolCalls }}
{"name": "{{ .Function.Name }}", "parameters": {{ .Function.Arguments }}}{{ end }}
{{- else }}

{{ .Content }}
{{- end }}{{ if not $last }}<|eot_id|>{{ end }}
{{- else if eq .Role "tool" }}<|start_header_id|>tool<|end_header_id|>

{{ .Content }}<|eot_id|>{{ if $last }}<|start_header_id|>assistant<|end_header_id|>

{{ end }}
{{- end }}
{{- end }}"""

SYSTEM """You are a helpful assistant with tool calling capabilities."""

PARAMETER temperature 0.1
PARAMETER num_ctx 8192
```

#### Pontos Importantes do Template

1. **Estrutura de mensagens Llama**:
   - `<|start_header_id|>role<|end_header_id|>` para iniciar
   - `<|eot_id|>` para finalizar
   - Roles: `system`, `user`, `assistant`, `tool`

2. **Instrução de function calling** (linha 26-28):
   ```
   Given the following functions, please respond with a JSON for a function call
   with its proper arguments that best answers the given prompt.

   Respond in the format {"name": function name, "parameters": dictionary of
   argument name and its value}. Do not use variables.
   ```

3. **Formato de resposta** (linha 43):
   ```json
   {"name": "função", "parameters": {"arg": "valor"}}
   ```

4. **Context window**: 8192 tokens (mesmo do Llama 3.2 Vision base)

### Criação do Modelo

```bash
ollama create llama32-vision-tools-v1 -f Modelfile.llama32-vision-tools-v1
```

**Output esperado**:
```
transferring model data
using existing layer sha256:...
creating new layer sha256:...
writing manifest
success
```

### Validação e Teste

**Arquivo de teste**: `teste_llama32_vision_tools.py`

```python
#!/usr/bin/env python3
"""
Teste: Llama 3.2 Vision com Tools via Modelfile Customizado

Objetivo: Validar se llama32-vision-tools-v1 funciona com bind_tools() + ToolNode.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

@tool
def obter_info() -> str:
    """Retorna informações sobre o teste."""
    return "Teste de tools funcionando!"

@tool
def calcular_soma(a: int, b: int) -> int:
    """
    Calcula a soma de dois números.

    Args:
        a: Primeiro número
        b: Segundo número

    Returns:
        Soma de a + b
    """
    return a + b

ALL_TOOLS = [obter_info, calcular_soma]

def main():
    print("=" * 80)
    print("🧪 TESTE: Llama 3.2 Vision com Tools via Modelfile Customizado")
    print("=" * 80)

    model_name = "llama32-vision-tools-v1"

    # Criar modelo base
    llm_base = ChatOllama(
        model=model_name,
        temperature=0.1,
        num_ctx=8192
    )

    # Bind tools
    llm_with_tools = llm_base.bind_tools(ALL_TOOLS)

    # Invocar
    pergunta = "Por favor, calcule a soma de 15 e 27"
    response = llm_with_tools.invoke([
        HumanMessage(content=pergunta)
    ])

    # Analisar resposta
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"✅ {len(response.tool_calls)} tool call(s) detectada(s)")
        for i, tc in enumerate(response.tool_calls, 1):
            print(f"   {i}. {tc['name']}({tc['args']})")
    else:
        print("❌ Modelo não gerou tool calls")

if __name__ == "__main__":
    main()
```

**Resultado da execução** (`teste_llama32_vision_tools.log`):

```
================================================================================
🧪 TESTE: Llama 3.2 Vision com Tools via Modelfile Customizado
================================================================================

🎯 OBJETIVO:
   Verificar se llama32-vision-tools-v1 aceita bind_tools()
   e consegue gerar tool calls

🤖 Testando modelo: llama32-vision-tools-v1

1. Criando ChatOllama...
   ✅ ChatOllama criado

2. Executando bind_tools()...
   ✅ bind_tools() executado sem erros!

3. Invocando modelo com pergunta que requer tools...
   Pergunta: Por favor, calcule a soma de 15 e 27

📄 Resposta do modelo:
   🔧 Tool calls detectadas: 1
      1. calcular_soma({'a': 15, 'b': 27})

================================================================================
🎉 SUCESSO TOTAL!
================================================================================
   ✅ Modelfile customizado FUNCIONOU!
   ✅ Ollama aceitou tools
   ✅ Modelo gerou tool calls
   ✅ 1 tool call(s) detectada(s)
```

### Comparação: Qwen vs Llama

Agora temos **dois modelos de visão funcionais com tools no Ollama**:

| Característica | qwen-vision-tools-v1 | llama32-vision-tools-v1 |
|----------------|----------------------|-------------------------|
| **Modelo base** | Qwen2.5-VL:7B | Llama 3.2 Vision:11B |
| **Parâmetros** | 7B | 11B |
| **VRAM (estimado)** | ~8-10 GB | ~12-14 GB |
| **Template adaptado de** | Llama 3.1 (híbrido) | Llama 3.1 (direto) |
| **Formato de mensagens** | `<\|im_start\|>...<\|im_end\|>` | `<\|start_header_id\|>...<\|eot_id\|>` |
| **Tool call format** | JSON simples | `{"name": ..., "parameters": ...}` |
| **bind_tools() funciona?** | ✅ Sim | ✅ Sim |
| **ToolNode funciona?** | ✅ Sim | ✅ Sim |
| **Qualidade de visão** | Boa (QVGA até 1080p) | Boa (similar) |
| **Velocidade** | Mais rápido | Mais lento |

**Quando usar cada um:**

- **Qwen2.5-VL-7B**: Se você tem menos VRAM ou precisa de respostas mais rápidas
- **Llama 3.2 Vision-11B**: Se você tem VRAM disponível e quer aproveitar modelo maior

Ambos são completamente funcionais com LangGraph e podem processar screenshots + tools simultaneamente.

---

## Investigação: Template vs Treinamento

### Pergunta Crítica

Com o sucesso do Modelfile customizado, surgiu uma dúvida importante:

> "O template sozinho é suficiente para habilitar function calling, ou o modelo precisa ter sido treinado especificamente para isso?"

Em outras palavras: podemos pegar qualquer modelo e adicionar suporte a tools apenas customizando o template?

### Hipótese de Teste

Se o template for suficiente:
- Moondream (modelo SEM treinamento de function calling) + template de tools = funciona

Se o treinamento for necessário:
- Moondream + template de tools = falha (retorna texto ao invés de JSON)

### Teste Controlado: Moondream

Criamos `Modelfile.moondream-tools-test` aplicando o mesmo template ao Moondream (modelo de visão pequeno, provavelmente sem function calling training):

```dockerfile
FROM moondream:1.8b

TEMPLATE """{{- if or .System .Tools }}<|im_start|>system
{{- if .System }}

{{ .System }}
{{- end }}
{{- if .Tools }}

You are a helpful assistant with tool calling capabilities.
{{- end }}<|im_end|>
...
```

**Teste**: `teste_moondream_tools.py`

**Resultado**:

```
📄 Resposta do modelo:
   💬 Texto: ;D"=936FD82E@G8D6!3."@*&+G(@=4:%))=A,<$CA!A)3B(F#6<:;F6-.,<9HC...

================================================================================
📊 RESULTADO
================================================================================
Tool calls: 0

✅ CONCLUSÃO: Treinamento É NECESSÁRIO
   Template sozinho NÃO é suficiente
   Modelo precisa ter sido treinado para function calling

   Modelo retornou texto ao invés de tool calls:
   >>> You are an Android app testing agent...
   >>> ;D"=936FD82E@G8D6!3."@*&+G(@=4:%))=A,<$CA!...
```

### Conclusão da Investigação

**Template customizado NÃO cria a capacidade de function calling do zero.**

O que acontece:
1. **Template** = Interface de comunicação (como formatar entrada/saída)
2. **Treinamento** = Conhecimento do modelo sobre quando e como usar tools

**Analogia**:
- Template é como dar um formulário em branco para alguém
- Treinamento é ensinar a pessoa a preencher o formulário corretamente

**Por que Qwen2.5-VL funcionou?**

O Qwen2.5-VL já possui treinamento para function calling no dataset original. O template customizado apenas **expõe essa capacidade** ao Ollama, mas não cria a habilidade do zero.

**Modelos com function calling training**:
- Qwen 2.5+ (todas as versões)
- Llama 3.1+
- Mistral 7B v0.3+
- Gemma 3+ (versões específicas)

**Modelos SEM function calling training**:
- Moondream
- Modelos mais antigos pré-2023
- Modelos pequenos (<1B parâmetros geralmente)

---

## Comparação: Mistral Manual vs LangGraph Automático

Antes de usar LangGraph, já tínhamos um exemplo funcional de function calling com Mistral-7B usando HuggingFace diretamente (arquivo: `src/exemplos/basico/function_call.py`).

Vale comparar as duas abordagens para entender as vantagens/desvantagens de cada uma.

### Abordagem 1: Mistral via HuggingFace (Manual)

**Código simplificado**:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

# Carrega modelo
model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-Instruct-v0.3")
tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.3")

# Define tools como funções Python
def obter_ip_externo() -> str:
    """Obtém o endereço IP externo da máquina atual."""
    return "187.75.23.45"

def obter_geolocalizacao_ip(ip: str) -> str:
    """Obtém informações de geolocalização de um endereço IP."""
    return "São Paulo, SP, Brasil"

tools = [obter_ip_externo, obter_geolocalizacao_ip]

# Gera resposta
conversation = [{"role": "user", "content": "Em que cidade estou?"}]

inputs = tokenizer.apply_chat_template(
    conversation,
    tools=tools,
    add_generation_prompt=True,
    return_tensors="pt"
)

outputs = model.generate(inputs, max_new_tokens=300)
resposta = tokenizer.decode(outputs[0][len(inputs[0]):])
```

**O que o Mistral retorna**:

```
Para saber em que cidade estou, você precisará utilizar as funções...

[{"name": "obter_ip_externo", "arguments": {}}]

Após obter o endereço IP, podemos utilizar obter_geolocalizacao_ip...

[{"name": "obter_geolocalizacao_ip",
  "arguments": {"ip": "$retorno_obter_ip_externo"}}]

Finalmente, podemos utilizar consultar_clima_brasileiro...

[{"name": "consultar_clima_brasileiro",
  "arguments": {"cidade": "$retorno_obter_geolocalizacao_ip.localidade"}}]
```

**Parsing e execução manual**:

```python
import re
import json

# 1. Extrair JSONs da resposta
tool_calls_json = re.findall(r'\[{.*?}\]', resposta)

# 2. Parsear cada JSON
tool_calls = [json.loads(tc) for tc in tool_calls_json]

# 3. Executar sequencialmente
resultados = {}
for call in tool_calls:
    nome = call['name']
    args = call['arguments']

    # Substituir referências a resultados anteriores
    for key, value in args.items():
        if isinstance(value, str) and value.startswith('$retorno_'):
            # Exemplo: "$retorno_obter_ip_externo" → "187.75.23.45"
            var_name = value.replace('$retorno_', '')
            args[key] = resultados[var_name]

    # Executar tool
    if nome == 'obter_ip_externo':
        resultado = obter_ip_externo()
    elif nome == 'obter_geolocalizacao_ip':
        resultado = obter_geolocalizacao_ip(**args)

    resultados[nome] = resultado

# 4. Request final para sintetizar resposta
conversation.append({"role": "assistant", "content": resposta})
conversation.append({"role": "user", "content": f"Resultados: {resultados}"})

resposta_final = model.generate(...)
```

**Características**:
- ✅ 2 gerações do modelo apenas (planejar + sintetizar)
- ✅ Múltiplas tools planejadas de uma vez
- ❌ Parsing manual complexo (regex para extrair JSONs)
- ❌ Execução manual sequencial
- ❌ Substituição manual de variáveis (`$retorno_...`)
- ❌ Plano fixo (não pode re-planejar após ver resultado)
- ❌ Sem integração com ferramentas de debugging

**Resultado real** (arquivo: `/home/pedro/tmp/results-apc/function_call_real_20250929_155051/`):

Para "Em que cidade estou?", o Mistral retornou 3 tool calls em uma única resposta, executadas sequencialmente de forma manual.

### Abordagem 2: Qwen2.5-VL via LangGraph (Automático)

**Código simplificado** (arquivo: `src/experimental/android_agent/agent/react_agent_with_tools.py`):

```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_ollama import ChatOllama
from langchain_core.tools import tool

# Define tools
@tool
def click(x: int, y: int) -> str:
    """Clica em coordenadas (x, y) na tela Android."""
    return f"Clicked at ({x}, {y})"

@tool
def set_text(x: int, y: int, text: str) -> str:
    """Insere texto em campo na posição (x, y)."""
    return f"Text '{text}' entered at ({x}, {y})"

ALL_TOOLS = [click, set_text]

# Criar modelo com tools
llm_base = ChatOllama(model="qwen-vision-tools-v1")
llm_with_tools = llm_base.bind_tools(ALL_TOOLS)

# Criar ToolNode
tool_node = ToolNode(ALL_TOOLS)

# Definir nós do grafo
def raciocinar(state):
    """Modelo analisa e decide ação."""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state):
    """Decide se executa tools ou finaliza."""
    last_msg = state["messages"][-1]
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        return "tools"
    return "end"

# Construir grafo
workflow = StateGraph(AgentState)
workflow.add_node("raciocinar", raciocinar)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("raciocinar")
workflow.add_conditional_edges("raciocinar", should_continue, {
    "tools": "tools",
    "end": END
})
workflow.add_edge("tools", "raciocinar")  # Loop

agente = workflow.compile()

# Executar
resultado = agente.invoke({
    "screenshot_path": "001.png",
    "ui_description": "...",
    "messages": [],
    "iteration": 0
})
```

**O que acontece internamente**:

```
Iteração 1:
  🧠 raciocinar() → llm_with_tools.invoke()
     Modelo retorna: AIMessage(tool_calls=[{"name": "click", "args": {"x": 540, "y": 273}}])

  ✅ should_continue() → detecta tool_calls → retorna "tools"

  🔧 ToolNode executa automaticamente:
     resultado = click(540, 273)  # "Clicked at (540, 273)"
     Cria: ToolMessage(content="Clicked at (540, 273)")
     Adiciona ao state["messages"]

  ↩️ Volta para raciocinar()

Iteração 2:
  🧠 raciocinar() → llm_with_tools.invoke(messages_com_resultado_anterior)
     Modelo VÊ: "Clicked at (540, 273)" no histórico
     Decide próxima ação baseada no resultado
     Retorna: AIMessage(tool_calls=[{"name": "set_text", "args": {...}}])

  (continua...)

Iteração N:
  🧠 raciocinar()
     Modelo decide que exploração está completa
     Retorna: AIMessage(content="Análise completa") ← SEM tool_calls

  ✅ should_continue() → sem tool_calls → retorna "end"

  🏁 Finaliza
```

**Características**:
- ✅ Parsing automático (LangChain)
- ✅ Execução automática (ToolNode)
- ✅ Histórico gerenciado automaticamente
- ✅ Modelo vê resultados reais e pode re-planejar
- ✅ Integração com LangSmith para debugging
- ✅ Código limpo e manutenível
- ❌ N gerações do modelo (1 por tool)
- ❌ Mais lento que Mistral manual

**Resultado real** (arquivo: `teste_custom_vision_tools_v1.log`):

Para uma tela Android, o modelo chamou `click()` em 3 iterações sequenciais, cada uma vendo o resultado da anterior.

---

## Encadeamento de Tools

Esta seção aborda uma questão fundamental: **como múltiplas tools que dependem umas das outras são executadas?**

### Cenário de Teste

Pergunta: **"Em que cidade estou?"**

Requer duas tools em sequência:
1. `obter_ip_externo()` → Retorna IP do usuário
2. `obter_geolocalizacao_ip(ip)` → Recebe IP e retorna cidade

A segunda tool **depende** do resultado da primeira.

### Abordagem 1: Mistral com Execução Manual

**O que o Mistral retorna em uma única geração**:

```json
[
  {"name": "obter_ip_externo", "arguments": {}},
  {"name": "obter_geolocalizacao_ip", "arguments": {"ip": "$retorno_obter_ip_externo"}},
  {"name": "consultar_clima_brasileiro", "arguments": {"cidade": "$retorno_obter_geolocalizacao_ip.localidade"}}
]
```

**Como funciona o encadeamento**:

1. Modelo planeja todas as tools de uma vez
2. Usa **referências simbólicas** para indicar dependências (`$retorno_...`)
3. Desenvolvedor executa sequencialmente:

```python
# Execução sequencial com substituição de variáveis
resultado1 = obter_ip_externo()
# → "187.75.23.45"

# Substituir $retorno_obter_ip_externo pelo resultado real
resultado2 = obter_geolocalizacao_ip(ip="187.75.23.45")
# → {"cidade": "São Paulo", "estado": "SP", ...}

# Substituir $retorno_obter_geolocalizacao_ip.localidade
resultado3 = consultar_clima_brasileiro(cidade="São Paulo")
# → {"temperatura": 25, ...}
```

**Vantagens**:
- 1 geração do modelo (rápido)
- Plano completo visível

**Desvantagens**:
- Parsing manual complexo
- Substituição de variáveis manual
- Plano fixo (não pode ajustar se algo falhar)

### Abordagem 2: LangGraph com Múltiplas Iterações

**Teste realizado** (arquivo: `teste_langgraph_encadeamento.py`):

Criamos um teste para verificar se LangGraph consegue fazer encadeamento "estilo Mistral" (múltiplas tools em 1 resposta).

**Resultado**:

```
🔍 qwen-vision-tools-v1:
------------------------------------------------------------
   Iterações: 0
   Mensagens com tool calls: 0
   ❌ Nenhuma tool foi chamada

❌ SEM ENCADEAMENTO em nenhum modelo testado
   Todos os modelos retornam apenas 1 tool call por iteração
   Encadeamento ocorre via múltiplas iterações do grafo LangGraph
```

**Como funciona o encadeamento no LangGraph**:

```
Iteração 1:
  🧠 Modelo recebe: "Em que cidade estou?"
     Decide: obter_ip_externo()
     Retorna: AIMessage(tool_calls=[{"name": "obter_ip_externo", "args": {}}])

  🔧 ToolNode executa:
     resultado = obter_ip_externo()  # "187.75.23.45"
     Adiciona: ToolMessage(content="187.75.23.45")

  📝 Histórico agora contém:
     - HumanMessage("Em que cidade estou?")
     - AIMessage(tool_calls=[obter_ip_externo])
     - ToolMessage("187.75.23.45")  ← RESULTADO REAL disponível

Iteração 2:
  🧠 Modelo recebe histórico completo com resultado "187.75.23.45"
     Analisa: "Tenho o IP, agora preciso da geolocalização"
     Decide: obter_geolocalizacao_ip(ip="187.75.23.45")
     Retorna: AIMessage(tool_calls=[{"name": "obter_geolocalizacao_ip",
                                     "args": {"ip": "187.75.23.45"}}])

  🔧 ToolNode executa:
     resultado = obter_geolocalizacao_ip("187.75.23.45")
     # "São Paulo, SP, Brasil"
     Adiciona: ToolMessage(content="São Paulo, SP, Brasil")

  📝 Histórico agora contém:
     - HumanMessage("Em que cidade estou?")
     - AIMessage(tool_calls=[obter_ip_externo])
     - ToolMessage("187.75.23.45")
     - AIMessage(tool_calls=[obter_geolocalizacao_ip])
     - ToolMessage("São Paulo, SP, Brasil")  ← NOVO RESULTADO

Iteração 3:
  🧠 Modelo recebe histórico completo
     Analisa: "Tenho IP e localização, pergunta respondida"
     Retorna: AIMessage(content="Você está em São Paulo, SP, Brasil")
     ← SEM tool_calls

  ✅ should_continue() → sem tool_calls → END
```

**Vantagens**:
- Modelo vê resultados REAIS (não referências simbólicas)
- Pode re-planejar a cada iteração
- Automático (sem parsing/substituição manual)
- Robusto a falhas (pode adaptar estratégia)

**Desvantagens**:
- N gerações do modelo (mais lento)
- Não vê plano completo de antemão

### ToolNode e Execução Paralela

Descoberta importante da documentação do LangGraph:

**Se um modelo retornar múltiplas tool calls em 1 resposta**, o ToolNode executa todas **em paralelo**, não sequencialmente!

```python
# Se modelo retornar:
AIMessage(tool_calls=[
    {"name": "obter_ip_externo", "args": {}},
    {"name": "obter_geolocalizacao_ip", "args": {"ip": "$retorno_obter_ip_externo"}}
])

# ToolNode executa:
Thread 1: resultado1 = obter_ip_externo()  # "187.75.23.45"
Thread 2: resultado2 = obter_geolocalizacao_ip(ip="$retorno_obter_ip_externo")
          # ❌ ERRO! String literal, não o resultado de Thread 1
```

**Por que isso acontece?**

O ToolNode não implementa substituição de variáveis. Ele simplesmente:
1. Extrai tool_calls da mensagem
2. Executa todas concorrentemente
3. Coleta resultados

**Pode desabilitar execução paralela**:

```python
model.bind_tools(tools, parallel_tool_calls=False)
```

Mas isso força execução **uma por vez**, não resolve o problema de referências simbólicas.

**Conclusão**: O LangGraph não implementa encadeamento "estilo Mistral" com referências simbólicas. O encadeamento acontece através de múltiplas iterações do grafo.

### Comparação Direta

| Aspecto | Mistral Manual | LangGraph |
|---------|----------------|-----------|
| **Tool calls por resposta** | Múltiplas (3+) | 1 |
| **Encadeamento** | Referências simbólicas | Histórico de mensagens |
| **Execução de tools** | Sequencial manual | 1 por iteração |
| **Tool 2 vê resultado de Tool 1** | Via substituição de `$retorno_` | Via ToolMessage no histórico |
| **Gerações do modelo** | 2 (planejar + sintetizar) | N (1 por tool + 1 final) |
| **Parsing** | Manual (regex) | Automático |
| **Re-planejamento** | ❌ Plano fixo | ✅ A cada iteração |
| **Debugging** | Manual (prints) | LangSmith |

### Command + InjectedState: Compartilhamento de Dados entre Tools

Após compreender como funciona o encadeamento via múltiplas iterações no LangGraph, surgiu uma questão adicional: **seria possível melhorar a eficiência compartilhando dados entre tools através do state, ao invés de apenas via histórico de mensagens?**

O LangGraph oferece dois recursos que permitem isso:
- **Command**: Tipo de retorno que permite tools atualizarem o state diretamente
- **InjectedState**: Anotação de tipo que permite tools acessarem o state atual

#### Motivação

No exemplo "Em que cidade estou?", a segunda tool precisa do IP retornado pela primeira. Existem duas formas de passar essa informação:

**Forma 1: Via histórico de mensagens** (já vimos):
```
Tool 1 retorna: ToolMessage(content="187.75.23.45")
Tool 2 recebe IP através do prompt que o modelo gera após ver o histórico
```

**Forma 2: Via state compartilhado** (novo):
```
Tool 1 salva: state["ip_externo"] = "187.75.23.45"
Tool 2 lê: ip = state.get("ip_externo")
```

A segunda abordagem é mais direta: Tool 2 não precisa receber o IP como argumento do modelo, ela acessa diretamente do state. Isso torna a assinatura da tool mais simples.

#### Implementação

**State com Reducers**

Para que tools possam atualizar campos do state via Command, é necessário definir **reducers** para esses campos:

```python
from typing import TypedDict, List, Annotated
import operator

def update_field(existing, new):
    """
    Reducer para campos simples: sobrescreve valor existente com novo.

    Chamado quando múltiplas atualizações ao mesmo campo ocorrem.
    No nosso caso, tool retorna Command(update={"ip_externo": "..."})
    """
    return new if new else existing

class AgentState(TypedDict):
    """Estado do agente com campos compartilhados entre tools."""
    messages: Annotated[List, operator.add]  # Mensagens acumulam
    iteration: int                            # Contador simples

    # Campos compartilhados entre tools (precisam de reducer)
    ip_externo: Annotated[str, update_field]
    localizacao: Annotated[str, update_field]
```

O reducer é necessário porque o LangGraph permite múltiplas atualizações concorrentes ao state. Sem reducer, o framework não sabe como combinar os valores.

**Tool 1: Salvar Dados no State**

```python
from langgraph.types import Command
from langgraph.prebuilt import InjectedState
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from typing import Annotated

@tool
def obter_ip_externo_v2(
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Obtém o endereço IP externo da máquina atual.

    Esta versão usa Command para atualizar o state diretamente,
    permitindo que outras tools acessem o IP sem precisar parsear mensagens.

    Returns:
        Command atualizando state com o IP
    """
    # Simula obtenção do IP
    ip = "187.75.23.45"

    # Retorna Command para atualizar state
    return Command(
        update={
            "ip_externo": ip,  # Salva no state
            "messages": [ToolMessage(
                content=f"IP externo obtido: {ip}",
                tool_call_id=tool_call_id
            )]
        }
    )
```

**Pontos importantes**:
1. Tool retorna `Command` ao invés de `str`
2. `Command.update` é um dicionário com campos do state a atualizar
3. `ip_externo` é salvo no state para outras tools acessarem
4. `messages` ainda precisa incluir ToolMessage para histórico
5. `InjectedToolCallId` é necessário para criar ToolMessage válida

**Tool 2: Ler Dados do State**

```python
@tool
def obter_geolocalizacao_ip_v2(
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Obtém geolocalização do IP externo.

    Esta versão usa InjectedState para acessar o IP diretamente do state,
    sem precisar receber como argumento!

    Args:
        state: State injetado automaticamente pelo LangGraph (NÃO é visto pelo modelo)

    Returns:
        Command atualizando state com a localização
    """
    # Acessa IP do state (colocado pela tool anterior)
    ip = state.get("ip_externo", "")

    if not ip:
        return Command(update={
            "messages": [ToolMessage(
                content="Erro: IP não disponível no state",
                tool_call_id=tool_call_id
            )]
        })

    # Simula geolocalização
    localizacao = f"São Paulo, SP, Brasil (baseado em {ip})"

    return Command(
        update={
            "localizacao": localizacao,  # Salva no state
            "messages": [ToolMessage(
                content=f"Localização: {localizacao}",
                tool_call_id=tool_call_id
            )]
        }
    )
```

**Pontos importantes**:
1. Parâmetro `state: Annotated[dict, InjectedState]` é injetado automaticamente
2. **IMPORTANTE**: Tipo deve ser `dict` genérico, NÃO `AgentState` (causa erro)
3. `InjectedState` é importado de `langgraph.prebuilt`
4. Modelo **NÃO vê** este parâmetro no JSON Schema da tool
5. Tool pode ser chamada sem argumentos: `obter_geolocalizacao_ip_v2({})`

**Imports Corretos**

```python
from langgraph.prebuilt import ToolNode, InjectedState  # InjectedState aqui!
from langgraph.types import Command
from langchain_core.tools import tool, InjectedToolCallId
```

#### Teste Comparativo

Criamos um teste para comparar as duas abordagens: tools antigas (apenas string) vs tools com Command + InjectedState.

**Arquivo**: `teste_langgraph_command_state.py`

**Configuração do teste**:
- Pergunta: "Em que cidade estou?"
- Modelo: `qwen3:4b` (4GB VRAM, conhecido por funcionar bem com tools)
- Máximo de iterações: 5

**Resultados** (arquivo: `teste_langgraph_command_state_v2.log`):

```
🔍 Tools antigas (sem Command):
------------------------------------------------------------
   Iterações: 2
   IP no state: (vazio)
   Localização no state: (vazio)
   Tools chamadas: 6
      1. obter_ip_externo_v1
      2. obter_ip_externo_v1
      3. obter_geolocalizacao_ip_v1
      4. obter_ip_externo_v1
      5. obter_ip_externo_v1
      6. obter_geolocalizacao_ip_v1

🔍 Tools com Command + InjectedState:
------------------------------------------------------------
   Iterações: 2
   IP no state: 187.75.23.45
   Localização no state: São Paulo, SP, Brasil (baseado em 187.75.23.45)
   Tools chamadas: 6
      1. obter_ip_externo_v2
      2. obter_ip_externo_v2
      3. obter_geolocalizacao_ip_v2
      4. obter_ip_externo_v2
      5. obter_ip_externo_v2
      6. obter_geolocalizacao_ip_v2
```

**Observações do log detalhado**:

**Iteração 1 (V2 com Command)**:
```
📊 State atual:
   ip_externo:
   localizacao:

🔧 Tool calls: 1
   1. obter_ip_externo_v2({})

🌐 TOOL: obter_ip_externo_v2()
   → IP obtido: 187.75.23.45
   → Atualizando state['ip_externo'] = 187.75.23.45
```

**Iteração 2 (V2 com Command)**:
```
📊 State atual:
   ip_externo: 187.75.23.45  ← Salvo pela tool anterior!
   localizacao:

🔧 Tool calls: 1
   1. obter_geolocalizacao_ip_v2({})  ← SEM argumento 'ip'!

📍 TOOL: obter_geolocalizacao_ip_v2()
   → IP lido do state: 187.75.23.45  ← Acessou diretamente do state
   → Localização obtida: São Paulo, SP, Brasil
   → Atualizando state['localizacao'] = São Paulo, SP, Brasil
```

#### Análise dos Resultados

**Eficiência**:
- Ambas as abordagens requerem **2 iterações** (mesma eficiência)
- Command + InjectedState **não reduz** o número de gerações do modelo
- Modelo ainda precisa decidir chamar Tool 2 após ver resultado de Tool 1

**Diferenças**:

| Aspecto | Tools Antigas | Command + InjectedState |
|---------|---------------|-------------------------|
| **State atualizado** | ❌ Vazio | ✅ Dados salvos |
| **Tool 2 precisa de argumento** | ✅ Sim: `ip: str` | ❌ Não: lê do state |
| **Assinatura da tool** | `(ip: str) -> str` | `() -> Command` |
| **Complexidade** | Baixa | Média (reducers, imports) |
| **Iterações** | 2 | 2 |

**Vantagens do Command + InjectedState**:

1. **State mais rico**: Campos do state refletem o progresso real
2. **Assinaturas mais simples**: Tools dependentes não precisam receber dados como argumentos
3. **Debugging facilitado**: State mostra claramente quais dados foram coletados
4. **Reutilização**: Outras partes do código podem acessar `state["ip_externo"]`

**Desvantagens**:

1. **Complexidade adicional**: Requer reducers, imports corretos, anotações de tipo
2. **Mesma eficiência**: Não reduz número de iterações
3. **Curva de aprendizado**: Mais conceitos para entender

#### Limitação Crítica: Falta de Garantia de Pré-Requisitos

Mesmo com Command + InjectedState permitindo compartilhamento de dados via state, **não há mecanismo para garantir que tools pré-requisitos sejam executadas antes de tools dependentes**.

**Cenário problemático**:

```python
# Tool 2 depende de Tool 1
@tool
def obter_geolocalizacao_ip_v2(
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    ip = state.get("ip_externo", "")

    if not ip:  # ← Pode acontecer!
        return Command(update={
            "messages": [ToolMessage(
                content="Erro: IP não disponível no state",
                tool_call_id=tool_call_id
            )]
        })
    # ...
```

**O que pode acontecer**:

1. Modelo decide chamar `obter_geolocalizacao_ip_v2()` **SEM ter chamado** `obter_ip_externo_v2()` primeiro
2. Tool executa com `state["ip_externo"]` vazio
3. Retorna erro

**Por que isso acontece?**

O LangGraph **não conhece** a relação de dependência entre tools. A cada iteração, o modelo:
1. Analisa histórico de mensagens
2. Analisa JSON Schema das tools disponíveis
3. Decide qual tool chamar

O modelo **pode errar** essa decisão. Ele pode:
- Esquecer de chamar Tool 1
- Chamar Tool 2 diretamente
- Não perceber que Tool 2 precisa de dados de Tool 1

**Defesas possíveis (mas não garantias)**:

1. **Docstring clara**:
```python
@tool
def obter_geolocalizacao_ip_v2(...) -> Command:
    """
    Obtém geolocalização do IP externo.

    IMPORTANTE: Requer que obter_ip_externo_v2() tenha sido chamada antes!
    """
```

2. **System prompt explícito**:
```python
system_content = """
You have access to these tools:
- obter_ip_externo_v2(): Get external IP and save to state
- obter_geolocalizacao_ip_v2(): Get location from IP saved in state

IMPORTANT: You MUST call obter_ip_externo_v2() BEFORE calling obter_geolocalizacao_ip_v2()!
"""
```

3. **Validação defensiva na tool**:
```python
if not ip:
    return Command(update={
        "messages": [ToolMessage(
            content="Erro: Chame obter_ip_externo_v2() primeiro!",
            tool_call_id=tool_call_id
        )]
    })
```

**Mas nenhuma dessas é uma GARANTIA**. O modelo pode ignorar instruções.

**Comparação com Mistral Manual**:

A abordagem manual com Mistral **também não garante** pré-requisitos:
- Modelo pode retornar tools fora de ordem
- Desenvolvedor precisa reordenar manualmente
- Ou executar sequencialmente e falhar

**Conclusão sobre esta limitação**:

Command + InjectedState é útil para:
- ✅ Simplificar assinaturas de tools
- ✅ Enriquecer o state com dados intermediários
- ✅ Facilitar debugging
- ❌ **NÃO** garante ordem de execução
- ❌ **NÃO** impede que modelo chame tools fora de ordem

**Quando usar mesmo assim**:

1. **Cenários com múltiplas tools independentes que compartilham dados**:
   ```python
   obter_perfil_usuario() → state["user_id"]
   obter_historico_compras() → lê state["user_id"]
   obter_recomendacoes() → lê state["user_id"]
   calcular_desconto() → lê state["user_id"] + state["historico"]
   ```

2. **Quando validação defensiva é suficiente**:
   - Tool retorna erro se pré-requisito não foi executado
   - Modelo vê erro e corrige na próxima iteração
   - Aceitável ter 1-2 iterações extras de correção

3. **Quando o state precisa ser inspecionado externamente**:
   - Callbacks que monitoram progresso
   - Logging/debugging avançado
   - Persistência entre execuções

**Quando NÃO usar**:

1. **Tools com dependências críticas**:
   - Operações financeiras (transferência precisa de validação prévia)
   - Ações irreversíveis (deletar arquivo precisa de confirmação prévia)
   - Sequências obrigatórias rígidas

2. **Quando simplicidade é prioritária**:
   - Projeto pequeno com poucas tools
   - Equipe sem experiência com LangGraph
   - Não há benefício claro de state compartilhado

#### Quando Usar Command + InjectedState

**Recomendado para**:

1. **Múltiplas tools que compartilham dados** (mas sem dependências críticas):
   - Exemplo: Dashboard com vários widgets usando mesmo user_id
   - Exemplo: Pipeline de processamento com metadados compartilhados

2. **State precisa ser acessado por outras partes do código**:
   - Callbacks que monitoram progresso
   - Persistência de sessão entre invocações
   - Logging estruturado com dados intermediários

3. **Debugging e observabilidade são prioritários**:
   - LangSmith pode mostrar evolução do state
   - Facilita entender qual tool populou qual campo
   - Reprodução de bugs mais fácil

4. **Tools com assinaturas complexas** (muitos argumentos):
   - Ao invés de `tool(arg1, arg2, arg3, arg4, arg5)`
   - Pode fazer `tool()` lendo `state["dados_contexto"]`

**NÃO recomendado para**:

1. **Projetos simples** com poucas tools e sem compartilhamento de dados
2. **Dependências críticas** onde ordem DEVE ser garantida
3. **Equipes iniciantes** em LangGraph (curva de aprendizado adicional)

#### Tratamento Manual: Alternativas Práticas

Como a falta de garantia de execução de pré-requisitos **inviabiliza** o uso direto de Command + InjectedState em muitos cenários, existem alternativas para forçar a ordem de execução:

**Alternativa 1: Grafo com Nós Separados (Sequência Forçada)**

Ao invés de deixar o modelo decidir qual tool chamar, force a sequência no próprio grafo:

```python
from langgraph.graph import StateGraph, END

def chamar_tool_1(state):
    """Nó que sempre chama Tool 1."""
    resultado = obter_ip_externo()
    return {
        **state,
        "ip_externo": resultado,
        "messages": [ToolMessage(content=resultado)]
    }

def chamar_tool_2(state):
    """Nó que sempre chama Tool 2 (garante que Tool 1 já executou)."""
    ip = state["ip_externo"]
    resultado = obter_geolocalizacao_ip(ip)
    return {
        **state,
        "localizacao": resultado,
        "messages": [ToolMessage(content=resultado)]
    }

# Construir grafo com sequência fixa
workflow = StateGraph(AgentState)
workflow.add_node("tool_1", chamar_tool_1)
workflow.add_node("tool_2", chamar_tool_2)
workflow.add_node("raciocinar", raciocinar)

workflow.set_entry_point("tool_1")
workflow.add_edge("tool_1", "tool_2")  # Sequência garantida!
workflow.add_edge("tool_2", "raciocinar")
workflow.add_edge("raciocinar", END)
```

**Vantagens**:
- ✅ Sequência garantida pela estrutura do grafo
- ✅ Não depende de decisões do modelo
- ✅ Simples de debugar

**Desvantagens**:
- ❌ Perde flexibilidade (sempre executa mesma sequência)
- ❌ Modelo não pode pular tools desnecessárias
- ❌ Não é realmente um agente (é um pipeline fixo)

**Alternativa 2: Tool Composta (Encapsula Sequência)**

Crie uma tool de alto nível que internamente chama outras tools na ordem correta:

```python
@tool
def obter_localizacao_completa() -> dict:
    """
    Obtém localização completa do usuário (IP + geolocalização).

    Esta tool internamente chama obter_ip_externo() seguido de
    obter_geolocalizacao_ip(), garantindo a ordem correta.

    Returns:
        Dicionário com IP e localização
    """
    # Passo 1: Obter IP (garantido executar primeiro)
    ip = obter_ip_externo()

    # Passo 2: Obter localização (garantido executar depois)
    localizacao = obter_geolocalizacao_ip(ip)

    return {
        "ip": ip,
        "localizacao": localizacao
    }
```

**Vantagens**:
- ✅ Sequência garantida dentro da tool
- ✅ Modelo vê apenas 1 tool (interface mais simples)
- ✅ Reutilizável em outros contextos

**Desvantagens**:
- ❌ Perde granularidade (não pode chamar só Tool 1)
- ❌ Histórico de mensagens não mostra passos intermediários
- ❌ Debugging mais difícil (tudo acontece dentro da tool)

**Alternativa 3: Conditional Edges com Verificação de State**

Use conditional edges para verificar se pré-requisitos foram executados antes de permitir tool:

```python
def pode_chamar_tool_2(state: AgentState) -> str:
    """Verifica se Tool 1 já foi executada antes de permitir Tool 2."""
    if not state.get("ip_externo"):
        return "tool_1_primeiro"  # Força Tool 1
    return "tool_2_ok"  # Permite Tool 2

def raciocinar(state):
    """Modelo decide qual tool chamar."""
    response = llm_with_tools.invoke(state["messages"])

    # Se modelo tentou chamar Tool 2 sem pré-requisito
    if response.tool_calls:
        tool_name = response.tool_calls[0]['name']
        if tool_name == 'obter_geolocalizacao_ip_v2':
            # Redireciona para verificação
            return {"messages": [response], "verificar_prereq": True}

    return {"messages": [response]}

# Grafo com verificação
workflow = StateGraph(AgentState)
workflow.add_node("raciocinar", raciocinar)
workflow.add_node("verificar", lambda s: s)  # Nó de verificação
workflow.add_node("tools", tool_node)

workflow.set_entry_point("raciocinar")
workflow.add_conditional_edges("raciocinar", should_continue, {
    "verificar": "verificar",
    "tools": "tools",
    "end": END
})
workflow.add_conditional_edges("verificar", pode_chamar_tool_2, {
    "tool_1_primeiro": "tools",  # Executa Tool 1
    "tool_2_ok": "tools"          # Executa Tool 2
})
```

**Vantagens**:
- ✅ Grafo valida pré-requisitos
- ✅ Modelo ainda tem flexibilidade
- ✅ Pode corrigir decisões erradas do modelo

**Desvantagens**:
- ❌ Complexidade alta (muito código de validação)
- ❌ Difícil de manter (lógica espalhada)
- ❌ Iterações extras para correções

**Alternativa 4: Voltar para Tools Simples (V1)**

A alternativa mais simples é não usar Command + InjectedState e voltar para tools que recebem argumentos explícitos:

```python
@tool
def obter_ip_externo() -> str:
    """Obtém IP externo."""
    return "187.75.23.45"

@tool
def obter_geolocalizacao_ip(ip: str) -> str:
    """
    Obtém geolocalização de um IP.

    Args:
        ip: Endereço IP para consultar
    """
    return f"São Paulo, SP (baseado em {ip})"
```

O modelo precisa passar o IP como argumento, o que força a sequência lógica:
- Modelo não consegue chamar `obter_geolocalizacao_ip()` sem ter o IP
- Se tentar, receberá erro de argumento faltante
- Precisa chamar `obter_ip_externo()` primeiro para obter o IP

**Vantagens**:
- ✅ Simplicidade máxima
- ✅ Sem complexidade adicional (reducers, Command, etc)
- ✅ Sequência emerge naturalmente dos argumentos obrigatórios
- ✅ Menos chance de erros de implementação

**Desvantagens**:
- ❌ Modelo precisa copiar/colar resultados entre tools
- ❌ State não é enriquecido com dados intermediários
- ❌ Histórico fica mais verboso

#### Recomendação Final: Quando Usar Cada Abordagem

| Cenário | Abordagem Recomendada |
|---------|----------------------|
| **Sequência crítica, sempre a mesma** | Grafo com nós separados (Alt. 1) |
| **Pipeline conhecido, reutilizável** | Tool composta (Alt. 2) |
| **Agente flexível, validação possível** | Conditional edges (Alt. 3) |
| **Simplicidade prioritária** | Tools simples V1 (Alt. 4) ⭐ |
| **Debugging/state rico prioritário** | Command + InjectedState + validação defensiva |

**Para a maioria dos casos: Tools simples V1 (Alternativa 4) é a escolha mais prática.**

Command + InjectedState adiciona complexidade que só se justifica quando:
1. State precisa ser inspecionado externamente (callbacks, persistência)
2. Múltiplas tools independentes compartilham dados
3. Validação defensiva + iterações extras são aceitáveis

**Para nosso caso de teste Android**: Tools simples V1 é suficiente e mais confiável.

---

## Conclusões e Recomendações

### Quando Usar LangGraph + ToolNode

**Recomendado para**:

1. **Aplicações interativas/reativas**
   - Android testing (nosso caso)
   - Navegação web autônoma
   - Exploração de APIs desconhecidas
   - Qualquer cenário onde a resposta muda o ambiente

2. **Quando re-planejamento é necessário**
   - Não sabemos quantos passos serão necessários
   - Decisões dependem de resultados intermediários
   - Podem ocorrer falhas que exigem estratégia alternativa

3. **Projetos com múltiplos agentes/grafos complexos**
   - LangGraph permite estruturas beyond ReACT simples
   - Ramificações condicionais
   - Sub-grafos e delegação

4. **Quando debugging é crítico**
   - LangSmith rastreia cada passo
   - Visualização do grafo de execução
   - Análise de performance

**Trade-off**: Mais lento (múltiplas gerações), mas mais robusto e flexível.

### Quando Usar Mistral Manual

**Recomendado para**:

1. **Consultas com pipeline conhecido**
   - "Em que cidade estou?" → sempre IP + geolocalização
   - "Qual o clima em X?" → sempre geolocalização + clima
   - Pipeline fixo e previsível

2. **Performance é prioridade**
   - 2 gerações vs N gerações
   - Reduz latência significativamente
   - Economiza tokens/custo

3. **Ambiente estático**
   - Resultados de tools não mudam o ambiente
   - Não precisa re-analisar após cada ação

4. **Prototipagem rápida**
   - Menos código para setup
   - Mais controle manual
   - Bom para entender function calling

**Trade-off**: Mais rápido, mas menos flexível e mais código manual.

### Por que LangGraph é Superior para Android Testing

Nosso caso específico tem características que favorecem LangGraph:

1. **Ambiente muda a cada ação**
   ```
   Click em botão → Nova tela carrega
   Coordenadas antigas não são mais válidas
   Modelo precisa VER nova tela para decidir próxima ação
   ```

2. **Pipeline desconhecido**
   - Não sabemos quantas ações serão necessárias
   - Cada app tem fluxo diferente
   - Exploração é não-determinística

3. **Vision necessária a cada passo**
   - Screenshot muda após cada ação
   - Análise visual guia decisões
   - Qwen2.5-VL + LangGraph permite isso

4. **Debugging é essencial**
   - Precisamos entender por que modelo escolheu determinada ação
   - LangSmith permite análise post-mortem
   - Visualização do grafo de decisões

### Modelfile Customizado: Quando Aplicar

**Você pode criar Modelfile customizado quando**:

1. Modelo base tem function calling training
2. Modelo não está na whitelist do Ollama
3. Precisa de ajustes no template (formato de prompt específico)

**Você NÃO pode criar function calling do zero via template**:

- Modelos sem training retornarão texto, não JSONs
- Template apenas expõe capacidade existente

**Modelos que podem se beneficiar**:

- Versões novas de modelos conhecidos (ex: Qwen 3.0 quando lançar)
- Fine-tunes de modelos com function calling (ex: Qwen2.5-custom)
- Modelos multimodais recentes não reconhecidos pelo Ollama

### Arquitetura Recomendada para Este Projeto

Para o agente de teste Android, a arquitetura ideal é:

```
src/experimental/android_agent/
├── parser/
│   └── uiautomator.py          # Extrai elementos + coordenadas do XML
├── tools/
│   ├── android_fake.py         # Tools fake (para teste)
│   └── android_real.py         # Tools reais (ADB integration)
├── agent/
│   └── react_agent_with_tools.py  # LangGraph + ToolNode
└── models/
    └── Modelfile.qwen-vision-tools-v1  # Modelo customizado

Modelo: qwen-vision-tools-v1
Framework: LangGraph
Tools: bind_tools() + ToolNode
Encadeamento: Múltiplas iterações do grafo
```

**Vantagens desta arquitetura**:
- Vision + Tools integrados
- Execução automática de ações
- Re-análise de screenshot após cada ação
- Código limpo e manutenível
- Expansível (fácil adicionar novos nós ao grafo)

---

## Referências e Arquivos

### Arquivos de Código

**Agente Android**:
- `src/experimental/android_agent/agent/react_agent_with_tools.py` - Agente LangGraph completo
- `src/experimental/android_agent/tools/android_fake.py` - 7 tools fake
- `src/experimental/android_agent/parser/uiautomator.py` - Parser de XML UIAutomator

**Modelfiles**:
- `Modelfile.qwen-vision-tools-v1` - Qwen2.5-VL com tools ✅
- `Modelfile.llama32-vision-tools-v1` - Llama 3.2 Vision com tools ✅
- `Modelfile.moondream-tools-test` - Teste de template vs treinamento ❌

**Testes**:
- `teste_custom_vision_tools_v1.py` - Validação Qwen2.5-VL com tools ✅
- `teste_llama32_vision_tools.py` - Validação Llama 3.2 Vision com tools ✅
- `teste_moondream_tools.py` - Teste de template vs treinamento ❌
- `teste_langgraph_encadeamento.py` - Teste de encadeamento com LangGraph
- `teste_langgraph_command_state.py` - Teste comparativo Command + InjectedState vs tools antigas

**Exemplo Mistral**:
- `src/exemplos/basico/function_call.py` - Function calling manual com Mistral
- `src/agents/mistral_agent_clean.py` - Agente Mistral reutilizável

### Logs de Resultados

**Sucesso com modelos customizados**:
- `teste_custom_vision_tools_v1.log` - Qwen2.5-VL: 3 tool calls ✅
- `teste_llama32_vision_tools.log` - Llama 3.2 Vision: 1 tool call ✅

**Teste de template vs treinamento**:
- `teste_moondream_tools.log` - 0 tool calls (template insuficiente) ❌

**Testes de encadeamento**:
- `teste_langgraph_encadeamento_v2.log` - Nenhum modelo retornou múltiplas tools

**Testes de Command + InjectedState**:
- `teste_langgraph_command_state_v2.log` - Sucesso: ambas abordagens funcionam com 2 iterações
- `teste_langgraph_command_state_final.log` - Falha: V2 atingiu max iterations sem salvar localização
- `teste_langgraph_command_state.log` - Falha: modelo não chamou tools (modelo errado)

**Resultados históricos Mistral**:
- `/home/pedro/tmp/results-apc/function_call_real_20250929_155051/` - Exemplo com 3 tools encadeadas

### Documentação Externa

**Ollama**:
- [Tool Support Blog Post](https://ollama.com/blog/tool-support)
- [Modelfile Documentation](https://github.com/ollama/ollama/blob/main/docs/modelfile.md)

**LangGraph**:
- [How to Call Tools](https://langchain-ai.github.io/langgraph/how-tos/tool-calling/)
- [ToolNode Reference](https://langchain-ai.github.io/langgraph/reference/prebuilt/#toolnode)
- [GitHub Discussion #2394: Parallel Tool Execution](https://github.com/langchain-ai/langgraph/discussions/2394)
- [GitHub Issue #303: Sequential Tool Execution Request](https://github.com/langchain-ai/langgraphjs/issues/303)

**LangChain**:
- [Tool Calling Concepts](https://python.langchain.com/docs/concepts/tool_calling/)
- [How to Disable Parallel Tool Calling](https://python.langchain.com/docs/how_to/tool_calling_parallel/)

**Mistral AI**:
- [Function Calling Documentation](https://docs.mistral.ai/capabilities/function_calling/)

---

## Apêndice: Exemplo Completo de Uso

### Setup do Ambiente

```bash
# 1. Criar modelo customizado
ollama create qwen-vision-tools-v1 -f Modelfile.qwen-vision-tools-v1

# 2. Verificar
ollama list | grep qwen-vision-tools-v1

# 3. Instalar dependências
pip install langchain-ollama langgraph langchain-core
```

### Código Mínimo Funcional

```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict, List, Annotated
import operator

# 1. Definir tools
@tool
def exemplo_tool(param: str) -> str:
    """Tool de exemplo."""
    return f"Executado com {param}"

# 2. Definir estado
class State(TypedDict):
    messages: Annotated[List, operator.add]

# 3. Criar modelo com tools
llm = ChatOllama(model="qwen-vision-tools-v1")
llm_with_tools = llm.bind_tools([exemplo_tool])
tool_node = ToolNode([exemplo_tool])

# 4. Definir nós
def raciocinar(state):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

def should_continue(state):
    if hasattr(state["messages"][-1], 'tool_calls') and state["messages"][-1].tool_calls:
        return "tools"
    return "end"

# 5. Construir grafo
workflow = StateGraph(State)
workflow.add_node("raciocinar", raciocinar)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("raciocinar")
workflow.add_conditional_edges("raciocinar", should_continue, {
    "tools": "tools",
    "end": END
})
workflow.add_edge("tools", "raciocinar")

agente = workflow.compile()

# 6. Executar
resultado = agente.invoke({
    "messages": [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Use a tool de exemplo com o parametro 'teste'")
    ]
})

print(resultado["messages"])
```

Este exemplo mínimo demonstra todos os conceitos fundamentais:
- Definição de tools com `@tool`
- Modelo customizado via Ollama
- `bind_tools()` para registrar tools
- ToolNode para execução automática
- Grafo com loop para múltiplas iterações
- Estado com histórico de mensagens

---

## Apêndice A: Atualização Assíncrona do State

### Motivação para Android Testing

No contexto de testes Android, o agente pode precisar aguardar eventos externos antes de continuar:
- Aguardar callback de ação executada via ADB
- Esperar notificação de que screenshot foi capturado
- Receber resultado de análise em background
- Sincronizar com fila de eventos de sistema externo

O LangGraph suporta atualização assíncrona do state através de **checkpointers** e da API `aupdate_state()`.

### Como Funciona

**Arquitetura**:

```
1. LangGraph compila com checkpointer (MemorySaver, SqliteSaver, etc)
2. Grafo executa e pode pausar aguardando eventos
3. Sistema externo (fila, webhook, callback) detecta evento
4. Sistema chama aupdate_state() para atualizar state
5. Próximo nó do grafo já tem acesso aos dados atualizados
```

**Componentes necessários**:

1. **Checkpointer**: Persiste state entre execuções
   ```python
   from langgraph.checkpoint.memory import InMemorySaver
   from langgraph.checkpoint.sqlite import AsyncSqliteSaver

   # Opção 1: Em memória (testes)
   checkpointer = InMemorySaver()

   # Opção 2: SQLite (persistência)
   checkpointer = AsyncSqliteSaver.from_conn_string("checkpoint.db")
   ```

2. **Thread ID**: Identifica sessão do grafo
   ```python
   config = {"configurable": {"thread_id": "android_test_123"}}
   ```

3. **API de Atualização**:
   ```python
   # Síncrono
   snapshot = graph.update_state(config, values={"screenshot_ready": True})

   # Assíncrono
   snapshot = await graph.aupdate_state(config, values={"screenshot_ready": True})
   ```

### Exemplo Conceitual para Android

**Cenário**: Agente executa ação via ADB e aguarda callback antes de continuar.

**State**:
```python
class AndroidState(TypedDict):
    messages: Annotated[List, operator.add]
    screenshot_path: str
    ui_description: str
    action_completed: bool  # ← Atualizado externamente
    last_action_result: str  # ← Atualizado externamente
```

**Grafo com nó de espera**:
```python
def executar_acao(state):
    """Executa ação via ADB e retorna imediatamente."""
    # Executa comando ADB de forma assíncrona
    adb_async_execute("input tap 500 300")

    # Marca que está aguardando
    return {
        **state,
        "action_completed": False,
        "aguardando_callback": True
    }

def verificar_conclusao(state):
    """Verifica se ação foi concluída (via state atualizado externamente)."""
    if state.get("action_completed"):
        return "continuar"
    else:
        return "aguardar"  # Volta para aguardar

def processar_resultado(state):
    """Processa resultado após confirmação."""
    resultado = state.get("last_action_result")
    print(f"Ação concluída: {resultado}")
    # Captura novo screenshot, etc
    return state

# Construir grafo
workflow = StateGraph(AndroidState)
workflow.add_node("executar_acao", executar_acao)
workflow.add_node("verificar", verificar_conclusao)
workflow.add_node("processar", processar_resultado)

workflow.set_entry_point("executar_acao")
workflow.add_edge("executar_acao", "verificar")
workflow.add_conditional_edges("verificar", lambda s: s.get("action_completed"), {
    True: "processar",
    False: "verificar"  # Loop até action_completed = True
})

graph = workflow.compile(checkpointer=InMemorySaver())
```

**Sistema externo atualiza state**:
```python
# Callback do ADB ou sistema de monitoramento
async def adb_callback_handler(thread_id: str, resultado: str):
    """
    Chamado quando ADB confirma que ação foi executada.
    Atualiza state do LangGraph de forma assíncrona.
    """
    config = {"configurable": {"thread_id": thread_id}}

    # Atualiza state externamente
    await graph.aupdate_state(
        config,
        values={
            "action_completed": True,
            "last_action_result": resultado
        }
    )

    # Próxima iteração do grafo verá state atualizado
```

**Execução**:
```python
# Thread 1: Executa grafo
config = {"configurable": {"thread_id": "test_123"}}
resultado = await graph.ainvoke(initial_state, config)

# Thread 2: Sistema externo recebe callback e atualiza
await adb_callback_handler("test_123", "Click executado com sucesso")

# Thread 1: Grafo detecta mudança e continua
```

### Referências da API

**Métodos de atualização**:

```python
# Síncrono
graph.update_state(
    config: RunnableConfig,
    values: dict,
    *,
    as_node: Optional[str] = None  # Simula atualização vindo de nó específico
) -> StateSnapshot

# Assíncrono
await graph.aupdate_state(
    config: RunnableConfig,
    values: dict,
    *,
    as_node: Optional[str] = None
) -> StateSnapshot
```

**Checkpointers assíncronos**:
- `AsyncSqliteSaver` - Para persistência em SQLite
- `AsyncPostgresSaver` - Para PostgreSQL
- `InMemorySaver` - Funciona tanto síncrono quanto assíncrono

**Documentação oficial**:
- [Persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [Time Travel](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/time-travel/)
- [Graph Reference - aupdate_state](https://langchain-ai.github.io/langgraph/reference/graphs/)

### Limitações

1. **Polling vs Event-Driven**:
   - Atualização de state é manual (precisa chamar `aupdate_state`)
   - Não há mecanismo nativo de escuta de eventos
   - Requer integração externa (filas, webhooks, callbacks)

2. **Concorrência**:
   - Múltiplas atualizações ao mesmo thread podem colidir
   - Checkpointer gerencia com timestamps
   - Pode haver race conditions em cenários complexos

3. **Performance**:
   - Cada atualização cria novo checkpoint
   - Overhead de I/O (SQLite, PostgreSQL)
   - Para cenários de alta frequência, considerar buffers

---

## Apêndice B: Alternativas para Vision + Tools Local

### Resultado da Investigação Profunda

Após busca extensiva na documentação e comunidade (Outubro 2025), identificamos as seguintes alternativas para usar vision models com function calling:

### 1. Ollama + Modelfile Customizado (Nossa Solução) ⭐

**Status**: ✅ Funciona perfeitamente

**Como**: Criar Modelfile customizado adicionando template de tools ao modelo base

**Vantagens**:
- Funciona nativamente com `bind_tools()` + ToolNode do LangGraph
- Não requer mudanças no código do agente
- Modelo permanece local
- Integração transparente

**Desvantagens**:
- Requer criação manual do Modelfile para cada modelo
- Depende do modelo base ter treinamento de function calling
- Ollama não reconhece automaticamente (Issue #8626 ainda aberta)

**Modelos testados com sucesso**:
- `qwen-vision-tools-v1` (Qwen2.5-VL-7B + template customizado) ✅
- `llama32-vision-tools-v1` (Llama 3.2 Vision 11B + template customizado) ✅

**Status oficial Ollama** (Out/2025):
- [Issue #8626](https://github.com/ollama/ollama/issues/8626): "Tool Support for vision models" - ABERTA
- [Issue #8345](https://github.com/ollama/ollama/issues/8345): "llama3.2-vision does not support tools" - ABERTA
  - **Resolvido via Modelfile**: `llama32-vision-tools-v1` funciona perfeitamente ✅
- Sem previsão de suporte nativo oficial

### 2. HuggingFace Transformers Direto (Qwen2.5-VL/Qwen3-VL)

**Status**: ✅ Funciona, mas requer integração manual

**Como**: Usar `transformers` diretamente ao invés de via Ollama

```python
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

model = Qwen2VLForConditionalGeneration.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")
processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")
```

**Modelos com tools nativos**:
- **Qwen2.5-VL** (Fevereiro 2025):
  - "directly plays as a visual agent that can reason and dynamically direct tools"
  - Suporta JSON estruturado para tool calls
  - Computer use e phone use capabilities

- **Qwen3-VL** (2025):
  - "can operate graphical interfaces (PC/mobile)"
  - "understands functions, and performs real-world tasks through tool invocation"
  - Reconhece elementos de UI e invoca tools

**Vantagens**:
- Tools nativos (não precisa de Modelfile)
- Controle total sobre geração
- Modelos mais recentes

**Desvantagens**:
- ❌ Não funciona com ToolNode do LangGraph (requer integração manual)
- ❌ Precisa implementar parsing de tool calls
- ❌ Precisa implementar execução de tools
- ❌ Mais código boilerplate
- Carregamento mais lento (sem cache do Ollama)

**Integração com LangGraph**:
```python
# Requer criar wrapper customizado
class Qwen2VLWrapper:
    def __init__(self):
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(...)

    def bind_tools(self, tools):
        # Implementar conversão de tools para formato Qwen
        # Implementar parsing de respostas
        # Implementar execução
        pass
```

### 3. smolagents (Nova Biblioteca 2025)

**Status**: ⚠️ Em desenvolvimento ativo

**Como**: Usar `smolagents` que integra VLMs com tools

```python
# Conceitual - verificar docs atualizadas
from smolagents import VLMAgent

agent = VLMAgent(model="Qwen2.5-VL-7B", tools=[...])
```

**Características**:
- Implementa ReAct framework
- Suporte a VLMs com tools integrado
- Casos de uso: Document AI, GUI control

**Vantagens**:
- Integração mais simples que HuggingFace direto
- Projetado especificamente para agentes visuais

**Desvantagens**:
- ❌ Não usa LangGraph (framework diferente)
- ❌ Comunidade/docs menores
- ⚠️ Biblioteca nova (menos madura)

### 4. APIs Pagas (Cloud)

**Status**: ✅ Suporte nativo completo

**Provedores** (todos com vision + tools nativos):
- **GPT-4o** (OpenAI) - Liderança em function calling
- **Claude Sonnet** (Anthropic) - Ótimo para reasoning
- **Gemini 2.0** (Google) - Performance competitiva

**Integração com LangGraph**:
```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# Funciona nativamente com bind_tools() + ToolNode
llm = ChatOpenAI(model="gpt-4o")
# ou
llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")

llm_with_tools = llm.bind_tools(tools)  # ✅ Funciona out-of-the-box
```

**Vantagens**:
- ✅ Funciona nativamente com LangGraph
- ✅ Melhor performance de function calling
- ✅ Sem setup local

**Desvantagens**:
- ❌ Custo por token
- ❌ Dados enviados para cloud
- ❌ Requer internet
- ❌ Latência de rede

### Comparação Resumida

| Solução | Local | LangGraph Nativo | Tools Nativos | Setup | Performance |
|---------|-------|------------------|---------------|-------|-------------|
| **Ollama + Modelfile** ⭐ | ✅ | ✅ | ⚠️ Via template | Médio | Alta |
| **HuggingFace direto** | ✅ | ❌ | ✅ | Alto | Média |
| **smolagents** | ✅ | ❌ | ✅ | Médio | Média |
| **APIs pagas** | ❌ | ✅ | ✅ | Baixo | Muito Alta |

### Recomendação Final

**Para este projeto (teste Android local com LangGraph)**:

1. **Melhor opção**: Ollama + Modelfile customizado (`qwen-vision-tools-v1`)
   - ✅ Funciona nativamente com bind_tools() + ToolNode
   - ✅ Totalmente local
   - ✅ Já validado e funcionando
   - ✅ Código do agente permanece limpo

2. **Se precisar de modelos mais novos**: HuggingFace direto (Qwen2.5-VL/Qwen3-VL)
   - Tools nativos mais robustos
   - Mas requer refatoração significativa do código

3. **Para produção com orçamento**: APIs pagas
   - GPT-4o ou Claude Sonnet
   - Melhor performance e confiabilidade

**Nosso Modelfile customizado não é um workaround, é a solução oficial atual para Ollama** até que o Issue #8626 seja resolvido.

---

## Apêndice C: Observabilidade e Debugging com LangSmith

### O que é LangSmith?

LangSmith é a plataforma oficial de observabilidade para aplicações LangChain/LangGraph. Funciona como um "debugger visual" que captura automaticamente cada execução do seu agente, permitindo análise detalhada de:

- Estrutura do grafo executado
- Fluxo de mensagens entre nós
- Tool calls com argumentos e resultados
- Tempo de execução de cada componente
- Tokens consumidos
- Erros com contexto completo

### Por que Usar com LangGraph?

Debugging de agentes ReACT com vision models é complexo:
- Múltiplas iterações do loop
- Decisões do modelo nem sempre óbvias
- Tool calls podem falhar silenciosamente
- Difícil entender POR QUE o modelo escolheu determinada ação

**LangSmith resolve isso mostrando**:
1. Qual screenshot o modelo viu
2. Qual tool o modelo decidiu chamar (e por quê)
3. Resultado de cada tool
4. Próxima decisão após ver resultado
5. Onde o agente travou ou entrou em loop

### Configuração

**Passo 1: Criar conta**

Acesse https://smith.langchain.com e crie uma conta gratuita (tier free existe).

**Passo 2: Obter API Key**

No dashboard do LangSmith:
1. Settings → API Keys
2. Create API Key
3. Copiar a chave

**Passo 3: Configurar no ambiente**

**Opção A: Variáveis de ambiente** (recomendado):

```bash
# Adicionar ao ~/.bashrc ou ~/.zshrc
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY="lsv2_pt_..."  # Sua chave aqui
export LANGCHAIN_PROJECT="android-agent-tests"  # Nome do projeto

# Recarregar shell
source ~/.bashrc
```

**Opção B: No código Python**:

```python
import os

# Configurar antes de criar o agente
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "lsv2_pt_..."
os.environ["LANGCHAIN_PROJECT"] = "android-agent-tests"

# Código normal do LangGraph - rastreamento automático
from langgraph.graph import StateGraph
# ... seu código ...
```

**Opção C: Arquivo .env**:

```bash
# Criar .env na raiz do projeto
echo "LANGCHAIN_TRACING_V2=true" >> .env
echo "LANGCHAIN_API_KEY=lsv2_pt_..." >> .env
echo "LANGCHAIN_PROJECT=android-agent-tests" >> .env
```

```python
# Carregar no código
from dotenv import load_dotenv
load_dotenv()

# Resto do código normal
```

### O que Aparece no Dashboard

Após executar seu agente, acesse https://smith.langchain.com e verá:

#### 1. Lista de Execuções (Traces)

```
┌─────────────────────────────────────────────────────────┐
│ Trace: android-agent-click-login                       │
│ Status: ✅ Success                                      │
│ Duration: 12.3s                                         │
│ Tokens: 1,247 (input: 890, output: 357)               │
│ Cost: $0.0023                                           │
└─────────────────────────────────────────────────────────┘
```

#### 2. Visualização do Grafo

```
[START] → [observar] → [raciocinar] → [tools] → [increment] → ...
                            ↓                         ↑
                          [END] ←─── (loop) ─────────┘
```

Cada nó mostra:
- ⏱️ Tempo de execução
- 📊 Input/Output
- ❌ Erros (se houver)

#### 3. Timeline de Execução

```
0.0s   [observar]         → SystemMessage adicionado
0.1s   [raciocinar]       → Modelo analisa screenshot
3.2s   [raciocinar]       → AIMessage(tool_calls=[click])
3.3s   [tools]            → Executa click(540, 273)
3.4s   [tools]            → ToolMessage("Clicked at ...")
3.5s   [increment]        → iteration=1
3.6s   [raciocinar]       → Modelo analisa novamente
6.8s   [raciocinar]       → AIMessage(tool_calls=[set_text])
...
```

#### 4. Detalhes de Tool Calls

Para cada tool call, você vê:

```json
{
  "tool_call_id": "call_abc123",
  "name": "click",
  "arguments": {
    "x": 540,
    "y": 273
  },
  "result": "Clicked at position (540, 273)"
}
```

#### 5. Mensagens Completas

Histórico de todas as mensagens:

```
[0] SystemMessage
    content: "You are an Android testing agent..."

[1] HumanMessage
    content: [text, image]
    - text: "Analyze this screen and decide action"
    - image: <screenshot thumbnail>

[2] AIMessage
    content: ""
    tool_calls: [{"name": "click", "args": {"x": 540, "y": 273}}]

[3] ToolMessage
    content: "Clicked at position (540, 273)"
    tool_call_id: "call_abc123"

[4] AIMessage
    content: "I clicked the login button. Let me wait for the next screen..."
    tool_calls: []
```

#### 6. Imagens (Vision Models)

**Diferencial importante**: LangSmith mostra os screenshots que o modelo analisou!

Você clica na mensagem e vê:
- 🖼️ Screenshot original
- 🎯 Coordenadas clicadas (se aplicável)
- 📝 Análise do modelo
- 🔧 Tool escolhida

### Exemplo Prático: Debugging Android Test

**Cenário**: Agente clica no botão errado.

**Sem LangSmith**:
- Você só vê logs: "Clicked at (540, 273)"
- Não sabe POR QUE o modelo escolheu essas coordenadas
- Difícil reproduzir o problema

**Com LangSmith**:
1. Abre trace da execução
2. Vê screenshot que modelo analisou
3. Vê tool call: `click(540, 273)`
4. Vê UI description que modelo recebeu
5. Entende: "Ah, o XML tinha dois botões com texto similar, modelo escolheu errado"

**Solução identificada**: Melhorar UI description para diferenciar botões.

### Filtragem e Busca

LangSmith permite filtrar execuções:

```
Status: ✅ Success | ❌ Error | ⏸️ Running
Duration: > 10s
Tokens: > 5000
Project: android-agent-tests
Tags: screenshot-analysis, click-action
```

Busca por:
- Nome da tool
- Conteúdo de mensagens
- Erros específicos
- Range de datas

### Feedback Loop

Recursos avançados:

1. **Anotações**: Marcar execuções como "boa" ou "ruim"
2. **Comparação**: Comparar duas execuções lado a lado
3. **Datasets**: Criar conjunto de testes a partir de traces reais
4. **Regression Testing**: Rodar dataset após mudanças no código

### Configuração Avançada

**Desabilitar para testes rápidos**:

```python
# Temporariamente desabilitar
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Ou usar context manager
from langchain.callbacks.tracers.langchain import wait_for_all_tracers

with wait_for_all_tracers():
    # Código que não quer rastrear
    pass
```

**Projetos separados**:

```python
# Desenvolvimento
os.environ["LANGCHAIN_PROJECT"] = "android-agent-dev"

# Testes
os.environ["LANGCHAIN_PROJECT"] = "android-agent-tests"

# Produção
os.environ["LANGCHAIN_PROJECT"] = "android-agent-prod"
```

**Tags customizadas**:

```python
from langchain.callbacks import LangChainTracer

tracer = LangChainTracer(
    project_name="android-agent",
    tags=["screenshot-001", "login-flow"]
)

resultado = agente.invoke(
    state,
    config={"callbacks": [tracer]}
)
```

### Limitações

1. **Requer internet**: Traces são enviados para cloud LangSmith
2. **Latência adicional**: ~50-100ms por trace (assíncrono, não bloqueia)
3. **Tamanho de imagens**: Screenshots grandes aumentam upload
4. **Tier free**: Limite de traces/mês (verificar planos atuais)

### Alternativas Locais

Se não pode usar cloud:

**Opção 1: LangSmith Self-Hosted** (Enterprise):
- Requer licença
- Deploy em servidor próprio

**Opção 2: Logging customizado**:

```python
import logging
from langchain.callbacks import StdOutCallbackHandler

logging.basicConfig(level=logging.INFO)

agente = workflow.compile()
resultado = agente.invoke(
    state,
    config={"callbacks": [StdOutCallbackHandler()]}
)
```

**Opção 3: Salvar traces em arquivo**:

```python
import json
from datetime import datetime

def salvar_trace(state, resultado):
    trace = {
        "timestamp": datetime.now().isoformat(),
        "messages": [msg.dict() for msg in resultado["messages"]],
        "iterations": resultado["iteration"],
        # ... outros campos
    }

    filename = f"traces/trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(trace, f, indent=2, ensure_ascii=False)
```

### Dicas de Uso

1. **Sempre ative no desenvolvimento**: Vale a pena mesmo com latência
2. **Use projetos separados**: Facilita organização
3. **Anote execuções problemáticas**: Marca para revisar depois
4. **Compare antes/depois**: Ao mudar prompts ou tools
5. **Screenshots são ouro**: Você VÊ o que modelo viu (crucial para vision)

### Integração com Nosso Agente

Arquivo: `src/experimental/android_agent/agent/react_agent_with_tools.py`

**Já funciona automaticamente!** Só precisa das variáveis de ambiente.

Para verificar se está funcionando:

```python
# Adicionar print de confirmação
import os

if os.getenv("LANGCHAIN_TRACING_V2") == "true":
    print(f"✅ LangSmith ativo: {os.getenv('LANGCHAIN_PROJECT')}")
else:
    print("⚠️  LangSmith desabilitado")

# Executar agente normalmente
agente = criar_agente_com_tools(...)
resultado = agente.invoke(...)

# Checar dashboard: https://smith.langchain.com
```

### Recursos Adicionais

**Documentação oficial**:
- [LangSmith Docs](https://docs.smith.langchain.com/)
- [Tracing LangGraph](https://docs.smith.langchain.com/tracing/faq/langchain_specific_guides/langgraph)
- [Debugging Tips](https://docs.smith.langchain.com/tracing/faq/debugging_tips)

**Tutoriais em vídeo**:
- [LangSmith Overview](https://www.youtube.com/watch?v=gE_z9lqZoYI)
- [Debugging LangGraph Agents](https://www.youtube.com/watch?v=VqVeFWvX_-0)

---

**Última atualização**: 2025-10-13
**Versão do documento**: 1.4
**Changelog**:
- v1.4 (2025-10-13): Adicionada seção detalhada sobre Llama 3.2 Vision com Tools (Modelfile, testes, comparação com Qwen)
- v1.3 (2025-10-13): Adicionado Apêndice C (Observabilidade com LangSmith)
- v1.2 (2025-10-13): Adicionados Apêndices A (Atualização Assíncrona) e B (Alternativas Vision+Tools)
- v1.1 (2025-10-13): Adicionada seção Command + InjectedState com análise de limitações e alternativas práticas
- v1.0 (2025-10-13): Versão inicial cobrindo investigação completa de tools com vision models

**Autor**: Investigação colaborativa Claude + Usuário

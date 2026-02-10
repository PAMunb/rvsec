# Validacao Individual de Modelos

**Data**: 2025-12-25
**Status**: Em andamento

## Objetivo

Testar cada modelo individualmente, ajustando configuracoes (parser, coordenadas, etc) ate funcionar corretamente.

## Resumo Apos Validacao Manual

### Modelos FUNCIONAIS (recomendados)

| Modelo | Server | coords_provided | visual_only | Status |
|--------|--------|-----------------|-------------|--------|
| Qwen3-VL-4B-Instruct | SGLang | 100% | 50% | **MELHOR** - Recomendado |
| MiniCPM-V-4.5 | vLLM | 92.9% | 46.4% | **OK** - Bom grounding |
| Fara-7B | vLLM | 92.9% | 14.3% | **OK** - Microsoft, vLLM |
| gemma-3-4b-it | SGLang | 100% | 3.6% | OK coords, grounding ruim |

### Modelos EXCLUIDOS

| Modelo | Server | Motivo |
|--------|--------|--------|
| Qwen3-VL-4B-Thinking | SGLang | Gera lixo multilingual |
| Llava-OneVision-7B | vLLM | Arquitetura nao suportada |
| Molmo-7B-D-0924 | vLLM | Requer tensorflow |
| InternVL2-8B | vLLM | Nao gera tool calls estruturados |
| AutoGLM-Phone-9B | vLLM | Incompativel com bitsandbytes |

---

## Modelos a Testar

### 1. Llava-OneVision-7B

**HuggingFace**: `lmms-lab/llava-onevision-qwen2-7b-ov`
**Status**: INCOMPATIVEL com vLLM

#### Teste Manual

```bash
MODEL_PATH=lmms-lab/llava-onevision-qwen2-7b-ov \
TOOL_CALL_PARSER=pythonic \
QUANTIZATION=bitsandbytes \
docker compose -f docker-compose.vllm.yml up
```

#### Resultado

- Data: 2025-12-25
- coords_provided: N/A
- visual_only: N/A
- **Erro**: `Model architectures ['LlavaQwenForCausalLM'] are not supported`
- **Nota**: vLLM suporta `LlavaOnevisionForConditionalGeneration` mas este modelo usa `LlavaQwenForCausalLM`
- **Conclusao**: Modelo EXCLUIDO - arquitetura incompativel

---

### 2. Molmo-7B-D-0924

**HuggingFace**: `allenai/Molmo-7B-D-0924`
**Status**: INCOMPATIVEL - requer tensorflow

#### Teste Manual

```bash
MODEL_PATH=allenai/Molmo-7B-D-0924 \
TOOL_CALL_PARSER=pythonic \
QUANTIZATION=bitsandbytes \
CONTEXT_LENGTH=4096 \
docker compose -f docker-compose.vllm.yml up
```

#### Resultado

- Data: 2025-12-25
- coords_provided: N/A
- visual_only: N/A
- **Erro**: `ImportError: This modeling file requires tensorflow`
- **Nota**: max_position_embeddings=4096 (requer CONTEXT_LENGTH=4096)
- **Conclusao**: Modelo EXCLUIDO - requer tensorflow nao disponivel no vLLM

---

### 3. InternVL2-8B

**HuggingFace**: `OpenGVLab/InternVL2-8B`
**Status**: NAO SUPORTA tool calls estruturados

#### Teste Manual

```bash
MODEL_PATH=OpenGVLab/InternVL2-8B \
TOOL_CALL_PARSER=pythonic \
QUANTIZATION=bitsandbytes \
CONTEXT_LENGTH=4096 \
EXTRA_ARGS="--max-num-seqs 16 --gpu-memory-utilization 0.75" \
docker compose -f docker-compose.vllm.yml up
```

#### Resultado

- Data: 2025-12-25
- coords_provided: 0% (0/2 tool calls)
- visual_only: 0% (0/2 tool calls)
- **Problema**: OOM com configuracao padrao, precisa de max-num-seqs=16
- **Problema**: Modelo entende tarefa e coordenadas mas gera TEXTO, nao tool call
- **Resposta tipica**: `"To click on the \"Allow\" button using android_click tool... android_click 540 1054"`
- **Conclusao**: Modelo EXCLUIDO - nao suporta function calling estruturado

---

### 4. AutoGLM-Phone-9B

**HuggingFace**: `zai-org/AutoGLM-Phone-9B-Multilingual`
**Status**: INCOMPATIVEL - bitsandbytes nao funciona

#### Teste Manual

```bash
MODEL_PATH=zai-org/AutoGLM-Phone-9B-Multilingual \
TOOL_CALL_PARSER=pythonic \
QUANTIZATION=bitsandbytes \
docker compose -f docker-compose.vllm.yml up
```

#### Resultado

- Data: 2025-12-25
- coords_provided: N/A
- visual_only: N/A
- **Erro**: `AssertionError: param_data.shape == loaded_weight.shape` em `linear.py:781`
- **Nota**: Arquitetura Glm4vForConditionalGeneration tem incompatibilidade com bitsandbytes
- **Nota**: Modelo 9B nao cabe em 16GB VRAM sem quantizacao
- **Conclusao**: Modelo EXCLUIDO - incompativel com bitsandbytes no vLLM

---

### 5. Qwen3-VL-4B-Thinking

**HuggingFace**: `Qwen/Qwen3-VL-4B-Thinking`
**Status**: NAO ADEQUADO - gera lixo multilingual

#### Teste Manual

```bash
MODEL_PATH=Qwen/Qwen3-VL-4B-Thinking \
TOOL_CALL_PARSER=qwen25 \
docker compose -f docker-compose.yml up
```

#### Resultado

- Data: 2025-12-25
- coords_provided: 0% (0/2 tool calls)
- visual_only: 0% (0/2 tool calls)
- Latencia: ~28s (muito lento)
- **Problema**: Modelo gera texto corrupto multilingual (japones, arabe, russo misturados)
- **Resposta tipica**: `"ありました越來'\"... relentسري thieves(Matรวม apologies..."`
- **Nota**: Modelos "Thinking" sao projetados para raciocinio longo, nao tool calls
- **Conclusao**: Modelo EXCLUIDO - nao adequado para tool calls

---

### 6. gemma-3-4b-it

**HuggingFace**: `google/gemma-3-4b-it`
**Status**: FUNCIONA - grounding visual ruim

#### Teste Manual

```bash
MODEL_PATH=google/gemma-3-4b-it \
TOOL_CALL_PARSER=pythonic \
docker compose -f docker-compose.yml up
```

#### Resultado

- Data: 2025-12-25
- coords_provided: **100%** (28/28 hits, 100% tool calls)
- visual_only: **3.6%** (1/28 hits, 92.9% tool calls)
- Latencia: ~1s (rapido)
- **Formato**: Gera codigo Python em bloco \`\`\`tool_code
- **Parser**: Adicionado suporte para formato pythonico no parser
- **Nota**: Modelo segue instrucoes bem mas tem grounding visual muito ruim
- **Conclusao**: USAVEL para coords_provided, NAO RECOMENDADO para visual_only

---

### 7. Fara-7B

**HuggingFace**: `microsoft/Fara-7B`
**Status**: **FUNCIONA** - validado no benchmark

#### Teste Manual

```bash
MODEL_PATH=microsoft/Fara-7B \
TOOL_CALL_PARSER=pythonic \
QUANTIZATION=bitsandbytes \
docker compose -f docker-compose.vllm.yml up
```

#### Resultado (do benchmark inicial)

- Data: 2025-12-25
- coords_provided: **92.9%** (26/28 hits, 100% tool calls)
- visual_only: **14.3%** (4/28 hits, 100% tool calls)
- **Formato**: Usa `{"coordinate": [x, y]}` - parser ja suporta
- **Nota**: Modelo funciona bem com coordenadas fornecidas
- **Conclusao**: **USAVEL** - alternativa ao Qwen para casos onde vLLM e preferido

---

## Tool Call Parsers Disponiveis

### SGLang
- qwen, qwen25, qwen3_coder
- pythonic
- mistral, llama3

### vLLM
- qwen, qwen3_xml
- pythonic
- hermes, llama3_json, mistral

---

## Notas de Configuracao

### Conversao de Coordenadas Qwen

O Qwen3-VL retorna coordenadas em formato [0, 1000). Ver `docs/009_qwen3vl_coordinates.md`.

```python
pixel_x = int((x / 1000) * image_width)
pixel_y = int((y / 1000) * image_height)
```

### Quantizacao

Modelos >6B precisam de quantizacao 4-bit (bitsandbytes) para caber em 16GB VRAM.

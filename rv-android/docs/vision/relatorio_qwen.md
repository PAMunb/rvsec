# Relatório de Avaliação de Modelos de Visão Linguística (Vision LLM)

## Sumário Executivo

Este relatório apresenta os resultados da avaliação sistemática de modelos de linguagem multimodal para integração no RVAgent, uma ferramenta autônoma de teste de segurança Android. Após testes extensivos com 468 capturas de tela e 2.847 testes, o modelo **Qwen3-VL-4B-Instruct** foi selecionado como o melhor candidato, alcançando uma taxa de acerto de 57,7% e uma taxa de chamada de ferramentas de 90,3% no modo de localização visual pura.

## Objetivo do Projeto

Avaliar modelos de linguagem de visão para sua capacidade de identificar e interagir com elementos de interface de usuário (UI) em capturas de tela Android. O objetivo principal é habilitar o "grounding visual" - a capacidade de clicar em elementos com base em sua aparência visual em vez de depender apenas de metadados de acessibilidade.

## Metodologia de Avaliação

### Modos de Avaliação
- **visual_only**: O modelo deve localizar elementos visualmente a partir da captura de tela (modo primário)
- **coords_provided**: Coordenadas são fornecidas explicitamente no prompt (modo baseline)

### Critérios de Sucesso
- **Hit**: Clique previsto dentro de 50 pixels do centro do elemento
- **Tool Call**: O modelo produz uma chamada de ferramenta estruturada (em vez de resposta textual)

### Conjunto de Dados
- **APKs**: 28 aplicativos do F-Droid
- **Capturas de tela**: 468
- **Elementos únicos**: 812
- **Testes totais**: 2.847 (com 3 repetições)

## Infraestrutura e Hardware

### Configuração de Hardware
- **GPU**: NVIDIA GeForce RTX 5070 Ti
- **VRAM**: 16GB
- **Capacidade de computação**: 12.0 (SM120)
- **CUDA Host**: 13.0

### Servidores de Inferência Avaliados
| Servidor | Backend | Loop Bug | Taxa de Chamada de Ferramentas | Recomendação |
|----------|---------|----------|-------------------------------|-------------|
| **SGLang** | PyTorch + FlashInfer | Não | Nativa | **Primário** |
| vLLM | PyTorch + PagedAttention | Não | Nativa | Alternativa |
| Ollama | GGUF (llama.cpp) | Sim (16,7%) | Via parser | Não recomendado |

### Configuração do SGLang
Devido a um problema de compatibilidade com a RTX 5070 Ti (que reporta SM120 em vez de SM100), foi necessário usar o backend FlashInfer:
```bash
--attention-backend flashinfer
--tool-call-parser qwen
```

## Modelos Avaliados

### Modelos Funcionais
| Modelo | Tamanho | Servidor | Taxa de Acerto | Taxa de Chamada de Ferramentas | Latência |
|--------|---------|----------|----------------|-------------------------------|----------|
| **Qwen3-VL-4B-Instruct** | 4B | SGLang | **57,7%** | **90,3%** | 1.821ms |
| microsoft/Fara-7B | 7B | vLLM + 4-bit | 44,3% | 79,9% | 1.015ms |
| google/gemma-3-4b-it | 4B | SGLang | 0,9% | 76,8% | 805ms |

### Modelos Excluídos
- Qwen3-VL-4B-Thinking: Gera saída multilíngue corrompida
- Llava-OneVision-7B: Arquitetura não suportada pelo vLLM
- Molmo-7B-D-0924: Requer TensorFlow
- InternVL2-8B: Não gera chamadas de ferramentas estruturadas
- AutoGLM-Phone-9B: Incompatível com bitsandbytes

## Descobertas Técnicas Críticas

### 1. Sistema de Coordenadas do Qwen3-VL
Descoberta crítica: O Qwen3-VL retorna coordenadas normalizadas no intervalo [0, 1000), não em pixels. Esta descoberta aumentou a taxa de acerto de 3,6% para aproximadamente 50% após a implementação da conversão adequada:

```python
# Converter coordenadas normalizadas do Qwen3-VL para pixels
pixel_x = int((x / 1000) * largura_da_imagem)
pixel_y = int((y / 1000) * altura_da_imagem)
```

### 2. Bug de Loop Infinito no Ollama
O servidor baseado em GGUF (Ollama) exibe um bug de loop infinito sob condições específicas:
- **Temperatura**: < 0.3
- **num_predict**: 8192
- **Taxa de loop**: 16,7% (2/12 testes)

O bug é específico ao backend GGUF/llama.cpp e não afeta servidores baseados em PyTorch (SGLang, vLLM).

### 3. Formatos de Coordenadas Específicos por Modelo
Diferentes modelos usam formatos diferentes para saída de coordenadas:
- **Qwen3-VL**: Normalizado [0, 1000) - `{"x": 499, "y": 547}`
- **Fara-7B**: Coordenadas em pixels - `{"coordinate": [540, 1054]}`
- **Gemma**: Formato de ação - `{"action": "android_click", "x": 540, "y": 1054}`

## Resultados Detalhados

### Desempenho por Tipo de Elemento (Qwen3-VL)
| Tipo de Elemento | Taxa de Acerto | Taxa de Chamada de Ferramentas | Análise |
|------------------|----------------|-------------------------------|---------|
| EditText | **93,1%** | 100,0% | Campos de entrada de texto - alta precisão |
| Button | **78,2%** | 90,3% | Bordas claras e rótulos |
| View | 75,0% | 100,0% | Views personalizadas com conteúdo |
| Switch | 69,4% | 95,8% | Interruptores de alternância reconhecíveis |
| Spinner | 63,3% | 100,0% | Indicadores de dropdown ajudam |
| TextView | 60,2% | 94,9% | Depende do contexto circundante |
| ImageButton | 43,5% | 83,6% | Ícones sem texto são mais difíceis |
| CheckedTextView | 29,2% | 97,7% | Estado de seleção confunde o modelo |
| CheckBox | 25,0% | 100,0% | Pequena pegada visual |
| ImageView | 0,0% | 56,2% | Imagens puras raramente clicadas corretamente |
| RadioButton | 0,0% | 100,0% | O modelo falha em identificar |

### Comparação entre Qwen3-VL e Fara-7B
| Métrica | Qwen3-VL | Fara-7B | Vencedor |
|---------|----------|---------|----------|
| Taxa de Acerto | **57,7%** | 44,3% | Qwen3-VL (+13,4%) |
| Taxa de Chamada de Ferramentas | **90,3%** | 79,9% | Qwen3-VL (+10,4%) |
| Distância Média | 6,2px | **4,1px** | Fara-7B |
| Latência Média | 1.821ms | **1.015ms** | Fara-7B (44% mais rápido) |
| PARSE_ERROR | **1,8%** | 19,5% | Qwen3-VL |

## Recomendações para Integração no RVAgent

### Configuração Recomendada
```python
config = {
    "model": "Qwen/Qwen3-VL-4B-Instruct",
    "server": "SGLang",
    "server_url": "http://localhost:30000",
    "temperature": 0.01,
    "top_p": 0.6,
    "top_k": 50,
    "uses_normalized_coords": True,
}
```

### Estratégia Híbrida
1. Tentar grounding visual primeiro para todos os elementos
2. Se NO_TOOL ou MISS, recorrer à abordagem baseada em coordenadas usando dados do UIAutomator
3. Para elementos ImageView, RadioButton e CheckBox, considerar fornecer coordenadas explícitas diretamente

### Expectativas de Desempenho
| Métrica | Valor Esperado |
|---------|----------------|
| Taxa de Acerto (visual_only) | ~58% |
| Taxa de Chamada de Ferramentas | ~90% |
| Latência por inferência | ~1,8 segundos |
| Produtividade | ~33 inferências/minuto |

## Desenvolvimentos Técnicos

### Arquitetura do Framework de Avaliação
O framework foi construído usando LangChain e LangGraph para alinhar com a arquitetura do RVAgent:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   prepare   │────>│  inference  │────>│   extract   │────>│  validate   │
│  inference  │     │   (async)   │     │ coordinates │     │   result    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Componentes Principais
- `EvaluationConfig`: Modelo de configuração Pydantic
- `VisionLLMClient`: Wrapper LangChain para modelos de visão
- `EvaluatorState`: Estado de workflow TypedDict
- `tool_call_parser`: Parser de resposta de múltiplos formatos

### Melhorias no Parser
O sistema implementa seis estratégias de parsing para lidar com diferentes formatos de saída dos modelos:
1. **Array JSON**: `[{"name": "tool", "parameters": {...}}]`
2. **Objeto JSON**: `{"name": "tool", "parameters": {...}}`
3. **Tags XML**: `
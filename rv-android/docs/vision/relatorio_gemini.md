
# Relatório Técnico Final: Avaliação de Vision LLMs para Automação de UI Android

**Projeto**: RVSec Vision LLM Evaluator
**Período**: 22 de Dezembro de 2025 - 06 de Janeiro de 2026
**Hardware**: NVIDIA RTX 5070 Ti (16GB VRAM)

---

## 1. Introdução e Objetivos

Este relatório consolida os resultados da avaliação sistemática de modelos de linguagem de visão (Vision LLMs) para integração ao RVAgent, uma ferramenta de teste autônomo de segurança para Android. O objetivo principal foi selecionar o modelo e a infraestrutura de inferência ideais para tarefas de *visual grounding*, ou seja, a capacidade de identificar e interagir com elementos de UI (menus, botões, campos de texto) a partir de capturas de tela, sem depender exclusivamente de metadados de acessibilidade.

A avaliação focou em três métricas principais:
- **Hit Rate**: A precisão com que o modelo clica no elemento correto.
- **Tool Call Rate**: A frequência com que o modelo gera uma chamada de ferramenta estruturada em vez de uma resposta textual.
- **Latência**: O tempo de resposta para cada inferência.

---

## 2. Infraestrutura e Metodologia

### 2.1. Arquitetura de Avaliação

A avaliação foi conduzida utilizando uma arquitetura baseada em **LangChain e LangGraph**, espelhando a implementação do RVAgent para garantir a relevância dos resultados. O fluxo de trabalho processa cada elemento da seguinte forma:

`preparar_inferencia` -> `executar_inferencia` -> `extrair_coordenadas` -> `validar_resultado`

- **Dataset**: Foram utilizadas **468 capturas de tela** de **28 aplicações Android** do repositório F-Droid, totalizando **812 elementos únicos** e **2.847 testes** (com 3 repetições por elemento).
- **Modo de Avaliação**: O foco principal foi o modo `visual_only`, onde o modelo precisa localizar o elemento na tela sem receber suas coordenadas no prompt, testando sua real capacidade de grounding visual.

### 2.2. Comparação de Servidores de Inferência

Três servidores de inferência foram avaliados para hospedar os modelos:

| Servidor | Backend | Bug de Loop Infinito | Recomendação |
|----------|---------|----------------------|----------------|
| **SGLang** | PyTorch + FlashInfer | Não (0%) | **Primário** |
| **vLLM** | PyTorch + PagedAttention | Não (0%) | Alternativa |
| **Ollama** | GGUF (llama.cpp) | **Sim (16.7%)** | Não recomendado |

O **Ollama foi descartado** devido a um bug crítico de loop infinito, onde o modelo entra em um ciclo de repetição de tokens com temperatura baixa (< 0.3). Este comportamento, causado por uma falha no sampler do backend GGUF, torna-o inadequado para produção. **SGLang foi escolhido como o servidor primário** por sua estabilidade, performance e suporte nativo a tool calling.

---

## 3. Descobertas Técnicas Principais

### 3.1. O Sistema de Coordenadas Normalizadas do Qwen3-VL

Uma descoberta crucial foi que o **Qwen3-VL não opera com coordenadas de pixels**, mas sim com um sistema de coordenadas normalizadas no intervalo **[0, 1000)**.

- **Problema**: O modelo retornava coordenadas como `(499, 547)` para um alvo em `(540, 1054)`, resultando em uma taxa de acerto inicial de apenas 3.6%.
- **Solução**: Implementar uma função de desnormalização baseada nas dimensões da imagem.
  ```python
  pixel_x = int((qwen_x / 1000) * largura_imagem)
  pixel_y = int((qwen_y / 1000) * altura_imagem)
  ```
- **Impacto**: Após a correção, a taxa de acerto do Qwen3-VL no modo `visual_only` saltou de **3.6% para mais de 50%**.

### 3.2. A Necessidade de um Parser Robusto

Os modelos de visão demonstraram grande inconsistência no formato de saída das chamadas de ferramenta. Para contornar isso, foi desenvolvido um parser de fallback com múltiplas estratégias:

1.  **Tenta o parser nativo** do LangChain.
2.  Se falhar, **procura por tags XML** `<tool_call>`.
3.  Se falhar, **procura por blocos de código JSON ou Python**.
4.  Aplica **correções com expressões regulares** para consertar JSON malformado (ex: `"x": [a, b]` -> `"x": a, "y": b`).

Essa abordagem se mostrou vital, especialmente para o Qwen3-VL, onde o parser de fallback (XML) obteve uma taxa de acerto **superior à nativa (69.5% vs 60.2%)**.

### 3.3. Engenharia de Prompt

A clareza do prompt demonstrou ser mais impactante do que o ajuste fino de parâmetros como temperatura.

- **Prompt V1 (Genérico)**: "Você é um assistente de automação de UI..." -> Baixa taxa de tool call.
- **Prompt V2 (Diretivo)**: "Você é um agente de automação. Você DEVE usar ferramentas. NUNCA responda com texto. Forneça coordenadas de PIXEL EXATAS." -> Aumentou a taxa de tool call de ~70% para perto de 100%.

---

## 4. Resultados do Benchmark Final (468 Screenshots)

Dois modelos finalistas foram submetidos a um benchmark completo.

| Métrica | Qwen3-VL-4B (SGLang, bf16) | Fara-7B (vLLM, 4-bit) | Vencedor |
|------------------|------------------------------|-------------------------|--------------------|
| **Hit Rate** | **57.7%** | 44.3% | **Qwen3-VL (+13.4%)** |
| **Tool Call Rate** | **90.3%** | 79.9% | **Qwen3-VL (+10.4%)** |
| **Latência Média** | 1,821ms | **1,015ms** | **Fara-7B (44% mais rápido)** |
| **Avg. Distância** | 6.2px | **4.1px** | **Fara-7B** |
| **Consistência** | **98.9%** | N/A | **Qwen3-VL** |

### Análise de Falhas (Categorias de Resultado)

| Categoria | Qwen3-VL | Fara-7B | Análise |
|-------------|----------|---------|-------------------------------------------------|
| **HIT** | 57.7% | 44.3% | Qwen3-VL é mais preciso. |
| **MISS** | 30.8% | 35.7% | Ambos erram, mas Fara-7B erra mais. |
| **NO_TOOL** | 9.7% | 20.1% | Fara-7B tem o dobro de chance de não chamar a ferramenta. |
| **PARSE_ERROR** | 1.8% | 19.5% | O formato de saída do Fara-7B é muito mais inconsistente. |

### Performance por Tipo de Elemento

- **Qwen3-VL se destaca em**:
  - `EditText`: **93.1%** vs 12.4% do Fara-7B.
  - `Button`: **78.2%** vs 66.2%.
  - `TextView`: **60.2%** vs 33.9%.

- **Fara-7B se destaca em**:
  - `CheckedTextView`: **71.6%** vs 29.2% do Qwen3-VL.
  - `RadioButton`: **61.5%** vs 0%.
  - `CheckBox`: **54.6%** vs 25.0%.

Isso sugere que o Fara-7B foi treinado com mais exemplos de controles de seleção, enquanto o Qwen3-VL é superior em elementos textuais.

---

## 5. Conclusões e Recomendação Final

### Veredito

**O modelo Qwen3-VL-4B-Instruct, servido via SGLang, é a escolha recomendada para integração ao RVAgent.**

### Justificativa

Apesar de o Fara-7B ser 44% mais rápido, sua menor precisão e, principalmente, sua baixa confiabilidade na geração de tool calls (20.1% de `NO_TOOL` e 19.5% de `PARSE_ERROR`) o tornam uma opção arriscada para um agente autônomo, onde uma única falha pode comprometer toda uma sequência de testes.

O **Qwen3-VL oferece um equilíbrio superior entre precisão (57.7% de acerto) e confiabilidade (90.3% de tool call)**, que são as métricas mais críticas para a tarefa.

### Estratégia de Integração no RVAgent

1.  **Modelo Primário**: Utilizar o Qwen3-VL-4B-Instruct com SGLang.
2.  **Estratégia Híbrida**:
    - Tentar o `visual_only` como primeira abordagem.
    - Em caso de falha (`MISS` ou `NO_TOOL`), recorrer a uma segunda tentativa no modo `coords_provided`, utilizando as coordenadas extraídas do UIAutomator.
    - Para elementos onde o Qwen3-VL demonstrou performance zero (`ImageView`, `RadioButton`), considerar o uso direto do modo `coords_provided`.
3.  **Configuração**:
    - `temperature: 0.01`, `top_p: 0.6`, `top_k: 50`.
    - Ativar a desnormalização de coordenadas.

Com esta abordagem, espera-se que o RVAgent atinja uma taxa de sucesso de interação com a UI de aproximadamente **58% na primeira tentativa visual**, com um fallback robusto para garantir a continuidade da execução.

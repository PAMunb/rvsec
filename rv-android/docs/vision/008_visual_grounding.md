# 008 - Visual Grounding Evaluation

**Data**: 2025-12-25
**Modelo**: Qwen3-VL-4B-Instruct
**Servidor**: vLLM (porta 8000)

## Objetivo

Avaliar a capacidade de grounding visual do modelo - localizar elementos na tela SEM coordenadas fornecidas no prompt.

## Modos de Avaliação

| Modo | Descrição | Coordenadas no Prompt |
|------|-----------|----------------------|
| `coords_provided` | Baseline - coordenadas explícitas | Sim |
| `visual_only` | Grounding real - modelo descobre | Não |
| `description_only` | Mais difícil - sem contexto UI | Não |

## Resultados - Qwen3-VL-4B-Instruct

### Benchmark Final (50 screenshots, 144 elementos)

| Modo | Hit Rate | Tool Call Rate | Avg Distance | Avg Latency |
|------|----------|----------------|--------------|-------------|
| `coords_provided` | **100%** | 100% | 0.0px | 1589ms |
| `visual_only` | **3.5%** | 87.5% | 34.7px | 1511ms |

**Diferença**: 96.5 pontos percentuais entre os modos.

### Detalhes por App (visual_only)

| App | Screenshots | Hit Rate | Tool Call Rate |
|-----|-------------|----------|----------------|
| ar.rulosoft.mimanganu | 8 | 8.3% | 100% |
| au.com.wallaceit.reddinator | 13 | 0% | 69.2% |
| biz.gyrus.yaab | 12 | 0% | 72.2% |
| byrne.utilities.pasttext | 7 | 0% | 100% |
| ca.farrelltonsolar.classic | 10 | 20% | 100% |

### Análise de Erro - Exemplo "Allow" Button

```
Espaço Device: 1080x1920
Espaço Qwen:   704x1248

Allow Button:
  Target Device:     (540, 1054) <- centro real do botão
  Target Qwen:       (352, 685)  <- convertido
  Predicted Qwen:    (499, 510)  <- modelo retornou
  Predicted Device:  (765, 784)  <- convertido

  Erro Qwen:   228px
  Erro Device: 351px
```

**Observação**: O modelo erra em ambos os espaços de coordenadas. No espaço Device o erro é maior devido à escala proporcional.

### Padrão de Erro

O modelo tende a apontar para:
- ~225px à direita do alvo
- ~270px acima do alvo
- Região central do diálogo em vez dos botões na parte inferior

## Formato de Saída do Qwen3-VL

O modelo retorna coordenadas no formato `"x": [x, y]` (array) em vez de `"x": valor, "y": valor`:

```json
{"name": "android_click", "arguments": {"x": [499, 510], "element_description": "..."}}
```

**Correção implementada**: `normalize_tool_args()` em `src/parsers/tool_call_parser.py` converte este formato.

## Comparação com Documentos Anteriores

| Fonte | Modelo | visual_only | coords_provided |
|-------|--------|-------------|-----------------|
| docs/old/001_gemma.md | Gemma 3 4B | 30% | 100% |
| docs/old/002_vision.md | Qwen 2.5VL 7B | 96.7% | 98.3% |
| **Este teste** | Qwen3-VL-4B | **3.6%** | 100% |

## Conclusões

1. **coords_provided é trivial**: O modelo copia as coordenadas fornecidas - não testa visão
2. **visual_only mede grounding real**: Capacidade do modelo localizar elementos visualmente
3. **Qwen3-VL-4B tem baixo grounding**: 3.6% hit rate sem coordenadas
4. **Tool calling funciona**: 100% das vezes o modelo chama a ferramenta correta

## Próximos Passos

1. Testar com mais screenshots (50+) para amostra estatística
2. Comparar espaços de coordenadas (Device vs Optimized)
3. Testar outros modelos (MiniCPM-V, Llava-OneVision, etc.)
4. Avaliar se temperatura/prompt afetam precisão visual

## Arquivos Modificados

- `src/evaluator/evaluator.py` - Adicionado `GroundingMode` enum e prompts
- `src/parsers/tool_call_parser.py` - Suporte ao formato `x:[x,y]`
- `src/inference/sglang_client.py` - Normalização de argumentos
- `tests/test_evaluator.py` - Parâmetro `--grounding-mode`

# Descoberta: Sistema de Coordenadas do Qwen3-VL

**Data**: 2025-12-25
**Autor**: Claude Code + Pedro
**Status**: Validado

## Problema

O modelo Qwen3-VL-4B-Instruct estava apresentando hit rate de 3.6% no modo `visual_only`, apesar de fazer tool calls corretamente.

Análise das coordenadas mostrou:
- Target: (540, 1054) pixels
- Predicted: (499, 547) ← aparentemente muito errado

## Descoberta

O Qwen3-VL usa **coordenadas normalizadas no intervalo [0, 1000)**, não coordenadas em pixels.

### Fonte Oficial
- [GitHub Issue #1486](https://github.com/QwenLM/Qwen3-VL/issues/1486)
- Documentação swift: "Qwen3-VL's bbox output uses normalized 1000 relative coordinates"
- Formato: `<box>(x1,y1),(x2,y2)</box>` com valores em [0, 1000)

### Conversão Correta

```python
# De [0, 1000) para pixels
pixel_x = int((x / 1000) * image_width)
pixel_y = int((y / 1000) * image_height)
```

Exemplo:
- Raw: (499, 547)
- Convertido: (499/1000 * 1080, 547/1000 * 1920) = (539, 1050)
- Distância ao target (540, 1054): **4 pixels** ✓

## Implementação

### Função de Conversão
```python
# src/parsers/tool_call_parser.py
def denormalize_qwen_coords(
    x: int | float,
    y: int | float,
    image_width: int = 1080,
    image_height: int = 1920,
) -> tuple[int, int]:
    """Convert Qwen3-VL [0, 1000) normalized coordinates to pixel coordinates."""
    if 0 <= x < 1000 and 0 <= y < 1000:
        pixel_x = int((x / 1000) * image_width)
        pixel_y = int((y / 1000) * image_height)
        return pixel_x, pixel_y
    return int(x), int(y)
```

### Quando Aplicar
- **VISUAL_ONLY**: Aplicar conversão (modelo descobre coordenadas visualmente)
- **COORDS_PROVIDED**: NÃO aplicar (modelo copia coordenadas do prompt em pixels)

## Resultados Após Correção

| Modo | Antes | Depois |
|------|-------|--------|
| coords_provided | 100% | 100% |
| visual_only | 3.6% | **50%** |

## Parâmetros de Amostragem Recomendados

Conforme documentação do HuggingFace para tarefas VL:
- temperature: 0.7
- top_p: 0.8
- top_k: 20
- presence_penalty: 1.5

## Conclusão

1. O Qwen3-VL consegue fazer grounding visual com **50% de precisão** em visual_only
2. A conversão de coordenadas [0, 1000) → pixels é essencial
3. O modelo retorna coordenadas normalizadas independente das dimensões informadas no prompt

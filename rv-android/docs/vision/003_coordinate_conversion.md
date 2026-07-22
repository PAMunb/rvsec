# Conversão de Coordenadas para Qwen3-VL

Data: 2025-12-23

## O Problema

O Qwen3-VL processa imagens em uma resolução "otimizada" que deve ser múltipla de 32. Quando o modelo retorna coordenadas de clique, elas estão neste espaço otimizado, não nas coordenadas nativas do dispositivo.

### Espaços de Coordenadas

| Espaço | Dimensões | Usado em |
|--------|-----------|----------|
| **Device** | 1080×1920 | UIAutomator bounds, execução real |
| **Otimizado (Qwen3-VL)** | 704×1248 | Processamento do modelo, prompts, respostas |

### Dimensões Otimizadas

```python
# Múltiplos de 32 (requisito do Qwen3-VL)
QWEN3_VL_WIDTH = 704   # 22 × 32
QWEN3_VL_HEIGHT = 1248 # 39 × 32
```

Fonte: `rv-agent/src/rv_agent/constants.py`

### Fatores de Escala

```python
# Device (1080×1920) → Otimizado (704×1248)
scale_to_opt_x = 704 / 1080 = 0.652
scale_to_opt_y = 1248 / 1920 = 0.650

# Otimizado → Device
scale_to_dev_x = 1080 / 704 = 1.534
scale_to_dev_y = 1920 / 1248 = 1.538
```

## Sintoma do Problema

Sem conversão de coordenadas:
- Target (device): (673, 1061)
- Predicted (otimizado): (673, 552)
- Erro aparente: **509px**

O modelo retornou Y=552 no espaço otimizado, mas estávamos comparando com Y=1061 do device.

## Solução Implementada

### 1. Módulo de Coordenadas (`src/utils/coordinates.py`)

```python
from src.utils.coordinates import CoordinateConverter

converter = CoordinateConverter(
    device_dims=(1080, 1920),
    optimized_dims=(704, 1248),
)

# Para prompts: device → otimizado
opt_x, opt_y = converter.device_to_optimized(540, 960)
# Resultado: (352, 624)

# Para execução: otimizado → device
dev_x, dev_y = converter.optimized_to_device(352, 624)
# Resultado: (540, 960)
```

### 2. Parser UIAutomator Atualizado

O parser agora aceita um converter opcional:

```python
parser.generate_ui_description(
    include_coords=True,
    converter=converter,  # Coordenadas no espaço otimizado
)
```

Saída do prompt:
```
Available UI elements:
  1. Button 'OK' at position (352, 624)  # Coordenadas otimizadas
  2. CheckBox 'Remember' at position (130, 520)
```

### 3. System Prompt com Dimensões

O system prompt agora informa as dimensões corretas:

```
The screen image has dimensions 704x1248 pixels. All coordinates are relative to this image.

When asked to click on an element, you MUST use the android_click tool with:
- x: The X coordinate (horizontal position from left edge, 0 to 704)
- y: The Y coordinate (vertical position from top edge, 0 to 1248)
```

### 4. Validação no Espaço Correto

A validação agora compara coordenadas no mesmo espaço:
- Target convertido para otimizado
- Predicted já está em otimizado (resposta do modelo)
- Distância calculada no espaço otimizado

## Resultados

### Antes (sem conversão)
- Erro médio: ~250-500px
- Hits falsos (acertava elemento errado)

### Depois (com conversão)
- Hits perfeitos: **0.0px** de distância
- Validação precisa

## Fluxo Completo

```
┌─────────────────────────────────────────────────────────────────┐
│ UIAutomator XML                                                  │
│ bounds="[324,978][702,1144]" (device space)                     │
└─────────────────────┬───────────────────────────────────────────┘
                      │ converter.device_to_optimized()
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ Prompt para LLM                                                  │
│ "Button 'OK' at position (335, 690)" (optimized space)          │
└─────────────────────┬───────────────────────────────────────────┘
                      │ LLM inference
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ Resposta do LLM                                                  │
│ android_click(x=335, y=690) (optimized space)                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │ Validação (mesmo espaço)
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ Métrica                                                          │
│ distance = 0.0px ✓                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Configuração no Evaluator

```python
config = EvaluationConfig(
    device_width=1080,
    device_height=1920,
    use_optimized_coords=True,  # Habilita conversão
)
```

## Arquivos Modificados

- `src/utils/coordinates.py` - Conversor de coordenadas
- `src/parsers/uiautomator_parser.py` - Suporte a converter
- `src/evaluator/evaluator.py` - Integração com conversão

## Referências

- `rv-agent/src/rv_agent/core/coordinate_converter.py` - Implementação original
- `rv-agent/COORDINATE_CONVERSION_SUMMARY.md` - Documentação original
- `rv-agent/src/rv_agent/constants.py` - Constantes validadas

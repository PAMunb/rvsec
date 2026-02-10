# 019 - Fara-7B Full Benchmark Results and Model Comparison

**Date**: 2025-12-27
**Status**: COMPLETE
**Objective**: Compare Fara-7B vs Qwen3-VL for RVAgent integration

---

## Executive Summary

| Metric | Qwen3-VL | Fara-7B | Winner |
|--------|----------|---------|--------|
| **Hit Rate** | 57.7% | 44.3% | **Qwen3-VL (+13.4%)** |
| **Tool Call Rate** | 90.3% | 79.9% | **Qwen3-VL (+10.4%)** |
| **Avg Distance** | 6.2px | 4.1px | **Fara-7B** |
| **Avg Latency** | 1,821ms | 1,015ms | **Fara-7B (44% faster)** |
| **Consistency** | 98.9% | - | - |

**Recommendation**: Use **Qwen3-VL** for RVAgent - higher accuracy is more important than speed for autonomous testing.

---

## Fara-7B Configuration

```python
model = "microsoft/Fara-7B"
server = "vLLM"
quantization = "bitsandbytes"  # 4-bit on-the-fly
server_url = "http://localhost:8000"
temperature = 0.01
top_p = 0.6
top_k = 50
grounding_mode = "visual_only"
hit_tolerance_px = 50
repetitions = 3
uses_normalized_coords = False  # Pixel coordinates directly
```

---

## Result Categories Comparison

| Category | Qwen3-VL | Fara-7B |
|----------|----------|---------|
| **HIT** | 57.7% | 44.3% |
| **MISS** | 30.8% | 35.7% |
| **NO_TOOL** | 9.7% | 20.1% |
| **PARSE_ERROR** | 1.8% | 0.0% |

### Analysis

- **Fara-7B has 2x higher NO_TOOL rate** (20.1% vs 9.7%)
- Fara-7B responses often return text explanations instead of tool calls
- The pythonic parser may not be optimal for Fara-7B's output format

---

## Element Type Performance Comparison

| Element Type | Qwen3-VL | Fara-7B | Better Model |
|--------------|----------|---------|--------------|
| **EditText** | **93.1%** | 12.4% | Qwen (+80.7%) |
| **Button** | **78.2%** | 66.2% | Qwen (+12.0%) |
| **ImageButton** | **43.5%** | 34.0% | Qwen (+9.5%) |
| **TextView** | **60.2%** | 33.9% | Qwen (+26.3%) |
| **Spinner** | **63.3%** | 29.3% | Qwen (+34.0%) |
| **CheckedTextView** | 29.2% | **71.6%** | Fara (+42.4%) |
| **RadioButton** | 0.0% | **61.5%** | Fara (+61.5%) |
| **CheckBox** | 25.0% | **54.6%** | Fara (+29.6%) |
| **Switch** | **69.4%** | 61.1% | Qwen (+8.3%) |
| **ImageView** | 0.0% | 1.4% | ~Tie |
| **View** | **75.0%** | 25.0% | Qwen (+50.0%) |

### Key Findings

**Qwen3-VL excels at**:
- **EditText**: 93.1% vs 12.4% - Qwen is dramatically better at text input fields
- **Button, TextView, Spinner**: 20-35% better across common elements

**Fara-7B excels at**:
- **CheckedTextView**: 71.6% vs 29.2% - better at list items with checkmarks
- **RadioButton**: 61.5% vs 0% - Qwen completely fails, Fara handles well
- **CheckBox**: 54.6% vs 25.0% - better at selection controls

### Hypothesis

Fara-7B may have been trained on more UI patterns involving selection controls (checkboxes, radio buttons), while Qwen3-VL was trained more on text-centric interactions.

---

## Latency Comparison

| Metric | Qwen3-VL (SGLang) | Fara-7B (vLLM) |
|--------|-------------------|----------------|
| Avg Latency | 1,821ms | **1,015ms** |
| Min Latency | ~1,590ms | ~485ms |
| Max Latency | ~2,606ms | ~21,666ms* |

*Outlier: Some Fara-7B responses took very long (21s), likely due to long text generation

**Fara-7B is 44% faster on average**, but with higher variance.

---

## Token Usage

| Metric | Qwen3-VL | Fara-7B |
|--------|----------|---------|
| Avg Prompt Tokens | 2,493 | TBD |
| Avg Completion Tokens | 97 | TBD |
| Total Tokens | 7,374,089 | TBD |

---

## Parser Strategy Analysis

**Qwen3-VL**:
- native: 54.8% (60.2% hit rate)
- xml: 35.5% (69.5% hit rate)
- none: 9.7%

**Fara-7B**:
- Primarily returns text responses instead of tool calls
- pythonic parser may not match output format well
- Higher NO_TOOL rate indicates format issues

---

## Recommendations for RVAgent

### Primary Model: Qwen3-VL-4B-Instruct (SGLang)

| Reason | Details |
|--------|---------|
| Higher accuracy | 57.7% vs 44.3% overall hit rate |
| Better tool calling | 90.3% vs 79.9% tool call rate |
| Excellent on common elements | EditText, Button, TextView |
| Consistent | 98.9% consistency across repetitions |

### Hybrid Strategy

Consider a **hybrid approach** for optimal coverage:

```python
def click_element(element_type, element):
    if element_type in ["CheckedTextView", "RadioButton", "CheckBox"]:
        # Fara-7B performs better on selection controls
        return fara_7b.click(element)
    else:
        # Qwen3-VL for everything else
        return qwen3vl.click(element)
```

However, the complexity of running two models may not justify the marginal improvement.

### Fallback Strategy

For elements where visual grounding fails consistently:
1. Try visual grounding first (Qwen3-VL)
2. If NO_TOOL or MISS, provide explicit coordinates from UIAutomator

---

## Files Generated

| File | Description |
|------|-------------|
| `results/eval_20251227_205122.json` | Qwen3-VL full benchmark |
| `results/eval_20251227_223843.json` | Fara-7B full benchmark |
| `docs/017_full_benchmark_results.md` | Qwen3-VL detailed analysis |
| `docs/018_benchmark_methodology.md` | Methodology documentation |
| `docs/019_fara7b_results_comparison.md` | This comparison document |

---

## Final Verdict

### For RVAgent Integration

| Decision | Model | Reason |
|----------|-------|--------|
| **PRIMARY** | Qwen3-VL-4B-Instruct | Best overall accuracy, reliable tool calling |
| **BACKUP** | None needed | Single model sufficient |
| **NOT RECOMMENDED** | Fara-7B | Lower accuracy, higher NO_TOOL rate |

### Hardware Requirements

| Model | Server | VRAM | Quantization |
|-------|--------|------|--------------|
| Qwen3-VL-4B | SGLang | ~8GB | bf16 (no quant) |
| Fara-7B | vLLM | ~6GB | bitsandbytes 4-bit |

### Performance Expectations

With Qwen3-VL in `visual_only` mode:
- **~58% of clicks will be accurate** (within 50px)
- **~90% of requests will produce tool calls**
- **~1.8s per inference** on RTX 5070 Ti
- **~33 inferences per minute**

For higher accuracy, consider:
- `coords_provided` mode: ~100% accuracy (but defeats visual grounding purpose)
- Hybrid approach: visual first, coordinate fallback

---

## Benchmark Commands Summary

```bash
# Qwen3-VL (SGLang)
docker compose up -d
poetry run python tests/test_evaluator.py \
    --model Qwen/Qwen3-VL-4B-Instruct \
    --url http://localhost:30000 \
    --max-screenshots 468 \
    --repetitions 3

# Fara-7B (vLLM)
MODEL_PATH=microsoft/Fara-7B QUANTIZATION=bitsandbytes TOOL_CALL_PARSER=pythonic \
docker compose -f docker-compose.vllm.yml up -d
poetry run python tests/test_evaluator.py \
    --model microsoft/Fara-7B \
    --url http://localhost:8000 \
    --max-screenshots 468 \
    --repetitions 3
```

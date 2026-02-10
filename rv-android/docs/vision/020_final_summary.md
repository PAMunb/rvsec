# 020 - Final Benchmark Summary

**Date**: 2025-12-27
**Status**: COMPLETE
**Objective**: Summarize all benchmark findings and provide final recommendations

---

## Project Goal

Evaluate Vision LLM models for the RVAgent autonomous Android testing tool. Find the best model for:
- UI element identification from screenshots
- Tool calling (android_click, android_input, etc.)
- Production deployment on RTX 5070 Ti (16GB VRAM)

---

## Models Evaluated

### Full Benchmark (468 Screenshots, 2,847 Tests)

| Model | Server | Quant | Hit Rate | Tool Call | Latency | Status |
|-------|--------|-------|----------|-----------|---------|--------|
| **Qwen3-VL-4B** | SGLang | bf16 | **57.7%** | **90.3%** | 1,821ms | **RECOMMENDED** |
| Fara-7B | vLLM | 4-bit | 44.3% | 79.9% | 1,015ms | Faster alternative |
| gemma-3-4b-it | SGLang | bf16 | 0.9% | 76.8% | 805ms | Not suitable |

### Models Excluded (Failed Validation)

| Model | Reason |
|-------|--------|
| Qwen3-VL-4B-Thinking | Generates multilingual garbage |
| Llava-OneVision-7B | Architecture not supported |
| Molmo-7B-D-0924 | Requires tensorflow |
| InternVL2-8B | No structured tool calls |
| AutoGLM-Phone-9B | Incompatible with bitsandbytes |
| MiniCPM-V-4.5 | Does not respond to standard prompts |

---

## Key Findings

### 1. Qwen3-VL vs Fara-7B Trade-offs

| Aspect | Qwen3-VL | Fara-7B | Winner |
|--------|----------|---------|--------|
| **Accuracy** | 57.7% | 44.3% | Qwen (+13.4%) |
| **Tool Call Rate** | 90.3% | 79.9% | Qwen (+10.4%) |
| **Speed** | 1,821ms | 1,015ms | Fara (44% faster) |
| **Consistency** | 98.9% | - | Qwen |
| **VRAM Usage** | ~8GB | ~6GB | Fara |

### 2. Element Type Performance

**Qwen3-VL excels at**:
- EditText: 93.1% (vs Fara 12.4%)
- Button: 78.2% (vs Fara 66.2%)
- TextView: 60.2% (vs Fara 33.9%)

**Fara-7B excels at**:
- CheckedTextView: 71.6% (vs Qwen 29.2%)
- RadioButton: 61.5% (vs Qwen 0%)
- CheckBox: 54.6% (vs Qwen 25.0%)

### 3. Coordinate Handling

| Model | Format | Conversion |
|-------|--------|------------|
| Qwen3-VL | Normalized [0, 1000) | `pixel = (coord/1000) * dimension` |
| Fara-7B | Pixel coordinates | None needed |

### 4. Parser Strategy Distribution (Qwen3-VL)

| Strategy | Usage | Hit Rate |
|----------|-------|----------|
| native | 54.8% | 60.2% |
| xml (fallback) | 35.5% | **69.5%** |
| none | 9.7% | 0% |

The XML fallback parser actually achieves higher accuracy than native tool calls.

### 5. Result Categories

| Category | Qwen3-VL | Fara-7B |
|----------|----------|---------|
| HIT | 57.7% | 44.3% |
| MISS | 30.8% | 35.7% |
| NO_TOOL | 9.7% | 20.1% |
| PARSE_ERROR | 1.8% | 0.0% |

---

## Configuration

### Optimal LLM Parameters

```python
temperature = 0.01   # Near-deterministic
top_p = 0.6          # Focused sampling
top_k = 50           # Limited vocabulary
max_tokens = 2048    # Sufficient for tool calls
```

### Evaluation Parameters

```python
grounding_mode = "visual_only"  # Real visual grounding test
hit_tolerance_px = 50           # Standard tolerance
max_elements_per_screenshot = 3 # Top visually identifiable elements
repetitions = 3                 # Statistical significance
```

---

## Infrastructure

### SGLang (Qwen3-VL)

```bash
docker compose up -d
# Port 30000, tool-call-parser: qwen
```

### vLLM (Fara-7B)

```bash
MODEL_PATH=microsoft/Fara-7B \
QUANTIZATION=bitsandbytes \
TOOL_CALL_PARSER=pythonic \
docker compose -f docker-compose.vllm.yml up -d
# Port 8000
```

---

## Recommendations

### For RVAgent Integration

1. **Primary Model**: Qwen3-VL-4B-Instruct (SGLang)
   - Higher accuracy (57.7% vs 44.3%)
   - Better tool call rate (90.3% vs 79.9%)
   - More reliable for text-based elements

2. **Fallback Strategy**:
   - Try visual grounding first
   - If NO_TOOL or MISS, provide explicit coordinates from UIAutomator

3. **Not Recommended**:
   - Fara-7B as primary (lower accuracy)
   - gemma-3-4b-it (unusable in visual_only mode)
   - Any excluded models

### Performance Expectations

With Qwen3-VL in production:
- ~58% of clicks accurate (within 50px)
- ~90% of requests produce tool calls
- ~1.8s per inference
- ~33 inferences per minute

---

## Files Reference

### Results

| File | Description |
|------|-------------|
| `results/eval_20251227_205122.json` | Qwen3-VL full benchmark |
| `results/eval_20251227_223843.json` | Fara-7B full benchmark |

### Documentation

| File | Description |
|------|-------------|
| `docs/016_full_benchmark_plan.md` | Benchmark planning |
| `docs/017_full_benchmark_results.md` | Qwen3-VL detailed analysis |
| `docs/018_benchmark_methodology.md` | Complete methodology |
| `docs/019_fara7b_results_comparison.md` | Model comparison |
| `docs/020_final_summary.md` | This document |

### Code

| File | Description |
|------|-------------|
| `src/evaluator/evaluator.py` | LangGraph-based evaluator |
| `src/llm/client.py` | VisionLLMClient |
| `src/llm/graph/nodes.py` | Workflow nodes |
| `src/llm/graph/state.py` | TypedDict state |
| `src/parsers/tool_call_parser.py` | Multi-format parser |
| `tests/test_evaluator.py` | Benchmark runner |

---

## Next Steps

1. **Integrate into RVAgent**: Deploy Qwen3-VL with SGLang
2. **Improve Fara-7B**: Investigate prompt engineering to boost hit rate
3. **Hybrid Approach**: Consider element-type-based model selection
4. **Production Optimization**: Fine-tune for specific APK categories

---

## Conclusion

**Qwen3-VL-4B-Instruct** is the recommended model for RVAgent integration:
- 13.4% higher accuracy than Fara-7B
- 10.4% higher tool call rate
- Excellent on common elements (EditText, Button)
- High consistency (98.9%)

The speed advantage of Fara-7B (44% faster) does not compensate for its lower accuracy in an autonomous testing context where correctness matters more than throughput.

# 016 - Full Benchmark Plan (468 Screenshots)

**Date**: 2025-12-27
**Status**: PLANNING
**Objective**: Rigorous full benchmark with all screenshots for final model selection

---

## Scope

| Parameter | Value |
|-----------|-------|
| Total Screenshots | 468 |
| Total APKs | 28 |
| Grounding Mode | visual_only |
| Repetitions | 1 (or 3 for statistical significance) |
| Hit Tolerance | 50px |

---

## Models to Benchmark

Based on preliminary results (docs/014_benchmark_comparison.md):

| Model | Server | Quantization | Preliminary Hit Rate | Include? |
|-------|--------|--------------|---------------------|----------|
| **Qwen3-VL-4B-Instruct** | SGLang | None (bf16) | 67.1% (150ss) | **YES - Primary** |
| **microsoft/Fara-7B** | vLLM | 4-bit bitsandbytes | 35.7% (50ss) | **YES - Comparison** |
| google/gemma-3-4b-it | SGLang | None | 0.9% (50ss) | NO - Unusable |
| Qwen3-VL (vLLM + 4-bit) | vLLM | 4-bit bitsandbytes | 23.9% (150ss) | NO - Degraded |

**Decision**: Only benchmark Qwen3-VL (SGLang) and Fara-7B (vLLM) as viable options.

---

## Configuration (Fixed for All Tests)

```python
# LLM Parameters
temperature = 0.01
top_p = 0.6
top_k = 50

# Evaluation Parameters
grounding_mode = "visual_only"
hit_tolerance_px = 50
max_elements_per_screenshot = 3  # Top 3 visually identifiable elements

# Server URLs
sglang_url = "http://localhost:30000"
vllm_url = "http://localhost:8000"
```

---

## Metrics to Capture

### Primary Metrics (Per Model)

| Metric | Description |
|--------|-------------|
| **Hit Rate** | % of clicks within 50px of element center |
| **Tool Call Rate** | % of requests producing valid tool calls |
| **Avg Distance (Hits)** | Mean euclidean distance for successful hits only |
| **Avg Latency** | Mean response time in ms |

### Result Categories (Tracked per element)

| Category | Description |
|----------|-------------|
| `HIT` | Tool called with coordinates within 50px tolerance |
| `MISS` | Tool called but coordinates >50px from target |
| `NO_TOOL` | Model returned text instead of tool call |
| `PARSE_ERROR` | Tool called but coordinates couldn't be extracted |
| `API_ERROR` | Server/inference error |

### Parser Strategies (Tracked per element)

| Strategy | Description |
|----------|-------------|
| `native` | LangChain native tool_calls (preferred) |
| `xml` | Fallback: `<tool_call>` XML tags (Qwen format) |
| `json_array` | Fallback: `[{"name": "...", ...}]` |
| `json_object` | Fallback: `{"name": "...", ...}` |
| `pythonic` | Fallback: `android_click(x=540, y=1054)` |
| `gemma` | Fallback: `{"action": "android_click", "x": ..., "y": ...}` |
| `none` | No tool call extracted |

### Token Stats (Aggregated)

| Metric | Description |
|--------|-------------|
| `avg_prompt_tokens` | Average input tokens per request |
| `avg_completion_tokens` | Average output tokens per request |
| `total_tokens` | Sum of all tokens used |

### Repetition Stats

| Metric | Description |
|--------|-------------|
| `avg_consistency` | % of repetitions that agree on hit/miss |
| `avg_distance_stddev` | Standard deviation of distance across repetitions |

### Per-Element Data (Saved in JSON)

| Field | Description |
|-------|-------------|
| `target` | Ground truth coordinates {x, y} |
| `predicted` | Predicted coordinates after denormalization {x, y} |
| `raw_coords` | Raw LLM output coordinates before denormalization {x, y} |
| `result_category` | HIT, MISS, NO_TOOL, PARSE_ERROR, API_ERROR |
| `parser_strategy` | native, xml, json_array, pythonic, gemma, none |
| `input_prompt` | Full prompt sent to LLM |
| `content` | Raw LLM response text |
| `prompt_tokens` | Input tokens for this request |
| `completion_tokens` | Output tokens for this request |
| `latency_ms` | Response time |
| `error` | Error message if any |

### Per-Element-Type Metrics

| Element Type | Expected Count | Metrics |
|--------------|----------------|---------|
| Button | ~150 | Hit rate, tool call rate |
| TextView | ~200 | Hit rate, tool call rate |
| EditText | ~50 | Hit rate, tool call rate |
| ImageButton | ~150 | Hit rate, tool call rate |
| CheckBox | ~40 | Hit rate, tool call rate |
| Spinner | ~50 | Hit rate, tool call rate |
| CheckedTextView | ~100 | Hit rate, tool call rate |
| ImageView | ~70 | Hit rate, tool call rate |
| RadioButton | ~20 | Hit rate, tool call rate |
| View | ~30 | Hit rate, tool call rate |

---

## Execution Plan

### Phase 1: Qwen3-VL SGLang (Primary)

```bash
# 1. Start SGLang server
docker compose up -d

# 2. Wait for server ready
curl http://localhost:30000/v1/models

# 3. Run full benchmark
poetry run python tests/test_evaluator.py \
    --model Qwen/Qwen3-VL-4B-Instruct \
    --url http://localhost:30000 \
    --max-screenshots 468 \
    --repetitions 1

# 4. Save results
# Results auto-saved to results/eval_YYYYMMDD_HHMMSS.json
```

**Estimated time**: ~15-20 minutes (468 × 3 elements × 1.8s/element)

### Phase 2: Fara-7B vLLM (Comparison)

```bash
# 1. Stop SGLang, start vLLM
docker compose down
MODEL_PATH=microsoft/Fara-7B TOOL_CALL_PARSER=pythonic docker compose -f docker-compose.vllm.yml up -d

# 2. Wait for server ready (longer due to quantization)
curl http://localhost:8000/v1/models

# 3. Run full benchmark
poetry run python tests/test_evaluator.py \
    --model microsoft/Fara-7B \
    --url http://localhost:8000 \
    --max-screenshots 468 \
    --repetitions 1

# 4. Save results
```

**Estimated time**: ~20-25 minutes

---

## Expected Element Count

To estimate total test count, let's count visually identifiable elements:

```python
# From preliminary analysis (150 screenshots):
# ~3.5 elements per screenshot on average (filtered by is_visually_identifiable)
#
# 468 screenshots × 3.5 elements ≈ 1,638 total tests per model
# With repetitions=3: 4,914 tests per model
```

---

## Result Files

| File | Content |
|------|---------|
| `results/eval_YYYYMMDD_qwen3vl_full.json` | Qwen3-VL 468ss results |
| `results/eval_YYYYMMDD_fara7b_full.json` | Fara-7B 468ss results |
| `docs/017_full_benchmark_results.md` | Final comparison analysis |

---

## Analysis Plan

After both benchmarks complete:

1. **Overall Comparison**: Hit rate, tool call rate, latency
2. **Per-Element Breakdown**: Which model is better for each element type
3. **Error Analysis**: Categorize failures (NO_TOOL, MISS, etc.)
4. **Statistical Significance**: Confidence intervals if repetitions > 1
5. **Recommendation**: Final model selection for RVAgent

---

## Reproducibility Checklist

- [ ] Same docker image version for both tests
- [ ] Same LLM parameters (temp, top_p, top_k)
- [ ] Same screenshot dataset (468 files)
- [ ] Same element filtering (is_visually_identifiable)
- [ ] Same coordinate conversion (Qwen: [0,1000) → pixels)
- [ ] Same hit tolerance (50px)
- [ ] Raw results saved as JSON
- [ ] Logs captured for debugging

---

## Notes

### Qwen3-VL Coordinate Format
- Returns normalized [0, 1000) coordinates
- Requires denormalization: `pixel = (coord / 1000) * dimension`
- Handled in `extract_coordinates` node

### Fara-7B Tool Call Formats
- Multiple inconsistent formats (3 variations)
- Parser handles: nested arguments, coordinate arrays, minimal format
- May have lower tool call rate due to format variations

### Gemma Exclusion
- 0.9% hit rate in visual_only mode
- Only suitable with explicit coordinates in prompt
- Not viable for autonomous agent use case

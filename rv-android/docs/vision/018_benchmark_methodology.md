# 018 - Benchmark Methodology and Execution Log

**Date**: 2025-12-27
**Status**: COMPLETE
**Objective**: Document the complete benchmark methodology, architecture, and execution steps

---

## Overview

This document describes the rigorous benchmark methodology used to evaluate Vision LLM models for the RVAgent autonomous Android testing tool.

---

## Architecture

### LangChain/LangGraph Pipeline

The evaluator uses a LangGraph-based pipeline following the RVAgent architecture pattern:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  prepare_       │────▶│  run_           │────▶│  extract_       │────▶│  validate_      │
│  inference      │     │  inference      │     │  coordinates    │     │  result         │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
       │                       │                       │                       │
       ▼                       ▼                       ▼                       ▼
  Build prompt           Call LLM with            Parse tool              Calculate
  + encode image         tool binding             calls + coords          hit/miss
```

### Key Components

| Component | File | Description |
|-----------|------|-------------|
| **State** | `src/llm/graph/state.py` | TypedDict with all tracking fields |
| **Nodes** | `src/llm/graph/nodes.py` | LangGraph workflow nodes |
| **Client** | `src/llm/client.py` | LangChain ChatOpenAI wrapper |
| **Tools** | `src/llm/tools/android_tools.py` | @tool decorated functions |
| **Evaluator** | `src/evaluator/evaluator.py` | Main evaluation orchestrator |
| **Parser** | `src/parsers/tool_call_parser.py` | Fallback tool call extraction |

---

## Metrics Captured

### Per-Element Metrics

| Field | Type | Description |
|-------|------|-------------|
| `element_class` | str | Android widget class (Button, EditText, etc.) |
| `element_text` | str | Text content of element |
| `target` | {x, y} | Ground truth coordinates from UIAutomator |
| `predicted` | {x, y} | Model predicted coordinates (denormalized) |
| `raw_coords` | {x, y} | Raw LLM output before denormalization |
| `repetition` | int | Repetition number (1-3) |
| `hit` | bool | Whether prediction was within tolerance |
| `distance` | float | Euclidean distance in pixels |
| `result_category` | str | HIT, MISS, NO_TOOL, PARSE_ERROR, API_ERROR |
| `tool_called` | bool | Whether model produced tool call |
| `tool_name` | str | Name of tool called |
| `parser_strategy` | str | native, xml, json_array, pythonic, gemma, none |
| `latency_ms` | float | Inference time in milliseconds |
| `prompt_tokens` | int | Input tokens |
| `completion_tokens` | int | Output tokens |
| `total_tokens` | int | Total tokens |
| `input_prompt` | str | Full prompt sent to LLM |
| `content` | str | Raw LLM response text |
| `finish_reason` | str | LLM finish reason |
| `error` | str | Error message if any |

### Aggregated Metrics

| Metric | Description |
|--------|-------------|
| `hit_rate` | % of predictions within 50px tolerance |
| `tool_call_rate` | % of requests producing valid tool calls |
| `avg_distance` | Mean distance for hits only |
| `avg_latency_ms` | Mean response time |
| `result_categories` | Distribution of HIT/MISS/NO_TOOL/etc. |
| `parser_strategies` | Distribution of parsing methods used |
| `token_stats` | Token usage statistics |
| `repetition_stats` | Consistency across repetitions |
| `element_type_metrics` | Per-element-type breakdown |

---

## Result Categories

| Category | Description | Cause |
|----------|-------------|-------|
| **HIT** | Coordinates within 50px of target | Success |
| **MISS** | Tool called but >50px from target | Wrong visual identification |
| **NO_TOOL** | Model returned text, no tool call | Model didn't understand task |
| **PARSE_ERROR** | Tool called but coords not extracted | Malformed JSON/format |
| **API_ERROR** | Server/inference error | Network, OOM, timeout |

---

## Parser Strategies

The system uses a multi-strategy parser to handle different model output formats:

| Strategy | Format | Example |
|----------|--------|---------|
| **native** | LangChain tool_calls | `response.tool_calls[0]` |
| **xml** | Qwen XML format | `<tool_call>{"name": "android_click", ...}</tool_call>` |
| **json_array** | JSON array | `[{"name": "android_click", "args": {...}}]` |
| **json_object** | JSON object | `{"name": "android_click", "args": {...}}` |
| **pythonic** | Python function | `android_click(x=540, y=1054)` |
| **gemma** | Gemma format | `{"action": "android_click", "x": 540, "y": 1054}` |
| **none** | No tool found | Text response only |

---

## Coordinate Handling

### Qwen3-VL Normalization

Qwen3-VL returns coordinates in **normalized [0, 1000) format**, NOT pixel coordinates:

```python
# Raw model output: {"x": 499, "y": 547}
# Image dimensions: 1080 x 1920

# Denormalization formula:
pixel_x = int((raw_x / 1000) * image_width)   # (499/1000) * 1080 = 539
pixel_y = int((raw_y / 1000) * image_height)  # (547/1000) * 1920 = 1050

# Implemented in extract_coordinates() node
```

### Fara-7B Pixel Coordinates

Fara-7B returns pixel coordinates directly - no conversion needed.

---

## Execution Commands

### Phase 1: Qwen3-VL Benchmark (SGLang)

```bash
# 1. Start SGLang server
docker compose up -d

# 2. Verify server is ready
curl http://localhost:30000/v1/models

# 3. Run full benchmark (468 screenshots, 3 repetitions)
poetry run python tests/test_evaluator.py \
    --model Qwen/Qwen3-VL-4B-Instruct \
    --url http://localhost:30000 \
    --max-screenshots 468 \
    --repetitions 3

# Results saved to: results/eval_20251227_205122.json
```

### Phase 2: Fara-7B Benchmark (vLLM)

```bash
# 1. Stop SGLang
docker compose down

# 2. Start vLLM with Fara-7B + 4-bit quantization
MODEL_PATH=microsoft/Fara-7B \
QUANTIZATION=bitsandbytes \
TOOL_CALL_PARSER=pythonic \
docker compose -f docker-compose.vllm.yml up -d

# 3. Verify server is ready
curl http://localhost:8000/v1/models

# 4. Run full benchmark
poetry run python tests/test_evaluator.py \
    --model microsoft/Fara-7B \
    --url http://localhost:8000 \
    --max-screenshots 468 \
    --repetitions 3

# Results saved to: results/eval_YYYYMMDD_HHMMSS.json
```

---

## Configuration

### LLM Parameters (Fixed for All Tests)

```python
temperature = 0.01      # Near-deterministic
top_p = 0.6            # Focused sampling
top_k = 50             # Limited vocabulary
```

### Evaluation Parameters

```python
grounding_mode = "visual_only"   # No coordinates in prompt
hit_tolerance_px = 50            # 50 pixel tolerance
max_elements_per_screenshot = 3  # Top 3 visually identifiable
repetitions = 3                  # For statistical significance
```

---

## Server Configurations

### SGLang (Qwen3-VL)

```yaml
# docker-compose.yml
image: lmsysorg/sglang:latest
command:
  --model-path Qwen/Qwen3-VL-4B-Instruct
  --port 30000
  --trust-remote-code
  --attention-backend flashinfer  # RTX 5070 Ti compatibility
  --tool-call-parser qwen
```

### vLLM (Fara-7B)

```yaml
# docker-compose.vllm.yml
image: vllm/vllm-openai:latest
command:
  --model microsoft/Fara-7B
  --port 8000
  --trust-remote-code
  --max-model-len 8192
  --dtype bfloat16
  --quantization bitsandbytes     # 4-bit on-the-fly
  --enable-auto-tool-choice
  --tool-call-parser pythonic
```

---

## Test Dataset

| Parameter | Value |
|-----------|-------|
| Total APKs | 28 |
| Total Screenshots | 468 |
| Elements per Screenshot | ~3 (visually identifiable) |
| Total Unique Elements | 812 |
| Total Tests (with reps) | 2,847 |

### Element Type Distribution

| Type | Count | % |
|------|-------|---|
| Button | 290 | 35.7% |
| ImageButton | 148 | 18.2% |
| TextView | 123 | 15.1% |
| EditText | 102 | 12.6% |
| CheckedTextView | 88 | 10.8% |
| ImageView | 70 | 8.6% |
| Spinner | 49 | 6.0% |
| CheckBox | 36 | 4.4% |
| Switch | 24 | 3.0% |
| RadioButton | 13 | 1.6% |
| Other | 6 | 0.7% |

---

## Results Summary

### Qwen3-VL-4B-Instruct (SGLang, bf16)

| Metric | Value |
|--------|-------|
| Hit Rate | 57.7% |
| Tool Call Rate | 90.3% |
| Avg Distance | 6.2px |
| Avg Latency | 1,821ms |
| Consistency | 98.9% |

**Result Categories**:
- HIT: 57.7%
- MISS: 30.8%
- NO_TOOL: 9.7%
- PARSE_ERROR: 1.8%

**Parser Strategies**:
- native: 54.8% (60.2% hit rate)
- xml: 35.5% (69.5% hit rate)
- none: 9.7%

### Fara-7B (vLLM, bitsandbytes 4-bit)

| Metric | Value |
|--------|-------|
| Hit Rate | 44.3% |
| Tool Call Rate | 79.9% |
| Avg Distance | 4.1px |
| Avg Latency | 1,015ms |

**Status**: COMPLETE - Results in `results/eval_20251227_223843.json`

---

## Hardware

| Component | Specification |
|-----------|---------------|
| GPU | NVIDIA RTX 5070 Ti (16GB VRAM) |
| Architecture | Blackwell (SM120) |
| CUDA | 13.0 (host) / 12.9.1 (container) |
| Host OS | Linux 6.14.0-37-generic |

---

## Files Generated

| File | Description |
|------|-------------|
| `results/eval_20251227_205122.json` | Qwen3-VL full benchmark (2,847 tests) |
| `docs/016_full_benchmark_plan.md` | Benchmark planning |
| `docs/017_full_benchmark_results.md` | Qwen3-VL analysis |
| `docs/018_benchmark_methodology.md` | This document |

---

## Reproducibility Checklist

- [x] Same docker image versions
- [x] Same LLM parameters (temp=0.01, top_p=0.6, top_k=50)
- [x] Same screenshot dataset (468 files)
- [x] Same element filtering (is_visually_identifiable)
- [x] Same coordinate conversion (Qwen: [0,1000) → pixels)
- [x] Same hit tolerance (50px)
- [x] Raw results saved as JSON
- [x] Input prompts saved for debugging
- [x] Raw LLM responses saved
- [x] Fara-7B benchmark complete

---

## Known Issues

### RTX 5070 Ti (SM120) Compatibility

SGLang's TRTLLM MHA backend expects SM100 for Blackwell detection, but RTX 5070 Ti reports SM120.

**Workaround**: Use `--attention-backend flashinfer`

### Qwen3-VL XML Format

Qwen3-VL sometimes outputs tool calls in `<tool_call>` XML format instead of native OpenAI format. The fallback parser handles this transparently.

### Fara-7B Coordinate Formats

Fara-7B uses multiple coordinate formats:
- `{"x": 540, "y": 1054}`
- `{"coordinate": [540, 1054]}`
- Nested arguments structure

The parser normalizes all formats to standard `{x, y}`.

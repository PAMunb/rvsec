# Vision LLM Evaluation for Android UI Automation

## Final Technical Report

**Project**: RVSec Vision LLM Evaluator
**Period**: December 23-28, 2025
**Author**: Automated evaluation framework for RVAgent integration
**Hardware**: NVIDIA RTX 5070 Ti (16GB VRAM)

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Objectives and Scope](#2-objectives-and-scope)
3. [Dataset Description](#3-dataset-description)
4. [Infrastructure Architecture](#4-infrastructure-architecture)
5. [Model Selection Process](#5-model-selection-process)
6. [Technical Discoveries](#6-technical-discoveries)
7. [Evaluation Methodology](#7-evaluation-methodology)
8. [Benchmark Results](#8-benchmark-results)
9. [Model Comparison](#9-model-comparison)
10. [Parser Development](#10-parser-development)
11. [Conclusions and Recommendations](#11-conclusions-and-recommendations)
12. [Appendices](#appendices)

---

## 1. Introduction

This report documents the systematic evaluation of multimodal vision language models (Vision LLMs) for integration into the RVAgent autonomous Android testing tool. The goal was to identify the optimal model and configuration for performing UI element interactions based on visual analysis of screenshots.

RVAgent is an autonomous testing agent that navigates Android applications to discover security vulnerabilities. A critical capability is the ability to identify and interact with UI elements based on their visual appearance rather than relying solely on accessibility metadata. This visual grounding capability enables the agent to handle dynamic UIs, custom widgets, and scenarios where traditional element identification fails.

The evaluation process involved testing multiple candidate models across different inference servers, analyzing their behavior under various configurations, and measuring their accuracy at locating clickable UI elements. This work revealed several technical challenges, including coordinate system differences between models, inference server bugs, and format inconsistencies in model outputs.

---

## 2. Objectives and Scope

### Primary Objectives

1. **Model Selection**: Identify which vision LLM performs best at locating UI elements visually
2. **Server Validation**: Determine which inference server is most reliable for production deployment
3. **Configuration Optimization**: Find optimal sampling parameters for accurate visual grounding
4. **Integration Preparation**: Develop parsing and validation infrastructure compatible with RVAgent

### Evaluation Modes

Two grounding modes were evaluated:

| Mode | Description | Purpose |
|------|-------------|---------|
| `coords_provided` | Element coordinates are explicitly stated in the prompt | Baseline validation - tests if model can follow instructions |
| `visual_only` | Model must locate element visually from screenshot | Real capability assessment - tests visual grounding |

The `visual_only` mode is the primary evaluation target, as it represents the actual use case where coordinates are unknown.

### Success Criteria

- **Hit**: Predicted click within 50 pixels of element center (Euclidean distance)
- **Tool Call**: Model produces a structured tool call (vs. text response)
- **Latency**: Response time per inference

---

## 3. Dataset Description

### Source

The test dataset consists of screenshots and UIAutomator XML dumps collected from 28 Android applications available on F-Droid, an open-source Android app repository.

### Composition

| Metric | Value |
|--------|-------|
| Total APKs | 28 |
| Total Screenshots | 468 |
| Total Unique Elements | 812 |
| Element Types | 13 distinct classes |

### Application Categories

The applications span multiple categories to ensure diversity:

- File managers (SimpleNotes, AnotherFileManager)
- RSS readers (Reddinator, RSS Reader)
- Utilities (Puzzle Solver, Calculator)
- Cryptocurrency wallets (Wallet apps)
- Games and entertainment

### Element Distribution

| Element Type | Count | Percentage |
|--------------|-------|------------|
| Button | 290 | 35.7% |
| ImageButton | 148 | 18.2% |
| TextView | 123 | 15.1% |
| EditText | 102 | 12.6% |
| CheckedTextView | 88 | 10.8% |
| Other | 61 | 7.5% |

### Ground Truth

Ground truth coordinates are extracted programmatically from UIAutomator XML files. Each element's bounds are parsed, and the center point is calculated:

```python
# Example bounds parsing
bounds = "[0,0][1080,1920]"  # [left,top][right,bottom]
center_x = (left + right) // 2
center_y = (top + bottom) // 2
```

This provides pixel-accurate target coordinates for validation.

---

## 4. Infrastructure Architecture

### Hardware Configuration

| Component | Specification |
|-----------|--------------|
| GPU | NVIDIA GeForce RTX 5070 Ti |
| VRAM | 16GB |
| Compute Capability | 12.0 (SM120) |
| Host CUDA | 13.0 |
| Driver | 580.95.05 |

### Inference Server Comparison

Three inference servers were evaluated:

| Server | Backend | Tool Calling | Loop Bug | Recommendation |
|--------|---------|--------------|----------|----------------|
| **SGLang** | PyTorch + FlashInfer | Native | No | **Primary** |
| **vLLM** | PyTorch + PagedAttention | Native | No | Fallback |
| **Ollama** | GGUF (llama.cpp) | Via parser | Yes (16.7%) | Not recommended |

#### SGLang Configuration

SGLang was selected as the primary server due to its stability and performance. A compatibility issue was discovered with the RTX 5070 Ti:

**Problem**: The RTX 5070 Ti reports compute capability 12.0 (SM120), but SGLang's TRTLLM MHA backend expects SM100 for Blackwell detection.

**Solution**: Use the FlashInfer attention backend:

```bash
python -m sglang.launch_server \
    --model-path Qwen/Qwen3-VL-4B-Instruct \
    --port 30000 \
    --attention-backend flashinfer \  # Required for SM120
    --tool-call-parser qwen \
    --trust-remote-code
```

#### vLLM Configuration

vLLM was used as a secondary server for models requiring bitsandbytes quantization:

```bash
docker compose -f docker-compose.vllm.yml up -d
# Supports: QUANTIZATION=bitsandbytes for 4-bit models
```

### Evaluation Framework

The evaluation framework was built using LangChain and LangGraph to align with RVAgent's architecture:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   prepare   │────>│  inference  │────>│   extract   │────>│  validate   │
│  inference  │     │   (async)   │     │ coordinates │     │   result    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

Key components:

- `EvaluationConfig`: Pydantic configuration model
- `VisionLLMClient`: LangChain wrapper for vision models
- `EvaluatorState`: TypedDict workflow state
- `tool_call_parser`: Multi-format response parser

---

## 5. Model Selection Process

### Candidate Models

Nine vision models were evaluated for compatibility and performance:

| Model | Parameters | Architecture | Status |
|-------|------------|--------------|--------|
| Qwen3-VL-4B-Instruct | 4B | Qwen3-VL | **Selected** |
| Qwen3-VL-4B-Thinking | 4B | Qwen3-VL | Excluded |
| microsoft/Fara-7B | 7B | Qwen2.5-VL | **Alternative** |
| google/gemma-3-4b-it | 4B | Gemma | Low performance |
| openbmb/MiniCPM-V-4.5 | 4B | MiniCPM-V | Functional |
| lmms-lab/llava-onevision-7b | 7B | LLaVA | Incompatible |
| allenai/Molmo-7B-D-0924 | 7B | Molmo | Requires TensorFlow |
| OpenGVLab/InternVL2-8B | 8B | InternVL | No structured output |
| zai-org/AutoGLM-Phone-9B | 9B | GLM4V | Quantization fails |

### Exclusion Reasons

**Qwen3-VL-4B-Thinking**: Generated corrupted multilingual output mixing Japanese, Arabic, Russian, and other scripts. "Thinking" models are designed for extended reasoning, not tool calling.

**LLaVA-OneVision-7B**: vLLM error: `Model architectures ['LlavaQwenForCausalLM'] are not supported`. The model uses a different architecture class than expected.

**Molmo-7B-D-0924**: Requires TensorFlow which is not available in the vLLM container.

**InternVL2-8B**: Understands tasks correctly but outputs plain text instead of structured tool calls. Example output: `"To click on the \"Allow\" button using android_click tool... android_click 540 1054"`.

**AutoGLM-Phone-9B**: Assertion error during bitsandbytes quantization: `param_data.shape == loaded_weight.shape` fails. The 9B model requires quantization to fit in 16GB VRAM.

### Selected Models

| Model | Server | Quantization | VRAM Usage |
|-------|--------|--------------|------------|
| Qwen3-VL-4B-Instruct | SGLang | bf16 (none) | ~8GB |
| microsoft/Fara-7B | vLLM | bitsandbytes 4-bit | ~6GB |

---

## 6. Technical Discoveries

### 6.1 Qwen3-VL Coordinate System

A critical discovery was that Qwen3-VL uses a normalized coordinate system, not pixel coordinates.

**Problem Observed**: Initial visual grounding showed only 3.6% hit rate despite correct tool calls. Analysis revealed:

- Target coordinates: (540, 1054) pixels
- Model output: (499, 547) - appeared incorrect

**Discovery**: Qwen3-VL outputs coordinates in the range [0, 1000), which must be converted to pixel coordinates.

**Source**: [GitHub Issue #1486](https://github.com/QwenLM/Qwen3-VL/issues/1486) confirms this is documented behavior.

**Conversion Formula**:

```python
def denormalize_qwen_coords(x, y, image_width, image_height):
    pixel_x = int((x / 1000) * image_width)
    pixel_y = int((y / 1000) * image_height)
    return pixel_x, pixel_y

# Example:
# Raw: (499, 547)
# Converted: (499/1000 * 1080, 547/1000 * 1920) = (539, 1050)
# Distance to target (540, 1054): 4 pixels
```

**Impact**: After applying the conversion, hit rate increased from 3.6% to approximately 50%.

### 6.2 Ollama Infinite Loop Bug

The GGUF-based Ollama server exhibited an infinite loop bug under specific conditions.

**Symptoms**:
- Model generates repetitive text indefinitely
- No tool calls produced
- Generation continues until `num_predict` limit
- Duration: 60-70+ seconds per request

**Trigger Conditions**:

| Parameter | Safe Value | Risky Value |
|-----------|------------|-------------|
| Temperature | >= 0.6 | < 0.3 |
| num_predict | <= 2048 | 8192 |

**Test Results**:

| Test Conditions | Loop Rate |
|-----------------|-----------|
| temp=0.6, num_predict=2048 | 0% (0/12) |
| temp=0.01-0.1, num_predict=8192 | 16.7% (2/12) |

**Root Cause**: The `repeat_penalty` parameter is ignored by the GGUF/llama.cpp backend used by Ollama. Low temperature combined with high token limits creates conditions where the model can enter and not escape repetition loops.

**Confirmation**: PyTorch-based servers (SGLang, vLLM) showed 0% loop rate under identical conditions, confirming the bug is specific to the GGUF backend.

**Recommendation**: Use SGLang or vLLM for production deployments.

### 6.3 Model-Specific Coordinate Formats

Different models output coordinates in different formats, requiring flexible parsing:

| Model | Coordinate Format | Example |
|-------|-------------------|---------|
| Qwen3-VL | Normalized [0, 1000) | `{"x": 499, "y": 547}` |
| Fara-7B | Pixel coordinates | `{"coordinate": [540, 1054]}` |
| Gemma | Action format | `{"action": "android_click", "x": 540, "y": 1054}` |

Fara-7B specifically uses multiple output formats:

- `{"coordinate": [x, y]}`
- `{"bbox": [x, y]}`
- `{"bbox_2d": [x, y]}`
- `{"bounds": [x, y]}`
- `{"bndbox": [x, y]}`
- `{"center": [x, y]}`

---

## 7. Evaluation Methodology

### Test Protocol

Each evaluation follows this protocol:

1. **Element Selection**: Extract clickable elements from UIAutomator XML, filtered by visual identifiability
2. **Prompt Generation**: Create vision message with screenshot and click instruction
3. **Inference**: Send to model, record response and latency
4. **Parsing**: Extract coordinates from response using multi-strategy parser
5. **Validation**: Calculate distance from predicted to target coordinates
6. **Classification**: Categorize result as HIT, MISS, NO_TOOL, or PARSE_ERROR

### Result Categories

| Category | Description |
|----------|-------------|
| **HIT** | Tool called, coordinates within 50px of target |
| **MISS** | Tool called, coordinates outside 50px tolerance |
| **NO_TOOL** | Model returned text instead of tool call |
| **PARSE_ERROR** | Tool call detected but coordinates could not be extracted |

### Metrics Computed

**Primary Metrics**:
- **Hit Rate**: HIT / Total tests
- **Tool Call Rate**: (HIT + MISS + PARSE_ERROR) / Total tests
- **Average Distance**: Mean Euclidean distance for HITs only

**Secondary Metrics**:
- **Latency**: Response time in milliseconds
- **Consistency**: Variance across repeated tests of same element
- **Per-Element-Type Performance**: Breakdown by UI element class

### Visual Element Filtering

Container layouts (LinearLayout, RelativeLayout, FrameLayout) were excluded from visual grounding evaluation because they have no visual representation in screenshots. The `is_visually_identifiable` filter selects only elements that:

1. Have intrinsic visual representation (Button, EditText, CheckBox, etc.), OR
2. Have text or content description that makes them identifiable

### Configuration Sweep

An extended configuration sweep tested 12 parameter combinations:

| Parameter | Values Tested |
|-----------|---------------|
| Temperature | 0.01, 0.1, 0.3, 0.6 |
| Top-P | 0.1, 0.6, 0.9 |
| Top-K | 10, 50, 100 |

**Result**: Configuration impact on hit rate was minimal (~0.5% variance). Best configuration:
- temperature=0.01
- top_p=0.6
- top_k=50

---

## 8. Benchmark Results

### 8.1 Qwen3-VL-4B-Instruct (Full Benchmark)

**Configuration**:
- Model: Qwen/Qwen3-VL-4B-Instruct
- Server: SGLang (bf16, no quantization)
- Screenshots: 468
- Elements: 812
- Repetitions: 3
- Total Tests: 2,847

**Results**:

| Metric | Value |
|--------|-------|
| **Hit Rate** | **57.7%** |
| **Tool Call Rate** | **90.3%** |
| **Average Distance (hits)** | 6.2px |
| **Average Latency** | 1,821ms |
| **Consistency** | 98.9% |

**Result Category Distribution**:

| Category | Count | Rate |
|----------|-------|------|
| HIT | 1,642 | 57.7% |
| MISS | 878 | 30.8% |
| NO_TOOL | 277 | 9.7% |
| PARSE_ERROR | 50 | 1.8% |

### 8.2 Fara-7B (Full Benchmark)

**Configuration**:
- Model: microsoft/Fara-7B
- Server: vLLM with bitsandbytes 4-bit quantization
- Screenshots: 468
- Elements: 812
- Repetitions: 3
- Total Tests: 2,847

**Results**:

| Metric | Value |
|--------|-------|
| **Hit Rate** | **44.3%** |
| **Tool Call Rate** | **79.9%** |
| **Average Distance (hits)** | 4.1px |
| **Average Latency** | 1,015ms |

**Result Category Distribution**:

| Category | Count | Rate |
|----------|-------|------|
| HIT | 1,261 | 44.3% |
| MISS | 458 | 16.1% |
| NO_TOOL | 573 | 20.1% |
| PARSE_ERROR | 555 | 19.5% |

### 8.3 Element Type Performance

Performance varies significantly by UI element type:

**Qwen3-VL Performance by Element Type**:

| Element Type | Hit Rate | Tool Call Rate | Analysis |
|--------------|----------|----------------|----------|
| EditText | **93.1%** | 100.0% | Text input fields are visually distinct |
| Button | **78.2%** | 90.3% | Clear boundaries and labels |
| View | 75.0% | 100.0% | Custom views with content |
| Switch | 69.4% | 95.8% | Toggle switches recognizable |
| Spinner | 63.3% | 100.0% | Dropdown indicators help |
| TextView | 60.2% | 94.9% | Depends on surrounding context |
| ImageButton | 43.5% | 83.6% | Icons without text are harder |
| CheckedTextView | 29.2% | 97.7% | Selection state confuses model |
| CheckBox | 25.0% | 100.0% | Small visual footprint |
| ImageView | 0.0% | 56.2% | Pure images rarely clicked correctly |
| RadioButton | 0.0% | 100.0% | Model fails to identify |

**Fara-7B Comparative Strengths**:

| Element Type | Qwen3-VL | Fara-7B | Difference |
|--------------|----------|---------|------------|
| CheckedTextView | 29.2% | **71.6%** | Fara +42.4% |
| RadioButton | 0.0% | **61.5%** | Fara +61.5% |
| CheckBox | 25.0% | **54.6%** | Fara +29.6% |
| EditText | **93.1%** | 12.4% | Qwen +80.7% |
| Button | **78.2%** | 66.2% | Qwen +12.0% |

This suggests Fara-7B may have been trained on more selection control patterns, while Qwen3-VL handles text-based elements better.

---

## 9. Model Comparison

### Summary Comparison

| Metric | Qwen3-VL | Fara-7B | Winner |
|--------|----------|---------|--------|
| Hit Rate | **57.7%** | 44.3% | Qwen3-VL (+13.4%) |
| Tool Call Rate | **90.3%** | 79.9% | Qwen3-VL (+10.4%) |
| Avg Distance | 6.2px | **4.1px** | Fara-7B |
| Avg Latency | 1,821ms | **1,015ms** | Fara-7B (44% faster) |
| PARSE_ERROR | **1.8%** | 19.5% | Qwen3-VL |
| NO_TOOL | **9.7%** | 20.1% | Qwen3-VL |

### Analysis

**Qwen3-VL Advantages**:
1. Higher overall accuracy (57.7% vs 44.3%)
2. More reliable tool calling (90.3% vs 79.9%)
3. Lower parse error rate (1.8% vs 19.5%)
4. Better on common elements (EditText, Button, TextView)
5. High consistency (98.9% across repetitions)

**Fara-7B Advantages**:
1. Faster inference (44% improvement)
2. Better on selection controls (CheckBox, RadioButton, CheckedTextView)
3. More precise when correct (4.1px vs 6.2px average distance)
4. Lower VRAM with quantization

### Selection Rationale

Qwen3-VL was selected as the primary model because:

1. **Accuracy is more important than speed** for autonomous testing - a wrong click can derail an entire test sequence
2. **Higher tool call rate** means fewer failed interactions requiring retry logic
3. **Lower parse error rate** indicates more predictable output format
4. **Better performance on common elements** (Button, EditText) which are frequently interacted with

The 44% latency advantage of Fara-7B does not compensate for the 13.4% accuracy deficit.

---

## 10. Parser Development

### Challenge

Vision models produce tool calls in multiple formats depending on:
- Model architecture and training
- Inference server configuration
- Tool call parser settings

A flexible parser was required to handle all observed formats.

### Parser Strategies

The `tool_call_parser.py` module implements six parsing strategies, attempted in order:

1. **JSON Array**: `[{"name": "tool", "parameters": {...}}]`
2. **JSON Object**: `{"name": "tool", "parameters": {...}}`
3. **XML Tags**: `<tool_call>{"name": ...}</tool_call>`
4. **Markdown Code Blocks**: ` ```json {...} ``` `
5. **Pythonic Calls**: `android_click(x=540, y=1054)`
6. **Native Tool Calls**: LangChain's native tool_calls field

### Coordinate Normalization

The `normalize_tool_args` function handles multiple coordinate formats:

```python
# Supported formats:
{"x": 540, "y": 1054}           # Standard
{"x": [540, 1054]}              # Qwen3-VL malformed
{"coordinate": [540, 1054]}     # Fara-7B
{"coordinates": [540, 1054]}    # Alternative
{"bbox": [540, 1054]}           # Fara-7B variant
{"bbox_2d": [540, 1054]}        # Fara-7B variant
{"bounds": [540, 1054]}         # Fara-7B variant
{"bndbox": [540, 1054]}         # Fara-7B variant
{"center": [540, 1054]}         # Fara-7B variant
{"arguments": {"coordinate": [540, 1054]}}  # Nested
```

### JSON Fix Patterns

Malformed JSON from models is automatically corrected:

| Pattern | Fix |
|---------|-----|
| `"x": 352, 782` | `"x": 352, "y": 782` |
| `"x": [352, 782]` | `"x": 352, "y": 782` |
| `"x": .91` | `"x": 0.91` |
| `"x":": 541` | `"x": 541` |
| Truncated `{...` | Add missing `}` |

### Parser Improvement Results

After adding support for Fara-7B coordinate formats, the PARSE_ERROR rate decreased:

| Version | PARSE_ERROR Rate |
|---------|------------------|
| Original | 19.5% |
| After bbox/bbox_2d/bounds | 14.4% |
| After bndbox/center | 12.5% |

The remaining ~12.5% PARSE_ERROR cases occur when models output element descriptions without coordinates, which cannot be fixed at the parser level.

---

## 11. Conclusions and Recommendations

### Key Findings

1. **Qwen3-VL-4B-Instruct is the recommended model** for RVAgent integration, achieving 57.7% hit rate and 90.3% tool call rate in visual grounding mode.

2. **SGLang is the recommended inference server** due to zero loop bugs and native tool calling support. The RTX 5070 Ti requires the FlashInfer attention backend.

3. **Coordinate system handling is critical** - Qwen3-VL uses [0, 1000) normalized coordinates that must be converted to pixels.

4. **Element type affects performance significantly** - EditText (93.1%) and Button (78.2%) are reliable, while ImageView (0%) and RadioButton (0%) require explicit coordinate guidance.

5. **Configuration has minimal impact** on visual grounding accuracy (~0.5% variance across configurations tested).

### Integration Recommendations

**For RVAgent Integration**:

```python
# Recommended configuration
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

**Hybrid Strategy**:

1. Try visual grounding first for all elements
2. If NO_TOOL or MISS, fall back to coordinate-based approach using UIAutomator data
3. For ImageView, RadioButton, and CheckBox elements, consider providing explicit coordinates directly

**Performance Expectations**:

| Metric | Expected Value |
|--------|----------------|
| Hit Rate (visual_only) | ~58% |
| Tool Call Rate | ~90% |
| Latency per inference | ~1.8 seconds |
| Throughput | ~33 inferences/minute |

### Limitations

1. **Visual grounding is not 100% reliable** - approximately 42% of visual clicks will miss the target
2. **Icon-based elements are problematic** - ImageButton, ImageView have low accuracy
3. **Selection controls require attention** - CheckBox, RadioButton performance varies by model

### Future Work

1. **Fine-tuning**: Train a model specifically on Android UI screenshots and interaction patterns
2. **Multi-model ensemble**: Use Qwen3-VL for text elements and Fara-7B for selection controls
3. **Confidence-based fallback**: Use model confidence scores to decide when to fall back to coordinates
4. **Larger models**: Evaluate 7B+ parameter models when VRAM permits (with better quantization)

---

## Appendices

### A. File Structure

```
rvsec-vision-llm/
├── src/
│   ├── config/evaluation_config.py
│   ├── llm/
│   │   ├── client.py
│   │   ├── tools/android_tools.py
│   │   └── graph/{state.py, nodes.py}
│   ├── evaluator/evaluator.py
│   ├── parsers/{tool_call_parser.py, uiautomator_parser.py}
│   └── validation/click_validator.py
├── tests/test_evaluator.py
├── scripts/run_benchmark.py
├── results/                    # JSON benchmark results
├── screenshots/                # Test dataset (468 screenshots)
└── docs/                       # Documentation
```

### B. Commands Reference

```bash
# Start SGLang server
docker compose up -d

# Start vLLM server (for Fara-7B)
MODEL_PATH=microsoft/Fara-7B \
QUANTIZATION=bitsandbytes \
TOOL_CALL_PARSER=pythonic \
docker compose -f docker-compose.vllm.yml up -d

# Run benchmark
poetry run python tests/test_evaluator.py \
    --model Qwen/Qwen3-VL-4B-Instruct \
    --url http://localhost:30000 \
    --max-screenshots 468 \
    --repetitions 3
```

### C. Documentation Index

| Document | Content |
|----------|---------|
| 001_sglang_validation.md | Initial SGLang server validation |
| 002_server_comparison.md | Server comparison results |
| 006_ollama_loop_bug.md | Ollama infinite loop analysis |
| 009_qwen3vl_coordinates.md | Coordinate system discovery |
| 010_model_validation.md | Model compatibility testing |
| 011_element_type_analysis.md | Element-wise performance breakdown |
| 015_langchain_refactoring.md | Architecture documentation |
| 017_full_benchmark_results.md | Qwen3-VL detailed results |
| 019_fara7b_results_comparison.md | Model comparison |
| 021_fara7b_parser_improvements.md | Parser enhancement documentation |

### D. Benchmark Data

Full benchmark results are stored in JSON format:

- `results/eval_20251227_205122.json` - Qwen3-VL full benchmark (2,847 tests)
- `results/eval_20251227_223843.json` - Fara-7B full benchmark (2,847 tests)

Each result file contains:
- Configuration parameters
- Per-screenshot results
- Per-element results with coordinates and distances
- Aggregate metrics
- Parser strategy statistics
- Token usage statistics

---

**End of Report**

*Generated: December 28, 2025*

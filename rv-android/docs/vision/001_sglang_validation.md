# 001 - SGLang Validation Results

**Date**: 2025-12-23
**Phase**: 0 - Basic Validation
**Objective**: Verify SGLang can load vision models, process images, and use tool calling

---

## Hardware Configuration

| Component | Value |
|-----------|-------|
| GPU | NVIDIA GeForce RTX 5070 Ti |
| VRAM | 16GB |
| Compute Capability | 12.0 (SM120) |
| Host CUDA | 13.0 |
| Driver | 580.95.05 |

---

## SGLang Configuration

```yaml
image: lmsysorg/sglang:latest
container_cuda: 12.9.1
pytorch: 2.9.1+cu129
flashinfer: 0.5.3
triton: 3.5.1
```

### Required Parameters for RTX 5070 Ti (SM120)

```bash
--attention-backend flashinfer  # Required! TRTLLM MHA expects SM100
--enable-multimodal             # Required for vision models
--context-length 8192           # Or lower for larger models
--tool-call-parser <parser>     # Model-specific (qwen, pythonic, etc.)
```

**Note**: SGLang defaults to TRTLLM MHA backend which only supports SM100 (Blackwell original). RTX 5070 Ti reports SM120, causing detection failure. Use FlashInfer as workaround.

---

## Test Results

### Test Configuration

- **Screenshot**: `screenshots/com.rafapps.simplenotes_7.apk/001.png`
- **Target Element**: Sort button
- **Expected Coordinates**: (889, 136)
- **Task**: Click on the Sort button

### Results Summary

| Model | Status | Coordinates | Distance | Latency | Context | Notes |
|-------|--------|-------------|----------|---------|---------|-------|
| Qwen3-VL-4B-Instruct | **PASS** | (889, 136) | 0.0px | 2442ms | 8192 | parser=qwen |
| Qwen3-VL-4B-Thinking | **PASS** | (889, 136) | 0.0px | 1441ms | 8192 | parser=qwen |
| gemma-3-4b-it | **PARTIAL** | (889, 136) | 0.0px | 1135ms | 4096 | JSON format |
| AutoGLM-Phone-9B | **SKIP** | - | - | - | - | OOM, GGUF only |
| Fara-7B | **SKIP** | - | - | - | - | OOM, GGUF only |

### Memory Usage

| Model | Weights | KV Cache | Context | Status |
|-------|---------|----------|---------|--------|
| Qwen3-VL-4B-Instruct | 8.63GB | 2.14GB | 8192 | OK |
| gemma-3-4b-it | 8.07GB | 2.26GB | 4096 | OK (OOM with 8192) |
| Fara-7B | 14.43GB | - | - | OOM during weight loading |
| AutoGLM-Phone-9B | >14GB | - | - | OOM (estimated) |

---

## Detailed Findings

### 1. Qwen3-VL-4B Models (Recommended)

Both Qwen3-VL-4B variants achieved **perfect accuracy** (0.0px distance):

```
Testing: Qwen3-VL-4B-Instruct
  SUCCESS - Tool: android_click
  Coordinates: (889, 136)
  Distance from expected: 0.0px
  Latency: 2442ms

Testing: Qwen3-VL-4B-Thinking
  SUCCESS - Tool: android_click
  Coordinates: (889, 136)
  Distance from expected: 0.0px
  Latency: 1441ms
```

**Configuration**:
```bash
MODEL_PATH=Qwen/Qwen3-VL-4B-Instruct
TOOL_CALL_PARSER=qwen
CONTEXT_LENGTH=8192
```

### 2. gemma-3-4b-it (Needs Parser)

Gemma returned correct coordinates but in custom JSON format instead of OpenAI tool call format:

```json
{
  "action": "android_click",
  "element_id": "Sort",
  "coordinates": [889, 136]
}
```

**Issues**:
- OOM with context=8192, needs context<=4096
- Requires custom parser for JSON output
- `pythonic` tool-call-parser does not work

**TODO**: Create custom gemma output parser for evaluator

### 3. AutoGLM-Phone-9B and Fara-7B (Require llama.cpp)

Both models exceed 16GB VRAM without quantization:
- **Fara-7B**: 14.43GB weights alone (based on Qwen-2.5-VL-7B)
- **AutoGLM-Phone-9B**: ~9B parameters, similar issue

Only GGUF quantized versions available:
- [Fara-7B GGUF](https://huggingface.co/bartowski/microsoft_Fara-7B-GGUF)
- [AutoGLM-Phone-9B GGUF](https://huggingface.co/mradermacher/AutoGLM-Phone-9B-Multilingual-GGUF)

**Solution**: Use llama.cpp server instead of SGLang for these models.

---

## SGLang Quantization Notes

SGLang does NOT support bitsandbytes on-the-fly quantization in production mode.

**Supported quantization methods**:
```
fp8, blockwise_int8, modelopt, modelopt_fp8, modelopt_fp4, w8a8_int8,
w8a8_fp8, awq, awq_marlin, gguf, gptq, gptq_marlin, moe_wna16,
compressed-tensors, qoq, w4afp8, petit_nvfp4, fbgemm_fp8, quark,
auto-round, mxfp4
```

**Known issues with bitsandbytes**:
- https://github.com/sgl-project/sglang/issues/2769 (Bug)
- https://github.com/sgl-project/sglang/issues/4263 (Low performance)

**Recommendation**: Use pre-quantized AWQ/GPTQ models for larger models.

---

## Conclusions

1. **Qwen3-VL-4B-Instruct is the best option for SGLang** on 16GB VRAM
   - Perfect accuracy (0.0px)
   - Proper tool calling support with `--tool-call-parser qwen`
   - Fits comfortably with context=8192

2. **gemma-3-4b-it works but needs custom handling**
   - Correct coordinates but wrong output format
   - Requires context<=4096 due to memory
   - Need to implement custom JSON parser

3. **Larger models (7B+) require llama.cpp**
   - No AWQ/GPTQ versions available
   - SGLang bitsandbytes has issues
   - GGUF + llama.cpp is the viable path

---

## Next Steps

1. ~~Phase 0 complete for SGLang~~
2. Test llama.cpp with GGUF models (Fara-7B, AutoGLM-Phone-9B)
3. Phase 1: Validate infinite loop bug with Ollama
4. Phase 2: Build evaluator infrastructure

---

## Raw Test Output

### Qwen3-VL-4B Test
```
RVSec Vision LLM Evaluator - Phase 0
Server URL: http://localhost:30000
Loading test screenshot...
  Screenshot: screenshots/com.rafapps.simplenotes_7.apk/001.png
  Target element: Sort
  Expected coords: (889, 136)

Testing: Qwen3-VL-4B-Instruct
  SUCCESS - Tool: android_click
  Coordinates: (889, 136)
  Distance from expected: 0.0px
  Latency: 2442ms

Testing: Qwen3-VL-4B-Thinking
  SUCCESS - Tool: android_click
  Coordinates: (889, 136)
  Distance from expected: 0.0px
  Latency: 1441ms

Overall: 2/2 models passed
```

### gemma-3-4b-it Test
```
Testing: gemma-3-4b-it
  FAILED - No tool call in response. Content: ```json
{
  "action": "android_click",
  "element_id": "Sort",
  "coordinates": [889, 136]
}
```
  Latency: 1135ms

Overall: 0/1 models passed (but coordinates correct)
```

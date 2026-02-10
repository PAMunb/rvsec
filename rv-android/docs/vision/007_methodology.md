# Evaluation Methodology

## Overview

This document describes the methodology used to evaluate inference servers and vision-language models for the RVAgent Android UI automation system.

## Phase 1: Loop Bug Validation

### Objective
Identify and exclude inference servers with the infinite loop bug that affects GGUF-based backends.

### Servers Tested

| Server | Backend | Result | Status |
|--------|---------|--------|--------|
| Ollama | llama.cpp/GGUF | 16.7% loop rate | **EXCLUDED** |
| LM Studio | llama.cpp/GGUF | Not tested (same backend) | **EXCLUDED** |
| SGLang | PyTorch/FlashInfer | 0% loop rate | PASSED |
| vLLM | PyTorch/PagedAttention | 0% loop rate | PASSED |

### LM Studio Exclusion Rationale

LM Studio was excluded without direct testing because:

1. **Same Backend**: LM Studio uses llama.cpp internally, the same backend as Ollama
   - Source: [llama.cpp GitHub](https://github.com/ggml-org/llama.cpp) - "Every model running with llama.cpp works as expected when run from within any app like Ollama or LM Studio"

2. **Known Token Repetition Issues**: llama.cpp has documented token repetition bugs
   - Source: [GitHub Issue #13310](https://github.com/ggml-org/llama.cpp/issues/13310) - "Qwen3-8B and other models generate garbage output / repeat tokens (GGGGGGGGGG...) in llama.cpp via LM Studio"

3. **GGUF Format Limitation**: Both use GGUF format with the same sampler implementation
   - The `repeat_penalty` bug is in the llama.cpp sampler, affecting all GGUF-based tools

4. **No Docker Support**: LM Studio is a desktop application without official headless Docker images
   - Community alternatives require manual AppImage setup

### Loop Bug Characteristics

- **Trigger conditions**: temperature < 0.3, max_tokens > 2048, repetitive UI patterns
- **Root cause**: `repeat_penalty` parameter ignored in GGUF sampler
- **Duration**: 60+ seconds of token generation without useful output
- **Detection**: `done_reason: "length"` with ~8192 tokens

## Phase 2: Inference Server Comparison (SGLang vs vLLM)

### Objective
Compare SGLang and vLLM performance across multiple models and configurations.

### Quantization Support

| Feature | SGLang | vLLM |
|---------|--------|------|
| AWQ | ✅ | ✅ |
| GPTQ | ✅ | ✅ |
| FP8 | ✅ | ✅ |
| bitsandbytes (on-the-fly) | ❌ | ✅ |
| Pre-quantized models | ✅ | ✅ |

**Key Finding**: vLLM supports **on-the-fly quantization via bitsandbytes**, allowing testing of non-quantized models in 4-bit mode without pre-quantization.

Sources:
- [vLLM Quantization Docs](https://docs.vllm.ai/en/latest/features/quantization/)
- [vLLM BitsAndBytes Docs](https://docs.vllm.ai/en/stable/features/quantization/bnb/)
- [SGLang GitHub](https://github.com/sgl-project/sglang)

### Models to Test

**Primary (with AWQ/GPTQ available)**:
- Qwen/Qwen3-VL-4B-Instruct
- Qwen/Qwen3-VL-4B-AWQ

**Secondary (via vLLM bitsandbytes)**:
- google/gemma-3-4b-it
- microsoft/Fara-7B
- zai-org/AutoGLM-Phone-9B-Multilingual

### Test Configuration

- **Sample size**: 50-70 screenshots (statistically significant subset)
- **Repetitions**: 3 per configuration (variance measurement)
- **Temperature sweep**: 0.1, 0.25, 0.4, 0.6
- **Top-P sweep**: 0.8, 0.9, 0.95

### Metrics Collected

| Metric | Description | Unit |
|--------|-------------|------|
| Hit Rate | Click inside target element bounds | % |
| Center Distance | Euclidean distance from element center | pixels |
| Latency (TTFT) | Time to first token | ms |
| Latency (Total) | Total response time | ms |
| Token Count | Tokens generated | count |
| Tool Call Success | Valid tool call parsed | % |
| Memory Usage | GPU VRAM consumption | GB |
| Throughput | Requests per second | req/s |

### Execution Protocol

1. Start server A with model X
2. Run test suite (50-70 screenshots × 3 repetitions)
3. Stop server A, clear GPU memory
4. Start server B with model X
5. Run test suite (50-70 screenshots × 3 repetitions)
6. Repeat for each model

## Phase 3: Final Benchmark

### Objective
Validate the winning model/server/config combination on the complete dataset.

### Configuration
- **Full dataset**: 468 screenshots
- **Single pass**: Best configuration from Phase 2
- **Metrics**: Complete metrics suite

### Success Criteria
- Hit rate > 95%
- Average center distance < 50px
- No infinite loops
- Stable tool calling

## File References

- `tests/test_ollama_loop.py` - Ollama loop bug test
- `tests/test_sglang_loop.py` - SGLang loop bug test
- `tests/test_vllm_loop.py` - vLLM loop bug test
- `tests/test_lmstudio_loop.py` - LM Studio test (excluded)
- `docs/006_ollama_loop_bug.md` - Detailed loop bug analysis
- `docs/002_server_comparison.md` - Server comparison results

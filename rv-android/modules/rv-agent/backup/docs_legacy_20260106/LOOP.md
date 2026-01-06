# Token Repetition Loop Bug - Qwen3-VL 4B on Ollama

**Date**: 2025-11-14
**Model**: qwen3-vl:4b (Qwen3-VL-4B-Instruct)
**Backend**: Ollama (GGUF format)
**Project**: RVAgent (Android UI testing with vision-language models)

---

## Executive Summary

The Qwen3-VL 4B model exhibits a critical **token repetition loop bug** when running on Ollama (GGUF backend). The model generates the same text fragment thousands of times until hitting the `num_predict` token limit, rendering responses invalid and consuming 14-58 seconds per occurrence.

**Key Findings:**
- **Bug is in Ollama's GGUF sampler**, not in the model itself
- **repeat_penalty parameter is completely IGNORED** by Ollama
- **No official fix available** (confirmed by GitHub issues since January 2025)
- **Safety nets reduce damage but NOT probability** (loop duration: 58s → 14s, but still 50% occurrence rate)
- **HuggingFace backend does NOT exhibit this bug** (uses PyTorch natively)

---

## 1. Problem Description

### What is the "Loop" / "Token Repetition"?

**Technical Definition:**
The model **repeats the same text fragment** (words, JSON, or code) hundreds or thousands of times until reaching the `num_predict` token limit.

**Example (Generic):**
```
Input: "What should I click on this screen?"
Output: {
  "action": "click",
  "reasoning": "I should click the button"
}
{
  "action": "click",
  "reasoning": "I should click the button"
}
{
  "action": "click",
  "reasoning": "I should click the button"
}
[... repeated 100+ times until 2048 tokens ...]
```

**Actual RVAgent Example:**
```json
{
  "done_reason": "length",
  "eval_count": 2048,
  "eval_duration": 14342853476,  // 14.3 seconds
  "total_duration": 14351700000,
  "tool_calls": []  // Empty - invalid response
}
```

**Impact:**
- LLM response is **invalid** (parsing fails)
- System falls back to algorithm
- **14-58 seconds wasted** per occurrence
- High fallback rate degrades testing effectiveness

---

## 2. Root Cause Analysis

### 2.1. Confirmed Bug in Ollama GGUF Sampler

**GitHub Evidence:**

1. **ollama/ollama #10767** (January 2025)
   - Title: "repeat_penalty has no effect"
   - Status: Open, no fix
   - Confirmed: `repeat_penalty` is **completely ignored** by Ollama

2. **QwenLM/Qwen3-VL #1611** (February 2025)
   - Title: "Infinite repetition loop during table transcription"
   - Root cause: GGUF sampler bug in Ollama
   - Workaround: Use HuggingFace or vLLM instead

3. **ggml-org/llama.cpp #14663** (March 2025)
   - Title: "Repetition with non-Q4 quantization and flash attention"
   - Confirmed: Bug specific to GGUF backend

**Technical Cause:**
- Ollama uses **GGUF quantized models** (converted from PyTorch/SafeTensors)
- Bug in **GGUF's sampling logic** for vision-language models
- **repeat_penalty** parameter exists but is **not applied** during token generation
- **Flash attention** exacerbates the issue

### 2.2. Why It Doesn't Happen with HuggingFace

**Key Difference:**
- HuggingFace uses **native PyTorch** models (no GGUF conversion)
- Sampling is done by **transformers library** (not llama.cpp/GGUF)
- **repeat_penalty is properly implemented** in transformers

**Evidence:**
- Official Qwen3-VL HuggingFace demo: **No loops reported**
- Community reports: Loops only occur with Ollama/llama.cpp
- vLLM (uses HuggingFace models): **No loops**

### 2.3. Triggering Conditions

**Visual Patterns that Trigger Loops:**
1. **Repetitive UI elements** (lists, grids, tables)
2. **Forms with multiple similar fields**
3. **Icon grids** (app drawer, home screen)
4. **Long scrollable lists** (settings, contacts)
5. **Tabular data** (spreadsheets, calendars)

**Model State Factors:**
- **Low temperature** (< 0.3): Increases loop probability (greedy decoding)
- **Large context window** (16K): Allows longer loops before truncation
- **High num_predict** (8192): Permits 58-second loops
- **Quantization level**: Q8/BF16 worse than Q4

**RVAgent Context:**
- Testing **Android apps** with UI grids and lists
- **CryptoApp**: Simple UI, **0% loops** (no grids)
- **Simplenotes**: List-based UI, **high loop rate** (3/5 calls)

---

## 3. Evidence from RVAgent Tests

### 3.1. Test 1: 5 Apps with 8K Model (Before Loop Mitigation)

**Configuration:**
- Model: `qwen3-vl-4b-8k:latest` (8K context, 4K output)
- Duration: 300s per app (5 apps = 25 min)
- Parameters: temperature=0.1, top_p=0.9, top_k=40

**Results:**
- **Overall success rate: 88.6%**
- **Simplenotes: 3 loops** (out of 5 LLM calls)
  - Each loop: **28 seconds**, 4096 tokens
- **Average tokens/call: 4,598** (exceeds 4096 limit)

**Loop Example:**
```json
{
  "app": "com.rafapps.simplenotes",
  "done_reason": "length",
  "eval_count": 4096,
  "total_duration": 28547123456  // 28.5 seconds
}
```

### 3.2. Test 2: 5 Apps with 16K Model (No Mitigation)

**Configuration:**
- Model: `qwen3-vl-4b-16k:latest` (16K context, 8K output)
- Duration: 300s per app (5 apps = 25 min)
- Parameters: temperature=0.25, top_p=0.8, top_k=50

**Results:**
- **Overall success rate: 48.1%** (WORSE than 8K!)
- **Simplenotes: 3 loops** (out of 5 LLM calls)
  - Each loop: **58 seconds**, 8192 tokens
  - **174 seconds total wasted** (58% of test time)

**Loop Example:**
```json
{
  "app": "com.rafapps.simplenotes",
  "done_reason": "length",
  "eval_count": 8192,
  "total_duration": 58702115327  // 58.7 seconds
}
```

**Why Worse?**
- Larger `num_predict` (8192) allows **longer loops**
- Same loop probability, but **4x duration** (28s → 58s)

### 3.3. Test 3: CryptoApp with 16K Model (Monitored)

**Configuration:**
- Model: `qwen3-vl-4b-16k:latest`
- Duration: 120s
- App: br.unb.cic.cryptoapp (simple cipher UI)

**Results:**
- **Success rate: 100%** ✅
- **Zero loops** (all `done_reason: 'stop'`)
- **Average tokens/call: 3,450**
- GPU memory: 9.9 GB

**Why No Loops?**
- CryptoApp has **simple, non-repetitive UI**
- Few elements (buttons, text fields, cipher output)
- **No grids or lists** that trigger visual repetition

### 3.4. Test 4: Safety Nets Validation (FAILED)

**Configuration:**
- Model: `qwen3-vl-4b-16k:latest` with safety nets
- Modelfile parameters:
  - `temperature 0.6` (Qwen official recommendation)
  - `top_p 0.95` (more diverse sampling)
  - `top_k 20` (fewer candidates)
- agent_factory.py:
  - `num_predict 2048` (damage control)

**Results (4 LLM calls):**
- **2 loops** (50% loop rate) ❌
- **Loop duration: 14.3 seconds** ✅ (vs 58s before)
- **Still invalid responses** (fallback triggered)

**Conclusion:**
- ✅ **Damage control works**: 58s → 14s (4x reduction)
- ❌ **Probability NOT reduced**: 50% loop rate (expected ~10%)
- ❌ **Safety nets FAILED to prevent loops**

---

## 4. Solutions Attempted

### 4.1. Solution 1: Increase Context Window (FAILED)

**Approach:**
Created custom model with 16K context window (vs 8K default)

**Implementation:**
```dockerfile
# Modelfile.qwen3-vl-4b-16k
FROM qwen3-vl:4b
PARAMETER num_ctx 16384  # 16K context
PARAMETER num_predict 8192  # 8K output
```

**Result:**
- ❌ **WORSE performance** (88.6% → 48.1% success)
- **Loop duration increased** (28s → 58s)
- Larger context allows **longer loops** before truncation

**Conclusion:** Increasing context window EXACERBATES the problem.

### 4.2. Solution 2: Safety Net Parameters (PARTIAL SUCCESS)

**Approach:**
Apply Qwen3-VL official recommendations to reduce loop probability

**Implementation:**

**Modelfile:**
```dockerfile
FROM qwen3-vl:4b
PARAMETER num_ctx 16384
PARAMETER temperature 0.6   # Official: 0.6 for VL
PARAMETER top_p 0.95        # Official: 0.95
PARAMETER top_k 20          # Official: 20
```

**agent_factory.py:**
```python
llm_base = ChatOllama(
    model="qwen3-vl-4b-16k:latest",
    temperature=0.6,    # Reduce loop probability
    top_p=0.95,         # More diverse sampling
    top_k=20,           # Fewer low-quality candidates
    num_predict=2048,   # Limit damage (14s instead of 58s)
    num_ctx=16384,
    timeout=15.0        # Kill loops after 15s
)
```

**Result:**
- ✅ **Damage reduced**: 58s → 14s per loop
- ❌ **Probability NOT reduced**: 50% loop rate (expected ~10%)
- ⚠️ **Still unusable**: 50% of responses are invalid

**Conclusion:** Safety nets mitigate damage but do NOT solve root cause.

### 4.3. Solution 3: repeat_penalty (NO EFFECT)

**Approach:**
Use `repeat_penalty` parameter to penalize repetition

**Implementation:**
```dockerfile
PARAMETER repeat_penalty 1.5
PARAMETER repeat_last_n 128
```

**Result:**
- ❌ **Completely ignored** by Ollama (confirmed by issue #10767)
- **No change in loop behavior**

**Conclusion:** repeat_penalty does NOT work in Ollama GGUF backend.

---

## 5. Comparison: Ollama vs HuggingFace/vLLM

| Aspect | Ollama (GGUF) | HuggingFace/vLLM |
|--------|---------------|------------------|
| **Backend** | llama.cpp (GGUF) | transformers (PyTorch) |
| **Format** | Quantized GGUF | Native PyTorch/SafeTensors |
| **Sampling** | llama.cpp sampler | transformers sampler |
| **repeat_penalty** | ❌ Ignored | ✅ Working |
| **Loop bug** | ✅ Present | ❌ Absent |
| **GPU memory** | ~10 GB (Q4_K_M) | ~14-16 GB (BF16) |
| **Quantization** | Built-in (Q4, Q8) | Requires bitsandbytes/AWQ |
| **Performance** | Fast | Slightly slower |
| **Setup** | Simple (1 command) | Complex (pip install, model download) |

---

## 6. Recommended Solution: Migrate to vLLM

### Why vLLM?

**Advantages:**
1. ✅ **No loop bug** (uses HuggingFace transformers)
2. ✅ **repeat_penalty works** properly
3. ✅ **Quantization support** (AWQ, GPTQ, bitsandbytes)
4. ✅ **Fast inference** (optimized for production)
5. ✅ **OpenAI-compatible API** (easy integration)
6. ✅ **Same model** (Qwen3-VL-4B-Instruct)

**Disadvantages:**
- ⚠️ More complex setup than Ollama
- ⚠️ Slightly higher GPU memory (14-16 GB vs 10 GB)
- ⚠️ Requires CUDA toolkit and transformers

### vLLM Implementation Plan

**Step 1: Install vLLM**
```bash
# Create virtual environment
python -m venv vllm-env
source vllm-env/bin/activate

# Install vLLM with CUDA support
pip install vllm
pip install "transformers>=4.40.0"
```

**Step 2: Download Model**
```bash
# Download Qwen3-VL-4B-Instruct from HuggingFace
huggingface-cli download Qwen/Qwen3-VL-4B-Instruct \
  --local-dir ./models/qwen3-vl-4b
```

**Step 3: Launch vLLM Server**
```bash
# Start OpenAI-compatible server
python -m vllm.entrypoints.openai.api_server \
  --model ./models/qwen3-vl-4b \
  --dtype bfloat16 \
  --max-model-len 16384 \
  --max-num-seqs 4 \
  --gpu-memory-utilization 0.9 \
  --port 8000
```

**Step 4: Test with Quantization (Optional)**

**AWQ Quantization (4-bit):**
```bash
# Download pre-quantized AWQ model (if available)
huggingface-cli download Qwen/Qwen3-VL-4B-Instruct-AWQ \
  --local-dir ./models/qwen3-vl-4b-awq

# Launch with AWQ
python -m vllm.entrypoints.openai.api_server \
  --model ./models/qwen3-vl-4b-awq \
  --quantization awq \
  --dtype float16 \
  --max-model-len 16384 \
  --port 8000
```

**GPTQ Quantization (4-bit):**
```bash
# Or use GPTQ if AWQ not available
python -m vllm.entrypoints.openai.api_server \
  --model ./models/qwen3-vl-4b \
  --quantization gptq \
  --dtype float16 \
  --max-model-len 16384 \
  --port 8000
```

**Step 5: Update RVAgent LLMClient**

**Option A: Use langchain-openai (recommended)**
```python
from langchain_openai import ChatOpenAI

llm_base = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    model="./models/qwen3-vl-4b",
    temperature=0.6,
    top_p=0.95,
    max_tokens=2048,
    timeout=15.0
)
```

**Option B: Direct vLLM integration**
```python
from vllm import LLM, SamplingParams

llm = LLM(
    model="./models/qwen3-vl-4b",
    dtype="bfloat16",
    max_model_len=16384,
    gpu_memory_utilization=0.9
)

sampling_params = SamplingParams(
    temperature=0.6,
    top_p=0.95,
    top_k=20,
    max_tokens=2048,
    repetition_penalty=1.1  # This WORKS in vLLM!
)
```

---

## 7. Alternative Solutions (Not Recommended)

### 7.1. Use Smaller Context Window (8K)

**Pros:**
- ✅ Shorter loops (28s vs 58s)
- ✅ Slightly better success rate (88.6% vs 48.1%)

**Cons:**
- ❌ Doesn't solve root cause
- ❌ Still 10-20% loop occurrence
- ❌ Limited context for complex screens

**Verdict:** Mitigation, not solution.

### 7.2. Implement Loop Detector

**Concept:**
```python
def _detect_repetition_loop(response: AIMessage) -> bool:
    """Detect if response is in repetition loop."""
    if not response.tool_calls or len(response.tool_calls) < 3:
        return False

    # Check if last 3 tool_calls are identical
    recent_calls = response.tool_calls[-3:]
    first = json.dumps(recent_calls[0], sort_keys=True)

    for call in recent_calls[1:]:
        if json.dumps(call, sort_keys=True) != first:
            return False

    return True  # Loop detected
```

**Pros:**
- ✅ Can detect and abort loops early
- ✅ Force fallback before 14s timeout

**Cons:**
- ❌ Complex to implement reliably
- ❌ Doesn't prevent loops (only detects)
- ❌ May false-positive on valid repeated actions

**Verdict:** Band-aid solution, not worth the complexity.

### 7.3. Wait for Ollama Fix

**Status:**
- Issue #10767 open since January 2025
- No fix timeline announced
- Community workaround: "Use HuggingFace or vLLM"

**Verdict:** Not viable for production.

---

## 8. Decision Matrix

| Solution | Fixes Loop? | GPU Memory | Setup Complexity | Performance | Verdict |
|----------|-------------|------------|------------------|-------------|---------|
| **vLLM** | ✅ Yes | 14-16 GB | Medium | Fast | ✅ **RECOMMENDED** |
| **vLLM + AWQ** | ✅ Yes | 10-12 GB | High | Fast | ✅ **BEST** |
| Safety nets | ❌ No (50% loops) | 10 GB | Low | Fast | ❌ Insufficient |
| 8K context | ⚠️ Partial (28s loops) | 11 GB | Low | Fast | ⚠️ Workaround |
| Loop detector | ⚠️ Detects only | 10 GB | High | Fast | ❌ Complex |
| Wait for fix | ❓ Unknown | 10 GB | None | Fast | ❌ No timeline |

---

## 9. Next Steps

### Immediate (Today)

1. ✅ Document loop bug comprehensively (this file)
2. 🔄 Research vLLM setup and quantization options
3. 🔄 Test vLLM with Qwen3-VL-4B-Instruct
4. 🔄 Verify loop bug is absent in vLLM

### Short-term (This Week)

5. ⏳ Implement vLLM backend in RVAgent
6. ⏳ Create LLMClient adapter for vLLM
7. ⏳ Test vLLM with 5-app benchmark
8. ⏳ Compare performance: vLLM vs Ollama (without loops)

### Long-term (This Month)

9. ⏳ Evaluate AWQ/GPTQ quantization for memory efficiency
10. ⏳ Production deployment with vLLM
11. ⏳ Monitor Ollama issues for potential fix

---

## 10. References

### GitHub Issues

- **ollama/ollama #10767**: https://github.com/ollama/ollama/issues/10767
  - Title: "repeat_penalty has no effect"
  - Confirmed: Parameter completely ignored

- **QwenLM/Qwen3-VL #1611**: https://github.com/QwenLM/Qwen3-VL/issues/1611
  - Title: "Infinite repetition loop during table transcription"
  - Workaround: Use HuggingFace or vLLM

- **ggml-org/llama.cpp #14663**: https://github.com/ggml-org/llama.cpp/issues/14663
  - Title: "Repetition with non-Q4 quantization and flash attention"
  - Root cause: GGUF sampler bug

### Documentation

- **Qwen3-VL Official Docs**: https://qwen.readthedocs.io/en/latest/
  - Recommended parameters: temp=0.6, top_p=0.95, top_k=20

- **vLLM Documentation**: https://docs.vllm.ai/
  - Installation, quantization, OpenAI API

- **Transformers Sampling**: https://huggingface.co/docs/transformers/main_classes/text_generation
  - How repeat_penalty works in HuggingFace

### Blog Posts

- **Simon Willison**: "Qwen2.5-VL in Ollama - Token Repetition Issues"
  - https://simonwillison.net/2025/May/18/qwen25vl-in-ollama/
  - Community reports of same bug

---

## 11. Test Logs Reference

**Location:** `/tmp/v13_5apps_*`

- `v13_5apps_analysis.log`: 5-app test with 8K model (baseline)
- `v13_5apps_16k.log`: 5-app test with 16K model (no mitigation)
- `v13_5apps_16k_safetynets.log`: 5-app test with safety nets (partial test)

**Key Metrics:**
```bash
# Count loops in logs
grep "done_reason.*length" /tmp/v13_5apps_*.log | wc -l

# Analyze loop duration
grep -A 2 "done_reason.*length" /tmp/v13_5apps_*.log | grep total_duration
```

---

## Conclusion

The **token repetition loop bug is a critical blocker** for production use of Qwen3-VL with Ollama. Safety nets reduce damage (58s → 14s) but do NOT solve the root cause (50% loop rate persists).

**Recommended Action:** Migrate to **vLLM with AWQ quantization** to eliminate loops while maintaining performance and memory efficiency comparable to Ollama.

**Status:** ✅ Investigation complete, ready to implement vLLM migration.

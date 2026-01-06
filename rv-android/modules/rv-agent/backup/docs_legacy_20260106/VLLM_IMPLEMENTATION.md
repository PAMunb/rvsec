# vLLM Implementation Summary

## Changes Implemented

### 1. Core Files Modified

#### `agent_factory.py`
- **Import**: Changed from `langchain_ollama.ChatOllama` to `langchain_openai.ChatOpenAI`
- **LLM Client Creation**:
  - Base URL: `http://localhost:8000/v1` (vLLM server endpoint)
  - Model: `./models/qwen3-vl-4b-fp8`
  - Removed: `num_predict`, `num_ctx`, `request_timeout` (Ollama-specific parameters)
  - Added: `repetition_penalty=1.1` (prevents token repetition)
  - Kept: Qwen3-VL recommended parameters (temperature=0.6, top_p=0.95, top_k=20)

#### `pyproject.toml`
- Removed: `langchain-ollama`, `ollama`
- Added: `langchain-openai@^1.0.0`

### 2. Files Backed Up

Location: `backup/2025-11-14_vllm-migration/`
- `agent_factory.py.bak`
- `Modelfile.qwen3-vl-4b-16k`

### 3. vLLM Server Configuration

**Running Server**:
```bash
python -m vllm.entrypoints.openai.api_server \
  --model ./models/qwen3-vl-4b-fp8 \
  --quantization fp8 \
  --dtype float16 \
  --max-model-len 16384 \
  --max-num-seqs 4 \
  --gpu-memory-utilization 0.9 \
  --port 8000 \
  --host 0.0.0.0 \
  --trust-remote-code
```

**Model Details**:
- Model: Qwen/Qwen3-VL-4B-Instruct-FP8
- Size: 5.7 GB on disk
- GPU Memory: 5.2 GB during inference
- Context Window: 16,384 tokens
- Quantization: FP8 (block size 128)

**Performance**:
- Loading time: ~1.8 seconds
- Prompt throughput: 207.4 tokens/s
- Generation throughput: 3.1 tokens/s

### 4. Test Results

#### Quick Validation (`test_vllm_quick.py`)
```
✅ Text query: PASS (finish_reason='stop')
✅ Vision query: PASS (finish_reason='stop')
Loop rate: 0% (vs 50% with Ollama)
```

### 5. Architecture Notes

**LLM Client Flow**:
1. `AgentFactory._create_llm_client()` creates `ChatOpenAI` instance
2. Points to vLLM server at `http://localhost:8000/v1`
3. Binds Android tools for tool calling
4. Returns `LLMClient` with configured LLM

**Key Parameters**:
- `temperature=0.6`: Qwen3-VL official recommendation
- `top_p=0.95`: Diverse sampling (Qwen3-VL recommended)
- `top_k=20`: Candidate selection (Qwen3-VL recommended)
- `max_tokens=2048`: Maximum output tokens
- `repetition_penalty=1.1`: Prevents token loops (works with vLLM, ignored by Ollama)

### 6. Benefits vs Ollama

| Metric | Ollama GGUF | vLLM FP8 |
|--------|-------------|----------|
| Loop rate | 50% | 0% |
| Loop duration | 14-58s | N/A |
| Token repetition | Bug | Fixed |
| repeat_penalty | Ignored | Works |
| Model format | Q4_K_M (2.6 GB) | FP8 (5.7 GB) |
| GPU memory | Lower | 5.2 GB |
| Reliability | Unstable | Stable |

## Next Steps

### Testing
1. **Integration Test**: Run `test_vllm_rvagent_cryptoapp.py` with CryptoApp
2. **Validation**: Verify zero loop rate with real workflow
3. **Performance**: Compare exploration metrics with Ollama baseline

### Production Deployment
1. Create systemd service for vLLM server
2. Configure automatic startup on boot
3. Add health monitoring and restart policies
4. Update deployment documentation

## Technical References

### vLLM Documentation
- OpenAI-compatible API: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html
- Quantization guide: https://docs.vllm.ai/en/latest/quantization/

### Qwen3-VL
- Official repository: https://github.com/QwenLM/Qwen3-VL
- Recommended parameters: temperature=0.6, top_p=0.95, top_k=20

### Bug References
- Ollama issue #10767: Token repetition in vision models
- Qwen3-VL issue #1611: GGUF sampler bug
- llama.cpp issue #14663: repeat_penalty ignored

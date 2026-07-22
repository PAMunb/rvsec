# vLLM Tool Calling Migration - Problem Log

**Date**: 2025-11-14
**Context**: Migration from LangChain bind_tools() to vLLM native tool calling
**Goal**: Enable tool calling with vLLM server for Qwen3-VL-4B-FP8 model

---

## Problem History

### Initial Issue: bind_tools() 404 Errors

**Problem**: LangChain's `bind_tools()` method was returning 404 errors when used with vLLM server.

```python
# Original approach that failed
tools = create_android_tools()
llm_with_tools = llm_base.bind_tools(tools)
```

**Error logs**:
```
❌ HTTP error 404: 404 page not found
```

**Root Cause**: vLLM's OpenAI-compatible API doesn't support LangChain's `bind_tools()` method. The method tries to use an endpoint or format that vLLM doesn't implement.

---

## Migration Attempts

### Phase 1: vLLM Native Tool Calling with Hermes Parser

**Approach**: Use vLLM's built-in Hermes parser for native tool calling support.

**Implementation**:
1. Restarted vLLM server with Hermes parser flags:
   ```bash
   vllm serve ./models/qwen3-vl-4b-fp8 \
     --tool-call-parser hermes \
     --enable-auto-tool-choice \
     --port 8000
   ```

2. Created `get_tool_schemas()` in `android_tools.py`:
   ```python
   def get_tool_schemas():
       """Get OpenAI-compatible tool schemas for vLLM native tool calling."""
       return [
           {
               "type": "function",
               "function": {
                   "name": "android_click",
                   "description": "Click on buttons, images, checkboxes...",
                   "parameters": {
                       "type": "object",
                       "properties": {
                           "element_description": {"type": "string"},
                           "x": {"type": "integer"},
                           "y": {"type": "integer"}
                       },
                       "required": ["element_description", "x", "y"]
                   }
               }
           },
           # ... 6 more tools
       ]
   ```

3. Modified `llm_client.py` to use direct HTTP API:
   - Replaced LangChain's `invoke()` with `httpx.post()`
   - Added direct API request to `/v1/chat/completions`
   - Included tool schemas in request
   - Expected tool_calls in response JSON

**Test Results**:

Configuration issues found first:
1. **Error**: `apk_path` parameter not accepted by RVAgentConfig
   - **Fix**: Removed invalid parameter

2. **Error**: Wrong port configuration (11434 instead of 8000)
   - **Root Cause**: `get_langchain_config()` hardcoded Ollama port
   - **Fix**: Added `llm_base_url` optional field to RVAgentConfig
   - **Implementation**: Modified `get_langchain_config()` to check `llm_base_url` first

After configuration fixes, server connection succeeded but tool calling failed:

**Critical Errors**:

1. **AIMessage validation error**:
   ```
   ValidationError: 2 validation errors for AIMessage
   content.str
     Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
   ```
   - **Root Cause**: vLLM returned `content=None` when tool calls were present
   - **Impact**: AIMessage constructor failed, preventing action extraction

2. **Malformed tool calls in content**:
   ```
   🔍 FULL LLM RESPONSE (no tool calls):
   <tool_call>
   {"name": "android_click", "arguments": {"element_description": "Message Digest option in the dropdown menu", "x":": 704x1248 pixels
   ```
   - **Root Cause**: Tool calls appeared in `content` field with `<tool_call>` tags, not in `message.tool_calls` structure
   - **Impact**: Native tool call extraction failed completely

3. **Hermes Parser JSON Decode Errors** (from vLLM server logs):
   ```
   ERROR [hermes_tool_parser.py:157] Error in extracting tool call from response.
   json.decoder.JSONDecodeError: Invalid control character at: line 2 column 132 (char 132)
   ```
   ```
   ERROR [hermes_tool_parser.py:157] Error in extracting tool call from response.
   json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes: line 2 column 101 (char 101)
   ```

**Conclusion Phase 1**:
- **FAILED**: Qwen3-VL-4B-FP8 is NOT trained for Hermes-style tool calling
- The model generates malformed JSON that the Hermes parser cannot extract
- Native tool calling via Hermes parser is NOT viable with this model

---

### Phase 2: JSON Parser Approach (Current)

**Status**: BLOCKED - Format mismatch discovered

**Approach**:
- Remove Hermes parser from vLLM
- Use prompt engineering to request JSON responses
- Leverage existing JSON parser fallback mechanism

**Implementation Completed**:
1. ✅ Restarted vLLM without `--tool-call-parser hermes` flag (PID 779568)
2. ✅ Modified LLM client to NOT send tool schemas in request
3. ✅ Removed all native tool calling extraction code
4. ✅ Simplified to rely ONLY on `_parse_and_inject_tool_calls()` method

**Test Results (First Run - 2025-11-14 13:50)**:

Server working, LLM responding, but **JSON parser fails to extract actions**:

```
🔍 FULL LLM RESPONSE (no tool calls):
================================================================================
android_click(352, 177)
================================================================================

No native tool calls - attempting JSON/XML parsing...
❌ No tool calls found in response
No tool calls found in text either
⚠️  No tool calls found in response
```

**Root Cause Identified**:

The model generates actions in **simple Python function call format**:
```python
android_click(352, 177)
android_type_text("password")
```

But the JSON parser (`rv_agent.llm.tools.json_parser`) expects structured formats:
- **JSON format**: `{"name": "android_click", "arguments": {"x": 352, "y": 177}}`
- **XML format**: `<tool_call><name>android_click</name>...</tool_call>`

**Impact**: All LLM responses fall back to algorithm because parser cannot extract actions.

**Options to Resolve**:

**Option A**: Modify prompt to force JSON format output
- Add explicit JSON format requirement to system prompt
- Risk: May confuse vision model or reduce response quality
- Effort: Low (prompt change only)

**Option B**: Extend JSON parser to handle function call format
- Add regex to parse `function_name(arg1, arg2)` format
- Risk: Parsing ambiguity with complex arguments
- Effort: Medium (parser modification)

**Option C**: Return to Ollama (original working solution)
- vLLM tool calling not viable with Qwen3-VL
- Ollama has proven stable JSON parser integration
- Effort: None (revert changes)

**Advantages**:
- Model-agnostic approach (when formats match)
- No dependency on native tool calling support
- vLLM server running stably

**Trade-offs**:
- **CRITICAL**: Requires exact format match between LLM output and parser expectations
- Current prompts don't enforce JSON format strongly enough
- Need significant prompt engineering OR parser extension

---

## Key Learnings

1. **Not all models support native tool calling**: Even with vLLM's Hermes parser, models need to be specifically trained for tool calling format.

2. **Qwen3-VL limitations**: The Qwen3-VL-4B-FP8 model generates tool calls in an incompatible format that Hermes parser cannot extract.

3. **Configuration complexity**: vLLM integration requires careful port management and configuration parameter mapping.

4. **Fallback mechanisms are essential**: Having a JSON parser fallback proves valuable when native approaches fail.

---

## Configuration Changes Made

### RVAgentConfig (`modules/rv-agent/src/rv_agent/config/agent_config.py`)

Added optional `llm_base_url` field:
```python
llm_base_url: Optional[str] = Field(
    default=None,
    description="Optional custom base URL for LLM API (e.g., 'http://localhost:8000/v1' for vLLM)"
)
```

Modified `get_langchain_config()`:
```python
# Use custom base_url if provided, otherwise use provider defaults
if self.llm_base_url:
    config["base_url"] = self.llm_base_url
elif self.llm_provider == "ollama":
    config["base_url"] = "http://localhost:11434"
```

### LLMClient (`modules/rv-agent/src/rv_agent/llm/llm_client.py`)

Added direct HTTP API implementation:
- Initialized HTTP client and tool schemas in `__init__`
- Replaced LangChain invoke with `httpx.post()` to `/v1/chat/completions`
- Added `_convert_messages_to_openai_format()` helper
- Attempted to extract tool_calls from vLLM JSON response

### AndroidTools (`modules/rv-agent/src/rv_agent/llm/tools/android_tools.py`)

Added `get_tool_schemas()` function for OpenAI-compatible tool definitions.

---

## Next Steps

1. **Complete Phase 2 implementation**:
   - Start vLLM without Hermes parser
   - Test JSON parser approach with existing fallback
   - Validate action extraction works

2. **Prompt engineering** (if needed):
   - Modify prompts to explicitly request JSON format
   - Test prompt variations for optimal JSON generation

3. **Performance validation**:
   - Compare JSON parser success rate vs. original Ollama
   - Measure latency impact of vLLM vs. Ollama
   - Verify tool call accuracy

4. **Alternative considerations**:
   - Test with different vLLM tool parsers (if available)
   - Consider using Ollama with vLLM model (if supported)
   - Evaluate fine-tuning model for Hermes format (long-term)

---

## Server Configurations Tested

### Hermes Parser (Failed)
```bash
vllm serve ./models/qwen3-vl-4b-fp8 \
  --quantization fp8 \
  --dtype float16 \
  --max-model-len 16384 \
  --max-num-seqs 4 \
  --gpu-memory-utilization 0.9 \
  --port 8000 \
  --host 0.0.0.0 \
  --trust-remote-code \
  --tool-call-parser hermes \
  --enable-auto-tool-choice
```

### JSON Mode (Current)
```bash
vllm serve ./models/qwen3-vl-4b-fp8 \
  --quantization fp8 \
  --dtype float16 \
  --max-model-len 16384 \
  --max-num-seqs 4 \
  --gpu-memory-utilization 0.9 \
  --port 8000 \
  --host 0.0.0.0 \
  --trust-remote-code
```

---

## References

- vLLM documentation: https://docs.vllm.ai/
- OpenAI tool calling format: https://platform.openai.com/docs/guides/function-calling
- LangChain bind_tools: https://python.langchain.com/docs/how_to/tool_calling/

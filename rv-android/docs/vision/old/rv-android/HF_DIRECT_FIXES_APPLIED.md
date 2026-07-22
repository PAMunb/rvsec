# HuggingFace Transformers Direct - Fixes Applied

## Issues Fixed

### 1. Action Format Key Mismatch ✅
**Problem**: LLMClient was creating action dict with `action_type` key, but ToolExecutor expected `tool_name` key for LLM format.

**Files Changed**:
- `/rv_agent/llm/llm_client.py` (line 280, 711)

**Changes**:
```python
# BEFORE (wrong)
action = {
    'action_type': first_tool.get('name'),  # ← Wrong key!
    'tool_args': first_tool.get('args', {}),
    'tool_id': first_tool.get('id')
}

# AFTER (correct)
action = {
    'tool_name': first_tool.get('name'),  # ← Correct key for LLM format
    'tool_args': first_tool.get('args', {}),
    'tool_id': first_tool.get('id')
}
```

**Impact**: ToolExecutor now correctly maps `android_click` → `CLICK`, etc.

### 2. String Coordinate Conversion ✅
**Problem**: LLM sometimes generates `{"x": "681", "y": "777"}` (strings) instead of integers.

**Files Changed**:
- `/rv_agent/llm/tools/json_parser.py` (lines 22-45, 127-131)

**Changes Added**:
1. New function `_normalize_tool_args()` that converts string coordinates to integers
2. Applied normalization when parsing XML tool calls

```python
def _normalize_tool_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize tool arguments by converting string numbers to integers."""
    normalized = {}
    for key, value in args.items():
        if key in ('x', 'y') and isinstance(value, str):
            try:
                normalized[key] = int(value)
            except ValueError:
                normalized[key] = value
        else:
            normalized[key] = value
    return normalized
```

**Impact**: Coordinates are now properly converted to integers before execution.

## Expected Improvements

### Before Fixes:
- Parser successes: 9/14 iterations (64%)
- Action executions: **0/9** (all failed due to format mismatch)
- LLM fallbacks: ~100% (due to execution failures)

### After Fixes (Expected):
- Parser successes: 9/14 iterations (unchanged)
- Action executions: **9/9** (100% success for parsed actions)
- LLM fallbacks: Reduced to ~35% (only when parser fails)

## Remaining Issues

### JSON Malformation (Model-side)
Some iterations still have malformed JSON:
- Missing keys: `{"x": 352, 177}`
- Extra chars: `{"x":": 750, "y": 80}`

This is a model generation issue that may need:
- Better prompt engineering
- Temperature adjustment
- Post-processing JSON repair

## Next Steps

1. ✅ **Re-test with CryptoApp** using HF Direct backend
2. 📊 **Compare results**:
   - Execution success rate
   - LLM vs Algorithm ratio
   - Screen coverage
3. 🔍 **Analyze JSON malformation** patterns to add repair logic if needed
4. ⚙️ **Benchmark vs vLLM** for performance comparison

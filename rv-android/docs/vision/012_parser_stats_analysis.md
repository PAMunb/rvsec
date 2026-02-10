# Parser Statistics Analysis

**Date**: 2025-12-27
**Model**: Qwen3-VL-4B-Instruct (SGLang)
**Mode**: visual_only

---

## Summary

This analysis investigates parsing failures and identifies patterns in malformed JSON output from the vision LLM.

---

## Parser Statistics

| Metric | Value |
|--------|-------|
| Total calls | 71 |
| Successful parses | 46 |
| Failed parses | 25 |
| **Success rate** | **64.8%** |

### Strategy Used

All successful parses used the `xml_tool_call` strategy:
- Model wraps tool calls in `<tool_call>...</tool_call>` tags
- JSON content inside the tags requires parsing

### Failure Reasons

All 25 failures were `parse_failed` - the model attempted to call tools but produced malformed JSON.

---

## Malformed JSON Patterns Identified

### Pattern 1: Double Colon

```json
"x":": 541, "y": 562
```

Model outputs `:":` instead of just `:` for coordinate values.

**Fix applied**: Regex to normalize `"x":": N` to `"x": N`

### Pattern 2: Trailing Quote on Integer

```json
"y": 473", "element_description": ...
```

Model outputs integer followed by errant quote (not a string, just trailing quote).

**Fix applied**: Regex to remove trailing quote from `"y": N"` pattern.

### Pattern 3: Missing Leading Zero on Float

```json
"x": .91
```

Qwen3-VL sometimes omits leading zero on normalized coordinates.

**Fix already existed**: Converts `.91` to `0.91`.

---

## Code Fix Applied

Updated `src/parsers/tool_call_parser.py` `_fix_malformed_json()` function:

```python
# Pattern 0b: Fix double colon: "x":": 541 -> "x": 541
s = re.sub(r'"([xy])":\s*"?:\s*(\d+)', r'"\1": \2', s)

# Pattern 0c: Fix numeric value with trailing quote only: "y": 473" -> "y": 473
s = re.sub(r'"([xy])":\s*(\d+)"(\s*[,}])', r'"\1": \2\3', s)
```

### Test Results

| Test Case | Before Fix | After Fix |
|-----------|------------|-----------|
| `"x":": 541` | INVALID | VALID |
| `"y": 473"` | INVALID | VALID |
| Normal JSON | VALID | VALID (unchanged) |

---

## Impact Analysis

### Before Fix

- 25 parse failures out of 71 calls (35.2% failure rate)
- All failures were due to malformed JSON patterns
- Loss of ~35% of valid tool calls

### Expected After Fix

- Most double-colon and trailing-quote failures should be recovered
- Expected improvement: 10-20 additional successful parses
- Estimated new success rate: 85-95%

---

## Root Cause

The model (Qwen3-VL-4B-Instruct) occasionally produces JSON with formatting errors:

1. **Tokenization artifacts**: The `:":` pattern suggests the model is emitting colon tokens incorrectly
2. **String/number confusion**: The `N"` pattern (integer followed by quote) suggests confusion between string and integer output
3. **Consistent format**: Model consistently uses `<tool_call>` XML format, but JSON inside is sometimes malformed

---

## Recommendations

1. **Keep JSON fix patterns updated**: As new malformation patterns are discovered, add corresponding fixes
2. **Consider temperature**: Lower temperature (0.01) may reduce formatting errors
3. **Monitor parser stats**: Track success rate over time to identify regression or new patterns
4. **Model comparison**: Compare parser success rates across different models (Gemma, Fara, MiniCPM-V)

---

## Files Modified

- `src/parsers/tool_call_parser.py`: Added new JSON fix patterns

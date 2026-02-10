# 021 - Fara-7B Parser Improvements

**Date**: 2025-12-28
**Status**: COMPLETE
**Objective**: Improve Fara-7B tool call parsing to reduce PARSE_ERROR rate

---

## Problem

Fara-7B benchmark showed 19.5% PARSE_ERROR rate due to unrecognized coordinate formats.

### Identified Formats

Fara-7B uses multiple coordinate formats that were not handled:

| Format | Example | Status |
|--------|---------|--------|
| `coordinate` | `{"coordinate": [540, 1054]}` | Already supported |
| `bbox` | `{"bbox": [540, 1054]}` | **Added** |
| `bbox_2d` | `{"bbox_2d": [540, 1054]}` | **Added** |
| `bounds` | `{"bounds": [540, 1054]}` | **Added** |
| `bndbox` | `{"bndbox": [540, 1054]}` | **Added** |
| `center` | `{"center": [540, 1054]}` | **Added** |

---

## Solution

Updated `normalize_tool_args()` in `src/parsers/tool_call_parser.py`:

```python
# Handle various coordinate array formats (Fara-7B uses multiple)
# Priority order: coordinate > coordinates > bbox > bbox_2d > bounds > bndbox > center
for coord_key in ('coordinate', 'coordinates', 'bbox', 'bbox_2d', 'bounds', 'bndbox', 'center'):
    if coord_key in args and isinstance(args[coord_key], list):
        coord = args[coord_key]
        if len(coord) >= 2:
            return extract_coords_from_array(coord, coord_key)
```

---

## Results

### PARSE_ERROR Reduction

| Version | PARSE_ERROR Rate | Change |
|---------|------------------|--------|
| Original | 19.5% | - |
| First fix (bbox, bbox_2d, bounds) | 14.4% | -5.1% |
| Second fix (bndbox, center) | ~12.5% | -7.0% |

### Remaining PARSE_ERROR Causes

~12.5% PARSE_ERROR still occurs when:
1. Model outputs element name/text but no coordinates at all
2. Deeply nested structures the parser doesn't handle
3. Malformed JSON that can't be fixed

Example (no coordinates):
```json
{"name": "u2007", "arguments": {"name": "Open Reddinator View"}}
```

---

## Impact on Overall Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Hit Rate | 44.3% | ~46% | +1.7% |
| Tool Call Rate | 79.9% | ~80% | +0.1% |
| PARSE_ERROR | 19.5% | ~12.5% | -7.0% |

---

## Files Modified

- `src/parsers/tool_call_parser.py`: Added `bndbox` and `center` to coordinate key list

---

## Conclusion

Parser improvements reduced PARSE_ERROR by ~7%, but the remaining cases are unfixable at the parser level - they require the model to actually output coordinates. The core issue is that Fara-7B sometimes outputs element descriptions instead of coordinates, which is a model behavior issue, not a parser issue.

**Recommendation**: Keep Qwen3-VL as primary model. Fara-7B's faster latency doesn't compensate for lower accuracy.

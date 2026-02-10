# Prompt and Parser Fixes for Multi-Model Support

**Date**: 2025-12-27
**Models Affected**: Fara-7B, and potentially other vision models
**Issue**: Low hit rate due to models returning element IDs instead of coordinates

---

## Problem Description

During Fara-7B testing, we discovered that the model would sometimes return element identifiers instead of pixel coordinates:

```json
// Expected (correct)
{"name": "android_click", "arguments": {"x": 540, "y": 1056}}

// Actual (incorrect - no coordinates)
{"name": "android_click", "arguments": {"id": "ImageView 'Search'"}}
{"name": "android_click", "arguments": {"name": "Downloads"}}
```

This caused the evaluator to report `predicted_x=None, predicted_y=None`, resulting in missed hits even when the model correctly identified the element.

---

## Root Cause Analysis

1. **Model Training**: Fara-7B was trained to use element IDs as a fallback when it cannot determine precise coordinates
2. **Prompt Ambiguity**: The original prompts didn't explicitly require numeric pixel coordinates
3. **Tool Definitions**: Lacked explicit coordinate range and format requirements

---

## Fixes Applied

### 1. System Prompt Update (`evaluator.py`)

**Before:**
```python
SYSTEM_PROMPT_VISUAL = """You are an Android UI automation assistant.

The screen image has dimensions {width}x{height} pixels.

When asked to click on an element, you MUST:
1. Look at the screenshot and find the element visually
2. Determine its coordinates by analyzing the image
3. Use the android_click tool with the coordinates you found

You must locate elements by their visual appearance, not by provided coordinates."""
```

**After:**
```python
SYSTEM_PROMPT_VISUAL = """You are an Android UI automation assistant.

The screen image has dimensions {width}x{height} pixels.

When asked to click on an element, you MUST:
1. Look at the screenshot and find the element visually
2. Determine its EXACT PIXEL coordinates (x, y) by analyzing the image
3. Use the android_click tool with x and y parameters

CRITICAL: You MUST always provide numeric x,y pixel coordinates. Never use element IDs or names.
The x coordinate must be between 0 and {width}, y between 0 and {height}."""
```

**Key Changes:**
- Added "EXACT PIXEL coordinates"
- Added "CRITICAL" instruction forbidding element IDs
- Specified valid coordinate ranges

### 2. Tool Definitions Update (`android_tools.py`)

**Before:**
```python
{
    "name": "android_click",
    "description": "Click on a UI element at the specified coordinates...",
    "parameters": {
        "properties": {
            "x": {
                "type": "integer",
                "description": "X coordinate of the click position (horizontal, from left edge)"
            },
            "y": {
                "type": "integer",
                "description": "Y coordinate of the click position (vertical, from top edge)"
            },
            ...
        }
    }
}
```

**After:**
```python
{
    "name": "android_click",
    "description": "Click on a UI element at the specified pixel coordinates. You MUST provide exact numeric x,y coordinates. Screen is 1080x1920 pixels.",
    "parameters": {
        "properties": {
            "x": {
                "type": "integer",
                "description": "X pixel coordinate (0-1080, horizontal position from left edge). REQUIRED: must be a number."
            },
            "y": {
                "type": "integer",
                "description": "Y pixel coordinate (0-1920, vertical position from top edge). REQUIRED: must be a number."
            },
            ...
        }
    }
}
```

**Key Changes:**
- Added pixel ranges (0-1080, 0-1920)
- Added "REQUIRED: must be a number"
- Emphasized "exact numeric x,y coordinates" in description

### 3. Parser JSON Fixes (`tool_call_parser.py`)

Added new patterns to `_fix_malformed_json()`:

```python
# Pattern 0b: Fix double colon: "x":": 541 -> "x": 541
# Qwen3-VL sometimes outputs ":": instead of ":"
s = re.sub(r'"([xy])":\s*"?:\s*(\d+)', r'"\1": \2', s)

# Pattern 0c: Fix numeric value with trailing quote: "y": 473" -> "y": 473
# Model outputs integer followed by errant quote
s = re.sub(r'"([xy])":\s*(\d+)"(\s*[,}])', r'"\1": \2\3', s)
```

**Malformed JSON Examples Fixed:**
| Input | Output |
|-------|--------|
| `"x":": 541` | `"x": 541` |
| `"y": 473"` | `"y": 473` |

### 4. Evaluator Multi-Tool Support (`evaluator.py`)

**Before:**
```python
if tool_called and tool_name == "android_click":
    # Extract coordinates...
```

**After:**
```python
# Accept any tool that has x,y coordinates as a click action
CLICK_TOOL_NAMES = {"android_click", "u2009", "tap", "click", "left_click"}
is_click_tool = tool_called and (
    tool_name in CLICK_TOOL_NAMES
    or (tool_name and "click" in tool_name.lower())
)

if is_click_tool:
    # Extract coordinates...
```

**Reason:** Fara-7B sometimes uses non-standard tool names like `u2009` (Unicode thin space character) instead of `android_click`.

---

## Results

### Before Fixes (Fara-7B)
| Metric | Value |
|--------|-------|
| Hit Rate | 23.5% |
| Coordinate Rate | 68.2% |

### After Fixes (Fara-7B)
| Metric | Value |
|--------|-------|
| Hit Rate | **31.8%** |
| Coordinate Rate | **86.4%** |

**Improvement:** +8.3% hit rate, +18.2% coordinate rate

---

## Model-Specific Behaviors

### Qwen3-VL-4B-Instruct
- Uses `<tool_call>` XML format
- Returns coordinates in [0, 1000) normalized range
- Tool name: `android_click`

### Fara-7B (Microsoft)
- Uses `<tool_call>` XML format
- Returns pixel coordinates directly (0-1080, 0-1920)
- Tool names: `android_click`, `u2009`, or custom names
- Fallback: May use `{"id": "..."}` or `{"name": "..."}` instead of coordinates

### Coordinate Handling

**IMPORTANT**: Coordinate conversion is model-specific:

| Model | Coordinate Format | Conversion |
|-------|-------------------|------------|
| Qwen3-VL | Normalized [0, 1000) | `denormalize_qwen_coords()` |
| MiniCPM-V-4_5 | Normalized [0, 1000) | `denormalize_qwen_coords()` |
| Fara-7B | Pixel coordinates directly | None (use as-is) |

**Note**: Both Qwen3-VL and MiniCPM-V use the same [0, 1000) normalized coordinate system.
The evaluator checks for "qwen" or "minicpm" in the model name to apply conversion.

The evaluator checks the model name to determine if conversion is needed:

```python
# In evaluator.py
model_lower = self.config.model.lower()
uses_normalized_coords = "qwen" in model_lower or "minicpm" in model_lower

if uses_normalized_coords and grounding_mode in (VISUAL_ONLY, DESCRIPTION_ONLY):
    predicted_x, predicted_y = denormalize_qwen_coords(raw_x, raw_y, ...)
else:
    # Fara-7B, etc. return pixel coordinates directly
    predicted_x, predicted_y = raw_x, raw_y
```

Examples:
- Qwen3-VL: `(499, 547)` → converted to `(539, 1050)` via `denormalize_qwen_coords()`
- MiniCPM-V: `(495, 547)` → converted to `(534, 1050)` via `denormalize_qwen_coords()`
- Fara-7B: `(764, 136)` → used directly as `(764, 136)`

---

## Files Modified

| File | Changes |
|------|---------|
| `src/evaluator/evaluator.py` | Updated SYSTEM_PROMPT_VISUAL, added multi-tool support |
| `src/tools/android_tools.py` | Updated tool descriptions with pixel ranges |
| `src/parsers/tool_call_parser.py` | Added JSON fix patterns for malformed output |

---

## Testing

To verify fixes work correctly:

```bash
# Quick validation (5 screenshots)
poetry run python3 -c "
import asyncio
from pathlib import Path
from src.evaluator.evaluator import LLMEvaluator, EvaluationConfig, GroundingMode

async def test():
    config = EvaluationConfig(
        model='microsoft/Fara-7B',
        server_url='http://localhost:8000',
        temperature=0.01,
        top_p=0.6,
        top_k=50,
        max_screenshots=5,
        max_elements_per_screenshot=10,
        repetitions_per_element=1,
        grounding_mode=GroundingMode.VISUAL_ONLY,
    )
    evaluator = LLMEvaluator(config)
    run = await evaluator.run_evaluation(screenshots_dir=Path('screenshots'))
    print(f'Hit rate: {run.overall_hit_rate:.1%}')
    print(f'Tool call rate: {run.overall_tool_call_rate:.1%}')

asyncio.run(test())
"
```

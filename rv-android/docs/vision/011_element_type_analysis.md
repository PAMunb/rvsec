# Element Type Analysis Report

**Date**: 2025-12-27
**Model**: Qwen3-VL-4B-Instruct (SGLang)
**Mode**: visual_only
**Config**: temp=0.01, top_p=0.6, top_k=50

---

## Summary

This analysis investigates which UI element types the vision LLM has difficulty locating visually. The extended_sweep benchmark showed a ~41% overall hit rate, and this analysis breaks down performance by element class.

---

## Element Type Performance

| Rank | Element Class | Tests | Hits | Hit Rate | Tool Call | Avg Dist |
|------|--------------|-------|------|----------|-----------|----------|
| 1 | LinearLayout | 74 | 4 | **5.4%** | 91.9% | 5.7px |
| 2 | RelativeLayout | 38 | 3 | **7.9%** | 84.2% | 9.3px |
| 3 | CheckBox | 107 | 24 | **22.4%** | 97.2% | 25.1px |
| 4 | ImageButton | 37 | 18 | 48.6% | 100.0% | 3.4px |
| 5 | View | 12 | 6 | 50.0% | 100.0% | 7.9px |
| 6 | TextView | 117 | 63 | 53.8% | 94.0% | 5.0px |
| 7 | SeekBar | 12 | 7 | 58.3% | 100.0% | 10.4px |
| 8 | ImageView | 8 | 5 | 62.5% | 100.0% | 4.2px |
| 9 | Spinner | 11 | 7 | 63.6% | 100.0% | 24.7px |
| 10 | CheckedTextView | 30 | 22 | 73.3% | 93.3% | 4.7px |
| 11 | Button | 40 | 38 | **95.0%** | 97.5% | 4.4px |
| 12 | EditText | 9 | 9 | **100.0%** | 100.0% | 8.7px |

---

## Key Findings

### 1. Layout Containers Are Invisible (Expected Failures)

**LinearLayout (5.4%) and RelativeLayout (7.9%)** have extremely low hit rates because:
- They are **invisible container elements** with no visual representation
- The model cannot "see" them in the screenshot
- They are only defined in the UIAutomator XML hierarchy
- **Recommendation**: Exclude Layout containers from visual grounding evaluation

### 2. CheckBox Has Unexpectedly Low Performance (22.4%)

Despite being a visible widget, CheckBox performance is poor:
- 107 tests, only 24 hits (22.4%)
- When it hits, distance is poor (25.1px average)
- **Possible causes**:
  - Small visual footprint (square icon)
  - Visual similarity to other small icons
  - May be confused with the adjacent text label

### 3. Button and EditText Excel (95-100%)

These elements have clear visual characteristics:
- **Button (95%)**: Well-defined borders, text labels, distinct styling
- **EditText (100%)**: Clear input field boundaries
- **Conclusion**: Elements with strong visual identity are easy to locate

### 4. When It Hits, It's Precise

For most element types, avg_distance is under 10px when the model successfully locates the element. This indicates:
- The vision grounding is precise when successful
- The issue is finding the correct element, not coordinate precision

---

## Adjusted Hit Rate (Excluding Layouts)

If we exclude invisible Layout containers from the evaluation:

| Metric | With Layouts | Without Layouts |
|--------|--------------|-----------------|
| Total Tests | 495 | 383 |
| Total Hits | 206 | 199 |
| Hit Rate | 41.6% | **52.0%** |

This provides a more realistic view of visual grounding capability on **visible** UI elements.

---

## Parser Statistics

| Metric | Value |
|--------|-------|
| Total calls | 71 |
| Successful parses | 46 |
| Failed parses | 25 |
| Success rate | 64.8% |

**Strategy used**: All successful parses used `xml_tool_call` strategy

**Failure reasons**: 25 `parse_failed` (model output didn't match expected format)

---

## Recommendations

### For Evaluation Methodology

1. **Exclude Layout containers** from visual grounding benchmarks (LinearLayout, RelativeLayout, FrameLayout, etc.)
2. **Weight by element visibility**: Elements should have visual representation to be included
3. **Focus on interactive widgets**: Button, EditText, CheckBox, TextView, ImageButton

### For Model Improvement

1. **Improve CheckBox detection**: Add training examples with checkboxes
2. **Handle small elements**: CheckBox, radio buttons, toggle switches need attention
3. **Visual distinctiveness**: Elements with clear boundaries perform better

### For RVAgent Integration

1. **Filter element types**: Exclude invisible containers from click targets
2. **Fallback strategy**: For low-performing elements, consider coordinate-based approach
3. **Confidence threshold**: Use higher threshold for element types with lower hit rates

---

## Files

- **Analysis script**: `scripts/analyze_element_types.py`
- **Raw results**: `results/element_type_analysis_20251227_111846.json`

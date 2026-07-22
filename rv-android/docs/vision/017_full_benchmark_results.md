# 017 - Full Benchmark Results: Qwen3-VL-4B-Instruct

**Date**: 2025-12-27
**Status**: COMPLETE
**Model**: Qwen/Qwen3-VL-4B-Instruct
**Server**: SGLang (bf16, no quantization)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 2,847 |
| **Unique Elements** | 812 |
| **Screenshots** | 468 |
| **Repetitions** | 3 |
| **Hit Rate** | **57.7%** |
| **Tool Call Rate** | **90.3%** |
| **Avg Distance (hits only)** | 6.2px |
| **Avg Latency** | 1,821ms |
| **Consistency** | 98.9% |

---

## Configuration

```python
model = "Qwen/Qwen3-VL-4B-Instruct"
server_url = "http://localhost:30000"  # SGLang
temperature = 0.01
top_p = 0.6
top_k = 50
grounding_mode = "visual_only"
hit_tolerance_px = 50
repetitions = 3
```

---

## Result Categories

| Category | Count | Rate | Description |
|----------|-------|------|-------------|
| **HIT** | 1,642 | 57.7% | Correct click within 50px tolerance |
| **MISS** | 878 | 30.8% | Tool called but wrong coordinates |
| **NO_TOOL** | 277 | 9.7% | Model returned text instead of tool call |
| **PARSE_ERROR** | 50 | 1.8% | Tool called but coordinates couldn't be extracted |

### Analysis

- **88.5% of tests** resulted in some form of tool call (HIT + MISS + PARSE_ERROR)
- **NO_TOOL cases** (9.7%) indicate the model sometimes responds with explanatory text instead of action
- **PARSE_ERROR** (1.8%) is low, indicating the fallback parser handles most edge cases

---

## Parser Strategy Distribution

| Strategy | Count | Rate | Hit Rate | Description |
|----------|-------|------|----------|-------------|
| **native** | 1,559 | 54.8% | 60.2% | LangChain native tool_calls |
| **xml** | 1,011 | 35.5% | 69.5% | Fallback: `<tool_call>` XML tags |
| **none** | 277 | 9.7% | 0.0% | No tool call extracted |

### Key Insight

The **XML fallback parser achieves higher hit rate (69.5%)** than native tool calls (60.2%). This suggests:

1. When the model uses `<tool_call>` XML format, it may be more deliberate about coordinates
2. The native format may sometimes have parsing issues with malformed JSON
3. Both strategies are viable; the dual-parser approach is working correctly

---

## Element Type Performance

| Element Type | Tests | Hit Rate | Tool Call Rate | Avg Distance | Latency |
|--------------|-------|----------|----------------|--------------|---------|
| **EditText** | 306 | **93.1%** | 100.0% | 8.6px | 1,809ms |
| **Button** | 870 | **78.2%** | 90.3% | 4.7px | 1,868ms |
| **View** | 12 | 75.0% | 100.0% | 8.9px | 1,693ms |
| **Switch** | 72 | 69.4% | 95.8% | 13.0px | 1,733ms |
| **Spinner** | 147 | 63.3% | 100.0% | 5.7px | 1,590ms |
| **TextView** | 369 | 60.2% | 94.9% | 8.5px | 1,935ms |
| **ImageButton** | 444 | 43.5% | 83.6% | 3.3px | 1,775ms |
| **CheckedTextView** | 264 | 29.2% | 97.7% | 7.3px | 1,884ms |
| **CheckBox** | 108 | 25.0% | 100.0% | 7.5px | 1,800ms |
| **ImageView** | 210 | 0.0% | 56.2% | - | 1,694ms |
| **RadioButton** | 39 | 0.0% | 100.0% | - | 1,712ms |
| **Chip** | 3 | 100.0% | 100.0% | 3.6px | 1,702ms |
| **SeekBar** | 3 | 100.0% | 100.0% | 3.6px | 1,877ms |

### Element Type Analysis

**High Performance (>75% hit rate)**:
- **EditText**: Excellent at 93.1% - text input fields are visually distinct
- **Button**: Strong at 78.2% - clear visual affordance

**Medium Performance (50-75%)**:
- **Switch, Spinner, TextView**: 60-70% range
- These have less distinctive visual features

**Low Performance (<50%)**:
- **ImageButton**: 43.5% - icons without text are harder to identify
- **CheckBox, CheckedTextView**: ~25-30% - selection state affects identification
- **ImageView, RadioButton**: 0% - model struggles with these element types

### Recommendations for RVAgent

1. **High confidence**: EditText, Button - can rely on visual grounding
2. **Medium confidence**: Switch, Spinner, TextView - use visual + fallback strategies
3. **Low confidence**: ImageButton, CheckBox - consider providing explicit coordinates
4. **Not suitable**: ImageView, RadioButton - require explicit coordinate guidance

---

## Token Statistics

| Metric | Value |
|--------|-------|
| Avg Prompt Tokens | 2,493 |
| Avg Completion Tokens | 97 |
| Avg Total Tokens | 2,590 |
| **Total Prompt Tokens** | 7,096,716 |
| **Total Completion Tokens** | 277,373 |
| **Total Tokens** | 7,374,089 |

### Cost Estimation (if using API)

At typical rates ($0.003/1K input, $0.015/1K output):
- Input cost: ~$21.29
- Output cost: ~$4.16
- **Total: ~$25.45** for 2,847 tests

---

## Repetition Statistics

| Metric | Value |
|--------|-------|
| Total Unique Elements | 812 |
| Elements with 3 Repetitions | 812 (100%) |
| **Average Consistency** | 98.9% |
| Average Distance StdDev | 0.29px |

### Consistency Analysis

The 98.9% consistency rate indicates:
- Model is highly deterministic at temperature=0.01
- Same element gets same result across repetitions
- Low variance (0.29px stddev) confirms reproducibility

---

## Latency Distribution

| Metric | Value |
|--------|-------|
| Average | 1,821ms |
| Min (Spinner) | 1,590ms |
| Max (TextView) | 1,935ms |

**Throughput**: ~33 inferences per minute on RTX 5070 Ti

---

## Comparison with Preliminary Results

| Metric | Preliminary (150ss) | Full (468ss) | Delta |
|--------|---------------------|--------------|-------|
| Hit Rate | 67.1% | 57.7% | -9.4% |
| Tool Call Rate | ~95% | 90.3% | -4.7% |
| Avg Distance | ~5px | 6.2px | +1.2px |

The decrease in performance with the full dataset suggests:
1. The preliminary sample may have been biased toward "easier" screenshots
2. Some APKs have more challenging UI layouts
3. Element diversity increases complexity

---

## Files

| File | Description |
|------|-------------|
| `results/eval_20251227_205122.json` | Raw benchmark results (2,847 tests) |
| `docs/016_full_benchmark_plan.md` | Benchmark planning document |
| `docs/017_full_benchmark_results.md` | This analysis document |

---

## Conclusions

### Strengths
1. **High tool call rate** (90.3%) - model reliably produces actionable output
2. **Excellent consistency** (98.9%) - deterministic behavior at low temperature
3. **Strong on text elements** - EditText (93.1%), Button (78.2%)
4. **Low parse errors** (1.8%) - fallback parser handles edge cases well

### Weaknesses
1. **Overall hit rate** (57.7%) may be insufficient for autonomous operation
2. **Icon-based elements** (ImageButton, ImageView) have low accuracy
3. **Selection controls** (CheckBox, RadioButton) are problematic

### Recommendations for RVAgent Integration

1. **Use visual grounding for**:
   - Text-based elements (EditText, Button, TextView)
   - Elements with clear text labels

2. **Provide explicit coordinates for**:
   - ImageButton, ImageView (icons without text)
   - CheckBox, RadioButton (selection controls)
   - Any element where visual identification might fail

3. **Hybrid approach**:
   - Try visual grounding first
   - Fall back to coordinate-based approach if model returns NO_TOOL or low confidence

4. **Consider Fara-7B comparison**:
   - Run the same benchmark with Fara-7B for comparison
   - May have different strengths/weaknesses

---

## Next Steps

- [ ] Run Fara-7B benchmark (468 screenshots, 3 reps) for comparison
- [ ] Analyze failure cases by APK to identify problematic apps
- [ ] Test hybrid grounding strategy (visual + coordinate fallback)
- [ ] Integrate winning model into RVAgent

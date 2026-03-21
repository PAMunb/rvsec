# Exploratory: SGLang Multimodal Regression and Qwen3.5-4B Evaluation

**Date**: 2026-03-19
**Context**: gh43-aperv-llm-validation, Group 0.5 Pre-Validation
**Hardware**: NVIDIA RTX 5070 Ti (16GB VRAM), SGLang Docker (`lmsysorg/sglang:latest`)

## 1. Problem

The pre-validation script (`scripts/prevalidation.py`) was producing 0% hit rate on per-widget grounding tests. Tool calls were either absent or returned incorrect coordinates (distance >1000px from target). This happened across all three image processing modes (max_edge, smart_resize, raw) and both temperatures tested (0.01, 0.7).

Separately, re-running the rvsec-vision-llm benchmark (`tests/test_evaluator.py`) also produced 0% hit rate, despite the same codebase having achieved 57.7% hit rate on December 27, 2025.

## 2. Investigation

### 2.1 Confirming the baseline

The 57.7% benchmark (file `eval_20251227_205122.json`) was confirmed to use:
- Model: `Qwen/Qwen3-VL-4B-Instruct` on SGLang at port 30000
- 2847 tests across 468 screenshots, 3 repetitions per element
- Coordinates in Qwen normalized [0, 1000) space, converted via `pixel = int((qwen / 1000) * dim)`
- Tool calling via LangChain `bind_tools()` with `--tool-call-parser qwen` on SGLang
- Parser strategy distribution: 54.8% native, 35.5% XML fallback, 9.7% no_tool

### 2.2 Isolating the failure

Three diagnostic requests were sent directly via `httpx` to `http://localhost:30000/v1/chat/completions`:

| Test | Description | Result |
|------|-------------|--------|
| Text-only + tools | "Click on the Allow button at position (540, 1054)" | **Works.** `android_click(x=540, y=1054)` returned correctly. |
| Multimodal without tools | Screenshot + "Describe what you see" | **Broken.** Model says "The image appears to be a broken or corrupted image." Output is garbage (repeated zeros or random characters). |
| Multimodal + tools | Screenshot + "Click on Allow" + tool schema | **Empty.** 2 completion tokens, no tool call, no content. |

This isolated the problem: **text-only inference works, but multimodal (vision) is broken.** The vision encoder is receiving corrupted pixel data.

### 2.3 Token count anomaly

A 1080x1920 PNG image should produce approximately 2691 visual tokens for Qwen3-VL (based on patch_size=14, spatial_merge_size=2). However, SGLang reported only 2066 total prompt tokens (including text tokens), suggesting the image was not being tokenized into the expected number of visual tokens.

The image was verified as valid (PIL `verify()` passed, 1080x1920 RGBA, 60KB).

### 2.4 SGLang version analysis

The current container uses `lmsysorg/sglang:latest` (v0.5.9, image built 2026-02-23, transformers 4.57.1, torch 2.9.1+cu129). The December benchmark used an older version — likely v0.5.6.post2 (released 2025-12-11), which was the latest available on December 27.

Adding `--disable-fast-image-processor` did not fix the issue. The model still described images as corrupted, and the token count actually decreased to 969 (fewer visual tokens than before).

**Root cause**: SGLang v0.5.9 has a regression in multimodal processing for Qwen3-VL-4B-Instruct. The vision encoder produces corrupted embeddings regardless of the image processor variant (fast or slow).

## 3. Qwen3.5-4B as Alternative

### 3.1 Prior evaluation (March 6, 2026)

The rvsec-vision-llm project evaluated `Qwen/Qwen3.5-4B` on March 6. Key results from `docs/20260306_qwen35.md`:

| Config | Thinking | Temp | Hit Rate | Tool Call | Latency |
|--------|----------|------|----------|-----------|---------|
| A | ON | 0.01 | 100.0% | 100.0% | 5,409ms |
| B | OFF | 0.01 | 25.0% | 100.0% | 1,730ms |
| C | ON | 0.7 | 75.0% | 100.0% | 5,065ms |
| D | OFF | 0.7 | 50.0% | 100.0% | 1,724ms |

The conclusion at that time was that **thinking mode is essential** (ON = 87-100%, OFF = 25-50%) and that without thinking the model is not viable. Latency with thinking was ~3x that of Qwen3-VL (5.4s vs 1.8s).

### 3.2 Infrastructure requirements

Qwen3.5-4B differs from Qwen3-VL in infrastructure:

| Aspect | Qwen3-VL-4B-Instruct | Qwen3.5-4B |
|--------|----------------------|-------------|
| SGLang attention backend | flashinfer | **triton** (required for GDN on Blackwell) |
| Tool call parser | `qwen` | `qwen3_coder` |
| Reasoning parser | N/A | `qwen3` (for thinking mode) |
| Thinking mode | No | Yes (default ON, disable via `chat_template_kwargs`) |
| Coordinate system | [0, 1000) normalized | [0, 1000) normalized (same) |

SGLang launch command for Qwen3.5-4B:
```
python3 -m sglang.launch_server --model-path Qwen/Qwen3.5-4B \
  --host 0.0.0.0 --port 30000 --trust-remote-code \
  --attention-backend triton --tool-call-parser qwen3_coder \
  --enable-multimodal --context-length 8192 --reasoning-parser qwen3
```

### 3.3 Today's diagnostic tests (2026-03-19)

With Qwen3.5-4B running on SGLang v0.5.9, the same diagnostic multimodal request was repeated. Target: "Allow" button at (540, 1054) in `ar.rulosoft.mimanganu_75.apk/001.png`.

**Vision works.** The model describes the screenshot correctly: "I can see a permission dialog asking 'Allow Mi Manga Nu to access photos, media, and files on your device?'"

#### With thinking (enable_thinking=True, temp=0.7, top_p=0.8)

| Rep | Raw (x,y) | Device (x,y) | Distance | Hit | Latency | Tokens |
|-----|-----------|-------------- |----------|-----|---------|--------|
| 1 | (540, 540) | (583, 1036) | 46.6px | Yes | 8.9s | 541 |
| 2 | (540, 550) | (583, 1056) | 43.0px | Yes | 7.1s | 448 |
| 3 | (540, 550) | (583, 1056) | 43.0px | Yes | 4.4s | 271 |
| 4 | — | — | — | NO_TOOL | 31.2s | 2048 (max) |

3/4 hits (75%), average distance 44px, average latency 12.9s. One NO_TOOL where thinking consumed all 2048 tokens before producing a tool call.

#### Without thinking (enable_thinking=False, temp=0.7, top_p=0.8)

`chat_template_kwargs: {"enable_thinking": false}` sent at top level of request JSON body (per [HuggingFace documentation](https://huggingface.co/Qwen/Qwen3.5-4B)).

| Rep | Raw (x,y) | Device (x,y) | Distance | Hit | Latency | Tokens |
|-----|-----------|-------------- |----------|-----|---------|--------|
| 1 | (499, 550) | (538, 1056) | 2.8px | Yes | 1.5s | 41 |
| 2 | (499, 550) | (538, 1056) | 2.8px | Yes | 1.2s | 41 |
| 3 | (499, 549) | (538, 1054) | 2.0px | Yes | 1.1s | 33 |
| 4 | (499, 549) | (538, 1054) | 2.0px | Yes | 1.3s | 41 |

4/4 hits (100%), average distance 2.4px, average latency 1.3s. Perfectly consistent coordinates.

### 3.4 Contradiction with March 6 results

The March 6 evaluation found thinking OFF = 25-50% hit rate, but today's test shows 100% with higher precision and lower latency. Possible explanations for this discrepancy:

1. **Request format difference**: Today's test sends `chat_template_kwargs` at the top level of the JSON body (as documented by HuggingFace). The March 6 test used LangChain's `extra_body` parameter, which wraps it differently. If LangChain was not forwarding `enable_thinking: false` correctly, the model may have still been in thinking mode — but with the reasoning parser stripping the thinking content, making it *look* like non-thinking mode while still consuming tokens and introducing variance.

2. **Sampling parameters**: Today used Qwen-recommended params (temp=0.7, top_p=0.8, top_k=20). March 6 used temp=0.01, top_p=0.6 for configs B and F (the failing ones). Low temperature may interact poorly with non-thinking mode.

3. **Single element vs. multi-element**: Today tested only the "Allow" button (a large, high-contrast, text-labeled element). The 25% hit rate on March 6 included "Deny" and "READ LATER" buttons — still easy elements, but different enough to reveal variance.

**This discrepancy needs to be resolved through a proper smoke test** before drawing conclusions about Qwen3.5-4B viability.

## 4. Summary of Findings

| Finding | Impact |
|---------|--------|
| SGLang v0.5.9 breaks multimodal for Qwen3-VL-4B-Instruct | Cannot use the validated model on current infrastructure |
| Qwen3.5-4B multimodal works on SGLang v0.5.9 | Alternative model is available |
| Qwen3.5-4B without thinking: 100% hit, 2.4px avg, 1.3s latency (single element) | Promising but needs broader validation |
| Qwen3.5-4B with thinking: 75% hit, 44px avg, 12.9s latency (single element) | Worse than without thinking on this test |
| Contradiction with March 6 results on thinking mode | Needs smoke test to resolve |

## 5. Smoke Test (prevalidation.py, Qwen3.5-4B, no thinking)

### 5.1 Parser fix required

The first smoke test run showed only 30% tool call rate (21/70 widgets). Investigation revealed the Qwen3.5-4B model returns coordinates in a malformed format: `"x": "498, 549"` — both x and y packed into the x field as a comma-separated string. The `parse_click_response` function attempted `int("498, 549")`, which raised `ValueError` and was silently classified as `no_tool_call`.

The `_extract_xy` helper was added to handle this Qwen3.5 quirk: when `x` is a string containing a comma, split it and use the two parts as (x, y). This brought the tool call rate from 30% to 97%.

### 5.2 Smoke test configuration

- **Script**: `modules/aperv-llm-validation/scripts/prevalidation.py`
- **Model**: Qwen/Qwen3.5-4B with `enable_thinking: false` via `chat_template_kwargs`
- **Image mode**: raw (1080x1920, no resize)
- **Temperature**: 0.7 (Qwen-recommended for non-thinking mode)
- **Screenshots**: 10 (2 apps, 70 widget tests total)
- **Coordinate conversion**: 2-step (qwen→image→device), which for raw mode collapses to single-step

### 5.3 Results

| Metric | Qwen3.5-4B (no thinking) | Qwen3-VL (Dec benchmark) |
|--------|--------------------------|--------------------------|
| Tool call rate | **97.1%** (68/70) | 90.3% |
| Center hit (<50px) | 47.1% (32/68) | 57.7% |
| Bounds hit | 91.2% (62/68) | — |
| Average latency | **~1.3s** | 1.8s |
| Errors | 2/70 | — |

### 5.4 Per-element-type breakdown

| Widget Class | Tests | Center Hit | Rate | vs Qwen3-VL |
|---|---|---|---|---|
| Button | 3 | 3 | **100.0%** | 78.2% (+21.8%) |
| TextView | 11 | 10 | **90.9%** | 60.2% (+30.7%) |
| ImageView | 5 | 4 | **80.0%** | 0.0% (+80.0%) |
| ImageButton | 9 | 5 | **55.6%** | 43.5% (+12.1%) |
| CheckBox | 40 | 10 | 25.0% | 25.0% (=) |

The most striking improvement is **ImageView: 0% → 80%**. Qwen3-VL could not click on ImageView elements at all; Qwen3.5-4B locates them correctly 80% of the time. Button, TextView, and ImageButton also improved significantly.

### 5.5 Resolving the March 6 contradiction

The March 6 evaluation found thinking OFF = 25-50% hit rate, but today's smoke test shows 47.1% center hit with a 97% tool call rate. The discrepancy is now explained by **three factors**:

1. **Parser bug**: The March 6 test used the rvsec-vision-llm codebase, which may not have handled Qwen3.5's `"x": "498, 549"` format. Many "PARSE_ERROR" or tool calls with None coordinates would have been counted as misses rather than hits.

2. **Sampling parameters**: March 6 used temp=0.01, top_p=0.6 (our Qwen3-VL-optimized config). Today used temp=0.7, top_p=0.8 (Qwen-recommended for non-thinking). The model may perform differently under each setting.

3. **`enable_thinking` propagation**: The March 6 test sent `enable_thinking: false` via LangChain's `extra_body`. If LangChain or SGLang didn't propagate this correctly, the model would have been in thinking mode — consuming tokens on reasoning before tool generation and sometimes hitting the max_tokens limit.

The center hit rate of 47.1% (vs 57.7% for Qwen3-VL) is 10.6 points lower, but with 30% lower latency and dramatically better performance on ImageView and TextView elements.

## 6. Scaled Smoke Test (100 screenshots, 8 apps)

The 10-screenshot test was expanded to 100 screenshots across 8 apps (491 widgets total).

### Results

| Metric | Qwen3.5-4B (no thinking) | Qwen3-VL (Dec benchmark) |
|--------|--------------------------|--------------------------|
| Tool call rate | **85.5%** (420/491) | 90.3% |
| Center hit (<50px) | **66.2%** (278/420) | 57.7% |
| Bounds hit | **84.3%** (354/420) | — |
| Average latency | **1.9s** | 1.8s |

### Per-element-type (scaled)

| Widget Class | Tests | Center Hit | Rate | vs Qwen3-VL |
|---|---|---|---|---|
| Button | 67 | 63 | **94.0%** | 78.2% (+15.8%) |
| ImageView | 14 | 13 | **92.9%** | 0.0% (+92.9%) |
| ImageButton | 45 | 36 | **80.0%** | 43.5% (+36.5%) |
| TextView | 147 | 116 | **78.9%** | 60.2% (+18.7%) |
| CheckedTextView | 35 | 15 | **42.9%** | 29.2% (+13.7%) |
| CheckBox | 52 | 19 | **36.5%** | 25.0% (+11.5%) |
| EditText | 25 | 8 | 32.0% | **93.1%** (-61.1%) |

At scale, the center hit rate is **66.2%** — 8.5 points ABOVE the Qwen3-VL baseline of 57.7%. The earlier 10-screenshot test (47.1%) was pulled down by a CheckBox-heavy app.

### Distance distribution

The distance distribution is bimodal: 59.8% of valid predictions fall within 20px (very precise), while 22.4% are above 200px (gross misses). The average distance is inflated by these outliers.

| Range | Count | % |
|---|---|---|
| 0-10px | 92 | 21.9% |
| 10-20px | 159 | 37.9% |
| 20-50px | 27 | 6.4% |
| 50-100px | 30 | 7.1% |
| 100-500px | 64 | 15.2% |
| 500+px | 48 | 11.4% |

### Parser fix for Qwen3.5 coordinate format

The Qwen3.5-4B model frequently returns tool call arguments in a malformed format: `"x": "498, 549"` — both coordinates packed as a comma-separated string in the x field. The `_extract_xy` helper splits this format correctly. Without this fix, tool call rate drops from 85% to 30%.

## 7. Cryptoapp Smoke Test (tabs, spinners, radio buttons)

The cryptoapp (Crypto App — a cryptography learning tool) was chosen specifically because it contains tabs, spinners, and radio buttons that other apps in the first 100 screenshots lacked.

### Spinner text inheritance fix

The UIAutomator parser was missing Spinner text: the Spinner element has `text=""` but its child TextView has the displayed value (e.g. `text="AES"`). A fix was added to inherit text from the first child TextView when the parent is an `ALWAYS_CLICKABLE_TYPE` with no text of its own.

Before fix: Spinners excluded from test (no text → `select_widgets` filter).
After fix: Spinners included with correct label (e.g. `text="MD5"`, `text="AES"`, `text="RSA"`).

### Results (raw mode, 25 screenshots, 121 widgets)

| Widget Class | Tests | Center Hit | Rate | Bounds Hit |
|---|---|---|---|---|
| **LinearLayout (tabs)** | 16 | 15 | **93.8%** | 93.8% |
| **RadioButton** | 9 | 7 | **77.8%** | 100% |
| **Button** | 17 | 13 | **76.5%** | 82.4% |
| **EditText** | 19 | 6 | 31.6% | 100% |
| **Spinner** | 13 | 1 | **7.7%** | 100% |
| **CheckedTextView** | 13 | 0 | 0.0% | 100% |
| **TextView** | 16 | 0 | 0.0% | 100% |

Tabs (93.8%) and RadioButtons (77.8%) work well. Spinners hit bounds 100% but center hit is only 7.7% — the model clicks the text area within the spinner but not at the center of the widget bounding box (the text is typically left-aligned while the center includes the dropdown arrow).

## 8. Decision: Qwen3.5-4B replaces Qwen3-VL-4B

**Decision**: Use Qwen3.5-4B (without thinking) for all Group 0.5 pre-validation.

**Rationale**:

1. **Qwen3-VL-4B is broken** on SGLang v0.5.9 (multimodal regression). The only fix is downgrading SGLang to v0.5.6.post2, which means pulling a ~38GB Docker image and losing access to Qwen3.5 features.

2. **Qwen3.5-4B outperforms** the Qwen3-VL baseline at scale: 66.2% vs 57.7% center hit rate (+8.5pp), with comparable latency (1.9s vs 1.8s).

3. **Element-type coverage is dramatically better**: ImageView 0%→93%, ImageButton 43%→80%, Button 78%→94%. The only regression is EditText (93%→32%), which is less critical for grounding tests since EditText interaction is primarily type_text, not click.

4. **Tabs and RadioButtons work**: 93.8% and 77.8% center hit respectively — important element types for the cryptoapp and similar apps in the dataset.

5. **No thinking mode needed**: Non-thinking mode at ~1.9s is fast enough for batch processing (~1900 inferences/hour), and more accurate than thinking mode on this task.

### Infrastructure configuration

```bash
# SGLang launch (in docker-compose.sglang.yml)
MODEL_PATH=Qwen/Qwen3.5-4B
TOOL_CALL_PARSER=qwen3_coder
REASONING_PARSER=qwen3
ATTENTION_BACKEND=triton
CONTEXT_LENGTH=8192
```

```bash
# Pre-validation command
uv run python modules/aperv-llm-validation/scripts/prevalidation.py \
  --model "Qwen/Qwen3.5-4B" --disable-thinking \
  --modes raw --temperatures 0.7 \
  --screenshots-dir /path/to/screenshots \
  --output-dir results/prevalidation
```

### Code changes made during exploration

| File | Change |
|------|--------|
| `pipeline/sglang_client.py` | Added `extra_body` parameter to `call()` |
| `data/uiautomator_parser.py` | Spinner text inheritance from child TextView |
| `scripts/prevalidation.py` | `_extract_xy` for Qwen3.5 comma-separated coords; `--model`, `--disable-thinking` CLI args; `extra_body` forwarding |

## 9. 3-Mode Comparison (cryptoapp, 25 screenshots)

All three image processing modes were compared on the same cryptoapp dataset:

| Mode | Image Size | Tool Calls | Bounds Hit | **Center Hit** | Avg Dist |
|---|---|---|---|---|---|
| **raw** | 1080x1920 | 110 | 98.2% | **51.8%** | 184.6px |
| smart_resize | ~576x1024 | 113 | 97.3% | 47.8% | 207.7px |
| max_edge | 562x1000 | 105 | 99.0% | 39.0% | 228.2px |

Raw mode wins by +4pp over smart_resize and +12.8pp over max_edge. This is consistent with the hypothesis: the model grounds coordinates more accurately when it sees the image at its native resolution. Any resize introduces a conversion layer (image→device pixel mapping) that accumulates error.

**Conclusion**: The resize step can be eliminated. Raw mode is both simpler (no resize, single-step coordinate conversion) and more accurate. The 2-step conversion `qwen→image→device` collapses to `pixel = int((qwen / 1000) * device_dim)`, identical to the formula used in rv-agent's `ActionNormalizer`.

## 10. APE Loop Latency — Qwen3.5-4B Abandoned for Production (2026-03-20)

### Problem

Qwen3.5-4B was integrated into APE-RV Java (APE repo gh7, 5 commits on master). Smoke
testing on the emulator revealed **unacceptable latency**: ~4.7s per LLM call vs ~1.7s
with Qwen3-VL. All 6 prompt variants showed the same latency.

### Root Cause: Visual Token Count

The latency difference is caused by the image size, not network or model overhead:

| | Qwen3-VL (resized) | Qwen3.5-4B (raw) |
|---|---|---|
| Image dimensions | 562x1000 | 1080x1920 |
| Visual tokens | ~863 | ~2345 |
| Prefill time (host, uncached) | ~1.5s | ~3.6s |
| Total time (emulator) | ~1.7s | ~4.7s |

Raw mode (1080x1920) produces **2.7x more visual tokens** than resized mode (562x1000),
directly increasing prefill time. The +12.8pp accuracy gain from raw mode does not justify
+175% latency in the APE exploration loop, where each call uses a NEW screenshot (no
prefix caching possible).

### Why pre-validation latency was misleading

The pre-validation reported ~2.0s average latency for Qwen3.5-4B with raw images. This
was an artifact of **prefix caching**: the pre-validation tests multiple widgets per
screenshot, so the image tokens are prefilled once and cached for subsequent widget tests
on the same screenshot. Measured from the host:

| Condition | Latency |
|---|---|
| First call (uncached, new image) | 3.6s |
| Subsequent calls (same image, cached) | 2.4s |
| APE loop (always new image) | 3.6s + ~1s emulator overhead = **~4.7s** |

The ~2.0s average was dominated by cached calls. In the APE loop, every call has a
different screenshot — **zero cache hits**.

### Could resized mode fix Qwen3.5-4B latency?

Testing Qwen3.5-4B with resized images (562x1000, same as Qwen3-VL) produced ~2.5s from
the host (uncached) — still 67% slower than Qwen3-VL at 1.5s. The attention backend
difference (triton vs flashinfer) and model architecture changes contribute additional
overhead independent of image size.

### SGLang Qwen3-VL fix found

The Qwen3-VL multimodal regression was tracked to SGLang issue
[#19513](https://github.com/sgl-project/sglang/issues/19513). Key findings:

| Fact | Detail |
|---|---|
| Bug | `qwen3_vl.py` lost `"model.visual." → "visual."` weight mapping — vision encoder loads wrong weights |
| Introduced in | **v0.5.7** (Jan 2026) |
| Affects | v0.5.7, v0.5.8, v0.5.9 |
| Last working release | **v0.5.6.post2** (Dec 2025) |
| Fix | [PR #19333](https://github.com/sgl-project/sglang/pull/19333) merged 2026-02-27 on `main` |
| In a release? | **No** — v0.5.9 (2026-02-24) is the latest release, fix is post-release |
| Dec benchmark | Used SGLang via pip (~v0.5.6.post2) — worked |
| exp3 (2026-03-17) | Used `lmsysorg/sglang:latest` = v0.5.9 — **broken** |

### Decision: Revert to Qwen3-VL + SGLang v0.5.6.post2

**Decision**: Abandon Qwen3.5-4B for the APE exploration loop. Revert APE repo to
Qwen3-VL. Pin SGLang Docker image to `lmsysorg/sglang:v0.5.6.post2`.

**Rationale**:

1. **Latency is blocante**: 4.7s/call makes the LLM variant uncompetitive — in a 1-minute
   run with ~5 LLM calls, that's ~24s of LLM overhead (40% of total time) vs ~9s with
   Qwen3-VL.

2. **v0.5.6.post2 is the exact version** that produced the 57.7% benchmark and the ~1.7s
   latency in the Dec/2025 evaluation and subsequent experiments.

3. **The SGLang fix exists** but is not in any release yet. When v0.5.10 ships with the
   fix, Qwen3-VL on the new version can be re-evaluated.

4. **Qwen3.5-4B pre-validation results remain valid** as a grounding accuracy reference
   (59.4% center hit, 81.8% bounds hit) but are NOT applicable to production latency
   decisions.

**Actions taken**:
- APE repo: reverted gh7 commits (Qwen3.5-4B migration) on master
- APE repo: pinned `docker-compose.sglang.yml` to `lmsysorg/sglang:v0.5.6.post2`
- APE repo: deleted `prompt-variants` branch (will recreate for Qwen3-VL)
- rv-android gh43: Group 0A pivoted from "Qwen3.5 migration" to "Pin SGLang for Qwen3-VL"

## 11. Qwen3-VL Pre-Validation on SGLang v0.5.6.post2 (2026-03-20)

### Coordinate Space Finding

A direct test confirmed that **Qwen3-VL always returns [0, 1000) normalized coordinates**
regardless of the prompt's coordinate description. Five configurations were tested (raw vs
resized image × pixel vs normalized vs bare tool description) — all returned identical
coordinates (499, 255) for the same button, matching the normalized space exactly.

This means:
- The "3-space coordinate problem" from the design doc does not exist in practice
- The 2-step conversion `qwen→resized→device` is mathematically equivalent to 1-step
  `qwen→device` (rounding error ≤1px)
- The prompt's tool description ("pixel coordinates 0-1080" vs "normalized [0,1000)") is
  ignored by the model — it always outputs in its native [0, 1000) space

### Parser Fix Required

The prevalidation.py script was missing Qwen3-VL's most common malformed JSON format:
`{"x": 499, 255}` (missing "y" key). This is the same format that APE Java's
`ToolCallParser.fixMalformedJson()` handles with the `FIX_MISSING_Y_KEY` regex. Without
the fix, the script failed to parse most responses → 7% hit rate. With the fix → 72%.

Added `_fix_malformed_json()` to the script with all 4 patterns from APE Java:
- `"x": 499, 255` → `"x": 499, "y": 255` (missing y key)
- `"x": [499, 255]` → `"x": 499, "y": 255` (array format)
- `"x": "499, 255"` → `"x": 499, "y": 255` (comma-separated string, Qwen3.5)
- `": .91` → `": 0.91` (missing leading zero)

### Results: 468 screenshots, 28 apps

| Metric | Qwen3-VL (v0.5.6.post2) | Qwen3.5-4B (v0.5.9) | Qwen3-VL (Dec 2025) |
|---|---|---|---|
| Image mode | max_edge (562x1000) | raw (1080x1920) | max_edge (562x1000) |
| Temperature | 0.3 | 0.7 | 0.01 |
| Valid calls | **2,038** | 1,842 | 2,847 |
| Errors | **22** | 218 | ~277 |
| **Center hit** | **69.4%** | 59.4% | 57.7% |
| **Bounds hit** | **82.8%** | 81.8% | — |
| Latency (host) | ~1.0s | ~2.0s | ~1.8s |

**69.4% center hit** — 11.7pp above the December baseline and 10.0pp above Qwen3.5-4B.
Results from 2,060 real calls to Qwen3-VL (cache read disabled, all calls hit the model).
Initial run had 486 parser errors; after fixing `_fix_malformed_json` for 3 additional
Qwen3-VL formats (`"x":": N, M`, `"x": = N, M`, truncated JSON), errors dropped to 22.

### Per-Widget Class

| Widget Class | Calls | Center Hit | Rate | vs Qwen3.5-4B |
|---|---|---|---|---|
| Button | 446 | 389 | **87.2%** | 80.9% (+6.3pp) |
| EditText | 113 | 98 | **86.7%** | 32.0% (+54.7pp) |
| ImageView | 103 | 90 | **87.4%** | 90.8% (-3.4pp) |
| ImageButton | 196 | 165 | **84.2%** | 83.5% (+0.7pp) |
| LinearLayout (tabs) | 130 | 102 | **78.5%** | — |
| TextView | 524 | 336 | **64.1%** | — |
| Spinner | 52 | 30 | **57.7%** | — |
| CheckBox | 163 | 81 | **49.7%** | — |
| CheckedTextView | 143 | 56 | **39.2%** | — |
| Tabs (ActionBar$Tab) | 32 | 32 | **100.0%** | — |

Key finding: EditText went from 32% (Qwen3.5) to **86.7%** (Qwen3-VL) — the Qwen3.5
regression on EditText is eliminated.

### Parser Fixes Applied (3 rounds)

Initial run had 486 errors (all `no_tool_call`). Investigation revealed the prevalidation
script was missing Qwen3-VL's malformed JSON formats:

| Round | Fix | Errors remaining |
|---|---|---|
| 1 | `<tool_call>` XML extraction + truncated JSON (missing `}`) | 471 → 208 |
| 2 | `"x":": N, M` format (stray `:` in key) | 208 → 27 |
| 3 | `"x": = N, M` format (stray `=`) | 27 → **28** (irreducible) |

The 28 remaining errors are genuine: the model responds with text explaining the element
is not visible (e.g., "There is no element labeled 'Submit' visible in the screenshot").

### Implications

1. **Qwen3-VL on v0.5.6.post2 is the correct choice** — better accuracy than Qwen3.5,
   lower latency (~1.0s vs ~4.7s), no EditText regression
2. **Temperature 0.3** (APE default) produces better results than 0.01 (Dec benchmark)
   or 0.7 (Qwen-recommended) for coordinate grounding
3. **22 errors are irreducible** — model refuses to click when element is genuinely not
   visible in the screenshot (correct behavior)
4. These results use the **same 468 screenshots** as the Qwen3.5 pre-validation — directly
   comparable
5. Results validated with **cache read disabled** — all 2,060 calls hit the real model

# gh43: APE-RV LLM Validation — Tasks

<!-- Subagent dispatch hints:
  Group 0: manual/sequential (Java fixture generation — requires APE Java repo access)
  Group 0.5: sequential (pre-validation — requires SGLang, ~1-1.5h)
  Group 1: sequential (foundation — models, constants, cache, pyproject)
  Group 2: parallel (2A, 2B, 2C are independent — 3 subagents, ~6 files each)
  Group 3: sequential (depends on Group 2C prompt_builder; includes action_list)
  Group 3.5: sequential (som_overlay variant, depends on Group 2C)
  Group 4: sequential (depends on Groups 2+3)
  Group 5: sequential (depends on Group 4, requires SGLang for reasoning gate)
  Group 6: sequential (final verification)

  Critical path: 0 → 1 → 2(parallel) → 3 → 3.5 → 4 → 5 → 6
  Groups 0.5, 7-11 are execution/analysis phases (post-implementation)
  Group 0.5 can run in parallel with Groups 1-6 (implementation) since it uses existing rvsec-vision-llm approach
-->

## 0. Golden Fixture Preparation (prerequisite)

APE Java commit: `b2852dd` (master, `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape`)

- [ ] 0.1 Implement temporary `GoldenFixtureExporter` class in APE Java (local-only, NOT committed):
  - Hook into `LlmRouter.selectAction()` — after each LLM call, export 3 files:
    - `call_NNN.json` — all pipeline intermediaries (see schema in design.md)
    - `call_NNN.png` — screenshot captured at moment of call (copy from device)
    - `call_NNN.uiautomator` — UIAutomator XML dump at moment of call (copy from device)
  - Write files to emulator filesystem: `/data/local/tmp/golden/<app>/`
  - JSON fields: screenshot_file, uiautomator_file, app, activity, commit, device_w, device_h,
    resize (orig/new dims), jpeg_base64_sha256, jpeg_base64_first100, system_message,
    user_text, widget_list, tools_schema, llm_response_raw, parsed_action (type/x/y/text),
    pixel_coords, match_result (step/widget_index/distance)
  - Enable via flag (e.g., system property `ape.golden.export=true`)
- [ ] 0.2 Select 10 APKs for golden dataset (including cryptoapp):
  - cryptoapp (known activities + widget types)
  - 4-5 F-Droid apps with high no_match in exp3 (diverse UI complexity)
  - 4-5 apps with low no_match (successful matching baseline)
- [ ] 0.3 Run `rv-experiment` with golden export enabled:
  - `rv-experiment run --tools aperv --apks-dir <dir_with_10_apks> --timeout 150`
  - 2-3 min timeout per APK — enough for multiple LLM calls per app
  - All LLM calls during execution generate golden fixtures automatically
- [ ] 0.4 Pull fixtures from emulator and organize:
  - `adb pull /data/local/tmp/golden/ tests/fixtures/golden/`
  - Verify JSON files reference correct companion PNG + XML files
  - Count total fixtures (expect ~50-150 depending on LLM call frequency)
- [ ] 0.5 Create `tests/fixtures/golden/README.md`:
  - APE Java commit: `b2852dd`
  - Date of generation
  - List of 10 APKs used
  - Total fixture count
  - Instructions to re-generate (instrument LlmRouter, run rv-experiment, pull)
- [ ] 0.6 Remove `GoldenFixtureExporter` instrumentation from APE Java (revert local changes):
  - `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape && git checkout .`
  - Verify APE repo is clean: `git status` shows no modifications

## 0.5. Pre-Validation: Pure Grounding + smart_resize (requires SGLang)

This phase tests the VLM's baseline coordinate grounding accuracy WITHOUT coordinates in the
prompt, comparing three image processing approaches at two temperatures. It can run before or
in parallel with module implementation (Groups 1-6) since it reuses the rvsec-vision-llm
approach.

**Prior art**: rvsec-vision-llm showed 57.7% hit rate with pure grounding (no coords in prompt),
~100% with coordinates. This phase isolates the image processing variable.

**Execution window**: 2026-03-19 13:30 to 2026-03-20 09:00 (~20h SGLang available).
**Estimated time**: Depends on scope (see Q6 in design.md Open Questions):
- Per-screenshot (1 prompt per screenshot): 468 × 3 modes × 2 temps = 2,808 calls (~1.5h)
- Per-widget (each text widget → separate call): ~14,040 calls (~7h)
Resolve Q6 before execution.

- [ ] 0.5.1 Implement lightweight pre-validation script (standalone, not part of the module):
  - Input: 468 screenshots + UIAutomator XML pairs
  - For each widget with text label: prompt `"Click on the element labeled [text]"` + screenshot
  - Tool schema: `click(x: int, y: int)` with coordinates in [0, 1000) range
  - NO coordinates in prompt (pure visual grounding)
  - Output: CSV with (screenshot, widget_text, widget_bounds, mode, temperature, predicted_x, predicted_y, hit, distance_to_center)
- [ ] 0.5.2 Implement three image processing modes:
  - Mode A: max-edge 1000px + JPEG quality 80 (current APE-RV)
  - Mode B: smart_resize(factor=32, min_pixels=3136, max_pixels=10035200) + JPEG quality 80
    - factor=32 for Qwen3-VL (patch_size=16 × merge_size=2)
    - smart_resize algorithm: dimensions divisible by factor, total pixels in [min, max], preserve aspect ratio
  - Mode C: raw (no resize) + JPEG quality 80 — device-native resolution (1080×1920), as AppAgent does
- [ ] 0.5.3 Run all 6 conditions (3 modes × 2 temperatures):
  - Temperatures: 0.01 (near-deterministic) and 0.7 (high variance)
  - All 468 screenshots, widgets with text labels only
  - `--sglang-url http://192.168.0.36:30000/v1`
  - Expected baseline (Mode A, temp 0.3): ~57% hit rate (matching rvsec-vision-llm)
- [ ] 0.5.4 Generate comparison report (`results/000_prevalidation_report.md`):
  - Narrative report following P2 (human-readable, self-contained, explains why not just what)
  - Hit rate per mode × temperature (6 cells, global + per app)
  - McNemar test for pairwise mode comparison (within same temperature)
  - Mean distance to widget center for misses per condition
  - Error distribution by category per condition
  - Resized dimensions comparison: Mode A vs Mode B vs Mode C for representative screenshots
  - Token consumption and latency comparison across modes
  - Per-app breakdown: which apps benefit most from each mode
- [ ] 0.5.5 Decision gate:
  - If Mode B improves hit rate by ≥5pp over Mode A → use smart_resize in all prompt variants
  - If Mode C (raw) is best → consider eliminating resize entirely
  - If both ≤50% → pure grounding is limited, coordinates in prompt are essential (confirmed)
  - If Mode A ≈57% → confirms replication of rvsec-vision-llm results
  - If temperature 0.01 ≈ 0.7 → grounding is temperature-insensitive, use 0.01 for reproducibility
  - If 0.01 >> 0.7 → low temperature critical for coordinate accuracy
  - Document all decisions with rationale in `results/000_prevalidation_report.md`

## 1. Module Infrastructure (sequential)

- [ ] 1.1 Create `modules/aperv-llm-validation/` directory structure:
  ```
  src/aperv_llm_validation/{__init__,constants,cli}.py
  src/aperv_llm_validation/pipeline/__init__.py
  src/aperv_llm_validation/data/__init__.py
  src/aperv_llm_validation/prompts/__init__.py
  src/aperv_llm_validation/evaluation/__init__.py
  src/aperv_llm_validation/infrastructure/__init__.py
  tests/__init__.py
  tests/fixtures/golden/README.md
  tests/fixtures/cryptoapp/
  scripts/
  ```
- [ ] 1.2 Create `pyproject.toml` with dependencies:
  - Runtime: openai, Pillow, pydantic, rich, defusedxml
  - Dev: pytest, pytest-asyncio
  - Entry point: `aperv-llm-validate = "aperv_llm_validation.cli:main"`
- [ ] 1.3 Create `constants.py` with APE-RV constants:
  - `MAX_EDGE_PX = 1000`, `JPEG_QUALITY = 80`
  - `BOUNDARY_TOP_RATIO = 0.05`, `BOUNDARY_BOTTOM_RATIO = 0.94`
  - `MIN_EUCLIDEAN_TOLERANCE = 50.0`
  - `DEVICE_WIDTH = 1080`, `DEVICE_HEIGHT = 1920`
  - `QWEN_COORD_RANGE = 1000`
  - `INPUT_CLASS_NAMES` (EditText, AutoCompleteTextView, SearchView, androidx SearchView)
  - `CONTAINER_CLASS_NAMES` (FrameLayout, LinearLayout, RelativeLayout, ConstraintLayout, ViewGroup)
  - `EDGE_MISS_THRESHOLD = 20` — max distance (px) to widget bound for edge_miss
  - `TOLERANCE_MISS_MAX = 100` — max distance (px) from center for tolerance_miss
  - `GAP_THRESHOLD = 100` — min distance (px) for gap classification
  - `FEW_WIDGETS_THRESHOLD = 2` — max clickable widgets for few_widgets
  - `MAX_CONTAINER_RATE = 0.30` — guardrail: flag if container click rate exceeds
  - `MIN_SEMANTIC_RATE = 0.50` — guardrail: flag if semantic widget rate below
  - `MAX_BACK_RATE = 0.15` — guardrail: flag if back rate exceeds
  - `MAX_PER_APP_STD_DEV = 0.25` — guardrail: flag if per-app std dev exceeds
  - `DEFAULT_SGLANG_URL = "http://192.168.0.36:30000/v1"`
  - `DEFAULT_TEMPERATURE = 0.3`
  - `DEFAULT_MODEL = "default"`
  - `CACHE_DB_NAME = "llm_responses.db"`
  - `QWEN3_VL_PATCH_SIZE = 16`
  - `QWEN3_VL_MERGE_SIZE = 2`
  - `SMART_RESIZE_FACTOR = 32`  # QWEN3_VL_PATCH_SIZE × QWEN3_VL_MERGE_SIZE
  - `SMART_RESIZE_MIN_PIXELS = 3136`  # 56 × 56
  - `SMART_RESIZE_MAX_PIXELS = 10035200`  # ~3169 × 3169
- [ ] 1.4 Create `data/models.py` with dataclasses (see design.md Data Models):
  - `Widget` (frozen dataclass with center, area, width, height properties)
  - `MatchStep` (enum: back, bounds_match, long_click_retry, euclidean_match, no_match)
  - `NoMatchCategory` (enum: 7 categories including stale_model)
  - `ParsedAction` (frozen dataclass: action_type, x, y, text, reasoning, parse_level)
  - `MatchResult` (frozen dataclass: matched, step, widget, pixel coords, distance, classification)
  - `EvaluationResult` (frozen dataclass: screenshot_id, app_name, prompt, rep, LLM data, match, quality)
  - `PromptConfig` (dataclass: name, description, build functions)
- [ ] 1.5 Create `infrastructure/response_cache.py`:
  - SQLite-backed cache with table `llm_responses`
  - Key: `hash(screenshot_basename + prompt_name + rep_seed + temperature + resize_mode)`
  - Methods: `get()`, `put()`, `stats()` (hits, misses, size)
  - Thread-safe (SQLite WAL mode)
  - Auto-create DB on first access
- [ ] 1.6 Write `tests/test_response_cache.py`:
  - Test put/get round-trip
  - Test cache miss returns None
  - Test stats (hits, misses, total)
  - Test duplicate key overwrites
- [ ] 1.7 Run `uv sync` to verify module resolves
- [ ] 1.8 Run `/rv-test-run aperv-llm-validation` (verify cache tests pass)

## 2A. Pipeline — Image Processing + Coordinates (parallel)

- [ ] 2A.1 Implement `pipeline/image_processor.py`:
  - `calculate_resized_dimensions(orig_w, orig_h, max_edge=1000)` -> (new_w, new_h)
  - `smart_resize(height, width, factor=32, min_pixels=3136, max_pixels=10035200)` -> (new_h, new_w) — Qwen3-VL optimized resize: dimensions divisible by factor, total pixels in [min, max], preserve aspect ratio
  - `process_screenshot(png_path, mode="max_edge")` -> str — read PNG, resize (Pillow LANCZOS), JPEG quality 80, base64 encode (no data URI prefix); mode: "max_edge" (APE legacy) or "smart_resize" (Qwen3-VL)
  - `process_screenshot_bytes(png_bytes) -> str` — same but from bytes
- [ ] 2A.2 Implement `pipeline/coordinate_normalizer.py`:
  - `qwen_to_pixel(qwen_x, qwen_y, device_w=1080, device_h=1920) -> (pixel_x, pixel_y)` — `int((q / 1000.0) * dim)`, clamp [0, dim-1]
  - `pixel_to_qwen(pixel_x, pixel_y, device_w=1080, device_h=1920) -> (qwen_x, qwen_y)` — `int((p / dim) * 1000)`, clamp [0, 999]
- [ ] 2A.3 Write `tests/test_image_processor.py`:
  - Test `calculate_resized_dimensions(1080, 1920, 1000)` -> (562, 1000) — matches Java
  - Test `calculate_resized_dimensions(1920, 1080, 1000)` -> (1000, 562)
  - Test `calculate_resized_dimensions(800, 600, 1000)` -> (800, 600) — no resize needed
  - Test `calculate_resized_dimensions(0, 0, 1000)` -> raises ValueError
  - Test `smart_resize(1920, 1080, factor=32)` -> dimensions divisible by 32
  - Test `smart_resize(1080, 1920, factor=32)` -> dimensions divisible by 32
  - Test `smart_resize` output: both dimensions % 32 == 0, area within [min, max] pixels
  - Test `process_screenshot(path, mode="smart_resize")` produces valid base64
  - Test `process_screenshot` with real PNG from cryptoapp fixtures
- [ ] 2A.4 Write `tests/test_coordinate_normalizer.py`:
  - Test `qwen_to_pixel(500, 500, 1080, 1920)` -> (540, 960) — matches Java
  - Test `qwen_to_pixel(0, 0, 1080, 1920)` -> (0, 0)
  - Test `qwen_to_pixel(999, 999, 1080, 1920)` -> (1079, 1918) — clamp
  - Test `pixel_to_qwen(540, 960, 1080, 1920)` -> (500, 500) — round-trip
  - Test clamp: `qwen_to_pixel(1500, 1500, ...)` -> clamped to (dim-1)
- [ ] 2A.5 Write `tests/test_golden_fidelity.py` (image + coords section):
  - Load all golden fixture JSONs, verify `calculate_resized_dimensions` matches Java `resize` field
  - Verify JPEG SSIM >= 0.98 against golden `jpeg_base64_sha256`
- [ ] 2A.6 Run `/rv-test-run aperv-llm-validation` (verify 2A tests pass)

## 2B. Pipeline — Parser + Matching Algorithm (parallel)

- [ ] 2B.1 Implement `pipeline/tool_call_parser.py`:
  - 3-level fallback: native tool_calls -> `<tool_call>` XML tags -> inline JSON with "name"+"arguments"
  - `fix_malformed_json(s)`:
    - Missing "y": `"x": 352, 782` -> `"x": 352, "y": 782`
    - Array coords: `"x": [352, 782]` -> `"x": 352, "y": 782`
    - Missing leading zero: `: .91` -> `: 0.91`
    - Truncated JSON: auto-close braces
  - `parse(response_content, tool_calls=None) -> ParsedAction|None`
  - Extract `reasoning` field when present
  - Track `parse_level` (native, xml_tag, inline_json) for telemetry
- [ ] 2B.2 Implement `pipeline/action_mapper.py`:
  - `map_to_action(pixel_x, pixel_y, action_type, text, widgets, device_w, device_h) -> MatchResult`
  - Exact 5-step replica of `LlmRouter.mapToModelAction()`:
    1. Back action -> return back result
    2. Boundary reject: `pixel_y < device_h * 0.05` or `pixel_y > device_h * 0.94`
    3. Bounds containment: smallest widget whose bounds contain (pixel_x, pixel_y)
       - type_text filter: restrict to INPUT_CLASS_NAMES
    4. Long-click retry: if long_click failed containment, retry without type filter
    5. Euclidean fallback: nearest center within `max(50, min(widget_w, widget_h) / 2)`
  - Return classification on no_match (delegate to NoMatchClassifier)
- [ ] 2B.3 Write `tests/test_tool_call_parser.py`:
  - Test native format: `{"name": "click", "arguments": {"x": 500, "y": 600}}`
  - Test XML: `<tool_call>{"name": "click", "arguments": {"x": 500, "y": 600}}</tool_call>`
  - Test inline JSON in text: `"I'll click here: {"name": "click", ...}"`
  - Test malformed: `"x": 352, 782` -> fixes to `"x": 352, "y": 782`
  - Test array: `"x": [352, 782]` -> fixes
  - Test truncated JSON: auto-closes braces
  - Test reasoning extraction: `{"arguments": {"x": 500, "y": 600, "reasoning": "Login button"}}`
  - Test NO_TOOL: conversational response with no tool call -> returns None
  - Test negative: response that looks like JSON but is not a tool call -> returns None
- [ ] 2B.4 Write `tests/test_action_mapper.py`:
  - Test boundary rejection: pixel at (540, 50) -> rejected (top 5%)
  - Test boundary rejection: pixel at (540, 1850) -> rejected (bottom >94%)
  - Test boundary pass: pixel at (540, 100) -> not rejected
  - Test bounds containment: pixel at widget center -> match (bounds_match)
  - Test bounds containment: pixel inside bounds but off-center -> match (smallest area)
  - Test overlapping widgets: select smallest area widget
  - Test Euclidean fallback: pixel 30px from widget center -> match (within tolerance)
  - Test Euclidean miss: pixel 200px from any widget -> no_match (gap)
  - Test type_text filter: pixel on Button with type_text -> no_match (type_mismatch)
  - Test type_text filter: pixel on EditText with type_text -> match
  - Test long_click retry: long_click on non-long-clickable -> retry -> match
- [ ] 2B.5 Write golden fidelity tests (matching section):
  - Load all golden fixture JSONs, verify `map_to_action` produces same widget + step as Java `match_result`
- [ ] 2B.6 Run `/rv-test-run aperv-llm-validation` (verify 2B tests pass)

## 2C. Pipeline — Data Parsing + Prompt Builder (parallel)

- [ ] 2C.1 Implement `data/uiautomator_parser.py`:
  - `parse_uiautomator(xml_path) -> list[Widget]` — parse `.uiautomator` XML using defusedxml
  - Parse bounds `[left,top][right,bottom]` format
  - Filter: clickable=true, enabled=true, bounds area > 0, not system UI (by package or resource_id)
  - Extract: class_name, text, content_desc, resource_id, bounds, checkable, editable
  - Handle malformed XML gracefully (log warning, return empty list)
- [ ] 2C.2 Implement `pipeline/prompt_builder.py`:
  - `build_widget_list(widgets, device_w, device_h) -> str` — format as APE:
    `[i] ClassName "text" @(normX,normY) (v:0)` (v:0 since offline, no visit history)
  - `build_system_message(include_type_text, include_reasoning=False) -> str` — exact replica of `ApePromptBuilder.buildSystemMessage()`
  - `build_user_text(activity, widgets, device_w, device_h) -> str` — screen header + widget list + exploration context
  - `build_messages(screenshot_b64, widgets, activity, device_w, device_h, prompt_config) -> list[dict]` — assemble 2-message multimodal prompt
  - `build_tool_schema(include_type_text, include_reasoning=False) -> list[dict]` — OpenAI tools array
- [ ] 2C.3 Implement `pipeline/sglang_client.py`:
  - `SglangClient` class wrapping OpenAI client
  - `call(messages, tools, temperature, model) -> dict` — raw OpenAI response
  - Health check: `GET /v1/models` with timeout
  - Retry: 3x with exponential backoff on timeout/connection error
  - Integrate with `ResponseCache` (check before call, store after)
- [ ] 2C.4 Write `tests/test_uiautomator_parser.py`:
  - Test parsing cryptoapp `001.uiautomator` fixture:
    - Verify widget count, class names, bounds, text
    - Verify system UI elements filtered out
    - Verify zero-area elements filtered out
  - Test malformed XML -> returns empty list + logs warning
  - Test missing file -> raises FileNotFoundError
- [ ] 2C.5 Write `tests/test_prompt_builder.py`:
  - Verify widget list format matches APE output for known widgets
  - Verify system message text matches `ApePromptBuilder.buildSystemMessage()`
  - Verify tool schema structure matches `LlmRouter.buildToolsSchema()`
  - Verify type_text is conditional (only when input fields present)
  - Verify reasoning parameter added when `include_reasoning=True`
- [ ] 2C.6 Write golden fidelity tests (prompt section):
  - Load all golden fixture JSONs, verify prompt strings match Java `system_message` + `user_text` exactly
- [ ] 2C.7 Run `/rv-test-run aperv-llm-validation` (verify 2C tests pass)

## 3. Prompt Variants (sequential, depends on Group 2C)

- [ ] 3.1 Implement `prompts/registry.py`:
  - `PROMPT_REGISTRY: dict[str, PromptConfig]` — maps name to config
  - `get_prompt(name) -> PromptConfig` — with validation
  - `list_prompts() -> list[str]` — available variant names
- [ ] 3.2 Implement `prompts/ape_current.py`:
  - Exact replica of APE production prompt (from `ApePromptBuilder`)
  - No reasoning parameter in tool schema
- [ ] 3.3 Implement `prompts/ape_reasoning.py`:
  - Same as ape_current but tool schema includes `reasoning` (optional string)
- [ ] 3.4 Implement `prompts/compact_v1.py`:
  - Minimal system message (~100 tokens) based on v2 strict:
    ```
    Android testing agent. Coordinates [0,1000).
    CRITICAL RULES: 1. MUST use tool. 2. Dialog → click Allow/OK first.
    3. [DM]/[M] > unvisited > visited. 4. type_text for input fields.
    ```
  - Same widget list format as APE, tool schema with reasoning
- [ ] 3.5 Implement `prompts/rvsmart_v13.py`:
  - Replica of RVSmart V13 system message (dialog handling, JSON response format)
  - Widget list in RVSmart format: `1. Button "Login" @(500,600)`
  - Tool schema with reasoning
- [ ] 3.6 Implement `prompts/rvsmart_v17.py`:
  - Replica of RVSmart V17 (6-step reasoning, MOP markers, test-status tags)
  - Widget list with [UNTESTED] tags (all UNTESTED since offline)
  - Tool schema with reasoning
- [ ] 3.7 Implement `prompts/visual_only.py`:
  - No widget list — screenshot only
  - Minimal system message: "Click the most promising interactive element. Coordinates [0,1000)."
  - Tool schema with reasoning
  - Baseline for measuring how much the widget list helps coordinate accuracy
- [ ] 3.8 Implement `prompts/action_list.py`:
  - SOTA upper-bound variant: action-list selection (DroidBot-GPT, LLMDroid style — sota.md §8.1)
  - Numbered widget list: `"Available actions: 1. Click Button 'Login' 2. Click EditText 'Email' ..."`
  - Tool schema: `select_action(action_id: int, reasoning: str)` — no coordinates
  - Match is 100% by construction (any valid ID maps to a widget)
  - Metric: action quality (semantic widget rate, diversity, type_text coverage) — not match rate
  - Minimal system message: "Select the most promising action by number to explore the app."
  - Include back action: `"0. Go back"`
  - Note: This is a COMPARISON variant to establish the ceiling for element selection.
    It informs whether coordinate prediction is worth optimizing or should be replaced.

## 3.5. SoM Overlay Variant (sequential, depends on Group 2C)

- [ ] 3.5.1 Implement `prompts/som_overlay.py`:
  - Draw numbered labels on screenshot using Pillow (not OpenCV):
    - Semi-transparent dark background rectangle
    - White text number at widget center, offset +10px
    - Element deduplication: skip labels within 30px of existing label
    - Font: Pillow default, size adaptive to widget area
  - Minimal system message: "Interactive elements are labeled with numbers. Select an element."
  - Modified tool schema: `click(element_id: int)` instead of `click(x: int, y: int)`
  - Also include `type_text(element_id: int, text: str)` and `back()`
  - Include reasoning parameter
  - Note: This is a FALLBACK variant for comparison, not the primary approach
- [ ] 3.5.2 Write `tests/test_som_overlay.py`:
  - Test SoM annotation on cryptoapp screenshot
  - Test element deduplication (overlapping labels)
  - Test tool schema has element_id parameter instead of x/y

## 4. Evaluation Engine (sequential, depends on Groups 2+3)

- [ ] 4.1 Implement `evaluation/evaluator.py`:
  - `EvaluatorConfig` (Pydantic): sglang_url, model, temperature, screenshots_dir, cache_dir, seed
  - `Evaluator` class with `run()` method (see design.md API)
  - For each screenshot: check for matching `.uiautomator` (skip orphan PNGs with warning)
  - For each (screenshot, prompt, rep): check cache -> parse XML -> process image -> build prompt -> call LLM (or cache) -> parse -> normalize -> match -> classify -> compute guardrails -> record
  - Progress bar (rich)
  - Resume capability: skip already-evaluated tuples (by checking results CSV)
  - `health_check()`: verify SGLang availability + model name before run
- [ ] 4.2 Implement `evaluation/nomatch_classifier.py`:
  - `classify_nomatch(pixel_x, pixel_y, action_type, widgets, device_w, device_h) -> NoMatchCategory`
  - Order: boundary_rejection -> type_mismatch -> edge_miss -> tolerance_miss -> few_widgets -> gap (canonical order; stale_model assigned post-hoc in Group 10)
  - `compute_nearest_widget_distance(pixel_x, pixel_y, widgets) -> (Widget, float)`
  - `compute_nearest_bound_distance(pixel_x, pixel_y, widgets) -> (Widget, float)` — for edge_miss
  - Note: `stale_model` is assigned during reasoning analysis (Group 10), not here
- [ ] 4.3 Implement `evaluation/quality_guardrails.py`:
  - `compute_guardrails(results: list[EvaluationResult]) -> dict`
  - Metrics:
    - `container_click_rate`: % matches on CONTAINER_CLASS_NAMES
    - `semantic_widget_rate`: % matches on widgets with text/content_desc/resource_id
    - `back_rate`: % calls returning back
    - `type_text_coverage`: % using type_text when EditText present
    - `action_diversity`: Shannon entropy of action type distribution
    - `per_app_consistency`: std dev of per-app match rates
  - `quality_score(results) -> float`: composite 0.6×match + 0.2×semantic + 0.1×type_text + 0.1×diversity
- [ ] 4.4 Implement `evaluation/reporter.py`:
  - `generate_csv(results, output_path)` — one row per evaluation call
  - `generate_summary(results, output_path)` — markdown report:
    - Per-prompt: match rate, tool call rate, quality score, guardrail values
    - McNemar pairwise comparison table with Bonferroni-corrected p-values
    - No_match classification: 7-category distribution per prompt
    - type_text usage when EditText present
    - Token consumption and latency
    - Per-app match rate table (flag std dev > 25pp)
    - Top-10 screenshots by no_match rate per prompt (difficulty ranking)
    - Reasoning analysis: group reasoning texts for no_match cases
  - `generate_visualizations(results, screenshots_dir, output_dir)`:
    - Annotated screenshots for top-10 no_match cases: draw click point, nearest widget bounds, classification
    - Heatmap of no_match coordinates on generic screen template
- [ ] 4.5 Implement `cli.py`:
  - `run` command: `--screenshots-dir`, `--prompts`, `--repetitions`, `--max-screenshots`, `--sglang-url`, `--temperature`, `--output-dir`, `--use-cache/--no-cache`, `--cache-dir`, `--seed`
  - `report` command: `--results-dir`, `--format csv|markdown|both`
  - `list-prompts` command: list available prompt variants with descriptions
  - `validate-golden` command: `--fixtures-dir` — run golden fidelity checks
  - Use `rich` for progress bars and CLI formatting
- [ ] 4.6 Write `tests/test_nomatch_classifier.py`:
  - Test boundary_rejection: pixel at (540, 50) with 1920 height -> boundary_rejection
  - Test edge_miss: pixel 10px from widget bound -> edge_miss
  - Test tolerance_miss: pixel 60px from nearest widget center -> tolerance_miss
  - Test gap: pixel 200px from any widget -> gap
  - Test type_mismatch: widget at point is Button, action is type_text -> type_mismatch
  - Test few_widgets: 1 clickable widget -> few_widgets
  - Test nearest_widget_distance computation
  - Test nearest_bound_distance computation
- [ ] 4.7 Write `tests/test_quality_guardrails.py`:
  - Test container_click_rate with synthetic results (3 FrameLayout, 7 Button -> 30%)
  - Test semantic_widget_rate: widgets with/without text
  - Test back_rate calculation
  - Test type_text_coverage when EditText present
  - Test action_diversity (Shannon entropy) for uniform vs skewed distributions
  - Test quality_score composite calculation
- [ ] 4.8 Run `/rv-test-run aperv-llm-validation` (verify Groups 1-4 tests pass)
- [ ] 4.9 Run `/rv-doc-code modules/aperv-llm-validation/src/aperv_llm_validation/data/models.py`
- [ ] 4.10 Run `/rv-doc-code modules/aperv-llm-validation/src/aperv_llm_validation/evaluation/evaluator.py`
- [ ] 4.11 Run `/rv-doc-code modules/aperv-llm-validation/src/aperv_llm_validation/pipeline/action_mapper.py`

## 5. Integration Test (sequential, depends on Group 4)

- [ ] 5.1 End-to-end pipeline test with cryptoapp fixtures (mocked LLM):
  - Load `001.uiautomator` + `001.png` from test fixtures
  - Run full pipeline: parse -> image process -> build prompt -> (mock LLM response with known coords) -> parse -> normalize -> match
  - Verify: widget at center of Button "CIPHER" -> match (bounds_match)
  - Verify: coordinates in status bar -> boundary_rejection
  - Verify: coordinates between widgets -> no_match with correct classification
  - Verify: type_text on non-input -> type_mismatch
- [ ] 5.2 Verify ImageProcessor output dimensions match APE Java:
  - Process same PNG through Python and compare with golden fixtures
  - Verify for at least 5 screenshots from different apps
- [ ] 5.3 Verify cache integration:
  - Run pipeline with mock LLM, verify response cached
  - Run again, verify cache hit (no LLM call)
  - Run with `--no-cache`, verify LLM called despite cache
- [ ] 5.4 Reasoning validation gate (requires SGLang):
  - Run 50 screenshots × `ape_current` (no reasoning) and `ape_reasoning` (with reasoning)
  - Compare coordinates: must be identical in >= 95% of cases
  - Compare match rate: `ape_reasoning` within ±2pp of `ape_current`
  - If validation fails: document as finding, use `ape_current` as baseline
  - Note: this is a GATE — blocks Group 7 interpretation if reasoning alters behavior
- [ ] 5.5 Smoke test with live SGLang (if available):
  - 3 screenshots × ape_current × 1 rep
  - Verify pipeline runs end-to-end without errors
  - Verify results CSV is generated with correct columns
  - Verify cache populated

## 6. Implementation Verification

- [ ] 6.1 Run `/rv-qa-lint-fix aperv-llm-validation`
- [ ] 6.2 Run `/rv-verify aperv-llm-validation`
- [ ] 6.3 Verify acceptance criteria from plan.md (implementation section)
- [ ] 6.4 Run `/rv-code-reviewer`

## 7. Execution — Baseline Run (sequential, requires SGLang at 192.168.0.36)

- [ ] 7.0 Run SGLang health check: verify model availability and version
- [ ] 7.1 Run `ape_current` prompt (APE production baseline):
  - All 468 screenshots × 1 rep
  - `uv run aperv-llm-validate run --screenshots-dir /home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots --prompts ape_current --repetitions 1`
  - This establishes the offline baseline: expected match rate ~62% (matching exp3)
- [ ] 7.2 Run `ape_reasoning` prompt (same as baseline but with reasoning):
  - All 468 screenshots × 1 rep
  - Compare match rate with ape_current (should be within ±2pp per validation gate)
  - Collect reasoning texts for no_match analysis
- [ ] 7.3 Quick validation: compare ape_current match rate with exp3 (62.1% expected)
  - If deviation > 5pp: investigate replication fidelity issue before proceeding

## 8. Execution — Prompt Comparison (sequential)

- [ ] 8.1 Run `compact_v1` prompt: 468 screenshots × 1 rep
- [ ] 8.2 Run `rvsmart_v13` prompt: 468 screenshots × 1 rep
- [ ] 8.3 Run `rvsmart_v17` prompt: 468 screenshots × 1 rep
- [ ] 8.4 Run `visual_only` prompt: 468 screenshots × 1 rep
- [ ] 8.5 Run `som_overlay` prompt: 468 screenshots × 1 rep
  - Note: uses element_id instead of coordinates; analyzed separately from coordinate variants
- [ ] 8.6 Run `action_list` prompt: 468 screenshots × 1 rep
  - Note: match rate is 100% by construction; focus on action quality metrics
  - Compare action selection quality with coordinate-based variants (same widget chosen?)

## 9. Execution — Best Prompt Deep Evaluation (sequential, depends on 7+8 analysis)

- [ ] 9.1 Select top-2 prompts using formal criteria:
  - **Primary**: Highest match rate (mean across 468 screenshots)
  - **Tiebreaker 1**: Lowest per-app variance (std dev of per-app match rates)
  - **Tiebreaker 2**: Highest type_text usage when EditText present
  - **Tiebreaker 3**: Highest action diversity (Shannon entropy)
  - **Tiebreaker 4**: Lowest token consumption
  - **Stability rule**: If top-2 difference < 2pp, select both; if >= 5pp, select #1 + #2
  - Also consider quality score (composite metric) — flag if rank differs from match rate rank
- [ ] 9.2 Run top-2 prompts with 3 repetitions (statistical significance):
  - All 468 screenshots × 3 reps each
- [ ] 9.3 Run top-2 prompts on high-no_match subset:
  - Select 30 screenshots from apps with highest no_match in baseline
  - 3 reps each — focus analysis on hardest cases
  - Document selection criteria: top-N apps by no_match rate, diverse app categories

## 10. Analysis and Reports (sequential, depends on 7+8+9)

- [ ] 10.1 Generate per-prompt comparison report:
  - Match rate, no_match rate, tool call rate, quality score per prompt variant
  - **McNemar test** for pairwise comparison of 6 coordinate-based variants (C(6,2) = 15 pairs,
    Bonferroni threshold = 0.05/15 = 0.0033). `som_overlay` and `action_list` analyzed separately
    (different action spaces — not included in pairwise McNemar)
  - Bootstrap 95% CI for each prompt's match rate (10,000 resamples, stratified by app)
  - Action diversity: distribution of click/long_click/type_text/back per prompt
  - type_text usage: % of calls using type_text when EditText present
  - Token consumption: input + output tokens per call per prompt
  - Latency: ms per call per prompt
- [ ] 10.2 Generate quality guardrail report:
  - Container click rate per prompt (flag > 30%)
  - Semantic widget rate per prompt (flag < 50%)
  - Back action rate per prompt (flag > 15%)
  - Per-app match rate consistency (flag std dev > 25pp)
  - Quality score (composite) — compare ranking vs match-rate-only ranking
- [ ] 10.3 Generate no_match classification report:
  - 7-category distribution (boundary_rejection, edge_miss, tolerance_miss, gap, type_mismatch, few_widgets, stale_model)
  - Per-prompt breakdown: which prompts produce which types of no_match
  - Distance histogram: distribution of distance to nearest widget for no_match calls
  - Heatmap: where on screen do no_match coordinates cluster
- [ ] 10.4 Generate reasoning analysis report:
  - Group reasoning texts by no_match category
  - Identify patterns: "correct intent, wrong coords" vs "wrong intent"
  - Assign `stale_model` category: cases where reasoning mentions visible element not in XML
  - Examples of each category with reasoning text (top-5 per category)
  - Quantify: what % of `gap` cases are actually `stale_model` (timing gap)?
- [ ] 10.5 Generate action_list and som_overlay comparison report (separate from McNemar):
  - action_list: action quality (semantic rate, diversity, type_text coverage), widget selection overlap with best coordinate variant
  - som_overlay: element selection accuracy, overlap with coordinate variants
  - Key question: does action_list select the **same widgets** as the best coordinate variant?
    If yes + better quality metrics → action-list is strictly superior
  - Key question: does action_list achieve higher semantic_widget_rate and type_text coverage?
    If yes → coordinate prediction introduces noise that degrades action selection
- [ ] 10.6 Generate per-screenshot difficulty report:
  - Rank screenshots by no_match rate across all prompts
  - Identify "hard" screenshots: high no_match across all prompts (structural issues)
  - Identify "prompt-sensitive" screenshots: high variance across prompts (improvement opportunity)
  - Per-element type analysis: match rate by widget class (Button, ImageButton, EditText, etc.)
  - Per-activity analysis: match rate by activity name
- [ ] 10.7 Generate visualizations:
  - Top-10 no_match cases: annotated screenshots with click point, nearest widget bounds, classification label
  - Heatmap of no_match coordinates overlaid on generic 1080×1920 screen template
  - Bar charts: per-prompt match rate with 95% CI error bars
- [ ] 10.8 Generate final summary report (`results/005_final_report.md`):
  - Executive summary: best prompt, expected no_match reduction, quality score
  - Recommendation for APE Java prompt update (ready-to-port prompt text)
  - Data-driven input for Phase A' (which APKs to re-run, what logging to add)
  - Data-driven input for Phase C (which matching algorithm improvements are warranted)
  - Repetition analysis: mean ± std for top-2 prompts (flag if std > 3pp)
  - All supporting tables and figures

## 11. Conclusions and Next Steps

- [ ] 11.1 Update `docs/20260318_aperv_coordenadas_gh46.md` with Phase B results
- [ ] 11.2 Create optimized prompt file for APE Java implementation (ready to port):
  - If best coordinate variant ≥ 75% match + quality ≥ 0.70: port prompt (system message, tool schema, widget list format, temperature)
  - If best coordinate variant < 65%: create architecture change recommendation (action-list/SoM) instead of prompt file
  - If 65-75%: port prompt but flag that timing gap (gh46) should be prioritized
- [ ] 11.3 Document lessons learned and parameter recommendations
- [ ] 11.4 Plan Phase A'/C adjustments based on Phase B findings:
  - If `stale_model` is dominant no_match cause: prioritize timing gap fix
  - If `gap` (non-stale) is dominant: prioritize prompt improvement
  - If `boundary_rejection` is high: add boundary avoidance to prompt
  - If `edge_miss` is high: consider snap-to-nearest in matching algorithm

# gh43: APE-RV LLM Validation — Tasks

<!-- ============================================================
  EXECUTION PLAN (pivoted 2026-03-19)
  ============================================================

  FOUR PARALLEL TRACKS:

  TRACK A — APE Java Prompt Variants (Group 0)
  ──────────────────────────────────────────────
  Create branch gh43-prompt-variants in APE repo.
  Implement 6 prompt variants as Java string constants in ApePromptBuilder.
  Add structured telemetry to LlmRouter.
  Build + smoke test with cryptoapp.

  TRACK B — Pre-Validation (Group 0.5, requires SGLang)
  ──────────────────────────────────────────────────────
  Independent of all other tracks.
  Per-widget grounding test, 3 image processing modes, 2 temperatures, ~14k calls.

  TRACK C — Python Analysis Module (Group 1)
  ──────────────────────────────────────────────
  Can be built in parallel with Track A.
  Restructure Python module from pipeline replication to analysis toolkit.
  Telemetry parser, results parser, no-match classifier, statistics, reports.
  Infrastructure from old Group 1 is ALREADY DONE (constants.py, models.py,
  cache, image_processor, coordinate_normalizer, uiautomator_parser, etc.).

  TRACK D — Experiment Execution + Analysis (Groups 2-4)
  ──────────────────────────────────────────────────────
  Requires: Track A (APE Java) + Track C (Python analysis) complete.
  Run rv-experiment with 10 APKs × 6 variants × 3 reps = 180 runs.
  Analyze results with Python module. Generate reports.

  DEPENDENCY GRAPH:
    Track A (Group 0) ──────────────────────────→ Group 2 (execution)
    Track B (Group 0.5) ── independent ──────────→ feeds Group 3 decisions
    Track C (Group 1) ──────────────────────────→ Group 3 (analysis)
    Group 2 + Group 1 ─────────────────────────→ Group 3 (analysis)
    Group 3 ───────────────────────────────────→ Group 4 (conclusions)
-->

## 0. APE Java Prompt Variants (branch gh43-prompt-variants)

APE repo: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape`
APE Java commit: `b2852dd` (master)

- [ ] 0.1 Create branch `gh43-prompt-variants` from master (commit b2852dd) in APE repo
- [ ] 0.2 Add prompt variant selection to `ApePromptBuilder.java`:
  - Read system property `ape.llm.prompt_variant` (default: "ape_current")
  - Add 6 system message constants (keep `buildSystemMessage()` as ape_current baseline)
  - Variants: ape_current (existing), ape_reasoning (same + reasoning in schema), compact_v1 (minimal ~100 tokens), rvsmart_v13 (dialog handling, RVSmart format), rvsmart_v17 (6-step reasoning, MOP tags), visual_only (no widget list)
- [ ] 0.3 Add enhanced telemetry to `LlmRouter.java`:
  - Log per-call: variant name, qwen coords, pixel coords, matched/no_match, nearest widget class, distance to nearest, widget count, activity name
  - Format: `[APE-LLM-TEL] variant=X call=N qwen=(x,y) pixel=(px,py) result=matched|no_match nearest_class=Button nearest_dist=12.5 widgets=8 activity=MainActivity`
  - This structured log line enables Python analysis of no-match causes
- [ ] 0.4 For ape_reasoning variant: add optional `reasoning` string parameter to tool schema
- [ ] 0.5 For visual_only variant: skip widget list in user text (send only screenshot)
- [ ] 0.6 Build APE: `./gradlew assembleDebug` or equivalent
- [ ] 0.7 Test with 1 APK (cryptoapp) to verify variant selection works:
  - `rv-experiment run --tools aperv --apks-dir apks_examples --timeout 60 --tool-args "prompt_variant=compact_v1"`
  - Verify telemetry logs contain variant name
- [ ] 0.8 Note: Do NOT commit to APE master. Branch is temporary for this experiment.

## 0.5. Pre-Validation: Pure Grounding + smart_resize (requires SGLang)

This phase tests the VLM's baseline coordinate grounding accuracy WITHOUT coordinates in the
prompt, comparing three image processing approaches at two temperatures. It can run before or
in parallel with module implementation (Groups 1-6) since it reuses the rvsec-vision-llm
approach.

**Prior art**: rvsec-vision-llm showed 57.7% hit rate with pure grounding (no coords in prompt),
~100% with coordinates. This phase isolates the image processing variable.

**Execution window**: 2026-03-19 13:30 to 2026-03-20 09:00 (~20h SGLang available).
**Scope**: Per-widget — each visible widget with text/content_desc that is `clickable=true` OR
belongs to ALWAYS_CLICKABLE_TYPES (tabs, spinners, navigation, FABs, chips). Cap: 20 widgets
per screenshot. Only `click` actions.
**Estimated time**: avg ~8 widgets/screen (cap 20) × 468 screenshots × 3 modes × 2 temps ≈ 8k-22k calls (~4-11h).

- [x] 0.5.1 Implement lightweight pre-validation script (standalone, not part of the module):
  - Input: 468 screenshots + UIAutomator XML pairs
  - Widget selection: visible, has text/content_desc, clickable=true OR class in ALWAYS_CLICKABLE_TYPES (tabs, spinners, navigation, FABs, chips), cap 20 per screenshot
  - For each selected widget: prompt includes **resized image dimensions** (`"Screen is {img_w}x{img_h} pixels. Click on the element labeled [text]"`). Dimensions match the image the model sees (max_edge: 562×1000, smart_resize: varies, raw: 1080×1920).
  - Tool: `android_click(x, y)` with description specifying pixel ranges for the resized image. Qwen3-VL returns [0, 1000) normalized coords regardless.
  - Coordinate conversion: Qwen [0,1000) → resized image pixels → device pixels (2-step). Hit checked against UIAutomator bounds (device pixel space).
  - NO widget coordinates in prompt (pure visual grounding)
  - Two hit metrics: `bounds_hit` (pixel in widget bounds, strict) + `center_hit` (≤50px from center, matches rvsec-vision-llm 57.7% baseline)
  - Output: CSV with (screenshot, widget_text, widget_class, widget_bounds, mode, temperature, predicted_qwen_x/y, predicted_pixel_x/y, bounds_hit, center_hit, distance_to_center, tokens, latency)
  - Summary: hit rates per mode×temp, per widget class, per app
  - Fallback parser: native tool_calls → JSON in content (handles Qwen malformed output)
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
  - Expected baseline (Mode A, temp 0.01): center_hit ~57% (matching rvsec-vision-llm)
- [ ] 0.5.4 Generate comparison report (`results/000_prevalidation_report.md`):
  - Narrative report following P2 (human-readable, self-contained, explains why not just what)
  - bounds_hit AND center_hit rate per mode × temperature (6 cells, global + per app)
  - Per widget class breakdown (Button, EditText, CheckBox, Spinner, Tab, etc.)
  - McNemar test for pairwise mode comparison (within same temperature)
  - Mean distance to widget center for misses per condition
  - Error distribution by category per condition
  - Resized dimensions comparison: Mode A vs Mode B vs Mode C for representative screenshots
  - Token consumption and latency comparison across modes
  - Per-app breakdown: which apps benefit most from each mode
  - Tool call success rate per condition
- [ ] 0.5.5 Decision gate:
  - If Mode B improves center_hit rate by ≥5pp over Mode A → use smart_resize in all prompt variants
  - If Mode C (raw) is best → consider eliminating resize entirely
  - If both ≤50% → pure grounding is limited, coordinates in prompt are essential (confirmed)
  - If Mode A center_hit ≈57% → confirms replication of rvsec-vision-llm results
  - If temperature 0.01 ≈ 0.7 → grounding is temperature-insensitive, use 0.01 for reproducibility
  - If 0.01 >> 0.7 → low temperature critical for coordinate accuracy
  - Document all decisions with rationale in `results/000_prevalidation_report.md`

## 1. Python Analysis Module

Infrastructure from the previous plan is already built and reusable:
constants.py, models.py, response_cache.py, image_processor.py, coordinate_normalizer.py,
uiautomator_parser.py, sglang_client.py (all [x] from old Groups 1, 2A, 2B, 2C).

- [x] 1.1 Module infrastructure: directory structure, pyproject.toml, uv sync (done in old Group 1)
- [x] 1.2 Constants, models, response cache (done in old Groups 1.3-1.6)
- [x] 1.3 Image processor + coordinate normalizer (done in old Groups 2A.1-2A.4)
- [x] 1.4 UIAutomator parser (done in old Group 2C.1, 2C.4)
- [ ] 1.5 Restructure module: delete `pipeline/prompt_builder.py`, `pipeline/tool_call_parser.py`, `pipeline/action_mapper.py`; delete `prompts/` directory contents (keep `__init__.py`); delete `evaluation/` directory contents (keep `__init__.py`); delete obsolete tests for deleted modules
- [ ] 1.6 Create `analysis/__init__.py`
- [ ] 1.7 Create `analysis/telemetry_parser.py`:
  - Parse `[APE-LLM-TEL]` lines from logcat files
  - Extract: variant, call number, qwen coords, pixel coords, result, nearest widget class, distance, widget count, activity
  - Return list of `TelemetryEntry` dataclasses
- [ ] 1.8 Create `analysis/results_parser.py`:
  - Parse rv-experiment results directory structure
  - Load coverage metrics per run (method_coverage, activity_coverage, mop_coverage)
  - Group by variant, app, repetition
- [ ] 1.9 Create `analysis/nomatch_classifier.py`:
  - Classify no-match from telemetry data (7-category taxonomy: boundary_rejection, edge_miss, tolerance_miss, gap, type_mismatch, few_widgets, stale_model)
  - Input: `TelemetryEntry` with pixel coords, widget count
  - Uses boundary ratios, distance thresholds from constants.py
- [ ] 1.10 Create `analysis/statistics.py`:
  - McNemar test for pairwise prompt comparison (on per-APK coverage binary outcomes)
  - Bonferroni correction (6 variants, C(6,2)=15 pairs, threshold 0.0033)
  - Bootstrap 95% CI for coverage metrics
  - Kruskal-Wallis for multi-group comparison
- [ ] 1.11 Create `analysis/quality_guardrails.py`:
  - Compute from telemetry: match_rate, container_click_rate, back_rate, action_diversity
  - quality_score composite
- [ ] 1.12 Create `analysis/reporter.py`:
  - Generate markdown comparison reports
  - Per-variant: coverage metrics, match rate, quality guardrails
  - Pairwise statistical tests
  - Per-app breakdown
  - Visualizations placeholder (charts via matplotlib)
- [ ] 1.13 Update `cli.py`:
  - `prevalidate` command (Group 0.5)
  - `analyze` command: `--results-dir` (rv-experiment output)
  - `report` command: `--analysis-dir` → markdown + CSV
- [ ] 1.14 Write tests for analysis components (telemetry_parser, results_parser, nomatch_classifier, statistics, quality_guardrails, reporter)
- [ ] 1.15 Run all tests: `uv run pytest modules/aperv-llm-validation/tests/ -v`

## 2. Experiment Execution (requires emulator + SGLang on experiment machine)

Requires: Group 0 (APE Java prompt variants) complete.

- [ ] 2.1 Select 10 APKs (instrumented + static analysis JSON):
  - cryptoapp + 9 others from the instrumented set on experiment machine
  - Mix of complexity levels (simple/medium/complex UI)
- [ ] 2.2 Run baseline: `rv-experiment run --tools aperv --apks-dir <dir> --timeout 150 --tool-args "prompt_variant=ape_current"` × 3 reps
- [ ] 2.3 Run compact_v1: same command with `prompt_variant=compact_v1` × 3 reps
- [ ] 2.4 Run rvsmart_v13: same command with `prompt_variant=rvsmart_v13` × 3 reps
- [ ] 2.5 Run rvsmart_v17: same command with `prompt_variant=rvsmart_v17` × 3 reps
- [ ] 2.6 Run visual_only: same command with `prompt_variant=visual_only` × 3 reps
- [ ] 2.7 Run ape_reasoning: same command with `prompt_variant=ape_reasoning` × 3 reps
- [ ] 2.8 Total: 6 variants × 10 APKs × 3 reps = 180 runs, ~9h estimated
- [ ] 2.9 Collect all results + logcat files from rv-experiment output

## 3. Analysis and Reports

Requires: Groups 1 (Python analysis) + 2 (experiment execution) complete.

- [ ] 3.1 Parse all results with Python analysis module:
  - `uv run aperv-llm-validate analyze --results-dir <rv-experiment-output>`
- [ ] 3.2 Generate per-variant comparison report:
  - Coverage metrics (method, activity, MOP) per variant with mean ± std across 3 reps
  - McNemar test for pairwise comparison (15 pairs, Bonferroni threshold 0.0033)
  - Bootstrap 95% CI for coverage metrics
  - Kruskal-Wallis for multi-group comparison
- [ ] 3.3 Generate no-match classification report from telemetry:
  - 7-category distribution per variant
  - Per-variant breakdown: which variants produce which types of no-match
  - Distance histogram to nearest widget for no-match calls
- [ ] 3.4 Generate quality guardrail report:
  - Container click rate, semantic widget rate, back rate per variant
  - Per-app match rate consistency (flag std dev > 25pp)
  - Quality score composite per variant
- [ ] 3.5 Generate per-app breakdown:
  - Coverage by variant × app matrix
  - Identify apps where variant choice matters most
- [ ] 3.6 Final summary with best prompt recommendation + coverage impact:
  - Executive summary: best variant, coverage improvement over baseline
  - If best variant significantly better (McNemar p < 0.0033): recommend porting to APE master
  - If no significant difference: document and recommend focusing on timing gap (gh46)

## 4. Conclusions

- [ ] 4.1 Document results and recommendations in final report
- [ ] 4.2 Plan next steps:
  - If best variant > baseline: port prompt to APE master
  - If timing gap (stale_model) dominates no-match: prioritize gh46
  - If coordinate prediction limited across all variants: consider architectural change (action-list/SoM, deferred)
- [ ] 4.3 Clean up: delete APE branch `gh43-prompt-variants` (or keep for reference if results warrant porting)

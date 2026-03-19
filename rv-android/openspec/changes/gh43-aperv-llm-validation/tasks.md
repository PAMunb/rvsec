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
  Per-widget grounding test, raw mode (no resize), Qwen3.5-4B (no thinking), ~4-9k calls.

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

## 0.5. Pre-Validation: Pure Grounding (requires SGLang)

This phase tests the VLM's baseline coordinate grounding accuracy WITHOUT coordinates in the
prompt, using raw screenshots (no resize) and the Qwen3.5-4B model.

**Model**: Qwen3.5-4B (without thinking). Replaces Qwen3-VL-4B-Instruct which broke on SGLang
v0.5.9. See `exploration-sglang-qwen35.md` for investigation and validation.
**Image mode**: raw (1080x1920, no resize). Outperformed max_edge by +12.8pp and smart_resize
by +4pp on cryptoapp. Eliminates the 3-space coordinate problem.
**Temperature**: 0.7 (Qwen-recommended for non-thinking mode).
**Scope**: Per-widget with text/content_desc, clickable=true OR ALWAYS_CLICKABLE_TYPES.
Cap: 20 widgets per screenshot. Only `click` actions.
**Estimated time**: avg ~8 widgets/screen × 468 screenshots × ~2s/call ≈ ~4k-9k calls (~2-5h).

- [x] 0.5.1 Implement lightweight pre-validation script (`scripts/prevalidation.py`):
  - Input: 468 screenshots + UIAutomator XML pairs
  - Widget selection: visible, has text/content_desc, clickable=true OR ALWAYS_CLICKABLE_TYPES
  - For Spinners/tabs with empty text: inherit text from first child TextView
  - Prompt: `"Screen is 1080x1920 pixels. Click on the element labeled [text]"` (NO coords)
  - Tool: `android_click(x, y)` with pixel ranges 0-1080, 0-1920
  - Coordinate conversion: single-step `pixel = int((qwen / 1000) * device_dim)`
  - `chat_template_kwargs: {"enable_thinking": false}` via OpenAI SDK `extra_body`
  - Parser handles Qwen3.5 `"x": "498, 549"` format via `_extract_xy` helper
  - Two hit metrics: `bounds_hit` (pixel in widget bounds) + `center_hit` (≤50px from center)
  - Output: CSV + summary per widget class and per app
  - Responses cached in SQLite for reproducibility (full response JSON)
- [x] 0.5.2 Image processing modes implemented (all 3 modes exist in code):
  - Mode A: max-edge 1000px + JPEG quality 80
  - Mode B: smart_resize(factor=32)
  - Mode C: raw (no resize) + JPEG quality 80
- [x] 0.5.3 Exploratory 3-mode comparison on cryptoapp (25 screenshots):
  - raw: 51.8% center hit | smart_resize: 47.8% | max_edge: 39.0%
  - **Decision: use raw mode only** — simplest and most accurate
- [x] 0.5.4 Smoke tests completed (see `exploration-sglang-qwen35.md`):
  - 100 screenshots (8 apps): 66.2% center hit, 84.3% bounds hit, 85.5% tool call rate
  - Cryptoapp (25 screenshots): tabs 93.8%, RadioButton 77.8%, Spinner 7.7% center hit
  - Latency: ~1.9s average
- [ ] 0.5.5 Run full pre-validation (468 screenshots, raw mode, temp=0.7):
  ```bash
  uv run python modules/aperv-llm-validation/scripts/prevalidation.py \
    --screenshots-dir /home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots \
    --model "Qwen/Qwen3.5-4B" --disable-thinking \
    --modes raw --temperatures 0.7 \
    --output-dir results/prevalidation --cache-dir .cache/prevalidation
  ```
- [ ] 0.5.6 Generate pre-validation report (`results/000_prevalidation_report.md`):
  - Narrative report following P2
  - center_hit and bounds_hit rate (global + per app + per widget class)
  - Per widget class breakdown (Button, EditText, CheckBox, Spinner, Tab, RadioButton, etc.)
  - Distance distribution histogram
  - Token consumption and latency statistics
  - Per-app breakdown: which apps have best/worst grounding
  - Tool call success rate and error analysis
  - Comparison with Qwen3-VL December baseline (57.7%)

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

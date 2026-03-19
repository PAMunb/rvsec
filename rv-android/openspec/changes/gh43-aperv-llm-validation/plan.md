# gh43: APE-RV LLM Coordinate Mapping — Validation Module

**Date**: 2026-03-19
**Track**: FF SDD (upgraded from Quick Path)
**Priority**: High
**GitHub Issue**: #43
**Affected modules**: New module `aperv-llm-validation` (standalone, no integration with existing modules)

> **Note**: This plan.md is a supplementary context document retained from the Quick Path
> origin. The authoritative SDD artifacts are `proposal.md`, `design.md`, and `tasks.md`.
> Delta specs are not required because this is a standalone investigation module with no
> changes to existing module behavior or specifications.

### Related Documents

| Document | Content |
|----------|---------|
| `proposal.md` | Change proposal (WHY + WHAT + impact) |
| `design.md` | Architecture, data models, API, diagrams, decisions |
| `docs/20260318_aperv_coordenadas_gh46.md` | Investigation: no_match rate, mapToModelAction, timing gap |
| `docs/20260316_aperv_llm.md` | LLM integration modes, 19 calibration parameters |
| `docs/20260317_aperv_llm_rvandroid.md` | rv-android config keys, aperv-tool variants |
| `docs/20260317_aperv_comparacao.md` | Exp3 baseline: sata_mop_llm vs all tools |
| `docs/20260318_rvape_calibracao.md` | Calibration plan: MACRO/MICRO, Optuna TPE |
| `docs/vision/FINAL_REPORT.md` | Qwen3-VL benchmark: 57.7% hit rate on 468 screenshots |
| `docs/vision/004_prompt_engineering.md` | Prompt v2 strict, fallback parser |
| `openspec/changes/gh43-aperv-llm-validation/sota.md` | SOTA survey: 21 LLM Android testing tools, prompt analysis, positioning |

---

## Context

APE-RV's LLM integration has a 37.3% no_match rate (3,554/9,525 calls in exp3). Each no_match
wastes 1-3s of LLM overhead without benefit. The LLM variant (`aperv:sata_mop_llm` at 27.60%
method coverage) performed **worse** than the non-LLM baseline (`aperv:sata_mop_v1` at 28.35%,
p=0.014).

To investigate and reduce no_match, we need an offline validation environment that **replicates
the APE-RV LLM pipeline exactly** — same image processing, same prompt format, same coordinate
conversion, same matching algorithm. Only by replicating the exact behavior can we:

1. Test alternative prompts and measure their impact on match/no_match rate
2. Add a `reasoning` parameter to understand what the LLM intended when it produced a no_match
3. Classify no_match causes with a 7-category taxonomy (including `stale_model` for timing gap)
4. Establish a baseline before modifying the APE Java code
5. Validate that prompt improvements translate to better exploration, not just higher match rate

Prior work in `rvsec-vision-llm` established a visual grounding benchmark (57.7% hit rate with
Qwen3-VL-4B on 468 screenshots), but used different evaluation criteria (50px center tolerance
vs APE's bounds containment + Euclidean fallback). Components from rvsec-vision-llm will be
adapted to match APE's exact behavior.

### Consolidated Findings from Four Independent Analyses

Four LLMs (Claude, Codex, Gemini, Qwen) analyzed the original plan, followed by a second
round of five analyses (Claude, Codex, Gemini, MiniMax, Qwen) on the full artifact set
(proposal, design, plan, tasks, sota). Key consensus:

| Finding | Claude | Codex | Gemini | Qwen | Resolution |
|---------|--------|-------|--------|------|------------|
| Golden dataset from Java is essential | Yes | Yes | Yes | Yes | Added: golden fixtures with tolerances |
| Python/Java drift is risk #1 | Yes | Yes | Yes | Yes | Added: tolerance table in design.md |
| `reasoning` may alter LLM behavior | — | Yes | — | Yes | Added: validation gate (50 screenshots) |
| McNemar > t-test for binary paired data | — | Yes | — | — | Changed: McNemar as primary test |
| SGLang health check + cache | Yes | — | Yes | Yes | Added: SQLite response cache |
| Match rate alone is dangerous metric | — | Yes | — | — | Added: quality guardrails |
| `tolerance_miss` range inconsistent | — | Yes | — | — | Fixed: 50-100px (not 20-100px) |
| LLM response visualization | — | — | Yes | — | Added: annotated screenshot output |
| Holdout set | Yes | — | Yes | Yes | Decided: no holdout; report per-app variance |
| Dataset has 469 PNGs vs 468 XMLs | — | Yes | — | — | Added: orphan PNG handling |
| **Second round (5 LLMs)**: | | | | | |
| Add action-list variant (SOTA Approach A) | All 5 | All 5 | All 5 | All 5 | Added: `action_list` variant (Group 3.8, 8.5) |
| Harmonize Bonferroni (6 vs 7 vs 21 vs 15) | All 5 | All 5 | All 5 | All 5 | Fixed: 6 coord-based → 15 pairs, 0.0033; SoM+action_list separate |
| SoM incomparable with coordinate variants | All 5 | All 5 | All 5 | All 5 | Fixed: separate analysis, not in McNemar |
| Add quantitative success criteria | 4/5 | 4/5 | 4/5 | 4/5 | Added: Success Criteria section |
| Include temperature in cache key | 4/5 | 4/5 | 4/5 | 4/5 | Fixed: cache key includes temperature + resize_mode |
| Document offline limitations | 4/5 | 4/5 | 4/5 | 4/5 | Added: Limitations section in design.md |

---

## Scope

### New module: `modules/aperv-llm-validation/`

A uv workspace module that replicates the APE-RV LLM pipeline offline against screenshots
with UIAutomator XML ground truth. See `design.md` for full architecture, component diagrams,
data models, and API design.

### Pipeline Components (replicate APE Java in Python)

Each component replicates the exact behavior of its Java counterpart in the `ape` repo.
Fidelity is verified against a **golden dataset** generated by temporarily instrumenting the
APE Java code (`LlmRouter.selectAction()`) to export one JSON + PNG + XML per LLM call during
a normal `rv-experiment` run on 10 APKs (including cryptoapp) with 2-3 min timeout each.
All captured call data becomes golden fixtures. Instrumentation is local-only, NOT committed
to the APE repo. APE Java commit: `b2852dd`.

| Component | APE Java Source | Python Replica | Fidelity Criterion |
|-----------|----------------|----------------|-------------------|
| `ImageProcessor` | `ImageProcessor.java` | `pipeline/image_processor.py` | Dimensions exact; JPEG SSIM ≥ 0.98 |
| `PromptBuilder` | `ApePromptBuilder.java` | `pipeline/prompt_builder.py` | Exact string match |
| `ToolCallParser` | `ToolCallParser.java` | `pipeline/tool_call_parser.py` | Same parsed values |
| `CoordinateNormalizer` | `CoordinateNormalizer.java` | `pipeline/coordinate_normalizer.py` | Exact integers |
| `ActionMapper` | `LlmRouter.mapToModelAction()` | `pipeline/action_mapper.py` | Same widget, same step (±1px Euclidean) |
| `SglangClient` | `SglangClient.java` | `pipeline/sglang_client.py` | N/A (wrapper) |

### UIAutomator -> ModelAction Simulation

The 468 screenshots each have a `.uiautomator` XML with element bounds. We parse these to
simulate APE's ModelActions:

- Parse XML nodes with `clickable=true`, `enabled=true`, and valid bounds (area > 0)
- Filter like GUITreeBuilder: exclude system UI, invisible elements, zero-area nodes
- Build widget list in APE format with class name, text, bounds, normalized coordinates
- This simulates what `buildAndValidateNewState()` produces as ModelActions

**Note**: Dataset has 469 PNGs but only 468 XMLs (orphan: `cryptoapp.apk/009_novo.png`).
The evaluator skips PNGs without a matching `.uiautomator` file and logs a warning.

### Prompt Variants to Test

| ID | Name | Description | Source | Tests |
|----|------|-------------|--------|-------|
| `ape_current` | APE Production | Exact replica of `ApePromptBuilder.buildSystemMessage()` | `ape` repo | Production baseline |
| `ape_reasoning` | APE + Reasoning | Same as above but tool schema includes `reasoning` param | New | Reasoning field impact |
| `compact_v1` | Compact Strict | Minimal tokens, CRITICAL RULES, mandatory tool use | `004_prompt_engineering.md` v2 | Token efficiency |
| `rvsmart_v13` | RVSmart V13 | Dialog handling, JSON response format | `PromptBuilder.java` SYSTEM_V13 | Cross-tool transfer |
| `rvsmart_v17` | RVSmart V17 | 6-step reasoning, MOP-aware, test-status tags | `PromptBuilder.java` SYSTEM_V17 | MOP prompting |
| `visual_only` | Visual Only | No widget list — LLM uses only screenshot | `rvsec-vision-llm` | Widget list value |
| `som_overlay` | SoM Overlay | Numbered labels on screenshot, LLM returns element_id | SOTA Approach B (sota.md §8.1) | SoM grounding accuracy |
| `action_list` | Action-List | Numbered widget list, LLM returns action_id (no coordinates) | SOTA Approach A (sota.md §8.1) | Upper bound: 100% match by construction |

Variants are designed to test **orthogonal dimensions**: prompt text (verbose vs minimal vs
structured), widget list format (APE vs RVSmart vs none vs numbered list), and schema
(with/without reasoning, coordinate vs element selection).

**Statistical comparison**: The 6 coordinate-based variants (ape_current through visual_only)
form the main comparison set (15 pairwise McNemar tests). `som_overlay` and `action_list` use
different action spaces (element_id/action_id vs x,y) and are analyzed separately.
See `design.md` Section "Prompt Variant Architecture" for full analysis.

### Tool Schema with Reasoning

```json
{
  "name": "click",
  "parameters": {
    "x": {"type": "integer", "description": "X coordinate [0,1000)"},
    "y": {"type": "integer", "description": "Y coordinate [0,1000)"},
    "reasoning": {"type": "string", "description": "Brief reason for this action"}
  },
  "required": ["x", "y"]
}
```

The `reasoning` field is optional and NOT sent to production APE. It exists purely for
analysis. **Validation gate**: before using reasoning in analysis, confirm `ape_reasoning`
match rate is within ±2pp of `ape_current` on 50 screenshots (see design.md D6).

### Evaluation Methodology

For each screenshot x prompt variant:

1. Parse `.uiautomator` XML -> list of clickable widgets with bounds (simulated ModelActions)
2. Build prompt using the variant's format (widget list + screenshot)
3. Process screenshot through ImageProcessor replica (JPEG resize + base64)
4. Check response cache (SQLite) -> use cached response if available
5. If cache miss: send to SGLang (Qwen3-VL-4B), cache response
6. Parse response through ToolCallParser replica (3-level fallback)
7. Convert coordinates through CoordinateNormalizer replica
8. Run ActionMapper replica (5-step matching algorithm)
9. Record: match/no_match, action type, reasoning, distance, classification
10. Compute quality guardrails (container rate, semantic rate, diversity)

### Metrics

| Metric | What It Measures | Category |
|--------|------------------|----------|
| **Match rate** | % of LLM calls that map to a ModelAction | Primary |
| **No-match rate** | % of LLM calls with no matching ModelAction | Primary |
| **Tool call rate** | % of LLM responses that produce a valid tool call | Primary |
| **Quality score** | Composite: 0.6×match + 0.2×semantic + 0.1×type_text + 0.1×diversity | Primary |
| Container click rate | % of matches on generic containers (FrameLayout, etc.) | Guardrail |
| Semantic widget rate | % of matches on widgets with text/content_desc/resource_id | Guardrail |
| Back action rate | % of LLM calls returning back | Guardrail |
| type_text usage | % of calls that use type_text when EditText is present | Guardrail |
| Action diversity | Shannon entropy of action type distribution | Guardrail |
| Per-app consistency | Std dev of match rate across apps | Guardrail |
| Edge miss rate | % of no_match within 20px of a widget bound | Classification |
| Avg distance (no_match) | Mean distance to nearest widget center on no_match | Classification |
| Token consumption | Input + output tokens per call | Efficiency |
| Latency | ms per LLM call | Efficiency |

### No-match Classification (7-category taxonomy)

| Category | Criterion | Root Cause |
|----------|-----------|------------|
| `boundary_rejection` | `pixelY < 5%` or `pixelY > 94%` of screen height | LLM targeting status/nav bar |
| `edge_miss` | Nearest widget bound <= 20px | Imprecise grounding |
| `tolerance_miss` | Distance 50-100px from nearest widget center | Poor spatial reasoning |
| `gap` | Distance > 100px from any widget | Hallucination or dynamic element |
| `type_mismatch` | Widget exists at point but wrong action type | Wrong action inference |
| `few_widgets` | <= 2 clickable widgets in the screen | Structural (limited content) |
| `stale_model` | Element in screenshot absent from XML (via reasoning analysis) | Timing gap |

Note: `tolerance_miss` uses 50-100px range (matching Euclidean fallback minimum of 50px from
`max(50, min(w,h)/2)`), not 20-100px as in the original plan.

### LLM Response Cache

SQLite-backed persistent cache (see `design.md` D2):
- **Key**: `hash(screenshot_basename + prompt_name + rep_seed + temperature + resize_mode)`
- **Value**: Full OpenAI response + tokens + latency
- **Benefits**: Reproducibility (re-generate reports without LLM), resilience (SGLang restart),
  speed (skip cached calls on re-run)
- **CLI flags**: `--use-cache` (default) / `--no-cache` / `--cache-dir PATH`

### Statistical Methodology

- **Primary test**: McNemar test for pairwise prompt comparison (binary paired data)
- **Multiple comparisons**: Bonferroni correction for 6 coordinate-based variants (C(6,2) = 15
  pairs, threshold = 0.05/15 = 0.0033). `som_overlay` and `action_list` use different action
  spaces and are analyzed separately (not included in pairwise McNemar)
- **Confidence intervals**: Bootstrap 95% CI, stratified by app (10,000 resamples)
- **Repetition analysis**: Mean ± std across reps; Wilcoxon signed-rank on per-screenshot means
- See `design.md` Section "Statistical Methodology" for full rationale

---

## Replication Fidelity

### Golden Dataset

Temporarily instrument `LlmRouter.selectAction()` in the APE Java code with a
`GoldenFixtureExporter` that saves 3 files per LLM call: JSON (all intermediaries),
PNG (screenshot), and UIAutomator XML (dump) — both captured at the moment of that call.
Files are written to the emulator filesystem (`/data/local/tmp/golden/`), then pulled to the
host via `adb pull` after each APK run.

Run `rv-experiment` on 10 APKs (including cryptoapp) × 2-3 min timeout. All captured call
data becomes golden fixtures. The instrumentation is local-only — NOT committed to the APE
repo. APE Java commit pinned: `b2852dd`.

### Golden Fixture Contents (per LLM call — JSON + PNG + XML)

| Field | Content | Tolerance |
|-------|---------|-----------|
| `screenshot_file` | Reference to companion `.png` | — |
| `uiautomator_file` | Reference to companion `.uiautomator` | — |
| `resize` | `(orig_w, orig_h, new_w, new_h)` | Exact |
| `jpeg_base64_sha256` + `first100` | JPEG hash and prefix | SSIM >= 0.98 |
| `system_message` + `user_text` | Full prompt strings | Exact |
| `widget_list` | Formatted string | Exact |
| `parsed_action` | `type, x, y, text` from ToolCallParser | Exact |
| `pixel_coords` | `[pixelX, pixelY]` from CoordinateNormalizer | Exact |
| `match_result` | `step, widget_index, distance` | Same widget (±1px Euclidean) |

---

## File Inventory

See `design.md` Section "File Inventory" for full directory tree. Key additions vs original plan:

| File | Purpose | Tier |
|------|---------|------|
| `infrastructure/response_cache.py` | SQLite LLM response cache | Tier 2 |
| `evaluation/quality_guardrails.py` | Container rate, semantic rate, diversity | Tier 2 |
| `tests/test_quality_guardrails.py` | Unit tests for guardrails | Tier 2 |
| `tests/test_response_cache.py` | Cache CRUD + stats tests | Tier 2 |
| `tests/test_golden_fidelity.py` | Golden dataset validation | Tier 1 |
| `tests/fixtures/golden/` | Java pipeline outputs (10 APKs × 2-3 min, all LLM calls) | Tier 1 |
| `prompts/registry.py` | Prompt variant registry | New |
| `scripts/generate_golden_fixtures.sh` | Instructions for Java fixture generation | Tier 1 |

---

## Execution Order

```
=== IMPLEMENTATION (Groups 1-6) ===

Group 0: Golden Fixture Preparation (prerequisite)
  Instrument APE Java (local-only, commit b2852dd), run rv-experiment on 10 APKs × 2-3 min,
  pull JSON+PNG+XML fixtures from emulator, copy to tests/fixtures/golden/

Group 1: Module Infrastructure (sequential)
  Create module dir, pyproject.toml, constants, models, cache

Group 2: Pipeline Components (parallel — 3 subagents)
  2A: image_processor + coordinate_normalizer + tests + golden fidelity
  2B: tool_call_parser + action_mapper + tests + golden fidelity
  2C: uiautomator_parser + prompt_builder + tests + golden fidelity

Group 3: Prompt Variants (sequential)
  Define 7 prompt variants + registry, verify format matches APE
  (6 coordinate-based + action_list; som_overlay in Group 3.5)

Group 4: Evaluation Engine (sequential, depends on 2+3)
  evaluator + nomatch_classifier + quality_guardrails + reporter + CLI + cache integration

Group 5: Integration Test (sequential, depends on 4)
  End-to-end: 5 screenshots × 2 prompts → verify pipeline
  Reasoning validation gate: 50 screenshots × ape_current vs ape_reasoning

Group 6: Implementation Verification
  lint-fix, verify, acceptance criteria

=== EXECUTION (Groups 7-9, requires SGLang at 192.168.0.36) ===

Group 7: Baseline Run (SGLang health check first)
  ape_current (468 screenshots × 1 rep) → establishes offline baseline (~62% match expected)
  ape_reasoning (468 × 1 rep) → same baseline + reasoning texts for analysis

Group 8: Prompt Comparison
  compact_v1, rvsmart_v13, rvsmart_v17, visual_only, som_overlay, action_list (468 × 1 rep each)

Group 9: Deep Evaluation
  Top-2 prompts × 468 screenshots × 3 reps (statistical significance)
  Top-2 prompts × 30 hard screenshots × 3 reps (focus on worst cases)
  Top-2 selection: match rate primary, tiebreaker by variance → type_text → diversity → token cost

=== ANALYSIS (Groups 10-11) ===

Group 10: Reports
  Per-prompt comparison (McNemar + Bonferroni), quality guardrail analysis,
  no_match classification, reasoning analysis, per-screenshot difficulty,
  per-app consistency, visualizations (annotated screenshots), final summary

Group 11: Conclusions
  Update investigation plan, create optimized prompt for APE Java,
  plan Phase A'/C adjustments
```

### Estimated Execution Time (Groups 7-9)

Assumptions: ~2s per LLM call (Qwen3-VL-4B on SGLang), 468 screenshots, cache reduces
re-runs to near-zero.

| Run | Calls | Time |
|-----|-------|------|
| Group 7: 2 prompts × 468 × 1 rep | 936 | ~31 min |
| Group 8: 6 prompts × 468 × 1 rep | 2,808 | ~94 min |
| Group 9: 2 prompts × 468 × 3 reps | 2,808 | ~94 min |
| Group 9: 2 prompts × 30 × 3 reps | 180 | ~6 min |
| **Total** | **6,732** | **~3.7 hours** |

---

## Success Criteria

Quantitative thresholds for interpreting results:

| Result | Interpretation | Action |
|--------|---------------|--------|
| Best coordinate variant ≥ 75% match + quality ≥ 0.70 | Prompt improvement viable | Port best prompt to APE Java |
| Best coordinate variant 65-75% | Marginal; timing gap likely dominates | Prioritize gh46 |
| Best coordinate variant < 65% | Coordinate prediction fundamentally limited | Recommend action-list/SoM |
| smart_resize ≥ +5pp hit rate | Image processing bottleneck | Apply smart_resize in Java |
| `stale_model` > 30% of no_match | Timing gap is primary cause | Confirms gh46 priority |

---

## Acceptance Criteria

### Implementation (Groups 0-6)

- [ ] Golden fixtures generated from APE Java commit `b2852dd` (10 APKs × 2-3 min, all LLM calls)
- [ ] Module installs cleanly via `uv sync` (workspace member via `modules/*` glob)
- [ ] Pipeline components replicate APE Java behavior (verified by golden fidelity tests)
- [ ] `ImageProcessor`: Resize dimensions exact; JPEG SSIM >= 0.98 vs Java output
- [ ] `CoordinateNormalizer`: `qwen_to_pixel(500, 500, 1080, 1920)` -> `(540, 960)` exact
- [ ] `ActionMapper`: Same widget selected, same algorithm step, for all golden fixtures
- [ ] `ToolCallParser`: 3-level fallback handles native, XML, inline JSON; malformed fixes match APE
- [ ] Response cache: put/get round-trip, stats, concurrent access
- [ ] Quality guardrails: container rate, semantic rate, back rate, diversity computed correctly
- [ ] 7 prompt variants defined, registered, and tested (6 coordinate-based + action_list; som_overlay in Group 3.5)
- [ ] Reasoning validation gate: `ape_reasoning` within ±2pp of `ape_current` on 50 screenshots
- [ ] No-match classifier: 7 categories with correct distance thresholds
- [ ] All tests pass (~82 tests), lint clean

### Execution (Groups 7-9)

- [ ] SGLang health check passes before each group
- [ ] Baseline run completed: ape_current match rate measured (expected ~62%)
- [ ] All 8 prompt variants evaluated on full 468-screenshot dataset (6 coordinate + SoM + action_list)
- [ ] Top-2 prompts selected using formal criteria (match rate + tiebreakers)
- [ ] Top-2 prompts evaluated with 3 repetitions for statistical significance
- [ ] Hard-screenshot subset (30) evaluated with top-2 prompts

### Analysis (Groups 10-11)

- [ ] McNemar pairwise comparison with Bonferroni correction
- [ ] Quality guardrail report: container rate, semantic rate, back rate per prompt
- [ ] No-match classification report with 7-category distribution per prompt
- [ ] Reasoning analysis: "correct intent, wrong coords" vs "wrong intent"
- [ ] Per-app match rate consistency analysis
- [ ] Visualizations: annotated no_match screenshots (top-10 cases)
- [ ] Final summary with best prompt recommendation + quality score
- [ ] Optimized prompt ready for APE Java implementation

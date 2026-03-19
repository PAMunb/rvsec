# gh43: APE-RV LLM Coordinate Mapping — Validation Module

**Date**: 2026-03-19
**Track**: FF SDD (upgraded from Quick Path)
**Priority**: High
**GitHub Issue**: #43
**Affected modules**: New module `aperv-llm-validation` (analysis toolkit), APE Java (temporary branch)

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

### Consolidated Findings from Four Independent Analyses

Four LLMs (Claude, Codex, Gemini, Qwen) analyzed the original plan, followed by a second
round of five analyses (Claude, Codex, Gemini, MiniMax, Qwen) on the full artifact set
(proposal, design, plan, tasks, sota). Key consensus:

| Finding | Claude | Codex | Gemini | Qwen | Resolution |
|---------|--------|-------|--------|------|------------|
| Python/Java drift is risk #1 | Yes | Yes | Yes | Yes | **Eliminated**: test in Java directly |
| `reasoning` may alter LLM behavior | — | Yes | — | Yes | Added: validation gate (50 screenshots) |
| McNemar > t-test for binary paired data | — | Yes | — | — | Changed: McNemar as primary test |
| SGLang health check + cache | Yes | — | Yes | Yes | Added: SQLite response cache (pre-validation) |
| Match rate alone is dangerous metric | — | Yes | — | — | **Resolved**: use real coverage metrics |
| Add action-list variant (SOTA Approach A) | All 5 | All 5 | All 5 | All 5 | Deferred: requires tool schema + Java matching changes |
| Harmonize Bonferroni (6 vs 7 vs 21 vs 15) | All 5 | All 5 | All 5 | All 5 | Fixed: 6 coord-based → 15 pairs, 0.0033 |
| SoM incomparable with coordinate variants | All 5 | All 5 | All 5 | All 5 | Deferred: separate change with tool schema |
| Add quantitative success criteria | 4/5 | 4/5 | 4/5 | 4/5 | Added: coverage-based thresholds |
| Include temperature in cache key | 4/5 | 4/5 | 4/5 | 4/5 | Fixed: cache key includes temperature + resize_mode |
| Document offline limitations | 4/5 | 4/5 | 4/5 | 4/5 | **Eliminated**: testing online with real APKs |

### Strategy Pivot

The original design replicated the APE Java LLM pipeline in Python for offline testing against
static screenshots. After analysis, we identified critical risks: Python/Java implementation
drift, match rate as a proxy metric (higher match rate does not guarantee better coverage),
and inability to capture timing-dependent effects (stale_model).

The pivot: implement prompt variants directly in APE Java (temporary branch) and test with
rv-experiment on real instrumented APKs. This approach provides real coverage metrics (method,
activity, MOP), eliminates drift risk entirely, and reuses the same infrastructure validated
in exp3. The Python module becomes an analysis toolkit for pre-validation and results analysis,
not a pipeline replica.

---

## Scope

### Python module: `modules/aperv-llm-validation/` (analysis toolkit)

An analysis toolkit with three responsibilities:

1. **Pre-validation** (Group 0.5): grounding test on 468 screenshots via SGLang (Qwen3.5-4B, raw mode)
2. **Results parsing**: parse rv-experiment output directories to extract per-APK coverage
3. **Statistical analysis + reports**: McNemar tests, Bonferroni correction, quality guardrails,
   visualizations

The module does NOT replicate pipeline components (prompt building, tool call parsing,
coordinate normalization, action matching). Those run in the real APE Java code.

### APE Java: Temporary branch `gh43-prompt-variants`

6 coordinate-based prompt variants implemented as Java string constants in `ApePromptBuilder`.
The variant is selected via a configuration parameter (e.g., `ape.llm.prompt_variant=compact_v1`).
Enhanced telemetry in `LlmRouter` logs no-match details for post-hoc analysis.

This branch is NOT merged to APE master. Only the winning variant is ported after validation.

### Prompt Variants (6 coordinate-based)

| ID | Name | Description | Source |
|----|------|-------------|--------|
| `ape_current` | APE Production | Current `ApePromptBuilder.buildSystemMessage()` | `ape` repo (baseline) |
| `ape_reasoning` | APE + Reasoning | Same + tool schema includes `reasoning` param | New |
| `compact_v1` | Compact Strict | Minimal tokens, CRITICAL RULES, mandatory tool use | `004_prompt_engineering.md` v2 |
| `rvsmart_v13` | RVSmart V13 | Dialog handling, JSON response format | `PromptBuilder.java` SYSTEM_V13 |
| `rvsmart_v17` | RVSmart V17 | 6-step reasoning, MOP-aware, test-status tags | `PromptBuilder.java` SYSTEM_V17 |
| `visual_only` | Visual Only | No widget list — LLM uses only screenshot | `rvsec-vision-llm` |

**Deferred**: `som_overlay` (SoM) and `action_list` require changes to APE's tool schema and
`mapToModelAction()` matching algorithm. These are separate changes.

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

The `reasoning` field is optional. **Validation gate**: since both `ape_current` and
`ape_reasoning` run as full rv-experiment variants, validation happens by comparing their
coverage results. If `ape_reasoning` is within ±2pp of `ape_current` on method coverage
and match rate, reasoning texts are safe to use for no-match analysis.

### Evaluation Methodology

1. **Pre-validation** (Python, offline): raw grounding test on 468 screenshots via SGLang (Qwen3.5-4B)
2. **Prompt comparison** (Java, online): rv-experiment runs each variant on 10 instrumented
   APKs × 2.5 min timeout × 3 reps. rv-experiment produces standard results directories with
   method/activity/MOP coverage per APK.
3. **Analysis** (Python, offline): parse rv-experiment results, compute statistics, generate
   reports

### Metrics

| Metric | Source | Category |
|--------|--------|----------|
| **Method coverage** | rv-experiment results | Primary |
| **Activity coverage** | rv-experiment results | Primary |
| **MOP coverage** | rv-experiment results | Primary |
| Match rate | Java telemetry logs | Secondary |
| No-match rate | Java telemetry logs | Secondary |
| Container click rate | Java telemetry logs | Guardrail |
| Back action rate | Java telemetry logs | Guardrail |
| type_text usage | Java telemetry logs | Guardrail |
| Token consumption | Java telemetry logs | Efficiency |
| Latency | Java telemetry logs | Efficiency |
| raw grounding hit rate | Pre-validation | Pre-validation |

### No-match Classification (7-category taxonomy)

Analyzed from Java telemetry logs, not computed in Python.

| Category | Criterion | Root Cause |
|----------|-----------|------------|
| `boundary_rejection` | `pixelY < 5%` or `pixelY > 94%` of screen height | LLM targeting status/nav bar |
| `edge_miss` | Nearest widget bound <= 20px | Imprecise grounding |
| `tolerance_miss` | Distance 50-100px from nearest widget center | Poor spatial reasoning |
| `gap` | Distance > 100px from any widget | Hallucination or dynamic element |
| `type_mismatch` | Widget exists at point but wrong action type | Wrong action inference |
| `few_widgets` | <= 2 clickable widgets in the screen | Structural (limited content) |
| `stale_model` | Element in screenshot absent from XML (via reasoning analysis) | Timing gap |

### LLM Response Cache

SQLite-backed persistent cache for **pre-validation only** (see `design.md` D2):
- **Key**: `hash(screenshot_basename + prompt_name + rep_seed + temperature + resize_mode)`
- **Value**: Full OpenAI response + tokens + latency
- **CLI flags**: `--use-cache` (default) / `--no-cache` / `--cache-dir PATH`

### Statistical Methodology

- **Primary test**: McNemar test on per-APK coverage outcomes (binary: improved/not improved
  vs baseline)
- **Multiple comparisons**: Bonferroni correction for 6 coordinate-based variants (C(6,2) = 15
  pairs, threshold = 0.05/15 = 0.0033)
- **Confidence intervals**: Bootstrap 95% CI, stratified by app (10,000 resamples)
- **Repetition analysis**: Mean ± std across 3 reps per variant per APK
- See `design.md` for full rationale

---

## File Inventory

See `design.md` Section "File Inventory" for full directory tree. Key files:

| File | Purpose |
|------|---------|
| `analysis/pre_validation.py` | smart_resize grounding test execution |
| `analysis/results_parser.py` | Parse rv-experiment output directories |
| `analysis/statistics.py` | McNemar, Bonferroni, bootstrap CI |
| `analysis/nomatch_classifier.py` | 7-category taxonomy from telemetry logs |
| `analysis/quality_guardrails.py` | Container rate, semantic rate, diversity |
| `analysis/reporter.py` | Generate comparison reports + visualizations |
| `infrastructure/response_cache.py` | SQLite LLM response cache (pre-validation) |
| `infrastructure/sglang_client.py` | SGLang wrapper (pre-validation) |
| `cli/main.py` | CLI entry point |
| `tests/` | Unit and integration tests |

---

## Execution Order

```
=== Track A: APE Java Prompt Variants (Group 0) ===

Group 0: APE Java (temporary branch gh43-prompt-variants)
  Create branch from APE master. Add 6 prompt variant string constants in
  ApePromptBuilder. Add variant selection via config parameter. Add enhanced
  telemetry in LlmRouter (no-match details). Verify each variant produces
  valid prompts via unit test.

=== Track B: Python Pre-validation (Group 0.5, independent) ===

Group 0.5: Pre-validation
  Raw grounding test on 468 screenshots via SGLang with Qwen3.5-4B (~2-5h).
  Establishes baseline coordinate accuracy before prompt comparison.
  3-mode comparison already done: raw > smart_resize > max_edge (see exploration doc).

=== Track C: Python Analysis Module (Group 1, parallel with A) ===

Group 1: Analysis Toolkit
  Module skeleton (pyproject.toml, constants, models).
  Results parser for rv-experiment output directories.
  Statistics module (McNemar, Bonferroni, bootstrap CI).
  No-match classifier (7-category taxonomy from telemetry).
  Quality guardrails (container rate, back rate, diversity).
  Reporter (comparison tables, visualizations).
  CLI entry point.
  Tests.

=== Track D: Execution + Analysis (Groups 2-4, after A+C) ===

Group 2: rv-experiment Execution
  Run rv-experiment with each of the 6 variants on 10 instrumented APKs
  × 2.5 min timeout × 3 reps. Total: 6 × 10 × 3 = 180 runs (~9h).
  Collect results directories + telemetry logs.

Group 3: Statistical Analysis
  Parse results. McNemar pairwise comparison with Bonferroni correction.
  No-match classification from telemetry. Quality guardrail analysis.
  Per-app consistency analysis.

Group 4: Reports + Conclusions
  Generate comparison report. Identify best variant.
  If best ≥ +3pp method coverage → port to APE master.
  Update investigation plan, plan Phase A'/C adjustments.
```

### Estimated Execution Time

| Phase | Computation | Time |
|-------|-------------|------|
| Pre-validation (Group 0.5) | 468 screenshots × all visible text widgets × raw mode × temp 0.7 × ~2s | ~2-5h |
| rv-experiment (Group 2) | 6 variants × 10 APKs × 3 reps × 2.5 min | ~9h (7.5h + overhead) |
| Analysis (Groups 3-4) | Offline parsing + statistics | ~1h |
| **Total** | | **~14-21h** |

---

## Success Criteria

Quantitative thresholds for interpreting results (based on real coverage, not match rate):

| Result | Interpretation | Action |
|--------|---------------|--------|
| Best variant ≥ +3pp method coverage over baseline | Prompt improvement viable | Port best prompt to APE master |
| Best variant +1-3pp method coverage | Marginal improvement | Prioritize gh46 (timing gap) |
| Best variant ≤ baseline method coverage | Prompt is not the issue | Focus on timing gap and architecture |
| raw mode ≥ +5pp over max_edge in pre-validation | Image resize is hurting accuracy | Eliminate resize in Java |
| `stale_model` > 30% of no_match (from telemetry) | Timing gap is primary cause | Confirms gh46 priority |

---

## Acceptance Criteria

### Track A: APE Java (Group 0)

- [ ] Temporary branch `gh43-prompt-variants` created from APE master
- [ ] 6 prompt variants as string constants in `ApePromptBuilder`
- [ ] Variant selectable via configuration parameter
- [ ] Enhanced telemetry in `LlmRouter` (no-match coordinates, distance, classification)
- [ ] Each variant produces valid prompts (verified by unit test)

### Track B: Pre-validation (Group 0.5)

- [x] Model validated: Qwen3.5-4B (no thinking) on SGLang v0.5.9 with raw mode
- [x] 3-mode comparison completed: raw > smart_resize > max_edge
- [x] Smoke tests: 66.2% center hit (100 screenshots), 51.8% (cryptoapp with tabs/spinners)
- [ ] Full 468-screenshot pre-validation with raw mode
- [ ] Results cached in SQLite for reproducibility
- [ ] Hit rate report generated

### Track C: Python Analysis Module (Group 1)

- [ ] Module installs cleanly via `uv sync` (workspace member via `modules/*` glob)
- [ ] Results parser correctly reads rv-experiment output directories
- [ ] Statistics module computes McNemar + Bonferroni correctly
- [ ] No-match classifier handles 7-category taxonomy from telemetry logs
- [ ] Reporter generates comparison tables and visualizations
- [ ] All tests pass, lint clean

### Track D: Execution + Analysis (Groups 2-4)

- [ ] All 6 variants executed on 10 APKs × 3 reps via rv-experiment
- [ ] McNemar pairwise comparison with Bonferroni correction completed
- [ ] No-match classification report from telemetry logs
- [ ] Quality guardrail analysis (container rate, back rate, diversity)
- [ ] Per-app coverage consistency analysis
- [ ] Final summary with best variant recommendation and coverage deltas

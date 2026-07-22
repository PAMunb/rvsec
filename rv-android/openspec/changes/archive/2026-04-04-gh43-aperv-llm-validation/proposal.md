# Proposal: gh43 — APE-RV LLM Coordinate Mapping Validation

**Date**: 2026-03-19
**Track**: FF SDD (upgraded from Quick Path — design decisions warrant formal design document)
**GitHub Issue**: #43

---

## Why

APE-RV's LLM integration has a 37.3% no_match rate (3,554/9,525 calls in exp3). Each no_match
wastes 1-3s of LLM overhead without benefit. The LLM variant (`aperv:sata_mop_llm` at 27.60%
method coverage) performed **worse** than the non-LLM baseline (`aperv:sata_mop_v1` at 28.35%,
p=0.014). Before investing ~131h of compute in calibration (MACRO+MICRO), we need to understand
**why** the LLM is hurting rather than helping.

A state-of-the-art survey of 21 LLM-driven Android testing tools (see `sota.md`), followed by
deep source code analysis of 10 open-source repositories, validated the approach and informed
the design with SOTA-grounded improvements. The survey revealed that APE-RV's coordinate
prediction approach is unique — all mature tools use action-list selection or Set-of-Marks
instead — confirming the need for systematic prompt validation.

The deep analysis also uncovered that APE-RV's image preprocessing (max-edge 1000px) is not
optimized for Qwen3-VL's vision encoder (patch_size=16, requiring dimensions divisible by 32),
and that APE-RV is the only tool with a 3-space coordinate pipeline (resized image → Qwen
normalized → device pixels), introducing error accumulation.

Initial design replicated the Java pipeline in Python for offline testing against static
screenshots. After analysis, we pivoted to testing directly via rv-experiment with real APKs —
this provides real coverage metrics (method, activity, MOP) instead of match rate proxies,
eliminates Python/Java drift risk, and uses the same infrastructure already validated in exp3.

## What Changes

- **Temporary APE Java branch** (`gh43-prompt-variants`): 6 coordinate-based prompt variants
  implemented as Java string constants in `ApePromptBuilder`, selectable via configuration.
  Branch is NOT merged to APE master — only the winning variant is ported after validation.
- **Enhanced telemetry** in `LlmRouter`: logs no-match details (coordinates, nearest widget,
  distance, classification) for post-hoc analysis of the 7-category taxonomy
- **Pre-validation phase** (Group 0.5): pure grounding test comparing max-edge 1000px vs
  smart_resize(factor=32) image preprocessing — isolates VLM spatial accuracy before prompt
  investment (~7h SGLang, per-widget grounding on 468 screenshots)
- **smart_resize(factor=32)**: Qwen3-VL-optimized image preprocessing (patch_size=16 ×
  merge_size=2), replacing generic max-edge resize if pre-validation confirms improvement
- **Python analysis module** `modules/aperv-llm-validation/`: analysis toolkit for
  pre-validation execution, rv-experiment results parsing, statistical comparison, and
  report generation. NOT a pipeline replica — does not replicate prompt building, tool call
  parsing, or coordinate normalization
- **6 coordinate-based prompt variants** compared on real coverage metrics via rv-experiment
  (SoM and action-list deferred to future change — require tool schema changes + Java matching
  algorithm modifications)
- **No-match taxonomy** with 7 classification categories (adds `stale_model` for timing gap),
  analyzed from Java telemetry logs
- **Coordinate space analysis**: documents APE-RV's unique 3-space pipeline and 999 vs 1000
  normalization asymmetry
- **LLM response cache** (SQLite) for pre-validation reproducibility and resilience
- **Statistical analysis** using McNemar test (binary paired data on per-APK coverage outcomes)
  with Bonferroni correction for 6 variants (15 pairs, threshold 0.0033)
- **Quality guardrails** beyond coverage: widget class distribution, container click rate,
  back rate, type_text appropriateness (from telemetry)

## Capabilities

### New Capabilities

- **validation**: LLM prompt validation analysis toolkit (`modules/aperv-llm-validation/`) —
  pre-validation execution, rv-experiment results parsing, statistical comparison, and
  report generation

### Modified Capabilities

_(none — standalone analysis module with no changes to existing specs)_

## Impact

| Area | Impact |
|------|--------|
| **Affected modules** | New: `aperv-llm-validation` (analysis toolkit). Modified: APE Java (temporary branch only) |
| **Dependencies** | openai, Pillow, pydantic, rich (Python); APE Java repo (temporary branch) |
| **External systems** | SGLang server (pre-validation), rv-experiment + emulator (prompt comparison) |
| **Data** | 468 screenshots for pre-validation; 10 instrumented APKs for rv-experiment |
| **Compute** | ~4-11h pre-validation (Group 0.5, per-widget grounding) + ~9h rv-experiment (6 variants × 10 APKs × 3 reps × 2.5 min) |
| **Downstream** | Findings feed into calibration plan (D4) and APE Java prompt optimization |
| **Related FRs** | Supports FR21-FR32 (rv-agent) indirectly via LLM pipeline understanding |

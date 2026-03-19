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

An offline validation environment that replicates the APE-RV LLM pipeline exactly enables:
testing alternative prompts, classifying no_match root causes, measuring overhead vs benefit,
and establishing an empirical baseline before any Java code changes.

A state-of-the-art survey of 21 LLM-driven Android testing tools (see `sota.md`), followed by
deep source code analysis of 10 open-source repositories, validated the approach and informed
the design with SOTA-grounded improvements. The survey revealed that APE-RV's coordinate
prediction approach is unique — all mature tools use action-list selection or Set-of-Marks
instead — confirming the need for offline validation before Java changes.

The deep analysis also uncovered that APE-RV's image preprocessing (max-edge 1000px) is not
optimized for Qwen3-VL's vision encoder (patch_size=16, requiring dimensions divisible by 32),
and that APE-RV is the only tool with a 3-space coordinate pipeline (resized image → Qwen
normalized → device pixels), introducing error accumulation.

## What Changes

- **New standalone module** `modules/aperv-llm-validation/`: offline replication of the APE-RV
  LLM pipeline (image processing, prompt building, tool call parsing, coordinate normalization,
  action matching) running against 468 screenshots with UIAutomator XML ground truth
- **Pre-validation phase** (Group 0.5): pure grounding test comparing max-edge 1000px vs
  smart_resize(factor=32) image preprocessing — isolates VLM spatial accuracy before prompt
  investment (~1-1.5h SGLang)
- **smart_resize(factor=32)**: Qwen3-VL-optimized image preprocessing (patch_size=16 ×
  merge_size=2), replacing generic max-edge resize if pre-validation confirms improvement
- **7 prompt variants** compared on match rate, action quality, token efficiency, and latency
  (6 coordinate-based + 1 SoM fallback for comparison)
- **No-match taxonomy** with 7 classification categories (adds `stale_model` for timing gap)
- **Coordinate space analysis**: documents APE-RV's unique 3-space pipeline and 999 vs 1000
  normalization asymmetry
- **Golden dataset** from Java pipeline for replication fidelity verification
- **LLM response cache** (SQLite) for reproducibility and resilience
- **Statistical analysis** using McNemar test (binary paired data) instead of t-test/Wilcoxon
- **Quality guardrails** beyond match rate: widget class distribution, container click rate,
  back rate, type_text appropriateness

## Capabilities

### New Capabilities

- **validation**: Offline LLM pipeline validation module (`modules/aperv-llm-validation/`)

### Modified Capabilities

_(none — standalone module with no changes to existing specs)_

## Impact

| Area | Impact |
|------|--------|
| **Affected modules** | New: `aperv-llm-validation` (standalone, no integration with existing modules) |
| **Dependencies** | openai, Pillow, pydantic, rich, defusedxml |
| **External systems** | SGLang server (Qwen3-VL-4B at `http://192.168.0.36:30000/v1`) |
| **Data** | 468 screenshots in `/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/` |
| **Compute** | ~1-1.5h pre-validation (Group 0.5) + ~3.2h full evaluation (Groups 7-9) |
| **Downstream** | Findings feed into calibration plan (D4) and APE Java prompt optimization |
| **Related FRs** | Supports FR21-FR32 (rv-agent) indirectly via LLM pipeline understanding |

# Proposal: gh88-cal-llm-control

**GitHub Issue**: #88
**Track**: Full SDD
**Date**: 2026-07-23

## Why

The APE-RV LLM calibration campaign (planning docs `docs/20260721_plano_calibracao_llm.md` rev. 3.2 and `docs/20260721_metodologia_calibracao_loop.md`) is approved at the plan level but has no executable support: the 11 Phase-A arms do not exist as named variants, and the autonomous-loop state machine (CONFIG-GEN → PRE-FLIGHT → SMOKE → RUN+MONITOR → CONSOLIDATE → VERIFY → ANALYZE → DECIDE) has no scaffold. Without named `cal_*` variants, arms that differ only in LLM keys would have to use `@override` — but task identity `(apk, tool, variant, rep, timeout)` strips the `@` suffix, so override-only arms collide and are silently skipped on resume. Without the scaffold, every iteration would be hand-assembled (composes, filters, smoke checks, consolidation), which is exactly the class of error the methodology's independent-verifier design exists to prevent.

This change merges the methodology's R1 (`cal-llm-arms`) and R2 (`cal-experiment-scaffold`) into a single control change, because they are jointly the prerequisite of Phase A: the scaffold's PRE-FLIGHT gate (11+ distinct identities, manifest×`get_variants()` audit) is unverifiable without the variants existing, and the variants are unusable without the scaffold that generates and audits their deployment.

## What Changes

- **`aperv-tool` (R1)**: add 9 named calibration variants `cal_a1`…`cal_a9` to `get_variants()` matching the plan §6 arm table, all on the `sata_mop_act_frontier` substrate — the cmpma-winning algorithmic configuration; when a step is not delegated to the LLM, the arm explores in frontier mode (ANC1 is the `ape` builtin tool; ANC2 is the existing `sata_mop_act_frontier` — 9 new variants complete the 11 arms, and `cal_* − ANC2` isolates the LLM contribution on the same algorithmic base). Add a `LLM_ARM_KEYS` guard requiring every `cal_*` variant to declare ALL LLM keys explicitly, closing the INV-APV-14 gap where `_LLM_FLAGS` omits `llm_percentage` and `llm_prompt_variant`. Add two `APERV_PROPERTY_MAPPING` entries: `llm_max_tokens` → `ape.llmMaxTokens` and `llm_snap_tolerance_px` → the Phase-B (J1) snapping property (inert until the Phase-B jar exists).
- **`experimento-cal/` + `calibracao/` scaffold (R2)**: one deterministic, testable script per loop state; state transitions are agent-driven following the methodology, with fixed human gates G1–G4:
  - **config-gen**: per-iteration `iterN/manifest.json` (per arm: variant name, complete key dict, expected `[APE-LLM-CONFIG]` string, predicted identities); snapshots `tool.py` (and `ape-rv.jar` in Phase B) into `iterN/artifacts/` with recorded hashes; generates composes (shared SGLang + 8 containers with arm-order rotation) and APK filters from the manifest — never by hand.
  - **preflight**: independent audit of manifest × composes × `get_variants()`; dry-run confirming 11+ distinct task identities; fixed image `phtcosta/rvandroid:0.9.3` (`87744cd58be9`); bind-mounted artifact hashes equal to the manifest.
  - **smoke-gate**: smoke compose (4 APKs × extreme arms, 90s, 1 rep) plus a checker: `[APE-LLM-CONFIG]` equals the manifest field-by-field per arm, `server_model` correct, coverage > 0, 0 VerifyError.
  - **monitor/resume**: fixed-cadence monitor; auto-restart only OOM exit-137 containers (standing authorization); auto-resume of ERROR tasks by dedup identity; completion criterion = non-empty logcats per identity, never COMPLETED counts.
  - **consolidate**: from raw logcats (anti-gh58), dedup by identity, producing `iterN/per_apk_paired.csv` + `iterN/tel_proxies.csv` for N arms.
  - **verify**: independent verification via a code path forbidden to reuse `consolidate_compare.py`/`analyze_cmpv2_llm.py` — direct `RVSEC-COV`/`RVSEC` marker re-derivation, config-ack == manifest in 100% of LLM tasks, 0 identity collisions, 100% paired completeness, contention gate (per-arm median time_ms ≤ 2× global median), divergence 0 on integer counts / ≤ 0.01pp on percentages.
  - **analyze**: pre-declared gate order (proxy elimination → trimmed-mean + paired bootstrap B≥10,000 fixed-seed ranking vs ANC1/ANC2 → mechanistic prediction-vs-observed check → between-reps determinism), using `stats_utils.py` **vendored (copied) into the scaffold** from `rvsec-calibracao` — not imported at runtime; new multi-arm Friedman+Holm script (descriptive only).
  - **decide + journal**: `iterN/decision.md` template encoding the declarative per-phase rules (screening promotes top-k, never concludes by p-value); append-only `calibracao/journal.jsonl` with one record per state transition (timestamp, iteration, state, artifact, hash).
  - **status (acompanhamento)**: `status.py` derives the current campaign position from the journal + `iterN/` artifacts + phase configs (never a hand-maintained file) — per-iteration done/current/pending across the eight states, the pending human gate, the next action, and a cross-iteration decision summary. This is what makes the agent-driven loop trackable: any session answers "where are we / what's next" without reconstructing state by hand.

This change is also the calibration campaign's **tracking vehicle**: every phase — Fase 0 (subset + no-match inputs), Phase A (`cala`), Phase B (`calb`), Phase C (`calc`) — is registered as a task in `tasks.md`, which serves as the campaign management checklist, and the change closes only when the calibration concludes (final-experiment config ratified at gate G4). The per-iteration loop state (CONFIG-GEN→DECIDE) stays DERIVED by `status.py` from the journal (INV-CAL-14); the tasks track phase milestones and the human gates G1–G4, never the loop states (a hand-maintained loop status would drift from the artifacts).

Out of scope: R3 (micro-Optuna driver — optional, its own change if P10 is approved) and J1–J4 (`ape` repo code changes, human gate G2 — tracked in the `ape` repo; Phase B consumes their locally built, bytecode-audited jar as an external dependency, not as gh88 code).

## Capabilities

### New Capabilities
- `calibration-control`: the calibration-campaign control scaffold — manifest-driven config generation with artifact snapshots, independent pre-flight audit, smoke gating, run monitoring/resume policy, N-arm consolidation, independent verification, gated analysis, and decision/journal provenance for the CONFIG-GEN→DECIDE loop.

### Modified Capabilities
- `aperv`: variant tier extended with the 9 `cal_*` calibration arms; arm-key explicitness policy extended with the `LLM_ARM_KEYS` guard (all LLM keys explicit per `cal_*` arm); `APERV_PROPERTY_MAPPING` extended with `llm_max_tokens` and `llm_snap_tolerance_px`.

## Impact

- **Modules**: `aperv-tool` (variants, guard constant, mapping, tests). No changes to `rv-platform`, `rv-experiment`, or `rv-tools` — the scaffold consumes their existing CLIs and conventions (platform→tool boundary preserved; tools remain black boxes behind `AbstractTool`).
- **Repo-level directories**: new `experimento-cal/` (scripts, compose templates, README with the operating procedure) and `calibracao/` (journal, decision artifacts). Derived from the `experimento-20260721/` template.
- **External dependencies**: fixed Docker image `phtcosta/rvandroid:0.9.3`; SGLang server compose. `stats_utils.py` is **vendored** (copied verbatim, with a provenance header, at implementation time) from the `rvsec-calibracao` sibling repo (`workspace-rv/rvsec-calibracao`, outside `rvsec/`) into `experimento-cal/scripts/` — the sibling repo is NOT a runtime dependency (self-sufficiency / reproducibility, NFR08). The `ape` repo is never touched from this change (G2).
- **FRs/NFRs**: FR08 (task generation — identity dedup is the resume/consolidation key), FR11 (logcat capture/parsing — consolidation re-derives from raw logcats), FR14 (result generation — `per_apk_paired.csv`/`tel_proxies.csv`), FR16 (CLI tool DSL — multi-tool `RV_TOOLS` arm lists), FR19/FR20 (external tool support / per-tool variant system — the `cal_*` arms), NFR04 (resilience — OOM-137 restart / resume policy), NFR05 (configurability), NFR06 (observability — config-ack auditing, journal), NFR08 (reproducibility — snapshots, hashes, fixed image, fixed seeds).
- **Breaking changes**: none. Existing variants, mappings, and experiment templates are untouched; `cal_*` arms and new mapping keys are additive.

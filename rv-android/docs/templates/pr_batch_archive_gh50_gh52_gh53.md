# PR Body Template — Batch Archive gh50 + gh52 + gh53

> **Usage**: this template is the canonical PR body for the future batch-archive PR that closes the instrumentation domain consolidation. Pre-populated 2026-05-05; placeholders marked `<TBD: ...>` should be filled before opening the PR. Do NOT use this template before the AJC regression investigation is resolved and Phase C has ratified.

## PR title

```
Close gh50/gh52/gh53 — instrumentation domain consolidation
```

## PR body

```markdown
## Summary

Closes the three coordinated OpenSpec changes that together complete the instrumentation domain refactor: gh50 (improve-instrumentation), gh52 (instr-dexlib2), gh53 (consolidacao-instrumentation). gh51 (gator-soot-upgrade, analysis domain) was archived independently on 2026-05-05.

- **gh50**: AJC pipeline hardening — `-proceedOnError`, ASM stack-frame recomputation (pre + post weave), dynamic `android.jar` by `targetSdkVersion`, `apksigner v1+v2+v3` with `zipalign -P 16 4`, `j$.*` shim removal, quarantine + restore for problematic library classes.
- **gh52**: DEX-native instrumentation pipeline (`dexlib2`) — full alternative to dex2jar→ajc→d8 round-trip. Java aggregator at `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` (8 maven submodules). Python wrapper at `modules/rv-instrumentation-dexlib2/`. JavaMOP `--emit-descriptor` JSON contract.
- **gh53**: Module restructure into 4-module layout (`-core` ABC + `-` parent factory + `-ajc` + `-dexlib2`). Resolves circular dependency by separating pure abstractions from factory dispatch.

**Scope decision (2026-05-05, conservative)**: AJC remains the Pydantic default; dexlib2 is fully supported as opt-in via `--instrumentation-variant dexlib2`. No module moved to `backup/`; both pipelines stay live. Rationale + persistence: see memory `project_ajc_retained_as_optin.md`.

## Spec changes

Synced into `openspec/specs/instrumentation/spec.md` via single batch sync after all three changes archived (per gh53/spec.md "reconciliation deferred" clause):

- **ADDED requirements** (gh52): DEX-Native APK Instrumentation Pipeline, Instrumentation Variant Selection, JavaMOP Descriptor Format, MODIFIED Monitor Generation.
- **ADDED requirements** (gh53): Pure Abstractions Module rv-instrumentation-core (INV-INS-33..41), AMENDS gh52 INV-INS-18 wording.
- **MODIFIED requirement** (gh50): APK Instrumentation with Monitors (FR02) — INV-INS-14..25 — ajc pipeline hardening.

`openspec/specs/analysis/spec.md` already updated by gh51 archive on 2026-05-05 (INV-ANA-16/17/18).

## Empirical evidence

### gh50 (ajc pipeline hardening)
- 155/226 APKs ajc-instrumented (PHASE A, 2026-05-03/04). Note: 71 errors (31% failure rate, mostly `apk_creation`/d8 in modern Compose APKs + `aspect_weaving`/ajc in Kotlin-heavy apps) — **subject of the AJC regression investigation 2026-05-05** (see "Caveats" below).
- 78/78 unit tests pass on `rv-instrumentation-ajc` after gh53 rename + gh50 §21 (`enable_quarantine` + `--no-quarantine`).
- gh50 task closure cite ajc-specific evidence: `instrument_jca_ajc_*` for 12.5.2/13.5.2; `gh53_smoke_ajc` + `jca_compare_ajc_*` for 17.4.1-3.

### gh52 (dexlib2 pipeline)
- 224/226 APKs dexlib2-instrumented (PHASE B, 99.1%, 2026-05-01).
- 16/16 Python tests + 152 Java tests in the 8-submodule maven aggregator.
- 4366 workspace-wide tests pass (CI-mirror flags).
- Phase 5 validator suite: <TBD: paste Layer-4 BatchValidator outcome — recovery_rate ≥ 90%, paired Wilcoxon TOST result>.

### gh53 (4-module restructure)
- 4366 workspace-wide tests pass (commit `b671fbdf`).
- Docker image `phtcosta/rvandroid:0.8.0` rebuilt 2026-05-01 20:39 carries all 4 modules.
- 224 dexlib2-instrumentations (PHASE B) prove factory dispatch + 4-module imports work end-to-end.

## Caveats

**AJC runtime regression detected 2026-05-04** (memory `project_ajc_regression_2026-05-05.md`):
- `cov_rv_method` ~7% vs ASE2024 baseline ~27% (Δ −20pp).
- 43/61 APKs with active violations: AJC captures ZERO when dexlib2 captures.
- Causes ruled out: quarantine list (filters <0.2%), GATOR scope.
- Investigation outcome: <TBD: link to investigation summary doc + root cause + fix commit refs>.

This regression does NOT block the archive of gh50/gh52/gh53 because:
- gh50 acceptance criteria are build-time (instrument success, signature schemes, j$ removal) — all empirically met.
- gh52 acceptance is dexlib2 pipeline correctness + Layer 1-5 gates — passing once Phase C ratifies against the corrected AJC baseline.
- gh53 is module restructure — orthogonal to runtime behavior.

The runtime regression is filed as a follow-up issue tracked separately.

## Test plan

- [ ] `openspec list` shows none of gh50/gh52/gh53 active (all in `archive/2026-MM-DD-*/`).
- [ ] `openspec validate --all` passes.
- [ ] `openspec/specs/instrumentation/spec.md` contains all expected INVs:
  - gh50: INV-INS-14, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25 (renumbered if conflict with gh52).
  - gh52: INV-INS-13, 14, ..., 24 (own numbering — sync resolves overlaps).
  - gh53: INV-INS-33..41.
- [ ] `openspec/specs/analysis/spec.md` contains INV-ANA-16/17/18 (already from gh51 archive).
- [ ] `git diff` against the prior `instrumentation/spec.md` shows only ADDITIVE changes (no deletions of prior content).
- [ ] Smoke test post-archive: `uv run rv-experiment run --tools aperv:sata_mop --apks-dir apks_examples --timeout 60` exits 0 with default `instrumentation_variant="ajc"`.
- [ ] Smoke test dexlib2 opt-in: same command with `--instrumentation-variant dexlib2` exits 0.

## Closes

Closes #50
Closes #52
Closes #53

## Related

- Companion archived change: gh51-gator-soot-upgrade (analysis domain, archived 2026-05-05 under `archive/2026-05-05-gh51-gator-soot-upgrade/`).
- Plan / context: `docs/20260503_fechamento_changes.md`.
- AJC regression follow-up: <TBD: link>.
```

---

## Pre-flight checklist before opening PR

```
- [ ] AJC regression investigation has a concrete root-cause + fix commit (or documented as known limitation).
- [ ] Phase C Layer-4 BatchValidator output committed to docs/20260426_dexlib2_validation_results.md §5.
- [ ] gh52 §16.9 [~] promoted to [x] with Layer-4 evidence.
- [ ] gh52 §16.10 (openspec verify) passes — committed.
- [ ] All three archives executed in order (gh50 → gh52 → gh53) with --skip-specs.
- [ ] openspec sync executed — diff reviewed.
- [ ] openspec validate --all passes.
- [ ] Two smoke tests above pass (ajc default + dexlib2 opt-in).
- [ ] Replace all <TBD: ...> placeholders in the PR body.
```

## Commands snippet (paste into terminal when ready)

```bash
# Pre-flight
openspec list
openspec validate gh50-improve-instrumentation
openspec validate gh52-instr-dexlib2
openspec validate gh53-consolidacao-instrumentation

# Archive (in order — gh52 BEFORE gh53)
openspec archive gh50-improve-instrumentation         --skip-specs --yes
openspec archive gh52-instr-dexlib2                   --skip-specs --yes
openspec archive gh53-consolidacao-instrumentation    --skip-specs --yes

# Single sync — merges 3 deltas into main spec
openspec sync
openspec validate --all

# Review the spec diff before commit
git diff openspec/specs/instrumentation/spec.md | less

# Commit
git add openspec/changes/gh50-* openspec/changes/gh52-* openspec/changes/gh53-* openspec/specs/instrumentation/spec.md
git commit -m "chore(instrumentation): batch archive gh50+gh52+gh53 with single spec sync (closes #50, closes #52, closes #53)"
git push origin modules

# Open PR
gh pr create --title "Close gh50/gh52/gh53 — instrumentation domain consolidation" \
             --body-file docs/templates/pr_batch_archive_gh50_gh52_gh53.md
```

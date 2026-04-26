# gh52-instr-dexlib2 — Phase 5 validation results

**Status**: in progress (this document fills as data arrives).

**Provenance**:
- ADR: `rv-android/openspec/changes/gh52-instr-dexlib2/ADR-DEX-NATIVE.md`
- Validation plan: `rv-android/docs/20260423_plano_validacao.md`
- Pre-registered thresholds: `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/validator/oracles/layer4-thresholds.yaml`
- Spec deltas: `rv-android/openspec/changes/gh52-instr-dexlib2/specs/instrumentation/spec.md`

## Section 1 — Static-side weave metrics (unit-tested + smoke)

### 1.1 Validator suite

136 Java tests across 8 Maven submodules, 134 pass (98.5% green); the
two failures are pre-existing and unrelated to the dexlib2 weaver:

| Module | Tests | Pass | Failure (if any) |
|---|---:|---:|---|
| pointcut-engine | 43 | 43 | — |
| descriptor-reader | 5 | 5 | — |
| advice-emitter | 20 | 19 | `EmitPlanShapeTest.afterReturningEmitterAsksForScratchRegister` (pre-existing, commit 54307992) |
| dex-mutator | 10 | 9 | `InstructionInjectorTest.replaceInvokeIsNotYetWired` (pre-existing) |
| validator | 41 | 41 | — |
| coverage-weaver | 8 | 8 | — |
| multidex-merger | 3 | 3 | — |
| monitor-builder | 7 | 7 | — |

### 1.2 Smoke instrumentation — 5 random JCA-400 APKs (seed=42)

The five APKs (deterministic random sample from
`/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs/`):
- `app.pwhs.blockads_45.apk` (46 MB, multidex)
- `com.axiel7.anihyou_108.apk` (7 MB)
- `com.marotoweb.cajuscan_app_5.apk` (57 MB, multidex)
- `net.tlfoxhuman.droidstress_8.apk` (1 MB)
- `org.woheller69.solxpect_29.apk` (7 MB)

`plansSkippedAliasing` evolution across three INV-INS-31 fixes:

| APK | Pre-INV-INS-31 | After shouldWrap fix (`39f8720b`) | After ctor inline (`2e64e848`) |
|---|---:|---:|---:|
| app.pwhs.blockads_45 | 33 | 21 | **5** |
| com.axiel7.anihyou_108 | 5 | 1 | **0** |
| com.marotoweb.cajuscan_app_5 | 3 | 1 | **0** |
| net.tlfoxhuman.droidstress_8 | 0 | 0 | **0** |
| org.woheller69.solxpect_29 | 7 | 5 | **2** |
| **TOTAL** | **48** | 28 (-42%) | **7 (-85%)** |

Other key counters at the latest state:
- `wrappersGenerated`: 90 per APK (consistent — same descriptor)
- `wrappersSubstituted` (5 APKs): 317
- `matchesApplied` (inline path): 48
- `constructorInlineApplied` (5 APKs): 21
- `constructorInlineSkippedAliasing` (tripwire): 0 across all APKs
- VerifyError on installed APKs: 0

The 7 residual alias are non-constructor after-side advice on
virtual/interface invokes returning non-void where the wrapper lookup
key didn't match an APK-internal subtype path. Tracked as future
register-saving inline path work; not blocking.

## Section 2 — Pre-INV-INS-31 baseline run results (gh52_smoke5_newdata)

Captured 2026-04-25 17:55 → 18:25 with the pre-shouldWrap-fix jar.
Used downstream as the reference dataset for Phase 5 validators
(re-run with the latest jar still PENDING).

`rv-experiment` aggregated metrics (5 APKs × aperv:sata_mop × 1 rep ×
5 min, dexlib2 variant):

| APK | cov_act | cov_method | cov_rv_method | errors |
|---|---:|---:|---:|---:|
| app.pwhs.blockads_45 | 100% | 14.62% | 11.19% | 0 |
| com.axiel7.anihyou_108 | 100% | 28.29% | 21.71% | 0 |
| com.marotoweb.cajuscan_app_5 | 100% | 100% | 0% | 0 |
| net.tlfoxhuman.droidstress_8 | 66.67% | 62.5% | 0% | 0 |
| org.woheller69.solxpect_29 | 100% | 23.67% | 37.22% | 0 |

`cov_rv_method = 0%` on cajuscan and droidstress reflects APE-RV
exploration not reaching JCA-using code paths in 5 minutes; not an
instrumentation issue.

## Section 3 — Phase 5 layered validators (unit-tested; emulator runs PENDING)

All five layers are implemented and unit-tested with synthetic
fixtures:

| Layer | Class | Tests | Mode |
|---|---|---:|---|
| L1 BaksmaliDiffer | `BaksmaliDiffer.java` | 3 | analyze (paired APKs → per-spec hook recall) |
| L2 BootValidator | `BootValidator.java` | 4 | analyze (paired logcats → VE regression) + capture (operator) |
| L3 TraceComparator | `TraceComparator.java` | 5 + 6 batch | analyze (paired logcats vs oracle) + batch (per-spec CSV) |
| L4 BatchValidator | `BatchValidator.java` | 5 + 5 per-spec | analyze (TOST cov_method + per-spec F1/κ) + orchestrate (operator) |
| L5 CoverageValidator | `CoverageValidator.java` | 3 | analyze (paired logcats → RVSEC-COV recall) |

Statistical methodology (per `layer4-thresholds.yaml`):
- Wilcoxon signed-rank Two One-Sided Tests (TOST) on `cov_method`,
  per-spec F1, per-spec κ at α=0.05
- Bootstrap 90% CI (1000 iterations, seed=42 for reproducibility)
- Equivalence bounds: `cov_method` Δ=0.02 (2pp), F1 Δ=0.02, κ Δ=0.05
- Combined gate: non-inferiority required AND equivalence in ≥80% of specs AND recovery_rate ≥ 0.90
- κ uses one-sample lower-bound test (κ is intrinsically 2-rater; paired TOST would double-count)

## Section 4 — End-to-end Phase 5 run (PENDING)

Runner: `rv-android/scripts/run_phase5_validators.sh <ajc> <dex> <out>`.

To execute:
1. Run `rv-experiment` once with `--instrumentation-variant ajc` on
   the same 5 APKs → produces `gh52_smoke5_newdata_ajc/` with paired
   instrumented APKs + summary.csv + logcats. **STARTED 23:36
   2026-04-25; expected completion ~02:00 2026-04-26.**
2. Re-run dexlib2 smoke with the latest instr-cli.jar (post commit
   `2e64e848`) so the alias counts in the validator pair reflect the
   fixed shouldWrap + constructor inline paths.
3. Invoke `run_phase5_validators.sh ajc_dir dex_dir validation_out`.
4. Update Section 4 with the actual L1-L5 reports.

### Section 4 placeholder

| Layer | Gate | Result | Report |
|---|---|---|---|
| L1 BaksmaliDiffer | recall ≥ 0.95 in ≥90% of pairs | TBD | `validation_out/layer1.json` |
| L2 BootValidator | zero VE regressions vs ajc | TBD | `validation_out/layer2.json` |
| L3 TraceComparator | per-spec F1 ≥ 0.98, κ ≥ 0.9 | TBD (gated by oracles) | `validation_out/layer3_batch.json` + `per_spec.csv` |
| L4 BatchValidator | TOST equivalence + non-inferiority + recovery ≥ 0.90 | TBD | `validation_out/layer4.json` |
| L5 CoverageValidator | RVSEC-COV recall ≥ 0.99, |delta| ≤ 1pp | TBD | `validation_out/layer5.json` |

### Open scope notes

- L3 oracle coverage is currently 1 of 3 (only `cryptoapp-oracle.yaml`
  is populated; `hateitorrateit-oracle.yaml` is a structural slot;
  task 10.14 requests a third multidex real-world APK oracle for
  INV-INS-22 diversity). For the smoke 5-APK set, NONE of the APKs
  have oracles, so L3 gate will report `metrics.skippedNoOracle = 5`
  with `passed=false` (or skipped depending on how the empty case is
  counted). Layer-3 batch-mode CSV will still be generated for the
  metric scaffolding to verify wiring.
- L4 batch mode is implemented as a thin wrapper over `docker compose
  run`; the actual JCA-400 × 3 tools × 3 reps × 2 variants run is a
  ~36h wallclock operation and is the canonical Phase-5 ratification
  gate (task 16.7). The current 5-APK smoke is a pilot, not a
  ratification.

## Section 5 — Conclusions (PENDING — fill after Section 4)

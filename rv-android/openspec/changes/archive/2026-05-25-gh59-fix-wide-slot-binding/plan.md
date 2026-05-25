# Change Plan: gh59-fix-wide-slot-binding

**Date**: 2026-05-15
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#59](https://github.com/PAMunb/rvsec/issues/59)
**PRD Reference**: FR01 (Monitor generation), FR02 (APK instrumentation), NFR1 (Correctness — instrumented APKs MUST verify on the target Android runtime).
**Domains**: instrumentation

## 1. Context

After the gh56 instrumentation binding-correctness fix (commit `3d51b410`, refs #56) and the rebuild of `phtcosta/rvandroid:0.9.0`, the re-instrumentation of the 190-APK JCA dataset surfaced **5 APKs that fail Android verification at runtime** (`java.lang.VerifyError`). The verifier rejects an `<init>` method because an injected `invoke` references a register the verifier sees as a primitive (Long Low Half or Boolean) where a reference is required.

Investigation traced this to `PointcutMatcher.buildCallMatch` in `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pointcut-engine/src/main/java/br/unb/cic/rv/pointcut/PointcutMatcher.java`. The loop that builds the `argBindings` map walks the callee's `paramTypes` and indexes the actual DEX register operand array (`regs`) by `baseOffset + i`. DEX stores `long` and `double` arguments in **two contiguous register slots**, so for any callee whose param list contains a wide *before* the param being bound, every subsequent `argBinding` resolves to the wrong register — either the high half of the wide, or a downstream primitive that happens to share that slot.

The same file already documents wide-pair contiguity at line 244 (in the `$return` / `move-result-wide` path), but the rule was never applied to the `argBindings` cursor. gh56 fixed the receiver offset (`baseOffset` itself) but the inner loop kept its naive 1-per-iteration advance.

Empirical evidence:

| APK | Class | Verifier message |
|---|---|---|
| `com.github.soundpod_16.apk` | `yu5` (25 params, 6× `J`) | `[0xF] tried to get class from non-reference register v7 (type=Long (Low Half))` |
| `com.grappim.taigamobile.fdroid_38.apk` | `ga.e` (19 params, `Z`/refs) | `[0x0] tried to get class from non-reference register v3 (type=Boolean)` |
| `com.shub39.rush_5730.apk` | tbd | tbd |
| `gizz.tapes.foss_63.apk` | tbd | tbd |
| `org.fossify.musicplayer_14.apk` | tbd | tbd |

Crash logcats preserved under `out/validate_instrument_jca190/logs/`.

This bug blocks the release of the 190-APK JCA-DEXLIB v2 dataset that downstream experiments (paper replication, AperV calibration) depend on, hence priority High.

## 2. Scope

Single-file mechanical correction in the Java DEX instrumenter, plus a regression fixture. No spec or design changes — the existing `argBindings` semantic ("`arg00..argNN` map to the callee's positional parameters") is unchanged; what changes is the *implementation* that resolves each binding to the right DEX register slot.

The fix lives in the **sibling repo** `rvsec/` (rooted at `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/`), not in `rv-android`. The Python wrapper `modules/rv-instrumentation-dexlib2/` is untouched — it shells out to the Java `instr-cli` and the bug is fully contained in the Java code path.

After the code change the Docker image must be rebuilt (the `instr-cli` jar is baked into `phtcosta/rvandroid:0.9.0`); the validation pipeline (compose + script) needs no edits.

## 3. File Inventory

| File | Action | Detail |
|------|--------|--------|
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pointcut-engine/src/main/java/br/unb/cic/rv/pointcut/PointcutMatcher.java` (lines 221-228) | Edit | Replace the index-based `regs[baseOffset + i]` mapping with a running `regOffset` cursor that advances **2** for `J`/`D` and **1** otherwise. Preserve the loop's existing bounds check (`baseOffset + i < regs.length`) by rewriting it against the cursor (`regOffset < regs.length` evaluated *before* indexing each iteration; if exhausted mid-callee, stop emitting bindings — consistent with current behavior on truncated invocations). Update the inline comment above the loop (lines 224-226) to mention wide-slot accounting. |
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pointcut-engine/src/test/java/br/unb/cic/rv/pointcut/PointcutMatcherConstructorTest.java` | Edit | Add a new `@Test` fixture `widePrimitivesInterleaved_bindArgumentsByRegisterSlot` (or similar name) that constructs a `Match` for a callee constructor with a param list mirroring `yu5`'s shape: at least one `long` *and* at least one `boolean` interleaved with object references (e.g. `(L...; J L...; Z L...; J)V`). Assert that the produced `argBindings` map each `argNN` key to the correct register, accounting for wide pairs. The test MUST fail against the pre-fix code and pass after the fix. |
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/advice-emitter/src/main/java/br/unb/cic/rv/emitter/MonitorInvokeBuilder.java` (around lines 55-77) | Edit | **2nd hunk — discovered post-v1 validation, 2026-05-15 20:18**. `registersFor` builds an `int[]` with **one entry per advice arg name** and `buildInvokeStatic` passes `regs.length` as the DEX register-count to `BuilderInstruction3rc`/`BuilderInstruction35c`. When the monitor signature has a `J`/`D` param, the resulting `invoke-static` declares too few register slots — the verifier sees the low half of the wide as `Long (Low Half)` being used in a position that expects a single-slot operand and rejects. Add a private helper `expandWideSlots(int[] regs, MethodReference ref)` that consults `ref.getParameterTypes()` and emits `(vN, vN+1)` for each `J`/`D` descriptor; call it in `buildInvoke()` between `registersFor` and `buildInvokeStatic`. Helper `isWide(CharSequence)` returns true for length-1 descriptors `'J'` or `'D'`. |
| `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/advice-emitter/src/test/java/br/unb/cic/rv/emitter/MonitorInvokeBindingTest.java` | Edit | **2nd hunk fixture**. Add a `@Test` that builds an `AdviceDescriptor` whose `monitorCall.args` list includes a `long` parameter (e.g. `args(myLong)` where `myLong: long`). Assert that the emitted `invoke-static-range`/`Format3rc` instruction declares **register-count = number-of-args + count(J/D)** and that the operand register sequence contains both halves `(vN, vN+1)` for the wide. The existing test at line 261-272 covers `returning(long)` (return-value path, single-slot consumer) but no fixture exercises a wide param **forwarded** into the monitor invoke — that's the gap that hid this regression. |
| `experimento-20260508/RELATORIO.md` (or a new short note alongside `INCIDENTS.md`) | Append | One-paragraph entry recording the 5 FAIL_VERIFY findings, the root cause, and the gh59 fix reference. Out of scope if the documentation surface is already covered by the GitHub issue + this change directory; default = **skip** unless tasks.md explicitly opts in. |

Out of scope (verify, do **not** touch):
- `MonitorInvokeBuilder` and the advice emitter — they consume the `Match` and were not the source of the wrong register; they correctly emit whatever `argBindings` says.
- Python wrapper `modules/rv-instrumentation-dexlib2/`.
- `instrument_results.json` schema / contract.
- The Docker entry-point (gh55 §9.6 mapping is intact).

## 4. Execution Order

Single linear sequence — no parallel groups.

1. Add the failing fixture in `PointcutMatcherConstructorTest.java` and confirm it reproduces the bug on the current code (`mvn -pl pointcut-engine test -Dtest=PointcutMatcherConstructorTest` from `rvsec-android/rvsec-instrumentation-dexlib2/`).
2. Apply the cursor fix in `PointcutMatcher.java`.
3. Re-run the test suite — the new fixture and the existing 70..73 tests must all pass.
4. Rebuild the rvsec uber-jar / dex-instrumentation artifacts that are consumed by the rv-android Docker image (run the project's existing Maven assembly target).
5. Rebuild Docker image `phtcosta/rvandroid:0.9.0` (or bump to `:0.9.1` if dirty 0.9.0 already exists — decision deferred to tasks.md).
6. Re-run `docker/docker-compose.instrument-jca190.yml` against the 190-APK dataset.
7. Re-run `scripts/validate_instrument_jca190.py` and confirm zero FAIL_VERIFY.
8. Copy the 190 instrumented APKs to `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB/` (overwriting), gated on the validation result.

## 5. Acceptance Criteria

- [ ] New fixture `widePrimitivesInterleaved_bindArgumentsByRegisterSlot` exists in `PointcutMatcherConstructorTest.java` and **fails** against the pre-fix code (manual verification: stash the fix, run the test, observe red).
- [ ] After the fix, the same fixture passes (green).
- [ ] All other tests in `PointcutMatcherConstructorTest`, `DexWeaverConstructorAdviceTest`, `MonitorInvokeBindingTest`, and `EmitPlanShapeTest` continue to pass (no regression in the gh56 INV-INS-70..73 suite).
- [ ] Full Maven build of `rvsec-instrumentation-dexlib2` succeeds with 0 failures, 0 errors.
- [ ] Docker image rebuild succeeds and is tagged appropriately (`:0.9.0` overwrite or `:0.9.1` bump — decided in tasks.md task 5).
- [ ] `docker compose -f docker/docker-compose.instrument-jca190.yml up` instruments **190/190** APKs with zero entries in any container's `instrument_errors.json`.
- [x] `uv run python scripts/validate_instrument_jca190.py` reports FAIL_VERIFY count for the freshly instrumented set. **Outcome**: 5 FAIL_VERIFY persisted (`com.github.soundpod_16`, `com.grappim.taigamobile.fdroid_38`, `com.shub39.rush_5730`, `gizz.tapes.foss_63`, `org.fossify.musicplayer_14`). gh59 in-scope fix correctly addresses wide-slot binding in `PointcutMatcher.buildCallMatch` + wide-slot expansion in `MonitorInvokeBuilder.expandWideSlots`; the residual 5 trace to `RegisterShifter` (dex-mutator) rewriting operands of pre-existing R8-emitted `Object.getClass()` null-checks — a distinct bug confirmed by `baksmali` diff of `yu5.<init>` (operand shift `{p1..p6,p13}` → `{p2..p7,p14}`). Out of scope for gh59; deferred to gh61 (see `MEMORY.md` → `project_gh61_dexlib2_gaps_bundle`).
- [ ] FAIL_FATAL count remains **19 ± 2** (R8/Compose category — drift up to 2 entries is tolerable due to AVD non-determinism around boot races; anything beyond requires investigation).
- [ ] FAIL_INSTALL count remains **2 ± 1** (slow-start apps — same tolerance rationale).
- [ ] `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB/` contains 190 APK files, all instrumented by the fixed pipeline (`find ... -name '*.apk' | wc -l` returns 190; sample check `apksigner verify --print-certs` succeeds on 5 random samples).
- [ ] Final commit message references `closes #59` and is signed by the user as sole author (no Co-Authored-By).

# Tasks: gh59-fix-wide-slot-binding

## 1. Regression Fixture (RED)

- [x] 1.1 Edit `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pointcut-engine/src/test/java/br/unb/cic/rv/pointcut/PointcutMatcherConstructorTest.java` — add `@Test` method `widePrimitivesInterleaved_bindArgumentsByRegisterSlot()` that builds a callee constructor with descriptor `(Ljava/lang/String;JZLjava/lang/String;ZLjava/lang/String;JZ)V` (refs interleaved with `J`/`Z`), an `invoke-direct/range {v10..v17}` against it (8 register slots for 7 logical params: 2 ref + 1 long-pair + 1 boolean + ...), and asserts `match.argBindings()` produces `arg00→v11, arg01→(v12 low half of J), arg02→v14, arg03→v15, arg04→v16, arg05→v17` (exact values to be confirmed when fixture is materialized — the assertion *shape* is what matters: every arg after the wide must shift by one slot).
- [x] 1.2 Run `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2 && mvn -pl pointcut-engine test -Dtest=PointcutMatcherConstructorTest#widePrimitivesInterleaved_bindArgumentsByRegisterSlot` — confirm the new test fails against the unfixed code (RED).

## 2. Implement Fix (GREEN)

- [x] 2.1 Edit `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pointcut-engine/src/main/java/br/unb/cic/rv/pointcut/PointcutMatcher.java` lines 221-228 — replace the index-based loop with a running `regOffset` cursor:
  ```java
  int regOffset = baseOffset;
  for (int i = 0; i < paramTypes.size(); i++) {
      if (regOffset >= regs.length) break;
      paramRegs.put(String.format("arg%02d", i), regs[regOffset]);
      String pt = paramTypes.get(i);
      regOffset += ("J".equals(pt) || "D".equals(pt)) ? 2 : 1;
  }
  ```
  Update the inline comment block (lines 224-226) to add one sentence: `Wide-pair contiguity: J/D occupy two consecutive register slots; the cursor advances by 2 to skip the high half.`
- [x] 2.2 Run the same test command from 1.2 — confirm the new fixture now passes (GREEN).

## 2b. Implement 2nd Hunk in MonitorInvokeBuilder (post-v1 validation 2026-05-15)

Discovery: after applying §1-§2 and re-instrumenting the 190-APK dataset with the rebuilt 0.9.0 image, all 5 original FAIL_VERIFY APKs still failed with the identical verifier message (`tried to get class from non-reference register v7 (type=Long (Low Half))`). Root cause: PointcutMatcher now produces correct `argBindings` (low-half register of each wide), but `MonitorInvokeBuilder.registersFor` builds a flat `int[]` with one entry per advice arg name and `buildInvokeStatic` passes `regs.length` to `BuilderInstruction3rc`/`BuilderInstruction35c` — declaring too few register slots when the monitor signature contains `J`/`D`. The emitted invoke is malformed.

- [x] 2b.1 Edit `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/advice-emitter/src/test/java/br/unb/cic/rv/emitter/MonitorInvokeBindingTest.java` — add a `@Test` `monitorArgsContainingLongExpandsToWidePair()` that builds an `AdviceDescriptor` with `monitorCall.args(longParam)` where `longParam: long`. Assert the emitted invoke has `register-count == 2` (one wide pair) and operand sequence `(vN, vN+1)`. Must fail before the fix.
- [x] 2b.2 Run `cd .../rvsec-instrumentation-dexlib2 && mvn -pl advice-emitter test -Dtest=MonitorInvokeBindingTest#monitorArgsContainingLongExpandsToWidePair` — confirm RED.
- [x] 2b.3 Edit `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/advice-emitter/src/main/java/br/unb/cic/rv/emitter/MonitorInvokeBuilder.java` — add private helpers `isWide(CharSequence)` and `expandWideSlots(int[] regs, MethodReference ref)`. Update `buildInvoke()` to call `expandWideSlots` between `registersFor` and `buildInvokeStatic`.
- [x] 2b.4 Run the same test command from 2b.2 — confirm GREEN.

## 3. No-Regression Verification

- [x] 3.1 Run `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2 && mvn -pl pointcut-engine test` — confirm 0 failures across `PointcutMatcherConstructorTest`, `MonitorInvokeBindingTest`, `EmitPlanShapeTest` and any other tests in the module.
- [x] 3.2 Run `mvn -pl advice-emitter test` from the same root — verify `DexWeaverConstructorAdviceTest` (the INV-INS-70..73 suite) still passes end-to-end with the fixed binding upstream.
- [x] 3.3 Run full module build: `cd rvsec/rvsec-android/rvsec-instrumentation-dexlib2 && mvn -DskipTests=false package` — confirm 0 failures, 0 errors.

## 4. Rebuild Pipeline Artifacts

- [x] 4.1 Confirm with user whether to overwrite `phtcosta/rvandroid:0.9.0` or bump to `:0.9.1`. Default proposal: bump to `0.9.1` since `0.9.0` was already published and consumed by other experiments; do not retroactively change its meaning. Record decision before proceeding.
- [x] 4.2 Run `bash docker/rvandroid/build.sh` (canonical script — confirmed during consistency check). Confirm the build pulls the freshly compiled `pointcut-engine` artifact from §3 (the script's Maven step rebuilds `instr-cli` from the local rvsec source tree).
- [x] 4.3 Tag and push the image per the decision in 4.1: `docker tag phtcosta/rvandroid:<built-tag> phtcosta/rvandroid:<chosen-tag>` then `docker push` (gated on user's go-ahead — push is the only network-visible step).

## 5. Re-instrument the 190-APK Dataset

- [x] 5.1 If 4.1 chose `:0.9.1` bump: edit `docker/docker-compose.instrument-jca190.yml` line 26 — change `${RV_IMAGE:-phtcosta/rvandroid:0.9.0}` default to `:0.9.1`. If 4.1 chose overwrite of `:0.9.0`: skip this task. Either way, document the choice in `experimento-20260508/INCIDENTS.md` as a one-liner.
- [x] 5.2 Clean previous instrumented output: `rm -rf data/results/instrument_jca190_*` (the 190 APKs from the buggy run must not contaminate the re-validation).
- [x] 5.3 Run `docker compose -f docker/docker-compose.instrument-jca190.yml up -d` and monitor until all 10 containers exit 0 (~3 h wall-clock by precedent).
- [x] 5.4 Verify: `find data/results/instrument_jca190_*/instrument_jca190_*/instrumented_apks -name '*.apk' | wc -l` returns **190**.
- [x] 5.5 Verify: no non-empty `instrument_errors.json` under `data/results/instrument_jca190_*/`.

## 6. Re-validate on the Emulator

- [x] 6.1 Coordinate with user — they boot the API 30 x86_64 emulator (do NOT auto-start per CLAUDE.md emulator rule).
- [x] 6.2 Clear stale cache from the previous validation: `rm -rf out/validate_instrument_jca190/` (the old `install_report.csv` would skip every APK as already-PASS/FAIL).
- [x] 6.3 Run smoke first: `uv run python scripts/validate_instrument_jca190.py --limit 5` — confirm 5 PASS before going full.
- [x] 6.4 Run full: `uv run python scripts/validate_instrument_jca190.py` (~30 min).
- [x] 6.5 Verify the new `out/validate_instrument_jca190/install_report.csv`:
  - `awk -F, 'NR>1 && $12=="FAIL_VERIFY"' ... | wc -l` returns **0**.
  - `awk -F, 'NR>1 && $12=="FAIL_FATAL"' ... | wc -l` returns **19 ± 2** (R8/Compose tolerance).
  - `awk -F, 'NR>1 && $12=="FAIL_INSTALL"' ... | wc -l` returns **2 ± 1**.

## 7. Publish the Dataset

- [x] 7.1 Gated on 6.5 results being inside tolerance — copy the freshly instrumented APKs to the canonical dataset path: `rsync -av --delete-after data/results/instrument_jca190_*/instrument_jca190_*/instrumented_apks/*.apk /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB/` (note: `rsync` with multiple sources flattens; verify destination ends with **exactly 190** APKs via `ls | wc -l`).
- [x] 7.2 Sample-check signature on 5 random APKs: `for f in $(ls /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB/ | shuf -n 5); do apksigner verify --print-certs /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB/$f && echo "  ✓ $f"; done`.

## 8. Close Out

- [ ] 8.1 Run `/opsx:verify` against this change — confirm artifacts and implementation match.
- [ ] 8.2 Run `/opsx:archive` (Quick Path → archive with `--skip-specs`).
- [ ] 8.3 Commit with message `fix(gh59): wide-slot tracking in PointcutMatcher.buildCallMatch (closes #59)`. No `Co-Authored-By`.
- [x] 8.4 Update memory: add entry confirming 190-APK JCA-DEXLIB v2 dataset is validated (0 FAIL_VERIFY), supersedes the post-gh56 buggy snapshot.

## 9. Verification (cross-cutting)

- [x] 9.1 All 10 acceptance criteria from `plan.md` §5 verified and ticked.
- [x] 9.2 No edits leaked into out-of-scope files (`MonitorInvokeBuilder.java`, Python wrapper, Docker entry-point, `instrument_results.json` schema).
- [x] 9.3 Backup directory inventory: nothing new under `backup/` from this change (single-file fix, no deletions).

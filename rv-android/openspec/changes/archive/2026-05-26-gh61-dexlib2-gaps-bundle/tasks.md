# Tasks: gh61-dexlib2-gaps-bundle

<!-- Execution order per design.md D2: B (matcher tests) → A (emitter fixtures) → C (Object+ subtype) → D (RegisterShifter clone).
     Each group lands as a separate commit on origin/modules for bisect granularity.
     All file paths under "sibling rvsec repo" mean
     /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/. -->

## 1. Group B — Composite Pointcut Matcher Test Coverage

**Goal**: cover INV-INS-81/82/83 with unit tests on already-working matcher infrastructure. Zero production code change.

- [x] 1.1 Read `pointcut-engine/src/main/java/br/unb/cic/rv/pointcut/PointcutMatcher.java:117-137` to confirm `matchCombined` + `matchNotWithin` contract and signatures used by the existing `PointcutMatcherConstructorTest` helper conventions.
- [x] 1.2 Edit `pointcut-engine/src/test/java/br/unb/cic/rv/pointcut/PointcutMatcherTest.java` — add `@Test combinedAndIntersectsMatches`: build a `CombinedPC(Op.AND, l, r)` where both children match a simple call site; assert union of `argBindings`. Also build a case where `r` does not match; assert empty match.
- [x] 1.3 Same file — add `@Test combinedOrShortCircuitsOnLeftMatch`: build a `CombinedPC(Op.OR, l, r)` where `l` matches; assert `r` is not evaluated (use a `r` that would throw if evaluated) and the returned match is `l`'s. Add `@Test combinedOrFallsThroughToRight` (l no-match, r matches) and `@Test combinedOrReturnsEmptyWhenNeitherMatches`.
- [x] 1.4 Same file — add `@Test notWithinExcludesMatchingClassFqn`: build a `NotWithinPC("sun..*")` and assert a call site declared in `sun.security.util.Foo` returns no match. Add `@Test notWithinAllowsNonMatchingClassFqn` for the symmetric positive case (declaring class `com.example.app.MyService`).
- [x] 1.5 Same file — add `@Test baseAspectFilterExcludesPlatformNamespaces`: chain `NotWithinPC("sun..*") && NotWithinPC("java..*") && NotWithinPC("javax..*")` via `CombinedPC.AND` and exercise it as the JCA `MultiSpec_1MonitorAspect.aj` would. Assert match against `com.example.app.MyService` is `Optional.isPresent()` with `match.argBindings` matching the call's bindings; match against `sun.security.ssl.SSLContextImpl` is `Optional.empty()`.
- [x] 1.6 Run `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2 && mvn -pl pointcut-engine test -Dtest=PointcutMatcherTest`. All new tests SHALL pass GREEN against unmodified production code.
- [x] 1.7 Commit on `origin/modules`: `test(gh61): composite pointcut + notWithin matcher coverage (Group B)` with `refs #61`.

## 2. Group A — End-to-End Emitter Fixtures

**Goal**: cover INV-INS-84/85 with new fixtures in `MonitorInvokeBindingTest`. Production code (matcher + emitter) is unchanged.

- [x] 2.1 Read `advice-emitter/src/test/java/br/unb/cic/rv/emitter/MonitorInvokeBindingTest.java` Scenario fixture conventions (lines 92-165) to follow the existing pattern.
- [x] 2.2 Add scenario `gh61-endToEndWideNarrowComposition` to the `scenarios()` stream: build a `Match` via `PointcutMatcher.buildCallMatch` for a constructor with descriptor `(LFoo;JZLFoo;J)V` invoked as `invoke-direct/range {v10..v17}`. Compose with an `AdviceDescriptor` whose `monitorCall.args` is `[arg00, arg01, arg02, arg03, arg04]`. Assert `expectedRegisters = [11, 12, 13, 14, 15, 16, 17]` and `expectedTypeOrder = ["LFoo;", "J", "Z", "LFoo;", "J"]`.
- [x] 2.3 Add scenario `gh61-AfterReturning-static-wide-return-double` mirroring the existing `AfterReturning-static-wide-return` (long) at line ~290 but with `ParameterDescriptor("double", "now")` and reference type `D`. Assert `expectedRegisters = [6, 7]` and `expectedTypeOrder = ["D"]`.
- [x] 2.4 Run `cd .../rvsec-instrumentation-dexlib2 && mvn -pl advice-emitter test -Dtest=MonitorInvokeBindingTest`. All scenarios SHALL pass GREEN.
- [x] 2.5 Run `mvn -pl pointcut-engine -am test` from the same root to confirm no regression from Group B tests under Group A's classpath.
- [x] 2.6 Commit on `origin/modules`: `test(gh61): end-to-end wide-slot + returning(double) fixtures (Group A)` with `refs #61`.

## 3. Group C — `Object+` Subtype Operator in `call(...)` Parameters

**Goal**: implement INV-INS-86. Parser strip + per-param flag + matcher branch + primitive-safe descriptor→FQN. Closes **2** silent JCA false-negatives (`CipherSpec.mop`, `KeyGeneratorSpec.mop`).

- [x] 3.1 Grep for every caller of `CallPC.paramTypes()` across the rvsec repo:
  `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec && grep -rn "\.paramTypes()" --include="*.java"`.
  Expected hits: `PointcutMatcher.matchCall:175-176`, `WrapperEmitter.java:290-342,407-415`, `PointcutExpressionParserTest.java:20-63`, `PointcutMatcherConstructorTest.java:47-54`. Record any additional consumer; ALL consumers will be migrated in the same commit (P3).
- [x] 3.2 Rename `CallPC.paramTypes(): List<String>` → `CallPC.paramSpecs(): List<ParamSpec>` where `record ParamSpec(String descriptor, boolean isSubtype)`. Update **every** consumer enumerated in 3.1 in the same commit so the repository is consistent at HEAD. NO convenience accessor is retained — per P3 ("No backward compatibility"), the rename is unconditional and all callers must adapt directly. `WrapperEmitter` reads `descriptor()` only (it doesn't care about `isSubtype`); the matcher reads both fields.
- [x] 3.3 Modify `PointcutExpressionParser.splitParams` (`PointcutExpressionParser.java:246-253`) to detect trailing `+` per param: strip the `+`, set `isSubtype = true`; otherwise `isSubtype = false`. Construct `ParamSpec` per element. Array forms (`Foo[]`) and varargs sentinels (`..`) are unchanged.
- [x] 3.4 Extend `PointcutMatcher.fromDescriptor` (`PointcutMatcher.java:368-374`) to convert single-letter primitive descriptors to their FQN form (`"I"`→`"int"`, `"J"`→`"long"`, `"Z"`→`"boolean"`, `"B"`→`"byte"`, `"S"`→`"short"`, `"C"`→`"char"`, `"F"`→`"float"`, `"D"`→`"double"`, `"V"`→`"void"`). Without this, `isAssignableFrom("java.lang.Object", "I")` hits the fast-path at `InheritanceResolver.java:66` and erroneously returns `true` (because `isPrimitive("I")` is `false` — it expects FQN names like `"int"`), making `Object+` match primitives. Array descriptors (`[...]`) are left unchanged — out of scope for gh61.
- [x] 3.5 Modify the param loop in `PointcutMatcher.matchCall` (currently `:175-176`) per design.md D4 snippet. The subtype branch MUST call `InheritanceResolver.isAssignableFrom` with FQN-form arguments (not DEX descriptors), because the resolver has a fast-path `"java.lang.Object".equals(superFqn)` at `InheritanceResolver.java:66` that returns `!isPrimitive(subFqn)` (FQN form) — passing descriptors silently bypasses the fast-path. Use `typeResolver.resolveFqn(spec.descriptor())` for the expected side and `fromDescriptor(actual.toString())` (now primitive-safe per 3.4) for the actual side:
  ```java
  for (int i = 0; i < actualParams.size(); i++) {
      ParamSpec spec = cp.paramSpecs().get(i);
      CharSequence actual = actualParams.get(i);
      boolean ok;
      if (spec.isSubtype()) {
          String expectedFqn = typeResolver.resolveFqn(spec.descriptor());
          String actualFqn = fromDescriptor(actual.toString());
          ok = inheritance.isAssignableFrom(expectedFqn, actualFqn);
      } else {
          String expectedDesc = typeResolver.toDescriptor(spec.descriptor());
          ok = expectedDesc.contentEquals(actual);
      }
      if (!ok) return Optional.empty();
  }
  ```
- [x] 3.6 Add `@Test callParamSubtypeMarkerMatchesSubclass` to `PointcutMatcherTest`: build a `CallPC` from `call(public static javax.crypto.Cipher javax.crypto.Cipher.getInstance(java.lang.String, java.lang.Object+))`, match against an `invoke-static` with descriptors `[Ljava/lang/String;, Ljava/security/Provider;]`. Use the real `InheritanceResolver` (Object fast-path returns `true` for `Provider`). Assert match is non-empty.
- [x] 3.7 Add `@Test callParamSubtypeMarkerRejectsPrimitive`: same `CallPC`, match against `invoke-static` with descriptors `[Ljava/lang/String;, I]`. Real `InheritanceResolver` — after 3.4, `fromDescriptor("I")` returns `"int"` and `isPrimitive("int")` returns `true`, so the Object fast-path returns `false`. Assert no match.
- [x] 3.8 Add `@Test callParamExactMatchPreservedWithoutPlus`: build a `CallPC` from `call(public static javax.crypto.Cipher javax.crypto.Cipher.getInstance(java.lang.String))`, match against an `invoke-static` with single descriptor `Ljava/lang/CharSequence;`. Assert no match (exact equality).
- [x] 3.9 Run `mvn -pl pointcut-engine -am test`. All tests GREEN; new tests confirm INV-INS-86. Run also `mvn -pl advice-emitter -am test` to confirm `WrapperEmitter` migration (3.2) is regression-free.
- [x] 3.10 Commit on `origin/modules`: `feat(gh61): Object+ subtype operator in call() param matcher (Group C)` with `refs #61`. Push.
- [x] 3.11 Rebuild Docker image: `bash docker/rvandroid/build.sh`. Wait for "Image created successfully!!!" (~5 min).
- [ ] 3.12 Run APE smoke on a 5-10 APK subset that uses `Cipher.getInstance(String, Provider)` (pick from `data/results/exp_ape_gh59_*/monitor_events.csv` grepping for `CipherSpec` events) via `docker compose -f docker/docker-compose.exp-ape-gh59.yml up -d --scale instrument=1` against a small APK list. Inspect `monitor_events.csv` post-run: `g2` events for `CipherSpec` and `KeyGeneratorSpec` SHALL be > 0 (pre-fix baseline was 0). `KeyManagerFactorySpec`/`KeyPairGeneratorSpec`/`TrustManagerFactorySpec`/`SecureRandomSpec` `g2` events SHALL stay at 0 in gh61 — they use `(String, ..)`, a separate gap tracked under gh62.

## 4. Group D — `RegisterShifter` Frame-Growth Fix (clone path)

**Goal**: ensure register growth persists through dex serialisation. Implements INV-INS-80. The reflection path is removed entirely (D1 in design.md).

### 4a. Supplier cache audit (HARD GATE — must precede implementation)

- [x] 4.0 Per design.md D5, audit `MutableImplSupplier` / `DexFileMutator` cache before any Group D code change:
  - `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec && grep -rn "MutableImplSupplier\|DexFileMutator\|forMethod\|mutationsView" --include="*.java"` — enumerate every consumer of the MMI cache.
  - Read `dex-mutator/src/main/java/br/unb/cic/rv/mutator/DexFileMutator.java` and locate the per-method MMI cache (`Map<MethodSignature, MutableMethodImplementation>` or equivalent).
  - Extend `MutableImplSupplier` interface with `void replaceImpl(Method method, MutableMethodImplementation newImpl)` and implement it in `DexFileMutator` by updating the cache entry.
  - The implementation MUST cause `forMethod(m)` to return the **new** MMI on all subsequent calls within the same `DexFileMutator` instance.
  - Land 4.0 as its own commit `feat(gh61): MutableImplSupplier.replaceImpl + DexFileMutator cache update (Group D §4a)` with `refs #61` BEFORE touching `RegisterShifter`. This commit MUST compile and pass existing tests on its own (replaceImpl is unused at this stage).

### 4b. Caller inventory

- [x] 4.1 Grep for all callers of `bumpRegisterCount` and `spillLowRegisters` across the entire rvsec repo:
  `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec && grep -rn "bumpRegisterCount\|spillLowRegisters" --include="*.java"`.
  Expected callers: `RegisterShifter.java` (self), `RegisterAllocator.java:42`, `CoverageWeaver.java:136`. Record any additional caller and add to the patch list.

### 4c. Implementation

- [x] 4.2 Rewrite `RegisterShifter.bumpRegisterCount(src, delta)` per design.md API Design. Allocate `dst = new MutableMethodImplementation(src.getRegisterCount() + delta)`. For every instruction `ins` in `src.getInstructions()`:
   - if `ins` is a label-bearing branch (`BuilderInstruction10t/20t/21t/22t/30t/31t/32t` for `goto`/`if-*` family), rebuild it with a destination-owned label obtained via `dst.newLabelForIndex(srcLabel.getLocation().getIndex())`;
   - if `ins` is a `PackedSwitchPayload`, `SparseSwitchPayload`, or `ArrayPayload`, rebuild it with its label refs re-homed onto `dst`;
   - otherwise append the instruction as-is via `dst.addInstruction(ins)`.
   For every `tryBlock` in `src.getTryBlocks()`, re-add via `dst.addCatch(tryBlock.getExceptionType(), dst.newLabelForIndex(start.getLocation().getIndex()), dst.newLabelForIndex(end.getLocation().getIndex()), dst.newLabelForIndex(handler.getLocation().getIndex()))` for each handler. Copy debug items. Return `dst`. Signature changes from `static void` to `static MutableMethodImplementation`. Drop all reflection code and the `Field f = ...` block. Realistic LOC: 80-150 per design.md OQ1.
- [x] 4.3 Update `RegisterShifter.spillLowRegisters` to capture the return of `bumpRegisterCount` and return it. Signature changes from `static void` to `static MutableMethodImplementation`.
- [x] 4.4 Update `RegisterAllocator.allocate:42` to capture the returned MMI; if `RegisterAllocator` obtains its MMI via `MutableImplSupplier`, also call `supplier.replaceImpl(method, newMmi)` per design.md D5. Update any other caller from 4.1.
- [x] 4.5 Update `CoverageWeaver.injectLogCall:136` to capture the returned MMI **and** notify the supplier via `mutableSupplier.replaceImpl(method, newMmi)` (per design.md D5). All subsequent mutations in `injectLogCall` after `L136` MUST use the returned MMI — auditing every reference to the pre-spill `impl` variable in `CoverageWeaver.java:136-200` is part of this task.
- [x] 4.6 Update the `RegisterShifter.java:42-60` class docstring: remove "<h3>Why reflection on registerCount</h3>" section; replace with a "<h3>Frame growth via clone</h3>" section per P4 (current-state, not migration history).

### 4d. Tests

- [x] 4.7 Add `@Test spillGrowsDexRegistersSize` to `RegisterShifterFormatsTest.java`. Build a synthetic `ClassDef` with one method whose `MutableMethodImplementation` has `registerCount=2`. Call `RegisterShifter.spillLowRegisters(mmi, 1)`. Serialise via the temp-file API (the in-memory store is not used in this codebase):
   ```java
   Path tmp = Files.createTempFile("gh61-spill-", ".dex");
   try {
       DexBuilder db = new DexBuilder(Opcodes.getDefault());
       // add ClassDef containing the spilled method into db
       DexPool.writeTo(tmp.toString(), db);
       try (InputStream in = new BufferedInputStream(Files.newInputStream(tmp))) {
           DexBackedDexFile parsed = DexBackedDexFile.fromInputStream(Opcodes.getDefault(), in);
           DexBackedMethod m = ... // look up by name
           assertEquals(3, m.getImplementation().getRegisterCount());
       }
   } finally {
       Files.deleteIfExists(tmp);
   }
   ```
   Repeat with `registerCount=34 → 35` to mirror the `yu5.<init>` scenario. NOTE: before committing, run `javap -cp <smali-dexlib2-3.0.8.jar> com.android.tools.smali.dexlib2.writer.pool.DexPool` to confirm the exact `writeTo` overload available in the build's pinned smali version.
- [x] 4.8 Add `@Test clonePreservesLabelsAndTryBlocks` to `RegisterShifterFormatsTest.java`. Build an MMI with: a `goto` to a forward label, an `if-eqz` to a backward label, a `packed-switch` payload, and a try/catch block. Call `bumpRegisterCount(src, 1)`. Assert (a) the returned MMI's branch targets resolve to cloned instructions at the same logical positions; (b) the switch payload's case labels are re-homed; (c) the try block start/end/handler labels are present and bound to cloned instructions. This is the HARD GATE — if this test cannot pass, gh61 Group D is blocked and an upstream dexlib2 patch becomes necessary.
- [x] 4.8b Add `@Test injectionViaCoverageWeaverPersistsRegistersThroughCache`. Construct a real `DexFileMutator`, request an MMI for a synthetic method whose body needs spilling, run the full `CoverageWeaver.injectLogCall` path on it, serialise the mutator's `toDexFile()`, parse with `DexBackedDexFile`, assert the method's `registers_size` equals `oldCount + 1` AND the injected `invoke-static` to the coverage logger is present. This test fails today (cache stale) — it's the unit-level mirror of the production failure mode that motivates design.md D5.
- [x] 4.9 Run `mvn -pl dex-mutator test -Dtest=RegisterShifterFormatsTest`. All three new tests (4.7, 4.8, 4.8b) SHALL pass GREEN against the new `bumpRegisterCount` + `replaceImpl`.
- [x] 4.10 Run full reactor: `cd .../rvsec-instrumentation-dexlib2 && mvn -DskipTests=false package`. All 9 modules SHALL build SUCCESS with 0 failures. If any other module breaks on the signature change, treat as a missed caller from 4.1 and patch it.

### 4e. Empirical verification (pipeline)

- [x] 4.11 Capture `yu5.<init>` baksmali pre-fix snapshot from the current Docker image's instrumentation output: see existing `data/results/instrument_jca190_*/instrumented_apks/com.github.soundpod_16.apk`. Save the `.registers` line of `yu5.<init>` to `experimento-jca-ape-gh59/gh61_yu5_pre.txt`.
- [x] 4.12 Commit Group D source changes on `origin/modules`: `fix(gh61): persist registerCount via MMI clone in RegisterShifter (Group D)` with `refs #61`. Push.
- [x] 4.13 Rebuild Docker image: `bash docker/rvandroid/build.sh`. Wait for "Image created successfully!!!".
- [x] 4.14 Clean previous instrumentation outputs: `rm -rf out/validate_instrument_jca190/` and `data/results/instrument_jca190_*` (after confirming no in-flight runs).
- [x] 4.15 Re-instrument the 190-APK dataset: `docker compose -f docker/docker-compose.instrument-jca190.yml up -d` and monitor until all 10 containers exit 0 (~2 h).
- [x] 4.16 Verify all 190 APKs instrumented: `find data/results/instrument_jca190_*/instrument_jca190_*/instrumented_apks -name '*.apk' | wc -l` SHALL return `190`. Verify all `instrument_errors.json` files are empty (`[]`).
- [x] 4.17 Capture `yu5.<init>` baksmali post-fix and diff against the pre-fix snapshot (4.11). The `.registers N` line SHALL show `N` incremented relative to pre-fix.
- [x] 4.18 Run smoke validation: `uv run python scripts/validate_instrument_jca190.py --limit 5`. SHALL show 5/5 PASS. rv-platform manages the emulator lifecycle automatically per `CLAUDE.md` — do not start/stop emulators manually.
- [x] 4.19 Run full validation: `uv run python scripts/validate_instrument_jca190.py`. The 5 target APKs (`com.github.soundpod_16`, `com.grappim.taigamobile.fdroid_38`, `com.shub39.rush_5730`, `gizz.tapes.foss_63`, `org.fossify.musicplayer_14`) SHALL all report `PASS`. `FAIL_FATAL` SHALL stay within `19±2`; `FAIL_INSTALL` within `2±1`; `FAIL_VERIFY` SHALL drop to **0**.

## 5. Integration & Verification

- [ ] 5.1 Run optional full APE experiment: `docker compose -f docker/docker-compose.exp-ape-gh59.yml up -d` (8 containers × 163 APKs × 3 reps × 300 s ≈ 6h 40min). Compare against gh59 baseline: tasks COMPLETED ≥ 480, MOP events ≥ 4300, APKs with violation ≥ 100. Group C is expected to increase MOP event count due to new `g2` triggers — record the delta. Skip this step if 4.19 + 3.11 satisfy the user.
- [ ] 5.2 Re-stage APKs to canonical dataset path: `bash scripts/stage_apks_exp_ape_gh59.sh` (rsync the freshly instrumented 190 to `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB/`). Skip if 5.1 was skipped.
- [x] 5.3 Run `/opsx:verify` against the change — confirm artifacts and implementation match.
- [ ] 5.4 Update memory: edit `MEMORY.md` → `project_gh61_dexlib2_gaps_bundle` to record outcome (5/5 target APKs PASS, Group C g2 event delta, drift in FAIL counts, any unexpected regression).
- [ ] 5.5 Invoke `/rv-code-reviewer` via Skill tool against the Group C + Group D diff (the groups with production code changes).

## 6. Close Out

- [ ] 6.1 Run `/opsx:archive` (Full SDD: `openspec archive gh61-dexlib2-gaps-bundle --yes`). Spec deltas SHALL auto-merge into `openspec/specs/instrumentation/spec.md`.
- [ ] 6.2 Commit rv-android side of the change (compose updates, scripts if changed, archived OpenSpec dir): `chore(gh61): archive change + rv-android pipeline artifacts (closes #61)` with `closes #61`. Push.
- [ ] 6.3 Close issue #61 manually via `gh issue close 61 --repo PAMunb/rvsec --comment "..."` referencing the rvsec commits + rv-android commit + empirical results (since `closes #61` only auto-fires on default branch and we are on `modules`).

## 7. Cross-Cutting Verification

- [ ] 7.1 All 8 acceptance criteria from the proposal (INV-INS-80 through 87) verified by their corresponding tests/scenarios.
- [ ] 7.2 No edits leaked into out-of-scope files: `MonitorInvokeBuilder.java`, `DexWeaver.java`, Python wrappers in `modules/rv-instrumentation-dexlib2/`, Docker entry-point. Group C touches `PointcutExpressionParser.java`, `CallPC.java`, `PointcutMatcher.java` (param loop at `:175-176` + `fromDescriptor` at `:368-374`) only. Group D touches `MutableImplSupplier.java` (interface), `DexFileMutator.java` (cache update), `RegisterShifter.java`, `RegisterAllocator.java:42`, `CoverageWeaver.java:136` only. Group D ships as 2 commits (4.0 cache infra + 4.12 RegisterShifter implementation), so total commits on `origin/modules` for gh61 = 5 (B + A + C + 4.0 + 4.12). Confirm via `git diff origin/modules~5..origin/modules --stat`.
- [ ] 7.3 No new entries under `backup/` from this change.
- [ ] 7.4 Dropped-scope items remain in the deferred state:
  - Around-advice: `EmitterDispatchTest:58` still asserts `UnsupportedOperationException`.
  - After-throwing: `DexWeaver.applyPlan:534-540` still no-ops on `TRY_CATCH_WRAP`; `MonitorInvokeBuilder.resolveBindings:325` still injects the `0` placeholder; `WrapperEmitter.shouldWrap` still returns true for any `"after"` but the wrapper path semantics remain after-returning only.
  - `this(name)`, `withincode(...)`, `cflow(...)`, `handler(...)`, `get/set(...)`, `initialization(...)`: still unimplemented; no JCA `.mop` demands them.
  - Positive `WithinPC` semantics: matcher still treats `within(...)` as always-match per `PointcutMatcher.java:109`; the weaver continues to filter.

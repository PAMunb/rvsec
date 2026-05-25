# Proposal: gh61-dexlib2-gaps-bundle

## Why

gh59 (closed 2026-05-25) closed the wide-slot binding gap in the dexlib2 instrumenter (`PointcutMatcher.buildCallMatch` + `MonitorInvokeBuilder.expandWideSlots`) but left **5 APKs persistently failing with `java.lang.VerifyError`** in `validate_instrument_jca190.py` (`com.github.soundpod_16`, `com.grappim.taigamobile.fdroid_38`, `com.shub39.rush_5730`, `gizz.tapes.foss_63`, `org.fossify.musicplayer_14`). A Phase 1 Explore (2026-05-25, three parallel subagents reading the rvsec instrumenter sources and JCA `.mop` files) reclassified the surface area and isolated the real production bug: **`RegisterShifter.bumpRegisterCount` mutates the `private final registerCount` field of `MutableMethodImplementation` via reflection, but the dex writer reads the register count from a different source and emits the original value**. The +1 operand shift on pre-existing `Object.getClass()` null-checks in `yu5.<init>` (baksmali diff confirms `{p1..p6,p13}` → `{p2..p7,p14}` against unchanged `.registers 34`) is the *symptom* of frame-growth not landing — the shift itself is correct per the `RegisterShifter.spillLowRegisters` contract.

A second, independent gap was surfaced during the same review (claude-opus-4-7 cross-LLM analysis): the AspectJ `T+` subtype operator in `call(...)` parameter positions is not honored by the matcher. `TypeResolver.toDescriptor("Object+")` produces the malformed descriptor `Ljava/lang/Object+;`, which `PointcutMatcher.matchCall:175-176` then compares for exact equality against the actual call-site descriptor — never matching. Direct inspection of the JCA `.mop` corpus confirms exactly **2** call-sites use `Object+`: `CipherSpec.mop:40` (`call(public static Cipher Cipher.getInstance(String, Object+))`, the `g2` event) and `KeyGeneratorSpec.mop:37` (same pattern for `KeyGenerator`). These two `g2` events are silently swallowed in the dexlib2 pipeline today; AJC fires them. `KeyManagerFactorySpec.mop:35`, `TrustManagerFactorySpec.mop:37`, and `SecureRandomSpec.mop:63,77` use trailing-varargs `(String, ..)` rather than `Object+` and are a separate silent gap tracked under gh62 (AspectJ grammar coverage). The two gh61 gaps are unrelated mechanically but share the same instrumentation surface and ship together as one bundle.

GitHub Issue: [#61](https://github.com/PAMunb/rvsec/issues/61)

## What Changes

**Group A — Baseline fixtures (additive, no production behavior change)**

- Add `@Test` `endToEndWideNarrowComposition` in `MonitorInvokeBindingTest.java`: replay the `(LFoo;JZLFoo;J)V` scenario from `PointcutMatcherConstructorTest.constructorWidePrimitivesInterleavedBindArgumentsByRegisterSlot` through `MonitorInvokeBuilder.buildInvoke` and assert the emitted operand list expands every `J` to its `(vN, vN+1)` pair while keeping `Z`/refs single-slot. Closes the **matcher↔emitter integration gap** identified in Q5 of the Explore (the gap that hid the gh59 bug).
- Add `@Test` `returningDoubleExpandsToWidePair` in `MonitorInvokeBindingTest.java`, mirroring the existing `AfterReturning-static-wide-return` (`returning(long)`) scenario but with descriptor `D`. Asserts emitted register array is `[vN, vN+1]`.


**Group B — Test coverage for existing matcher infrastructure**

- Expand `PointcutMatcherTest.java` to cover `CombinedPC.AND` and `CombinedPC.OR` matching (binding-merge semantics through AND, short-circuit through OR).
- Add `NotWithinPC` coverage: positive class match (within-target should not fire) and negative class match (out-of-target should fire). Use a class FQN prefix matching the JCA `MultiSpec_1MonitorAspect.aj` base aspect pattern (`!within(sun..*)`, `!within(java..*)`).
- No production code changes — `PointcutMatcher.matchCombined:117-129` + `matchNotWithin:131-137` already work; this is **test debt** identified in Phase 1 Explore Q2.

**Group C — `Object+` subtype operator in `call(...)` parameters**

- **2** JCA `.mop` call-sites use `Object+` as a subtype marker for the `Provider` parameter: `CipherSpec.mop:40` and `KeyGeneratorSpec.mop:37` (both `getInstance(String, Object+)` for the `g2` event). The current parser passes `Object+` through `splitParams` unchanged; `TypeResolver.toDescriptor("Object+")` produces the malformed descriptor `Ljava/lang/Object+;`; `PointcutMatcher.matchCall:175-176` does exact `contentEquals` against `Ljava/security/Provider;`. Result: these 2 `g2` events silently never fire in the dexlib2 pipeline (AJC fires them).
- Fix: strip trailing `+` in `splitParams`, plumb a per-param `boolean isSubtype` flag through `CallPC`, and use `InheritanceResolver.isAssignableFrom` when the flag is set (matcher already imports `InheritanceResolver`). The matcher MUST convert DEX descriptors back to FQN before calling `InheritanceResolver` — primitives in particular MUST be converted to their FQN form (`"I"` → `"int"`, `"D"` → `"double"`, etc.) so that `InheritanceResolver.isPrimitive` (which expects FQN names) correctly rejects them via the `Object` fast-path. The current `PointcutMatcher.fromDescriptor` returns primitives unchanged (`"I"` stays `"I"`) and MUST be extended.
- Empirical impact: re-run an APE smoke (~10 APKs that exercise `Cipher.getInstance(String, Provider)`) and confirm `g2` event count for `CipherSpec` and `KeyGeneratorSpec` grows relative to gh59 baseline (pre-fix: 0).

**Group D — `RegisterShifter` frame-growth fix**

- The 5 residual `FAIL_VERIFY` APKs (`com.github.soundpod_16`, `com.grappim.taigamobile.fdroid_38`, `com.shub39.rush_5730`, `gizz.tapes.foss_63`, `org.fossify.musicplayer_14`) all exhibit the same pattern: `bumpRegisterCount` succeeds in-process (no `ReflectiveOperationException`) but the serialised dex `registers_size` field stays at the old value, leaving operand references past the declared frame.
- Replace the reflection-based mutation in `RegisterShifter.bumpRegisterCount` with a clone path: allocate a fresh `MutableMethodImplementation(oldCount + delta)`, copy every instruction (operands already shifted by the caller), re-home labels and try blocks, return the new MMI. The reflection path is dropped entirely — it is JDK-fragile (per the existing `RegisterShifter.java:42-47` docstring) and the production failure proves the dex writer does not honor the mutation regardless. P1 simplicity favors a single deterministic path; P3 forbids carrying the reflection shim "for compatibility".
- API change: `bumpRegisterCount(mmi, delta) → MutableMethodImplementation` (returns the grown MMI). Callers (`spillLowRegisters`, `RegisterAllocator.allocate:42`, `CoverageWeaver.injectLogCall:136`) accept the replacement and propagate it through.
- **Supplier cache addition** (design.md D5): the `MutableImplSupplier` interface gains a new method `void replaceImpl(Method, MutableMethodImplementation)`, implemented by `DexFileMutator` to update its per-method MMI cache. Callers that consume the new MMI from `bumpRegisterCount`/`spillLowRegisters` and originally obtained their source MMI from a supplier MUST invoke `replaceImpl` immediately after capturing the new MMI. Without this, `DexFileMutator.toDexFile()` serialises the pre-spill MMI from the stale cache and the fix is invisible at the dex-file level. This is a separate commit (Group D §4a, task 4.0) shipped before the `RegisterShifter` rewrite so the cache infrastructure is in place when the callers need it.
- The 5 target APKs MUST move from `FAIL_VERIFY` to `PASS` in `validate_instrument_jca190.py` after the fix.

**Out of scope (deferred to future changes)**

- **Around-advice**: Phase 1 confirmed **zero `around` keyword** in any JCA `.mop` at `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/*.mop`. `EmitterDispatchTest.java:58` already asserts `UnsupportedOperationException` for around-advice — a deliberate, documented limitation. Open a separate change when the first MOP spec requires around.
- **After-throwing advice**: the dispatch/emitter path exists (`EmitterDispatch.select` routes to `AfterThrowingEmitter`, which emits a `TRY_CATCH_WRAP` plan; `MonitorInvokeBuilder.resolveBindings:325` injects a `0` placeholder for the `throwing(name)` register), but `DexWeaver.applyPlan:534-540` no-ops on `TRY_CATCH_WRAP` ("Pending: task 5.x integration"). `WrapperEmitter.shouldWrap` returns true for any `"after"` advice — including `after-throwing` — but the wrapper path only produces semantically correct rewrites for `after-returning` (the `WrapperEmitter.java:51` docstring documents this scope). The combined effect is that no `after-throwing` advice is realised end-to-end; combined with zero `after() throwing(...)` advice in any JCA `.mop`, no current downstream is blocked. Implementing after-throwing is feature work, not a bug fix.
- **`this(name)`, `withincode(...)`, `cflow(...)`, `handler(...)`, `get/set(...)`, `initialization(...)`**: no JCA `.mop` uses these primitives. Marked as known dexlib2 gaps; open when a spec demands them. **For the `generic`/`generic_new` spec sets these gaps are material** — `get(...)` alone occurs 356× in `generic/` and 158× in `generic_new/`, and `T+` in `call(...)` owner position is the dominant pattern in `generic_new/` — but those sets are not the gh61 target. They are tracked under **gh62 (AspectJ grammar coverage)**.
- **Positive `WithinPC` semantics**: matcher treats `within(...)` as always-match and lets the weaver filter. Documented choice; reverse only when a JCA spec demands matcher-side filtering.
- **Trailing-varargs `(T, ..)` mixed form**: 4+ JCA call-sites (`KeyManagerFactory`, `TrustManagerFactory`, `SecureRandom.getInstance(String, ..)`) use a leading concrete type followed by `..`. `PointcutExpressionParser.isVarargs:256-258` only recognises `..` as the *sole* element of the param list; mixed forms fall into the exact-match loop where `TypeResolver.toDescriptor("..")` produces the malformed `Ljava/lang/..;`. Symmetric to the `Object+` bug but mechanically separate. Tracked under gh62.
- **`BaseAspect.notwithin()` named-pointcut reference**: `MOP_CommonPointCut` references the named `BaseAspect.notwithin()` (an OR-chain of platform-namespace `!within(...)` filters). The dexlib2 parser wraps named refs in `NamedRefPC` always-match (`PointcutMatcher.java:109-112`), so the filter never executes inside the matcher. Whether the weaver re-applies the filter independently is unverified; tracked under gh62.

## Capabilities

### New Capabilities
*(none — all changes are within the existing instrumentation capability)*

### Modified Capabilities
- `instrumentation`: (a) refine `RegisterShifter`'s frame-growth contract so that `spillLowRegisters(threshold=0, delta=N)` produces a dex output whose `registers_size` field equals `oldCount + N` (the operand-shift contract itself is unchanged — already correct per current spec); (b) add a supplier-cache replacement contract (`MutableImplSupplier.replaceImpl`) so the grown MMI propagates through `DexFileMutator`'s per-method cache to the final dex serialisation; (c) extend the pointcut matcher to honor the AspectJ `T+` subtype operator in `call(...)` parameter positions via `InheritanceResolver.isAssignableFrom` against FQN-form descriptors (primitive-safe).

## Impact

**Affected modules (sibling rvsec repo at `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`):**

- `dex-mutator/src/main/java/br/unb/cic/rv/mutator/MutableImplSupplier.java` (Group D §4a — add `replaceImpl(Method, MutableMethodImplementation)` to the interface).
- `dex-mutator/src/main/java/br/unb/cic/rv/mutator/DexFileMutator.java` (Group D §4a — implement `replaceImpl` by updating the per-method MMI cache; the canonical `MutableImplSupplier`).
- `dex-mutator/src/main/java/br/unb/cic/rv/mutator/RegisterShifter.java` (Group D — rewrite `bumpRegisterCount` to allocate-and-return a grown MMI; drop the reflection path).
- `dex-mutator/src/main/java/br/unb/cic/rv/mutator/RegisterAllocator.java:42` (Group D — accept new MMI from `bumpRegisterCount` and notify the supplier via `replaceImpl`).
- `coverage-weaver/src/main/java/br/unb/cic/rv/coverage/CoverageWeaver.java:136` (Group D — `injectLogCall` accepts new MMI from `spillLowRegisters`, notifies supplier, and uses the new MMI for every mutation after L136).
- `dex-mutator/src/test/java/br/unb/cic/rv/mutator/RegisterShifterFormatsTest.java` (Group D — `spillGrowsDexRegistersSize` + `clonePreservesLabelsAndTryBlocks` + `injectionViaCoverageWeaverPersistsRegistersThroughCache` roundtrip assertions).
- `advice-emitter/src/test/java/br/unb/cic/rv/emitter/MonitorInvokeBindingTest.java` (Group A — 2 new fixtures).
- `pointcut-engine/src/main/java/br/unb/cic/rv/pointcut/PointcutExpressionParser.java` (Group C — strip `+` in `splitParams`, set `isSubtype` flag).
- `pointcut-engine/src/main/java/br/unb/cic/rv/pointcut/CallPC.java` (Group C — add per-param `isSubtype` flag in `ParamSpec`).
- `pointcut-engine/src/main/java/br/unb/cic/rv/pointcut/PointcutMatcher.java:175-176` (Group C — branch on `isSubtype` to use `InheritanceResolver.isAssignableFrom`).
- `pointcut-engine/src/test/java/br/unb/cic/rv/pointcut/PointcutMatcherTest.java` (Group B coverage suite + Group C `callParamSubtypeMarkerMatchesSubclass`).

**Affected modules (rv-android uv workspace):**

- `modules/rv-instrumentation-dexlib2/` — Python wrapper unchanged; only consumes the rebuilt `instr-cli.jar`.

**Pipeline impact:**

- Docker image `phtcosta/rvandroid:0.9.0` requires rebuild (`bash docker/rvandroid/build.sh`) after each rvsec commit; the build pulls `origin/modules` so push gates the rebuild.
- `docker-compose.instrument-jca190.yml` re-runs against the 190 originals at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs/` (~2 h wall-clock).
- `validate_instrument_jca190.py` re-runs against the freshly instrumented set (~25 min on a single emulator).
- Optional: full APE experiment via `docker-compose.exp-ape-gh59.yml` (8 containers × 163 APKs × 3 reps × 300 s ≈ 6h 40min) for end-to-end regression check — baseline 480/489 tasks, 4373 MOP events, 106/163 APKs with violation. Re-run only if RegisterShifter fix appears risky in smoke.

**PRD references:**

- **FR01** (Monitor generation): unaffected — monitors are emitted upstream of `RegisterShifter`.
- **FR02** (APK instrumentation): correctness improved on two axes — (a) Group D: frame growth now persists, eliminating the `VerifyError` failure mode on methods whose pre-existing operand register references must shift to make room for coverage-spill locals (5/190 → 0/190 expected); (b) Group C: `Object+` subtype matcher now fires `g2` events for `Cipher.getInstance(String, Provider)` and `KeyGenerator.getInstance(String, Provider)`, closing a silent false-negative in 2 JCA specs (`CipherSpec.mop`, `KeyGeneratorSpec.mop`).
- **NFR08** (Reproducibility): the dex-writer behavior is deterministic regardless of host JDK because the new clone path does not depend on reflection on a `private final` field.

**Cross-module dependencies:**

- The `MutableImplSupplier` interface (in `dex-mutator/`) gains a new method `replaceImpl`. Every consumer of the interface (today: `CoverageWeaver` in `coverage-weaver/`, potentially `RegisterAllocator` if it obtains MMI via the supplier) MUST update to call `replaceImpl` after capturing a returned MMI. Task 4.0 grep enumerates the consumers before the interface change ships, so the cross-module update lands atomically. No new external dependency.
- The Maven artifact chain inside `rvsec-instrumentation-dexlib2` is unchanged: `dex-mutator` ← `coverage-weaver` ← `cli` → `instr-cli.jar` baked into Docker image.

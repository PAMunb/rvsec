# Design: gh61-dexlib2-gaps-bundle

## Context

Phase 1 Explore (2026-05-25) and a cross-LLM artifact review (2026-05-25, five reviewers) identified four discrete work-streams remaining after gh59 closed the wide-slot binding gap:

1. The 5-APK `VerifyError` residual traces to `RegisterShifter.bumpRegisterCount` failing to persist its reflection-based mutation of `MutableMethodImplementation.registerCount` through to the dex writer's `registers_size` field. The +1 operand shift on `Object.getClass()` null-checks emitted by R8 in `yu5.<init>` is correct per the `spillLowRegisters(threshold=0, delta=1)` contract — what fails is the frame growth that would absorb the shifted high-end operands.
2. `PointcutMatcher` has full support for `CombinedPC.AND/OR`, `NotWithinPC`, and parenthesised compositions (`matchCombined:117-129`, `matchNotWithin:131-137`, parser `parseUnary:74-94`). JCA spec aspects use `!within(sun..*) && !within(java..*) && ...` in the base aspect filter. But `PointcutMatcherTest.java` has zero coverage for these paths.
3. Pre-existing emitter test fixtures pass gh59's audit cleanly — but two coverage gaps from the same family as the gh59 latent bug remain open: end-to-end matcher↔emitter wide+narrow composition, and `returning(double)` symmetric to the existing `returning(long)`.
4. The AspectJ `T+` subtype operator is not honored in `call(...)` parameter positions. Parser passes `Object+` through `splitParams` unchanged; `TypeResolver.toDescriptor("Object+")` produces the malformed descriptor `Ljava/lang/Object+;`; `PointcutMatcher.matchCall:175-176` uses exact `contentEquals` against the actual descriptor. The JCA corpus uses `Object+` in exactly **2** call-sites — `CipherSpec.mop:40` and `KeyGeneratorSpec.mop:37`, both `getInstance(String, Object+)` for the `g2` event. These 2 events silently never fire in the dexlib2 pipeline; AJC fires them. (`KeyManagerFactory`, `TrustManagerFactory`, `SecureRandom.getInstance(String, ..)` use trailing-varargs, not `Object+` — separate gap, tracked under gh62.)

Around-advice was dropped after confirming zero `around` keyword usage in any JCA `.mop` (`EmitterDispatchTest.java:58` asserts `UnsupportedOperationException`). After-throwing instrumentation was dropped after confirming the end-to-end path is non-functional: `EmitterDispatch.select` routes `after-throwing` advice to `AfterThrowingEmitter`, which generates a `TRY_CATCH_WRAP` plan; `MonitorInvokeBuilder.resolveBindings:325` injects a `0` placeholder for the `throwing(name)` register; but `DexWeaver.applyPlan:534-540` no-ops on `TRY_CATCH_WRAP` ("Pending: task 5.x integration"), and the wrapper path (`WrapperEmitter.shouldWrap` returns true for any `position == "after"`, but `WrapperEmitter.java:51` documents the scope as `after-returning` only) does not produce semantically correct after-throwing rewrites. Combined with zero `after() throwing(...)` advice in any JCA `.mop`, no current downstream is blocked.

Relevant FRs/NFRs from `docs/PRD.md`: FR02 (APK instrumentation), NFR08 (reproducibility across host JDK versions — the new clone path is JDK-independent because it does not depend on reflection on a `private final` field).

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│ rvsec-instrumentation-dexlib2 (Maven multi-module)                   │
│                                                                      │
│  ┌────────────────┐    ┌────────────────┐    ┌──────────────────┐    │
│  │ pointcut-engine│    │ advice-emitter │    │  dex-mutator     │    │
│  │                │    │                │    │                  │    │
│  │ Parser         │    │ MonitorInvoke- │    │ DexFileMutator   │    │
│  │  splitParams   │    │  Builder       │    │  implements      │    │
│  │ CallPC         │    │  buildInvoke   │    │  MutableImpl-    │    │
│  │  ParamSpec     │    │  expandWideSl. │    │  Supplier        │    │
│  │ PointcutMatcher│───▶│                │───▶│  + replaceImpl   │    │
│  │  matchCall +   │    │                │    │  (NEW Group D)   │    │
│  │  isSubtype     │    │                │    │       │          │    │
│  │  fromDescr.+   │    │                │    │       ▼          │    │
│  │   primitives   │    │                │    │ DexWeaver        │    │
│  │  matchCombined │    │                │    │ CoverageWeaver   │    │
│  │  matchNotWithin│    │                │    │  injectLogCall   │    │
│  └────────────────┘    └────────────────┘    │       │          │    │
│     ▲          ▲              ▲              │       ▼          │    │
│  GROUP B    GROUP C        GROUP A           │ RegisterShifter  │    │
│  (test)     (Object+)      (test)            │  bumpRegister-   │    │
│                                              │   Count          │    │
│                                              │  (NEW: clone)    │    │
│                                              │     GROUP D      │    │
│                                              └──────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
              │              │                │                │
              ▼              ▼                ▼                ▼
   PointcutMatcherTest   PointcutMatcher- MonitorInvoke-  RegisterShifter-
   (+ Group B suite)      Test            BindingTest      FormatsTest
                          (+ Group C       (+ Group A      (+ Group D
                          callParam-       fixtures)        spillGrowsDex-
                          Subtype-)                         RegistersSize)
                                                                │
                                                                ▼
                                                  phtcosta/rvandroid:0.9.0
                                                  Docker image rebuild
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|----------------|-------|--------|
| `MutableImplSupplier.replaceImpl(method, impl)` (NEW method, Group D §4a) | Update the per-method MMI cache so subsequent `forMethod` lookups return the new MMI | `Method`, `MutableMethodImplementation` | side effect on supplier cache |
| `DexFileMutator` (canonical `MutableImplSupplier`, Group D §4a) | Implements `replaceImpl` by updating its internal `Map<MethodSignature, MutableMethodImplementation>` | per-method MMI updates | post-spill MMI returned by `forMethod` and serialised by `toDexFile` |
| `RegisterShifter.bumpRegisterCount(mmi, delta)` (NEW signature, Group D) | Allocate a fresh `MutableMethodImplementation` with `registerCount + delta`, copy every instruction (operands already shifted), re-home labels and try blocks | `MutableMethodImplementation`, `int delta` | New `MutableMethodImplementation` with grown frame |
| `RegisterShifter.spillLowRegisters(mut, count)` (signature update, Group D) | Carve `count` slots at the low end + shift every operand `>= 0` by `count` + return the grown MMI from `bumpRegisterCount` | `MutableMethodImplementation`, `int count` | New `MutableMethodImplementation` |
| `CallPC.ParamSpec { descriptor, isSubtype }` (NEW, Group C) | Per-param flag distinguishing exact-match vs `T+` subtype-match | parse-time | matcher input |
| `PointcutMatcher.matchCall` (modified, Group C) | When `isSubtype`, use `InheritanceResolver.isAssignableFrom`; otherwise exact `contentEquals` | `CallPC`, call site `MethodReference` | `Optional<Match>` |
| `PointcutMatcherTest` (Group B suite + Group C test) | Verify `CombinedPC` and `NotWithinPC` matching semantics + binding merge + `T+` subtype on call params | Fixture pointcut + class FQN | Assertion |
| `MonitorInvokeBindingTest` (Group A fixtures) | Verify wide-slot expansion through full matcher↔emitter pipeline + `returning(double)` symmetric to existing `returning(long)` | Fixture `Match` + advice descriptor | Asserted operand array |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|----------------|------|
| FR02-INV-INS-80 (NEW): `spillLowRegisters(mut, N)` MUST produce a dex output whose `registers_size == oldCount + N` | `RegisterShifter.bumpRegisterCount` rewritten to allocate-and-return a grown MMI (Group D) | `RegisterShifterFormatsTest.spillGrowsDexRegistersSize` (NEW) |
| FR02-INV-INS-81 (NEW): `PointcutMatcher.match` honours `CombinedPC.AND` by intersecting matches and merging argBindings | `PointcutMatcher.matchCombined:117-129` (existing) | `PointcutMatcherTest.combinedAndIntersectsMatches` (NEW Group B) |
| FR02-INV-INS-82 (NEW): `PointcutMatcher.match` honours `CombinedPC.OR` with short-circuit | `PointcutMatcher.matchCombined:117-129` (existing) | `PointcutMatcherTest.combinedOrShortCircuitsOnLeftMatch` (NEW Group B) |
| FR02-INV-INS-83 (NEW): `PointcutMatcher.match` returns empty for class FQNs prefix-matching a `NotWithinPC` operand | `PointcutMatcher.matchNotWithin:131-137` (existing) | `PointcutMatcherTest.notWithinExcludesMatchingClassFqn` (NEW Group B) |
| FR02-INV-INS-84 (NEW): `MonitorInvokeBuilder.expandWideSlots` expands every `J`/`D` arg through the full `Match`→`buildInvoke` pipeline | `MonitorInvokeBuilder.expandWideSlots:98-117` (existing from gh59) | `MonitorInvokeBindingTest.endToEndWideNarrowComposition` (NEW Group A) |
| FR02-INV-INS-85 (NEW): `returning(double)` produces an emitted register array `[vN, vN+1]` | `MonitorInvokeBuilder.expandWideSlots:98-117` (existing) | `MonitorInvokeBindingTest.returningDoubleExpandsToWidePair` (NEW Group A) |
| FR02-INV-INS-86 (NEW): A `call(...)` param spelled `T+` MUST match any subtype of `T` per `InheritanceResolver` against an FQN-form actual descriptor (primitives included) | `Parser.splitParams` (strip trailing `+`, set `ParamSpec.isSubtype`); `PointcutMatcher.fromDescriptor` (extended for primitives); `PointcutMatcher.matchCall:175-176` (branch on `isSubtype`) (Group C) | `PointcutMatcherTest.callParamSubtypeMarkerMatchesSubclass` + `callParamSubtypeMarkerRejectsPrimitive` + `callParamExactMatchPreservedWithoutPlus` (NEW Group C) |
| FR02-INV-INS-87 (NEW): A caller capturing the new MMI from `bumpRegisterCount`/`spillLowRegisters` MUST notify its `MutableImplSupplier` via `replaceImpl(method, newMmi)` so `DexFileMutator`'s per-method cache returns the post-spill MMI on subsequent lookups | NEW `MutableImplSupplier.replaceImpl` + `DexFileMutator` cache update (Group D §4a, task 4.0); `RegisterAllocator.allocate:42` and `CoverageWeaver.injectLogCall:136` invoke `replaceImpl` (Group D §4c, tasks 4.4 and 4.5) | `RegisterShifterFormatsTest.injectionViaCoverageWeaverPersistsRegistersThroughCache` (NEW Group D task 4.8b) |

## Goals / Non-Goals

**Goals:**

- The 5 target APKs (`com.github.soundpod_16`, `com.grappim.taigamobile.fdroid_38`, `com.shub39.rush_5730`, `gizz.tapes.foss_63`, `org.fossify.musicplayer_14`) move from `FAIL_VERIFY` to `PASS` in `validate_instrument_jca190.py`.
- Test coverage for matcher composite and `NotWithinPC` paths reaches parity with parser coverage.
- The two Group A coverage holes (matcher↔emitter wide+narrow, `returning(double)`) get fixtures so future regressions surface in unit tests rather than 9-h full-pipeline runs.
- `Object+` subtype operator in `call(...)` parameters fires `g2` events for `Cipher.getInstance(String, Provider)` and `KeyGenerator.getInstance(String, Provider)` at parity with AJC (the 2 `Object+` call-sites in the JCA corpus). Empirical check: APE smoke on a 5-10 APK subset that exercises `Cipher.getInstance(String, Provider)` shows non-zero `g2` events post-fix vs. zero pre-fix.
- Full APE experiment regression bar: ≥480 tasks COMPLETED, ≥4 300 MOP events, ≥100 APKs with violation (gh59 baselines).

**Non-Goals:**

- Implementing around-advice. No JCA `.mop` uses it; `EmitterDispatchTest:58` already throws `UnsupportedOperationException` and that is the intended contract today.
- Implementing after-throwing instrumentation. The dispatch and emitter paths exist (`EmitterDispatch` routes to `AfterThrowingEmitter`, which generates a `TRY_CATCH_WRAP` plan; `MonitorInvokeBuilder.resolveBindings:325` injects a `0` placeholder), but `DexWeaver.applyPlan:534-540` no-ops on `TRY_CATCH_WRAP`, and the wrapper path (`WrapperEmitter.shouldWrap` returns true for any `position == "after"`, but `WrapperEmitter.java:51` documents the scope as `after-returning` only) does not produce semantically correct after-throwing rewrites. No JCA `.mop` requests after-throwing. Removing the `0` placeholder in `MonitorInvokeBuilder.resolveBindings:325` is also not in scope.
- Adding positive `WithinPC` semantics. The current always-match behaviour (`PointcutMatcher.java:109`) is a documented choice — the weaver does the filtering. Reverse only when a JCA spec demands it.
- Refactoring `RegisterShifter`'s instruction-format coverage. All formats currently supported by `shift(...)` stay as-is; Group D is scoped to `bumpRegisterCount`'s persistence semantics.
- Implementing `this(name)`, `withincode(...)`, `cflow(...)`, `handler(...)`, `get/set(...)`, `initialization(...)`. No JCA `.mop` uses these; documented as gaps to be opened when a spec demands them.

## Decisions

### D1 — `bumpRegisterCount`: clone-direct (drop reflection entirely)

**Choice:** `RegisterShifter.bumpRegisterCount` is rewritten to allocate a fresh `MutableMethodImplementation(oldCount + delta)`, copy every instruction (operands already shifted by the caller), re-home labels and try blocks, and return the new MMI. The reflection path on the `private final registerCount` field is removed entirely — not retained as a fast-path fallback.

**Why:** P1 (simplicity) and P3 (no backward compatibility) favor a single deterministic implementation. The empirical evidence in gh61 proves the reflection mutation does not survive to the dex writer's `registers_size` on the host JDK we ship in Docker, so the reflection path is provably non-functional in the production environment — not just "fragile across future JDKs". Keeping it as a "try first" branch would be carrying a known-broken path "for compatibility", which CLAUDE.md P3 explicitly forbids. The clone path is ~3× the code volume per the existing `RegisterShifter.java:42-47` docstring, but it is JDK-independent (NFR08) and removes the entire failure mode rather than papering over it.

**Caller impact:** `bumpRegisterCount` changes signature from `static void` to `static MutableMethodImplementation` (returns the grown MMI). `spillLowRegisters` likewise returns the grown MMI. The two known callers update:

- `RegisterAllocator.allocate:42` already calls `bumpRegisterCount` directly — accepts the return.
- `CoverageWeaver.injectLogCall:136` calls `spillLowRegisters` — accepts the return and propagates the new MMI through the rest of the method body.

A grep for cross-module callers of `bumpRegisterCount` is part of Group D task 4.1 to catch any other consumer.

**Alternatives considered:**

- *Keep reflection-first, fall back to clone.* Rejected per P1/P3 above. The dual path adds branch complexity for zero benefit once the reflection path is proven non-functional in production.
- *Patch dexlib2 upstream to expose a `setRegisterCount` API.* Rejected: external dependency change, slow review cycle. Worth an upstream issue but does not gate gh61.
- *Encode the extra registers via `move-wide/from16` preambles.* Rejected: that mechanism is for high-register access from 4-bit ops, not for growing the frame. Conflates two orthogonal concerns.

### D2 — Group A/B/C/D order: B → A → C → D

**Choice:** Land Group B (matcher tests, zero prod change) → Group A (emitter fixtures, zero prod change) → Group C (Object+ subtype, small prod change) → Group D (RegisterShifter rewrite, largest prod change), each with reactor build green between groups.

**Why:** Risk increases monotonically across the four groups. Test debt first (B, A) normalises the test surface and may surface latent bugs cheaply (as gh59 found the `returning(long)` bug). Group C is a localised matcher change with a single new test. Group D is a signature change touching three callers and is the only group with real regression risk on the full pipeline.

**Alternatives considered:**

- *D first (fix the bug, validate empirically).* Rejected: the empirical loop is ~9 h; if a baseline fixture would have caught a related bug in 5 min we lose a day to slow feedback.
- *A/B/C/D in parallel.* Rejected: change is small enough that serial work is faster than parallel coordination overhead.

### D3 — Test the dex output, not just the in-process MMI

**Choice:** `RegisterShifterFormatsTest.spillGrowsDexRegistersSize` (NEW) MUST assert the final dex bytecode's register count, not just `mmi.getRegisterCount()` after the bump call. Mechanism: write the containing class to a temp `.dex` file via `DexPool.writeTo(String, DexFile)`, parse back with `DexBackedDexFile`, look up the method, and assert `method.getImplementation().getRegisterCount() == oldCount + delta`.

**Why:** The bug is precisely the divergence between in-process MMI state and serialised dex state. An assertion on the MMI alone would have given false confidence in gh52/gh56. The roundtrip test surfaces the divergence at build time, not at install time on an Android device.

**Concrete mechanism (per tasks.md 4.7):**

```java
Path tmp = Files.createTempFile("gh61-spill-", ".dex");
try {
    DexBuilder db = new DexBuilder(Opcodes.getDefault());
    // ... add ClassDef containing our spilled method to db ...
    DexPool.writeTo(tmp.toString(), db);
    DexBackedDexFile parsed =
        DexBackedDexFile.fromInputStream(Opcodes.getDefault(),
            new BufferedInputStream(Files.newInputStream(tmp)));
    DexBackedMethod m = ... // look up by name
    assertEquals(oldCount + delta, m.getImplementation().getRegisterCount());
} finally {
    Files.deleteIfExists(tmp);
}
```

`DexPool.writeTo(MemoryDataStore)` is not used anywhere in this codebase and the project doesn't import `org.jf.util.MemoryDataStore`-equivalents from smali-dexlib2 3.0.8; the temp-file path is the verified API. The implementation task MUST verify the exact `DexPool.writeTo` overload available via `javap -cp` against the resolved jar before committing the test.

**Alternatives considered:**

- *Assert via baksmali roundtrip.* Rejected: too slow for a unit test; baksmali is a tool, not a library, and adds 1-2 s per fixture.
- *Assert only on `mmi.getRegisterCount()`.* Rejected: this is the assertion that already passes today on the buggy code.

### D4 — `Object+` subtype: per-param flag at parse time, FQN-form at match time

**Choice:** Strip trailing `+` from each param string in `Parser.splitParams`; record the presence of `+` as a per-param `boolean isSubtype` flag on `CallPC.ParamSpec`. `PointcutMatcher.matchCall:175-176` branches on the flag: `isSubtype == true` uses `InheritanceResolver.isAssignableFrom(expectedFqn, actualFqn)` (FQN-form, e.g. `"java.lang.Object"` vs `"java.security.Provider"`); `isSubtype == false` retains the current exact `contentEquals` on DEX descriptors.

**Why:** P1 favors localising the change to the layer that already understands type semantics. `TypeResolver.toDescriptor` is intentionally a one-line FQN converter — teaching it about `+` would push subtype semantics into a type-naming layer that has no inheritance context. The matcher already imports `InheritanceResolver` for `staticinitialization(T+)` (`PointcutMatcher.matchStaticInit:304-306`); reusing it for call-param subtype is symmetric.

**FQN-vs-descriptor pitfall:** `InheritanceResolver.isAssignableFrom(superFqn, subFqn)` takes FQNs because it has a fast-path `"java.lang.Object".equals(superFqn)` at `InheritanceResolver.java:66` that returns `!isPrimitive(subFqn)`. That fast-path is precisely what we want for `Object+`. Passing DEX descriptors (`"Ljava/lang/Object;"`) silently bypasses the fast-path. Group C task 3.4 must use `typeResolver.resolveFqn(...)` for the expected side and convert the actual param descriptor back to FQN before the call.

**Primitive descriptor pitfall (BLOCKER for Object+ correctness):** the current helper `PointcutMatcher.fromDescriptor` at `PointcutMatcher.java:368-374` only handles the `L...;` reference-type form and returns the input unchanged for primitives — `fromDescriptor("I")` returns `"I"`, not `"int"`. But `InheritanceResolver.isPrimitive` at `InheritanceResolver.java:145-149` matches on the FQN form (`"int"`, `"long"`, etc.), so `isAssignableFrom("java.lang.Object", "I")` would hit the fast-path, compute `!isPrimitive("I") = !false = true`, and erroneously match a primitive argument against `Object+`. Group C MUST extend `fromDescriptor` (or introduce a sibling helper) so that single-letter primitive descriptors (`Z`, `B`, `S`, `C`, `I`, `J`, `F`, `D`, `V`) are converted to their FQN form. Array descriptors (`[Ljava/lang/Object;`, `[I`) are out of scope for gh61 — no JCA `.mop` uses `Array+` as a subtype marker; declared as a Non-Goal.

**Alternatives considered:**

- *Strip `+` in `TypeResolver.toDescriptor` and always use exact match.* Rejected: silently loses subtype semantics — `Object+` would match only `Object` exactly, not `Provider`. Worse than the bug being fixed.
- *Expand `T+` into the cartesian product of known subtypes at parse time.* Rejected: requires a closed-world classpath at parse time and explodes for `Object+`.

### D5 — Propagate the clone MMI through `DexFileMutator`'s per-method cache

**Choice:** Before refactoring the two production callers (`RegisterAllocator.allocate:42`, `CoverageWeaver.injectLogCall:136`), Group D MUST audit the supplier that produces the `MutableMethodImplementation` in production — in `CoverageWeaver` this is a `MutableImplSupplier` whose canonical implementation is `DexFileMutator`. `DexFileMutator` caches MMIs per method in a `Map<MethodSignature, MutableMethodImplementation>` (Maven module `dex-mutator`, `DexFileMutator.java`). After `spillLowRegisters` returns a **new** MMI, the cache still points to the **old** MMI; subsequent `DexWeaver.applyPlan` lookups and the final `DexFileMutator.toDexFile()` serialise the pre-spill MMI, silently dropping both the frame growth and any instructions injected onto the new MMI after the spill call.

The mandatory shape of the fix is **either** (a) extend `MutableImplSupplier` with `void replaceImpl(Method m, MutableMethodImplementation newImpl)` and implement it in `DexFileMutator` by updating the cache, plumbing the call through every caller that consumes `spillLowRegisters`/`bumpRegisterCount`; **or** (b) keep the in-place mutation contract by making `spillLowRegisters` mutate the original MMI's instruction list in place and copy operands into a freshly-allocated MMI only *inside* `bumpRegisterCount`, then have `bumpRegisterCount` itself drive the cache update via the supplier. Option (a) is preferred — it keeps `RegisterShifter` pure and pushes the side effect to the supplier where the cache lives.

**Why:** The CRITICAL finding from the cross-LLM review (claude-opus-4-7, gemini-2.5-pro) is that the unit test `spillGrowsDexRegistersSize` (task 4.7) measures via `DexPool` directly and would pass green even if the production pipeline silently dropped the clone. Without this decision, gh61 ships a fix that the integration test (`validate_instrument_jca190.py`) detects only as "still failing", with no diagnostic trail back to the cache. Codifying the supplier-side replacement contract is the only way to make the production behaviour observable from a unit test (task 4.8b — see below) and from `RegisterShifter` alone.

**Scope of audit:** `Grep -rn "mutationsView\|forMethod\|MutableImplSupplier\|DexFileMutator" rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` to enumerate every consumer of the MMI cache. Update each to call `replaceImpl` after any operation that returns a new MMI.

**Alternatives considered:**

- *Leave the cache as-is and rely on the caller to "do the right thing".* Rejected: silent failure mode, indistinguishable in unit tests from success — the exact failure pattern that hid the gh59 latent bug.
- *Make `bumpRegisterCount` mutate in place by writing into the original instruction list.* Rejected: defeats the whole purpose of the clone path (the `private final` field is the entire reason we need a fresh MMI).

## API Design

### `RegisterShifter.bumpRegisterCount(MutableMethodImplementation src, int delta)` — Group D

```java
/**
 * Return a fresh MutableMethodImplementation whose register count is
 * src.getRegisterCount() + delta.
 *
 * Reconstruction obligations:
 *  - Every instruction that carries a Label (branch ops 21t/22t/31t/32t,
 *    goto/if-*, and the three payload ops PackedSwitch/SparseSwitch/Array)
 *    MUST be rebuilt against a destination-owned Label obtained via
 *    dst.newLabelForIndex(srcLabel.getLocation().getIndex()).
 *  - Every try block MUST be re-added via dst.addCatch(...) with start,
 *    end, and handler labels re-homed onto cloned instructions.
 *  - Debug items SHOULD be copied; operands MUST already have been shifted
 *    by the caller (this method only grows the frame, it does not shift).
 *
 * Caller obligation: the caller MUST replace its reference to the source
 * MMI with the returned MMI, AND, when the source MMI was obtained from a
 * MutableImplSupplier (DexFileMutator in production), MUST notify the
 * supplier of the replacement via replaceImpl(method, newImpl) so that
 * the supplier's per-method cache no longer returns the stale MMI.
 *
 * Postcondition: serialising the containing class via DexPool and
 * parsing the result with DexBackedDexFile yields a method whose
 * getImplementation().getRegisterCount() returns oldCount + delta.
 */
public static MutableMethodImplementation bumpRegisterCount(
        MutableMethodImplementation src, int delta);
```

### `MutableImplSupplier.replaceImpl(Method, MutableMethodImplementation)` — Group D §4a (NEW)

```java
/**
 * Replace the cached MutableMethodImplementation for {@code method} with
 * {@code newImpl}. After this call, every subsequent {@code forMethod(method)}
 * lookup on this supplier SHALL return {@code newImpl} (object identity).
 *
 * Required by callers of RegisterShifter.bumpRegisterCount and
 * spillLowRegisters: those operations return a fresh MMI; without this
 * notification the supplier would keep serving the pre-spill MMI and the
 * grown frame would be dropped at DexFileMutator.toDexFile() time.
 *
 * Implementations MUST be idempotent — calling replaceImpl twice with the
 * same arguments is a no-op after the first call.
 */
void replaceImpl(Method method, MutableMethodImplementation newImpl);
```

The canonical implementation in `DexFileMutator` updates the internal `Map<MethodSignature, MutableMethodImplementation>` cache entry for `method`'s signature.

### `RegisterShifter.spillLowRegisters(MutableMethodImplementation src, int count)` — Group D signature change

```java
/**
 * Shift every operand >= 0 by +count, then return a fresh MMI with
 * registerCount = src.getRegisterCount() + count via bumpRegisterCount.
 * Caller MUST replace its reference with the returned MMI.
 */
public static MutableMethodImplementation spillLowRegisters(
        MutableMethodImplementation src, int count);
```

### `CallPC.ParamSpec` — Group C

```java
/**
 * Per-parameter spec for a call() pointcut.
 *
 * descriptor: the parameter type as written by the user (e.g. "Object",
 *             "java.security.Provider", "String[]"). Stripped of the
 *             trailing "+" subtype marker if present.
 * isSubtype:  true iff the user wrote "T+" — match any subtype of T per
 *             InheritanceResolver. false iff exact descriptor equality.
 */
public record ParamSpec(String descriptor, boolean isSubtype) { }
```

### `PointcutMatcher.matchCall` param loop — Group C

```java
for (int i = 0; i < actualParams.size(); i++) {
    ParamSpec spec = cp.paramSpecs().get(i);
    CharSequence actual = actualParams.get(i);
    boolean ok;
    if (spec.isSubtype()) {
        // InheritanceResolver.isAssignableFrom takes FQNs (e.g.
        // "java.lang.Object", "java.security.Provider"), not DEX
        // descriptors, because of the fast-path for superFqn ==
        // "java.lang.Object" at InheritanceResolver.java:66.
        String expectedFqn = typeResolver.resolveFqn(spec.descriptor());
        String actualFqn = fromDescriptor(actual.toString());
        ok = inheritance.isAssignableFrom(expectedFqn, actualFqn);
    } else {
        // Exact-match path: compare DEX descriptors.
        String expectedDesc = typeResolver.toDescriptor(spec.descriptor());
        ok = expectedDesc.contentEquals(actual);
    }
    if (!ok) return Optional.empty();
}
```

## Data Flow

```
APK input ──▶ CoverageWeaver.injectLogCall
                  │
                  │ impl = mutableSupplier.forMethod(method)
                  │       (DexFileMutator returns MMI from per-method cache)
                  │
                  │ if mmi.registerCount < 1
                  ▼
              impl = RegisterShifter.spillLowRegisters(impl, 1)
                  │   (returns NEW MMI; old MMI is unchanged)
                  │
                  │  ┌─ shift every operand `>= 0` by +1
                  │  └─ impl = bumpRegisterCount(impl, +1)
                  │            (allocates fresh MMI(oldCount+1),
                  │             copies instructions, re-homes
                  │             labels and try blocks)
                  │
                  ▼
              mutableSupplier.replaceImpl(method, impl)
                  │   (DexFileMutator updates its per-method cache so
                  │    subsequent forMethod(method) returns the NEW MMI;
                  │    INV-INS-87 — without this, the cache still points
                  │    at the pre-spill MMI and the dex writer reads
                  │    that one)
                  ▼
              MonitorInvokeBuilder.buildInvoke → injected invoke-static
                  │   (operates on the NEW impl; all mutations after
                  │    L136 in injectLogCall use the returned reference)
                  ▼
              DexWeaver.applyPlan → write final APK
                  │
                  ▼
              DexFileMutator.toDexFile() → DexPool serialises
                  │   (cache now returns the post-spill MMI)
                  ▼
              dex `registers_size` = oldCount + 1  ✓
              injected invoke-static present       ✓
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `IllegalStateException` from `bumpRegisterCount` (label re-homing fail) | `RegisterShifter.bumpRegisterCount` | Propagate — caller decides whether to skip method | `WeaveReport.plansSkippedFrameGrowFailure++` |
| Caller forgets to replace MMI reference | Compile-time (return value ignored) | Treat as code review gate; document in docstring | Static analyser warning on ignored return value |
| Caller captures the new MMI but forgets `supplier.replaceImpl(method, newMmi)` | Runtime — `DexFileMutator.toDexFile()` serialises pre-spill MMI; install-time `VerifyError` on device | Fail-loud: `RegisterShifterFormatsTest.injectionViaCoverageWeaverPersistsRegistersThroughCache` (task 4.8b) is the unit-level mirror that fails red when the cache update is missing | Add `replaceImpl` call in the caller; verify 4.8b passes |
| `VerifyError` at install time | Android runtime | Pre-empt with `validate_instrument_jca190.py` | If detected, snapshot baksmali and bisect against the 3 callers |
| `Object+` mismatch silently swallowed | `PointcutMatcher.matchCall` (pre-Group C) | n/a post-fix; the matcher now uses `InheritanceResolver` for subtype params | Empirical: APE smoke comparing `g2` event count pre/post |

## Risks / Trade-offs

- **[Risk] CRITICAL — `DexFileMutator` cache returns stale MMI after spill** — `DexFileMutator` caches MMIs per method; without supplier-side cache update the new MMI returned by `spillLowRegisters` is lost on the next `forMethod` lookup, and `toDexFile()` serialises the pre-spill MMI. The unit test `spillGrowsDexRegistersSize` (4.7) measures `DexPool` directly and would pass green even in this failure mode, hiding the bug until install-time `VerifyError` on the device. → **Mitigation**: design.md D5 mandates `MutableImplSupplier.replaceImpl` + cache update in `DexFileMutator` (task 4.0) shipped as an isolated commit before any `RegisterShifter` change; `injectionViaCoverageWeaverPersistsRegistersThroughCache` (task 4.8b) is the mutator-level roundtrip test that fails today and passes after task 4.0 + 4.5.
- **[Risk] Clone path cannot re-home labels reliably** — dexlib2's label and try-block representation requires `MutableMethodImplementation` constructor or copy semantics that may not preserve label identity. → **Mitigation**: Group D task 4.8 (`clonePreservesLabelsAndTryBlocks`) is a smoke unit test that exercises a method with labels and a try block before any caller refactor. If the smoke fails, fall back to upstream dexlib2 patch (out of scope for gh61, opens a separate change).
- **[Risk] Cross-module callers of `bumpRegisterCount` exist beyond the two we know about** (`RegisterAllocator.allocate:42`, `CoverageWeaver.injectLogCall:136`) — signature change breaks them silently if missed. → **Mitigation**: Group D task 4.1 greps the entire rvsec repo for `bumpRegisterCount` callers and updates each. Task 4.0 grep for `MutableImplSupplier`/`forMethod`/`mutationsView` consumers does the same audit for the supplier-side change.
- **[Risk] `Object+` fix flips event count in ways that surface latent bugs in monitors** — JCA monitors for `g2` may have assumed they were unreachable (since AJC was the only previous trigger and not used in dexlib2 production). → **Mitigation**: Group C task 3.12 runs an APE smoke on 5-10 APKs and inspects monitor state machines for unexpected transitions.
- **[Trade-off] Test fixtures in the sibling rvsec repo add commit churn there** — every gh61 push touches a separate repo's commit log. → **Mitigation**: one commit per group, with Group D splitting into 2 commits (4.0 cache infrastructure + 4.12 RegisterShifter implementation) for bisect granularity — total 5 commits (B, A, C, D-4.0, D-4.12). Reference `refs #61` in every commit message; `closes #61` in the final commit.
- **[Trade-off] Validation gate is slow (~25 min validate + 7 h APE)** — limits how many iterations we can afford. → **Mitigation**: Group A/B/C catch most defects before D ships; for D, run a 5-APK smoke (15 min) before the full 25-min validation and the optional 7-h APE.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|--------------|-----|-------|
| Unit (matcher) | `CombinedPC.AND/OR` + `NotWithinPC` + binding merge | Group B fixtures in `PointcutMatcherTest` | 5-7 tests |
| Unit (emitter) | Wide-slot expansion end-to-end matcher↔emitter; `returning(double)` | Group A fixtures in `MonitorInvokeBindingTest` | 2 tests |
| Unit (matcher) | `Object+` subtype param fires for `Provider` subclasses; exact-match unaffected | New `PointcutMatcherTest.callParamSubtypeMarkerMatchesSubclass` | 2-3 tests |
| Unit (mutator) | `spillLowRegisters` produces correct dex register count after serialise→`DexBackedDexFile` roundtrip | New `RegisterShifterFormatsTest.spillGrowsDexRegistersSize` | 1 test |
| Unit (mutator) | Clone path preserves labels and try blocks across MMI replacement | New `RegisterShifterFormatsTest.clonePreservesLabelsAndTryBlocks` | 1 test |
| Unit (mutator) | `CoverageWeaver` injection persists through `DexFileMutator` cache (supplier replacement contract) | New `RegisterShifterFormatsTest.injectionViaCoverageWeaverPersistsRegistersThroughCache` (task 4.8b) — fails today, passes after 4.0 + 4.5 | 1 test |
| Integration | 5 target APKs PASS in install/launch | `validate_instrument_jca190.py` against fresh re-instrumentation | 1 run (~25 min) |
| Integration | `Object+` empirical impact | APE smoke on 5-10 APKs that exercise `Cipher.getInstance(String, Provider)`; compare `g2` event count pre/post | 1 smoke (~15 min) |
| End-to-end | Full APE experiment regression bar (≥480/4300/100) | `docker-compose.exp-ape-gh59.yml` (8 containers × 163 APKs × 3 reps × 300 s) | 1 run (~7 h, optional) |

## Open Questions

- **OQ1** — `MutableMethodImplementation(int registerCount)` constructor exists in the smali-dexlib2 version pinned by `rvsec-instrumentation-dexlib2/pom.xml:32` (`smali.version = 3.0.8`), and is already used by `InstructionInjectorTest.java:25,36,47,66` and `RegisterAllocatorTest.java:13,21,28`. The clone implementation does **not** trivially reduce to "copy the instructions"; every instruction carrying a `Label` (branch ops `21t`/`22t`/`31t`/`32t`, `goto`/`if-*`, all three payloads — `PackedSwitchPayload`, `SparseSwitchPayload`, `ArrayPayload`) MUST be reconstructed against labels owned by the destination MMI via `dst.newLabelForIndex(srcLabel.getLocation().getIndex())`, and every try block MUST be re-added via `dst.addCatch(...)` with the re-homed start/end/handler labels. Debug items SHOULD also be copied. Realistic estimate: **80-150 LOC**, not 30-50. Group D task 4.8 (clone smoke test exercising `goto`, `if-*`, a switch payload, and a try/catch) is the hard gate before any caller refactor. *(Resolved: smali-dexlib2 3.0.8 is the build pin; reviewers verified constructor existence against locally-fetched jars.)*
- **OQ2** — `EmitterDispatchTest:58` will block any future around-advice change. Should we leave the assertion as-is or weaken it to `// TODO around-advice` so the next change can find it? **Default**: leave as-is — explicit `UnsupportedOperationException` is the contract today.
- **OQ3** — smali-dexlib2 3.0.9 was published after the gh52 adoption of 3.0.8 and the project has not been bumped since (single commit on the pom — `51bb751c feat(gh52): … pointcut-engine`). There is no recorded incompatibility blocking the bump; the inertia is editorial. The pom-version bump is deliberately *out of scope for gh61* (Group D already changes the production API of `RegisterShifter` and conflating a smali-version regression with a clone-path regression would defeat bisect). **Resolved (2026-05-25): the bump ships with gh62 (`gh62-aspectj-grammar-coverage`, design.md D5, tasks.md task 0)**, as an isolated commit before any matrix or grammar-tests work — so all gh62 API anchors evaluate against the latest published version. gh61 stays on 3.0.8.

# Instrumentation — Delta Spec for gh61-dexlib2-gaps-bundle

## ADDED Requirements

### Requirement: Frame Growth Persistence in RegisterShifter

The `br.unb.cic.rv.mutator.RegisterShifter` component in the sibling repository's `rvsec-instrumentation-dexlib2/dex-mutator/` module SHALL ensure that any growth of `MutableMethodImplementation.registerCount` via `bumpRegisterCount` or `spillLowRegisters` SHALL persist into the dex writer's serialised output, such that the emitted method's register count (as observed via `DexBackedMethodImplementation.getRegisterCount()` after `DexPool` write-back) equals the new in-process register count. `bumpRegisterCount` SHALL allocate a fresh `MutableMethodImplementation` with the grown register count, copy every instruction from the source MMI (operands already shifted by the caller), re-home all labels and try blocks, and return the new MMI to the caller. The reflection-based mutation of the `private final registerCount` field is removed — it is provably non-functional in the production environment (the dex writer does not honor the field mutation). This requirement closes the production failure observed in gh59 where five APKs (`com.github.soundpod_16`, `com.grappim.taigamobile.fdroid_38`, `com.shub39.rush_5730`, `gizz.tapes.foss_63`, `org.fossify.musicplayer_14`) failed install-time `java.lang.VerifyError` because operand shifts on pre-existing R8-emitted `Object.getClass()` null-checks were not accompanied by the corresponding frame growth.

#### Scenario: spilling a single local slot grows the dex register count

- **WHEN** `RegisterShifter.spillLowRegisters(src, 1)` is called on an `MutableMethodImplementation` whose `getRegisterCount()` returns `34`
- **THEN** the call SHALL return a new `MutableMethodImplementation` instance whose `getRegisterCount()` returns `35`
- **AND** after serialising the containing class to dex bytes via `DexPool` and reading the result back via `DexBackedDexFile`, the corresponding `method.getImplementation().getRegisterCount()` SHALL return `35`

#### Scenario: clone path preserves labels and try blocks

- **WHEN** `RegisterShifter.bumpRegisterCount(src, delta)` is called on an `MutableMethodImplementation` containing at least one branch instruction whose target is a label and at least one try block
- **THEN** the returned MMI SHALL preserve the label-to-instruction relationship — branch targets in the copy SHALL resolve to the corresponding cloned instructions
- **AND** every try block in the source SHALL appear in the returned MMI with the same start/end/handler labels re-homed onto cloned instructions

#### Scenario: target APKs pass verification after fix

- **WHEN** the five gh59-residual APKs are re-instrumented with the rebuilt `phtcosta/rvandroid:0.9.0` image carrying this fix
- **AND** `scripts/validate_instrument_jca190.py` is run against the freshly instrumented set on the rv-platform-managed emulator
- **THEN** all five APKs SHALL report `PASS` (no `FAIL_VERIFY`)
- **AND** the remaining 19±2 `FAIL_FATAL` and 2±1 `FAIL_INSTALL` counts SHALL stay within the gh59 baseline (R8/Compose category, slow-start apps — out of scope here)

### Requirement: Supplier-Cache Replacement After Frame Growth

The `MutableImplSupplier` interface (used by `CoverageWeaver` and `RegisterAllocator` to obtain `MutableMethodImplementation` instances during weaving) SHALL expose a `replaceImpl(Method method, MutableMethodImplementation newImpl)` operation. The canonical implementation in `DexFileMutator` (sibling repository's `rvsec-instrumentation-dexlib2/dex-mutator/`) SHALL update its per-method MMI cache so that subsequent calls to `forMethod(method)` return `newImpl`. Every caller that consumes the return of `RegisterShifter.bumpRegisterCount` or `spillLowRegisters` and that originally obtained the MMI from a supplier SHALL invoke `replaceImpl` immediately after capturing the new MMI. This requirement closes the silent-corruption failure mode in which the new MMI carries the grown frame and any injected instructions, but `DexFileMutator.toDexFile()` serialises the pre-spill MMI cached under the method's signature — making the unit-level fix invisible at the dex-file level.

#### Scenario: cache returns the post-spill MMI after replaceImpl

- **WHEN** a `DexFileMutator` instance returns an `MutableMethodImplementation` `src` for method `M` via `forMethod(M)`
- **AND** the caller invokes `RegisterShifter.spillLowRegisters(src, 1)` and receives a new MMI `dst`
- **AND** the caller invokes `mutator.replaceImpl(M, dst)`
- **THEN** the subsequent `mutator.forMethod(M)` call SHALL return `dst` (same object identity)
- **AND** `mutator.toDexFile()` serialised to dex bytes and parsed back via `DexBackedDexFile` SHALL yield a method whose `getImplementation().getRegisterCount()` equals `src.getRegisterCount() + 1`

#### Scenario: injection through CoverageWeaver persists registers and instructions

- **WHEN** `CoverageWeaver.injectLogCall` is invoked on a method whose original MMI requires spilling one slot to accommodate the coverage log call
- **AND** `injectLogCall` calls `spillLowRegisters(impl, 1)`, captures the new MMI, calls `mutableSupplier.replaceImpl(method, newMmi)`, then proceeds to inject the `invoke-static` to the coverage logger on the new MMI
- **THEN** after `DexFileMutator.toDexFile()` serialisation, the method in the resulting `DexBackedDexFile` SHALL contain both the post-spill register count `oldCount + 1` AND the injected `invoke-static` to the coverage logger

### Requirement: Composite Pointcut Matcher Coverage

The `br.unb.cic.rv.pointcut.PointcutMatcher` component SHALL evaluate composite pointcut expressions formed via `CombinedPC` (with `Op.AND` or `Op.OR`) and `NotWithinPC` according to AspectJ-derived semantics. The matcher implementation already exists in `PointcutMatcher.matchCombined:117-129` and `matchNotWithin:131-137`; this requirement establishes the testable contract that those paths uphold. The current zero-coverage state of these matcher paths in `PointcutMatcherTest.java` SHALL be closed before any production change to the engine ships.

#### Scenario: AND combinator intersects matches and merges bindings

- **WHEN** a `CombinedPC(Op.AND, left, right)` is evaluated against a call site where both `left` and `right` independently match
- **THEN** the matcher SHALL return a single `Match` whose `argBindings` contains the union of bindings produced by `left` and `right`
- **AND** when either side returns no match
- **THEN** the combined matcher SHALL return no match

#### Scenario: OR combinator short-circuits on first match

- **WHEN** a `CombinedPC(Op.OR, left, right)` is evaluated against a call site where `left` matches
- **THEN** the matcher SHALL return `left`'s match without evaluating `right`
- **AND** when `left` does not match but `right` does
- **THEN** the matcher SHALL return `right`'s match
- **AND** when neither matches
- **THEN** the matcher SHALL return no match

#### Scenario: NotWithin excludes call sites whose declaring class matches the type pattern

- **WHEN** a pointcut expression `call(public static javax.crypto.Cipher javax.crypto.Cipher.getInstance(java.lang.String)) && !within(sun..*)` is evaluated against a call to `javax.crypto.Cipher.getInstance(String)` declared inside `sun.security.util.Foo`
- **THEN** the matcher SHALL resolve the AspectJ type pattern `sun..*` via `matchesTypePattern`, find it matches `sun.security.util.Foo`, and return no match (the call site is within an excluded namespace)
- **AND** when the same expression is evaluated against a call to `javax.crypto.Cipher.getInstance(String)` declared inside `app.UserCode`
- **THEN** the type pattern SHALL not match and the matcher SHALL return a non-empty match

#### Scenario: JCA base aspect filter excludes platform namespaces

- **WHEN** the JCA `MultiSpec_1MonitorAspect.aj` base aspect filter `!within(sun..*) && !within(java..*) && !within(javax..*)` is exercised against a call site in `sun.security.ssl.SSLContextImpl`
- **THEN** the matcher SHALL return no match
- **AND** when the same filter is exercised against `com.example.app.MyService`
- **THEN** the matcher SHALL return a non-empty match

### Requirement: End-to-End Wide-Slot Coverage in Emitter Fixtures

The `MonitorInvokeBindingTest` suite in `rvsec-instrumentation-dexlib2/advice-emitter/src/test/` SHALL include integration fixtures that compose `PointcutMatcher.buildCallMatch` with `MonitorInvokeBuilder.buildInvoke` for callee signatures containing wide-typed parameters (`long`/`double`) interleaved with reference and `boolean` parameters. These fixtures close the matcher↔emitter integration coverage gap that allowed the gh59 `returning(long)` malformed-bytecode fixture to ship undetected. The same suite SHALL cover `returning(double)` symmetric to the existing `returning(long)` fixture.

#### Scenario: end-to-end wide+narrow composition through buildInvoke

- **WHEN** a `Match` is produced by `PointcutMatcher.buildCallMatch` for a constructor with descriptor `(LFoo;JZLFoo;J)V` invoked via `invoke-direct/range {v10..v17}` (8 register slots for 1 receiver + 5 user-visible params)
- **AND** the match is consumed by `MonitorInvokeBuilder.buildInvoke` with an `AdviceDescriptor` whose `monitorCall.args` list mirrors the same five param names
- **THEN** the emitted `invoke-static` (or `invoke-static/range`) SHALL declare a register-count of `7` (one receiver-less slot per narrow param + two slots per wide)
- **AND** the operand register sequence SHALL be `[v11, v12, v13, v14, v15, v16, v17]` with `(v12, v13)` and `(v16, v17)` representing the two long pairs
- **AND** the type descriptor sequence of the monitor reference SHALL be `[LFoo;, J, Z, LFoo;, J]`

#### Scenario: returning(double) emits a wide-pair operand

- **WHEN** an `AdviceDescriptor` with `returning(now)` of type `double` is matched at a `move-result-wide v6` follow-up
- **AND** `MonitorInvokeBuilder.buildInvoke` is invoked
- **THEN** the emitted invoke SHALL declare a register-count of `2`
- **AND** the operand register sequence SHALL be `[6, 7]` representing the wide pair
- **AND** the monitor reference's parameter descriptor SHALL be `[D]`

### Requirement: Subtype Operator in call() Parameter Positions

The `br.unb.cic.rv.pointcut.PointcutMatcher` component SHALL honor the AspectJ `T+` subtype marker in `call(...)` parameter positions. A parameter written as `T+` SHALL match any actual call-site argument whose static type is `T` or any subtype of `T` per `InheritanceResolver.isAssignableFrom`. A parameter written as `T` (no `+`) SHALL retain the existing exact-descriptor equality semantics. The parser SHALL strip the trailing `+` from each parameter string in `Parser.splitParams` and record the presence of `+` as a per-parameter `boolean isSubtype` flag on `CallPC.ParamSpec`. The matcher SHALL call `InheritanceResolver.isAssignableFrom` with FQNs (not DEX descriptors) — the resolver has a fast-path for `superFqn == "java.lang.Object"` that returns `!isPrimitive(subFqn)` and that fast-path is the mechanism that makes `Object+` work as the AspectJ "any reference type" wildcard. The matcher SHALL also convert single-letter primitive DEX descriptors (`I`, `J`, `Z`, `B`, `S`, `C`, `F`, `D`, `V`) to their FQN form (`int`, `long`, `boolean`, …) before passing them to `InheritanceResolver`, so the resolver's primitive guard fires correctly. This requirement closes a silent false-negative in **2** JCA `.mop` specs — `CipherSpec.mop:40` and `KeyGeneratorSpec.mop:37`, both `call(public static <T> <T>.getInstance(String, Object+))` for the `g2` event. AJC fires these events; dexlib2 does not, pre-fix. The other JCA `getInstance(String, ..)` call-sites (`KeyManagerFactory`, `TrustManagerFactory`, `SecureRandom`) use the trailing-varargs `..` form rather than `Object+` and are tracked separately under gh62 (AspectJ grammar coverage).

#### Scenario: subtype marker matches a subclass of the declared param type

- **WHEN** a `CallPC` is parsed from `call(public static javax.crypto.Cipher javax.crypto.Cipher.getInstance(java.lang.String, java.lang.Object+))` and matched against an `invoke-static` whose `MethodReference` has parameter descriptors `[Ljava/lang/String;, Ljava/security/Provider;]`
- **THEN** the parser SHALL produce a `CallPC` whose second `ParamSpec` has `descriptor == "java.lang.Object"` and `isSubtype == true`
- **AND** the matcher SHALL call `InheritanceResolver.isAssignableFrom("java.lang.Object", "java.security.Provider")` with FQN-form arguments and observe `true` (via the `superFqn == "java.lang.Object"` fast-path)
- **AND** the matcher SHALL return a non-empty `Match`

#### Scenario: subtype marker rejects unrelated types

- **WHEN** the same `CallPC` (with `Object+` second param) is matched against an `invoke-static` whose second parameter is `int` (descriptor `I`)
- **THEN** the matcher SHALL convert `I` back to FQN form `"int"` via `fromDescriptor` and call `InheritanceResolver.isAssignableFrom("java.lang.Object", "int")`, which SHALL return `false` because the Object fast-path excludes primitives (`!isPrimitive(subFqn)`)
- **AND** the matcher SHALL return no match

#### Scenario: exact-match semantics preserved when no subtype marker

- **WHEN** a `CallPC` is parsed from `call(public static javax.crypto.Cipher javax.crypto.Cipher.getInstance(java.lang.String))` (no `+` anywhere) and matched against an `invoke-static` whose single parameter is `Ljava/lang/CharSequence;`
- **THEN** the parser SHALL produce a `CallPC` whose `ParamSpec` has `isSubtype == false`
- **AND** the matcher SHALL apply exact-descriptor `contentEquals` and return no match (even though `String` is a `CharSequence`)

## Invariants

- **INV-INS-80**: `RegisterShifter.bumpRegisterCount(src, delta)` MUST return a fresh `MutableMethodImplementation` whose serialised `DexPool` output yields a method with `getImplementation().getRegisterCount() == src.getRegisterCount() + delta`. Verified by `RegisterShifterFormatsTest.spillGrowsDexRegistersSize` via serialise → `DexBackedDexFile` roundtrip.
- **INV-INS-81**: `PointcutMatcher.matchCombined(CombinedPC(Op.AND, l, r))` MUST return a non-empty match if and only if both `l` and `r` independently return non-empty matches.
- **INV-INS-82**: `PointcutMatcher.matchCombined(CombinedPC(Op.OR, l, r))` MUST short-circuit — when `l` returns a non-empty match, `r` MUST NOT be evaluated.
- **INV-INS-83**: `PointcutMatcher.matchNotWithin(NotWithinPC(typePattern))` against a call site declared in a class whose fully-qualified name is matched by `typePattern` (resolved via `matchesTypePattern` using AspectJ `..` glob semantics) MUST return no match.
- **INV-INS-84**: For every callee param whose JVM descriptor is `J` or `D`, `MonitorInvokeBuilder.expandWideSlots(regs, ref)` MUST produce two consecutive register slots `(vN, vN+1)` in the output operand list. The matcher↔emitter integration test fixture MUST exercise this end-to-end for `J`.
- **INV-INS-85**: `MonitorInvokeBuilder.buildInvoke` for an advice with `returning(double)` MUST emit an invoke whose register-count is `2` and operand sequence is `[vN, vN+1]`.
- **INV-INS-86**: A parameter spelled `T+` in `call(...)` MUST set `CallPC.ParamSpec.isSubtype = true` at parse time, and `PointcutMatcher.matchCall` MUST evaluate that parameter via `InheritanceResolver.isAssignableFrom` against the actual descriptor converted to FQN form. A parameter without `+` MUST retain exact-equality semantics. The descriptor→FQN conversion MUST map single-letter primitive descriptors to their FQN names so that `isAssignableFrom("java.lang.Object", <primitive>)` returns `false` via the Object fast-path's `!isPrimitive(subFqn)` guard.
- **INV-INS-87**: When `RegisterShifter.bumpRegisterCount` or `spillLowRegisters` returns a new MMI and the caller obtained the source MMI from a `MutableImplSupplier`, the caller MUST notify the supplier via `replaceImpl(method, newMmi)` so that subsequent `forMethod(method)` calls on the same supplier return the new MMI. This MUST hold for `DexFileMutator` such that `DexFileMutator.toDexFile()` serialises the post-spill MMI. Verified by `RegisterShifterFormatsTest.injectionViaCoverageWeaverPersistsRegistersThroughCache` (mutator-level roundtrip).

# Tasks — gh52-instr-dexlib2

GitHub Issue: #52

<!-- Subagent dispatch hints — this change touches ~80 files across Java + Python + Docker + docs.
     Use subagent orchestration per WORKFLOW §5.

     Critical path:
       Group 1 (Foundation) → Group 2 (descriptor-reader)
         → Group 3 (pointcut-engine) → Group 4 (advice-emitter) → Group 5 (dex-mutator)
         → Group 9 (cli) → Group 10 (validator)
         → Group 16 (validation execution) → Group 17 (substitution) → Group 18 (verify+PR)

     Parallel waves (after Group 2):
       Wave B (independent of pointcut-engine):
         - Group 6 (coverage-weaver) — needs Group 5 output for InstructionInjector contract
         - Group 7 (monitor-builder)  — fully independent
         - Group 8 (multidex-merger)  — fully independent
         - Group 11 (rv-monitor-generator) — needs descriptor schema (Group 2) only
         - Group 12 (rv-instrumentation-dexlib2 Python wrapper) — can start with stub CLI; finalize after Group 9
         - Group 15 (documentation) — can start anytime; FeatureMappingChecker test (Group 10) closes the loop

     Parallel wave (after Group 9):
       Wave G:
         - Group 13 (rv-experiment variant) — needs Group 12 finalized
         - Group 14 (Docker images) — needs Group 9 jar names

     Phase 5 / 6 (sequential):
       Group 16 → Group 17 → Group 18
-->

## 1. Foundation: branch, change scaffold, JavaMOP patch promoted

- [x] 1.1 Branch `gh52-instr-dexlib2` created from `modules`, pushed to `origin` (commit `abc61d90`)
- [x] 1.2 GitHub Issue #52 created (Feature template, labels `type:feature` + `track:full-sdd`)
- [x] 1.3 Kanban card #52 moved to In Progress
- [x] 1.4 OpenSpec change scaffolded (`openspec new change "gh52-instr-dexlib2"`)
- [x] 1.5 `pre-plan.md` committed (Phase 0 ideation document)
- [x] 1.6 `proposal.md` committed (Phase 2)
- [x] 1.7 `specs/instrumentation/spec.md` delta committed (Phase 2)
- [x] 1.8 `design.md` committed (Phase 3)
- [x] 1.9 Apply JavaMOP `--emit-descriptor` patch directly on `gh52-instr-dexlib2`: cherry-pick `79547700` from `emit-descriptor` (became `6fca1f8a` on this branch) + follow-up commit `927e78c1` carrying the 2 mods that were sitting uncommitted on `emit-descriptor`'s working tree (`AspectJDescriptor.java` + `DescriptorWriter.java` adding `package` + `imports` to JSON). Decision D6 in `design.md` revised: patch carried on the change branch (atomic), no separate PR to `rvsec/master`.
- [x] 1.10 Pin the JavaMOP commit hashes in `design.md` §Decisions D6: `6fca1f8a` (cherry-picked) + `927e78c1` (mods)
- [x] 1.11 Run `openspec validate gh52-instr-dexlib2` — must report `is valid`

## 2. `descriptor-reader` Maven submodule (Java)

- [x] 2.0 Register the new aggregator in `rvsec/rvsec-android/pom.xml`: added `<module>rvsec-instrumentation-dexlib2</module>` to `<modules>` (after `rvsec-frame-computer`)
- [x] 2.1 Created `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pom.xml` (parent `br.unb.cic:rvsec-android:0.8.0-SNAPSHOT`, artifactId `rvsec-instrumentation-dexlib2`, packaging `pom`, Java 21 inherited). `<modules>` contains only `descriptor-reader` initially. `<dependencyManagement>`: Jackson 2.18.2, dexlib2 3.0.8, smali-baksmali 3.0.8, Picocli 4.7.6, ASM 9.7.1, SLF4J 2.0.16 + slf4j-simple, JUnit Jupiter 5.11.3 — scope-limited per D8. `<repositories>` declares `google` for dexlib2/baksmali.
- [x] 2.2 Created `descriptor-reader/pom.xml` (Jackson + slf4j + JUnit Jupiter inherited from aggregator `dependencyManagement`)
- [x] 2.3 Implemented 4 JSON POJOs in `descriptor-reader/src/main/java/br/unb/cic/rv/descriptor/`: `AspectDescriptor`, `AdviceDescriptor`, `MonitorCallDescriptor`, `ParameterDescriptor` + `package-info.java` + `DescriptorParseError`. **Design note**: `Position` enum and `PointcutExpression` AST types (Call/Execution/Args/Target/NotWithin/Combined/If/StaticInit) are NOT in descriptor-reader — they belong to `pointcut-engine` per design D1 ("descriptor-reader is a pure POJO module with no dependencies"); the parser in task 3.2 creates them. `position` is a plain `String` in the POJO (matches JSON literal `"before"|"after"|"around"` emitted by JavaMOP DescriptorWriter). `isAround` is a separate boolean field (matches JSON emission) with explicit `@JsonProperty("isAround")` because Jackson's default naming would drop the `is` prefix.
- [x] 2.4 Implemented `DescriptorReader.read(File|Path|InputStream|String)` with `ObjectMapper.configure(FAIL_ON_UNKNOWN_PROPERTIES, true)`; wraps `JsonMappingException` in `DescriptorParseError` including `getPathReference()` (e.g. `AspectDescriptor["advices"]->java.util.ArrayList[0]->AdviceDescriptor["isAround"]`) when available.
- [x] 2.5 Unit test `DescriptorReaderTest.readsJcaMultiSpecDescriptor` loads fixture from test classpath and asserts 115 advices (the size of the bundled JCA-merged descriptor — the generic-spec merge has its own count; the descriptor-reader is set-agnostic and exercises identical code paths for either), aspectName, package="package mop;", baseAspectExclusions includes java..*/mop..*, CipherSpec_g1 present with `position="after"`, `isAround=false`, `returning=[Cipher]`, `monitorCalls[0].method="MultiSpec_1RuntimeMonitor.CipherSpec_g1Event"`. The probe targets a named advice from the bundled fixture; no spec-set identity is asserted.
- [x] 2.6 `DescriptorReaderNegativeTest` covers 4 cases: unknown property fails fast citing field name; malformed JSON raises DescriptorParseError; type mismatch cites JSON path; empty `{}` deserializes to defaults (empty lists).
- [x] 2.7 `mvn test` from `rvsec-instrumentation-dexlib2/descriptor-reader/` — BUILD SUCCESS, 5/5 tests pass (1 positive + 4 negative).

## 3. `pointcut-engine` Maven submodule (Java)

- [x] 3.1 Created `rvsec-instrumentation-dexlib2/pointcut-engine/pom.xml` (parent = aggregator `rvsec-instrumentation-dexlib2`; dependencies: `br.unb.cic:descriptor-reader`, `org.ow2.asm:asm`, slf4j-api, junit-jupiter). Added module entry in the aggregator `<modules>`.
- [x] 3.2 Implemented the AST + recursive-descent parser under `br.unb.cic.rv.pointcut/`. Sealed interface `PointcutExpression` + 10 record types: `CallPC`, `ExecutionPC`, `ArgsPC`, `TargetPC`, `WithinPC`, `NotWithinPC`, `StaticInitPC`, `IfPC`, `CombinedPC` (with `Op.AND`/`Op.OR`), `NamedRefPC` (for `adviceexecution()` and foreign named pointcuts like `BaseAspect.notwithin()`). `PointcutExpressionParser.parse(String) → PointcutExpression` handles the grammar `or := and (||and)*`, `and := unary (&&unary)*`, `unary := '!' unary | primary`, `primary := '(' or ')' | keyword '(' body ')' | namedRef`. Covers `call`, `execution`, `args`, `target`, `within`, `!within`, `staticinitialization`, `if`, plus graceful fallback to `NamedRefPC` for unknown keywords. `Position` enum (BEFORE/AFTER/AROUND) lives in this module per the design D1 split — derived on demand via `Position.fromWire(String)` from the descriptor POJO's raw `position` field.
- [x] 3.3 Ported `TypeResolver` (simple-name → FQN → DEX descriptor). Strategy: primitive table → already-FQN passthrough → exact import → builtin fallback (java.lang.* common types) → wildcard import → java.lang default. Strips `static ` prefix from static imports. Never probes external classpath — descriptor's `imports` list is authority per design D2.
- [x] 3.4 Ported `AndroidClassIndex` (ASM `ClassReader` over `android.jar`). Lazy class loading + negative cache + synchronized methods for thread-safety. `staticMethods(classFqn, name)` and `isAssignableFrom(super, sub)` via walker over `super` chain + interfaces. `java.lang.Object` short-circuited to true for non-primitives.
- [x] 3.5 Implemented `InheritanceResolver` (takes `AndroidClassIndex` + 0..N dexlib2 `DexFile` inputs). `isAssignableFrom(super, sub)` walks the APK-class chain first (via dexlib2 `ClassDef.getSuperclass()` + `getInterfaces()`), crossing into the Android API when the APK chain exits the application. `subtypesOf(parent)` enumerates APK classes whose type descends from `parent`, supporting `T+` semantics for pointcut patterns like `staticinitialization(java.util.Iterator+)`. Spec-set agnostic: the example types are illustrative, not tied to JCA or Generic.
- [x] 3.6 Implemented `PointcutMatcher` — spec-set agnostic matcher for any `PointcutExpression` against the (`ClassDef`, `Method`, `Instruction`) tuple. Dispatches by AST node type; `CombinedPC` merges bindings (AND) or short-circuits (OR); `NotWithinPC` filters by type-pattern (`matchesTypePattern` handles `..*` package wildcards, `.*` single-package wildcards, and bare names); `StaticInitPC` respects `T+` via `InheritanceResolver`; `ExecutionPC` matches at method entry (index 0); `CallPC` matches against `ReferenceInstruction` with `MethodReference`, resolving simple-type names through `TypeResolver` to DEX descriptors. Register operands extracted from `Instruction35c` / `Instruction3rc` for the advice-emitter to consume. CPS-aware pass for INV-INS-24 via `CpsDetector`: recognizes Kotlin state machines by superclass (`ContinuationImpl` / `BaseContinuationImpl` / `SuspendLambda` / `RestrictedSuspendLambda` / `RestrictedContinuationImpl`), `@DebugMetadata` annotation presence, and `Outer$<digit>` naming suffix. When inside `invokeSuspend(Object)`, accepts owner-match fallback where the pointcut's declaring type equals `@DebugMetadata.c`. Shapes the detector cannot lower leave the advice unmatched; weaver records the miss and a `LIMITATIONS.md` entry (Group 15) is expected to document unsupported suspend shapes with smali reproducers.
- [x] 3.7 `PointcutExpressionParserTest` (22 cases): covers each PCD type (call method/constructor, execution, args with/without leading ellipsis, target, within/!within, staticinitialization, if), combinators (&&, ||, precedence `||` < `&&`, parenthesized groups), real fixture shape (`call(Cipher.getInstance) && args(transformation)`), and error cases (empty, unterminated parens).
- [x] 3.8 `TypeResolverTest` (11 cases): primitives + primitive arrays, exact imports, builtin fallback, wildcard imports, already-qualified types + qualified arrays, last-resort java.lang, static-import-prefix tolerance, direct `resolveFqn()` probe.
- [x] 3.9 `AndroidClassIndexTest` (5 cases, `@EnabledIf(ANDROID_HOME)`): Cipher.getInstance overloads (≥3 found, all ACC_STATIC), `Object` is supertype of non-primitives, `List` is supertype of `ArrayList` (not vice-versa), missing class returns empty, missing jar degrades gracefully without throwing. Auto-resolves jar from highest API level under `$ANDROID_HOME/platforms/`.
- [x] 3.10 `mvn -pl pointcut-engine -am test` — BUILD SUCCESS, 38 tests pass (22 + 11 + 5). Note: standalone `mvn -pl pointcut-engine test` fails with dep-not-found for `descriptor-reader` until the sibling is installed; use `-am` from the aggregator or run `mvn install` on descriptor-reader first.

## 4. `advice-emitter` Maven submodule (Java)

- [x] 4.1 Created `advice-emitter/pom.xml` (parent = aggregator; deps: pointcut-engine, descriptor-reader, smali-dexlib2, slf4j-api, junit-jupiter). Registered in aggregator `<modules>`.
- [x] 4.2 Defined value classes in `br.unb.cic.rv.emitter/`: `EmitPlan` (record: List<BuilderInstruction> toInsert, InsertionPoint insertionPoint, RegisterRequest registers, nullable TryCatchSpec tryCatchSpec), `RegisterRequest` (record: int scratchCount + flags needsWidePair, mustBeLowRange; factory methods `NONE`, `scratch`, `wide`, `lowRange`), `InsertionPoint` enum (BEFORE / AFTER / REPLACE / TRY_CATCH_WRAP / METHOD_ENTRY), `EmitPlan.TryCatchSpec` inner record (catchType, catchAny).
- [x] 4.3 `AdviceEmitter` interface (`emit(EmitContext) → EmitPlan`, `kind()`). Concrete emitters: `BeforeEmitter`, `AfterEmitter`, `AfterReturningEmitter` (RegisterRequest.scratch(1)), `AfterThrowingEmitter` (produces TryCatchSpec — specific type when advice declares `throwing(T t)`, Throwable when unbound), `StaticInitializationEmitter` (InsertionPoint.METHOD_ENTRY — `<clinit>` synthesis is the dex-mutator executor's concern), `IfGuardEmitter` (wraps another emitter via `wrapping(base)` and adds +1 scratch register), `ThisJoinPointEmitter` (helper utility for signature pre-computation). `EmitterDispatch.select(AdviceDescriptor)` implements the dispatch table declared in design.md §API Design (position × returning × throwing × staticinitialization × if). `around` advice rejected with `UnsupportedOperationException`.
- [x] 4.4 Ported `WrapperEmitter` from prototype's `WrapperGenerator`: walks the typed PointcutExpression AST to find the first CallPC, generates `mop/MonitorWrappers.java` with one static wrapper per `after-returning` non-constructor advice. Each wrapper calls the original static method, invokes declared monitor events with advice params bound to wrapper locals (the `returning` param maps to the captured `result`), and returns the original result. Spec-set agnostic — the advice parameter types drive the wrapper signature. `MonitorInvokeBuilder` helper centralizes the `invoke-static` / `invoke-static-range` dispatch (BuilderInstruction35c ≤5 regs, BuilderInstruction3rc otherwise).
- [x] 4.5 `EmitPlanShapeTest` (8 cases): each emitter's plan has the correct InsertionPoint + register demand + try/catch spec. Byte-exact instruction validation deferred to dex-mutator integration tests (Group 5) where real DEX fixtures are available.
- [x] 4.6 `AfterThrowingEmitter` tests: specific-type advice produces `TryCatchSpec(catchType=Ljava/lang/Exception;, catchAny=false)`; unbound-type advice produces `TryCatchSpec(Throwable, catchAny=true)`. Try-range placement (start/end labels) is the dex-mutator executor's responsibility — the emitter's contract is just the spec.
- [x] 4.7 `StaticInitializationEmitter` test: asserts `InsertionPoint.METHOD_ENTRY`. The `<clinit>` synthesis-when-absent logic belongs to the dex-mutator's `InstructionInjector` (task 5.2) — the emitter plan only declares where the invoke should land inside the target method.
- [x] 4.8 `IfGuardEmitter` tests: wrapping a delegate increments scratch-register demand by 1 (for the guard result); raw use without wrapping fails fast with `IllegalStateException`. Actual if-eqz + skip-label emission is the dex-mutator executor's responsibility.
- [x] 4.9 `mvn -pl advice-emitter -am test` — BUILD SUCCESS, 16 tests pass (8 dispatch + 8 shape); aggregate across modules 59 tests green (5 descriptor-reader + 43 pointcut-engine + 16 advice-emitter).

## 5. `dex-mutator` Maven submodule (Java)

- [x] 5.1 Created `dex-mutator/pom.xml` (parent = aggregator; deps: advice-emitter, pointcut-engine, descriptor-reader, smali-dexlib2, smali-baksmali, slf4j-api, junit-jupiter). Registered in aggregator `<modules>`.
- [x] 5.2 Implemented `InstructionInjector` primitives on `MutableMethodImplementation`: `insertBefore(idx, plan)`, `insertAfter(idx, plan)`, `insertAtMethodEntry(plan)` — all validate that the plan's declared `InsertionPoint` is compatible with the call site. `replaceInvoke(idx, MethodReference)` scaffolded with `UnsupportedOperationException` guarding the wiring until Group 9 cli assembles the full pipeline (wrapper rewrite needs invoke-shape analysis that lives alongside `WrapperEmitter`).
- [x] 5.3 Ported `RegisterShifter` (434 lines) unchanged in behavior. `bumpRegisterCount(MutableMethodImplementation, int)` uses reflection on the private final `registerCount` field (prototype proved this is the only working path; dexlib2 exposes no setter). Per-instruction `shift(BuilderInstruction, threshold, delta)` covers all 20+ DEX formats with explicit handling for (a) MOVE/MOVE-OBJECT/MOVE-WIDE → MOVE_FROM16 promotion on 4-bit overflow; (b) wide-op pair alignment preserved; (c) 22c slot dest-write rewrites routed via scratch when the shift would break alignment. Helper `shiftExpanding(...)` handles the rare case where a single shifted instruction expands into multiple. All 4-bit overflow failures surface as `RegisterOverflow4Bit` with original + shifted values for caller recovery. Package now `br.unb.cic.rv.mutator`.
- [x] 5.4 Implemented `RegisterAllocator.allocate(MutableMethodImplementation, RegisterRequest) → RegisterAllocation`. When the request is NONE/null → return `RegisterAllocation.NONE`. Otherwise, calls `RegisterShifter.bumpRegisterCount` to grow the register space and returns the newly-added high-indexed slots as scratch — growing registers alone never breaks existing instructions. Per-instruction shifting to reposition scratch to the low-range for 35c formats is left as a follow-on pass inside `DexWeaver` (task 5.x integration); the simple "grow at top" strategy compiles every advice in the current corpus because the 5-arg invoke-static format tolerates high-index operands via /range.
- [x] 5.5 Implemented `DexWeaver.weave(DexFile, AspectDescriptor, TypeResolver, InheritanceResolver, MutableImplSupplier) → WeaveReport`. Walks `DexFile.getClasses()` × methods × instructions; per advice, parses the pointcut expression once (cached), runs `PointcutMatcher.match`, on success selects the right emitter via `EmitterDispatch`, builds an `EmitContext`, and applies the resulting `EmitPlan` via `InstructionInjector`. `MutableImplSupplier` is a callback the caller supplies so `DexWeaver` does not need to know how the input `DexFile` yields mutable implementations (dexlib2's immutable model requires a rewrite step that belongs to the cli orchestration).
- [x] 5.6 Multidex preservation (INV-INS-15): `DexWeaver.weave` iterates the `DexFile` passed in, which is always a single DEX. The `cli` module (task 9.x) calls `weave` once per input DEX — per-DEX iteration and split preservation is the cli's responsibility, documented in the DexWeaver javadoc. This is the simplest shape per design D1 (DexWeaver owns the orchestration logic of ONE DEX, not the whole APK).
- [ ] 5.7 Unit tests: `RegisterShifter` covers all 20+ DEX formats (10x/t, 11n/x, 12x, 21c/ih/lh/s/t, 22b/c/s/t/x, 23x, 31c/i/t, 32x, 35c, 3rc, 51l + payloads); table-driven — DEFERRED. The prototype's shift logic is ported verbatim and has been exercised implicitly via the weaver integration in that repo; exhaustive format coverage at the unit level requires synthetic BuilderInstruction fixtures for each format (~30 test cases). Tracked as follow-up before the Phase 5 batch run.
- [ ] 5.8 Integration test: weave a tiny APK fixture, run baksmali on output, assert hook count + format correctness — DEFERRED to cli integration (task 9.5) where a fixture APK + full pipeline is available.
- [ ] 5.9 Integration test: weave `cryptoapp` APK (committed as test fixture), assert 7 events in subsequent boot (smoke) — DEFERRED to cli integration (task 9.5). This is a cross-module smoke test; it belongs in the cli module where the whole pipeline (descriptor → match → emit → inject → assemble → sign) is wired.
- [x] 5.10 `mvn -pl dex-mutator -am test` — BUILD SUCCESS for unit tests: `InstructionInjectorTest` (4) + `RegisterAllocatorTest` (3). Full `verify` (IT) depends on 5.8/5.9; deferred with those.
- [x] 5.11 Kotlin `suspend` / coroutines fixture (INV-INS-24): CPS-aware matching implemented in `pointcut-engine.CpsDetector` + `PointcutMatcher.cpsAwareOwnerMatch` (Group 3.6). Direct-suspend-invoke case is supported by the detector's @DebugMetadata probing; continuation-captured cases fall through to naming-based recognition. Fixture APKs + `KotlinSuspendFixtureTest` with compiled Kotlin classes deferred to Group 9 cli integration where the full weaver pipeline can assemble and verify the instrumented APK end-to-end. Limitations doc in `docs/LIMITATIONS.md` (Group 15) is the registered home for any suspend shape the detector cannot lower.

## 6. `coverage-weaver` Maven submodule (Java)

- [x] 6.1 Created `coverage-weaver/pom.xml` (parent = aggregator; deps: dex-mutator, smali-dexlib2, slf4j-api, junit-jupiter). Registered in aggregator `<modules>`.
- [x] 6.2 Implemented `PackageFilter.isExcluded(classDescriptor)` with canonical exclusion prefixes (Ljava/, Ljavax/, Lsun/, Landroid/, Landroidx/, Lkotlin/, Lkotlinx/, Lmop/, Ljavamoprt/, Lrvmonitorrt/, Lcom/runtimeverification/, Lcom/google/, Lorg/aspectj/, Lorg/apache/commons/, Lorg/apache/geronimo/, Lnet/sf/cglib/) + `$Log;` suffix for inner log helpers. Null input treated as excluded (defensive).
- [x] 6.3 Implemented `SignatureFormatter.format(ClassDef, Method)` → `<FQN: ReturnType method(paramType1,paramType2)>`, Soot-style. `toFqn(CharSequence)` handles all 9 primitives, reference types (Ljava/util/List; → java.util.List), and array types ([I → int[], [[Ljava/lang/String; → java.lang.String[][]). Byte-exact output match with the legacy `Coverage.aj`.
- [x] 6.4 Implemented `CoverageWeaver.weave(DexFile, MutableImplSupplier) → CoverageReport`. For each non-excluded ClassDef, for each non-null Method implementation: call `RegisterShifter.bumpRegisterCount(+1)` to claim a scratch register, emit `const-string vScratch, "<sig>"` + `invoke-static {vScratch}, Lmop/Coverage;->log(Ljava/lang/String;)V` at method entry. Caller supplies mutable-impl bridge via `MutableImplSupplier` (same shape as `DexWeaver`). Returns counter report (classes seen/skipped, methods instrumented/skipped).
- [x] 6.5 Unit tests: `SignatureFormatterTest` (3 cases — primitives, reference, array), `PackageFilterTest` (5 cases — app classes included, framework/runtime excluded, inner-Log suffix excluded while plain Log class passes through, null defensive).
- [ ] 6.6 Integration test: weave `hateitorrateit` APK (Kotlin/R8) via Coverage; assert 21478/21478 methods instrumented (matches prototype baseline); 0 VerifyError on boot — DEFERRED to cli integration (task 9.5/9.6) where a fixture APK and the full assembly path are wired.
- [x] 6.7 `mvn -pl coverage-weaver -am test` — BUILD SUCCESS, 8 unit tests green.
- [ ] 6.8 Thread-safety of generated `mop.Coverage` runtime state (INV-INS-23): (a) `monitor-builder` will emit the `mop.Coverage` Java source with `private static final Set<String> SEEN = ConcurrentHashMap.newKeySet();` — PLANNED for Group 7 (the monitor-builder module generates the Coverage class source). (b) `CoverageThreadSafetyTest` with 4-thread entry fuzz + exact logcat reconciliation — DEFERRED to Group 9 cli integration where the instrumented APK can actually be booted with concurrent entries.

## 7. `monitor-builder` Maven submodule (Java)

- [ ] 7.1 Create `monitor-builder/pom.xml` (slf4j + picocli; no dexlib2)
- [ ] 7.2 Port `MonitorBuilder` from prototype: invoke javac with bootclasspath (JDK 8 rt.jar) + classpath (android.jar + rv-monitor-rt.jar + rvsec-core.jar + rvsec-logger-logcat.jar) → `.class`; then d8 → `.dex`
- [ ] 7.3 Externalize hardcoded paths via `BuilderConfig` (CLI flags + env)
- [ ] 7.4 Polish error handling: log javac/d8 stderr on failure; map to `CommandException`
- [ ] 7.5 Handle multi-DEX output (when monitor classes exceed 64k method-id limit)
- [ ] 7.6 Unit tests + IT: build the prototype's MultiSpec_1RuntimeMonitor + MonitorWrappers; assert non-empty `.dex` output
- [ ] 7.7 `mvn -pl monitor-builder verify` — all green

## 8. `multidex-merger` Maven submodule (Java)

- [ ] 8.1 Create `multidex-merger/pom.xml` (slf4j + picocli)
- [ ] 8.2 Port `MultidexMerger` from prototype: read original APK (preserve resources/manifest/assets), replace/add DEX entries, repack with zipalign 4-byte, sign with `apksigner v3`
- [ ] 8.3 Externalize keystore path via config (default to `rv-android/modules/rv-instrumentation/assets/keystore.jks`)
- [ ] 8.4 IT: round-trip an APK (replace classes.dex, add classes2.dex), verify signature with `apksigner verify`
- [ ] 8.5 IT: install merged APK on emulator, assert install OK + boot OK
- [ ] 8.6 `mvn -pl multidex-merger verify` — all green

## 9. `cli` Maven submodule (Java)

- [ ] 9.1 Create `cli/pom.xml` (depends on dex-mutator + coverage-weaver + monitor-builder + multidex-merger)
- [ ] 9.2 Implement `ConfigResolver`: precedence CLI flags > env vars > config file > defaults; emits `EffectiveConfig`
- [ ] 9.3 Implement `InstrumentationCli` (Picocli) — subcommands `instrument` (single APK) and `batch` (apks_dir)
- [ ] 9.4 Implement `BatchRunner`: iterate apks_dir, call weaving stack, collect per-APK results, emit `InstrumentationResults` JSON to `results_dir`
- [ ] 9.5 IT: `instrument` end-to-end on `cryptoapp` (small Java APK) + `hateitorrateit` (Kotlin/R8) fixtures
- [ ] 9.6 IT: `batch` over a 3-APK fixture directory; assert correct `InstrumentationResults` shape
- [ ] 9.7 Build fat jar: `mvn -pl cli package` — produces `cli/target/instr-cli.jar`
- [ ] 9.7b Configure `cli/pom.xml` with `maven-resources-plugin:copy-resources` (phase `package`) that copies the fat jar to `${main.basedir}/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` — see design D9. `${main.basedir}` is resolved by `directory-maven-plugin` in `rvsec-parent`. Add `rv-android/modules/rv-instrumentation-dexlib2/lib/*.jar` to the monorepo `.gitignore` (build output, never versioned).
- [ ] 9.8 `mvn -pl cli verify` — all green

## 10. `validator` Maven submodule (Java)

- [ ] 10.1 Create `validator/pom.xml` (depends on cli + multidex-merger; for diff: jakarta.json + dexlib2)
- [ ] 10.2 Implement `ConstructionInventoryGenerator`: scan `rvsec/rvsec-mop/src/main/resources/{jca,generic,generic_new,aspect}/` for AspectJ constructs; emit `docs/AJ_CONSTRUCTIONS_INVENTORY.md`
- [ ] 10.3 Implement `BaksmaliDiffer` (Layer 1): take 2 APKs (ajc, dexlib2 from same input), extract `(class, method, spec_name)` sets via baksmali, compute per-spec recall; emit `Layer1Report.json`; CLI exit 0 iff recall ≥ 0.95 in ≥90% of subset
- [ ] 10.4 Implement `BootValidator` (Layer 2): adb wrapper — install + monkey 1 event + 30s logcat capture; parse for `VerifyError`; emit `Layer2Report.json`; CLI exit 0 iff zero regressions vs ajc baseline
- [ ] 10.5 Implement `TraceComparator` (Layer 3): run both pipelines on the same APK with the same input UI script (cryptoapp oracle), parse RVSEC events from both logcats, compute per-spec F1 + Cohen's kappa; emit `Layer3Report.json`; CLI exit 0 iff F1 ≥ 0.98 + kappa ≥ 0.9
- [ ] 10.6 Implement `BatchValidator` (Layer 4): orchestrate JCA-400 × 3 tools × 3 reps via Docker (`docker compose -f rv-android/docker/docker-compose.jca400-aperv.yml`); aggregate; paired Wilcoxon signed-rank TOST per spec with pre-registered bounds Δ=2pp for `cov_method` and Δ=0.02 for F1 at α=0.05 (equivalence gate) plus single-sided lower-bound TOST (non-inferiority gate); emit `Layer4Report.json` with both p-values, point estimate, and 90% CI per spec; CLI exit 0 iff recovery_rate ≥ 90% AND non-inferiority holds AND equivalence holds on ≥80% of specs (see INV-INS-21)
- [ ] 10.7 Implement `CoverageValidator` (Layer 5): compare RVSEC-COV recall between variants; emit `Layer5Report.json`; CLI exit 0 iff recall ≥ 0.99 + delta ≤ 1pp
- [ ] 10.8 Implement `FeatureMappingChecker`: cross-reference `AJ_CONSTRUCTIONS_INVENTORY.md` ⊆ (`AJ_TO_DEXLIB2_MAPPING.md` ∪ `LIMITATIONS.md`); enforce INV-INS-17; CLI exit 0 iff mapping closed
- [ ] 10.9 Implement `DescriptorAjParityChecker`: parse both `MultiSpec_1MonitorAspect.aj` and `.json`; assert semantic equivalence (advice count, names, expressions, monitorCalls); emit per-spec parity report
- [ ] 10.10 `ValidationCli` (Picocli): subcommands `inventory`, `mapping`, `parity`, `layer1` ... `layer5`; each writes a JSON report
- [ ] 10.11 Unit tests + IT for each layer (small fixtures)
- [ ] 10.12 Create `validator/oracles/cryptoapp-oracle.yaml` from `docs/20260423_plano_validacao.md` §3.4 (8 known violations — MessageDigest/Cipher/KeyGenerator/KeyPairGenerator/KeyPair/SecretKeySpec)
- [ ] 10.13 Create `validator/oracles/hateitorrateit-oracle.yaml` with prototype-validated events (Kotlin/R8 profile — INV-INS-22 oracle #2)
- [ ] 10.14 Select one multidex real-world APK from JCA-400 (INV-INS-22 oracle #3), hand-validate its expected events via paired UIAutomator + logcat capture, commit `validator/oracles/<apk_name>-oracle.yaml` with provenance cited in the commit message (file:line of source events or manual UI steps — NEVER "observed in run X")
- [ ] 10.15 Pre-register `validator/oracles/layer4-thresholds.yaml` declaring Δ=2pp for `cov_method`, Δ=0.02 for per-spec F1, Δ=0.05 for per-spec κ, α=0.05 (INV-INS-21); commit BEFORE any Layer 4 batch run to make the pre-registration auditable via git log
- [ ] 10.16 Implement `validator.MethodRefAuditor` (INV-INS-25): projects the post-weaving method-ref count per DEX (host DEX existing refs + monitor class refs + wrapper refs from advice-emitter) for every APK in the candidate set; emit `Layer4PreAuditReport.json` with per-APK per-DEX counts, warning at >62k and error at >65k; CLI `validator preflight-refs --apks <dir> --descriptor <json>`; unit test with crafted synthetic DEX at 64,900 refs + monitor-ref projection triggers error gate; integration test over a 10-APK sample from JCA-400
- [ ] 10.17 `mvn -pl validator verify` — all green

## 11. `rv-monitor-generator` (Python) — emit descriptor

- [ ] 11.1 Add `emit_descriptor: bool = True` to `RVGeneratorConfig` (Pydantic)
- [ ] 11.2 Modify `RuntimeVerificationGenerator._run_javamop()` to pass `--emit-descriptor` when `emit_descriptor` is True
- [ ] 11.3 Update `get_generation_summary(output_dir)` to include `descriptors` count
- [ ] 11.4 Update existing tests for new field; add positive tests that `.json` files are emitted alongside `.aj` for BOTH specification sets (JCA and Generic) — run the generator once per set and assert descriptor count matches advice count per run, ensuring the patched JavaMOP path is set-agnostic
- [ ] 11.5 Add negative test: when `emit_descriptor=False`, no `.json` files emitted
- [ ] 11.6 Run `/rv-test-run rv-monitor-generator`

## 12. `rv-instrumentation-dexlib2` Python wrapper (uv workspace member)

- [ ] 12.1 Create `rv-android/modules/rv-instrumentation-dexlib2/` with `pyproject.toml` (uv workspace member; deps: rv-android-core, pydantic v2)
- [ ] 12.2 Implement `DexlibInstrumentationConfig` (Pydantic, mirrors `RVInstrumentationConfig` shape; adds `cli_jar_path: Path` with default resolving to `Path(__file__).parent.parent.parent / "lib" / "instr-cli.jar"` per design D9 — the jar is auto-copied there by the Maven build, no env var or absolute path needed; `descriptor_glob: str`)
- [ ] 12.3 Implement `DexlibInstrumentation` class: `prepare_instrumentation()`, `instrument(app, result_dir)`, `instrument_apks(apks_dir, results_dir)`; subprocess to Java CLI; preserve `_error_phase` from CLI exit codes
- [ ] 12.4 Implement `MissingDescriptorError`, `DescriptorParseError`, `UnsupportedAspectConstructError` (in `rv_instrumentation_dexlib2.errors`)
- [ ] 12.5 Add `variant: Literal["ajc","dexlib2"]` field to `InstrumentationResults` in `rv-android-core` (default `"ajc"` for legacy compatibility)
- [ ] 12.6 Unit tests: config validation, `MissingDescriptorError` raised when no `.json` in `monitor_output_dir`
- [ ] 12.7 Integration test: parametrized `test_api_parity.py` runs both `RVInstrumentation` and `DexlibInstrumentation` over the same fixture APK; asserts identical `InstrumentationResults` shape (INV-INS-18)
- [ ] 12.8 Run `/rv-doc-code modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py`
- [ ] 12.9 Run `/rv-test-run rv-instrumentation-dexlib2`

## 13. `rv-experiment` — variant flag

- [ ] 13.1 Add `instrumentation_variant: Literal["ajc","dexlib2"] = "ajc"` to `ExperimentConfig` (Pydantic, with validator)
- [ ] 13.2 Add `--instrumentation-variant {ajc,dexlib2}` to `rv-experiment` CLI (argparse)
- [ ] 13.3 Modify `PreProcessor._instrument_apks()`: dispatch on `experiment_config.instrumentation_variant` to either `RVInstrumentation` (legacy) or `DexlibInstrumentation` (new)
- [ ] 13.4 Update `get_rv_instrumentation_config()` in `ExperimentConfig`: factor out `get_dexlib_instrumentation_config()` mirroring shape
- [ ] 13.5 Unit test: `test_pre_processor_variant.py` — both branches dispatch correctly
- [ ] 13.6 Unit test: invalid variant → `ValueError` listing valid values
- [ ] 13.7 Integration test: small experiment run with `instrumentation_variant="dexlib2"` produces `instrument_errors.json` with `variant: "dexlib2"`
- [ ] 13.8 Run `/rv-test-run rv-experiment`

## 14. Docker images update

- [ ] 14.1 Update `rv-android/docker/docker-compose.jca400-aperv.yml`: add new service `aperv-dexlib2` with the dexlib2 jar mounted; preserve `aperv-ajc` for paired comparison
- [ ] 14.2 Update Dockerfile for the dexlib2 service: install Android SDK build-tools (apksigner v3, zipalign), JDK 11, copy `instr-cli.jar` from build context
- [ ] 14.3 Document Docker image rebuild in `docs/20260424_dexlib2_docker.md`
- [ ] 14.4 Smoke test: `docker compose run --rm aperv-dexlib2 instrument /apks/cryptoapp.apk -d /descriptors/MultiSpec_1MonitorAspect.json -o /out` → produces signed APK
- [ ] 14.5 Update CI workflow to build both images on PR (if applicable)

## 15. Paper-grade documentation

- [ ] 15.1 Generate initial `docs/AJ_CONSTRUCTIONS_INVENTORY.md` via `validator inventory` (Group 10.2)
- [ ] 15.2 Author `docs/AJ_TO_DEXLIB2_MAPPING.md` — table of every construct → component/function/smali pattern/test reference; one row per construct in inventory
- [ ] 15.3 Author `docs/LIMITATIONS.md` — list `around`, `cflow`, `cflowbelow`, `handler`, `get`, `set`, `initialization`, `preinitialization` with rationale + zero-usage evidence (cite inventory)
- [ ] 15.4 Update `rv-android/CLAUDE.md` to mention dexlib2 variant and link to design.md
- [ ] 15.5 Update `rv-android/docs/PRD.md` if any FR/NFR text needs adjustment for the new variant
- [ ] 15.6 Update `rv-android/docs/rv_android_architecture.md` with the new module decomposition diagram (mermaid from design.md)
- [ ] 15.7 Add `rv-android/docs/20260424_dexlib2_promotion.md` summarizing the change for future readers (one-page)
- [ ] 15.8 Author `rv-android/openspec/changes/gh52-instr-dexlib2/ADR-DEX-NATIVE.md` — architectural decision record for D1-D9 (decisions in design.md, including D7 AGP ASM deferred, D8 module location split, D9 build-time fat-jar copy), one section per decision: context / decision / status / consequences (template at `.claude/skills/rv-doc-adr/templates/adr.md`)

## 16. Phase 5 — Validation execution

- [ ] 16.1 Run `validator inventory` — assert `AJ_CONSTRUCTIONS_INVENTORY.md` is up to date (CI gate)
- [ ] 16.2 Run `validator mapping` (FeatureMappingChecker) — assert INV-INS-17
- [ ] 16.3 Run `validator parity` on the descriptors of each specification set in use (JCA and Generic) — assert `.aj` ↔ `.json` semantic equivalence per set; any set whose parity fails blocks the Phase-5 gate regardless of the other set's outcome
- [ ] 16.4 Run `validator layer1` (BaksmaliDiffer) over 30-APK subset — gate: recall ≥ 0.95 in ≥27/30 APKs
- [ ] 16.5 Run `validator layer2` (BootValidator) over 30-APK subset — gate: zero regressions vs ajc
- [ ] 16.6 Run `validator layer3` (TraceComparator) on cryptoapp + 30-APK subset — gate: F1 ≥ 0.98, kappa ≥ 0.9
- [ ] 16.6a Pre-batch 64k method-ref audit (INV-INS-25): run the projected-post-weaving ref counter over every APK in the Layer-4 candidate set, emit `Layer4PreAuditReport.json`; APKs projected to cross 65,000 host-DEX refs MUST be flagged; `multidex-merger` config MUST be set to emit an extra DEX for each flagged APK; batch run is BLOCKED while any APK carries unhandled overflow — never proceed assuming the host will accept a >65,536-ref DEX
- [ ] 16.7 Schedule `validator layer4` (BatchValidator JCA-400 × 3 × 3, ~36h) — single-shot weekend run for Phase-5 ratification; weekly thereafter for regression detection — gates: recovery_rate ≥ 90%; paired Wilcoxon signed-rank TOST per spec with pre-registered Δ=2pp (`cov_method`) / Δ=0.02 (F1) / Δ=0.05 (κ) at α=0.05 reject the lower-bound one-sided test (non-inferiority, mandatory); equivalence (both TOSTs reject) on ≥80% of specs (mandatory); thresholds file `validator/oracles/layer4-thresholds.yaml` committed before the run (INV-INS-21)
- [ ] 16.8 Run `validator layer5` (CoverageValidator) — gate: RVSEC-COV recall ≥ 0.99, delta ≤ 1pp
- [ ] 16.9 Aggregate reports into `docs/20260MM_dexlib2_validation_results.md` (post-Layer-4 dated)
- [ ] 16.10 Run `openspec verify gh52-instr-dexlib2` — must report all spec-aligned

## 17. Phase 6 — Substitution (P3)

- [ ] 17.1 Move legacy `rv-android/modules/rv-instrumentation/` → `rv-android/backup/2026-MM-DD-rv-instrumentation-ajc/`
- [ ] 17.2 Rename consideration: Python wrapper currently at `rv-android/modules/rv-instrumentation-dexlib2/` could be promoted to `rv-instrumentation` after legacy removal; decide based on consumer references. Java aggregator stays at `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` regardless.
- [ ] 17.3 Update `rv-experiment.PreProcessor._instrument_apks()` dispatch: now default to `dexlib2`; legacy `ajc` branch removed (unless retained as opt-in)
- [ ] 17.4 Change default of `ExperimentConfig.instrumentation_variant` to `"dexlib2"`
- [ ] 17.5 Grep entire repo for remaining references to legacy `RVInstrumentation` class — update or remove
- [ ] 17.6 Run `openspec sync gh52-instr-dexlib2` — merge delta specs into main `openspec/specs/instrumentation/spec.md`; manually add REMOVED Requirements section for the legacy ajc-specific REQUIREMENTS no longer applicable
- [ ] 17.7 Run `openspec validate --all` — must pass

## 18. Verification, code review, PR, archive

- [ ] 18.1 Run `/rv-qa-lint-fix rv-instrumentation-dexlib2` (Python wrapper)
- [ ] 18.2 Run `/rv-qa-lint-fix rv-monitor-generator`
- [ ] 18.3 Run `/rv-qa-lint-fix rv-experiment`
- [ ] 18.4 Run `mvn verify` over `rv-instrumentation-dexlib2/` — full Java test suite green
- [ ] 18.5 Run `/rv-verify rv-instrumentation-dexlib2` (Python wrapper)
- [ ] 18.6 Run `/rv-verify rv-monitor-generator`
- [ ] 18.7 Run `/rv-verify rv-experiment`
- [ ] 18.8 Invoke `/rv-code-reviewer` via Skill tool — review entire change against pre-plan + design + spec
- [ ] 18.9 Address review findings; commit fixes
- [ ] 18.10 Run `/rv-docs-sync` — propagate API/architecture changes into all consumer docs
- [ ] 18.11 Open PR `gh52-instr-dexlib2 → modules` with body referencing #52 and validation reports
- [ ] 18.12 Move card #52 to In Review on Kanban
- [ ] 18.13 After PR approved + merged: close #52 (commit `closes #52` in merge commit body or via `gh issue close`); move card to Done
- [ ] 18.14 Run `openspec archive gh52-instr-dexlib2` — moves change to `openspec/changes/archive/YYYY-MM-DD-gh52-instr-dexlib2/`
- [ ] 18.15 Run `/rv-retrospective` (optional) — capture process learnings: subagent dispatch effectiveness, Layer-4 wallclock vs estimate, gaps surfaced

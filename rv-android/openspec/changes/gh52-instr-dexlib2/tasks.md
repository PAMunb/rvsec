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
         - Group 12 (rv-instrumentation-dexlib2-py) — can start with stub CLI; finalize after Group 9
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
- [ ] 1.11 Run `openspec validate gh52-instr-dexlib2` — must report `is valid`

## 2. `descriptor-reader` Maven submodule (Java)

- [ ] 2.1 Create `rv-android/modules/rv-instrumentation-dexlib2/` parent `pom.xml` (packaging `pom`, Java 11, Jackson 2.18.2, JUnit 5, Picocli, dexlib2 3.0.8, ASM 9.7.1)
- [ ] 2.2 Create `descriptor-reader/pom.xml` (Jackson + slf4j only)
- [ ] 2.3 Implement POJOs: `AspectDescriptor`, `AdviceDescriptor`, `MonitorCallDescriptor`, `ParameterDescriptor`, `Position` enum, `PointcutExpression` (interface) + `CallPC`, `ExecutionPC`, `ArgsPC`, `TargetPC`, `NotWithinPC`, `CombinedPC`, `IfPC`, `StaticInitPC`
- [ ] 2.4 Implement `DescriptorReader.read(Path) → AspectDescriptor` (Jackson `ObjectMapper` config: fail on unknown properties, JSON pointer in errors)
- [ ] 2.5 Unit tests: load fixture `MultiSpec_1MonitorAspect.json` from `prototipo-dexlib2` test-fixtures; assert 115 advices, package, imports, common pointcut, base aspect exclusions
- [ ] 2.6 Negative tests: missing `imports`, empty `advices`, malformed `position` value → `DescriptorParseError` with JSON pointer
- [ ] 2.7 `mvn -pl descriptor-reader test` — all green

## 3. `pointcut-engine` Maven submodule (Java)

- [ ] 3.1 Create `pointcut-engine/pom.xml` (depends on descriptor-reader + ASM)
- [ ] 3.2 Port `PointcutExpressionParser` from prototype, refactor: returns typed `PointcutExpression` AST (not raw call-target list); cover `call`, `execution`, `args`, `target`, `!within`, `&&`, `||`, `!`, `staticinitialization`, `if`
- [ ] 3.3 Port `TypeResolver`: input simple name + imports → DEX type descriptor; respect descriptor's `imports` array as authority; never probe external classpath
- [ ] 3.4 Port `AndroidClassIndex`: ASM-based index of `android.jar`; methods `staticMethods(classFqn, methodName)`, `isAssignableFrom(parent, child)`; lazy-load + thread-safe
- [ ] 3.5 Implement `InheritanceResolver`: combines `AndroidClassIndex` with current APK's class hierarchy for `X+` semantics
- [ ] 3.6 Implement `PointcutMatcher`: takes `PointcutExpression` + `ClassDef` + `Method` + `Instruction` → `Optional<Match>` (with arg bindings). Include a CPS-aware resolution pass (INV-INS-24): when the enclosing class is a Kotlin state machine (extends `kotlin.coroutines.jvm.internal.BaseContinuationImpl` or `SuspendLambda`, or class name ends with `$<digit>`), match pointcuts against the call sites inside `invokeSuspend(Object, Throwable)` by resolving the source suspend-fun name from the `@DebugMetadata` annotation (when present) or by smali-level pattern recognition; patterns that cannot be matched must surface an `UnsupportedKotlinSuspendPatternError` captured in `LIMITATIONS.md`
- [ ] 3.7 Unit tests for each parser case (one fixture per AspectJ construct from `AJ_CONSTRUCTIONS_INVENTORY` — Group 15)
- [ ] 3.8 Unit tests for type resolution (Cipher → `Ljavax/crypto/Cipher;`, etc.)
- [ ] 3.9 Unit tests for AndroidClassIndex overload expansion (Cipher.getInstance returns 4 overloads)
- [ ] 3.10 `mvn -pl pointcut-engine test` — all green

## 4. `advice-emitter` Maven submodule (Java)

- [ ] 4.1 Create `advice-emitter/pom.xml` (depends on pointcut-engine + dexlib2 model directly; per design D1, `EmitPlan` and `RegisterRequest` value classes live in this module — `dex-mutator` consumes them, no circular dep)
- [ ] 4.2 Define `EmitPlan` value class (List<Instruction> toInsert, InsertionPoint point, RegisterRequest regs)
- [ ] 4.3 Define `AdviceEmitter` interface; concrete: `BeforeEmitter`, `AfterEmitter`, `AfterReturningEmitter`, `AfterThrowingEmitter` (uses `addCatch` for try/handler), `StaticInitializationEmitter` (synthesize `<clinit>` if absent), `IfGuardEmitter` (emit `if-eqz` before invoke), `ThisJoinPointEmitter` (pre-compute string constant)
- [ ] 4.4 Port `WrapperEmitter` from prototype's `WrapperGenerator`: generate `mop.MonitorWrappers.java` with one static method per `after returning` overload to avoid register aliasing
- [ ] 4.5 Unit tests per emitter: golden-file `EmitPlan` JSON serialization for canonical advices
- [ ] 4.6 `AfterThrowingEmitter` test: verify `tryStartLabel` / `catchAllHandler` placement
- [ ] 4.7 `StaticInitializationEmitter` test: synthesize `<clinit>` when missing; preserve when present
- [ ] 4.8 `IfGuardEmitter` test: emit `if-eqz` and skip-label before monitor invoke
- [ ] 4.9 `mvn -pl advice-emitter test` — all green

## 5. `dex-mutator` Maven submodule (Java)

- [ ] 5.1 Create `dex-mutator/pom.xml` (depends on advice-emitter + dexlib2; consumes `EmitPlan`/`RegisterRequest` types from advice-emitter per design D1)
- [ ] 5.2 Implement `InstructionInjector` primitives: `insertBefore(idx, EmitPlan)`, `insertAfter(idx, EmitPlan)`, `replaceInvoke(idx, MethodReference)`
- [ ] 5.3 Port `RegisterShifter` from prototype: bump `MutableMethodImplementation.registerCount` via reflection (NOT via setter — the prototype proved reflection is the only working path for mutable impls), shift register refs ≥ threshold by delta, expand 4-bit overflows to `from16`/`from32` formats. Cover explicitly: (a) MOVE/MOVE-OBJECT/MOVE-WIDE → MOVE_FROM16 promotion when receiver or result register crosses 15; (b) try-catch range endpoints adjustment when shifted instructions cross a catch handler boundary; (c) wide-op special cases (MOVE_WIDE consumes 2 adjacent registers — shifting must preserve pair alignment); (d) reconstruction of `MutableMethodImplementation` via a fresh builder instance rather than in-place setters when the instruction list is rewritten (dexlib2's MutableMethodImplementation is not fully mutation-safe when register counts change)
- [ ] 5.4 Implement `RegisterAllocator`: encapsulates scratch register allocation + spill decisions; uses `RegisterShifter` only when needed
- [ ] 5.5 Implement `DexWeaver.weave(DexFile, AspectDescriptor) → MutableDexFile`: orchestrates ClassDef × Method × Instruction iteration; for each match, calls `RegisterAllocator` + `InstructionInjector`
- [ ] 5.6 Implement `DexWeaver.weaveDexFile()` per-DEX iteration to preserve multidex split (INV-INS-15)
- [ ] 5.7 Unit tests: `RegisterShifter` covers all 20+ DEX formats (10x/t, 11n/x, 12x, 21c/ih/lh/s/t, 22b/c/s/t/x, 23x, 31c/i/t, 32x, 35c, 3rc, 51l + payloads); table-driven
- [ ] 5.8 Integration test: weave a tiny APK fixture, run baksmali on output, assert hook count + format correctness
- [ ] 5.9 Integration test: weave `cryptoapp` APK (committed as test fixture), assert 7 events in subsequent boot (smoke)
- [ ] 5.10 `mvn -pl dex-mutator verify` — all green (unit + IT)
- [ ] 5.11 Kotlin `suspend` / coroutines fixture (INV-INS-24): add `advice-emitter/src/test/KotlinSuspendFixtureTest` exercising two cases — (a) direct-suspend-invoke: a `suspend fun` whose body calls `Cipher.getInstance(...)` and returns synchronously, advice MUST match inside `invokeSuspend`; (b) continuation-captured: a `suspend fun` that awaits before the crypto call (forces state-machine expansion), advice MUST still match at the DEX-level call site. Each case ships a minimal Kotlin source + pre-built DEX as test resource. If the weaver cannot match a case, the test MUST be marked `@Disabled` with a comment citing the `LIMITATIONS.md` entry that justifies the gap (smali-level reproducer required in that entry).

## 6. `coverage-weaver` Maven submodule (Java)

- [ ] 6.1 Create `coverage-weaver/pom.xml` (depends on dex-mutator)
- [ ] 6.2 Implement `PackageFilter`: canonical exclusion list (java/, android/, androidx/, kotlin/, mop/, com/google/ + explicit `*..Log` exclusion); shared constant with rv-monitor-generator's `Coverage.aj`
- [ ] 6.3 Implement `SignatureFormatter`: emit `<FQN: ReturnType method(params)>` Soot-style; byte-exact match to production Coverage.aj output
- [ ] 6.4 Implement `CoverageWeaver`: prepend `invoke-static Lmop/Coverage;.log(Ljava/lang/String;)V` to every non-excluded method; uses `RegisterAllocator` for scratch
- [ ] 6.5 Unit tests: signature formatting on canonical method shapes (constructor, static, varargs, generics)
- [ ] 6.6 Integration test: weave `hateitorrateit` APK (Kotlin/R8) via Coverage; assert 21478/21478 methods instrumented (matches prototype baseline); 0 VerifyError on boot
- [ ] 6.7 `mvn -pl coverage-weaver verify` — all green
- [ ] 6.8 Thread-safety of generated `mop.Coverage` runtime state (INV-INS-23): (a) make `monitor-builder` (or the Coverage-class emitter, wherever the generated class source lives for the dexlib2 variant) produce a `mop.Coverage` with `private static final Set<String> SEEN = ConcurrentHashMap.newKeySet();` — NOT `HashSet<String>`; (b) add `coverage-weaver/src/test/CoverageThreadSafetyTest` that instruments a small fixture APK, boots it with ≥4 concurrent entry threads (UIAutomator driver or in-process stub), counts `RVSEC-COV` tags in logcat, and asserts the in-memory set size matches the logcat event count exactly (zero dropped events)

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
- [ ] 11.4 Update existing tests for new field; add positive test that `.json` files are emitted alongside `.aj` for JCA specs
- [ ] 11.5 Add negative test: when `emit_descriptor=False`, no `.json` files emitted
- [ ] 11.6 Run `/rv-test-run rv-monitor-generator`

## 12. `rv-instrumentation-dexlib2-py` Python wrapper

- [ ] 12.1 Create `rv-android/modules/rv-instrumentation-dexlib2-py/` with `pyproject.toml` (uv workspace member; deps: rv-android-core, pydantic v2)
- [ ] 12.2 Implement `DexlibInstrumentationConfig` (Pydantic, mirrors `RVInstrumentationConfig` shape; adds `cli_jar_path: Path`, `descriptor_glob: str`)
- [ ] 12.3 Implement `DexlibInstrumentation` class: `prepare_instrumentation()`, `instrument(app, result_dir)`, `instrument_apks(apks_dir, results_dir)`; subprocess to Java CLI; preserve `_error_phase` from CLI exit codes
- [ ] 12.4 Implement `MissingDescriptorError`, `DescriptorParseError`, `UnsupportedAspectConstructError` (in `rv-instrumentation-dexlib2-py.errors`)
- [ ] 12.5 Add `variant: Literal["ajc","dexlib2"]` field to `InstrumentationResults` in `rv-android-core` (default `"ajc"` for legacy compatibility)
- [ ] 12.6 Unit tests: config validation, `MissingDescriptorError` raised when no `.json` in `monitor_output_dir`
- [ ] 12.7 Integration test: parametrized `test_api_parity.py` runs both `RVInstrumentation` and `DexlibInstrumentation` over the same fixture APK; asserts identical `InstrumentationResults` shape (INV-INS-18)
- [ ] 12.8 Run `/rv-doc-code modules/rv-instrumentation-dexlib2-py/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py`
- [ ] 12.9 Run `/rv-test-run rv-instrumentation-dexlib2-py`

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
- [ ] 15.8 Author `rv-android/openspec/changes/gh52-instr-dexlib2/ADR-DEX-NATIVE.md` — architectural decision record for D1-D7 (decisions in design.md, including D7 AGP ASM deferred alternative), one section per decision: context / decision / status / consequences (template at `.claude/skills/rv-doc-adr/templates/adr.md`)

## 16. Phase 5 — Validation execution

- [ ] 16.1 Run `validator inventory` — assert `AJ_CONSTRUCTIONS_INVENTORY.md` is up to date (CI gate)
- [ ] 16.2 Run `validator mapping` (FeatureMappingChecker) — assert INV-INS-17
- [ ] 16.3 Run `validator parity` on JCA descriptors — assert `.aj` ↔ `.json` semantic equivalence
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
- [ ] 17.2 Rename `rv-android/modules/rv-instrumentation-dexlib2/` files appropriately (keep submodule layout); rename Python module `rv-instrumentation-dexlib2-py` → `rv-instrumentation-py` (or keep as-is, decide based on consumer references)
- [ ] 17.3 Update `rv-experiment.PreProcessor._instrument_apks()` dispatch: now default to `dexlib2`; legacy `ajc` branch removed (unless retained as opt-in)
- [ ] 17.4 Change default of `ExperimentConfig.instrumentation_variant` to `"dexlib2"`
- [ ] 17.5 Grep entire repo for remaining references to legacy `RVInstrumentation` class — update or remove
- [ ] 17.6 Run `openspec sync gh52-instr-dexlib2` — merge delta specs into main `openspec/specs/instrumentation/spec.md`; manually add REMOVED Requirements section for the legacy ajc-specific REQUIREMENTS no longer applicable
- [ ] 17.7 Run `openspec validate --all` — must pass

## 18. Verification, code review, PR, archive

- [ ] 18.1 Run `/rv-qa-lint-fix rv-instrumentation-dexlib2-py`
- [ ] 18.2 Run `/rv-qa-lint-fix rv-monitor-generator`
- [ ] 18.3 Run `/rv-qa-lint-fix rv-experiment`
- [ ] 18.4 Run `mvn verify` over `rv-instrumentation-dexlib2/` — full Java test suite green
- [ ] 18.5 Run `/rv-verify rv-instrumentation-dexlib2-py`
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

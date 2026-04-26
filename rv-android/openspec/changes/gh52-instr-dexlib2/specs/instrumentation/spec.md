# Spec Delta — instrumentation

GitHub Issue: #52

## Purpose

This delta extends the `instrumentation` capability with a DEX-native weaving pipeline implemented over `dexlib2`, alongside the existing AspectJ/dex2jar pipeline that this delta also amends. After Phase 4 (Implement) and during Phase 5 (Verify), both pipelines coexist behind a variant flag (`ajc` | `dexlib2`) so that paired comparison on the JCA-400 dataset is possible. The DEX-native pipeline becomes the default in Phase 6, and the AspectJ pipeline is then quarantined to `backup/` per Development Principle P3 (no backward compatibility); that quarantine is documented as a separate REMOVED set in a later delta tied to the same change once Layer-4 validation has ratified parity.

The motivation is structural and was diagnosed in `docs/20260421_problema_dex2jar.md`: the legacy pipeline performs a `APK → dex2jar → ajc → d8 → APK` round-trip that is irreconcilable with R8-optimized DEX bytecode under JVMS §4.10.1.9 type-consistency. The empirical effect was 63.6% of JCA-400 APKs booting with `VerifyError` despite the pipeline reporting 74.5% success. The DEX-native pipeline operates exclusively on DEX bytecode and never crosses into JVM `.class` form, eliminating the round-trip entirely. A working prototype (`prototipo-dexlib2`) validated this end-to-end on cryptoapp (Java) and hateitorrateit (Kotlin/R8) with 100% method coverage and zero `VerifyError`.

The capability remains the boundary between RV-Android's experiment orchestration (`rv-experiment`) and the act of producing a runtime-monitored APK from a baseline APK plus a set of MOP specifications. Variant selection is a configuration concern; the public Python contract `instrument_apks(apks_dir, results_dir) → InstrumentationResults` is preserved unchanged across the variant boundary so that downstream consumers (rv-platform, rv-experiment) require no API changes.

The DEX-native pipeline introduces three new artifacts in the contract between `rv-monitor-generator` and `rv-instrumentation`: (a) a JSON descriptor (`MultiSpec_*MonitorAspect.json`) emitted by JavaMOP under the `--emit-descriptor` flag, carrying the structured pointcut/advice metadata that the weaver consumes; (b) a Maven validator harness operationalizing the rigor framework from `docs/20260423_plano_validacao.md` (Layers 1-5 + static checks); and (c) three paper-grade documents (`AJ_CONSTRUCTIONS_INVENTORY.md`, `AJ_TO_DEXLIB2_MAPPING.md`, `LIMITATIONS.md`) that prove construction-by-construction equivalence and explicitly document the AspectJ constructs that are out of scope. The canonical out-of-scope set (8 items, empirically zero usages across all RVSEC specifications) is: `around`, `cflow`, `cflowbelow`, `handler`, `get`, `set`, `initialization`, `preinitialization`.

```mermaid
flowchart LR
    subgraph IN["Inputs"]
        APK[APK]
        MOP[".mop specs<br/>(JCA / generic)"]
    end
    subgraph GEN["rv-monitor-generator<br/>(MODIFIED — emits .json)"]
        JM["javamop<br/>--emit-descriptor"]
        RM[rv-monitor]
        JM --> AJ[".aj"]
        JM --> JSON[".json descriptor"]
        JM --> RVM[".rvm"]
        RVM --> RM
        RM --> JAVA[".java monitor"]
    end
    subgraph DISP{"variant<br/>flag"}
    end
    subgraph AJC["ajc variant<br/>(unchanged path)"]
        AJW[ajc weave + d8]
    end
    subgraph DLX["dexlib2 variant<br/>(NEW path)"]
        DR[descriptor-reader]
        PE[pointcut-engine]
        AE[advice-emitter]
        DM[dex-mutator]
        CW[coverage-weaver]
        MB[monitor-builder]
        MM[multidex-merger]
        DR --> PE --> AE --> DM
        CW --> DM
        JAVA --> MB
        DM --> MM
        MB --> MM
    end
    subgraph OUT["Outputs"]
        SAPK["Signed APK<br/>+ InstrumentationResults<br/>+ variant tag"]
    end

    APK --> DISP
    MOP --> JM
    AJ --> AJC
    JSON --> DR
    JAVA --> AJC
    DISP -->|"'ajc'"| AJC
    DISP -->|"'dexlib2'"| DLX
    AJC --> SAPK
    MM --> SAPK

    classDef mod fill:#ffe,stroke:#cc3;
    classDef new fill:#efe,stroke:#3c3;
    class GEN mod
    class JSON,DR,PE,AE,DM,CW,MB,MM,DLX new
```

## Data Contracts

### Input

- `descriptor_path: pathlib.Path` — path to a `MultiSpec_*MonitorAspect.json` file emitted by `javamop --emit-descriptor`. Source: `rv-monitor-generator` writes one descriptor per merged aspect alongside the existing `.aj` and `.java` outputs in `monitor_output_dir`.
- `instrumentation_variant: Literal["ajc","dexlib2"]` — set by `ExperimentConfig` (default `"ajc"` until Phase 6 ratification, then `"dexlib2"`). Consumed by `PreProcessor._instrument_apks()` to dispatch to `RVInstrumentation` (legacy) or `DexlibInstrumentation` (new).
- `apk_path: pathlib.Path` — original APK to instrument (existing input, unchanged).

### Output

- `signed_apk_path: pathlib.Path` — instrumented + signed APK at `{instrumented_dir}/{app_name}.apk`. The contract `hash(signed) ≠ hash(original)` is preserved across both variants.
- `InstrumentationResults` — Pydantic model with `success_count`, `total_count`, `errors`, plus a new field `variant: Literal["ajc","dexlib2"]` recording which pipeline produced the results (consumed by `rv-platform` for traceability).
- `validation_report_path: pathlib.Path` (validator only) — JSON report from any `validator/` layer (BaksmaliDiff, TraceComparator, etc.) used by Phase 5 gates.

### Side-Effects

- **Filesystem (rv-monitor-generator)**: writes `MultiSpec_*MonitorAspect.json` to `monitor_output_dir/` alongside `.aj`/`.java`/`coverage.aj`/`logging.aj`. The `.json` is additive and does not invalidate any existing artifact.
- **Filesystem (rv-instrumentation-dexlib2)**: temporary working directories per APK (decompiled DEX index, woven DEX, signed APK staging). Cleaned after each APK regardless of success or failure (analogous to legacy `tmp_dir` lifecycle in INV-INS-08).
- **JVM subprocess**: the Python wrapper `DexlibInstrumentation` invokes the Java CLI `InstrumentationCli` once per APK; failures surface as non-zero exit codes mapped to `CommandException` with `tool="dexlib2-cli"` and accurate `_error_phase`.

### Error

- `MissingDescriptorError` — raised when `instrumentation_variant == "dexlib2"` and the corresponding `MultiSpec_*MonitorAspect.json` is absent from `monitor_output_dir`. The error message MUST identify the missing file and indicate that `rv-monitor-generator` must be invoked with the `--emit-descriptor` flag enabled.
- `DescriptorParseError` — raised when the JSON descriptor exists but fails Jackson deserialization against the `AspectDescriptor` schema. Message MUST cite the exact JSON pointer of the failing field.
- `UnsupportedAspectConstructError` — raised when a descriptor advice references a construct in the canonical out-of-scope set (`around`, `cflow`, `cflowbelow`, `handler`, `get`, `set`, `initialization`, `preinitialization`). The error message MUST cite `docs/LIMITATIONS.md` and the offending advice name.
- `CommandException` — preserved for tool failures (`d8`, `apksigner`, `zipalign`, `javac`, `dexlib2-cli`), with `_error_phase` populated by the innermost decorator analogous to the legacy pipeline (INV-INS-08 / FR02).

## Invariants

- **INV-INS-13**: When `instrumentation_variant == "dexlib2"`, the resolved `monitor_output_dir` MUST contain at least one `MultiSpec_*MonitorAspect.json` file before `instrument_apks()` begins. Validation MUST occur at preparation time, not per-APK.
- **INV-INS-14**: Each pipeline MUST satisfy the subset of INV-INS-01..INV-INS-12 that applies to its tool chain. Both variants MUST satisfy the tool-agnostic invariants: hash(signed) ≠ hash(original) (INV-INS-06), temp directories cleaned per APK (INV-INS-08), specification sets never mixed (INV-INS-09), and the semantic content of INV-INS-10 that the APK is signed before placement in `instrumented_dir`. The tool-specific wording of INV-INS-10 (`d2j-apk-sign` + `jarsigner`) applies ONLY to the `ajc` variant; for the `dexlib2` variant, "APK signed" is satisfied by `apksigner v3` alone (no `d2j-apk-sign`, no `jarsigner`). INV-INS-11 (dex2jar tools must exist and be executable) applies ONLY to the `ajc` variant. For the `dexlib2` variant, `DexlibInstrumentationConfig` validators MUST instead assert that `apksigner` v3, `zipalign`, and `d8` are present and executable — the dex2jar suite is NOT required and MUST NOT be probed at preparation time.
- **INV-INS-15**: The DEX-native pipeline MUST preserve the multidex split decisions of the input APK. If the input has `classes.dex` + `classes2.dex` + `classes3.dex`, the output MUST contain the same partitioning of application classes; the weaver MAY add a single additional DEX file for monitor classes when the host DEX would otherwise exceed the 65,536 method-id limit.
- **INV-INS-16**: Coverage weaving MUST instrument every method in app code (i.e., every `Lcom/example/...;` class not matched by the canonical exclusion filter), with zero exceptions for register pressure. When a method's register count would exceed Dalvik's 4-bit limit after injection, `RegisterShifter` MUST expand instructions to the corresponding wide format (`/from16`, `move-object/from16`, etc.) preserving semantics.
- **INV-INS-17**: The `validator/FeatureMappingChecker` MUST assert that every AspectJ construct enumerated in `docs/AJ_CONSTRUCTIONS_INVENTORY.md` has either (a) at least one positive test in `validator/src/test/` proving the dexlib2 mapping, or (b) an explicit entry in `docs/LIMITATIONS.md` declaring the construct as out of scope with empirical evidence of zero usage in RVSEC specifications. A construct present in inventory but absent from both MUST fail the check.
- **INV-INS-18**: The Python public API `instrument_apks(apks_dir, results_dir) → InstrumentationResults` MUST behave identically (return type, exception types, side-effect surface) regardless of the variant chosen. Differences MUST be confined to `InstrumentationResults.variant`, error messages, and the contents of the produced APKs. The `variant` field MUST be a required attribute (no Pydantic default) on the producing path — every pipeline writes its own variant tag explicitly. Backward-compatible deserialization of legacy `InstrumentationResults` JSON (written before this change) MUST be provided via a Pydantic `model_validator(mode="before")` that injects `variant="ajc"` when the key is absent. This separation prevents silent mis-tagging when `ExperimentConfig.instrumentation_variant` defaults switch in Phase 6.
- **INV-INS-19**: When the `--emit-descriptor` flag is passed to `rv-monitor-generator`, the resulting JSON descriptor for each merged aspect MUST mirror the semantic content of the corresponding `.aj` file. Specifically, for every `AdviceAndPointCut` entry the JSON MUST encode: advice position (before/after/around), pointcut expression as parsed AST, parameter list, returning/throwing bindings, and the full `monitorCalls` list. Validation MUST be possible by `validator/DescriptorAjParityChecker` comparing JSON tree against `.aj` text round-trip.
- **INV-INS-20**: During the coexistence phase (Phase 4 → Phase 5), failure of one variant on a given APK MUST NOT prevent the other variant from being attempted on that APK in a separate run. Variant selection is per-experiment-run, not per-APK; cross-variant comparison is an external batch operation owned by the `validator/` harness.
- **INV-INS-21**: Statistical equivalence and non-inferiority claims for Layer-4 MUST use paired Wilcoxon signed-rank Two One-Sided Tests (TOST) against pre-registered equivalence bounds, declared in `validator/oracles/layer4-thresholds.yaml` before the batch runs: Δ=2pp for `cov_method`, Δ=0.02 for per-spec F1, Δ=0.05 for per-spec Cohen's kappa, all at α=0.05. Equivalence holds when both one-sided TOSTs reject; non-inferiority (the weaker claim accepted for Phase-6 promotion) holds when the lower-bound TOST alone rejects. Mann-Whitney U MUST NOT be used as the primary gate — as an unpaired test on paired samples it violates model assumptions, and failing to reject its H0 ("same distribution") is not evidence of equivalence. MWU MAY figure as a supplementary distributional check only. The Layer-4 report MUST include, per spec: point estimate of the paired median difference, bootstrapped 90% CI (≥10,000 resamples), both TOST p-values, and the Wilcoxon effect size `r`.
- **INV-INS-22**: The Ground-Truth Oracle Diversity requirement (below) MUST be satisfied before any Layer-3 or Layer-4 report can be cited as evidence for Phase-6 promotion. A single oracle (cryptoapp alone) is insufficient: it exercises one bytecode profile (Java, pre-R8, non-multidex) and 8 known violations, generalizing poorly to the Kotlin/R8/multidex universe that motivates this change.
- **INV-INS-23**: The generated `mop.Coverage` runtime class (produced for the `dexlib2` variant) MUST back its seen-signatures state with a thread-safe lock-free collection — `ConcurrentHashMap.newKeySet()` is the canonical choice. Plain `HashSet<String>` (or any non-thread-safe set) MUST NOT be used. Validation: `coverage-weaver/src/test/CoverageThreadSafetyTest` MUST run a ≥4-thread entry fuzz against an instrumented fixture and reconcile the in-memory signature set with the `RVSEC-COV` logcat event count; reconciliation MUST be exact (zero dropped events). This invariant is specific to the `dexlib2` variant; the `ajc` variant's `Coverage.aj` is outside this change's scope.
- **INV-INS-24**: When the `dexlib2` pipeline instruments a Kotlin APK containing a `suspend` function whose body invokes a method targeted by a MOP pointcut, the advice MUST fire at least once on the effective DEX-level call inside the compiler-generated `invokeSuspend(Object, Throwable)` state machine. The weaver MUST match pointcuts against the Kotlin-to-JVM lowering of suspend bodies, not only against user-visible method signatures. If a specific suspend pattern (e.g., non-trivial continuation captures, tail-call optimizations under `-Xjvm-default=all`) cannot be matched, `docs/LIMITATIONS.md` MUST name the pattern with a minimal reproducer and a smali-level excerpt showing where matching fails. Validation: `advice-emitter/src/test/KotlinSuspendFixtureTest` asserts matching against at least a direct-suspend-invoke case and a continuation-captured case.
- **INV-INS-25**: Before the Layer-4 batch executes, a pre-batch method-ref audit MUST run over the candidate APK set and emit `Layer4PreAuditReport.json` identifying any APK whose host DEX (projected post-weaving) would cross 65,000 method refs. APKs that would exceed the 65,536 Dalvik limit without an additional DEX partition MUST be flagged, and `multidex-merger` MUST emit an extra DEX rather than allowing ref-table corruption or silent overflow. The audit is a hard gate for the Layer-4 run: no batch proceeds while any candidate APK carries an unhandled overflow.
- **INV-INS-26**: Any code path that adds scratch register slots to a method MUST preserve Android DEX's calling convention (parameters live in the highest `paramRegisterCount` slots). Naive `bumpRegisterCount(+N)` alone is insufficient: it implicitly relocates the parameter window without rewriting the bytecode that references the old positions, leaving every parameter register Undefined at method entry → `java.lang.VerifyError: tried to get class from non-reference register vN (type=Undefined)` on the first instruction that touches a parameter (essentially every instrumented method that has parameters). The canonical strategy MUST be: when scratch is needed at a low register, shift every existing register reference up by `N` first (via `RegisterShifter.shiftExpanding` with `threshold=0, delta=N`), then call `bumpRegisterCount(+N)` — both steps in `RegisterShifter.spillLowRegisters`. When the method already has at least `N` free local registers (`localCount >= N`), no shift/bump is needed; use the existing low locals as scratch. This applies to both `coverage-weaver.CoverageWeaver` and `dex-mutator.RegisterAllocator`. Validation: `coverage-weaver/src/test/SpillStrategyTest` MUST cover both branches (free-locals path and shift+bump path) on synthetic methods with paramRegs ∈ {0, 1, 4} and localCount ∈ {0, 1, 3}, and the cli-level smoke MUST install + boot the woven cryptoapp on a physical or emulated API 30 device without `VerifyError` (proxied via `validator layer2`).
- **INV-INS-27**: Any advice emitter that inserts instructions AFTER a matched invoke MUST insert AFTER the invoke's `move-result*` instruction (when present), not between the invoke and its move-result. The DEX `move-result*` family is **only valid as the immediate successor of an invoke that returns a value**: any non-move-result instruction in between (including the monitor's `invoke-static` for the advice event) makes `move-result*` read from the WRONG invoke's pseudo-register, leading to either `VerifyError: type Undefined unexpected` (when the new invoke returns void) or silent return-value corruption (when the new invoke returns a compatible type). Validation: `advice-emitter/src/test/MoveResultGuardTest` MUST construct synthetic match contexts where the matched invoke is followed by a move-result and assert the emitter's plan inserts past the move-result, not before it; the cli-level smoke MUST install + boot a fixture APK whose advice targets a method whose return is consumed via `move-result-object` (`androidx.core.util.Preconditions.checkArgument` is the canonical reproducer found during the gh52 cryptoapp smoke).
- **INV-INS-28**: The `args()` pointcut binding offset MUST come from the matched invoke's actual opcode (`invoke-static*` → first register operand is the first arg; non-static invokes → first register operand is the receiver and args start at offset 1). The AspectJ `static` modifier is stripped at parse time and MUST NOT be relied on as the source of truth — using a stub heuristic that always reports the call as non-static silently shifts every static-call binding by one register, causing the advice's `args(arg)` to point at either the receiver position of a different invoke (typically v0, frequently an Uninitialized Reference) or at an unrelated register. Surfaced in the gh52 cryptoapp smoke as `VerifyError: register v0 has type Uninitialized Reference: java.lang.IllegalArgumentException Allocation PC: 3 but expected Reference: java.lang.Object` on every match against `String.valueOf(Object)` inside `androidx.core.util.Preconditions.{checkArgument, checkNotNull, checkStringNotEmpty}`. Validation: `pointcut-engine/src/test/StaticInvokeBindingTest` MUST cover the static / non-static / constructor cases on synthetic invoke instructions and assert the resulting `argBindings` map points at the right register operand index.
- **INV-INS-29**: AFTER advice on a matched invoke whose register operands or `move-result*` destination overlap the advice's `args()` / `target()` / `returning()` bindings MUST route through a static wrapper in `mop.MonitorWrappers`, not through inline injection. Inline injection of an after-side hook reads register state AFTER the matched invoke + `move-result*` have overwritten the binding source registers — the verifier observes the resulting type confusion (e.g. `register v2 has type Imprecise Constant: 32767 but expected Reference: javax.crypto.KeyGenerator`) and rejects the class. The wrapper substitution path (D5 + D12) replaces the matched invoke's `MethodReference` with a wrapper that calls the original AND fires every monitor event using its own local frame, so the caller's registers stay byte-identical. Wrapper substitution MUST be performed before any inline advice in a 2-pass weaver (`replaceInstruction` is size-stable so left-to-right is safe; inline advice MUST iterate right-to-left so its `applyPlan` insertions never invalidate already-processed indices). When a matched call is not eligible for wrapper substitution (instance-method targets, varargs / wildcard-param patterns that would need overload expansion via `AndroidClassIndex`), the inline AFTER hook MUST be skipped and recorded in `weaveCounts.plansSkippedAliasing` rather than emitted with broken register bindings. Validation: `dex-mutator/src/test/WrapperSubstitutionTest` (synthetic descriptors covering static / instance / constructor + args / target / returning) + `coverage-weaver` smoke against cryptoapp showing zero `VerifyError` and ≥ 50 wrappersSubstituted across the 6 woven DEXes.
- **INV-INS-30**: `MonitorInvokeBuilder.registersFor` MUST resolve advice parameter names to registers via the bindings declared in the expression (`target(name)` → `match.targetRegister`; `args(n1, n2, ...)` → `match.argBindings.get("argNN")` per slot; `returning(name)` / `throwing(name)` → 0 best-effort, since those binding sources are handled by the wrapper system D5 / D12 not the inline path). The previous positional-only resolution (walking advice parameters in declaration order and looking up `arg00`, `arg01`, ...) silently mis-bound every advice that mixed `target()` with `args()` — a `KeyGenerator.init(int)` advice with `target(k)` would call `KeyGeneratorSpec_initEvent(KeyGenerator)` with the int key-size register instead of the receiver, surfacing as `VerifyError: register v2 has type Imprecise Constant: 32767 but expected Reference: javax.crypto.KeyGenerator`. The runtime monitor's signature follows `monitorCall.args` order, so `buildMethodReference` MUST also walk that name list (not the advice's declaration order) to produce parameter descriptors that match. Validation: `advice-emitter/src/test/MonitorInvokeBindingTest` covering the four binding clauses + their cross-products on synthetic match contexts; cli-level smoke against cryptoapp must emit each advice's `<spec>_<event>Event(...)` invoke with register operands typed correctly per the verifier (proxied via zero `VerifyError` after weave).
- **INV-INS-31**: The wrapper system MUST cover instance-method advices (advices whose matched call is `invoke-virtual` / `invoke-interface` / `invoke-direct` / `invoke-super`) and not just static-call advices. Concrete overloads MUST be enumerated through `AndroidClassIndex.methods(declFqn, methodName, /*onlyStatic=*/false)` so that varargs (`..`), supertype-pattern (`T+`), and ambiguous-`Object` parameter patterns expand to the actual Android API signatures rather than being defensively skipped at the descriptor level. For each enumerated overload, `WrapperEmitter` MUST emit one wrapper Java method per overload: static targets keep the original call form `<DeclaringFqn>.<method>(p0, ...)`; instance targets MUST take the receiver as the wrapper's first parameter (`<DeclaringFqn> recv`) and call `recv.<method>(p0, ...)` so that `target(name)` advice bindings map to `recv` and `args(...)` bindings map to `p0..pN` in the wrapper body. The DEX-side substitution MUST register the wrapper's `MethodReference` with the receiver descriptor prepended (so the wrapper-call's static parameter list lines up with the instance-call's register operands, including the receiver at register C), while the lookup KEY MUST remain the original (unprepended) signature so the call site is found. `findWrapperReplacement` MUST therefore accept every invoke kind, not just `INVOKE_STATIC`. The 52 `plansSkippedAliasing` reported on the cryptoapp + 3-APK smoke run pre-INV-INS-31 stemmed from this defensive skip; lifting the static-only filter is what reduces that count. **Subtype-dispatch correction (Phase 2)**: When a call site dispatches through an APK-internal subtype (e.g. `invoke-virtual {recv}, Lcom/myapp/CustomCipher;->doFinal(...)` where `CustomCipher` extends `javax.crypto.Cipher`), `findWrapperReplacement`'s exact-class lookup MUST still resolve to the parent's wrapper. This is achieved by `DexWeaver.expandWrapperReplacementsForApk(InheritanceResolver)` which walks each instance wrapper's `subtypesOf(parentFqn)` BEFORE the per-DEX weave loop and registers additional lookup keys pointing at the SAME static `MethodReference` (the wrapper signature stays receiver-typed as the parent — DEX verifier accepts the substitution because subtypes are assignable to their supertypes per JVMS §4.10.1.9). Static wrappers MUST NOT be expanded — `invoke-static` on a subtype invokes the subtype's own static, not the parent's. `BatchRunner` MUST construct one multi-DEX `InheritanceResolver` across every `classes*.dex` of the APK and call the expansion exactly once before weaving. `WeaveReport.wrappersAliasedToSubtype` reports the additional key count for observability. Validation: `advice-emitter/src/test/WrapperEmitterTest` (4 cases) covering Phase 1 + `dex-mutator/src/test/DexWeaverWrapperSubtypeTest` (2 cases) covering Phase 2's instance-aliasing and static-skipping behavior; cli-level smoke must show `plansSkippedAliasing` strictly decreasing (target: 0) without introducing any new `VerifyError`.

## ADDED Requirements

### Requirement: DEX-Native APK Instrumentation Pipeline

The system MUST provide an alternative to the AspectJ-based instrumentation pipeline that operates exclusively over DEX bytecode using `dexlib2`, eliminating the `dex2jar → ajc → d8` round-trip and the JVMS §4.10.1.9 type-consistency conflict it induces on R8-optimized APKs. This pipeline MUST be implemented as a Maven multi-module Java aggregator `rvsec-instrumentation-dexlib2` at `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` (sibling of `rvsec-apk`, `rvsec-gator`, etc. under the `rvsec-android` aggregator) wrapped by a Python module `rv-instrumentation-dexlib2` at `rv-android/modules/rv-instrumentation-dexlib2/` (uv workspace member) that exposes the same `instrument_apks(apks_dir, results_dir) → InstrumentationResults` contract used by the legacy pipeline.

The Java side MUST decompose into single-responsibility submodules: `descriptor-reader` (Jackson POJO model for the JSON descriptor), `pointcut-engine` (parser + matcher + type resolver + android.jar overload index), `advice-emitter` (one emitter per advice kind: before, after, after returning, after throwing, staticinitialization, if-guarded, plus a wrapper emitter for register-aliasing-safe replacement), `dex-mutator` (DexWeaver orchestration + InstructionInjector + RegisterAllocator + RegisterShifter), `coverage-weaver` (the `execution(* *.*(..))` catch-all with canonical package filter and Soot-style signature formatting), `monitor-builder` (javac + d8 over `MultiSpec_*RuntimeMonitor.java`, `mop.MonitorWrappers.java`, and runtime JARs), `multidex-merger` (apksigner v3 + zipalign), `cli` (Picocli unified entry point), and `validator` (the rigor harness — see separate requirement).

The pipeline MUST consume the JSON descriptor produced by `javamop --emit-descriptor` (see modified Monitor Generation requirement below) as its sole source of pointcut/advice semantics. It MUST NOT parse the textual `.aj` output. The descriptor's `imports` list MUST be the authority for resolving simple type names (e.g., `Cipher` → `Ljavax/crypto/Cipher;`) into DEX type descriptors.

The pipeline MUST preserve the multidex structure of the input APK (INV-INS-15) and MUST honor the canonical Coverage exclusion filter (INV-INS-16). When register pressure forces `4-bit` instruction format expansion, the weaver MUST emit the corresponding `from16` / `from32` variants and bump `MethodImplementation.registerCount` accordingly, never silently dropping or skipping advice insertions.

#### Scenario: DEX-native instrumentation of an R8-optimized APK previously failing under ajc

- **WHEN** an APK previously known to fail at boot with `VerifyError` under the `ajc` variant (e.g., `hateitorrateit` from the JCA-400 dataset), and the corresponding JSON descriptor is present in `monitor_output_dir`, and `instrumentation_variant == "dexlib2"`
- **THEN** `DexlibInstrumentation.instrument(app, result_dir)` MUST produce a signed APK at `{instrumented_dir}/{app.name}.apk`
- **AND** the instrumented APK hash MUST differ from the original APK hash (preserving INV-INS-06)
- **AND** booting the APK in an emulator MUST NOT raise `VerifyError`
- **AND** RVSEC-COV events MUST be emitted to logcat for app-code methods exercised during the boot sequence
- **AND** all AspectJ business advices in the descriptor that match invocations executed during boot MUST trigger the corresponding monitor event

#### Scenario: Missing descriptor when dexlib2 variant is selected

- **WHEN** `instrumentation_variant == "dexlib2"` and `monitor_output_dir` contains `MultiSpec_1MonitorAspect.aj` and `MultiSpec_1RuntimeMonitor.java` but no `MultiSpec_1MonitorAspect.json`
- **THEN** `DexlibInstrumentation.prepare_instrumentation()` MUST raise `MissingDescriptorError` before any APK processing begins
- **AND** the error message MUST identify the missing JSON file and mention the `--emit-descriptor` flag

#### Scenario: Multidex preservation under DEX-native weaving

- **WHEN** an input APK contains `classes.dex` + `classes2.dex` (two DEX files due to method-id pressure) and `instrumentation_variant == "dexlib2"`
- **THEN** the output APK MUST contain at least `classes.dex` + `classes2.dex` with the same application-class assignment to each DEX
- **AND** if monitor classes (from `MultiSpec_*RuntimeMonitor.java` + `mop.MonitorWrappers.java`) push the host DEX over 65,536 method refs, exactly one additional DEX file MUST be added for the monitor classes
- **AND** the output APK MUST NOT silently merge multidex partitions

#### Scenario: Register-pressure expansion preserves advice insertion

- **WHEN** the weaver injects a monitor call into a method whose register usage would push an instruction beyond Dalvik's 4-bit register-index limit (e.g., needs `v16` or higher in a `12x` `move` form)
- **THEN** `RegisterShifter` MUST expand the affected instructions to the wider format (`22x` `move/from16`, `32x` `move/from16`, etc.)
- **AND** `MethodImplementation.registerCount` MUST be bumped by the number of additional registers consumed
- **AND** the advice insertion MUST NOT be silently skipped due to register pressure

### Requirement: Instrumentation Variant Selection

`rv-experiment` MUST allow an experiment to select the instrumentation backend by setting `ExperimentConfig.instrumentation_variant: Literal["ajc","dexlib2"]`. The default value MUST be `"ajc"` during Phase 4 → Phase 5 (coexistence and validation) and MUST switch to `"dexlib2"` in Phase 6 once Layer-4 validation ratifies parity.

`PreProcessor._instrument_apks()` MUST dispatch to `RVInstrumentation` for the `"ajc"` value and to `DexlibInstrumentation` for the `"dexlib2"` value. Both implementations MUST honor the same `instrument_apks(apks_dir, results_dir) → InstrumentationResults` contract (INV-INS-18). The `InstrumentationResults` model MUST carry a new `variant: Literal["ajc","dexlib2"]` field recording which pipeline produced the results, persisted to `instrument_errors.json` and any downstream reports.

The variant selection MUST be exposed at the CLI level (`rv-experiment --instrumentation-variant <ajc|dexlib2>`) and via `ExperimentConfig` deserialization for batch / Docker scenarios. Selecting a variant MUST NOT alter `rv-monitor-generator` behavior: the generator always emits both `.aj`/`.java` (consumed by ajc) and `.json` (consumed by dexlib2), so a single monitor-generation run supports both variants.

#### Scenario: Variant flag dispatches to dexlib2 pipeline

- **WHEN** `ExperimentConfig.instrumentation_variant` is `"dexlib2"` and an experiment is run
- **THEN** `PreProcessor._instrument_apks()` MUST instantiate `DexlibInstrumentation` (not `RVInstrumentation`)
- **AND** the resulting `InstrumentationResults.variant` MUST equal `"dexlib2"`
- **AND** `instrument_errors.json` MUST record `variant: "dexlib2"` at its root

#### Scenario: Default variant during coexistence phase

- **WHEN** `ExperimentConfig` is loaded without an explicit `instrumentation_variant` field, before Phase 6 ratification
- **THEN** `instrumentation_variant` MUST default to `"ajc"`
- **AND** `InstrumentationResults.variant` MUST equal `"ajc"`

#### Scenario: Default variant after Phase 6 ratification

- **WHEN** the Phase 6 substitution commit has been merged (legacy `rv-instrumentation` quarantined to `backup/`) and `ExperimentConfig` is loaded without an explicit `instrumentation_variant`
- **THEN** `instrumentation_variant` MUST default to `"dexlib2"`

#### Scenario: Invalid variant value

- **WHEN** `ExperimentConfig.instrumentation_variant` is set to a value not in `["ajc","dexlib2"]`
- **THEN** `ExperimentConfig.validate()` MUST raise a `ValueError` with message listing the valid variants

### Requirement: JavaMOP Descriptor Format and Emission

The contract between `rv-monitor-generator` and the DEX-native instrumentation pipeline MUST be a JSON descriptor file emitted by JavaMOP under the `--emit-descriptor` flag. The descriptor MUST be written alongside the existing `.aj` artifact at `{monitor_output_dir}/MultiSpec_<N>MonitorAspect.json` and MUST mirror the semantic content of the AspectJ AST that produced the `.aj` (INV-INS-19). Parsing of the textual `.aj` is forbidden as a contract source; the JSON is the canonical machine-readable form.

The descriptor schema MUST contain at minimum: `aspectName`, `fileName`, `shortName`, `package` (the MOP file's `package` declaration), `imports` (the resolved import list including JavaMOP-required imports), `commonPointcut`, `baseAspectExclusions`, and an `advices` array. Each advice MUST encode `name`, `specName`, `parameters[]`, `position` (`before` | `after` | `around`), `returning` (nullable), `throwing` (nullable), `expression` (the textual pointcut for human readability), and `monitorCalls[]` (target class, method name, args by name).

The `imports` field MUST include both the user's imports and the JavaMOP-required set (`java.util.concurrent.*`, `java.util.concurrent.locks.*`, `java.util.*`, `javamoprt.*`, `java.lang.ref.*`, `org.aspectj.lang.*`) so that the weaver's `TypeResolver` can map any simple type name appearing in a pointcut to a fully-qualified DEX descriptor without recourse to external classpath probing.

The patch enabling this emission MUST be applied to the vendored `rvsec/javamop/` and pinned at the commit recorded in this change's design document.

#### Scenario: Descriptor emitted alongside .aj for any specification set

- **WHEN** `RuntimeVerificationGenerator.generate_monitors(output_dir)` is invoked with `mop_specs_dir` pointing to any supported specification set (JCA, Generic, or a future addition), `javamop_bin` is the patched JavaMOP, and the configuration enables descriptor emission
- **THEN** `output_dir` MUST contain `MultiSpec_1MonitorAspect.aj` (existing behavior)
- **AND** `output_dir` MUST contain `MultiSpec_1MonitorAspect.json`
- **AND** the JSON MUST validate against the `AspectDescriptor` schema declared in `descriptor-reader`
- **AND** the JSON `advices` array MUST have exactly the same length as the `.aj` advice count (115 for the JCA merge — empirically validated in the prototype; each spec set has its own count). The descriptor-reader does NOT depend on that count; the scenario enforces a per-set invariant, not a constant.

#### Scenario: Descriptor imports include both user and required sets

- **WHEN** a MOP spec declares `import javax.crypto.Cipher;` at the top
- **THEN** the emitted descriptor's `imports` array MUST include `"javax.crypto.Cipher"`
- **AND** it MUST also include the JavaMOP-required entries: `"java.util.concurrent.*"`, `"java.util.concurrent.locks.*"`, `"java.util.*"`, `"javamoprt.*"`, `"java.lang.ref.*"`, `"org.aspectj.lang.*"`
- **AND** there MUST be no duplicate entries

#### Scenario: Weaver rejects descriptor missing required fields

- **WHEN** `DexWeaver` loads a JSON descriptor that lacks the `imports` field or has `advices: []`
- **THEN** `DescriptorReader.read(path)` MUST raise `DescriptorParseError`
- **AND** the error MUST identify the missing field by JSON pointer

### Requirement: Validator Harness for Layered Equivalence Gates

The change MUST include a Maven submodule `validator/` that operationalizes the 6-layer validation framework documented in `docs/20260423_plano_validacao.md`. Each layer MUST be runnable independently as a CLI subcommand and MUST emit a JSON report at a predictable path; gates MUST be defined as machine-checkable thresholds so that CI can block merges on regression.

The harness MUST include: (a) `BaksmaliDiffer` performing static hook diff between an `ajc`-instrumented APK and a `dexlib2`-instrumented APK from the same input + same descriptor, computing per-spec hook recall (Layer 1 gate: recall ≥ 0.95 in ≥90% of subset); (b) `BootValidator` exercising install + monkey-launch and parsing logcat for `VerifyError` and the `RVSEC` / `RVSEC-COV` event tags (Layer 2 gate: zero regressions vs ajc baseline); (c) `TraceComparator` running both pipelines against the three mandatory oracles (INV-INS-22: cryptoapp, hateitorrateit, and one multidex APK) and on a 30-APK subset, computing per-spec F1 + Cohen's kappa (Layer 3 gate: F1 ≥ 0.98, kappa ≥ 0.9 on every oracle AND on the aggregate of the 30-APK subset); (d) `BatchValidator` orchestrating the 945-task JCA-400 × 3 tools × 3 reps execution via Docker (Layer 4 gate: recovery_rate ≥ 90%, paired Wilcoxon signed-rank TOST non-inferiority lower-bound rejects per INV-INS-21 across all specs, equivalence holds in ≥80% of specs; thresholds file pre-registered before the run); (e) `CoverageValidator` measuring RVSEC-COV recall against ajc baseline (Layer 5 gate: recall ≥ 0.99, delta ≤ 1pp); (f) `FeatureMappingChecker` enforcing INV-INS-17.

#### Scenario: Layer 1 baksmali diff passes threshold

- **WHEN** `BaksmaliDiffer` is run over a 30-APK subset with `ajc` and `dexlib2` outputs both available
- **THEN** the resulting JSON report MUST contain a per-APK recall value
- **AND** at least 27 of the 30 APKs (≥90%) MUST have recall ≥ 0.95
- **AND** the CLI MUST exit with code 0

#### Scenario: Layer 4 large-scale gate fails on non-inferiority

- **WHEN** `BatchValidator` runs the 945-task batch and, for any spec, the paired Wilcoxon signed-rank lower-bound TOST fails to reject at α=0.05 against the pre-registered bound (Δ=2pp for `cov_method`, Δ=0.02 for F1, Δ=0.05 for κ), i.e., we cannot rule out that `dexlib2` median is more than Δ below `ajc` median
- **THEN** the CLI MUST exit with code 1
- **AND** the JSON report MUST identify the affected specs, the point estimate of the paired median difference, the bootstrapped 90% CI, both TOST p-values, and the Wilcoxon effect size `r`
- **AND** CI MUST block the Phase 6 substitution merge

#### Scenario: Layer 4 passes non-inferiority but not full equivalence

- **WHEN** `BatchValidator` runs the batch, the lower-bound TOST rejects for every spec (non-inferiority holds), but the upper-bound TOST rejects on fewer than 80% of specs (full equivalence does not hold globally)
- **THEN** the CLI MUST exit with code 0 (non-inferiority alone is sufficient for Phase-6 promotion per INV-INS-21)
- **AND** the JSON report MUST flag each spec where full equivalence did NOT hold, recording point estimate + CI + TOST p-values, so reviewers can see where `dexlib2` drifts positively against `ajc`

#### Scenario: FeatureMappingChecker fails on missing mapping

- **WHEN** `docs/AJ_CONSTRUCTIONS_INVENTORY.md` lists the construct `staticinitialization(T+)` as used in `generic_new` specifications, and the validator finds no test in `validator/src/test/` exercising the dexlib2 mapping for that construct, and `docs/LIMITATIONS.md` does not list it as out-of-scope
- **THEN** `FeatureMappingChecker` MUST exit with code 1
- **AND** the JSON report MUST identify the construct and the missing mapping

### Requirement: AspectJ-to-Dexlib2 Mapping Documentation

Three documents MUST be produced and kept current with the implementation: `docs/AJ_CONSTRUCTIONS_INVENTORY.md`, `docs/AJ_TO_DEXLIB2_MAPPING.md`, and `docs/LIMITATIONS.md`. These documents support paper-grade defense of the substitution and are mandatory artifacts of the change.

`AJ_CONSTRUCTIONS_INVENTORY.md` MUST enumerate every AspectJ construct (`call`, `execution`, `before`, `after`, `after returning`, `after throwing`, `target`, `args`, `!within`, `staticinitialization`, `if`, `thisJoinPoint`, `adviceexecution`, `around`, `cflow`, `cflowbelow`, `handler`, `get`, `set`, `initialization`, `preinitialization`) and for each one MUST list every `.mop` or `.aj` file under `rvsec/rvsec-mop/src/main/resources/{jca,generic,generic_new,aspect}/` that uses it, with file:line citations. The inventory MUST be regenerated programmatically by `validator/ConstructionInventoryGenerator` and the diff between regenerated and committed versions MUST be empty in CI.

`AJ_TO_DEXLIB2_MAPPING.md` MUST be a table with columns: AspectJ construct, dexlib2 component (Maven submodule + class), function (method name), smali pattern (bytecode shape emitted), and test reference (validator test file:line). Every row MUST have a corresponding test in `validator/`. INV-INS-17 enforces this.

`LIMITATIONS.md` MUST list every AspectJ construct that the dexlib2 weaver does not support. For each entry the document MUST give a rationale and the empirical evidence (from the inventory) of zero usage in the RVSEC specification corpus, justifying the out-of-scope decision. Currently expected entries: `around`, `cflow`, `cflowbelow`, `handler`, `get`, `set`, `initialization`, `preinitialization`.

#### Scenario: Inventory regeneration matches committed file

- **WHEN** `ConstructionInventoryGenerator` is run with `rvsec/rvsec-mop/src/main/resources/` as input
- **THEN** the generated `AJ_CONSTRUCTIONS_INVENTORY.md` MUST be byte-identical to the committed `docs/AJ_CONSTRUCTIONS_INVENTORY.md`
- **AND** if any spec file added a new construct usage since the last commit, the diff MUST identify the construct, the file, and the line

#### Scenario: Limitations document covers every gap

- **WHEN** `FeatureMappingChecker` is run after a new spec is added that uses `cflow()`
- **THEN** the check MUST fail because `cflow` is in `LIMITATIONS.md` but the new spec triggers it
- **AND** the report MUST direct the developer either to remove the `cflow` use, implement support, or move the construct out of the LIMITATIONS list with new evidence

### Requirement: Ground-Truth Oracle Diversity for Equivalence Claims

The claim that `dexlib2` is behaviorally equivalent to `ajc` on APKs that `ajc` handles correctly MUST be supported by at least three ground-truth oracle APKs exercising disjoint bytecode profiles, each with a hand-validated expected-event list committed to `validator/oracles/<name>-oracle.yaml` BEFORE Layer-3 or Layer-4 execution (so that oracles are not retrofitted to observed behavior). The three mandatory profiles are:

1. **Java-only, single DEX, pre-R8** — baseline profile. Canonical APK: `cryptoapp` with 8 known violations (see `docs/20260423_plano_validacao.md` §3.4 oracle table).
2. **Kotlin + R8-optimized, single or multi DEX** — the profile that motivates this change. Canonical APK: `hateitorrateit` (validated by the prototype at 100% method instrumentation, zero `VerifyError`).
3. **Multidex real-world APK from JCA-400** — exercises monitor-refs spillover and `classes.dex` + `classes2.dex` preservation (INV-INS-15). Concrete APK MUST be selected from JCA-400 and recorded in `validator/oracles/<name>-oracle.yaml` before Phase 5 execution.

Additional oracles MAY be added, but dropping below three is permitted only if `LIMITATIONS.md` carries an explicit entry naming the unverified profile and acknowledging the reviewer scrutiny that concession invites. A single oracle (cryptoapp alone) is insufficient for Phase-6 promotion.

#### Scenario: Layer 3 runs against three oracles

- **WHEN** `TraceComparator` is invoked for the Phase-5 ratification gate
- **THEN** at least three oracle YAMLs MUST be present in `validator/oracles/`
- **AND** each oracle MUST satisfy its expected event list with F1 ≥ 0.98 and κ ≥ 0.9 under both variants
- **AND** the report MUST name the three oracles and their bytecode profiles in its header

#### Scenario: Oracle added after execution

- **WHEN** a new oracle YAML is committed after a Layer-3 run already produced a report
- **THEN** the report MUST be regenerated with the new oracle before any gate ratification
- **AND** the commit message MUST cite the expected events and their provenance explicitly (source files, line numbers, or manual UI validation steps) — never "observed in run X"

#### Scenario: Multidex oracle profile unavailable

- **WHEN** the Phase-5 ratification gate is scheduled but no multidex oracle has been committed to `validator/oracles/`
- **THEN** the gate MUST be held
- **AND** either (a) a multidex oracle MUST be selected from JCA-400 and its expected-event list committed, OR (b) `docs/LIMITATIONS.md` MUST be updated with an entry "multidex profile unverified" naming the scrutiny this invites — no silent continuation is allowed

## MODIFIED Requirements

### Requirement: Monitor Generation from JavaMOP Specifications (FR01, NFR07)

The system MUST generate runtime verification monitors from MOP specification files through a coordinated pipeline of two tools: JavaMOP and RV-Monitor. JavaMOP reads `.mop` files and produces three artifacts: (a) `.aj` AspectJ files that define pointcuts and weaving advice for method interception, (b) `.rvm` intermediate files containing monitor state machine specifications, and (c) — when the patched JavaMOP is invoked with `--emit-descriptor` — `MultiSpec_*MonitorAspect.json` JSON descriptors mirroring the semantic content of each merged `.aj` (see new Requirement: JavaMOP Descriptor Format and Emission). RV-Monitor then reads the `.rvm` files and synthesizes `.java` monitor classes that implement the runtime verification logic.

The generation pipeline uses the `-merge` flag for both JavaMOP and RV-Monitor, which combines multiple specification files into unified merged artifacts. This is critical because merged monitors share a single aspect that intercepts all relevant methods, rather than creating individual aspects per specification that would multiply the runtime overhead.

The patched JavaMOP exposes the `--emit-descriptor` flag (commit pinned in this change's design document). When the flag is enabled in the generator's invocation, every merged aspect MUST receive a sibling JSON descriptor in `output_dir`. The descriptor emission MUST be additive: existing `.aj`, `.rvm`, and `.java` outputs MUST remain byte-identical to the unflagged invocation. `RuntimeVerificationGenerator` MUST enable `--emit-descriptor` by default to support both instrumentation variants from a single generation run.

A known bug in JavaMOP's `-d` (output directory) option causes `.rvm` files to remain in the source `mop_specs_dir` instead of being placed in the output directory. The generator MUST implement a workaround by explicitly moving `.rvm` files from `mop_specs_dir` to the output directory after JavaMOP execution.

After JavaMOP completes, custom AspectJ files from the `aspects_dir` MUST be copied into the output directory. This includes `Coverage.aj` (method coverage tracking) and `logging.aj` (additional logging). These custom aspects are woven alongside the generated monitor aspects during instrumentation under the `ajc` variant, and the `Coverage.aj` semantics are reimplemented natively in the `coverage-weaver` submodule for the `dexlib2` variant.

After RV-Monitor completes, all intermediate `.rvm` files MUST be deleted from the output directory, as they are no longer needed.

#### Scenario: Successful generation with a specification set and descriptor emission

- **WHEN** `mop_specs_dir` points to one of the specification-set directories under `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/` (`jca/` with 23 `.mop` files in the current corpus, or `generic/` / `generic_new/` with their own counts), and `javamop_bin` is the patched JavaMOP supporting `--emit-descriptor`, and `rvmonitor_bin` is a valid executable, and `aspects_dir` contains `coverage.aj` and `logging.aj`
- **THEN** `RuntimeVerificationGenerator.generate_monitors(output_dir)` MUST return `True`
- **AND** the output directory MUST contain at least one `.aj` file (merged aspects from JavaMOP)
- **AND** the output directory MUST contain at least one `MultiSpec_*MonitorAspect.json` file (descriptor emitted under the new flag)
- **AND** the output directory MUST contain at least one `.java` file (monitor classes from RV-Monitor)
- **AND** the output directory MUST contain `coverage.aj` (copied from aspects_dir)
- **AND** the output directory MUST NOT contain any `.rvm` files (intermediaries cleaned up)
- **AND** an experiment run uses exactly one set at a time — the caller selects which set via the Python wrapper's configuration, and descriptor emission is identical in structure across sets

#### Scenario: Generation with empty specification directory

- **WHEN** `mop_specs_dir` points to a directory containing zero `.mop` files
- **THEN** `RVGeneratorConfig` initialization MUST raise a `ConfigurationError`
- **AND** the error message MUST list the available specification sets (JCA, Generic)

#### Scenario: JavaMOP binary not found

- **WHEN** `javamop_bin` points to a path that does not exist
- **THEN** `RVGeneratorConfig` initialization MUST raise a `ConfigurationError` with message `"JavaMOP binary not found: {path}"`

#### Scenario: JavaMOP binary not executable

- **WHEN** `javamop_bin` points to a file that exists but lacks execute permissions
- **THEN** `RVGeneratorConfig` initialization MUST raise a `ConfigurationError` with message `"JavaMOP binary not executable: {path}"`

#### Scenario: RV-Monitor execution failure

- **WHEN** RV-Monitor returns a non-zero exit code during `.rvm` processing
- **THEN** `generate_monitors()` MUST catch the `CommandException`
- **AND** `generate_monitors()` MUST return `False`
- **AND** the error MUST be logged via `ErrorHandler.handle_error()` with context including `component`, `operation`, `output_dir`, and `mop_specs_dir`

#### Scenario: Descriptor emission disabled

- **WHEN** `RuntimeVerificationGenerator` is invoked with `emit_descriptor=False` (override of default)
- **THEN** the output directory MUST contain `.aj` and `.java` artifacts as before
- **AND** the output directory MUST NOT contain any `.json` descriptor files
- **AND** subsequent attempts to use `instrumentation_variant == "dexlib2"` MUST raise `MissingDescriptorError` (see DEX-Native Pipeline requirement)

#### Scenario: Generation summary after successful run with descriptor emission

- **WHEN** `generate_monitors()` has completed successfully in `output_dir` with descriptor emission enabled
- **THEN** `get_generation_summary(output_dir)` MUST return a dictionary with keys `output_directory`, `aspectj_files` (count), `monitor_classes` (count), `descriptors` (count), and `specs_processed` (containing `source_directory` and `count`)

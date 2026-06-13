# Delta Spec: Instrumentation Pipeline Hardening (gh54)

---

## STATUS: WITHDRAWN — NOT MERGED INTO BASE SPEC (2026-05-06)

Esta delta NÃO foi sincronizada para `openspec/specs/instrumentation/spec.md`. As três `### Requirement:` ADDED (Coverage Aspect Excludes Kotlin/Compose, DEX Weaver Emits check-cast, Instrumenter Rejects Pre-Instrumented Input) e os quatro invariantes (INV-INS-42, INV-INS-43, INV-INS-44, INV-INS-45) **não fazem parte do spec base**.

A change foi arquivada via `openspec archive --skip-specs`. Ver `proposal.md` (header de fechamento) e `design.md` (Closure findings) para a análise consolidada.

**Implicação para futura numeração**: INV-INS-42..45 ficam **livres** — uma futura change (e.g., gh55) pode reusá-los para outro propósito sem colisão. Isto é seguro porque (a) nenhum código foi escrito referenciando os números; (b) nenhum spec base foi atualizado; (c) o validator harness (`rvsec-instrumentation-dexlib2/validator/`) não tem testes registrados para 42-45.

Os blocos seguintes preservam o desenho original como registro histórico — não são normativos.

---

## Purpose

This delta extends the existing **Instrumentation Pipeline** capability with three additive requirements that close empirically-validated coverage gaps between the AJC and DEX variants. The base capability (`openspec/specs/instrumentation/spec.md`) is unchanged; this delta only adds new requirements that constrain how the pipeline behaves under specific failure modes uncovered by the `validacao_full` experiment (2026-05-05/06, 72 APKs, 851 tasks, 11 h wall).

The motivation is concrete and quantitative. In the baseline experiment the AJC variant produced `VerifyError` at runtime in 8 of 72 APKs (mean `cov_rv_method = 0 %` for the affected APKs, all in the NEW BROKEN R8/Compose category). The DEX variant produced `VerifyError` in 12 of 72 APKs (spread across OLD-CLEAN and NEW WORKS, triggered by register-alias mismatch at advice insertion sites). Both failure modes leave artefacts (stale `mop/` and `ajc$` references) inside `data/apks/` that, if re-instrumented, produce the contaminated double-instrumentation pattern documented in `feedback_verify_apk_clean_before_instrument.md` (3 h investigation cost in the smoke v1 incident). The three requirements added here close all three loops at the right architectural layer.

The first requirement (`Coverage Aspect Excludes Kotlin/Compose Synthetic Code`) extends the AJC pipeline's `Coverage.aj` resource so the generated coverage aspect skips weaving into Kotlin standard library, Coroutines, Compose runtime, and class-initialiser methods. These code paths produce stackmap-level edge cases that the existing `rvsec-frame-computer` cannot reconcile after AspectJ 1.9.25.1 weaving. The fix is a 4-line additive change to a build-time resource — fully reversible, no new tool dependency, and applies identically to every APK processed by the AJC variant.

The second requirement (`DEX Weaver Emits check-cast Before Typed Crypto Invokes`) extends the DEX variant's bytecode injection logic in `DexWeaver.java` so each injected `invoke` to a monitor method whose signature declares a typed crypto parameter (e.g. `SecureRandom`, `KeyPair`, `SecretKeySpec`) is preceded by a `check-cast` instruction that proves the source register's type to the ART verifier. This eliminates the register-alias `VerifyError` failure mode without modifying upstream rv-monitor templates. Runtime behaviour: if the source register actually holds a wrong type at execution, `ClassCastException` is thrown and absorbed by the existing rv-monitor advice try/catch — the class still loads, only the specific advice site no-ops for that call.

The third requirement (`Instrumenter Rejects Pre-Instrumented Input APKs`) adds a precondition to `Instrumenter.instrument_apks()` (the ABC contract in `rv-instrumentation-core`) that detects already-instrumented APKs at the input gate and rejects them with a typed `ContaminationError` carrying a diagnostic message. This applies uniformly to both variants via inheritance and replaces the prior implicit assumption that callers pass clean APKs. It does NOT prevent intentional re-runs over an already-instrumented batch (callers must pass clean originals from the source dataset); the check is conservative (requires both `Lmop/` AND `ajc$` references to fire) to avoid false positives on third-party packages that happen to share the `mop` name.

All three requirements are enforced at the variant boundary (Java side for A.AJC and A.DEX, Python ABC for B1) and require no API changes in `rv-experiment`, `rv-platform`, `rv-coverage`, or any downstream consumer. The acceptance gate is empirical: re-running `validacao_full` with the fixes in place must reduce the dex-ajc mean `cov_rv_method` gap below 5 pp in each of the three APK categories (OLD-CLEAN, NEW BROKEN, NEW WORKS); the pre-fix baseline numbers are recorded in `out/validacao_full_consolidated/REPORT.md` and the post-fix numbers will be appended to that file.

## Data Contracts

### Input
- `apk_path: pathlib.Path` — absolute path to a candidate input APK supplied by `rv-experiment.PreProcessor` to `Instrumenter.instrument_apks()`. Must be a regular file readable by the current process. Source: caller (rv-experiment).
- `Coverage.aj` resource — AspectJ source file at `rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj`, packaged into `rvsec-mop` JAR and copied to the monitor output directory by `RuntimeVerificationGenerator`. Source: build artefact.

### Output
- For B1: `None` on a clean APK (validation passes), or `ContaminationError` raised on a contaminated APK (validation fails). Destination: `instrument_apks()` loop, which records the failed APK in `instrument_errors.json` with `phase=validation` and continues with the next APK.
- For A.AJC: woven `.class` files in the AJC output directory, with no `Coverage.aj` advice in any class matching `kotlin..*`, `kotlinx..*`, `androidx.compose..*`, or any method named `<clinit>`. Destination: the `d8` step that consumes the woven classes.
- For A.DEX: instrumented `.dex` files in which every injected `invoke-static` to a `mop/MultiSpec_*MonitorAspect` method whose first non-receiver parameter declares a typed crypto reference is preceded by `check-cast vN, L<type>;` reading from the same source register. Destination: the `apksigner` step.

### Side-Effects
- **[Filesystem (B1)]**: the contaminated APK file is NOT modified. The pipeline records the rejection in `instrument_errors.json` (existing artefact) under the new `phase` value `validation`.
- **[Filesystem (A.AJC)]**: the AJC output directory contains `Coverage.aj` with the new exclusions baked in. No additional files are created or removed.
- **[APK bytecode (A.DEX)]**: each instrumented method that fires monitor advice grows by one DEX instruction (`check-cast`) per advice site. Total APK size growth measured in KB for typical apps; APK manifest unchanged.

### Error
- `ContaminationError(apk_path: Path, found_lmop_refs: int, found_ajc_refs: int)` — new exception in `rv_instrumentation_core.errors`, raised by `Instrumenter.validate_input_apk()` when both `Lmop/` and `ajc$` references are detected in any `classes*.dex` of the input APK. Message format: `"APK {apk_path.name} appears already instrumented (found {found_lmop_refs} Lmop/ and {found_ajc_refs} ajc$ references). Re-instrumentation is not supported; use a clean original APK."`

## Invariants

- **INV-INS-42**: After A.AJC, the compiled `Coverage.aj` aspect MUST NOT match any joinpoint whose declaring class FQN starts with `kotlin.`, `kotlinx.`, or `androidx.compose.`, AND MUST NOT match any joinpoint whose method name is `<clinit>`. Enforced by the `excludedPackages()` pointcut at compile time (ajc resolves the patterns when building the merged aspect).
- **INV-INS-43**: After A.DEX, every instrumented method in the output APK that contains an injected `invoke` to a monitor method declaring a typed crypto parameter (from the static allow-list of 20 crypto types) MUST contain a `check-cast vSourceReg, L<expectedType>;` instruction immediately preceding the `invoke`, where `vSourceReg` is the same register whose value is passed as the first non-receiver argument.
- **INV-INS-44**: `Instrumenter.instrument_apks()` MUST invoke `validate_input_apk(apk_path)` for every APK in the batch BEFORE any decompile, weaving, or DEX manipulation step is performed for that APK. The check MUST NOT be opt-out via configuration in this change. A failed validation MUST NOT abort the batch — it MUST be recorded in `instrument_errors.json` and the loop MUST continue with the next APK.
- **INV-INS-45**: After A.AJC exclusions are applied, `Coverage.aj` recall on **app-package methods** (methods whose declaring class FQN matches the detected `code_package`) MUST remain ≥ 0.99 against the pre-fix baseline. The exclusions target only `kotlin.*`, `kotlinx.*`, `androidx.compose.*`, and class initialisers — these are LIBRARY/SYNTHETIC code paths, not app-level methods. Any drop in app-package RVSEC-COV recall caused by INV-INS-42 indicates an over-broad exclusion pattern and MUST be tightened. Validation runs the existing `validator-cli layer5` harness (`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/validator/`) on the cryptoapp oracle (`oracles/cryptoapp-oracle.yaml`) post-fix and asserts recall ≥ 0.99.

## ADDED Requirements

### Requirement: Coverage Aspect Excludes Kotlin/Compose Synthetic Code (FR01, gh54)

The `Coverage.aj` aspect MUST exclude four additional joinpoint patterns from its weave to prevent `VerifyError` failures in R8/Compose-obfuscated apps. The `excludedPackages()` pointcut MUST extend to cover (a) `within(kotlin..*)` to skip Kotlin standard library calls and synthetic accessor classes generated by the Kotlin compiler, (b) `within(kotlinx..*)` to skip Kotlinx Coroutines runtime infrastructure, (c) `within(androidx.compose..*)` to skip the entire Jetpack Compose runtime including its lambda implementations, and (d) `execution(* *<clinit>(..))` to skip class initialiser methods (which trigger the most common Frame Computer failure mode in obfuscated classes).

These exclusions MUST be implemented as additive clauses in the existing `excludedPackages()` definition in `rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj`, NOT as a new pointcut. The exclusions are unconditional — there is no runtime config flag, env var, or per-APK override that re-enables weaving in these packages. Reverting requires removing the clauses from the source file.

#### Scenario: AJC instrumentation of an R8-obfuscated Compose app

- **WHEN** the AJC variant processes `io.github.deprec8.enigmadroid_16.apk` (a known NEW BROKEN APK with R8-obfuscated Compose UI) and runs `ajc` weaving with the updated `Coverage.aj` resource
- **THEN** the resulting instrumented APK MUST be installable via `adb install` on an Android API 29 emulator
- **AND** running the APK with `ape@300` for 3 reps MUST produce `cov_rv_method > 0%` (no longer 0%)
- **AND** the trace files MUST contain zero `[APE] // Short Msg: java.lang.VerifyError` entries with `Verifier rejected class r9.s` (the previously-failing class)

#### Scenario: AJC instrumentation of a non-Compose app

- **WHEN** the AJC variant processes `cryptoapp.apk` (a known clean Java app with no Kotlin/Compose dependencies)
- **THEN** the new exclusions MUST have NO observable effect — the post-fix coverage MUST be within ±2 pp of the baseline (`mean cov_rv_method = 100% per validacao_v2`)
- **AND** the same 4 violations of `MessageDigestSpec` SHA-1 in `MessageDigestUtil.hash` MUST be captured

#### Scenario: Class initialiser advice is suppressed

- **WHEN** the AJC variant processes any APK containing classes with non-trivial `<clinit>` methods
- **THEN** the woven `.class` files MUST NOT contain coverage advice insertions in `<clinit>` methods
- **AND** the `RVSEC-COV` log emitted at runtime MUST NOT include any signature whose method name is `<clinit>`

### Requirement: DEX Weaver Emits check-cast Before Typed Crypto Invokes (FR02, gh54)

The DEX variant's bytecode weaver (`DexWeaver.java` in `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator/`) MUST emit a `check-cast vSourceReg, L<expectedType>;` instruction immediately before each injected `invoke` whose target is a `mop/MultiSpec_*MonitorAspect` method declaring a typed crypto reference parameter. The allow-list of crypto types MUST include at minimum: `SecureRandom`, `KeyPair`, `KeyPairGenerator`, `KeyGenerator`, `Cipher`, `MessageDigest`, `Mac`, `KeyStore`, `SSLContext`, `TrustManagerFactory`, `KeyManagerFactory`, `Signature`, `SecretKey`, `SecretKeySpec`, `IvParameterSpec`, `PBEKeySpec`, `PBEParameterSpec`, `GCMParameterSpec`, `DHGenParameterSpec`, `IHMACParameterSpec`.

The `check-cast` MUST read from and write back to the same source register that the `invoke` reads as its first non-receiver argument; this guarantees the ART verifier sees a register provably holding the expected type at the `invoke` site. If the source register at runtime actually holds a different type, `ClassCastException` is thrown — the existing rv-monitor advice template wraps the dispatch in try/catch, so the exception is absorbed without crashing the app or interrupting the surrounding application code.

The emission is unconditional for the listed types; no register liveness analysis is performed. This is intentional: the `check-cast` overhead is a single DEX instruction per advice site, and the cast is elided by ART's JIT when the type is statically narrowable. There is no opt-out flag.

#### Scenario: DEX instrumentation of a method with String in the source register

- **WHEN** the DEX variant processes a method that calls `SecureRandom.nextBytes(byte[])` where the `SecureRandom` instance comes from a register that the dexlib2 type analysis classifies as `String` (the previously-failing pattern in `org.secuso.privacyfriendlyludo_5.apk`)
- **THEN** the generated DEX MUST contain `check-cast v0, Ljava/security/SecureRandom;` immediately before the `invoke-virtual {v0, ...}, Lmop/MultiSpec_*MonitorAspect;->ajc$...$secure_random$...:(Ljava/security/SecureRandom;...)V`
- **AND** the resulting APK MUST install on an Android API 29 emulator without `INSTALL_FAILED_VERIFICATION_FAILURE`
- **AND** running the APK at runtime MUST NOT produce `[APE] // Short Msg: java.lang.VerifyError` for the affected method's declaring class

#### Scenario: DEX instrumentation of a method with the correct type already in the register

- **WHEN** the DEX variant processes a method that calls `SecureRandom.nextBytes(byte[])` where the source register already statically holds `Ljava/security/SecureRandom;`
- **THEN** the `check-cast` MUST still be emitted (the design is unconditional)
- **AND** ART's JIT MUST elide the runtime check (no measurable overhead)

#### Scenario: Type mismatch at runtime is absorbed gracefully

- **WHEN** the DEX-instrumented APK runs and a `check-cast` fails (the source register actually contains a different reference type than declared by the monitor signature)
- **THEN** `ClassCastException` MUST be thrown at the `check-cast` site
- **AND** the existing rv-monitor advice try/catch MUST absorb the exception
- **AND** the application MUST continue executing past the failed advice site without crash
- **AND** no `RVSEC` violation event is emitted for that specific call (the advice no-ops)

### Requirement: Instrumenter Rejects Pre-Instrumented Input APKs (FR02, gh54)

The `Instrumenter` ABC in `rv-instrumentation-core` MUST expose a default method `validate_input_apk(apk_path: Path) -> None` that detects and rejects APKs whose `classes*.dex` files contain references to instrumentation runtime classes from a previous run. Detection MUST require the conjunction of two signals: at least one `Lmop/` class descriptor reference AND at least one `ajc$` synthetic method reference within the same APK. Both signals together strongly indicate prior instrumentation; either alone is insufficient (third-party apps may legitimately use the package name `mop` or contain unrelated AspectJ artefacts).

The validation MUST be invoked from `Instrumenter.instrument_apks()` for every APK in the batch BEFORE any decompile, weave, or DEX manipulation step is executed for that APK. A `ContaminationError` raised by validation MUST NOT abort the batch — it MUST be recorded in the existing `instrument_errors.json` artefact under a new `phase` value of `validation` and the loop MUST continue with the next APK.

The default implementation MUST use `androguard` to read the APK's DEX entries and scan for the two signal patterns. Both variant subclasses (`AjcInstrumentation`, `DexlibInstrumentation`) inherit this default implementation; neither is required to override it. The check is mandatory for both variants.

#### Scenario: Contaminated APK is rejected with diagnostic message

- **WHEN** `Instrumenter.instrument_apks()` is called with `apk_paths` containing `data/apks/com.aptasystems.dicewarepasswordgenerator_8.apk` (a known contaminated APK from the smoke v1 incident, containing 65 `Lmop/` references and many `ajc$` synthetics)
- **THEN** `validate_input_apk()` MUST raise `ContaminationError` with message containing the substring `"appears already instrumented"` AND the substring `"65"` (the actual count of `Lmop/` references)
- **AND** the APK MUST NOT be decompiled, weaved, or DEXed
- **AND** the rejection MUST appear in `instrument_errors.json` with key `com.aptasystems.dicewarepasswordgenerator_8.apk` and value containing `phase: validation`
- **AND** the next APK in the batch MUST be processed normally (the loop continues)

#### Scenario: Clean APK passes validation

- **WHEN** `Instrumenter.instrument_apks()` is called with `apk_paths` containing `cryptoapp.apk` (a known clean APK with zero `Lmop/` and zero `ajc$` references)
- **THEN** `validate_input_apk()` MUST return `None` without raising
- **AND** the APK MUST proceed through the normal weave + DEX + sign pipeline
- **AND** no `validation` entry MUST appear in `instrument_errors.json` for this APK

#### Scenario: APK with only one signal type is accepted

- **WHEN** `validate_input_apk()` is called with an APK that contains references to a third-party class named `mop.SomeUnrelatedClass` (one signal: `Lmop/` present) but no `ajc$` synthetics (second signal: absent)
- **THEN** the validation MUST return `None` (both signals are required for rejection)
- **AND** the APK MUST proceed to the weave step

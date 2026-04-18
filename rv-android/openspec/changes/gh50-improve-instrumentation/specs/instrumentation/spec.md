## Purpose

Delta spec for the rv-instrumentation pipeline weaving configuration. This change adds configurable class exclusion from AspectJ weaving via `-xmlConfigured` + `aop.xml`, adds `--no-desugaring` to d8, and adds `-proceedOnError` to ajc, significantly improving instrumentation success rate on modern APKs.

## ADDED Invariants

- **INV-INS-13**: The d8 command MUST include the `--no-desugaring` flag. Since `--min-api 26` provides native Java 8 support, desugaring is unnecessary and causes conflicts with pre-desugared classes (j$ prefix) from the original APK build.

- **INV-INS-14**: The ajc command MUST include the `-proceedOnError` flag. This allows partial weaving to continue when individual classes cause compilation errors, producing woven output for all successfully processed classes instead of aborting the entire APK.

- **INV-INS-15**: When a `weaving_excludes.yaml` configuration file is available, the instrumentation pipeline MUST generate a `META-INF/aop.xml` file with `<exclude within="..."/>` entries for each pattern, and pass the `-xmlConfigured` flag to ajc. This prevents weaving into library packages whose bytecode is incompatible with AspectJ's stack frame recomputation.

- **INV-INS-16**: The default `weaving_excludes.yaml` MUST include at least the following patterns: `com.google..*`, `androidx..*`, `kotlin..*`, `kotlinx..*`, `android.support..*`, `j$..*`, `org.apache..*`, `okhttp3..*`, `okio..*`. These patterns cover the library packages that cause the majority of d8 compilation failures after weaving.

## MODIFIED Requirements

### Requirement: APK Instrumentation with Monitors (FR02)

The system MUST instrument Android APKs with generated runtime verification monitors through a multi-phase pipeline. The pipeline transforms a standard APK into a monitored APK by: (1) decompiling DEX bytecode to Java classes, (2) injecting monitor artifacts, (3) weaving aspects via AspectJ, (4) merging runtime dependencies, (5) recompiling to DEX, and (6) signing the APK.

The instrumentation pipeline relies on several external tools that MUST be available:
- **dex2jar** (`d2j-dex2jar.sh`): Converts APK DEX bytecode to JAR format. If the conversion produces an exception file, the pipeline MUST raise a `CommandException`.
- **ajc (AspectJ Compiler)**: Weaves monitor pointcuts into application bytecode. Uses Java 1.8 source compatibility (`-source 1.8`), suppresses lint warnings (`-Xlint:ignore`), proceeds on class-level errors (`-proceedOnError`), and optionally uses `-xmlConfigured` with a generated `aop.xml` for class exclusion. The classpath MUST include `android.jar` and all runtime verification JARs from `lib_tmp_dir`.
- **d8 (Android DEX compiler)**: Converts the instrumented JAR back to DEX format. Uses `--release` mode with `--min-api 26`, `--no-desugaring`, and `--lib android.jar`.
- **jarsigner**: Signs the APK with the configured keystore using `SHA256withRSA` signature algorithm and `SHA-256` digest algorithm.
- **Maven**: Resolves and downloads runtime dependencies (`rv-monitor-rt.jar`, `rvsec-core.jar`, `rvsec-logger-logcat.jar`, `aspectjrt.jar`) into `lib_tmp_dir`.

Before AspectJ weaving, the pipeline MUST check for a `weaving_excludes.yaml` configuration. If present, it MUST generate an `aop.xml` file in the temporary directory with `<exclude within="..."/>` entries for each pattern and pass `-xmlConfigured` to the ajc command. If absent, ajc runs without class exclusion (current behavior preserved).

Before instrumentation begins, `prepare_instrumentation()` MUST clean temporary directories from previous runs and execute Maven dependency resolution. After each APK, temporary directories (`tmp_dir`, `rvm_tmp_dir`) MUST be cleaned. After the entire batch, `lib_tmp_dir` MUST be cleaned.

The pipeline supports both single APK instrumentation (`instrument()`) and batch instrumentation (`instrument_apks()`). Batch instrumentation provides error isolation: if one APK fails, processing continues with the next APK. All errors are collected in `InstrumentationResults.errors` and saved to `instrument_errors.json`.

The following pipeline methods MUST use `@ErrorHandler.handle_errors` with `reraise=True` to ensure exceptions propagate to the batch loop: `instrument()`, `__include_generated_monitors()`, `__weave_monitors()`, `__create_apk()`, `__sign_apk()`, `__merge_support_classes()`. The batch loop (`instrument_apks()`) MUST use `reraise=False` (default) to continue processing after per-APK failures.

#### Scenario: Successful instrumentation with d8 --no-desugaring

- **WHEN** an APK is instrumented and the d8 compilation step runs
- **THEN** the d8 command MUST include `--no-desugaring` alongside `--release`, `--min-api 26`, and `--lib android.jar`
- **AND** APKs that previously failed with "Merging DEX file containing classes with prefix 'j$.'" MUST now compile successfully

#### Scenario: ajc proceeds on class-level errors

- **WHEN** ajc encounters a class with incompatible bytecode (e.g., invalid stack map frames) during weaving
- **THEN** ajc MUST continue processing remaining classes instead of aborting (due to `-proceedOnError`)
- **AND** the problematic class MUST be included in the output with its original bytecode (not woven)
- **AND** all other classes MUST be woven normally

#### Scenario: Weaving with class exclusion via aop.xml

- **WHEN** `weaving_excludes.yaml` exists with patterns `["com.google..*", "androidx..*", "kotlin..*"]`
- **THEN** the pipeline MUST generate `aop.xml` in the temporary directory containing:
  ```xml
  <aspectj>
    <weaver>
      <exclude within="com.google..*"/>
      <exclude within="androidx..*"/>
      <exclude within="kotlin..*"/>
    </weaver>
  </aspectj>
  ```
- **AND** ajc MUST be invoked with `-xmlConfigured` flag
- **AND** classes matching excluded patterns MUST NOT receive woven advice
- **AND** classes NOT matching excluded patterns MUST be woven normally

#### Scenario: No weaving_excludes.yaml (backward compatible)

- **WHEN** `weaving_excludes.yaml` is not found in the assets directory
- **THEN** ajc MUST be invoked WITHOUT `-xmlConfigured` flag
- **AND** weaving behavior MUST be identical to previous versions (all classes in `-inpath` are woven)

#### Scenario: Successful single APK instrumentation

- **WHEN** an APK at `app.path` exists and is a valid `.apk` file, and `monitor_output_dir` contains `.aj` and `.java` files, and all external tools are available
- **THEN** `RVInstrumentation.instrument(app, result_dir)` MUST produce a signed APK at `{instrumented_dir}/{app.name}`
- **AND** the instrumented APK hash MUST differ from the original APK hash
- **AND** temporary directories (`tmp_dir`, `rvm_tmp_dir`) MUST be cleaned after completion

#### Scenario: Pipeline phase failure with accurate phase reporting

- **WHEN** `jarsigner` returns a non-zero exit code during APK signing
- **THEN** the `CommandException` MUST propagate from `__sign_apk()` through `__create_apk()` and `instrument()` decorators (all with `reraise=True`)
- **AND** the exception MUST carry `_error_phase == "apk_signing"` (set by the innermost decorator)
- **AND** the batch loop MUST record the error in `InstrumentationResults.errors` with `phase="apk_signing"` and `tool="jarsigner"`

#### Scenario: Batch instrumentation with mixed results

- **WHEN** `instrument_apks()` processes 10 APKs and 3 fail during different pipeline phases (aspect_weaving, apk_creation, apk_signing)
- **THEN** `InstrumentationResults.success_count` MUST be 7
- **AND** `InstrumentationResults.total_count` MUST be 10
- **AND** `InstrumentationResults.success_rate` MUST be 70.0
- **AND** `InstrumentationResults.errors` MUST contain 3 entries, each with `code`, `tool`, `message`, and `phase` matching the actual pipeline phase where the failure occurred
- **AND** `instrument_errors.json` MUST be written to `results_dir` with the serialized error models

#### Scenario: Skip existing instrumented APK

- **WHEN** an instrumented APK already exists at `{result_dir}/{app.name}` and `force_instrumentation` is `False`
- **THEN** the pipeline MUST skip this APK without error
- **AND** a log message "Skipping already instrumented APK" MUST be emitted

#### Scenario: dex2jar conversion failure with phase from outer decorator

- **WHEN** dex2jar produces an exception file during DEX-to-JAR conversion
- **THEN** a `CommandException` MUST be raised with tool name `"dex2jar"`
- **AND** the error MUST be recorded in `InstrumentationResults.errors` with `phase="single_apk_instrumentation"` and `tool="dex2jar"`

#### Scenario: Instrumentation verification detects unchanged APK

- **WHEN** the instrumented APK file hash equals the original APK file hash
- **THEN** `check_if_instrumented()` MUST raise a `CommandException` with tool `"instrumentation_verification"` and message `"APK {name} was not actually instrumented - hashes match original"`

#### Scenario: Maven dependency resolution failure

- **WHEN** Maven (`mvn clean compile`) fails during `prepare_instrumentation()`
- **THEN** a `CommandException` MUST be raised with tool name `"maven"`
- **AND** `instrument_apks()` MUST record the error in `InstrumentationResults.errors` with key `"setup_error"` and `phase="preparation"`
- **AND** processing MUST NOT continue to individual APK instrumentation

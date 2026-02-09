# Specification: Instrumentation Pipeline

## Purpose

The Instrumentation Pipeline domain encompasses the complete transformation of MOP (Monitoring-Oriented Programming) specifications into runtime verification monitors and their subsequent weaving into Android APK artifacts. This domain is implemented by two modules -- **rv-monitor-generator** and **rv-instrumentation** -- which together form the first phase of the RV-Android experiment workflow. Without this pipeline, no runtime verification is possible: uninstrumented APKs cannot produce `RVSEC-COV` coverage events or `RVSEC` violation events during execution.

### Problem Context

Runtime verification detects API usage violations by observing method call sequences at runtime. For this to work, three conditions MUST be met:

1. **Monitors MUST exist**: Formal MOP specifications MUST be compiled into executable AspectJ aspects and Java monitor classes that encode the expected API usage patterns.
2. **Monitors MUST be woven into the APK**: The generated aspects MUST be integrated into the APK's bytecode so that method calls trigger monitor state transitions at runtime.
3. **Coverage tracking MUST be present**: A `Coverage.aj` aspect MUST be woven alongside the monitors so that every method execution is logged via `Log.v("RVSEC-COV", signature)`, enabling real-time coverage measurement.

If any of these conditions is not met, the experiment executes on uninstrumented APKs, coverage reads 0%, and no violations are detected.

### Pipeline Architecture

The instrumentation pipeline is a linear, six-stage process that transforms DEX bytecode into instrumented DEX bytecode. The pipeline was inspired by the original **RV-Android** project by Daian et al. (Runtime Verification Inc., 2015), which implemented the same core sequence as a bash script (`instrument_apk.sh`). As research requirements grew -- multiple specification sets, batch processing, static analysis integration, experiment orchestration -- the pipeline was reimplemented in Python while preserving the same fundamental stages.

```
MOP Specifications (.mop files)
         |
         v
  [rv-monitor-generator]
         |
    (1) JavaMOP: .mop --> .aj (AspectJ aspects) + .rvm (intermediate specs)
    (2) Copy custom aspects: Coverage.aj, logging.aj --> output
    (3) RV-Monitor: .rvm --> .java (monitor classes)
    (4) Clean up: delete .rvm intermediaries
         |
         v
  Monitor Artifacts (.aj + .java files)
         |
         v
  [rv-instrumentation]
         |
    (5) Prepare: Maven dependency resolution (rv-monitor-rt.jar, aspectjrt.jar,
                 rvsec-core.jar, rvsec-logger-logcat.jar)
         |
    Per APK:
    (6)  dex2jar: APK DEX --> JAR (Java bytecode)
    (7)  Monitor Integration: copy .aj + .java into tmp/
    (8)  AspectJ Weaving: ajc compiles aspects into bytecode
    (9)  Dependency Merge: extract and merge runtime libraries
    (10) d8 Compiler: JAR --> DEX (Android bytecode)
    (11) APK Assembly: replace classes.dex in APK copy
    (12) APK Signing: dex2jar sign + jarsigner with keystore
    (13) Verification: compare hash(original) != hash(instrumented)
         |
         v
  Instrumented APK (signed, ready for deployment)
```

### Module Responsibilities

| Module | Responsibility | Key Class | Source Directory |
|--------|---------------|-----------|-----------------|
| rv-monitor-generator | Transform MOP specs into monitor artifacts | `RuntimeVerificationGenerator` | `modules/rv-monitor-generator/src/rv_monitor_generator/` |
| rv-instrumentation | Weave monitors into APK bytecode | `RVInstrumentation` | `modules/rv-instrumentation/src/rv_instrumentation/` |

### Data Models

```
RVGeneratorConfig (Pydantic BaseValidatedModel):
  javamop_bin: Optional[str]     # Path to JavaMOP binary executable
  rvmonitor_bin: Optional[str]   # Path to RV-Monitor binary executable
  mop_specs_dir: Optional[str]   # Directory containing .mop specification files
  aspects_dir: Optional[str]     # Directory containing custom .aj files (Coverage.aj, logging.aj)
  rvsec_root: Optional[str]      # RVSEC installation root for auto-discovery

RuntimeVerificationGenerator (Pydantic BaseValidatedModel):
  config: RVGeneratorConfig      # Validated configuration
  _logger: Logger                # Structured logging
  _error_handler: ErrorHandler   # Centralized error handling

RVInstrumentationConfig (Pydantic BaseValidatedModel):
  rvsec_root: Optional[str]          # RVSEC installation root
  monitor_output_dir: Optional[str]  # Directory with .aj + .java monitor artifacts
  android_jar_path: Optional[str]    # Android SDK android.jar for classpath
  android_platforms_dir: Optional[str] # Android SDK platforms directory
  instrumented_dir: Optional[str]    # Output directory for signed instrumented APKs
  working_dir: Optional[str]         # Base working directory
  tmp_dir: Optional[str]             # Temporary processing directory
  lib_tmp_dir: Optional[str]         # Library extraction directory
  rvm_tmp_dir: Optional[str]         # RV-Monitor processing directory
  keystore_file: Optional[str]       # Keystore for APK signing (defaults to bundled)
  keystore_password: Optional[str]   # Keystore password (default: "password")
  dex2jar_home: Optional[str]        # dex2jar tool suite directory

Dex2jarTools (Pydantic BaseValidatedModel):
  dex2jar: str                       # Path to d2j-dex2jar.sh
  asm_verify: str                    # Path to d2j-asm-verify.sh
  apk_sign: str                      # Path to d2j-apk-sign.sh

InstrumentationResults (Pydantic BaseValidatedModel):
  errors: Dict[str, InstrumentationError]  # Errors keyed by APK name
  success_count: int                        # Number of successfully instrumented APKs
  total_count: int                          # Total APKs processed
  success_rate: float                       # Computed: (success_count / total_count) * 100

InstrumentationError (Pydantic BaseValidatedModel):
  code: int             # Numeric error code
  tool: Optional[str]   # Name of tool that failed (dex2jar, ajc, d8, jarsigner)
  message: str          # Human-readable description
  phase: str            # Pipeline phase (decompilation, weaving, compilation, signing)
```

### Specification Sets

The pipeline processes three distinct sets of MOP specifications. Each set is used independently per experiment -- sets are NEVER mixed within a single instrumentation run. The `specification_set` parameter in `ExperimentConfig` determines which set is used. All specification sets reside under `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/`.

| Set | Directory | Count | Origin | Purpose |
|-----|-----------|-------|--------|---------|
| JCA | `jca/` | 23 | Translated from 23 CrySL rules via TDD | Detect cryptographic API misuses (Cipher, MessageDigest, SSLContext, etc.) |
| Generic (FSM) | `generic/` | 118 | JavaMOP specification database | Detect general API pattern violations (Iterator, Collections, Streams) |
| Generic (new) | `generic_new/` | 27 | Curated subset with descriptive names | Detect general API violations (Closeable, Map, InputStream patterns) |

The JCA specifications were derived from 23 CrySL rules previously validated by cryptography experts. The translation followed a TDD approach, with 31 JUnit test classes and 200+ test methods from CogniCrypt serving as the test oracle.

### Coverage.aj Aspect

In addition to MOP monitor aspects, a custom `Coverage.aj` aspect is woven into every instrumented APK. This aspect is located in the aspects directory (`$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/aspect/coverage.aj`) and is copied into the monitor output directory by rv-monitor-generator during step (2) of the generation pipeline.

The Coverage.aj aspect:
- Intercepts all method executions (excluding system packages: `java.*`, `android.*`, `dalvik.*`)
- Logs unique method signatures via `Log.v("RVSEC-COV", signature)` on Android logcat
- Uses a `HashSet` for deduplication, ensuring each signature is logged only once per execution
- Signature format: `<className: returnType methodName(params)>`

This is the mechanism by which the downstream rv-coverage module tracks method coverage in real-time.

### Configuration Priority System

Both `RVGeneratorConfig` and `RVInstrumentationConfig` implement the same priority-based path resolution strategy:

1. **Explicit individual paths** (highest priority): All required paths provided directly
2. **Explicit `rvsec_root`**: Automatic path discovery from RVSEC installation layout
3. **`RVSEC_HOME` environment variable**: Fallback to environment-based discovery
4. **Configuration error**: If no valid source is available, a `ConfigurationError` is raised

The standard RVSEC directory layout assumed for auto-discovery:

```
$RVSEC_HOME/
  javamop/bin/javamop                              # JavaMOP binary
  rv-monitor/bin/rv-monitor                        # RV-Monitor binary
  rvsec/rvsec-mop/src/main/resources/
    jca/                                           # JCA specifications (.mop)
    generic/                                       # Generic FSM specifications (.mop)
    generic_new/                                   # Curated generic specifications (.mop)
    aspect/                                        # Custom aspects
      coverage.aj                                  # Method coverage tracking
      logging.aj                                   # Additional logging aspects
  rv-android/                                      # Working directory for instrumentation
    lib/dex2jar/                                   # dex2jar tool suite
    assets/keystore.jks                            # Development keystore
```

### Integration with Experiment Orchestration

The `PreProcessor` component in rv-experiment orchestrates the instrumentation pipeline during Phase 1 (pre-processing) of the three-phase experiment workflow:

```
PreProcessor.process(generate_monitors, instrument, static_analysis)
  |
  |--> _generate_monitors()
  |      ExperimentConfig.get_monitored_operations_config() --> RVGeneratorConfig
  |      RuntimeVerificationGenerator(config).generate_monitors(output_dir)
  |
  |--> _instrument_apks()
  |      ExperimentConfig.get_rv_instrumentation_config() --> RVInstrumentationConfig
  |      RVInstrumentation(config).instrument_apks(apks_dir, results_dir)
  |
  |--> _run_static_analysis()
         (separate domain -- not covered in this spec)
```

Both methods use Just-in-Time (JIT) configuration: `ExperimentConfig` creates `RVGeneratorConfig` and `RVInstrumentationConfig` instances only when the corresponding pre-processing step is actually invoked.

### Relationships with Other Domains

| Domain | Relationship | Contract |
|--------|-------------|----------|
| **rv-experiment** | Orchestrator | Calls `generate_monitors()` and `instrument_apks()` via JIT configs from `ExperimentConfig` |
| **rv-coverage** | Consumer | Parses `RVSEC-COV` logcat entries produced by woven Coverage.aj aspect |
| **rv-platform** | Consumer | Executes instrumented APKs on emulator; captures logcat with monitor output |
| **rv-static-analysis** | Sibling | Runs on same APKs during pre-processing; independent of instrumentation |
| **rv-android-core** | Foundation | Provides `Command`, `ErrorHandler`, `LoggingManager`, `BaseValidatedModel`, `App`, constants |

### Success Rate Context

In the ICST study, the instrumentation pipeline achieved a **34.6% success rate** (193 of 557 APKs successfully instrumented). Common failure causes include:

- dex2jar conversion failures on multidex APKs or obfuscated code
- AspectJ weaving errors due to unsupported bytecode patterns
- d8 compilation failures due to classpath issues or unsupported API levels
- DEX method count limits exceeded after monitor injection

The 188 APKs used in the final dataset were the subset of 193 that also had REACH-reachable MOP methods. Improving the instrumentation success rate is listed as a planned improvement (PRD Section 12.2).

### External Tool Dependencies

| Tool | Version Constraint | Purpose | Configuration |
|------|-------------------|---------|---------------|
| JavaMOP | Java 8+ required | Process .mop files, generate .aj and .rvm files | `javamop_bin` in `RVGeneratorConfig` |
| RV-Monitor | Java 8+ required | Transform .rvm files into .java monitor classes | `rvmonitor_bin` in `RVGeneratorConfig` |
| dex2jar | 2.x | Convert APK DEX bytecode to Java JAR | `dex2jar_home` in `RVInstrumentationConfig` |
| ajc (AspectJ) | System PATH | Weave aspects into Java bytecode | System PATH lookup |
| d8 | Android SDK | Convert JAR back to DEX format | `ANDROID_HOME` env var |
| jarsigner | JDK | Sign instrumented APK with keystore | System PATH lookup |
| Maven | System PATH | Resolve runtime dependencies (rv-monitor-rt, aspectjrt, etc.) | System PATH lookup |
| zip | System PATH | APK manipulation (DEX replacement, META-INF cleanup) | System PATH lookup |

## Data Contracts

### Input

- `mop_specs_dir: str` -- Directory containing `.mop` specification files (source: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{jca,generic,generic_new}/`)
- `aspects_dir: str` -- Directory containing custom `.aj` files including Coverage.aj (source: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/aspect/`)
- `javamop_bin: str` -- Path to JavaMOP executable (source: `$RVSEC_HOME/javamop/bin/javamop`)
- `rvmonitor_bin: str` -- Path to RV-Monitor executable (source: `$RVSEC_HOME/rv-monitor/bin/rv-monitor`)
- `apks_dir: str` -- Directory containing original APK files to instrument (source: experiment configuration)
- `android_jar_path: str` -- Path to `android.jar` from Android SDK (source: `$ANDROID_HOME/platforms/android-29/android.jar`)
- `monitor_output_dir: str` -- Directory with generated monitor artifacts (source: output of rv-monitor-generator)
- `keystore_file: str` -- JKS keystore file for APK signing (source: bundled `assets/keystore.jks` or user-provided)

### Output

- `monitor_output_dir/` -- Directory containing generated artifacts:
  - `MultiSpec_*.aj` -- Merged AspectJ aspects from JavaMOP (pointcuts and advice)
  - `*MonitorAspect.aj` -- Individual monitor aspects
  - `*.java` -- Java monitor classes from RV-Monitor
  - `coverage.aj` -- Coverage aspect (copied from aspects_dir)
  - `logging.aj` -- Logging aspect (copied from aspects_dir)
- `instrumented_dir/` -- Directory containing signed instrumented APK files (consumer: rv-platform for emulator deployment)
- `InstrumentationResults` -- Pydantic model with success/error counts (consumer: rv-experiment post-processing)
- `instrument_errors.json` -- JSON file with per-APK error details (consumer: rv-experiment result manager)

### Side-Effects

- **File System (monitor generation)**: Creates and resets the monitor output directory; moves `.rvm` files between directories as a workaround for the JavaMOP `-d` bug
- **File System (instrumentation)**: Creates temporary directories (`tmp/`, `lib_tmp/`, `rvm_tmp/`) during processing and deletes them after each APK; creates the instrumented output directory
- **File System (Maven)**: Executes `mvn clean compile` to download and stage runtime dependencies into `lib_tmp/`
- **File System (signing)**: Creates signed APK files in the instrumented output directory using the configured keystore
- **Process execution**: Spawns external processes for JavaMOP, RV-Monitor, dex2jar, ajc, d8, jarsigner, Maven, and zip

### Error

- `ConfigurationError` -- Raised when path resolution fails, binaries are not found or not executable, MOP specifications are not found, Android SDK is not configured, or keystore is missing
- `CommandException` -- Raised when an external tool (JavaMOP, RV-Monitor, dex2jar, ajc, d8, jarsigner) returns a non-zero exit code or produces error output
- `InstrumentationError` -- Raised when a pipeline phase fails (decompilation, weaving, compilation, signing) or when the instrumented APK hash matches the original (indicating instrumentation had no effect)
- `RVAndroidError` -- Base exception class from rv-android-core; `ConfigurationError` inherits from it

## Invariants

- **INV-INS-01**: A monitor generation run MUST produce at least one `.aj` file and at least one `.java` file in the output directory when given a non-empty `mop_specs_dir`. If the output directory is empty after generation, the pipeline MUST return `False`.

- **INV-INS-02**: The `mop_specs_dir` MUST contain at least one `.mop` file. If no `.mop` files are found, `RVGeneratorConfig` MUST raise a `ConfigurationError` during initialization with a message listing available specification sets.

- **INV-INS-03**: The `javamop_bin` and `rvmonitor_bin` MUST point to existing, executable files. Both tools MUST produce output (stdout or stderr) when invoked with the `-h` flag. If either check fails, `RVGeneratorConfig` MUST raise a `ConfigurationError`.

- **INV-INS-04**: RV-Monitor MUST NOT leave `.rvm` intermediary files in the output directory after generation completes. The generator MUST delete all `.rvm` files from the output directory after RV-Monitor finishes.

- **INV-INS-05**: Custom aspects from `aspects_dir` (including `Coverage.aj`) MUST be copied into the monitor output directory during JavaMOP execution. The `Coverage.aj` aspect MUST be present in the output to enable method coverage tracking.

- **INV-INS-06**: An instrumented APK MUST have a different file hash than its original APK. If `hash(original) == hash(instrumented)`, `RVInstrumentation.check_if_instrumented()` MUST raise a `CommandException`, indicating instrumentation had no effect.

- **INV-INS-07**: The `monitor_output_dir` for instrumentation MUST contain both `.aj` files and `.java` files before instrumentation begins. `RVInstrumentationConfig._validate_monitor_artifacts()` MUST raise a `ConfigurationError` if either is missing.

- **INV-INS-08**: Temporary directories (`tmp_dir`, `rvm_tmp_dir`) MUST be cleaned after each APK instrumentation, whether the instrumentation succeeded or failed. The `lib_tmp_dir` MUST be cleaned after the entire batch completes.

- **INV-INS-09**: Specification sets MUST NOT be mixed within a single generation or instrumentation run. The `specification_set` field in `ExperimentConfig` MUST be one of `"jca"`, `"generic"`, or `"custom"`. If `"custom"` is specified, `custom_specs_dir` MUST be provided.

- **INV-INS-10**: The instrumented APK MUST be signed with a valid keystore before being placed in `instrumented_dir`. The signing process MUST include both `d2j-apk-sign` (initial signing) and `jarsigner` (keystore signing with SHA256withRSA / SHA-256 digest), followed by `jarsigner -verify` to confirm signature integrity.

- **INV-INS-11**: The dex2jar tools (`d2j-dex2jar.sh`, `d2j-asm-verify.sh`, `d2j-apk-sign.sh`) MUST exist and be executable in the `dex2jar_home` directory. `Dex2jarTools` field validators MUST raise `ValueError` if any tool is missing or not executable.

- **INV-INS-12**: When `RVSEC_HOME` is not set and no explicit paths are provided, both `RVGeneratorConfig` and `RVInstrumentationConfig` MUST raise a `ConfigurationError` during initialization, not during execution.

## Requirements

### Requirement: Monitor Generation from JavaMOP Specifications (FR01, NFR07)

The system MUST generate runtime verification monitors from MOP specification files through a coordinated pipeline of two tools: JavaMOP and RV-Monitor. JavaMOP reads `.mop` files and produces two artifacts: (a) `.aj` AspectJ files that define pointcuts and weaving advice for method interception, and (b) `.rvm` intermediate files containing monitor state machine specifications. RV-Monitor then reads the `.rvm` files and synthesizes `.java` monitor classes that implement the runtime verification logic.

The generation pipeline uses the `-merge` flag for both JavaMOP and RV-Monitor, which combines multiple specification files into unified merged artifacts. This is critical because merged monitors share a single aspect that intercepts all relevant methods, rather than creating individual aspects per specification that would multiply the runtime overhead.

A known bug in JavaMOP's `-d` (output directory) option causes `.rvm` files to remain in the source `mop_specs_dir` instead of being placed in the output directory. The generator MUST implement a workaround by explicitly moving `.rvm` files from `mop_specs_dir` to the output directory after JavaMOP execution.

After JavaMOP completes, custom AspectJ files from the `aspects_dir` MUST be copied into the output directory. This includes `Coverage.aj` (method coverage tracking) and `logging.aj` (additional logging). These custom aspects are woven alongside the generated monitor aspects during instrumentation.

After RV-Monitor completes, all intermediate `.rvm` files MUST be deleted from the output directory, as they are no longer needed.

#### Scenario: Successful generation with JCA specifications

- **WHEN** `mop_specs_dir` points to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/` containing 23 `.mop` files, and `javamop_bin` and `rvmonitor_bin` are valid executables, and `aspects_dir` contains `coverage.aj` and `logging.aj`
- **THEN** `RuntimeVerificationGenerator.generate_monitors(output_dir)` MUST return `True`
- **AND** the output directory MUST contain at least one `.aj` file (merged aspects from JavaMOP)
- **AND** the output directory MUST contain at least one `.java` file (monitor classes from RV-Monitor)
- **AND** the output directory MUST contain `coverage.aj` (copied from aspects_dir)
- **AND** the output directory MUST NOT contain any `.rvm` files (intermediaries cleaned up)

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

#### Scenario: Generation summary after successful run

- **WHEN** `generate_monitors()` has completed successfully in `output_dir`
- **THEN** `get_generation_summary(output_dir)` MUST return a dictionary with keys `output_directory`, `aspectj_files` (count), `monitor_classes` (count), and `specs_processed` (containing `source_directory` and `count`)

### Requirement: APK Instrumentation with Monitors (FR02)

The system MUST instrument Android APKs with generated runtime verification monitors through a multi-phase pipeline. The pipeline transforms a standard APK into a monitored APK by: (1) decompiling DEX bytecode to Java classes, (2) injecting monitor artifacts, (3) weaving aspects via AspectJ, (4) merging runtime dependencies, (5) recompiling to DEX, and (6) signing the APK.

The instrumentation pipeline relies on several external tools that MUST be available:
- **dex2jar** (`d2j-dex2jar.sh`): Converts APK DEX bytecode to JAR format. If the conversion produces an exception file, the pipeline MUST raise a `CommandException`.
- **ajc (AspectJ Compiler)**: Weaves monitor pointcuts into application bytecode. Uses Java 1.8 source compatibility (`-source 1.8`) and suppresses lint warnings (`-Xlint:ignore`). The classpath MUST include `android.jar` and all runtime verification JARs from `lib_tmp_dir`.
- **d8 (Android DEX compiler)**: Converts the instrumented JAR back to DEX format. Uses `--release` mode with `--min-api 26` and `--lib android.jar`.
- **jarsigner**: Signs the APK with the configured keystore using `SHA256withRSA` signature algorithm and `SHA-256` digest algorithm.
- **Maven**: Resolves and downloads runtime dependencies (`rv-monitor-rt.jar`, `rvsec-core.jar`, `rvsec-logger-logcat.jar`, `aspectjrt.jar`) into `lib_tmp_dir`.

Before instrumentation begins, `prepare_instrumentation()` MUST clean temporary directories from previous runs and execute Maven dependency resolution. After each APK, temporary directories (`tmp_dir`, `rvm_tmp_dir`) MUST be cleaned. After the entire batch, `lib_tmp_dir` MUST be cleaned.

The pipeline supports both single APK instrumentation (`instrument()`) and batch instrumentation (`instrument_apks()`). Batch instrumentation provides error isolation: if one APK fails, processing continues with the next APK. All errors are collected in `InstrumentationResults.errors` and saved to `instrument_errors.json`.

#### Scenario: Successful single APK instrumentation

- **WHEN** an APK at `app.path` exists and is a valid `.apk` file, and `monitor_output_dir` contains `.aj` and `.java` files, and all external tools are available
- **THEN** `RVInstrumentation.instrument(app, result_dir)` MUST produce a signed APK at `{instrumented_dir}/{app.name}`
- **AND** the instrumented APK hash MUST differ from the original APK hash
- **AND** temporary directories (`tmp_dir`, `rvm_tmp_dir`) MUST be cleaned after completion

#### Scenario: Skip existing instrumented APK

- **WHEN** an instrumented APK already exists at `{result_dir}/{app.name}` and `force_instrumentation` is `False`
- **THEN** the pipeline MUST skip this APK without error
- **AND** a log message "Skipping already instrumented APK" MUST be emitted

#### Scenario: Force re-instrumentation

- **WHEN** an instrumented APK already exists at `{result_dir}/{app.name}` and `force_instrumentation` is `True`
- **THEN** the existing APK MUST be deleted
- **AND** the full instrumentation pipeline MUST execute
- **AND** a new signed APK MUST be created at `{instrumented_dir}/{app.name}`

#### Scenario: dex2jar conversion failure

- **WHEN** dex2jar produces an exception file during DEX-to-JAR conversion
- **THEN** a `CommandException` MUST be raised with tool name `"dex2jar"`, code `"-1"`, and message referencing the exception file
- **AND** the error MUST be recorded in `InstrumentationResults.errors` with `phase="command_execution"` and `tool="dex2jar"`
- **AND** temporary directories MUST be cleaned despite the failure

#### Scenario: Batch instrumentation with mixed results

- **WHEN** `instrument_apks()` processes 10 APKs and 3 fail during different pipeline phases (dex2jar, ajc, d8)
- **THEN** `InstrumentationResults.success_count` MUST be 7
- **AND** `InstrumentationResults.total_count` MUST be 10
- **AND** `InstrumentationResults.success_rate` MUST be 70.0
- **AND** `InstrumentationResults.errors` MUST contain 3 entries, each with `code`, `tool`, `message`, and `phase`
- **AND** `instrument_errors.json` MUST be written to `results_dir` with the serialized error models

#### Scenario: Instrumentation verification detects unchanged APK

- **WHEN** the instrumented APK file hash equals the original APK file hash
- **THEN** `check_if_instrumented()` MUST raise a `CommandException` with tool `"instrumentation_verification"` and message `"APK {name} was not actually instrumented - hashes match original"`

#### Scenario: Maven dependency resolution failure

- **WHEN** Maven (`mvn clean compile`) fails during `prepare_instrumentation()`
- **THEN** a `CommandException` MUST be raised with tool name `"maven"`
- **AND** `instrument_apks()` MUST record the error in `InstrumentationResults.errors` with key `"setup_error"` and `phase="preparation"`
- **AND** processing MUST NOT continue to individual APK instrumentation

### Requirement: Specification Set Support (FR03)

The system MUST support multiple, independent specification sets for different API monitoring domains. Each specification set represents a collection of `.mop` files targeting a specific category of API usage patterns. The system MUST ensure that specification sets are never mixed within a single experiment run.

Three predefined specification sets are supported:

1. **JCA (Java Cryptography Architecture)** -- 23 specifications derived from CrySL rules, detecting misuses of cryptographic APIs:
   - `CipherSpec.mop`: Cipher initialization and usage sequences
   - `MessageDigestSpec.mop`: Hash algorithm validation (rejects MD5, SHA-1)
   - `SSLContextSpec.mop`: TLS version validation (rejects TLSv1)
   - `SecretKeySpecSpec.mop`: Key specification validation
   - `KeyGeneratorSpec.mop`: Key generation operation sequences
   - `SignatureSpec.mop`: Digital signature operation sequences
   - `MacSpec.mop`: Message Authentication Code operation sequences
   - `KeyStoreSpec.mop`: Keystore operation sequences
   - And 15 additional specifications covering SecureRandom, PBE, IvParameterSpec, etc.

2. **Generic (FSM)** -- 118 specifications from the JavaMOP specification database, detecting general API pattern violations such as Iterator hasNext/next ordering, stream resource management, and collection modification during iteration.

3. **Generic (new)** -- 27 curated specifications with descriptive names, such as `Closeable_MeaninglessClose`, `Map_UnsafeIterator`, `InputStream_ManipulateAfterClose`.

The specification set is determined by the `specification_set` field in `ExperimentConfig`, which maps to a subdirectory under `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/`. The `get_monitored_operations_config()` JIT method resolves the mapping:
- `"jca"` maps to `{mop_base_dir}/jca/`
- `"generic"` maps to `{mop_base_dir}/generic/`
- `"custom"` uses `custom_specs_dir` (MUST be explicitly provided)

When no `mop_specs_dir` is explicitly provided to `RVGeneratorConfig`, it defaults to the JCA specification set for backward compatibility.

#### Scenario: JCA specification set selection

- **WHEN** `ExperimentConfig.specification_set` is `"jca"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/`
- **AND** the directory MUST contain 23 `.mop` files

#### Scenario: Generic specification set selection

- **WHEN** `ExperimentConfig.specification_set` is `"generic"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic/`

#### Scenario: Custom specification set with valid directory

- **WHEN** `ExperimentConfig.specification_set` is `"custom"` and `custom_specs_dir` points to a directory containing `.mop` files
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` set to `custom_specs_dir`
- **AND** the directory MUST be validated to contain at least one `.mop` file

#### Scenario: Custom specification set without directory

- **WHEN** `ExperimentConfig.specification_set` is `"custom"` and `custom_specs_dir` is `None`
- **THEN** `get_monitored_operations_config()` MUST raise a `ConfigurationError` with message indicating that `custom_specs_dir` is required

#### Scenario: Invalid specification set value

- **WHEN** `ExperimentConfig.specification_set` is set to a value not in `["jca", "generic", "custom"]`
- **THEN** `ExperimentConfig.validate()` MUST raise a `ValueError` with message listing the valid specification sets

#### Scenario: Default specification set when using RVGeneratorConfig directly

- **WHEN** `RVGeneratorConfig` is created with only `rvsec_root` (no explicit `mop_specs_dir`)
- **THEN** `mop_specs_dir` MUST default to `{rvsec_root}/rvsec/rvsec-mop/src/main/resources/jca/` for backward compatibility

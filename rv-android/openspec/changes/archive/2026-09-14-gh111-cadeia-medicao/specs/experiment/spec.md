## Purpose

The experiment capability orchestrates a campaign: it resolves the run's policies at the entry point, runs pre-processing (monitor generation, instrumentation, static analysis), hands the instrumented APKs to `rv-platform` for execution, and post-processes the results. It is the only layer permitted to read the environment, and it is where a run's scope-key policy is decided and propagated by value.

This change gives it a second such policy and repairs three pre-processing behaviours that fail silently.

The new policy is build-type-suffix neutralization. RV-Android is generic and the manifest applicationId is the rule; the corpus under study was built with `assembleDebug`, so the declared id carries a `.debug`-family segment that the compiled classes do not. The correct shape for that fact is a run scalar resolved here and passed to `App` by value — the same aridity `package_detector` already has under INV-EXP-34 — and not a per-APK curated map, which would require a loader, an input policy that does not exist, and resume semantics.

The three repairs share the shape the whole change is about. `--skip-instrument` silently disables static analysis, because `_get_target_apks_for_analysis` lists `instrumented_apks/`, which does not exist when instrumentation was skipped, and the resulting warning does not name the cause. INV-EXP-16 does not hold: the docstring says APKs without `.apk.json` are excluded from execution and the filter logs each exclusion, but nothing excludes them, and the fallback message at `modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py:484-492` states something factually false about which APKs will run. `--skip-monitors` leaves `out/monitors` pointing at whatever a previous run left there, so a directory generated for a **different specification set** is consumed with no check and no log.

## Data Contracts

### Input
- `strip_build_type_suffix: bool` — resolved from `--strip-build-type-suffix` / `--no-strip-build-type-suffix` and `RV_STRIP_BUILD_TYPE_SUFFIX`, precedence CLI > env > default `False`
- `skip_instrument`, `skip_static`, `skip_monitors: bool` — unchanged flags whose failure modes are repaired

### Output
- `ExperimentConfig.strip_build_type_suffix` — forwarded to every `App` construction and to `PlatformConfig`
- `experiment_config.json` — records the resolved policy for the run

### Side-Effects
- **[Filesystem]**: pre-processing writes `out/monitors`, `out/instrumented_apks` and the `.apk.json` artefacts

### Error
- `click.BadParameter` — malformed environment value, raised before any `App` is constructed
- Pre-processing abort with a message naming the cause when a requested step cannot run

## Invariants

- **INV-EXP-35**: `RV_STRIP_BUILD_TYPE_SUFFIX` MUST be read only at an entry point — inside `modules/rv-experiment/` and the `rv-static-analysis` command's own `__main__` — through an `ENV_*` constant of the core registry, with no string literal at any read site. No module between an entry point and `App` MUST read it: `rv-platform`, `rv-instrumentation-*` and `rv-android-core` MUST receive the resolved boolean by value. Precedence MUST be CLI flag > environment variable > default `False`.

- **INV-EXP-36**: The neutralization policy MUST NOT reach the ajc instrumenter. `rv-instrumentation-ajc` MUST continue to receive `App` objects whose `code_package` is the declared applicationId, because `ajc_instrumentation.py:854-885` uses that value as an anti-quarantine guard which is inert precisely in the suffixed applications. Feeding it the neutralized key would activate the guard and change the instrumentation path, which this change does not touch. The divergence MUST be recorded in the module's documentation.

- **INV-EXP-37**: A pre-processing step that a flag combination makes impossible MUST fail with a message naming the flag and the cause, or MUST run. It MUST NOT return silently. `--skip-instrument --static-analysis` MUST NOT log "No APKs available for static analysis" without stating that instrumentation was skipped.

- **INV-EXP-38**: When `--skip-monitors` is given, the monitors directory MUST be verified against the run's requested specification set before being consumed. A directory whose provenance does not match MUST abort the run with a message naming both sets. It MUST NOT be consumed silently.

- **INV-EXP-39**: When static analysis was requested and did not produce an artefact for every instrumented APK, pre-processing MUST emit one consolidated report at the end of the phase, naming the count and listing the APKs. A per-APK warning buried in the phase log MUST NOT be the only record. The run MUST continue: a campaign of 200 APKs MUST NOT be aborted because GATOR failed on three of them, and the violation counts of those three do not depend on static analysis.

- **INV-EXP-16**: `get_instrumented_apks()` MUST return the set that will execute, and that set MUST be every APK present in `instrumented_apks/`, regardless of whether a `.apk.json` static analysis artefact accompanies it. The function MUST NOT log an exclusion it does not perform. An APK with no artefact MUST still execute and MUST contribute its violation counts, which do not depend on static analysis; its coverage cells MUST be published empty per INV-PLT-35, never as `0.00`. This also settles the interaction with INV-EXP-08: originals copied into `instrumented_apks/` by the instrumentation fallback carry no `.apk.json` and MUST execute like any other APK, without a coverage denominator.

## ADDED Requirements

### Requirement: Build-Type Suffix Neutralization CLI Flag

The `rv-experiment run` command SHALL expose the negatable boolean pair `--strip-build-type-suffix` / `--no-strip-build-type-suffix`. The resolved value SHALL set `ExperimentConfig.strip_build_type_suffix`, which the workflow SHALL forward to every `App` it constructs, to the sub-module configurations that construct their own, and to `PlatformConfig` so that task generation constructs its `App` objects under the same policy.

An absent flag SHALL fall through to `RV_STRIP_BUILD_TYPE_SUFFIX`, parsed with the project's truthiness convention; an explicit negative SHALL win over a truthy variable. The default SHALL be `False`, meaning `App.code_package` reports the declared applicationId verbatim.

`rv-static-analysis` SHALL expose the same pair on its own command line and SHALL resolve the variable itself, because it constructs `App` when invoked standalone. Both entry points SHALL parse the environment value through the shared helper, so the two commands cannot diverge.

The resolved policy SHALL be recorded in `experiment_config.json`, which is the run's provenance record.

#### Scenario: Default reports the declared package
- **WHEN** the user runs `uv run rv-experiment run ...` with neither the flag nor the variable set
- **THEN** `ExperimentConfig.strip_build_type_suffix` MUST be `False`
- **AND** every `App` MUST report `code_package == package_name`

#### Scenario: The policy reaches static analysis
- **WHEN** an experiment resolves the policy to `True` over an APK declaring `org.fossify.paint.debug`
- **THEN** GATOR MUST be invoked with `-clientParam codePackage=org.fossify.paint`
- **AND** the analysis artefact MUST record `org.fossify.paint` as the effective key (INV-ANA-66)
- **AND** the analysis artefact MUST also record the count of compiled classes under that key (`class_defs_under_key`), which is what makes the denominator gate a pure artefact predicate (INV-ANA-69)

#### Scenario: The policy reaches task generation
- **WHEN** an experiment resolves the policy to `True`
- **THEN** the `PlatformConfig` built by `ExecutionController` MUST carry it
- **AND** `rv-platform` MUST NOT read `RV_STRIP_BUILD_TYPE_SUFFIX` to obtain it

#### Scenario: The policy does not reach the ajc instrumenter
- **WHEN** an experiment resolves the policy to `True` and instruments with the `ajc` variant over an APK declaring `br.com.colman.petals.debug`
- **THEN** `ajc_instrumentation.py` MUST receive `code_package == br.com.colman.petals.debug`
- **AND** the anti-quarantine guard at `ajc_instrumentation.py:854-885` MUST remain inert, because the declared id it receives still matches the APK's own manifest
- **AND** the divergence MUST be recorded in `modules/rv-instrumentation-ajc` documentation

#### Scenario: The read stays at the entry points
- **WHEN** `scripts/check_env_vars_drift.py` runs over the implemented change
- **THEN** it MUST report zero violations
- **AND** every read MUST go through the registry constant with no string literal at a read site

### Requirement: A Skipped Step Never Disables Another Step Silently

Pre-processing SHALL either run each requested step or abort with a message naming why it cannot. A flag combination that makes a requested step impossible SHALL NOT produce a warning that describes a symptom without its cause.

`--skip-instrument` combined with `--static-analysis` is the measured case: `_get_target_apks_for_analysis` lists `instrumented_apks/`, the directory does not exist, the empty list yields "No APKs available for static analysis", and the run continues as if the user had asked for nothing. The header of `process()` at `modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py:83-90` compounds it by claiming static analysis runs on original APKs and depends on no earlier step — the opposite of the code.

#### Scenario: Static analysis requested with instrumentation skipped
- **WHEN** the user runs `rv-experiment run --skip-instrument --static-analysis --apks-dir ./apks_examples`
- **THEN** the run MUST abort before execution
- **AND** the message MUST state that static analysis reads `instrumented_apks/` and that `--skip-instrument` left it absent

#### Scenario: Static analysis over a directory from a previous run
- **WHEN** the user runs with `--skip-instrument` and `--apks-dir` pointing at a previous run's `instrumented_apks/`
- **THEN** static analysis MUST run over those APKs
- **AND** no abort MUST occur, because the input the step needs is present

### Requirement: Monitors Are Not Reused Across Specification Sets

When `--skip-monitors` is given, the run SHALL verify that the existing `out/monitors` directory was generated for the requested specification set before consuming it, and SHALL abort naming both sets when it was not.

`reset_folder` does not run under `--skip-monitors`, while `config.py:810-812` and `:883` keep pointing at `out/monitors`, so a directory left by a `jca` run is consumed by a `jca_android` run with no check and no log. The two sets accuse different things; mixing them silently produces a campaign whose specification provenance is unknowable after the fact.

#### Scenario: Leftover monitors from another set
- **WHEN** `out/monitors` was generated for `jca` and the user runs `rv-experiment run --skip-monitors --specification-set jca_android`
- **THEN** the run MUST abort
- **AND** the message MUST name both `jca` and `jca_android`

#### Scenario: Leftover monitors from the same set
- **WHEN** `out/monitors` was generated for `jca` and the user runs `--skip-monitors --specification-set jca`
- **THEN** the run MUST proceed
- **AND** it MUST log that it is reusing monitors generated for `jca`

## MODIFIED Requirements

### Requirement: Three-Phase Workflow (FR15, NFR08)

The rv-experiment module MUST provide a three-phase experiment workflow coordinated by the `ExperimentController`. The three phases — pre-processing, execution, and post-processing — MUST execute in strict order.

The `ExperimentController` is the sole orchestrator. It instantiates `PreProcessor`, `ExecutionController`, and `PostProcessor` during `__init__()` and calls them in sequence during `run()`. The controller MUST NOT bypass any phase; however, individual operations within Phase 1 MAY be skipped via boolean flags.

Phase 1 (pre-processing) MUST support three independent operations: monitor generation, APK instrumentation, and static analysis. Each operation MAY be individually skipped without affecting the others. The operations MUST execute in the order: monitor generation, then instrumentation, then static analysis. This ordering exists because instrumentation depends on generated monitors, and static analysis depends on instrumentation results to determine which APKs to analyze.

Static analysis MUST only run for APKs that have a corresponding instrumented version in the `instrumented_apks/` directory (INV-EXP-15). `_get_target_apks_for_analysis()` MUST scan `instrumented_apks/` for `.apk` files and return the original APK paths for those files only. Static analysis uses original APKs (not instrumented) because GATOR needs unmodified DEX bytecode, but the analysis is only meaningful for APKs that will enter the experiment — which requires successful instrumentation.

Phase 2 (execution) MUST translate experiment configuration into a `PlatformConfig`, create a `Platform` instance, and call `Platform.run()`. The `ExecutionController` MUST NOT perform any task management, emulator control, or result processing. `get_instrumented_apks()` MUST return every APK found in `instrumented_apks/`, whether or not a corresponding `.apk.json` static analysis output file is present, and MUST report the APKs lacking one rather than excluding them (INV-EXP-16). An APK without static analysis data MUST still enter execution: its violation counts do not depend on static analysis, and only its coverage cells are undefined — those MUST be published empty (INV-PLT-35).

Phase 3 (post-processing) MUST create basic diagnostics and completion metadata. It does not read back task results — rv-platform handles result processing.

The exclusion this requirement used to state never existed in the code, and this change resolves the contradiction in favour of executing. The set of APKs handed to execution comes from `execution_controller.py:258-260` and `platform.py:350-351`, which glob `out/instrumented_apks` — the instrumented APKs, which is the correct behaviour. The filter at `modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py:433-467` logs each APK lacking a `.apk.json` as excluded, and **nothing excludes it**; the return value of that filter decides nothing. In the mixed case — some APKs analysed, some not — the current behaviour is the worst of both: an APK enters execution carrying a warning that says it was excluded.

Three decisions already taken force this resolution. Violations do not depend on static analysis — that is the answer to Q8, whose first scenario is precisely running an instrumented APK with no static analysis, and `result_processor.py:632-638` already implements it at the report level; excluding the APK from execution would destroy that scenario one layer earlier. Excluding APKs so a number closes is a named anti-pattern in this lineage and has already cost the corpus 55 applications once. And with the denominator published as a column (INV-PLT-33), excluding a denominator-less row becomes a **reader-side** decision — explicit and revisable — rather than a pipeline-side one that is irreversible and invisible.

The rider is not optional: an APK that runs without a denominator MUST publish **empty** coverage cells, never `0.00` (INV-PLT-35). Writing zero would recreate the exact ambiguity this change's accounting exists to remove, and `cov_method == 0` is one of four distinct conditions this lineage forbids reading as an automatic accusation.

`get_instrumented_apks()` today returns a filtered list that decides nothing: `experiment_controller.py:267` uses it for an emptiness test and passes it to `execution_controller.setup`, where the `apks` parameter is consumed on exactly one line — the log context at `:130`. The executed set comes from the directory glob at `:258-260`. Either the returned list becomes the executed set or it stops being called a filter; this requirement chooses the second, so the function SHALL stop filtering and SHALL report instead.

The fallback at `modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py:484-492` emits `"No instrumented APKs found, using original APKs"`, which is factually false about the set that will run. That message SHALL be removed or corrected; it MUST NOT describe a fallback that does not occur.

This change invalidates test expectations that are green today, and the implementation MUST update them rather than leave them red. In `modules/rv-experiment/tests/experiment/test_pre_processor.py`, `test_excludes_apks_without_json` asserts `len(result) == 1` for a directory holding two APKs of which one has no `.apk.json`, and under this requirement the result is 2; `test_falls_back_to_originals_when_no_apk_has_json` asserts that the fallback path fires, and under this requirement it does not fire at all. Independently of the exclusion semantics, six of that file's 29 tests stub `App` with a fixed-arity `lambda app_path, package_detector=False:`, so the new `strip_build_type_suffix` keyword argument raises `TypeError` in those six — and one of them additionally asserts the exact call kwargs (`:190-192`), so widening the lambda alone does not repair it. Two further tests read a cell that INV-PLT-35 makes empty: `modules/rv-platform/tests/execution/test_resume_integration.py:675` and `modules/rv-platform/tests/components/test_result_processor.py:1283` both apply `float(...)` to a `cov_method` cell for an APK seeded without a `.apk.json`, and `float("")` raises `ValueError`. These are the measured current states of those files, not predictions.

#### Scenario: Full Experiment With All Phases Enabled

- **WHEN** an `ExperimentConfig` is created with `generate_monitors=True`, `instrument_apks=True`, `run_static_analysis=True`, a valid `apks_dir` containing at least one APK, at least one `ToolConfig`, and a valid `RVSEC_HOME` path
- **THEN** `ExperimentController.run()` MUST execute Phase 1 (PreProcessor.process) with all three operations enabled
- **AND** Phase 1 MUST produce files in `out/monitors/`, `out/instrumented_apks/`, and static analysis files alongside instrumented APKs
- **AND** static analysis MUST run only for APKs that have a corresponding `.apk` file in `out/instrumented_apks/`
- **AND** Phase 2 (ExecutionController) MUST create a PlatformConfig with `apks_dir` pointing to `out/instrumented_apks/`
- **AND** Phase 2 MUST include every `.apk` in `out/instrumented_apks/`, whether or not a matching `.apk.json` is present
- **AND** Phase 3 (PostProcessor) MUST create `instrument_errors.json` and `experiment_completion.json` in the results directory

#### Scenario: Mixed instrumentation results filter downstream phases

- **WHEN** `instrument_apks=True` and `run_static_analysis=True` and `apks_dir` contains 10 APKs, of which 3 fail instrumentation
- **THEN** `_get_target_apks_for_analysis()` MUST return only the 7 original APK paths corresponding to successfully instrumented APKs
- **AND** 3 APKs MUST be logged as skipped for static analysis due to instrumentation failure
- **AND** if 1 of the 7 APKs fails static analysis (no `.json` produced), `get_instrumented_apks()` MUST still return all 7 APKs for execution and MUST report the 1 without an artefact instead of excluding it
- **AND** `instrument_errors.json` MUST contain 3 entries with accurate phase information

#### Scenario: An APK without static analysis data executes

- **WHEN** `instrumented_apks/` holds `app.apk` with no `app.apk.json`, and the run did not skip static analysis
- **THEN** `app.apk` MUST be present in the executed set
- **AND** the log MUST state that it will run without a coverage denominator
- **AND** the message `"Excluding app.apk from execution"` MUST NOT be emitted, because no exclusion occurs

#### Scenario: The mixed case

- **WHEN** `instrumented_apks/` holds `a.apk` with `a.apk.json` and `b.apk` without
- **THEN** the executed set and the logged set MUST be identical, and MUST contain both
- **AND** no APK MUST be logged as excluded while being executed
- **AND** `b.apk` MUST still contribute its violation counts, which do not depend on static analysis

#### Scenario: The consolidated report at the end of pre-processing

- **WHEN** 48 of 50 instrumented APKs produced a `.apk.json` and static analysis was requested
- **THEN** pre-processing MUST emit one report naming `2 of 50` and listing the two APK filenames
- **AND** the run MUST continue into execution

#### Scenario: Static analysis skipped by flag is reported, not silent

- **WHEN** the user runs `rv-experiment run --skip-static` over 50 instrumented APKs
- **THEN** the consolidated pre-processing report of INV-EXP-39 MUST state that static analysis was skipped **by flag** and that all 50 APKs will run without a coverage denominator
- **AND** their coverage cells MUST be published empty with `measured` false (INV-PLT-35, INV-PLT-36)
- **AND** the run MUST continue — skipping a step by flag is a choice, not a failure

#### Scenario: The cosmetic fallback does not fire

- **WHEN** `out/instrumented_apks` contains APKs and the run reaches execution
- **THEN** the message `"No instrumented APKs found, using original APKs"` MUST NOT be emitted
- **AND** the executed set MUST be the instrumented APKs

#### Scenario: Experiment With All Pre-Processing Skipped

- **WHEN** an `ExperimentConfig` is created with `generate_monitors=False`, `instrument_apks=False`, `run_static_analysis=False`
- **THEN** `PreProcessor.process()` MUST NOT invoke monitor generation, instrumentation, or static analysis
- **AND** `PreProcessor.process()` MUST log a warning for each skipped step
- **AND** `PreProcessor.get_instrumented_apks()` MUST scan `instrumented_apks/` and return every `.apk` it finds, reporting which of them have no `.apk.json`
- **AND** only if `instrumented_apks/` holds no APK at all MUST it fall back to App objects from the original `apks_dir`
- **AND** Phase 2 MUST proceed with the available APKs
- **AND** the experiment MUST complete without errors — where a `.apk.json` exists the coverage is a true `0.00` (a real denominator that no runtime event reaches, because the APKs are not instrumented), and where none exists the cells are empty per INV-PLT-35

#### Scenario: Pre-Processing Failure Does Not Abort Experiment

- **WHEN** APK instrumentation fails due to a compilation error or missing external tool
- **THEN** `PreProcessor._instrument_apks()` MUST catch the exception via ErrorHandler
- **AND** `PreProcessor._copy_original_apks()` MUST copy original APKs to `out/instrumented_apks/` as fallback
- **AND** Phase 2 and Phase 3 MUST still execute using the copied original APKs
- **AND** the experiment MUST complete (with a warning logged about the instrumentation failure)

#### Scenario: Module Import Failure for Optional Sub-Modules

- **WHEN** the `rv_monitor_generator` Python module is not installed or not importable
- **THEN** `PreProcessor._generate_monitors()` MUST catch the `ImportError`
- **AND** MUST log a warning: "Monitor generator module not available - skipping monitor generation"
- **AND** execution MUST continue with the remaining pre-processing steps

#### Scenario: Execution Phase Failure Propagation

- **WHEN** `Platform.run()` raises an exception during Phase 2
- **THEN** `ExecutionController.run()` MUST catch the exception, set `has_errors=True`, and raise `RVExperimentExecutionError`
- **AND** `ExperimentController.run()` MUST catch the error, log it, and return `False`

#### Scenario: No APKs Available for Execution

- **WHEN** `PreProcessor.get_instrumented_apks()` returns an empty list (no instrumented APKs found and no original APKs available)
- **THEN** `ExperimentController._run_execution()` MUST log "No APKs available for execution" and return `False`
- **AND** Phase 2 MUST NOT create a Platform instance or attempt execution
- **AND** Phase 3 MUST still execute to produce diagnostics

### Requirement: Package Detector Opt-In CLI Flag (FR15, NFR05)

The `rv-experiment run` command MUST expose the negatable boolean pair `--package-detector` / `--no-package-detector`. The resolved value MUST set `ExperimentConfig.package_detector`, which the experiment workflow MUST forward to every `App` it constructs, to the sub-module configurations that construct their own, and to `PlatformConfig` so that task generation constructs its `App` objects under the same policy.

An absent flag MUST be distinguishable from an explicitly negative one: with the flag absent the value falls through to `RV_PACKAGE_DETECTOR`, and with `--no-package-detector` given the resolved value MUST be `False` even when the variable is truthy. When neither the flag nor the variable is provided, the resolved value MUST be `False`, meaning `App.code_package` reports the package declared in the APK manifest. The environment variable MUST be parsed with the project's existing truthiness convention — `"true"`, `"1"`, `"yes"`, `"on"`, case-insensitive — matching INV-CORE-12.

The flag controls provenance, not normalization: enabling it runs `PackageDetector` as specified in INV-ANA-14, and disabling it reports the declared applicationId verbatim. The detector election itself applies no rewriting of the identifier. Build-type-suffix stripping — a rewriting rule that *is* a property of a particular corpus — is not this flag's business either: it is its own opt-in run policy (`--strip-build-type-suffix`, INV-CORE-58), stated by the caller through its own channel, and when both policies are on the detector takes precedence (INV-CORE-18). What remains true is that neither package flag ever rewrites silently: every rewriting is a policy the run states.

`rv-static-analysis` MUST expose the same negatable pair on its own command line and MUST resolve `RV_PACKAGE_DETECTOR` itself under the same precedence, because it constructs `App` when invoked standalone and is therefore an entry point rather than an intermediate layer. Both entry points MUST parse the environment value through one shared helper, so that the two commands cannot diverge on what a given string means.

#### Scenario: Default reports the declared package

- **WHEN** the user runs `uv run rv-experiment run ...` with neither `--package-detector` nor `RV_PACKAGE_DETECTOR` set
- **THEN** `ExperimentConfig.package_detector` MUST be `False`
- **AND** every `App` constructed by the run MUST report `code_package == package_name`
- **AND** `PackageDetector` MUST NOT be invoked at any point in the run

#### Scenario: Environment variable enables the detector

- **WHEN** the shell has `RV_PACKAGE_DETECTOR=true` exported
- **AND** the user runs `uv run rv-experiment run ...` without the flag
- **THEN** `ExperimentConfig.package_detector` MUST be `True`
- **AND** each `App` MUST report `code_package_source == "detector"`

#### Scenario: CLI flag overrides the environment variable

- **WHEN** the shell has `RV_PACKAGE_DETECTOR=true` exported
- **AND** the user runs `uv run rv-experiment run --package-detector ...`
- **THEN** the resolved value MUST be `True` — the flag and the variable agree, and the flag is the authority
- **AND** when the shell has `RV_PACKAGE_DETECTOR=true` and the user runs `uv run rv-experiment run --no-package-detector ...`, the resolved value MUST be `False`

#### Scenario: The resolved value reaches task generation

- **WHEN** an experiment resolves `package_detector` to `True`
- **THEN** the `PlatformConfig` built by `ExecutionController` MUST carry `package_detector == True`
- **AND** every `App` constructed during task generation MUST report `code_package_source == "detector"`
- **AND** `rv-platform` MUST NOT read `RV_PACKAGE_DETECTOR` to obtain it

#### Scenario: Standalone static analysis honours both the flag and the variable

- **WHEN** the user runs `uv run rv-static-analysis --apk <path> --package-detector`
- **THEN** the `App` it constructs MUST report `code_package_source == "detector"`

- **WHEN** the shell has `RV_PACKAGE_DETECTOR=true` exported and the user runs `uv run rv-static-analysis --apk <path>` with no flag
- **THEN** the resolved value MUST be `True`, because a standalone invocation is a run and resolves the variable itself

- **WHEN** the shell has `RV_PACKAGE_DETECTOR=true` exported and the user runs `uv run rv-static-analysis --apk <path> --no-package-detector`
- **THEN** the resolved value MUST be `False`

- **WHEN** the shell has `RV_PACKAGE_DETECTOR=maybe` exported and the user runs `uv run rv-static-analysis --apk <path>` with no flag
- **THEN** the command MUST exit nonzero with a message naming the variable, before constructing any `App`

#### Scenario: The read stays at the entry points and goes through the registry

- **WHEN** `scripts/check_env_vars_drift.py` runs over the implemented change
- **THEN** it MUST report zero violations
- **AND** every read of `RV_PACKAGE_DETECTOR` MUST go through the `ENV_PACKAGE_DETECTOR` constant, with no string literal at any read site
- **AND** no read MUST exist in `rv-platform`, in `rv-instrumentation-*`, or anywhere in `rv-android-core` — `domain/app.py` included (INV-CORE-55)

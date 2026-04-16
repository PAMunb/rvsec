## Purpose

Delta spec for the rv-experiment PreProcessor downstream filtering. This change ensures that static analysis only runs for APKs that were successfully instrumented, and execution only includes APKs that have both an instrumented APK and static analysis data.

## ADDED Invariants

- **INV-EXP-15**: The PreProcessor MUST filter APKs for static analysis based on instrumentation outcome. `_get_target_apks_for_analysis()` MUST return original APK paths only for APKs that have a corresponding instrumented file in the `instrumented_apks/` directory. APKs that failed instrumentation MUST be logged as skipped and excluded from static analysis.

- **INV-EXP-16**: The PreProcessor MUST filter APKs for execution based on static analysis data presence. `get_instrumented_apks()` MUST return only APKs from `instrumented_apks/` that have a corresponding `.apk.json` file (static analysis output) in the same directory. APKs without static analysis data MUST be logged with a warning and excluded from execution. This filtering is based on file presence, not on flags, so it works correctly with both `--static-analysis` and `--skip-static` when pre-existing artifacts are available.

Note on interaction with INV-EXP-08: When the instrumentation module is unavailable and `_copy_original_apks()` copies originals to `instrumented_apks/`, those copies will not have `.apk.json` files. INV-EXP-16 filtering will exclude them, and `get_instrumented_apks()` will fall back to original APKs from `apks_dir`. The net result is equivalent to current behavior (experiment runs on originals with 0% coverage), but through a filtering chain rather than direct fallback.

## MODIFIED Requirements

### Requirement: Three-Phase Workflow (FR15, NFR08)

The rv-experiment module MUST provide a three-phase experiment workflow coordinated by the `ExperimentController`. The three phases — pre-processing, execution, and post-processing — MUST execute in strict order.

The `ExperimentController` is the sole orchestrator. It instantiates `PreProcessor`, `ExecutionController`, and `PostProcessor` during `__init__()` and calls them in sequence during `run()`. The controller MUST NOT bypass any phase; however, individual operations within Phase 1 MAY be skipped via boolean flags.

Phase 1 (pre-processing) MUST support three independent operations: monitor generation, APK instrumentation, and static analysis. Each operation MAY be individually skipped without affecting the others. The operations MUST execute in the order: monitor generation, then instrumentation, then static analysis. This ordering exists because instrumentation depends on generated monitors, and static analysis depends on instrumentation results to determine which APKs to analyze.

Static analysis MUST only run for APKs that have a corresponding instrumented version in the `instrumented_apks/` directory (INV-EXP-15). `_get_target_apks_for_analysis()` MUST scan `instrumented_apks/` for `.apk` files and return the original APK paths for those files only. Static analysis uses original APKs (not instrumented) because GATOR needs unmodified DEX bytecode, but the analysis is only meaningful for APKs that will enter the experiment — which requires successful instrumentation.

Phase 2 (execution) MUST translate experiment configuration into a `PlatformConfig`, create a `Platform` instance, and call `Platform.run()`. The `ExecutionController` MUST NOT perform any task management, emulator control, or result processing. `get_instrumented_apks()` MUST return only APKs from `instrumented_apks/` that have a corresponding `.apk.json` static analysis output file (INV-EXP-16). APKs without static analysis data produce meaningless coverage results and MUST be excluded from execution.

Phase 3 (post-processing) MUST create basic diagnostics and completion metadata. It does not read back task results — rv-platform handles result processing.

#### Scenario: Full Experiment With All Phases Enabled

- **WHEN** an `ExperimentConfig` is created with `generate_monitors=True`, `instrument_apks=True`, `run_static_analysis=True`, a valid `apks_dir` containing at least one APK, at least one `ToolConfig`, and a valid `RVSEC_HOME` path
- **THEN** `ExperimentController.run()` MUST execute Phase 1 (PreProcessor.process) with all three operations enabled
- **AND** Phase 1 MUST produce files in `out/monitors/`, `out/instrumented_apks/`, and static analysis files alongside instrumented APKs
- **AND** static analysis MUST run only for APKs that have a corresponding `.apk` file in `out/instrumented_apks/`
- **AND** Phase 2 (ExecutionController) MUST create a PlatformConfig with `apks_dir` pointing to `out/instrumented_apks/`
- **AND** Phase 2 MUST only include APKs that have both `.apk` and `.apk.json` in `out/instrumented_apks/`
- **AND** Phase 3 (PostProcessor) MUST create `instrument_errors.json` and `experiment_completion.json` in the results directory

#### Scenario: Mixed instrumentation results filter downstream phases

- **WHEN** `instrument_apks=True` and `run_static_analysis=True` and `apks_dir` contains 10 APKs, of which 3 fail instrumentation
- **THEN** `_get_target_apks_for_analysis()` MUST return only the 7 original APK paths corresponding to successfully instrumented APKs
- **AND** 3 APKs MUST be logged as skipped for static analysis due to instrumentation failure
- **AND** if 1 of the 7 APKs fails static analysis (no `.json` produced), `get_instrumented_apks()` MUST return only 6 APKs for execution
- **AND** `instrument_errors.json` MUST contain 3 entries with accurate phase information

#### Scenario: Experiment With All Pre-Processing Skipped

- **WHEN** an `ExperimentConfig` is created with `generate_monitors=False`, `instrument_apks=False`, `run_static_analysis=False`
- **THEN** `PreProcessor.process()` MUST NOT invoke monitor generation, instrumentation, or static analysis
- **AND** `PreProcessor.process()` MUST log a warning for each skipped step
- **AND** `PreProcessor.get_instrumented_apks()` MUST scan `instrumented_apks/` for APKs with corresponding `.apk.json` files
- **AND** if no APKs with `.apk.json` are found, MUST fall back to App objects from the original `apks_dir`
- **AND** Phase 2 MUST proceed with the available APKs
- **AND** the experiment MUST complete without errors (coverage will be 0% because APKs are not instrumented)

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

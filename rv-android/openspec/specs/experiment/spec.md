# Specification: Experiment Orchestration

## Purpose

The Experiment Orchestration domain provides the top-level coordination layer for executing Android testing experiments with runtime verification. It sits above both the platform execution engine (rv-platform) and the pre-processing pipeline (rv-monitor-generator, rv-instrumentation, rv-static-analysis), serving as the single entry point that ties together monitor generation, APK instrumentation, static analysis, task execution, and post-experiment diagnostics into a coherent, reproducible workflow.

### Problem This Domain Solves

Running a complete RV-Android experiment requires executing a multi-step pipeline across multiple independent modules. Without a coordinator, the user would need to:

1. Manually invoke rv-monitor-generator to produce `.aj` aspects and `.java` monitor classes from MOP specifications.
2. Feed those monitors into rv-instrumentation to instrument each APK.
3. Run rv-static-analysis (GATOR, GESDA, REACH) on each instrumented APK.
4. Configure rv-platform with the correct directories, tool specifications, timeouts, and repetitions.
5. Launch rv-platform for task execution, emulator management, and result processing.
6. Gather post-experiment metadata, instrumentation error reports, and completion diagnostics.

rv-experiment automates all six steps through a three-phase workflow (pre-processing, execution, post-processing) orchestrated by the `ExperimentController`. It provides a Click-based CLI that accepts a tool specification DSL, translates CLI arguments into a validated `ExperimentConfig` (Pydantic model), and delegates execution to the appropriate sub-modules.

### Fit in the Overall Pipeline

```
User CLI Input
      |
      v
rv-experiment CLI (__main__.py)
      |
      v
ExperimentConfig (Pydantic validation, JIT sub-module config)
      |
      v
ExperimentController.run()
      |
      +---> Phase 1: PreProcessor
      |       |
      |       +---> rv-monitor-generator (generate monitors)
      |       +---> rv-instrumentation (instrument APKs)
      |       +---> rv-static-analysis (GATOR, GESDA, REACH)
      |
      +---> Phase 2: ExecutionController
      |       |
      |       +---> Creates PlatformConfig from ExperimentConfig
      |       +---> Instantiates rv-platform Platform
      |       +---> Delegates execution (Platform.run())
      |       +---> No data transfer back (results stay in rv-platform)
      |
      +---> Phase 3: PostProcessor
              |
              +---> ResultManager (instrumentation errors JSON)
              +---> Completion diagnostics (experiment_completion.json)
```

### Key Design Decisions and Constraints

1. **No data transfer between rv-platform and rv-experiment.** The execution phase delegates to rv-platform, which handles all task execution and result processing. rv-experiment does not read back task results, coverage data, or error logs. Results persist inside rv-platform's results directory. This eliminates coupling and prevents rv-experiment from duplicating rv-platform's responsibilities.

2. **Just-in-time sub-module configuration.** `ExperimentConfig` does not eagerly create configurations for rv-monitor-generator, rv-instrumentation, or rv-static-analysis. Instead, it exposes `get_monitored_operations_config()`, `get_rv_instrumentation_config()`, and `get_static_analysis_config()` methods that construct and validate sub-module configuration objects only when invoked by the `PreProcessor`. This reduces initialization overhead and avoids errors for sub-modules that will be skipped.

3. **Skip flags for artifact reuse.** The CLI provides `--skip-monitors`, `--skip-instrument`, and `--skip-static` flags. When skip flags are used, the corresponding pre-processing step is not executed, and the `--apks-dir` MUST point to a directory containing previously instrumented APKs. If skip flags are used with non-instrumented APKs, the experiment will run but coverage will be 0% because the APKs lack runtime verification monitors.

4. **Clean separation: orchestration vs. execution.** rv-experiment handles only orchestration (phase sequencing, configuration assembly). rv-platform handles execution (task generation, emulator management, tool execution, coverage tracking, result processing). rv-experiment never manages emulators, tasks, or results directly.

5. **Tool specification DSL.** The CLI uses a compact DSL (`tool:variant@param=value`) instead of verbose JSON for tool configuration. The DSL is parsed by `CLIContext.parse_tool_specification()` and converted to `ToolConfig` objects (from rv-platform). This makes the CLI ergonomic for interactive use while maintaining structured configuration internally.

6. **RVSEC_HOME resolution hierarchy.** The `ExperimentConfig` resolves RVSEC_HOME through a three-level priority: (1) explicit `rvsec_root` field in configuration, (2) `RVSEC_HOME` environment variable, (3) error if neither is defined. This path is required for monitor generation and instrumentation because it points to the parent RVSEC project containing JavaMOP, RV-Monitor, and MOP specification files.

7. **Specification set isolation.** Each experiment uses exactly one specification set (JCA, generic, or custom). Specification sets are never mixed within a single experiment. The specification set determines which MOP specification directory is used for monitor generation.

8. **Fallback behavior for missing modules.** If rv-monitor-generator, rv-instrumentation, or rv-static-analysis modules are not importable, `PreProcessor` logs a warning and continues execution rather than failing. If instrumentation fails, original APKs are copied to the instrumented directory as a fallback. This enables partial experiments when not all sub-modules are available.

### Data Models

```
ExperimentConfig (Pydantic BaseValidatedModel):
  name: str                           # Experiment identifier (auto-generated if empty)
  description: str                    # Human-readable experiment description
  output_dir: str                     # Pre-processing artifacts directory (default: "out")
  results_dir: Optional[str]          # Results base directory (default: "results")
  rvsec_root: Optional[str]           # Override for RVSEC_HOME environment variable
  tool_configs: List[ToolConfig]      # Tool configurations with name, variants, parameters
  repetitions: int                    # Number of repetitions per task (gt=0)
  timeouts: List[int]                 # Timeout values in seconds
  no_window: bool                     # Run emulator headless (default: True)
  generate_monitors: bool             # Enable monitor generation phase (default: True)
  instrument_apks: bool               # Enable APK instrumentation phase (default: True)
  run_static_analysis: bool           # Enable static analysis phase (default: True)
  specification_set: str              # "jca", "generic", or "custom"
  custom_specs_dir: Optional[str]     # Required when specification_set == "custom"
  custom_aspects_dir: Optional[str]   # Optional custom AspectJ aspects directory
  apks_dir: str                       # Source APK directory (default: "./apks_examples/")
  metadata: Dict[str, Any]            # Arbitrary metadata (e.g., created_via, cli_version)
  created_at: Optional[str]           # ISO timestamp of creation
  resume_mode: bool                   # Enable experiment continuation (default: False)
  status_file: Optional[str]          # Path to status file for continuation

ToolConfig (from rv-platform):
  name: str                           # Tool name (e.g., "monkey", "droidbot", "rvagent")
  variants: List[str]                 # Variant identifiers (e.g., ["dfs_greedy"])
  parameters: Dict[str, Any]          # Additional tool parameters (e.g., {"seed": 42})

PlatformConfig (from rv-platform, created by ExecutionController):
  apks_dir: str                       # Path to instrumented APKs directory
  tools: List[ToolConfig]             # Tools to execute
  repetitions: int                    # Repetitions per task
  timeouts: List[int]                 # Timeout values
  results_dir: str                    # Results directory
  no_window: bool                     # Headless emulator flag
  log_level: str                      # Logging level (default: "INFO")
```

### Relationships with Other Domains

**Consumed by rv-experiment (inputs):**
- `RVGeneratorConfig` from rv-monitor-generator (created JIT by `get_monitored_operations_config()`)
- `RVInstrumentationConfig` from rv-instrumentation (created JIT by `get_rv_instrumentation_config()`)
- `RVStaticAnalysisConfig` from rv-static-analysis (created JIT by `get_static_analysis_config()`)
- `PlatformConfig` and `ToolConfig` from rv-platform (created by `ExecutionController._create_platform_config()`)
- `AbstractTool` instances from rv-tools via `ToolFactory`
- `App` domain model from rv-android-core

**Produced by rv-experiment (outputs):**
- `instrument_errors.json` -- instrumentation error records per APK
- `experiment_completion.json` -- basic completion diagnostics with timestamp
- `experiment_config.json` -- serialized experiment configuration (optional, via `save_experiment_config()`)

**Dependencies:**
- rv-android-core: ErrorHandler, LoggingManager, BaseValidatedModel, App, constants
- rv-platform: Platform, PlatformConfig, ToolConfig, TaskStorage
- rv-tools: ToolRegistry, ToolFactory
- rv-monitor-generator: RuntimeVerificationGenerator, RVGeneratorConfig (optional import)
- rv-instrumentation: RVInstrumentation, RVInstrumentationConfig (optional import)
- rv-static-analysis: StaticAnalyzer, RVStaticAnalysisConfig (optional import)

## Data Contracts

### Input

- `tools: str` -- Comma-separated tool specification DSL string from CLI (source: user input via Click)
- `config: str` -- Path to JSON configuration file (source: user input via Click, alternative to DSL)
- `apks_dir: str` -- Directory containing source APK files (source: user input or default `./apks_examples/`)
- `specification_set: str` -- One of "jca", "generic", "custom" (source: user input, default: "jca")
- `custom_specs_dir: str` -- Directory with `.mop` specification files (source: user input, required when specification_set == "custom")
- `timeout: int` -- Execution timeout in seconds (source: user input, default: 300)
- `repetitions: int` -- Number of experiment repetitions (source: user input, default: 1)
- `generate_monitors: bool` -- Whether to run monitor generation (source: CLI flag `--generate-monitors/--skip-monitors`)
- `instrument_apks: bool` -- Whether to run APK instrumentation (source: CLI flag `--instrument-apks/--skip-instrument`)
- `static_analysis: bool` -- Whether to run static analysis (source: CLI flag `--static-analysis/--skip-static`)
- `no_window: bool` -- Headless emulator mode (source: CLI flag `--no-window/--window`, default: headless)

### Output

- `instrument_errors.json: Dict[str, Any]` -- Keyed by APK name, containing instrumentation error details per APK (destination: results directory, consumed by researchers for debugging)
- `experiment_completion.json: Dict[str, Any]` -- Contains `results_directory`, `completion_timestamp`, `post_processing_completed` (destination: results directory)
- `experiment_config.json: str` -- Serialized ExperimentConfig in JSON format (destination: results directory, optional)

### Side-Effects

- **Filesystem (output_dir)**: Creates `out/monitors/` directory with generated `.aj` and `.java` monitor files
- **Filesystem (output_dir)**: Creates `out/instrumented_apks/` directory with instrumented APK files; falls back to copying original APKs if instrumentation fails
- **Filesystem (output_dir)**: Creates static analysis output files (`.wtg`, `.gesda`, `.reach`) in `out/instrumented_apks/` alongside the APKs
- **Filesystem (results_dir)**: Creates experiment results directory structure under `results/<experiment_name>/`
- **Filesystem (results_dir)**: rv-platform writes `coverage.csv`, `errors.csv`, `summary.csv`, `results.json`, `performance.csv`, `tasks.json` (not created by rv-experiment, but caused by its delegation to rv-platform)
- **Android Emulator**: Emulator sessions are started and stopped by rv-platform during Phase 2 (not by rv-experiment directly)
- **External Processes**: JavaMOP, RV-Monitor, ajc, dex2jar, d8, jarsigner, GATOR, GESDA, REACH are invoked as subprocesses during Phase 1

### Error

- `ConfigurationError` -- Raised when ExperimentConfig validation fails: missing APK directory, invalid specification set, invalid tool configurations, missing RVSEC_HOME
- `RVExperimentExecutionError` -- Raised when execution phase fails: platform execution failure, missing setup call, no APKs available, no valid tools found
- `MonitorConfigError` -- Raised when RVGeneratorConfig creation fails (wrapped as ConfigurationError)
- `InstrumentationConfigError` -- Raised when RVInstrumentationConfig creation fails (wrapped as ConfigurationError)
- `ValueError` -- Raised for invalid tool specification DSL parsing, empty experiment name, non-positive repetitions or timeouts
- `FileNotFoundError` -- Raised when configuration file does not exist for `ExperimentConfig.from_file()`
- `ImportError` -- Caught and logged as warning when optional sub-modules (rv-monitor-generator, rv-instrumentation, rv-static-analysis) are not available; execution continues

## Invariants

- **INV-EXP-01**: The experiment workflow MUST execute phases in strict sequential order: pre-processing, then execution, then post-processing. Phase 2 MUST NOT start before Phase 1 completes. Phase 3 MUST NOT start before Phase 2 completes.

- **INV-EXP-02**: rv-experiment MUST NOT read back task results, coverage data, or error logs from rv-platform after execution. Data flows one-way from rv-experiment to rv-platform via `PlatformConfig`. The only information flowing back is the aggregate success/failure status from `Platform.run()` (a dictionary with `total_tasks`, `successful_tasks`, `failed_tasks` counts).

- **INV-EXP-03**: `ExperimentConfig.validate()` MUST be called before experiment execution. The validation MUST check: (a) name is non-empty, (b) at least one tool is configured, (c) repetitions > 0, (d) all timeouts > 0, (e) APK source directory exists and contains `.apk` files, (f) specification_set is one of "jca", "generic", "custom".

- **INV-EXP-04**: When `specification_set` is "custom", the `custom_specs_dir` field MUST be set and MUST point to a directory containing at least one `.mop` file. The CLI MUST raise `ClickException` before execution if this condition is violated.

- **INV-EXP-05**: Each just-in-time configuration method (`get_monitored_operations_config()`, `get_rv_instrumentation_config()`, `get_static_analysis_config()`) MUST resolve RVSEC_HOME using the three-level priority hierarchy: (1) `rvsec_root` field, (2) `RVSEC_HOME` environment variable, (3) `ConfigurationError`.

- **INV-EXP-06**: The `ExecutionController.setup()` method MUST be called before `ExecutionController.run()`. Calling `run()` without prior `setup()` MUST raise `RVExperimentExecutionError`.

- **INV-EXP-07**: When skip flags are used (`generate_monitors=False`, `instrument_apks=False`, `run_static_analysis=False`), the corresponding pre-processing step MUST NOT be executed. The `PreProcessor.process()` method MUST respect these boolean parameters and log a warning for each skipped step.

- **INV-EXP-08**: If APK instrumentation fails or the instrumentation module is not available, the `PreProcessor` MUST copy original APKs to the instrumented directory (`out/instrumented_apks/`) as a fallback. The experiment MUST NOT abort due to instrumentation failure.

- **INV-EXP-09**: The tool specification DSL parsing MUST handle commas inside parameter sections correctly. A comma followed by a parameter-like token (containing `=`) MUST be treated as a parameter separator within the same tool spec, not as a tool separator.

- **INV-EXP-11**: The `PostProcessor` MUST generate an `instrument_errors.json` file in the results directory, even if no instrumentation errors occurred (in which case the file contains an empty JSON object `{}`).

- **INV-EXP-12**: `ExperimentConfig.model_post_init()` MUST set default values for `name` (timestamp-based), `output_dir` ("out"), `results_dir` ("results"), and `created_at` (ISO timestamp) when these fields are empty or None.

- **INV-EXP-13**: When resuming an experiment (via `--resume-dir` or via `--name` with an existing `tasks.json`), all three pre-processing skip flags MUST be set to `True` regardless of their CLI values. This invariant ensures that pre-processing artifacts from the original run are reused intact. The `apks_dir` for the platform MUST point to the instrumented APKs directory from the original run — if the user provides `--apks-dir` pointing to non-instrumented APKs during a resume, the pre-processing skip flags mean those APKs will be used as-is (without instrumentation), resulting in 0% coverage. This trade-off is documented in CLAUDE.md under "Reusing Pre-Processed Artifacts."

- **INV-EXP-14**: The experiment results directory MUST be a flat path without internal nesting. `ExperimentController` MUST use `config.results_dir` directly as the results directory — it MUST NOT append `config.name` or any other subdirectory component. The CLI layer (`__main__.py`) is responsible for constructing the complete results path (e.g., `results/my_experiment/` or `results/cli_experiment_20260212_abc123/`) before passing it to `ExperimentConfig.results_dir`. Specifically: when `ExperimentController.__init__()` is called with `config.results_dir = "results/my_experiment"`, then `self.results_dir` MUST be `"results/my_experiment"` (not `"results/my_experiment/my_experiment"`), `tasks.json` MUST be written to `results/my_experiment/tasks.json`, and all result artifacts (summary.csv, errors.csv, etc.) MUST be in `results/my_experiment/`.

## Requirements

### Requirement: Three-Phase Workflow (FR15, NFR08)

The Experiment Orchestration domain MUST implement a three-phase sequential workflow that coordinates the complete experiment lifecycle: pre-processing, execution, and post-processing. This design exists because a complete RV-Android experiment involves three distinct concerns -- preparing artifacts (monitors, instrumented APKs, static analysis data), running test generation tools on emulators, and collecting post-experiment metadata -- each requiring different sub-modules with different failure modes and skip capabilities.

The `ExperimentController` is the sole orchestrator. It instantiates `PreProcessor`, `ExecutionController`, and `PostProcessor` during `__init__()` and calls them in sequence during `run()`. The controller MUST NOT bypass any phase; however, individual operations within Phase 1 MAY be skipped via boolean flags.

Phase 1 (pre-processing) MUST support three independent operations: monitor generation, APK instrumentation, and static analysis. Each operation MAY be individually skipped without affecting the others. The operations MUST execute in the order: monitor generation, then instrumentation, then static analysis. This ordering exists because instrumentation depends on generated monitors, and static analysis operates on instrumented APKs (preferring them over originals).

Phase 2 (execution) MUST translate experiment configuration into a `PlatformConfig`, create a `Platform` instance, and call `Platform.run()`. The `ExecutionController` MUST NOT perform any task management, emulator control, or result processing. It only reads the aggregate result counts (`total_tasks`, `successful_tasks`, `failed_tasks`) returned by `Platform.run()`.

Phase 3 (post-processing) MUST generate instrumentation errors JSON and completion diagnostics. It MUST NOT generate CSV or JSON result files; those are produced by rv-platform during Phase 2.

#### Scenario: Full Experiment With All Phases Enabled

- **WHEN** an `ExperimentConfig` is created with `generate_monitors=True`, `instrument_apks=True`, `run_static_analysis=True`, a valid `apks_dir` containing at least one APK, at least one `ToolConfig`, and a valid `RVSEC_HOME` path
- **THEN** `ExperimentController.run()` MUST execute Phase 1 (PreProcessor.process) with all three operations enabled
- **AND** Phase 1 MUST produce files in `out/monitors/`, `out/instrumented_apks/`, and static analysis files alongside instrumented APKs
- **AND** Phase 2 (ExecutionController) MUST create a PlatformConfig with `apks_dir` pointing to `out/instrumented_apks/`
- **AND** Phase 3 (PostProcessor) MUST create `instrument_errors.json` and `experiment_completion.json` in the results directory

#### Scenario: Experiment With All Pre-Processing Skipped

- **WHEN** an `ExperimentConfig` is created with `generate_monitors=False`, `instrument_apks=False`, `run_static_analysis=False`
- **THEN** `PreProcessor.process()` MUST NOT invoke monitor generation, instrumentation, or static analysis
- **AND** `PreProcessor.process()` MUST log a warning for each skipped step
- **AND** `PreProcessor.get_instrumented_apks()` MUST return App objects from the original `apks_dir` as fallback
- **AND** Phase 2 MUST proceed with the original (non-instrumented) APKs
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

### Requirement: CLI with Tool Specification DSL (FR16, NFR05)

The Experiment Orchestration domain MUST provide a Click-based CLI with four commands (`run`, `config`, `list-tools`, `validate`) and a tool specification DSL that allows compact, composable tool configuration from the command line. This design exists because experiments often involve comparing multiple tools with different configurations, and a verbose JSON-only interface would be impractical for iterative experimentation.

The `run` command MUST support two mutually exclusive modes: CLI mode (tool specifications via `--tools` argument) and config mode (JSON file via `--config` argument). When `--config` is provided, all other tool/execution arguments are ignored and the configuration is loaded from the file.

The `run` command MUST also support experiment resume via `--resume-dir` flag (pointing to an existing results directory) and via `--name` flag (detecting existing results directory with `tasks.json`). When resume is detected, pre-processing skip flags MUST be auto-set to `True` as defined by INV-EXP-13. This resume capability is required for Docker containerization — containers may be killed and restarted by resource limits, orchestrators, or watchdog processes, and without functional resume, a restart means discarding all completed work.

The tool specification DSL format MUST be: `tool_name[:variant1][:variant2][@param1=value1,param2=value2]`. Multiple tools are separated by commas. The parser MUST correctly handle commas that appear inside parameter sections (e.g., `rvagent:multimode@temperature=0.3,top_p=0.6` is one tool, not two).

The CLI MUST provide skip flags (`--skip-monitors`, `--skip-instrument`, `--skip-static`) that disable the corresponding pre-processing phase. These flags map directly to the `generate_monitors`, `instrument_apks`, and `run_static_analysis` fields of `ExperimentConfig`.

The CLI MUST provide `--no-window/--window` flag to control emulator visibility, with `--no-window` (headless) as the default.

#### Scenario: Single Tool With Default Configuration

- **WHEN** the user runs `rv-experiment run --tools monkey`
- **THEN** the CLI MUST parse the tool specification into `ToolConfig(name="monkey", variants=[], parameters={})`
- **AND** an `ExperimentConfig` MUST be created with `tool_configs` containing that single ToolConfig
- **AND** the experiment MUST execute with default timeout (300s), default repetitions (1), and default specification set (jca)

#### Scenario: Multiple Tools With Variants and Parameters

- **WHEN** the user runs `rv-experiment run --tools monkey,droidbot:dfs_greedy,rvagent:multimode@temperature=0.3`
- **THEN** the CLI MUST parse three ToolConfig objects:
  - `ToolConfig(name="monkey", variants=[], parameters={})`
  - `ToolConfig(name="droidbot", variants=["dfs_greedy"], parameters={})`
  - `ToolConfig(name="rvagent", variants=["multimode"], parameters={"temperature": "0.3"})`
- **AND** `ExperimentConfig.tool_configs` MUST contain all three in order

#### Scenario: Parameters With Commas Inside Tool Specification

- **WHEN** the user runs `rv-experiment run --tools rvagent:multimode@temperature=0.3,top_p=0.6`
- **THEN** the DSL parser MUST treat `temperature=0.3` and `top_p=0.6` as parameters of the same `rvagent` tool
- **AND** MUST NOT split this into two separate tool specifications
- **AND** the resulting ToolConfig MUST have `parameters={"temperature": "0.3", "top_p": "0.6"}`

#### Scenario: Configuration File Mode

- **WHEN** the user runs `rv-experiment run --config experiment_config.json`
- **THEN** the CLI MUST load the configuration from the JSON file using `ExperimentConfig.from_file()`
- **AND** MUST call `experiment_config.validate()` before execution
- **AND** MUST NOT parse the `--tools` argument

#### Scenario: Custom Specification Set Without Directory

- **WHEN** the user runs `rv-experiment run --tools monkey --specification-set custom` without providing `--custom-specs-dir`
- **THEN** the CLI MUST raise a `ClickException` with message: "Custom specification directory (--custom-specs-dir) is required when using --specification-set=custom"
- **AND** the experiment MUST NOT start

#### Scenario: Unknown Tool Warning

- **WHEN** the user specifies a tool name that is not registered in the ToolRegistry (e.g., `rv-experiment run --tools unknown_tool`)
- **THEN** the CLI MUST log a warning: "Tool 'unknown_tool' not found in registry. Available tools: ..."
- **AND** the tool specification MUST still be parsed and included in the configuration (validation happens later during `ExperimentConfig.validate()`)

#### Scenario: Resume With --resume-dir Flag

- **WHEN** the user runs `rv-experiment run --resume-dir ./results/my_experiment`
- **THEN** the CLI MUST use `./results/my_experiment` as the experiment results directory
- **AND** MUST auto-set `generate_monitors=False`, `instrument_apks=False`, `run_static_analysis=False`
- **AND** MUST log "Resuming experiment from ./results/my_experiment"

#### Scenario: Resume With --name Detecting Existing Results

- **WHEN** the user runs `rv-experiment run --tools monkey --name my_experiment`
- **AND** the directory `results/my_experiment/` already exists and contains `tasks.json`
- **THEN** the CLI MUST enable resume mode and auto-skip pre-processing
- **AND** MUST log "Resuming experiment 'my_experiment' — auto-skipping pre-processing"

### Requirement: Experiment Resume via CLI (FR16-ext)

The CLI MUST support two mechanisms for resuming interrupted experiments: an explicit `--resume-dir` flag pointing to an existing results directory, and an implicit resume via the `--name` flag when the named results directory already contains a `tasks.json` file. Both mechanisms MUST auto-skip all pre-processing phases (monitor generation, APK instrumentation, static analysis) because the pre-processing artifacts — generated monitors in `out/monitors/`, instrumented APKs in `out/instrumented_apks/`, and static analysis files (`.wtg`, `.gesda`, `.reach`) — already exist from the original run and re-generating them would waste time and potentially overwrite the artifacts that the platform needs for coverage tracking.

Resume detection relies on the presence of a `tasks.json` file in the target results directory. This file is written atomically by `TaskStorage` after each task state change (using write-to-temp-then-rename semantics with `fsync`), so its presence reliably indicates that a previous experiment run used this directory and reached at least the task generation phase. The platform's `_skip_completed_tasks()` handles the actual task-level skipping based on identity matching — rv-experiment's responsibility is limited to ensuring the same results directory is reused and that pre-processing is bypassed.

The auto-skip behavior on resume is formalized as INV-EXP-13. When resume is detected, the CLI sets `generate_monitors=False`, `instrument_apks=False`, and `run_static_analysis=False` regardless of what the user passed on the command line. This matches the rvsec-02/ICST pattern where Docker containers used `RV_SKIP_MONITORS=true`, `RV_SKIP_INSTRUMENT=true`, and `RV_SKIP_STATIC_ANALYSIS=true` environment variables for resumed containers, because re-running the pre-processing pipeline on already-instrumented APKs would overwrite them with freshly instrumented versions that may differ if the specification set or RVSEC tools have been updated.

The `--resume-dir` flag provides explicit control for advanced users and Docker automation (via the `RV_RESUME_DIR` environment variable in the Docker entry point). The `--name` flag provides implicit, ergonomic resume for interactive use — the researcher runs the same command twice and the system automatically detects the existing results. When both are provided, `--resume-dir` takes precedence because explicit intent overrides implicit detection.

#### Scenario: Resume With --resume-dir Flag

- **WHEN** the user runs `rv-experiment run --resume-dir ./results/my_experiment`
- **THEN** the CLI MUST use `./results/my_experiment` as the experiment results directory, bypassing the normal directory creation logic (`cli_experiment_YYYYMMDD_HHMMSS_uuid`)
- **AND** MUST auto-set `generate_monitors=False`, `instrument_apks=False`, `run_static_analysis=False`
- **AND** MUST log "Resuming experiment from ./results/my_experiment"
- **AND** the `--apks-dir` argument MUST be provided by the user (or default applies) — the CLI does NOT auto-detect the APKs directory from the results structure, because the user knows which APKs were used in the original run and should point to the instrumented APKs directory explicitly
- **AND** the platform MUST skip already-completed tasks via `_skip_completed_tasks()`

#### Scenario: Resume With --name Detecting Existing Results

- **WHEN** the user runs `rv-experiment run --tools monkey --name my_experiment`
- **AND** the directory `results/my_experiment/` already exists and contains a `tasks.json` file
- **THEN** the CLI MUST detect the existing experiment and enable resume mode
- **AND** MUST auto-set `generate_monitors=False`, `instrument_apks=False`, `run_static_analysis=False`
- **AND** MUST log "Resuming experiment 'my_experiment' — auto-skipping pre-processing"
- **AND** MUST use `results/my_experiment/` as the experiment results directory (not create a new one)
- **AND** the platform MUST skip already-completed tasks via `_skip_completed_tasks()`

#### Scenario: First Run With --name (No Existing Results)

- **WHEN** the user runs `rv-experiment run --tools monkey --name new_experiment`
- **AND** the directory `results/new_experiment/` does not exist
- **THEN** the CLI MUST create the results directory `results/new_experiment/` normally
- **AND** MUST NOT modify the skip flags (pre-processing runs as configured by the user)
- **AND** the experiment MUST execute as a fresh run with the deterministic name `new_experiment`

#### Scenario: --resume-dir With Non-Existent Directory

- **WHEN** the user runs `rv-experiment run --resume-dir ./results/nonexistent`
- **THEN** Click's `type=click.Path(exists=True)` MUST reject the argument before any experiment logic executes
- **AND** the CLI MUST display an error message indicating the directory does not exist
- **AND** the experiment MUST NOT start

#### Scenario: --resume-dir Overrides --name

- **WHEN** the user provides both `--resume-dir ./results/old_exp` and `--name new_exp`
- **THEN** `--resume-dir` MUST take precedence because it represents explicit intent
- **AND** the experiment MUST use `./results/old_exp` as the results directory
- **AND** the `--name` value MUST be ignored for directory selection purposes

### Requirement: Docker Execution Mode (FR16-ext, NFR08)

The experiment orchestration system MUST support execution inside Docker containers as a first-class deployment mode. This is not merely about packaging — Docker execution enables parallel experiment execution (multiple containers running simultaneously, each with its own emulator) and crash recovery (containers are killed and restarted routinely by orchestrators, resource limits, or watchdog processes). The rvsec-02/ICST study validated this pattern with 7 parallel containers over thousands of restarts.

Docker execution uses a shell entry point (`docker-entrypoint.sh`) that translates Docker environment variables to `rv-experiment` CLI arguments. This follows the standard Docker pattern: the Dockerfile sets ENV defaults, the user overrides them at `docker run` time, and the entry point assembles the CLI command. The entry point script MUST echo the generated command for debugging transparency and MUST support both execution mode (default, runs `rv-experiment run`) and interactive mode (when the user passes `bash` or `shell` as the command, drops into a shell for debugging).

Environment variables are categorized into two groups:

1. **CLI-translated variables**: Read by `docker-entrypoint.sh` and converted to `rv-experiment run` flags. Examples: `RV_TOOLS` (-> `--tools`), `RV_TIMEOUTS` (-> `--timeout`), `RV_EXPERIMENT_NAME` (-> `--name`), `RV_RESUME_DIR` (-> `--resume-dir`). These have no effect outside Docker unless a standalone script performs the same translation.

2. **Pass-through variables**: Read directly by Python modules via `os.environ.get()`. Examples: `RVSEC_HOME`, `ANDROID_HOME`, `RVAGENT_MODE`. These are set as container environment variables in `docker-compose.yml` and are NOT translated to CLI flags by the entry point.

The entry point MUST also support a startup delay (`RV_DELAY`) for staggering container startups in parallel execution. The first activities (emulator boot, APK instrumentation) consume significant CPU and I/O, so staggering prevents resource contention.

Docker Compose files provide two deployment patterns:

1. **Single container** (`docker-compose.yml`): One rvandroid container with a Humanoid service dependency and `docker.sock` mount for ARES/QTesting sibling containers.

2. **Parallel containers** (`docker-compose.parallel.yml`): YAML anchors define a base service (`x-rvandroid`), with N concrete services (rv01, rv02, ...) each having their own `RV_EXPERIMENT_NAME`, `RV_DEVICE_PORT`, `RV_DELAY`, and per-container result volumes. All containers share the same Humanoid REST service. Each container has its own `docker.sock` mount for independent ARES/QTesting sibling container spawning.

The `docker.sock` mount (`/var/run/docker.sock:/var/run/docker.sock`) in both compose files allows each rvandroid container to spawn ARES/QTesting sibling containers via the host's Docker daemon. Without this mount, Docker-based tools (ARES, QTesting) fail because there is no Docker daemon available inside the container. See the tools domain delta spec (INV-TOOL-15) for the network configuration of sibling containers.

#### Scenario: Docker Entry Point Translates Environment Variables to CLI

- **WHEN** a Docker container starts with `RV_TOOLS=monkey,droidbot`, `RV_TIMEOUTS=300`, `RV_EXPERIMENT_NAME=batch_01`, `RV_NO_WINDOW=true`
- **THEN** the entry point MUST generate: `uv run rv-experiment run --tools monkey,droidbot --timeout 300 --name batch_01 --no-window`
- **AND** MUST echo the generated command to stdout for debugging
- **AND** MUST use `exec` to replace the shell process with the Python process (proper signal handling)

#### Scenario: Docker Entry Point Supports Interactive Mode

- **WHEN** the user runs `docker run ... phtcosta/rvandroid:0.8.0 bash`
- **THEN** the entry point MUST detect the `bash` or `shell` argument
- **AND** MUST drop into an interactive bash shell instead of running the experiment
- **AND** the user MUST be able to run `rv-experiment` commands manually inside the container

#### Scenario: Docker Entry Point Applies Startup Delay

- **WHEN** a Docker container starts with `RV_DELAY=30`
- **THEN** the entry point MUST `sleep 30` before executing the experiment command
- **AND** MUST log the delay duration

#### Scenario: Docker Resume on Container Restart

- **WHEN** a Docker container with `RV_EXPERIMENT_NAME=batch_01` completes 3 out of 10 tasks and is killed
- **AND** a new container starts with the same `RV_EXPERIMENT_NAME=batch_01` and the same result volume mount
- **THEN** the entry point MUST generate the same `--name batch_01` CLI argument
- **AND** rv-experiment MUST detect `results/batch_01/tasks.json` and trigger resume mode (INV-EXP-13)
- **AND** the platform MUST skip the 3 completed tasks and execute the remaining 7

#### Scenario: Parallel Docker Execution With Independent Experiments

- **WHEN** `docker-compose.parallel.yml` is used with rv01 (`RV_EXPERIMENT_NAME=rv01`) and rv02 (`RV_EXPERIMENT_NAME=rv02`)
- **THEN** each container MUST use its own results directory (`results/rv01/`, `results/rv02/`)
- **AND** each container MUST use its own emulator port (`RV_DEVICE_PORT=5554`, `RV_DEVICE_PORT=5556`)
- **AND** each container MUST have its own `docker.sock` mount for independent ARES/QTesting sibling container spawning
- **AND** the Humanoid service MUST be shared across all containers (single instance)
- **AND** containers MUST be staggered via `RV_DELAY` to avoid resource contention during emulator boot

#### Scenario: docker.sock Mount Enables Docker-Based Tools

- **WHEN** a rvandroid container has `/var/run/docker.sock:/var/run/docker.sock` mounted
- **THEN** `AresTool._build_ares_command()` and `QTestingTool._build_qtesting_command()` MUST be able to execute `docker run` to spawn sibling containers
- **AND** the sibling containers MUST share the parent's network namespace via `--network container:$(hostname)` (INV-TOOL-15)

- **WHEN** a rvandroid container does NOT have the `docker.sock` mount
- **THEN** Docker-based tools (ARES, QTesting) MUST fail with a clear error when attempting `docker run`
- **AND** non-Docker tools (Monkey, DroidBot, APE, etc.) MUST continue to function normally

### Requirement: Just-in-Time Sub-Module Configuration (FR17, NFR05)

The Experiment Orchestration domain MUST create sub-module configurations only when they are needed during experiment execution. This design exists because eager construction of all sub-module configurations during `ExperimentConfig.__init__()` would: (a) fail if optional sub-modules are not installed, (b) validate paths that may not be needed (e.g., RVSEC_HOME when pre-processing is skipped), and (c) couple configuration construction to the full module dependency tree.

`ExperimentConfig` MUST provide three JIT configuration methods:
- `get_monitored_operations_config()` -- creates `RVGeneratorConfig` for rv-monitor-generator
- `get_rv_instrumentation_config()` -- creates `RVInstrumentationConfig` for rv-instrumentation
- `get_static_analysis_config()` -- creates `RVStaticAnalysisConfig` for rv-static-analysis

Each method MUST resolve RVSEC_HOME using the three-level priority hierarchy (INV-EXP-05) and MUST construct the appropriate sub-module configuration with validated paths. These methods are called only by `PreProcessor` during Phase 1 when the corresponding operation is enabled.

The `get_monitored_operations_config()` method MUST select the specification directory based on the `specification_set` field: "jca" maps to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca`, "generic" maps to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic`, and "custom" uses the `custom_specs_dir` field directly.

The `get_module_config()` method MUST serve as a generic dispatcher that routes module names to the appropriate JIT method. It MUST support the module names "rv-monitor-generator", "rv-instrumentation", and "rv-static-analysis".

#### Scenario: JIT Configuration for Monitor Generation With JCA Specs

- **WHEN** `PreProcessor._generate_monitors()` calls `config.get_monitored_operations_config()` with `specification_set="jca"` and `RVSEC_HOME="/path/to/rvsec"`
- **THEN** the method MUST return an `RVGeneratorConfig` instance with:
  - `rvsec_root="/path/to/rvsec"`
  - `javamop_bin="/path/to/rvsec/javamop/bin/javamop"`
  - `rvmonitor_bin="/path/to/rvsec/rv-monitor/bin/rv-monitor"`
  - `mop_specs_dir="/path/to/rvsec/rvsec/rvsec-mop/src/main/resources/jca"`
  - `aspects_dir="/path/to/rvsec/rvsec/rvsec-mop/src/main/resources/aspect"`

#### Scenario: JIT Configuration for Custom Specification Set

- **WHEN** `config.get_monitored_operations_config()` is called with `specification_set="custom"` and `custom_specs_dir="/my/specs"`
- **THEN** the method MUST validate that `/my/specs` is a directory containing at least one `.mop` file
- **AND** MUST return an `RVGeneratorConfig` with `mop_specs_dir="/my/specs"`
- **AND** if the directory does not contain `.mop` files, MUST raise `ConfigurationError` with message: "Invalid specs dir: /my/specs"

#### Scenario: JIT Configuration for Custom Aspects Directory

- **WHEN** `config.get_monitored_operations_config()` is called with `custom_aspects_dir="/my/aspects"`
- **THEN** the method MUST use `/my/aspects` as the `aspects_dir` in the returned `RVGeneratorConfig`
- **AND** MUST NOT use the default RVSEC aspects directory

#### Scenario: RVSEC_HOME Not Available

- **WHEN** a JIT configuration method is called but neither `rvsec_root` is set in configuration nor `RVSEC_HOME` environment variable is defined
- **THEN** the method MUST raise `ConfigurationError` with message: "RVSEC_HOME not found in configuration or environment. Set rvsec_root field in configuration or RVSEC_HOME environment variable"

#### Scenario: RVSEC_HOME Path Does Not Exist

- **WHEN** `rvsec_root` is set to "/nonexistent/path" in configuration
- **THEN** `get_effective_rvsec_root()` MUST raise `ConfigurationError` with message: "Configured rvsec_root path does not exist: /nonexistent/path"

#### Scenario: JIT Configuration Not Called When Phase Is Skipped

- **WHEN** `generate_monitors=False` is set in ExperimentConfig
- **THEN** `PreProcessor.process()` MUST NOT call `config.get_monitored_operations_config()`
- **AND** missing or invalid RVSEC_HOME MUST NOT cause an error if all three pre-processing phases are skipped

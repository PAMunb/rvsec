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
              +---> EventBus: EXPERIMENT_COMPLETED
```

### Key Design Decisions and Constraints

1. **No data transfer between rv-platform and rv-experiment.** The execution phase delegates to rv-platform, which handles all task execution and result processing. rv-experiment does not read back task results, coverage data, or error logs. Results persist inside rv-platform's results directory. This eliminates coupling and prevents rv-experiment from duplicating rv-platform's responsibilities.

2. **Just-in-time sub-module configuration.** `ExperimentConfig` does not eagerly create configurations for rv-monitor-generator, rv-instrumentation, or rv-static-analysis. Instead, it exposes `get_monitored_operations_config()`, `get_rv_instrumentation_config()`, and `get_static_analysis_config()` methods that construct and validate sub-module configuration objects only when invoked by the `PreProcessor`. This reduces initialization overhead and avoids errors for sub-modules that will be skipped.

3. **Skip flags for artifact reuse.** The CLI provides `--skip-monitors`, `--skip-instrument`, and `--skip-static` flags. When skip flags are used, the corresponding pre-processing step is not executed, and the `--apks-dir` MUST point to a directory containing previously instrumented APKs. If skip flags are used with non-instrumented APKs, the experiment will run but coverage will be 0% because the APKs lack runtime verification monitors.

4. **Clean separation: orchestration vs. execution.** rv-experiment handles only orchestration (phase sequencing, configuration assembly, event publishing). rv-platform handles execution (task generation, emulator management, tool execution, coverage tracking, result processing). rv-experiment never manages emulators, tasks, or results directly.

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
  experiment_dir: str                 # Derived: results_dir/name
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
- EventBus events: `EXPERIMENT_STARTED`, `EXPERIMENT_COMPLETED`, `EXPERIMENT_FAILED`, `WORKFLOW_COMPLETED`, `MONITOR_GENERATED`, `INSTRUMENTATION_COMPLETED`, `STATIC_ANALYSIS_COMPLETED`

**Dependencies:**
- rv-android-core: ErrorHandler, EventBus, LoggingManager, BaseValidatedModel, App, constants
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
- `EventBus events` -- Published to `LIFECYCLE_CHANNEL` and `ANALYSIS` channels (destination: EventBus subscribers)

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

- **INV-EXP-10**: The `ExperimentController` MUST publish an `EXPERIMENT_COMPLETED` or `EXPERIMENT_FAILED` event via EventBus at the end of every experiment run, regardless of success or failure.

- **INV-EXP-11**: The `PostProcessor` MUST generate an `instrument_errors.json` file in the results directory, even if no instrumentation errors occurred (in which case the file contains an empty JSON object `{}`).

- **INV-EXP-12**: `ExperimentConfig.model_post_init()` MUST set default values for `name` (timestamp-based), `output_dir` ("out"), `results_dir` ("results"), `experiment_dir` (results_dir/name), and `created_at` (ISO timestamp) when these fields are empty or None.

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
- **AND** an `EXPERIMENT_COMPLETED` event MUST be published to the EventBus

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
- **AND** `ExperimentController.run()` MUST catch the error, log it, publish an `EXPERIMENT_FAILED` event, and return `False`

#### Scenario: No APKs Available for Execution

- **WHEN** `PreProcessor.get_instrumented_apks()` returns an empty list (no instrumented APKs found and no original APKs available)
- **THEN** `ExperimentController._run_execution()` MUST log "No APKs available for execution" and return `False`
- **AND** Phase 2 MUST NOT create a Platform instance or attempt execution
- **AND** Phase 3 MUST still execute to produce diagnostics

### Requirement: CLI with Tool Specification DSL (FR16, NFR05)

The Experiment Orchestration domain MUST provide a Click-based CLI with four commands (`run`, `config`, `list-tools`, `validate`) and a tool specification DSL that allows compact, composable tool configuration from the command line. This design exists because experiments often involve comparing multiple tools with different configurations, and a verbose JSON-only interface would be impractical for iterative experimentation.

The `run` command MUST support two mutually exclusive modes: CLI mode (tool specifications via `--tools` argument) and config mode (JSON file via `--config` argument). When `--config` is provided, all other tool/execution arguments are ignored and the configuration is loaded from the file.

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

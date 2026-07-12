# Specification: Execution Platform

## Purpose

rv-platform is the central execution engine for Android testing experiments in the RV-Android framework. It sits between the experiment orchestrator (rv-experiment) and the individual testing tools, providing the machinery that turns a declarative experiment configuration into concrete task executions with measurable results.

The fundamental problem rv-platform solves is: given a set of APK files, a set of testing tools (each with variants), repetition counts, and timeout values, execute every combination on an Android emulator while tracking method coverage and specification violations in real-time, then produce standardized output files for research analysis. This involves coordinating multiple concurrent concerns -- emulator lifecycle, APK installation, logcat capture, coverage tracking, static analysis data loading, tool execution, and result generation -- in a reliable and reproducible manner.

### Position in the Pipeline

rv-platform operates in the execution phase of the three-phase experiment workflow:

```
rv-experiment (orchestration)
  |
  |  Phase 1: Pre-processing (monitors, instrumentation, static analysis)
  |
  +---> rv-platform (execution)          <-- this domain
  |       |
  |       +---> Task Generation
  |       +---> For each task:
  |       |       Phase 1: Load static analysis data
  |       |       Phase 2: Initialize coverage tracker
  |       |       Phase 3: Emulator session
  |       |         - Start emulator (dynamic port)
  |       |         - Install APK
  |       |         - Start logcat capture
  |       |         - Start coverage tracking
  |       |         - Execute testing tool
  |       |         - Stop coverage tracking
  |       |         - Stop logcat capture
  |       |       Cleanup all components
  |       +---> Result Processing (CSV/JSON generation)
  |
  |  Phase 3: Post-processing (diagnostics)
```

rv-experiment creates a `PlatformConfig` and delegates execution to `Platform.run()`. rv-platform generates tasks, executes them, and writes results to disk. rv-experiment does not receive data back programmatically -- results stay on disk in the results directory.

rv-platform can also be used standalone via its own CLI (`rv-platform run`), bypassing rv-experiment entirely. In standalone mode, the user provides tool names and APK directory directly, and rv-platform handles everything from task generation through result output.

### Key Design Decisions

1. **Component-Based Execution**: Instead of a monolithic executor, `TaskExecutor` delegates to pluggable components (`StaticAnalysisComponent`, `EmulatorComponent`, `LogcatComponent`, `CoverageComponent`, `ToolExecutionComponent`). Each component follows a standardized `initialize/execute/cleanup` lifecycle defined by the `ITaskComponent` interface. This enables adding new execution phases without modifying the executor itself.

2. **Coordinated Phase Execution**: Components do not all execute in a flat sequence. The executor implements three distinct phases: Phase 1 runs static analysis loading outside the emulator session, Phase 2 initializes the coverage tracker outside the emulator session, and Phase 3 runs the emulator session with logcat capture, coverage tracking, and tool execution inside the emulator context manager. This ordering ensures static analysis data is available before the coverage tracker is configured, and that the emulator is only started when all preparation is complete.

3. **Tool Timeout as Success**: When a testing tool exceeds its configured timeout, `ToolExecutionComponent` catches the `RVToolTimeoutError` and returns `True` (success). This is by design: timeouts are the normal termination mechanism for time-bounded experiments. The tool runs for the configured duration, the timeout fires, execution stops, and results are collected. This is not an error condition.

4. **Atomic Task Persistence**: `TaskStorage` uses write-to-temp-file-then-rename for atomic saves (`fsync` + `shutil.move`), ensuring the tasks.json file is never in a partially written state. This protects against data loss if the process is interrupted during a write. Transaction support (`begin_transaction/commit_transaction/rollback_transaction`) enables batched updates.

5. **Non-Critical Static Analysis**: Static analysis data loading is treated as non-critical. If static analysis files are not found or parsing fails, execution continues without static data. Coverage tracking will be limited (no MOP method classification, no REACH-based universe), but the experiment still runs. This is logged as a warning, not an error.

6. **Dynamic Port Allocation**: `EmulatorComponent` supports dynamic emulator port allocation (default port 5554, configurable via `tool_config.parameters["device_port"]`). This enables parallel task execution where each task gets a unique emulator port to avoid conflicts.

### Data Models

```
PlatformConfig (Pydantic BaseValidatedModel):
  apks_dir: str               # Directory containing APK files (validated: must exist, must be directory)
  tools: List[ToolConfig]      # At least one tool required
  repetitions: int             # >= 1, default 1
  timeouts: List[int]          # At least one timeout, each >= 1 second
  max_parallel_tasks: int      # >= 1, default 1 (future feature)
  no_window: bool              # Headless emulator mode, default False
  results_dir: str             # Output directory, default "results"
  task_storage_file: str       # Persistence file name, default "tasks.json"
  log_level: str               # DEBUG|INFO|WARNING|ERROR|CRITICAL, default "INFO"
  skip_result_processing: bool # Skip CSV/JSON generation, default False

TaskState (Enum) [rv_android_core]:
  CREATED                      # Task has been created
  INITIALIZING                 # Task is being initialized
  READY                        # Task is ready for execution
  RUNNING                      # Task is currently executing
  COMPLETED                    # Task finished successfully (including timeout)
  ERROR                        # Task failed with an error
  CANCELED                     # Task was canceled

ExperimentMetadata (Pydantic BaseValidatedModel):
  experiment_id: str           # Unique experiment identifier
  start_time: datetime         # Experiment start timestamp
  config_checksum: str         # SHA-256 of experiment configuration JSON
  current_status: str          # running|completed|failed

StorageConfig (Pydantic BaseValidatedModel):
  enable_metadata: bool        # Store experiment metadata, default True
  enable_statistics: bool      # Calculate statistics on save, default True
  auto_save: bool              # Save after each task update, default True
  compression: bool            # Enable storage compression, default False
  backup_count: int            # Number of backup files, default 3

ExperimentStatistics (Pydantic BaseValidatedModel):
  total_tasks: int             # Total task count
  completed_tasks: int         # Completed task count
  failed_tasks: int            # Failed task count
  pending_tasks: int           # Pending task count
  completion_percentage: float # (completed / total) * 100
  average_execution_time: float # Average execution time in seconds
  total_execution_time: float  # Sum of execution times in seconds
  last_updated: datetime       # Last calculation timestamp
```

### Relationships with Other Domains

**Upstream (consumed by rv-platform)**:
- **rv-android-core**: Domain models (`Task`, `TaskConfiguration`, `TaskFactory`, `TaskState`, `App`, `ToolConfig`), `ErrorHandler`, `LoggingManager`, `PerformanceMonitor`, `EmulatorManager`, `LogcatManager`, `BaseValidatedModel`, `AbstractTool`
- **rv-tools**: `ToolFactory` and `ToolRegistry` for resolving tool names/variants to configured tool instances
- **rv-coverage**: `CoverageTracker` for real-time logcat-based method coverage tracking, `logcat_parser` for parsing existing logcat files
- **rv-static-analysis**: `static_analysis_parser` for loading GATOR/GESDA/REACH data files

**Downstream (produced by rv-platform)**:
- **rv-experiment**: Receives no programmatic data; reads results from disk (CSV/JSON files, tasks.json)
- **Researchers/Analysis tools**: Consume the output files (coverage.csv, errors.csv, summary.csv, results.json, performance.csv)

**Lateral**:
- **rv-agent** (via rvagent-tool): Registered as a tool in rv-tools; executed by `ToolExecutionComponent` like any other tool
- **Testing tools** (Monkey, DroidBot, etc.): Registered as tools in rv-tools; executed by `ToolExecutionComponent`

## Data Contracts

### Input

- `PlatformConfig` -- Complete platform configuration (from rv-experiment via `PlatformConfig` construction, or from CLI arguments, or from JSON file)
- `APK files: List[Path]` -- APK files discovered in `config.apks_dir` via `glob("*.apk")`, sorted alphabetically
- `Static analysis files: *.reach, *.wtg, *.gesda` -- Optional files co-located with APKs or in `apks_dir`, copied to task results directory before loading (source: rv-static-analysis pre-processing)

### Output

- `coverage.csv` -- Per-method coverage data with progressive metrics; columns: `apk, rep, timeout, tool, time, class, method, signature, cov_class, cov_act, cov_method, cov_rv_method`
- `errors.csv` -- Monitored operations violations; columns: `apk, rep, timeout, tool, time, spec, class, method, message, unique_msg`
- `summary.csv` -- Aggregate metrics per task; columns: `apk, rep, timeout, tool, cov_act, cov_method, cov_rv_method, errors`
- `results.json` -- Hierarchical JSON keyed by `apk > repetition > timeout > tool`, containing summary metrics and monitored operations error details
- `performance.csv` -- Task execution timing; columns vary by mode (basic: `apk, rep, timeout, tool, execution_time_seconds, task_state, monitoring_enabled, timestamp`; detailed: `apk, rep, timeout, tool, metric_name, metric_value, metric_unit, metric_timestamp, task_id, context_info`)
- `tasks.json` -- Persistent task state with experiment metadata and statistics for experiment continuation
- `Dict[str, Any]` -- Execution summary returned from `Platform.run()` containing `total_tasks`, `successful_tasks`, `failed_tasks`, `success_rate`, `total_execution_time`, `average_execution_time`, and per-task `results` list

### Side-Effects

- **Android Emulator**: Starts and stops Android emulator instances via `EmulatorManager`; installs APK on the emulator; clears logcat buffer
- **Logcat Capture**: Starts a background logcat capture process writing to a file on disk; stopped after tool execution
- **File System**: Creates results directory, writes CSV/JSON output files, copies static analysis files from APK directory to task results directory, creates temporary files during atomic save (`.tmp` suffix)
- **PerformanceMonitor**: Records timing metrics for task execution, component execution, and environment setup

### Error

- `EmulatorError` -- Raised when emulator startup fails or APK installation fails; propagated from `EmulatorComponent`
- `TaskExecutionError` -- Raised when a component execution fails (static analysis, coverage, tool execution) and the failure is critical; raised by `TaskExecutor._execute_coordinated_components()`
- `AnalysisError` -- Raised when coverage tracker initialization, start, stop, or result processing fails; handled by `CoverageComponent` with `ErrorHandler` decorator
- `RVToolTimeoutError` -- Raised by testing tools when execution exceeds the configured timeout; caught by `ToolExecutionComponent` and treated as successful completion (returns `True`)
- `RVToolExecutionError` -- Raised by testing tools when an actual execution failure occurs (not a timeout); caught by `ToolExecutionComponent` and returned as failure (returns `False`)
- `ValueError` -- Raised by `PlatformConfig` validators (empty APK directory, no APK files found, no tools specified, invalid repetitions, invalid timeouts, invalid log level) and by `Platform._load_tool()` when tool loading fails

## Invariants

- **INV-PLT-01**: The system MUST generate exactly `|APKs| x |tool_configs| x repetitions x |timeouts|` tasks during task generation. Each ToolConfig represents one tool+variant pair; variant expansion is handled at the CLI parser layer before reaching the platform.

- **INV-PLT-02**: Every task MUST transition through states in a valid sequence. The only valid terminal states are `COMPLETED` and `ERROR`. A task in state `RUNNING` MUST transition to either `COMPLETED` or `ERROR`. A task MUST NOT transition from a terminal state to any other state.

- **INV-PLT-03**: `TaskStorage.save()` MUST use atomic file operations (write to temporary file, `fsync`, then rename). The storage file MUST NOT be left in a partially written state even if the process is interrupted during a write.

- **INV-PLT-04**: When `RVToolTimeoutError` is raised during tool execution, `ToolExecutionComponent.execute()` MUST return `True` (success) and MUST NOT propagate the exception. Tool timeouts are the expected termination mechanism for time-bounded experiments.

- **INV-PLT-05**: Static analysis data loading failure MUST NOT prevent task execution. If `StaticAnalysisComponent.execute()` fails to load static data, it MUST return `True` and log a warning. The task continues without static analysis data.

- **INV-PLT-06**: All registered components MUST have their `cleanup()` method called, even if a preceding component fails during execution. Component cleanup failures MUST be logged as warnings but MUST NOT propagate as exceptions.

- **INV-PLT-07**: `TaskStorage` MUST be thread-safe. All public methods that read or modify the task dictionary MUST acquire the `RLock` before accessing shared state.

- **INV-PLT-08**: When `auto_save` is `True` in `StorageConfig`, `TaskStorage.update_task()` MUST call `save()` after updating the task dictionary. When `auto_save` is `False`, `save()` MUST NOT be called automatically.

- **INV-PLT-09**: `PlatformConfig` MUST validate that `apks_dir` exists and is a directory, that at least one tool is specified, that `repetitions >= 1`, that all timeouts are `>= 1`, and that `log_level` is one of `DEBUG, INFO, WARNING, ERROR, CRITICAL`. Validation MUST occur at construction time via Pydantic field validators.

- **INV-PLT-10**: The `ResultProcessorComponent` MUST only process tasks with `TaskState.COMPLETED`. Tasks in any other state MUST be excluded from CSV/JSON output generation.

- **INV-PLT-11**: During a `TaskStorage` transaction, changes MUST be buffered in `transaction_tasks` and MUST NOT be applied to the main `tasks` dictionary until `commit_transaction()` is called. `rollback_transaction()` MUST discard all buffered changes.

- **INV-PLT-12**: `ExperimentMetadata.config_checksum` MUST be computed as the SHA-256 hex digest of the JSON-serialized configuration dictionary with sorted keys. `check_continuation_compatibility()` MUST return `True` only when the new configuration produces an identical checksum.

- **INV-PLT-13**: Phase 3 (emulator session) in `TaskExecutor._execute_coordinated_components()` MUST execute within the emulator context manager. If either the `EmulatorComponent` or `ToolExecutionComponent` is missing, the emulator session MUST be skipped with a warning.

- **INV-PLT-14**: `ResultProcessorComponent` MUST generate all five output files (`coverage.csv`, `errors.csv`, `summary.csv`, `results.json`, `performance.csv`) when at least one completed task exists. If no completed tasks exist, it MUST log a warning and skip file generation.

- **INV-PLT-15**: `ResultProcessorComponent._resolve_static_data(task)` MUST obtain the per-APK results directory as follows: use `task.results_dir` when it is a non-empty string; otherwise, when `task.results_dir` is empty (the resume case, where it was not serialized) and `task.result.logcat_file` is set, derive it as `os.path.dirname(task.result.logcat_file)` (at runtime `task.results_dir == os.path.dirname(task.result.logcat_file)`, both built from `base_results_dir / apk_name`). With that directory, `_reconstruct_repository_from_logcat(task)` MUST invoke `parse_logcat_file(logcat_file, static_data)` with a non-`None` `static_data` whenever the static-analysis JSON exists at `<derived_dir>/f"{task.config.apk_name}.json"`. When `task.static_data` is already populated, that value MUST be reused; when it is `None`, the method MUST call `static_analysis_parser.read_static_analysis_files(<derived_dir>, task.config.apk_name, task.app.code_package if task.app else None)` (note `code_package=None` is tolerated — the GATOR JSON's reachability is already filtered to app classes). If the JSON is absent, the method MUST log a warning, record the task as having unresolved static data, and proceed with `static_data=None` for coverage purposes — in that degraded case `errors` (including the `total_errors`/`unique_errors` aggregates, see analysis INV-ANA-25) are still reliable but per-method coverage MUST be zero. The unresolved count MUST be **at most once per task**, achieved with two fields of disjoint responsibility (not a single overloaded sentinel): (1) `task.static_data` MUST be assigned a *valid* `StaticAnalysisData` on every path — an **empty** `StaticAnalysisData()` in the unresolved case (JSON absent or parser raised) — so it doubles as the parse memo (non-`None` short-circuits re-entry) AND remains a legal argument to `parse_logcat_file`; (2) the count MUST be tracked on a component-level set of task ids (`_unresolved_task_ids`), guarded by membership, so re-entry from any of the four reconstruction call sites (`_write_task_coverage_data`, `_write_task_summary_data`, `_write_task_error_data`, `_extract_task_data`) neither re-parses the JSON nor re-counts. Consequently `static_analysis_parser.read_static_analysis_files` MUST be invoked **at most once per task** across all writers (observable via call count). The count is a property of the task, not of the writer pass; the set MUST be (re)initialized at the start of `ResultProcessorComponent.execute()` so a subsequent consolidation pass reports only that pass.

- **INV-PLT-16**: `_write_task_coverage_data` and `_write_task_summary_data` MUST be unified to a single path that reads from `task.repository.calculate_metrics().to_dict()` after `_reconstruct_repository_from_logcat` has ensured `task.repository` is populated. The pre-existing cascade in `_write_task_summary_data` (3 tiers: `task.result.coverage_metrics` → `task.repository.calculate_metrics()` → zeros) and the `else` branch in `_write_task_coverage_data` (single fallback emitting empty `class/method/signature`) are removed entirely (P3, no backward-compatibility shim). When `_reconstruct_repository_from_logcat` returns `None` (logcat file missing), both writers MUST emit zeroed rows with an explicit warning — they MUST NOT fall back to reading stale serialized values from `task.result.coverage_metrics`.

- **INV-PLT-17**: The `cov_class` column in both `coverage.csv` and `summary.csv` MUST contain the `class_coverage` metric from `CoverageMetrics.to_dict()` (the percentage of called classes over total static classes). This corrects a pre-existing bug where the runtime path in `_write_task_coverage_data` wrote `method_coverage` into the `cov_class` slot.

- **INV-PLT-18**: Reconstructing a resumed task MUST produce CSV-equivalent results to the same task processed live. Formally, for any completed task `t`, the metrics computed from `Task.from_dict(t.to_dict())` followed by `_reconstruct_repository_from_logcat` (with the logcat and co-located static-analysis JSON present) MUST equal `t.repository.calculate_metrics().to_dict()` for every coverage and error field, within a rounding tolerance of `0.01`. This is the round-trip equivalence that any future change dropping a runtime field required for reconstruction MUST break. Additionally, when one or more resumed tasks have a non-empty logcat but reconstruct to zero per-method coverage (static data unresolved), `ResultProcessorComponent` MUST emit a single prominent aggregate WARNING reporting `N/M` affected tasks — the corruption MUST NOT be silent.

- **INV-PLT-19**: The headers and column order of `coverage.csv`, `errors.csv`, and `summary.csv` MUST remain byte-identical to baseline; the diagnostic feature MUST NOT add columns to them.
- **INV-PLT-20**: Diagnostic events MUST survive the resume reconstruction path — a task whose repository is rebuilt from its `.logcat` MUST still produce its `app_events.csv` rows.
- **INV-PLT-21**: WHEN `logcat_diagnostics` is `false`, `LogcatComponent` MUST start capture with the baseline tag set (no diagnostic tags passed).

- **INV-PLT-22**: The `rv-platform run --timeouts` argument MUST be declared as a string and parsed into `List[int]` with the same rules as the rv-experiment CLI (comma split, whitespace trim, positive integers only, order preserved, no deduplication). Invalid input MUST abort with a CLI usage error before `PlatformConfig` construction.
## Requirements
### Requirement: Android Emulator Management (FR07, NFR04, NFR07)

The platform MUST manage the full lifecycle of Android emulator instances during task execution. This includes starting the emulator with a named AVD, allocating a unique device port, installing the APK under test, and stopping the emulator after task completion. Emulator management is encapsulated in `EmulatorComponent`, which operates within the Phase 3 context manager in `TaskExecutor._run_emulator_session()`.

Dynamic port allocation is necessary because the ICST study runs multiple tool configurations across 188 applications, and future parallel execution requires isolated emulator instances. Each task can specify a unique `device_port` (default 5554) and `device_serial` (default `emulator-5554`) via `tool_config.parameters`, enabling multiple concurrent emulator sessions without port conflicts.

The emulator is started using the `EmulatorManager.start_emulator()` context manager, which ensures proper cleanup on both normal and exceptional exits. App installation is verified via `CommandResult.is_failure()` -- if installation fails, `EmulatorError` is raised and the task transitions to `ERROR` state.

#### Scenario: Successful Emulator Startup and APK Installation

- **WHEN** a task is being executed with `apk_name="cryptoapp.apk"` and `no_window=True`
- **THEN** `EmulatorComponent.start_emulator("RVSec")` MUST start the emulator in headless mode on the default port 5554
- **AND** `EmulatorComponent.install_app()` MUST install the APK on the emulator

#### Scenario: APK Installation Failure

- **WHEN** `EmulatorComponent.install_app()` is called and `EmulatorManager.install_app()` returns `False`
- **THEN** the component MUST raise `EmulatorError` with message containing the app name
- **AND** the error MUST be handled by `ErrorHandler` with task context
- **AND** the method MUST return `False`

#### Scenario: Dynamic Port Allocation for Parallel Execution

- **WHEN** a task has `tool_config.parameters = {"device_port": 5558, "device_serial": "emulator-5558"}`
- **THEN** `EmulatorComponent.start_emulator()` MUST pass port `5558` to `EmulatorManager.start_emulator()`
- **AND** `EmulatorComponent.install_app()` MUST pass `device_serial="emulator-5558"` to `EmulatorManager.install_app()`

#### Scenario: Skip Installation When Configured

- **WHEN** `task.config.skip_installation` is `True`
- **THEN** `EmulatorComponent.install_app()` MUST return `True` without calling `EmulatorManager.install_app()`
- **AND** a skip log message MUST be emitted

#### Scenario: Logcat Buffer Clearing

- **WHEN** `EmulatorComponent.clean_logcat()` is called
- **THEN** the component MUST call `EmulatorManager.clear_logcat()` to reset the logcat buffer
- **AND** if clearing fails, the error MUST be logged as a warning (non-critical)

### Requirement: Task Generation (FR08)

The platform MUST generate tasks as the Cartesian product of discovered APKs, configured tools (each ToolConfig representing one tool+variant pair), repetitions, and timeouts. Each unique combination produces exactly one `Task` object with a `TaskConfiguration` containing the APK name, tool configuration (name, variant, parameters), repetition number, and timeout value.

Task generation is the first step of `Platform.run()`. The platform discovers APK files by globbing `*.apk` in the configured `apks_dir` (sorted alphabetically). If no APK files are found, `Platform._discover_apks()` raises `ValueError`. For each APK, the platform iterates over all tool configs, repetition numbers (1 to `config.repetitions` inclusive), and timeout values. For each combination, a `Task` is created via `TaskFactory.create_task()`, associated with an `App` instance, and initialized with the results directory.

Variant expansion is handled at the CLI parser layer, not inside Platform. When the CLI receives `droidbot:dfs_greedy:bfs_greedy`, the parser creates two separate ToolConfig instances — `ToolConfig(name="droidbot", variant="dfs_greedy")` and `ToolConfig(name="droidbot", variant="bfs_greedy")`. Platform receives a flat list of ToolConfig objects with singular variants.

Tasks follow a lifecycle: `CREATED` (initial) -> `RUNNING` (when executor begins) -> `COMPLETED` (success, including timeout) or `ERROR` (failure). The `INITIALIZING`, `READY`, and `CANCELED` states are defined in `TaskState` but are not actively used by `TaskExecutor.execute()` in the current implementation.

#### Scenario: Basic Task Generation

- **WHEN** `apks_dir` contains 2 APK files, `tools` has 1 ToolConfig with `variant="default"`, `repetitions=1`, and `timeouts=[300]`
- **THEN** `Platform._generate_tasks()` MUST produce exactly 2 tasks (2 APKs x 1 tool_config x 1 rep x 1 timeout)
- **AND** each task MUST have an `App` instance set via `task.set_app()`
- **AND** each task MUST be initialized with the results directory via `task.initialize()`

#### Scenario: Multi-Variant Task Generation

- **WHEN** `tools` has 2 ToolConfig instances `[ToolConfig(name="droidbot", variant="dfs_greedy"), ToolConfig(name="droidbot", variant="bfs_greedy")]`, `repetitions=3`, and `timeouts=[60, 300]`
- **THEN** the number of tasks per APK MUST be `2 x 3 x 2 = 12`
- **AND** each task's `TaskConfiguration.tool_config.variant` MUST match the corresponding variant name

#### Scenario: No APKs Found

- **WHEN** `apks_dir` exists but contains no `.apk` files
- **THEN** `Platform._discover_apks()` MUST raise `ValueError` with a message including the directory path

### Requirement: Component-Based Task Execution (FR09, NFR02)

The platform MUST execute tasks through a component-based architecture where each component handles a specific concern (static analysis, emulator, logcat, coverage, tool execution). Components implement the `ITaskComponent` interface with `initialize(context)`, `execute(context)`, and `cleanup(context)` methods. The `TaskExecutor` coordinates component execution in three phases.

This design exists because task execution involves multiple orthogonal concerns that interact in specific ways. Static analysis data must be loaded before the coverage tracker can classify methods. The coverage tracker must be initialized before the emulator session begins. Inside the emulator session, logcat capture must start before coverage tracking, and coverage tracking must start before tool execution. After tool execution, coverage must stop before logcat capture stops. This strict ordering is enforced by `TaskExecutor._execute_coordinated_components()`.

Components are identified by string matching on their `name` property (`"StaticAnalysis"`, `"Coverage"`, `"Emulator"`, `"Logcat"`, `"ToolExecution"`). The executor iterates registered components and assigns them to the appropriate phase based on name containment.

The executor logs lifecycle transitions: task started, task completed, task failed, and tool started (for accurate timing coordination).

#### Scenario: Successful Three-Phase Execution

- **WHEN** a task is executed with all five components registered (StaticAnalysis, Emulator, Logcat, Coverage, ToolExecution)
- **THEN** Phase 1 MUST execute `StaticAnalysisComponent.execute()` outside the emulator session
- **AND** Phase 2 MUST execute `CoverageComponent.execute()` outside the emulator session
- **AND** Phase 3 MUST start the emulator via `EmulatorComponent.start_emulator("RVSec")`
- **AND** inside the emulator session, the execution order MUST be: install app -> start logcat -> start coverage -> mark tool execution start -> execute tool -> stop coverage -> process coverage results -> stop logcat
- **AND** the task state MUST transition from `RUNNING` to `COMPLETED`

#### Scenario: Component Execution Failure

- **WHEN** `StaticAnalysisComponent.execute()` or `CoverageComponent.execute()` returns `False` and raises `TaskExecutionError`
- **THEN** the executor MUST catch the exception and update task state to `ERROR`
- **AND** `_cleanup_resources()` MUST be called to clean up all registered components

#### Scenario: Missing Emulator or Tool Component

- **WHEN** the executor has no `EmulatorComponent` or no `ToolExecutionComponent` registered
- **THEN** Phase 3 (emulator session) MUST be skipped
- **AND** a warning MUST be logged: "Missing emulator or tool component - skipping emulator session"

#### Scenario: Task Without App Instance

- **WHEN** `TaskExecutor.execute()` is called and `task.app` is `None`
- **THEN** the method MUST return `False` immediately without executing any components
- **AND** the task state MUST be set to `ERROR` with message "Task has no app instance set"

#### Scenario: Cleanup After Exception

- **WHEN** an exception occurs during component execution
- **THEN** `_cleanup_resources()` MUST call `cleanup(context)` on all registered components
- **AND** if a component's `cleanup()` raises an exception, the error MUST be logged as a warning but MUST NOT prevent cleanup of remaining components
- **AND** post-execution hooks MUST still be called with `success=False`

#### Scenario: Pre/Post Execution Hooks

- **WHEN** hooks have been registered via `add_pre_execution_hook()` and `add_post_execution_hook()`
- **THEN** pre-execution hooks MUST be called before task state transitions to `RUNNING`
- **AND** post-execution hooks MUST be called after execution completes, with `(task, True)` on success or `(task, False)` on failure

### Requirement: Persistent Task Storage (FR10, NFR08)

The platform MUST provide persistent task storage with atomic file operations, thread safety, and transaction support. `TaskStorage` persists task state to a JSON file (`tasks.json`) in the results directory, enabling experiment continuation after interruption and providing a complete record of task execution history.

Experiment continuation works through configuration checksum validation. When `TaskStorage` loads an existing `tasks.json` file, it reads the `ExperimentMetadata.config_checksum` (SHA-256 of the JSON-serialized configuration with sorted keys). A new experiment can call `check_continuation_compatibility(config_dict)` to verify that its configuration matches the stored one. If checksums match, the experiment can resume by skipping already-completed tasks. If checksums differ, a warning is logged but execution continues — the researcher may have intentionally changed the configuration between runs.

The storage format is versioned (currently version 3) and includes three sections: `tasks` (serialized task objects), `experiment` (metadata with experiment ID, start time, and checksum), and `statistics` (computed from task data on each save).

#### Scenario: Atomic Save Operation

- **WHEN** `TaskStorage.save()` is called with 10 tasks
- **THEN** the system MUST write the JSON data to a temporary file (`{storage_file}.tmp`)
- **AND** the system MUST call `f.flush()` and `os.fsync(f.fileno())` on the temporary file
- **AND** the system MUST atomically rename the temporary file to the final storage file via `shutil.move()`
- **AND** if any step fails, the temporary file MUST be cleaned up

#### Scenario: Load From Existing Storage

- **WHEN** `TaskStorage.load()` is called and the storage file exists with valid JSON
- **THEN** the system MUST deserialize all tasks using `TaskFactory.create_task_from_dict()`
- **AND** experiment metadata MUST be loaded if `enable_metadata` is `True`
- **AND** previous statistics MUST be logged if present
- **AND** `loaded` MUST be set to `True`

#### Scenario: Load From Non-Existent File

- **WHEN** `TaskStorage.load()` is called and the storage file does not exist
- **THEN** the system MUST start with empty storage (no tasks)
- **AND** `loaded` MUST be set to `True`
- **AND** no error MUST be raised

#### Scenario: Transaction Commit

- **WHEN** `begin_transaction()` is called, followed by multiple `update_task()` calls, followed by `commit_transaction()`
- **THEN** all task updates MUST be buffered in `transaction_tasks` during the transaction
- **AND** `commit_transaction()` MUST apply all buffered changes to the main `tasks` dictionary
- **AND** `save()` MUST be called exactly once after applying all changes
- **AND** `in_transaction` MUST be set to `False` after commit

#### Scenario: Transaction Rollback

- **WHEN** `begin_transaction()` is called, followed by multiple `update_task()` calls, followed by `rollback_transaction()`
- **THEN** all buffered changes MUST be discarded
- **AND** the main `tasks` dictionary MUST remain unchanged
- **AND** `in_transaction` MUST be set to `False` after rollback

#### Scenario: Configuration Checksum Validation

- **WHEN** `check_continuation_compatibility(config_dict)` is called
- **THEN** the system MUST compute SHA-256 of `json.dumps(config_dict, sort_keys=True)`
- **AND** return `True` only if the computed checksum matches `experiment_metadata.config_checksum`
- **AND** if checksums do not match, the mismatch MUST be logged at DEBUG level with the first 8 characters of both checksums (the caller in `_skip_completed_tasks()` is responsible for logging the user-visible WARNING)

#### Scenario: Skip Completed Tasks During Resume

- **WHEN** `_skip_completed_tasks()` is called and `TaskStorage.get_completed_tasks()` returns N completed tasks (N > 0)
- **THEN** the platform MUST call `check_continuation_compatibility()` with the current config dict to validate configuration consistency, logging a warning if checksums differ
- **AND** the platform MUST compute task identity as the tuple `(apk_name, tool_name, variant, repetition, timeout)` for each completed task
- **AND** MUST remove from `self.tasks` any task whose identity matches a completed task's identity
- **AND** MUST log "Resume: skipped N already-completed tasks (M remaining)" where M is the count of tasks remaining after filtering
- **AND** tasks with `ERROR` state MUST NOT be skipped — they are re-executed on resume, giving the researcher a chance to recover from transient failures

### Requirement: Experiment Resume Integration (FR10-ext)

The platform MUST initialize `ExperimentMetadata` during `Platform.run()` and use it to validate configuration consistency when resuming an interrupted experiment. This requirement completes the resume architecture that was partially defined but never wired: `ExperimentMetadata`, `check_continuation_compatibility()`, and `_skip_completed_tasks()` all exist in the codebase but are not connected to each other.

The gap is purely an integration problem. `ExperimentMetadata` (defined in `task_storage.py`) stores a SHA-256 configuration checksum and an experiment identifier, but `Platform.run()` never creates an instance of it. `check_continuation_compatibility()` computes a new checksum and compares it against the stored one, but no caller ever invokes it. `_skip_completed_tasks()` can filter already-completed tasks by identity matching (APK name, tool name, variant, repetition, timeout), but without metadata initialization there is no stored checksum to validate against, and without resume detection in the CLI layer the same results directory is never reused across runs. The root cause is that every experiment run generates a unique results directory name with a timestamp and UUID (`cli_experiment_YYYYMMDD_HHMMSS_uuid`), so the second run creates a fresh directory and the old `tasks.json` is abandoned in the old directory.

This change wires the existing components together. `Platform.run()` creates an `ExperimentMetadata` instance after task generation (the point where the full configuration is available for checksumming) and stores it via `TaskStorage.set_experiment_metadata()`. When `_skip_completed_tasks()` finds previously completed tasks in the loaded `tasks.json` — indicating that the same results directory was reused, which happens when rv-experiment detects a resume scenario via `--name` or `--resume-dir` — it calls `check_continuation_compatibility()` to verify the configuration has not changed. A checksum mismatch produces a warning but does not block execution, because the researcher may have intentionally changed timeouts, added a tool, or adjusted parameters between runs. Task identity matching ensures that only genuinely completed tasks are skipped regardless of any configuration drift.

The rvsec-02/ICST study proved this pattern in a Docker environment: 7 containers running simultaneously, each with its own `execution_memory.json` file for crash recovery. When a container was killed and restarted, it read the memory file, skipped already-completed APKs, and continued with the remaining ones. The `tasks.json` + `ExperimentMetadata` combination serves the same purpose but with stronger guarantees — atomic writes (write-to-temp-then-rename), checksum validation, and task-level granularity (rather than APK-level).

#### Scenario: First Run Stores Metadata

- **WHEN** `Platform.run()` is called for the first time (no existing `tasks.json` in the results directory)
- **THEN** `Platform` MUST create an `ExperimentMetadata` with `experiment_id` set to the results directory path
- **AND** `config_checksum` MUST be the SHA-256 hex digest of `json.dumps(config_dict, sort_keys=True)` where `config_dict` is derived from the current `PlatformConfig` (serialized via `.model_dump()`)
- **AND** `start_time` MUST be the current ISO timestamp
- **AND** `current_status` MUST be `"running"`
- **AND** `TaskStorage.set_experiment_metadata()` MUST be called with the created metadata
- **AND** the metadata MUST be persisted to `tasks.json` on the next `save()` call

#### Scenario: Resume With Same Configuration

- **WHEN** `Platform.run()` is called and `TaskStorage` loads an existing `tasks.json` with N completed tasks (N > 0)
- **AND** the current `PlatformConfig` produces the same SHA-256 checksum as the stored `ExperimentMetadata.config_checksum`
- **THEN** `check_continuation_compatibility()` MUST return `True`
- **AND** `_skip_completed_tasks()` MUST remove from `self.tasks` any task whose identity tuple `(apk_name, tool_name, variant, repetition, timeout)` matches a completed task
- **AND** the platform MUST log "Resume: skipped N already-completed tasks (M remaining)" where M is the count of tasks remaining after filtering
- **AND** only the remaining M tasks MUST be executed

#### Scenario: Resume With Changed Configuration

- **WHEN** `Platform.run()` is called and `TaskStorage` loads an existing `tasks.json` with completed tasks
- **AND** the current `PlatformConfig` produces a different SHA-256 checksum than the stored `ExperimentMetadata.config_checksum` (e.g., the researcher changed a timeout value or added a new tool)
- **THEN** `check_continuation_compatibility()` MUST return `False`
- **AND** `_skip_completed_tasks()` MUST log a single warning: "Config changed since last run (stored: abcd1234, current: efgh5678) — resuming anyway" with the first 8 hex characters of both checksums
- **AND** `_skip_completed_tasks()` MUST still skip previously completed tasks based on identity matching, because task identity is independent of the config checksum — a completed `(cryptoapp, monkey, default, 1, 300)` task is the same regardless of whether the researcher also changed the timeout list or added a new tool
- **AND** execution MUST proceed with the remaining tasks under the new configuration

#### Scenario: Resume With No Completed Tasks

- **WHEN** `Platform.run()` is called and `TaskStorage` loads an existing `tasks.json` but all tasks have a state other than `COMPLETED` (e.g., all `ERROR` or `CREATED`)
- **THEN** `_skip_completed_tasks()` MUST return without modifying the task list, because there are no completed tasks to skip
- **AND** no resume log messages MUST be emitted (this is effectively a fresh run reusing the same directory)
- **AND** all generated tasks MUST be executed normally

### Requirement: Result Consolidation on Resume (FR10-ext)

When the platform resumes an experiment (either Form 1: Expand Experiment or Form 2: Crash Recovery), the result processing phase MUST produce output files (`summary.csv`, `results.json`, `coverage.csv`, `errors.csv`, `performance.csv`) that reflect the **entire experiment state** — all completed tasks from all sessions — not just the tasks executed in the current session. Note: `errors.csv` contains **monitored operations violations** (formal property violations detected by runtime verification monitors), not application crashes or general errors. This is necessary because the output files are the researcher's primary data artifact: they are imported into analysis notebooks, used for statistical comparisons, and included in publications. If a resumed experiment's output files only contain the current session's data, the researcher loses visibility into previously completed work and must manually reconstruct the full picture from raw data files.

The mechanism for achieving this is straightforward: `_process_results()` MUST use `TaskStorage.get_completed_tasks()` as its data source instead of the filtered `Platform.tasks` list. `TaskStorage` is the authoritative source of truth for the experiment state — it contains all tasks from all sessions (loaded from `tasks.json` at startup, updated via `update_task()` during execution). The `ResultProcessorComponent` receives this complete task list and generates output files with all completed tasks included.

Tasks loaded from `tasks.json` (from previous sessions) do not have `task.repository` data — the `LogcatRepository` that `CoverageTracker` populates in-memory during task execution is runtime-only and never serialized. They also do not carry `task.results_dir` or `task.app`: `Task.to_dict()` serializes only `id/config/result`, so `Task.from_dict()` reconstructs them with `results_dir=""` and `app=None`. Without special handling, every CSV column derived from per-method calls would be empty, because `register_method_call` requires the `classes` dict populated from static-analysis data, and the JSON path built from an empty `results_dir` does not resolve. The solution reconstructs both pieces on demand: the per-APK directory is recovered from the serialized `task.result.logcat_file` via `os.path.dirname(...)` (at runtime `task.results_dir == os.path.dirname(task.result.logcat_file)`), and the static-analysis JSON co-located there is loaded by `static_analysis_parser.read_static_analysis_files(<derived_dir>, apk_name, code_package)`. `ResultProcessorComponent._reconstruct_repository_from_logcat(task)` MUST obtain `static_data` this way, then invoke `parse_logcat_file(logcat_file, static_data)` to produce a `LogcatRepository` whose `classes` is populated and whose `register_method_call` correctly accumulates per-method coverage from `RVSEC-COV` entries. With this in place, the runtime path (Branch 1, current session) and the resume path (reconstruct) produce equivalent `LogcatRepository` objects, so all downstream CSV writers operate uniformly.

The reconstruct path also captures `RVSEC` violation entries via `LogcatRepository.register_rv_error`, which stores violations unconditionally and does not need `static_data`. Therefore, even when the static-analysis JSON is absent (e.g., a campaign that ran without static analysis), `errors.csv` is reliable; per `analysis` INV-ANA-25, the `total_errors`/`unique_errors` aggregates from `calculate_metrics().to_dict()` MUST also remain accurate in that degraded case (they MUST NOT be zeroed by the absence of coverage data). Only the per-method coverage portion is degraded. The reconstruct method MUST log a warning AND increment a counter (at most once per task) when `static_data` is unavailable, so the researcher knows the resulting coverage rows are zero by construction, not by content, and the count of affected tasks is surfaced rather than silently absorbed.

The execution summary (returned by `Platform.run()` and displayed by the CLI) MUST also reflect the complete experiment scope. It MUST include the count of skipped tasks (from previous runs) alongside the count of executed tasks, so the researcher sees the full picture: "Total tasks: 5 (2 executed, 3 skipped from previous runs)".

#### Scenario: Result Processing After Resume Includes All Sessions

- **WHEN** `Platform.run()` resumes an experiment by skipping N previously completed tasks and executing M new tasks
- **THEN** `_process_results()` MUST pass all N+M completed tasks to `ResultProcessorComponent`
- **AND** `summary.csv` MUST contain N+M rows (one per completed task, from all sessions) with all coverage and error columns populated from `LogcatRepository.calculate_metrics()`
- **AND** `results.json` MUST contain summary data for all N+M completed tasks
- **AND** `results.json` MUST contain MOP violation details (violation messages, spec names, class/method) for all N+M tasks that have logcat files
- **AND** `errors.csv` MUST contain MOP violation rows for all N+M tasks that have logcat files with `RVSEC` entries
- **AND** `coverage.csv` MUST contain per-method entries for all N+M tasks that have logcat files AND static-analysis JSON available (reconstructed for the N resumed tasks via re-parse, native for the M current-session tasks)
- **AND** `performance.csv` MUST contain entries for at least the M tasks from the current session

#### Scenario: Resume After tasks.json Round-Trip Resolves results_dir from Logcat

- **WHEN** a task is reconstructed via `Task.from_dict(Task.to_dict())` (the real resume path), so `task.results_dir == ""` and `task.app is None`
- **AND** `task.result.logcat_file` points to an existing logcat in a per-APK directory that also contains the co-located `f"{task.config.apk_name}.json"`
- **THEN** `_resolve_static_data(task)` MUST derive the directory as `os.path.dirname(task.result.logcat_file)` and call `read_static_analysis_files(<derived_dir>, task.config.apk_name, None)`
- **AND** the returned `StaticAnalysisData` MUST be non-empty (classes and methods loaded from the JSON)
- **AND** `repository.calculate_metrics().to_dict()["method_coverage"]` MUST be greater than zero when the logcat contains `RVSEC-COV` entries for reachable methods
- **AND** `repository.calculate_metrics().to_dict()["total_errors"]` MUST equal the count of `RVSEC` violation entries in the logcat

#### Scenario: Logcat Re-Reading with On-Demand Static Data Re-Parse

- **WHEN** `ResultProcessorComponent._reconstruct_repository_from_logcat(task)` is invoked for a task whose `task.repository` is `None` (loaded from `tasks.json`)
- **AND** `task.result.logcat_file` points to an existing file on disk
- **AND** `task.static_data` is `None`
- **AND** the static-analysis JSON exists at `os.path.dirname(task.result.logcat_file) / f"{task.config.apk_name}.json"`
- **THEN** the method MUST call `static_analysis_parser.read_static_analysis_files(<derived_dir>, task.config.apk_name, task.app.code_package if task.app else None)` to obtain a `StaticAnalysisData` instance
- **AND** MUST cache the result on `task.static_data` so repeated invocations within the same `ResultProcessorComponent.execute()` call do not re-parse
- **AND** MUST call `parse_logcat_file(logcat_file, static_data)` with that data
- **AND** the returned `LogcatRepository` MUST have `len(get_method_calls()) > 0` for any logcat that contains `RVSEC-COV` entries for methods present in the reachability section
- **AND** `repository.calculate_metrics().to_dict()` MUST return non-zero values for `method_coverage`, `reachable_method_coverage`, `mop_method_coverage`, and `direct_mop_method_coverage` when corresponding methods are called

#### Scenario: Static Analysis JSON Missing on Resume

- **WHEN** `ResultProcessorComponent._reconstruct_repository_from_logcat(task)` is invoked
- **AND** `task.result.logcat_file` points to an existing file
- **AND** the static-analysis JSON does not exist at `os.path.dirname(task.result.logcat_file) / f"{task.config.apk_name}.json"`
- **THEN** the method MUST log a warning identifying the task and the missing JSON, and MUST record the task once in the unresolved-static-data set (`_unresolved_task_ids`)
- **AND** the task MUST be counted **at most once**, regardless of how many CSV writers (`_write_task_coverage_data`, `_write_task_summary_data`, `_write_task_error_data`, `_extract_task_data`) trigger reconstruction or in what order — `task.static_data` MUST be memoized as an empty `StaticAnalysisData` (not an arbitrary sentinel) so re-entry returns the memo without re-parsing or re-counting, and the membership-guarded set absorbs duplicates
- **AND** `static_analysis_parser.read_static_analysis_files` MUST be invoked at most once for that task across all writers (the memo short-circuits re-entry, including after a parser exception)
- **AND** a task whose JSON IS present and populated MUST NOT be added to the set (the resolved↔unresolved distinction is by empty vs non-empty `classes`, not by whether the parser ran)
- **AND** MUST call `parse_logcat_file(logcat_file, static_data=None)` so `RVSEC` entries are still captured
- **AND** `errors.csv` MUST contain rows for that task
- **AND** `summary.csv` for that task MUST report `mop_errors_total` and `mop_errors_unique` equal to the actual violation counts (NOT zeroed by the absence of coverage data)
- **AND** every coverage-percentage column in `summary.csv` (`cov_act`, `cov_class`, `cov_method`, `cov_reachable`, `cov_reaches_target`, `cov_directly_reaches_target`) MUST be `0.00` for that task (`cov_rv_method` is intentionally not a `summary.csv` column — see `result_processor._write_summary_data`, where it would alias `cov_reaches_target`; it exists only in `coverage.csv`)
- **AND** `coverage.csv` MUST have zero per-method rows for that task

#### Scenario: No Fallback to Serialized Coverage Metrics When JSON Is Absent

- **WHEN** coverage cannot be reconstructed for a task (logcat present but static-analysis JSON genuinely absent) and `task.result.coverage_metrics` carries serialized runtime values
- **THEN** the writer MUST NOT use the serialized `coverage_metrics` to populate `summary.csv` `cov_*` columns
- **AND** every coverage-percentage column in the `summary.csv` row for that task MUST be `0.00`, consistent with the zero per-method rows in `coverage.csv` (so `verify.py` C3 / INV-PLT-17 holds: `summary cov_* == 0` whenever `coverage_rows == 0`)
- **AND** the `mop_errors_total`/`mop_errors_unique` columns MUST still equal the actual violation counts (errors are independent of static data, see analysis INV-ANA-25)
- **AND** the unresolved-static-data counter MUST be incremented (once for the task) and surfaced in the aggregate WARNING

#### Scenario: Orchestrated Resume Skips Static Analysis but Reuses Persisted JSON

- **WHEN** rv-experiment resumes an experiment via `--name` (implicit, when `results/<name>/tasks.json` exists) or `--resume-dir` (explicit), which forces `generate_monitors`, `instrument_apks`, and `static_analysis` to `False`
- **AND** the static-analysis JSON produced by the original run persists co-located with each task's logcat in the per-APK results directory (`<apk_dir>/<apk_name>.json`)
- **THEN** `_resolve_static_data` MUST locate that JSON via `os.path.dirname(task.result.logcat_file)` without re-running static analysis (Phase 1 is skipped)
- **AND** reconstructed per-method coverage MUST be non-zero for any task whose logcat contains `RVSEC-COV` entries for reachable methods
- **AND** no new GATOR/static-analysis invocation MUST occur during the resumed run

#### Scenario: Round-Trip Metric Equivalence Between Live and Resumed Task

- **WHEN** a completed task `t` has a populated `LogcatRepository` from live execution, and its logcat plus co-located static-analysis JSON exist on disk
- **AND** a resumed copy is built via `Task.from_dict(t.to_dict())` (so the copy has `results_dir=""`, `app=None`, `repository=None`) and processed through `_resolve_static_data` + `_reconstruct_repository_from_logcat`
- **THEN** the resumed copy's `calculate_metrics().to_dict()` MUST equal `t.repository.calculate_metrics().to_dict()` for `cov_act`, `cov_class`, `cov_method`, `cov_reachable`, `cov_reaches_target`, `cov_directly_reaches_target`, `mop_errors_total`, and `mop_errors_unique`, within a tolerance of `0.01` (INV-PLT-18)
- **AND** this equivalence MUST hold across at least three logcat fixtures: one with MOP violations, one representing a `--skip-static` run (logcat present, no JSON → coverage zero but errors accurate), and one normal coverage-bearing run

#### Scenario: Resume Coverage Health Check Warning

- **WHEN** `ResultProcessorComponent.execute()` finishes processing all completed tasks
- **AND** N of the M resumed tasks had a non-empty logcat file but reconstructed to zero per-method coverage because static data was unresolved
- **THEN** the component MUST emit exactly one prominent aggregate WARNING of the form "Resume coverage health: N/M resumed tasks had unresolved static data — coverage zeroed for those tasks" (INV-PLT-18)
- **AND** `len(_unresolved_task_ids)` MUST equal N exactly (each affected task counted once)
- **AND** when N is 0, no such warning MUST be emitted
- **AND** a subsequent `execute()` pass MUST start from a re-initialized set, so its `N` reflects only that pass (not an accumulation across passes)

#### Scenario: Logcat File Missing on Resume

- **WHEN** `ResultProcessorComponent` processes a completed task whose `task.repository` is `None`
- **AND** `task.result.logcat_file` does not exist on disk, or is `None`
- **THEN** `ResultProcessorComponent` MUST log a warning: "No logcat file available for task {task.id} — MOP violation details cannot be reconstructed"
- **AND** `errors.csv` MUST NOT have entries for that task (no data source to reconstruct from)
- **AND** `results.json` MUST include the task with empty violation details and zeroed coverage metrics
- **AND** `summary.csv` MUST include the task row with all coverage columns set to `0.00` and `mop_errors_total = mop_errors_unique = 0`
- **AND** `coverage.csv` MUST have zero per-method rows for that task

#### Scenario: Execution Summary Includes Skipped Count

- **WHEN** `_skip_completed_tasks()` skips N tasks from a previous run
- **AND** `_execute_tasks()` completes M tasks in the current session
- **THEN** `_generate_summary()` MUST return a dict with `skipped_tasks: N` in addition to the existing `total_tasks`, `successful_tasks`, and `failed_tasks` fields
- **AND** the `total_tasks` field MUST represent the number of tasks executed in this session (M)
- **AND** the platform MUST log "Execution summary: X/M tasks successful (N skipped from previous runs)"
- **AND** the CLI (`__main__.py`) MUST display the skipped count when N > 0

#### Scenario: First Run (No Resume) Has Zero Skipped

- **WHEN** `Platform.run()` executes for the first time (no existing `tasks.json`, or `tasks.json` has no completed tasks)
- **THEN** `_skipped_count` MUST be 0
- **AND** the summary MUST have `skipped_tasks: 0`
- **AND** `_process_results()` MUST behave identically to the non-resume case
- **AND** no "skipped from previous runs" messages MUST appear in CLI output

### Requirement: Logcat Capture (FR11)

The platform MUST capture Android logcat output during task execution via `LogcatComponent`. Logcat capture runs as a background process that writes raw logcat output to a file on disk. The captured output contains two categories of data relevant to the framework: method coverage events (tagged `RVSEC-COV`) and specification violation events (tagged `RVSEC`). Parsing of this data is handled by `CoverageComponent` via rv-coverage's `CoverageTracker`.

`LogcatComponent` delegates to `LogcatManager` (from rv-android-core) for starting and stopping the capture process. The component supports device-specific capture through `device_serial`, which is extracted from `task.config.tool_config.parameters` to support parallel execution on different emulator instances.

Logcat capture starts after the emulator is running and the APK is installed, and stops after the testing tool completes. The captured file is stored at `task.result.logcat_file`. If `task.config.clean_logcat` is `True`, the logcat buffer is cleared before capture begins to avoid contamination from previous runs.

#### Scenario: Logcat Capture Lifecycle

- **WHEN** a task is executed with `LogcatComponent` registered
- **THEN** `start_capture()` MUST be called after emulator startup and APK installation
- **AND** the capture MUST write to `task.result.logcat_file`
- **AND** `stop_capture()` MUST be called after tool execution completes and coverage tracking stops

#### Scenario: Clean Logcat Buffer

- **WHEN** `task.config.clean_logcat` is `True`
- **THEN** `LogcatManager.start_capture()` MUST be called with `clear_buffer=True`
- **AND** the logcat buffer MUST be cleared before capture begins

#### Scenario: Parallel Execution Device Serial

- **WHEN** `task.config.tool_config.parameters` contains `device_serial: "emulator-5558"`
- **THEN** `LogcatComponent` MUST initialize `LogcatManager` with `device_serial="emulator-5558"`
- **AND** logcat capture MUST be scoped to that specific emulator instance

#### Scenario: Capture Stop Failure

- **WHEN** `stop_capture()` is called and `LogcatManager.stop_capture()` raises an exception
- **THEN** the error MUST be logged as a warning
- **AND** the exception MUST NOT propagate (cleanup is non-critical)

### Requirement: Result Generation (FR14)

The platform MUST generate standardized output files from completed experiment tasks. `ResultProcessorComponent` processes only tasks with `TaskState.COMPLETED` and generates five output files: `coverage.csv`, `errors.csv`, `summary.csv`, `results.json`, and `performance.csv`. Result processing can be skipped during execution (via `skip_result_processing=True`) and run standalone later using `rv-platform run --process-results <results_dir>`.

This requirement serves the research purpose of the project. The CSV files are the primary data format for statistical analysis of experiment results. The JSON file provides a hierarchical view for programmatic access. The performance file captures execution timing for experiment optimization.

Result processing is invoked by `Platform._process_results()` after all tasks have been executed. It creates a `ResultProcessorComponent` with the complete task list and the results directory, then calls `initialize() -> execute() -> cleanup()`. The component filters for completed tasks and generates each file independently, using `ErrorHandler` decorators to ensure that a failure in one file generation does not prevent the others.

Per-method coverage rows in `coverage.csv` AND aggregate rows in `summary.csv` are produced from the same `LogcatRepository.calculate_metrics()` source. There is no separate "Branch 2 fallback" path that bypasses repository data for resumed tasks; reconstruction of `task.repository` from logcat + static-analysis JSON (see Requirement "Result Consolidation on Resume (FR10-ext)") ensures both writers operate uniformly on a populated repository.

#### Scenario: Full Result Generation

- **WHEN** an experiment completes with 5 tasks, all in `COMPLETED` state
- **THEN** `ResultProcessorComponent` MUST generate all five files: `coverage.csv`, `errors.csv`, `summary.csv`, `results.json`, `performance.csv`
- **AND** all files MUST be written to `config.results_dir`

#### Scenario: Coverage CSV Format

- **WHEN** `coverage.csv` is generated for a completed task with repository data
- **THEN** the header row MUST be: `apk, rep, timeout, tool, time, class, method, signature, cov_class, cov_act, cov_method, cov_rv_method, cov_reachable, cov_reaches_target, cov_directly_reaches_target`
- **AND** each method call MUST produce one row with progressive coverage metrics (cumulative unique methods / total methods)
- **AND** `cov_method`, `cov_act`, `cov_rv_method` MUST be cumulative-progressive (each row reflects the cumulative state up to and including that call)
- **AND** `cov_class`, `cov_reachable`, `cov_reaches_target`, `cov_directly_reaches_target` MUST equal the final task value from `repository.calculate_metrics().to_dict()` and are row-constant — `cov_class` MUST be `class_coverage` (NOT `method_coverage` as in the pre-fix code), `cov_reachable` MUST be `reachable_method_coverage`, `cov_reaches_target` MUST be `mop_method_coverage`, `cov_directly_reaches_target` MUST be `direct_mop_method_coverage`. Rationale: these metrics are derived from static-analysis denominators that do not change during execution; row-constant values match the offline regen tooling and downstream notebooks already in use
- **AND** coverage percentages MUST be rounded to 2 decimal places

#### Scenario: Errors CSV Format

- **WHEN** `errors.csv` is generated for a completed task with monitored operations violations
- **THEN** the header row MUST be: `apk, rep, timeout, tool, time, spec, class, method, message, unique_msg`
- **AND** each violation MUST produce one row
- **AND** `unique_msg` MUST be constructed as `class:::method:::spec:::error_type:::message` if not already provided

#### Scenario: Summary CSV Format

- **WHEN** `summary.csv` is generated
- **THEN** each completed task MUST produce exactly one row
- **AND** the header MUST be: `apk, rep, timeout, tool, cov_act, cov_class, cov_method, cov_reachable, cov_reaches_target, cov_directly_reaches_target, mop_errors_total, mop_errors_unique`
- **AND** each value MUST be read from `task.repository.calculate_metrics().to_dict()` after `_reconstruct_repository_from_logcat` populated `task.repository`
- **AND** `cov_act` MUST be the `activity_coverage` key from the dict
- **AND** `cov_class` MUST be the `class_coverage` key (NOT `method_coverage` as the pre-fix code wrote)
- **AND** `cov_method` MUST be the `method_coverage` key
- **AND** `cov_reachable` MUST be the `reachable_method_coverage` key
- **AND** `cov_reaches_target` MUST be the `mop_method_coverage` key
- **AND** `cov_directly_reaches_target` MUST be the `direct_mop_method_coverage` key
- **AND** `mop_errors_total` MUST be the `total_errors` key (semantically equivalent to the renamed `errors` column from the pre-fix schema)
- **AND** `mop_errors_unique` MUST be the `unique_errors` key
- **AND** coverage values MUST be rounded to 2 decimal places

#### Scenario: Results JSON Hierarchical Structure

- **WHEN** `results.json` is generated for tasks across multiple APKs, repetitions, and timeouts
- **THEN** the JSON MUST be structured as: `{apk_name: {repetitions: {rep: {timeouts: {timeout: {tools: {tool_name: data}}}}}}}`
- **AND** each tool data entry MUST contain `summary` (with coverage metrics) and `monitored_operations_errors` (with total, messages, and details)

#### Scenario: No Completed Tasks

- **WHEN** `ResultProcessorComponent.execute()` is called and no tasks have `TaskState.COMPLETED`
- **THEN** a warning MUST be logged: "No completed tasks found for result processing"
- **AND** no output files MUST be generated

#### Scenario: Standalone Result Processing

- **WHEN** `rv-platform run --process-results <results_dir>` is invoked via CLI
- **THEN** the system MUST load tasks from the results directory's `tasks.json`
- **AND** MUST run `ResultProcessorComponent` on the loaded tasks
- **AND** MUST write output files to the same results directory

<!-- No REMOVED Requirements section: the cascade fallback paths were described inline inside the
     existing "Result Consolidation on Resume (FR10-ext)" requirement, not as a standalone Requirement
     entry. The MODIFIED rewrite of that requirement above replaces those paragraphs with the unified
     reconstruct-via-static-data semantics. INV-PLT-16 forbids re-introduction of the fallback paths. -->

### Requirement: Tool-Configuration Channel via ToolConfig.parameters (NFR01, NFR02)

`PlatformConfig.tools` is a `List[ToolConfig]` (required field at `modules/rv-platform/src/rv_platform/config/platform_config.py:50`), where each `ToolConfig` (defined in `rv_android_core.domain.task.ToolConfig`) carries `name: str`, `variant: str`, and `parameters: Dict[str, Any]`. The `ToolFactory` (in `rv_tools.registry.factory`, L2; the rv-platform module imports it via `from rv_tools import ToolFactory`) MUST consult the matching `ToolConfig.parameters` when instantiating a tool plugin: it merges variant defaults from the registry with the entry's `parameters` dictionary and forwards the result as the `config` argument of `AbstractTool.configure()`. The `parameters` dictionary defaults to `{}` (empty) — the concrete tool decides whether to raise on missing required keys (per INV-TOOL-21).

The dictionary contents are decided at Layer 5 (`rv-experiment`): values may originate from environment variables (resolved via the `ENV_*` registry), CLI flags, or hard-coded defaults. The Platform layer treats `parameters` as opaque pass-through data — it does not interpret keys or apply per-tool logic.

This is the sole sanctioned channel for delivering per-tool configuration values that come from outside the Tools domain. Tool plugins MUST NOT read environment variables (INV-TOOL-20), configuration files, or any other external state during their lifecycle.

#### Scenario: Humanoid URL flows from CLI through ToolConfig.parameters to HumanoidTool

- **WHEN** `rv-experiment` resolves `RV_HUMANOID_URL=http://humanoid:50405` from the environment
- **AND** instantiates `PlatformConfig` with `tools=[ToolConfig(name="humanoid", variant="default", parameters={"humanoid_url": "http://humanoid:50405"})]`
- **AND** the platform schedules a task using the `humanoid` tool
- **THEN** the `ToolFactory.create_tool` MUST instantiate `HumanoidTool` and call `tool.configure({"humanoid_url": "http://humanoid:50405", ...variant_defaults})`
- **AND** at no point does the platform or the tool read `RV_HUMANOID_URL` from `os.environ`

#### Scenario: ToolConfig with empty parameters defaults gracefully

- **WHEN** `PlatformConfig.tools` contains `ToolConfig(name="monkey", variant="default", parameters={})`
- **AND** the platform schedules a task using the `monkey` tool
- **THEN** the `ToolFactory.create_tool` MUST instantiate `MonkeyTool` and call `tool.configure({...variant_defaults})` (empty `parameters` merged with variant defaults)
- **AND** the tool SHALL succeed if it has no required config keys, or raise per INV-TOOL-21 if it does

#### Scenario: PlatformConfig rejects malformed tools field

- **WHEN** code instantiates `PlatformConfig(tools="not a list", ...)`
- **THEN** Pydantic MUST raise `ValidationError` naming `tools` and the expected type (`List[ToolConfig]`)

#### Scenario: ToolFactory does not bypass parameters dict

- **WHEN** `ToolFactory.create_tool(tool_config)` (in `rv_tools.registry.factory`) is invoked
- **THEN** the only L2 input that influences `AbstractTool.configure()` MUST be the merge of variant defaults and `tool_config.parameters`
- **AND** the factory MUST NOT read any environment variable, configuration file, or other source to populate the `config` argument

### Requirement: Diagnostic Events CSV Generation (FR14)

`result_processor` SHALL generate a per-run `app_events.csv` containing one row per diagnostic event,
using `LogcatRepository.get_diagnostic_events()`, with the column set
`apk,rep,timeout,tool,time,category,exception_class,method,source,message,process,pid,fatal,n_frames,stack_head`.
The full multi-line stack trace SHALL NOT be written to the CSV (it remains in the `.logcat`). The
existing `coverage.csv`/`errors.csv`/`summary.csv` writers and schemas SHALL remain unchanged.

#### Scenario: One row per diagnostic event with stack_head only
- **WHEN** a task's repository holds one crash event for `br.unb.cic.cryptoapp`
- **THEN** `app_events.csv` contains one row with `category=crash`,
  `exception_class=java.lang.NullPointerException`, `process=br.unb.cic.cryptoapp`, `fatal=true`,
  and a non-empty `stack_head`
- **AND** the row contains no multi-line trace (the full block stays in the `.logcat`)

#### Scenario: Existing CSV schemas unchanged
- **WHEN** the run completes with diagnostics enabled
- **THEN** the headers of `coverage.csv`, `errors.csv`, and `summary.csv` are byte-identical to baseline

#### Scenario: app_events survives resume reconstruction
- **WHEN** a task is processed via `_reconstruct_repository_from_logcat` (resume) and its `.logcat`
  contains a crash block
- **THEN** the reconstructed repository yields the crash event and `app_events.csv` includes its row

### Requirement: Capture Flag Threading to LogcatComponent (FR07, FR08)

The platform SHALL thread the `RV_LOGCAT_DIAGNOSTICS` setting from `PlatformConfig` into
`LogcatComponent`, which SHALL pass the augmented tag set to `LogcatManager.start_capture` only when
diagnostics are enabled. When disabled, capture SHALL use the baseline tags.

#### Scenario: Enabled flag augments capture
- **WHEN** `PlatformConfig.logcat_diagnostics` is `true`
- **THEN** `LogcatComponent` calls `start_capture(tags=default_tags + ["AndroidRuntime:E","art:E","dalvikvm:E","ActivityManager:W"])`

#### Scenario: Disabled flag uses baseline capture
- **WHEN** `PlatformConfig.logcat_diagnostics` is `false` (default)
- **THEN** `LogcatComponent` starts capture without passing diagnostic tags (baseline command emitted)

### Requirement: Standalone CLI Timeout List (FR08)

The `rv-platform run` command MUST expose `--timeouts` (string, comma-separated positive
integers, default `"300"`) and MUST parse it into a `List[int]` assigned to
`PlatformConfig.timeouts`. Parsing and validation MUST match the rv-experiment CLI behavior
(INV-PLT-22), so a researcher can move an invocation between the two entry points without
changing the flag value.

The scalar flag `--timeout` MUST NOT exist on `rv-platform run` (hard rename, P3 — no alias).

#### Scenario: Multiple Timeouts via Standalone CLI

- **WHEN** the user runs `rv-platform run --tools monkey --apks-dir ./apks_examples --timeouts 60,300`
  against a directory with 1 APK and default repetitions (1)
- **THEN** `PlatformConfig.timeouts` MUST be `[60, 300]`
- **AND** `Platform._generate_tasks()` MUST produce exactly 2 tasks (1 APK × 1 tool × 1 rep × 2
  timeouts)

#### Scenario: Invalid Timeout Rejected Before Platform Setup

- **WHEN** the user runs `rv-platform run --tools monkey --timeouts 300,-5`
- **THEN** the CLI MUST exit with a usage error stating timeouts must be positive integers
- **AND** no `PlatformConfig` MUST be constructed and no task generation MUST occur

#### Scenario: Old Scalar Flag No Longer Exists

- **WHEN** the user runs `rv-platform run --tools monkey --timeout 300`
- **THEN** argparse MUST reject the unknown argument `--timeout` with a usage error


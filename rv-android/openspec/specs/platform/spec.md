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
  |  Phase 3: Post-processing (diagnostics, events)
```

rv-experiment creates a `PlatformConfig` and delegates execution to `Platform.run()`. rv-platform generates tasks, executes them, and writes results to disk. rv-experiment does not receive data back programmatically -- results stay on disk in the results directory.

rv-platform can also be used standalone via its own CLI (`rv-platform run`), bypassing rv-experiment entirely. In standalone mode, the user provides tool names and APK directory directly, and rv-platform handles everything from task generation through result output.

### Key Design Decisions

1. **Component-Based Execution**: Instead of a monolithic executor, `TaskExecutor` delegates to pluggable components (`StaticAnalysisComponent`, `EmulatorComponent`, `LogcatComponent`, `CoverageComponent`, `ToolExecutionComponent`). Each component follows a standardized `initialize/execute/cleanup` lifecycle defined by the `ITaskComponent` interface. This enables adding new execution phases without modifying the executor itself.

2. **Coordinated Phase Execution**: Components do not all execute in a flat sequence. The executor implements three distinct phases: Phase 1 runs static analysis loading outside the emulator session, Phase 2 initializes the coverage tracker outside the emulator session, and Phase 3 runs the emulator session with logcat capture, coverage tracking, and tool execution inside the emulator context manager. This ordering ensures static analysis data is available before the coverage tracker is configured, and that the emulator is only started when all preparation is complete.

3. **Tool Timeout as Success**: When a testing tool exceeds its configured timeout, `ToolExecutionComponent` catches the `RVToolTimeoutError` and returns `True` (success). This is by design: timeouts are the normal termination mechanism for time-bounded experiments. The tool runs for the configured duration, the timeout fires, execution stops, and results are collected. This is not an error condition.

4. **Atomic Task Persistence**: `TaskStorage` uses write-to-temp-file-then-rename for atomic saves (`fsync` + `shutil.move`), ensuring the tasks.json file is never in a partially written state. This protects against data loss if the process is interrupted during a write. Transaction support (`begin_transaction/commit_transaction/rollback_transaction`) enables batched updates.

5. **Non-Critical Static Analysis**: Static analysis data loading is treated as non-critical. If static analysis files are not found or parsing fails, execution continues without static data. Coverage tracking will be limited (no MOP method classification, no REACH-based universe), but the experiment still runs. This is logged as a warning, not an error.

6. **Dynamic Port Allocation**: `EmulatorComponent` supports dynamic emulator port allocation (default port 5554, configurable via `additional_params.device_port`). This enables parallel task execution where each task gets a unique emulator port to avoid conflicts.

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

ToolConfig (Pydantic BaseValidatedModel) [rv_platform]:
  name: str                    # Tool identifier (non-empty, trimmed)
  variants: List[str]          # Tool variants to execute (empty list = ["default"])
  parameters: Dict[str, Any]   # Tool-specific parameters

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
- **rv-android-core**: Domain models (`Task`, `TaskConfiguration`, `TaskFactory`, `TaskState`, `App`, `ToolConfig`), `EventBus`, `ErrorHandler`, `LoggingManager`, `PerformanceMonitor`, `EmulatorManager`, `LogcatManager`, `BaseValidatedModel`, `AbstractTool`
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
- `EventBus: Optional[EventBus]` -- Shared event bus instance for inter-module communication (defaults to singleton)

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
- **EventBus**: Publishes events to `LIFECYCLE`, `ERROR`, `ANALYSIS`, and `METRICS` channels: `TASK_STARTED`, `TASK_COMPLETED`, `TASK_FAILED`, `TOOL_STARTED`, `TOOL_STOPPED`, `EMULATOR_STARTED`, `APP_INSTALLED`, `STATIC_ANALYSIS_COMPLETED`, `COVERAGE_TRACKING_STARTED`, `COVERAGE_TRACKING_STOPPED`, `COVERAGE_UPDATED`
- **PerformanceMonitor**: Records timing metrics for task execution, component execution, and environment setup

### Error

- `EmulatorError` -- Raised when emulator startup fails or APK installation fails; propagated from `EmulatorComponent`
- `TaskExecutionError` -- Raised when a component execution fails (static analysis, coverage, tool execution) and the failure is critical; raised by `TaskExecutor._execute_coordinated_components()`
- `AnalysisError` -- Raised when coverage tracker initialization, start, stop, or result processing fails; handled by `CoverageComponent` with `ErrorHandler` decorator
- `RVToolTimeoutError` -- Raised by testing tools when execution exceeds the configured timeout; caught by `ToolExecutionComponent` and treated as successful completion (returns `True`)
- `RVToolExecutionError` -- Raised by testing tools when an actual execution failure occurs (not a timeout); caught by `ToolExecutionComponent` and returned as failure (returns `False`)
- `ValueError` -- Raised by `PlatformConfig` validators (empty APK directory, no APK files found, no tools specified, invalid repetitions, invalid timeouts, invalid log level) and by `Platform._load_tool()` when tool loading fails

## Invariants

- **INV-PLT-01**: The system MUST generate exactly `|APKs| x |tools| x |variants_per_tool| x repetitions x |timeouts|` tasks during task generation. If `variants` is empty for a tool, the system MUST use `["default"]` as the variant list, yielding exactly one variant per such tool.

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

## Requirements

### Requirement: Android Emulator Management (FR07, NFR04, NFR07)

The platform MUST manage the full lifecycle of Android emulator instances during task execution. This includes starting the emulator with a named AVD, allocating a unique device port, installing the APK under test, and stopping the emulator after task completion. Emulator management is encapsulated in `EmulatorComponent`, which operates within the Phase 3 context manager in `TaskExecutor._run_emulator_session()`.

Dynamic port allocation is necessary because the ICST study runs multiple tool configurations across 188 applications, and future parallel execution requires isolated emulator instances. Each task can specify a unique `device_port` (default 5554) and `device_serial` (default `emulator-5554`) via `tool_config.additional_params`, enabling multiple concurrent emulator sessions without port conflicts.

The emulator is started using the `EmulatorManager.start_emulator()` context manager, which ensures proper cleanup on both normal and exceptional exits. App installation is verified via `CommandResult.is_failure()` -- if installation fails, `EmulatorError` is raised and the task transitions to `ERROR` state.

#### Scenario: Successful Emulator Startup and APK Installation

- **WHEN** a task is being executed with `apk_name="cryptoapp.apk"` and `no_window=True`
- **THEN** `EmulatorComponent.start_emulator("RVSec")` MUST start the emulator in headless mode on the default port 5554
- **AND** `EmulatorComponent.install_app()` MUST install the APK on the emulator
- **AND** an `EMULATOR_STARTED` event MUST be published to the EventBus with the task's `device_id`
- **AND** an `APP_INSTALLED` event MUST be published with the app name

#### Scenario: APK Installation Failure

- **WHEN** `EmulatorComponent.install_app()` is called and `EmulatorManager.install_app()` returns `False`
- **THEN** the component MUST raise `EmulatorError` with message containing the app name
- **AND** the error MUST be handled by `ErrorHandler` with task context
- **AND** the method MUST return `False`

#### Scenario: Dynamic Port Allocation for Parallel Execution

- **WHEN** a task has `tool_config.additional_params = {"device_port": 5558, "device_serial": "emulator-5558"}`
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

The platform MUST generate tasks as the Cartesian product of discovered APKs, configured tools, tool variants, repetitions, and timeouts. Each unique combination produces exactly one `Task` object with a `TaskConfiguration` containing the APK name, tool configuration (name, variant, additional parameters), repetition number, and timeout value.

Task generation is the first step of `Platform.run()`. The platform discovers APK files by globbing `*.apk` in the configured `apks_dir` (sorted alphabetically). If no APK files are found, `Platform._discover_apks()` raises `ValueError`. For each APK, the platform iterates over all tools, their variants (defaulting to `["default"]` if the variants list is empty), repetition numbers (1 to `config.repetitions` inclusive), and timeout values. For each combination, a `Task` is created via `TaskFactory.create_task()`, associated with an `App` instance, and initialized with the results directory.

Tasks follow a lifecycle: `CREATED` (initial) -> `RUNNING` (when executor begins) -> `COMPLETED` (success, including timeout) or `ERROR` (failure). The `INITIALIZING`, `READY`, and `CANCELED` states are defined in `TaskState` but are not actively used by `TaskExecutor.execute()` in the current implementation.

#### Scenario: Basic Task Generation

- **WHEN** `apks_dir` contains 2 APK files, `tools` has 1 tool with no variants, `repetitions=1`, and `timeouts=[300]`
- **THEN** `Platform._generate_tasks()` MUST produce exactly 2 tasks (2 APKs x 1 tool x 1 variant x 1 rep x 1 timeout)
- **AND** each task MUST have an `App` instance set via `task.set_app()`
- **AND** each task MUST be initialized with the results directory via `task.initialize()`

#### Scenario: Multi-Variant Task Generation

- **WHEN** `tools` has 1 tool with `variants=["dfs_greedy", "bfs_greedy"]`, `repetitions=3`, and `timeouts=[60, 300]`
- **THEN** the number of tasks per APK MUST be `1 x 2 x 3 x 2 = 12`
- **AND** each task's `TaskConfiguration.tool_config.variant` MUST match the corresponding variant name

#### Scenario: Default Variant Fallback

- **WHEN** a `ToolConfig` has `variants=[]` (empty list)
- **THEN** the platform MUST use `["default"]` as the variant list, producing exactly one variant per tool

#### Scenario: No APKs Found

- **WHEN** `apks_dir` exists but contains no `.apk` files
- **THEN** `Platform._discover_apks()` MUST raise `ValueError` with a message including the directory path
- **AND** no tasks MUST be generated

#### Scenario: Task Storage Integration

- **WHEN** tasks are generated
- **THEN** each task MUST be appended to the in-memory `Platform.tasks` list
- **AND** after execution, each task MUST be persisted to `TaskStorage` via `update_task()`

### Requirement: Component-Based Task Execution (FR09, NFR02)

The platform MUST execute tasks through a component-based architecture where each component handles a specific concern (static analysis, emulator, logcat, coverage, tool execution). Components implement the `ITaskComponent` interface with `initialize(context)`, `execute(context)`, and `cleanup(context)` methods. The `TaskExecutor` coordinates component execution in three phases.

This design exists because task execution involves multiple orthogonal concerns that interact in specific ways. Static analysis data must be loaded before the coverage tracker can classify methods. The coverage tracker must be initialized before the emulator session begins. Inside the emulator session, logcat capture must start before coverage tracking, and coverage tracking must start before tool execution. After tool execution, coverage must stop before logcat capture stops. This strict ordering is enforced by `TaskExecutor._execute_coordinated_components()`.

Components are identified by string matching on their `name` property (`"StaticAnalysis"`, `"Coverage"`, `"Emulator"`, `"Logcat"`, `"ToolExecution"`). The executor iterates registered components and assigns them to the appropriate phase based on name containment.

The executor publishes lifecycle events to the EventBus: `TASK_STARTED` when execution begins, `TASK_COMPLETED` when execution succeeds, `TASK_FAILED` when execution fails, and `TOOL_STARTED` when the testing tool begins execution (for accurate timing coordination).

#### Scenario: Successful Three-Phase Execution

- **WHEN** a task is executed with all five components registered (StaticAnalysis, Emulator, Logcat, Coverage, ToolExecution)
- **THEN** Phase 1 MUST execute `StaticAnalysisComponent.execute()` outside the emulator session
- **AND** Phase 2 MUST execute `CoverageComponent.execute()` outside the emulator session
- **AND** Phase 3 MUST start the emulator via `EmulatorComponent.start_emulator("RVSec")`
- **AND** inside the emulator session, the execution order MUST be: install app -> start logcat -> start coverage -> mark tool execution start -> execute tool -> stop coverage -> process coverage results -> stop logcat
- **AND** the task state MUST transition from `RUNNING` to `COMPLETED`
- **AND** `TASK_STARTED`, `TOOL_STARTED`, and `TASK_COMPLETED` events MUST be published

#### Scenario: Component Execution Failure

- **WHEN** `StaticAnalysisComponent.execute()` or `CoverageComponent.execute()` returns `False` and raises `TaskExecutionError`
- **THEN** the executor MUST catch the exception, update task state to `ERROR`, and publish a `TASK_FAILED` event
- **AND** `_cleanup_resources()` MUST be called to clean up all registered components

#### Scenario: Missing Emulator or Tool Component

- **WHEN** the executor has no `EmulatorComponent` or no `ToolExecutionComponent` registered
- **THEN** Phase 3 (emulator session) MUST be skipped
- **AND** a warning MUST be logged: "Missing emulator or tool component - skipping emulator session"

#### Scenario: Task Without App Instance

- **WHEN** `TaskExecutor.execute()` is called and `task.app` is `None`
- **THEN** the method MUST return `False` immediately without executing any components
- **AND** the task state MUST be set to `ERROR` with message "Task has no app instance set"
- **AND** a `TASK_FAILED` event MUST be published

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

Experiment continuation works through configuration checksum validation. When `TaskStorage` loads an existing `tasks.json` file, it reads the `ExperimentMetadata.config_checksum` (SHA-256 of the JSON-serialized configuration with sorted keys). A new experiment can call `check_continuation_compatibility(config_dict)` to verify that its configuration matches the stored one. If checksums match, the experiment can resume by skipping already-completed tasks.

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
- **AND** if checksums do not match, a warning MUST be logged with the first 8 characters of both checksums

### Requirement: Logcat Capture (FR11)

The platform MUST capture Android logcat output during task execution via `LogcatComponent`. Logcat capture runs as a background process that writes raw logcat output to a file on disk. The captured output contains two categories of data relevant to the framework: method coverage events (tagged `RVSEC-COV`) and specification violation events (tagged `RVSEC`). Parsing of this data is handled by `CoverageComponent` via rv-coverage's `CoverageTracker`.

`LogcatComponent` delegates to `LogcatManager` (from rv-android-core) for starting and stopping the capture process. The component supports device-specific capture through `device_serial`, which is extracted from `task.config.tool_config.additional_params` to support parallel execution on different emulator instances.

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

- **WHEN** `task.config.tool_config.additional_params` contains `device_serial: "emulator-5558"`
- **THEN** `LogcatComponent` MUST initialize `LogcatManager` with `device_serial="emulator-5558"`
- **AND** logcat capture MUST be scoped to that specific emulator instance

#### Scenario: Capture Stop Failure

- **WHEN** `stop_capture()` is called and `LogcatManager.stop_capture()` raises an exception
- **THEN** the error MUST be logged as a warning
- **AND** the exception MUST NOT propagate (cleanup is non-critical)

### Requirement: Result Generation (FR14)

The platform MUST generate standardized output files from completed experiment tasks. `ResultProcessorComponent` processes only tasks with `TaskState.COMPLETED` and generates five output files: `coverage.csv`, `errors.csv`, `summary.csv`, `results.json`, and `performance.csv`. Result processing can be skipped during execution (via `skip_result_processing=True`) and run standalone later using `rv-platform run --process-results <results_dir>`.

This requirement serves the research purpose of the project. The CSV files are the primary data format for statistical analysis of experiment results (the ICST study used pandas/scipy to analyze coverage and violation data from these files). The JSON file provides a hierarchical view for programmatic access. The performance file captures execution timing for experiment optimization.

Result processing is invoked by `Platform._process_results()` after all tasks have been executed. It creates a `ResultProcessorComponent` with the complete task list and the results directory, then calls `initialize() -> execute() -> cleanup()`. The component filters for completed tasks and generates each file independently, using `ErrorHandler` decorators to ensure that a failure in one file generation does not prevent the others.

#### Scenario: Full Result Generation

- **WHEN** an experiment completes with 5 tasks, all in `COMPLETED` state
- **THEN** `ResultProcessorComponent` MUST generate all five files: `coverage.csv`, `errors.csv`, `summary.csv`, `results.json`, `performance.csv`
- **AND** all files MUST be written to `config.results_dir`

#### Scenario: Coverage CSV Format

- **WHEN** `coverage.csv` is generated for a completed task with repository data
- **THEN** the header row MUST be: `apk, rep, timeout, tool, time, class, method, signature, cov_class, cov_act, cov_method, cov_rv_method`
- **AND** each method call MUST produce one row with progressive coverage metrics (cumulative unique methods / total methods)
- **AND** coverage percentages MUST be rounded to 2 decimal places

#### Scenario: Errors CSV Format

- **WHEN** `errors.csv` is generated for a completed task with monitored operations violations
- **THEN** the header row MUST be: `apk, rep, timeout, tool, time, spec, class, method, message, unique_msg`
- **AND** each violation MUST produce one row
- **AND** `unique_msg` MUST be constructed as `class:::method:::spec:::error_type:::message` if not already provided

#### Scenario: Summary CSV Format

- **WHEN** `summary.csv` is generated
- **THEN** each completed task MUST produce exactly one row
- **AND** the header MUST be: `apk, rep, timeout, tool, cov_act, cov_method, cov_rv_method, errors`
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

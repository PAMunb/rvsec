# Delta Spec: platform — gh83-reconstruction-time-stamping

## Purpose

This delta corrects the `time` column semantics of the rv-platform CSV writers (`modules/rv-platform/src/rv_platform/components/result_processor.py`). The `time` column of `coverage.csv`, `errors.csv`, and `app_events.csv` is specified (core spec, `RvCoverageLog`/`RvErrorLog` data contracts) as seconds elapsed since tool execution start. Two writer behaviors currently violate that contract on the reconstruction path: `_write_task_error_data` and `_write_task_app_events` replace any `time_since_task_start` equal to `0` with the row index from `enumerate(..., 1)`, and `_write_task_coverage_data` exposes all-zero `time` values because reconstruction never stamps timing. Under reconstruction (resume, offline consolidation) every entry carries `0`, so the errors and app-events `time` columns degenerate into a sequential counter (1, 2, 3, …) and the coverage `time` column into all zeros — corrupting the time-series data used in the thesis experiments while looking superficially plausible.

The fix has two halves. The rv-coverage half (see the analysis delta) makes `parse_logcat_file` stamp real timing when given the tool execution start epoch. The platform half specified here makes `_reconstruct_repository_from_logcat` pass `task.result.tool_execution_start` (already serialized in `tasks.json` and restored by `TaskResult.from_dict`) into the parser, and removes the row-index fabrication from the writers entirely: a `time` of `0` is a legitimate value meaning "occurred within the first second of tool execution" and MUST be written as-is. With both halves in place, the live path and the reconstruction path produce identical `time` columns — extending the INV-PLT-18 live/resume round-trip equivalence, which previously covered only coverage and error metrics, to the `time` values themselves.

## Data Contracts

### Input
- `task.result.tool_execution_start: Optional[datetime]` — tool execution start epoch, serialized in `tasks.json` (`TaskResult.to_dict`/`from_dict`). Consumed by `_reconstruct_repository_from_logcat` and forwarded to `parse_logcat_file`.

### Output
- `coverage.csv`, `errors.csv`, `app_events.csv` — column sets unchanged; the `time` column MUST contain `time_since_task_start` values (integer seconds since tool execution start), identical between live and reconstructed processing of the same task.

### Side-Effects
- **[Logging]**: when `task.result.tool_execution_start` is `None` for a task being reconstructed (legacy `tasks.json`), the component MUST log a warning identifying the task; the resulting `time` values are `0` by construction, never fabricated.

### Error
- No new error paths.

## Invariants

- **INV-PLT-23**: `ResultProcessorComponent._reconstruct_repository_from_logcat(task)` MUST invoke `parse_logcat_file(logcat_file, static_data, tool_execution_start=task.result.tool_execution_start)` whenever `task.result.tool_execution_start` is non-`None`, so reconstructed repositories carry the same `time_since_task_start` values the live `CoverageTracker` would have produced (analysis INV-ANA-49). When it is `None`, the component MUST log a warning for that task and proceed; the zeros in the output are then an explicit degraded state, not silent corruption.
- **INV-PLT-24**: CSV writers MUST NOT fabricate `time` values. The `time` column of `coverage.csv`, `errors.csv`, and `app_events.csv` MUST be exactly the entry's `time_since_task_start` (with `0` representable, meaning first-second occurrence). Substituting row indices, counters, or any other synthesized value for missing or zero timing is prohibited — this extends the INV-PLT-18 live/resume round-trip equivalence to the `time` column: for any completed task with `tool_execution_start` persisted, the `time` column produced from `Task.from_dict(t.to_dict())` + reconstruction MUST equal the one produced from the live repository.

## MODIFIED Requirements

### Requirement: Result Generation (FR14)

The platform MUST generate standardized output files from completed experiment tasks. `ResultProcessorComponent` processes only tasks with `TaskState.COMPLETED` and generates five output files: `coverage.csv`, `errors.csv`, `summary.csv`, `results.json`, and `performance.csv`. Result processing can be skipped during execution (via `skip_result_processing=True`) and run standalone later using `rv-platform run --process-results <results_dir>`.

This requirement serves the research purpose of the project. The CSV files are the primary data format for statistical analysis of experiment results. The JSON file provides a hierarchical view for programmatic access. The performance file captures execution timing for experiment optimization.

Result processing is invoked by `Platform._process_results()` after all tasks have been executed. It creates a `ResultProcessorComponent` with the complete task list and the results directory, then calls `initialize() -> execute() -> cleanup()`. The component filters for completed tasks and generates each file independently, using `ErrorHandler` decorators to ensure that a failure in one file generation does not prevent the others.

Per-method coverage rows in `coverage.csv` AND aggregate rows in `summary.csv` are produced from the same `LogcatRepository.calculate_metrics()` source. There is no separate "Branch 2 fallback" path that bypasses repository data for resumed tasks; reconstruction of `task.repository` from logcat + static-analysis JSON (see Requirement "Result Consolidation on Resume (FR10-ext)") ensures both writers operate uniformly on a populated repository.

The `time` column of `coverage.csv` and `errors.csv` MUST contain the entry's `time_since_task_start` — integer seconds elapsed since tool execution start — on both the live path (stamped by `CoverageTracker`) and the reconstruction path (stamped by `parse_logcat_file` from the persisted `tool_execution_start`, INV-PLT-23). Writers MUST NOT substitute row indices or any other fabricated value when timing is `0` or missing (INV-PLT-24): `0` is a legitimate first-second timestamp, and a repository reconstructed without an epoch produces `0`s that MUST be written as-is with the degraded state logged.

#### Scenario: Full Result Generation

- **WHEN** an experiment completes with 5 tasks, all in `COMPLETED` state
- **THEN** `ResultProcessorComponent` MUST generate all five files: `coverage.csv`, `errors.csv`, `summary.csv`, `results.json`, `performance.csv`
- **AND** all files MUST be written to `config.results_dir`

#### Scenario: Coverage CSV Format

- **WHEN** `coverage.csv` is generated for a completed task with repository data
- **THEN** the header row MUST be: `apk, rep, timeout, tool, time, class, method, signature, cov_class, cov_act, cov_method, cov_rv_method, cov_reachable, cov_reaches_target, cov_directly_reaches_target`
- **AND** each method call MUST produce one row with progressive coverage metrics (cumulative unique methods / total methods)
- **AND** the `time` value of each row MUST be the method's `time_since_task_start` (first-call time), written as-is — including `0` for first-second calls — with rows ordered chronologically by it
- **AND** `cov_method`, `cov_act`, `cov_rv_method` MUST be cumulative-progressive (each row reflects the cumulative state up to and including that call)
- **AND** `cov_class`, `cov_reachable`, `cov_reaches_target`, `cov_directly_reaches_target` MUST equal the final task value from `repository.calculate_metrics().to_dict()` and are row-constant — `cov_class` MUST be `class_coverage` (NOT `method_coverage` as in the pre-fix code), `cov_reachable` MUST be `reachable_method_coverage`, `cov_reaches_target` MUST be `mop_method_coverage`, `cov_directly_reaches_target` MUST be `direct_mop_method_coverage`. Rationale: these metrics are derived from static-analysis denominators that do not change during execution; row-constant values match the offline regen tooling and downstream notebooks already in use
- **AND** coverage percentages MUST be rounded to 2 decimal places

#### Scenario: Errors CSV Format

- **WHEN** `errors.csv` is generated for a completed task with monitored operations violations
- **THEN** the header row MUST be: `apk, rep, timeout, tool, time, spec, class, method, message, unique_msg`
- **AND** each violation MUST produce one row
- **AND** the `time` value MUST be the violation's `time_since_task_start`, written as-is — a violation at second zero produces `0`, and no row index or counter is ever substituted (INV-PLT-24)
- **AND** `unique_msg` MUST be constructed as `class:::method:::spec:::error_type:::message` if not already provided

#### Scenario: Time Column Round-Trip Equivalence on Resume

- **WHEN** a task completed live (repository populated by `CoverageTracker`, `tool_execution_start` persisted) is serialized to `tasks.json`, reloaded via `Task.from_dict`, and processed through `_reconstruct_repository_from_logcat`
- **THEN** the `time` column of `coverage.csv` and `errors.csv` rows for that task MUST be identical to the rows the live repository would have produced
- **AND** the `time` values MUST NOT form a sequential row counter uncorrelated with the logcat timestamps

#### Scenario: Reconstruction Without Persisted Epoch Degrades Explicitly

- **WHEN** a task from a legacy `tasks.json` with `tool_execution_start = None` is reconstructed
- **THEN** the `time` values for that task MUST be `0` (never row indices)
- **AND** a warning identifying the task MUST be logged

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

### Requirement: Diagnostic Events CSV Generation (FR14)

`result_processor` SHALL generate a per-run `app_events.csv` containing one row per diagnostic event,
using `LogcatRepository.get_diagnostic_events()`, with the column set
`apk,rep,timeout,tool,time,category,exception_class,method,source,message,process,pid,fatal,n_frames,stack_head`.
The full multi-line stack trace SHALL NOT be written to the CSV (it remains in the `.logcat`). The
existing `coverage.csv`/`errors.csv`/`summary.csv` writers and schemas SHALL remain unchanged.

The `time` value of each row MUST be the event's `time_since_task_start` (seconds since tool execution
start), written as-is on both the live and reconstruction paths — `0` is a legitimate first-second
value, and no row index or counter is ever substituted (INV-PLT-24).

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
- **AND** the row's `time` value equals the event's `time_since_task_start` stamped from the persisted
  `tool_execution_start` (not a row index)

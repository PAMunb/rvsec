# Delta Spec — platform (gh58)

## Purpose

This delta extends `openspec/specs/platform/spec.md` to (a) correct the resume-path result-consolidation contract, which previously documented a degraded fallback as if it were intentional, and (b) extend the `coverage.csv` and `summary.csv` data contracts with the extended column set already populated by `LogcatRepository.calculate_metrics()`. The driver is gh58 (GitHub Issue #58): the experiment `experimento-20260508` produced corrupt consolidated CSVs because every task loaded from `tasks.json` on resume took a path that called `parse_logcat_file` without `static_data` (so per-method coverage silently no-opped) or fell through to a Branch 2 fallback that wrote empty `class/method/signature` and stale aggregate percentages. The fix promotes `static_analysis_parser.read_static_analysis_files` — already used by `StaticAnalysisComponent.load_static_data` — into the result-processor reconstruct path, so resume-path output becomes byte-equivalent to single-session output. Once that holds, the Branch 2 fallback is unreachable dead code and is deleted per P3.

The extended CSV contract reflects metrics the system already computes but never wrote: `class_coverage`, `reachable_method_coverage`, `mop_method_coverage`, `direct_mop_method_coverage`, `total_errors`, and `unique_errors`. These are central to the downstream evaluation of cryptographic API misuse detection (denominators must distinguish "all methods", "reachable methods", "methods that reach an MOP", and "methods that directly invoke an MOP"), so capturing them in the persistent CSV — not only in `task.result.coverage_metrics` — is required for downstream notebooks and the regen tooling in `scripts/regenerate_results/`.

## Data Contracts

### Output

- `coverage.csv` — header MUST be: `apk, rep, timeout, tool, time, class, method, signature, cov_class, cov_act, cov_method, cov_rv_method, cov_reachable, cov_reaches_mop, cov_directly_reaches_mop`
- `summary.csv` — header MUST be: `apk, rep, timeout, tool, cov_act, cov_class, cov_method, cov_reachable, cov_reaches_mop, cov_directly_reaches_mop, mop_errors_total, mop_errors_unique` (12 columns). The legacy `cov_rv_method` column is dropped from `summary.csv` because, with row-constant final values, it would alias `cov_reaches_mop`; it is retained in `coverage.csv` where it carries distinct progressive semantics.

All other Data Contracts fields from the main spec are unchanged.

## Invariants

- **INV-PLT-15**: `ResultProcessorComponent._reconstruct_repository_from_logcat(task)` MUST invoke `parse_logcat_file(logcat_file, static_data)` with a non-`None` `static_data` whenever the static-analysis JSON exists at `task.results_dir / f"{task.config.apk_name}.json"`. When `task.static_data` is already populated, that value MUST be reused; when it is `None`, the method MUST call `static_analysis_parser.read_static_analysis_files(task.results_dir, task.config.apk_name, task.app.code_package if task.app else None)` to re-parse the JSON on demand. If the JSON is absent, the method MUST log a warning and proceed with `static_data=None` — in that degraded case `errors` are still reliable but per-method coverage MUST be zero.

- **INV-PLT-16**: `_write_task_coverage_data` and `_write_task_summary_data` MUST be unified to a single path that reads from `task.repository.calculate_metrics().to_dict()` after `_reconstruct_repository_from_logcat` has ensured `task.repository` is populated. The pre-existing cascade in `_write_task_summary_data` (3 tiers: `task.result.coverage_metrics` → `task.repository.calculate_metrics()` → zeros) and the `else` branch in `_write_task_coverage_data` (single fallback emitting empty `class/method/signature`) MUST be removed entirely (P3, no backward-compatibility shim). When `_reconstruct_repository_from_logcat` returns `None` (logcat file missing), both writers MUST emit zeroed rows with an explicit warning — they MUST NOT fall back to reading stale serialized values from `task.result.coverage_metrics`.

- **INV-PLT-17**: The `cov_class` column in both `coverage.csv` and `summary.csv` MUST contain the `class_coverage` metric from `CoverageMetrics.to_dict()` (the percentage of called classes over total static classes). This corrects a pre-existing bug where the runtime Branch 1 path in `_write_task_coverage_data` wrote `method_coverage` into the `cov_class` slot.

## MODIFIED Requirements

### Requirement: Result Consolidation on Resume (FR10-ext)

When the platform resumes an experiment (either Form 1: Expand Experiment or Form 2: Crash Recovery), the result processing phase MUST produce output files (`summary.csv`, `results.json`, `coverage.csv`, `errors.csv`, `performance.csv`) that reflect the **entire experiment state** — all completed tasks from all sessions — not just the tasks executed in the current session. Note: `errors.csv` contains **monitored operations violations** (formal property violations detected by runtime verification monitors), not application crashes or general errors. This is necessary because the output files are the researcher's primary data artifact: they are imported into analysis notebooks, used for statistical comparisons, and included in publications. If a resumed experiment's output files only contain the current session's data, the researcher loses visibility into previously completed work and must manually reconstruct the full picture from raw data files.

The mechanism for achieving this is straightforward: `_process_results()` MUST use `TaskStorage.get_completed_tasks()` as its data source instead of the filtered `Platform.tasks` list. `TaskStorage` is the authoritative source of truth for the experiment state — it contains all tasks from all sessions (loaded from `tasks.json` at startup, updated via `update_task()` during execution). The `ResultProcessorComponent` receives this complete task list and generates output files with all completed tasks included.

Tasks loaded from `tasks.json` (from previous sessions) do not have `task.repository` data — the `LogcatRepository` that `CoverageTracker` populates in-memory during task execution is runtime-only and never serialized. Without special handling, every CSV column derived from per-method calls would be empty, because `register_method_call` requires the `classes` dict populated from static-analysis data. The solution is to reconstruct that data on demand: every task has its static-analysis JSON co-located with the APK in `task.results_dir`, and the existing parser `static_analysis_parser.read_static_analysis_files(results_dir, apk_name, code_package)` already loads it in milliseconds. `ResultProcessorComponent._reconstruct_repository_from_logcat(task)` MUST obtain `static_data` by calling that same function (the very call `StaticAnalysisComponent.load_static_data` makes during real-time execution), then invoke `parse_logcat_file(logcat_file, static_data)` to produce a `LogcatRepository` whose `classes` is populated and whose `register_method_call` correctly accumulates per-method coverage from `RVSEC-COV` entries. With this in place, the runtime path (Branch 1, current session) and the resume path (reconstruct) produce equivalent `LogcatRepository` objects, so all downstream CSV writers operate uniformly.

The reconstruct path also captures `RVSEC` violation entries via `LogcatRepository.register_rv_error`, which stores violations unconditionally and does not need `static_data`. Therefore, even when the static-analysis JSON is absent (e.g., a campaign that ran without static analysis), `errors.csv` is reliable; only the per-method coverage portion is degraded in that case. The reconstruct method MUST log a warning when `static_data` is unavailable so the researcher knows the resulting coverage rows are zero by construction, not by content.

The execution summary (returned by `Platform.run()` and displayed by the CLI) MUST also reflect the complete experiment scope. It MUST include the count of skipped tasks (from previous runs) alongside the count of executed tasks, so the researcher sees the full picture: "Total tasks: 5 (2 executed, 3 skipped from previous runs)".

#### Scenario: Result Processing After Resume Includes All Sessions

- **WHEN** `Platform.run()` resumes an experiment by skipping N previously completed tasks and executing M new tasks
- **THEN** `_process_results()` MUST pass all N+M completed tasks to `ResultProcessorComponent`
- **AND** `summary.csv` MUST contain N+M rows (one per completed task, from all sessions) with all 13 columns populated from `LogcatRepository.calculate_metrics()`
- **AND** `results.json` MUST contain summary data for all N+M completed tasks
- **AND** `results.json` MUST contain MOP violation details (violation messages, spec names, class/method) for all N+M tasks that have logcat files
- **AND** `errors.csv` MUST contain MOP violation rows for all N+M tasks that have logcat files with `RVSEC` entries
- **AND** `coverage.csv` MUST contain per-method entries for all N+M tasks that have logcat files AND static-analysis JSON available (reconstructed for the N resumed tasks via re-parse, native for the M current-session tasks)
- **AND** `performance.csv` MUST contain entries for at least the M tasks from the current session

#### Scenario: Logcat Re-Reading with On-Demand Static Data Re-Parse

- **WHEN** `ResultProcessorComponent._reconstruct_repository_from_logcat(task)` is invoked for a task whose `task.repository` is `None` (loaded from `tasks.json`)
- **AND** `task.result.logcat_file` points to an existing file on disk
- **AND** `task.static_data` is `None`
- **AND** the static-analysis JSON exists at `task.results_dir / f"{task.config.apk_name}.json"`
- **THEN** the method MUST call `static_analysis_parser.read_static_analysis_files(task.results_dir, task.config.apk_name, task.app.code_package if task.app else None)` to obtain a `StaticAnalysisData` instance
- **AND** MUST cache the result on `task.static_data` so repeated invocations within the same `ResultProcessorComponent.execute()` call do not re-parse
- **AND** MUST call `parse_logcat_file(logcat_file, static_data)` with that data
- **AND** the returned `LogcatRepository` MUST have `len(get_method_calls()) > 0` for any logcat that contains `RVSEC-COV` entries for methods present in the reachability section
- **AND** `repository.calculate_metrics().to_dict()` MUST return non-zero values for `method_coverage`, `reachable_method_coverage`, `mop_method_coverage`, and `direct_mop_method_coverage` when corresponding methods are called

#### Scenario: Static Analysis JSON Missing on Resume

- **WHEN** `ResultProcessorComponent._reconstruct_repository_from_logcat(task)` is invoked
- **AND** `task.result.logcat_file` points to an existing file
- **AND** the static-analysis JSON does not exist at `task.results_dir / f"{task.config.apk_name}.json"`
- **THEN** the method MUST log a warning: "Static analysis JSON missing for task {task.id} ({task.config.apk_name}.json) — per-method coverage will be zero, only MOP violations will be reliable"
- **AND** MUST call `parse_logcat_file(logcat_file, static_data=None)` so `RVSEC` entries are still captured
- **AND** `errors.csv` MUST contain rows for that task
- **AND** every coverage-percentage column in `summary.csv` (`cov_act`, `cov_class`, `cov_method`, `cov_rv_method`, `cov_reachable`, `cov_reaches_mop`, `cov_directly_reaches_mop`) MUST be `0.00` for that task
- **AND** `coverage.csv` MUST have zero per-method rows for that task

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
- **THEN** the header row MUST be: `apk, rep, timeout, tool, time, class, method, signature, cov_class, cov_act, cov_method, cov_rv_method, cov_reachable, cov_reaches_mop, cov_directly_reaches_mop`
- **AND** each method call MUST produce one row with progressive coverage metrics (cumulative unique methods / total methods)
- **AND** `cov_method`, `cov_act`, `cov_rv_method` MUST be cumulative-progressive (each row reflects the cumulative state up to and including that call)
- **AND** `cov_class`, `cov_reachable`, `cov_reaches_mop`, `cov_directly_reaches_mop` MUST equal the final task value from `repository.calculate_metrics().to_dict()` and are row-constant — `cov_class` MUST be `class_coverage` (NOT `method_coverage` as in the pre-fix code), `cov_reachable` MUST be `reachable_method_coverage`, `cov_reaches_mop` MUST be `mop_method_coverage`, `cov_directly_reaches_mop` MUST be `direct_mop_method_coverage`. Rationale: these metrics are derived from static-analysis denominators that do not change during execution; row-constant values match the offline regen tooling and downstream notebooks already in use
- **AND** coverage percentages MUST be rounded to 2 decimal places

#### Scenario: Errors CSV Format

- **WHEN** `errors.csv` is generated for a completed task with monitored operations violations
- **THEN** the header row MUST be: `apk, rep, timeout, tool, time, spec, class, method, message, unique_msg`
- **AND** each violation MUST produce one row
- **AND** `unique_msg` MUST be constructed as `class:::method:::spec:::error_type:::message` if not already provided

#### Scenario: Summary CSV Format

- **WHEN** `summary.csv` is generated
- **THEN** each completed task MUST produce exactly one row
- **AND** the header MUST be: `apk, rep, timeout, tool, cov_act, cov_class, cov_method, cov_reachable, cov_reaches_mop, cov_directly_reaches_mop, mop_errors_total, mop_errors_unique`
- **AND** each value MUST be read from `task.repository.calculate_metrics().to_dict()` after `_reconstruct_repository_from_logcat` populated `task.repository`
- **AND** `cov_act` MUST be the `activity_coverage` key from the dict
- **AND** `cov_class` MUST be the `class_coverage` key (NOT `method_coverage` as the pre-fix code wrote)
- **AND** `cov_method` MUST be the `method_coverage` key
- **AND** `cov_reachable` MUST be the `reachable_method_coverage` key
- **AND** `cov_reaches_mop` MUST be the `mop_method_coverage` key
- **AND** `cov_directly_reaches_mop` MUST be the `direct_mop_method_coverage` key
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


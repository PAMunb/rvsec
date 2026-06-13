# Platform — Resume Static-Data Resolution (gh65)

## Purpose

This delta closes the gap left by gh58: the resume path reconstructs per-method coverage by re-parsing the static-analysis JSON on demand, but the JSON path is built from `task.results_dir`, which is **not serialized** in `tasks.json`. `Task.to_dict()` persists only `id/config/result`; on resume, `Task.from_dict()` → `__init__` leaves `results_dir=""` (string) and `app=None`. Consequently `read_static_analysis_files("", apk, None)` builds a relative, non-existent path, the parser returns empty `StaticAnalysisData` without raising, and every CSV derived from `calculate_metrics()` is zeroed for resumed tasks.

The fix derives `results_dir` from data that **is** serialized. At runtime, `Task.initialize()` establishes the identity `task.results_dir == os.path.dirname(task.result.logcat_file)` (both built from `base_results_dir / apk_name`). Because `task.result.logcat_file` is serialized, the resume path can reconstruct the exact per-APK directory — where the static-analysis JSON is co-located as `<apk_name>.json`. Empirical validation on `experimento-20260604` (4 VMs, 169 APKs, 1299 tasks) confirmed 0 missing JSONs via this derivation.

This delta also reconciles INV-PLT-16. gh58 removed all fallback to serialized `coverage_metrics` to forbid *silent* use of stale values. The gh65 decision permits a fallback to the serialized (partial) `task.result.coverage_metrics` only when the logcat/JSON are genuinely absent, gated behind an explicit log and a counter of affected tasks — an **auditable, non-silent** fallback, not a return to the silent cascade gh58 deleted.

## Invariants

- **INV-PLT-15** (MODIFIED): `ResultProcessorComponent._resolve_static_data(task)` MUST obtain the per-APK results directory as follows: use `task.results_dir` when it is a non-empty string; otherwise, when `task.results_dir` is empty (the resume case, where it was not serialized) and `task.result.logcat_file` is set, derive it as `os.path.dirname(task.result.logcat_file)`. With that directory, `_reconstruct_repository_from_logcat(task)` MUST invoke `parse_logcat_file(logcat_file, static_data)` with a non-`None` `static_data` whenever the static-analysis JSON exists at `<derived_dir>/f"{task.config.apk_name}.json"`. When `task.static_data` is already populated, that value MUST be reused; when it is `None`, the method MUST call `static_analysis_parser.read_static_analysis_files(<derived_dir>, task.config.apk_name, task.app.code_package if task.app else None)` (note `code_package=None` is tolerated by the parser — the GATOR JSON is already filtered). If the JSON is absent, the method MUST log a warning, increment a counter of tasks with unresolved static data, and proceed with `static_data=None` — in that degraded case `errors` (including the `total_errors`/`unique_errors` aggregates, see analysis INV-ANA-25) are still reliable but per-method coverage MUST be zero.

- **INV-PLT-16** (MODIFIED): `_write_task_coverage_data` and `_write_task_summary_data` MUST read from `task.repository.calculate_metrics().to_dict()` after `_reconstruct_repository_from_logcat` has populated `task.repository`. The 3-tier silent cascade gh58 removed MUST NOT be re-introduced. However, when `_reconstruct_repository_from_logcat` cannot reconstruct coverage (logcat present but static-analysis JSON genuinely absent), the writers MAY fall back to the serialized `task.result.coverage_metrics` for the fields it carries, **only if** the fallback is logged explicitly and counted (per-task and aggregate). This is an auditable, non-silent fallback. When the logcat file itself is missing, both writers MUST emit zeroed rows with an explicit warning.

- **INV-PLT-17** (unchanged here; extended in tooling): The `cov_class` column in both `coverage.csv` and `summary.csv` MUST contain the `class_coverage` metric from `CoverageMetrics.to_dict()`. The offline tooling (`scripts/regenerate_results/`) MUST honor the same guarantee; its `verify.py` C3 check MUST validate `cov_class` rather than skipping it.

- **INV-PLT-18** (ADDED): Reconstructing a resumed task MUST produce CSV-equivalent results to the same task processed live. Formally, for any completed task `t`, the metrics computed from `Task.from_dict(t.to_dict())` followed by `_reconstruct_repository_from_logcat` (with the logcat and co-located static-analysis JSON present) MUST equal `t.repository.calculate_metrics().to_dict()` for every coverage and error field, within a rounding tolerance of `0.01`. This is the round-trip equivalence that any future change dropping a runtime field required for reconstruction MUST break. Additionally, when one or more resumed tasks have a non-empty logcat but reconstruct to zero per-method coverage (static data unresolved), `ResultProcessorComponent` MUST emit a single prominent aggregate WARNING reporting `N/M` affected tasks — the corruption MUST NOT be silent.

## MODIFIED Requirements

### Requirement: Result Consolidation on Resume (FR10-ext)

When the platform resumes an experiment (either Form 1: Expand Experiment or Form 2: Crash Recovery), the result processing phase MUST produce output files (`summary.csv`, `results.json`, `coverage.csv`, `errors.csv`, `performance.csv`) that reflect the **entire experiment state** — all completed tasks from all sessions — not just the tasks executed in the current session. Note: `errors.csv` contains **monitored operations violations** (formal property violations detected by runtime verification monitors), not application crashes or general errors. This is necessary because the output files are the researcher's primary data artifact: they are imported into analysis notebooks, used for statistical comparisons, and included in publications. If a resumed experiment's output files only contain the current session's data, the researcher loses visibility into previously completed work and must manually reconstruct the full picture from raw data files.

The mechanism for achieving this is straightforward: `_process_results()` MUST use `TaskStorage.get_completed_tasks()` as its data source instead of the filtered `Platform.tasks` list. `TaskStorage` is the authoritative source of truth for the experiment state — it contains all tasks from all sessions (loaded from `tasks.json` at startup, updated via `update_task()` during execution). The `ResultProcessorComponent` receives this complete task list and generates output files with all completed tasks included.

Tasks loaded from `tasks.json` (from previous sessions) do not have `task.repository` data — the `LogcatRepository` that `CoverageTracker` populates in-memory during task execution is runtime-only and never serialized. They also do not carry `task.results_dir` or `task.app`: `Task.to_dict()` serializes only `id/config/result`, so `Task.from_dict()` reconstructs them with `results_dir=""` and `app=None`. Without special handling, every CSV column derived from per-method calls would be empty, because `register_method_call` requires the `classes` dict populated from static-analysis data, and the JSON path built from an empty `results_dir` does not resolve. The solution reconstructs both pieces on demand: the per-APK directory is recovered from the serialized `task.result.logcat_file` via `os.path.dirname(...)` (at runtime `task.results_dir == os.path.dirname(task.result.logcat_file)`), and the static-analysis JSON co-located there is loaded by `static_analysis_parser.read_static_analysis_files(<derived_dir>, apk_name, code_package)`. `ResultProcessorComponent._reconstruct_repository_from_logcat(task)` MUST obtain `static_data` this way, then invoke `parse_logcat_file(logcat_file, static_data)` to produce a `LogcatRepository` whose `classes` is populated and whose `register_method_call` correctly accumulates per-method coverage from `RVSEC-COV` entries. With this in place, the runtime path (Branch 1, current session) and the resume path (reconstruct) produce equivalent `LogcatRepository` objects, so all downstream CSV writers operate uniformly.

The reconstruct path also captures `RVSEC` violation entries via `LogcatRepository.register_rv_error`, which stores violations unconditionally and does not need `static_data`. Therefore, even when the static-analysis JSON is absent (e.g., a campaign that ran without static analysis), `errors.csv` is reliable; per `analysis` INV-ANA-25, the `total_errors`/`unique_errors` aggregates from `calculate_metrics().to_dict()` MUST also remain accurate in that degraded case (they MUST NOT be zeroed by the absence of coverage data). Only the per-method coverage portion is degraded. The reconstruct method MUST log a warning AND increment a counter when `static_data` is unavailable, so the researcher knows the resulting coverage rows are zero by construction, not by content, and the count of affected tasks is surfaced rather than silently absorbed.

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
- **THEN** the method MUST log a warning identifying the task and the missing JSON, and MUST increment the counter of tasks with unresolved static data
- **AND** MUST call `parse_logcat_file(logcat_file, static_data=None)` so `RVSEC` entries are still captured
- **AND** `errors.csv` MUST contain rows for that task
- **AND** `summary.csv` for that task MUST report `mop_errors_total` and `mop_errors_unique` equal to the actual violation counts (NOT zeroed by the absence of coverage data)
- **AND** every coverage-percentage column in `summary.csv` (`cov_act`, `cov_class`, `cov_method`, `cov_reachable`, `cov_reaches_target`, `cov_directly_reaches_target`) MUST be `0.00` for that task (`cov_rv_method` is intentionally not a `summary.csv` column — see `result_processor._write_summary_data`, where it would alias `cov_reaches_target`; it exists only in `coverage.csv`)
- **AND** `coverage.csv` MUST have zero per-method rows for that task

#### Scenario: Auditable Fallback to Serialized Coverage Metrics

- **WHEN** coverage cannot be reconstructed for a task (logcat present but static-analysis JSON genuinely absent) and `task.result.coverage_metrics` carries serialized runtime values
- **THEN** the writer MAY use the serialized `coverage_metrics` for the fields it contains, but only after logging an explicit per-task message and incrementing the fallback counter
- **AND** the fallback MUST NOT be silent: the aggregate count of tasks that used the serialized fallback MUST be surfaced in the processing log
- **AND** when no serialized `coverage_metrics` is available either, the writer MUST emit a zeroed row with a warning rather than fabricating values

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
- **AND** the unresolved-task counter MUST equal N exactly
- **AND** when N is 0, no such warning MUST be emitted

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

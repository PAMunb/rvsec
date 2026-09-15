## Purpose

This delta bounds the memory of result export and of a long run. `ResultProcessorComponent` (`modules/rv-platform/src/rv_platform/components/result_processor.py`) makes six passes over all completed tasks, one per output file (`execute()`, `:239-244`). The coverage and summary passes store the reconstructed repository on the task (`:525`, `:955`) and `_resolve_static_data` stores the parsed static model on the task (`:361`), one per task although every execution of the same APK shares it; nothing releases either. During the run the same accumulation happens earlier: `StaticAnalysisComponent` and `CoverageComponent` assign `task.static_data` and `task.repository` (`static_analysis.py:137`, `coverage.py:61,149,307`), and `Platform` keeps the finished task, with both, in `TaskStorage` (`platform.py:430` → `task_storage.py:457`). Neither field is serialised to `tasks.json` (`Task.to_dict`, `rv-android-core/.../domain/task.py:878-890`), so nothing after completion needs them in memory.

A full campaign container was killed by the kernel inside the first export pass. The fix processes one task at a time with one static model per APK, and releases a task's repository and static model when the task finishes. Files, headers, columns and row content do not change; row order within a file follows tasks ordered by `(apk, tool, rep, timeout)`.

## Data Contracts

### Input
- `tasks: list[Task]` — the platform's task list; only `TaskState.COMPLETED` tasks are processed
- `<results_dir>/<apk>/<apk>.json` — static-analysis output, read once per APK
- `task.result.logcat_file` — the persisted logcat each repository is reconstructed from

### Output
- `coverage.csv`, `errors.csv`, `app_events.csv`, `summary.csv`, `results.json`, `performance.csv` in `results_dir`

### Side-Effects
- **Task objects**: `repository` and `static_data` are `None` after the task finishes and after its rows are written

### Error
- A writer failure for one task is counted into `task.result.write_errors` (INV-PLT-32); it does not abort the pass

## Invariants

- **INV-PLT-14**: `ResultProcessorComponent` MUST generate all six output files (`coverage.csv`, `errors.csv`, `app_events.csv`, `summary.csv`, `results.json`, `performance.csv`) when at least one completed task exists. If no completed tasks exist, it MUST log a warning and skip file generation.
- **INV-PLT-15**: `ResultProcessorComponent._resolve_static_data(task)` MUST obtain the per-APK results directory from `task.results_dir` when it is a non-empty string, and otherwise, when `task.result.logcat_file` is set, as `os.path.dirname(task.result.logcat_file)`. The component MUST hold at most one parsed static model, keyed by APK, and MUST call `static_analysis_parser.read_static_analysis_files` **at most once per APK per `execute()`** (observable via call count), replacing the cached model when the APK of the task changes. When the JSON is absent or the parser raises, the model for that APK MUST be an empty `StaticAnalysisData()`, a warning MUST be logged, and every task of that APK MUST be recorded once in `_unresolved_task_ids` (re-initialised at the start of `execute()`); such tasks keep reliable `errors` and write empty coverage cells (INV-PLT-35). `_reconstruct_repository_from_logcat(task)` MUST pass the APK's model to `parse_logcat_file`.
- **INV-PLT-38**: A task's `repository` and `static_data` MUST be `None` (a) once `Platform` has stored the finished task in `TaskStorage`, and (b) once `ResultProcessorComponent` has written that task's rows and extracted its `results.json` entry. No reader of a finished task MAY depend on either field being populated.

## MODIFIED Requirements

### Requirement: Result Generation (FR14)

The platform MUST generate standardized output files from completed experiment tasks. `ResultProcessorComponent` processes only tasks with `TaskState.COMPLETED` and generates six output files: `coverage.csv`, `errors.csv`, `app_events.csv`, `summary.csv`, `results.json`, and `performance.csv`. Result processing can be skipped during execution (via `skip_result_processing=True`) and run standalone later using `rv-platform run --process-results <results_dir>`.

This requirement serves the research purpose of the project. The CSV files are the primary data format for statistical analysis of experiment results. The JSON file provides a hierarchical view for programmatic access. The performance file captures execution timing for experiment optimization.

**Ordering dependency on `gh104-legible-violation-reports`.** That change modifies this same requirement, and it is 106 tasks done of 109 — it archives first. Its rewrite adds `code` and `event` to `errors.csv` and, in passing, **re-asserts** the twelve-column `summary.csv` scenario and restates INV-PLT-19. This block is therefore copied from gh104's modified version, not from the base spec, and edited only where `summary.csv` is concerned; gh104's `errors.csv` changes are carried through intact. Had this delta been written against the base instead, whichever of the two archived second would have silently overwritten the other's work on this requirement.

Result processing is invoked by `Platform._process_results()` after all tasks have been executed. It creates a `ResultProcessorComponent` with the complete task list and the results directory, then calls `initialize() -> execute() -> cleanup()`. The component filters for completed tasks, orders them by `(apk, tool, rep, timeout)`, opens the four streamed CSV files and writes their headers once, and then makes **one pass over the tasks**: for each task it resolves the static model, reconstructs the task's repository from its logcat, runs the four row writers and the `results.json` extractor, and releases the repository and the static model before the next task (INV-PLT-15, INV-PLT-38). The static model is cached for one APK at a time and replaced when the APK changes, which the ordering makes contiguous. `performance.csv` is generated after the pass; it reads no repository. A failure in one writer for one task is counted into that task's result and does not stop the other writers or the other tasks.

The pass is task-major rather than file-major because memory is the binding constraint of a campaign export. Six file-major passes each hold, for every task already visited, a parsed repository and a static model assigned to the task object; a campaign container of about 1,600 executions was killed by the kernel inside the first pass, after 179 to 726 tasks, with 2.8 to 4.7 million parsed methods in memory. The task-major order holds one repository and one static model at a time and was measured at 5 to 11 minutes and at most 365 MB of resident memory per container on the same data (`experimento-estudo02/scripts/regenerate_tables.py`). `results.json` is still built as one nested dictionary and written at the end; it carries no repository and no static model.

Per-method coverage rows in `coverage.csv` AND aggregate rows in `summary.csv` are produced from the same `LogcatRepository.calculate_metrics()` source. There is no separate "Branch 2 fallback" path that bypasses repository data for resumed tasks, and there is no live-repository path either: a completed task releases its repository when it finishes (INV-PLT-38), so every task's repository is reconstructed from its logcat and static-analysis JSON (see Requirement "Result Consolidation on Resume (FR10-ext)"), live run and resume alike.

The `time` column of `coverage.csv` and `errors.csv` MUST contain the entry's `time_since_task_start` — integer seconds elapsed since tool execution start — on both the live path (stamped by `CoverageTracker`) and the reconstruction path (stamped by `parse_logcat_file` from the persisted `tool_execution_start`, INV-PLT-23). Writers MUST NOT substitute row indices or any other fabricated value when timing is `0` or missing (INV-PLT-24): `0` is a legitimate first-second timestamp, and a repository reconstructed without an epoch produces `0`s that MUST be written as-is with the degraded state logged.

`errors.csv` carries thirteen columns: `apk, rep, timeout, tool, time, spec, class, method, source, code, event, message, unique_msg` (INV-PLT-19). `code` and `event` are the record's `code` and `event` fields — the `code=` and `ev=` values of the message envelope, or the sentinel `UNSPECIFIED` when the record carries no envelope — and `unique_msg` is the record's own key, read from the domain object. The writer MUST NOT assemble `unique_msg` from the other fields: the key is `__hash__` and `__eq__` of `RvErrorLog` and is built in exactly one place (core INV-CORE-25), so a formula copied into the writer would re-key a record under an identity the domain did not give it.

`summary.csv` carries seventeen columns: the twelve of the previous header, followed by `classes_total`, `methods_total`, `unmatched_out_of_scope`, `unmatched_in_scope` and `measured` (INV-PLT-19 as restated by this change). The four accounting columns publish the denominators the percentages divide by and the two discard counters of `ParserDiagnostics`; `measured` states whether the coverage cells of the row were computed at all. Appending them after `mop_errors_unique` keeps the first twelve positions stable for readers that index by position.

A failure while writing one task's rows to `errors.csv`, or while extracting one task's data for `results.json`, MUST be counted into that task's result and logged at ERROR level with the task id and the number of rows not written (INV-PLT-32). It MUST NOT be reduced to a WARNING and skipped, because the file then ends silently short of every row of that task and nothing downstream can tell a task with no violations from a task whose violations were lost. Generation of the remaining tasks and of the other files continues.

#### Scenario: Full Result Generation

- **WHEN** an experiment completes with 5 tasks, all in `COMPLETED` state
- **THEN** `ResultProcessorComponent` MUST generate all six files: `coverage.csv`, `errors.csv`, `app_events.csv`, `summary.csv`, `results.json`, `performance.csv`
- **AND** all files MUST be written to `config.results_dir`

#### Scenario: Coverage CSV Format

- **WHEN** `coverage.csv` is generated for a completed task with repository data
- **THEN** the header row MUST be: `apk, rep, timeout, tool, time, class, method, signature, cov_class, cov_act, cov_method, cov_rv_method, cov_reachable, cov_reaches_target, cov_directly_reaches_target`
- **AND** each method call MUST produce one row with progressive coverage metrics (cumulative unique methods / total methods)
- **AND** the `time` value of each row MUST be the method's `time_since_task_start` (first-call time), written as-is — including `0` for first-second calls — with rows ordered chronologically by it
- **AND** `cov_method`, `cov_act`, `cov_rv_method` MUST be cumulative-progressive (each row reflects the cumulative state up to and including that call)
- **AND** `cov_class`, `cov_reachable`, `cov_reaches_target`, `cov_directly_reaches_target` MUST equal the final task value from `repository.calculate_metrics().to_dict()` and are row-constant — `cov_class` MUST be `class_coverage` (NOT `method_coverage` as in the pre-fix code), `cov_reachable` MUST be `reachable_method_coverage`, `cov_reaches_target` MUST be `mop_method_coverage`, `cov_directly_reaches_target` MUST be `direct_mop_method_coverage`. Rationale: these metrics are derived from static-analysis denominators that do not change during execution; row-constant values match the offline regen tooling and downstream notebooks already in use
- **AND** coverage percentages MUST be rounded to 2 decimal places
- **AND** when the task's denominator is absent (`total_classes == 0`), all seven coverage values of the row — the four row-constant `cov_*_final` columns and the three per-row progressive percentages — MUST be empty cells rather than `0.00` (INV-PLT-35)

#### Scenario: Errors CSV Format

- **WHEN** `errors.csv` is generated for a completed task with monitored operations violations
- **THEN** the header row MUST be exactly: `apk,rep,timeout,tool,time,spec,class,method,source,code,event,message,unique_msg`
- **AND** each violation MUST produce one row of thirteen values
- **AND** the `source` value MUST be the violation's `RvErrorLog.source` — the source position (`File.ext:NN`) where it occurred — written as-is, empty only when the emitter supplied none
- **AND** the `code` and `event` values MUST be the violation's `RvErrorLog.code` and `RvErrorLog.event` — for a record whose message is `v=1 code=PBEKEYSPEC-FORB-01 ev=f1 obj=PBEKeySpec val='PBEKeySpec(char[])' exp='PBEKeySpec(char[],byte[],int,int)' msg='forbidden constructor'` they are `PBEKEYSPEC-FORB-01` and `f1`
- **AND** `source` MUST NOT appear in `unique_msg`, so two violations of the same misuse at different source lines share one `unique_msg` and count as one unique error
- **AND** the `time` value MUST be the violation's `time_since_task_start`, written as-is — a violation at second zero produces `0`, and no row index or counter is ever substituted (INV-PLT-24)
- **AND** `unique_msg` MUST be the record's `unique_msg` as computed by `RvErrorLog` — seven `:::`-separated parts — and the writer MUST NOT contain a fallback that assembles it from the other columns

#### Scenario: Legacy Record Without Envelope Gets the Sentinels

- **WHEN** `errors.csv` is generated for a task whose logcat was produced by the frozen `jca` set, with a violation whose message is `unknown` and carries no envelope
- **THEN** the row's `code` column MUST be `UNSPECIFIED` and its `event` column MUST be `UNSPECIFIED`
- **AND** neither MUST be an empty string, so a reader can distinguish "no envelope" from "envelope with an empty value"
- **AND** the row's `unique_msg` MUST end in `:::UNSPECIFIED:::UNSPECIFIED:::unknown`

#### Scenario: Write Failure Is Counted, Not Swallowed

- **WHEN** `_write_task_error_data` is writing the 37 violation rows of task `t-0042` and the writer raises on the 12th row
- **THEN** the failure MUST be logged at ERROR level naming task `t-0042` and stating that 26 rows were not written
- **AND** the task's result MUST record one write error for `errors.csv`
- **AND** the message MUST NOT be logged as a WARNING
- **AND** `errors.csv` generation MUST continue with the next completed task, and the other five files MUST still be generated

#### Scenario: results.json Extraction Failure Is Counted, Not Swallowed

- **WHEN** `_extract_task_data` for task `t-0042` raises while listing its violations
- **THEN** the failure MUST be logged at ERROR level naming task `t-0042`
- **AND** the task's result MUST record one extraction error for `results.json`
- **AND** the entry written for the task MUST make the loss visible, not present an empty `monitored_operations_errors` as if the task had none

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
- **AND** the header MUST be: `apk, rep, timeout, tool, cov_act, cov_class, cov_method, cov_reachable, cov_reaches_target, cov_directly_reaches_target, mop_errors_total, mop_errors_unique, classes_total, methods_total, unmatched_out_of_scope, unmatched_in_scope, measured`
- **AND** each value of the first twelve columns MUST be read from `task.repository.calculate_metrics().to_dict()` after `_reconstruct_repository_from_logcat` populated `task.repository`
- **AND** `cov_act` MUST be the `activity_coverage` key from the dict
- **AND** `cov_class` MUST be the `class_coverage` key (NOT `method_coverage` as the pre-fix code wrote)
- **AND** `cov_method` MUST be the `method_coverage` key
- **AND** `cov_reachable` MUST be the `reachable_method_coverage` key
- **AND** `cov_reaches_target` MUST be the `mop_method_coverage` key
- **AND** `cov_directly_reaches_target` MUST be the `direct_mop_method_coverage` key
- **AND** `mop_errors_total` MUST be the `total_errors` key (semantically equivalent to the renamed `errors` column from the pre-fix schema)
- **AND** `mop_errors_unique` MUST be the `unique_errors` key
- **AND** `classes_total` MUST be the `total_classes` key and `methods_total` the `total_methods` key — the denominators the percentages divide by (INV-PLT-33)
- **AND** `unmatched_out_of_scope` and `unmatched_in_scope` MUST be the two `ParserDiagnostics` discard counters, written as separate columns and never summed (INV-PLT-34)
- **AND** `measured` MUST be `true` when the coverage cells of the row were computed from a real denominator and `false` when they are empty (INV-PLT-36)
- **AND** coverage values MUST be rounded to 2 decimal places
- **AND** the twelve original columns MUST keep their positions, so a reader indexing the first twelve positionally is unaffected

#### Scenario: Results JSON Hierarchical Structure

- **WHEN** `results.json` is generated for tasks across multiple APKs, repetitions, and timeouts
- **THEN** the JSON MUST be structured as: `{apk_name: {repetitions: {rep: {timeouts: {timeout: {tools: {tool_name: data}}}}}}}`
- **AND** each tool data entry MUST contain `summary` (with coverage metrics) and `monitored_operations_errors` (with total, messages, and details)
- **AND** each entry of `messages` MUST be the record's `unique_msg` as the domain object computed it, never re-assembled from the record's fields
- **AND** when the task had no denominator, the coverage entries of `summary` MUST be `null` rather than `0` — in the repository branch (`result_processor.py:1034-1043`) and in the `else` branch that reads the serialized `coverage_metrics` (`:1050-1064`) alike (INV-PLT-35)

#### Scenario: No Completed Tasks

- **WHEN** `ResultProcessorComponent.execute()` is called and no tasks have `TaskState.COMPLETED`
- **THEN** a warning MUST be logged: "No completed tasks found for result processing"
- **AND** no output files MUST be generated

#### Scenario: Standalone Result Processing

- **WHEN** `rv-platform run --process-results <results_dir>` is invoked via CLI
- **THEN** the system MUST load tasks from the results directory's `tasks.json`
- **AND** MUST run `ResultProcessorComponent` on the loaded tasks
- **AND** MUST write output files to the same results directory

#### Scenario: Memory Does Not Grow With the Number of Tasks

- **WHEN** `ResultProcessorComponent.execute()` runs over 600 synthetic completed tasks of one APK, each with a logcat of 2,000 coverage lines and a static-analysis JSON of 5,000 methods
- **THEN** at most one `LogcatRepository` and one `StaticAnalysisData` MUST be reachable from the component and the tasks at any time after the first task
- **AND** after `execute()` returns, every task's `repository` and `static_data` MUST be `None`
- **AND** `static_analysis_parser.read_static_analysis_files` MUST have been called once for the APK

#### Scenario: One Pass Reproduces the Reference Tables

- **WHEN** the tasks of one container of a completed campaign are processed with `PYTHONHASHSEED=0`
- **THEN** `coverage.csv`, `errors.csv`, `app_events.csv`, `summary.csv` and `results.json` MUST be byte-identical to those written by `experimento-estudo02/scripts/regenerate_tables.py` for the same container under the same seed
- **AND** `performance.csv` MUST be identical to the reference in every column except `timestamp`, which records when the file was generated

## ADDED Requirements

### Requirement: A Finished Task Releases Its Parsed State

When a task finishes, `Platform` SHALL set `task.repository` and `task.static_data` to `None` after the task is stored in `TaskStorage` (INV-PLT-38). The coverage metrics a run needs after completion are already on `task.result` (`coverage.py:293`), `tasks.json` never serialises either field, and result generation reconstructs every repository from the logcat; keeping them alive only makes a long session's memory grow with each finished execution.

#### Scenario: A finished task holds no parsed state

- **WHEN** a task completes and `Platform` calls `task_storage.update_task(task)`
- **THEN** immediately afterwards `task.repository` MUST be `None` and `task.static_data` MUST be `None`
- **AND** `task.result.coverage_metrics` MUST be unchanged
- **AND** the task's rows produced by `ResultProcessorComponent` at the end of the run MUST equal those produced for the same task by `rv-platform run --process-results`

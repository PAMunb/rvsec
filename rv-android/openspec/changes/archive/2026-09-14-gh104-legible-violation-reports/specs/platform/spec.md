## Purpose

The `platform` capability owns `ResultProcessorComponent`, the writer of the five output files, and among them `errors.csv` — the file every downstream analysis of violations reads. This change touches it for two reasons. First, the record it serialises gains two fields: in the published dataset 72.93 % of the 97,018 violation rows carry the literal `unknown` as their message, and no column says which event of the automaton fired, so per-event attribution is impossible from the file. The successor set `jca_android` emits a message envelope carrying a stable `code=` and the offending `ev=`; the `core` delta admits both into `RvErrorLog` and its identity; this delta writes them out as two new columns, `code` and `event`, placed after `source`, filled with the sentinel `UNSPECIFIED` when the record carries no envelope so a legacy row is well-formed and its absence of attribution is explicit rather than an empty cell.

Second, the transport from the domain object to the file is not honest today. `_write_task_error_data` catches every exception of a task's rows and logs a WARNING (`result_processor.py:654-655`); the `results.json` path does the same (`:1046-1047`). A single bad record silently loses every row of that task, and nothing in the output says so. And the same writer carries three copies of the `unique_msg` formula as fallbacks (`:631`, `:999`, `:1038`), so a record whose `unique_msg` were ever missing would be re-keyed here under a formula that need not match the domain's. Both are replaced: a write failure is counted into the task result and logged as an error with the number of rows it lost, and the fallbacks are deleted because the domain object always carries the key (core INV-CORE-25).

The header of `errors.csv` is a contract shared with `rvsec-dataset`, `aperv_tool.analysis.violations.ERRORS_CSV_HEADER` and the article's scripts; the `campaign-analysis` delta changes its reader in step. Readers that address columns by name tolerate the two new columns; readers that address them positionally do not, and the consumer matrix of the proposal names each of them.

## Data Contracts

Only the entries this change alters are restated; every other input, output, side-effect and error of the capability is unchanged.

### Input

- `RvErrorLog.to_dict()` records -- from `task.repository.get_errors()` or the reconstructed repository; each carries `code`, `event` and `unique_msg` (source: `rv-android-core`, core INV-CORE-25)

### Output

- `errors.csv` -- Monitored operations violations; columns: `apk, rep, timeout, tool, time, spec, class, method, source, code, event, message, unique_msg` (13 columns; destination: `rvsec-dataset`, `aperv_tool.analysis.violations`, article scripts). This entry replaces the 11-column list of the upstream Data Contracts (`openspec/specs/platform/spec.md:131`), which lacks `code` and `event`.
- `results.json` -- `monitored_operations_errors.messages` lists each record's `unique_msg` exactly as the domain object computed it (destination: programmatic consumers)

### Side-Effects

- **[Task result]**: a failure while writing a task's rows to `errors.csv` or while extracting a task's data for `results.json` increments an error count on that task's result and is logged at ERROR level with the task id and the number of rows not written

### Error

- `Exception` from the CSV writer or from `to_dict()` during `_write_task_error_data` or the `results.json` extraction -- counted into the task result and logged as an error; never reduced to a WARNING that hides the rows of the task

## Invariants

- **INV-PLT-19** (restated, replacing the entry of the same number): The headers and column order of `coverage.csv`, `errors.csv` and `summary.csv` MUST NOT be changed by the diagnostic-events feature — every diagnostic field belongs to `app_events.csv` alone. `errors.csv` carries exactly `apk, rep, timeout, tool, time, spec, class, method, source, code, event, message, unique_msg`; `source` was added by gh89 and `code`, `event` by this change, and these three are the only additions since the baseline. `coverage.csv` and `summary.csv` remain byte-identical to baseline.
- **INV-PLT-32**: A failure to write a task's violation rows (`errors.csv`) or to extract a task's violation data (`results.json`) MUST be counted into that task's result and logged at ERROR level with the number of rows lost. It MUST NOT be swallowed as a WARNING that leaves the file silently short, and the writer MUST NOT re-key the record: `unique_msg` MUST be read from the domain object, never assembled in the writer (core INV-CORE-25).

## MODIFIED Requirements

### Requirement: Result Generation (FR14)

The platform MUST generate standardized output files from completed experiment tasks. `ResultProcessorComponent` processes only tasks with `TaskState.COMPLETED` and generates five output files: `coverage.csv`, `errors.csv`, `summary.csv`, `results.json`, and `performance.csv`. Result processing can be skipped during execution (via `skip_result_processing=True`) and run standalone later using `rv-platform run --process-results <results_dir>`.

This requirement serves the research purpose of the project. The CSV files are the primary data format for statistical analysis of experiment results. The JSON file provides a hierarchical view for programmatic access. The performance file captures execution timing for experiment optimization.

Result processing is invoked by `Platform._process_results()` after all tasks have been executed. It creates a `ResultProcessorComponent` with the complete task list and the results directory, then calls `initialize() -> execute() -> cleanup()`. The component filters for completed tasks and generates each file independently, using `ErrorHandler` decorators to ensure that a failure in one file generation does not prevent the others.

Per-method coverage rows in `coverage.csv` AND aggregate rows in `summary.csv` are produced from the same `LogcatRepository.calculate_metrics()` source. There is no separate "Branch 2 fallback" path that bypasses repository data for resumed tasks; reconstruction of `task.repository` from logcat + static-analysis JSON (see Requirement "Result Consolidation on Resume (FR10-ext)") ensures both writers operate uniformly on a populated repository.

The `time` column of `coverage.csv` and `errors.csv` MUST contain the entry's `time_since_task_start` — integer seconds elapsed since tool execution start — on both the live path (stamped by `CoverageTracker`) and the reconstruction path (stamped by `parse_logcat_file` from the persisted `tool_execution_start`, INV-PLT-23). Writers MUST NOT substitute row indices or any other fabricated value when timing is `0` or missing (INV-PLT-24): `0` is a legitimate first-second timestamp, and a repository reconstructed without an epoch produces `0`s that MUST be written as-is with the degraded state logged.

`errors.csv` carries thirteen columns: `apk, rep, timeout, tool, time, spec, class, method, source, code, event, message, unique_msg` (INV-PLT-19). `code` and `event` are the record's `code` and `event` fields — the `code=` and `ev=` values of the message envelope, or the sentinel `UNSPECIFIED` when the record carries no envelope — and `unique_msg` is the record's own key, read from the domain object. The writer MUST NOT assemble `unique_msg` from the other fields: the key is `__hash__` and `__eq__` of `RvErrorLog` and is built in exactly one place (core INV-CORE-25), so a formula copied into the writer would re-key a record under an identity the domain did not give it.

A failure while writing one task's rows to `errors.csv`, or while extracting one task's data for `results.json`, MUST be counted into that task's result and logged at ERROR level with the task id and the number of rows not written (INV-PLT-32). It MUST NOT be reduced to a WARNING and skipped, because the file then ends silently short of every row of that task and nothing downstream can tell a task with no violations from a task whose violations were lost. Generation of the remaining tasks and of the other files continues.

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
- **AND** `errors.csv` generation MUST continue with the next completed task, and the other four files MUST still be generated

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
- **AND** each entry of `messages` MUST be the record's `unique_msg` as the domain object computed it, never re-assembled from the record's fields

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
`coverage.csv` and `summary.csv` writers and schemas SHALL remain unchanged; `errors.csv` is governed by
`Requirement: Result Generation (FR14)`, whose 13-column header carries `code` and `event`.

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
- **THEN** the headers of `coverage.csv` and `summary.csv` are byte-identical to baseline
- **AND** the header of `errors.csv` is the 13-column header of `Requirement: Result Generation (FR14)`

#### Scenario: app_events survives resume reconstruction
- **WHEN** a task is processed via `_reconstruct_repository_from_logcat` (resume) and its `.logcat`
  contains a crash block
- **THEN** the reconstructed repository yields the crash event and `app_events.csv` includes its row
- **AND** the row's `time` value equals the event's `time_since_task_start` stamped from the persisted
  `tool_execution_start` (not a row index)

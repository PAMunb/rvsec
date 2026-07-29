# Platform — delta for gh89-error-description-key

## Purpose

`ResultProcessorComponent`
(`modules/rv-platform/src/rv_platform/components/result_processor.py`) writes the per-run
`errors.csv` that is the researcher's primary artifact for monitored-operations violations: it
is what `rvsec-dataset` assembles and what the thesis and journal analysis scripts read. Its
column set is therefore a published contract, and this delta changes it — one column, `source`,
appended after `method`.

The reason is the defect gh89 fixes upstream. A violation record identifies *where* a
specification was violated, and the `(apk, class, method, spec)` key built from it identifies
one **unique misuse**. When the monitor failed to split a stack frame it left the whole frame —
source position included — inside `class` and `method`, so the line number silently joined that
key and one misuse was counted once per line it occurred at. The parser now strips the position
out of those two fields and binds it to `RvErrorLog.source`.

That leaves a choice about the position itself, and the two available options are not the same
decision. Keeping it *out of the key* is mandatory — that is the whole fix. *Discarding* it is
a separate and unnecessary loss: until now `to_dict()` omitted `source`, so the field was parsed
and then thrown away and no consumer could see it. The position is the most direct pointer to
where a violation happened, and it is the evidence needed to audit, after a campaign has run,
whether a frame-form normalization fired and on what. So it is written to its own column, and to
no key.

The column is appended by name rather than replacing anything, because every known consumer
addresses this file by column name — `rvsec-dataset` (`unittests/report.py`,
`unittests/classify.py`) and the `ase-journal` analysis scripts all use `csv.DictReader`,
`pandas.read_csv`, or a `header.index(...)` lookup. That was verified against those consumers
rather than assumed, and the verification is a precondition of this delta, not a follow-up.

## Data Contracts

### Input
- `error: Dict[str, Any]` — one entry from `LogcatRepository.get_errors()`, i.e.
  `RvErrorLog.to_dict()`, which now carries `source`.

### Output
- `errors.csv` — 11 columns:
  `apk, rep, timeout, tool, time, spec, class, method, source, message, unique_msg`.

### Side-Effects
- **[Filesystem]**: one column is added to `errors.csv`. `coverage.csv`, `summary.csv`,
  `performance.csv`, `results.json` and `app_events.csv` are untouched.

### Error
- None added. A record serialized before `source` entered the schema yields an empty cell
  rather than a failure.

## Invariants

- **INV-PLT-19** (amended): The headers and column order of `coverage.csv`, `errors.csv` and
  `summary.csv` MUST NOT be changed by the diagnostic-events feature — every diagnostic field
  belongs to `app_events.csv` alone. `errors.csv` carries exactly
  `apk, rep, timeout, tool, time, spec, class, method, source, message, unique_msg`; the
  `source` column is gh89's and is the only addition since the baseline. `coverage.csv` and
  `summary.csv` remain byte-identical to baseline.
- **INV-PLT-25**: The `source` column MUST NOT participate in any key, count or aggregate.
  Adding it MUST NOT change `total_errors`, `unique_errors`, `mop_errors_unique`, or any
  coverage metric, because `RvErrorLog.unique_msg`, `__eq__` and `__hash__` exclude it
  (core INV-CORE-40).
- **INV-PLT-26**: No value written to the `class` or `method` column of `errors.csv` MUST end
  with a `(<file>:<line>)` group. The source position belongs to the `source` column alone
  (analysis INV-ANA-50, core INV-CORE-42).

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
- **THEN** the header row MUST be: `apk, rep, timeout, tool, time, spec, class, method, source, message, unique_msg`
- **AND** each violation MUST produce one row
- **AND** the `source` value MUST be the violation's `RvErrorLog.source` — the source position (`File.ext:NN`) where it occurred — written as-is, empty only when the emitter supplied none
- **AND** `source` MUST NOT appear in `unique_msg`, so two violations of the same misuse at different source lines share one `unique_msg` and count as one unique error
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

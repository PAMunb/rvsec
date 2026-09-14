## Purpose

The platform capability executes tasks and turns their outcome into the run's report. `ResultProcessor` writes `summary.csv`, `errors.csv` and the performance files, and those columns are what every downstream reading of a campaign consults.

Today the report publishes fractions without publishing what produced them. `cov_class` and `cov_method` appear; the denominators do not. Nothing states how many runtime events were dropped, or why. A run whose denominator collapsed to one class and a run that genuinely covered everything write the same `100.00`, and a run whose denominator was empty writes `0.00` — the same value as a run that executed and covered nothing.

This change adds the accounting that the analysis and core capabilities produce, so that the CSV a reader opens carries the evidence needed to trust or distrust its own numbers. Adding columns to `summary.csv` is not a free act: the base requirement freezes that header by name, so this delta must modify the requirement that freezes it rather than quietly widening the file underneath it.

## Data Contracts

### Input

- `ParserDiagnostics` — discard counters, split out-of-scope × in-scope (source: `rv-android-core`, `modules/rv-android-core/src/rv_android_core/domain/coverage.py:453`, INV-ANA-68). It is **not** defined in `rv-coverage`.
- `LogcatRepository` — the object whose `calculate_metrics()` produces the class and method denominators and numerators (source: `rv-android-core`, `modules/rv-android-core/src/rv_android_core/domain/coverage.py:559`, INV-CORE-60). There is no class named `CoverageData` in the tree; the writer reads `LogcatRepository.calculate_metrics().to_dict()`.

### Output

- `summary.csv` — gains `classes_total`, `methods_total`, `unmatched_out_of_scope`, `unmatched_in_scope` and `measured`, appended after `mop_errors_unique`, for a seventeen-column header (INV-PLT-19 as restated below)
- `scripts/regenerate_results/regenerate_container.py` is a **second writer** of the same file: its module-level `SUMMARY_HEADER` (`:78-91`, under the comment "Exact headers from result_processor.py") is written at `:385`. It is a hand-maintained copy with no test guarding the duplication, so this change must reconcile it in the same commit or the offline regeneration path silently produces a twelve-column `summary.csv` while `rv-platform` produces seventeen.

### Side-Effects

- **[Filesystem]**: the CSVs written under `results/<id>/`

### Error

- None new; a refused denominator aborts upstream, in the analysis capability

## Invariants

- **INV-PLT-19** (restated, replacing both the entry of the same number in `openspec/specs/platform/spec.md:192` and its restatement in the `gh104-legible-violation-reports` delta): The headers and column order of `coverage.csv`, `errors.csv` and `summary.csv` are contracts and MUST NOT drift except by restating this invariant. `coverage.csv` keeps its fifteen-column header unchanged. `errors.csv` carries exactly `apk, rep, timeout, tool, time, spec, class, method, source, code, event, message, unique_msg` — `source` from gh89, `code` and `event` from gh104. `summary.csv` carries exactly, and in this order:

  `apk, rep, timeout, tool, cov_act, cov_class, cov_method, cov_reachable, cov_reaches_target, cov_directly_reaches_target, mop_errors_total, mop_errors_unique, classes_total, methods_total, unmatched_out_of_scope, unmatched_in_scope, measured`

  The five new columns are appended after `mop_errors_unique`, so a reader addressing the first twelve positionally still reads what it read before. From this change forward the byte-identity guarantee holds against **this** seventeen-column header, not the twelve-column baseline: any later change that adds, removes or reorders a column MUST restate this invariant with the new header, so the invariant keeps being a tripwire instead of quietly becoming false. Every other writer of `summary.csv` in the repository MUST emit this same header — specifically `SUMMARY_HEADER` in `scripts/regenerate_results/regenerate_container.py:78-91`, written at `:385`.

- **INV-PLT-33**: `summary.csv` MUST publish the denominators alongside the percentages. A row carrying `cov_class` MUST also carry the class count that percentage divides by, and a row carrying `cov_method` MUST also carry the method count. A percentage whose denominator is not in the same row cannot be audited after the fact.

- **INV-PLT-34**: `summary.csv` MUST publish the two discard counters as separate columns. They MUST NOT be summed into one, and a run in which the parser produced no diagnostics MUST write empty cells rather than zeros, so that "not measured" and "measured as zero" remain distinguishable.

- **INV-PLT-35**: A task whose coverage has no denominator MUST write **empty** cells for every derived coverage value and MUST NOT write `0.00` or `0`. This covers **all six** percentage columns of `summary.csv` — `cov_act`, `cov_class`, `cov_method`, `cov_reachable`, `cov_reaches_target`, `cov_directly_reaches_target` — not the three originally named, because `_write_task_summary_data` builds all six through the same `_val` helper (`result_processor.py:903-917`) and `LogcatRepository.calculate_metrics()` returns early when `self.classes` is empty (`rv-android-core/.../domain/coverage.py:742-746`), leaving all six numerators and denominators at `0` so all six write `0.00`. The denominator columns `classes_total` and `methods_total` MUST be empty in the same case.

  The same rule reaches two further artefacts, each named explicitly:
  - `coverage.csv` — **two mechanisms, both covered**: the four `cov_*_final` row-constant columns (`cov_class`, `cov_reachable`, `cov_reaches_target`, `cov_directly_reaches_target`), built with `round(metrics_dict.get(..., 0) or 0, 2)` at `result_processor.py:483-492`, **and** the three per-row progressive percentages (`cov_act`, `cov_method`, `cov_rv_method`), computed in the row loop at `~:496-545` and written at `:555-557`. All seven MUST be empty in the denominator-less case rather than `0.00`.
  - `results.json` — the `summary` block at `result_processor.py:1025-1035` and the stale-read `else` branch at `:1050-1064` (which reads the serialized `coverage_metrics` with `.get(..., 0)`) MUST NOT emit `0` as a measured value when no denominator existed; the absence MUST be representable as `null`.

  The rule deliberately stops at the CSVs and `results.json`: `tasks.json`'s `coverage_metrics` keeps `0.0` for the unmeasured case, by design. That field is consumed as a number by the resume protocol (`TaskResult.from_dict`) and by aperv-tool's loader, and the not-measured distinction is already carried where readers aggregate — the empty cells and the `measured` column. aperv-tool's `_coverage_rank` ranks a missing number below every present one on its own side, so the two artefacts stay individually coherent.

  The discriminator MUST be the denominator itself — `metrics_dict.get("total_classes", 0) == 0`, already in scope at `result_processor.py:899`. It MUST NOT be `self._unresolved_task_ids`: that set is populated only by `_resolve_static_data` (`:316`), reached only via `_reconstruct_repository_from_logcat` (`:379`), which the writer calls only when `not task.repository` (`:889-892`) — the resume path. On the live path a task whose static analysis failed runs to completion with an empty-classes repository (INV-PLT-05), writes six `0.00`, and never enters the set. The denominator is the only discriminator true on both paths.

  The row's violation columns MUST still be written, because violation detection does not depend on static analysis (INV-EXP-16 as modified by this change).

- **INV-PLT-36**: `summary.csv` MUST carry a `measured` boolean column stating whether the row's coverage cells were computed from a real denominator. Its value MUST be `true` exactly when the coverage cells are filled and `false` exactly when they are empty; it MUST never be empty itself, because a column whose purpose is to survive aggregation cannot itself go missing.

- **INV-PLT-15** (**amended, not replaced**): the base invariant at `openspec/specs/platform/spec.md:184` stands in full — the directory derivation, the `task.static_data` memo, the membership-guarded `_unresolved_task_ids` set and the at-most-once parse are unchanged by this change. One clause is amended: where the base says that in the degraded case "per-method coverage MUST be zero", it MUST now read that per-method coverage rows are **absent** and the task's coverage cells are **empty** (INV-PLT-35). `errors` aggregates remain reliable, as the base already states.

- **INV-PLT-16** (**amended, not replaced**): the base invariant at `openspec/specs/platform/spec.md:186` stands in full — the unification of `_write_task_coverage_data` and `_write_task_summary_data` onto one repository-backed path, and the removal of the three-tier cascade and of the `else` branch, are unchanged. Its final clause is amended: where the base says both writers "MUST emit zeroed rows with an explicit warning" when reconstruction returns `None`, it MUST now read **empty** coverage cells with an explicit warning. The prohibition on falling back to stale serialized values is unchanged; only zero stops being an admissible way to say "not measured" (INV-PLT-35).

- **INV-PLT-37** (new; **INV-PLT-17 of the base is untouched**): the consistency between `summary.csv` and `coverage.csv` becomes directional — when a task has **no denominator**, its `coverage.csv` per-method rows number zero **and** its `summary.csv` coverage cells are empty with `measured=false`; when a task has a denominator and covered nothing, its rows number zero **and** its cells read `0.00` with `measured=true`. Any consistency check (such as `verify.py` C3, `scripts/regenerate_results/verify.py:164`) MUST be updated to this directional form.

  This rule carries a **new number on purpose**. The base spec attributes the `summary cov_* == 0 whenever coverage_rows == 0` rule to INV-PLT-17 in a scenario bullet at `openspec/specs/platform/spec.md:521`, but the invariant that actually bears that number (`:188`) says something else entirely — that `cov_class` MUST hold `class_coverage`, the guard against the pre-fix code writing `method_coverage` into that slot. Restating "INV-PLT-17" would have deleted that guard at hand-sync time (task 8.17) while believing it was amending a consistency rule. The bullet at `:521` is corrected by this delta's own scenario; the invariant keeps its meaning and its number.

- **INV-PLT-18** (**amended, not replaced**): the base invariant at `openspec/specs/platform/spec.md:190` stands in full — the round-trip equivalence between a live and a reconstructed task, within a rounding tolerance of `0.01`, is unchanged and remains the tripwire for any future change that drops a field reconstruction needs. Its final clause is amended: the aggregate resume-health WARNING is kept but reworded to "Resume coverage health: N/M resumed tasks had unresolved static data — coverage cells left empty for those tasks" (`result_processor.py:206`), because "coverage zeroed" would describe exactly the behaviour INV-PLT-35 forbids.

## MODIFIED Requirements

### Requirement: Result Generation (FR14)

The platform MUST generate standardized output files from completed experiment tasks. `ResultProcessorComponent` processes only tasks with `TaskState.COMPLETED` and generates five output files: `coverage.csv`, `errors.csv`, `summary.csv`, `results.json`, and `performance.csv`. Result processing can be skipped during execution (via `skip_result_processing=True`) and run standalone later using `rv-platform run --process-results <results_dir>`.

This requirement serves the research purpose of the project. The CSV files are the primary data format for statistical analysis of experiment results. The JSON file provides a hierarchical view for programmatic access. The performance file captures execution timing for experiment optimization.

**Ordering dependency on `gh104-legible-violation-reports`.** That change modifies this same requirement, and it is 106 tasks done of 109 — it archives first. Its rewrite adds `code` and `event` to `errors.csv` and, in passing, **re-asserts** the twelve-column `summary.csv` scenario and restates INV-PLT-19. This block is therefore copied from gh104's modified version, not from the base spec, and edited only where `summary.csv` is concerned; gh104's `errors.csv` changes are carried through intact. Had this delta been written against the base instead, whichever of the two archived second would have silently overwritten the other's work on this requirement.

Result processing is invoked by `Platform._process_results()` after all tasks have been executed. It creates a `ResultProcessorComponent` with the complete task list and the results directory, then calls `initialize() -> execute() -> cleanup()`. The component filters for completed tasks and generates each file independently, using `ErrorHandler` decorators to ensure that a failure in one file generation does not prevent the others.

Per-method coverage rows in `coverage.csv` AND aggregate rows in `summary.csv` are produced from the same `LogcatRepository.calculate_metrics()` source. There is no separate "Branch 2 fallback" path that bypasses repository data for resumed tasks; reconstruction of `task.repository` from logcat + static-analysis JSON (see Requirement "Result Consolidation on Resume (FR10-ext)") ensures both writers operate uniformly on a populated repository.

The `time` column of `coverage.csv` and `errors.csv` MUST contain the entry's `time_since_task_start` — integer seconds elapsed since tool execution start — on both the live path (stamped by `CoverageTracker`) and the reconstruction path (stamped by `parse_logcat_file` from the persisted `tool_execution_start`, INV-PLT-23). Writers MUST NOT substitute row indices or any other fabricated value when timing is `0` or missing (INV-PLT-24): `0` is a legitimate first-second timestamp, and a repository reconstructed without an epoch produces `0`s that MUST be written as-is with the degraded state logged.

`errors.csv` carries thirteen columns: `apk, rep, timeout, tool, time, spec, class, method, source, code, event, message, unique_msg` (INV-PLT-19). `code` and `event` are the record's `code` and `event` fields — the `code=` and `ev=` values of the message envelope, or the sentinel `UNSPECIFIED` when the record carries no envelope — and `unique_msg` is the record's own key, read from the domain object. The writer MUST NOT assemble `unique_msg` from the other fields: the key is `__hash__` and `__eq__` of `RvErrorLog` and is built in exactly one place (core INV-CORE-25), so a formula copied into the writer would re-key a record under an identity the domain did not give it.

`summary.csv` carries seventeen columns: the twelve of the previous header, followed by `classes_total`, `methods_total`, `unmatched_out_of_scope`, `unmatched_in_scope` and `measured` (INV-PLT-19 as restated by this change). The four accounting columns publish the denominators the percentages divide by and the two discard counters of `ParserDiagnostics`; `measured` states whether the coverage cells of the row were computed at all. Appending them after `mop_errors_unique` keeps the first twelve positions stable for readers that index by position.

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

### Requirement: Result Consolidation on Resume (FR10-ext)

When the platform resumes an experiment (either Form 1: Expand Experiment or Form 2: Crash Recovery), the result processing phase MUST produce output files (`summary.csv`, `results.json`, `coverage.csv`, `errors.csv`, `performance.csv`) that reflect the **entire experiment state** — all completed tasks from all sessions — not just the tasks executed in the current session. Note: `errors.csv` contains **monitored operations violations** (formal property violations detected by runtime verification monitors), not application crashes or general errors. This is necessary because the output files are the researcher's primary data artifact: they are imported into analysis notebooks, used for statistical comparisons, and included in publications. If a resumed experiment's output files only contain the current session's data, the researcher loses visibility into previously completed work and must manually reconstruct the full picture from raw data files.

The mechanism for achieving this is straightforward: `_process_results()` MUST use `TaskStorage.get_completed_tasks()` as its data source instead of the filtered `Platform.tasks` list. `TaskStorage` is the authoritative source of truth for the experiment state — it contains all tasks from all sessions (loaded from `tasks.json` at startup, updated via `update_task()` during execution). The `ResultProcessorComponent` receives this complete task list and generates output files with all completed tasks included.

Tasks loaded from `tasks.json` (from previous sessions) do not have `task.repository` data — the `LogcatRepository` that `CoverageTracker` populates in-memory during task execution is runtime-only and never serialized. They also do not carry `task.results_dir` or `task.app`: `Task.to_dict()` serializes only `id/config/result`, so `Task.from_dict()` reconstructs them with `results_dir=""` and `app=None`. Without special handling, every CSV column derived from per-method calls would be empty, because `register_method_call` requires the `classes` dict populated from static-analysis data, and the JSON path built from an empty `results_dir` does not resolve. The solution reconstructs both pieces on demand: the per-APK directory is recovered from the serialized `task.result.logcat_file` via `os.path.dirname(...)` (at runtime `task.results_dir == os.path.dirname(task.result.logcat_file)`), and the static-analysis JSON co-located there is loaded by `static_analysis_parser.read_static_analysis_files(<derived_dir>, apk_name, code_package)`. `ResultProcessorComponent._reconstruct_repository_from_logcat(task)` MUST obtain `static_data` this way, then invoke `parse_logcat_file(logcat_file, static_data)` to produce a `LogcatRepository` whose `classes` is populated and whose `register_method_call` correctly accumulates per-method coverage from `RVSEC-COV` entries. With this in place, the runtime path (Branch 1, current session) and the resume path (reconstruct) produce equivalent `LogcatRepository` objects, so all downstream CSV writers operate uniformly.

The reconstruct path also captures `RVSEC` violation entries via `LogcatRepository.register_rv_error`, which stores violations unconditionally and does not need `static_data`. Therefore, even when the static-analysis JSON is absent (e.g., a campaign that ran without static analysis), `errors.csv` is reliable; per `analysis` INV-ANA-25, the `total_errors`/`unique_errors` aggregates from `calculate_metrics().to_dict()` MUST also remain accurate in that degraded case (they MUST NOT be zeroed by the absence of coverage data). Only the per-method coverage portion is degraded — and it degrades to **empty cells with `measured=false`**, never to `0.00` (INV-PLT-35 — a zeroed column would be indistinguishable from a measured zero, which is exactly the ambiguity that invariant removes). The reconstruct method MUST log a warning AND increment a counter (at most once per task) when `static_data` is unavailable, so the researcher knows the resulting coverage cells are empty by construction, not covered-nothing by content, and the count of affected tasks is surfaced rather than silently absorbed.

The execution summary (returned by `Platform.run()` and displayed by the CLI) MUST also reflect the complete experiment scope. It MUST include the count of skipped tasks (from previous runs) alongside the count of executed tasks, so the researcher sees the full picture: "Total tasks: 5 (2 executed, 3 skipped from previous runs)".

#### Scenario: Result Processing After Resume Includes All Sessions

- **WHEN** `Platform.run()` resumes an experiment by skipping N previously completed tasks and executing M new tasks
- **THEN** `_process_results()` MUST pass all N+M completed tasks to `ResultProcessorComponent`
- **AND** `summary.csv` MUST contain N+M rows (one per completed task, from all sessions) with all coverage and error columns populated from `LogcatRepository.calculate_metrics()` — coverage cells empty, per INV-PLT-35, for any task without a denominator
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
- **AND** every coverage-percentage column in `summary.csv` (`cov_act`, `cov_class`, `cov_method`, `cov_reachable`, `cov_reaches_target`, `cov_directly_reaches_target`) MUST be **empty** for that task, with `classes_total` and `methods_total` empty and `measured = false` (INV-PLT-35, INV-PLT-36; `cov_rv_method` is intentionally not a `summary.csv` column — see `result_processor._write_summary_data`, where it would alias `cov_reaches_target`; it exists only in `coverage.csv`)
- **AND** `coverage.csv` MUST have zero per-method rows for that task

#### Scenario: No Fallback to Serialized Coverage Metrics When JSON Is Absent

- **WHEN** coverage cannot be reconstructed for a task (logcat present but static-analysis JSON genuinely absent) and `task.result.coverage_metrics` carries serialized runtime values
- **THEN** the writer MUST NOT use the serialized `coverage_metrics` to populate `summary.csv` `cov_*` columns
- **AND** every coverage-percentage column in the `summary.csv` row for that task MUST be **empty** with `measured = false`, consistent with the zero per-method rows in `coverage.csv` under the directional form of the consistency check (INV-PLT-37: no denominator → zero rows **and** empty cells; denominator with nothing covered → zero rows **and** `0.00`)
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
- **AND** this equivalence MUST hold across at least three logcat fixtures: one with MOP violations, one representing a `--skip-static` run (logcat present, no JSON → coverage cells empty but errors accurate), and one normal coverage-bearing run

#### Scenario: Resume Coverage Health Check Warning

- **WHEN** `ResultProcessorComponent.execute()` finishes processing all completed tasks
- **AND** N of the M resumed tasks had a non-empty logcat file but reconstructed to empty coverage cells because static data was unresolved
- **THEN** the component MUST emit exactly one prominent aggregate WARNING of the form "Resume coverage health: N/M resumed tasks had unresolved static data — coverage cells left empty for those tasks" (INV-PLT-18 as restated by this change)
- **AND** `len(_unresolved_task_ids)` MUST equal N exactly (each affected task counted once)
- **AND** when N is 0, no such warning MUST be emitted
- **AND** a subsequent `execute()` pass MUST start from a re-initialized set, so its `N` reflects only that pass (not an accumulation across passes)

#### Scenario: Logcat File Missing on Resume

- **WHEN** `ResultProcessorComponent` processes a completed task whose `task.repository` is `None`
- **AND** `task.result.logcat_file` does not exist on disk, or is `None`
- **THEN** `ResultProcessorComponent` MUST log a warning: "No logcat file available for task {task.id} — MOP violation details cannot be reconstructed"
- **AND** `errors.csv` MUST NOT have entries for that task (no data source to reconstruct from)
- **AND** `results.json` MUST include the task with empty violation details and `null` coverage entries (INV-PLT-35)
- **AND** `summary.csv` MUST include the task row with all coverage cells **empty**, `measured = false`, and `mop_errors_total = mop_errors_unique = 0`
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

## ADDED Requirements

### Requirement: The Report Publishes Its Denominators

`ResultProcessor` SHALL write the class and method denominators as columns of `summary.csv`, alongside the percentages computed from them.

A percentage alone cannot be audited. The four collapsed artefacts of the article corpus publish `cov_class` values of `100.00` and `0.00` that are indistinguishable, in the CSV, from correct measurements — and the collapse was found by reading artefacts, not reports. With the denominator present, a reader sees `1` where the app has 771 classes without opening anything else.

The denominator is also the writer's discriminator. `metrics_dict.get("total_classes", 0) == 0` is the single test that separates "no denominator" from "covered nothing", and it holds on both the live and the resume path (INV-PLT-35).

#### Scenario: A healthy row
- **WHEN** an APK with 550 classes in its denominator covers 96 of them
- **THEN** `summary.csv` MUST carry `classes_total = 550`
- **AND** it MUST carry `cov_class` computed from that denominator

#### Scenario: A degenerate denominator that reached the report
- **WHEN** an APK's denominator is 1 class and that class was covered
- **THEN** `summary.csv` MUST carry `classes_total = 1` next to `cov_class = 100.00`
- **AND** the two together MUST make the degeneracy readable without consulting the artefact

#### Scenario: An APK that ran without static analysis
- **WHEN** an APK executed with no `.apk.json` and its logcat carried 7 violations
- **THEN** all six percentage cells — `cov_act`, `cov_class`, `cov_method`, `cov_reachable`, `cov_reaches_target`, `cov_directly_reaches_target` — MUST be empty, and so MUST `classes_total` and `methods_total`
- **AND** `mop_errors_total` MUST be `7`
- **AND** no coverage cell MUST read `0.00`, because that value asserts a measurement that had no denominator
- **AND** the same task's `coverage.csv` rows MUST leave their seven `cov_*_final` cells empty, and its `results.json` coverage entries MUST be `null`

#### Scenario: An APK that ran and genuinely covered nothing
- **WHEN** an APK has a 705-class denominator and its logcat carried no `RVSEC-COV` line
- **THEN** `classes_total` MUST be `705`
- **AND** `cov_class` MUST be `0.00`
- **AND** the pair MUST be distinguishable from the previous scenario by the presence of the denominator

#### Scenario: The live path with failed static analysis is caught by the denominator, not by the resume set
- **WHEN** a task runs to completion on the live path with an empty-classes repository, so `task.repository` is populated and `_reconstruct_repository_from_logcat` is never called
- **THEN** the writer MUST still leave all six coverage cells empty, because it tests `metrics_dict.get("total_classes", 0) == 0`
- **AND** it MUST NOT decide by membership in `self._unresolved_task_ids`, which this task never enters

### Requirement: The Report Publishes What the Crossing Discarded

`ResultProcessor` SHALL write the out-of-scope and in-scope discard counts as two separate columns of `summary.csv`.

An out-of-scope count is expected and informative: the weavers instrument by a library deny-list rather than by the app key, so library events legitimately arrive and are legitimately dropped. An in-scope count is a defect signal — the class is under the effective key and the denominator does not hold it, or holds it under a signature that does not match. Summing them would erase exactly the distinction the counters exist to draw.

#### Scenario: Library events dropped, nothing else
- **WHEN** a task produced 4000 coverage events, 1200 of them from bundled libraries, and every in-scope event matched
- **THEN** `unmatched_out_of_scope` MUST be `1200`
- **AND** `unmatched_in_scope` MUST be `0`

#### Scenario: A signature mismatch inside the scope
- **WHEN** a task's coverage events include 37 in-scope signatures absent from the denominator
- **THEN** `unmatched_in_scope` MUST be `37`
- **AND** the value MUST be readable without inspecting any log

#### Scenario: Diagnostics were not produced
- **WHEN** a task ran under a configuration that produced no parser diagnostics
- **THEN** both columns MUST be empty
- **AND** they MUST NOT be written as `0`, because that would assert a measurement that was not made

### Requirement: The Report States Whether It Measured

`ResultProcessor` SHALL write a `measured` boolean column in `summary.csv`, `true` when the row's coverage cells were computed from a real denominator and `false` when those cells are empty. The empty cell itself remains the contract for the coverage values (the writer emits `""`); `measured` is what carries that fact through aggregation.

An empty cell is not a signal under `pandas`, and every in-repo consumer of `summary.csv` reads it with `pd.read_csv` and no `dtype`. The cell becomes `NaN`, and `NaN` is precisely what the aggregators of this project skip: `.mean()` and `.groupby()` drop it, so the row count is unchanged while the denominator of every aggregate silently changes, with nothing recording the change. Without `measured`, INV-PLT-35 would relocate the silence one layer down instead of removing it — the same class of defect this change exists to end.

Two measured consequences make this concrete:

- `scripts/aperv_objective.py:76-78` and `scripts/analyze_calibration.py:186-192` both feed `scipy.stats.trim_mean`, which does **not** skip `NaN`. An APK whose rows are all empty yields a `NaN` APK mean, and the APE-RV calibration objective returns `nan` — a verdict-class consequence.
- `scripts/verify_phase.py` is a gate over **errors only** (`:115`); its `cov_method` means at `:385-386` feed a check that is explicitly `passed=True  # Informational`. A row that ran without a denominator would vanish from those means instead of pulling them toward zero — a report whose meaning changes with nothing announcing it, though no verdict flips there.

The column is live, not merely published: task 8.3 makes those consumers filter by it and adds it to aperv-tool's loader. A boolean column survives a `.mean()` — its mean is the fraction of rows that were actually measured. An empty cell does not.

#### Scenario: A measured row
- **WHEN** an APK with a 705-class denominator produces a row whose six coverage cells are filled, including `cov_class = 0.00` for a run that covered nothing
- **THEN** `measured` MUST be `true`
- **AND** the row MUST participate in every downstream `.mean()` exactly as it does today

#### Scenario: An unmeasured row
- **WHEN** an APK executed with no denominator, so its six coverage cells and both denominator cells are empty
- **THEN** `measured` MUST be `false`
- **AND** `measured` MUST NOT itself be empty
- **AND** a consumer computing `df["measured"].mean()` MUST obtain the fraction of rows that carried a denominator, without reading any other file

#### Scenario: A gate can tell a shrunken denominator from a stable one
- **WHEN** a campaign of 40 rows produces 12 rows with `measured = false`
- **THEN** `df["cov_method"].mean()` MUST be understood as the mean of the 28 measured rows
- **AND** `df["measured"].sum() == 28` MUST make that denominator readable from the same file, so `scripts/verify_phase.py` and `scripts/aperv_objective.py` can refuse or qualify the comparison instead of averaging silently over a changed base

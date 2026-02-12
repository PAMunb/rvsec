## ADDED Requirements

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
- **AND** the platform MUST log a warning: "Config changed since last run (stored: abcd1234, current: efgh5678) — resuming anyway"
- **AND** `_skip_completed_tasks()` MUST still skip previously completed tasks based on identity matching, because task identity is independent of the config checksum — a completed `(cryptoapp, monkey, default, 1, 300)` task is the same regardless of whether the researcher also changed the timeout list or added a new tool
- **AND** execution MUST proceed with the remaining tasks under the new configuration

#### Scenario: Resume With No Completed Tasks

- **WHEN** `Platform.run()` is called and `TaskStorage` loads an existing `tasks.json` but all tasks have a state other than `COMPLETED` (e.g., all `ERROR` or `CREATED`)
- **THEN** `_skip_completed_tasks()` MUST return without modifying the task list, because there are no completed tasks to skip
- **AND** no resume log messages MUST be emitted (this is effectively a fresh run reusing the same directory)
- **AND** all generated tasks MUST be executed normally

### Requirement: Result Consolidation on Resume (FR10-ext)

When the platform resumes an experiment (either Form 1: Expand Experiment or Form 2: Crash Recovery), the result processing phase MUST produce output files (summary.csv, results.json, coverage.csv, errors.csv, performance.csv) that reflect the **entire experiment state** — all completed tasks from all sessions — not just the tasks executed in the current session. Note: `errors.csv` contains **monitored operations violations** (formal property violations detected by runtime verification monitors), not application crashes or general errors. This is necessary because the output files are the researcher's primary data artifact: they are imported into analysis notebooks, used for statistical comparisons, and included in publications. If a resumed experiment's output files only contain the current session's data, the researcher loses visibility into previously completed work and must manually reconstruct the full picture from raw data files.

The mechanism for achieving this is straightforward: `_process_results()` MUST use `TaskStorage.get_completed_tasks()` as its data source instead of the filtered `Platform.tasks` list. `TaskStorage` is the authoritative source of truth for the experiment state — it contains all tasks from all sessions (loaded from `tasks.json` at startup, updated via `update_task()` during execution). The `ResultProcessorComponent` receives this complete task list and generates output files with all completed tasks included.

Tasks loaded from `tasks.json` (from previous sessions) do not have `task.repository` data — the `LogcatRepository` that `CoverageTracker` populates in-memory during task execution is runtime-only and never serialized. Without special handling, `errors.csv` would be empty (no monitored operations violation records) and `results.json` would lack MOP violation details for previously completed tasks. This is unacceptable because the output files are the researcher's primary data artifact for analysis and publication. Note: `errors.csv` contains **monitored operations violations** (formal property violations detected by runtime verification monitors via `RVSEC` logcat entries), not application crashes or general errors.

To solve this, `ResultProcessorComponent` MUST reconstruct MOP violation data by re-reading the persisted logcat file. Every task that runs through `CoverageComponent` produces a `.logcat` file stored in the results directory (at the path recorded in `task.result.logcat_file`). This file contains all `RVSEC` (monitored operations violations) and `RVSEC-COV` (method coverage) entries captured during execution. When `task.repository` is `None` (loaded from `tasks.json`), `ResultProcessorComponent` MUST call `parse_logcat_file(logcat_file)` from rv-coverage to parse the logcat and obtain a `LogcatRepository` with the violation data. The `LogcatRepository.register_rv_error()` method stores violations unconditionally (no static analysis data needed), so MOP violation reconstruction works regardless of whether static analysis files are present.

For coverage data, the situation differs: `LogcatRepository.register_method_call()` only registers calls to methods that exist in `self.classes` (populated from static analysis data). Without static analysis data, method calls are silently ignored, meaning progressive per-method coverage data (`coverage.csv` rows with individual method signatures and timestamps) cannot be reconstructed from logcat alone. For loaded tasks, `coverage.csv` MUST include a single summary row using `task.result.coverage_metrics` (which IS serialized in `tasks.json` and contains the final aggregate percentages). This is acceptable because `summary.csv` already contains the same aggregate metrics that researchers use for statistical analysis, and the per-method progressive data is primarily useful for temporal visualization, not for quantitative comparisons.

The key distinction: `summary.csv` and `results.json` summary data use `task.result.coverage_metrics` (serialized, complete for all tasks). `errors.csv` (MOP violations) and `results.json` violation details use logcat re-reading (reconstructed from `RVSEC` entries, complete for all tasks with logcat files). `coverage.csv` per-method progressive data is only available for current-session tasks (runtime-only `repository` required).

The execution summary (returned by `Platform.run()` and displayed by the CLI) MUST also reflect the complete experiment scope. It MUST include the count of skipped tasks (from previous runs) alongside the count of executed tasks, so the researcher sees the full picture: "Total tasks: 5 (2 executed, 3 skipped from previous runs)".

#### Scenario: Result Processing After Resume Includes All Sessions

- **WHEN** `Platform.run()` resumes an experiment by skipping N previously completed tasks and executing M new tasks
- **THEN** `_process_results()` MUST pass all N+M completed tasks to `ResultProcessorComponent`
- **AND** `summary.csv` MUST contain N+M rows (one per completed task, from all sessions)
- **AND** `results.json` MUST contain summary data for all N+M completed tasks
- **AND** `results.json` MUST contain MOP violation details (violation messages, spec names, class/method) for all N+M tasks that have logcat files, reconstructed via `parse_logcat_file()` when `task.repository` is `None`
- **AND** `errors.csv` MUST contain MOP violation rows for all N+M tasks that have logcat files with `RVSEC` entries (monitored operations violations), reconstructed via `parse_logcat_file()` when `task.repository` is `None`
- **AND** `coverage.csv` MUST contain per-method entries for the M tasks from the current session (which have `task.repository`), and a single summary row for each of the N tasks from previous sessions (using `task.result.coverage_metrics`)
- **AND** `performance.csv` MUST contain entries for at least the M tasks from the current session

#### Scenario: Logcat Re-Reading for MOP Violation Reconstruction

- **WHEN** `ResultProcessorComponent` processes a completed task whose `task.repository` is `None` (loaded from `tasks.json`)
- **AND** `task.result.logcat_file` points to an existing file on disk
- **THEN** `ResultProcessorComponent` MUST call `parse_logcat_file(logcat_file)` from rv-coverage to reconstruct a `LogcatRepository`
- **AND** MUST use `repository.get_errors()` to obtain the list of monitored operations violations (formal property violations from `RVSEC` logcat entries — not application crashes)
- **AND** MUST write each violation to `errors.csv` with the same fields (apk, rep, timeout, tool, time, spec, class, method, message, unique_msg) as for tasks with in-memory repositories
- **AND** MUST include violation details (total count, messages, details) in `results.json` for the task
- **AND** the reconstructed repository MUST NOT be used for `coverage.csv` per-method data (because `register_method_call()` requires static analysis class data which is unavailable)

#### Scenario: Logcat File Missing on Resume

- **WHEN** `ResultProcessorComponent` processes a completed task whose `task.repository` is `None`
- **AND** `task.result.logcat_file` does not exist on disk, or is `None`
- **THEN** `ResultProcessorComponent` MUST log a warning: "No logcat file available for task {task.id} — MOP violation details cannot be reconstructed"
- **AND** `errors.csv` MUST NOT have entries for that task (no data source to reconstruct from)
- **AND** `results.json` MUST still include summary data from `task.result.coverage_metrics` but with empty violation details
- **AND** `coverage.csv` MUST include a summary row from `task.result.coverage_metrics` (if available)

#### Scenario: Execution Summary Includes Skipped Count

- **WHEN** `_skip_completed_tasks()` skips N tasks from a previous run
- **AND** `_execute_tasks()` completes M tasks in the current session
- **THEN** `_generate_summary()` MUST return a dict with `skipped_tasks: N` in addition to the existing `total_tasks`, `successful_tasks`, and `failed_tasks` fields
- **AND** the `total_tasks` field MUST represent the number of tasks executed in this session (M), to maintain backward compatibility with callers that use this field for success rate calculation
- **AND** the platform MUST log "Execution summary: X/M tasks successful (N skipped from previous runs)"
- **AND** the CLI (`__main__.py`) MUST display the skipped count when N > 0

#### Scenario: First Run (No Resume) Has Zero Skipped

- **WHEN** `Platform.run()` executes for the first time (no existing `tasks.json`, or `tasks.json` has no completed tasks)
- **THEN** `_skipped_count` MUST be 0
- **AND** the summary MUST have `skipped_tasks: 0`
- **AND** `_process_results()` MUST behave identically to the non-resume case (passing `self.tasks` or `TaskStorage.get_completed_tasks()` yields the same result since there are no previous-session tasks)
- **AND** no "skipped from previous runs" messages MUST appear in CLI output

## MODIFIED Requirements

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
- **AND** if checksums do not match, a warning MUST be logged with the first 8 characters of both checksums

#### Scenario: Skip Completed Tasks During Resume

- **WHEN** `_skip_completed_tasks()` is called and `TaskStorage.get_completed_tasks()` returns N completed tasks (N > 0)
- **THEN** the platform MUST call `check_continuation_compatibility()` with the current config dict to validate configuration consistency, logging a warning if checksums differ
- **AND** the platform MUST compute task identity as the tuple `(apk_name, tool_name, variant, repetition, timeout)` for each completed task
- **AND** MUST remove from `self.tasks` any task whose identity matches a completed task's identity
- **AND** MUST log "Resume: skipped N already-completed tasks (M remaining)" where M is the count of tasks remaining after filtering
- **AND** tasks with `ERROR` state MUST NOT be skipped — they are re-executed on resume, giving the researcher a chance to recover from transient failures

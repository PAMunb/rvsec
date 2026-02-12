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

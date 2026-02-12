# Design: Resume + Docker

## Context

This design supports the `resume-docker` change, addressing FR10 (Persistent Task Storage), FR16 (CLI Interface), FR16-ext (Resume via CLI), FR10-ext (Resume Integration), and NFR08 (Reproducibility).

RV-Android's resume architecture has all building blocks implemented but none wired together. `TaskStorage` provides atomic persistence with write-to-temp-then-rename semantics and `fsync`. `ExperimentMetadata` stores a SHA-256 configuration checksum and experiment identifier. `_skip_completed_tasks()` can filter already-completed tasks by identity matching (APK name, tool name, variant, repetition, timeout). `check_continuation_compatibility()` validates that the current configuration matches the stored one. The gap is purely integration: no CLI flag triggers resume, `ExperimentMetadata` is never initialized by `Platform.run()`, the checksum validation is never called, and every experiment run generates a non-deterministic results directory (`cli_experiment_YYYYMMDD_HHMMSS_uuid` at `__main__.py:860`), making it impossible for a second run to find the first run's `tasks.json`.

Docker containerization requires functional resume because containers are routinely killed and restarted — by resource limits (`docker kill`), by orchestrators, by manual intervention, or by watchdog processes. The rvsec-02/ICST study proved this pattern with 7 parallel containers, each with its own `execution_memory.json` file for crash recovery and `RV_SKIP_*=true` environment variables for pre-processing bypass on restart.

**Constraints:**
- Resume must not change `TaskStorage` internals (already correct, just unused)
- Docker entry point must translate env vars to the existing `rv-experiment` CLI
- Pre-processing artifacts must be reused on resume (not re-generated)
- Environment variables must align with `rv_android_core.constants` naming conventions
- **No backward compatibility**: All dead code is removed outright — no adapters, wrappers, shims, or compatibility layers. Old files are backed up to `backup/` before modification. This is a system evolution, not a migration.

**Current state of affected files:**
- `modules/rv-experiment/src/rv_experiment/__main__.py` (1038 lines) — CLI entry point, no `--resume-dir` flag, `--name` generates unique ID
- `modules/rv-platform/src/rv_platform/platform.py` (461 lines) — `_skip_completed_tasks()` works if same dir, `ExperimentMetadata` never initialized
- `modules/rv-experiment/src/rv_experiment/config.py` (941 lines) — Dead code (`get_artifact_validation_config()` crashes on undefined fields, `load_from_status()` never called)
- `modules/rv-platform/src/rv_platform/storage/task_storage.py` (741 lines) — `ExperimentMetadata`, `check_continuation_compatibility()` exist but unused

## Resume Usage Forms

The resume mechanism supports two distinct usage patterns. Both patterns rely on the same underlying machinery — `TaskStorage` with `tasks.json` persistence and `_skip_completed_tasks()` with identity matching — but they differ in user intent and when they occur.

### Form 1: Expand Experiment

The researcher runs an experiment with a given configuration, analyzes the results, and decides more data is needed. Instead of starting from scratch, they re-run the same command with expanded parameters (e.g., more repetitions, additional tools, or extra timeout values). The system detects the existing `tasks.json` in the results directory, skips all tasks that were already completed in the previous run, and executes only the newly generated tasks.

**Example**: A researcher runs 2 repetitions of monkey testing, then decides 5 repetitions are needed for statistical significance:

```
# First run: 2 repetitions
rv-platform run --tools monkey --apks-dir ./apks --repetitions 2 --timeout 60 --results-dir ./results/exp01

# Second run: 5 repetitions (tasks for rep 1 and 2 are skipped)
rv-platform run --tools monkey --apks-dir ./apks --repetitions 5 --timeout 60 --results-dir ./results/exp01
```

The second run generates 5 tasks, finds 2 already completed in `tasks.json`, skips them, and executes only the 3 remaining tasks (reps 3, 4, 5). The config checksum will differ (because `repetitions` changed from 2 to 5), so a warning is logged, but execution proceeds normally — task identity matching is independent of the checksum.

This form is also how researchers add new tools to an existing experiment:

```
# First run: monkey only
rv-experiment run --tools monkey --name exp01 --timeout 300

# Second run: add droidbot (monkey tasks skipped)
rv-experiment run --tools monkey,droidbot --name exp01 --timeout 300
```

### Form 2: Crash Recovery

The researcher starts an experiment that is interrupted mid-execution — by Ctrl+C, container restart, system crash, OOM kill, or any other failure. They re-run the exact same command, and the system picks up where it left off by skipping the tasks that completed before the interruption.

**Example**: A 10-repetition experiment is interrupted after 3 tasks complete:

```
# First run: interrupted after 3/10 tasks complete
rv-platform run --tools monkey --apks-dir ./apks --repetitions 10 --timeout 300 --results-dir ./results/exp01
# ... Ctrl+C after task 3 ...

# Second run: resumes from task 4 (same config, checksum matches)
rv-platform run --tools monkey --apks-dir ./apks --repetitions 10 --timeout 300 --results-dir ./results/exp01
```

The second run generates the same 10 tasks, finds 3 already completed in `tasks.json`, skips them, and executes the remaining 7. The config checksum matches because the configuration is identical, so no warning is logged.

This is the primary Docker use case: containers are killed and restarted routinely (by orchestrators, resource limits, or watchdog processes), and each restart must continue from where the previous instance stopped. The rvsec-02/ICST study validated this pattern with 7 parallel containers over thousands of restarts.

### Key Difference Between Forms

| Aspect | Form 1 (Expand) | Form 2 (Crash Recovery) |
|--------|-----------------|------------------------|
| Config changes between runs | Yes (more reps, new tools, different timeouts) | No (identical command) |
| Config checksum | Mismatch (warning logged) | Match (no warning) |
| New tasks generated | Yes (the expansion adds tasks) | No (same tasks regenerated) |
| User intent | Add more data to existing experiment | Continue interrupted experiment |
| Task identity overlap | Partial (old tasks skip, new tasks execute) | Complete (all old tasks attempt to skip) |
| Docker relevance | Less common (config changes require image rebuild or env var update) | Primary use case (container restart with same env vars) |

Both forms produce the same result: a consolidated experiment where CSV/JSON output files contain data from all completed tasks, regardless of which run completed them.

## Architecture

### Resume Flow

```
User CLI (--resume-dir / --name)
     |
     v
rv-experiment CLI (__main__.py)
     |  detect resume: tasks.json exists in results/<name>/?
     |  auto-set skip flags (INV-EXP-13)
     v
ExperimentConfig (resume_mode=True, skip_*=True)
     |
     v
ExperimentController.run()
     |
     +---> Phase 1: PreProcessor (ALL SKIPPED on resume — monitors, instrumentation, static analysis)
     |
     +---> Phase 2: ExecutionController
     |       |
     |       +---> Platform.run()
     |               |
     |               +---> _generate_tasks() — generates full task list from config
     |               +---> ExperimentMetadata.create_from_config() → set_experiment_metadata()
     |               +---> _skip_completed_tasks()
     |               |       |
     |               |       +---> check_continuation_compatibility() → warn if mismatch
     |               |       +---> filter tasks by identity match (apk, tool, variant, rep, timeout)
     |               |       +---> log "Resume: skipped N already-completed tasks (M remaining)"
     |               |
     |               +---> _execute_tasks() (remaining tasks only)
     |
     +---> Phase 3: PostProcessor
```

### Docker Flow

```
Docker Container (docker run -e RV_EXPERIMENT_NAME=batch_01 -v ./results:/opt/.../results ...)
     |
     v
docker-entrypoint.sh
     |  Translates env vars to CLI args:
     |    RV_TOOLS → --tools
     |    RV_TIMEOUTS → --timeout
     |    RV_EXPERIMENT_NAME → --name
     |    RV_RESUME_DIR → --resume-dir
     |    ... (see Environment Variable Reference below)
     |  Passes through system env vars: RVSEC_HOME, ANDROID_HOME, TOOLS_DIR
     v
poetry run rv-experiment run --tools monkey --name batch_01 --no-window ...
     |
     v
CLI detects results/batch_01/tasks.json exists → auto-resume
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `__main__.py:_create_experiment_config_from_cli()` | Detect resume via `--resume-dir` or `--name` with existing `tasks.json`, auto-set skip flags | CLI args + filesystem check | `ExperimentConfig` with `resume_mode=True` |
| `platform.py:Platform.run()` | Initialize `ExperimentMetadata` after task generation, delegate to `_skip_completed_tasks()` | `PlatformConfig` | Execution summary dict |
| `platform.py:_skip_completed_tasks()` | Call `check_continuation_compatibility()` for checksum validation, then filter tasks by identity | Completed tasks from `TaskStorage` | Filtered task list (remaining tasks) |
| `task_storage.py:ExperimentMetadata` | Store experiment ID and config checksum (SHA-256) | Config dict | Persisted metadata in `tasks.json` |
| `docker-entrypoint.sh` | Translate Docker env vars to `rv-experiment` CLI args, support interactive mode | Environment variables | CLI command string |

## Mapping: Spec → Implementation

| Requirement | Implementation | Test |
|-------------|---------------|------|
| FR10-ext: Resume Integration | `platform.py:run()` — metadata init after `_generate_tasks()`, checksum validation in `_skip_completed_tasks()` | `test_platform_resume_metadata_init`, `test_platform_resume_checksum_match`, `test_platform_resume_checksum_mismatch` |
| FR10: Skip Completed Tasks | `platform.py:_skip_completed_tasks()` — identity match on (apk, tool, variant, rep, timeout) | `test_skip_completed_tasks_filters`, `test_skip_completed_error_tasks_rerun` |
| FR16-ext: Resume via CLI | `__main__.py` — `--resume-dir` Click option + `--name` resume detection | `test_cli_resume_dir`, `test_cli_resume_name_existing`, `test_cli_resume_name_new` |
| FR16: CLI DSL (MODIFIED) | `__main__.py` — 2 resume scenarios added to existing CLI | existing CLI tests + `test_cli_resume_overrides` |
| INV-PLT-12: Config Checksum | `task_storage.py:check_continuation_compatibility()` — already implemented, now called by `_skip_completed_tasks()` | `test_checksum_match`, `test_checksum_mismatch_warns` |
| INV-EXP-13: Resume Auto-Skip | `__main__.py` — all skip flags auto-set to `True` on resume detection | `test_resume_auto_skip_flags` |
| Dead Code REMOVED | `config.py` — delete `get_artifact_validation_config()`, `load_from_status()`, and `experiment_dir` field entirely (backup original to `backup/`). No adapters, no wrappers, no compatibility layers. | verify no import errors, no callers broken, grep confirms zero references |
| FR10-ext: Result Consolidation on Resume | `platform.py:_process_results()` — use `TaskStorage.get_completed_tasks()` instead of filtered `self.tasks`; `_generate_summary()` includes `skipped_tasks` count; `__main__.py` displays skipped tasks in CLI summary | `test_process_results_uses_all_completed_tasks`, `test_generate_summary_includes_skipped_count`, `test_generate_summary_total_includes_skipped` |
| FR10-ext: Logcat Re-Reading for MOP Violations | `result_processor.py:_reconstruct_repository_from_logcat()` — re-read logcat file via `parse_logcat_file()` when `task.repository` is `None`; update `_write_task_error_data()`, `_extract_task_data()` to use reconstructed repository | `test_result_processor_reconstructs_violations_from_logcat`, `test_result_processor_handles_missing_logcat`, `test_result_processor_json_includes_violation_details` |
| INV-EXP-14: Results Directory Structure | `experiment_controller.py` — use `config.results_dir` directly, remove nesting logic | `test_cli_name_detects_existing_results` (existing, validates flat path), `test_experiment_controller_flat_directory` |

## Decisions

### D1: Resume Detection via `tasks.json` Existence

**Decision**: Detect resume by checking if `tasks.json` exists in the target results directory.

**Alternatives considered**:
- *Explicit status file with state machine*: A dedicated `experiment_status.json` with states like `RUNNING`, `INTERRUPTED`, `COMPLETED`. This would provide richer state information but adds complexity. The rvsec-02 pattern used a similar simple file check (`execution_memory.json` existence) and proved reliable across thousands of container restarts.
- *CLI flag `--resume true/false`*: Requires the user to remember to set it on re-run, which is error-prone and breaks the "run the same command twice" ergonomic pattern.

**Rationale**: The `tasks.json` file is already written atomically by `TaskStorage` after each task state change. Its presence is a reliable indicator that a previous run used this directory and reached at least the task generation phase. If the file is corrupted (unlikely due to atomic writes), `TaskStorage.load()` will fail gracefully and the run proceeds as a fresh experiment. This matches the rvsec-02 approach (`execution_memory.json` existence check) that was validated in production.

### D2: Auto-Skip Pre-Processing on Resume

**Decision**: When resume is detected, auto-set all three skip flags (`generate_monitors`, `instrument_apks`, `run_static_analysis`) to `True` regardless of CLI values.

**Alternatives considered**:
- *Respect CLI skip flags on resume*: Let the user choose which pre-processing to re-run. This adds flexibility but creates a footgun — re-running instrumentation would overwrite the instrumented APKs that the previous run's results are based on, potentially invalidating the skipped tasks.

**Rationale**: Pre-processing artifacts from the original run already exist in `out/monitors/`, `out/instrumented_apks/`, and alongside the instrumented APKs (`.wtg`, `.gesda`, `.reach` files). Re-running any pre-processing step would overwrite these artifacts and waste time (instrumentation alone takes minutes per APK). The ICST study used `RV_SKIP_*=true` for all resumed containers. INV-EXP-13 formalizes this behavior.

### D3: Warn But Don't Block on Config Mismatch

**Decision**: Log a warning on configuration checksum mismatch, continue execution.

**Alternatives considered**:
- *Block execution and require `--force`*: Safe but too strict for research workflows. A researcher might interrupt an experiment, add a new tool or change a timeout, and resume. Blocking would force them to delete `tasks.json` and restart from scratch.
- *Ignore silently*: Hides potential issues. The researcher should know their config changed.

**Rationale**: Task identity matching (`(apk, tool, variant, rep, timeout)`) ensures only genuinely completed tasks are skipped. A changed config may add new tasks (new tool or timeout) while benefiting from skipping already-completed ones. The warning (logged with first 8 chars of both checksums) provides visibility without obstruction. In Docker environments where the same config is always used, the checksums will always match.

### D4: Docker Entry Point Pattern (env vars → CLI)

**Decision**: Bash script (`docker-entrypoint.sh`) translating Docker environment variables to `rv-experiment` CLI arguments.

**Alternatives considered**:
- *Python entry point*: Like rvsec-02's `main.py`. More powerful (can read config files, validate env vars) but more complex and adds a Python dependency layer before the experiment even starts.
- *Direct CLI in Dockerfile CMD*: No env var support, requires rebuilding the image to change parameters.

**Rationale**: Bash is the standard Docker entry point approach. The script is transparent (echoes the generated command), supports both execution mode (default) and interactive mode (`docker run ... bash`), and follows the same pattern used by most Docker images. Environment variables are the standard Docker mechanism for runtime configuration.

### D5: Dev Image Based on Tools Image

**Decision**: Dev Dockerfile builds on `phtcosta/rvandroid_tools:0.8.0` with `COPY` instead of `git clone`.

**Alternatives considered**:
- *Build on production image*: Would include stale git-cloned source alongside the COPY'd local source, wasting space and causing confusion.
- *Separate base image with only system dependencies*: Unnecessary duplication of the tools image build steps.

**Rationale**: The tools image already has all system dependencies (Java, Android SDK, Python, DroidBot, etc.). Building on it and COPY'ing local source provides the same environment as production with fresh local code. Volume mounting (`-v $(pwd)/modules:/opt/.../modules`) enables hot-reload during development without rebuilding the image.

### D6: ExperimentMetadata Initialization in Platform.run()

**Decision**: Create and store `ExperimentMetadata` after `_generate_tasks()` and before `_skip_completed_tasks()`.

**Alternatives considered**:
- *Initialize before task generation*: The config checksum would be available, but task generation might modify internal state that should be captured.
- *Initialize in `TaskStorage.__init__()`*: Would couple storage initialization with metadata creation, making the storage less reusable.

**Rationale**: Natural location in the `Platform.run()` flow — tasks are generated (full config available for checksumming), metadata must exist before checksum validation in `_skip_completed_tasks()`. The metadata is stored via `TaskStorage.set_experiment_metadata()` which is already defined and working, just never called.

### D7: Environment Variable Naming Convention

**Decision**: Docker entry point env vars follow the naming convention established in `rv_android_core.constants` (prefix `RV_` for experiment params, `RVAGENT_` for rv-agent params, no prefix for system paths like `RVSEC_HOME`, `ANDROID_HOME`, `TOOLS_DIR`).

**Rationale**: The constants module already defines canonical names for all RV-Android environment variables. Using the same names in Docker avoids confusion and ensures the entry point documentation matches the codebase. The only new env vars introduced by this change are `RV_EXPERIMENT_NAME` and `RV_RESUME_DIR`, which follow the `RV_` prefix pattern.

### D8: TaskStorage as Source of Truth for Result Processing on Resume

**Decision**: When processing results after a resume, use `TaskStorage.get_completed_tasks()` as the data source for `ResultProcessorComponent` instead of `Platform.tasks` (the filtered execution queue).

**Alternatives considered**:
- *Maintain a separate `all_tasks` list alongside `self.tasks`*: Keep `self.tasks` for execution queue and `self.all_tasks` for result processing. This duplicates state and creates a synchronization risk — if `self.all_tasks` falls out of sync with `TaskStorage`, results would be inconsistent with the persisted state.
- *Don't filter `self.tasks` in-place; filter a copy for execution*: Instead of `self.tasks = [t for t in self.tasks if ...]`, create `tasks_to_execute = [t for t in self.tasks if ...]` and iterate over that. This preserves the original list but means `self.tasks` would contain tasks that were never executed in this session — their `repository` data would be None (since it is only populated during task execution), and `ResultProcessorComponent` would need to handle this gracefully. The same fallback path exists with `TaskStorage`-loaded tasks.
- *Re-load tasks from TaskStorage at result processing time*: This is the chosen approach. `TaskStorage` is the authoritative source of truth — it contains all tasks from all sessions, with their final state. It is already populated by `update_task()` during execution and `load()` at startup. Using it directly avoids any state duplication.

**Rationale**: `TaskStorage` already maintains the complete experiment state. Using it as the result processing data source eliminates the dual-purpose problem with `self.tasks` and ensures CSV/JSON output files always reflect the full experiment, regardless of how many sessions contributed to it. However, tasks loaded from `tasks.json` lack `task.repository` (runtime-only, not serialized). For summary-level data (`summary.csv`), the existing fallback using `task.result.coverage_metrics` works correctly. For MOP violation data (`errors.csv` and `results.json` violation details), `ResultProcessorComponent` MUST reconstruct the data by re-reading the persisted logcat file via `parse_logcat_file()` — see D9. For coverage per-method progressive data (`coverage.csv`), the fallback is a single summary row from `task.result.coverage_metrics`, because method call reconstruction requires static analysis class data which is unavailable for loaded tasks.

### D9: Logcat Re-Reading for MOP Violation Reconstruction

**Decision**: When `task.repository` is `None` (loaded from `tasks.json`), `ResultProcessorComponent` re-reads the persisted logcat file via `parse_logcat_file()` from rv-coverage to reconstruct a `LogcatRepository` with MOP violation data.

**Alternatives considered**:
- *Serialize the full repository to tasks.json*: Would make all data available on resume, but `LogcatRepository` contains large data structures (all class/method coverage data, error objects with timestamps) that would significantly increase `tasks.json` size. The file is already written atomically on every task state change, so bloating it impacts write performance. Also requires implementing full serialization/deserialization for `LogcatRepository`, `ClassCoverageData`, `MethodCoverageData`, and `RvErrorLog` objects.
- *Accept the data loss (original approach)*: The initial design said "this trade-off is acceptable" for missing `errors.csv` data. This was wrong — `errors.csv` contains monitored operations violations (formal property violations detected by runtime verification monitors), which are a primary experiment output. Missing violations in a resumed experiment means the researcher has an incomplete picture of the application's compliance with specifications.
- *Load static analysis data from disk for full reconstruction*: Would enable both error AND per-method coverage reconstruction. The `.reach`, `.gesda`, `.wtg` files may still exist from the original run. However, this adds complexity (file discovery, parsing, error handling) and couples `ResultProcessorComponent` to static analysis file formats. Deferred as a follow-up improvement.

**Rationale**: Logcat files are already persisted in the results directory (one per task execution). The `parse_logcat_file()` function already exists in rv-coverage and handles all parsing. `LogcatRepository.register_rv_error()` stores MOP violations unconditionally (no static analysis data needed), so violation reconstruction from `RVSEC` logcat entries works regardless of whether static analysis files are present. The approach is minimal (one new method in `ResultProcessorComponent`), uses existing infrastructure, and solves the critical gap (empty `errors.csv` on resume). The limitation — per-method coverage cannot be reconstructed without static analysis data — is acceptable because `summary.csv` already contains the aggregate coverage metrics.

### D10: Docker Network for Sibling Containers

**Decision**: ARES and QTesting Docker sibling containers use `--network container:$(hostname)` to share the parent container's network namespace, detected via the presence of `/.dockerenv`.

**Alternatives considered**:
- *`--network host`*: Simpler but shares the entire host network, which is unnecessary and less isolated. Also does not work on macOS Docker Desktop.
- *Docker user-defined bridge network*: Requires creating a network in advance and configuring service discovery. Adds complexity for no benefit — the sibling container only needs to reach the emulator inside the parent, which is already at `localhost:5554` in the parent's network namespace.
- *Pass emulator IP explicitly via environment variable*: The rvandroid container would need to discover its own IP and pass it. This is fragile because container IPs can change, and ARES/QTesting are hardcoded to connect to `localhost` or `emulator-5554`.

**Rationale**: The `--network container:CONTAINER_ID` flag makes the sibling container share the exact network namespace of the parent container. From the sibling's perspective, `localhost` is the same as the parent's `localhost` — the emulator at port 5554 is directly reachable without any configuration changes. The detection mechanism (`os.path.exists('/.dockerenv')`) is the standard way to check if code is running inside a Docker container. When running outside Docker (standalone mode), no network flag is added, and ARES/QTesting connect to the emulator via the default Docker bridge or `adb connect`. `socket.gethostname()` returns the container ID when running inside Docker, which is the value needed for `--network container:`.

### Docker Sibling Container Architecture

```
┌─── Docker Host ──────────────────────────────────────────────────┐
│                                                                   │
│  docker.sock (/var/run/docker.sock)                              │
│       │                                                           │
│  ┌────┼── rvandroid container ──────────────────────────────┐    │
│  │    │                                                      │    │
│  │    │  Emulator (localhost:5554)                           │    │
│  │    │  rv-experiment → AresTool._build_ares_command()      │    │
│  │    │    → detects /.dockerenv → adds --network flag       │    │
│  │    │    → docker run --network container:$(hostname) ...  │    │
│  │    │                                                      │    │
│  │    │  docker.sock mounted from host ──────────┐          │    │
│  └────┼──────────────────────────────────────────│──────────┘    │
│       │                                          │                │
│       │                                          ▼                │
│  ┌────┴── ares/qtesting container (sibling) ─────────────────┐   │
│  │  --network container:<rvandroid-container-id>             │   │
│  │  Shares rvandroid's network namespace                     │   │
│  │  Sees emulator at localhost:5554                          │   │
│  │  No network configuration needed in ARES/QTesting code    │   │
│  └───────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

**Key points:**
- The `docker.sock` mount (`/var/run/docker.sock:/var/run/docker.sock`) in `docker-compose.yml` allows the rvandroid container to spawn sibling containers via the host's Docker daemon
- `--network container:$(hostname)` makes the sibling share the parent's network stack — `localhost` in the sibling IS `localhost` in the parent
- The Docker CLI binary must be available inside the rvandroid container (installed in the tools Docker image layer)
- When running outside Docker, `/.dockerenv` does not exist, so no `--network` flag is added — ARES/QTesting use their default network behavior (host Docker bridge)
- ARES and QTesting are **NOT** declared as services in `docker-compose.yml` — they are spawned on-demand at runtime by each rvandroid container via `docker run`. Only Humanoid is a shared service in the compose file because it is a REST server that all rvandroid containers connect to over the network.
- In parallel execution (e.g., 7 containers in `docker-compose.parallel.yml`), each rvandroid container (rv01..rv07) can independently spawn its own ARES/QTesting sibling. This means up to 7 ARES containers may run simultaneously, each sharing the network namespace of its specific parent. There is no conflict because each sibling is isolated to its parent's emulator via `--network container:<parent-container-id>`.
- The ARES and QTesting Docker images must be **pre-built** on the host before running experiments that use these tools. The `docker/build_all.sh` script builds them as steps 5/6 and 6/6.

## Code Evolution Principle

This change follows the project's strict code evolution policy: **all changes are complete replacements, never backward-compatible adaptations**. When code is identified as dead, abandoned, or superseded by a new approach, it is deleted entirely from the source files. No adapters, wrappers, shims, deprecation annotations, compatibility re-exports, or `# removed` comments are created. The rationale is straightforward — the system is evolving, and carrying forward unused code creates confusion for future readers (both human and LLM) about what is actually live versus what is historical residue.

**Concrete actions in this change:**
- `get_artifact_validation_config()` and `load_from_status()` in `config.py` are **deleted**, not commented out or marked deprecated. They were remnants of an abandoned resume attempt that was never completed, and the new resume architecture (CLI detection + platform task skipping) follows a fundamentally different approach.
- The original `config.py` is backed up to `backup/config.py.bak` before modification, preserving the full context for the thesis record and enabling recovery if needed.
- No `_deprecated_` prefix, no `# TODO: remove in next version`, no adapter class bridging old and new — the methods simply cease to exist in the codebase.
- Any `import` or reference to these methods (none exist, but verified by grep) would be removed in the same commit.

This policy is documented in the project's `CLAUDE.md` under "Development Principles" (Principle 3: No Backward Compatibility) and applies to all changes, not just this one.

## Environment Variable Reference

Complete inventory of environment variables relevant to Docker and standalone execution. Variables are categorized by how they are handled: some are translated to CLI flags by the entry point script, while others are passed through as system environment variables read directly by Python modules.

### CLI-Translated Variables (entry point → rv-experiment CLI flags)

These variables are read by `docker-entrypoint.sh` and translated to `rv-experiment run` command-line arguments. They have no effect outside Docker unless a standalone script performs the same translation.

| Variable | CLI Flag | Default | Description | Source (constants.py) |
|----------|----------|---------|-------------|----------------------|
| `RV_TOOLS` | `--tools` | `monkey` | Tool specification DSL (comma-separated) | `ENV_TOOLS` |
| `RV_TIMEOUTS` | `--timeout` | `300` | Execution timeout in seconds | `ENV_TIMEOUTS` |
| `RV_REPETITIONS` | `--repetitions` | `1` | Number of repetitions per task | `ENV_REPETITIONS` |
| `RV_APKS_DIR` | `--apks-dir` | `./apks` | Directory containing APK files | — (CLI concept) |
| `RV_NO_WINDOW` | `--no-window / --window` | `true` | Headless emulator mode | `ENV_NO_WINDOW` |
| `RV_SPEC_SET` | `--specification-set` | — | Spec set name: `jca`, `generic`, or `custom` | — (new) |
| `RV_JCA_SPEC` | `--specification-set jca/generic` | `true` | Legacy boolean: `true`=jca, `false`=generic. Overridden by `RV_SPEC_SET` if set. | `ENV_JCA_SPEC` |
| `RV_SKIP_MONITORS` | `--skip-monitors` | `false` | Skip monitor generation phase | `ENV_SKIP_MONITORS` |
| `RV_SKIP_INSTRUMENT` | `--skip-instrument` | `false` | Skip APK instrumentation phase | `ENV_SKIP_INSTRUMENT` |
| `RV_SKIP_STATIC_ANALYSIS` | `--skip-static` | `false` | Skip static analysis phase | `ENV_SKIP_STATIC_ANALYSIS` |
| `RV_DEVICE_PORT` | `--device-port` | — | Emulator port (for parallel execution) | — (CLI concept) |
| `RV_APKS_FILTER` | `--apks-filter` | — | Regex filter for APK selection | — (CLI concept) |
| `RV_EXPERIMENT_NAME` | `--name` | — | Deterministic experiment name (enables resume) | — (new) |
| `RV_RESUME_DIR` | `--resume-dir` | — | Explicit resume from existing results dir | — (new) |
| `RV_DEBUG` | `--log-level DEBUG` | `false` | Enable debug logging | `ENV_DEBUG` |

### Pass-Through Variables (read directly by Python modules)

These variables are NOT translated to CLI flags. They are read directly by Python modules via `os.environ.get()` or `os.getenv()`. In Docker, they must be set as container environment variables (`docker run -e VAR=value` or in `docker-compose.yml`).

| Variable | Read By | Default | Description | Source (constants.py) |
|----------|---------|---------|-------------|----------------------|
| `RVSEC_HOME` | rv-experiment, rv-static-analysis, rv-instrumentation, rv-monitor-generator, rv-android-core | None (required for full pipeline) | Path to RVSEC installation (JavaMOP, RV-Monitor, specs) | `ENV_RVSEC_HOME` |
| `ANDROID_HOME` | rv-static-analysis | None (required) | Android SDK path (set in base Docker image) | `ENV_ANDROID_HOME` |
| `TOOLS_DIR` | rv-tools (APE, DroidMate, FastBot, Humanoid) | `""` | Path to external tools directory | — (in tool code) |
| `RV_HUMANOID_URL` | rv-tools (Humanoid tool) | — | Humanoid inference server URL | `ENV_HUMANOID_URL` |
| `RV_RT_JAR` | rv-static-analysis | auto-detected | Path to rt.jar for static analysis | `ENV_RT_JAR` |
| `RVAGENT_MODE` | rv-agent | from config | Override rv-agent execution mode (pure_algorithm, llm_only, multimode) | — (in agent code) |
| `RVAGENT_LOG_LEVEL` | rv-agent | from config | Override rv-agent log level | — (in agent code) |
| `RVAGENT_VERBOSE_COUNTERS` | rv-agent | `false` | Enable verbose counter output for debugging | — (in agent code) |
| `RV_PYDANTIC` | rv-android-core | `false` | Enable Pydantic validation (dev only) | — (in validation code) |

### Docker-Only Variables (entry point behavior, not in Python code)

| Variable | Default | Description |
|----------|---------|-------------|
| `RV_DELAY` | `0` | Startup delay in seconds before running the experiment. Useful for staggering container startups in parallel execution — the first activities (emulator boot, APK instrumentation) consume significant CPU and I/O. |

### Deprecated / Not Used in Docker

| Variable | Reason |
|----------|--------|
| `RV_MEMORY_FILE` | Replaced by `tasks.json` + `--resume-dir`/`--name` resume mechanism |
| `RV_RVANDROID_URL` | Deprecated — was used by the discontinued `rvandroid` LLM tool |
| `RV_SKIP_EXPERIMENT` | Does not apply to Docker (the container's purpose is to run the experiment) |

## Data Flow

### Resume Flow (--name)

```
CLI --name "my_exp"
  → check results/my_exp/tasks.json exists?
    → YES: set skip_monitors=True, skip_instrument=True, skip_static=True
           use results/my_exp/ as experiment_dir
           set resume_mode=True
           log "Resuming experiment 'my_exp' — auto-skipping pre-processing"
    → NO:  create results/my_exp/ normally (first run)
  → ExperimentConfig(resume_mode=True/False, experiment_dir="results/my_exp")
  → ExperimentController.run()
    → Phase 1: PreProcessor.process() → all skipped (resume) or runs normally (first run)
    → Phase 2: Platform.run()
      → _generate_tasks() → N tasks (full cartesian product)
      → ExperimentMetadata(experiment_id="results/my_exp", checksum=SHA256(config))
      → TaskStorage.set_experiment_metadata(metadata)
      → _skip_completed_tasks()
        → load completed from tasks.json → K completed tasks
        → check_continuation_compatibility(config_dict) → True/False (warn if False)
        → filter: N - K = M remaining tasks
      → _execute_tasks() → run M remaining tasks
    → Phase 3: PostProcessor → diagnostics
```

### Docker Resume Flow

```
docker run -e RV_EXPERIMENT_NAME=batch_01 -v ./results:/opt/.../results ...
  → docker-entrypoint.sh
    → sleep ${RV_DELAY:-0}  # stagger container startups
    → CMD="poetry run rv-experiment run --tools monkey --name batch_01 --no-window ..."
    → echo "=== RV-Android Docker ==="
    → echo "CMD: $CMD"
    → exec $CMD
      → CLI detects results/batch_01/tasks.json exists
      → auto-skip pre-processing (INV-EXP-13)
      → Platform skips K completed tasks, runs M remaining
      → Container completes or is killed → next restart picks up where it left off
```

## Bug: Result Consolidation on Resume

### Discovery

During manual smoke testing of the resume mechanism (Form 1: Expand Experiment), the following sequence was executed:

1. Run rv-platform with `--repetitions 1` → 1 task generated, 1 executed, results written to `results/smoke_test/`
2. Run rv-platform with `--repetitions 2` against the same results directory → 2 tasks generated, 1 skipped (rep 1 already completed), 1 executed (rep 2)

The resume mechanism itself worked correctly: `_skip_completed_tasks()` identified the completed rep-1 task and removed it from the execution queue. The `tasks.json` file was also correct — it contained both tasks (rep 1 from run 1 and rep 2 from run 2) with `COMPLETED` state and correct timestamps.

However, the output files (`summary.csv`, `results.json`, `coverage.csv`, `errors.csv`, `performance.csv`) only contained data from rep 2 (the current session). Data from rep 1 was lost from the consolidated output, even though rep 1's raw data (logcat files, trace files) was still present in the results directory.

### Root Cause Analysis

The root cause is that `Platform.tasks` serves a dual purpose that becomes contradictory during resume:

1. **Execution queue** — After `_skip_completed_tasks()` filters `self.tasks`, it contains only the tasks to be executed in the current session. This is correct for `_execute_tasks()`.
2. **Complete experiment state** — `_process_results()` and `_generate_summary()` also use `self.tasks` as the source of truth for the entire experiment. After resume filtering, this list is incomplete.

The specific code paths affected are:

- **`_process_results()` at `platform.py:466`**: Creates `ResultProcessorComponent(self.tasks, self.config.results_dir)`. After `_skip_completed_tasks()`, `self.tasks` only contains the tasks executed in the current session. `ResultProcessorComponent` writes CSVs with `open(path, 'w')` (overwrite mode), so all output files are rewritten with data from only the current session's tasks.

- **`_generate_summary()` at `platform.py:408`**: Receives `results` from `_execute_tasks()`, which only returns results for tasks executed in the current session. The summary reports `total_tasks: 1` when the experiment actually has 2 tasks (1 skipped + 1 executed).

- **`__main__.py:188`**: CLI prints `results['total_tasks']` from `_generate_summary()`, so the user sees "Total tasks: 1" instead of the correct count.

The `tasks.json` file is unaffected because `TaskStorage` maintains its own internal dictionary (`self.tasks`), which is populated both from loaded data (previous runs) and from `update_task()` calls (current session). This means `tasks.json` correctly contains the full experiment state, but the CSV/JSON output files do not reflect it.

### Why This Was Not Caught in Design

The original design explicitly listed "Changes to result processing or CSV/JSON output format" under Non-Goals. The assumption was that `_skip_completed_tasks()` only needed to filter the execution queue, and that result processing would naturally include all tasks. This assumption was wrong because the same `self.tasks` list is used for both purposes, and resume filtering modifies it in-place.

The design also did not account for `ResultProcessorComponent`'s data source model. `ResultProcessorComponent` was designed to process a list of task objects passed to it during construction — it does not have access to `TaskStorage` or any other source of historical task data. This means it can only process what it receives, and after resume filtering, it receives an incomplete list.

### Fix Approach

The fix involves 5 changes, all in rv-platform:

**1. Track skipped count in `_skip_completed_tasks()`** (`platform.py`): Store the number of skipped tasks in `self._skipped_count` (initialized to 0 in `__init__`). This count is needed by `_generate_summary()` to report the correct total.

**2. Use TaskStorage as source of truth for `_process_results()`** (`platform.py`): Instead of passing `self.tasks` (filtered execution queue), pass `self.task_storage.get_completed_tasks()` to `ResultProcessorComponent`. This retrieves all completed tasks from `TaskStorage`, which includes both previously completed tasks (loaded from `tasks.json`) and newly completed tasks (added via `update_task()` during the current session).

The `ResultProcessorComponent` already handles tasks without `task.repository` data (runtime-only, not serialized). Its `_write_task_coverage_data()` method has a fallback path: `if hasattr(task, 'repository') and task.repository:` for detailed per-method data, and an `else:` branch that uses `task.result.coverage_metrics` (which IS serialized in `tasks.json`). This means tasks loaded from `tasks.json` will use the summary-level coverage metrics, which is sufficient for `summary.csv` and `results.json`. The detailed `coverage.csv` will only contain per-method entries for tasks from the current session (because `repository` data is runtime-only), but this is acceptable — the summary-level data captures the aggregate metrics that matter for research analysis.

**3. Include skipped count in `_generate_summary()`** (`platform.py`): Add `skipped_tasks` to the summary dict. Change log message to include total experiment scope: "Execution summary: X/Y tasks successful (Z skipped from previous runs)".

**4. Wire skipped count through `run()`** (`platform.py`): Pass `self._skipped_count` to `_generate_summary()` so it can calculate the correct totals.

**5. Update CLI summary display** (`__main__.py`): Show skipped tasks when `skipped_tasks > 0`: "Skipped (from previous runs): N". Adjust total display to show both executed and skipped counts.

**6. Re-read logcat files for MOP violation reconstruction** (`result_processor.py`): Add a method `_reconstruct_repository_from_logcat(task)` that checks if `task.result.logcat_file` exists on disk and calls `parse_logcat_file(logcat_file)` from rv-coverage to reconstruct a `LogcatRepository`. Update `_write_task_error_data()`, `_write_task_coverage_data()`, and `_extract_task_data()` to use this method when `task.repository` is `None`. The reconstructed repository provides MOP violation data (from `RVSEC` logcat entries) but NOT per-method coverage data (because `register_method_call()` requires static analysis class data). For coverage, the existing fallback (single summary row from `task.result.coverage_metrics`) is retained.

## Bug: ExperimentController Double-Nesting

### Discovery

During smoke test 8.2.1 (rv-experiment Form 1), the second run (resume with `--name smoke_exp --repetitions 2`) triggered full pre-processing (monitor generation, APK instrumentation, static analysis) instead of auto-skipping. Investigation revealed that resume detection in `__main__.py` checked `results/smoke_exp/tasks.json`, but the actual file was at `results/smoke_exp/smoke_exp/tasks.json` — a double-nested directory.

### Root Cause Analysis

The double nesting originates from two independent path constructions that both include the experiment name:

1. `__main__.py` (line 876): Sets `output_dir = str(Path(f"./{RESULTS_DIR}/{name}"))` → `"results/smoke_exp"`
2. `ExperimentConfig.__init__`: Sets `self.results_dir = output_dir` → `"results/smoke_exp"`
3. `ExperimentController.__init__` (line 62): `results_base_dir = config.results_dir` → `"results/smoke_exp"`
4. `ExperimentController.__init__` (line 67): `experiment_folder = config.name` → `"smoke_exp"`
5. `ExperimentController.__init__` (line 75): `self.results_dir = os.path.join(results_base_dir, experiment_folder)` → `"results/smoke_exp/smoke_exp"`

Step 5 is the bug: `ExperimentController` appends `config.name` to `config.results_dir`, but `config.results_dir` already contains the experiment name (set by `__main__.py` in step 1).

### Fix

Change `ExperimentController.__init__()` to use `config.results_dir` directly:

```python
# config.results_dir already contains the full experiment path
# (e.g., "results/smoke_exp" or "results/cli_experiment_20260212_...")
# set by __main__.py before calling execute_with_config()
self.results_dir = config.results_dir or f"./{rv_cte.RESULTS_DIR}"
os.makedirs(self.results_dir, exist_ok=True)
```

Also remove the dead `experiment_dir` field from `ExperimentConfig` — it was set via `get_experiment_dir(self.results_dir, self.name)` but never read by any code in the codebase. The `get_experiment_dir` import is removed from config.py.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `--resume-dir` path does not exist | Click `type=Path(exists=True)` | Reject before any experiment logic | User corrects path |
| Config checksum mismatch on resume | `check_continuation_compatibility()` | Warning log with first 8 chars of both checksums, continue execution | User aware of config change; task identity matching still works |
| `get_artifact_validation_config()` crash | Dead code referencing `self.artifact_reuse_enabled` (undefined) | Remove the method entirely (this change) | No callers affected |
| Docker entry point invalid env vars | `docker-entrypoint.sh` | CLI validates downstream (Click param types, Pydantic validators) | User fixes env vars, restarts container |
| `tasks.json` corrupted on resume | `TaskStorage.load()` | Graceful failure — start fresh if JSON parsing fails | Experiment runs as first run (no tasks skipped) |
| Startup delay timeout | `RV_DELAY` in entrypoint | `sleep` finishes, experiment proceeds normally | No action needed |
| Logcat file missing on resume | `ResultProcessorComponent._reconstruct_repository_from_logcat()` | Warning log, skip MOP violation reconstruction for that task | `errors.csv` omits that task; `summary.csv` still works from `task.result.coverage_metrics` |

## Testing Strategy

Testing follows a layered approach: unit tests first (covering resume logic, result consolidation, MOP violation reconstruction, and summary counts), then manual smoke tests on a real emulator (covering both resume forms end-to-end). The order matters — unit tests must pass before manual testing, because smoke tests rely on the correctness of the underlying logic.

### Unit Tests (rv-platform)

These tests run without an emulator and verify the resume and result consolidation logic in isolation.

| # | Test | What It Verifies | How |
|---|------|-----------------|-----|
| U1 | `test_skip_completed_tasks_filters_by_identity` | `_skip_completed_tasks()` removes tasks whose (apk, tool, variant, rep, timeout) matches a completed task from TaskStorage | Mock TaskStorage with 2 completed tasks, generate 5 tasks, verify 3 remain after filtering |
| U2 | `test_skip_completed_tasks_stores_skipped_count` | `_skip_completed_tasks()` stores the number of skipped tasks in `self._skipped_count` | Mock TaskStorage with 3 completed tasks, verify `_skipped_count == 3` after filtering |
| U3 | `test_skip_completed_tasks_does_not_skip_error_tasks` | Tasks with `ERROR` state are NOT skipped — they re-execute on resume | Mock TaskStorage with ERROR tasks, verify they remain in the task list |
| U4 | `test_skip_completed_tasks_checksum_mismatch_warns` | Config checksum mismatch logs a warning but does not block | Mock TaskStorage with different checksum, verify warning logged and tasks still filtered |
| U5 | `test_skip_completed_tasks_checksum_match_no_warning` | Config checksum match does not log a warning | Mock TaskStorage with same checksum, verify no warning logged |
| U6 | `test_metadata_created_after_task_generation` | `Platform.run()` creates `ExperimentMetadata` with correct checksum | Mock dependencies, verify `set_experiment_metadata()` called after `_generate_tasks()` |
| U7 | `test_process_results_uses_all_completed_tasks` | `_process_results()` passes all completed tasks from TaskStorage (not just session tasks) to `ResultProcessorComponent` | Mock TaskStorage with 3 completed tasks, verify ResultProcessorComponent receives all 3 |
| U8 | `test_generate_summary_includes_skipped_count` | `_generate_summary()` includes `skipped_tasks` in the summary dict | Call with results and skipped_count > 0, verify `summary['skipped_tasks']` is correct |
| U9 | `test_generate_summary_total_includes_skipped` | Summary `total_tasks` reflects only executed tasks (M), and `skipped_tasks` is reported separately | Call with 1 result and skipped_count=2, verify `total_tasks == 1` and `skipped_tasks == 2` |
| U10 | `test_no_resume_skipped_count_zero` | When no tasks are skipped, `_skipped_count` is 0 and summary has `skipped_tasks: 0` | Run without any completed tasks in TaskStorage |
| U15 | `test_result_processor_reconstructs_violations_from_logcat` | `ResultProcessorComponent` reconstructs MOP violations from logcat file when `task.repository` is `None` | Create a mock task with `repository=None` and a real logcat file containing `RVSEC` entries; verify `errors.csv` has violation rows |
| U16 | `test_result_processor_handles_missing_logcat` | Graceful handling when logcat file does not exist | Create a mock task with `repository=None` and `logcat_file` pointing to non-existent path; verify warning logged and `errors.csv` is empty for that task |
| U17 | `test_result_processor_json_includes_violation_details_from_logcat` | `results.json` contains MOP violation details reconstructed from logcat | Create mock task with `repository=None` and logcat with `RVSEC` entries; verify `results.json` `monitored_operations_errors` has correct `total`, `messages`, and `details` |

### Unit Tests (rv-experiment)

These tests verify the CLI resume detection and auto-skip logic.

| # | Test | What It Verifies | How |
|---|------|-----------------|-----|
| U11 | `test_cli_resume_dir_sets_skip_flags` | `--resume-dir` auto-sets all 3 skip flags to True | Mock CLI invocation with `--resume-dir`, assert `generate_monitors=False`, etc. |
| U12 | `test_cli_name_detects_existing_results` | `--name` with existing `tasks.json` triggers resume mode | Create temp dir with `tasks.json`, mock CLI with `--name`, verify `resume_mode=True` |
| U13 | `test_cli_name_first_run_no_resume` | `--name` without existing results runs as fresh experiment | Mock CLI with `--name` pointing to non-existent dir, verify `resume_mode=False` |
| U14 | `test_cli_resume_dir_overrides_name` | `--resume-dir` takes precedence over `--name` | Mock CLI with both flags, verify results dir is from `--resume-dir` |

### Smoke Tests (Manual, with Emulator)

These tests validate the end-to-end resume behavior on a real emulator with real APK execution. They require a running Android emulator and are executed manually during the verification phase. Each smoke test validates one of the two resume forms.

**Emulator Cleanup (required before each smoke test)**:
After killing a running experiment, the emulator may leave behind lock files and temporary disk images that prevent a clean restart. Always run these cleanup steps before re-running a test:

```bash
# 1. Kill any running emulator
adb -s emulator-5554 emu kill 2>/dev/null

# 2. Remove AVD multiinstance lock
rm -f ~/.android/avd/RVSec.avd/multiinstance.lock

# 3. Remove temporary qcow2 disk images
rm -f /tmp/android-*/emulator-*.qcow2

# 4. Clean previous test results
rm -rf results/smoke_test/
```

Without this cleanup, the emulator may fail to boot or tools may fail with unexpected exit codes (observed with `monkey` exit codes 8, 22, 47 — the `monkey` tool is particularly sensitive to emulator state after a hard kill).

**Tool recommendation**: Use `ape` instead of `monkey` for crash recovery smoke tests. The `monkey` tool fails with non-zero exit codes when the emulator has been killed and restarted, while `ape` handles this scenario correctly.

**Smoke Test 1: Form 1 (Expand Experiment)** — Validates that running rv-platform with expanded parameters (more repetitions) correctly skips already-completed tasks and consolidates results from all sessions into the output files.

Steps:
1. Clean any previous test data: `rm -rf results/smoke_test/`
2. Run rv-platform with 1 repetition: `poetry run rv-platform run --tools monkey --apks-dir ./apks_examples --repetitions 1 --timeout 60 --results-dir ./results/smoke_test --no-window`
3. Verify: `tasks.json` has 1 completed task, `summary.csv` has 1 row, logcat file exists for rep 1
4. Run rv-platform with 2 repetitions (same results dir): `poetry run rv-platform run --tools monkey --apks-dir ./apks_examples --repetitions 2 --timeout 60 --results-dir ./results/smoke_test --no-window`
5. Verify:
   - CLI output shows "Resume: skipped 1 already-completed tasks (1 remaining)"
   - CLI output shows "Skipped (from previous runs): 1"
   - `tasks.json` has 2 completed tasks (both with correct timestamps)
   - `summary.csv` has 2 rows (rep 1 AND rep 2)
   - `results.json` has data for both reps
   - Logcat files exist for both rep 1 and rep 2
6. Clean up: `rm -rf results/smoke_test/`

**Smoke Test 2: Form 2 (Crash Recovery)** — Validates that an interrupted experiment can be resumed with the same command and completes correctly.

Steps:
1. Clean any previous test data: `rm -rf results/smoke_test/`
2. Run rv-platform with 3 repetitions in background: `poetry run rv-platform run --tools monkey --apks-dir ./apks_examples --repetitions 3 --timeout 60 --results-dir ./results/smoke_test --no-window &`
3. Wait ~90 seconds (enough for at least 1 task to complete — each task takes ~110s with emulator boot, so adjust timing as needed)
4. Kill the process: `kill %1` (or equivalent)
5. Verify intermediate state: `tasks.json` has at least 1 completed task, possibly 1 running/created task
6. Re-run the same command: `poetry run rv-platform run --tools monkey --apks-dir ./apks_examples --repetitions 3 --timeout 60 --results-dir ./results/smoke_test --no-window`
7. Verify:
   - CLI output shows "Resume: skipped N already-completed tasks (M remaining)" where N >= 1
   - Config checksum matches (no mismatch warning, since same command)
   - All 3 tasks are completed after the second run finishes
   - `tasks.json` has 3 completed tasks
   - `summary.csv` has 3 rows
   - Logcat files exist for all 3 reps
8. Clean up: `rm -rf results/smoke_test/`

**Smoke Test 3: rv-experiment Form 1 (Expand Experiment)** — Validates resume through rv-experiment CLI with `--name` flag, including pre-processing auto-skip.

Steps:
1. Run rv-experiment with full pipeline: `poetry run rv-experiment run --tools monkey --apks-dir ./apks_examples --timeout 60 --name smoke_exp --no-window --repetitions 1`
2. Verify: experiment completes, pre-processing runs (monitors generated, APKs instrumented), 1 task executed
3. Run rv-experiment again with more repetitions (same name): `poetry run rv-experiment run --tools monkey --apks-dir ./apks_examples --timeout 60 --name smoke_exp --no-window --repetitions 2`
4. Verify:
   - Log shows "Resuming experiment 'smoke_exp' — auto-skipping pre-processing"
   - Pre-processing is skipped (no monitor generation, no instrumentation, no static analysis)
   - Rep 1 is skipped, rep 2 is executed
   - Results consolidated in `results/smoke_exp/`
   - `summary.csv` has 2 rows (rep 1 AND rep 2)
   - `errors.csv` has MOP violation rows for any task that detected violations (reconstructed from logcat for rep 1)
   - `results.json` has violation details for all tasks with logcat files
   - Logcat files exist for both reps
5. Clean up: `rm -rf results/smoke_exp/`

**Smoke Test 4: rv-experiment Form 2 (Crash Recovery)** — Validates that an interrupted rv-experiment can be resumed with the same command.

Steps:
1. Run rv-experiment with `--name` and 3 reps in background: `poetry run rv-experiment run --tools monkey --apks-dir ./apks_examples --timeout 60 --name smoke_exp2 --no-window --repetitions 3 &`
2. Wait for at least 1 task to complete (monitor timing: pre-processing takes several minutes on first run, then ~110s per task)
3. Kill the process: `kill %1`
4. Verify intermediate state: `results/smoke_exp2/tasks.json` has at least 1 completed task
5. Re-run the same command: `poetry run rv-experiment run --tools monkey --apks-dir ./apks_examples --timeout 60 --name smoke_exp2 --no-window --repetitions 3`
6. Verify:
   - Log shows "Resuming experiment 'smoke_exp2' — auto-skipping pre-processing"
   - Pre-processing is skipped on second run
   - Completed tasks from first run are skipped
   - All 3 tasks are completed after the second run finishes
   - Results consolidated in `results/smoke_exp2/`
7. Clean up: `rm -rf results/smoke_exp2/`

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| R1: Resume skips tasks that should re-run (false positive match) | Incomplete or stale results | Only `COMPLETED` tasks are skipped; `ERROR` tasks re-run. Task identity includes all 5 dimensions (apk, tool, variant, rep, timeout). Delete `tasks.json` for a full clean re-run. |
| R2: Config checksum too sensitive (e.g., changing log_level triggers warning) | Unnecessary warning messages on harmless changes | Warning only, does not block. In Docker with identical configs, checksums always match. |
| R3: Docker image size (~3-4 GB) | Slow first pull | Inherent to Java + Python + Android SDK architecture. Docker layer caching makes subsequent builds fast. |
| R4: `--resume-dir` with wrong `apks_dir` | 0% coverage | Resume auto-skips pre-processing; existing instrumented APKs are reused. If user points to non-instrumented APKs, coverage will be 0%. Documented in CLAUDE.md. **Follow-up improvement**: store `original_apks_dir` in `ExperimentMetadata` and warn on divergence during resume — not in this change scope (P1). |
| R5: Parallel containers competing for emulator port | Port conflict errors | Each container uses `RV_DEVICE_PORT` for unique port allocation. Docker Compose template provides per-container port configuration. |

## Goals / Non-Goals

**Goals:**
- Wire existing resume building blocks into a working end-to-end flow
- Add `--resume-dir` CLI flag for explicit resume (Docker-friendly)
- Make `--name` flag resume-aware (detect existing `tasks.json`) (researcher-friendly)
- Create Docker entry point with complete env var translation (aligned with `constants.py`)
- Create Docker files: production, dev, single and parallel compose
- Remove dead code in `config.py` (`get_artifact_validation_config()`, `load_from_status()`, `experiment_dir` field)
- Document all environment variables with their source, default, and Docker vs standalone behavior
- Fix result consolidation on resume: ensure CSV/JSON output files include all completed tasks from all sessions, not just the current session (discovered during smoke testing — see "Bug: Result Consolidation on Resume" section)
- Fix MOP violation reconstruction on resume: `ResultProcessorComponent` re-reads logcat files to reconstruct monitored operations violation data (`errors.csv`, `results.json` violation details) for tasks loaded from `tasks.json` (discovered during smoke testing — see D9 decision)
- Fix ExperimentController double-nesting: use `config.results_dir` directly instead of appending `config.name` (discovered during smoke testing — see "Bug: ExperimentController Double-Nesting" section)
- Document the two resume usage forms (Expand Experiment and Crash Recovery) in specs and module CLAUDE.md
- Enable ARES and QTesting Docker sibling containers: add `docker.sock` mount to compose files, add `--network container:$(hostname)` flag when running inside Docker, integrate ARES/QTesting image builds into `build_all.sh`

**Non-Goals:**
- Parallel task execution within a single Platform instance (`max_parallel_tasks` stays at 1 — parallelism is achieved via Docker containers)
- Watchdog/auto-restart mechanism (Docker Compose `restart: on-failure` handles this natively)
- Changes to `TaskStorage` internals (already correct, just unused)
- Updating PRD FR03 with Legunsen/Owolabi spec set references (follow-up documentation change)

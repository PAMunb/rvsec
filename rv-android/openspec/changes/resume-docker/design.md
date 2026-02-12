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
| Dead Code REMOVED | `config.py` — delete `get_artifact_validation_config()` and `load_from_status()` entirely (backup original to `backup/`). No adapters, no wrappers, no compatibility layers. | verify no import errors, no callers broken, grep confirms zero references |

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

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `--resume-dir` path does not exist | Click `type=Path(exists=True)` | Reject before any experiment logic | User corrects path |
| Config checksum mismatch on resume | `check_continuation_compatibility()` | Warning log with first 8 chars of both checksums, continue execution | User aware of config change; task identity matching still works |
| `get_artifact_validation_config()` crash | Dead code referencing `self.artifact_reuse_enabled` (undefined) | Remove the method entirely (this change) | No callers affected |
| Docker entry point invalid env vars | `docker-entrypoint.sh` | CLI validates downstream (Click param types, Pydantic validators) | User fixes env vars, restarts container |
| `tasks.json` corrupted on resume | `TaskStorage.load()` | Graceful failure — start fresh if JSON parsing fails | Experiment runs as first run (no tasks skipped) |
| Startup delay timeout | `RV_DELAY` in entrypoint | `sleep` finishes, experiment proceeds normally | No action needed |

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|----------|
| Unit | Resume detection logic in CLI (`--resume-dir`, `--name` with existing dir) | Mock filesystem (`tasks.json` existence check) | ~4 tests |
| Unit | Auto-skip flag behavior (INV-EXP-13) | Assert all 3 skip flags are `True` when resume detected | ~2 tests |
| Unit | `ExperimentMetadata` creation in `Platform.run()` | Mock `TaskStorage`, verify `set_experiment_metadata()` called with correct checksum | ~3 tests |
| Unit | `_skip_completed_tasks()` with checksum validation | Mock `TaskStorage` with completed tasks, verify filtering and warning log | ~3 tests |
| Unit | `_skip_completed_tasks()` does not skip ERROR tasks | Mock `TaskStorage` with ERROR tasks, verify they remain in task list | ~1 test |
| Integration | Full resume flow (CLI → Platform) | Temp directory with pre-populated `tasks.json`, run CLI twice | ~2 tests |
| Smoke | Docker entry point env var translation | Shell script testing with `echo` instead of `exec` | ~2 tests |
| Manual | End-to-end resume (run, kill, resume) | Real experiment with emulator: run with `--name`, Ctrl+C after ~2 tasks, re-run same command | 1 test |

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
- Remove dead code in `config.py` (`get_artifact_validation_config()`, `load_from_status()`)
- Document all environment variables with their source, default, and Docker vs standalone behavior

**Non-Goals:**
- Parallel task execution within a single Platform instance (`max_parallel_tasks` stays at 1 — parallelism is achieved via Docker containers)
- ARES and QTesting Docker sibling containers (deferred to follow-up change — these tools require separate server processes)
- Watchdog/auto-restart mechanism (Docker Compose `restart: on-failure` handles this natively)
- Changes to `TaskStorage` internals (already correct, just unused)
- Changes to result processing or CSV/JSON output format
- Updating PRD FR03 with Legunsen/Owolabi spec set references (follow-up documentation change)

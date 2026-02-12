## Why

The experiment resume capability in RV-Android is architecturally present but functionally broken. All the building blocks exist in the codebase — `TaskStorage` provides atomic JSON persistence with write-to-temp-then-rename semantics, `ExperimentMetadata` stores a SHA-256 configuration checksum for compatibility validation, `_skip_completed_tasks()` can filter already-completed tasks by identity matching, and `check_continuation_compatibility()` can verify that the current configuration matches what was stored. However, none of these components are wired together. `ExperimentMetadata` is never initialized by `Platform.run()`, `check_continuation_compatibility()` is never called, and there is no CLI flag to specify that an experiment should resume from an existing results directory.

The root cause is in the CLI layer: every experiment run creates a new results directory with a non-deterministic name (`cli_experiment_YYYYMMDD_HHMMSS_uuid` at `__main__.py:860`), so even if the user runs the exact same command twice, the second run cannot find the first run's `tasks.json` because it lives in a different directory. This makes experiment continuation impossible through normal usage. Additionally, two dead methods in `config.py` — `get_artifact_validation_config()` (which crashes at runtime because it references `self.artifact_reuse_enabled` and `self.phase_control`, fields that do not exist on the model) and `load_from_status()` (which is never called from any entry point) — suggest that a previous attempt at implementing resume was abandoned mid-way.

This gap blocks Docker containerization, which is the immediate operational goal. Docker containers are killed and restarted routinely — by resource limits, by orchestrators, by manual intervention, or by watchdog processes. Without functional resume, a container restart means restarting the entire experiment from scratch, wasting hours of already-completed work. The rvsec-02/ICST study proved the viability of Docker-based parallel experiments: 7 containers running simultaneously, each with its own `execution_memory.json` file for crash recovery and `RV_SKIP_*=true` environment variables for pre-processing bypass on restart. This exact pattern needs to be replicated in the current `rv-experiment` CLI architecture.

Fixing resume and adding Docker support are also prerequisites for the rv-agent-validation framework's parallel experiment execution (Phases B-E of the validation plan), which requires running multiple experiment batches concurrently across different APK subsets.

## What Changes

### Resume Integration (rv-experiment + rv-platform)

The resume fix is an integration task, not a new implementation. The strategy is to wire existing components together and add the missing CLI entry points:

- **Add `--resume-dir` CLI flag** to `rv-experiment` for explicit resume from an existing results directory. When provided, the CLI uses that directory as the experiment output, auto-skips all pre-processing (monitors, instrumentation, static analysis), and lets the platform's `_skip_completed_tasks()` handle the actual task filtering. This is the Docker-friendly entry point — a container sets `RV_RESUME_DIR` to resume.
- **Make `--name` flag resume-aware**: when `--name my_experiment` is provided and `results/my_experiment/` already exists with a `tasks.json`, the CLI automatically detects this as a resume scenario. This is the human-friendly entry point — the researcher runs the same command twice and the system does the right thing.
- **Wire `ExperimentMetadata` initialization** in `Platform.run()`. After task generation (so the full config is available for checksumming), `Platform` creates an `ExperimentMetadata` instance and stores it via `TaskStorage.set_experiment_metadata()`. This is currently defined but never created.
- **Wire `check_continuation_compatibility()`** in `_skip_completed_tasks()`. When previously completed tasks are found (indicating a resume), the platform calls `check_continuation_compatibility()` to compare the current config checksum against the stored one. A mismatch produces a warning but does not block execution — the researcher may have intentionally changed timeouts or added tools.
- **Remove dead code**: `get_artifact_validation_config()` (crashes on undefined fields `artifact_reuse_enabled` and `phase_control`) and `load_from_status()` (dead method never called from any entry point). These are remnants of an abandoned resume implementation attempt.

### Docker Containerization (infrastructure)

Docker files are DevOps infrastructure supporting the resume capability:

- **Create `docker-entrypoint.sh`** translating environment variables (RV_TOOLS, RV_TIMEOUTS, RV_EXPERIMENT_NAME, RV_RESUME_DIR, etc.) to `rv-experiment` CLI arguments. This follows the standard Docker pattern: the Dockerfile sets ENV defaults, the user overrides them at runtime, and the entrypoint script assembles the CLI command. It supports both execution mode (default) and interactive mode (`docker run ... bash`).
- **Update production Dockerfile** with ENTRYPOINT, ENV defaults, and VOLUME declarations for `apks/`, `out/`, and `results/`. The production image clones the RVSEC repository and builds with Maven + Poetry.
- **Create dev Dockerfile** for local development. Instead of git clone, it COPYs local source code, enabling rapid iteration without pushing to GitHub. Volume mounting (`-v $(pwd)/modules:/opt/.../modules`) provides hot-reload without rebuilding.
- **Create Docker Compose files** for single execution (with Humanoid service dependency) and parallel execution (YAML anchors for N containers with per-container volumes and experiment names).
- **Clean legacy code** from `docker/tools/Dockerfile` — approximately 80 lines of commented-out Sapienz, Stoat, Humanoid, and pyflann installation that are no longer relevant.

## Capabilities

### New Capabilities

_None_ — Resume and Docker are extensions of existing experiment and platform capabilities, not new spec domains. The resume architecture already exists in the platform spec (INV-PLT-12, FR10); the experiment spec already defines `resume_mode` and `status_file` fields in the data model. This change wires what was specified but never implemented.

### Modified Capabilities

- `platform`: Wire `ExperimentMetadata` initialization in `Platform.run()`, completing the intent of FR10 (Persistent Task Storage) and INV-PLT-12 (Config Checksum). The existing `_skip_completed_tasks()` method already handles the task filtering logic correctly — the change adds checksum validation via `check_continuation_compatibility()` before the filtering step, and adds the metadata initialization that was always expected but never done. New scenarios cover: first run storing metadata, resume with same config, resume with changed config, resume with no completed tasks.
- `experiment`: Add `--resume-dir` CLI flag and make `--name` resume-aware with auto-skip behavior, extending FR16 (CLI Interface). The existing skip flags (`--skip-monitors`, `--skip-instrument`, `--skip-static`) are auto-set on resume — this is the same pattern used in rvsec-02 with `RV_SKIP_*=true` environment variables. New invariant INV-EXP-13 formalizes the auto-skip behavior. Dead code removal (`get_artifact_validation_config()`, `load_from_status()`) cleans up the abandoned resume implementation.

## Impact

### Affected Modules
- **rv-experiment**: `__main__.py` (CLI flags, resume detection logic), `config.py` (dead code removal — 2 methods)
- **rv-platform**: `platform.py` (ExperimentMetadata initialization in `run()`, checksum validation in `_skip_completed_tasks()`)

### Affected Infrastructure
- `docker/rvandroid/Dockerfile` — Production image: add ENTRYPOINT, ENV, VOLUME, CMD
- `docker/rvandroid/docker-entrypoint.sh` — New entry point script (env vars to CLI translation)
- `docker/rvandroid_dev/Dockerfile` — New dev image (COPY-based, no git clone)
- `docker/docker-compose.yml` — Single execution with Humanoid service
- `docker/docker-compose.parallel.yml` — Parallel execution template with YAML anchors
- `docker/tools/Dockerfile` — Remove ~80 lines of commented legacy code
- `docker/build_all.sh` — Add tools build step, ensure correct build order

### Dependencies
- Resume fix must be completed before Docker entry point can use `--name` for auto-resume (the entry point generates `--name $RV_EXPERIMENT_NAME`, which triggers the resume detection logic in the CLI)
- Docker entry point depends on `--resume-dir` flag existing in CLI (for explicit resume via `RV_RESUME_DIR` env var)
- No external API changes — all changes are internal to rv-experiment and rv-platform
- No changes to `TaskStorage` internals — the existing atomic persistence, threading, and transaction support are already correct

### Related FRs/NFRs (from PRD)
- **FR10**: Persistent Task Storage — task state persistence for resume/recovery. The existing implementation handles storage correctly; this change wires the metadata initialization and checksum validation that were specified but never connected.
- **FR16**: CLI Interface — experiment control via command-line flags. This change adds `--resume-dir` and makes `--name` resume-aware, both following the existing flag pattern established by `--skip-monitors`, `--skip-instrument`, and `--skip-static`.
- **NFR08**: Reproducibility — deterministic experiment identification and resumability. By making `--name` produce deterministic results directories (and detect existing ones), experiments become resumable and reproducible.

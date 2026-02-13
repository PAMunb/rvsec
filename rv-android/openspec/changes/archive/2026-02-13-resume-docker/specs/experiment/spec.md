## ADDED Requirements

### Requirement: Experiment Resume via CLI (FR16-ext)

The CLI MUST support two mechanisms for resuming interrupted experiments: an explicit `--resume-dir` flag pointing to an existing results directory, and an implicit resume via the `--name` flag when the named results directory already contains a `tasks.json` file. Both mechanisms MUST auto-skip all pre-processing phases (monitor generation, APK instrumentation, static analysis) because the pre-processing artifacts — generated monitors in `out/monitors/`, instrumented APKs in `out/instrumented_apks/`, and static analysis files (`.wtg`, `.gesda`, `.reach`) — already exist from the original run and re-generating them would waste time and potentially overwrite the artifacts that the platform needs for coverage tracking.

Resume detection relies on the presence of a `tasks.json` file in the target results directory. This file is written atomically by `TaskStorage` after each task state change (using write-to-temp-then-rename semantics with `fsync`), so its presence reliably indicates that a previous experiment run used this directory and reached at least the task generation phase. The platform's `_skip_completed_tasks()` handles the actual task-level skipping based on identity matching — rv-experiment's responsibility is limited to ensuring the same results directory is reused and that pre-processing is bypassed.

The auto-skip behavior on resume is formalized as INV-EXP-13. When resume is detected, the CLI sets `generate_monitors=False`, `instrument_apks=False`, and `run_static_analysis=False` regardless of what the user passed on the command line. This matches the rvsec-02/ICST pattern where Docker containers used `RV_SKIP_MONITORS=true`, `RV_SKIP_INSTRUMENT=true`, and `RV_SKIP_STATIC_ANALYSIS=true` environment variables for resumed containers, because re-running the pre-processing pipeline on already-instrumented APKs would overwrite them with freshly instrumented versions that may differ if the specification set or RVSEC tools have been updated.

The `--resume-dir` flag provides explicit control for advanced users and Docker automation (via the `RV_RESUME_DIR` environment variable in the Docker entry point). The `--name` flag provides implicit, ergonomic resume for interactive use — the researcher runs the same command twice and the system automatically detects the existing results. When both are provided, `--resume-dir` takes precedence because explicit intent overrides implicit detection.

#### Scenario: Resume With --resume-dir Flag

- **WHEN** the user runs `rv-experiment run --resume-dir ./results/my_experiment`
- **THEN** the CLI MUST use `./results/my_experiment` as the experiment results directory, bypassing the normal directory creation logic (`cli_experiment_YYYYMMDD_HHMMSS_uuid`)
- **AND** MUST auto-set `generate_monitors=False`, `instrument_apks=False`, `run_static_analysis=False`
- **AND** MUST log "Resuming experiment from ./results/my_experiment"
- **AND** the `--apks-dir` argument MUST be provided by the user (or default applies) — the CLI does NOT auto-detect the APKs directory from the results structure, because the user knows which APKs were used in the original run and should point to the instrumented APKs directory explicitly
- **AND** the platform MUST skip already-completed tasks via `_skip_completed_tasks()`

#### Scenario: Resume With --name Detecting Existing Results

- **WHEN** the user runs `rv-experiment run --tools monkey --name my_experiment`
- **AND** the directory `results/my_experiment/` already exists and contains a `tasks.json` file
- **THEN** the CLI MUST detect the existing experiment and enable resume mode
- **AND** MUST auto-set `generate_monitors=False`, `instrument_apks=False`, `run_static_analysis=False`
- **AND** MUST log "Resuming experiment 'my_experiment' — auto-skipping pre-processing"
- **AND** MUST use `results/my_experiment/` as the experiment results directory (not create a new one)
- **AND** the platform MUST skip already-completed tasks via `_skip_completed_tasks()`

#### Scenario: First Run With --name (No Existing Results)

- **WHEN** the user runs `rv-experiment run --tools monkey --name new_experiment`
- **AND** the directory `results/new_experiment/` does not exist
- **THEN** the CLI MUST create the results directory `results/new_experiment/` normally
- **AND** MUST NOT modify the skip flags (pre-processing runs as configured by the user)
- **AND** the experiment MUST execute as a fresh run with the deterministic name `new_experiment`

#### Scenario: --resume-dir With Non-Existent Directory

- **WHEN** the user runs `rv-experiment run --resume-dir ./results/nonexistent`
- **THEN** Click's `type=click.Path(exists=True)` MUST reject the argument before any experiment logic executes
- **AND** the CLI MUST display an error message indicating the directory does not exist
- **AND** the experiment MUST NOT start

#### Scenario: --resume-dir Overrides --name

- **WHEN** the user provides both `--resume-dir ./results/old_exp` and `--name new_exp`
- **THEN** `--resume-dir` MUST take precedence because it represents explicit intent
- **AND** the experiment MUST use `./results/old_exp` as the results directory
- **AND** the `--name` value MUST be ignored for directory selection purposes

### Invariant: INV-EXP-13 (Resume Auto-Skip)

When resuming an experiment (via `--resume-dir` or via `--name` with an existing `tasks.json`), all three pre-processing skip flags MUST be set to `True` regardless of their CLI values. This invariant ensures that pre-processing artifacts from the original run are reused intact. The `apks_dir` for the platform MUST point to the instrumented APKs directory from the original run — if the user provides `--apks-dir` pointing to non-instrumented APKs during a resume, the pre-processing skip flags mean those APKs will be used as-is (without instrumentation), resulting in 0% coverage. This trade-off is documented in CLAUDE.md under "Reusing Pre-Processed Artifacts."

### Invariant: INV-EXP-14 (Results Directory Structure)

The experiment results directory MUST be a flat path without internal nesting. `ExperimentController` MUST use `config.results_dir` directly as the results directory — it MUST NOT append `config.name` or any other subdirectory component. The CLI layer (`__main__.py`) is responsible for constructing the complete results path (e.g., `results/my_experiment/` or `results/cli_experiment_20260212_abc123/`) before passing it to `ExperimentConfig.results_dir`.

This invariant exists because a bug was discovered during smoke testing where `ExperimentController.__init__()` appended `config.name` to `config.results_dir`, creating double-nested directories (e.g., `results/smoke_exp/smoke_exp/`). This caused resume detection to fail: `__main__.py` checked `results/smoke_exp/tasks.json` but the file was actually at `results/smoke_exp/smoke_exp/tasks.json`. The fix ensures a single, predictable directory structure where `tasks.json`, logcat files, and all result artifacts live directly under `config.results_dir`.

#### Scenario: ExperimentController Uses config.results_dir Directly

- **WHEN** `ExperimentController.__init__()` is called with `config.results_dir = "results/my_experiment"`
- **THEN** `self.results_dir` MUST be `"results/my_experiment"` (not `"results/my_experiment/my_experiment"`)
- **AND** `tasks.json` MUST be written to `results/my_experiment/tasks.json`
- **AND** all result artifacts (summary.csv, errors.csv, etc.) MUST be in `results/my_experiment/`

## MODIFIED Requirements

### Requirement: CLI with Tool Specification DSL (FR16, NFR05)

The Experiment Orchestration domain MUST provide a Click-based CLI with four commands (`run`, `config`, `list-tools`, `validate`) and a tool specification DSL that allows compact, composable tool configuration from the command line. This design exists because experiments often involve comparing multiple tools with different configurations, and a verbose JSON-only interface would be impractical for iterative experimentation.

The `run` command MUST support two mutually exclusive modes: CLI mode (tool specifications via `--tools` argument) and config mode (JSON file via `--config` argument). When `--config` is provided, all other tool/execution arguments are ignored and the configuration is loaded from the file.

The `run` command MUST also support experiment resume via `--resume-dir` flag (pointing to an existing results directory) and via `--name` flag (detecting existing results directory with `tasks.json`). When resume is detected, pre-processing skip flags MUST be auto-set to `True` as defined by INV-EXP-13. This resume capability is required for Docker containerization — containers may be killed and restarted by resource limits, orchestrators, or watchdog processes, and without functional resume, a restart means discarding all completed work.

The tool specification DSL format MUST be: `tool_name[:variant1][:variant2][@param1=value1,param2=value2]`. Multiple tools are separated by commas. The parser MUST correctly handle commas that appear inside parameter sections (e.g., `rvagent:multimode@temperature=0.3,top_p=0.6` is one tool, not two).

The CLI MUST provide skip flags (`--skip-monitors`, `--skip-instrument`, `--skip-static`) that disable the corresponding pre-processing phase. These flags map directly to the `generate_monitors`, `instrument_apks`, and `run_static_analysis` fields of `ExperimentConfig`.

The CLI MUST provide `--no-window/--window` flag to control emulator visibility, with `--no-window` (headless) as the default.

#### Scenario: Single Tool With Default Configuration

- **WHEN** the user runs `rv-experiment run --tools monkey`
- **THEN** the CLI MUST parse the tool specification into `ToolConfig(name="monkey", variants=[], parameters={})`
- **AND** an `ExperimentConfig` MUST be created with `tool_configs` containing that single ToolConfig
- **AND** the experiment MUST execute with default timeout (300s), default repetitions (1), and default specification set (jca)

#### Scenario: Multiple Tools With Variants and Parameters

- **WHEN** the user runs `rv-experiment run --tools monkey,droidbot:dfs_greedy,rvagent:multimode@temperature=0.3`
- **THEN** the CLI MUST parse three ToolConfig objects:
  - `ToolConfig(name="monkey", variants=[], parameters={})`
  - `ToolConfig(name="droidbot", variants=["dfs_greedy"], parameters={})`
  - `ToolConfig(name="rvagent", variants=["multimode"], parameters={"temperature": "0.3"})`
- **AND** `ExperimentConfig.tool_configs` MUST contain all three in order

#### Scenario: Parameters With Commas Inside Tool Specification

- **WHEN** the user runs `rv-experiment run --tools rvagent:multimode@temperature=0.3,top_p=0.6`
- **THEN** the DSL parser MUST treat `temperature=0.3` and `top_p=0.6` as parameters of the same `rvagent` tool
- **AND** MUST NOT split this into two separate tool specifications
- **AND** the resulting ToolConfig MUST have `parameters={"temperature": "0.3", "top_p": "0.6"}`

#### Scenario: Configuration File Mode

- **WHEN** the user runs `rv-experiment run --config experiment_config.json`
- **THEN** the CLI MUST load the configuration from the JSON file using `ExperimentConfig.from_file()`
- **AND** MUST call `experiment_config.validate()` before execution
- **AND** MUST NOT parse the `--tools` argument

#### Scenario: Custom Specification Set Without Directory

- **WHEN** the user runs `rv-experiment run --tools monkey --specification-set custom` without providing `--custom-specs-dir`
- **THEN** the CLI MUST raise a `ClickException` with message: "Custom specification directory (--custom-specs-dir) is required when using --specification-set=custom"
- **AND** the experiment MUST NOT start

#### Scenario: Unknown Tool Warning

- **WHEN** the user specifies a tool name that is not registered in the ToolRegistry (e.g., `rv-experiment run --tools unknown_tool`)
- **THEN** the CLI MUST log a warning: "Tool 'unknown_tool' not found in registry. Available tools: ..."
- **AND** the tool specification MUST still be parsed and included in the configuration (validation happens later during `ExperimentConfig.validate()`)

#### Scenario: Resume With --resume-dir Flag

- **WHEN** the user runs `rv-experiment run --resume-dir ./results/my_experiment`
- **THEN** the CLI MUST use `./results/my_experiment` as the experiment results directory
- **AND** MUST auto-set `generate_monitors=False`, `instrument_apks=False`, `run_static_analysis=False`
- **AND** MUST log "Resuming experiment from ./results/my_experiment"

#### Scenario: Resume With --name Detecting Existing Results

- **WHEN** the user runs `rv-experiment run --tools monkey --name my_experiment`
- **AND** the directory `results/my_experiment/` already exists and contains `tasks.json`
- **THEN** the CLI MUST enable resume mode and auto-skip pre-processing
- **AND** MUST log "Resuming experiment 'my_experiment' — auto-skipping pre-processing"

### Requirement: Docker Execution Mode (FR16-ext, NFR08)

The experiment orchestration system MUST support execution inside Docker containers as a first-class deployment mode. This is not merely about packaging — Docker execution enables parallel experiment execution (multiple containers running simultaneously, each with its own emulator) and crash recovery (containers are killed and restarted routinely by orchestrators, resource limits, or watchdog processes). The rvsec-02/ICST study validated this pattern with 7 parallel containers over thousands of restarts.

Docker execution uses a shell entry point (`docker-entrypoint.sh`) that translates Docker environment variables to `rv-experiment` CLI arguments. This follows the standard Docker pattern: the Dockerfile sets ENV defaults, the user overrides them at `docker run` time, and the entry point assembles the CLI command. The entry point script MUST echo the generated command for debugging transparency and MUST support both execution mode (default, runs `rv-experiment run`) and interactive mode (when the user passes `bash` or `shell` as the command, drops into a shell for debugging).

Environment variables are categorized into two groups:

1. **CLI-translated variables**: Read by `docker-entrypoint.sh` and converted to `rv-experiment run` flags. Examples: `RV_TOOLS` (→ `--tools`), `RV_TIMEOUTS` (→ `--timeout`), `RV_EXPERIMENT_NAME` (→ `--name`), `RV_RESUME_DIR` (→ `--resume-dir`). These have no effect outside Docker unless a standalone script performs the same translation.

2. **Pass-through variables**: Read directly by Python modules via `os.environ.get()`. Examples: `RVSEC_HOME`, `ANDROID_HOME`, `RVAGENT_MODE`. These are set as container environment variables in `docker-compose.yml` and are NOT translated to CLI flags by the entry point.

The entry point MUST also support a startup delay (`RV_DELAY`) for staggering container startups in parallel execution. The first activities (emulator boot, APK instrumentation) consume significant CPU and I/O, so staggering prevents resource contention.

Docker Compose files provide two deployment patterns:

1. **Single container** (`docker-compose.yml`): One rvandroid container with a Humanoid service dependency and `docker.sock` mount for ARES/QTesting sibling containers.

2. **Parallel containers** (`docker-compose.parallel.yml`): YAML anchors define a base service (`x-rvandroid`), with N concrete services (rv01, rv02, ...) each having their own `RV_EXPERIMENT_NAME`, `RV_DEVICE_PORT`, `RV_DELAY`, and per-container result volumes. All containers share the same Humanoid REST service. Each container has its own `docker.sock` mount for independent ARES/QTesting sibling container spawning.

The `docker.sock` mount (`/var/run/docker.sock:/var/run/docker.sock`) in both compose files allows each rvandroid container to spawn ARES/QTesting sibling containers via the host's Docker daemon. Without this mount, Docker-based tools (ARES, QTesting) fail because there is no Docker daemon available inside the container. See the tools domain delta spec (INV-TOOL-15) for the network configuration of sibling containers.

#### Scenario: Docker Entry Point Translates Environment Variables to CLI

- **WHEN** a Docker container starts with `RV_TOOLS=monkey,droidbot`, `RV_TIMEOUTS=300`, `RV_EXPERIMENT_NAME=batch_01`, `RV_NO_WINDOW=true`
- **THEN** the entry point MUST generate: `poetry run rv-experiment run --tools monkey,droidbot --timeout 300 --name batch_01 --no-window`
- **AND** MUST echo the generated command to stdout for debugging
- **AND** MUST use `exec` to replace the shell process with the Python process (proper signal handling)

#### Scenario: Docker Entry Point Supports Interactive Mode

- **WHEN** the user runs `docker run ... phtcosta/rvandroid:0.8.0 bash`
- **THEN** the entry point MUST detect the `bash` or `shell` argument
- **AND** MUST drop into an interactive bash shell instead of running the experiment
- **AND** the user MUST be able to run `rv-experiment` commands manually inside the container

#### Scenario: Docker Entry Point Applies Startup Delay

- **WHEN** a Docker container starts with `RV_DELAY=30`
- **THEN** the entry point MUST `sleep 30` before executing the experiment command
- **AND** MUST log the delay duration

#### Scenario: Docker Resume on Container Restart

- **WHEN** a Docker container with `RV_EXPERIMENT_NAME=batch_01` completes 3 out of 10 tasks and is killed
- **AND** a new container starts with the same `RV_EXPERIMENT_NAME=batch_01` and the same result volume mount
- **THEN** the entry point MUST generate the same `--name batch_01` CLI argument
- **AND** rv-experiment MUST detect `results/batch_01/tasks.json` and trigger resume mode (INV-EXP-13)
- **AND** the platform MUST skip the 3 completed tasks and execute the remaining 7

#### Scenario: Parallel Docker Execution With Independent Experiments

- **WHEN** `docker-compose.parallel.yml` is used with rv01 (`RV_EXPERIMENT_NAME=rv01`) and rv02 (`RV_EXPERIMENT_NAME=rv02`)
- **THEN** each container MUST use its own results directory (`results/rv01/`, `results/rv02/`)
- **AND** each container MUST use its own emulator port (`RV_DEVICE_PORT=5554`, `RV_DEVICE_PORT=5556`)
- **AND** each container MUST have its own `docker.sock` mount for independent ARES/QTesting sibling container spawning
- **AND** the Humanoid service MUST be shared across all containers (single instance)
- **AND** containers MUST be staggered via `RV_DELAY` to avoid resource contention during emulator boot

#### Scenario: docker.sock Mount Enables Docker-Based Tools

- **WHEN** a rvandroid container has `/var/run/docker.sock:/var/run/docker.sock` mounted
- **THEN** `AresTool._build_ares_command()` and `QTestingTool._build_qtesting_command()` MUST be able to execute `docker run` to spawn sibling containers
- **AND** the sibling containers MUST share the parent's network namespace via `--network container:$(hostname)` (INV-TOOL-15)

- **WHEN** a rvandroid container does NOT have the `docker.sock` mount
- **THEN** Docker-based tools (ARES, QTesting) MUST fail with a clear error when attempting `docker run`
- **AND** non-Docker tools (Monkey, DroidBot, APE, etc.) MUST continue to function normally

## REMOVED Requirements

### Requirement: Dead Code in ExperimentConfig

Two methods in `ExperimentConfig` (`modules/rv-experiment/src/rv_experiment/config.py`) MUST be **completely removed** — not deprecated, not wrapped, not hidden behind a flag. This follows the project's code evolution principle: all changes are complete replacements, never backward-compatible shims. Legacy code is removed or overwritten, not preserved alongside new implementations. The original file MUST be backed up to `backup/` before modification, preserving the full git-diff context for the thesis record, but the production codebase MUST NOT retain any trace of these methods.

**`get_artifact_validation_config()`** (line ~934) references two fields that do not exist on the `ExperimentConfig` model: `self.artifact_reuse_enabled` and `self.phase_control`. Calling this method raises `AttributeError` at runtime. No code path in rv-experiment or any other module calls this method. The method was presumably written for a planned artifact validation feature that was never integrated. It MUST be deleted from the source file — not commented out, not marked `@deprecated`, not guarded with `if False`.

**`load_from_status()`** is a class method that was intended to reconstruct an `ExperimentConfig` from a status file, enabling experiment continuation from a saved state. However, no entry point in rv-experiment (neither the CLI nor the `ExperimentController`) ever calls this method. The resume mechanism implemented in this change uses a fundamentally different approach: instead of reconstructing the full experiment config from a status file, the user re-runs the same CLI command with `--name` or `--resume-dir`, and the platform's `_skip_completed_tasks()` handles the task-level skipping. This approach is simpler and more robust because it does not require serializing and deserializing the full experiment state. The old method MUST be deleted entirely — no adapter, no compatibility layer, no re-export.

**`experiment_dir` field** on `ExperimentConfig` was set during `__init__` via `get_experiment_dir(self.results_dir, self.name)` but never read by any code in the entire codebase. It was a dead field — computed and stored but never consumed. The `get_experiment_dir` import from `constants.py` is also removed from config.py. The function itself remains in `constants.py` since it may be used elsewhere, but the field and its initialization in `ExperimentConfig.__init__` are deleted.

**Removal policy**: The code is deleted outright. No migration is needed because neither method was ever successfully invoked by any caller, and the `experiment_dir` field was never read. Removing them does not change any observable behavior. No backward-compatibility wrapper, adapter, or shim is created — the methods and fields simply cease to exist. Any future resume-related code will be written from scratch following the new architecture (CLI detection + platform task skipping), not built on top of these abandoned methods. The `resume_mode` and `status_file` fields in the `ExperimentConfig` data model are retained because they are now wired to the CLI's resume detection logic — they are live code, not dead code.

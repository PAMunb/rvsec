## Purpose

The Experiment Orchestration domain (`rv-experiment`) is the top-level entry point for RV-Android experiments and the **only** Layer 5 module. After this change, it is also the **only** sanctioned reader of user-facing `RV_*` environment variables. Lower layers (Platform L4, Analysis/Instrumentation L3, Tools L2) receive their configuration via Pydantic models, never via direct `os.environ` access. The narrow exceptions (`RV_PYDANTIC`, `RVSEC_HOME`, `ANDROID_HOME`) are infrastructure-level reads owned by Core (L1).

The Docker entry point is reshaped accordingly. Previously it translated environment variables to `rv-experiment` CLI flags (e.g., `RV_TOOLS=monkey` → `--tools monkey`). After this change it stops translating. Instead it validates the environment-variable allow-list (rejecting unknown `RV_*` names with exit 64) and execs `rv-experiment` directly. The Python configuration layer reads the variables itself via `ENV_*` constants from the Core registry. Two motivations drive this:

1. **Single point of truth**. The same code paths handle Docker invocations and direct CLI invocations. No "this works inside Docker but not outside" surprises.
2. **Allow-list discipline**. With the entry point validating against the registry, typos in environment-variable names fail loudly rather than being silently ignored.

The change also adds two CLI flags (`--analysis-timeout`, `--jvm-memory`) to surface configuration that previously had no flag equivalent and was therefore reachable only through Docker translation. This eliminates the silent-failure cliff observed when `rv-experiment` ran outside Docker with `RV_SA_TIMEOUT=900` set in the environment — the value was previously ignored; after this change, both the env var and the flag work uniformly.

## Data Contracts

### Input
- Environment variables (allow-list defined by `ENV_*` constants in `rv-android-core`)
- CLI flags (parsed by Click)
- Existing inputs unchanged

### Output
- `ExperimentConfig` (Pydantic, `extra="forbid"`) — single in-memory representation of resolved configuration
- Pass-through to `PlatformConfig.tools` (each entry's `parameters` dict) for tool-specific values; the L5 source field is `ExperimentConfig.tool_configs`, translated by `ConfigurationFactory`.

### Side-Effects
- Docker entry point exits with code 64 when an unknown `RV_*` variable is set in the environment

### Error
- `pydantic.ValidationError` on unknown `ExperimentConfig` fields
- Shell exit 64 from entry point on unknown `RV_*` env var

## Invariants

- **INV-EXP-30**: `rv-experiment` is the only Python module under `modules/` that reads user-facing `RV_*` environment variables. Verified by lint scoped to `modules/` excluding `modules/rv-experiment/` and the L1 cross-layer infra family of 6 names: the three `RV_*`-prefixed toggles in `modules/rv-android-core/util/validation/config.py` (`RV_PYDANTIC`, `RV_PYDANTIC_STRICT`, `RV_PYDANTIC_LOG`), plus the three legacy non-`RV_*` paths consumed at L1 (`RVSEC_HOME` and `TOOLS_DIR` in `modules/rv-android-core/util/jar_resolver.py`; `ANDROID_HOME` in `modules/rv-android-core/util/android/android.py`).
- **INV-EXP-31**: The Docker entry point at `docker/rvandroid/docker-entrypoint.sh` MUST exit with code 64 when an environment variable matching the regex `^RV_[A-Z_]+` is set but is not present in the registry derived from `rv-android-core/constants.py`.
- **INV-EXP-32**: Every CLI flag for tunable values has a corresponding `ENV_*` env var of equivalent semantics (and vice versa). Precedence is **CLI flag > env var > Pydantic default**, asserted by unit tests.

## MODIFIED Requirements

### Requirement: Docker Execution Mode (FR16-ext, NFR08)

The experiment orchestration system MUST support execution inside Docker containers as a first-class deployment mode. This is not merely about packaging — Docker execution enables parallel experiment execution (multiple containers running simultaneously, each with its own emulator) and crash recovery (containers are killed and restarted routinely by orchestrators, resource limits, or watchdog processes). The rvsec-02/ICST study validated this pattern with 7 parallel containers over thousands of restarts.

Docker execution uses a shell entry point (`docker/rvandroid/docker-entrypoint.sh`) that performs **two responsibilities and only two**: (a) it validates the allow-list of `RV_*` environment variables present in the container, rejecting unknown names with exit 64; (b) it execs `rv-experiment run` (or drops to an interactive shell on `bash`/`shell` argument). The entry point MUST NOT translate environment variables into CLI flags — `rv-experiment` reads its configuration from the environment itself, via the `ENV_*` constants registry in `rv-android-core`. This unification ensures that a given `RV_X` value produces identical behavior whether the user runs `docker run -e RV_X=...` or `RV_X=... uv run rv-experiment ...` outside Docker.

The allow-list of recognized `RV_*` variables is derived deterministically from `rv-android-core/src/rv_android_core/constants.py`. The entry point invokes `docker/rvandroid/scripts/validate_env_vars.sh` (or equivalent inline check) which compares the set of `RV_*` variables present in the environment against the set of `ENV_*` constants exported from `constants.py`. Any difference (an unknown name, or a known name that has been removed) produces exit code 64 and a message naming the offending variables and pointing at the registry as the source of truth.

The entry point continues to support the interactive shell shortcut: when invoked with `bash` or `shell` as the command argument, the entry point drops into an interactive bash shell instead of running the experiment, allowing manual debugging inside the container. The startup-delay variable `RV_DELAY` retains its existing semantics (sleep before exec) for staggering parallel container starts.

Docker Compose files provide two deployment patterns:

1. **Single container** (`docker-compose.yml`): One rvandroid container with a Humanoid service dependency and `docker.sock` mount for ARES/QTesting sibling containers.
2. **Parallel containers** (`docker-compose.parallel.yml`): YAML anchors define a base service (`x-rvandroid`), with N concrete services (rv01, rv02, ...) each having their own `RV_EXPERIMENT_NAME`, `RV_DEVICE_PORT`, `RV_DELAY`, and per-container result volumes. All containers share the same Humanoid REST service. Each container has its own `docker.sock` mount for independent ARES/QTesting sibling container spawning.

The `docker.sock` mount (`/var/run/docker.sock:/var/run/docker.sock`) in both compose files allows each rvandroid container to spawn ARES/QTesting sibling containers via the host's Docker daemon. Without this mount, Docker-based tools (ARES, QTesting) fail because there is no Docker daemon available inside the container. See the tools domain for the network configuration of sibling containers.

#### Scenario: Docker Entry Point Validates Environment-Variable Allow-List

- **WHEN** a Docker container starts with `RV_TOOLS=monkey,droidbot`, `RV_TIMEOUTS=300`, `RV_EXPERIMENT_NAME=batch_01`
- **AND** all of the names match `ENV_*` constants in `rv-android-core/constants.py`
- **THEN** the entry point MUST proceed to exec `uv run rv-experiment run`
- **AND** MUST NOT add any CLI flags derived from environment variables (translation removed)
- **AND** MUST use `exec` to replace the shell process with the Python process (proper signal handling)

#### Scenario: Docker Entry Point Rejects Unknown RV_* Variable

- **WHEN** a Docker container starts with `RV_INVENTADO=foo` set in the environment
- **AND** `RV_INVENTADO` does not correspond to any `ENV_*` constant in `rv-android-core/constants.py`
- **THEN** the entry point MUST exit with code 64
- **AND** MUST emit a message naming `RV_INVENTADO` as unknown
- **AND** MUST point at `rv-android-core/constants.py` as the canonical registry of valid names

#### Scenario: Docker Entry Point Rejects Removed Variable

- **WHEN** a Docker container starts with `RV_JCA_SPEC=jca` (a name removed by this change)
- **THEN** the entry point MUST exit with code 64 (the name is no longer in the registry)
- **AND** the message MAY suggest the replacement (`RV_SPEC_SET`) when a known mapping exists

#### Scenario: Docker Entry Point Supports Interactive Mode

- **WHEN** the user runs `docker run ... phtcosta/rvandroid:VERSION bash`
- **THEN** the entry point MUST detect the `bash` or `shell` argument
- **AND** MUST drop into an interactive bash shell instead of running the experiment
- **AND** MUST NOT perform allow-list validation (interactive mode bypasses validation; the user is debugging)

#### Scenario: Docker Entry Point Applies Startup Delay

- **WHEN** a Docker container starts with `RV_DELAY=30`
- **AND** allow-list validation passes
- **THEN** the entry point MUST `sleep 30` before executing the experiment command
- **AND** MUST log the delay duration

#### Scenario: Identical Behavior Inside and Outside Docker

- **WHEN** the user runs `RV_TIMEOUTS=600 RV_TOOLS=monkey uv run rv-experiment run` outside Docker
- **AND** the user runs `docker run -e RV_TIMEOUTS=600 -e RV_TOOLS=monkey phtcosta/rvandroid:VERSION` inside Docker
- **THEN** both invocations MUST produce identical effective `ExperimentConfig` values
- **AND** the Python configuration layer MUST read both environment values via `ENV_TIMEOUTS` and `ENV_TOOLS` constants

## ADDED Requirements

### Requirement: Static-Analysis Tuning CLI Flags (FR15, NFR05)

The `rv-experiment run` command MUST expose `--analysis-timeout` (integer seconds) and `--jvm-memory` (string, e.g., `4g`) as command-line flags. These flags MUST set `ExperimentConfig.analysis_timeout` and `ExperimentConfig.jvm_memory` respectively, which `ExperimentConfig.get_static_analysis_config()` already forwards to `RVStaticAnalysisConfig`.

When neither the flag nor the corresponding environment variable is provided, `ExperimentConfig` falls back to the Pydantic-declared default (currently 600 seconds for analysis-timeout, `4g` for jvm-memory). When both are provided, the CLI flag wins (precedence: CLI > env > default), per INV-EXP-32.

The flags eliminate the silent-failure cliff that existed when `rv-experiment` ran outside Docker — previously, only `RV_SA_TIMEOUT` and `RV_JVM_MEMORY` could tune these values, and only via Docker entry-point translation. After this change, both the env vars and the flags work uniformly via `ExperimentConfig`.

#### Scenario: CLI flag overrides env var

- **WHEN** the shell has `RV_SA_TIMEOUT=900` exported
- **AND** the user runs `uv run rv-experiment run --analysis-timeout 600 ...`
- **THEN** the effective `ExperimentConfig.analysis_timeout` MUST be `600`
- **AND** the value forwarded to `RVStaticAnalysisConfig` MUST be `600`

#### Scenario: Env var works without Docker

- **WHEN** the shell has `RV_SA_TIMEOUT=900` exported
- **AND** the user runs `uv run rv-experiment run ...` (no Docker, no `--analysis-timeout` flag)
- **THEN** the effective `ExperimentConfig.analysis_timeout` MUST be `900`
- **AND** the silent-failure path observed before this change MUST NOT occur

#### Scenario: Default applies when neither is set

- **WHEN** neither `RV_SA_TIMEOUT` nor `--analysis-timeout` is provided
- **THEN** the effective `ExperimentConfig.analysis_timeout` MUST be the Pydantic-declared default (600)

### Requirement: Layer-Purity Audit for Environment Reads (NFR01, NFR03)

The `rv-experiment` module is the single Python module under `modules/` that reads user-facing `RV_*` environment variables. The CI lint MUST verify this by running a combined grep covering all read forms (`os\.environ\.get`, `os\.environ\[`, `os\.getenv`, `dict\(os\.environ`, `os\.environ\.copy`) over `modules/`. Hits MUST occur only inside `modules/rv-experiment/` plus the L1 cross-layer infrastructure family in `modules/rv-android-core/util/validation/config.py` (the three `RV_PYDANTIC*` toggles) and the legacy SDK paths `RVSEC_HOME` / `ANDROID_HOME`.

#### Scenario: Lint rejects new env read in lower layer

- **WHEN** a developer adds `os.environ.get(ENV_TOOLS)` in `modules/rv-platform/src/rv_platform/...`
- **THEN** the CI lint MUST fail naming the offending file and line
- **AND** the message MUST point the developer at the experiment delta spec for the Layer Purity rule

#### Scenario: Cross-layer infra family is permitted

- **WHEN** `modules/rv-android-core/src/rv_android_core/util/validation/config.py` reads `RV_PYDANTIC`, `RV_PYDANTIC_STRICT`, or `RV_PYDANTIC_LOG`
- **THEN** the CI lint MUST recognize all three as authorized L1 cross-layer infra reads (they control validation behavior across every module)
- **AND** MUST NOT flag any of them
- **AND** the lint MUST also accept `RVSEC_HOME` and `ANDROID_HOME` reads in `rv-android-core` (legacy SDK paths)

<!-- The previous draft contained a "REMOVED Requirement: Docker Entry Point CLI-Flag Translation"
     block here. It was redundant: in the baseline (`openspec/specs/experiment/spec.md:429`), CLI-flag
     translation is described as a behavior of the existing "Docker Execution Mode" requirement, not
     as a standalone requirement. The MODIFIED Requirement above already replaces that behavior with
     the allow-list-validation pattern; there is no separate requirement to remove. Per P3, the
     pre-refactor `docker-entrypoint.sh` is moved to `backup/2026-05-06_env_var_cleanup/` (see tasks
     5.1) — the deletion is operational, not a separate spec delta. -->


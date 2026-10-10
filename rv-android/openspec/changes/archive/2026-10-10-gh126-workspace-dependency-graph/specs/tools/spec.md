## Purpose

The tool infrastructure registers two tools that live outside rv-tools: `rvagent` (module `rvagent-tool`) and `aperv` (module `aperv-tool`). rv-platform's `_register_external_tools()` imports both when `rv_platform` is imported. Until this delta the spec named only `rvagent` as an external tool, and it stated a dependency graph that the code does not have. rv-platform imported `aperv_tool` without declaring `aperv-tool`. Both plugin modules declared `rv-tools` but never imported it, because `AbstractTool` and `ToolSpec` come from `rv-android-core`. rv-uiautomator declared `rv-screen-parser` and never imported it.

No runtime behaviour changes. The root `uv sync` installs every workspace member, so the installed set is the same before and after. What changes is that the declared graph now states exactly the edges the code imports. Registration itself (idempotency checks, the `ImportError` and `Exception` guards) stays as it is.

The narrative sections of `openspec/specs/tools/spec.md` that repeat the old graph are corrected by hand when this change is archived: design decision 3 ("rvagent-tool depends on rv-agent + rv-tools") and the "Dependencies" list under "Relationship with Other Domains" ("rv-screen-parser: rv-uiautomator depends on it for UI parsing capabilities"). rv-uiautomator's only workspace dependency is `rv-android-core`.

## Invariants

- **INV-TOOL-12** (modified): External tool registration in rv-platform MUST be idempotent. `_register_external_tools()` MUST check `is_tool_registered("rvagent")` before registering `RVAgentTool` and `is_tool_registered("aperv")` before registering `ApeRVTool`. Multiple imports of `rv_platform` MUST NOT produce duplicate registrations.
- **INV-TOOL-26**: Every plugin module that `_register_external_tools()` imports MUST be declared in `modules/rv-platform/pyproject.toml`, in `dependencies` and in `[tool.uv.sources]`. A plugin module (`rvagent-tool`, `aperv-tool`) or a tool-infrastructure module (`rv-uiautomator`) MUST NOT declare a workspace module that its `src/` never imports.

## MODIFIED Requirements

### Requirement: External Tool Support (FR19, NFR02)

The system MUST support 8 third-party Android test generation tools, each implemented as a class extending `AbstractTool` in the `rv_tools.builtin` package. Each tool implementation follows a consistent pattern: a class-level `TOOL_SPEC` attribute created via `ToolSpec.create_builtin_spec()`, a parameterless `__init__()` that delegates to `super().__init__(name, description, process_pattern)`, and implementations of `get_tool_spec()`, `get_variants()`, `configure()`, and `execute_tool_specific_logic()`.

Tools execute via the template method in `AbstractTool.execute()`: it calls `execute_tool_specific_logic()`, then `kill_related_processes()`. If `RVCommandTimeoutError` is raised, it is converted to `RVToolTimeoutError` (expected behavior). Tools build their specific commands (ADB shell commands, project scripts, etc.) and execute them via `_execute_and_check_command()`, which integrates the circuit breaker pattern for resilience against consistently failing commands.

The 8 built-in tools and their invocation mechanisms are:

| Tool | Module | Invocation | Process Pattern |
|------|--------|------------|-----------------|
| Monkey | `builtin/monkey/` | `adb shell monkey` | `com.android.commands.monkey` |
| DroidBot | `builtin/droidbot/` | `uv run droidbot` | `droidbot` |
| APE | `builtin/ape/` | ADB command | `ape` |
| FastBot | `builtin/fastbot/` | ADB command | `fastbot` |
| ARES | `builtin/ares/` | Docker-based | `ares` |
| DroidMate | `builtin/droidmate/` | JAR execution | `droidmate` |
| Humanoid | `builtin/humanoid/` | DroidBot + Humanoid inference | `humanoid` |
| QTesting | `builtin/qtesting/` | Docker-based | `qtesting` |

Two tools live outside rv-tools, each in its own workspace module: the LLM-driven tool (`rvagent`, module `rvagent-tool`) and APE-RV (`aperv`, module `aperv-tool`). They are not built-ins. rv-platform's `_register_external_tools()` registers both on import. `RVAgentTool` wraps `rv-agent`'s `AgentFactory` and `RVAgent`, mapping platform `Task`/`App` objects to `RVAgentConfig`. `ApeRVTool` wraps the APE-RV binary (`aperv` spec).

Because rv-platform imports both plugin modules, its `pyproject.toml` SHALL declare both `rvagent-tool` and `aperv-tool`, each in `dependencies` and as a workspace source in `[tool.uv.sources]` (INV-TOOL-26). A plugin module SHALL NOT declare rv-tools. Both subclass `AbstractTool` and use `ToolSpec` from `rv-android-core` (`rv_android_core.tools.abstract_tool`), and neither imports `rv_tools`. `rvagent-tool` declares `rv-android-core` and `rv-agent`; `aperv-tool` declares `rv-android-core`. A declared edge that no module imports makes the workspace graph state a coupling that does not exist, and the edge from rv-platform to `aperv-tool` would otherwise be an import the graph does not show.

ARES and QTesting are Docker-based tools that execute via `docker run` commands built by `_build_ares_command()` and `_build_qtesting_command()` respectively. Unlike other tools (Monkey, DroidBot, APE) that run via ADB shell commands or local scripts, these tools spawn a separate Docker container for each execution.

In standalone mode (developer workstation), the spawned container uses `--network host` to share the host's network namespace and reach the emulator at `localhost:5554`. In production Docker deployment (rvandroid container), the spawned container MUST share the parent container's network namespace via `--network container:$(hostname)` (INV-TOOL-15) to reach the emulator at `localhost:5554`.

The Docker socket (`/var/run/docker.sock`) MUST be mounted into the rvandroid container for Docker-based tools to function. Without this mount, `docker run` commands fail because there is no Docker daemon available inside the container. The Docker CLI binary is installed in the tools Docker image layer (`docker/tools/Dockerfile`).

ARES and QTesting images (`phtcosta/ares:latest`, `phtcosta/qtesting:latest`) MUST be pre-built on the Docker host before running experiments that use these tools. They are NOT declared as services in `docker-compose.yml` — they are spawned on-demand at runtime by each rvandroid container. Only Humanoid is declared as a shared service in the compose files because it operates as a REST server that multiple rvandroid containers connect to over the network.

#### Scenario: Monkey tool executes with configured parameters

- **WHEN** a `MonkeyTool` instance is created and configured with variant `"default"` (event_count=1000, throttle=0)
- **AND** `execute(task, app)` is called with `app.package_name="com.example.app"` and `task.config.timeout=60`
- **THEN** the tool MUST build an ADB command: `adb -s <device_id> shell monkey -v -v --ignore-security-exceptions -p com.example.app <event_count>`
- **AND** the command MUST have a timeout of 60 seconds
- **AND** stdout and stderr MUST be redirected to `task.result.trace_file`

#### Scenario: DroidBot tool validates policy configuration

- **WHEN** `DroidBotTool.configure()` is called with `config={"policy": "invalid_policy"}`
- **THEN** a `ConfigurationError` MUST be raised with a message listing available policies
- **AND** the tool MUST NOT be left in a partially configured state

- **WHEN** `DroidBotTool.configure()` is called with `config={"policy": "dfs_greedy", "count": 10000000000}`
- **THEN** `self.config["policy"]` MUST equal `"dfs_greedy"`
- **AND** `self.config["count"]` MUST equal `10000000000`

#### Scenario: Tool timeout is handled as expected behavior

- **WHEN** a tool's `execute_tool_specific_logic()` raises `RVCommandTimeoutError` with `timeout_seconds=300`
- **THEN** `AbstractTool.execute()` MUST raise `RVToolTimeoutError` with `tool_name` and `timeout_seconds=300`
- **AND** the timeout MUST be logged at INFO level (not ERROR)
- **AND** the calling code (rv-platform `ToolExecutionComponent`) MUST treat this as successful completion

#### Scenario: RVAgent tool maps platform context to agent configuration

- **WHEN** `RVAgentTool` is configured with variant `"pure_algorithm"` and `execute_tool_specific_logic(task, app)` is called
- **THEN** `build_agent_config_dict()` MUST produce a dictionary with `agent_mode="pure_algorithm"` and `package_name=app.package_name`
- **AND** `timeout` MUST come from `task.config.timeout`, not from the variant configuration
- **AND** if `task.static_data` is available, it MUST be passed to `AgentFactory.create_agent()`

#### Scenario: Process cleanup after tool execution

- **WHEN** `MonkeyTool.execute()` completes successfully
- **THEN** `kill_related_processes("com.android.commands.monkey")` MUST be called
- **AND** matching processes on the device MUST be terminated via `adb shell kill`
- **AND** any failure during process cleanup MUST be logged as a warning but MUST NOT cause the execution to fail

#### Scenario: Circuit breaker prevents repeated failing commands

- **WHEN** `_execute_and_check_command()` is called and the command returns a non-zero exit code
- **THEN** `circuit_breaker.record_failure()` MUST be called
- **AND** `RVToolExecutionError` MUST be raised with the tool name and error details

- **WHEN** the circuit breaker is in the OPEN state due to consecutive failures
- **THEN** `_execute_and_check_command()` MUST raise `CircuitBreakerOpenError` without executing the command

#### Scenario: ARES Command Includes Network Flag Inside Docker

- **WHEN** `AresTool._build_ares_command()` is called
- **AND** the code is running inside a Docker container (`/.dockerenv` exists)
- **THEN** the generated `docker run` command MUST include `--network container:<hostname>` where `<hostname>` is `socket.gethostname()` (which returns the container ID inside Docker)
- **AND** the `--network` flag MUST appear before the Docker image name in the argument list
- **AND** all other command arguments (volumes, environment variables, ARES-specific flags) MUST remain unchanged

#### Scenario: QTesting Command Includes Network Flag Inside Docker

- **WHEN** `QTestingTool._build_qtesting_command()` is called
- **AND** the code is running inside a Docker container (`/.dockerenv` exists)
- **THEN** the generated `docker run` command MUST include `--network container:<hostname>` where `<hostname>` is `socket.gethostname()`
- **AND** the `--network` flag MUST appear before the Docker image name in the argument list
- **AND** all other command arguments MUST remain unchanged

#### Scenario: Host Network Outside Docker

- **WHEN** `AresTool._build_ares_command()` or `QTestingTool._build_qtesting_command()` is called
- **AND** the code is NOT running inside a Docker container (`/.dockerenv` does not exist)
- **THEN** the generated `docker run` command MUST include `--network host` so the sibling container can reach the emulator at `localhost:5554`
- **AND** no `--network container:` flag MUST be used (container networking is only for Docker-in-Docker)

#### Scenario: rv-platform declares every external plugin it registers

- **WHEN** `.claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py` is run from the rv-android root
- **THEN** the `rv-platform` entry MUST list `aperv-tool` and `rvagent-tool` under `declared`
- **AND** its `undeclared` line MUST be `-`
- **AND** the `aperv-tool` and `rvagent-tool` entries MUST NOT list `rv-tools` under `declared`

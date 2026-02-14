## MODIFIED Requirements

### Requirement: External Tool Support (FR19, NFR02)

The system MUST support 8 third-party Android test generation tools, each implemented as a class extending `AbstractTool` in the `rv_tools.builtin` package. Each tool implementation follows a consistent pattern: a class-level `TOOL_SPEC` attribute created via `ToolSpec.create_builtin_spec()`, a parameterless `__init__()` that delegates to `super().__init__(name, description, process_pattern)`, and implementations of `get_tool_spec()`, `get_variants()`, `configure()`, and `execute_tool_specific_logic()`.

Tools execute via the template method in `AbstractTool.execute()`: it calls `execute_tool_specific_logic()`, then `kill_related_processes()`. If `RVCommandTimeoutError` is raised, it is converted to `RVToolTimeoutError` (expected behavior). Tools build their specific commands (ADB shell commands, CLI scripts, etc.) and execute them via `_execute_and_check_command()`, which integrates the circuit breaker pattern for resilience against consistently failing commands.

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

The LLM-driven tool (`rvagent`) lives in a separate module (`rvagent-tool`) and is registered via `ExperimentToolRegistry`, not as a built-in. Its `RVAgentTool` wraps `rv-agent`'s `AgentFactory` and `RVAgent`, mapping platform `Task`/`App` objects to `RVAgentConfig`.

ARES and QTesting are Docker-based tools that execute via `docker run` commands built by `_build_ares_command()` and `_build_qtesting_command()` respectively. Unlike other tools (Monkey, DroidBot, APE) that run via ADB shell commands or local scripts, these tools spawn a separate Docker container for each execution.

In standalone mode (developer workstation), the spawned container uses `--network host` to share the host's network namespace and reach the emulator at `localhost:5554`. In production Docker deployment (rvandroid container), the spawned container MUST share the parent container's network namespace via `--network container:$(hostname)` (INV-TOOL-15) to reach the emulator at `localhost:5554`.

#### Scenario: DroidBot Tool Invocation

- **WHEN** DroidBot is executed via `execute_tool_specific_logic(task, app)`
- **THEN** the tool MUST build a command using `uv run droidbot` with the configured policy, device serial, APK path, output directory, and timeout
- **AND** MUST execute the command via `_execute_and_check_command()`

#### Scenario: Tool Timeout Handling

- **WHEN** any tool execution exceeds the configured timeout
- **THEN** `RVCommandTimeoutError` MUST be raised by the command execution layer
- **AND** the tool MUST convert it to `RVToolTimeoutError`
- **AND** the task MUST be marked as COMPLETED (timeout is expected behavior, not a failure)

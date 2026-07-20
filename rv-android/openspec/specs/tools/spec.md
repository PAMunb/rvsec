# Specification: Tool Infrastructure

## Purpose

The Tool Infrastructure domain provides the plugin system, registry, factory, and device interaction layer that enable RV-Android to integrate diverse Android testing tools through a uniform interface. It spans two modules -- **rv-tools** (registry, factory, and 8 built-in tool implementations) and **rv-uiautomator** (shared device interaction components) -- and is consumed by rv-platform (task execution), rv-experiment (experiment orchestration), and rv-agent (LLM-driven exploration).

### Problem Addressed

RV-Android evaluates multiple Android test-generation tools (Monkey, DroidBot, APE, FastBot, ARES, DroidMate, Humanoid, QTesting) and an LLM-driven agent (rv-agent) in runtime verification experiments. Each tool has different invocation mechanisms (ADB shell commands, Python scripts, Docker containers, JAR files), configuration schemas, process patterns for cleanup, and supported variants (e.g., DroidBot offers 6 exploration policies). Without a unified abstraction, experiment orchestration code would contain tool-specific branching, making it difficult to add new tools or run multi-tool experiments.

### Design Decisions

1. **Singleton Registry**: `ToolRegistry` uses a class-level singleton (`_instance`) to ensure a single source of truth for registered tools. All modules that need tools -- rv-platform's `ToolExecutionComponent`, rv-experiment's CLI, CLI's `list-tools` command -- access the same instance via `ToolRegistry.get_instance()`. The registry provides `reset_instance()` for test isolation.

2. **Auto-Registration at Import**: When `rv_tools` is imported, `_register_builtin_tools()` iterates over `BUILTIN_TOOLS` (a list of 8 tool classes from `rv_tools.builtin`) and calls `registry.register_tool_class(tool_class)` for each. This means the 8 built-in tools are available immediately after `import rv_tools`. Registration failures are logged as warnings but do not block module import.

3. **External Tool Registration via rv-platform**: Tools that live outside rv-tools (rvagent in `rvagent-tool`) are registered by `_register_external_tools()` in rv-platform's `__init__.py` when that module is imported. The function checks `is_tool_registered("rvagent")` before attempting registration to ensure idempotency. This respects the module dependency hierarchy: rv-tools depends only on rv-android-core, while rvagent-tool depends on rv-agent + rv-tools.

4. **AbstractTool Contract**: All tools extend `AbstractTool` (defined in rv-android-core), which enforces a template method pattern: `execute()` calls `execute_tool_specific_logic()`, handles `RVCommandTimeoutError` (converting it to `RVToolTimeoutError` -- timeouts are expected behavior), performs process cleanup via `kill_related_processes()`, and delegates to `ErrorHandler` for other exceptions. This gives every tool consistent timeout handling and cleanup.

5. **Variant System**: Each tool defines named variants as dictionaries of configuration parameters. Variants are registered alongside the tool class in the registry. The factory resolves a variant by name, merges it with any additional parameters from the experiment configuration, and calls `tool.configure(merged_config)`. This enables the tool specification DSL (`droidbot:dfs_greedy@count=5000`).

6. **UIAdapter Abstraction**: `UIAdapter` (in rv-uiautomator) defines a framework-agnostic interface for device operations. Currently, only `UIAutomator2Adapter` implements it (using the `uiautomator2` Python library). This abstraction enables future alternative backends without changing higher-level code.

7. **Action Executor Pattern**: `UIAutomatorActionExecutor` translates `GeneratedAction` objects (from LLM or algorithm) into concrete `UIAdapter` method calls. It dispatches on `WidgetEventType` (CLICK, LONG_CLICK, TEXT_CHANGE, SCROLL, BACK) and supports custom coordinate-based actions from vision strategies.

8. **State Format Conversion**: `StateConverter` bridges the UIAutomator state format (`xml`, `current_activity`, `current_package`) and DroidBot's expected format (`view_tree`/`hierarchy`, `activity`, `package_name`). This is documented as a temporary solution; the long-term plan is a typed `DeviceState` model.

### Data Models

```
ToolSpec (BaseValidatedModel):
  name: str               # Tool identifier used in registry keys and CLI
  description: str        # Human-readable tool description
  url: str                # Repository or documentation URL
  version: str            # Version string (default "1.0.0")
  process_pattern: str?   # Pattern for kill_related_processes() cleanup (nullable)

ToolConfig (BaseValidatedModel, defined in rv-android-core):
  name: str               # Tool identifier (must match registry key)
  variant: str            # Variant name (singular, default "default")
  parameters: Dict        # Parameter overrides

AbstractTool (ABC):
  name: str               # Tool identifier (from ToolSpec.name)
  description: str        # Tool description (from ToolSpec.description)
  process_pattern: str    # Process pattern for cleanup
  config: Dict            # Resolved configuration (set by configure())
  logger: Logger          # Structured logger
  error_handler: ErrorHandler
  circuit_breaker: CommandCircuitBreaker

UIAdapter (ABC):
  (no state -- pure interface)
  Methods: connect, get_ui_state, click, input_text, long_click,
           swipe, press_back, press_home, take_screenshot,
           launch_app, stop_app

UIAutomator2Adapter (UIAdapter):
  device_id: str          # Target device (default "emulator-5554")
  device: u2.Device?      # UIAutomator2 device handle
  connected: bool         # Connection status
```

### Component Interactions

```
Module Import
     |
     v
rv_tools.__init__ --> _register_builtin_tools()
     |                          |
     |                 For each BUILTIN_TOOLS[]:
     |                          |
     v                          v
ToolRegistry.get_instance() <-- register_tool_class(tool_class)
     |                              |
     |                     tool_class.get_tool_spec() --> ToolSpec
     |                     tool_class.get_variants()  --> Dict[str, Dict]
     |                              |
     |                     register_variant() for each variant
     v
rv_platform.__init__ --> _register_external_tools()
     |                          |
     |                 is_tool_registered("rvagent")? --> skip if True
     |                          |
     |                 import RVAgentTool from rvagent_tool
     |                 register_tool_class(RVAgentTool)
     v
ToolFactory.create_tool(tool_config)
     |
     +-- Resolve tool_class from registry
     +-- Get variant_config from registry
     +-- Merge with tool_config.parameters
     +-- Create tool_class() instance
     +-- Call tool.configure(merged_config)
     v
Configured AbstractTool instance
     |
     v
TaskExecutor (rv-platform) --> tool.execute(task, app)
     |
     +-- execute_tool_specific_logic(task, app) [tool-specific]
     +-- kill_related_processes(process_pattern) [cleanup]
     +-- ErrorHandler for exceptions
```

```
UIAutomator2Adapter                 UIAutomatorActionExecutor
        |                                     |
        v                                     v
  u2.connect(device_id)              execute(action, adapter)
  device.dump_hierarchy()                |
  device.click(x, y)             dispatch on WidgetEventType:
  device.send_keys(text)           CLICK  -> adapter.click(x, y)
  device.long_click(x, y, dur)    TEXT_CHANGE -> adapter.click + adapter.input_text
  device.swipe(...)               LONG_CLICK -> adapter.long_click(x, y, dur)
  device.press("back"/"home")     SCROLL -> adapter.swipe(x1, y1, x2, y2)
  device.screenshot(path)         BACK   -> adapter.press_back()
  device.app_start(package)       custom -> adapter.click(coords)
  device.app_stop(package)
```

### Relationship with Other Domains

**Consumers:**
- **rv-platform**: `ToolFactory.create_tool()` in `ToolExecutionComponent` to instantiate tools for task execution. Uses `ToolRegistry` for tool validation and discovery.
- **rv-experiment**: Uses `ToolRegistry.get_instance()` from rv-tools directly. CLI parses tool specification DSL and generates `ToolConfig` objects.
- **rv-agent**: Uses `UIAutomator2Adapter` (via rv-uiautomator) for device interaction. `UIAutomatorActionExecutor` executes generated actions. `RVAgentTool` (in rvagent-tool module) wraps rv-agent as an `AbstractTool`.

**Dependencies:**
- **rv-android-core**: Provides `AbstractTool`, `ToolSpec`, `Command`, `CommandResult`, `ErrorHandler`, `LoggingManager`, `PerformanceMonitor`, `BaseValidatedModel`, domain models (`Task`, `App`, `WidgetEventType`), and exception classes.
- **rv-screen-parser**: rv-uiautomator depends on it for UI parsing capabilities.
- **uiautomator2**: Python library for device communication (external dependency).
- **pillow**: Image processing for screenshot management (external dependency).

## Data Contracts

### Input

- `tool_config: ToolConfig` -- Tool name, variant, and parameter overrides. Provided by rv-platform from `PlatformConfig.tools` or by rv-experiment's CLI DSL parser.
- `task: Task` -- Task context containing execution timeout, device serial, result paths, and static analysis data. Provided by rv-platform's `TaskExecutor`.
- `app: App` -- Application under test with `package_name`, `path` (APK file), and metadata. Provided by rv-platform's APK discovery.
- `device_id: str` -- Android device identifier (default `"emulator-5554"`). Provided by emulator management or user.

### Output

- `tool_instance: AbstractTool` -- Configured tool instance ready for execution. Consumed by rv-platform's `ToolExecutionComponent`.
- `ui_state: Dict[str, Any]` -- Device UI state containing `xml` (hierarchy), `current_activity`, `current_package`, `device_info`, `timestamp`. Consumed by rv-agent and rv-screen-parser.
- `execution_result: bool` -- Success/failure of action execution. Consumed by rv-agent's execute_node.
- `registry_info: Dict[str, Any]` -- Registry statistics and metadata including `total_tools`, `total_variants`, `tools` list, `variants_by_tool` mapping. Consumed by CLI and diagnostics.

### Side-Effects

- **Device**: UIAutomator2Adapter performs clicks, swipes, text input, button presses, app launches/stops, and screenshot captures on the connected Android device/emulator.
- **File System**: Screenshot files written to configurable directory (`./screenshots/` default). Tool trace files written to `task.result.trace_file` during execution.
- **Processes**: `kill_related_processes()` terminates device-side processes matching the tool's `process_pattern` via `adb shell kill`.
- **Logging**: All operations emit structured log entries via `LoggingManager` with component context.

### Error

- `ToolNotFoundError` -- Raised when requesting a tool or variant that is not registered in the registry.
- `ToolRegistrationError` -- Raised when tool class registration fails (e.g., `get_tool_spec()` or `get_variants()` throws).
- `ConfigurationError` -- Raised when tool configuration is invalid (e.g., missing required parameter, invalid variant name, invalid DroidBot policy).
- `ToolCreationError` -- Raised when `ToolFactory.create_tool()` fails during instance creation.
- `RVToolTimeoutError` -- Raised when tool execution exceeds the configured timeout. This is expected behavior and is handled gracefully (task is marked as completed, not failed).
- `RVToolExecutionError` -- Raised when a tool command returns a non-zero exit code.
- `CircuitBreakerOpenError` -- Raised when the circuit breaker blocks command execution after consecutive failures.

## Invariants

- **INV-TOOL-01**: The `ToolRegistry` singleton MUST return the same instance across all callers within a process. `ToolRegistry.get_instance()` MUST always return a non-None `ToolRegistry` object. `reset_instance()` MUST only be used in test code.

- **INV-TOOL-02**: Every registered tool MUST have at least a `"default"` variant. The `get_variants()` classmethod MUST return a dictionary containing the key `"default"`.

- **INV-TOOL-03**: Tool names MUST be unique within the registry. Registering a tool with an existing name MUST replace the previous registration and log a warning. The registry MUST NOT contain duplicate tool names.

- **INV-TOOL-04**: A `ToolSpec` MUST have non-empty `name`, `description`, `url`, and `version` fields. These fields are validated by Pydantic via the `@validated_model(['name', 'description', 'url', 'version'])` decorator.

- **INV-TOOL-05**: `ToolFactory.create_tool()` MUST call `tool.configure(config)` before returning the tool instance. A tool instance returned by the factory MUST have its configuration applied.

- **INV-TOOL-06**: `AbstractTool.execute()` MUST convert `RVCommandTimeoutError` to `RVToolTimeoutError`. Tool timeouts MUST NOT be treated as errors -- they indicate the tool ran for the full allocated time.

- **INV-TOOL-07**: `AbstractTool.execute()` MUST call `kill_related_processes()` after successful execution. Process cleanup MUST NOT raise exceptions that propagate to the caller (cleanup errors are logged as warnings).

- **INV-TOOL-08**: Built-in tool auto-registration MUST NOT fail the `rv_tools` module import. Any individual tool registration failure MUST be logged as a warning and skipped.

- **INV-TOOL-09**: `UIAutomator2Adapter` MUST check `self.connected` and `self.device is not None` before every device operation. If the device is not connected, the operation MUST return `False` (for actions) or `{}` (for state capture) without raising an exception.

- **INV-TOOL-10**: `UIAutomatorActionExecutor.execute()` MUST dispatch actions based on `WidgetEventType`. Unknown action types MUST return `False` and log a warning. The executor MUST NOT raise exceptions to the caller -- all errors MUST be caught and returned as `False`.

- **INV-TOOL-11**: `StateConverter.uiautomator_to_droidbot()` MUST map `xml` to both `view_tree` and `hierarchy`, `current_activity` to `activity`, and `current_package` to `package_name`. The converted state MUST include `_conversion_metadata` with source and target format identifiers.

- **INV-TOOL-12**: External tool registration in rv-platform MUST be idempotent. The `_register_external_tools()` function MUST check `is_tool_registered("rvagent")` before calling `register_tool_class()`. Multiple imports of `rv_platform` MUST NOT produce duplicate registrations.

- **INV-TOOL-13**: Variant configuration returned by `get_variant_config()` MUST be a copy of the stored configuration, not a reference. Modifications to the returned dictionary MUST NOT affect the registry's internal state.

- **INV-TOOL-14**: `UIAutomator2Adapter.connect()` MUST configure UIAutomator2 settings (`wait_timeout`) after successful connection. The `_configure_uiautomator_settings()` method MUST be called before returning `True`.

- **INV-TOOL-15**: When ARES or QTesting tools build their Docker `run` command inside a Docker container (detected by the presence of `/.dockerenv`), the command MUST include `--network container:<hostname>` where `<hostname>` is the current container's ID obtained via `socket.gethostname()`. This flag makes the sibling container (ARES/QTesting) share the parent container's network namespace, allowing it to reach the emulator at `localhost:5554` without any network configuration changes in the ARES/QTesting code or Dockerfiles. When running outside Docker (`/.dockerenv` does not exist), the command MUST use `--network host` so the sibling container shares the host's network namespace and can reach the emulator at `localhost:5554`.
## Requirements
### Requirement: Tool Registration and Factory System (FR18, NFR02)

The tool system MUST provide a centralized registry and factory for all Android testing tools. `ToolRegistry` maintains a singleton registry of tool classes and their variant configurations. `ToolFactory` creates configured tool instances from `ToolConfig` objects.

The factory resolution flow in `ToolFactory.create_tool()` is:
1. Resolve `tool_class` from registry using `tool_config.name`.
2. Get `variant_config` from registry using `tool_config.name` and `tool_config.variant`.
3. Merge variant_config with `tool_config.parameters` (parameters override variant values).
4. Create `tool_class()` instance and call `tool.configure(merged_config)`.

#### Scenario: Factory creates configured tool from ToolConfig

- **WHEN** `ToolFactory.create_tool(tool_config)` is called with `tool_config.name="droidbot"`, `tool_config.variant="dfs_greedy"`, `tool_config.parameters={"count": 5000}`
- **THEN** the factory MUST return a `DroidBotTool` instance
- **AND** the instance MUST have `config["policy"] == "dfs_greedy"` (from variant)
- **AND** the instance MUST have `config["count"] == 5000` (from parameters override)
- **AND** the instance MUST have `config["ignore_ad"] == True` (from variant defaults)

#### Scenario: Factory rejects invalid tool or variant

- **WHEN** `ToolFactory.create_tool(tool_config)` is called with `tool_config.name="nonexistent_tool"`
- **THEN** the factory MUST raise `ConfigurationError` with a message indicating the tool is not found
- **AND** no tool instance MUST be created

- **WHEN** `ToolFactory.create_tool(tool_config)` is called with `tool_config.name="droidbot"`, `tool_config.variant="invalid_variant"`
- **THEN** the factory MUST raise `ConfigurationError` with a message indicating the variant is invalid

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

The LLM-driven tool (`rvagent`) lives in a separate module (`rvagent-tool`) and is registered via rv-platform's `_register_external_tools()` on import, not as a built-in. Its `RVAgentTool` wraps `rv-agent`'s `AgentFactory` and `RVAgent`, mapping platform `Task`/`App` objects to `RVAgentConfig`.

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

### Requirement: Per-Tool Variant System (FR20)

Each tool MUST support multiple named variants representing different operational modes and parameter sets. Variants provide a way to reference complete tool configurations by name in experiment specifications, CLI arguments, and configuration files. The variant system enables the tool specification DSL format: `tool_name:variant_name@param=value`.

Variants are defined by each tool's `get_variants()` classmethod, which returns a dictionary mapping variant names to configuration parameter dictionaries. Every tool MUST include a `"default"` variant. Variants are registered in the `ToolRegistry.variants` data structure as a three-level dictionary: `tool_name -> variant_name -> config_dict`.

The variant resolution flow in `ToolFactory.create_tool()` is:
1. If `variant_name` is provided and not `"default"`, validate it exists via `registry.validate_tool_variant()`.
2. Get the variant configuration via `registry.get_variant_config()` (returns a copy).
3. Merge with `tool_config.parameters` (parameters override variant values).
4. Call `tool.configure(merged_config)` on the new instance.

The following tools and their variants are registered in the current system:

| Tool | Variants |
|------|----------|
| monkey | default, fast, stress |
| droidbot | default, dfs_greedy, bfs_greedy, dfs_naive, bfs_naive, random |
| ape | default, sata, bfs, dfs, random |
| fastbot | conservative, aggressive, balanced |
| ares | default, debug, fast |
| droidmate | default, systematic, quick, research |
| humanoid | default, visual, nlp, hybrid |
| qtesting | default, qlearning, dqn, ddqn |
| rvagent | default, multimode, pure_algorithm, llm_only, thorough |

#### Scenario: Listing variants for a registered tool

- **WHEN** `registry.get_tool_variants("droidbot")` is called
- **THEN** the result MUST contain at least `["default", "dfs_greedy", "bfs_greedy", "dfs_naive", "bfs_naive", "random"]`
- **AND** the order of variant names is not significant

#### Scenario: Variant configuration contains complete parameters

- **WHEN** `registry.get_variant_config("droidbot", "dfs_greedy")` is called
- **THEN** the returned dictionary MUST contain `policy="dfs_greedy"`, `count=10000000000`, `interval=3`, `ignore_ad=True`
- **AND** the dictionary MUST contain all parameters needed for `DroidBotTool.configure()` to succeed

#### Scenario: Additional parameters override variant values

- **WHEN** `ToolFactory.create_tool()` is called with variant `"dfs_greedy"` (which has `count=10000000000`) and `parameters={"count": 500}`
- **THEN** the final configuration passed to `configure()` MUST have `count=500`
- **AND** all other variant parameters MUST be preserved (e.g., `policy="dfs_greedy"`, `interval=3`)

#### Scenario: Validating a tool variant combination

- **WHEN** `registry.validate_tool_variant("monkey", "fast")` is called
- **THEN** the result MUST be `True`

- **WHEN** `registry.validate_tool_variant("monkey", "nonexistent")` is called
- **THEN** the result MUST be `False`

#### Scenario: RVAgent variants map to execution modes

- **WHEN** `registry.get_variant_config("rvagent", "pure_algorithm")` is called
- **THEN** the returned dictionary MUST contain `agent_mode="pure_algorithm"` and `strategy="rvagent"`
- **AND** the dictionary MUST NOT contain `llm_probability` (not applicable to pure_algorithm mode)

- **WHEN** `registry.get_variant_config("rvagent", "multimode")` is called
- **THEN** the returned dictionary MUST contain `agent_mode="multimode"`, `llm_probability=0.7`, `strategy="rvagent"`

#### Scenario: Tool specification DSL parsing

- **WHEN** the CLI receives the tool specification string `"droidbot:dfs_greedy@count=5000"`
- **THEN** the parser MUST extract `name="droidbot"`, `variant="dfs_greedy"`, `parameters={"count": "5000"}`
- **AND** the resulting `ToolConfig` MUST be usable by `ToolFactory.create_tool()`

- **WHEN** the CLI receives `"monkey,droidbot:bfs_greedy,rvagent:pure_algorithm"`
- **THEN** the parser MUST produce 3 `ToolConfig` objects, one for each tool specification

### Requirement: Device Interaction Abstraction (UIAdapter and UIAutomator2)

The rv-uiautomator module MUST provide a framework-agnostic device interaction interface (`UIAdapter`) with a concrete UIAutomator2 implementation (`UIAutomator2Adapter`). This abstraction is consumed by rv-agent for LLM-driven exploration and by other tools that need direct device interaction.

The `UIAdapter` abstract class defines 11 methods covering the fundamental device interactions needed for Android testing: `connect()`, `get_ui_state()`, `click()`, `input_text()`, `long_click()`, `swipe()`, `press_back()`, `press_home()`, `take_screenshot()`, `launch_app()`, `stop_app()`.

`UIAutomator2Adapter` implements this interface using the `uiautomator2` Python library (`import uiautomator2 as u2`). It wraps `u2.connect()` for device connection and delegates all operations to the device handle. Every operation is wrapped with `@ErrorHandler.handle_errors()` for consistent error management and `PerformanceMonitor.measure_time()` for execution timing.

The module also provides supporting utilities:
- **DeviceManager**: ADB-based device discovery (`adb devices`), connection verification, and device property retrieval.
- **ScreenshotManager**: Screenshot file path generation, image optimization (PNG to JPEG with quality control), validation, and cleanup of old files.
- **StateConverter**: Converts UIAutomator state to DroidBot-compatible format.
- **UIAutomatorActionExecutor**: Translates `GeneratedAction` objects to `UIAdapter` method calls.

Performance constants are tuned for headless mode execution: `ACTION_EXECUTION_DELAY=0.3s`, `TEXT_INPUT_DELAY=0.2s`, `DEFAULT_SWIPE_DURATION=0.25s`, `WAIT_FOR_IDLE_TIMEOUT=5.0s`.

#### Scenario: Connecting to an Android emulator

- **WHEN** `UIAutomator2Adapter.connect("emulator-5554")` is called
- **THEN** the adapter MUST call `u2.connect("emulator-5554")` and request `device.info`
- **AND** if `device.info` returns a non-None value, `connected` MUST be set to `True`
- **AND** `_configure_uiautomator_settings()` MUST be called to set `wait_timeout=5.0`
- **AND** the method MUST return `True`

- **WHEN** `u2.connect()` raises an exception
- **THEN** `connected` MUST remain `False`
- **AND** the method MUST return `False`
- **AND** the error MUST be logged

#### Scenario: Capturing UI state from device

- **WHEN** `get_ui_state()` is called on a connected adapter
- **THEN** the returned dictionary MUST contain keys `device_info`, `current_package`, `current_activity`, `xml`, `timestamp`
- **AND** `xml` MUST contain the UIAutomator XML hierarchy string from `device.dump_hierarchy()`
- **AND** `current_package` and `current_activity` MUST come from `device.app_current()`

- **WHEN** `get_ui_state()` is called on a disconnected adapter
- **THEN** the method MUST return an empty dictionary `{}`
- **AND** a warning MUST be logged

#### Scenario: Executing a click action via UIAutomatorActionExecutor

- **WHEN** `executor.execute(action, adapter)` is called with `action.action_type="click"` and `action.coordinates=[540, 1200]`
- **THEN** `adapter.click(540, 1200)` MUST be called
- **AND** the method MUST return `True` if the click succeeded

- **WHEN** `executor.execute(action, adapter)` is called with an action that has no coordinates
- **THEN** the executor MUST return `False`
- **AND** an error MUST be logged

#### Scenario: State format conversion

- **WHEN** `StateConverter.uiautomator_to_droidbot(ui_state)` is called with `ui_state={"xml": "<hierarchy>...</hierarchy>", "current_activity": ".MainActivity", "current_package": "com.example"}`
- **THEN** the result MUST contain `view_tree="<hierarchy>...</hierarchy>"`, `hierarchy="<hierarchy>...</hierarchy>"`, `activity=".MainActivity"`, `package_name="com.example"`
- **AND** `_conversion_metadata` MUST be present with `source_format="uiautomator"` and `target_format="droidbot"`

#### Scenario: Screen hash computation

- **WHEN** `StateConverter.compute_screen_hash(state)` is called with a state containing a hierarchy XML
- **THEN** the returned hash MUST be a 16-character hexadecimal string (SHA-256 truncated to `SCREEN_HASH_LENGTH`)
- **AND** calling the method twice with the same state MUST return the same hash

- **WHEN** the state has no hierarchy/XML but has activity and package
- **THEN** the hash MUST be computed from `"{package}/{activity}"`

#### Scenario: Device discovery via DeviceManager

- **WHEN** `DeviceManager.get_available_devices()` is called and `adb devices` lists `emulator-5554  device`
- **THEN** the result MUST include `"emulator-5554"`
- **AND** devices with status other than `"device"` (e.g., `"offline"`, `"unauthorized"`) MUST be excluded

### Requirement: Layer Purity for Tool Configuration (NFR01, NFR02)

Tool plugins (Layer 2) MUST receive all configuration values via the `AbstractTool.configure(config: Dict[str, Any])` contract established by `rv-android-core`. They MUST NOT read environment variables, configuration files, or any other external state during initialization or execution. The `config` dictionary is assembled at Layer 5 (by `rv-experiment`) and forwarded through the entries of `rv-platform.PlatformConfig.tools` (each a `ToolConfig` carrying a `parameters: Dict[str, Any]`) to `ToolFactory.create_tool` (in `rv_tools.registry.factory`, L2), which merges variant defaults with `tool_config.parameters` and calls `configure()`.

This rule has three concrete consequences:

1. **No `os.environ` reads in `rv-tools/src/rv_tools/builtin/`**. The `RV_HUMANOID_URL` read at `rv-tools/.../humanoid/tool.py:89` is the canonical example of a violation removed by this change. Any equivalent read in other tool plugins MUST also be removed.
2. **Tool configuration keys are documented**. Each tool's `configure()` MUST declare which keys it expects (via Pydantic model or explicit `config["..."]` access). The set of declared keys forms part of the tool's public contract.
3. **Tools cannot probe the environment as a fallback**. Even if `config` lacks a value, the tool MUST raise rather than silently fall back to `os.environ`. The L5 resolver is responsible for providing defaults.

#### Scenario: Humanoid tool uses variant default when L5 does not override

- **WHEN** `rv-experiment` does NOT set `RV_HUMANOID_URL` and does NOT pass `--humanoid-url`
- **AND** the factory builds `tool_config = ToolConfig(name="humanoid", variant="default", parameters={})`
- **AND** `ToolFactory.create_tool(tool_config)` merges `{**variant_defaults, **{}}` and calls `tool.configure({"policy": "dfs_greedy", "count": 10_000_000_000, "ignore_ad": True, "humanoid_url": "127.0.0.1:50405"})`
- **THEN** `self.url` MUST equal `"127.0.0.1:50405"` (the variant default carried in `get_variants()["default"]["humanoid_url"]`)
- **AND** the tool source file MUST contain no `os.environ` reads or `ENV_*` imports
- **AND** running `grep -rn 'ENV_HUMANOID_URL\|os\.environ' modules/rv-tools/src/rv_tools/builtin/humanoid/` MUST return 0 hits

#### Scenario: L5-resolved URL overrides variant default

- **WHEN** `rv-experiment` resolves `RV_HUMANOID_URL=http://humanoid:50405` from the environment (or from `--humanoid-url`)
- **AND** the factory builds `tool_config = ToolConfig(name="humanoid", variant="default", parameters={"humanoid_url": "http://humanoid:50405"})`
- **AND** `ToolFactory.create_tool(tool_config)` merges `{**variant_defaults, "humanoid_url": "http://humanoid:50405"}` (parameters wins because it merges last)
- **THEN** `self.url` MUST equal `"http://humanoid:50405"`
- **AND** at no point does the platform or the tool read `RV_HUMANOID_URL` directly from `os.environ`

#### Scenario: Tool fails fast for keys without variant default and without L5 injection

- **WHEN** a hypothetical tool plugin declares no variant default for required key `K` and L5 also injects no `K`
- **AND** `tool.configure(merged_dict)` accesses `merged_dict["K"]`
- **THEN** the tool MUST raise `KeyError` naming `K` (no `os.environ` fallback at L2)
- **AND** the fix is to add `K` to `get_variants()` defaults or have L5 inject it, never to read env at L2

#### Scenario: Lint enforces no env reads in tool plugins (all three plugin trees)

- **WHEN** a developer reintroduces `os.environ.get(ENV_X)`, `os.getenv(ENV_X)`, or `os.environ["RV_X"]` anywhere under `modules/rv-tools/src/rv_tools/builtin/`, `modules/aperv-tool/src/`, or `modules/rvagent-tool/src/`
- **THEN** the CI lint MUST fail naming the offending file, line, and plugin tree
- **AND** the message MUST cite `INV-TOOL-20` and `docs/rv_android_architecture.md` (Layer Purity rule)
- **AND** the lint MUST equally flag `dict(os.environ)` and `os.environ.copy()` in the same scope (environment leak via shallow copy)

### Requirement: Build ape-rv.jar from source in the image
The rvandroid image build SHALL compile the APE-RV binary from source and place the freshly built jar where `aperv-tool` resolves it, so the shipped jar always matches current `ape` source (and the current static-analysis JSON schema).

#### Scenario: Image built from scratch ships a source-compiled jar
- **WHEN** the rvandroid image is built from `docker/rvandroid/Dockerfile`
- **THEN** the Dockerfile clones `https://github.com/phtcosta/ape.git` (default branch, HTTPS, anonymous) AND runs `mvn package` AND copies `target/ape-rv.jar` to `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` inside the image
- **AND** the resulting `ape-rv.jar` is the compiled artifact, not the legacy committed binary
- **AND** the copied jar exists and is non-empty (build-time verifiable)

#### Scenario: Single-stage build using the base-image toolchain
- **WHEN** the ape build step runs in the image
- **THEN** it uses the toolchain already present in `phtcosta/rvandroid_tools:0.9.3` (`d8`, Maven, Git, JDK)
- **AND** no multi-stage builder is added
- **AND** the image tag is unchanged (the image is rebuilt in place)

### Requirement: No committed or bind-mounted jar dependency
The build and the repository SHALL NOT depend on a pre-committed `ape-rv.jar`, removing the drift that caused the stale-jar failure (legacy `reachesMop` vs gh60 `reachesTarget`).

#### Scenario: Committed jar removed and ignored
- **WHEN** this change is applied
- **THEN** the git-tracked `ape-rv.jar` under `modules/aperv-tool/src/aperv_tool/tools/aperv/` is deleted (backed up to `backup/` first)
- **AND** that directory's `.gitignore` ignores `ape-rv.jar`
- **AND** the deletion and the Dockerfile build step land in a single atomic commit (the jar otherwise enters the image via the `rvsec` clone, so neither half is safe alone)

#### Scenario: ape ref tracks the default branch
- **WHEN** the image is built at any time
- **THEN** the `ape` clone uses the repository default branch (current tip), with no build `ARG` and no pinned SHA


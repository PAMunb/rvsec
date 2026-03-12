# Specification: ApeRV Tool

## Purpose

`aperv-tool` is an rv-platform external tool module that wraps the enhanced APE-RV binary (`ape-rv.jar`) for integration into the rv-android experiment framework. APE (Ape Explores Apps, ICSE 2019) is a model-based Android UI exploration tool that uses adaptive random testing with a Widget Table Graph model. The enhanced version adds AndroidX ViewPager support and systematic OptionsMenu exploration (`MODEL_MENU` action).

The tool runs on the Android device using the `app_process` execution model — identical to how `rvsmart-tool` operates. The JAR is pushed to `/data/local/tmp/ape-rv.jar` via ADB, and execution is launched via `adb shell CLASSPATH=... /system/bin/app_process /system/bin com.android.commands.monkey.Monkey`. This execution model is necessary because APE requires internal Android APIs (`android.app.UiAutomationConnection`, `android.hardware.display.DisplayManagerGlobal`) that are inaccessible from the host via `adb shell monkey`.

The module is an optional uv workspace member. It is auto-discovered by `members = ["modules/*"]` in the root `pyproject.toml`. If not installed, rv-platform's `_register_external_tools()` catches the `ImportError` and logs a warning, allowing the platform to function normally with other tools.

Coverage metrics (method calls, MOP violations) are collected by the existing rv-android Python infrastructure via logcat `RVSEC-COV` tags — the same pipeline used by all other tools. No special output parsing is required.

The `sata_mop` variant is a placeholder for Phase 3 MOP-guided scoring. Until Phase 3 delivers the `MopData`/`MopScorer` Java components in `ape-rv.jar`, `sata_mop` behaves identically to `sata` (the `mop_data: None` value in the variant dict signals this intent).

## Data Contracts

### Input
- `task.config.device_id: str` — ADB device serial (default `"emulator-5554"`)
- `task.config.timeout: int` — exploration duration in seconds (default 300)
- `task.result.trace_file: str` — path where stdout from APE is written
- `self._tool_config["strategy"]: str` — APE exploration strategy from `configure()`

### Output
- `task.result.trace_file` — populated with APE stdout (binary write, `"wb"` mode)

### Side-Effects
- **[Device]**: `ape-rv.jar` pushed to `/data/local/tmp/ape-rv.jar` on the Android device
- **[Device]**: `ape.properties` pushed to `/data/local/tmp/ape.properties` if `_tool_config` is non-empty
- **[Logcat]**: APE writes `RVSEC-COV` log lines during execution (read by rv-android coverage infrastructure)

### Error
- `ConfigurationError` — raised by `configure()` when `strategy` key is absent or not in `["sata", "random", "bfs", "dfs"]`
- `RVToolExecutionError` — raised when `ape-rv.jar` cannot be found in any search path, or when an ADB push fails
- `RVToolTimeoutError` — raised when execution exceeds `task.config.timeout + 15` seconds (expected normal exit for exploration tools)

## Invariants

- **INV-APV-01**: `ApeRVTool` SHALL locate `ape-rv.jar` using `JarResolver` with search paths in priority order: (a) `os.path.dirname(__file__)` — module directory populated by `mvn install`, (b) `$RVSEC_HOME/ape/target/` — development Maven build, (c) `$TOOLS_DIR/aperv/` — manual placement. First match wins. If no path resolves, a `RVToolExecutionError` SHALL be raised listing all searched paths.

- **INV-APV-02**: `ApeRVTool.configure()` SHALL validate that the `strategy` key exists in `config` and its value is one of `["sata", "random", "bfs", "dfs"]`. An absent or invalid strategy SHALL raise `ConfigurationError` before any device interaction.

- **INV-APV-03**: `ApeRVTool` SHALL use device path `/data/local/tmp/ape-rv.jar` (not `/data/local/tmp/ape.jar`) to avoid collision with the builtin `ape` tool's device artifact.

- **INV-APV-04**: The `app_process` working directory SHALL be `/system/bin` (not `/data/local/tmp/`). The enhanced APE binary references system-level resources relative to its working directory during startup; using `/data/local/tmp/` causes startup failures. This intentionally diverges from the builtin `ape` tool, which uses `/data/local/tmp/` as working directory.

- **INV-APV-05**: `get_variants()` SHALL return a dict containing exactly the keys `["default", "sata", "sata_mop", "bfs", "random"]`. The `"default"` key SHALL map to the `sata` strategy (INV-TOOL-02 compliance).

- **INV-APV-06**: The `sata_mop` variant SHALL have `mop_data: None` in its configuration dict. Until Phase 3 delivers MOP-guided scoring in `ape-rv.jar`, `sata_mop` execution SHALL be identical to `sata`.

- **INV-APV-07**: `ApeRVTool.TOOL_SPEC.process_pattern` SHALL be `"com.android.commands.monkey"`. This is the same value used by the builtin `ape` tool. `AbstractTool.kill_related_processes()` uses this pattern to terminate device-side processes after execution. As a consequence, `ape` and `aperv` MUST NOT run concurrently on the same device — each cleanup would terminate the other's process. Experiments using `aperv` SHALL NOT include the builtin `ape` tool in the same run.

## Requirements

### Requirement: ApeRVTool Registration (FR18, FR19, NFR02)

`ApeRVTool` SHALL be registered as an external tool via rv-platform's `_register_external_tools()` function in `rv_platform/__init__.py`. Registration SHALL be idempotent: the function MUST check `registry.is_tool_registered("aperv")` before calling `registry.register_tool_class(ApeRVTool)`. If `aperv-tool` is not installed, the resulting `ImportError` SHALL be caught and logged as a warning; the platform SHALL continue operating normally. An unexpected exception during registration SHALL be logged as an error and SHALL NOT propagate.

#### Scenario: ApeRVTool registers on rv-platform import
- **WHEN** `import rv_platform` is executed and `aperv-tool` is installed
- **THEN** `ToolRegistry.get_instance().is_tool_registered("aperv")` SHALL return True
- **AND** `ToolRegistry.get_instance().get_tool_spec("aperv").name` SHALL be `"aperv"`

#### Scenario: Missing aperv-tool does not break rv-platform
- **WHEN** `import rv_platform` is executed and `aperv-tool` is NOT installed
- **THEN** rv-platform SHALL import successfully
- **AND** a warning log line SHALL be written containing `"aperv tool not available"`
- **AND** `ToolRegistry.get_instance().is_tool_registered("aperv")` SHALL return False

#### Scenario: Re-importing rv-platform does not double-register
- **WHEN** `import rv_platform` is executed twice
- **THEN** `ToolRegistry.get_instance()` SHALL contain exactly one registration for `"aperv"`

### Requirement: ApeRVTool Variants (FR20)

`ApeRVTool` SHALL define 5 variants. Every variant SHALL include a `"strategy"` key and a `"throttle_ms"` key. The `"default"` variant SHALL use strategy `"sata"` (INV-TOOL-02).

| Variant | strategy | throttle_ms | mop_data |
|---------|----------|-------------|----------|
| `default` | `"sata"` | 200 | — |
| `sata` | `"sata"` | 200 | — |
| `sata_mop` | `"sata"` | 200 | None |
| `bfs` | `"bfs"` | 200 | — |
| `random` | `"random"` | 200 | — |

#### Scenario: Creating tool with sata variant
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="aperv", variant="sata"))` is called
- **THEN** the factory SHALL return a configured `ApeRVTool` instance
- **AND** `tool._tool_config["strategy"]` SHALL equal `"sata"`

#### Scenario: Creating tool with sata_mop variant
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="aperv", variant="sata_mop"))` is called
- **THEN** the factory SHALL return a configured `ApeRVTool` instance
- **AND** `tool._tool_config["mop_data"]` SHALL be `None`

### Requirement: ApeRVTool Execution Contract (FR18, FR19)

`ApeRVTool.execute_tool_specific_logic(task, app)` SHALL perform the following steps in order:

1. Extract `device_serial` from `task.config.device_id` (default `"emulator-5554"`) and `timeout_seconds` from `task.config.timeout` (default 300).
2. Resolve `ape-rv.jar` path via `_resolve_jar_path()`.
3. Push JAR to `/data/local/tmp/ape-rv.jar` via `_push_file_to_device()`.
4. If `self._tool_config` is non-empty, generate and push `ape.properties` via `_push_properties()`.
5. Build the `app_process` command via `_build_main_command()`.
6. Execute the command, capturing stdout to `task.result.trace_file` opened in binary write mode.
7. If a `RVToolTimeoutError` is raised, log the timeout and re-raise.
8. Call `_check_empty_trace()` and log a warning if the trace file is empty.

The `app_process` invocation SHALL use:
```
adb -s <serial> shell CLASSPATH=/data/local/tmp/ape-rv.jar /system/bin/app_process /system/bin
  com.android.commands.monkey.Monkey -p <package_name>
  --running-minutes <max(1, timeout_seconds // 60)>
  --ape <strategy>
```

Command timeout SHALL be `timeout_seconds + 15` seconds.

#### Scenario: Successful APE execution
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `strategy="sata"`, timeout=60
- **THEN** `ape-rv.jar` SHALL be pushed to `/data/local/tmp/ape-rv.jar`
- **AND** the adb command SHALL include `--running-minutes 1` and `--ape sata`
- **AND** stdout SHALL be written to `task.result.trace_file`

#### Scenario: Execution timeout
- **WHEN** APE runs for longer than `timeout_seconds + 15` seconds
- **THEN** `RVToolTimeoutError` SHALL be raised and logged
- **AND** the timeout SHALL be re-raised to the caller

#### Scenario: Empty trace file
- **WHEN** APE execution completes but writes nothing to stdout
- **THEN** a warning log line SHALL contain `"aperv produced empty trace file"`

### Requirement: JAR Resolution (FR19)

`ApeRVTool._resolve_jar_path()` SHALL use `JarResolver.resolve_jar_path("ape-rv.jar", search_paths)` where `search_paths` is built as follows:

1. Always include `os.path.dirname(__file__)` (the module directory)
2. If `RVSEC_HOME` env var is set, append `$RVSEC_HOME/ape/target/`
3. If `TOOLS_DIR` env var is set, append `$TOOLS_DIR/aperv/`

The first existing path that contains `ape-rv.jar` wins. If no path resolves, `RVToolExecutionError` SHALL be raised with a message listing all searched paths.

#### Scenario: JAR found in module directory
- **WHEN** `ape-rv.jar` exists in `os.path.dirname(__file__)`
- **THEN** `_resolve_jar_path()` SHALL return the absolute path to that file

#### Scenario: JAR not found anywhere
- **WHEN** `ape-rv.jar` does not exist in any search path
- **THEN** `_resolve_jar_path()` SHALL raise `RVToolExecutionError`
- **AND** the error message SHALL list all searched paths

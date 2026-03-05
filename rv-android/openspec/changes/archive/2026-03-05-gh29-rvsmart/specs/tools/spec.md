# Delta Specification: Tool Infrastructure

## Purpose

This delta adds `RVSmartTool` as a new built-in tool in rv-tools, following the same `AbstractTool` contract used by APE, DroidBot, Monkey, and other existing tools. The tool pushes `rvsmart.jar` to the emulator, optionally pushes static analysis data and configuration, then executes the Java agent via `adb shell CLASSPATH=... /system/bin/app_process`. No changes to the registry, factory, or `AbstractTool` base class — only a new consumer of the existing extension points.

## ADDED Requirements

### Requirement: RVSmartTool Registration

`RVSmartTool` SHALL be registered as a built-in tool in `rv_tools.builtin`. It SHALL be included in the `BUILTIN_TOOLS` list in `rv_tools/__init__.py` and auto-registered via `_register_builtin_tools()` on module import.

The tool spec SHALL be:
- `name`: "rvsmart"
- `description`: "Java agent running inside emulator via app_process"
- `url`: "https://github.com/PAMunb/rvsec"
- `version`: "1.0.0"
- `process_pattern`: "br.unb.cic.rvsmart"

#### Scenario: RVSmartTool auto-registration
- **WHEN** `rv_tools` is imported
- **THEN** `ToolRegistry.get_instance().is_tool_registered("rvsmart")` SHALL return True
- **AND** `ToolRegistry.get_instance().get_tool_spec("rvsmart").name` SHALL be "rvsmart"

#### Scenario: Tool creation via factory
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="rvsmart", variant="mvp"))` is called
- **THEN** the factory SHALL return a configured `RVSmartTool` instance
- **AND** `tool.config["mode"]` SHALL be "pure_algorithm"
- **AND** `tool.config["throttle_ms"]` SHALL be 50

### Requirement: RVSmartTool Variants

`RVSmartTool` SHALL define 4 variants with a `"default"` variant (INV-TOOL-02):

| Variant | mode | throttle_ms | Notes |
|---------|------|-------------|-------|
| `default` | pure_algorithm | 50 | Same as mvp |
| `mvp` | pure_algorithm | 50 | Phase 1 target: ~12-16 evt/s |
| `fast` | pure_algorithm | 30 | Reduced throttle for maximum throughput |
| `hybrid` | multimode | 50 | LLM hybrid mode, requires SGLang |

The `hybrid` variant SHALL additionally include `llm_base_url: "http://10.0.2.2:30000/v1"` in its configuration.

#### Scenario: Variant resolution for hybrid mode
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="rvsmart", variant="hybrid"))` is called
- **THEN** `tool.config["mode"]` SHALL be "multimode"
- **AND** `tool.config["llm_base_url"]` SHALL be "http://10.0.2.2:30000/v1"

#### Scenario: Parameter override on variant
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="rvsmart", variant="mvp", parameters={"throttle_ms": 100}))` is called
- **THEN** `tool.config["throttle_ms"]` SHALL be 100 (parameter overrides variant default)

### Requirement: RVSmartTool Execution Contract

`RVSmartTool.execute_tool_specific_logic(task, app)` SHALL:
1. Resolve `rvsmart.jar` path via `JarResolver` (search paths in priority order: (a) `$RVSEC_HOME/rvsec-android/rvsmart/target/rvsmart.jar` — development Maven build, (b) `$TOOLS_DIR/rvsmart/rvsmart.jar` — manual placement, (c) `/opt/rv-android/tools/rvsmart/rvsmart.jar` — Docker image). First match wins.
2. Push `rvsmart.jar` to `/data/local/tmp/rvsmart.jar` via `adb push`.
3. If `task.static_data` is available and has a `json_path`, push the JSON to `/data/local/tmp/static_analysis.json`.
4. If configuration parameters require a properties file, generate `rvsmart.properties` and push to `/data/local/tmp/`.
5. Build the `adb shell` command: `adb -s <device_serial> shell CLASSPATH=/data/local/tmp/rvsmart.jar /system/bin/app_process /data/local/tmp/ br.unb.cic.rvsmart.Main --package <package_name> --timeout <timeout> [--static-data ...] [--config ...] [--mode ...]`.
6. Execute via `self._execute_and_check_command()` with stdout and stderr directed to `task.result.trace_file`.

Before full execution, `RVSmartTool` SHALL run a health check: `adb shell CLASSPATH=... app_process ... --health-check`. This validates ServiceManager connections and performs one UI capture to verify AccessibilityNodeInfo reflection, then exits with code 0 (success) or 1 (failure). If the health check fails, the tool SHALL log an error with the health check output and raise an exception (faster failure feedback than waiting for bootstrap timeout).

Timeout behavior follows the standard `AbstractTool` contract: `RVCommandTimeoutError` is converted to `RVToolTimeoutError` by the base class. This is expected behavior (INV-TOOL-06).

#### Scenario: Health check passes
- **WHEN** `--health-check` exits with code 0
- **THEN** `RVSmartTool` SHALL proceed with full execution

#### Scenario: Health check fails
- **WHEN** `--health-check` exits with code 1
- **THEN** `RVSmartTool` SHALL log "rvsmart health check failed: <stderr output>"
- **AND** `RVSmartTool` SHALL NOT proceed with full execution
- **AND** the task SHALL be marked as failed with a clear error message

#### Scenario: Execution with static analysis data
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `task.static_data.json_path = "/results/exp1/instrumented_apks/cryptoapp/static_analysis.json"`
- **THEN** rvsmart.jar SHALL be pushed to `/data/local/tmp/rvsmart.jar`
- **AND** static_analysis.json SHALL be pushed to `/data/local/tmp/static_analysis.json`
- **AND** the adb shell command SHALL include `--static-data /data/local/tmp/static_analysis.json`

#### Scenario: Execution without static analysis data
- **WHEN** `task.static_data` is None
- **THEN** the adb shell command SHALL NOT include `--static-data`
- **AND** rvsmart SHALL operate in heuristic mode (MopScorer/WtgScorer return 0)

#### Scenario: Timeout after configured duration
- **WHEN** the tool executes for the configured timeout (e.g., 300 seconds)
- **THEN** `RVCommandTimeoutError` SHALL be raised by the Command
- **AND** `AbstractTool.execute()` SHALL convert it to `RVToolTimeoutError`
- **AND** rv-platform SHALL treat this as success (INV-PLT-04)

### Requirement: RVSmartTool Metrics Extraction

After execution completes (timeout or otherwise), `RVSmartTool` SHALL extract the final metrics report from the trace file and write it to a separate file. The extraction logic searches for the last line starting with `RVSMART_METRICS:` in the trace file, parses the JSON payload, and writes it to `rvsmart_metrics.json` alongside the trace file in the task output directory.

Standard coverage metrics (`coverage_metrics` in `TaskResult`) are populated by rv-platform's `CoverageComponent` from logcat `RVSEC-COV` tags — same pipeline as all other tools. No changes to `TaskResult` model or `ResultProcessorComponent`. The `rvsmart_metrics.json` file contains rvsmart-specific operational metrics (throughput, multi-attempt stats, LLM stats) for Optuna calibration and post-processing scripts.

If the `RVSMART_METRICS:` line is not found (e.g., agent crashed before writing it), the tool SHALL log a warning and write a default metrics JSON. This is not a failure condition.

#### Scenario: Metrics extraction from trace file
- **WHEN** the trace file contains a line `RVSMART_METRICS:{"metadata":{...},...}`
- **THEN** `RVSmartTool` SHALL parse the JSON after the prefix
- **AND** the parsed metrics SHALL be written to `rvsmart_metrics.json` in the task output directory

#### Scenario: Missing metrics line
- **WHEN** the trace file does not contain a `RVSMART_METRICS:` line
- **THEN** `RVSmartTool` SHALL log a warning "rvsmart metrics not found in trace file"
- **AND** `RVSmartTool` SHALL write a default metrics JSON to `rvsmart_metrics.json`:
  ```json
  {
    "metadata": {"tool": "rvsmart", "status": "metrics_unavailable", "reason": "RVSMART_METRICS line not found"},
    "exploration": {"iterations": 0, "unique_states": 0, "throughput_evt_per_s": 0},
    "decisions": {"total_actions": 0, "algorithm_actions": 0, "llm_actions": 0},
    "ui_coverage": {"unique_activities": 0, "unique_hashes": 0},
    "confirmed_coverage": {"enabled": false, "unique_methods": 0},
    "llm": {"total_calls": 0, "successful_calls": 0, "circuit_breaker_trips": 0}
  }
  ```
- **AND** execution SHALL NOT be marked as failure
